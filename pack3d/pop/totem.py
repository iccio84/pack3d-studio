"""
Il totem lenticolare: un pannello curvo stampato fronte e retro, i popup
staccati davanti alle due facce, la piattina di plastica bianca sotto.

Dal proprietario: «Per lenticolare intendo un pannello curvato», «I pannelli
devono essere piegati in modo da essere curvo (la geometria non deve essere
sfaccettata) e alla base ci deve essere una piattina in plastica bianca che
permette al totem di stare su» (regole/pop.md, *Il totem*).

- **Due PDF, fronte e retro.** Ognuno ha il pannello col suo contorno di
  taglio e, dentro, i contorni dei popup. Il contorno del retro e' quello
  del fronte specchiato: lo stesso pannello, stampato sulle due facce. Il
  fronte e' la faccia convessa, il retro quella concava.
- **La curva.** Il pannello steso e' l'arco: la sua larghezza e' la
  lunghezza dell'arco, e l'altezza resta dritta (un cilindro). La freccia,
  se il PDF non la dice, e' una scelta: `FRECCIA`, dal render di
  riferimento. Liscia: i vertici fitti lungo l'arco e le normali condivise.
- **I popup**: le sagome coi loro contorni di taglio, davanti alla faccia
  della loro stampa, alla distanza `DISTANZA_POPUP`, curve come il pannello
  (sul retro concavo una sagoma piatta entrerebbe nel pannello ai lati),
  con un distanziale dietro.
- **La piattina**: una lastra di plastica bianca che segue l'arco sotto il
  pannello, larga `PIATTINA_MARGINE` per parte e coi capi tondi; il pannello
  ci sta sopra.
"""
from __future__ import annotations

import numpy as np

from . import fustella as F

PX_MM = 2.0                 # pixel per mm della texture: il totem e' quasi tutto grafica
SPESSORE = 3.0              # mm, il pannello (due facce stampate di 1,5)
SPESSORE_POPUP = 2.0        # mm
DISTANZA_POPUP = 12.0       # mm fra il pannello e il retro di un popup
FRECCIA = 100.0 / 580.0     # freccia dell'arco / larghezza del pannello, dal render
PIATTINA_SPESSORE = 6.0     # mm
PIATTINA_MARGINE = 45.0     # mm attorno al piede del pannello
PASSO_ARCO = 6.0            # mm fra due file di vertici lungo l'arco
DISTANZIALE = 40.0          # mm, il lato del distanziale di un popup
POPUP_MIN = 400.0           # mm2: sotto, un tracciato chiuso non e' un popup


def raggio(larghezza, freccia):
    """Il raggio dell'arco lungo `larghezza` con quella `freccia`."""
    lo, hi = larghezza / np.pi * 0.5 + 1e-6, 1e7
    for _ in range(100):                     # freccia(R) cala con R: bisezione
        r = (lo + hi) / 2
        f = r * (1 - np.cos(larghezza / (2 * r)))
        lo, hi = (r, hi) if f > freccia else (lo, r)
    return (lo + hi) / 2


def leggi(pdf):
    """(pannello, popup): il contorno del pannello (il tracciato chiuso piu'
    grande) e quelli dei popup (i chiusi dentro di lui)."""
    tagli = F.contorni_di_taglio(pdf)
    pannello, resto = tagli[0], tagli[1:]
    x0, y0 = pannello.min(0)
    x1, y1 = pannello.max(0)
    popup = [a for a in resto
             if np.all(a.min(0) >= (x0 - 1, y0 - 1)) and np.all(a.max(0) <= (x1 + 1, y1 + 1))
             and np.prod(a.max(0) - a.min(0)) > POPUP_MIN]
    return pannello, popup


def _sposta(a, d):
    return np.asarray(a, float) + d


