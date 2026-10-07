"""
Il ballotin: la scatola a tronco di piramide rovesciato, piu' larga in cima
che sul fondo, con gli spigoli verticali fatti da LENTI e due coperchi che
chiudono la cima.

Una lente sono due cordonature curve che partono e arrivano negli stessi due
punti: l'angolo del fondo e l'angolo della cima. La corda fra i due capi e' lo
spigolo del tronco, ma vivo solo ai capi: piegata, la lente curva e rientra
nel pack, e lo spigolo e' una gola fra le due facce. Sul ballotin Raffaello
Passion Fruit (fondo 90, cima 115, fianchi da 100) le lenti sono larghe 15 mm
a meta' altezza e magenta piene: sul pack sono le quattro gole degli spigoli.

La fustella, nel verso in cui la si legge:

    T1 | L1 | FRONTE | FONDO | RETRO | L2 | T2

- il FONDO e' un quadrato, e ai suoi quattro angoli partono le quattro lenti;
- FRONTE e RETRO sono i due trapezi della colonna, larghi in cima;
- i FIANCHI pendono dalle lenti del fronte: sono le due ali grandi, con la
  grafica. Dalle lenti del retro pendono invece due alette di colla, che a
  scatola montata stanno dentro i fianchi; le alette ai lati del fondo
  idem. Il fronte e' il trapezio che porta i fianchi;
- i due COPERCHI L1 e L2 chiudono la cima stesi, e ognuno porta la sua
  LINGUETTA (T1, T2). Quello la cui linguetta e' tratteggiata nel disegno
  tecnico sta SOTTO: il tratteggio vuol dire zona coperta. L'altro sta sopra,
  con la linguetta stesa sul primo - sul Raffaello e' il medaglione col
  marchio, che si legge dal fronte;
- in cima ai fianchi ci sono le alette che si chiudono per prime sotto i
  coperchi: si vedono nelle fessure ai lati, perche' i coperchi si
  stringono verso la linguetta;
- le FINESTRE sono le facce chiuse dentro i pannelli, senza tratteggio: quella
  smerlata sul fronte (le praline vere dentro la coppa disegnata) e quella
  che gira lo spigolo fra fronte e coperchio.

La fustella si legge come grafo planare: i tratti delle penne del disegno
tecnico, spezzati dove un tratto arriva su un altro, i rami morti potati, e le
facce percorse una per una. Il tratteggio - famiglie di segmenti paralleli a
pochi millimetri - si toglie prima, e serve dopo: dice quali facce sono coperte.
"""
from __future__ import annotations

import ctypes
import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from scipy.spatial import Delaunay, cKDTree

from . import folding
from .tracciati import _componi, _matrice, _pagina, _stile

PT2MM = 25.4 / 72.0
MM2PT = 72.0 / 25.4

# mm: due capi piu' vicini di cosi' sono lo stesso nodo
NODO = 0.3
# mm: un capo libero cosi' vicino a un altro nodo e' un buco del disegno
BUCO = 2.5
# punti per ogni curva di Bezier
CAMPIONI = 12
# Le lenti: freccia minima di ciascuna delle due curve, e quante ne servono
# per dire ballotin (una per spigolo).
FRECCIA_LENTE = 3.0
LENTI = 4
# Il fondo e' quadrato entro questo scarto relativo sui lati
QUADRO = 0.03
# Il rovescio del cartoncino: la tinta neutra di `folding`, in ombra. Dentro
# una scatola chiusa arriva poca luce, e un viewer senza occlusione ambientale
# dipinge l'interno chiaro come fuori: le finestre sparirebbero nel bianco
# della grafica. L'ombra si cuoce nella tinta.
INTERNO = tuple(int(c * 0.75) for c in folding.INTERNO)
TAGLIO = folding.TAGLIO
# mm sopra il bordo della cima: alette dei fianchi, coperchio di sotto,
# coperchio di sopra. Il cartoncino ha uno spessore, e tre strati stesi uno
# sull'altro non possono stare alla stessa quota.
STRATI = (0.15, 0.6, 1.05)


# --------------------------------------------------------------------------- #
# i tratti
# --------------------------------------------------------------------------- #
def polilinee(pdf, page_no=0, filtro=None):
    """Ogni tratto della pagina come polilinea in mm, telaio di misura (y in
    giu'), con lo stile `(spessore, colore)` di `tracciati._stile`. Le curve
    di Bezier si campionano: un ballotin ha gli spigoli curvi. `filtro`, se
    c'e', dice dallo stile quali tratti leggere: sui fogli grandi la grafica
    ha migliaia di tratti, e leggerli tutti costava secondi."""
    out = []

    def visita(o, t, m):
        if t != raw.FPDF_PAGEOBJ_PATH:
            return
        fill, stroke = ctypes.c_int(), ctypes.c_int()
        raw.FPDFPath_GetDrawMode(o, ctypes.byref(fill), ctypes.byref(stroke))
        if not stroke.value:
            return
        st = _stile(o)
        if filtro is not None and not filtro(st):
            return
        a, b, c, d, e, f = _componi(m, _matrice(o))
        n = raw.FPDFPath_CountSegments(o)
        x, y = ctypes.c_float(), ctypes.c_float()
        segs = []
        for k in range(n):
            s = raw.FPDFPath_GetPathSegment(o, k)
            raw.FPDFPathSegment_GetPoint(s, ctypes.byref(x), ctypes.byref(y))
            px, py = x.value, y.value
            segs.append((raw.FPDFPathSegment_GetType(s),
                         (a * px + c * py + e) * PT2MM,
                         (b * px + d * py + f) * PT2MM,
                         raw.FPDFPathSegment_GetClose(s)))
        cur, inizio, i = [], None, 0
        while i < len(segs):
            tipo, px, py, chiudi = segs[i]
            if tipo == raw.FPDF_SEGMENT_MOVETO:
                if len(cur) > 1:
                    out.append((np.array(cur), st))
                cur = [(px, py)]
                inizio = cur[0]
                i += 1
                continue
            if tipo == raw.FPDF_SEGMENT_BEZIERTO and i + 2 < len(segs) and cur:
                p0 = np.array(cur[-1])
                p1 = np.array((px, py))
                p2 = np.array(segs[i + 1][1:3])
                p3 = np.array(segs[i + 2][1:3])
                for tt in np.linspace(0.0, 1.0, CAMPIONI + 1)[1:]:
                    u = 1.0 - tt
                    cur.append(tuple(u ** 3 * p0 + 3 * u * u * tt * p1
                                     + 3 * u * tt * tt * p2 + tt ** 3 * p3))
                chiudi = segs[i + 2][3]
                i += 3
            else:
                cur.append((px, py))
                i += 1
            if chiudi and inizio is not None:
                cur.append(inizio)
        if len(cur) > 1:
            out.append((np.array(cur), st))

    doc = pdfium.PdfDocument(pdf)
    try:
        _pagina(doc[page_no], visita)
    finally:
        doc.close()
    return out


