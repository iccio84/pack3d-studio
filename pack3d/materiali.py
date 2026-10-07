"""
Il materiale del film dai DT secondari: alluminio, white plate, vernice opaca.

Un flowpack e' film di plastica, e la riflessione di serie - lucido, uguale
dappertutto - gli va bene. Quando il film e' METALLIZZATO, o ha una vernice
opaca, il file lo dice con copie del DT, una per lastra, accanto a quella
con la grafica:

- **alluminio** (`Aluminium`, `Aluminium Support`): il supporto e'
  metallizzato. A volte non sta in una copia ma e' il grigio del DT
  principale, scavato dove la grafica copre: sul Nutella Biscuits T3 e' un
  PANTONE 423 C che copre il 35% del foglio, quello che resta scoperto;
- **white plate**: il bianco coprente sotto gli inchiostri. Dove c'e', il
  film resta plastica bianca; dove non c'e', gli inchiostri sono trasparenti
  sul metallo e il pack e' metallizzato del loro colore, o argento dove non
  c'e' inchiostro;
- **vernice opaca** (`Matt Varnish`): opaca sulla plastica, satinata sul
  metallo. Sul Nutella Biscuits sono i raggi attorno al biscotto, che la
  grafica disegna in grigio chiaro sull'alluminio.

Le lastre si riconoscono dal nome, o dalla didascalia scritta accanto alla
copia; quando sono un PANTONE qualsiasi e le scritte sono in curve le dice
l'AI (`controllo.ruoli_lastre`), o il caso le dichiara. Le copie si trovano
sulla pagina dalle linee del DT, in qualunque scala, e la lastra si legge
separata da Ghostscript (`techink.mappe_lastre`): anche quando il bianco sotto
una foto e' un'immagine in DeviceN e non un tracciato.

Il risultato sono due mappe allineate alla texture: il colore base, con gli
inchiostri sul metallo, e metallo/ruvidita' del materiale glTF.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFilter

from . import techink

ALLUMINIO, BIANCO, OPACA = "alluminio", "bianco", "opaca"
RUOLI = (ALLUMINIO, BIANCO, OPACA)

# Come si chiamano. Strette di proposito: un "Silver" o un PANTONE 877 C sono
# inchiostri metallici stampati, non il supporto, e vanno trattati per
# quello che coprono - qui non si trattano. "White" da solo e' il bianco
# coprente (sul film non c'e' altro bianco da stampare), "White Chocolate" no.
_NOMI = (
    (ALLUMINIO, re.compile(
        r"alumin|allumin|metallis|metalliz|vmpet|\bmet\s*(pet|opp|bopp)\b")),
    (BIANCO, re.compile(
        r"white\s*(plate|underprint|base|layer|mode)|underprint|opaque\s*white"
        r"|bianco\s*(coprente|di\s*fondo|sotto)|^(white|bianco|weiss)$")),
    (OPACA, re.compile(
        r"\b(matt?e?|opac[ao]|opaque)\b.*\b(varnish|lacquer|lack|vernice|coating)\b"
        r"|\b(varnish|lacquer|lack|vernice|coating)\b.*\b(matt?e?|opac[ao]|opaque)\b"
        r"|soft\s*touch|mattlack")),
)

# Le copie del DT: rettangoli col rapporto del foglio, in scala qualsiasi, le
# cui linee lunghe sono quelle del DT. Sul Kinder Cards T2 le quattro copie
# sono a 1:2, sul Nutella Biscuits a 1:1 e 200 mm piu' in la'.
SPESSO = 1.2              # punti: i tratti del DT sono a filo di capello
SCALE = (0.2, 1.1)
FIRMA_LATO = 0.25         # le linee della firma: almeno un quarto del lato
FIRMA_MINIMA = 4
COMBACIA = 0.6            # quota delle linee del DT ritrovate nella copia
TOLLERANZA = 0.006        # in frazione del lato

DPI_GUARDA = 36           # la passata che dice dove dipinge ogni lastra
DPI_MASCHERA = 200        # le maschere, nel telaio del foglio
PIENO = 0.25              # quota d'inchiostro per dire dipinto (come techink)
COPERTURA_MINIMA = 0.002  # un campione di legenda e' meno di questo
NEL_DT = 0.3              # una lastra di materiale nel DT principale non c'e'
DIDASCALIA = 40.0         # punti: quanto puo' stare lontano il titolo
PIATTA = 0.9              # inchiostro medio di una campitura tecnica piena

# Il materiale. La riflettanza dell'alluminio metallizzato e' alta, ma non
# quella di uno specchio: sotto il film e la colla perde un po'.
F0_ALLUMINIO = 0.80
RUVIDITA = {"plastica": 0.30, "metallo": 0.16,
            "plastica opaca": 0.72, "metallo opaco": 0.50}


def ruolo_del_nome(nome):
    """Il ruolo che il nome di una lastra, o di una didascalia, dice. O None."""
    n = techink._norm(nome)
    for ruolo, rx in _NOMI:
        if rx.search(n):
            return ruolo
    return None


@dataclass
class Regione:
    """Il DT o una sua copia: riquadro nel telaio di misura, scala, specchio."""
    riquadro: tuple
    scala: float = 1.0
    specchio: bool = False
    principale: bool = False

    @property
    def nome(self):
        if self.principale:
            return "sul DT"
        return "copia %s%s" % ("1:1" if abs(self.scala - 1) < 0.01
                               else "in scala %.2f" % self.scala,
                               ", specchiata" if self.specchio else "")


@dataclass
class Lettura:
    """Cosa il file dice del materiale: le regioni e le lastre coi ruoli."""
    regioni: list
    # nome -> dict(regione=indice o None, coperture=[per regione], ruolo, fonte)
    lastre: dict = field(default_factory=dict)

    def con_ruolo(self, ruolo):
        return [n for n, v in sorted(self.lastre.items())
                if v["ruolo"] == ruolo and v["regione"] is not None]

    def irrisolte(self):
        """Le lastre che stanno in una copia, senza ruolo: le dira' l'AI."""
        return [n for n, v in sorted(self.lastre.items())
                if v["ruolo"] is None and v.get("candidata")]

    def applicabile(self):
        """Il materiale cambia: film metallizzato col suo bianco, o vernice."""
        return bool((self.con_ruolo(ALLUMINIO) and self.con_ruolo(BIANCO))
                    or self.con_ruolo(OPACA))

    def assegna(self, ruoli, fonte):
        """Ruoli da fuori - il caso, l'AI - per nome di lastra.

        Dall'AI, sul DT principale si accetta solo l'alluminio, e solo se e'
        una campitura piena e piatta come il grigio del Nutella Biscuits: una
        lastra sul DT va via dalla texture, e un errore li' cancellerebbe un
        inchiostro della grafica. Il caso invece l'ha guardato qualcuno.
        """
        for nome, ruolo in (ruoli or {}).items():
            n = techink._norm(nome)
            if n not in self.lastre or ruolo not in RUOLI:
                continue
            v = self.lastre[n]
            if fonte == "ai" and v["regione"] == 0 and (
                    ruolo != ALLUMINIO or v.get("piena", 0.0) < PIATTA
                    or not v.get("neutra")):
                continue
            v.update(ruolo=ruolo, fonte=fonte)


# --------------------------------------------------------------------------- #
# le copie del DT
# --------------------------------------------------------------------------- #
def _firma(Hs, Vs, foglio):
    """Le linee lunghe del DT in frazioni del foglio: ("H"|"V", c, a, b)."""
    X0, Y0, X1, Y1 = foglio
    W, H = X1 - X0, Y1 - Y0
    out = []
    for c, a, b in Hs:
        if (Y0 - 1 <= c <= Y1 + 1 and a >= X0 - 1 and b <= X1 + 1
                and b - a >= FIRMA_LATO * W):
            out.append(("H", (c - Y0) / H, (a - X0) / W, (b - X0) / W))
    for c, a, b in Vs:
        if (X0 - 1 <= c <= X1 + 1 and a >= Y0 - 1 and b <= Y1 + 1
                and b - a >= FIRMA_LATO * H):
            out.append(("V", (c - X0) / W, (a - Y0) / H, (b - Y0) / H))
    return out


def _combacia(firma, Ha, Va, r, s, W, H, specchio):
    """La quota della firma ritrovata nel riquadro `r` in scala `s`.

    `Ha` e `Va` sono i segmenti in array (c, a, b): qui si guarda solo
    quello che sta nel riquadro.
    """
    x0, y0, x1, y1 = r
    w, h = s * W, s * H
    sotto = {}
    q = Ha[(Ha[:, 0] >= y0 - 1) & (Ha[:, 0] <= y1 + 1)
           & (Ha[:, 2] >= x0 - 1) & (Ha[:, 1] <= x1 + 1)]
    c, u0, u1 = (q[:, 0] - y0) / h, (q[:, 1] - x0) / w, (q[:, 2] - x0) / w
    if specchio:
        u0, u1 = 1 - u1, 1 - u0
    sotto["H"] = (c, u0, u1)
    q = Va[(Va[:, 0] >= x0 - 1) & (Va[:, 0] <= x1 + 1)
           & (Va[:, 2] >= y0 - 1) & (Va[:, 1] <= y1 + 1)]
    u = (q[:, 0] - x0) / w
    sotto["V"] = (1 - u if specchio else u, (q[:, 1] - y0) / h, (q[:, 2] - y0) / h)
    trovate = 0
    for o, c, a, b in firma:
        cc, aa, bb = sotto[o]
        if np.any((np.abs(cc - c) <= TOLLERANZA)
                  & (np.minimum(b, bb) - np.maximum(a, aa) >= 0.8 * (b - a))):
            trovate += 1
    return trovate / len(firma)


def copie_del_dt(pdf, foglio, page_no=0):
    """Le copie del DT sulla pagina, senza il DT: [Regione].

    Un candidato e' una coppia di linee col rapporto del foglio: due
    orizzontali di uguale estensione a distanza `s * H`, o due verticali a
    `s * W`. Basta una delle due coppie - sul Nutella B-ready T2 il bordo
    sinistro della copia della vernice e' interrotto dalle fasce delle pinne.
    E la copia si conferma solo se dentro ci sono le linee lunghe del DT, nello
    stesso posto: un riquadro interno della grafica col rapporto giusto, come
    sul Kinder Country, non le ha.
    """
    from .tracciati import segmenti
    segs, _w, _h = segmenti(pdf, page_no)
    X0, Y0, X1, Y1 = foglio
    W, H = X1 - X0, Y1 - Y0
    if W <= 0 or H <= 0:
        return []
    Hs = [(c, a, b) for k, c, a, b, st in segs if k == "H" and st[0] <= SPESSO]
    Vs = [(c, a, b) for k, c, a, b, st in segs if k == "V" and st[0] <= SPESSO]
    firma = _firma(Hs, Vs, foglio)
    if len(firma) < FIRMA_MINIMA:
        return []

    candidati = set()
    for lista, lato, altro, verticale in ((Hs, W, H, False), (Vs, H, W, True)):
        # per estensione, a gruppi di 3 punti: due bordi della stessa copia
        # stanno nello stesso gruppo o in quello accanto
        gruppi = {}
        for c, a, b in lista:
            s = (b - a) / lato
            if SCALE[0] <= s <= SCALE[1]:
                gruppi.setdefault((int(a // 3), int(b // 3)), []).append((c, a, b, s))
        for (ka, kb), voci in gruppi.items():
            vicini = sorted(v for da in (-1, 0, 1) for db in (-1, 0, 1)
                            for v in gruppi.get((ka + da, kb + db), ()))
            for c, a, b, s in voci:
                tol = max(0.6, TOLLERANZA * s * altro)
                for c2, a2, b2, _s2 in vicini:
                    d = c2 - c - s * altro
                    if abs(d) <= tol and abs(a2 - a) <= tol and abs(b2 - b) <= tol:
                        r = ((c, a, c2, b) if verticale else (a, c, b, c2))
                        candidati.add((tuple(round(v, 2) for v in r), round(s, 4)))

    def dentro(r, q):
        return (r[0] >= q[0] - 1 and r[1] >= q[1] - 1
                and r[2] <= q[2] + 1 and r[3] <= q[3] + 1)

    Ha = np.array(Hs, float).reshape(-1, 3)
    Va = np.array(Vs, float).reshape(-1, 3)
    tenute = []
    for r, s in candidati:
        if dentro(r, foglio):
            continue                      # il DT stesso, o un suo riquadro
        # Specchiata solo se combacia nettamente meglio: un DT di flowpack e'
        # quasi simmetrico, e le copie del Nutella Biscuits tornano uguali nei
        # due versi. La vista interna del B-ready no.
        dritta = _combacia(firma, Ha, Va, r, s, W, H, False)
        rovescia = _combacia(firma, Ha, Va, r, s, W, H, True)
        specchio = rovescia > dritta + 0.05
        punti = max(dritta, rovescia)
        if punti >= COMBACIA:
            tenute.append((punti, (r[2] - r[0]) * (r[3] - r[1]), r, s, specchio))
    # le piu' grandi e convinte prima; una copia dentro un'altra, o dentro il
    # DT, e' un riquadro della grafica che per caso torna
    tenute.sort(key=lambda t: (-t[1], -t[0]))
    fuori = []
    for _p, _a, r, s, sp in tenute:
        if any(dentro(r, q.riquadro) for q in fuori):
            continue
        if any(not (r[2] < q.riquadro[0] or r[0] > q.riquadro[2]
                    or r[3] < q.riquadro[1] or r[1] > q.riquadro[3]) for q in fuori):
            continue                      # si sovrappone a una gia' presa
        fuori.append(Regione(r, s, sp))
    fuori.sort(key=lambda q: (q.riquadro[1], q.riquadro[0]))
    return fuori


# --------------------------------------------------------------------------- #
# la lettura
# --------------------------------------------------------------------------- #
def _spot(pdf, page_no):
    """Le tinte piatte della pagina, per nome: se non ce n'e', niente da fare."""
    import pypdf
    pagina = pypdf.PdfReader(pdf).pages[page_no]
    return set(techink.technical_separations(
        pagina, prova=lambda n: n not in techink.RESERVED).values())


def _copertura(mappa, riquadro, dpi):
    s = dpi / 72.0
    x0, y0, x1, y1 = (int(round(v * s)) for v in riquadro)
    h, w = mappa.shape
    sub = mappa[max(y0, 0):min(y1, h), max(x0, 0):min(x1, w)]
    if not sub.size:
        return 0.0
    return float(((255 - sub.astype(np.int16)) / 255.0 >= PIENO).mean())


def _neutre(pdf, page_no):
    """Le tinte piatte che a tinta piena sono un grigio neutro: l'alluminio
    disegnato sul DT lo e' (PANTONE 423 C sul Nutella Biscuits), un box area
    arancione no. Si legge la funzione di tipo 2, come `techink.lastre_bianche`."""
    import pypdf
    fuori = set()
    pagina = pypdf.PdfReader(pdf).pages[page_no]

    def grigio(alt, c):
        alt = str(alt[0] if isinstance(alt, list) else alt)
        v = [float(x) for x in c]
        if alt == "/Lab" and len(v) == 3:
            return 25.0 <= v[0] <= 92.0 and abs(v[1]) <= 6.0 and abs(v[2]) <= 6.0
        if alt == "/DeviceCMYK" and len(v) == 4:
            return max(v[:3]) - min(v[:3]) <= 0.08 and 0.12 <= max(v) <= 0.9
        if alt in ("/DeviceRGB", "/CalRGB") and len(v) == 3:
            return max(v) - min(v) <= 0.05 and 0.1 <= v[0] <= 0.85
        if alt in ("/DeviceGray", "/CalGray") and len(v) == 1:
            return 0.1 <= v[0] <= 0.85
        return False

    def giro(res, visti):
        if res is None:
            return
        res = res.get_object()
        if id(res) in visti:
            return
        visti.add(id(res))
        for _k, v in (res.get("/ColorSpace") or {}).items():
            try:
                cs = v.get_object()
                if not (isinstance(cs, list) and cs and cs[0] == "/Separation"):
                    continue
                f = cs[3].get_object()
                alt = cs[2].get_object() if hasattr(cs[2], "get_object") else cs[2]
                if f.get("/FunctionType") == 2 and grigio(alt, f.get("/C1", [])):
                    fuori.add(techink._norm(str(cs[1]).lstrip("/").replace("#20", " ")))
            except Exception:
                continue
        for _k, x in (res.get("/XObject") or {}).items():
            try:
                x = x.get_object()
                if x.get("/Subtype") == "/Form":
                    giro(x.get("/Resources"), visti)
            except Exception:
                continue

    giro(pagina.get("/Resources"), set())
    return fuori


def _piena(mappa, riquadro, dpi):
    """L'inchiostro medio dove la lastra dipinge, nel riquadro: 1 una
    campitura piena, meno una tinta sfumata o un'immagine."""
    s = dpi / 72.0
    x0, y0, x1, y1 = (int(round(v * s)) for v in riquadro)
    h, w = mappa.shape
    sub = (255 - mappa[max(y0, 0):min(y1, h), max(x0, 0):min(x1, w)].astype(np.float32)) / 255.0
    dipinto = sub[sub >= PIENO]
    return float(dipinto.mean()) if dipinto.size else 0.0


