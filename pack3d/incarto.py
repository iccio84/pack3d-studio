"""
L'incarto a triangolo: il foglio di film che avvolge una barretta rigida e
si chiude sulle testate a triangolo (Kinder Maxi, «KM T1 WRAPPING»).

Il DT e' un rettangolo: il passo lungo la barretta, il nastro attorno. Le
linee lunghe, da un taglio all'altro, sono gli spigoli della barretta e
dividono il nastro in cinque fasce:

- in mezzo la **faccia** (quella col marchio), con le testate dritte: la
  barretta finisce li', a `testa_faccia` mm dal taglio di testa;
- ai due lati i **fianchi**, con le testate inclinate: dalla faccia alla
  base la barretta si allunga, e finisce a `testa_base` mm dal taglio. La
  testata della barretta e' quindi un piano inclinato;
- fuori le due fasce del **fondo**, che si sormontano sotto: la linea
  tratteggiata intera dentro una delle due dice di quanto (`sormonto`), e la
  fascia dell'altra sta sopra, col suo taglio a vista. Le testate del fondo
  sono diagonali fino al taglio.

La sezione e' un trapezio: la faccia in cima, il fondo largo quanto
avanza del nastro, i fianchi inclinati.

La testata si chiude cosi' (chiesto a chi ha il pack: guardata di punta,
un triangolo con la punta in basso): il lembo della faccia scende sulla
testata a triangolo, la base sullo spigolo della faccia e la punta a meta'
dello spigolo del fondo, coi lati ripiegati sotto; le alette dei fianchi,
ripiegate prima, coprono i due triangoli ai lati. Il lembo del fondo sta
sotto e non si vede. Ogni pezzo e' il foglio piegato attorno alla sua
piega, senza stirarsi: un punto della testata prende la grafica dal punto
del foglio da cui arriva.

Il film e' sottile (0,1 mm): la barretta si modella con le sue facce e
basta, senza spessore e senza l'interno, che e' chiuso.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .dieline import PT2MM

# mm: un tratto e' dritto se si scosta meno di cosi'; due quote sono la
# stessa se differiscono meno di cosi'
TOLL = 0.35
# mm: le linee lunghe devono attraversare almeno questa parte del passo
LUNGA = 0.95
# mm: una fascia piu' stretta di cosi', contro un taglio, non e' una faccia
# (sul Kinder Maxi la riga a 1 mm dal taglio, dove l'eye-mark non e' stampato)
FASCIA_MIN = 3.0
# mm: le testate della faccia stanno dentro il foglio almeno di tanto
TESTA_MIN = 3.0


@dataclass
class Incarto:
    regione: tuple          # pt, il foglio sulla pagina (x0, y0, x1, y1)
    origine: tuple          # mm, l'angolo del foglio sulla pagina (x, y)
    passo: float            # mm, lungo la barretta
    nastro: float           # mm, attorno
    linee: tuple            # mm dal taglio di sopra: i quattro spigoli
    testa_faccia: float     # mm dal taglio di testa alla piega della faccia
    testa_base: float       # mm alla piega in basso dei fianchi
    sormonto: float         # mm, le due fasce del fondo una sull'altra
    sormonto_letto: bool
    fuori_sopra: bool       # True: sta sopra la fascia del fondo col taglio di sopra
    avvisi: list = field(default_factory=list)

    @property
    def fasce(self):
        y = (0.0,) + tuple(self.linee) + (self.nastro,)
        return [y[i + 1] - y[i] for i in range(5)]

    @property
    def faccia(self):
        return self.fasce[2]

    @property
    def fondo(self):
        f = self.fasce
        return f[0] + f[4] - self.sormonto

    def sezione(self):
        """(d_retro, d_fronte, h): di quanto il fondo sporge dalla faccia dal
        lato del fianco di sopra sul foglio (il retro, dove guarda la testa
        della scritta) e da quello di sotto (il fronte), e l'altezza."""
        f = self.fasce
        s1, s3 = f[1], f[3]
        D = self.fondo - self.faccia
        # stessa altezza dai due fianchi: s1^2 - d1^2 = s3^2 - d3^2, d1 + d3 = D
        if abs(D) < 1e-9:
            d1 = d3 = 0.0
        else:
            d1 = (D * D + s1 * s1 - s3 * s3) / (2.0 * D)
            d3 = D - d1
        h = math.sqrt(max(s1 * s1 - d1 * d1, 1e-6))
        return d1, d3, h


