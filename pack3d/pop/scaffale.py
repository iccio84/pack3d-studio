"""
L'espositore da terra a scaffale, coi pezzi tutti su una pagina.

Dal proprietario, il 16 novembre 2026: un PDF solo con tutti i pezzi
dell'espositore, ognuno col suo nome e la sua quantita' («Genera questo
espositore»). Il disegno tecnico e' diverso da quello degli altri espositori:

- **i tagli neri e le pieghe rosse**, tutte linee continue (gli altri PDF
  hanno le pieghe tratteggiate dello stesso colore dei tagli); una piega puo'
  essere disegnata a «L», due lati di un rettangolo in un tratto solo
  (`_dritti`);
- **in scala 1:2**: la pagina e' 2,97 x 2,10 m, piu' grande di ogni foglio, e
  ogni pezzo misura la meta' di quello che dice la sua scritta (le scritte
  sono curve, non testo: non si leggono). Una pagina piu' grande di due A0
  e' in scala 1:2 (`scala`);
- **il tratteggio delle zone incollate** (arancio, verde acqua) non e' stampa:
  si toglie dalla grafica come il disegno tecnico.

I pezzi che si vedono, riconosciuti dalla forma (`riconosci`), non dal nome:

- i **fianchi**: i due pezzi grandi uguali. Il fianco e' a doppia parete:
  la faccia stampata fuori, la piega doppia davanti (lo spessore del
  fianco), la parete di dentro con le asole dei ripiani; dietro, una
  striscia che gira sul retro della schiena (si avvita);
- la **schiena**: alta quanto i fianchi, con le feritoie dei ripiani;
- il **ripiano** (`RIPIANI`, uno per asola dei fianchi): il fondo, stampato
  sotto; il pannello di dietro girato di 180 gradi sopra il fondo, stampato
  sopra (in mezzo i rinforzi incollati: il tratteggio); la fascetta col
  marchio che sale davanti. Le alette ai lati entrano nelle asole dei
  fianchi, e non si vedono;
- il **dekl**: il frontale dello zoccolo sotto il ripiano piu' basso, le
  orecchie avvitate ai fianchi, il bordo in cima sotto il ripiano;
- il **topper**: il pannello stampato in cima, dietro la schiena, che sporge
  sopra.

I pezzi dentro le pareti (i rinforzi dei fianchi e dei ripiani, le croci
dello zoccolo, i tappi, i portaprezzi) e la scatola di trasporto non si
montano.
"""
from __future__ import annotations

import numpy as np

from . import fustella as F
from .espositore import Montaggio, _dove

PX_MM = 1.0
# il cartone: onda doppia EB. La piega doppia davanti al fianco e' larga 10 mm
SPESSORE = 4.5
# una pagina piu' grande di cosi' (mm, lato lungo: due A0) e' in scala 1:2
PAGINA_GRANDE = 2 * 1189.0
MINIMO_PX = 200



def _rgb(colore):
    """Il colore di pdfplumber (grigio, RGB o CMYK) in RGB fra 0 e 1."""
    try:
        c = [float(v) for v in colore]
    except TypeError:
        c = [float(colore)]
    if len(c) == 4:
        k = 1.0 - c[3]
        return tuple((1.0 - v) * k for v in c[:3])
    if len(c) == 3:
        return tuple(c)
    return (c[0],) * 3 if c else (0.0, 0.0, 0.0)


def _tipo(colore):
    """"taglio" (nero), "piega" (rosso) o None."""
    try:
        r, g, b = _rgb(colore)
    except (TypeError, ValueError):
        return None
    if max(r, g, b) < 0.25:
        return "taglio"
    if r > 0.75 and g < 0.3 and b < 0.3:
        return "piega"
    return None


def _dritti(pl):
    """Una piega disegnata in piu' tratti dritti (a «L», due lati di un
    rettangolo) diventa un tratto per lato; una curva resta com'e'."""
    a = np.asarray(pl, float)
    if len(a) <= 2 or len(a) > 6:
        return [a]
    return [a[i:i + 2] for i in range(len(a) - 1) if np.hypot(*(a[i + 1] - a[i])) > 1.0]


