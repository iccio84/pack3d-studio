"""
La fustella di un materiale POP: i pezzi, i loro pannelli e le pieghe.

Un espositore da terra arriva in un PDF solo, a una pagina, coi pezzi stesi
uno accanto all'altro in scala 1:1 (il corpo, la testata, i ripiani, il
divisorio...). Il disegno tecnico e' un colore suo, con le linee continue
per i tagli e quelle tratteggiate per le cordonature: lo si riconosce cosi',
senza sapere come si chiama il livello (`tratti`).

Da li':
- i **pezzi**: i tagli che si toccano, ognuno col suo riquadro; i tagli
  chiusi dentro un pezzo sono i suoi fori (`pezzi`);
- la **griglia**: tutta la pagina in pixel, alla stessa scala della texture,
  coi tagli e le pieghe disegnati (`Griglia`);
- i **pannelli** di un pezzo: le parti del cartone fra tagli e pieghe
  (`Griglia.pannelli`). Un pannello che non tocca nessuna piega e non e' il
  piu' grande del pezzo e' uno sfrido, un foro: si scarta.

Usa i moduli dei pack senza cambiarli (regole/pop.md, *Il confine*).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import re

import numpy as np

MM = 25.4 / 72.0
# sotto questa misura (mm) un gruppo di tagli non e' un pezzo
PEZZO_MIN = 150.0


# un punto della curva ogni tanto, in mm: le curve dei pezzi (le orecchie
# della testata, l'arco del frontalino) devono restare morbide anche da vicino
PASSO_CURVA = 1.5


def _bezier(p0, p1, p2, p3, passi=None):
    p0, p1, p2, p3 = (np.array(p, float) for p in (p0, p1, p2, p3))
    if passi is None:
        lungo = (np.hypot(*(p1 - p0)) + np.hypot(*(p2 - p1)) + np.hypot(*(p3 - p2))) * MM
        passi = max(4, int(np.ceil(lungo / PASSO_CURVA)))
    t = np.linspace(0.0, 1.0, passi + 1)[1:, None]
    pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
    return [tuple(p) for p in pts]


def _polilinea(o):
    """I punti di un tratto di pdfplumber, con le curve di Bezier stese."""
    if o.get("object_type") == "rect":
        x0, t, x1, b = o["x0"], o["top"], o["x1"], o["bottom"]
        return [[(x0, t), (x1, t), (x1, b), (x0, b), (x0, t)]]
    if o.get("path"):
        tratti, cur, inizio = [], [], None
        for cmd in o["path"]:
            c, pts = cmd[0], cmd[1:]
            if c == "m":
                if len(cur) > 1:
                    tratti.append(cur)
                cur = [tuple(pts[0])]
                inizio = tuple(pts[0])
            elif c == "l":
                cur.append(tuple(pts[0]))
            elif c == "c" and cur:
                cur.extend(_bezier(cur[-1], *pts))
            elif c == "h" and cur and inizio is not None:
                cur.append(inizio)
        if len(cur) > 1:
            tratti.append(cur)
        return tratti
    return [[tuple(p) for p in o.get("pts") or []]]


def tratti(pdf, segni=None):
    """`(tagli, pieghe)`: polilinee in mm, y verso il basso, dal colore del
    disegno tecnico. E' il colore (con lo spessore) che ha sia linee continue
    sia tratteggiate, e piu' lunghezza di tutti: i tagli sono le continue, le
    cordonature le tratteggiate. I triangoli chiusi non sono tagli
    (`_triangolo`): se `segni` e' una lista, ci finiscono loro."""
    import pdfplumber
    gruppi = defaultdict(lambda: {"continue": [], "tratteggiate": []})
    with pdfplumber.open(pdf) as doc:
        pg = doc.pages[0]
        for kind in ("lines", "rects", "curves"):
            for o in getattr(pg, kind):
                if not o.get("stroke"):
                    continue
                chiave = (round(float(o.get("linewidth") or 0), 1), str(o.get("stroking_color")))
                dash = o.get("dash")
                tratteggio = bool(dash and dash[0] and any(float(v) > 0 for v in dash[0]))
                for pl in _polilinea(o):
                    if len(pl) < 2:
                        continue
                    pl = [(float(x) * MM, float(y) * MM) for x, y in pl]
                    gruppi[chiave]["tratteggiate" if tratteggio else "continue"].append(pl)

    def lunghezza(pls):
        return sum(float(np.hypot(*np.diff(np.array(p), axis=0).T).sum()) for p in pls)

    candidati = [(lunghezza(g["continue"]) + lunghezza(g["tratteggiate"]), k)
                 for k, g in gruppi.items() if g["continue"] and g["tratteggiate"]]
    if not candidati:
        raise ValueError("nel PDF non c'e' un disegno tecnico con tagli e cordonature: "
                         "servono le linee continue (tagli) e tratteggiate (pieghe) "
                         "dello stesso colore")
    chiave = max(candidati)[1]
    tagli = [pl for pl in gruppi[chiave]["continue"] if not _triangolo(pl)]
    if segni is not None:
        segni.extend(pl for pl in gruppi[chiave]["continue"] if _triangolo(pl))
    return tagli, gruppi[chiave]["tratteggiate"]


