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
from PIL import Image

from . import colata, dieline, nero, strati

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


def rasterize_panels(pdf_path: str, panels: dict, dpi: int = 300,
                     inset_px: int = 4, page_no: int = 0, clean: bool = True,
                     note=None, nero_deciso=None, colata_riquadro=None) -> dict:
    """Ritaglia la grafica di ogni pannello da una rasterizzazione ad alta
    risoluzione. Con `clean` il foglio si prende dal solo livello della
    GRAFICA: sul modello 3D deve restare solo quello che si stampa.

    In `note`, se passata, finiscono le righe da dichiarare a chi guarda il
    modello: e' il punto da cui passano tutte le texture - astucci, flowpack e
    vassoi, server e riga di comando - quindi e' qui che il disegno tecnico si
    spegne e la colata si sostituisce.

    Il disegno tecnico non si toglie piu' DOPO la resa. Prima si spengono i
    livelli che il file dichiara tecnici - l'unico modo che non sbaglia, vedi
    `strati.py` - e poi quello che resta del DT si spegne oggetto per oggetto,
    in pdfium, prima di rendere: e' il livello che il file non aveva, fatto
    dalla costruzione. La maschera sui pixel con il riempimento dal pixel
    vicino, che c'era prima, lungo ogni cordonatura mangiava un millimetro di
    grafica e lo rifaceva coi bordi: era la texture "ritagliata in piu'
    punti". Spento l'oggetto, sotto resta quello che il file ci ha messo.
    """
    scale = dpi / 72.0
    pulito, spenti = (strati.senza_tecnici(pdf_path, page_no) if clean
                      else (pdf_path, []))
    livello = strati.GRAFICA if clean else None
    try:
        # `nero_deciso` arriva da chi costruisce, che la lastra se l'e'
        # presa all'inizio di tutto: Ghostscript parte con un fork, e
        # forkare a memoria piena la fa contare due volte. Vedi `nero.spia`.
        # Se non arriva - riga di comando - se la prende qui.
        deciso_nero = (nero_deciso if nero_deciso is not None
                       else nero.spia(pulito, page_no, scale))
        sheet = colata.foglio(pulito, scale, page_no, note,
                              riquadro=colata_riquadro, livello=livello)
        if note is not None and clean:
            c = strati.CONTI
            stima = "%d tratti%s" % (
                c.get("tratti", 0), " e %d contorni" % c["contorni"]
                if c.get("contorni") else "")
            if spenti:
                note.append("livello DT: i livelli tecnici del file (%s)%s"
                            % (", ".join(spenti),
                               ", piu' %s a filo di capello o di fustella "
                               "fuori da quei livelli" % stima
                               if c.get("tratti") or c.get("contorni") else ""))
            else:
                # Detto qui e non solo nelle regole: e' l'unica riga che
                # distingue un file preparato bene da uno su cui il livello
                # del DT e' a stima, e chi guarda il modello deve saperlo.
                note.append("nessun livello per il disegno tecnico nel file: "
                            "il livello DT l'ho fatto io, %s a filo di "
                            "capello o di fustella spenti e la grafica sotto "
                            "intera. E' una stima: chiedere il DT su un "
                            "livello suo" % stima)
            if c.get("etichette"):
                note.append("didascalie delle aree riservate tolte insieme "
                            "alle aree: %d oggetti - sono il nome del posto "
                            "(Best Before, EAN...), non si stampano"
                            % c["etichette"])
            if c.get("veli"):
                note.append("veli tecnici spenti: %d rettangoli "
                            "semitrasparenti che ricalcano celle del DT - "
                            "gole, fasce coperte - e sul pack sbiadivano la "
                            "grafica" % c["veli"])
            # vedi *la sovrastampa delle immagini* in `strati`
            if c.get("moltiplica"):
                quali = [q for q in (
                    "%d nei colori di processo - l'ombra della colata esce "
                    "rosso scuro e non azzurra" % c["processo"]
                    if c.get("processo") else "",
                    "%d in tinta piatta - una tinta a zero non copre piu' di "
                    "bianco la grafica sotto" % c["tinta"]
                    if c.get("tinta") else "") if q]
                note.append("sovrastampa simulata: %d immagini in sovrastampa "
                            "rese come si stampano, col loro inchiostro "
                            "sommato a quello che trovano (%s). Il "
                            "rasterizzatore la sovrastampa la ignora e le "
                            "dipingeva coprenti"
                            % (c["moltiplica"], "; ".join(quali)))
            if c.get("coperte"):
                note.append("sovrastampa: %d immagini in sovrastampa restano "
                            "coprenti, perche' sotto hanno lo stesso "
                            "inchiostro che stampano, e in macchina lo "
                            "sostituiscono invece di sommarlo" % c["coperte"])
            if c.get("spaiate"):
                note.append("sovrastampa: le immagini del file non tornano con "
                            "quelle del rasterizzatore, e restano coprenti come "
                            "le dipinge lui - l'ombra della colata puo' uscire "
                            "azzurra e una tinta piatta coprire la grafica "
                            "sotto: controllare sul modello")
            elif c.get("senza_gs"):
                note.append("sovrastampa: senza Ghostscript non si vede cosa "
                            "c'e' sotto le immagini, e vanno a moltiplica solo "
                            "le Separation e i DeviceN; le altre restano "
                            "coprenti")
        # Preso il foglio, la pagina in cassa non serve piu' a NESSUNO: `nero`
        # la sua resa se la fa da se', fuori dalla cassa. Buttarla qui e non
        # dopo il nero: quando la colata si sostituisce il foglio che torna e'
        # un'immagine nuova, e quella in cassa sarebbe un secondo foglio intero
        # vivo per niente.
        dieline.scarta_resa()
        # La `k` di `kinder` e' nera, e pdfium la fa azzurra perche' ignora la
        # sovrastampa. Si rimette il nero dove la lastra lo dichiara, e solo
        # li': vedi `nero.py` per perche' non si puo' rendere tutto con gs.
        sheet = nero.riporta(pulito, sheet, scale, page_no, note, deciso_nero,
                             livello=livello)
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
        w, h = im.size
        # Il margine serviva a non portarsi sul bordo della faccia la
        # cordonatura dipinta; ingrandire il ritaglio per coprirla stirava
        # pero' la grafica di qualche pixel. Col livello della grafica la
        # cordonatura non c'e', e sul bordo resta quello che ci va: la grafica
        # che gira sullo spigolo.
        if not clean and inset_px and w > 4 * inset_px and h > 4 * inset_px:
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


