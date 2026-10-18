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
- la bocca ha l'orlo arrotolato in fuori, a sezione tonda: un tubetto
  tutto attorno, come l'orlo di un vasetto. La carta sale, gira in fuori e
  torna alla parete, e da fuori si vede il rovescio, bianco carta in piena
  luce (non il rovescio in ombra dell'interno). Il diametro del tubetto e'
  `ORLO` volte la fascia che il DT lascia in cima fuori dalla stampa massima
  (`RISVOLTO` se non la disegna). La parete finisce alla stampa massima, e
  il tubetto e' centrato li';
- sul fondo la fascia che il DT lascia fuori dalla stampa massima, a
  tratteggio: la saldatura comincia dove finisce la grafica, e ne resta a
  vista solo un terzo, sotto la stampa massima - corta, piatta, le due pareti
  una contro l'altra, rigata dalle ganasce e con gli angoli tagliati a 45
  gradi; il resto della fascia e' rifilato. La saldatura e' larga quanto il
  tubo (i fianchi si ripiegano dentro), non di piu': nessun piede che sporge.
  Sopra, di lato, il tubo e' ancora schiacciato: lo spessore cresce in linea
  retta, un cuneo, fino a raggiungere il cono a un terzo abbondante della
  lunghezza (`PIZZICO`); poi il cono dritto fino all'orlo. Di fronte non
  cambia. Nessuna curva che si gonfi: il raccordo fra cuneo e cono sta sotto
  tutti e due.

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
# della fascia fuori dalla stampa massima, la parte che resta a vista sotto
# la grafica: la saldatura (il resto e' rifilato)
SALDATA = 1.0 / 3.0
# sopra la saldatura il tubo e' schiacciato: di lato lo spessore cresce in
# linea retta (un cuneo) fino a raggiungere il cono, a questa parte del tubo
# dalla saldatura alla bocca; poi il cono dritto fino all'orlo
PIZZICO = 0.35
# mm: il raccordo fra il cuneo e il cono, sotto tutte e due (niente pancia)
RACCORDO_CUNEO = 4.0
# gli angoli tagliati della saldatura, a 45 gradi: il lato del triangolo, in
# parte della larghezza (al massimo SMUSSO_MAX dell'altezza della saldatura)
SMUSSO = 0.2
SMUSSO_MAX = 0.8
# le righe delle ganasce sulla saldatura: passo e profondita', mm
RIGHE_PASSO = 0.8
RIGHE_FONDE = 0.08
# i fianchi della saldatura, dove le due pareti si incontrano: la parte del
# coseno in cui il davanti passa al dietro (lo spigolo arrotondato)
SPIGOLO = 0.15
# il diametro del tubetto dell'orlo, mm, se il DT non disegna la stampa
# massima in cima
RISVOLTO = 3.0
RISVOLTO_MAX = 10.0     # mm: un arco piu' in basso non e' quello della bocca
# il diametro del tubetto dell'orlo, in parte della fascia del DT fuori
# dalla stampa massima in cima: un poco piu' sottile della fascia (chiesto da
# chi ha caricato il caso 84c854d6a5, che a 1,0 lo voleva "un po' piu'
# piccolo")
ORLO = 0.7
# i passi attorno alla sezione del tubetto dell'orlo
PASSI_ORLO = 24
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
    risvolto: float = RISVOLTO      # mm, il diametro dell'orlo
    pattina_letta: bool = False
    saldatura_letta: bool = False
    risvolto_letto: bool = False

    @property
    def lato(self):
        return self.R_bocca - self.R_fondo

    @property
    def R_base(self):
        """Il raggio dell'arco dove il tubo finisce in basso: la saldatura
        sotto la stampa massima, il resto della fascia rifilato."""
        return self.R_fondo + self.saldatura * (1.0 - SALDATA)

    @property
    def R_cima(self):
        """Il raggio dell'arco dove la parete finisce e comincia l'orlo: la
        stampa massima in cima."""
        return self.R_bocca - self.risvolto

    @property
    def alto(self):
        """L'altezza del tubo montato, dal fondo saldato alla cima dell'orlo
        (mezzo tubetto sopra la parete)."""
        return ((self.R_cima - self.R_base) * math.sqrt(max(0.0, 1.0 - self.k ** 2))
                + self.orlo / 2.0)

    @property
    def orlo(self):
        """Il diametro del tubetto dell'orlo, mm."""
        return ORLO * self.risvolto

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
    risvolto = _risvolto(per_stile, stile, c, Rg, Rg * (a_des - a_sin))
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
                saldatura=float(saldatura),
                risvolto=risvolto if risvolto is not None else RISVOLTO,
                pattina_letta=letta, saldatura_letta=sal is not None,
                risvolto_letto=risvolto is not None)