_PAROLA = re.compile(r"[A-Za-z]{3,}")


def _titoli(pdf, page_no, copie):
    """{indice della copia: titolo} delle copie che ne hanno uno scritto.

    Il testo si legge copia per copia, in una fascia sopra, sotto e a
    sinistra larga quanto lei: sul Kinder Country i tre titoli stanno sulla
    stessa riga e pdfium li da' come una riga sola. E i titoli di una pagina
    stanno tutti dallo stesso lato: sul Kinder Cards T2 quello di una copia e'
    sopra di lei e sotto quella di prima, e il lato giusto e' quello dove ce
    ne sono di piu'. Un numero da solo e' una quota, non un titolo.
    """
    import pypdfium2 as pdfium
    if not copie:
        return {}
    doc = pdfium.PdfDocument(pdf)
    try:
        pagina = doc[page_no]
        mx0, _my0, _mx1, my1 = pagina.get_mediabox()
        tp = pagina.get_textpage()
        trovati = {}
        for k, q in enumerate(copie):
            a0, b0, a1, b1 = q.riquadro
            fascia = max(DIDASCALIA, 0.25 * (b1 - b0))
            lati = {"sopra": (a0, b0 - fascia, a1, b0),
                    "sotto": (a0, b1, a1, b1 + fascia),
                    "a sinistra": (a0 - 3 * fascia, b0, a0, b0 + fascia)}
            for lato, (x0, y0, x1, y1) in lati.items():
                testo = " ".join(tp.get_text_bounded(
                    mx0 + x0, my1 - y1, mx0 + x1, my1 - y0).split())
                if _PAROLA.search(testo):
                    trovati[(k, lato)] = testo
    finally:
        doc.close()
    if not trovati:
        return {}
    voti = {}
    for (_k, lato), testo in trovati.items():
        voti[lato] = voti.get(lato, 0) + (2 if ruolo_del_nome(testo) else 1)
    lato = max(voti, key=lambda v: (voti[v], v == "sopra"))
    return {k: t for (k, l), t in trovati.items() if l == lato}


