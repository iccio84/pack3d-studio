"""
Le incisioni: i tagli della fustella che stanno DENTRO le facce di un astuccio
chiuso, modellati come sono sul cartone.

Il primo e' il Kinder Choco Fresh T5 "with frontal opening": sul fronte c'e'
una finestra che si apre a strappo. Chi la guarda chiusa, in mano, ne vede i
tagli - due lati e due diagonali, la linguetta che gira sotto il fondo, la
mezzaluna per il dito - e il modello li deve far vedere allo stesso modo: come
SOLCHI nella faccia, che la luce fa leggere, non come righe disegnate sopra la
grafica. La grafica resta quella del file, intera: il taglio sul cartone non
e' stampato.

Quali tagli, lo dice la fustella:

- sono tratti della penna del disegno tecnico (`dieline._technical_pens`) che
  stanno dentro un pannello di una faccia del solido, non sul suo bordo: il
  bordo e' una piega o il contorno;
- un rettangolo chiuso dentro un pannello non e' un taglio, e' il riquadro di
  un'area (scadenza, codice a barre, vernice): lo spegne gia' la pulizia;
- un tratto con le SPUNTE - trattini corti che lo attraversano a intervalli -
  e' il taglio parziale dal rovescio: nella legenda dei disegni Ferrero e'
  proprio la riga con le stanghette. Sta sulla faccia interna del cartone e da
  fuori non si vede: non si incide;
- le spunte stesse non sono tagli.

Il resto si incide: un solco a V largo `LARGHEZZA` e profondo `PROFONDITA`,
mai piu' di meta' dello spessore del cartoncino. Le pareti del solco sono il
cartoncino tagliato, e hanno la tinta della costa (`folding.TAGLIO`).
"""
from __future__ import annotations

import math

import numpy as np

from .dieline import PT2MM

MM = 1.0 / PT2MM          # punti in un millimetro

# Il solco, in mm: quanto e' largo in superficie e quanto scende. Su un
# astuccio da 168 mm, a schermo pieno un millimetro sono cinque pixel: un solco
# di tre decimi si legge come il filo di un taglio, e da vicino e' un taglio.
LARGHEZZA = 0.35
PROFONDITA = 0.22
# Ogni quanto si campiona il solco lungo il taglio, in mm. Piu' fitto della
# larghezza: cosi' la triangolazione non scavalca mai il solco.
PASSO = 0.15
# Una spunta: un tratto piu' corto di cosi' che ne attraversa un altro.
SPUNTA = 2.6 * MM
# Quante spunte fanno di un tratto un taglio dal rovescio.
SPUNTE_MIN = 2
# Due estremi piu' vicini di cosi', in punti, sono lo stesso punto.
CUCI = 0.3
# Quanto dentro il pannello deve stare un tratto per non essere il suo bordo.
DENTRO = 0.6
# Un taglio piu' corto di cosi', in mm, non si incide.
CORTO = 1.0
# Per quanti mm un taglio deve correre accanto a quello dal rovescio per
# essere il bordo di un'apertura a strappo, e quanto lontano da un'apertura
# puo' stare un taglio che le appartiene (la mezzaluna per il dito).
ACCANTO = 10.0
VICINO = 3.0


def _tratti_tecnici(pdf, page_no=0):
    """I sottopercorsi della penna del disegno tecnico: liste di punti, in
    punti PDF col telaio della MediaBox (y dall'alto), come `tracciati`."""
    import pypdfium2 as pdfium
    from . import dieline, tracciati

    segs, larga, alta = tracciati.segmenti(pdf, page_no)
    penne = dieline._technical_pens(segs, larga, alta)
    if not penne:
        return []
    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[page_no]
        pieni, tratti = [], []
        tracciati._cammina(page, pieni, tratti)
    finally:
        doc.close()
    out = []
    for sp, r, st in tratti:
        if st not in penne or r is not None:
            continue            # un rettangolo chiuso e' il riquadro di un'area
        punti = [(float(x), float(y)) for x, y in sp]
        if len(punti) >= 2:
            out.append(punti)
    return out