def _risvolto(per_stile, stile_dt, c, Rg, giro_bocca):
    """La fascia in cima fuori dalla stampa massima, in mm: l'arco di un
    altro stile concentrico alla bocca e poco sotto. E' quella che si
    arrotola nell'orlo. None se il DT non la disegna."""
    migliore = None
    for stile, tratti in per_stile.items():
        if stile == stile_dt:
            continue
        for P in tratti:
            P = np.asarray(P, float)
            if len(P) < 3 or _lunghezza(P) < 0.15 * giro_bocca:
                continue
            if _freccia(P) < FRECCIA_MIN:
                continue
            cc, r = _cerchio(P)
            if np.linalg.norm(cc - c) > CONCENTRICI:
                continue
            d = Rg - r
            if 0.5 <= d <= RISVOLTO_MAX and (migliore is None or d < migliore):
                migliore = d
    return float(migliore) if migliore is not None else None


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
    righe = ["tubo a cono: alto %.1f mm, bocca %.1f mm, fondo %.1f mm di "
             "diametro" % (p.alto, p.giro(p.R_cima) / math.pi,
                           p.giro(p.R_base) / math.pi),
             "steso a settore di corona: lati da %.1f mm, archi da %.1f e "
             "%.1f mm" % (p.lato, p.R_bocca * (p.a_des - p.a_sin),
                           p.R_fondo * (p.a_des - p.a_sin)),
             "pattina da %.1f mm sul lato %s del foglio, sul retro%s"
             % (p.pattina, "sinistro" if p.pattina_a_sinistra else "destro",
                "" if p.pattina_letta else " (non scritta sul DT: valore d'uso)"),
             "saldatura da %.1f mm subito sotto la grafica%s: piatta, larga "
             "quanto il tubo, rigata e con gli angoli tagliati; sopra il tubo "
             "e' schiacciato, di lato un cuneo dritto per %.1f mm, poi il cono "
             "dritto fino all'orlo; il resto della fascia (%.1f mm) rifilato"
             % (p.saldatura * SALDATA,
                " (la stampa massima)" if p.saldatura_letta
                else " (stimata: il DT non disegna la stampa massima)",
                PIZZICO * (p.R_cima - p.R_base - p.saldatura * SALDATA)
                * math.sqrt(max(0.0, 1.0 - p.k ** 2)),
                p.saldatura * (1.0 - SALDATA)),
             "aperto in cima, l'orlo arrotolato in fuori a sezione tonda, "
             "bianco: un tubetto da %.2f mm di diametro%s"
             % (p.orlo, " (%d%% della fascia fuori dalla stampa massima in "
                "cima, %.1f mm)" % (round(100 * ORLO), p.risvolto)
                if p.risvolto_letto else " (valore d'uso)")]
    return righe


def tela(tex):
    """La texture del DT con sotto tre strisce: il rovescio in ombra
    (l'interno, `ballotin.INTERNO`), il taglio e il rovescio in piena luce
    (l'orlo della bocca, fuori). Il GLB resta a un materiale."""
    from PIL import Image
    from .ballotin import INTERNO, STRISCIA, TAGLIO
    t = Image.new("RGB", (tex.width, tex.height + 3 * STRISCIA), INTERNO)
    t.paste(tex.convert("RGB"), (0, 0))
    t.paste(Image.new("RGB", (tex.width, STRISCIA), TAGLIO),
            (0, tex.height + STRISCIA))
    t.paste(Image.new("RGB", (tex.width, STRISCIA), folding.INTERNO),
            (0, tex.height + 2 * STRISCIA))
    return t