def _triangolo(pl):
    """Un triangolo chiuso: il segno sul pezzo (il verso dell'onda, il lato
    di stampa), disegnato col colore dei tagli ma non e' un taglio. Dal
    proprietario: «Elimina tutti i fori triangolari (nel pdf ci sono ma non
    sono parte del dt quindi non vanno considerati)». Tagliato, lasciava un
    foro a triangolo in ogni pezzo."""
    a = np.array(pl, float)
    if len(a) < 4 or float(np.hypot(*(a[0] - a[-1]))) > 0.5:
        return False
    return len(np.unique(np.round(a, 1), axis=0)) == 3


@dataclass
class Pezzo:
    """Un pezzo della fustella: riquadro in mm (x0, y0, x1, y1) sulla
    pagina, i suoi tagli e le sue pieghe."""
    riquadro: tuple
    tagli: list = field(default_factory=list)
    pieghe: list = field(default_factory=list)
    nome: str = ""

    @property
    def larghezza(self):
        return self.riquadro[2] - self.riquadro[0]

    @property
    def altezza(self):
        return self.riquadro[3] - self.riquadro[1]

    def locale(self, x, y):
        """Un punto della pagina (mm) nel riquadro del pezzo (mm)."""
        return x - self.riquadro[0], y - self.riquadro[1]

    def pieghe_dritte(self, minimo=20.0):
        """Le pieghe dritte del pezzo, in mm locali, unite quando sono sulla
        stessa linea: [("V", x, y0, y1)] e [("H", y, x0, x1)]."""
        righe = []
        for pl in self.pieghe:
            a, b = np.array(pl[0]), np.array(pl[-1])
            x0, y0 = self.locale(*a)
            x1, y1 = self.locale(*b)
            if abs(x1 - x0) < 1.0:
                righe.append(("V", (x0 + x1) / 2, min(y0, y1), max(y0, y1)))
            elif abs(y1 - y0) < 1.0:
                righe.append(("H", (y0 + y1) / 2, min(x0, x1), max(x0, x1)))
        unite = []
        for asse in ("V", "H"):
            per = sorted((r for r in righe if r[0] == asse), key=lambda r: (round(r[1]), r[2]))
            for r in per:
                if unite and unite[-1][0] == asse and abs(unite[-1][1] - r[1]) < 1.0:
                    a = unite[-1]
                    unite[-1] = (asse, a[1], min(a[2], r[2]), max(a[3], r[3]))
                else:
                    unite.append(r)
        return [r for r in unite if r[3] - r[2] >= minimo]


def _bbox(pl):
    a = np.array(pl)
    return a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()