def monta(fronte, retro, uscita, freccia=None, t=SPESSORE, px_mm=PX_MM):
    """Costruisce il totem in `uscita` (GLB) dai PDF del fronte e del retro.
    Torna (avvisi, misure)."""
    from PIL import Image
    from .. import exporters
    from .espositore import Curva, Montaggio

    pf, popf = leggi(fronte)
    pr, popr = leggi(retro)
    larg = float(pf[:, 0].max() - pf[:, 0].min())
    alto = float(pf[:, 1].max() - pf[:, 1].min())
    f = larg * (FRECCIA if freccia is None else freccia / larg)
    R = raggio(larg, f)

    # La texture: le due pagine affiancate, fronte e retro, con in mezzo
    # una striscia bianca (la piattina e i distanziali). Le coordinate del
    # retro si spostano nella griglia unica.
    margine = 5.0
    zf = (pf[:, 0].min() - margine, min(pf[:, 1].min(), pr[:, 1].min()) - margine,
          pf[:, 0].max() + margine, max(pf[:, 1].max(), pr[:, 1].max()) + margine)
    zr = (pr[:, 0].min() - margine, zf[1], pr[:, 0].max() + margine, zf[3])
    Gf, Gr = F.Griglia(zf, px_mm), F.Griglia(zr, px_mm)
    bianco = 20.0
    dx = (zf[2] - zf[0]) + bianco - (zr[0] - zf[0])          # retro -> griglia unica
    G = F.Griglia((zf[0], zf[1], zf[2] + bianco + (zr[2] - zr[0]), zf[3]), px_mm)
    chiusi = lambda ls: [np.vstack([a, a[:1]]) for a in ls]
    sf = F.resa_senza_dt(fronte, Gf, chiusi([pf] + popf), chiusi([pf] + popf))
    sr = F.resa_senza_dt(retro, Gr, chiusi([pr] + popr), chiusi([pr] + popr))
    steso = Image.new("RGB", (G.W, G.H), "white")
    steso.paste(sf, (0, 0))
    steso.paste(sr, (int(round((zf[2] - zf[0] + bianco) * px_mm)), 0))
    mo = Montaggio(G, t / 2)
    tex = mo.texture(steso)
    x_bianco = zf[2] + bianco / 2
    uv_bianco = np.array([G.a_pixel(x_bianco, zf[1] + 2)[0] / G.W,
                          G.a_pixel(x_bianco, zf[1] + 2)[1] / G.H * mo.q])

    xc_f = (pf[:, 0].min() + pf[:, 0].max()) / 2
    xc_r = (pr[:, 0].min() + pr[:, 0].max()) / 2 + dx
    piede = pf[:, 1].max()                                   # il bordo in basso, sul foglio
    h0 = PIATTINA_SPESSORE

    def cilindro(rr, verso, xc, specchio):
        """(punto, Curva): la faccia stampata a raggio `rr`, il cartone
        verso l'asse (verso -1) o fuori (+1); sul retro il foglio e'
        specchiato."""
        def ang(x):
            s = (x - xc) * (-1.0 if specchio else 1.0)
            return s / R

        def punto(x, y):
            a = ang(x)
            return np.array([rr * np.sin(a), h0 + (piede - y), rr * np.cos(a) - R])

        def dentro(x, y):
            a = ang(x)
            return np.array([np.sin(a), 0.0, np.cos(a)]) * verso
        return punto, dentro

    def stendi(contorno, nome, rr, verso, xc, specchio, spessore, sposta=0.0):
        a = _sposta(contorno, (sposta, 0.0))
        pz = F.Pezzo((*a.min(0), *a.max(0)), tagli=[np.vstack([a, a[:1]])], nome=nome)
        punto, dentro = cilindro(rr, verso, xc, specchio)
        rq = pz.riquadro
        for masc, scarto in G.pannelli(pz):
            if masc.sum() < 50:
                continue
            mo.pannello(pz, masc, scarto,
                        lambda lx, ly, punto=punto: punto(lx + rq[0], ly + rq[1]),
                        Curva(lambda lx, ly, dentro=dentro: dentro(lx + rq[0], ly + rq[1]), 0,
                              passo=PASSO_ARCO),
                        nome, spessore=spessore)
        return pz

    th = t / 2
    tp = SPESSORE_POPUP
    d = DISTANZA_POPUP
    stendi(pf, "pannello_fronte", R, -1.0, xc_f, False, th)
    stendi(pr, "pannello_retro", R - t, 1.0, xc_r, True, th, sposta=dx)
    distanziali = []
    for i, a in enumerate(popf):
        stendi(a, "popup_fronte_%d" % (i + 1), R + d + tp, -1.0, xc_f, False, tp)
        distanziali.append((a, R, R + d, xc_f, False))
    for i, a in enumerate(popr):
        stendi(a, "popup_retro_%d" % (i + 1), R - t - d - tp, 1.0, xc_r, True, tp, sposta=dx)
        distanziali.append((_sposta(a, (dx, 0.0)), R - t - d, R - t, xc_r, True))

    # la piattina: una lastra lungo l'arco, sotto il pannello
    s0 = (pf[:, 0].min() - xc_f) / R
    s1 = (pf[:, 0].max() - xc_f) / R
    Rm = R - t / 2
    V, T = _piattina(Rm, s0, s1, PIATTINA_MARGINE, h0, R)
    mo.solido("piattina", V, np.tile(uv_bianco, (len(V), 1)), T)
    # i distanziali dei popup, al baricentro di ognuno
    for k, (a, r0, r1, xc, specchio) in enumerate(distanziali):
        cx, cy = a.mean(0)
        th0 = (cx - xc) * (-1.0 if specchio else 1.0) / R
        V, T = _settore(r0, r1, th0, DISTANZIALE / 2 / R, h0 + piede - cy, DISTANZIALE, R)
        mo.solido("distanziali", V, np.tile(uv_bianco, (len(V), 1)), T)

    V, UV, T, parti = mo.array()
    exporters.write_glb_mesh(V, UV, T, tex, uscita, tex_max=4096, parti=parti)
    avvisi = ["totem: pannello %.0f x %.0f mm, curvo con raggio %.0f mm (freccia %.0f, "
              "corda %.0f); %d popup davanti e %d dietro, a %.0f mm; piattina bianca "
              "di %.0f mm" % (larg, alto, R, f, 2 * R * np.sin(larg / (2 * R)), len(popf),
                              len(popr), d, h0)]
    return avvisi, dict(larghezza=larg, altezza=alto, raggio=R, freccia=f)