def _liscio(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def maglia(p, origine_mm, px_mm, misura_tex, spessore=None):
    """(V, UV, T) del tubo montato, in mm, con la texture del DT intero e
    sotto le strisce del rovescio (`tela`). Il fronte guarda +Z, la bocca +Y,
    il fondo sta a Y = 0."""
    from .ballotin import STRISCIA
    sp = folding.SPESSORE_CRT if spessore is None else spessore
    Wt, Ht = misura_tex
    uv_interno = (0.5, (Ht - 2.5 * STRISCIA) / Ht)
    uv_taglio = (0.5, (Ht - 1.5 * STRISCIA) / Ht)
    uv_rovescio = (0.5, (Ht - 0.5 * STRISCIA) / Ht)
    ox, oy = origine_mm
    cx, cy = p.centro
    span = p.a_des - p.a_sin
    base = p.R_base
    sal = p.R_fondo + p.saldatura - base     # la saldatura a vista
    pizzico = PIZZICO * (p.R_cima - base - sal)
    smusso = min(SMUSSO * p.giro(base) / math.pi, SMUSSO_MAX * sal)
    R_cima = p.R_cima

    def uv(sx, sy):
        return ((sx - ox) * px_mm / Wt, (sy - oy) * px_mm / Ht)

    def foglio(rho, a):
        return cx + rho * math.cos(a), cy + rho * math.sin(a)

    r_cono = lambda u: p.giro(base + u) / (2.0 * math.pi)     # noqa: E731
    pendenza = (r_cono(sal + pizzico) - sp) / pizzico if pizzico > 0 else 0.0

    def _tondo(u):
        """Quanto e' tondo il tubo a u dal fondo: 0 piatto, 1 tondo."""
        if u < sal:
            return 0.0
        if pizzico <= 0:
            return 1.0
        r = r_cono(u)
        cuneo = sp + pendenza * (u - sal)
        k = RACCORDO_CUNEO
        h = min(1.0, max(0.0, 0.5 + 0.5 * (r - cuneo) / k))
        b = r * (1 - h) + cuneo * h - k * h * (1 - h)
        return min(1.0, max(0.0, b / r))

    def punto(rho, s, dentro, oltre=0.0):
        """Il punto del tubo all'altezza dell'arco rho, a s mm lungo il giro
        dal mezzo del fronte (positivo verso destra); `oltre` lo porta fuori
        dal tubo di tanti mm (l'orlo)."""
        C = p.giro(rho)
        u = rho - base
        Y = u * math.sqrt(max(0.0, 1.0 - p.k ** 2))
        r = C / (2.0 * math.pi) - (sp if dentro else 0.0) + oltre
        th = 2.0 * math.pi * s / C
        x, zc = r * math.sin(th), r * math.cos(th)
        if sal <= 0:
            return (x, Y, zc)
        # schiacciato: la larghezza resta quella del tubo, lo spessore va a
        # zero - le due pareti una contro l'altra, ognuna col suo spessore.
        # Piatto sotto `sal` (la stampa massima); sopra, di lato, lo spessore
        # e' il minore fra il cuneo (una retta dalla saldatura al cono, a
        # `pizzico`) e il cono, col raccordo `RACCORDO_CUNEO` che sta sotto
        # tutti e due: nessuna curva che si gonfia
        tondo = _tondo(u)
        verso = max(-1.0, min(1.0, math.cos(th) / SPIGOLO))
        z = zc * tondo + verso * (0.0 if dentro else sp) * (1.0 - tondo)
        if u < sal:
            # le righe delle ganasce, le due pareti insieme
            z += (RIGHE_FONDE * math.sin(2.0 * math.pi * u / RIGHE_PASSO)
                  * min(1.0, (sal - u) / RIGHE_PASSO, u / RIGHE_PASSO + 0.5))
            # gli angoli tagliati a 45 gradi: il fondo sale verso i fianchi
            e = abs(x) - (r - smusso)
            if e > 0:
                Y = e + Y * (1.0 - e / sal)
        return (x, Y, z)

    rhos = np.linspace(base, R_cima, PASSI_ALTO + 1)
    if sal > 0:
        extra = np.r_[np.linspace(base, base + sal,
                                  int(4 * sal / RIGHE_PASSO) + 2),
                      np.linspace(base + sal, base + sal + pizzico, 60)]
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
                 righe=None):
        b = len(V)
        fs = np.linspace(f0, f1, PASSI_GIRO + 1)
        for rho in (rhos if righe is None else righe):
            C = p.giro(rho)
            for f in fs:
                s = (f - 0.5) * C
                x, y, z = punto(rho, s, dentro)
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
    # l'orlo: un tubetto attorno alla bocca, a sezione tonda, col rovescio
    # bianco a vista. La sezione parte dalla cima della parete (phi = pi,
    # tangente in su), sale, gira in fuori e scende, e torna li': il centro
    # e' mezzo diametro fuori dalla parete, all'altezza della cima
    rr = p.orlo / 2.0
    b = len(V)
    C = p.giro(R_cima)
    fs = np.linspace(0.0, 1.0, PASSI_GIRO + 1)
    for phi in np.linspace(math.pi, -math.pi, PASSI_ORLO + 1):
        for f in fs:
            x, y, z = punto(R_cima, (f - 0.5) * C, False, rr * (1.0 + math.cos(phi)))
            V.append((x, y + rr * math.sin(phi), z))
            UV.append(uv_rovescio)
    n = len(fs)
    for i in range(PASSI_ORLO):
        for j in range(n - 1):
            v00 = b + i * n + j
            v01, v10, v11 = v00 + 1, v00 + n, v00 + n + 1
            T.extend([(v00, v11, v01), (v00, v10, v11)])
    # le coste, fra il fuori e il dentro: il fondo e la cima della parete,
    # dentro l'orlo
    for rho, a, b_, uvc, su in (
            (base, (False, 0.0), (True, 0.0), uv_taglio, False),
            (R_cima, (False, 0.0), (True, 0.0), uv_rovescio, True)):
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