def _segmenti(percorsi):
    """I tratti come segmenti ((x0, y0), (x1, y1)), senza quelli nulli."""
    out = []
    for p in percorsi:
        for a, b in zip(p, p[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.05:
                out.append((a, b))
    return out


def _dentro_pannello(seg, p):
    """La parte di `seg` dentro il pannello `p`, o None: il bordo non conta.

    Liang-Barsky sul riquadro stretto di DENTRO: un tratto che corre lungo il
    bordo - la piega fra due facce - ne esce tutto; uno che parte dal bordo e
    scende dentro la faccia - il lato della finestra - perde il primo mezzo
    millimetro, che si rimette allungandolo fino al bordo vero.
    """
    (x0, y0), (x1, y1) = seg
    lo = [p.x0 + DENTRO, p.y0 + DENTRO]
    hi = [p.x1 - DENTRO, p.y1 - DENTRO]
    d = (x1 - x0, y1 - y0)
    t0, t1 = 0.0, 1.0
    for k, (o, dk) in enumerate(((x0, d[0]), (y0, d[1]))):
        if abs(dk) < 1e-12:
            if o < lo[k] or o > hi[k]:
                return None
            continue
        a, b = (lo[k] - o) / dk, (hi[k] - o) / dk
        if a > b:
            a, b = b, a
        t0, t1 = max(t0, a), min(t1, b)
        if t0 >= t1:
            return None
    pa = (x0 + d[0] * t0, y0 + d[1] * t0)
    pb = (x0 + d[0] * t1, y0 + d[1] * t1)
    return _al_bordo(pa, d, p, -1 if t0 > 0 else 0), _al_bordo(pb, d, p, 1 if t1 < 1 else 0)


def _al_bordo(q, d, p, verso):
    """`q` spinto lungo `d` fino al bordo vero del pannello, se il segmento ci
    arrivava (verso -1 all'indietro, 1 in avanti, 0 resta dov'e')."""
    if not verso:
        return q
    lung = math.hypot(*d)
    ux, uy = d[0] / lung * verso, d[1] / lung * verso
    passi = []
    for o, u, a, b in ((q[0], ux, p.x0, p.x1), (q[1], uy, p.y0, p.y1)):
        if abs(u) > 1e-9:
            passi.append(((b if u > 0 else a) - o) / u)
    t = min([s for s in passi if s >= 0] or [0.0])
    t = min(t, DENTRO * 1.5)
    return (q[0] + ux * t, q[1] + uy * t)


def _catene(segmenti):
    """I segmenti cuciti in linee: si cuce solo attraverso i punti in cui si
    incontrano due tratti e due soli. Un incrocio a tre - dove il taglio dal
    rovescio raggiunge quello davanti - spezza le linee, cosi' ognuna si
    giudica da se'."""
    nodi, idx = [], {}

    def nodo(q):
        k = (round(q[0] / CUCI), round(q[1] / CUCI))
        for dk in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (1, -1), (-1, 1), (-1, -1)):
            j = idx.get((k[0] + dk[0], k[1] + dk[1]))
            if j is not None and math.hypot(nodi[j][0] - q[0], nodi[j][1] - q[1]) <= CUCI:
                return j
        idx[k] = len(nodi)
        nodi.append(q)
        return len(nodi) - 1

    archi = [(nodo(a), nodo(b)) for a, b in segmenti]
    vicini = {}
    for k, (i, j) in enumerate(archi):
        if i == j:
            continue
        vicini.setdefault(i, []).append((k, j))
        vicini.setdefault(j, []).append((k, i))
    usati = set()
    linee = []

    def segui(i, k, j):
        linea = [nodi[i], nodi[j]]
        usati.add(k)
        while len(vicini.get(j, ())) == 2:
            prossimi = [(kk, jj) for kk, jj in vicini[j] if kk not in usati]
            if not prossimi:
                break
            k, jj = prossimi[0]
            usati.add(k)
            linea.append(nodi[jj])
            j = jj
        return linea

    for i, vv in vicini.items():          # prima dagli estremi e dagli incroci
        if len(vv) != 2:
            for k, j in vv:
                if k not in usati:
                    linee.append(segui(i, k, j))
    for i, vv in vicini.items():          # poi gli anelli chiusi
        for k, j in vv:
            if k not in usati:
                linee.append(segui(i, k, j))
    return linee


def _lunghezza(linea):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(linea, linea[1:]))