def _anello(r0, r1, a0, a1, n, R):
    """I punti in pianta (x, z) di una fascia d'arco fra i raggi r0 e r1."""
    a = np.linspace(a0, a1, n)
    est = np.stack([r1 * np.sin(a), r1 * np.cos(a) - R], 1)
    inn = np.stack([r0 * np.sin(a), r0 * np.cos(a) - R], 1)
    return est, inn


def _estrudi(pianta, y0, y1):
    """(V, T): il solido di un poligono in pianta (x, z), da y0 a y1, con le
    facce sopra, sotto e i fianchi; i vertici dei fianchi a parte (spigoli
    vivi)."""
    pts, tri = F.triangola([pianta])
    n = len(pts)
    sopra = np.column_stack([pts[:, 0], np.full(n, y1), pts[:, 1]])
    sotto = np.column_stack([pts[:, 0], np.full(n, y0), pts[:, 1]])
    V = [sopra, sotto]
    # verso: la faccia sopra guarda in su
    a, b, c = sopra[tri[:, 0]], sopra[tri[:, 1]], sopra[tri[:, 2]]
    su = np.cross(b - a, c - a)[:, 1] > 0
    tri = np.where(su[:, None], tri, tri[:, ::-1])
    T = [tri, tri[:, ::-1] + n]
    base = 2 * n
    p = np.asarray(pianta, float)
    q = np.roll(p, -1, axis=0)
    m = len(p)
    giro = np.sum(p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1])
    for i in range(m):
        A, B = p[i], q[i]
        quad = np.array([[A[0], y0, A[1]], [B[0], y0, B[1]], [B[0], y1, B[1]], [A[0], y1, A[1]]])
        V.append(quad)
        t2 = np.array([[0, 1, 2], [0, 2, 3]]) + base
        # fuori: a destra del verso del contorno se gira in senso orario
        e = B - A
        fuori = np.array([e[1], 0.0, -e[0]]) * (1 if giro > 0 else -1)
        nn = np.cross(quad[1] - quad[0], quad[2] - quad[0])
        if nn @ fuori < 0:
            t2 = t2[:, ::-1]
        T.append(t2)
        base += 4
    return np.concatenate(V), np.concatenate(T)


def _piattina(Rm, a0, a1, m, h, R):
    """La piattina: la fascia fra Rm - m e Rm + m lungo l'arco da a0 ad a1,
    coi capi tondi (mezzi cerchi di raggio m), spessa h."""
    est, inn = _anello(Rm - m, Rm + m, a0, a1, 160, R)
    capi = []
    for a, verso in ((a1, 1.0), (a0, -1.0)):
        c = np.array([Rm * np.sin(a), Rm * np.cos(a) - R])
        rad = np.array([np.sin(a), np.cos(a)])               # dal centro dell'arco in fuori
        tan = np.array([np.cos(a), -np.sin(a)]) * verso      # oltre il capo
        g = np.linspace(0, np.pi, 24)[1:-1]
        capi.append(c + m * (np.outer(np.cos(g), rad) + np.outer(np.sin(g), tan)))
    pianta = np.vstack([est, capi[0], inn[::-1], capi[1][::-1]])
    return _estrudi(pianta, 0.0, h)


def _settore(r0, r1, a, da, y, alto, R):
    """Un distanziale: il settore fra i raggi r0 e r1, attorno all'angolo
    `a` (+- da), alto `alto` attorno a y."""
    est, inn = _anello(r0, r1, a - da, a + da, 6, R)
    pianta = np.vstack([est, inn[::-1]])
    return _estrudi(pianta, y - alto / 2, y + alto / 2)