def leggi(pdf, foglio, page_no=0, dichiarati=None):
    """La `Lettura` del materiale di questo foglio, o None se non c'e' niente.

    `foglio` e' il riquadro dello steso nel telaio di misura. I ruoli vengono,
    in ordine, dal nome della lastra, dal titolo della sua copia e da
    `dichiarati` - `{lastra: ruolo}` del caso o dell'AI - che vince su tutti.
    """
    if not _spot(pdf, page_no):
        return None
    mappe = techink.mappe_lastre(pdf, page_no, DPI_GUARDA)
    if not mappe:
        return None
    nomi = sorted(mappe)
    ruoli = {n: ruolo_del_nome(n) for n in nomi}
    dichiarati = {techink._norm(k): v for k, v in (dichiarati or {}).items()
                  if v in RUOLI}
    # Le lastre che dipingono in grande fuori dal DT e niente dentro: il segno
    # che il file ha copie per le lastre. Senza, e senza un nome che le dica,
    # le copie non si cercano nemmeno. In grande vuol dire almeno l'1% del
    # foglio: i campioni della legenda sono un decimo.
    s = DPI_GUARDA / 72.0
    foglio_px = max(1.0, (foglio[2] - foglio[0]) * (foglio[3] - foglio[1]) * s * s)
    piatte = []
    for n, m in mappe.items():
        dentro = _copertura(m, foglio, DPI_GUARDA)
        tutta = float(((255 - m.astype(np.int16)) / 255.0 >= PIENO).sum()) / foglio_px
        if dentro < COPERTURA_MINIMA and tutta - dentro >= 5 * COPERTURA_MINIMA:
            piatte.append(n)
    if not (piatte or any(ruoli.values()) or dichiarati):
        return None
    copie = copie_del_dt(pdf, foglio, page_no)
    regioni = [Regione(tuple(foglio), 1.0, False, principale=True)] + copie
    lettura = Lettura(regioni)
    try:
        neutre = _neutre(pdf, page_no)
    except Exception:
        neutre = set()
    for n in nomi:
        cop = [_copertura(mappe[n], q.riquadro, DPI_GUARDA) for q in regioni]
        k = int(np.argmax(cop))
        regione = k if cop[k] >= COPERTURA_MINIMA else None
        # Una lastra di materiale in una copia non dipinge anche il DT: le
        # linee del disegno si', in tutte. E un box area o un'altra lastra
        # tecnica che si chiama per quello che e' non e' un materiale.
        candidata = (regione is not None and k > 0 and cop[0] < NEL_DT * cop[k]
                     and ruoli[n] is None and not techink.area(n)
                     and not techink.tecnica(n))
        lettura.lastre[n] = dict(regione=regione, coperture=cop, ruolo=ruoli[n],
                                 fonte="nome" if ruoli[n] else None,
                                 candidata=candidata,
                                 piena=_piena(mappe[n], foglio, DPI_GUARDA),
                                 neutra=n in neutre)
    for k, testo in _titoli(pdf, page_no, copie).items():
        qui = [(v["coperture"][k + 1], n) for n, v in lettura.lastre.items()
               if v["regione"] == k + 1 and v.get("candidata")]
        if not qui:
            continue
        n = max(qui)[1]
        # il titolo dice cos'e' la lastra della copia: un materiale, o
        # qualcos'altro - Cold Seal, Transparent Support - e allora non e' da
        # chiedere a nessuno
        lettura.lastre[n].update(ruolo=ruolo_del_nome(testo), fonte="didascalia",
                                 didascalia=testo, candidata=False)
    lettura.assegna(dichiarati, "dichiarato")
    return lettura