def _attraversa(spunta, linea):
    """La spunta taglia la linea vicino alla sua meta', quasi di traverso."""
    (ax, ay), (bx, by) = spunta[0], spunta[-1]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    du = (bx - ax, by - ay)
    ls = math.hypot(*du) or 1.0
    for (px, py), (qx, qy) in zip(linea, linea[1:]):
        dv = (qx - px, qy - py)
        lv = math.hypot(*dv)
        if lv < 1e-9:
            continue
        t = max(0.0, min(1.0, ((mx - px) * dv[0] + (my - py) * dv[1]) / lv ** 2))
        cx, cy = px + dv[0] * t, py + dv[1] * t
        if math.hypot(mx - cx, my - cy) > ls * 0.4:
            continue
        coseno = abs(du[0] * dv[0] + du[1] * dv[1]) / (ls * lv)
        if coseno < 0.5:                  # piu' di 60 gradi
            return True
    return False


def tagli(pdf, panels, facce, page_no=0):
    """{faccia: [linea, ...]} i tagli d'apertura da incidere, in punti PDF.

    `panels` sono i pannelli dell'astuccio risolto, `facce` i nomi di quelli
    che sul solido sono facce (non alette ne' lembi incollati).

    Si incide solo un'APERTURA A STRAPPO, e la si riconosce dalla sua firma:
    un taglio sul lato stampato con accanto, a pochi millimetri, il taglio dal
    rovescio con le spunte. E' quello che fa staccare il cartone pulito fra i
    due. Con lui vanno i tagli che lo continuano - la linguetta, anche quando
    gira su un'altra faccia - e quelli che gli stanno a un passo, come la
    mezzaluna per il dito. Un altro tratto dentro una faccia - il riquadro di
    un'area, una piega di servizio, un taglio di cui la fustella non dice a
    cosa serve - resta come oggi: senza la firma non si sa cos'e', e un solco
    sbagliato e' peggio di nessun solco.

    Ogni linea esce tagliata alla sua faccia: la linguetta che gira sotto il
    fondo esce in due pezzi, uno sul fronte e uno sul fondo.
    """
    percorsi = _tratti_tecnici(pdf, page_no)
    if not percorsi:
        return {}
    quadri = [panels[n] for n in facce if n in panels]
    if not quadri:
        return {}
    # i tratti che stanno dentro almeno una faccia, interi: le linee si cuciono
    # sul foglio, attraverso le pieghe, e si tagliano alle facce solo alla fine
    segmenti = [sg for sg in _segmenti(percorsi)
                if any(_dentro_pannello(sg, p) is not None for p in quadri)]
    if not segmenti:
        return {}
    linee = _catene(segmenti)
    corta = [len(l) == 2 and _lunghezza(l) < SPUNTA for l in linee]
    spunte = [l for l, c in zip(linee, corta) if c]
    resto = [l for l, c in zip(linee, corta) if not c]
    rovescio = [l for l in resto
                if sum(1 for sp in spunte if _attraversa(sp, l)) >= SPUNTE_MIN]
    visibili = [l for l in resto if not any(l is r for r in rovescio)]
    if not rovescio or not visibili:
        return {}
    gruppi = _gruppi(visibili)
    aperture = [g for g in gruppi if any(_accanto(l, rovescio) for l in g)]
    if not aperture:
        return {}
    vicini = [g for g in gruppi if not any(g is a for a in aperture)
              and any(_distanza_gruppi(g, a) <= VICINO * MM for a in aperture)]
    scelte = [l for g in aperture + vicini for l in g]
    out = {}
    for nome in facce:
        p = panels.get(nome)
        if p is None:
            continue
        pezzi = [d for l in scelte for a, b in zip(l, l[1:])
                 for d in [_dentro_pannello((a, b), p)] if d is not None]
        linee_f = [l for l in _catene(pezzi) if _lunghezza(l) * PT2MM >= CORTO]
        if linee_f:
            out[nome] = linee_f
    return out


def _distanza_punto(q, linea):
    best = float("inf")
    for (px, py), (qx, qy) in zip(linea, linea[1:]):
        dx, dy = qx - px, qy - py
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((q[0] - px) * dx + (q[1] - py) * dy) / l2))
        best = min(best, math.hypot(q[0] - px - dx * t, q[1] - py - dy * t))
    return best


def _campioni(linea, passo):
    """Punti lungo la linea, uno ogni `passo` punti PDF."""
    out = [linea[0]]
    for (px, py), (qx, qy) in zip(linea, linea[1:]):
        lung = math.hypot(qx - px, qy - py)
        n = max(1, int(lung / passo))
        out += [(px + (qx - px) * k / n, py + (qy - py) * k / n) for k in range(1, n + 1)]
    return out


