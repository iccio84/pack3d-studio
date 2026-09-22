"""
Piegatura virtuale: dai pannelli 2D della fustella alle facce 3D con UV.

Il punto delicato di un astuccio a fasciatura verticale
(RETRO - CIELO - FRONTE - FONDO) e' che la piega scavalca il cielo: sul solido
il retro e i due fianchi risultano ribaltati rispetto al piano di stampa.
Qui la cosa viene ricavata dalla catena di pieghe, non imposta a mano.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw

from . import colata, dieline, nero, strati, tracciati
from .dieline import _technical_pens, render_page

Image.MAX_IMAGE_PIXELS = None


def corners(W: float, H: float, D: float) -> dict:
    """Gli otto vertici del solido, centrato nell'origine. Fronte a z = +D/2."""
    hw, hh, hd = W / 2.0, H / 2.0, D / 2.0
    return {
        "FTL": (-hw,  hh,  hd), "FTR": ( hw,  hh,  hd),
        "FBR": ( hw, -hh,  hd), "FBL": (-hw, -hh,  hd),
        "BTL": (-hw,  hh, -hd), "BTR": ( hw,  hh, -hd),
        "BBR": ( hw, -hh, -hd), "BBL": (-hw, -hh, -hd),
    }


# Per ogni faccia: i quattro vertici corrispondenti agli angoli della texture
# nell'ordine (0,0) - (w,0) - (w,h) - (0,h), cioe' alto-sx, alto-dx, basso-dx,
# basso-sx del ritaglio piano.
#
#  - fronte  : orientamento naturale
#  - cielo   : la riga alta del ritaglio confina col retro, quindi va sul dietro
#  - fondo   : la riga alta confina col fronte, quindi va sul davanti
#  - retro   : oltre il cielo la fasciatura si ribalta -> alto piano = basso solido
#  - fianchi : agganciati al retro, ereditano lo stesso ribaltamento
FOLD_V = {
    "front":  ("FTL", "FTR", "FBR", "FBL"),
    "top":    ("BTL", "BTR", "FTR", "FTL"),
    "bottom": ("FBL", "FBR", "BBR", "BBL"),
    "back":   ("BBL", "BBR", "BTR", "BTL"),
    "left":   ("FBL", "BBL", "BTL", "FTL"),
    "right":  ("BBR", "FBR", "FTR", "BTR"),
}


# Fasciatura orizzontale: tutte le pieghe sono attorno a cordonature verticali,
# quindi l'orientamento verticale non si ribalta mai; la direzione orizzontale
# gira attorno alla scatola FRONTE -> FIANCO DX -> RETRO -> FIANCO SX.
FOLD_H = {
    "front":  ("FTL", "FTR", "FBR", "FBL"),
    "right":  ("FTR", "BTR", "BBR", "FBR"),
    "back":   ("BTR", "BTL", "BBL", "BBR"),
    "left":   ("BTL", "FTL", "FBL", "BBL"),
    "top":    ("BTL", "BTR", "FTR", "FTL"),
    "bottom": ("FBL", "FBR", "BBR", "BBL"),
}

FOLDS = {"vwrap": FOLD_V, "hwrap": FOLD_H}


# Su un astuccio APERTO i fianchi non sono agganciati al retro - che non c'e' -
# ma al FRONTE, e il fronte non si ribalta. La quinta dei fianchi va quindi
# ruotata di 180 gradi rispetto a quella di un astuccio chiuso, altrimenti la
# grafica dei fianchi esce capovolta: e' quello che si vedeva sul Pingui T6.
#
# Che questi siano i quad giusti lo conferma FOLD_H senza bisogno di fidarsi
# del ragionamento: nella fasciatura orizzontale i fianchi sono agganciati al
# fronte per costruzione, e le sue due voci sono identiche a queste.
FIANCHI_SUL_FRONTE = {
    "left":  ("BTL", "FTL", "FBL", "BBL"),
    "right": ("FTR", "BTR", "BBR", "FBR"),
}


# Le due falde che chiudono il retro di un astuccio con finestra non sono
# facce intere: sono FASCE del retro, e in mezzo resta il buco da cui si vede
# il prodotto. Qui sta a quale bordo del retro ognuna e' attaccata: `back_top`
# arriva scavalcando il cielo e si ferma in alto, `back_bottom` risale dal
# fondo. Il ritaglio piano si orienta da se', perche' una fascia del retro
# eredita la quinta del retro: basta accorciarla dal lato giusto.
FASCE_RETRO = {"back_top": True, "back_bottom": False}