def da_togliere(lettura):
    """Le lastre di materiale disegnate sul DT principale: non sono
    inchiostri, sono il disegno del materiale, e dalla texture vanno via -
    sul Nutella Biscuits il grigio dell'alluminio. Sotto resta l'inchiostro
    vero, o niente: e niente sul metallo e' argento."""
    if lettura is None or not lettura.applicabile():
        return []
    return [n for n, v in sorted(lettura.lastre.items())
            if v["ruolo"] is not None and v["regione"] == 0]


# --------------------------------------------------------------------------- #
# le maschere e le mappe
# --------------------------------------------------------------------------- #
def _ritaglio(pdf, page_no, riquadro, uscita):
    """Una copia del PDF con la sola regione `riquadro` (telaio di misura)."""
    import pypdf
    from pypdf.generic import RectangleObject
    w = pypdf.PdfWriter(clone_from=pdf)
    for i in range(len(w.pages) - 1, -1, -1):
        if i != page_no:
            w.remove_page(i)
    p = w.pages[0]
    if int(p.get("/Rotate", 0) or 0) % 360:
        raise ValueError("pagina con /Rotate: il ritaglio non sa dove cade")
    mb = p.mediabox
    x0, y0, x1, y1 = riquadro
    r = RectangleObject([float(mb.left) + x0, float(mb.top) - y1,
                         float(mb.left) + x1, float(mb.top) - y0])
    p.mediabox = r
    p.cropbox = r
    for chiave in ("/TrimBox", "/BleedBox", "/ArtBox"):
        if chiave in p:
            del p[chiave]
    with open(uscita, "wb") as fh:
        w.write(fh)
    return uscita