class _Resa:
    """La pagina aperta, coi tratti del disegno tecnico (tagli, pieghe) e del
    tratteggio delle zone incollate resi trasparenti: la grafica e basta.

    Il tratteggio sta negli stessi gruppi della grafica: togliere i gruppi
    (come fa col disegno tecnico `fustella.resa_quadricromia`) toglieva anche
    il marchio sulla fascetta dei ripiani. Qui si tocca solo il colore del
    tratto, in memoria: pdfium rende gli oggetti come sono, senza riscrivere
    la pagina (riscritta, la pagina usciva nera)."""

    def __init__(self, pdf):
        import ctypes
        import pypdfium2 as pdfium
        import pypdfium2.raw as R
        self.doc = pdfium.PdfDocument(pdf)
        self.pg = self.doc[0]
        self.oggetti = list(self.pg.get_objects(max_depth=32))
        for o in self.oggetti:
            if o.type != 2:                            # 2: un tracciato
                continue
            fm, st = ctypes.c_int(), ctypes.c_int()
            R.FPDFPath_GetDrawMode(o.raw, ctypes.byref(fm), ctypes.byref(st))
            if fm.value or not st.value:
                continue                              # pieno: e' grafica
            c = [ctypes.c_uint() for _ in range(4)]
            R.FPDFPageObj_GetStrokeColor(o.raw, *(ctypes.byref(v) for v in c))
            r, g, b, _a = (v.value for v in c)
            w = ctypes.c_float()
            R.FPDFPageObj_GetStrokeWidth(o.raw, ctypes.byref(w))
            if min(r, g, b) > 240 or w.value > 2.0:
                continue                              # un filetto bianco della grafica
            R.FPDFPageObj_SetStrokeColor(o.raw, r, g, b, 0)

    def rendi(self, griglia):
        return F._rendi(self.pg, griglia)

    def chiudi(self):
        del self.oggetti
        self.pg.close()
        self.doc.close()


def scala(pdf):
    """Il rapporto fra la misura vera e quella sulla pagina."""
    import pdfplumber
    with pdfplumber.open(pdf) as doc:
        pg = doc.pages[0]
        lato = max(float(pg.width), float(pg.height)) * F.MM
    return 2.0 if lato > PAGINA_GRANDE else 1.0


def tratti(pdf):
    """(tagli, pieghe, tratteggio) in mm della PAGINA: i tagli neri, le
    pieghe rosse, e le linee degli altri colori (il tratteggio delle zone
    incollate, che dalla grafica si toglie)."""
    import pdfplumber
    tagli, pieghe, altre = [], [], []
    with pdfplumber.open(pdf) as doc:
        pg = doc.pages[0]
        for kind in ("lines", "rects", "curves"):
            for o in getattr(pg, kind):
                if not o.get("stroke"):
                    continue
                c = _tipo(o.get("stroking_color"))
                for pl in F._polilinea(o):
                    if len(pl) < 2:
                        continue
                    pl = [(float(x) * F.MM, float(y) * F.MM) for x, y in pl]
                    if c == "taglio":
                        tagli.append(pl)
                    elif c == "piega":
                        pieghe.extend(_dritti(pl))
                    else:
                        altre.append(pl)
    if not tagli or not pieghe:
        raise ValueError("espositore: nel PDF non trovo i tagli neri e le pieghe rosse")
    return tagli, pieghe, altre


def e_scaffale(pdf):
    """Il PDF e' un espositore a scaffale: i tagli neri e le pieghe rosse
    continue, e tanti pezzi su una pagina. Un PDF col disegno tecnico degli
    altri espositori (le pieghe tratteggiate del colore dei tagli,
    `fustella.tratti`) non e' a scaffale, anche se ha linee nere e rosse."""
    try:
        F.tratti(pdf, [])
        return False
    except ValueError:
        pass
    except OSError:
        return False
    try:
        tagli, pieghe, _a = tratti(pdf)
    except (ValueError, OSError):
        return False
    return len(F.pezzi(tagli, pieghe)) >= 6


def _in_scala(p, s, nome):
    r = p.riquadro
    return F.Pezzo(tuple(v * s for v in r),
                   tagli=[np.asarray(a, float) * s for a in p.tagli],
                   pieghe=[np.asarray(a, float) * s for a in p.pieghe], nome=nome)