def _fascia(quad, a, b):
    """La fascia [a, b] di una faccia, in frazioni dell'altezza della texture.

    `a` e' il bordo alto del ritaglio, `b` quello basso, e gli angoli si
    interpolano lungo i due lati verticali della faccia: cosi' la fascia sta
    sul solido dove ci sta la faccia intera, e non serve rifare i conti sul
    ribaltamento della fasciatura.
    """
    c0, c1, c2, c3 = quad

    def mix(p, q, t):
        return tuple(p[i] + (q[i] - p[i]) * t for i in range(3))

    return [mix(c0, c3, a), mix(c1, c2, a), mix(c1, c2, b), mix(c0, c3, b)]


def disegno_tecnico(pdf_path, page_no=0):
    """Gli elementi da togliere dalla texture: i TRATTI, e solo quelli.

    Due passate leggere: la prima trova le penne della fustella, la seconda,
    sapendo gia' cosa cercare, si tiene solo quello che serve. Su uno steso
    curvo (coppe, settori) non ci sono segmenti dritti lunghi da cui dedurre
    la penna: resta valida la regola del filo di capello, che vale anche
    quando di penne non se ne trova nessuna.

    Pieni e scritte NON si scelgono piu' per colore. La regola vecchia -
    "tinta cromatica e non di una tinta piatta, quindi tecnica" - e' stata
    misurata su tutto il parco: su sei file su nove non toglie niente che i
    tratti non togliessero gia', e sugli altri tre cancella grafica, fra cui
    il logo `Brioss` e il bollino "x6" del Pingui. Il perche' sta in
    `strati.py`: una lastra tecnica usa colori che usa anche la grafica, e
    nessuna soglia separa due cose dello stesso colore. Chi lo dice davvero
    e' il livello, e quello si spegne prima di rasterizzare.
    """
    segs, larghezza, altezza = tracciati.segmenti(pdf_path, page_no)
    penne = _technical_pens(segs, larghezza, altezza)
    return tracciati.tecnici(pdf_path, page_no, penne, ())


def _technical_mask(dt, box, scale, margin=1.2):
    """Maschera del disegno tecnico dentro un pannello: tratti di fustella,
    retini delle aree print-free, quote e diciture tecniche."""
    tratti, pieni, scritte = dt
    x0, y0, x1, y1 = box
    W = max(1, round((x1 - x0) * scale))
    H = max(1, round((y1 - y0) * scale))
    m = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(m)

    def pt(x, y):
        return ((x - x0) * scale, (y - y0) * scale)

    for punti, lw in tratti:
        dr.line([pt(*q) for q in punti], fill=255, joint="curve",
                width=max(2, int(round(lw * scale + 2 * margin * scale))))
    for (a, b, c, d), punti in pieni:
        if punti is None:
            dr.rectangle([pt(a, b), pt(c, d)], fill=255)
        else:
            dr.polygon([pt(*q) for q in punti], fill=255)
    for a, b, c, d in scritte:
        dr.rectangle([pt(a - 0.5, b - 0.5), pt(c + 0.5, d + 0.5)], fill=255)
    return np.asarray(m) > 127


def _inpaint(rgb, mask):
    """Riempie le zone mascherate col pixel valido piu' vicino: adatto a tratti
    sottili e a retini, dove l'intorno e' gia' il colore di fondo."""
    from scipy.ndimage import distance_transform_edt
    if not mask.any():
        return rgb
    # Le distanze non ci servono, servono solo gli indici del pixel valido
    # piu' vicino. Chiederle comunque costa un array float64 grande quanto
    # l'immagine: su un foglio come quello del Brioss sono decine di MB
    # calcolati e buttati.
    idx = distance_transform_edt(mask, return_distances=False,
                                 return_indices=True)
    return rgb[idx[0], idx[1]]