def maschere(pdf, lettura, dimensione, page_no=0):
    """{ruolo: maschera HxW in [0, 1]} nel telaio della texture grezza.

    `dimensione` e' (larghezza, altezza) della texture com'esce da
    `rasterize_panels`, prima di ogni giro. Ogni regione si separa da sola,
    ritagliata, con la risoluzione che serve a darle `DPI_MASCHERA` nel telaio
    del foglio: una copia a 1:2 si separa al doppio.
    """
    W, H = dimensione
    fuori = {}
    cartella = tempfile.mkdtemp(prefix="materiali_")
    try:
        per_regione = {}
        for ruolo in RUOLI:
            for n in lettura.con_ruolo(ruolo):
                k = lettura.lastre[n]["regione"]
                if ruolo == ALLUMINIO and k == 0:
                    continue          # sul DT: il film e' metallizzato tutto
                per_regione.setdefault(k, []).append((n, ruolo))
        for k, voci in sorted(per_regione.items()):
            q = lettura.regioni[k]
            ritaglio = _ritaglio(pdf, page_no, q.riquadro,
                                 os.path.join(cartella, "r%d.pdf" % k))
            # Le linee del DT della copia bucano la lastra: sul Nutella
            # Biscuits il white plate usciva rigato di metallo lungo ogni
            # piega. Via tutte le altre tinte, e poi si chiudono i buchi di un
            # filo che resta, se una linea e' in quadricromia.
            altre = [n for n in lettura.lastre if n not in {v for v, _r in voci}]
            if altre:
                from .artwork import strip_separations
                ritaglio = strip_separations(
                    ritaglio, os.path.join(cartella, "s%d.pdf" % k), altre) or ritaglio
            mappe = techink.mappe_lastre(ritaglio, 0, DPI_MASCHERA / q.scala)
            for n, ruolo in voci:
                m = mappe.get(n)
                if m is None:
                    continue
                ink = Image.fromarray(255 - m)
                ink = ink.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
                if q.specchio:
                    ink = ink.transpose(Image.FLIP_LEFT_RIGHT)
                a = np.asarray(ink.resize((W, H), Image.BILINEAR), np.float32) / 255.0
                fuori[ruolo] = np.maximum(fuori.get(ruolo, 0.0), a)
    finally:
        shutil.rmtree(cartella, ignore_errors=True)
    if lettura.con_ruolo(ALLUMINIO) and any(
            lettura.lastre[n]["regione"] == 0 for n in lettura.con_ruolo(ALLUMINIO)):
        fuori[ALLUMINIO] = np.ones((H, W), np.float32)
    return fuori