def _lunghe(p, asse, frazione):
    """Le pieghe dritte lungo `asse` lunghe almeno `frazione` del pezzo."""
    lato = p.altezza if asse == "V" else p.larghezza
    return sorted(v for a, v, s, e in p.pieghe_dritte(minimo=frazione * lato) if a == asse)


def _inchiostro(pdf, pezzi):
    """Quanta stampa ha ogni pezzo: la frazione di pixel non bianchi nel suo
    riquadro, sulla pagina resa piccola."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        pg = doc[0]
        k = 0.5                                      # pixel per mm della pagina
        im = np.asarray(pg.render(scale=k * F.MM).to_pil().convert("L"), float)
    finally:
        doc.close()
    out = []
    for p in pezzi:
        x0, y0, x1, y1 = (int(round(v * k)) for v in p.riquadro)
        zona = im[max(y0, 0):y1, max(x0, 0):x1]
        out.append(float((zona < 200).mean()) if zona.size else 0.0)
    return out


def _tratteggiati(pezzi, altre):
    """Per ogni pezzo, i mm di tratteggio (le zone incollate) per m2 del suo
    riquadro: un pezzo tutto tratteggiato e' un rinforzo, non la grafica."""
    out = []
    centri = [np.asarray(pl, float).mean(0) for pl in altre]
    lungo = [float(np.hypot(*np.diff(np.asarray(pl, float), axis=0).T).sum()) for pl in altre]
    for p in pezzi:
        x0, y0, x1, y1 = p.riquadro
        tot = sum(L for c, L in zip(centri, lungo) if x0 <= c[0] <= x1 and y0 <= c[1] <= y1)
        out.append(tot / max(p.larghezza * p.altezza * 1e-6, 1e-9))
    return out


def riconosci(pezzi, inchiostro, tratteggio=None):
    """{ruolo: indice} dei pezzi che si montano, dalla forma."""
    tratteggio = tratteggio or [0.0] * len(pezzi)
    n = len(pezzi)
    area = [p.larghezza * p.altezza for p in pezzi]
    ruoli = {}
    # i fianchi: la coppia di pezzi uguali piu' grande, con le pieghe lunghe
    coppie = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = pezzi[i], pezzi[j]
            if (abs(a.larghezza - b.larghezza) < 0.02 * a.larghezza
                    and abs(a.altezza - b.altezza) < 0.02 * a.altezza
                    and a.altezza > a.larghezza and len(_lunghe(a, "V", 0.7)) >= 2):
                coppie.append((area[i], i, j))
    if not coppie:
        raise ValueError("espositore: non trovo i due fianchi (due pezzi grandi uguali)")
    _a, i, j = max(coppie)
    ruoli["fianco_a"], ruoli["fianco_b"] = i, j
    H = pezzi[i].altezza
    usati = {i, j}
    # la schiena: alta quanto i fianchi, stretta, con le feritoie
    cand = [k for k in range(n) if k not in usati
            and abs(pezzi[k].altezza - H) < 0.05 * H and pezzi[k].altezza > 2 * pezzi[k].larghezza]
    if not cand:
        raise ValueError("espositore: non trovo la schiena (alta quanto i fianchi)")
    ruoli["schiena"] = max(cand, key=lambda k: len(pezzi[k].tagli))
    usati.add(ruoli["schiena"])
    W = pezzi[ruoli["schiena"]].larghezza
    # il ripiano: il pezzo stampato con piu' pieghe lunghe orizzontali
    cand = [k for k in range(n) if k not in usati and inchiostro[k] > 0.3]
    if not cand:
        raise ValueError("espositore: non trovo il ripiano")
    ruoli["ripiano"] = max(cand, key=lambda k: len(_lunghe(pezzi[k], "H", 0.35)))
    usati.add(ruoli["ripiano"])
    # il dekl: stampato, largo poco piu' della schiena, basso
    cand = [k for k in range(n) if k not in usati and inchiostro[k] > 0.3
            and 1.0 < pezzi[k].larghezza / W < 1.3 and pezzi[k].altezza < 0.6 * pezzi[k].larghezza]
    if cand:
        ruoli["dekl"] = max(cand, key=lambda k: inchiostro[k])
        usati.add(ruoli["dekl"])
    # il topper: stampato, senza pieghe, il piu' grande che resta
    cand = [k for k in range(n) if k not in usati and inchiostro[k] > 0.3
            and not pezzi[k].pieghe and area[k] > 0.1 * W * H
            and tratteggio[k] < 0.2 * max(tratteggio)]
    if cand:
        ruoli["topper"] = max(cand, key=lambda k: area[k])
    return ruoli