def pezzi(tagli, pieghe, tolleranza=1.0):
    """I pezzi: i tagli che si toccano (riquadri entro `tolleranza` mm), poi i
    gruppi piccoli dentro un pezzo grande come suoi fori, e le pieghe che
    cadono nel riquadro."""
    bb = [_bbox(p) for p in tagli]
    padre = list(range(len(tagli)))

    def radice(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    ordine = sorted(range(len(tagli)), key=lambda i: bb[i][0])
    for k, i in enumerate(ordine):
        for j in ordine[k + 1:]:
            if bb[j][0] > bb[i][2] + tolleranza:
                break
            if bb[j][1] <= bb[i][3] + tolleranza and bb[i][1] <= bb[j][3] + tolleranza:
                padre[radice(i)] = radice(j)
    gruppi = defaultdict(list)
    for i in range(len(tagli)):
        gruppi[radice(i)].append(i)
    tutti = []
    for ii in gruppi.values():
        x0 = min(bb[i][0] for i in ii); y0 = min(bb[i][1] for i in ii)
        x1 = max(bb[i][2] for i in ii); y1 = max(bb[i][3] for i in ii)
        tutti.append(((x0, y0, x1, y1), ii))

    def dentro_un_altro(r):
        # una feritoia chiusa dentro un pezzo e' sua, anche se e' lunga
        return any(R is not r and R[0] <= r[0] and r[2] <= R[2] and R[1] <= r[1] and r[3] <= R[3]
                   for R, _ in tutti)

    grandi, piccoli = [], []
    for r, ii in tutti:
        x0, y0, x1, y1 = r
        if max(x1 - x0, y1 - y0) >= PEZZO_MIN and not dentro_un_altro(r):
            grandi.append((r, ii))
        else:
            piccoli.append((r, ii))
    fuori = []
    for r, ii in grandi:
        fuori.append(Pezzo(r, [tagli[i] for i in ii]))
    for r, ii in piccoli:
        for p in fuori:
            R = p.riquadro
            if R[0] <= r[0] and r[2] <= R[2] and R[1] <= r[1] and r[3] <= R[3]:
                p.tagli.extend(tagli[i] for i in ii)
                break
    for pl in pieghe:
        b = _bbox(pl)
        for p in fuori:
            R = p.riquadro
            if R[0] - 2 <= b[0] and b[2] <= R[2] + 2 and R[1] - 2 <= b[1] and b[3] <= R[3] + 2:
                p.pieghe.append(pl)
                break
    fuori.sort(key=lambda p: (round(p.riquadro[1] / 300.0), p.riquadro[0]))
    return fuori


class Griglia:
    """La pagina in pixel (`px_mm` pixel per mm) sul riquadro `zona` (mm),
    coi tagli e le pieghe disegnati: la stessa griglia della texture."""

    def __init__(self, zona, px_mm=1.0):
        self.zona = tuple(float(v) for v in zona)
        self.px = float(px_mm)
        self.W = int(np.ceil((self.zona[2] - self.zona[0]) * self.px))
        self.H = int(np.ceil((self.zona[3] - self.zona[1]) * self.px))

    def a_pixel(self, x, y):
        return (x - self.zona[0]) * self.px, (y - self.zona[1]) * self.px

    def a_mm(self, X, Y):
        return self.zona[0] + X / self.px, self.zona[1] + Y / self.px

    def _disegna(self, polilinee, riquadro):
        from PIL import Image, ImageDraw
        x0, y0, x1, y1 = riquadro
        X0, Y0 = (int(np.floor(v)) - 2 for v in self.a_pixel(x0, y0))
        X1, Y1 = (int(np.ceil(v)) + 2 for v in self.a_pixel(x1, y1))
        im = Image.new("1", (X1 - X0, Y1 - Y0), 0)
        d = ImageDraw.Draw(im)
        for pl in polilinee:
            pts = [self.a_pixel(x, y) for x, y in pl]
            d.line([(px - X0, py - Y0) for px, py in pts], fill=1, width=1)
        return np.array(im, bool), (X0, Y0)

    def _linee_di_piega(self, pezzo, pieno, origine, allunga_mm=40.0):
        """Le pieghe sulla griglia del pezzo, fino al taglio. Una cordonatura
        tratteggiata si ferma qualche millimetro prima del bordo, e lungo la
        linea ha dei ponticelli: cosi' com'e', i due pannelli restavano
        attaccati attorno ai capi. I tratti sulla stessa linea si uniscono
        (`Pezzo.pieghe_dritte`), e ogni piega si allunga dai due capi fino al
        bordo del pezzo, al massimo di `allunga_mm`. Fino al BORDO, non al
        primo taglio: la cordonatura del cartone spesso comincia con un
        taglio di mezzo millimetro sulla sua linea, e fermandosi li' restava
        un passaggio di quattro millimetri fra i due pannelli."""
        from PIL import Image, ImageDraw
        X0, Y0 = origine
        self._ultime_pieghe = []
        h, w = pieno.shape
        im = Image.new("1", (w, h), 0)
        d = ImageDraw.Draw(im)
        linee = []
        for asse, v, a, b in pezzo.pieghe_dritte(minimo=0.0):
            x0, y0 = pezzo.riquadro[0], pezzo.riquadro[1]
            if asse == "V":
                p, q = (x0 + v, y0 + a), (x0 + v, y0 + b)
            else:
                p, q = (x0 + a, y0 + v), (x0 + b, y0 + v)
            linee.append((p, q))
        for pl in pezzo.pieghe:                       # le oblique, come sono
            a, b = np.array(pl[0]), np.array(pl[-1])
            if abs(a[0] - b[0]) >= 1.0 and abs(a[1] - b[1]) >= 1.0:
                linee.append((tuple(a), tuple(b)))
        passi = int(allunga_mm * self.px)
        for p, q in linee:
            P = np.array(self.a_pixel(*p)) - (X0, Y0)
            Q = np.array(self.a_pixel(*q)) - (X0, Y0)
            L = float(np.hypot(*(Q - P)))
            if L < 1e-6:
                continue
            u = (Q - P) / L
            capi = []
            for punto, verso in ((P, -u), (Q, u)):
                fine = punto
                for k in range(1, passi + 1):
                    c = punto + verso * k
                    i, j = int(round(c[1])), int(round(c[0]))
                    if not (0 <= i < h and 0 <= j < w) or not pieno[i, j]:
                        break
                    fine = c
                capi.append(fine)
            d.line([tuple(capi[0]), tuple(capi[1])], fill=1, width=1)
            self._ultime_pieghe.append([self.a_mm(*(c + (X0, Y0))) for c in capi])
        return np.array(im, bool)

    def pannelli(self, pezzo):
        """[(maschera, (X0, Y0))]: i pannelli del pezzo, ognuno con la sua
        maschera ritagliata e lo scarto del ritaglio sulla griglia. Prima il
        cartone (dentro i tagli), poi diviso dalle pieghe."""
        from scipy import ndimage
        tagli, (X0, Y0) = self._disegna(pezzo.tagli, pezzo.riquadro)
        lab, n = ndimage.label(~tagli)
        bordo = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
        pieno = ~np.isin(lab, list(bordo))          # col contorno e i tagli dentro
        dentro = ~tagli & pieno
        pieghe = self._linee_di_piega(pezzo, pieno, (X0, Y0))
        pezzo.linee_piega = list(self._ultime_pieghe)
        # il cartone: dentro i tagli, cioe' quello che il bordo non raggiunge.
        # Lungo una piega del cartone spesso il disegno alterna tratti di
        # piega e brevi tagli (taglio-cordone): fra un tratto e l'altro
        # restava un pixel che teneva uniti i due pannelli. Le pieghe si
        # ingrossano di un pixel per dividere, e il pixel torna ai pannelli.
        pieghe = ndimage.binary_dilation(pieghe, iterations=1) & dentro
        parti, m = ndimage.label(dentro & ~pieghe)
        piega_vicina = ndimage.binary_dilation(pieghe, iterations=2)
        aree = ndimage.sum(np.ones_like(parti), parti, index=range(1, m + 1))
        piu_grande = int(np.argmax(aree)) + 1 if m else 0
        fuori = []
        for k in range(1, m + 1):
            sel = parti == k
            if k != piu_grande and not (sel & piega_vicina).any():
                continue                    # un foro: lo sfrido dentro un taglio chiuso
            ys, xs = np.nonzero(sel)
            a, b, c, d = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            # i pixel di piega accanto al pannello sono cartone suo: senza, fra
            # due pannelli resta una fessura di un pixel
            pieno = ndimage.binary_dilation(sel, iterations=2) & (dentro & pieghe | sel)
            ys, xs = np.nonzero(pieno)
            a, b, c, d = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            fuori.append((pieno[a:b, c:d], (X0 + c, Y0 + a)))
        return fuori


# ---------------------------------------------------------------------------
# La grafica senza il disegno tecnico

def _strato(h):
    """Il nome dello strato (contenuto facoltativo, /OC) di un oggetto della
    pagina di pdfium, o None se non sta in uno strato."""
    import ctypes
    import pypdfium2.raw as R
    for i in range(R.FPDFPageObj_CountMarks(h)):
        mk = R.FPDFPageObj_GetMark(h, i)
        buf = (ctypes.c_ushort * 512)()
        n = ctypes.c_ulong()
        if R.FPDFPageObjMark_GetParamStringValue(mk, b"Title", buf, 1024, ctypes.byref(n)):
            return bytes(buf)[:n.value].decode("utf-16-le").rstrip("\x00")
    return None


def _sul_dt(h, alto, albero, toll=0.6):
    """Un tracciato solo di contorno coi punti tutti sulle linee del disegno
    tecnico (entro `toll` mm): un pezzo del DT."""
    import ctypes
    import pypdfium2.raw as R
    riemp, contorno = ctypes.c_int(), ctypes.c_int()
    R.FPDFPath_GetDrawMode(h, ctypes.byref(riemp), ctypes.byref(contorno))
    if riemp.value or not contorno.value:
        return False
    m = R.FS_MATRIX()
    R.FPDFPageObj_GetMatrix(h, ctypes.byref(m))
    pts = []
    for i in range(R.FPDFPath_CountSegments(h)):
        sg = R.FPDFPath_GetPathSegment(h, i)
        x, y = ctypes.c_float(), ctypes.c_float()
        R.FPDFPathSegment_GetPoint(sg, ctypes.byref(x), ctypes.byref(y))
        X = m.a * x.value + m.c * y.value + m.e
        Y = m.b * x.value + m.d * y.value + m.f
        pts.append((X * MM, (alto - Y) * MM))
    if not pts:
        return False
    d, _ = albero.query(np.array(pts))
    return bool(d.max() <= toll)


def _rendi(pg, griglia):
    PT = 1.0 / MM
    W, Hh = pg.get_size()
    x0, y0, x1, y1 = griglia.zona
    im = pg.render(scale=griglia.px / PT,
                   crop=(x0 * PT, Hh - y1 * PT, W - x1 * PT, y0 * PT)).to_pil()
    return im.convert("RGB").resize((griglia.W, griglia.H))


def resa_senza_dt(pdf, griglia, tagli, linee, quota=0.03):
    """La pagina resa sulla griglia, senza il disegno tecnico: tagli,
    cordonature, quote, triangoli di orientamento. Non si ritocca la grafica
    (un ritocco attorno ai segni rovinava i loghi e i testi vicini): si
    tolgono gli OGGETTI del DT dal PDF prima di renderlo.

    Il DT e' lo strato (contenuto facoltativo) dove stanno le sue linee: si
    toglie tutto lo strato, con le quote e i segni, se toglierlo cambia meno
    di `quota` del cartone dentro i tagli - cioe' se nello strato non c'e'
    la grafica. Se non c'e' uno strato, o nello strato c'e' anche la grafica,
    si tolgono solo i tracciati che stanno sulle linee del DT. `linee` sono
    tutte (tagli, pieghe, segni), in mm; `tagli` servono per sapere dov'e'
    il cartone."""
    from scipy import ndimage
    from scipy.spatial import cKDTree
    albero = cKDTree(_campiona(linee, 0.5))
    # il cartone: dentro i tagli, quello che dal bordo non si raggiunge
    disegno, (X0, Y0) = griglia._disegna(tagli, griglia.zona)
    lab, _ = ndimage.label(~disegno)
    bordo = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    cartone = np.zeros((griglia.H, griglia.W), bool)
    c = ~np.isin(lab, bordo)
    h, w = cartone.shape
    ys, xs = slice(max(0, -Y0), min(c.shape[0], h - Y0)), slice(max(0, -X0), min(c.shape[1], w - X0))
    cartone[ys.start + Y0:ys.stop + Y0, xs.start + X0:xs.stop + X0] = c[ys, xs]
    cartone = ndimage.binary_erosion(cartone, iterations=3)

    strati, sul_dt = _oggetti(pdf, albero)
    tutta = np.asarray(_senza(pdf, griglia, ()), int)
    via = {i for i, _ in sul_dt}
    for nome in sorted({n for _, n in sul_dt if n is not None}):
        senza = np.asarray(_senza(pdf, griglia, strati[nome]), int)
        cambiati = (np.abs(tutta - senza).sum(-1) > 30) & cartone
        if cambiati.sum() <= quota * max(1, cartone.sum()):
            via.update(strati[nome])
    # Lo strato delle note - le zone rosa della colla e di quello che non si
    # stampa, le scritte dei pezzi - non e' la stampa. Dal proprietario: «le
    # note rosa vanno tolte».
    for nome, indici in strati.items():
        if nome and NOTE.search(nome):
            via.update(indici)
    return _senza(pdf, griglia, via)


# I nomi degli strati delle note: note, notes, nota, annotazioni, legenda,
# info, colla, glue
NOTE = re.compile(r"\b(note?s?|nota|annotazion\w*|legend\w*|info|colla|glue)\b", re.I)


def _oggetti(pdf, albero):
    """({strato: [indici]}, [(indice, strato)] dei tracciati sul DT): gli
    oggetti della pagina, per indice nell'ordine di pdfium."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    pg = doc[0]
    alto = pg.get_size()[1]
    strati, sul_dt = {}, []
    for i, o in enumerate(pg.get_objects(max_depth=0)):
        nome = _strato(o.raw)
        strati.setdefault(nome, []).append(i)
        if o.type == 2 and _sul_dt(o.raw, alto, albero):          # 2: un tracciato
            sul_dt.append((i, nome))
    del o
    pg.close()
    doc.close()
    return strati, sul_dt


def _senza(pdf, griglia, indici):
    """La pagina resa sulla griglia senza gli oggetti `indici`."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    pg = doc[0]
    if indici:
        oggetti = list(pg.get_objects(max_depth=0))
        for i in sorted(indici):
            pg.remove_obj(oggetti[i])
        del oggetti
    im = _rendi(pg, griglia)
    pg.close()
    doc.close()
    return im


# ---------------------------------------------------------------------------
# Il contorno di un pannello, con le curve vere del PDF

def contorni(masc):
    """Gli anelli del contorno di una maschera, in pixel (x, y) sui bordi dei
    pixel: un anello per ogni bordo chiuso, il cartone a destra di chi lo
    percorre. Sono a gradini: `aggancia` li porta sulle linee vere."""
    m = np.pad(np.asarray(masc, bool), 1)
    dentro = m[1:-1, 1:-1]
    i, j = np.nonzero(dentro)
    uscite = {}

    def lato(a, b):
        uscite.setdefault(a, []).append(b)

    for di, dj, da, db in ((-1, 0, (0, 0), (1, 0)), (0, 1, (1, 0), (1, 1)),
                           (1, 0, (1, 1), (0, 1)), (0, -1, (0, 1), (0, 0))):
        fuori = ~m[1 + i + di, 1 + j + dj]
        for ii, jj in zip(i[fuori], j[fuori]):
            lato((jj + da[0], ii + da[1]), (jj + db[0], ii + db[1]))
    anelli = []
    while uscite:
        inizio = next(iter(uscite))
        anello = [inizio]
        prec = None
        cur = inizio
        while True:
            lista = uscite.get(cur)
            if not lista:
                break
            if len(lista) > 1 and prec is not None:
                # a un incrocio (due pixel in diagonale) si gira a destra:
                # il cartone resta da una parte sola e gli anelli non si toccano
                dx0, dy0 = cur[0] - prec[0], cur[1] - prec[1]

                def svolta(b):
                    dx1, dy1 = b[0] - cur[0], b[1] - cur[1]
                    return -(dx0 * dy1 - dy0 * dx1)
                lista.sort(key=svolta)
            nxt = lista.pop()
            if not lista:
                del uscite[cur]
            prec, cur = cur, nxt
            if cur == inizio:
                break
            anello.append(cur)
        if len(anello) >= 4:
            anelli.append(np.array(anello, float))
    return anelli


def _campiona(polilinee, passo=0.25):
    """I punti delle polilinee, uno ogni `passo` mm."""
    pts = []
    for pl in polilinee:
        a = np.asarray(pl, float)
        for p, q in zip(a[:-1], a[1:]):
            n = max(1, int(np.ceil(np.hypot(*(q - p)) / passo)))
            t = np.linspace(0.0, 1.0, n + 1)[:, None]
            pts.append(p + (q - p) * t)
    return np.vstack(pts) if pts else np.zeros((0, 2))


def _douglas(a, tol):
    """Douglas-Peucker su un tratto aperto."""
    if len(a) < 3:
        return a
    p, q = a[0], a[-1]
    d = q - p
    L = float(np.hypot(*d))
    if L < 1e-9:
        dist = np.hypot(*(a - p).T)
    else:
        dist = np.abs(d[0] * (a[:, 1] - p[1]) - d[1] * (a[:, 0] - p[0])) / L
    k = int(np.argmax(dist))
    if dist[k] <= tol:
        return np.array([p, q])
    return np.vstack([_douglas(a[:k + 1], tol)[:-1], _douglas(a[k:], tol)])


def semplifica(anello, tol=0.15):
    """Un anello chiuso con meno punti: via quelli che stanno sulla linea
    dei vicini entro `tol` mm. Le curve tengono i loro punti."""
    a = np.asarray(anello, float)
    if len(a) < 4:
        return a
    # si parte dal punto piu' lontano dal primo, cosi' i due tratti sono buoni
    k = int(np.argmax(np.hypot(*(a - a[0]).T)))
    uno = _douglas(np.vstack([a[:k + 1]]), tol)
    due = _douglas(np.vstack([a[k:], a[:1]]), tol)
    return np.vstack([uno[:-1], due[:-1]])


def aggancia(anello, linee, toll=3.0, albero=None):
    """Ogni punto dell'anello sul punto piu' vicino delle `linee` (campionate
    fitte), se e' entro `toll` mm: i gradini dei pixel tornano sulle curve
    del PDF. Torna un punto per punto: quelli finiti uno sull'altro li
    toglie chi chiama."""
    from scipy.spatial import cKDTree
    if albero is None:
        albero = cKDTree(_campiona(linee))
    d, k = albero.query(anello)
    fuori = anello.copy()
    vicino = d <= toll
    fuori[vicino] = albero.data[k[vicino]]
    return fuori


# ---------------------------------------------------------------------------
# Triangolare un pannello: il contorno, i punti dentro, i solchi

def triangola(anelli, extra=None, griglia=None, giri=14, minimo=0.2):
    """(punti Nx2, triangoli Mx3) del poligono: il primo anello e' il
    contorno, gli altri i buchi (pari-dispari, il verso non conta). Come
    `ballotin.triangola`, che il POP usa e non cambia, con in piu' i punti
    `extra` (i campioni dei solchi delle incisioni) e una griglia dentro
    solo se si chiede. I lati del contorno che Delaunay non tiene si
    spezzano a meta' finche' ci sono tutti; si tengono i triangoli col
    baricentro dentro."""
    from scipy.spatial import Delaunay, cKDTree
    from ..ballotin import _pulisci, dentro
    anelli = [_pulisci(np.asarray(a, float)) for a in anelli]
    anelli = [a for a in anelli if len(a) >= 3]
    if not anelli:
        return np.zeros((0, 2)), np.zeros((0, 3), int)
    lati, pts = [], []
    for an in anelli:
        base = len(pts)
        pts.extend(an)
        lati.extend((base + i, base + (i + 1) % len(an)) for i in range(len(an)))
    pts = np.array(pts)
    lo, hi = pts.min(0), pts.max(0)
    bordo = cKDTree(_campiona([np.vstack([a, a[:1]]) for a in anelli], 0.2))
    aggiunti = []
    if griglia:
        xs = np.arange(lo[0] + griglia / 2, hi[0], griglia)
        ys = np.arange(lo[1] + griglia / 2, hi[1], griglia)
        if len(xs) and len(ys):
            aggiunti.append(np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2))
    if extra is not None and len(extra):
        aggiunti.append(np.asarray(extra, float))
    if aggiunti:
        g = np.vstack(aggiunti)
        g = g[dentro(g, anelli)]
        if len(g):
            d, _ = bordo.query(g)
            g = g[d > 0.12]
            if len(g):
                pts = np.vstack([pts, np.unique(np.round(g / 1e-3).astype(np.int64), axis=0) * 1e-3])
    m = 10.0
    cornice = np.array([[lo[0] - m, lo[1] - m], [hi[0] + m, lo[1] - m],
                        [hi[0] + m, hi[1] + m], [lo[0] - m, hi[1] + m]])
    pts = np.vstack([pts, cornice])
    for _ in range(giri):
        tri = Delaunay(pts).simplices
        presenti = set()
        for a, b, c in tri:
            presenti.update(((min(a, b), max(a, b)), (min(b, c), max(b, c)),
                             (min(c, a), max(c, a))))
        # un lato piu' corto di `minimo` non si spezza piu': i due bordi di
        # un taglio dentro il pannello stanno sulla stessa linea, e quel lato
        # Delaunay non lo tiene mai - spezzato a ogni giro, un pannello
        # arrivava a centomila triangoli
        mancano = [(u, v) for u, v in lati if (min(u, v), max(u, v)) not in presenti
                   and np.hypot(*(pts[u] - pts[v])) > minimo]
        if not mancano:
            break
        nuovi, punti = [], []
        for u, v in mancano:
            k = len(pts) + len(punti)
            punti.append((pts[u] + pts[v]) / 2)
            nuovi += [(u, k), (k, v)]
        via = set(mancano)
        lati = [l for l in lati if l not in via] + nuovi
        pts = np.vstack([pts, np.array(punti)])
    tri = Delaunay(pts).simplices
    tri = tri[dentro(pts[tri].mean(1), anelli)]
    usati, nuovo = np.unique(tri, return_inverse=True)
    return pts[usati], nuovo.reshape(tri.shape)