def rasterize_panels(pdf_path: str, panels: dict, dpi: int = 300,
                     inset_px: int = 4, page_no: int = 0, clean: bool = True,
                     note=None, nero_deciso=None) -> dict:
    """Ritaglia la grafica di ogni pannello da una rasterizzazione ad alta
    risoluzione. Con `clean` il disegno tecnico viene tolto dalla texture:
    sul modello 3D deve restare solo la grafica di stampa.

    In `note`, se passata, finiscono le righe da dichiarare a chi guarda il
    modello: e' il punto da cui passano tutte le texture - astucci e flowpack,
    server e riga di comando - quindi e' qui che il disegno tecnico si toglie
    e la colata si sostituisce.

    Prima cosa: se il file ha LIVELLI che dicono cosa e' tecnico, si spengono.
    E' l'unico modo che non sbaglia - vedi `strati.py` - e quello che resta da
    togliere a mano sono solo i tratti."""
    scale = dpi / 72.0
    pulito, spenti = (strati.senza_tecnici(pdf_path, page_no) if clean
                      else (pdf_path, []))
    try:
        if note is not None:
            if spenti:
                note.append("livelli tecnici spenti: %s" % ", ".join(spenti))
            else:
                # Detto qui e non solo nelle regole: e' l'unica riga che
                # distingue un file preparato bene da uno su cui la pulizia
                # e' a stima, e chi guarda il modello deve saperlo.
                note.append("nessun livello per il disegno tecnico: la "
                            "pulizia e' a stima, sui soli tratti a filo di "
                            "capello. Chiedere il DT su un livello suo")
        # `nero_deciso` arriva da chi costruisce, che la lastra se l'e'
        # presa all'inizio di tutto: Ghostscript parte con un fork, e
        # forkare a memoria piena la fa contare due volte. Vedi `nero.spia`.
        # Se non arriva - riga di comando - se la prende qui.
        deciso_nero = (nero_deciso if nero_deciso is not None
                       else nero.spia(pulito, page_no, scale))
        sheet = colata.foglio(pulito, scale, page_no, note)
        # La `k` di `kinder` e' nera, e pdfium la fa azzurra perche' ignora la
        # sovrastampa. Si rimette il nero dove la lastra lo dichiara, e solo
        # li': vedi `nero.py` per perche' non si puo' rendere tutto con gs.
        sheet = nero.riporta(pulito, sheet, scale, page_no, note, deciso_nero)
        # Preso il foglio, la pagina in cassa non serve piu' a nessuno: da qui
        # in giu' si alloca la maschera e la texture, e tenerla viva vorrebbe
        # dire sommare due rasterizzazioni nel momento peggiore.
        dieline.scarta_resa()
        dt = disegno_tecnico(pulito, page_no) if clean else None
    finally:
        if pulito != pdf_path:
            try:
                os.unlink(pulito)
            except OSError:
                pass

    out = {}
    for name, p in panels.items():
        box = (round(p.x0 * scale), round(p.y0 * scale),
               round(p.x1 * scale), round(p.y1 * scale))
        im = sheet.crop(box)
        if clean:
            arr = np.asarray(im).copy()
            mask = _technical_mask(dt, (p.x0, p.y0, p.x1, p.y1), scale)
            mask = mask[:arr.shape[0], :arr.shape[1]]
            if mask.shape != arr.shape[:2]:
                pad = np.zeros(arr.shape[:2], bool)
                pad[:mask.shape[0], :mask.shape[1]] = mask
                mask = pad
            im = Image.fromarray(_inpaint(arr, mask))
        w, h = im.size
        if inset_px and w > 4 * inset_px and h > 4 * inset_px:
            im = im.crop((inset_px, inset_px, w - inset_px, h - inset_px))
            im = im.resize((w, h), Image.LANCZOS)
        out[name] = im
    return out


UV = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


# --------------------------------------------------------------------------- #
# lo spessore del cartoncino
# --------------------------------------------------------------------------- #
# Un astuccio non e' una superficie. Se lo fosse - e finora lo era - guardando
# dentro la finestra di un Pingui T6 non si vedrebbe niente: ogni faccia ha una
# normale sola, e da dietro il culling la fa sparire. Il pack diventa un guscio
# di carta zero, e dove e' aperto si vede il vuoto.
#
# Con lo spessore l'interno c'e', ed e' cartoncino: per ogni faccia si aggiunge
# la faccia interna, e su ogni spigolo aperto la costa del taglio, che e' la
# parte che fa leggere lo spessore sul bordo di una finestra.
SPESSORE_CRT = float(os.environ.get("PACK3D_SPESSORE_CRT", "0.45"))

# Il rovescio del cartoncino e il taglio non stanno nell'artwork: il PDF dice
# solo la faccia stampata. Sono due tinte neutre, e vanno dichiarate per quello
# che sono - una stima, non una misura.
INTERNO = (238, 235, 229)
TAGLIO = (212, 203, 188)


