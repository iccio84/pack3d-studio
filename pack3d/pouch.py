"""
Il pouch: la busta stand-up col soffietto sul fondo (doypack).

Si fa da un nastro solo, come il flowpack, e la fustella dice tutto quello
che serve a montarla. Attraverso il nastro, da un bordo all'altro:

    lembo | pannello | piega in cima | pannello | soffietto | (lembo)

- il nastro si piega in cima alla busta: la piega e' la linea che ha ai due
  lati due fasce uguali, la saldatura alta, una su ogni pannello;
- i due pannelli sono lunghi uguali - dalla piega al fondo - e sono il fronte
  e il retro;
- quello che avanza dopo il secondo pannello e' la striscia del soffietto: si
  piega dentro e, a busta piena, si apre nella base. Ai suoi capi due fasce
  di saldatura, e fra loro il corpo, che e' la profondita' della base;
- l'ultima fascia chiude sul lembo del primo pannello: e' la saldatura
  longitudinale, sul fondo.

Lungo il nastro il passo e' la larghezza della busta, e ai due capi ci sono
le saldature laterali: le legge il lettore del flowpack, sono le sue testate.

Tutte le saldature sono piatte, senza zigrinatura. Il fronte e' il pannello
con piu' grafica: il retro di un pouch e' quasi sempre testo e fondo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

PT2MM = 25.4 / 72.0

# Quanto puo' scostarsi la lunghezza di un pannello da quella dell'altro, e
# quanto puo' scostarsi una linea dalla posizione attesa, in mm.
TOL_PANNELLI = 1.5
TOL_LINEA = 0.6
# La saldatura alta e le fasce del soffietto: piu' larghe di cosi' non sono
# saldature.
FASCIA_MAX = 20.0
# La forma della busta piena. Il profilo della mezza profondita' lungo
# l'altezza, da 1 sul fondo a 0 sotto la saldatura alta, e l'esponente della
# sezione fra le saldature laterali: 1 sarebbe una parabola, con un angolo
# vivo sulla saldatura; 0,5 un'ellisse, che ci arriva in verticale.
PROFILO_P = 1.6
PROFILO_Q = 0.75
SEZIONE_E = 0.85
# Mezzo spessore del film: fronte e retro si toccano nelle saldature, e
# fra le due facce resta questo, perche' non si sovrappongano.
FILM = 0.12


@dataclass(frozen=True)
class Pouch:
    foglio: tuple       # (x0, y0, x1, y1) dello steso, pt, telaio della pagina
    ruotato: bool       # il nastro corre in orizzontale sulla pagina
    passo: float        # mm: larghezza della busta, saldature laterali comprese
    laterale: float     # mm: ciascuna saldatura laterale
    nastro: float       # mm: larghezza del nastro
    rovescio: bool      # la struttura si legge dal bordo opposto dello steso
    piega: float        # mm dal bordo di lettura: la cima della busta
    altezza: float      # mm: dalla piega al fondo di ciascun pannello
    alta: float         # mm: la saldatura alta, su ciascun pannello
    soffietto: tuple    # (inizio, fine) del corpo del soffietto, mm di lettura
    avvisi: tuple = ()

    @property
    def corpo(self):
        """La larghezza di ciascun pannello fra le saldature laterali."""
        return self.passo - 2.0 * self.laterale

    @property
    def base(self):
        """La profondita' della base: il corpo del soffietto aperto."""
        return self.soffietto[1] - self.soffietto[0]

    def sul_foglio(self, w):
        """Una posizione di lettura sul nastro, in mm dal bordo dello steso."""
        return self.nastro - w if self.rovescio else w


def linee_attraverso(pdf, foglio, ruotato):
    """Le linee del disegno tecnico che attraversano il nastro, in mm dal suo
    bordo: piega, saldature, soffietto. Solo quelle lunghe almeno meta' del
    passo: le altre sono box, quote, marche."""
    from .dieline import _technical_pens
    from .flowpack import _ricuci
    from .tracciati import segmenti

    segs, larga, alta = segmenti(pdf, 0)
    penne = _technical_pens(segs, larga, alta)
    S = _ricuci([s for s in segs if s[4] in penne])
    x0, y0, x1, y1 = foglio
    if ruotato:
        verso, lungo, web = "V", (y0, y1), (x0, x1)
    else:
        verso, lungo, web = "H", (x0, x1), (y0, y1)
    passo = lungo[1] - lungo[0]
    linee = set()
    for k, c, a, b, _st in S:
        if k != verso or not web[0] - 3.0 <= c <= web[1] + 3.0:
            continue
        if min(b, lungo[1]) - max(a, lungo[0]) < 0.5 * passo:
            continue
        linee.add(round((c - web[0]) * PT2MM, 1))
    return sorted(linee)


