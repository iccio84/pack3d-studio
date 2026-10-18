"""
Il tubo a cono: uno sleeve di cartoncino arrotolato in un cono lungo e
stretto, aperto in cima, col fondo schiacciato e saldato piatto - il tubo di
un gelato da spremere. Un pezzo solo, cartotecnico.

Lo steso e' un settore di corona circolare: l'arco grande e' la bocca, in
cima; l'arco piccolo e' il fondo; i due lati dritti, che puntano al centro
dei due archi, si sovrappongono della pattina e fanno la cucitura, sul
retro. Montato:

- in cima il tubo e' tondo, con la circonferenza dell'arco grande meno la
  pattina;
- la bocca e' rimboccata in fuori (`RISVOLTO`): da fuori, sotto il bordo,
  si vede una fascia bianca, il rovescio del cartoncino;
- sul fondo la fascia che il DT lascia fuori dalla stampa massima, a
  tratteggio, e' quella che si deforma: in basso un terzo e' la saldatura,
  schiacciata piatta, le due pareti una contro l'altra, rigata dalle ganasce
  e con gli angoli tagliati; sopra il tubo torna tondo, e alla stampa massima
  lo e' gia'.

Il fronte e' il mezzo della parte che si vede, fra la pattina e l'altro lato.
La texture e' il DT intero, come per la scatola a punta: ogni punto della
maglia prende la grafica dal suo posto sul foglio.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from . import dieline as dl
from . import folding

PT2MM = dl.PT2MM

# la firma in fustella
LATO_MIN = 80.0         # mm: un lato dritto piu' corto non fa un tubo
SLANCIO_MIN = 1.2       # lato / diametro della bocca: piu' tozzo e' una coppa
CONCENTRICI = 3.0       # mm fra i centri dei due archi
RADIALE_GRADI = 3.0     # un lato punta al centro degli archi entro tanti gradi
GIRO_MIN = 20.0         # mm: l'arco del fondo, almeno
CHIUDE = 6.0            # mm fra i capi dei lati e i capi degli archi
FRECCIA_MIN = 0.8       # mm: un arco si distingue da una retta
# la pattina, se il DT non la scrive ("pattina 8 mm")
PATTINA = 8.0
PARALLELO = math.radians(1.5)
# la saldatura, se il DT non disegna la stampa massima: una parte del lato
SALDATURA = 0.12
# della fascia fuori dalla stampa massima, la parte saldata piatta (il resto
# torna tondo)
PIATTA = 1.0 / 3.0
# gli angoli tagliati della saldatura: il lato del triangolo, in parte
# dell'altezza della saldatura
SMUSSO = 0.6
# le righe delle ganasce sulla saldatura: passo e profondita', mm
RIGHE_PASSO = 1.2
RIGHE_FONDE = 0.15
# la bocca rimboccata in fuori: la fascia bianca che si vede, mm
RISVOLTO = 6.0
PASSI_GIRO = 72
PASSI_ALTO = 60


@dataclass
class Tubo:
    regione: tuple          # pt, il DT sulla pagina
    centro: tuple           # mm sul foglio, il centro dei due archi
    R_bocca: float          # mm, il raggio dell'arco grande
    R_fondo: float          # mm, il raggio dell'arco piccolo
    a_sin: float            # rad, l'angolo del lato sinistro (0 = verso la bocca)
    a_des: float            # rad, l'angolo del lato destro
    pattina: float          # mm
    pattina_a_sinistra: bool
    saldatura: float        # mm lungo il lato, dal fondo
    pattina_letta: bool = False
    saldatura_letta: bool = False

    @property
    def lato(self):
        return self.R_bocca - self.R_fondo

    def giro(self, rho):
        """La circonferenza del tubo all'altezza dell'arco di raggio rho."""
        return rho * (self.a_des - self.a_sin) - self.pattina

    @property
    def k(self):
        return (self.a_des - self.a_sin) / (2.0 * math.pi)

    @property
    def altezza(self):
        return self.lato * math.sqrt(max(0.0, 1.0 - self.k ** 2))

    @property
    def d_bocca(self):
        return self.giro(self.R_bocca) / math.pi

    @property
    def d_fondo(self):
        return self.giro(self.R_fondo) / math.pi


def _cerchio(P):
    """Centro e raggio del cerchio che passa meglio per i punti (Kasa)."""
    P = np.asarray(P, float)
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    r = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
    return np.array([cx, cy]), r


def _freccia(P):
    P = np.asarray(P, float)
    a, b = P[0], P[-1]
    d = b - a
    n = np.linalg.norm(d)
    if n < 1e-9:
        return 0.0
    return float(np.abs(np.cross(d, P - a)).max() / n)


def _lunghezza(P):
    return float(np.linalg.norm(np.diff(np.asarray(P, float), axis=0), axis=1).sum())


def _dist_retta(c, a, b):
    d = b - a
    return float(abs(np.cross(d, c - a)) / (np.linalg.norm(d) or 1.0))


def _firma(tratti):
    """Il settore di corona fra tratti dello stesso stile, o None:
    (centro, R_bocca, R_fondo, [lato_a, lato_b], stima del mezzo).

    Gli archi danno il centro; i lati sono rette lunghe che puntano al centro
    (entro RADIALE_GRADI: il lato della pattina e' scostato e parallelo) coi
    capi sui due archi. Se i contorni sono due, uno dentro l'altro - il taglio
    e l'abbondanza di stampa, nella stessa penna - il taglio e' quello
    dentro, la coppia di lati piu' stretta. Gli archi possono essere spezzati
    in piu' tratti: conta che ce ne sia uno ai due raggi."""
    archi, rette, curve = [], [], []
    for P in tratti:
        P = np.asarray(P, float)
        L = _lunghezza(P)
        if len(P) >= 5 and L >= 5.0:
            curve.append(P)
        if len(P) >= 5 and L >= 5.0 and _freccia(P) >= FRECCIA_MIN:
            archi.append(P)
        elif len(P) == 2 and L >= LATO_MIN:
            rette.append(P)
    if not archi or len(rette) < 2 or len(archi) > 40 or len(rette) > 60:
        return None
    best = None
    centri = []
    for A in sorted(archi, key=_lunghezza, reverse=True)[:6]:
        c, _ = _cerchio(A)
        if any(np.linalg.norm(c - q) <= CONCENTRICI for q in centri):
            continue
        centri.append(c)
        lati = []
        for R in rette:
            q = (R[0] + R[1]) / 2.0 - c
            d = R[1] - R[0]
            seno = abs(float(np.cross(d, q))) / (np.linalg.norm(d) * np.linalg.norm(q) or 1.0)
            if seno > math.sin(math.radians(RADIALE_GRADI)):
                continue
            rr = sorted(float(np.linalg.norm(p - c)) for p in R)
            a = math.atan2(q[1], q[0])
            lati.append((a, rr[0], rr[1], R))
        if len(lati) < 2:
            continue
        a_rif = lati[0][0]

        def rel(a):
            return (a - a_rif + math.pi) % (2 * math.pi) - math.pi

        for i in range(len(lati)):
            for j in range(len(lati)):
                ai, aj = rel(lati[i][0]), rel(lati[j][0])
                if aj <= ai:
                    continue
                Rp = (lati[i][1] + lati[j][1]) / 2.0
                Rg = (lati[i][2] + lati[j][2]) / 2.0
                if (abs(lati[i][1] - lati[j][1]) > CHIUDE
                        or abs(lati[i][2] - lati[j][2]) > CHIUDE):
                    continue
                if Rg - Rp < LATO_MIN:
                    continue
                # un arco al raggio della bocca e uno al raggio del fondo
                ok = 0
                for R in (Rg, Rp):
                    if any(np.median(np.abs(np.linalg.norm(A2 - c, axis=1) - R)) <= CHIUDE / 2
                           for A2 in curve):
                        ok += 1
                if ok < 2:
                    continue
                span = aj - ai
                if Rp * span < GIRO_MIN:
                    continue        # due lati dello stesso fianco
                if best is None or span < best[0] - 1e-6:
                    best = (span, c, Rg, Rp, [lati[i][3], lati[j][3]],
                            a_rif + (ai + aj) / 2.0)
    if best is None:
        return None
    return best[1:]


def _ang(c, q):
    """L'angolo del punto q visto dal centro: 0 dritto verso la bocca, che
    sul foglio puo' stare in qualunque verso; si misura poi dal mezzo."""
    d = np.asarray(q, float) - c
    return math.atan2(d[1], d[0])


def riconosci(pdf, page_no=0):
    """Il tubo letto dal foglio, o None se la fustella non e' un settore di
    corona lungo e stretto."""
    from .ballotin import polilinee
    per_stile = {}
    for P, stile in polilinee(pdf, page_no):
        per_stile.setdefault(stile, []).append(P)
    trovato = None
    for stile, tratti in per_stile.items():
        f = _firma(tratti)
        if f is not None and (trovato is None or f[1] > trovato[0][1]):
            trovato = (f, stile)
    if trovato is None:
        return None
    (c, Rg, Rp, lati, a_m), stile = trovato
    lato = Rg - Rp

    def rel(q):
        a = _ang(c, q) - a_m
        return (a + math.pi) % (2 * math.pi) - math.pi

    angoli = sorted(np.mean([rel(q) for q in R]) for R in lati)
    # "destra" sul foglio guardando dal centro verso la bocca: la bocca e' in
    # cima al pack, e la grafica si legge col fondo in basso
    a_sin, a_des = angoli[0], angoli[1]
    giro_bocca = Rg * (a_des - a_sin)
    if giro_bocca <= 0 or lato < SLANCIO_MIN * giro_bocca / math.pi:
        return None
    # il verso: col centro sotto la bocca, sinistra e destra del foglio sono
    # quelle del pack. Con gli angoli dell'immagine (y in giu') l'angolo
    # cresce in senso orario, cioe' verso destra guardando la bocca.
    pattina, letta = _pattina_scritta(pdf, page_no)
    sin_dentro, sal = _stampa_massima(per_stile, stile, c, Rp, Rg, a_m,
                                      a_sin, a_des)
    saldatura = sal if sal is not None else SALDATURA * lato
    # il DT: il settore, con la freccia della bocca
    aa = np.linspace(a_sin + a_m, a_des + a_m, 64)
    tutti = np.vstack([np.c_[c[0] + R * np.cos(aa), c[1] + R * np.sin(aa)]
                       for R in (Rg, Rp)])
    x0, y0 = tutti.min(0) / PT2MM
    x1, y1 = tutti.max(0) / PT2MM
    return Tubo(regione=(x0, y0, x1, y1), centro=(float(c[0]), float(c[1])),
                R_bocca=float(Rg), R_fondo=float(Rp),
                a_sin=float(a_sin + a_m), a_des=float(a_des + a_m),
                pattina=pattina,
                pattina_a_sinistra=sin_dentro if sin_dentro is not None else True,
                saldatura=float(saldatura), pattina_letta=letta,
                saldatura_letta=sal is not None)


def _pattina_scritta(pdf, page_no):
    """La pattina dal cartiglio ("Pattina 8 mm"), se c'e'."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        testo = doc[page_no].get_textpage().get_text_range()
    except Exception:
        return PATTINA, False
    m = re.search(r"pattina\s*(\d+(?:[.,]\d+)?)\s*mm", testo, re.I)
    if not m:
        return PATTINA, False
    v = float(m.group(1).replace(",", "."))
    return (v, True) if 2.0 <= v <= 20.0 else (PATTINA, False)


def _stampa_massima(per_stile, stile_dt, c, Rp, Rg, a_m, a_sin, a_des):
    """Le linee della stampa massima: rette di un altro stile, parallele a un
    lato e dentro il settore. Dicono da che parte e' la pattina (la linea
    piu' lontana dal suo lato) e dove comincia la saldatura (dove finiscono,
    verso il fondo). (pattina a sinistra?, saldatura in mm) o None."""
    lato = Rg - Rp
    dir_lato = {}
    for nome, a in (("sin", a_sin), ("des", a_des)):
        dir_lato[nome] = a + a_m
    distanze = {"sin": [], "des": []}
    fondo = []
    for stile, tratti in per_stile.items():
        if stile == stile_dt:
            continue
        for P in tratti:
            P = np.asarray(P, float)
            if len(P) != 2 or _lunghezza(P) < 0.5 * lato:
                continue
            d = P[1] - P[0]
            ang = math.atan2(d[1], d[0])
            for nome, a in dir_lato.items():
                u = np.array([math.cos(a), math.sin(a)])
                diff = abs((ang - a + math.pi / 2) % math.pi - math.pi / 2)
                if diff > PARALLELO:
                    continue
                q = (P[0] + P[1]) / 2.0 - c
                rho = float(np.linalg.norm(q))
                if not (Rp < rho < Rg):
                    continue
                aq = math.atan2(q[1], q[0]) - a_m
                aq = (aq + math.pi) % (2 * math.pi) - math.pi
                if not (a_sin < aq < a_des):
                    continue
                # distanza dalla retta del lato (che passa per il centro)
                dist = abs(float(np.cross(u, q)))
                if dist > 0.25 * rho * (a_des - a_sin):
                    continue
                distanze[nome].append(dist)
                fondo.append(min(float(np.dot(p - c, u)) for p in P))
    sin = min(distanze["sin"]) if distanze["sin"] else None
    des = min(distanze["des"]) if distanze["des"] else None
    lato_pattina = None
    if sin is not None and des is not None and abs(sin - des) > 2.0:
        lato_pattina = sin > des
    sal = None
    if fondo:
        s = min(fondo) - Rp
        if 3.0 <= s <= 0.3 * lato:
            sal = s
    return lato_pattina, sal


def dichiara(p):
    """Le righe che la pagina mostra prima di costruire."""
    alto = p.altezza - RISVOLTO * math.sqrt(max(0.0, 1.0 - p.k ** 2))
    righe = ["tubo a cono: alto %.1f mm, bocca %.1f mm, fondo %.1f mm di "
             "diametro" % (alto, p.giro(p.R_bocca - RISVOLTO) / math.pi,
                           p.d_fondo),
             "steso a settore di corona: lati da %.1f mm, archi da %.1f e "
             "%.1f mm" % (p.lato, p.R_bocca * (p.a_des - p.a_sin),
                           p.R_fondo * (p.a_des - p.a_sin)),
             "pattina da %.1f mm sul lato %s del foglio, sul retro%s"
             % (p.pattina, "sinistro" if p.pattina_a_sinistra else "destro",
                "" if p.pattina_letta else " (non scritta sul DT: valore d'uso)"),
             "fondo saldato piatto per %.1f mm, rigato e con gli angoli "
             "tagliati; tondo di nuovo a %.1f mm dal fondo%s"
             % (p.saldatura * PIATTA, p.saldatura,
                " (la stampa massima)" if p.saldatura_letta
                else " (stimato: il DT non lo disegna)"),
             "aperto in cima, la bocca rimboccata in fuori: fascia bianca "
             "da %.1f mm (valore d'uso)" % RISVOLTO]
    return righe


def _liscio(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def maglia(p, origine_mm, px_mm, misura_tex, spessore=None):
    """(V, UV, T) del tubo montato, in mm, con la texture del DT intero e
    sotto le strisce del rovescio (`ballotin.con_interno`). Il fronte guarda
    +Z, la bocca +Y, il fondo sta a Y = 0."""
    from .ballotin import STRISCIA
    sp = folding.SPESSORE_CRT if spessore is None else spessore
    Wt, Ht = misura_tex
    uv_interno = (0.5, (Ht - 1.5 * STRISCIA) / Ht)
    uv_taglio = (0.5, (Ht - 0.5 * STRISCIA) / Ht)
    ox, oy = origine_mm
    cx, cy = p.centro
    span = p.a_des - p.a_sin
    sal = p.saldatura
    piatta = sal * PIATTA
    smusso = piatta * SMUSSO
    R_cima = p.R_bocca - RISVOLTO

    def uv(sx, sy):
        return ((sx - ox) * px_mm / Wt, (sy - oy) * px_mm / Ht)

    def foglio(rho, a):
        return cx + rho * math.cos(a), cy + rho * math.sin(a)

    def punto(rho, s, dentro, oltre=0.0):
        """Il punto del tubo all'altezza dell'arco rho, a s mm lungo il giro
        dal mezzo del fronte (positivo verso destra); `oltre` lo porta fuori
        dal tubo di tanti mm (il risvolto)."""
        C = p.giro(rho)
        u = rho - p.R_fondo
        Y = u * math.sqrt(max(0.0, 1.0 - p.k ** 2))
        r = C / (2.0 * math.pi) - (sp if dentro else 0.0) + oltre
        th = 2.0 * math.pi * s / C
        xc, zc = r * math.sin(th), r * math.cos(th)
        # schiacciato: il giro diventa due pareti piatte larghe C/2
        q = ((s / C) + 0.5) % 1.0 - 0.5          # -0.5..0.5, 0 sul fronte
        if abs(q) <= 0.25:
            xf, zf = q * C, (0.0 if dentro else sp)
        else:
            xf = (0.5 * np.sign(q) - q) * C
            zf = -(0.0 if dentro else sp)
        if piatta <= 0:
            return (xc, Y, zc)
        # piatto fino a `piatta`, poi tondo di nuovo alla stampa massima
        w = 1.0 - _liscio((u - piatta) / (sal - piatta))
        if u < piatta:
            # le righe delle ganasce, le due pareti insieme
            zf += (RIGHE_FONDE * math.sin(2.0 * math.pi * u / RIGHE_PASSO)
                   * min(1.0, (piatta - u) / RIGHE_PASSO))
            # gli angoli tagliati: il fondo sale verso i fianchi
            e = abs(xf) - (C / 4.0 - smusso)
            if e > 0:
                Y = e + Y * (1.0 - e / piatta)
        return ((1 - w) * xc + w * xf, Y, (1 - w) * zc + w * zf)

    rhos = np.linspace(p.R_fondo, R_cima, PASSI_ALTO + 1)
    if sal > 0:
        extra = np.r_[np.linspace(p.R_fondo, p.R_fondo + piatta,
                                  int(4 * piatta / RIGHE_PASSO) + 2),
                      np.linspace(p.R_fondo + piatta, p.R_fondo + sal, 25)]
        rhos = np.unique(np.r_[rhos, extra])
    V, UV, T = [], [], []

    # la parte che si vede: dal bordo della pattina all'altro lato. Il mezzo
    # (s = 0) e' il fronte. Sul foglio, a parita' di angolo la distanza dal
    # lato cresce col raggio: la pattina e' una fascia di larghezza costante,
    # e in angolo vale pattina/rho; le colonne si danno in frazione del giro.
    def a_di(f, rho):
        """L'angolo sul foglio della frazione f della parte che si vede."""
        vis = span - p.pattina / rho
        if p.pattina_a_sinistra:
            return p.a_sin + p.pattina / rho + f * vis
        return p.a_sin + f * vis

    def striscia(f0, f1, dentro, verso, uv_fisso=None, oltre=0.0, raggio=0.0,
                 righe=None, fuori=0.0):
        b = len(V)
        fs = np.linspace(f0, f1, PASSI_GIRO + 1)
        for rho in (rhos if righe is None else righe):
            C = p.giro(rho)
            for f in fs:
                s = (f - 0.5) * C
                x, y, z = punto(rho, s, dentro, fuori)
                if raggio:
                    # la pattina sta sotto il bordo che la copre: un poco dentro
                    rr = math.hypot(x, z) or 1.0
                    x, z = x * (rr - raggio) / rr, z * (rr - raggio) / rr
                V.append((x, y, z))
                if uv_fisso is not None:
                    UV.append(uv_fisso)
                elif oltre:
                    # la pattina: dal lato del foglio fino al bordo della parte vista
                    t = (f - f0) / (f1 - f0) if f1 != f0 else 0.0
                    if p.pattina_a_sinistra:
                        a = p.a_sin + t * p.pattina / rho
                    else:
                        a = p.a_des - p.pattina / rho + t * p.pattina / rho
                    UV.append(uv(*foglio(rho, a)))
                else:
                    UV.append(uv(*foglio(rho, a_di(f, rho))))
        n = len(fs)
        for i in range(len(rhos if righe is None else righe) - 1):
            for j in range(n - 1):
                v00 = b + i * n + j
                v01, v10, v11 = v00 + 1, v00 + n, v00 + n + 1
                if verso > 0:
                    T.extend([(v00, v01, v11), (v00, v11, v10)])
                else:
                    T.extend([(v00, v11, v01), (v00, v10, v11)])

    # Sul foglio l'angolo dell'immagine cresce in senso orario (y in giu'):
    # guardando dal centro verso la bocca, verso destra. Il fronte e' il
    # mezzo della parte vista, e la sua destra sul foglio e' la destra del
    # pack (+X): la stampa e' fuori, nessuna specchiatura.
    striscia(0.0, 1.0, False, 1)
    striscia(0.0, 1.0, True, -1, uv_fisso=uv_interno)
    # la pattina, sotto l'altro bordo: oltre il retro, uno spessore dentro
    fp = p.pattina / p.giro(p.R_bocca)
    if p.pattina_a_sinistra:
        striscia(-fp, 0.0, False, 1, oltre=1, raggio=sp / 2.0)
    else:
        striscia(1.0, 1.0 + fp, False, 1, oltre=1, raggio=sp / 2.0)
    # il risvolto: la cima del foglio rimboccata in fuori sul tubo, col
    # rovescio bianco a vista, uno spessore fuori dalla parete
    giu = np.linspace(R_cima - RISVOLTO, R_cima, 7)
    striscia(0.0, 1.0, False, 1, uv_fisso=uv_interno, righe=giu, fuori=sp)
    # le coste, fra il fuori e il dentro: il fondo, il bordo del risvolto, e
    # la piega in cima, bianca anche lei
    for rho, a, b_, uvc, su in (
            (p.R_fondo, (False, 0.0), (True, 0.0), uv_taglio, False),
            (R_cima - RISVOLTO, (False, sp), (False, 0.0), uv_taglio, False),
            (R_cima, (False, sp), (True, 0.0), uv_interno, True)):
        b = len(V)
        C = p.giro(rho)
        fs = np.linspace(0.0, 1.0, PASSI_GIRO + 1)
        for f in fs:
            V.append(punto(rho, (f - 0.5) * C, a[0], a[1]))
            UV.append(uvc)
            V.append(punto(rho, (f - 0.5) * C, b_[0], b_[1]))
            UV.append(uvc)
        for j in range(len(fs) - 1):
            a0, a1, b0, b1 = b + 2 * j, b + 2 * j + 1, b + 2 * j + 2, b + 2 * j + 3
            if su:
                T.extend([(a0, b0, b1), (a0, b1, a1)])
            else:
                T.extend([(a0, b1, b0), (a0, a1, b1)])
    V = np.asarray(V, float)
    UV = np.asarray(UV, float)
    T = np.asarray(T, int)
    return V, UV, T