def _segmenti(tratti):
    """I tratti dritti di ogni polilinea, lunghi almeno 1 mm."""
    out = []
    for P in tratti:
        P = np.asarray(P, float)
        for a, b in zip(P[:-1], P[1:]):
            if np.hypot(*(b - a)) >= 1.0:
                out.append((a, b))
    return out


def _orizzontali(segs):
    """(y, x0, x1) dei tratti orizzontali."""
    out = []
    for a, b in segs:
        if abs(b[1] - a[1]) <= TOLL / 2:
            out.append(((a[1] + b[1]) / 2.0, min(a[0], b[0]), max(a[0], b[0])))
    return out


def _unisci(valori):
    """Le quote vicine come una sola."""
    out = []
    for v in sorted(valori):
        if out and v - out[-1][-1] <= TOLL:
            out[-1].append(v)
        else:
            out.append([v])
    return [float(np.mean(g)) for g in out]


def _foglio(segs):
    """(x0, x1, ys): il foglio fra le righe orizzontali che lo attraversano
    tutto, coi due tagli di lato. ys sono le quote delle righe, i tagli di
    sopra e di sotto compresi; None se non c'e'."""
    oriz = [o for o in _orizzontali(segs) if o[2] - o[1] >= 40.0]
    if len(oriz) < 6:
        return None
    best = None
    for _y, x0, x1 in oriz:
        L = x1 - x0
        ys = _unisci([y for y, a, b in oriz
                      if abs(a - x0) <= TOLL and abs(b - x1) <= TOLL])
        # righe spezzate in piu' tratti: conta la copertura
        if len(ys) < 6 or L <= 0:
            continue
        if best is None or (len(ys), L) > (len(best[2]), best[1] - best[0]):
            best = (x0, x1, ys)
    if best is None:
        return None
    x0, x1, ys = best
    # i due tagli di lato: tratti verticali dal primo all'ultimo y
    vert = [(a, b) for a, b in segs if abs(b[0] - a[0]) <= TOLL / 2]

    def lato(x):
        tot = 0.0
        for a, b in vert:
            if abs(a[0] - x) <= TOLL:
                lo, hi = sorted((a[1], b[1]))
                tot += max(0.0, min(hi, ys[-1]) - max(lo, ys[0]))
        return tot >= LUNGA * (ys[-1] - ys[0])

    if not (lato(x0) and lato(x1)):
        return None
    return best


def _testata(segs, ya, yb, x_lim, sinistra):
    """Il tratto che attraversa la fascia fra ya e yb vicino alla testata:
    (x a ya, x a yb), o None. `x_lim` limita la ricerca alla meta' giusta."""
    best = None
    for a, b in segs:
        for p, q in ((a, b), (b, a)):
            if abs(p[1] - ya) <= TOLL and abs(q[1] - yb) <= TOLL:
                if sinistra and max(p[0], q[0]) < x_lim:
                    c = (p[0], q[0])
                elif not sinistra and min(p[0], q[0]) > x_lim:
                    c = (p[0], q[0])
                else:
                    continue
                if best is None or abs(c[0] - c[1]) < abs(best[0] - best[1]):
                    best = c
    return best


def riconosci(pdf, page_no=0):
    """L'incarto letto dal foglio, o None se il DT non e' quello di una
    barretta incartata a triangolo. Su un flowpack esce subito: vuole cinque
    fasce fra righe intere, le testate dritte sulla faccia di mezzo e
    inclinate sui fianchi, simmetriche."""
    from .ballotin import polilinee
    per_stile = {}
    for P, stile in polilinee(pdf, page_no):
        per_stile.setdefault(stile, []).append(P)
    for stile, tratti in sorted(per_stile.items(), key=lambda kv: -len(kv[1])):
        segs = _segmenti(tratti)
        f = _foglio(segs)
        if f is None:
            continue
        p = _leggi(f, segs, per_stile, stile)
        if p is not None:
            return p
    return None