def _lineare(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055) * 255.0


def mappe_pbr(tex, mas):
    """(colore base, metallo/ruvidita', quota di metallo, quota di opaca).

    Il metallo e' l'alluminio dove non c'e' il white plate. Il colore base
    sul metallo e' la riflettanza: l'inchiostro trasparente filtra la luce
    che l'alluminio rimanda, cioe' il colore stampato sul bianco moltiplicato
    per quello dell'alluminio. La mappa metallo/ruvidita' e' quella di glTF:
    ruvidita' nel verde, metallo nel blu.
    """
    rgb = np.asarray(tex.convert("RGB"), np.float32)
    h, w = rgb.shape[:2]
    zero = np.zeros((h, w), np.float32)
    bianco = mas.get(BIANCO, zero)
    metallo = mas.get(ALLUMINIO, zero) * (1.0 - bianco) if BIANCO in mas else zero
    opaca = mas.get(OPACA, zero)
    lin = _lineare(rgb)
    base = lin * (1.0 - metallo[..., None] * (1.0 - F0_ALLUMINIO))
    lucida = metallo * RUVIDITA["metallo"] + (1 - metallo) * RUVIDITA["plastica"]
    matt = metallo * RUVIDITA["metallo opaco"] + (1 - metallo) * RUVIDITA["plastica opaca"]
    ruv = lucida * (1.0 - opaca) + matt * opaca
    mr = np.empty((h, w, 3), np.uint8)
    mr[..., 0] = 255
    mr[..., 1] = np.round(np.clip(ruv, 0, 1) * 255).astype(np.uint8)
    mr[..., 2] = np.round(np.clip(metallo, 0, 1) * 255).astype(np.uint8)
    colore = Image.fromarray(np.round(_srgb(base)).astype(np.uint8))
    return colore, Image.fromarray(mr), float(metallo.mean()), float(opaca.mean())