def infittisci(anello, passo):
    """Un anello chiuso con un punto almeno ogni `passo` mm."""
    a = np.asarray(anello, float)
    out = []
    for p, q in zip(a, np.roll(a, -1, axis=0)):
        k = max(1, int(np.ceil(np.hypot(*(q - p)) / passo)))
        out.extend(p + (q - p) * (np.arange(k) / k)[:, None])
    return np.array(out)


def solchi(linee, larghezza, passo):
    """I campioni dei solchi delle `linee` (polilinee in mm): la linea e i
    suoi due bordi a `larghezza / 2`, ogni `passo` mm, piu' le punte. Piu'
    fitti della larghezza: un triangolo non scavalca il solco."""
    a = larghezza / 2.0
    out = []
    for pl in linee:
        p = _campiona([pl], passo)
        if len(p) < 2:
            continue
        t = np.gradient(p, axis=0)
        t /= np.maximum(np.hypot(*t.T), 1e-12)[:, None]
        n = np.stack([-t[:, 1], t[:, 0]], 1)
        out += [p, p + n * a, p - n * a, p[:1] - t[:1] * a, p[-1:] + t[-1:] * a]
    return np.vstack(out) if out else np.zeros((0, 2))


def profondita_solco(xy, linee, larghezza, profondita):
    """Quanto scende il cartone nei punti `xy`: `profondita` sulla linea, a
    V fino a zero a `larghezza / 2`; sotto un quinto e' zero (i bordi del
    solco a fior di faccia, come `incisioni.maglia_incisa`)."""
    from scipy.spatial import cKDTree
    if not linee or not len(xy):
        return np.zeros(len(xy))
    albero = cKDTree(_campiona(linee, 0.05))
    d, _ = albero.query(xy)
    p = profondita * np.clip(1.0 - d / (larghezza / 2.0), 0.0, 1.0)
    p[p < 0.2 * profondita] = 0.0
    return p


def tagli_interni(pezzo, distanza=2.0):
    """I tagli del pezzo che stanno dentro il cartone senza toccarne il
    contorno: tutti i loro punti a piu' di `distanza` mm da fuori."""
    from scipy import ndimage
    G = Griglia(pezzo.riquadro, 1.0)
    disegno, (X0, Y0) = G._disegna(pezzo.tagli, pezzo.riquadro)
    lab, _ = ndimage.label(~disegno)
    bordo = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    fuori = np.isin(lab, bordo)
    dist = ndimage.distance_transform_edt(~fuori)
    h, w = dist.shape
    out = []
    for pl in pezzo.tagli:
        p = _campiona([pl], 0.5)
        X, Y = G.a_pixel(p[:, 0], p[:, 1])
        i = np.clip(np.round(Y - Y0).astype(int), 0, h - 1)
        j = np.clip(np.round(X - X0).astype(int), 0, w - 1)
        if dist[i, j].min() > distanza:
            out.append(pl)
    return out