def _leggi(f, segs, per_stile, stile):
    x0, x1, ys = f
    y0, y1 = ys[0], ys[-1]
    passo, nastro = x1 - x0, y1 - y0
    interne = [y for y in ys[1:-1]
               if y - y0 >= FASCIA_MIN and y1 - y >= FASCIA_MIN]
    if len(interne) != 4:
        return None
    lim = [y0] + interne + [y1]
    meta = x0 + passo / 2.0
    # la faccia: la fascia di mezzo, con le testate dritte
    ts = _testata(segs, lim[2], lim[3], meta, True)
    td = _testata(segs, lim[2], lim[3], meta, False)
    if ts is None or td is None:
        return None
    if abs(ts[0] - ts[1]) > TOLL or abs(td[0] - td[1]) > TOLL:
        return None
    tf_s, tf_d = ts[0] - x0, x1 - td[0]
    if tf_s < TESTA_MIN or abs(tf_s - tf_d) > 2 * TOLL:
        return None
    tf = (tf_s + tf_d) / 2.0
    # i fianchi: dalla faccia alla base, verso il taglio
    basi = []
    for ya, yb in ((lim[2], lim[1]), (lim[3], lim[4])):
        s = _testata(segs, ya, yb, meta, True)
        d = _testata(segs, ya, yb, meta, False)
        if s is None or d is None:
            return None
        if abs(s[0] - x0 - tf) > 2 * TOLL or abs(x1 - d[0] - tf) > 2 * TOLL:
            return None
        bs, bd = s[1] - x0, x1 - d[1]
        if bs > tf + TOLL or abs(bs - bd) > 2 * TOLL:
            return None
        basi.append((bs + bd) / 2.0)
    if abs(basi[0] - basi[1]) > 2 * TOLL:
        return None
    tb = sum(basi) / 2.0
    # il fondo: almeno una diagonale dalla base verso il taglio, dentro
    diagonali = 0
    for ya, yb in ((lim[1], lim[0]), (lim[4], lim[5])):
        s = _testata(segs, ya, yb, meta, True)
        if s is not None and abs(s[0] - x0 - tb) <= 2 * TOLL and s[1] - x0 > tb + 1.0:
            diagonali += 1
    if diagonali == 0:
        return None
    linee = tuple(y - y0 for y in interne)
    fasce = [lim[i + 1] - lim[i] for i in range(5)]
    sormonto, letto, fuori_sopra = _sormonto(per_stile, x0, x1, y0, y1, fasce)
    avvisi = []
    if not letto:
        avvisi.append("sormonto del fondo non segnato sul DT: stimato %.1f mm"
                      % sormonto)
    p = Incarto(regione=(x0 / PT2MM, y0 / PT2MM, x1 / PT2MM, y1 / PT2MM),
                origine=(x0, y0), passo=passo, nastro=nastro, linee=linee,
                testa_faccia=tf, testa_base=tb, sormonto=sormonto,
                sormonto_letto=letto, fuori_sopra=fuori_sopra, avvisi=avvisi)
    if p.fondo <= p.faccia * 0.5 or p.fondo >= p.faccia + fasce[1] + fasce[3]:
        return None
    return p


def _sormonto(per_stile, x0, x1, y0, y1, fasce):
    """(mm, letto, fuori_sopra): la riga intera - di qualunque penna - dentro
    una fascia del fondo, la piu' lontana dal suo taglio: li' arriva il
    taglio dell'altra fascia, che sta sopra. Le righe a meno di FASCIA_MIN
    dal taglio sono altro (l'area dell'eye-mark)."""
    cand = []
    for tratti in per_stile.values():
        for y, a, b in _orizzontali(_segmenti(tratti)):
            if a > x0 + TOLL + 1.0 or b < x1 - TOLL - 1.0:
                # anche tratteggiata: i trattini coprono il passo a pezzi
                continue
            cand.append(y)
    # le righe tratteggiate: tanti tratti alla stessa quota
    for tratti in per_stile.values():
        oriz = _orizzontali(_segmenti(tratti))
        quote = {}
        for y, a, b in oriz:
            if a >= x0 - TOLL and b <= x1 + TOLL:
                quote.setdefault(round(y / TOLL), []).append((y, b - a))
        for gruppo in quote.values():
            if len(gruppo) >= 5 and sum(l for _y, l in gruppo) >= 0.3 * (x1 - x0):
                cand.append(float(np.mean([y for y, _l in gruppo])))
    meglio = None
    for y in cand:
        # nella fascia di sotto (dal taglio di sotto) o in quella di sopra
        for d, fascia, fuori_sopra in ((y1 - y, fasce[4], True),
                                       (y - y0, fasce[0], False)):
            if FASCIA_MIN <= d <= fascia - 1.0:
                if meglio is None or d > meglio[0]:
                    meglio = (d, fuori_sopra)
    if meglio is not None:
        return meglio[0], True, meglio[1]
    return 0.8 * min(fasce[0], fasce[4]), False, fasce[0] >= fasce[4]