def _accanto(linea, rovescio):
    """La linea corre accanto a un taglio dal rovescio, fra 1,5 e 5 mm, per
    almeno ACCANTO mm della sua lunghezza."""
    passo = 1.0 * MM
    for r in rovescio:
        n = sum(1 for q in _campioni(linea, passo)
                if 1.5 * MM <= _distanza_punto(q, r) <= 5.0 * MM)
        if n * 1.0 >= ACCANTO:
            return True
    return False


def _distanza_gruppi(a, b):
    return min(_distanza_punto(q, lb) for la in a for q in _campioni(la, 1.0 * MM)
               for lb in b)


def _gruppi(linee):
    """Le linee raccolte per estremi in comune: il lato di una finestra e il
    lato della sua linguetta si toccano nel collo, e vanno giudicati insieme."""
    gruppo = list(range(len(linee)))

    def radice(i):
        while gruppo[i] != i:
            gruppo[i] = gruppo[gruppo[i]]
            i = gruppo[i]
        return i

    estremi = [(l[0], l[-1]) for l in linee]
    for i in range(len(linee)):
        for j in range(i + 1, len(linee)):
            if any(math.hypot(a[0] - b[0], a[1] - b[1]) <= CUCI
                   for a in estremi[i] for b in estremi[j]):
                gruppo[radice(i)] = radice(j)
    out = {}
    for i, l in enumerate(linee):
        out.setdefault(radice(i), []).append(l)
    return list(out.values())


# --------------------------------------------------------------------------- #
# il solco nella faccia
# --------------------------------------------------------------------------- #
# Le rotazioni con cui `artwork.gira_sulla_grafica` gira le texture
# (Image.ROTATE_*, antiorarie): dove finisce, nella texture girata, un punto
# (u, v) di quella presa dal foglio.
_GIRO_UV = {
    0: lambda u, v: (u, v),
    90: lambda u, v: (v, 1.0 - u),
    180: lambda u, v: (1.0 - u, 1.0 - v),
    270: lambda u, v: (1.0 - v, u),
}


def _uv_faccia(linea, p, gradi):
    """La linea dal foglio alle coordinate della texture della faccia."""
    gira = _GIRO_UV[int(gradi) % 360]
    w, h = (p.x1 - p.x0) or 1.0, (p.y1 - p.y0) or 1.0
    return [gira((x - p.x0) / w, (y - p.y0) / h) for x, y in linea]


def _ricampiona(linea, passo):
    """(punti, tangenti) lungo una linea in mm, uno ogni `passo` mm."""
    pts, tan = [], []
    for k, (a, b) in enumerate(zip(linea, linea[1:])):
        d = np.subtract(b, a)
        lung = float(np.hypot(*d))
        if lung < 1e-9:
            continue
        t = d / lung
        n = max(1, int(math.ceil(lung / passo)))
        for i in range(0 if not pts else 1, n + 1):
            pts.append(np.add(a, d * (i / n)))
            tan.append(t)
    return pts, tan


def _distanze(P, linee):
    """La distanza di ogni punto di P dalla linea piu' vicina, vettoriale."""
    best = np.full(len(P), np.inf)
    for linea in linee:
        A = np.asarray(linea[:-1], float)
        B = np.asarray(linea[1:], float)
        D = B - A
        L2 = np.maximum((D ** 2).sum(1), 1e-12)
        for a, d, l2 in zip(A, D, L2):
            t = np.clip(((P - a) @ d) / l2, 0.0, 1.0)
            q = a + t[:, None] * d
            best = np.minimum(best, np.hypot(*(P - q).T))
    return best


