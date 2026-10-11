"""
La scatola a punta: fronte e retro che in cima si chiudono uno contro l'altro,
senza cielo, coi fianchi che rientrano a soffietto.

Lo steso, lungo la colonna del corpo:

    ALETTA - CRESTA - FRONTE - FONDO - RETRO

con i fianchi agganciati al FRONTE. Sui fianchi una cordonatura orizzontale
che non attraversa il corpo - la piega del soffietto - divide la parte dritta,
sotto, dalla parte che sale verso la cima, e sopra la piega le cordonature
oblique a V fanno rientrare il fianco fra fronte e retro. Montata, la scatola
e' dritta fino all'altezza della piega; sopra, fronte e retro si inclinano
fino a toccarsi in cima, dove la cresta (la fascia stretta oltre il fronte)
fa da colmo e l'aletta scende sul retro e ci si incolla. Che l'aletta stia
appoggiata sul retro, e non dritta in su come la cresta di un cartone del
latte, l'ha detto chi aveva il pack in mano (vedi REGOLE.md, *La scatola a
punta*); lo dice anche la fustella, con l'area di colla in cima al retro.

Il fondo e' a soffietto: la sua fascia e' piu' lunga della profondita', con
una cordonatura in mezzo, e montato si appiattisce. Sul modello e' piatto,
con la sua grafica portata alla profondita' della scatola.

La texture e' il DT intero, come per il ballotin: ogni pezzo della maglia
prende la grafica dal suo posto sul foglio, e il verso giusto viene da se'.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import dieline as dl
from . import folding

PT2MM = dl.PT2MM

# la cresta e' una fascia stretta, una doppia cordonatura; oltre e' l'aletta
CRESTA_MAX = 6.0
ALETTA_MIN = 8.0
FIANCO_MIN = 10.0


@dataclass
class Punta:
    """Le quote dello steso, in mm sul foglio (y in giu'), e del solido."""
    regione: tuple          # ingombro della fustella, in punti
    xL: float               # bordi del corpo
    xR: float
    D: float                # profondita': la larghezza dei fianchi
    yP: float               # bordo libero dell'aletta
    yR: float               # piega fra aletta e cresta
    yF0: float              # cima del fronte
    yG: float               # piega del soffietto, sui fianchi
    yF1: float              # piede del fronte
    yB0: float              # piede del retro
    yB1: float              # cima del retro
    # dove finiscono i tagli a 45 gradi che partono dagli angoli della piega
    # del soffietto: quanto dentro dal bordo del fianco (x) e quanto sopra la
    # piega (y). Li' comincia la gamba della V. Vedi `_tagli`.
    taglio_x: float = 0.0
    taglio_y: float = 0.0

    @property
    def W(self):
        return self.xR - self.xL

    @property
    def cresta(self):
        return abs(self.yF0 - self.yR)

    @property
    def aletta(self):
        return abs(self.yR - self.yP)

    @property
    def dritto(self):
        """L'altezza della parte dritta: dal piede alla piega del soffietto."""
        return abs(self.yF1 - self.yG)

    @property
    def falda(self):
        """La parte del fronte che sale inclinata verso la cima."""
        return abs(self.yG - self.yF0)

    @property
    def chiude(self):
        """Quanto chiude ognuna delle due falde: mezza profondita' meno la
        cresta."""
        return (self.D - self.cresta) / 2.0

    @property
    def salita(self):
        """Quanto sale la falda: chiude mezza profondita' meno la cresta."""
        return float(np.sqrt(max(self.falda ** 2 - self.chiude ** 2, 0.0)))

    @property
    def altezza(self):
        return self.dritto + self.salita

    @property
    def fondo(self):
        return abs(self.yB0 - self.yF1)

    @property
    def dims_mm(self):
        return (round(self.W, 1), round(self.altezza, 1), round(self.D, 1))


def _oblique(tratti, box):
    """I mm di tratti obliqui della fustella col punto medio nel riquadro."""
    a, b, c, e = box
    tot = 0.0
    for p in tratti:
        p = np.asarray(p, float)
        if len(p) < 2:
            continue
        d = np.diff(p, axis=0)
        L = np.hypot(d[:, 0], d[:, 1])
        m = (p[:-1] + p[1:]) / 2.0
        ok = ((L > 0.3) & (np.abs(d[:, 1]) > 0.2 * L) & (np.abs(d[:, 1]) < 0.98 * L)
              & (m[:, 0] >= a) & (m[:, 0] <= c) & (m[:, 1] >= b) & (m[:, 1] <= e))
        tot += float(L[ok].sum())
    return tot


def _piega_dei_fianchi(d, fronte, fianchi, corpo):
    """La cordonatura orizzontale che attraversa tutti e due i fianchi e NON
    il corpo, dentro la fascia del fronte: la piega del soffietto. In punti."""
    y0, y1 = fronte
    h = y1 - y0
    out = []
    # le quote dalle cordonature stesse: la piega e' spesso tratteggiata, e i
    # tratti corti non entrano nella griglia `d.ys`
    for y in sorted({round(cy, 1) for cy, _a, _b in d.hsegs}):
        if out and abs(y - out[-1]) < 2.5:
            continue
        if not (y0 + 0.1 * h < y < y1 - 0.1 * h):
            continue

        def copre(x0, x1):
            span = 0.0
            for cy, a, b in d.hsegs:
                if abs(cy - y) < 2.5:
                    span += max(0.0, min(b, x1) - max(a, x0))
            return span / max(x1 - x0, 1e-9)

        if (all(copre(*f) >= 0.6 for f in fianchi)
                and copre(*corpo) < 0.3):
            out.append(y)
    return out[0] if len(out) == 1 else None


def _tagli(tratti, angoli, verso_su):
    """(x, y) in mm: dove finiscono i tagli a 45 gradi che dagli angoli della
    piega del soffietto salgono verso le gambe della V. Da ogni angolo si
    segue la catena di tratti obliqui allineati; la sua fine e' il punto in cui
    il taglio diventa la gamba della V, una cordonatura. (0, 0) se non ci sono
    su tutti e quattro gli angoli: allora la V parte dagli angoli.

    `verso_su` e' il segno di y verso la cima del fianco, sul foglio."""
    segs = []
    for p in tratti:
        p = np.asarray(p, float)
        for a, b in zip(p[:-1], p[1:]):
            d = b - a
            L = float(np.hypot(*d))
            if L > 0.3 and 0.2 * L < abs(d[1]) < 0.98 * L:
                segs.append((a, b))
    fini = []
    for c in angoli:
        c = np.asarray(c, float)
        fine, dirz = c, None
        for _ in range(20):
            passo = None
            for a, b in segs:
                for p, q in ((a, b), (b, a)):
                    if np.hypot(*(p - fine)) > 0.6:
                        continue
                    d = (q - p) / np.hypot(*(q - p))
                    if (q[1] - p[1]) * verso_su <= 0:
                        continue            # verso la cima, non indietro
                    if dirz is not None and float(d @ dirz) < 0.996:
                        continue            # dritto, non la gamba della V
                    passo = (q, d)
            if passo is None:
                break
            fine, dirz = passo
        if dirz is None:
            return 0.0, 0.0
        fini.append(np.abs(fine - c))
    m = np.mean(fini, axis=0)
    return float(m[0]), float(m[1])


def riconosci(pdf, page_no=0):
    """La scatola a punta, o None se la fustella non e' la sua."""
    d = dl.extract(pdf, page_no)
    xs = d.xs
    if len(xs) < 4 or len(d.ys) < 5:
        return None
    ci = max(range(len(xs) - 1), key=lambda i: xs[i + 1] - xs[i])
    corpo = (xs[ci], xs[ci + 1])
    ys = d.rows_in_col(*corpo)
    if len(ys) < 5:
        return None
    fasce = [(ys[i], ys[i + 1]) for i in range(len(ys) - 1)]

    # il fronte: la fascia piu' alta che porta un fianco per parte, uguali
    fronte, fianchi = None, None
    for a, b in sorted(fasce, key=lambda f: f[0] - f[1]):
        cx = d.cols_in_row(a, b)
        if len(cx) < 4:
            continue
        cols = [(cx[i], cx[i + 1]) for i in range(len(cx) - 1)]
        k = max(range(len(cols)), key=lambda i: cols[i][1] - cols[i][0])
        if k < 1 or k + 1 >= len(cols):
            continue
        if abs(cols[k][0] - corpo[0]) > 3 or abs(cols[k][1] - corpo[1]) > 3:
            continue
        sx, dx = cols[k - 1], cols[k + 1]
        ws, wd = (sx[1] - sx[0]) * PT2MM, (dx[1] - dx[0]) * PT2MM
        if min(ws, wd) < FIANCO_MIN or abs(ws - wd) > max(1.5, 0.08 * max(ws, wd)):
            continue
        fronte, fianchi = (a, b), (sx, dx)
        break
    if fronte is None:
        return None
    yG = _piega_dei_fianchi(d, fronte, fianchi, corpo)
    if yG is None:
        return None
    # la cima del fronte e' il capo piu' vicino alla piega del soffietto
    alto_in_su = (yG - fronte[0]) < (fronte[1] - yG)
    yF0, yF1 = (fronte[0], fronte[1]) if alto_in_su else (fronte[1], fronte[0])
    D = ((fianchi[0][1] - fianchi[0][0]) + (fianchi[1][1] - fianchi[1][0])) / 2.0 * PT2MM

    # oltre la cima: [cresta] e aletta, poi il foglio finisce
    oltre = [f for f in fasce if (f[1] <= yF0 + 0.5 if alto_in_su else f[0] >= yF0 - 0.5)]
    oltre.sort(key=lambda f: abs((f[0] + f[1]) / 2 - yF0))
    alte = [(f[1] - f[0]) * PT2MM for f in oltre]
    if len(alte) == 1:
        yR, yP = yF0, (oltre[0][0] if alto_in_su else oltre[0][1])
        if alte[0] < ALETTA_MIN:
            return None
    elif len(alte) == 2 and alte[0] <= CRESTA_MAX and alte[1] >= ALETTA_MIN:
        yR = oltre[0][0] if alto_in_su else oltre[0][1]
        yP = oltre[1][0] if alto_in_su else oltre[1][1]
    else:
        return None

    # oltre il piede: il fondo, poi il retro alto come il fronte, fino in fondo
    fine = ys[-1] if alto_in_su else ys[0]
    Hf = abs(yF1 - yF0)
    cand = [y for y in ys if (y > yF1 if alto_in_su else y < yF1)]
    yB0 = None
    for y in cand:
        if abs(abs(fine - y) - Hf) * PT2MM <= max(3.0, 0.03 * Hf * PT2MM):
            yB0 = y
            break
    if yB0 is None:
        return None
    fondo = abs(yB0 - yF1) * PT2MM
    if not (0.8 * D <= fondo <= 1.5 * D):
        return None

    m = PT2MM
    p = Punta(regione=d.bbox, xL=corpo[0] * m, xR=corpo[1] * m, D=D,
              yP=yP * m, yR=yR * m, yF0=yF0 * m, yG=yG * m, yF1=yF1 * m,
              yB0=yB0 * m, yB1=fine * m)
    # la falda deve poter chiudere la profondita', e l'aletta starci sopra
    if p.falda <= (p.D - p.cresta) / 2.0 + 2.0 or p.aletta > p.falda + 2.0:
        return None
    # il soffietto: le cordonature oblique sopra la piega, su tutti e due i
    # fianchi. Senza, una scatola con la piega orizzontale sui fianchi non e'
    # una scatola a punta.
    from .ballotin import tratti_fustella
    tratti = tratti_fustella(pdf, page_no)
    lo, hi = sorted((p.yG, p.yF0))
    for f in fianchi:
        if _oblique(tratti, (f[0] * m, lo, f[1] * m, hi)) < p.falda:
            return None
    angoli = [(x * m, p.yG) for f in fianchi for x in f]
    tx, ty = _tagli(tratti, angoli, np.sign(p.yF0 - p.yG))
    # i tagli devono stare nel fianco e sotto la cima
    if 0.0 < tx < p.D / 2.0 - 1.0 and 0.0 < ty < min(p.chiude, p.falda / 2.0):
        p.taglio_x, p.taglio_y = tx, ty
    return p


def dichiara(p):
    """Le righe che la pagina mostra prima di costruire."""
    return ["scatola a punta: %.1f x %.1f x %.1f mm" % p.dims_mm,
            "dritta per %.1f mm, poi fronte e retro si chiudono in cima con "
            "falde da %.1f mm" % (p.dritto, p.falda),
            "fianchi a soffietto: sopra la piega rientrano inclinati fino alla "
            "punta sotto la cresta, come il fianco di un cartone del latte",
            "aletta da %.1f mm piegata giu' e incollata sul retro" % p.aletta,
            "fondo a soffietto (%.1f mm steso), sul modello piatto" % p.fondo]


def _lerp(a, b, t):
    return a + (b - a) * t


def maglia(p, origine_mm, px_mm, misura_tex, spessore=None):
    """(V, UV, T) della scatola a punta chiusa, in mm, con la texture del DT
    intero e sotto le strisce del rovescio (`ballotin.con_interno`). Il fronte
    guarda +Z, la cima +Y, il fondo sta a Y = 0."""
    from .ballotin import STRISCIA
    sp = folding.SPESSORE_CRT if spessore is None else spessore
    W, D, t = p.W, p.D, p.cresta
    h1, s, c, v = p.dritto, p.falda, p.chiude, p.salita
    H = h1 + v
    Wt, Ht = misura_tex
    uv_interno = np.array([0.5, (Ht - 1.5 * STRISCIA) / Ht])
    ox, oy = origine_mm

    def uv(sx, sy):
        return ((sx - ox) * px_mm / Wt, (sy - oy) * px_mm / Ht)

    def x_corpo(X):
        return p.xL + (X + W / 2.0)

    def x_fianco(Z, destro):
        # il fianco e' agganciato al fronte: dal suo bordo verso il retro
        return p.xR + (D / 2.0 - Z) if destro else p.xL - (D / 2.0 - Z)

    yBG = p.yB0 + np.sign(p.yB1 - p.yB0) * h1      # piega del soffietto sul retro
    V, UV, T = [], [], []

    def quad(P3, S2, fuori, interno=True):
        """Un pezzo piano: tre o quattro angoli 3D e i loro punti sul foglio."""
        P3 = np.asarray(P3, float)
        n = np.cross(P3[1] - P3[0], P3[2] - P3[0])
        tri = [(0, 1, 2), (0, 2, 3)][:len(P3) - 2]
        if float(n @ np.asarray(fuori, float)) < 0:
            tri = [(i, k, j) for i, j, k in tri]
            n = -n
        n = n / (np.linalg.norm(n) or 1.0)
        b = len(V)
        V.extend(P3.tolist())
        UV.extend([uv(*q) for q in S2])
        T.extend([(b + i, b + j, b + k) for i, j, k in tri])
        if interno:
            b = len(V)
            V.extend((P3 - n * sp).tolist())
            UV.extend([tuple(uv_interno)] * len(P3))
            T.extend([(b + i, b + k, b + j) for i, j, k in tri])

    hw = W / 2.0
    # fronte, dritto e falda
    quad([(-hw, 0, D / 2), (hw, 0, D / 2), (hw, h1, D / 2), (-hw, h1, D / 2)],
         [(x_corpo(-hw), p.yF1), (x_corpo(hw), p.yF1),
          (x_corpo(hw), p.yG), (x_corpo(-hw), p.yG)], (0, 0, 1))
    quad([(-hw, h1, D / 2), (hw, h1, D / 2), (hw, H, t / 2), (-hw, H, t / 2)],
         [(x_corpo(-hw), p.yG), (x_corpo(hw), p.yG),
          (x_corpo(hw), p.yF0), (x_corpo(-hw), p.yF0)], (0, c, v))
    # retro, dritto e falda: la piega sul fondo non specchia le x
    quad([(-hw, 0, -D / 2), (hw, 0, -D / 2), (hw, h1, -D / 2), (-hw, h1, -D / 2)],
         [(x_corpo(-hw), p.yB0), (x_corpo(hw), p.yB0),
          (x_corpo(hw), yBG), (x_corpo(-hw), yBG)], (0, 0, -1))
    quad([(-hw, h1, -D / 2), (hw, h1, -D / 2), (hw, H, -t / 2), (-hw, H, -t / 2)],
         [(x_corpo(-hw), yBG), (x_corpo(hw), yBG),
          (x_corpo(hw), p.yB1), (x_corpo(-hw), p.yB1)], (0, c, -v))
    # fondo: piatto, con la fascia del soffietto portata alla profondita'
    quad([(-hw, 0, D / 2), (hw, 0, D / 2), (hw, 0, -D / 2), (-hw, 0, -D / 2)],
         [(x_corpo(-hw), p.yF1), (x_corpo(hw), p.yF1),
          (x_corpo(hw), p.yB0), (x_corpo(-hw), p.yB0)], (0, -1, 0))
    # l'aletta sul retro, uno spessore fuori: dalla cresta in giu' lungo la falda
    giu = np.array([0.0, -v, -c]) / s            # verso il basso lungo il retro
    nb = np.array([0.0, c, -v]) / s              # normale uscente del retro
    a0 = np.array([0.0, H, -t / 2]) + nb * sp
    a1 = a0 + giu * min(p.aletta, s)
    quad([(-hw, a0[1], a0[2]), (hw, a0[1], a0[2]), (hw, a1[1], a1[2]), (-hw, a1[1], a1[2])],
         [(x_corpo(-hw), p.yR), (x_corpo(hw), p.yR),
          (x_corpo(hw), p.yP), (x_corpo(-hw), p.yP)], nb, interno=False)
    r0, r1 = a0 - nb * sp / 2.0, a1 - nb * sp / 2.0     # il rovescio
    quad([(-hw, r0[1], r0[2]), (hw, r0[1], r0[2]), (hw, r1[1], r1[2]), (-hw, r1[1], r1[2])],
         [tuple(np.array([ox, oy]) + uv_interno * np.array([Wt, Ht]) / px_mm)] * 4,
         -nb, interno=False)
    # la cresta, dal colmo del fronte all'attacco dell'aletta
    quad([(-hw, H, t / 2), (hw, H, t / 2), (hw, a0[1], a0[2]), (-hw, a0[1], a0[2])],
         [(x_corpo(-hw), p.yF0), (x_corpo(hw), p.yF0),
          (x_corpo(hw), p.yR), (x_corpo(-hw), p.yR)], (0, 1, 0))
    # i fianchi: dritti fino alla piega, poi il soffietto, come il fianco di
    # un cartone del latte. Sopra la piega il fianco e' staccato dal fronte e
    # dal retro (tagli) e resta attaccato solo alla piega. Il pezzo centrale -
    # fra la piega, i tagli a 45 gradi agli angoli e le gambe della V - gira
    # intero sulla piega e si inclina dentro fino alla punta sotto la cresta,
    # in un piano solo: fra la piega e la fine dei tagli non c'e' nessuna
    # cordonatura. Le ali, fuori dalle gambe della V, girano sulle gambe e
    # riempiono lo spazio fino al bordo delle falde, contro il loro rovescio,
    # con la stampa verso il soffietto. Fra la gamba e il bordo della falda
    # l'ala si incurva appena (un paio di mm): la si fa a strisce. Vedi
    # REGOLE.md, *La scatola a punta*.
    su = np.sign(p.yF0 - p.yG)                   # verso la cima, sul foglio
    tx, ty = p.taglio_x, p.taglio_y
    nf = np.array([0.0, c, v]) / s               # normale uscente del fronte
    for destro, X, verso in ((False, -hw, -1.0), (True, hw, 1.0)):
        quad([(X, 0, D / 2), (X, 0, -D / 2), (X, h1, -D / 2), (X, h1, D / 2)],
             [(x_fianco(D / 2, destro), p.yF1), (x_fianco(-D / 2, destro), p.yF1),
              (x_fianco(-D / 2, destro), p.yG), (x_fianco(D / 2, destro), p.yG)],
             (verso, 0, 0))
        su3 = np.array([-verso * c, v, 0.0]) / s     # in su lungo il pezzo centrale
        n_c = np.array([verso * v, c, 0.0]) / s      # e la sua normale, fuori

        def punto(z, eta):
            return np.array([X, h1, z]) + eta * su3

        def foglio(z, eta):
            return np.array([x_fianco(z, destro), p.yG + su * eta])

        A = punto(0.0, s)
        CE = {k: punto(k * (D / 2 - tx), ty) for k in (1, -1)}
        # il pezzo centrale: dalla piega alla fine dei tagli, poi a punta
        if tx > 0:
            quad([punto(D / 2, 0), punto(-D / 2, 0), CE[-1], CE[1]],
                 [foglio(D / 2, 0), foglio(-D / 2, 0),
                  foglio(-(D / 2 - tx), ty), foglio(D / 2 - tx, ty)], n_c)
        quad([CE[1], CE[-1], A],
             [foglio(D / 2 - tx, ty), foglio(-(D / 2 - tx), ty), foglio(0.0, s)], n_c)
        for k, n_falda in ((1, nf), (-1, nf * [1, 1, -1])):
            # l'ala: il bordo libero lungo il bordo della falda, uno spessore e
            # mezzo dentro; l'altro lato e' la gamba della V
            g = 1.5 * sp * n_falda
            fuori0, fuori1 = np.array([X, h1, k * D / 2]) - g, np.array([X, H, k * t / 2]) - g
            f_fuori0, f_fuori1 = foglio(k * D / 2, 0), foglio(k * D / 2, s)
            f_ce, f_a = foglio(k * (D / 2 - tx), ty), foglio(0.0, s)
            passi = np.linspace(0.0, 1.0, 7)
            for a, b in zip(passi[:-1], passi[1:]):
                quad([_lerp(fuori0, fuori1, a), _lerp(fuori0, fuori1, b),
                      _lerp(CE[k], A, b), _lerp(CE[k], A, a)],
                     [_lerp(f_fuori0, f_fuori1, a), _lerp(f_fuori0, f_fuori1, b),
                      _lerp(f_ce, f_a, b), _lerp(f_ce, f_a, a)], -n_falda, interno=False)
    return (np.asarray(V, np.float32), np.asarray(UV, np.float32),
            np.asarray(T, np.int64))
