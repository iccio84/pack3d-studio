"""
La scatola a prisma: un fondo poligonale - esagono, ottagono, pentagono - con
una parete dritta su ogni lato, e il coperchio fatto allo stesso modo, che
calza sopra il fondo. Ogni pezzo e' un PDF suo.

Lo steso di un pezzo:

          parete
        /--------\\
  parete|  piano  |parete      (un lato per parete, quante sono i lati)
        \\--------/
          parete

con le linguette agli spigoli fra una parete e l'altra, e sul coperchio, oltre
le pareti, i risvolti che rientrano. Il piano e' la faccia piu' grande della
fustella; i suoi spigoli sono quelli dell'inviluppo convesso (una tacca nel
contorno non e' uno spigolo), e su ogni lato deve esserci una faccia, la
parete, attaccata lungo tutto il lato: l'altezza della parete e' quanto quella
faccia si allunga in fuori, misurata sulla perpendicolare al lato. Quattro
lati sono l'astuccio e il vassoio, che hanno i loro moduli: qui si arriva
dopo, coi lati da cinque in su.

Montata, ogni parete si alza di 90 gradi sul suo lato. Linguette e risvolti
stanno dentro e non si vedono: il modello non li porta. Il fondo sta a Y = 0
con le pareti in su; il coperchio, se c'e', sta capovolto sopra, col piano a
filo delle pareti del fondo piu' lo spessore e le sue pareti in giu'. Dei due
pezzi il coperchio e' quello col piano piu' largo: calza fuori.

Il verso: il piano del coperchio si guarda dall'alto, e lo steso cosi' com'e'
sul foglio e' la vista dall'alto col fronte in basso. Il fondo si guarda da
sotto, e la sua stampa si gira sui lati del coperchio; fra le posizioni che
combaciano, il fronte del fondo e' la parete piu' in basso sul foglio, come
quella del coperchio. Vedi REGOLE.md, *La scatola a prisma*.

La texture di ogni pezzo e' il suo DT intero, come per il ballotin.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import ballotin as B
from . import folding

PT2MM = B.PT2MM
MM2PT = B.MM2PT

LATI_MIN = 5          # quattro lati sono l'astuccio o il vassoio
LATI_MAX = 12
LATO_MIN = 15.0       # mm: un lato del piano piu' corto non e' un lato
PARETE_MIN = 5.0      # mm: una parete piu' bassa non e' una parete
GIRO_MIN = 12.0       # gradi: uno spigolo del piano gira almeno di tanto
PIENO = 0.93          # il piano riempie quasi tutto il suo inviluppo
PASSO = 0.2           # mm, il passo con cui si misura una parete
DOPPIO = 0.8          # un secondo disegno lungo almeno cosi' e' l'altra vista
DPI_DETTAGLIO = 30.0


@dataclass
class Prisma:
    regione: tuple            # (x0, y0, x1, y1) del DT, in punti
    piano: np.ndarray         # (N, 2) mm sul foglio, gli spigoli del piano
    pareti: list              # mm, l'altezza della parete su ogni lato
    normali: np.ndarray       # (N, 2) verso fuori di ogni lato, sul foglio
    centro: np.ndarray = field(default=None)

    @property
    def lati(self):
        return len(self.piano)

    @property
    def apotema(self):
        """La distanza media dal centro ai lati, mm."""
        return float(np.mean([(self.piano[i] - self.centro) @ self.normali[i]
                              for i in range(self.lati)]))

    @property
    def altezza(self):
        return float(np.median(self.pareti))

    @property
    def larghezza(self):
        """Ingombro sul foglio, mm (x, y)."""
        return tuple(float(v) for v in np.ptp(self.piano, axis=0))


def _facce(pdf, page_no=0):
    tratti = B.tratti_fustella(pdf, page_no)
    if not tratti:
        return None, None
    tr = B.tratteggi(tratti)
    segni = [tratti[i].mean(0) for i in tr]
    restano = [p for i, p in enumerate(tratti) if i not in tr]
    nodi, archi = B.grafo(restano)
    archi = B.pota(B.ripara(nodi, archi))
    tutte = B.facce(nodi, archi)
    pezzi = _pezzi_del_disegno(nodi, archi)
    if not pezzi:
        return None, None
    # due disegni lunghi uguali sono la vista di fuori e quella di dentro:
    # si tiene quello con la grafica (`_dettaglio`)
    lunghi = [p for p, lung in pezzi if lung >= DOPPIO * pezzi[0][1]]
    scelte = [B.componi(tutte, segni, p) for p in lunghi]
    if len(scelte) > 1:
        d = [_dettaglio(pdf, page_no, ff) for ff in scelte]
        return scelte[int(np.argmax(d))], archi
    return scelte[0], archi


def _pezzi_del_disegno(nodi, archi):
    """`[(archi, lunghezza)]` dei pezzi connessi del disegno, dal piu' lungo."""
    padre = list(range(len(nodi)))

    def radice(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    for u, v, _p in archi:
        a, b = radice(u), radice(v)
        if a != b:
            padre[a] = b
    peso, quali = {}, {}
    for e, (u, v, p) in enumerate(archi):
        r = radice(u)
        peso[r] = peso.get(r, 0.0) + float(np.sum(np.hypot(*np.diff(p, axis=0).T)))
        quali.setdefault(r, set()).add(e)
    return sorted(((quali[r], peso[r]) for r in peso), key=lambda x: -x[1])


def _dettaglio(pdf, page_no, ff):
    """Quanta grafica c'e' sotto un disegno: la media del gradiente della
    pagina, a bassa risoluzione, nel suo ingombro. La vista di dentro e' un
    fondo pieno o sfumato; quella di fuori ha scritte, marchi, codici."""
    if not ff:
        return 0.0
    import pypdfium2 as pdfium
    tutto = np.vstack([f.anello for f in ff])
    lo, hi = tutto.min(0), tutto.max(0)
    s = DPI_DETTAGLIO / 25.4
    doc = pdfium.PdfDocument(pdf)
    try:
        im = doc[page_no].render(scale=DPI_DETTAGLIO / 72.0).to_pil()
    finally:
        doc.close()
    g = np.asarray(im.convert("L"), float)
    x0, y0 = max(0, int(lo[0] * s)), max(0, int(lo[1] * s))
    x1, y1 = min(g.shape[1], int(hi[0] * s)), min(g.shape[0], int(hi[1] * s))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return 0.0
    q = g[y0:y1, x0:x1]
    return float(np.abs(np.diff(q, axis=0)).mean() + np.abs(np.diff(q, axis=1)).mean())


def _spigoli(anello):
    """Gli spigoli del piano: l'inviluppo convesso, senza i vertici dove il
    contorno quasi non gira."""
    from scipy.spatial import ConvexHull
    h = anello[ConvexHull(anello).vertices]
    cambiato = True
    while cambiato and len(h) > 3:
        cambiato = False
        for i in range(len(h)):
            a = h[i] - h[i - 1]
            b = h[(i + 1) % len(h)] - h[i]
            la, lb = np.hypot(*a), np.hypot(*b)
            giro = 0.0 if la < 1e-6 or lb < 1e-6 else math.degrees(
                math.acos(float(np.clip(a @ b / (la * lb), -1, 1))))
            if giro < GIRO_MIN:
                h = np.delete(h, i, axis=0)
                cambiato = True
                break
    return h


def _dentro(p, anello):
    return bool(B.dentro(np.asarray(p, float)[None], [anello])[0])


def _parete(ff, k_piano, a, b, n):
    """Quanto si allunga in fuori la faccia attaccata al lato a-b, o None.

    Si parte da tre punti del lato, appena fuori, e si va lungo la normale
    finche' si resta nella stessa faccia; la mediana delle tre misure."""
    misure = []
    for s in (0.3, 0.5, 0.7):
        q = a + (b - a) * s
        p0 = q + n * 0.6
        k = next((k for k, f in enumerate(ff) if k != k_piano
                  and _dentro(p0, f.anello)), None)
        if k is None:
            return None
        anello = ff[k].anello
        d = 0.6
        while d < 400.0 and _dentro(q + n * (d + PASSO), anello):
            d += PASSO
        lo, hi = d, d + PASSO
        for _ in range(8):
            m = (lo + hi) / 2.0
            if _dentro(q + n * m, anello):
                lo = m
            else:
                hi = m
        misure.append(lo)
    # una parete e' attaccata lungo tutto il lato: anche vicino agli spigoli
    for s in (0.12, 0.88):
        p0 = a + (b - a) * s + n * 0.6
        if not any(k != k_piano and _dentro(p0, f.anello)
                   for k, f in enumerate(ff)):
            return None
    return float(np.median(misure))


def riconosci(pdf, page_no=0):
    """Il `Prisma` letto dalla fustella, o None se il pezzo non e' un fondo
    poligonale con le pareti."""
    ff, _archi = _facce(pdf, page_no)
    if not ff:
        return None
    k = max(range(len(ff)), key=lambda i: ff[i].area)
    anello = ff[k].anello
    h = _spigoli(anello)
    n = len(h)
    if not LATI_MIN <= n <= LATI_MAX:
        return None
    if B.area(anello) < PIENO * abs(B.area(h)):
        return None
    lati = np.roll(h, -1, axis=0) - h
    if np.min(np.hypot(lati[:, 0], lati[:, 1])) < LATO_MIN:
        return None
    centro = ff[k].centro
    normali = []
    for i in range(n):
        e = lati[i] / np.hypot(*lati[i])
        m = np.array([e[1], -e[0]])
        if m @ ((h[i] + h[(i + 1) % n]) / 2.0 - centro) < 0:
            m = -m
        normali.append(m)
    normali = np.array(normali)
    pareti = []
    for i in range(n):
        p = _parete(ff, k, h[i], h[(i + 1) % n], normali[i])
        if p is None or p < PARETE_MIN:
            return None
        pareti.append(p)
    tutto = np.vstack([f.anello for f in ff])
    lo, hi = tutto.min(0), tutto.max(0)
    return Prisma(regione=tuple(float(v) * MM2PT
                                for v in (lo[0], lo[1], hi[0], hi[1])),
                  piano=h, pareti=pareti, normali=normali, centro=centro)


def pezzi(prismi):
    """`(fondo, coperchio)` fra i pezzi letti: il coperchio e' quello col
    piano piu' largo, e calza sopra il fondo solo se ha gli stessi lati. Un
    pezzo solo e' il fondo, aperto. None se i pezzi non stanno insieme."""
    if len(prismi) == 1:
        return prismi[0], None
    if len(prismi) != 2:
        return None
    a, b = sorted(prismi, key=lambda p: p.apotema)
    if a.lati != b.lati or b.apotema < a.apotema - 0.5:
        return None
    return a, b


def dichiara(fondo, coperchio=None):
    righe = ["scatola a prisma con %d lati: fondo largo %.1f x %.1f mm, "
             "pareti alte %.1f" % ((fondo.lati,) + fondo.larghezza
                                   + (fondo.altezza,))]
    if coperchio is not None:
        righe.append("coperchio a calzare: largo %.1f x %.1f mm, pareti alte "
                     "%.1f" % (coperchio.larghezza + (coperchio.altezza,)))
    else:
        righe.append("SENZA COPERCHIO: il fondo esce aperto - per chiuderlo "
                     "carica insieme il PDF del coperchio")
    return righe


def _angolo(v):
    return math.atan2(v[1], v[0])


def _ruota(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s], [s, c]])