def dichiara(p):
    d1, d3, h = p.sezione()
    a, B = p.faccia, p.fondo
    lungo_su = p.passo - 2 * p.testa_faccia
    lungo_giu = p.passo - 2 * p.testa_base
    incl = math.degrees(math.atan2(p.testa_faccia - p.testa_base, h))
    return ["incarto a triangolo: il film avvolge una barretta e si chiude "
            "sulle testate",
            "foglio %.1f x %.1f mm (passo x nastro)" % (p.passo, p.nastro),
            "barretta %.1f mm sulla faccia e %.1f alla base, larga %.1f sulla "
            "faccia e %.1f sul fondo, alta %.1f; fianchi %.1f e %.1f mm"
            % (lungo_su, lungo_giu, a, B, h, p.fasce[1], p.fasce[3]),
            "testate inclinate di %.0f gradi, chiuse col lembo della faccia "
            "che scende a triangolo, la punta in basso, e le alette dei "
            "fianchi ai lati" % incl,
            "fondo sormontato di %.1f mm%s" % (
                p.sormonto, "" if p.sormonto_letto else " (stimato)")]


def maglia(p, origine_mm, px_mm, misura_tex):
    """(V, UV, T) della barretta incartata, in mm, con la texture del foglio
    intero. La faccia guarda +Z, la testa della scritta +Y, la barretta corre
    lungo X; il centro della barretta e' l'origine."""
    Wt, Ht = misura_tex
    ox, oy = origine_mm
    fx, fy = p.origine          # l'angolo del foglio, mm sulla pagina
    P, G = p.passo, p.nastro
    l1, l2, l3, l4 = p.linee
    f = p.fasce
    a, B = p.faccia, p.fondo
    d1, d3, h = p.sezione()
    tf, tb = p.testa_faccia, p.testa_base

    def uv(sx, sy):
        """sx, sy: mm sul foglio, dal suo angolo."""
        return ((fx + sx - ox) * px_mm / Wt, (fy + sy - oy) * px_mm / Ht)

    # gli spigoli della sezione (Y, Z)
    BT = np.array([a / 2.0, h / 2.0])           # retro in cima
    FT = np.array([-a / 2.0, h / 2.0])          # fronte in cima
    FB = np.array([-a / 2.0 - d3, -h / 2.0])    # fronte alla base
    BB = np.array([a / 2.0 + d1, -h / 2.0])     # retro alla base
    giu = (BB - FB) / np.linalg.norm(BB - FB)   # lungo il fondo, verso il retro

    def sezione(y):
        """Il punto della sezione per la quota y del foglio (mm dal taglio
        di sopra), e la x di testata (dal taglio di testa) a quella quota."""
        if y <= l1:                     # fondo, la fascia di sopra
            return BB - (l1 - y) * giu, tb
        if y <= l2:                     # retro: dalla base alla faccia
            t = (y - l1) / f[1]
            return BB + t * (BT - BB), tb + t * (tf - tb)
        if y <= l3:                     # la faccia
            t = (y - l2) / f[2]
            return BT + t * (FT - BT), tf
        if y <= l4:                     # fronte: dalla faccia alla base
            t = (y - l3) / f[3]
            return FT + t * (FB - FT), tf + t * (tb - tf)
        return FB + (y - l4) * giu, tb  # fondo, la fascia di sotto

    V, UV, T = [], [], []

    def quad_strip(ys, nx=48):
        """Una fascia del foglio fra le quote ys (crescenti), dalla testata di
        sinistra a quella di destra, coi suoi vertici."""
        base = len(V)
        for y in ys:
            (Y, Z), xt = sezione(y)
            for i in range(nx + 1):
                x = xt + (P - 2 * xt) * i / nx
                V.append((x - P / 2.0, Y, Z))
                UV.append(uv(x, y))
        n = nx + 1
        for j in range(len(ys) - 1):
            for i in range(nx):
                q = base + j * n + i
                T.append((q, q + 1, q + n + 1))
                T.append((q, q + n + 1, q + n))

    # il fondo: della fascia che sta sotto si vede solo il pezzo fuori
    # dall'altra, fino al taglio dell'altra
    if p.fuori_sopra:
        quad_strip([0.0, l1])                       # sopra, col taglio a vista
        quad_strip([l4, l4 + (B - f[0])])           # sotto, il pezzo a vista
    else:
        quad_strip([l1 - (B - f[4]), l1])
        quad_strip([l4, G])
    quad_strip([l1, l2], 8)
    quad_strip([l2, l3], 12)
    quad_strip([l3, l4], 8)

    # le testate
    for sinistra in (True, False):
        s = 1.0 if sinistra else -1.0

        def X(x):
            """x dal taglio di testa di questa testata -> X della barretta."""
            return s * (x - P / 2.0)

        def foglio_x(x):
            return x if sinistra else P - x

        Xt, Xb = X(tf), X(tb)
        p_bt = np.array([Xt, BT[0], BT[1]])
        p_ft = np.array([Xt, FT[0], FT[1]])
        p_fb = np.array([Xb, FB[0], FB[1]])
        p_bb = np.array([Xb, BB[0], BB[1]])
        apice = (p_fb + p_bb) / 2.0
        # il lembo della faccia, piegato sullo spigolo della faccia: giu'
        # lungo la testata, di traverso alla barretta
        lungo = np.array([Xb - Xt, 0.0, -h])
        lungo /= np.linalg.norm(lungo)

        def da_faccia(q):
            fq = float(np.dot(q - p_bt, lungo))         # giu' dallo spigolo
            Y = q[1]
            return uv(foglio_x(tf - fq), l2 + (a / 2.0 - Y))

        def da_fianco(q, c0, c1, s0, s1):
            """Il punto della testata q, sull'aletta del fianco piegata sullo
            spigolo c0-c1 (3D), che sul foglio e' s0-s1."""
            e3 = c1 - c0
            L = np.linalg.norm(e3)
            e3 = e3 / L
            t = float(np.dot(q - c0, e3))
            g = float(np.linalg.norm(q - c0 - t * e3))
            es = (s1 - s0) / np.linalg.norm(s1 - s0)
            # verso fuori dalla barretta: x che cala verso il taglio
            n = np.array([es[1], -es[0]])
            if n[0] > 0:
                n = -n
            pt = s0 + t * es + g * n
            return uv(foglio_x(pt[0]), pt[1])

        tri = [
            # il triangolo del lembo, la punta in basso
            ((p_bt, p_ft, apice), da_faccia),
            # l'aletta del retro
            ((p_bt, apice, p_bb),
             lambda q: da_fianco(q, p_bt, p_bb, np.array([tf, l2]),
                                 np.array([tb, l1]))),
            # l'aletta del fronte
            ((p_ft, p_fb, apice),
             lambda q: da_fianco(q, p_ft, p_fb, np.array([tf, l3]),
                                 np.array([tb, l4]))),
        ]
        for (A, Bv, C), mappa in tri:
            base = len(V)
            for q in (A, Bv, C):
                V.append(tuple(q))
                UV.append(mappa(q))
            T.append((base, base + 1, base + 2))

    V = np.asarray(V, float)
    T = np.asarray(T, np.int64)
    # tutti i triangoli verso fuori: la barretta e' convessa
    c = V.mean(0)
    for k, (i, j, m) in enumerate(T):
        nrm = np.cross(V[j] - V[i], V[m] - V[i])
        if np.dot(nrm, (V[i] + V[j] + V[m]) / 3.0 - c) < 0:
            T[k] = (i, m, j)
    return V, np.asarray(UV, float), T