def struttura(linee, nastro):
    """`(rovescio, piega, altezza, alta, soffietto, avvisi)`: la lettura del
    nastro che spiega meglio le linee, o None.

    Si prova da tutti e due i bordi: lo steso puo' stare col soffietto in
    basso o in alto. La piega e' una linea fra un quarto e tre quinti del
    nastro; il secondo pannello finisce su una linea a una lunghezza dalla
    piega uguale alla prima; quello che avanza e' il soffietto, piu' corto di
    un pannello. Vince la lettura che ha la saldatura alta simmetrica e il
    corpo del soffietto fra due fasce.
    """
    candidati = []
    for rovescio in (False, True):
        pos = sorted({round(nastro - p, 1) if rovescio else p for p in linee}
                     | {0.0, round(nastro, 1)})

        def c_e(v):
            return any(abs(p - v) <= TOL_LINEA for p in pos)

        for f in pos:
            if not 0.25 * nastro <= f <= 0.6 * nastro:
                continue
            for g in pos:
                h1, h2 = f, g - f
                if g <= f or abs(h1 - h2) > TOL_PANNELLI:
                    continue
                resto = nastro - g
                if not 10.0 <= resto < h1:
                    continue
                alte = sorted(s for s in {round(abs(p - f), 1) for p in pos}
                              if 2.0 <= s <= FASCIA_MAX and c_e(f - s) and c_e(f + s))
                dentro = [p for p in pos if g + 2.0 <= p <= nastro - 2.0]
                a_b = dentro[0] if dentro and dentro[0] - g <= FASCIA_MAX else None
                b_b = dentro[-1] if dentro and nastro - dentro[-1] <= FASCIA_MAX else None
                punti = (2 if alte else 0) + (a_b is not None) + (b_b is not None)
                candidati.append((punti, -abs(h1 - h2), rovescio, f, g, alte, a_b, b_b))
    if not candidati:
        return None
    candidati.sort(key=lambda c: (c[0], c[1]), reverse=True)
    _p, _d, rovescio, f, g, alte, a_b, b_b = candidati[0]
    altezza = round((f + (g - f)) / 2.0, 2)
    avvisi = []
    if alte:
        alta = alte[0]
    else:
        alta = 6.0
        avvisi.append("pouch: la saldatura alta non e' disegnata ai due lati "
                      "della piega, la tengo di %.0f mm" % alta)
    if a_b is None or b_b is None or b_b - a_b < 10.0:
        a_b, b_b = g, nastro
        avvisi.append("pouch: le fasce del soffietto non si leggono, la base "
                      "e' tutta la striscia")
    return rovescio, f, altezza, alta, (a_b, b_b), avvisi


def leggi(pdf, fp):
    """Il pouch dallo steso gia' letto dal lettore del flowpack (`fp`):
    foglio, passo, nastro e saldature laterali sono le sue; la struttura
    attraverso il nastro la legge `struttura`."""
    from .flowpack import foglio_in_pagina

    foglio = foglio_in_pagina(fp)
    linee = linee_attraverso(pdf, foglio, fp.ruotato)
    letto = struttura(linee, fp.web_mm)
    if letto is None:
        raise ValueError(
            "pouch: sul nastro di %.0f mm non trovo la piega in cima con due "
            "pannelli lunghi uguali e il soffietto dopo; linee a %s mm"
            % (fp.web_mm, ", ".join("%g" % p for p in linee[:14])))
    rovescio, piega, altezza, alta, soffietto, avvisi = letto
    return Pouch(foglio=tuple(foglio), ruotato=bool(fp.ruotato),
                 passo=float(fp.step_mm), laterale=float(fp.end_fin),
                 nastro=float(fp.web_mm), rovescio=rovescio, piega=piega,
                 altezza=altezza, alta=alta, soffietto=soffietto,
                 avvisi=tuple(avvisi))


def dichiara(p):
    """I cartellini della lettura."""
    return ["pouch: busta stand-up col soffietto",
            "busta %.0f x %.0f mm, saldature laterali %.1f, alta %.1f"
            % (p.passo, p.altezza, p.laterale, p.alta),
            "soffietto: base profonda %.0f mm" % p.base,
            "nastro %.0f mm: piega in cima a %.0f, soffietto da %.0f"
            % (p.nastro, p.sul_foglio(p.piega),
               p.sul_foglio(p.piega + p.altezza))]