def assetti(fondo, coperchio=None):
    """Le matrici 2x2 dal foglio (x, y) al piano (X, Z) del modello, per il
    fondo e per il coperchio. Il coperchio si guarda dall'alto col fronte in
    basso sul foglio: (X, Z) = (x, y). Il fondo da sotto, quindi specchiato,
    e girato perche' i suoi lati stiano sotto quelli del coperchio e il suo
    fronte sia la parete piu' in basso sul foglio."""
    M_cop = np.eye(2)
    S = np.diag([1.0, -1.0])
    nf = fondo.normali @ S.T
    giu = int(np.argmax(fondo.normali[:, 1]))       # la parete piu' in basso
    # gira la parete in basso verso +Z
    t0 = _angolo((0.0, 1.0)) - _angolo(nf[giu])
    if coperchio is None:
        return _ruota(t0) @ S, None
    # fra le rotazioni che portano i lati del fondo su quelli del coperchio,
    # la piu' vicina a t0
    nc = coperchio.normali
    candidati = []
    for i in range(len(nf)):
        t = _angolo(nc[0]) - _angolo(nf[i])
        R = _ruota(t)
        err = max(min(math.acos(float(np.clip((R @ v) @ w, -1, 1)))
                      for w in nc) for v in nf)
        if err < math.radians(8.0):
            d = abs((t - t0 + math.pi) % (2 * math.pi) - math.pi)
            candidati.append((d, t))
    t = min(candidati)[1] if candidati else t0
    return _ruota(t) @ S, M_cop