def tratti_fustella(pdf, page_no=0, linee=None):
    """Le polilinee delle penne della fustella.

    La penna principale la sceglie `strati.penne`, come per ogni altro DT; da
    lei si prende il COLORE, e tutti i tratti di quel colore e di spessore
    vicino sono fustella. Sul Raffaello le finestre sono tagliate con penne da
    0,71 e 0,85 pt, cinque tratti in tutto, e nessuna soglia sul numero di
    segmenti le terrebbe: il colore si'.
    """
    from . import strati
    penne = strati.penne(pdf, page_no)
    if not penne:
        return []
    if linee is None:
        colori = {c for _w, c in penne}
        linee = polilinee(pdf, page_no, lambda st: st[1] in colori)
    peso = defaultdict(float)
    for p, st in linee:
        if st in penne:
            peso[st] += float(np.sum(np.hypot(*np.diff(p, axis=0).T)))
    if not peso:
        return []
    w0, colore = max(peso, key=peso.get)
    return [p for p, (w, c) in linee
            if c == colore and 0.5 * w0 <= w <= 1.5 * w0]


def _freccia(p):
    a, b = p[0], p[-1]
    d = b - a
    l = float(np.hypot(*d))
    if l < 1e-9:
        return 0.0, 0.0
    n = np.array([-d[1], d[0]]) / l
    return float(np.max(np.abs((p - a) @ n))), l


def ha_lenti(tratti, minimo=LENTI):
    """Prefiltro, in pochi millisecondi: almeno `minimo` coppie di curve con
    gli stessi due capi, ciascuna con la sua freccia. Su un astuccio non ce
    n'e' nessuna, e il grafo delle facce non si fa nemmeno."""
    curve = []
    for p in tratti:
        if len(p) < 6:
            continue
        f, l = _freccia(p)
        if f >= FRECCIA_LENTE and l > 20.0:
            curve.append(p)
    coppie = 0
    for i in range(len(curve)):
        a0, a1 = curve[i][0], curve[i][-1]
        for j in range(i + 1, len(curve)):
            b0, b1 = curve[j][0], curve[j][-1]
            if ((np.hypot(*(a0 - b0)) < 2.0 and np.hypot(*(a1 - b1)) < 2.0)
                    or (np.hypot(*(a0 - b1)) < 2.0 and np.hypot(*(a1 - b0)) < 2.0)):
                coppie += 1
    return coppie >= minimo


# --------------------------------------------------------------------------- #
# il grafo planare
# --------------------------------------------------------------------------- #
def tratteggi(tratti, tol_ang=0.8, vicino=7.0, minimo=3):
    """Indici dei segmenti di tratteggio: segmenti dritti con almeno `minimo`
    paralleli a meno di `vicino` mm e sovrapposti nella proiezione. Le
    cordonature allineate in fila - stessa retta - non si contano."""
    idx = [i for i, p in enumerate(tratti) if len(p) == 2]
    if not idx:
        return set()
    P = np.array([tratti[i] for i in idx])          # n x 2 x 2
    d = P[:, 1] - P[:, 0]
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 180.0
    fuori = set()
    for k, i in enumerate(idx):
        a = math.radians(ang[k])
        u = np.array([math.cos(a), math.sin(a)])
        n = np.array([-u[1], u[0]])
        da = np.abs((ang - ang[k] + 90.0) % 180.0 - 90.0)
        sel = np.nonzero(da < tol_ang)[0]
        sel = sel[sel != k]
        if len(sel) < minimo:
            continue
        off = P[sel, 0] @ n - P[k, 0] @ n
        t0 = np.minimum(P[sel, 0] @ u, P[sel, 1] @ u)
        t1 = np.maximum(P[sel, 0] @ u, P[sel, 1] @ u)
        s0, s1 = sorted((P[k, 0] @ u, P[k, 1] @ u))
        ok = ((np.abs(off) > 0.3) & (np.abs(off) < vicino)
              & (t1 >= s0 - 5.0) & (t0 <= s1 + 5.0))
        if int(ok.sum()) >= minimo:
            fuori.add(i)
    return fuori


def _su_segmento(pt, a, b, tol):
    ab = b - a
    l2 = float(ab @ ab)
    if l2 < 1e-12:
        return None
    t = float((pt - a) @ ab) / l2
    if t <= 1e-6 or t >= 1 - 1e-6:
        return None
    if np.hypot(*(pt - (a + t * ab))) <= tol:
        return t
    return None