def _uv_pannello(p, fronte_b, y, retro):
    """La posizione di lettura sul nastro di un punto alto `y` sul fronte o
    sul retro. Il pannello dopo la piega (B) scende verso il soffietto,
    l'altro verso il lembo."""
    giu = p.altezza - y
    dopo = fronte_b != retro        # il pannello e' B
    return p.piega + giu if dopo else p.piega - giu


def quale_fronte(p, tex):
    """`(fronte_b, avviso)`: il fronte e' il pannello con piu' grafica.

    Si misura sulla texture gia' pulita dal disegno tecnico: il dettaglio
    medio - quanto cambia l'immagine da un pixel al vicino - nella zona di
    ciascun pannello fra le saldature. Il retro di un pouch e' testo, fondo e
    spazi per la data; il fronte ha marchio, prodotto, illustrazioni.
    """
    im = np.asarray(tex.convert("L"), dtype=np.float32)
    h, w = im.shape

    def dettaglio(w0, w1):
        a, b = sorted((p.sul_foglio(w0), p.sul_foglio(w1)))
        s0 = (p.laterale + 2.0) / p.passo
        s1 = 1.0 - s0
        if p.ruotato:
            zona = im[int(s0 * h):int(s1 * h), int(a / p.nastro * w):int(b / p.nastro * w)]
        else:
            zona = im[int(a / p.nastro * h):int(b / p.nastro * h), int(s0 * w):int(s1 * w)]
        if zona.size < 16:
            return 0.0
        return float(np.abs(np.diff(zona, axis=0)).mean() + np.abs(np.diff(zona, axis=1)).mean())

    m = p.alta + 2.0
    a = dettaglio(m, p.piega - m)
    b = dettaglio(p.piega + m, p.piega + p.altezza - m)
    fronte_b = b >= a
    forte, debole = (b, a) if fronte_b else (a, b)
    if debole > 0 and forte / debole < 1.15:
        return fronte_b, ("pouch: fronte e retro hanno quasi la stessa grafica "
                          "(%.1f contro %.1f): il fronte e' quello %s, da "
                          "controllare" % (forte, debole,
                                           "attaccato al soffietto" if fronte_b
                                           else "dal lato del lembo"))
    return fronte_b, ("pouch: il fronte e' il pannello %s, con %.1f volte la "
                      "grafica dell'altro" % ("attaccato al soffietto" if fronte_b
                                              else "dal lato del lembo",
                                              forte / max(debole, 1e-6)))


def _profilo(t):
    """La mezza profondita' lungo l'altezza, in frazione di quella del fondo."""
    t = np.clip(t, 0.0, 1.0)
    return (1.0 - t ** PROFILO_P) ** PROFILO_Q


def _sezione(hz, corpo, n=400):
    """Una sezione fra le saldature laterali con mezza profondita' `hz`:
    `(theta, sigma, a)` - l'angolo che la percorre, la lunghezza di film dal
    centro e la mezza larghezza. La lunghezza totale e' il corpo: il film
    non si allunga, quindi piu' la busta si gonfia piu' si stringe."""
    th = np.linspace(-math.pi / 2.0, math.pi / 2.0, n)
    c = np.abs(np.cos(th))

    def lunghezza(a):
        x = a * np.sin(th)
        z = hz * c ** (2.0 * SEZIONE_E)
        s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(z)))])
        return s

    if hz <= 1e-6:
        a = corpo / 2.0
        s = lunghezza(a)
        return th, s - s[-1] / 2.0, a
    lo, hi = 0.2 * corpo / 2.0, corpo / 2.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if lunghezza(mid)[-1] > corpo:
            hi = mid
        else:
            lo = mid
    a = 0.5 * (lo + hi)
    s = lunghezza(a)
    return th, s * (corpo / s[-1]) - corpo / 2.0, a


def _colonne(p, n_corpo, n_lat):
    """Le colonne lungo il passo, come lunghezza di film dal centro: fitte
    vicino alle saldature, dove la busta si chiude."""
    L = p.corpo
    phi = np.linspace(-math.pi / 2.0, math.pi / 2.0, n_corpo)
    corpo = 0.5 * L * np.sin(phi)
    lat = np.linspace(0.0, p.laterale, n_lat + 1)[1:]
    return np.concatenate([-(L / 2.0 + lat[::-1]), corpo, L / 2.0 + lat])


def _triangoli(nr, nc, primo):
    i, j = np.meshgrid(np.arange(nr - 1), np.arange(nc - 1), indexing="ij")
    a = primo + i * nc + j
    b, c, d = a + 1, a + nc + 1, a + nc
    return np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3),
                           np.stack([a, c, d], -1).reshape(-1, 3)])