# Colonne in cui si divide una faccia che il fronte curvo piega: con 48 la
# corda di ogni colonna si scosta dall'arco meno di un centesimo di mm su una
# freccia di 10.
COLONNE_CURVA = 48


def curva_fronte(faces, dims_mm, freccia, alette=None, colonne=COLONNE_CURVA):
    """L'astuccio a fronte curvo (`dieline._fronte_curvo`): il fronte si
    incurva verso fuori di `freccia` mm in mezzo, retro e fianchi restano
    piani, cielo e fondo diventano a D.

    E' una deformazione di tutto il guscio, interno e coste compresi: ogni
    punto avanza di `freccia * b(x) * (z + D/2) / D`, con b(x) = 1 - (2x/W)^2
    - zero sul retro e sui fianchi, la freccia intera in mezzo al fronte. La
    parabola e l'arco con la stessa freccia differiscono meno della carta.

    Le texture seguono la carta, non lo spazio:
    - lungo il fronte (e lungo la piega di cielo e fondo) la u va per
      lunghezza d'arco, perche' il fronte e' piu' largo della sua corda;
    - su cielo e fondo `alette` dice quanto e' lunga ogni aletta (mm): dalla
      piega col fronte se ne prende quanto e' profondo il cielo in quel
      punto, D ai lati e D + freccia in mezzo, che e' dove la fustella
      taglia l'aletta.
    Ogni faccia toccata porta la sua `maglia`; il `quad` resta quello piano.
    """
    W, _H, D = dims_mm
    alette = alette or {}
    if freccia <= 0 or W <= 0 or D <= 0:
        return faces

    def b(x):
        return np.clip(1.0 - (2.0 * x / W) ** 2, 0.0, 1.0)

    def sposta(P):
        P = np.array(P, float)
        P[..., 2] = P[..., 2] + freccia * b(P[..., 0]) * (P[..., 2] + D / 2.0) / D
        return P

    # lunghezza d'arco lungo il fronte, per la u
    xs = np.linspace(-W / 2.0, W / 2.0, 2001)
    zs = freccia * b(xs)
    arco = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xs), np.diff(zs)))])
    arco /= arco[-1]

    def u_arco(x):
        return np.interp(x, xs, arco)

    for f in faces:
        q = np.array(f["quad"], float)
        lu, lv = abs(q[1, 0] - q[0, 0]), abs(q[3, 0] - q[0, 0])
        if max(lu, lv) < 1e-6:
            continue                 # tutta a x costante: un fianco
        if np.allclose(q[:, 2], -D / 2.0, atol=1e-6):
            continue                 # il retro non si muove
        nu, nv = (colonne, 1) if lu >= lv else (1, colonne)
        uv = np.array(f["uv"], float)
        su, sv = np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1)
        S, T_ = np.meshgrid(su, sv)                       # (nv+1, nu+1)
        S, T_ = S[..., None], T_[..., None]
        P = ((1 - S) * (1 - T_) * q[0] + S * (1 - T_) * q[1]
             + S * T_ * q[2] + (1 - S) * T_ * q[3])
        UVg = ((1 - S) * (1 - T_) * uv[0] + S * (1 - T_) * uv[1]
               + S * T_ * uv[2] + (1 - S) * T_ * uv[3])
        nome = f["name"]
        if nome in ("front", "top", "bottom"):
            # u lungo la x: per lunghezza d'arco
            UVg[..., 0] = u_arco(P[..., 0]) if q[1, 0] > q[0, 0] \
                else 1.0 - u_arco(P[..., 0])
        if nome in ("top", "bottom") and alette.get(nome):
            # v: 0 sul bordo lontano dal fronte per il cielo, sul fronte per il
            # fondo (FOLD_H); quanto ne copre il D in quel punto
            k = np.clip((D + freccia * b(P[..., 0])) / alette[nome], 0.0, 1.0)
            if nome == "top":
                UVg[..., 1] = 1.0 - (1.0 - UVg[..., 1]) * k
            else:
                UVg[..., 1] = UVg[..., 1] * k
        P = sposta(P)
        V = P.reshape(-1, 3)
        UVm = UVg.reshape(-1, 2)
        idx = lambda i, j: i * (nu + 1) + j           # noqa: E731
        T, N = [], np.zeros_like(V)
        for i in range(nv):
            for j in range(nu):
                a, bb, c, d_ = idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)
                T += [(a, c, bb), (a, d_, c)]
                e1, e2 = V[bb] - V[a], V[d_] - V[a]
                n = -np.cross(e1, e2)
                for k_ in (a, bb, c, d_):
                    N[k_] += n
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
        f["maglia"] = ((V, N, UVm, np.array(T, np.int64)), None)
    return faces