def con_effetto(quota_metallo, quota_opaca):
    """Se il materiale cambia abbastanza da valere un GLB diverso: mezzo
    punto di film metallico, o un millesimo di vernice opaca - i raggi del
    Nutella Biscuits sono l'1%."""
    return quota_metallo >= 0.005 or quota_opaca >= 0.001


def riga(lettura, quota_metallo, quota_opaca):
    """La riga per chi guarda il modello: cosa e' stato letto e da dove."""
    parti = []
    nomi = {ALLUMINIO: "alluminio", BIANCO: "white plate", OPACA: "vernice opaca"}
    for ruolo in RUOLI:
        for n in lettura.con_ruolo(ruolo):
            v = lettura.lastre[n]
            parti.append("%s %s (%s, %s)" % (
                nomi[ruolo], n.upper() if n.startswith("pantone") else n,
                lettura.regioni[v["regione"]].nome,
                {"nome": "dal nome", "didascalia": "dal titolo della copia",
                 "dichiarato": "dichiarato", "ai": "letto dall'AI"}.get(v["fonte"], "-")))
    effetti = []
    if quota_metallo > 0:
        effetti.append("metallo sul %.0f%% del film, dove non c'e' il white plate"
                       % (100 * quota_metallo))
    if quota_opaca > 0:
        effetti.append("vernice opaca sul %.1f%%" % (100 * quota_opaca))
    return "materiali dai DT: %s - %s" % ("; ".join(parti), ", ".join(effetti) or "nessun effetto")


def avviso_senza_bianco(lettura):
    """Alluminio senza white plate: non si sa dove il film resta bianco."""
    if lettura is None or not lettura.con_ruolo(ALLUMINIO) or lettura.con_ruolo(BIANCO):
        return None
    return ("materiali dai DT: il film e' metallizzato (%s) ma non ho trovato il "
            "white plate, che dice dove resta bianco: il modello resta plastica"
            % ", ".join(lettura.con_ruolo(ALLUMINIO)))