def _normale(quad):
    """La normale USCENTE, nella convenzione degli esportatori.

    E' la stessa formula di `exporters._normal`, ripetuta qui per non tirarsi
    dentro quel modulo: sul fronte - (FTL, FTR, FBR, FBL) - da' +z, e il fronte
    sta a z positivo.
    """
    a = np.array(quad[1], float) - np.array(quad[0], float)
    b = np.array(quad[3], float) - np.array(quad[0], float)
    n = -np.cross(a, b)
    return n / (np.linalg.norm(n) or 1.0)


def _nodo(p, griglia=0.02):
    """Un vertice arrotondato alla griglia, per riconoscere gli spigoli in comune."""
    return tuple(round(v / griglia) for v in p)


def _tinta(rgb):
    return Image.new("RGB", (4, 4), tuple(rgb))


def guscio(faces, spessore=SPESSORE_CRT, interno=INTERNO, taglio=TAGLIO):
    """Da un guscio di sole facce esterne a un guscio con spessore.

    Per ogni faccia si aggiunge la faccia INTERNA, spostata di `spessore` lungo
    la normale entrante e con l'avvolgimento rovesciato perche' la sua normale
    guardi dentro; e per ogni spigolo che non confina con nessun'altra faccia
    si aggiunge la COSTA, il taglio del cartoncino.

    Gli avvolgimenti non si ragionano, si derivano: su una superficie orientata
    due facce adiacenti percorrono lo spigolo in comune in senso OPPOSTO.
    Rovesciare l'ordine di un quad rovescia tutti i suoi spigoli, quindi la
    faccia interna e' coerente; e una costa percorre lo spigolo condiviso al
    contrario della faccia da cui nasce. Cosi' il verso viene giusto senza
    dipendere da quale convenzione usano gli esportatori.
    """
    if not spessore or spessore <= 0:
        return list(faces)

    conta = {}
    for f in faces:
        q = f["quad"]
        for i in range(4):
            a, b = _nodo(q[i]), _nodo(q[(i + 1) % 4])
            conta[(a, b) if a <= b else (b, a)] = conta.get(
                (a, b) if a <= b else (b, a), 0) + 1

    pelle, coste = _tinta(interno), _tinta(taglio)
    out = list(faces)
    for f in faces:
        q = [tuple(float(v) for v in p) for p in f["quad"]]
        n = _normale(q)
        dentro = [tuple(np.array(p) - n * spessore) for p in q]
        out.append({"name": f["name"] + " interno",
                    "quad": list(reversed(dentro)), "uv": list(UV),
                    "tex": pelle})
        for i in range(4):
            a, b = _nodo(q[i]), _nodo(q[(i + 1) % 4])
            if conta.get((a, b) if a <= b else (b, a), 0) > 1:
                continue        # spigolo di piega: dentro il cartoncino
            j = (i + 1) % 4
            out.append({"name": "%s taglio %d" % (f["name"], i),
                        "quad": [q[j], q[i], dentro[i], dentro[j]],
                        "uv": list(UV), "tex": coste})
    return out


def build_faces(dims_mm, textures: dict, layout: str = "vwrap",
                panels: dict | None = None, chiuso: bool = True,
                spessore: float = SPESSORE_CRT) -> list:
    """Facce pronte per rasterizzatore ed export: quad 3D + texture + UV.

    Con `panels` si costruiscono anche le falde del retro, che sono fasce e
    non facce: la loro altezza la sa solo la fustella. Con `chiuso` falso i
    fianchi si agganciano al fronte, vedi FIANCHI_SUL_FRONTE. Con `spessore`
    il guscio prende lo spessore del cartoncino, vedi `guscio`.
    """
    W, H, D = dims_mm
    C = corners(W, H, D)
    pieghe = FOLDS[layout]
    if layout == "vwrap" and not chiuso:
        pieghe = {**pieghe, **FIANCHI_SUL_FRONTE}
    faces = []
    for name, keys in pieghe.items():
        if name not in textures:
            continue
        faces.append({
            "name": name,
            "quad": [C[k] for k in keys],
            "uv": list(UV),
            "tex": textures[name],
        })
    if "back" in pieghe and panels:
        retro = [C[k] for k in pieghe["back"]]
        for name, in_alto in FASCE_RETRO.items():
            p = panels.get(name)
            if name not in textures or p is None or H <= 0:
                continue
            t = min(1.0, p.h_mm / H)
            if t <= 0.0:
                continue
            a, b = (1.0 - t, 1.0) if in_alto else (0.0, t)
            faces.append({
                "name": name,
                "quad": _fascia(retro, a, b),
                "uv": list(UV),
                "tex": textures[name],
            })
    return guscio(faces, spessore)