def gira_facce(faces, gradi):
    """Le facce del modello finito girate di `gradi` (multiplo di 90) in senso
    antiorario attorno alla normale del fronte, perche' il marchio si legga
    orizzontale e dritto: e' il fronte che la texture non ha potuto girare
    senza stirarlo (`artwork.gira_sulla_grafica`), e allora si gira la
    scatola. Il fronte resta davanti; guscio, interno e coste girano con lui.
    """
    from .verifica import gira_attorno_al_fronte
    if not int(gradi) % 360:
        return faces
    for f in faces:
        f["quad"] = [tuple(float(c) for c in p) for p in
                     gira_attorno_al_fronte(np.array(f["quad"], float), gradi)]
        if f.get("maglia"):
            # il fronte curvo: la maglia gira con la faccia, normali comprese
            f["maglia"] = tuple(
                None if m is None else
                (gira_attorno_al_fronte(np.asarray(m[0], float), gradi),
                 gira_attorno_al_fronte(np.asarray(m[1], float), gradi),
                 m[2], m[3])
                for m in f["maglia"])
    return faces


def build_faces(dims_mm, textures: dict, layout: str = "vwrap",
                panels: dict | None = None, chiuso: bool = True,
                spessore: float = SPESSORE_CRT,
                fianchi_sul_fronte: bool | None = None) -> list:
    """Facce pronte per rasterizzatore ed export: quad 3D + texture + UV.

    Con `panels` si costruiscono anche le falde del retro, che sono fasce e
    non facce: la loro altezza la sa solo la fustella. Con `chiuso` falso i
    fianchi si agganciano al fronte, vedi FIANCHI_SUL_FRONTE; lo stesso se
    `fianchi_sul_fronte` lo dice di un astuccio chiuso, i cui fianchi stampati
    stanno sulla fascia del fronte (`Dieline.fianchi_su`). Con `spessore` il
    guscio prende lo spessore del cartoncino, vedi `guscio`.
    """
    W, H, D = dims_mm
    C = corners(W, H, D)
    pieghe = FOLDS[layout]
    if fianchi_sul_fronte is None:
        fianchi_sul_fronte = not chiuso
    if layout == "vwrap" and fianchi_sul_fronte:
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