def leggi(pdf):
    """(pezzi in mm veri per ruolo, scala, tagli, pieghe, tratteggio in mm
    della pagina)."""
    tagli, pieghe, altre = tratti(pdf)
    pezzi = F.pezzi(tagli, pieghe)
    if len(pezzi) < 6:
        raise ValueError("espositore: nel PDF ci sono solo %d pezzi" % len(pezzi))
    ruoli = riconosci(pezzi, _inchiostro(pdf, pezzi), _tratteggiati(pezzi, altre))
    s = scala(pdf)
    return ({r: (pezzi[k], _in_scala(pezzi[k], s, r)) for r, k in ruoli.items()},
            s, tagli, pieghe, altre)


def _fronte(p):
    """Il fianco: (piega di dentro e di fuori della piega doppia davanti,
    piega di dietro, la parete di dentro sta a sinistra)."""
    v = _lunghe(p, "V", 0.7)
    W = p.larghezza
    coppie = [(a, b) for a, b in zip(v, v[1:]) if 4.0 < b - a < 20.0 and a > 200 and W - b > 200]
    if not coppie:
        raise ValueError("espositore: nel fianco non trovo la piega doppia davanti")
    a, b = coppie[0]
    # la parete di dentro ha le asole: i tagli lunghi orizzontali
    H = p.altezza
    y0 = p.riquadro[1]
    asole = [pl for pl in p.tagli if np.ptp(np.asarray(pl)[:, 0]) > 150
             and np.ptp(np.asarray(pl)[:, 1]) < 80
             and 0.05 * H < np.asarray(pl)[:, 1].min() - y0
             and np.asarray(pl)[:, 1].max() - y0 < 0.95 * H]
    xs = [np.asarray(pl)[:, 0].mean() - p.riquadro[0] for pl in asole]
    dentro_a_sinistra = (np.median(xs) < a) if xs else True
    # dietro: la prima piega dalla parte di fuori che lascia una striscia <= 60 mm
    if dentro_a_sinistra:
        fuori = [x for x in v if x > b + 100 and W - x <= 60.0]
        dietro = min(fuori) if fuori else W
    else:
        fuori = [x for x in v if x < a - 100 and x <= 60.0]
        dietro = max(fuori) if fuori else 0.0
    return a, b, dietro, dentro_a_sinistra, asole


