"""
L'espositore da terra a ripiani, in piu' PDF: un PDF per pezzo.

Il primo espositore (`espositore.py`) stava tutto su una tavola. Questo
arriva in cinque file, dal proprietario il 16 novembre 2026: «Questo
espositore è composto da più pdf. Può capitare che un espositore possa essere
in un unica pagina o più pdf». I pezzi:

- la **schiena**: il fondo e, ai lati, una striscia e un'ala che fanno il
  fianco interno, con le asole dei ripiani; in cima il cappello, con la
  feritoia del crowner;
- i **laterali**: due pezzi uguali e specchiati. La parte stampata e' il
  fianco di fuori; la piega doppia e' lo spigolo davanti, e l'aletta con le
  asole torna dentro, contro l'ala della schiena;
- la **base**: lo zoccolo davanti, col fronte inclinato e i fianchi che si
  incollano sui laterali, fuori; sul suo cielo poggia il ripiano piu' basso;
- il **ripiano**: un vassoio con le sponde e la fascetta davanti, ripetuto
  (`RIPIANI`) all'altezza delle asole dei laterali;
- il **crowner**: dietro la cima della schiena, con le alette girate di 180
  gradi dietro il pannello, di rinforzo. Di un PDF di piu' pagine si prende la prima.

Ogni PDF si legge da solo (`fustella.tratti`, `fustella.pezzi`) e si mette
nella tavola comune accanto agli altri, con la sua grafica: da li' il
montaggio e' quello del primo espositore (`espositore.Montaggio`). Quale
pezzo e' quale lo dicono i pezzi del PDF (`_ruolo`), non il nome del file.
Le alette nascoste (la linguetta in cima ai laterali, quelle sotto la
schiena e la base, gli angoli dei ripiani) non si montano.
"""
from __future__ import annotations

import numpy as np

from . import fustella as F
from .espositore import Montaggio, _dove

PX_MM = 2.0
# il cartone: piu' sottile del primo espositore, perche' la sponda del
# ripiano sta fra le due alette dei laterali
SPESSORE = 2.5
RIPIANI = 4
# un pannello piu' piccolo di cosi' (pixel) e' un ritaglio, non si monta
MINIMO_PX = 200


def _sposta(p, dx, dy, nome):
    """Il pezzo `p` spostato di (dx, dy) mm, col suo nome."""
    d = np.array([dx, dy], float)
    r = p.riquadro
    return F.Pezzo((r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy),
                   tagli=[np.asarray(a, float) + d for a in p.tagli],
                   pieghe=[np.asarray(a, float) + d for a in p.pieghe], nome=nome)


def _ruolo(pezzi):
    """Quale pezzo dell'espositore c'e' in un PDF, dai suoi pezzi."""
    if len(pezzi) == 2:
        a, b = sorted(pezzi, key=lambda p: -p.larghezza * p.altezza)
        if b.larghezza * b.altezza > 0.7 * a.larghezza * a.altezza:
            return "laterali"
        return "ripiano"
    if len(pezzi) == 1:
        p = pezzi[0]
        if p.altezza > 1.2 * p.larghezza:
            return "schiena"
        if p.larghezza > 2.0 * p.altezza:
            return "base"
        return "crowner"
    raise ValueError("espositore: un PDF con %d pezzi, non so che pezzo e'" % len(pezzi))


def leggi(pdfs):
    """{ruolo: (pdf, pezzi, tagli, pieghe, segni)} dai PDF dell'espositore."""
    letti = {}
    for k, pdf in enumerate(pdfs):
        segni = []
        try:
            tagli, pieghe = F.tratti(pdf, segni)
            pezzi = F.pezzi(tagli, pieghe)
            r = _ruolo(pezzi)
        except ValueError as e:
            raise ValueError("espositore, il PDF %d: %s" % (k + 1, e))
        if r in letti:
            raise ValueError("espositore: due PDF sembrano lo stesso pezzo (%s)" % r)
        letti[r] = (pdf, pezzi, tagli, pieghe, segni)
    manca = [r for r in ("schiena", "laterali", "base", "ripiano", "crowner") if r not in letti]
    if manca:
        raise ValueError("espositore a ripiani: mancano i PDF di %s" % ", ".join(manca))
    return letti


def _pieghe(p, asse, lungo=0.0):
    return sorted(v for a, v, s, e in p.pieghe_dritte(minimo=lungo) if a == asse)


