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
# mm: gli spigoli lunghi della barretta, arrotondati
RAGGIO = 1.0
# mm: la piega del film sugli spigoli delle testate
RAGGIO_TESTA = 0.8
# mm: lo spessore di un risvolto sulla testata. Il film ne ha 0,1: cosi'
# sottile il bordo di lembo e alette non si vedeva, e la testata sembrava
# dipinta («fai i risvolti piu' a vista, staccati, spessi»)
STRATO = 0.3
# mm: di quanto la punta del lembo della faccia si stacca dalla testata
STACCO = 0.7


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
    lungo X; il centro della barretta e' l'origine.

    Il film gira attorno alla sezione con gli spigoli arrotondati (`RAGGIO`),
    passa sugli spigoli delle testate con una piega tonda (`RAGGIO_TESTA`) e
    finisce sulla testata in tre strati: sotto il lembo del fondo, sopra le
    alette dei fianchi, in cima il triangolo del lembo della faccia, che si
    stacca verso la punta (`STACCO`). Ogni strato ha il suo spessore a vista
    (`STRATO`)."""
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
    rt = RAGGIO_TESTA
    T1, T2, W0 = STRATO, 2.0 * STRATO, 0.05

    def uv(sx, sy):
        """sx, sy: mm sul foglio, dal suo angolo in alto a sinistra."""
        return ((fx + sx - ox) * px_mm / Wt, (fy + sy - oy) * px_mm / Ht)

    # la sezione, da un taglio all'altro del fondo: la fascia che sta sopra
    # ha il taglio a vista, dell'altra si vede solo il pezzo fino a li'
    BT = np.array([a / 2.0, h / 2.0])           # retro in cima
    FT = np.array([-a / 2.0, h / 2.0])          # fronte in cima
    FB = np.array([-a / 2.0 - d3, -h / 2.0])    # fronte alla base
    BB = np.array([a / 2.0 + d1, -h / 2.0])     # retro alla base
    giu = (BB - FB) / np.linalg.norm(BB - FB)   # lungo il fondo, verso il retro
    if p.fuori_sopra:
        y_ini, y_fin = 0.0, l4 + (B - fa[0])
        bordo, verso_bordo = y_ini, 1.0
    else:
        y_ini, y_fin = l1 - (B - fa[4]), G
        bordo, verso_bordo = y_fin, -1.0
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

    def rialzo(y):
        """Il sormonto: la fascia di sopra sta sull'altra, uno strato su."""
        d = (y - bordo) * verso_bordo
        if d <= p.sormonto:
            return T1
        return T1 * max(0.0, 1.0 - (d - p.sormonto) / 1.0)

    # le quote dei vertici attorno alla sezione: pochi sulle facce piane,
    # fitti sugli spigoli tondi e dove il sormonto scende
    quote = set(np.linspace(y_ini, y_fin, 25))
    for k in range(1, 5):
        A = ang[k][4]
        quote.update(np.linspace(yk[k] - A / 2.0, yk[k] + A / 2.0, 7))
    for d in (p.sormonto, p.sormonto + 0.5, p.sormonto + 1.0):
        quote.add(bordo + verso_bordo * d)
    quote = sorted(q for q in quote if y_ini - 1e-9 <= q <= y_fin + 1e-9)

    # la testata, in coordinate sue: e di traverso (Y), f giu' lungo la
    # testata dallo spigolo della faccia, w fuori
    Lf = math.hypot(tf - tb, h)
    nb = math.hypot(d1, Lf)
    nf = math.hypot(d3, Lf)
    q_banda = [(0.0, -1.0), (-Lf / nb, d1 / nb), (0.0, 1.0), (Lf / nf, d3 / nf),
               (0.0, -1.0)]
    w_banda = [W0, T1, T2, T1, W0]
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
        u = e + a / 2.0 + d3
        if p.fuori_sopra:
            y = l1 - (B - u) if u >= B - fa[0] else l4 + u
        else:
            y = l4 + u if u <= fa[4] else l1 - (B - u)
        return tb - (Lf - f_), y

    V, UV, T = [], [], []

    def nuovo(q, t_uv):
        V.append(tuple(float(c) for c in q))
        UV.append(t_uv)
        return len(V) - 1

    def hermite(p0, m0, p1, m1, t):
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0
                + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1)

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

        def punto(self, e, f_, w):
            return self.O + e * self.Yh + f_ * self.dd + w * self.nn

        def uv(self, xs, ys_):
            return uv(xs if self.s > 0 else P - xs, ys_)

    teste = [Testa(1.0), Testa(-1.0)]
    NPIEGA = 6
    NCORPO = 30

    # il corpo e le pieghe di testata: una griglia sola, una riga per quota
    righe = []
    for y in quote:
        p2, n2 = profilo(y)
        p2 = p2 + rialzo(y) * n2
        xt = testata(y)
        i, j, t = banda_e_peso(y)
        q = np.array(q_banda[i]) * (1 - t) + np.array(q_banda[j]) * t
        q /= np.linalg.norm(q)
        w = w_banda[i] * (1 - t) + w_banda[j] * t
        banda = i if t < 0.5 else j
        riga = []
        lati = []
        for te in teste:
            E = np.array([te.X(xt), p2[0], p2[1]])
            e, f_ = float(p2[0]), float(np.dot(E - te.O, te.dd))
            eF, fF = e + rt * q[0], f_ + rt * q[1]
            F = te.punto(eF, fF, w)
            Bc = np.array([te.X(xt + rt), p2[0], p2[1]])
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
        sinistra, destra = lati
        riga.extend(sinistra)
        for n in range(1, NCORPO):
            x = xt + rt + (P - 2 * (xt + rt)) * n / NCORPO
            riga.append((np.array([x - P / 2.0, p2[0], p2[1]]), uv(x, y)))
        riga.extend(destra[::-1])
        righe.append([nuovo(qv, tv) for qv, tv in riga])
    for r0, r1 in zip(righe[:-1], righe[1:]):
        for c in range(len(r0) - 1):
            T.append((r0[c], r0[c + 1], r1[c + 1]))
            T.append((r0[c], r1[c + 1], r1[c]))
    # il taglio della fascia di sopra: il gradino dello strato
    r0, r1 = (righe[-1], righe[0]) if p.fuori_sopra else (righe[0], righe[-1])
    for c in range(len(r0) - 1):
        T.append((r0[c], r0[c + 1], r1[c + 1]))
        T.append((r0[c], r1[c + 1], r1[c]))
    n_corpo = len(T)

    # i lembi sulle testate
    da_girare = []      # (triangolo, punto di riferimento dentro)
    for te in teste:
        def tri(pa, pb, pc, banda, w, ref):
            """Un triangolo piatto del lembo della fascia `banda`, a w."""
            ids = [nuovo(te.punto(e, f_, w),
                         te.uv(*da_foglio_testata(banda, e, f_)))
                   for e, f_ in (pa, pb, pc)]
            da_girare.append((len(T), ref))
            T.append(tuple(ids))

        def bordo_a_vista(pa, pb, w_su, w_giu, banda, n=6):
            """Lo spessore di un lembo lungo il suo bordo libero."""
            prima = None
            for k in range(n + 1):
                t = k / n
                e = pa[0] + t * (pb[0] - pa[0])
                f_ = pa[1] + t * (pb[1] - pa[1])
                st = te.uv(*da_foglio_testata(banda, e, f_))
                su = nuovo(te.punto(e, f_, w_su(e, f_)), st)
                giu_ = nuovo(te.punto(e, f_, w_giu), st)
                if prima is not None:
                    for tr in ((prima[0], su, giu_), (prima[0], giu_, prima[1])):
                        da_girare.append((len(T), ("bordo", pa, pb, te)))
                        T.append(tr)
                prima = (su, giu_)

        # sotto: il lembo del fondo, su tutta la testata (si vede nelle fessure)
        base = [(-a / 2.0 + rt, rt), (a / 2.0 - rt, rt),
                (a / 2.0 + d1 - rt, Lf - rt), (-a / 2.0 - d3 + rt, Lf - rt)]
        tri(base[0], base[1], base[2], 4, W0 * 0.5, "fuori")
        tri(base[0], base[2], base[3], 4, W0 * 0.5, "fuori")
        # le alette dei fianchi
        for banda, E0, E1 in ((1, (a / 2.0, 0.0), (a / 2.0 + d1, Lf)),
                              (3, (-a / 2.0, 0.0), (-a / 2.0 - d3, Lf))):
            qb = q_banda[banda]
            P1 = (E0[0] + rt * qb[0], E0[1] + rt * qb[1])
            # sulla piega spostata, alla quota della piega del fondo
            tt = ((Lf - rt) - P1[1]) / (E1[1] - E0[1])
            P2 = (P1[0] + tt * (E1[0] - E0[0]), Lf - rt)
            P3 = (e_apice, Lf - rt)
            tri(P1, P2, P3, banda, T1, "fuori")
            bordo_a_vista(P2, P3, lambda e, f_: T1, W0 * 0.5, banda)

        # in cima il lembo della faccia, a triangolo con la punta in basso,
        # che si stacca verso la punta
        def w_lembo(e, f_):
            t = max(0.0, (f_ - rt) / (Lf - rt))
            return T2 + STACCO * t * t

        Q1, Q2, Q3 = (-a / 2.0, rt), (a / 2.0, rt), (e_apice, Lf - 0.3 * rt)
        NU, NV = 6, 8
        griglia = []
        for jv in range(NV + 1):
            v = jv / NV
            riga = []
            for iu in range(NU + 1):
                u = iu / NU
                e = (1 - v) * (Q1[0] + u * (Q2[0] - Q1[0])) + v * Q3[0]
                f_ = (1 - v) * (Q1[1] + u * (Q2[1] - Q1[1])) + v * Q3[1]
                riga.append(nuovo(te.punto(e, f_, w_lembo(e, f_)),
                                  te.uv(*da_foglio_testata(2, e, f_))))
            griglia.append(riga)
        for jv in range(NV):
            for iu in range(NU):
                a0, a1 = griglia[jv][iu], griglia[jv][iu + 1]
                b0, b1 = griglia[jv + 1][iu], griglia[jv + 1][iu + 1]
                for tr in ((a0, a1, b1), (a0, b1, b0)):
                    da_girare.append((len(T), "fuori"))
                    T.append(tr)
        bordo_a_vista(Q1, Q3, w_lembo, T1, 2, n=NV)
        bordo_a_vista(Q2, Q3, w_lembo, T1, 2, n=NV)

    V = np.asarray(V, float)
    T = np.asarray(T, np.int64)
    # il corpo verso fuori: la barretta e' convessa
    c = V.mean(0)
    for k in range(n_corpo):
        i, j, m = T[k]
        nrm = np.cross(V[j] - V[i], V[m] - V[i])
        if np.dot(nrm, (V[i] + V[j] + V[m]) / 3.0 - c) < 0:
            T[k] = (i, m, j)
    # i lembi: verso fuori dalla testata; i bordi: verso fuori dal lembo
    for k, ref in da_girare:
        i, j, m = T[k]
        nrm = np.cross(V[j] - V[i], V[m] - V[i])
        cen = (V[i] + V[j] + V[m]) / 3.0
        if ref == "fuori":
            te = teste[0] if cen[0] < 0 else teste[1]
            dentro = np.dot(nrm, te.nn) < 0
        else:
            _tag, pa, pb, te = ref
            # fuori dal bordo: dalla parte opposta al centro della testata
            mid = te.punto((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, 0.0)
            ctr = te.punto(0.0, Lf / 2.0, 0.0)
            dentro = np.dot(nrm, mid - ctr) < 0
        if dentro:
            T[k] = (i, m, j)
    return V, np.asarray(UV, float), T