def maglia_incisa(quad, linee_uv, profondita=PROFONDITA, larghezza=LARGHEZZA):
    """La faccia `quad` col solco delle linee: (superficie, solco).

    `linee_uv` sono nelle coordinate della texture, [0, 1] x [0, 1]. Ognuna
    delle due parti e' (V, N, UV, T): vertici 3D, normali, coordinate texture
    e triangoli. La superficie resta nel piano della faccia, con la sua
    texture; il solco e' a V, scende di `profondita` sulla linea e risale a
    zero a `larghezza / 2` di distanza.

    La triangolazione e' di Delaunay sui punti del solco - la linea e i suoi
    due bordi, ogni PASSO mm - piu' gli angoli della faccia: i campioni lungo
    il solco sono piu' fitti della sua larghezza, e un triangolo che lo
    scavalcasse avrebbe nel cerchio circoscritto i punti della linea, quindi
    Delaunay non lo fa.
    """
    from scipy.spatial import Delaunay

    q = np.asarray(quad, float)
    es, et = q[1] - q[0], q[3] - q[0]
    W, H = float(np.linalg.norm(es)), float(np.linalg.norm(et))
    es, et = es / W, et / H
    n = -np.cross(q[1] - q[0], q[3] - q[0])
    n /= np.linalg.norm(n)
    a = larghezza / 2.0
    linee = [[(u * W, v * H) for u, v in l] for l in linee_uv]
    punti = [(0.0, 0.0), (W, 0.0), (W, H), (0.0, H)]
    for linea in linee:
        P, T = _ricampiona(linea, PASSO)
        for k, (p, t) in enumerate(zip(P, T)):
            nn = np.array([-t[1], t[0]])
            punti += [tuple(p), tuple(p + nn * a), tuple(p - nn * a)]
            if k in (0, len(P) - 1):          # la punta: il solco si chiude
                verso = -t if k == 0 else t
                punti.append(tuple(p + verso * a))
    S = np.clip(np.array(punti, float), [0.0, 0.0], [W, H])
    S = np.unique(np.round(S / 0.002).astype(np.int64), axis=0) * 0.002
    prof = profondita * np.clip(1.0 - _distanze(S, linee) / a, 0.0, 1.0)
    # I bordi del solco stanno a fior di faccia: l'arrotondamento dei punti li
    # sposta di un millesimo e gli dava una profondita' di qualche micron, e
    # allora ogni triangolo grande che li tocca - mezza faccia - finiva nel
    # solco, grigio e storto.
    prof[prof < 0.2 * profondita] = 0.0
    tri = Delaunay(S).simplices
    V = q[0] + S[:, :1] * es + S[:, 1:] * et - prof[:, None] * n
    UV = np.column_stack([S[:, 0] / W, S[:, 1] / H])
    # il verso dei triangoli: la normale fuori dalla faccia
    a3, b3, c3 = V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]]
    rovesci = (np.cross(b3 - a3, c3 - a3) @ n) < 0
    tri[rovesci] = tri[rovesci][:, [0, 2, 1]]
    nel_solco = (prof[tri] > 1e-6).any(1)

    def parte(T, piatta):
        if not len(T):
            return None
        if piatta:
            usati, inv = np.unique(T, return_inverse=True)
            N = np.tile(n, (len(usati), 1))
            return V[usati], N, UV[usati], inv.reshape(-1, 3)
        # le pareti del solco a facce piatte: un vertice per triangolo
        Vt = V[T].reshape(-1, 3)
        UVt = UV[T].reshape(-1, 2)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        Nf = np.cross(b - a, c - a)
        Nf /= np.maximum(np.linalg.norm(Nf, axis=1, keepdims=True), 1e-12)
        return Vt, np.repeat(Nf, 3, axis=0), UVt, np.arange(len(Vt)).reshape(-1, 3)

    return parte(tri[~nel_solco], True), parte(tri[nel_solco], False)


def incidi(faces, tagli_faccia, panels, girate=None, spessore=None):
    """Mette il solco nelle facce che hanno tagli d'apertura. In place.

    `tagli_faccia` e' quello che torna `tagli`; `girate` le facce girate da
    `artwork.gira_sulla_grafica` e di quanto. Si chiama sulle facce finite -
    dopo `folding.gira_facce` - perche' il solco segua il quad cosi' com'e'.
    La faccia tiene il suo quad, che serve a tutto il resto (verifiche,
    guscio, viste): l'esportatore, se c'e' `maglia`, scrive quella.
    """
    girate = girate or {}
    prof = PROFONDITA if not spessore else min(PROFONDITA, 0.5 * spessore)
    n = 0
    for f in faces:
        linee = tagli_faccia.get(f["name"])
        p = panels.get(f["name"])
        if not linee or p is None:
            continue
        uv = [_uv_faccia(l, p, girate.get(f["name"], 0)) for l in linee]
        f["maglia"] = maglia_incisa(f["quad"], uv, prof)
        n += len(linee)
    return n