def _asole(p, x0, x1):
    """I fondi (mm locali) delle asole dei ripiani nell'aletta fra x0 e x1.
    Un'asola puo' essere disegnata a tratti separati: i tratti che si toccano
    (a 2 mm) fanno un'asola sola."""
    righe = []
    for pl in p.tagli:
        a = np.asarray(pl, float)
        (ax, ay), (bx, by) = p.locale(*a.min(0)), p.locale(*a.max(0))
        if x0 <= ax and bx <= x1 and bx - ax < 140 and by - ay < 60:
            righe.append([ax, ay, bx, by])
    gruppi = []
    for r in righe:
        for g in gruppi:
            if r[0] <= g[2] + 2 and g[0] <= r[2] + 2 and r[1] <= g[3] + 2 and g[1] <= r[3] + 2:
                g[:] = [min(g[0], r[0]), min(g[1], r[1]), max(g[2], r[2]), max(g[3], r[3])]
                break
        else:
            gruppi.append(list(r))
    fondi = [g[3] for g in gruppi if 60 < g[2] - g[0] < 140 and 20 < g[3] - g[1] < 60]
    return sorted(set(round(v, 1) for v in fondi))


def _vassoio(pz):
    """Il ripiano in un pezzo solo: i pezzi del suo PDF uniti, coi lati del
    fronte chiusi da due pieghe fra i capi della piega piu' bassa del pezzo
    di sopra (il risvolto) e di quella piu' alta del pezzo di sotto (il
    davanti del piano)."""
    pz = sorted(pz, key=lambda p: p.riquadro[1])
    r = (min(p.riquadro[0] for p in pz), min(p.riquadro[1] for p in pz),
         max(p.riquadro[2] for p in pz), max(p.riquadro[3] for p in pz))
    u = F.Pezzo(r, tagli=[a for p in pz for a in p.tagli],
                pieghe=[a for p in pz for a in p.pieghe], nome=pz[0].nome)
    for su, giu in zip(pz, pz[1:]):
        a = max((h for h in su.pieghe_dritte(minimo=100.0) if h[0] == "H"), key=lambda h: h[1])
        b = min((h for h in giu.pieghe_dritte(minimo=100.0) if h[0] == "H"), key=lambda h: h[1])
        ya, yb = su.riquadro[1] + a[1], giu.riquadro[1] + b[1]
        for xa, xb in ((su.riquadro[0] + a[2], giu.riquadro[0] + b[2]),
                       (su.riquadro[0] + a[3], giu.riquadro[0] + b[3])):
            u.pieghe.append(np.array([(xa, ya), (xb, yb)], float))
    return u


def _pendenza(p, e0, e1):
    """L'angolo (radianti) del fronte della base dalla verticale. I bordi
    lunghi del fianco (quello in cima e quello sul pavimento) stanno in
    orizzontale una volta montato: sul PDF fanno col fronte l'angolo del
    fronte stesso, 25 gradi sulla base del caso. La piega obliqua no: e'
    piu' ripida, e non da' la pendenza."""
    angoli = []
    for pl in p.tagli:
        a = np.asarray(pl, float)
        for u, v in zip(a, a[1:]):
            (ux, uy), (vx, vy) = p.locale(*u), p.locale(*v)
            dx, dy = abs(vx - ux), abs(vy - uy)
            fuori = max(ux, vx) <= e0 + 1.0 or min(ux, vx) >= e1 - 1.0
            if fuori and np.hypot(dx, dy) > 100.0 and 0.1 < dy / max(dx, 1e-9) < 1.2:
                angoli.append(np.arctan2(dy, dx))
    return float(np.median(angoli)) if angoli else 0.0