def monta(pdf, uscita, t=SPESSORE, px_mm=PX_MM, montaggio=None):
    """Costruisce l'espositore a scaffale in `uscita` (GLB). Torna (avvisi,
    misure)."""
    from PIL import Image
    from .. import exporters
    letti, s, tagli, pieghe, altre = leggi(pdf)

    # la tavola comune: i pezzi che si montano, uno accanto all'altro, in mm
    # veri; la grafica resa dalla pagina (in scala) alla stessa risoluzione
    resa = _Resa(pdf)
    ordine = [r for r in ("fianco_a", "fianco_b", "schiena", "ripiano", "dekl", "topper")
              if r in letti]
    rese, pezzi, x, alto = [], {}, 0.0, 0.0
    for r in ordine:
        pp, pv = letti[r]
        zp = tuple(v + d for v, d in zip(pp.riquadro, (-5, -5, 5, 5)))
        Gp = F.Griglia(zp, px_mm * s)
        rese.append((resa.rendi(Gp), x))
        zv = tuple(v * s for v in zp)
        pezzi[r] = _sposta(pv, x - zv[0], -zv[1], r)
        alto = max(alto, zv[3] - zv[1])
        x += zv[2] - zv[0] + 10.0
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
            P0 = np.array(punto(0.0, 0.0), float)
            U = np.array(punto(1.0, 0.0), float) - P0
            V = np.array(punto(0.0, 1.0), float) - P0
            mo.pannello(p, masc, scarto, punto, np.cross(U, V), nome)

    # --- la schiena: davanti a z = 0, alta fino alla piega in basso
    sch = pezzi["schiena"]
    hb = _lunghe(sch, "H", 0.7)
    Hc = hb[-1] if hb else sch.altezza                # l'altezza del corpo
    Ws = sch.larghezza
    Xi = Ws / 2.0                                     # la parete di dentro dei fianchi

    def regola_schiena(px, py, r):
        if py > Hc:
            return None                               # l'aletta sotto
        return (lambda lx, ly: (lx - Ws / 2.0, Hc - ly, 0.0),)
    stendi(sch, "schiena", regola_schiena)

    # --- i fianchi
    Zb = -2 * t                                       # il retro: la striscia dietro la schiena
    livelli = None
    profondo = None
    for r in ("fianco_a", "fianco_b"):
        p = pezzi[r]
        a, b, dietro, sx, asole = _fronte(p)
        hp = _lunghe(p, "H", 0.2)
        piede = max(hp)                               # la piega in basso
        doppia = b - a                                # lo spessore del fianco
        faccia = (dietro - b) if sx else (a - dietro)
        profondo = faccia if profondo is None else profondo
        Zf = Zb + faccia                              # lo spigolo davanti
        # destro: la faccia stampata a destra della piega doppia (si legge
        # dritta da destra, il davanti a sinistra)
        d = 1.0 if sx else -1.0
        Xo = Xi + doppia
        if livelli is None:
            livelli = []
            for pl in asole:
                q = np.asarray(pl, float) - (p.riquadro[0], p.riquadro[1])
                ys = q[:, 1]
                # la feritoia: dal lato lungo in alto al fondo
                orizz = [(u[1] + w[1]) / 2 for u, w in zip(q, q[1:])
                         if abs(u[1] - w[1]) < 0.5 and abs(u[0] - w[0]) > 100]
                livelli.append((piede - ys.max(), piede - (min(orizz) if orizz else ys.min())))
            livelli.sort()

        def regola_fianco(px, py, r, a=a, b=b, dietro=dietro, sx=sx, d=d, Zf=Zf,
                          Xo=Xo, piede=piede):
            if py > piede:
                return None                           # l'aletta sotto
            # u: quanto il punto sta dalla piega doppia, verso la faccia
            # stampata (positivo) o verso la parete di dentro (negativo)
            if sx:
                u = (lambda lx: lx - b)
                w = (lambda lx: a - lx)
                oltre, dentro = px > dietro, px < a
                fondo = dietro - b
            else:
                u = (lambda lx: a - lx)
                w = (lambda lx: lx - b)
                oltre, dentro = px < dietro, px > b
                fondo = a - dietro
            if a < px < b:                            # lo spigolo davanti
                return (lambda lx, ly: (d * (Xo + u(lx)), piede - ly, Zf),)
            if dentro:                                # la parete di dentro
                return (lambda lx, ly: (d * Xi, piede - ly, Zf - w(lx)),)
            if oltre:                                 # la striscia sul retro della schiena
                return (lambda lx, ly: (d * (Xo - (u(lx) - fondo)), piede - ly, Zb),)
            return (lambda lx, ly: (d * Xo, piede - ly, Zf - u(lx)),)    # la faccia stampata
        stendi(p, "fianco_%s" % ("destro" if sx else "sinistro"), regola_fianco)
    if not livelli:
        raise ValueError("espositore: nella parete di dentro dei fianchi non trovo le asole")

    # --- i ripiani: il fondo stampato sotto, il pannello girato sopra, la
    # fascetta davanti
    rp = pezzi["ripiano"]
    vr = _lunghe(rp, "V", 0.2)
    larghe = [x for x in vr if 0.1 * rp.larghezza < x < 0.9 * rp.larghezza]
    r0, r1 = min(larghe), max(larghe)
    rc = (r0 + r1) / 2.0
    hr = _lunghe(rp, "H", 0.35)
    salti = [(b - a, a, b) for a, b in zip(hr, hr[1:])]
    grandi = sorted((s_ for s_ in salti if s_[0] > 100), key=lambda s_: s_[1])
    if len(grandi) < 2:
        raise ValueError("espositore: nel ripiano non trovo il fondo e il pannello di sopra")
    (f0, f1), (g0, g1) = grandi[0][1:], grandi[1][1:]
    davanti = [y for y in hr if y < f0]
    fascia = max(((b - a, a, b) for a, b in zip(davanti, davanti[1:])), default=None)
    fondo = f1 - f0
    Zr = fondo                                        # il davanti del fondo; dietro a z = 0
    for k, (Yb, Yt) in enumerate(livelli):
        def regola_rip(px, py, r, Yb=Yb, Yt=Yt):
            if not (r0 - 1 < px < r1 + 1):
                return None                           # le alette nelle asole
            if f0 < py < f1:                          # il fondo, stampato sotto
                return (lambda lx, ly: (lx - rc, Yb, Zr - (ly - f0)),)
            if g0 < py < g1:                          # il pannello girato sopra
                return (lambda lx, ly: (lx - rc, Yt, ly - g0),)
            if fascia and fascia[1] < py < fascia[2]:  # la fascetta col marchio
                h1 = fascia[2]
                return (lambda lx, ly: (lx - rc, Yb + (h1 - ly), Zr + t),)
            return None
        stendi(rp, "ripiano_%d" % (k + 1), regola_rip)

    # --- il dekl: il frontale dello zoccolo
    if "dekl" in pezzi:
        dk = pezzi["dekl"]
        vd, hd = _lunghe(dk, "V", 0.3), _lunghe(dk, "H", 0.5)
        if len(vd) >= 2 and len(hd) >= 2:
            e0, e1, c0, c1 = vd[0], vd[-1], hd[0], hd[-1]
            dc = (e0 + e1) / 2.0
            Zd = Zr + t

            def regola_dekl(px, py, r):
                if py > c1:
                    return None                       # sotto, sul pavimento
                if e0 < px < e1:
                    if py < c0:                       # il bordo in cima, sotto il ripiano
                        return (lambda lx, ly: (lx - dc, c1 - c0, Zd - (c0 - ly)),)
                    return (lambda lx, ly: (lx - dc, c1 - ly, Zd),)
                if px < e0:                           # le orecchie, contro i fianchi
                    return (lambda lx, ly: (e0 - dc, c1 - ly, Zd - (e0 - lx)),)
                return (lambda lx, ly: (e1 - dc, c1 - ly, Zd - (lx - e1)),)
            stendi(dk, "dekl", regola_dekl)

    # --- il topper: dietro la schiena, sporge sopra
    if "topper" in pezzi:
        tp = pezzi["topper"]
        Zt = Zb - t / 2.0
        sotto = 100.0                                 # quanto sta dietro la schiena
        Yt0 = Hc - sotto + tp.altezza

        def regola_topper(px, py, r):
            return (lambda lx, ly: (lx - tp.larghezza / 2.0, Yt0 - ly, Zt),)
        stendi(tp, "topper", regola_topper)

    resa.chiudi()
    V, UV, T, parti = mo.array(_prima())
    if montaggio is not None:
        montaggio["mo"] = mo
    exporters.write_glb_mesh(V, UV, T, tex, uscita, tex_max=4096, parti=parti)
    largo = 2 * (Xi + doppia)
    misure = dict(larghezza=largo, profondita=profondo, altezza=Hc,
                  ripiani=[y for y, _ in livelli], scala=s)
    avvisi = ["espositore a scaffale da un PDF (disegno in scala 1:%g): %.0f x %.0f mm, "
              "alto %.0f%s; %d ripiani a %s mm; cartone %.1f mm"
              % (s, largo, profondo, Hc,
                 " (col topper %.0f)" % (Yt0) if "topper" in pezzi else "",
                 len(livelli), ", ".join("%.0f" % y for y, _ in livelli), t)]
    return avvisi, misure


def _sposta(p, dx, dy, nome):
    d = np.array([dx, dy], float)
    r = p.riquadro
    return F.Pezzo((r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy),
                   tagli=[np.asarray(a, float) + d for a in p.tagli],
                   pieghe=[np.asarray(a, float) + d for a in p.pieghe], nome=nome)


ORDINE = ("schiena", "fianco", "ripiano", "dekl", "topper")


def _prima():
    def prima(p):
        nome = p["nome"]
        return next((i for i, n in enumerate(ORDINE) if nome.startswith(n)), len(ORDINE))
    return prima