def grafo(tratti, tol=NODO):
    """(nodi Nx2, archi [(u, v, punti)]): le polilinee spezzate dove un'altra
    arriva sopra di loro - su un vertice o a meta' di un segmento - e i capi
    raggruppati entro `tol`. I doppioni si tolgono."""
    poli = [np.asarray(p, float) for p in tratti if len(p) >= 2]
    capi = np.array([p[0] for p in poli] + [p[-1] for p in poli])
    albero = cKDTree(capi)
    tagli = defaultdict(list)
    for k, p in enumerate(poli):
        lo, hi = p.min(0) - tol, p.max(0) + tol
        centro, raggio = (lo + hi) / 2, float(np.hypot(*(hi - lo))) / 2
        for c in albero.query_ball_point(centro, raggio):
            pt = capi[c]
            if np.any(pt < lo) or np.any(pt > hi):
                continue
            if np.hypot(*(pt - p[0])) <= tol or np.hypot(*(pt - p[-1])) <= tol:
                continue
            dv = np.hypot(*(p[1:-1] - pt).T) if len(p) > 2 else np.array([])
            if len(dv) and dv.min() <= tol:
                j = int(dv.argmin()) + 1
                tagli[k].append((j, 0.0, p[j].copy()))
                continue
            for j in range(len(p) - 1):
                t = _su_segmento(pt, p[j], p[j + 1], tol)
                if t is not None:
                    tagli[k].append((j, t, pt.copy()))
                    break
    pezzi = []
    for k, p in enumerate(poli):
        if k not in tagli:
            pezzi.append(p)
            continue
        cur = [p[0]]
        j_prec = 0
        for j, t, pt in sorted(tagli[k], key=lambda r: (r[0], r[1])):
            for v in range(j_prec + 1, j + 1):
                if t == 0.0 and v == j:
                    break
                cur.append(p[v])
            cur.append(p[j] if t == 0.0 else pt)
            if len(cur) >= 2 and np.hypot(*(cur[-1] - cur[0])) > 1e-9:
                pezzi.append(np.array(cur))
            cur = [cur[-1]]
            j_prec = j
        cur.extend(p[v] for v in range(j_prec + 1, len(p)))
        if len(cur) >= 2:
            pezzi.append(np.array(cur))
    # capi raggruppati per componenti connesse entro tol: un capo a 0,29 mm
    # da due nodi diversi li unisce, non ne sceglie uno a caso
    capi = np.array([p[0] for p in pezzi] + [p[-1] for p in pezzi])
    padre = list(range(len(capi)))

    def radice(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    for i, j in cKDTree(capi).query_pairs(tol):
        a, b = radice(i), radice(j)
        if a != b:
            padre[a] = b
    gruppi = defaultdict(list)
    for i in range(len(capi)):
        gruppi[radice(i)].append(i)
    nodo_di = np.zeros(len(capi), int)
    nodi = []
    for membri in gruppi.values():
        nodo_di[membri] = len(nodi)
        nodi.append(capi[membri].mean(0))
    n = len(pezzi)
    archi, visti = [], defaultdict(list)
    for k, p in enumerate(pezzi):
        u, v = int(nodo_di[k]), int(nodo_di[n + k])
        lung = float(np.sum(np.hypot(*np.diff(p, axis=0).T)))
        if u == v and lung < 4 * tol:
            continue
        p = p.copy()
        p[0], p[-1] = nodi[u], nodi[v]
        # un tratto disegnato due volte confonde il giro delle facce: lo
        # stesso angolo d'uscita, e l'ordine fra i due a caso
        m = p[len(p) // 2] if len(p) > 2 else (p[0] + p[-1]) / 2
        chiave = (min(u, v), max(u, v))
        if any(np.hypot(*(m - q)) <= 4 * tol for q in visti[chiave]):
            continue
        visti[chiave].append(m)
        archi.append((u, v, p))
    return np.array(nodi), archi


def ripara(nodi, archi, raggio=BUCO):
    """Un capo libero a meno di `raggio` mm da un altro nodo si collega a
    quello con un tratto dritto: sul Raffaello la cupola di L2 si ferma a
    1,9 mm dal bordo da una parte sola."""
    grado, vicini = defaultdict(int), defaultdict(set)
    for u, v, _p in archi:
        grado[u] += 1
        grado[v] += 1
        vicini[u].add(v)
        vicini[v].add(u)
    nuovi, fatti = list(archi), set()
    for n in [n for n in range(len(nodi)) if grado[n] == 1]:
        d = np.hypot(*(nodi - nodi[n]).T)
        d[n] = np.inf
        for m in vicini[n]:
            d[m] = np.inf
        m = int(d.argmin())
        if d[m] <= raggio and (min(n, m), max(n, m)) not in fatti:
            fatti.add((min(n, m), max(n, m)))
            nuovi.append((n, m, np.array([nodi[n], nodi[m]])))
    return nuovi


def pota(archi):
    """Via i rami morti - quote, richiami, tratteggi rimasti - finche' ce ne
    sono: un arco con un capo di grado 1 non chiude nessuna faccia."""
    vivi = list(range(len(archi)))
    while True:
        grado = defaultdict(int)
        for e in vivi:
            grado[archi[e][0]] += 1
            grado[archi[e][1]] += 1
        morti = {e for e in vivi
                 if grado[archi[e][0]] == 1 or grado[archi[e][1]] == 1}
        if not morti:
            return [archi[e] for e in vivi]
        vivi = [e for e in vivi if e not in morti]


def _direzione(p):
    for j in range(1, len(p)):
        d = p[j] - p[0]
        l = float(np.hypot(*d))
        if l > 1e-6:
            return d / l
    return np.array([1.0, 0.0])


def area(anello):
    x, y = anello[:, 0], anello[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def dentro(punti, anelli):
    """Pari-dispari su tutti gli anelli: True dove il punto e' dentro."""
    punti = np.atleast_2d(punti)
    ok = np.zeros(len(punti), bool)
    px, py = punti[:, 0:1], punti[:, 1:2]
    for an in anelli:
        x0, y0 = an[:, 0][None], an[:, 1][None]
        x1, y1 = np.roll(an[:, 0], -1)[None], np.roll(an[:, 1], -1)[None]
        dy = np.where(y1 - y0 == 0, 1e-12, y1 - y0)
        c = ((y0 > py) != (y1 > py)) & (px < (x1 - x0) * (py - y0) / dy + x0)
        ok ^= (np.sum(c, axis=1) % 2 == 1)
    return ok


@dataclass
class Faccia:
    anello: np.ndarray                 # mm, telaio di misura
    archi: list                        # [(arco, verso)] del contorno
    buchi: list = field(default_factory=list)   # [Faccia] dentro di lei
    tratteggio: int = 0                # segmenti di tratteggio dentro

    @property
    def area(self):
        return area(self.anello)

    @property
    def centro(self):
        """Il baricentro dell'area: la media dei vertici pende dalla parte
        dove il contorno e' spezzato piu' fitto."""
        x, y = self.anello[:, 0], self.anello[:, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        c = x * y1 - x1 * y
        a = c.sum() / 2.0
        if abs(a) < 1e-9:
            return self.anello.mean(0)
        return np.array([((x + x1) * c).sum(), ((y + y1) * c).sum()]) / (6.0 * a)


def facce(nodi, archi):
    """Le facce del grafo planare, ciascuna col suo contorno.

    Ogni semiarco si percorre una volta; al nodo d'arrivo si prende l'arco
    che viene subito prima, in senso angolare, di quello da cui si arriva:
    tutte le facce escono con lo stesso verso, e la faccia esterna - una per
    ogni pezzo staccato del disegno - col verso opposto.
    """
    uscite = defaultdict(list)
    for e, (u, v, p) in enumerate(archi):
        d0, d1 = _direzione(p), _direzione(p[::-1])
        uscite[u].append((math.atan2(d0[1], d0[0]), e, +1))
        uscite[v].append((math.atan2(d1[1], d1[0]), e, -1))
    for n in uscite:
        uscite[n].sort()
    fatti, out = set(), []
    for e0 in range(len(archi)):
        for s0 in (+1, -1):
            if (e0, s0) in fatti:
                continue
            giro, punti = [], []
            e, s = e0, s0
            while (e, s) not in fatti:
                fatti.add((e, s))
                giro.append((e, s))
                u, v, p = archi[e]
                pp = p if s > 0 else p[::-1]
                punti.extend(pp[:-1])
                arrivo = v if s > 0 else u
                lista = uscite[arrivo]
                k = next(i for i, (_a, ee, ss) in enumerate(lista)
                         if ee == e and ss == -s)
                _a, e, s = lista[(k - 1) % len(lista)]
            out.append(Faccia(np.array(punti), giro))
    return out


def componi(ff, segni=(), principali=None):
    """Le facce vere, coi loro buchi; il fuori se ne va.

    Un anello con l'area negativa e' il contorno di un pezzo staccato del
    disegno. Quello del pezzo principale e' il fuori di tutto; quello di un
    pezzo chiuso dentro una faccia - una finestra chiusa su se stessa,
    un'ellisse di colla - diventa un buco di quella faccia, e le sue facce
    restano. I pezzi che non stanno dentro nessuna faccia del principale - il
    cartiglio, la legenda, le scritte fatte a tratti - se ne vanno.
    `principali` sono gli archi del pezzo principale (vedi `principale`);
    `segni` i punti di mezzo dei tratteggi: ogni faccia sa quanti ne ha.
    """
    def del_principale(f):
        return principali is None or f.archi[0][0] in principali
    pos = [f for f in ff if f.area > 0]
    neg = sorted([f for f in ff if f.area < 0], key=lambda f: f.area)
    tenute = [f for f in pos if del_principale(f)]
    staccati = {}
    fuori = None
    for f in neg:
        if del_principale(f) and fuori is None:
            fuori = f
            continue
        c = f.anello[np.argmin(f.anello[:, 1])] + np.array([0.0, 1e-3])
        cand = [g for g in tenute if g.area > abs(f.area) + 1e-6
                and dentro(c[None], [g.anello])[0]]
        if cand:
            min(cand, key=lambda g: g.area).buchi.append(f)
            for e, _s in f.archi:
                staccati[e] = True
    # le facce dei pezzi staccati che stanno dentro: una finestra smerlata
    # e' un pezzo a se', e la sua faccia serve a dire che e' una finestra
    for f in pos:
        if not del_principale(f) and any(e in staccati for e, _s in f.archi):
            tenute.append(f)
    # i segni si contano a buchi assegnati: il riquadro tratteggiato
    # dell'ink-jet sul fondo e' un buco del fondo, e i suoi segni non fanno
    # del fondo una zona coperta
    if len(segni):
        segni = np.asarray(segni)
        for f in ff:
            f.tratteggio = int(dentro(segni, [f.anello] + [b.anello for b in f.buchi]).sum())
    return tenute


def principale(nodi, archi):
    """Gli indici degli archi del pezzo connesso piu' lungo del disegno."""
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
    peso = defaultdict(float)
    for u, v, p in archi:
        peso[radice(u)] += float(np.sum(np.hypot(*np.diff(p, axis=0).T)))
    if not peso:
        return set()
    r = max(peso, key=peso.get)
    return {e for e, a in enumerate(archi) if radice(a[0]) == r}


# --------------------------------------------------------------------------- #
# il riconoscimento
# --------------------------------------------------------------------------- #
@dataclass
class Ballotin:
    regione: tuple            # (x0, y0, x1, y1) del DT, in punti, telaio di misura
    facce: list               # tutte le Faccia del DT
    fondo: int
    fronte: int
    retro: int
    fianchi: tuple            # (sinistro, destro)
    lenti_fronte: tuple       # (sinistra, destra)
    lenti_retro: tuple
    coperchi: tuple           # (L1 sul fronte, L2 sul retro)
    linguette: tuple          # (T1, T2), None se manca
    alette: tuple             # (sinistra, destra) in cima ai fianchi
    finestre: list            # indici delle facce che sono finestre
    sotto: str                # "fronte" o "retro": il coperchio che sta sotto
    # i punti che servono alla maglia, in mm sul DT
    quadro_fondo: np.ndarray            # 4 angoli: fronte sx, fronte dx, retro dx, retro sx
    apici_fronte: np.ndarray            # (sx, dx) in cima alle lenti del fronte
    apici_retro: np.ndarray
    fianco_dietro: tuple                # ((giu', su) sx, (giu', su) dx)
    cerniera_aletta: tuple              # ((davanti, dietro) sx, (davanti, dietro) dx)
    destra: np.ndarray                  # versore: la destra del fronte sul DT
    su: np.ndarray                      # versore: dal fondo verso la cima del fronte
    fondo_mm: float = 0.0
    cima_mm: float = 0.0
    altezza_mm: float = 0.0
    fianco_mm: float = 0.0
    coperchi_mm: tuple = (0.0, 0.0)
    avvisi: tuple = ()


def _angoli(anello, soglia=35.0):
    """I vertici dove il contorno gira piu' di `soglia` gradi."""
    n = len(anello)
    out = []
    for i in range(n):
        a = anello[i] - anello[i - 1]
        b = anello[(i + 1) % n] - anello[i]
        la, lb = np.hypot(*a), np.hypot(*b)
        if la < 1e-9 or lb < 1e-9:
            continue
        c = float(np.clip((a @ b) / (la * lb), -1, 1))
        if math.degrees(math.acos(c)) > soglia:
            out.append(i)
    return out


def _quadrato(f):
    """I quattro angoli se la faccia e' un quadrato, se no None."""
    an = f.anello
    idx = _angoli(an, 45.0)
    if len(idx) != 4:
        return None
    q = an[idx]
    lati = [float(np.hypot(*(q[(i + 1) % 4] - q[i]))) for i in range(4)]
    m = sum(lati) / 4
    if m < 30.0 or max(abs(l - m) for l in lati) > QUADRO * m:
        return None
    for i in range(4):
        a, b = q[i] - q[i - 1], q[(i + 1) % 4] - q[i]
        c = abs(float(a @ b) / (np.hypot(*a) * np.hypot(*b)))
        if c > 0.05:
            return None
    return q


def _punte(anello, soglia=60.0, raggio=2.0):
    """Le punte del contorno: vertici dove gira piu' di `soglia` gradi, quelli
    a meno di `raggio` mm uniti nel loro punto di mezzo."""
    idx = _angoli(anello, soglia)
    gruppi = []
    for i in idx:
        p = anello[i]
        for g in gruppi:
            if np.hypot(*(np.mean(g, axis=0) - p)) < raggio:
                g.append(p)
                break
        else:
            gruppi.append([p])
    return [np.mean(g, axis=0) for g in gruppi]


def _lente(f):
    """(punta 1, punta 2, freccia) se la faccia e' una lente: due punte sole,
    lontane, e fra loro due curve con la pancia da parti opposte."""
    an = f.anello
    punte = _punte(an)
    if len(punte) != 2:
        return None
    A, B = punte
    d = B - A
    l = float(np.hypot(*d))
    if l < 20.0:
        return None
    n = np.array([-d[1], d[0]]) / l
    s = (an - A) @ n
    t = (an - A) @ (d / l)
    corpo = (t > 0.1 * l) & (t < 0.9 * l)
    if not corpo.any():
        return None
    su, giu = float(s[corpo].max()), float(-s[corpo].min())
    if min(su, giu) < FRECCIA_LENTE or su + giu > 0.4 * l:
        return None
    return A, B, max(su, giu)


def _vicini(ff, archi):
    """Per ogni arco le facce ai suoi due lati, e per ogni faccia le vicine."""
    lato = defaultdict(list)
    for k, f in enumerate(ff):
        for e, _s in f.archi:
            lato[e].append(k)
        for b in f.buchi:
            for e, _s in b.archi:
                lato[e].append(k)
    vic = defaultdict(set)
    for e, ks in lato.items():
        for a in ks:
            for b in ks:
                if a != b:
                    vic[a].add(b)
    return lato, vic


def riconosci(pdf, page_no=0):
    """Il `Ballotin` letto dal disegno tecnico, o None se non e' un ballotin.

    Non indovina: se una delle facce che servono non si trova, il pack non e'
    un ballotin come quelli che conosciamo e si torna None - l'astuccio e gli
    altri provano dopo.
    """
    tratti = tratti_fustella(pdf, page_no)
    if not tratti or not ha_lenti(tratti):
        return None
    tr = tratteggi(tratti)
    segni = [tratti[i].mean(0) for i in tr]
    restano = [p for i, p in enumerate(tratti) if i not in tr]
    nodi, archi = grafo(restano)
    archi = pota(ripara(nodi, archi))
    ff = componi(facce(nodi, archi), segni, principale(nodi, archi))
    return _classifica(ff, archi, page_no)


def _classifica(ff, archi, page_no=0):
    lato, vic = _vicini(ff, archi)
    lenti = {}
    for k, f in enumerate(ff):
        l = _lente(f)
        if l is not None:
            lenti[k] = l
    if len(lenti) < LENTI:
        return None
    # il fondo: il quadrato con una lente a ogni angolo
    fondo = q = None
    for k, f in enumerate(ff):
        qq = _quadrato(f)
        if qq is None:
            continue
        capi = [c for a, b, _f in lenti.values() for c in (a, b)]
        if all(min(np.hypot(*(c - v)) for c in capi) < 1.0 for v in qq):
            fondo, q = k, qq
            break
    if fondo is None:
        return None
    centro = q.mean(0)
    lato_fondo = float(np.mean([np.hypot(*(q[(i + 1) % 4] - q[i])) for i in range(4)]))

    def lente_da(v):
        """La lente che parte dall'angolo v: (indice, apice)."""
        for k, (a, b, _f) in lenti.items():
            if np.hypot(*(a - v)) < 1.0:
                return k, b
            if np.hypot(*(b - v)) < 1.0:
                return k, a
        return None, None

    # i due lati del fondo da cui le lenti partono in fuori sono la colonna
    colonna = []
    for i in range(4):
        v0, v1 = q[i], q[(i + 1) % 4]
        m = (v0 + v1) / 2
        n = m - centro
        n /= np.hypot(*n)
        k0, a0 = lente_da(v0)
        k1, a1 = lente_da(v1)
        if k0 is None or k1 is None or k0 == k1:
            continue
        d0 = (a0 - v0) / np.hypot(*(a0 - v0))
        d1 = (a1 - v1) / np.hypot(*(a1 - v1))
        if d0 @ n > 0.9 and d1 @ n > 0.9:
            colonna.append((i, v0, v1, k0, a0, k1, a1, n))
    if len(colonna) != 2:
        return None

    def trapezio(v0, v1, a0, a1):
        """La faccia fra le due lenti, sopra il lato v0-v1 del fondo."""
        m = (v0 + v1 + a0 + a1) / 4
        best = None
        for k in vic[fondo]:
            if k in lenti:
                continue
            if dentro(m[None], [ff[k].anello])[0]:
                if best is None or ff[k].area < ff[best].area:
                    best = k
        return best

    pannelli = []
    for i, v0, v1, k0, a0, k1, a1, n in colonna:
        t = trapezio(v0, v1, a0, a1)
        if t is None:
            return None
        # oltre ciascuna lente: il fianco (grande, con la grafica) o
        # un'aletta di colla
        ali = []
        for kl in (k0, k1):
            altre = [k for k in vic[kl] if k != t and k != fondo and k not in lenti]
            ali.append(max(altre, key=lambda k: ff[k].area) if altre else None)
        grandi = sum(1 for a in ali if a is not None and ff[a].area > 0.5 * ff[t].area)
        pannelli.append(dict(lato=i, v0=v0, v1=v1, lenti=(k0, k1), apici=(a0, a1),
                             normale=n, faccia=t, ali=ali, grandi=grandi))
    davanti = [p for p in pannelli if p["grandi"] == 2]
    if len(davanti) != 1:
        return None
    F = davanti[0]
    K = [p for p in pannelli if p is not F][0]

    # il verso del fronte: su dal fondo, e la sua destra guardandolo dritto
    su = F["normale"]
    destra = np.array([-su[1], su[0]])
    # angoli del fondo: fronte sx/dx, retro dx/sx
    def ordina(p):
        v0, v1 = p["v0"], p["v1"]
        a0, a1 = p["apici"]
        k0, k1 = p["lenti"]
        if (v1 - v0) @ destra < 0:
            v0, v1, a0, a1, k0, k1 = v1, v0, a1, a0, k1, k0
        return v0, v1, a0, a1, k0, k1
    f_sx, f_dx, af_sx, af_dx, lf_sx, lf_dx = ordina(F)
    r_sx, r_dx, ar_sx, ar_dx, lr_sx, lr_dx = ordina(K)
    ali_f = dict(zip(F["lenti"], F["ali"]))
    fianco_sx, fianco_dx = ali_f[lf_sx], ali_f[lf_dx]

    def apice(k_lente, capo_fondo):
        """La punta della lente lontana dal fondo. Le due curve non sempre
        arrivano nello stesso punto - sul Raffaello quella del fianco si
        ferma 0,9 mm sotto lo spigolo del fronte - e la punta e' il loro
        punto di mezzo."""
        a, b, _f = lenti[k_lente]
        return a if np.hypot(*(a - capo_fondo)) > np.hypot(*(b - capo_fondo)) else b

    af_sx, af_dx = apice(lf_sx, f_sx), apice(lf_dx, f_dx)
    ar_sx, ar_dx = apice(lr_sx, r_sx), apice(lr_dx, r_dx)

    def fianco(k, angolo_fondo, apice_f):
        """(dietro giu', dietro su, cerniera davanti, cerniera dietro) del
        fianco: il fondo del fianco parte dall'angolo del fondo, la cima dalla
        cima della lente; i due capi lontani sono gli angoli dietro."""
        an = ff[k].anello
        ang = an[_angoli(an, 30.0)]
        if len(ang) < 4:
            return None
        lontani = ang[np.argsort(-np.hypot(*(ang - apice_f).T)
                                 - np.hypot(*(ang - angolo_fondo).T))][:2]
        # dei due, quello giu' e' il piu' vicino all'angolo del fondo
        d = np.hypot(*(lontani - angolo_fondo).T)
        giu, su_ = (lontani[0], lontani[1]) if d[0] < d[1] else (lontani[1], lontani[0])
        return giu, su_

    fl = fianco(fianco_sx, f_sx, af_sx)
    fr = fianco(fianco_dx, f_dx, af_dx)
    if fl is None or fr is None:
        return None

    # i coperchi: oltre la cima del fronte e del retro
    def coperchio(p, ap0, ap1, escludi):
        m = (ap0 + ap1) / 2
        n = p["normale"]
        cand = []
        for k in vic[p["faccia"]]:
            if k in escludi or k in lenti:
                continue
            c = ff[k].centro
            if (c - m) @ n > 3.0 and ff[k].tratteggio == 0:
                cand.append(k)
        if not cand:
            return None
        return max(cand, key=lambda k: ff[k].area)

    usate = {fondo, F["faccia"], K["faccia"], fianco_sx, fianco_dx, *lenti}
    L1 = coperchio(F, af_sx, af_dx, usate)
    L2 = coperchio(K, ar_sx, ar_dx, usate)
    if L1 is None or L2 is None:
        return None
    usate |= {L1, L2}

    def linguetta(L, n, base):
        cand = [k for k in vic[L] if k not in usate
                and (ff[k].centro - base) @ n > (ff[L].centro - base) @ n]
        return max(cand, key=lambda k: ff[k].area) if cand else None
    T1 = linguetta(L1, F["normale"], centro)
    T2 = linguetta(L2, K["normale"], centro)
    usate |= {T1, T2} - {None}

    def aletta(k_fianco):
        cand = [k for k in vic[k_fianco] if k not in usate]
        return max(cand, key=lambda k: ff[k].area) if cand else None
    al_sx, al_dx = aletta(fianco_sx), aletta(fianco_dx)
    if al_sx is None or al_dx is None:
        return None

    def cerniera(k_fianco, k_aletta, apice_f):
        """I capi dell'arco (o degli archi) che il fianco ha in comune con la
        sua aletta: davanti quello vicino alla lente."""
        punti = []
        mie = {e for e, _s in ff[k_fianco].archi}
        for e, _s in ff[k_aletta].archi:
            if e in mie:
                punti.extend([archi[e][2][0], archi[e][2][-1]])
        if not punti:
            return None
        punti = np.array(punti)
        d = np.hypot(*(punti - apice_f).T)
        return punti[d.argmin()], punti[d.argmax()]

    cs = cerniera(fianco_sx, al_sx, af_sx)
    cd = cerniera(fianco_dx, al_dx, af_dx)
    if cs is None or cd is None:
        return None

    # le finestre: facce senza tratteggio chiuse fra un pannello e il suo
    # coperchio, o buchi di un pannello
    pannelli_vivi = {F["faccia"], K["faccia"], L1, L2, fianco_sx, fianco_dx}
    finestre = []
    for k, f in enumerate(ff):
        if k in usate or f.tratteggio:
            continue
        if vic[k] and vic[k] <= pannelli_vivi and lato_esterno(k, f, lato) is False:
            finestre.append(k)

    # chi sta sotto: il coperchio con la linguetta tratteggiata
    t1 = ff[T1].tratteggio if T1 is not None else 0
    t2 = ff[T2].tratteggio if T2 is not None else 0
    sotto = "fronte" if t1 > t2 else "retro"

    # le misure
    def altezza(v0, v1, a0, a1):
        u = (v1 - v0) / np.hypot(*(v1 - v0))
        n = np.array([-u[1], u[0]])
        return abs(float(((a0 + a1) / 2 - (v0 + v1) / 2) @ n))
    cima = (float(np.hypot(*(af_dx - af_sx))) + float(np.hypot(*(ar_dx - ar_sx)))) / 2
    fianco_alto = (altezza(f_sx, f_dx, af_sx, af_dx) + altezza(r_sx, r_dx, ar_sx, ar_dx)) / 2
    h = math.sqrt(max(fianco_alto ** 2 - ((cima - lato_fondo) / 2) ** 2, 1.0))

    def profondita(L, base0, base1, n):
        return float(max((ff[L].anello - (base0 + base1) / 2) @ n))

    tutto = np.vstack([f.anello for f in ff])
    lo, hi = tutto.min(0), tutto.max(0)
    return Ballotin(
        regione=tuple(float(v) * MM2PT for v in (lo[0], lo[1], hi[0], hi[1])),
        facce=ff, fondo=fondo, fronte=F["faccia"], retro=K["faccia"],
        fianchi=(fianco_sx, fianco_dx), lenti_fronte=(lf_sx, lf_dx),
        lenti_retro=(lr_sx, lr_dx), coperchi=(L1, L2), linguette=(T1, T2),
        alette=(al_sx, al_dx), finestre=finestre, sotto=sotto,
        quadro_fondo=np.array([f_sx, f_dx, r_dx, r_sx]),
        apici_fronte=np.array([af_sx, af_dx]), apici_retro=np.array([ar_sx, ar_dx]),
        fianco_dietro=(fl, fr), cerniera_aletta=(cs, cd),
        destra=destra, su=su, fondo_mm=lato_fondo, cima_mm=cima, altezza_mm=h,
        fianco_mm=fianco_alto,
        coperchi_mm=(profondita(L1, af_sx, af_dx, F["normale"]),
                     profondita(L2, ar_sx, ar_dx, K["normale"])))


def lato_esterno(k, f, lato):
    """True se la faccia tocca il fuori del disegno: un suo arco ha una
    faccia sola da una parte."""
    for e, _s in f.archi:
        if len(lato[e]) < 2:
            return True
    return False


def dichiara(b):
    """Le righe che la pagina mostra prima di costruire."""
    return ["ballotin: tronco di piramide, fondo %.1f, cima %.1f, alto %.1f mm"
            % (b.fondo_mm, b.cima_mm, b.altezza_mm),
            "spigoli a lente: la lente rientra nel pack fra le due facce",
            "coperchi da %.1f (fronte) e %.1f mm (retro): sotto quello del %s, "
            "la sua linguetta e' tratteggiata" % (b.coperchi_mm[0], b.coperchi_mm[1], b.sotto),
            "finestre: %d" % len(b.finestre)]


# --------------------------------------------------------------------------- #
# la maglia
# --------------------------------------------------------------------------- #
def _infittisci(anello, passo):
    out = []
    n = len(anello)
    for i in range(n):
        a, b = anello[i], anello[(i + 1) % n]
        k = max(1, int(np.ceil(np.hypot(*(b - a)) / passo)))
        for t in np.arange(k) / k:
            out.append(a + t * (b - a))
    return np.array(out)


def _pulisci(anello, tol=1e-3):
    keep = [anello[0]]
    for p in anello[1:]:
        if np.hypot(*(p - keep[-1])) > tol:
            keep.append(p)
    if len(keep) > 2 and np.hypot(*(keep[0] - keep[-1])) <= tol:
        keep.pop()
    return np.array(keep)


def triangola(anelli, bordo=0.8, griglia=4.0, giri=12):
    """(punti Nx2, triangoli Mx3) del poligono: il primo anello e' il
    contorno, gli altri i buchi; il verso non conta.

    Delaunay conforme, con quello che c'e' - scipy, niente librerie in piu':
    il bordo si infittisce, ogni suo lato che la triangolazione non contiene
    si spezza a meta' finche' ci sono tutti, e si tengono i triangoli col
    baricentro dentro.
    """
    anelli = [_pulisci(np.asarray(a, float)) for a in anelli]
    anelli = [a for a in anelli if len(a) >= 3]
    if not anelli:
        return np.zeros((0, 2)), np.zeros((0, 3), int)
    lati, pts = [], []
    for an in anelli:
        d = _infittisci(an, bordo)
        base = len(pts)
        pts.extend(d)
        lati.extend((base + i, base + (i + 1) % len(d)) for i in range(len(d)))
    pts = np.array(pts)
    lo, hi = pts.min(0), pts.max(0)
    xs = np.arange(lo[0] + griglia / 2, hi[0], griglia)
    ys = np.arange(lo[1] + griglia / 2, hi[1], griglia)
    if len(xs) and len(ys):
        g = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
        g = g[dentro(g, anelli)]
        if len(g):
            dist, _ = cKDTree(pts).query(g)
            pts = np.vstack([pts, g[dist > griglia * 0.45]])
    for _ in range(giri):
        tri = Delaunay(pts).simplices
        presenti = set()
        for a, b, c in tri:
            presenti.update(((min(a, b), max(a, b)), (min(b, c), max(b, c)),
                             (min(c, a), max(c, a))))
        mancano = [(u, v) for u, v in lati if (min(u, v), max(u, v)) not in presenti]
        if not mancano:
            break
        nuovi, aggiunti = [], []
        for u, v in mancano:
            k = len(pts) + len(aggiunti)
            aggiunti.append((pts[u] + pts[v]) / 2)
            nuovi += [(u, k), (k, v)]
        via = set(mancano)
        lati = [l for l in lati if l not in via] + nuovi
        pts = np.vstack([pts, np.array(aggiunti)])
    tri = Delaunay(pts).simplices
    tri = tri[dentro(pts[tri].mean(1), anelli)]
    return pts, tri


def _bilineare(src, dst):
    """La mappa che porta il quadrilatero piatto `src` su quello `dst`."""
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)

    def f(p):
        p = np.atleast_2d(p)
        u = np.full(len(p), 0.5)
        v = np.full(len(p), 0.5)
        for _ in range(40):
            P = (((1 - u) * (1 - v))[:, None] * src[0] + (u * (1 - v))[:, None] * src[1]
                 + (u * v)[:, None] * src[2] + ((1 - u) * v)[:, None] * src[3])
            du = (1 - v)[:, None] * (src[1] - src[0]) + v[:, None] * (src[2] - src[3])
            dv = (1 - u)[:, None] * (src[3] - src[0]) + u[:, None] * (src[2] - src[1])
            r = p - P
            det = du[:, 0] * dv[:, 1] - du[:, 1] * dv[:, 0]
            det = np.where(np.abs(det) < 1e-12, 1e-12, det)
            su = (r[:, 0] * dv[:, 1] - r[:, 1] * dv[:, 0]) / det
            sv = (du[:, 0] * r[:, 1] - du[:, 1] * r[:, 0]) / det
            u += su
            v += sv
            if max(np.abs(su).max(), np.abs(sv).max()) < 1e-10:
                break
        return (((1 - u) * (1 - v))[:, None] * dst[0] + (u * (1 - v))[:, None] * dst[1]
                + (u * v)[:, None] * dst[2] + ((1 - u) * v)[:, None] * dst[3])
    return f


# x / sin(x) per l'arco che ha una data lunghezza su una data corda: la
# tabella si inverte con un'interpolazione, e x resta sotto il mezzo giro
_X = np.linspace(1e-4, math.pi * 0.98, 4000)
_R = _X / np.sin(_X)


def _catene(anello, A, B):
    """Le due curve della lente come profili (t, s): t lungo la corda A-B da
    0 a 1, s la distanza con segno dalla corda. Una curva sta da una parte,
    l'altra dall'altra."""
    ch = B - A
    l = float(np.hypot(*ch))
    e = ch / l
    n = np.array([-e[1], e[0]])
    rel = anello - A
    t, s = rel @ e / l, rel @ n
    out = []
    for verso in (+1, -1):
        sel = (s * verso > 1e-9) & (t > 0) & (t < 1)
        tt = np.concatenate([[0.0], t[sel], [1.0]])
        ss = np.concatenate([[0.0], s[sel], [0.0]])
        o = np.argsort(tt, kind="stable")
        out.append((tt[o], ss[o]))
    return e, n, l, out


def _lente_che_rientra(anello, A, B, m_col, m_lat, centro_dt, asse):
    """La mappa di una lente piegata: rientra nel pack fra le due facce.

    Le due curve della lente stanno sulle due facce, ciascuna dove la mette la
    mappa della sua faccia - cosi' i bordi combaciano. In ogni sezione, fra i
    due punti delle curve, la lente fa un arco di cerchio lungo quanto e'
    larga stesa, con la pancia verso l'interno: a meta' altezza, su 15 mm di
    lente e 10,5 di corda, entra di 4,5 mm. Ai due capi la lente non ha
    larghezza, e lo spigolo torna vivo. `asse` e' il versore dello spigolo
    del tronco: la sezione gli sta di traverso.
    """
    e, n, l, ((t1, s1), (t2, s2)) = _catene(anello, A, B)
    # la curva della colonna e' quella dalla parte del centro della colonna
    verso_col = 1.0 if ((centro_dt - (A + B) / 2) @ n) > 0 else -1.0
    if verso_col > 0:
        (tc, sc), (tl, sl) = (t1, s1), (t2, s2)
    else:
        (tc, sc), (tl, sl) = (t2, s2), (t1, s1)
    asse = np.asarray(asse, float) / np.linalg.norm(asse)

    def f(p):
        p = np.atleast_2d(p)
        rel = p - A
        tt = np.clip(rel @ e / l, 0.0, 1.0)
        ss = rel @ n
        s_c = np.interp(tt, tc, sc)
        s_l = np.interp(tt, tl, sl)
        w = s_c - s_l
        u = np.clip(np.where(np.abs(w) > 1e-9, (ss - s_l) / np.where(np.abs(w) > 1e-9, w, 1.0), 0.5), 0.0, 1.0)
        base = A + (tt * l)[:, None] * e
        PC = m_col(base + s_c[:, None] * n)
        PL = m_lat(base + s_l[:, None] * n)
        corda = PC - PL
        c = np.linalg.norm(corda, axis=1)
        ok = c > 1e-6
        ec = corda / np.where(ok, c, 1.0)[:, None]
        M = (PC + PL) / 2
        # verso l'interno: dall'arco all'asse del pack, di traverso allo
        # spigolo e alla corda
        v = np.stack([-M[:, 0], np.zeros(len(M)), -M[:, 2]], 1)
        v -= (v @ asse)[:, None] * asse
        v -= np.sum(v * ec, axis=1)[:, None] * ec
        nv = np.linalg.norm(v, axis=1)
        n_in = v / np.where(nv > 1e-9, nv, 1.0)[:, None]
        r = np.abs(w) / np.where(ok, c, 1.0)
        x = np.interp(np.maximum(r, 1.0), _R, _X)
        R = c / (2.0 * np.sin(x))
        th = -x + 2.0 * x * u
        P = (M + (R * np.sin(th))[:, None] * ec
             + (R * (np.cos(th) - np.cos(x)))[:, None] * n_in)
        return np.where(ok[:, None], P, PL)
    return f


def _trasporta(P0, P1, Q0, Q1, prova, verso):
    """La mappa rigida del DT che porta il segmento P0-P1 su Q0-Q1 (con la
    lunghezza di Q), e manda il punto `prova` dalla parte `verso` di Q0-Q1;
    se la rotazione non ce lo manda, si specchia."""
    P0, P1, Q0, Q1 = (np.asarray(v, float) for v in (P0, P1, Q0, Q1))
    ep, eq = P1 - P0, Q1 - Q0
    k = np.hypot(*eq) / np.hypot(*ep)
    ap, aq = math.atan2(ep[1], ep[0]), math.atan2(eq[1], eq[0])

    def fa(specchio):
        if specchio:
            # specchia sulla retta P0-P1, poi ruota
            u = ep / np.hypot(*ep)
            S = 2.0 * np.outer(u, u) - np.eye(2)
        else:
            S = np.eye(2)
        th = aq - ap
        Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        Mx = k * Rm @ S

        def f(p):
            return (np.atleast_2d(p) - P0) @ Mx.T + Q0
        return f
    dritta = fa(False)
    q = dritta(prova)[0] - Q0
    nq = np.array([-eq[1], eq[0]])
    if (q @ nq) * (np.asarray(verso) - Q0) @ nq < 0:
        return fa(True)
    return dritta


def maglia(b, origine_mm, px_mm, misura_tex, spessore=None):
    """(V, UV, T) del ballotin chiuso, in mm, con la texture del DT intero.

    `origine_mm` e' l'angolo in alto a sinistra della texture sul DT, in mm;
    `px_mm` quanti pixel per mm; `misura_tex` (larghezza, altezza) in pixel
    della texture, che sotto ha una striscia della tinta dell'interno (vedi
    `con_interno`). Il fronte guarda +Z, la cima +Y, il fondo sta a Y = 0.
    """
    sp = folding.SPESSORE_CRT if spessore is None else spessore
    ff = b.facce
    a = b.cima_mm / 2
    c = b.fondo_mm / 2
    H = b.altezza_mm
    FL0, FR0, BR0, BL0 = (np.array(v, float) for v in ((-c, 0, c), (c, 0, c), (c, 0, -c), (-c, 0, -c)))
    FL1, FR1, BR1, BL1 = (np.array(v, float) for v in ((-a, H, a), (a, H, a), (a, H, -a), (-a, H, -a)))
    f_sx, f_dx, r_dx, r_sx = b.quadro_fondo
    af_sx, af_dx = b.apici_fronte
    ar_sx, ar_dx = b.apici_retro
    (fs_giu, fs_su), (fd_giu, fd_su) = b.fianco_dietro

    M_B = _bilineare([f_sx, f_dx, r_dx, r_sx], [FL0, FR0, BR0, BL0])
    M_F = _bilineare([f_sx, f_dx, af_dx, af_sx], [FL0, FR0, FR1, FL1])
    M_K = _bilineare([r_sx, r_dx, ar_dx, ar_sx], [BL0, BR0, BR1, BL1])
    M_WL = _bilineare([f_sx, fs_giu, fs_su, af_sx], [FL0, BL0, BL1, FL1])
    M_WR = _bilineare([f_dx, fd_giu, fd_su, af_dx], [FR0, BR0, BR1, FR1])
    destra = b.destra

    h_alette, h_sotto, h_sopra = STRATI
    centro = (f_sx + f_dx + r_dx + r_sx) / 4
    cima_f = ((af_sx + af_dx) / 2 - centro) @ b.su
    cima_r = ((ar_sx + ar_dx) / 2 - centro) @ (-b.su)

    def coperchio_fronte(h):
        def f(p):
            p = np.atleast_2d(p) - centro
            x = p @ destra
            t = p @ b.su - cima_f
            return np.stack([x, np.full(len(p), H + h), a - t], 1)
        return f

    def coperchio_retro(h):
        def f(p):
            p = np.atleast_2d(p) - centro
            x = p @ destra
            t = p @ (-b.su) - cima_r
            return np.stack([x, np.full(len(p), H + h), -a + t], 1)
        return f

    h1, h2 = (h_sotto, h_sopra) if b.sotto == "retro" else (h_sopra, h_sotto)
    M_L1, M_L2 = coperchio_fronte(h2), coperchio_retro(h1)

    def aletta(cern, verso_x):
        davanti, dietro = cern
        u = (dietro - davanti) / np.hypot(*(dietro - davanti))
        k = 2 * a / float(np.hypot(*(dietro - davanti)))

        def f(p):
            p = np.atleast_2d(p) - davanti
            s = p @ u * k
            t = np.abs(p @ np.array([-u[1], u[0]]))
            return np.stack([verso_x * (a - t), np.full(len(p), H + h_alette), a - s], 1)
        return f
    M_AL = aletta(b.cerniera_aletta[0], -1.0)
    M_AR = aletta(b.cerniera_aletta[1], +1.0)

    pezzi = []   # (anelli, mappa, normale fuori)
    finestre = set(b.finestre)

    def buchi(k):
        return [h.anello for h in ff[k].buchi if h.tratteggio == 0]

    def pezzo(k, mappa, fuori, con_buchi=True):
        if k is None:
            return
        pezzi.append(([ff[k].anello] + (buchi(k) if con_buchi else []), mappa,
                      np.array(fuori, float)))

    pezzo(b.fondo, M_B, (0, -1, 0))
    pezzo(b.fronte, M_F, (0, 0.12, 1))
    pezzo(b.retro, M_K, (0, 0.12, -1))
    pezzo(b.fianchi[0], M_WL, (-1, 0.12, 0))
    pezzo(b.fianchi[1], M_WR, (1, 0.12, 0))
    pezzo(b.coperchi[0], M_L1, (0, 1, 0))
    pezzo(b.coperchi[1], M_L2, (0, 1, 0))
    pezzo(b.linguette[0], M_L1, (0, 1, 0), False)
    pezzo(b.linguette[1], M_L2, (0, 1, 0), False)
    pezzo(b.alette[0], M_AL, (0, 1, 0), False)
    pezzo(b.alette[1], M_AR, (0, 1, 0), False)
    # Le lenti rientrano nel pack: ogni lente e' un pezzo suo, con le due
    # curve dove le mettono le facce accanto. Sul retro la curva dalla parte
    # dell'aletta sta dove sta il bordo dietro del fianco, che e' la stessa
    # curva: si porta sul DT del fianco e si mappa col fianco.
    an_fs, an_fd = ff[b.fianchi[0]].anello, ff[b.fianchi[1]].anello
    centro_fs, centro_fd = ff[b.fianchi[0]].centro, ff[b.fianchi[1]].centro
    T_sx = _trasporta(r_sx, ar_sx, fs_giu, fs_su, r_sx + (r_sx - centro), centro_fs)
    T_dx = _trasporta(r_dx, ar_dx, fd_giu, fd_su, r_dx + (r_dx - centro), centro_fd)

    def via(m, T):
        return lambda p: m(T(p))
    lenti = []
    for k_lente, A, B, m_col, m_lat, asse in (
            (b.lenti_fronte[0], f_sx, af_sx, M_F, M_WL, FL1 - FL0),
            (b.lenti_fronte[1], f_dx, af_dx, M_F, M_WR, FR1 - FR0),
            (b.lenti_retro[0], r_sx, ar_sx, M_K, via(M_WL, T_sx), BL1 - BL0),
            (b.lenti_retro[1], r_dx, ar_dx, M_K, via(M_WR, T_dx), BR1 - BR0)):
        an = ff[k_lente].anello
        lenti.append((an, _lente_che_rientra(an, A, B, m_col, m_lat, centro, asse)))

    Wt, Ht = misura_tex
    uv_interno = np.array([0.5, (Ht - STRISCIA / 2) / Ht])
    V, UV, T = [], [], []
    n_v = 0
    def aggiungi(pts, tri, P3, fuori, normali_vertice=False):
        nonlocal n_v
        uv = (pts - np.asarray(origine_mm)) * px_mm / np.array([Wt, Ht])
        nn = np.cross(P3[tri[:, 1]] - P3[tri[:, 0]], P3[tri[:, 2]] - P3[tri[:, 0]])
        if float(np.sum(nn @ fuori)) < 0:
            tri = tri[:, ::-1]
            nn = -nn
        if normali_vertice:
            # una superficie curva: il rovescio si sposta lungo la normale
            # di ogni vertice, non lungo una sola
            nv = np.zeros_like(P3)
            for j in range(3):
                np.add.at(nv, tri[:, j], nn)
            nv /= np.maximum(np.linalg.norm(nv, axis=1, keepdims=True), 1e-12)
        else:
            nm = nn.sum(0)
            nv = np.tile(nm / np.linalg.norm(nm), (len(P3), 1))
        V.append(P3)
        UV.append(uv)
        T.append(tri + n_v)
        n_v += len(P3)
        # il rovescio: cartoncino, uno spessore piu' in dentro
        V.append(P3 - nv * sp)
        UV.append(np.tile(uv_interno, (len(P3), 1)))
        T.append(tri[:, ::-1] + n_v)
        n_v += len(P3)

    for anelli, mappa, fuori in pezzi:
        pts, tri = triangola(anelli)
        if len(tri):
            aggiungi(pts, tri, mappa(pts), fuori)
    for an, mappa in lenti:
        pts, tri = triangola([an], bordo=0.5, griglia=1.2)
        if len(tri):
            P3 = mappa(pts)
            # fuori: dall'asse del pack verso la lente
            m = P3.mean(0)
            aggiungi(pts, tri, P3, np.array([m[0], 0.0, m[2]]), True)
    return np.vstack(V), np.vstack(UV), np.vstack(T)


# pixel della striscia della tinta dell'interno, sotto la texture del DT
STRISCIA = 24


def con_interno(tex):
    """La texture del DT con sotto la striscia della tinta dell'interno: il
    rovescio prende il colore da li', e il GLB resta a un materiale solo."""
    from PIL import Image
    tela = Image.new("RGB", (tex.width, tex.height + STRISCIA), INTERNO)
    tela.paste(tex.convert("RGB"), (0, 0))
    return tela
