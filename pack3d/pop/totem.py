"""
Il totem lenticolare: due pannelli curvi uguali, uno girato di 180 gradi
dietro l'altro - da sopra un'ellisse -, i popup piatti davanti, la base
ovale di plastica bianca sotto.

Dal proprietario: «Per lenticolare intendo un pannello curvato»; «I pannelli
devono essere piegati in modo da essere curvo (la geometria non deve essere
sfaccettata) e alla base ci deve essere una piattina in plastica bianca»;
«Il totem deve essere composto dai 2 pannelli piegati allo stesso modo, uno
poi va girato di 180 gradi in modo che diventi il retro dell'altro formando
così una struttura unica di forma ellittica (visto dall'alto). Ovviamente
geometricamente devono essere separati. La parte posteriore di ogni singolo
pannello va bianca. Inoltre ogni volta che riconosci un popup elimina
l'elemento grafico dalla struttura in modo che rimanga solo nel popup. Il
popup va più spesso e non va mai piegato»; «il basamento deve essere ovale
in modo da ospitare fronte e retro»; la colata «in quadricromia (ombra nera
e non ciano)» (regole/pop.md, *Il totem lenticolare*).

- **Due PDF, due pannelli**: il fronte e il retro, ognuno col suo contorno di
  taglio e, dentro, i contorni dei popup. Ognuno si curva uguale (un
  cilindro: la larghezza stesa e' l'arco) con la stampa fuori; il retro e'
  girato di 180 gradi. I bordi dei due archi si guardano a `FESSURA` mm: due
  pezzi, mai compenetrati. Il dietro di ogni pannello e' bianco.
- **La freccia**, se il PDF non la dice, e' una scelta: `FRECCIA`.
- **Liscio**: una fila di vertici ogni `PASSO_ARCO` mm lungo l'arco, le
  normali condivise.
- **I popup**: piatti, spessi `SPESSORE_POPUP`, a `DISTANZA_POPUP` dal
  pannello nel loro punto di mezzo, col distanziale; la loro grafica esce
  dal pannello (`fustella.oggetti_dentro`) e resta solo su di loro.
- **La grafica in quadricromia**: `fustella.resa_quadricromia`.
- **La base**: un ovale di plastica bianca che contiene le due curve con
  `BASE_MARGINE` mm attorno, spesso `BASE_SPESSORE`.
"""
from __future__ import annotations

import numpy as np

from . import fustella as F

