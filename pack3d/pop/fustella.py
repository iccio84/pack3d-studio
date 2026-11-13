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

import numpy as np

MM = 25.4 / 72.0
# sotto questa misura (mm) un gruppo di tagli non e' un pezzo
PEZZO_MIN = 150.0


def _bezier(p0, p1, p2, p3, passi=10):
    t = np.linspace(0.0, 1.0, passi + 1)[1:, None]
    p0, p1, p2, p3 = (np.array(p, float) for p in (p0, p1, p2, p3))
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


def tratti(pdf):
    """`(tagli, pieghe)`: polilinee in mm, y verso il basso, dal colore del
    disegno tecnico. E' il colore (con lo spessore) che ha sia linee continue
    sia tratteggiate, e piu' lunghezza di tutti: i tagli sono le continue, le
    cordonature le tratteggiate."""
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
    return gruppi[chiave]["continue"], gruppi[chiave]["tratteggiate"]


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