def monta(pdfs, uscita, t=SPESSORE, px_mm=PX_MM, ripiani=RIPIANI, montaggio=None):
    """Costruisce l'espositore a ripiani in `uscita` (GLB) dai suoi PDF.
    Torna (avvisi, misure). Con `montaggio` (un dict) ci lascia il
    `Montaggio`, per le prove (`espositore.intersezioni`)."""
    from PIL import Image
    from .. import exporters
    letti = leggi(pdfs)

    # la tavola comune: ogni PDF accanto all'altro, con la sua grafica
    rese, pezzi, x = [], {}, 0.0
    alto = 0.0
    for ruolo in ("schiena", "laterali", "base", "ripiano", "crowner"):
        pdf, pz, tagli, pieghe, segni = letti[ruolo]
        z = (min(p.riquadro[0] for p in pz) - 5, min(p.riquadro[1] for p in pz) - 5,
             max(p.riquadro[2] for p in pz) + 5, max(p.riquadro[3] for p in pz) + 5)
        Gz = F.Griglia(z, px_mm)
        rese.append((F.resa_quadricromia(pdf, Gz, tagli + pieghe + segni), x))
        dx, dy = x - z[0], -z[1]
        ordinati = sorted(pz, key=lambda p: (p.riquadro[0], p.riquadro[1]))
        pezzi[ruolo] = [_sposta(p, dx, dy, "%s_%d" % (ruolo, k)) for k, p in enumerate(ordinati)]
        alto = max(alto, z[3] - z[1])
        x += z[2] - z[0] + 10.0
    G = F.Griglia((0.0, 0.0, x, alto), px_mm)
    steso = Image.new("RGB", (G.W, G.H), "white")
    for im, xx in rese:
        steso.paste(im, (int(round(xx * px_mm)), 0))
    mo = Montaggio(G, t)
    tex = mo.texture(steso)

    def stendi(p, nome, regola):
        for pan in G.pannelli(p):
            masc, scarto = pan
            if masc.sum() < MINIMO_PX:
                continue
            r = _dove(pan, p, G)
            fatto = regola((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r)
            if fatto is None:
                continue
            punto, = fatto
            # la direzione del cartone e' quella che lascia la stampa dritta
            # vista da fuori: U x V, coi due assi del foglio sul modello
            P0 = np.array(punto(0.0, 0.0), float)
            U = np.array(punto(1.0, 0.0), float) - P0
            V = np.array(punto(0.0, 1.0), float) - P0
            mo.pannello(p, masc, scarto, punto, np.cross(U, V), nome)

    # --- la schiena: il fondo, i fianchi interni, il cappello
    sch = pezzi["schiena"][0]
    v = _pieghe(sch, "V", 200.0)
    h = _pieghe(sch, "H", 100.0)
    b0, b1 = v[1], v[2]                         # il fondo fra le due pieghe di dentro
    cima = max(y for y in _pieghe(sch, "H") if y < 0.2 * sch.altezza)
    piede = min(y for y in h if y > 0.8 * sch.altezza)
    Hs = piede - cima                           # l'altezza dell'espositore
    W = b1 - b0
    Xw = W / 2.0
    cx = (b0 + b1) / 2.0

    def regola_schiena(px, py, r):
        if py > piede:
            return None                         # le alette sotto
        if py < cima:                           # il cappello, piegato in avanti
            return (lambda lx, ly: (lx - cx, Hs, cima - ly),)
        if px < b0:                             # il fianco di sinistra
            return (lambda lx, ly: (-Xw, Hs - (ly - cima), b0 - lx),)
        if px > b1:
            return (lambda lx, ly: (Xw, Hs - (ly - cima), lx - b1),)
        return (lambda lx, ly: (lx - cx, Hs - (ly - cima), 0.0),)
    stendi(sch, "schiena", regola_schiena)

    # --- i laterali: fuori la stampa, lo spigolo davanti, dentro l'aletta
    profondo = b0                               # striscia e ala: il fianco
    fondi = None
    for k, lat in enumerate(pezzi["laterali"]):
        c0, c1 = _pieghe(lat, "V", 200.0)[:2]
        c = c1 - c0
        Dp = profondo + c / 2.0                 # lo spigolo davanti
        Xo, Xi = Xw + c / 2.0, Xw - c / 2.0
        top = max(y for y in _pieghe(lat, "H") if y < 0.2 * lat.altezza)
        a_destra = lat.larghezza - c1 > c0      # la stampa a destra: e' il fianco destro
        if a_destra:
            f = _asole(lat, 0.0, c0)
        else:
            f = _asole(lat, c1, lat.larghezza)
        fondi = fondi or [Hs - (y - top) for y in f]

        def regola_lat(px, py, r, c0=c0, c1=c1, top=top, Dp=Dp, Xo=Xo, Xi=Xi, a_destra=a_destra):
            if py < top:
                return None                     # la linguetta in cima
            Y = (lambda ly: Hs - (ly - top))
            if c0 < px < c1:                    # lo spigolo davanti
                if a_destra:
                    return (lambda lx, ly: (Xo - (c1 - lx), Y(ly), Dp),)
                return (lambda lx, ly: (-Xo + (lx - c0), Y(ly), Dp),)
            stampa = px > c1 if a_destra else px < c0
            if a_destra:
                if stampa:
                    return (lambda lx, ly: (Xo, Y(ly), Dp - (lx - c1)),)
                return (lambda lx, ly: (Xi, Y(ly), Dp - (c0 - lx)),)
            if stampa:
                return (lambda lx, ly: (-Xo, Y(ly), Dp - (c0 - lx)),)
            return (lambda lx, ly: (-Xi, Y(ly), Dp - (lx - c1)),)
        stendi(lat, "laterale_%s" % ("dx" if a_destra else "sx"), regola_lat)
    if not fondi:
        raise ValueError("espositore a ripiani: nelle alette dei laterali non trovo le asole")

    # --- la base: lo zoccolo davanti, col fronte inclinato. Il fianco e la
    # sua aletta oltre la piega obliqua sono un trapezio solo, piatto sulla
    # faccia stampata del laterale (il tratteggio in basso sul laterale e'
    # la colla): il bordo in cima e quello sul pavimento in orizzontale, il
    # bordo di fondo in verticale contro la schiena. Davanti allo spigolo
    # del laterale resta il triangolo del fianco.
    bs = pezzi["base"][0]
    vb = _pieghe(bs, "V", 100.0)
    f0, f1 = vb[1], vb[2]                       # il fronte fra le pieghe di dentro
    e0, e1 = vb[0], vb[3]                       # gli spigoli
    hb = _pieghe(bs, "H", 100.0)
    ft, fb = hb[0], hb[-1]
    Ls = fb - ft
    th = _pendenza(bs, e0, e1)
    hz, run = Ls * np.cos(th), Ls * np.sin(th)
    xb = (f1 - f0) / 2.0
    fc = (f0 + f1) / 2.0
    Zb = Dp + t                                 # il cielo, davanti allo spigolo
    su = np.array([0.0, np.cos(th), -np.sin(th)])    # su per il fronte
    indietro = np.array([0.0, -np.sin(th), -np.cos(th)])  # nel fianco, via dal fronte

    def regola_base(px, py, r):
        if py > fb:
            return None                         # l'aletta sotto
        if f0 < px < f1:
            if py < ft:                         # il cielo: ci poggia il ripiano piu' basso
                return (lambda lx, ly: (lx - fc, hz, Zb - (ft - ly)),)
            return (lambda lx, ly: (lx - fc, hz - (ly - ft) * np.cos(th),
                                    Zb + (ly - ft) * np.sin(th)),)
        if px < e0:                             # il fianco di sinistra e la sua aletta
            A = np.array([-xb, hz, Zb])
            return (lambda lx, ly: tuple(A + (e0 - lx) * indietro + (ft - ly) * su),)
        if px > e1:
            A = np.array([xb, hz, Zb])
            return (lambda lx, ly: tuple(A + (lx - e1) * indietro + (ft - ly) * su),)
        return None                             # gli spigoli, sottili
    stendi(bs, "base", regola_base)

    # --- i ripiani: il vassoio, stampato fuori. Il piano, le sponde e il
    # fronte col marchio; il risvolto del fronte si ripiega dentro. Sul PDF il
    # risvolto e il resto sono due pezzi (i tagli non si chiudono) e i lati del
    # fronte non hanno linee: si fa un pezzo solo, e i lati si chiudono con
    # due pieghe fra i capi delle pieghe del risvolto e del piano.
    rp = _vassoio(pezzi["ripiano"])
    vr = _pieghe(rp, "V", 100.0)
    hr = _pieghe(rp, "H", 100.0)
    r0, r1 = vr[0], vr[-1]
    risvolto, davanti, dietro = hr[0], hr[-2], hr[-1]   # 59.5, 119.5, 399.5 sul ripiano del caso
    cima_fronte = min(y for y in hr if y > risvolto + 0.5)
    sponda = davanti - cima_fronte
    rc = (r0 + r1) / 2.0
    fondo = dietro - davanti
    Zr = t + fondo                              # il davanti del ripiano
    quote = sorted(fondi)[:ripiani]
    # il ripiano piu' basso poggia sul cielo della base, se l'asola e' piu'
    # bassa del cielo (l'asola e' alta 35 mm: il vassoio ci sta lo stesso)
    quote[0] = max(quote[0], hz + t)
    for k, Yk in enumerate(quote):
        def regola_rip(px, py, r, Yk=Yk):
            if (r[2] - r[0]) < 60 and (r[3] - r[1]) < 60:
                return None                     # gli angoli
            if py < risvolto:                   # il risvolto, dentro il fronte
                return (lambda lx, ly: (lx - rc, Yk + sponda + t - (risvolto - ly), Zr - 2 * t),)
            if py < cima_fronte:
                return None                     # la piega doppia in cima al fronte
            if py < davanti:                    # il fronte, col marchio
                return (lambda lx, ly: (lx - rc, Yk + (davanti - ly), Zr),)
            if r0 < px < r1:
                if py > dietro:                 # la sponda di dietro
                    return (lambda lx, ly: (lx - rc, Yk + (ly - dietro), Zr - fondo),)
                return (lambda lx, ly: (lx - rc, Yk, Zr - (ly - davanti)),)
            if px < r0:
                return (lambda lx, ly: (r0 - rc, Yk + (r0 - lx), Zr - (ly - davanti)),)
            return (lambda lx, ly: (r1 - rc, Yk + (lx - r1), Zr - (ly - davanti)),)
        stendi(rp, "ripiano_%d" % (k + 1), regola_rip)

    # --- il crowner: dietro la cima della schiena, il piede del pannello al
    # filo del corpo. Le alette sono girate di 180 gradi, di rinforzo (dal
    # proprietario: «il crowner ha le alette girate di 180 gradi come
    # rinforzo»): oltre le pieghe doppie (larghe quanto il cartone) si
    # ripiegano piatte dietro il pannello, e la striscia oltre la piega a
    # tratti si ripiega ancora, piatta dietro l'aletta. Da davanti si vede
    # solo il pannello, come nel render del proprietario.
    cw = pezzi["crowner"][0]
    vc = _pieghe(cw, "V", 200.0)
    g0, g1 = vc[0], vc[-1]                      # le pieghe a tratti
    i0, i1 = vc[2], vc[-3]                      # il pannello davanti fra le pieghe doppie
    m0, m1 = vc[1], vc[-2]
    ccx = (i0 + i1) / 2.0
    # il piede del pannello: dove finiscono le pieghe doppie. Sotto c'e' la
    # linguetta, che scende dietro la schiena
    hcw = max(max(s, e) for a, v, s, e in cw.pieghe_dritte(minimo=200.0)
              if a == "V" and min(abs(v - i0), abs(v - i1)) < 0.5)
    Zc = -t
    Yc = Hs
    fl = m0 - g0                                # il fianco del crowner
    xc = (i1 - i0) / 2.0

    def regola_crowner(px, py, r):
        if py > hcw + 10.0 and i0 < px < i1:
            return None                         # la linguetta, dentro la feritoia
        Y = (lambda ly: Yc + (hcw - ly))
        if i0 < px < i1:
            return (lambda lx, ly: (lx - ccx, Y(ly), Zc),)
        if g0 < px < m0:
            return (lambda lx, ly: (-xc + (m0 - lx), Y(ly), Zc - t),)
        if px < g0:
            return (lambda lx, ly: (-xc + fl - (g0 - lx), Y(ly), Zc - 2 * t),)
        if m1 < px < g1:
            return (lambda lx, ly: (xc - (lx - m1), Y(ly), Zc - t),)
        if px > g1:
            return (lambda lx, ly: (xc - fl + (lx - g1), Y(ly), Zc - 2 * t),)
        return None                             # le pieghe doppie, sottili
    stendi(cw, "crowner", regola_crowner)

    V, UV, T, parti = mo.array(_prima(t))
    if montaggio is not None:
        montaggio["mo"] = mo
    exporters.write_glb_mesh(V, UV, T, tex, uscita, tex_max=4096, parti=parti)
    largo = 2 * (Xw + c / 2.0)
    misure = dict(larghezza=largo, profondita=Dp, altezza=Hs, ripiani=quote,
                  base=(hz, run, th), crowner=hcw)
    avvisi = ["espositore a ripiani da %d PDF: %.0f x %.0f mm, alto %.0f (col crowner %.0f); "
              "%d ripiani a %s mm; zoccolo alto %.0f; cartone %.1f mm"
              % (len(pdfs), largo, Dp, Hs, Yc + hcw, len(quote),
                 ", ".join("%.0f" % y for y in quote), hz, t)]
    return avvisi, misure


ORDINE = ("schiena", "laterale", "base", "crowner", "ripiano")


def _prima(t):
    def prima(p):
        nome = p["nome"]
        return next((i for i, n in enumerate(ORDINE) if nome.startswith(n)), len(ORDINE))
    return prima