def maglia(pr, M, origine_mm, px_mm, misura_tex, coperchio=False, quota=0.0,
           spessore=None):
    """(V, UV, T) di un pezzo, in mm, con la texture del suo DT intero e
    sotto le strisce del rovescio (`ballotin.con_interno`). `M` porta il
    foglio sul piano (X, Z) (`assetti`); il fondo ha il piano a Y = `quota`
    e le pareti in su, il coperchio il piano a Y = `quota` e le pareti in
    giu'."""
    from .ballotin import STRISCIA
    sp = folding.SPESSORE_CRT if spessore is None else spessore
    Wt, Ht = misura_tex
    uv_interno = (0.5, (Ht - 1.5 * STRISCIA) / Ht)
    taglio_uv = (0.5, (Ht - 0.5 * STRISCIA) / Ht)
    ox, oy = origine_mm
    c = pr.centro
    verso = -1.0 if coperchio else 1.0          # le pareti, in su o in giu'

    def uv(q):
        return ((q[0] - ox) * px_mm / Wt, (q[1] - oy) * px_mm / Ht)

    def p3(q, d=0.0):
        """Il punto del foglio `q`, sul piano, alzato di `d` lungo la parete."""
        X, Z = M @ (np.asarray(q, float) - c)
        return np.array([X, quota + verso * d, Z])

    V, UV, T = [], [], []

    def faccia(P3, U, fuori, tri, interno=True):
        P3 = np.asarray(P3, float)
        n = np.cross(P3[tri[0][1]] - P3[tri[0][0]], P3[tri[0][2]] - P3[tri[0][0]])
        if float(n @ fuori) < 0:
            tri = [(i, k, j) for i, j, k in tri]
        fuori = np.asarray(fuori, float) / np.linalg.norm(fuori)
        b = len(V)
        V.extend(P3.tolist())
        UV.extend(U)
        T.extend([(b + i, b + j, b + k) for i, j, k in tri])
        if interno:
            b = len(V)
            V.extend((P3 - fuori * sp).tolist())
            UV.extend([uv_interno] * len(P3))
            T.extend([(b + i, b + k, b + j) for i, j, k in tri])

    N = pr.lati
    # il piano: a ventaglio dal centro (e' convesso)
    P = [c] + list(pr.piano)
    tri = [(0, 1 + i, 1 + (i + 1) % N) for i in range(N)]
    faccia([p3(q) for q in P], [uv(q) for q in P], (0.0, -verso, 0.0), tri)
    # le pareti, e la costa sul bordo libero
    for i in range(N):
        a, b = pr.piano[i], pr.piano[(i + 1) % N]
        h, n = pr.pareti[i], pr.normali[i]
        fuori = np.append(M @ n, 0.0)[[0, 2, 1]]
        S2 = [a, b, b + n * h, a + n * h]
        P3 = [p3(a), p3(b), p3(b, h), p3(a, h)]
        faccia(P3, [uv(q) for q in S2], fuori, [(0, 1, 2), (0, 2, 3)])
        A, Bb = P3[3], P3[2]
        faccia([A, Bb, Bb - fuori * sp, A - fuori * sp], [taglio_uv] * 4,
               (0.0, verso, 0.0), [(0, 1, 2), (0, 2, 3)], interno=False)
    return (np.asarray(V, np.float32), np.asarray(UV, np.float32),
            np.asarray(T, np.int64))
