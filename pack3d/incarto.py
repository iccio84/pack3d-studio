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

Il modello e' un **monoblocco**, con tutti gli spigoli e gli angoli
arrotondati (chiesto cosi', dopo una versione coi risvolti a strati,
spessi e staccati): i lembi della testata non sono pezzi sopra pezzi ma
la grafica sulla testata piana, ognuno dove si vede - in cima il triangolo
del lembo della faccia, ai lati le alette dei fianchi - e il fondo non ha
il gradino del sormonto.
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
# mm: gli spigoli lunghi della barretta, arrotondati
RAGGIO = 1.5
# mm: gli spigoli delle testate, arrotondati come quelli lunghi: agli angoli
# i due raccordi si incontrano e anche l'angolo e' tondo
RAGGIO_TESTA = 1.5


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


def _interseca(n1, c1, n2, c2):
    """Il punto delle due rette n1.X = c1 e n2.X = c2."""
    A = np.array([n1, n2], float)
    return np.linalg.solve(A, np.array([c1, c2], float))


def maglia(p, origine_mm, px_mm, misura_tex):
    """(V, UV, T) della barretta incartata, in mm, con la texture del foglio
    intero. La faccia guarda +Z, la testa della scritta +Y, la barretta corre
    lungo X; il centro della barretta e' l'origine.

    Un monoblocco: il film gira attorno alla sezione con gli spigoli
    arrotondati (`RAGGIO`), passa sugli spigoli delle testate con un raccordo
    tondo (`RAGGIO_TESTA`) e la testata e' piana. Sulla testata ogni punto
    prende la grafica del lembo che li' sta sopra: in cima il triangolo del
    lembo della faccia, la punta in basso; ai lati le alette rosse dei
    fianchi. Il lembo del fondo, sotto, non si vede. Niente strati, niente
    gradini: la superficie e' una sola e chiusa."""
    Wt, Ht = misura_tex
    fx, fy = p.origine          # l'angolo del foglio, mm sulla pagina
    ox, oy = origine_mm
    P, G = p.passo, p.nastro
    l1, l2, l3, l4 = p.linee
    fa = p.fasce
    a, B = p.faccia, p.fondo
    d1, d3, h = p.sezione()
    tf, tb = p.testa_faccia, p.testa_base
    r = min(RAGGIO, 0.3 * min(fa[1], fa[3], a))
    rt = min(RAGGIO_TESTA, 0.3 * min(fa[1], fa[3], a))

    def uv(sx, sy):
        """sx, sy: mm sul foglio, dal suo angolo in alto a sinistra."""
        return ((fx + sx - ox) * px_mm / Wt, (fy + sy - oy) * px_mm / Ht)

    # la sezione, da un taglio all'altro del fondo: la fascia che sta sopra
    # ha il taglio a vista, dell'altra si vede solo il pezzo fino a li'. I
    # due capi cadono nello stesso punto: la sezione si chiude senza gradino
    BT = np.array([a / 2.0, h / 2.0])           # retro in cima
    FT = np.array([-a / 2.0, h / 2.0])          # fronte in cima
    FB = np.array([-a / 2.0 - d3, -h / 2.0])    # fronte alla base
    BB = np.array([a / 2.0 + d1, -h / 2.0])     # retro alla base
    giu = (BB - FB) / np.linalg.norm(BB - FB)   # lungo il fondo, verso il retro
    if p.fuori_sopra:
        y_ini, y_fin = 0.0, l4 + (B - fa[0])
    else:
        y_ini, y_fin = l1 - (B - fa[4]), G
    pts = [BB - (l1 - y_ini) * giu, BB, BT, FT, FB, FB + (y_fin - l4) * giu]
    yk = [y_ini, l1, l2, l3, l4, y_fin]
    ang = {}
    for k in range(1, 5):
        u_in = pts[k] - pts[k - 1]
        u_in /= np.linalg.norm(u_in)
        u_out = pts[k + 1] - pts[k]
        u_out /= np.linalg.norm(u_out)
        psi = math.acos(max(-1.0, min(1.0, float(np.dot(u_in, u_out)))))
        bis = u_out - u_in
        bis /= np.linalg.norm(bis)
        c = pts[k] + bis * r / math.cos(psi / 2.0)
        t_in = pts[k] - r * math.tan(psi / 2.0) * u_in
        ang[k] = (c, math.atan2(*(t_in - c)[::-1]), psi,
                  r * math.tan(psi / 2.0), r * psi)

    def profilo(y):
        """Il punto della sezione per la quota y del foglio, e la normale."""
        for k in range(1, 5):
            c, a0, psi, _ak, A = ang[k]
            if abs(y - yk[k]) <= A / 2.0:
                t = (y - (yk[k] - A / 2.0)) / A
                q = a0 + t * psi
                n = np.array([math.cos(q), math.sin(q)])
                return c + r * n, n
        i = max(j for j in range(5) if yk[j] <= y + 1e-9)
        i = min(i, 4)
        u = pts[i + 1] - pts[i]
        u /= np.linalg.norm(u)
        a_s, A_s = (ang[i][3], ang[i][4]) if i in ang else (0.0, 0.0)
        a_e, A_e = (ang[i + 1][3], ang[i + 1][4]) if i + 1 in ang else (0.0, 0.0)
        lo, hi = yk[i] + A_s / 2.0, yk[i + 1] - A_e / 2.0
        t = (y - lo) / (hi - lo) if hi > lo else 0.0
        p0, p1 = pts[i] + a_s * u, pts[i + 1] - a_e * u
        return p0 + t * (p1 - p0), np.array([u[1], -u[0]])

    def testata(y):
        """La x della piega di testata alla quota y, dal taglio di testa."""
        if y <= l1:
            return tb
        if y <= l2:
            return tb + (y - l1) / fa[1] * (tf - tb)
        if y <= l3:
            return tf
        if y <= l4:
            return tf + (y - l3) / fa[3] * (tb - tf)
        return tb

    # la testata, in coordinate sue: e di traverso (Y), f giu' lungo la
    # testata dallo spigolo della faccia, w fuori
    Lf = math.hypot(tf - tb, h)
    nb = math.hypot(d1, Lf)
    nf = math.hypot(d3, Lf)
    # le direzioni verso dentro la testata dai suoi quattro lati
    q_banda = [(0.0, -1.0), (-Lf / nb, d1 / nb), (0.0, 1.0), (Lf / nf, d3 / nf),
               (0.0, -1.0)]
    e_apice = (d1 - d3) / 2.0
    lim = [l1, l2, l3, l4]

    def banda_e_peso(y):
        """La fascia della quota y e, sugli spigoli tondi, il peso della
        fascia dopo: (i, j, t)."""
        for k in range(1, 5):
            A = ang[k][4]
            if abs(y - yk[k]) <= A / 2.0 and A > 0:
                return k - 1, k, (y - (yk[k] - A / 2.0)) / A
        i = sum(1 for v in lim if y > v)
        return i, i, 0.0

    def da_foglio_testata(i, e, f_):
        """Il punto della testata (e, f) sul lembo della fascia i: (x dal
        taglio di testa, y) sul foglio. Ogni lembo e' il foglio piegato
        sulla sua piega, senza stirarsi."""
        if i == 2:
            return tf - f_, l2 + (a / 2.0 - e)
        if i in (1, 3):
            if i == 1:
                E0, E1 = np.array([a / 2.0, 0.0]), np.array([a / 2.0 + d1, Lf])
                s0, s1 = np.array([tf, l2]), np.array([tb, l1])
            else:
                E0, E1 = np.array([-a / 2.0, 0.0]), np.array([-a / 2.0 - d3, Lf])
                s0, s1 = np.array([tf, l3]), np.array([tb, l4])
            ed = (E1 - E0) / np.linalg.norm(E1 - E0)
            v = np.array([e, f_]) - E0
            t = float(np.dot(v, ed))
            g = abs(float(ed[0] * v[1] - ed[1] * v[0]))
            es = (s1 - s0) / np.linalg.norm(s1 - s0)
            ns = np.array([es[1], -es[0]])
            if ns[0] > 0:
                ns = -ns
            q = s0 + t * es + g * ns
            return float(q[0]), float(q[1])
        # il fondo: la fascia 0 arriva dal retro (u = B allo spigolo), la 4
        # dal fronte (u = 0). La meta' si prende dalla fascia, non da u: sul
        # taglio u cade fra le due, e per un arrotondamento il raccordo
        # prendeva la grafica dall'altro capo del foglio
        u = e + a / 2.0 + d3
        y = l1 - (B - u) if i == 0 else l4 + u
        return tb - (Lf - f_), y

    # la testata piana, dentro i raccordi: il trapezio rientrato di rt, e su
    # di lui i lembi che si vedono. Le due rette dagli angoli in cima alla
    # punta del lembo della faccia la dividono in tre: in cima il lembo della
    # faccia, ai lati le alette (il lembo del fondo e' sotto, coperto)
    q1, q3 = np.array(q_banda[1]), np.array(q_banda[3])
    E0d, E0s = np.array([a / 2.0, 0.0]), np.array([-a / 2.0, 0.0])
    sopra = ((0.0, 1.0), rt)
    destra = (tuple(q1), float(np.dot(E0d, q1)) + rt)
    sinistra = (tuple(q3), float(np.dot(E0s, q3)) + rt)
    Cad = _interseca(*sopra, *destra)
    Cas = _interseca(*sopra, *sinistra)
    P3 = np.array([e_apice, Lf - rt])

    class Testa:
        """Il telaio di una testata: s = +1 a sinistra, -1 a destra."""

        def __init__(self, s):
            self.s = s
            self.Xt, self.Xb = self.X(tf), self.X(tb)
            self.O = np.array([self.Xt, 0.0, h / 2.0])
            dd = np.array([self.Xb - self.Xt, 0.0, -h])
            self.dd = dd / np.linalg.norm(dd)
            nn = np.array([self.dd[2], 0.0, -self.dd[0]])
            self.nn = nn if s > 0 else -nn
            self.Yh = np.array([0.0, 1.0, 0.0])

        def X(self, x):
            return self.s * (x - P / 2.0)

        def punto(self, e, f_, w=0.0):
            return self.O + e * self.Yh + f_ * self.dd + w * self.nn

        def uv(self, xs, ys_):
            return uv(xs if self.s > 0 else P - xs, ys_)

    teste = [Testa(1.0), Testa(-1.0)]

    def bordo(y):
        """Il bordo della testata piana alla quota y: (e, f) del punto F da
        cui parte il raccordo, la direzione verso dentro q, la fascia."""
        p0, _n = profilo(y)
        xt = testata(y)
        i, j, t = banda_e_peso(y)
        q = np.array(q_banda[i]) * (1 - t) + np.array(q_banda[j]) * t
        q /= np.linalg.norm(q)
        te = teste[0]
        E = np.array([te.X(xt), p0[0], p0[1]])
        e, f_ = float(p0[0]), float(np.dot(E - te.O, te.dd))
        return np.array([e + rt * q[0], f_ + rt * q[1]]), q, (i if t < 0.5 else j)

    # le quote dei vertici attorno alla sezione: pochi sulle facce piane,
    # fitti sugli spigoli tondi
    quote = set(np.linspace(y_ini, y_fin, 25))
    for k in range(1, 5):
        A = ang[k][4]
        quote.update(np.linspace(yk[k] - A / 2.0, yk[k] + A / 2.0, 9))
    quote = sorted(q for q in quote if y_ini - 1e-9 <= q <= y_fin + 1e-9)

    # sul bordo della testata, i tre punti dove i lembi si incontrano: dove
    # le rette dagli angoli in cima alla punta lo tagliano, e la punta. Ci va
    # una quota sua, cosi' raccordo e testata hanno li' lo stesso vertice
    def lato(F, A0, A1):
        d = A1 - A0
        return d[0] * (F[1] - A0[1]) - d[1] * (F[0] - A0[0])

    def taglia(g, ya, yb):
        ga = g(ya)
        for _ in range(60):
            ym = (ya + yb) / 2.0
            gm = g(ym)
            if (gm > 0) == (ga > 0):
                ya, ga = ym, gm
            else:
                yb = ym
        return (ya + yb) / 2.0

    def cerca(g, dove):
        for ya, yb in zip(quote[:-1], quote[1:]):
            if dove(ya, yb) and (g(ya) > 0) != (g(yb) > 0):
                return taglia(g, ya, yb)
        raise ValueError("incarto: il bordo della testata non incontra un lembo")

    sul_fondo = lambda ya, yb: yb <= l1 or ya >= l4
    y_d = cerca(lambda y: lato(bordo(y)[0], Cad, P3), lambda ya, yb: l1 <= ya and yb <= l3)
    y_s = cerca(lambda y: lato(bordo(y)[0], Cas, P3), lambda ya, yb: l2 <= ya and yb <= l4)
    y_p = cerca(lambda y: bordo(y)[0][0] - e_apice, sul_fondo)
    quote = sorted(set(quote) | {y_d, y_s, y_p})
    # a meta' di ogni spigolo tondo il raccordo passa da un lembo all'altro:
    # li' la riga e' doppia, coi due lembi, e fra le due non c'e' niente. Con
    # una riga sola i triangoli fra un lembo e l'altro prendevano la grafica
    # da due punti lontani del foglio, e sull'angolo arrivava un pezzo del
    # bianco della faccia («c'e' un buco bianco sul lato»)
    voci = []
    for y in quote:
        cambio = [k for k in range(1, 5) if abs(y - yk[k]) < 1e-9]
        if cambio:
            voci += [(y, cambio[0] - 1), (y, cambio[0])]
        else:
            voci.append((y, bordo(y)[2]))

    V, UV, T = [], [], []

    def nuovo(q, t_uv):
        V.append(tuple(float(c) for c in q))
        UV.append(t_uv)
        return len(V) - 1

    def hermite(p0, m0, p1, m1, t):
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0
                + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1)

    NPIEGA = 8
    NCORPO = 30

    # il corpo e i raccordi delle testate: una griglia sola, una riga per
    # quota; il raccordo va dal bordo della testata piana (F) al corpo
    righe = []
    giro = []                   # (e, f) del bordo della testata, quota per quota
    al_giro = {}                # la quota -> il suo posto nel giro
    for y, banda in voci:
        p0, _n = profilo(y)
        xt = testata(y)
        (eF, fF), q, _b = bordo(y)
        if y not in al_giro:
            al_giro[y] = len(giro)
            giro.append((eF, fF))
        riga = []
        lati = []
        for te in teste:
            F = te.punto(eF, fF)
            Bc = np.array([te.X(xt + rt), p0[0], p0[1]])
            k = 1.5 * rt
            m0 = -(q[0] * te.Yh + q[1] * te.dd) * k
            m1 = np.array([te.s, 0.0, 0.0]) * k
            sF = da_foglio_testata(banda, eF, fF)
            sB = (xt + rt, y)
            piega = []
            for n in range(NPIEGA + 1):
                tt = n / NPIEGA
                piega.append((hermite(F, m0, Bc, m1, tt),
                              te.uv(sF[0] + tt * (sB[0] - sF[0]),
                                    sF[1] + tt * (sB[1] - sF[1]))))
            lati.append(piega)
        sinistra_, destra_ = lati
        riga.extend(sinistra_)
        for n in range(1, NCORPO):
            x = xt + rt + (P - 2 * (xt + rt)) * n / NCORPO
            riga.append((np.array([x - P / 2.0, p0[0], p0[1]]), uv(x, y)))
        riga.extend(destra_[::-1])
        righe.append([nuovo(qv, tv) for qv, tv in riga])
    for k in range(len(righe) - 1):
        if voci[k][0] == voci[k + 1][0]:
            continue                    # la riga doppia: la cucitura dei lembi
        r0, r1 = righe[k], righe[k + 1]
        for c in range(len(r0) - 1):
            T.append((r0[c], r0[c + 1], r1[c + 1]))
            T.append((r0[c], r1[c + 1], r1[c]))
    n_corpo = len(T)

    # la testata piana: tre zone, ognuna col suo pezzo di bordo (gli stessi
    # punti F del raccordo: nessuna fessura) e chiusa dalle rette fino alla
    # punta; a ventaglio dal suo centro, con la grafica del lembo della zona.
    # Il primo e l'ultimo punto del giro sono lo stesso (il taglio del fondo)
    giro = giro[:-1]
    i_d, i_s, i_p = (al_giro[y] for y in (y_d, y_s, y_p))

    def arco(da, a_):
        """I punti del giro da `da` ad `a_` compresi, andando avanti."""
        n = len(giro)
        k, out = da, [giro[da]]
        while k != a_:
            k = (k + 1) % n
            out.append(giro[k])
        return out

    zone = [(2, arco(i_d, i_s)),            # in cima, il lembo della faccia
            (1, arco(i_p, i_d)),            # l'aletta del fianco col retro
            (3, arco(i_s, i_p))]            # l'aletta del fianco col fronte
    ventagli = []               # (primo, ultimo triangolo, testata)
    for te in teste:
        for banda, poli in zone:
            if banda == 2:
                poli = poli + [giro[i_p]]
            cen = np.mean(np.asarray(poli, float), axis=0)
            ids = [nuovo(te.punto(*q), te.uv(*da_foglio_testata(banda, *q)))
                   for q in [cen] + list(poli)]
            primo = len(T)
            for m in range(len(poli)):
                T.append((ids[0], ids[1 + m], ids[1 + (m + 1) % len(poli)]))
            ventagli.append((primo, len(T), te))

    V = np.asarray(V, float)
    T = np.asarray(T, np.int64)

    def normale(k):
        i, j, m = T[k]
        return np.cross(V[j] - V[i], V[m] - V[i])

    # le facce verso fuori, a blocchi interi: la griglia del corpo e ogni
    # ventaglio hanno il giro dei triangoli coerente, e si girano tutti
    # insieme. Il riferimento: il triangolo piu' grande della faccia in
    # cima (+Z) per il corpo, la normale della testata per i ventagli
    cima = max(range(n_corpo), key=lambda k: (V[T[k]][:, 2].min(), np.linalg.norm(normale(k))))
    if normale(cima)[2] < 0:
        T[:n_corpo] = T[:n_corpo][:, [0, 2, 1]]
    for primo, ultimo, te in ventagli:
        k = max(range(primo, ultimo), key=lambda k: np.linalg.norm(normale(k)))
        if np.dot(normale(k), te.nn) < 0:
            T[primo:ultimo] = T[primo:ultimo][:, [0, 2, 1]]
    return V, np.asarray(UV, float), T