def maglia(p, fronte_b, n_corpo=150, n_lat=4, n_alto=150, n_base=26):
    """`(V, UV, T)` della busta piena, in mm, in piedi: y in alto, il fronte
    verso +z. Fronte, retro e base sono tre griglie dello stesso film, e le
    UV sono le loro posizioni sullo steso: si mappa il film, non le facce.

    Il verso orizzontale lo decide la piega: fronte e retro escono dallo
    stesso nastro piegato in cima, quindi un punto ha la stessa x sull'uno e
    sull'altro, e la grafica non si specchia se la mappa conserva il verso
    del foglio. `segno` e' quel verso.
    """
    L, H = p.corpo, p.altezza
    Y = H - p.alta
    h0 = p.base / 2.0
    sig = _colonne(p, n_corpo, n_lat)
    s_foglio = sig + p.passo / 2.0
    corpo = np.abs(sig) <= L / 2.0 + 1e-9
    # il verso del foglio sul pack: vedi la docstring
    segno = (1.0 if fronte_b else -1.0) * (-1.0 if p.rovescio else 1.0) \
        * (-1.0 if p.ruotato else 1.0)
    ys = np.concatenate([np.linspace(0.0, Y, n_alto), np.linspace(Y, H, 5)[1:]])

    righe_x, righe_z = [], []
    for y in ys:
        hz = h0 * float(_profilo(y / Y)) if y < Y else 0.0
        th, s, a = _sezione(hz, L)
        x = np.empty_like(sig)
        z = np.zeros_like(sig)
        tc = np.interp(sig[corpo], s, th)
        x[corpo] = a * np.sin(tc)
        z[corpo] = hz * np.abs(np.cos(tc)) ** (2.0 * SEZIONE_E)
        fuori = ~corpo
        x[fuori] = np.sign(sig[fuori]) * (a + np.abs(sig[fuori]) - L / 2.0)
        righe_x.append(x)
        righe_z.append(z)
    X = np.array(righe_x) * segno
    Z = np.array(righe_z) + FILM
    Yg = np.repeat(ys[:, None], len(sig), 1)

    def uv(w_lettura, s):
        u = s / p.passo
        v = np.vectorize(p.sul_foglio)(w_lettura) / p.nastro
        return np.stack([v, u], -1) if p.ruotato else np.stack([u, v], -1)

    parti_v, parti_uv, parti_t = [], [], []
    n = 0
    for retro in (False, True):
        V = np.stack([X, Yg, -Z if retro else Z], -1).reshape(-1, 3)
        w = np.array([_uv_pannello(p, fronte_b, y, retro) for y in ys])
        W = np.repeat(w[:, None], len(sig), 1)
        S = np.repeat(s_foglio[None, :], len(ys), 0)
        UV = uv(W, S).reshape(-1, 2)
        T = _triangoli(len(ys), len(sig), n)
        parti_v.append(V), parti_uv.append(UV), parti_t.append(_verso(V, T, n, 2, -1.0 if retro else 1.0))
        n += len(V)

    # la base: il corpo del soffietto aperto, sul fondo, fra il fronte e il
    # retro. Le colonne sono quelle del corpo, perche' i bordi combacino.
    xb = X[0][corpo]
    zb = Z[0][corpo]
    f = np.linspace(1.0, -1.0, n_base)
    Vb = np.stack([np.repeat(xb[None, :], n_base, 0),
                   np.zeros((n_base, len(xb))),
                   f[:, None] * zb[None, :]], -1).reshape(-1, 3)
    a_b, b_b = p.soffietto
    # il bordo del soffietto che sta sotto il fronte: dalla parte del
    # pannello B se il fronte e' B, dalla parte del lembo se no
    davanti, dietro = (a_b, b_b) if fronte_b else (b_b, a_b)
    wb = davanti + (1.0 - f) / 2.0 * (dietro - davanti)
    UVb = uv(np.repeat(wb[:, None], len(xb), 1),
             np.repeat(s_foglio[corpo][None, :], n_base, 0)).reshape(-1, 2)
    Tb = _triangoli(n_base, len(xb), n)
    parti_v.append(Vb), parti_uv.append(UVb), parti_t.append(_verso(Vb, Tb, n, 1, -1.0))
    return (np.vstack(parti_v), np.vstack(parti_uv).astype(np.float32),
            np.vstack(parti_t))


def _verso(V, T, primo, asse, segno):
    """I triangoli di una parte, girati perche' la normale media guardi fuori
    lungo `asse` col `segno` dato: il viewer scarta le facce posteriori."""
    P = V[T - primo]
    nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    if (nrm[:, asse].sum() * segno) < 0:
        return T[:, [0, 2, 1]]
    return T