PX_MM = 2.0                 # pixel per mm della texture: il totem e' quasi tutto grafica
SPESSORE = 3.0              # mm, un pannello
SPESSORE_POPUP = 5.0        # mm: un popup e' piu' spesso del pannello
DISTANZA_POPUP = 12.0       # mm fra il pannello e il retro di un popup, nel suo mezzo
FRECCIA = 100.0 / 580.0     # freccia dell'arco / larghezza del pannello, dal render
FESSURA = 1.0               # mm fra i bordi dei due pannelli
BASE_SPESSORE = 6.0         # mm
BASE_MARGINE = 40.0         # mm attorno ai due pannelli
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

    lati = []
    for pdf in (fronte, retro):
        pann, popup = leggi(pdf)
        lati.append(dict(pdf=pdf, pann=pann, popup=popup))
    larg = float(lati[0]["pann"][:, 0].max() - lati[0]["pann"][:, 0].min())
    alto = max(float(l["pann"][:, 1].max() - l["pann"][:, 1].min()) for l in lati)
    f = larg * FRECCIA if freccia is None else float(freccia)
    R = raggio(larg, f)
    phi = larg / (2 * R)
    # il fronte ha l'asse dell'arco a z = zs - R; il suo bordo dentro sta a
    # z = FESSURA / 2, il retro e' lo stesso girato di 180 gradi
    zs = FESSURA / 2 + R - (R - t) * np.cos(phi)

    # La texture: per ogni lato la pagina del pannello (senza la grafica dei
    # popup) e quella dei popup, affiancate; in fondo una striscia bianca (il
    # dietro dei pannelli, la base, i distanziali).
    margine = 5.0
    y0 = min(l["pann"][:, 1].min() for l in lati) - margine
    y1 = max(l["pann"][:, 1].max() for l in lati) + margine
    rese, x = [], 0.0
    for l in lati:
        zona = (l["pann"][:, 0].min() - margine, y0, l["pann"][:, 0].max() + margine, y1)
        chiusi = [np.vstack([a, a[:1]]) for a in [l["pann"]] + l["popup"]]
        togli = F.oggetti_dentro(l["pdf"], l["popup"]) if l["popup"] else []
        Gz = F.Griglia(zona, px_mm)
        for chi, via in (("pann", togli), ("popup", [])):
            if chi == "popup" and not l["popup"]:
                continue
            rese.append((F.resa_quadricromia(l["pdf"], Gz, chiusi, via), x))
            l["dx_" + chi] = x - zona[0]                 # foglio -> griglia unica
            x += zona[2] - zona[0] + 10.0
    bianco = 20.0
    G = F.Griglia((0.0, y0, x + bianco, y1), px_mm)
    steso = Image.new("RGB", (G.W, G.H), "white")
    for im, xx in rese:
        steso.paste(im, (int(round(xx * px_mm)), 0))
    mo = Montaggio(G, t)
    tex = mo.texture(steso)
    X, Y = G.a_pixel(x + bianco / 2, y0 + 2.0)
    uv_bianco = np.array([X / G.W, Y / G.H * mo.q])
    piede = max(l["pann"][:, 1].max() for l in lati)
    h0 = BASE_SPESSORE

    def gira(P, retro):
        """Il retro e' il fronte girato di 180 gradi attorno alla verticale."""
        P = np.array(P, float)
        return P * np.array([-1.0, 1.0, -1.0]) if retro else P

    def stendi(contorno, nome, dx, punto, dentro, curva, spessore):
        a = np.asarray(contorno, float) + (dx, 0.0)
        pz = F.Pezzo((*a.min(0), *a.max(0)), tagli=[np.vstack([a, a[:1]])], nome=nome)
        rq = pz.riquadro
        for masc, scarto in G.pannelli(pz):
            if masc.sum() < 50:
                continue
            pp = (lambda lx, ly, punto=punto: punto(lx + rq[0] - dx, ly + rq[1]))
            dd = (lambda lx, ly, dentro=dentro: dentro(lx + rq[0] - dx, ly + rq[1]))
            mo.pannello(pz, masc, scarto, pp, Curva(dd, 0, passo=PASSO_ARCO) if curva else dd(0, 0),
                        nome, spessore=spessore, uv_dentro=uv_bianco)

    d, tp = DISTANZA_POPUP, SPESSORE_POPUP
    distanziali = []
    for k, l in enumerate(lati):
        retro = k == 1
        xc = (l["pann"][:, 0].min() + l["pann"][:, 0].max()) / 2

        def punto(xp, yp, xc=xc, retro=retro):
            a = (xp - xc) / R
            return gira((R * np.sin(a), h0 + piede - yp, R * np.cos(a) - R + zs), retro)

        def dentro(xp, yp, xc=xc, retro=retro):
            a = (xp - xc) / R
            return gira((-np.sin(a), 0.0, -np.cos(a)), retro)
        nome = "pannello_" + ("retro" if retro else "fronte")
        stendi(l["pann"], nome, l["dx_pann"], punto, dentro, True, t)
        # i popup: piatti, perpendicolari al raggio nel loro mezzo
        for i, a in enumerate(l["popup"]):
            cx, cy = (a.min(0) + a.max(0)) / 2
            ac = (cx - xc) / R
            n = np.array([np.sin(ac), 0.0, np.cos(ac)])          # fuori
            tg = np.array([np.cos(ac), 0.0, -np.sin(ac)])
            O = np.array([0.0, 0.0, zs - R])

            def pp(xp, yp, cx=cx, n=n, tg=tg, O=O, retro=retro):
                P = O + n * (R + d + tp) + tg * (xp - cx) + np.array([0.0, h0 + piede - yp, 0.0])
                return gira(P, retro)
            nd = gira(-n, retro)
            stendi(a, "popup_%s_%d" % ("retro" if retro else "fronte", i + 1), l["dx_popup"],
                   pp, lambda xp, yp, nd=nd: nd, False, tp)
            distanziali.append((O, n, tg, h0 + piede - cy, retro))

    # la base ovale: contiene i due archi, col margine
    a_ = np.linspace(-phi, phi, 200)
    arco = np.stack([R * np.sin(a_), R * np.cos(a_) - R + zs], 1)
    pts = np.vstack([arco, -arco])
    A = float(np.abs(pts[:, 0]).max()) + BASE_MARGINE
    B = BASE_MARGINE
    for _ in range(200):                                       # il minimo che li contiene
        if np.all(_dentro_di(pts, A, B, BASE_MARGINE)):
            break
        B += 2.0
    g = np.linspace(0, 2 * np.pi, 240, endpoint=False)
    V, T = _estrudi(np.stack([A * np.cos(g), B * np.sin(g)], 1), 0.0, h0)
    mo.solido("base", V, np.tile(uv_bianco, (len(V), 1)), T)
    for O, n, tg, y, retro in distanziali:
        c = O + n * R
        V, T = _scatola(c - n * 1.0, n, tg, DISTANZIALE, d + 1.0, y)
        V = gira(V, retro)
        mo.solido("distanziali", V, np.tile(uv_bianco, (len(V), 1)), T)

    V, UV, T, parti = mo.array()
    exporters.write_glb_mesh(V, UV, T, tex, uscita, tex_max=4096, parti=parti)
    corda = 2 * R * np.sin(phi)
    avvisi = ["totem: due pannelli %.0f x %.0f mm curvi con raggio %.0f mm (freccia %.0f, "
              "corda %.0f), il retro girato: da sopra un'ellisse di %.0f x %.0f mm; %d popup "
              "davanti e %d dietro, spessi %.0f mm a %.0f mm; base ovale %.0f x %.0f mm"
              % (larg, alto, R, f, corda, corda, 2 * zs, len(lati[0]["popup"]),
                 len(lati[1]["popup"]), tp, d, 2 * A, 2 * B)]
    return avvisi, dict(larghezza=larg, altezza=alto, raggio=R, freccia=f, base=(2 * A, 2 * B))


def _dentro_di(pts, A, B, m):
    """Se ogni punto sta nell'ellisse (A, B) con almeno `m` mm di margine."""
    g = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    e = np.stack([A * np.cos(g), B * np.sin(g)], 1)
    from scipy.spatial import cKDTree
    dist, _ = cKDTree(e).query(pts)
    r = (pts[:, 0] / A) ** 2 + (pts[:, 1] / B) ** 2
    return (r <= 1.0) & (dist >= m - 0.5)


def _scatola(base, n, tg, lato, prof, y):
    """Un distanziale: un parallelepipedo che parte da `base` lungo `n` per
    `prof` mm, largo `lato` lungo `tg` e alto `lato` attorno a y."""
    p = np.array([base + tg * s for s in (-lato / 2, lato / 2)])
    q = p + n * prof
    pianta = np.array([[p[0][0], p[0][2]], [p[1][0], p[1][2]], [q[1][0], q[1][2]],
                       [q[0][0], q[0][2]]])
    return _estrudi(pianta, y - lato / 2, y + lato / 2)


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
