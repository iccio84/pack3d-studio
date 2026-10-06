"""
L'apertura a strappo APERTA: la finestra di un astuccio sollevata sulla sua
cerniera, e la scatola appoggiata sulla faccia opposta.

Chiuso, l'astuccio con l'apertura a strappo mostra i tagli come solchi
(`incisioni`). Aperto, i tagli diventano bordi: la finestra - con la
linguetta che gira sotto il fondo - ruota sulla piega che la tiene attaccata,
e alla scatola resta il buco. Di quanti gradi lo dice chi lo chiede; tutto il
resto lo dice la fustella:

- la CERNIERA e' la piega su cui finiscono i due capi del contorno dei tagli
  d'apertura. Il contorno parte da una piega, gira attorno alla finestra e
  alla linguetta e torna sulla stessa piega: fra i due capi la finestra resta
  attaccata. Sul Kinder Choco Fresh T5 e' la piega fra fronte e cielo;
- il taglio sul lato stampato e quello dal rovescio non coincidono, corrono a
  3 mm l'uno dall'altro, e strappando il cartoncino si SFOGLIA fra i due. La
  scatola tiene lo strato di dentro fino al taglio dal rovescio, la finestra
  lo strato di fuori fino al taglio davanti: attorno al buco resta una
  cornice di cartoncino sfogliato, e la finestra ha la stessa cornice da
  sotto. Il taglio dal rovescio che si ferma poco prima della cerniera (sul
  Choco Fresh 2 mm) si allunga fino alla piega;
- un taglio vicino che si attacca al contorno con i due capi chiude con lui
  un pezzo a parte: la mezzaluna per il dito, che con la punta della
  linguetta fa una lunetta. E' il pezzo che si spinge dentro per prendere la
  linguetta: aperta la scatola, al suo posto c'e' il buco.

Ogni faccia attraversata dal contorno si triangola una volta sola, con i
bordi campionati fitti, e ogni triangolo si assegna a una ZONA: la scatola
intera (A), la finestra intera (B), la striscia sfogliata (C, o D se il
rovescio corre fuori dalla finestra), la lunetta (R). Dalla zona viene quale pezzo ha cartoncino e a che profondita': la
superficie stampata, il rovescio, la cornice sfogliata a meta' spessore, e i
bordi del taglio dove due zone si toccano. La scatola aperta appoggia sulla
faccia opposta a quella della cerniera: la finestra guarda in alto, la
cerniera sta dietro e la linguetta verso chi guarda.
"""
from __future__ import annotations

import math

import numpy as np

from . import incisioni
from .dieline import PT2MM

# Ogni quanto si campionano i bordi delle zone, in mm: molto piu' fitto della
# striscia sfogliata e della lunetta, cosi' Delaunay non fa triangoli che
# scavalcano un bordo.
PASSO = 0.25
# Quanto lontano dal contorno puo' stare, in punti, il capo di un taglio che
# gli si attacca: la mezzaluna del Choco Fresh tocca la linguetta a 0,15 mm.
ATTACCO = 1.5
# Fin dove si allunga il taglio dal rovescio che si ferma prima della
# cerniera, in mm.
ALLUNGA = 5.0
# Quanto vicini alla stessa piega devono stare i due capi del contorno, in
# punti, perche' quella piega sia la cerniera.
SULLA_PIEGA = 1.5
# Il massimo che si apre: oltre, la finestra si ripiega sul cielo.
GRADI_MAX = 180

# le zone: chi ha cartoncino e fra quali profondita', in frazioni dello
# spessore (0 la faccia stampata, 1 il rovescio). C e' la striscia fra i due
# tagli quando il rovescio corre dentro la finestra, come sul Choco Fresh; D
# la stessa striscia quando corre fuori, e gli strati si scambiano.
SCATOLA = {"A": (0.0, 1.0), "C": (0.5, 1.0), "D": (0.0, 0.5)}
FINESTRA = {"B": (0.0, 1.0), "C": (0.0, 0.5), "D": (0.5, 1.0)}


# --------------------------------------------------------------------------- #
# il contorno, la cerniera, lo strato di dentro, le lunette - sul foglio
# --------------------------------------------------------------------------- #
def _vicini(a, b, tol):
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol


def _cuci(linee, tol=incisioni.CUCI):
    """Le linee cucite capo a capo in una linea aperta, o None se non fanno
    una catena sola con due capi liberi."""
    linee = [list(l) for l in linee if len(l) >= 2]
    liberi = []
    for i, l in enumerate(linee):
        for capo in (0, -1):
            if not any(_vicini(l[capo], m[e], tol) for j, m in enumerate(linee)
                       if j != i for e in (0, -1)):
                liberi.append((i, capo))
    if len(liberi) != 2:
        return None
    i, capo = liberi[0]
    catena = linee[i] if capo == 0 else linee[i][::-1]
    usate = {i}
    while len(usate) < len(linee):
        for j, m in enumerate(linee):
            if j in usate:
                continue
            if _vicini(catena[-1], m[0], tol):
                catena += m[1:]
                break
            if _vicini(catena[-1], m[-1], tol):
                catena += m[::-1][1:]
                break
        else:
            return None
        usate.add(j)
    return catena


def _sul_segmento(q, a, b, tol):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / l2))
    return math.hypot(q[0] - a[0] - dx * t, q[1] - a[1] - dy * t) <= tol


def _lati(p):
    """I quattro lati del pannello: (a, b, verso fuori dal pannello)."""
    return (((p.x0, p.y0), (p.x1, p.y0), (0.0, -1.0)),
            ((p.x0, p.y1), (p.x1, p.y1), (0.0, 1.0)),
            ((p.x0, p.y0), (p.x0, p.y1), (-1.0, 0.0)),
            ((p.x1, p.y0), (p.x1, p.y1), (1.0, 0.0)))


def _dentro_pannello(q, p, margine=0.0):
    return (p.x0 - margine <= q[0] <= p.x1 + margine
            and p.y0 - margine <= q[1] <= p.y1 + margine)


def _cerniera(catena, panels, facce):
    """(faccia, (a, b), lato, faccia oltre la piega): la piega su cui
    finiscono i due capi del contorno - un lato della faccia della finestra
    che un'altra faccia ha in comune - o None. `lato` e' il lato intero,
    `(a, b)` i due capi."""
    a, b = catena[0], catena[-1]
    # la faccia della finestra e' quella in cui il contorno entra dal capo
    m = ((catena[0][0] + catena[1][0]) / 2.0, (catena[0][1] + catena[1][1]) / 2.0)
    for nome in facce:
        p = panels.get(nome)
        if p is None or not _dentro_pannello(m, p, 0.5):
            continue
        for u, v, (ox, oy) in _lati(p):
            if not (_sul_segmento(a, u, v, SULLA_PIEGA)
                    and _sul_segmento(b, u, v, SULLA_PIEGA)):
                continue
            # una piega e non un bordo libero: appena fuori dal lato, fra i
            # due capi, comincia un'altra faccia
            fuori = ((a[0] + b[0]) / 2.0 + 2.0 * ox, (a[1] + b[1]) / 2.0 + 2.0 * oy)
            oltre = [n for n in facce if n != nome and n in panels
                     and _dentro_pannello(fuori, panels[n])]
            if oltre:
                return nome, (a, b), (u, v), oltre[0]
    return None


def _proietta(q, catena):
    """(posizione lungo la catena, punto, distanza): il punto della catena
    piu' vicino a `q`; la posizione e' indice del segmento + frazione."""
    best = (None, None, float("inf"))
    for k, (a, b) in enumerate(zip(catena, catena[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / l2))
        c = (a[0] + dx * t, a[1] + dy * t)
        d = math.hypot(q[0] - c[0], q[1] - c[1])
        if d < best[2]:
            best = (k + t, c, d)
    return best


def _tratto(catena, s0, s1):
    """La catena fra le posizioni s0 e s1 (s0 < s1), coi capi interpolati."""
    def punto(s):
        k = min(int(s), len(catena) - 2)
        t = s - k
        a, b = catena[k], catena[k + 1]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    dentro = [catena[k] for k in range(int(math.floor(s0)) + 1, int(math.ceil(s1)))
              if s0 < k < s1]
    return [punto(s0)] + dentro + [punto(s1)]


def _allunga(r, piega):
    """Il capo libero del taglio dal rovescio portato sulla piega, lungo il
    suo ultimo tratto, se ci arriva entro ALLUNGA mm; altrimenti None."""
    (ax, ay), (bx, by) = r[-2], r[-1]
    (ux, uy), (vx, vy) = piega
    dx, dy = bx - ax, by - ay
    ex, ey = vx - ux, vy - uy
    den = dx * ey - dy * ex
    if abs(den) < 1e-12:
        return None
    t = ((ux - bx) * ey - (uy - by) * ex) / den
    if t < 0 or math.hypot(dx * t, dy * t) * PT2MM > ALLUNGA:
        return None
    return (bx + dx * t, by + dy * t)


def _strato_di_dentro(catena, rovescio, piega):
    """Il contorno dello strato di dentro: dove accanto al taglio davanti corre
    quello dal rovescio, dalla piega fino a dove i due si incontrano, il
    contorno passa sul rovescio. (catena, quanti tagli dal rovescio usati)."""
    dentro, usati = list(catena), 0
    for r in rovescio:
        r = list(r)
        s0, _c0, d0 = _proietta(r[0], dentro)
        s1, _c1, d1 = _proietta(r[-1], dentro)
        # un capo sul contorno - dove i due tagli si incontrano - l'altro libero
        if d0 <= incisioni.CUCI and d1 > incisioni.CUCI:
            s, rk = s0, r
        elif d1 <= incisioni.CUCI and d0 > incisioni.CUCI:
            s, rk = s1, r[::-1]
        else:
            continue
        capo = _allunga(rk, piega)
        if capo is None:
            continue
        # da che parte della catena c'e' la piega che il rovescio raggiunge
        if _vicini(capo, dentro[0], math.hypot(*np.subtract(capo, dentro[-1]))):
            k = int(math.ceil(s - 1e-9))
            dentro = [capo] + rk[::-1] + dentro[k + 1:] if k < len(dentro) else None
        else:
            k = int(math.floor(s + 1e-9))
            dentro = dentro[:k + 1] + rk + [capo]
        if dentro is None:
            return list(catena), 0
        usati += 1
    return dentro, usati


def _lunette(catena, vicini):
    """I pezzi che un taglio vicino chiude col contorno, attaccandoglisi coi
    due capi: [poligono in punti PDF]. E i tagli vicini che restano liberi."""
    pezzi, liberi = [], []
    for g in vicini:
        for l in g:
            s0, _c0, d0 = _proietta(l[0], catena)
            s1, _c1, d1 = _proietta(l[-1], catena)
            if d0 > ATTACCO or d1 > ATTACCO or abs(s1 - s0) < 1e-6:
                liberi.append(l)
                continue
            if s0 < s1:
                pezzi.append(list(l) + _tratto(catena, s0, s1)[::-1])
            else:
                pezzi.append(list(l) + _tratto(catena, s1, s0))
    return pezzi, liberi


# --------------------------------------------------------------------------- #
# geometria piana
# --------------------------------------------------------------------------- #
def _dentro_poligono(P, poli):
    """Vero per ogni punto di P (N x 2) dentro il poligono chiuso `poli`."""
    x, y = P[:, 0], P[:, 1]
    dentro = np.zeros(len(P), bool)
    q = np.asarray(poli, float)
    for (x0, y0), (x1, y1) in zip(q, np.roll(q, -1, axis=0)):
        if y0 == y1:
            continue
        passa = (y0 > y) != (y1 > y)
        xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
        dentro ^= passa & (x < xi)
    return dentro


def _liang(a, b, W, H):
    """Il segmento a-b dentro il rettangolo [0, W] x [0, H], o None."""
    d = (b[0] - a[0], b[1] - a[1])
    t0, t1 = 0.0, 1.0
    for o, dk, hi in ((a[0], d[0], W), (a[1], d[1], H)):
        if abs(dk) < 1e-12:
            if o < -1e-9 or o > hi + 1e-9:
                return None
            continue
        u, v = (0.0 - o) / dk, (hi - o) / dk
        if u > v:
            u, v = v, u
        t0, t1 = max(t0, u), min(t1, v)
        if t0 > t1:
            return None
    pa = (a[0] + d[0] * t0, a[1] + d[1] * t0)
    pb = (a[0] + d[0] * t1, a[1] + d[1] * t1)
    if math.hypot(pb[0] - pa[0], pb[1] - pa[1]) < 1e-9:
        return None
    return pa, pb


def _campioni_dentro(poli, W, H, passo=PASSO):
    """Punti lungo il bordo del poligono chiuso, dentro il rettangolo: ogni
    `passo` mm, coi punti in cui il bordo entra ed esce."""
    q = list(map(tuple, poli)) + [tuple(poli[0])]
    out = []
    for a, b in zip(q, q[1:]):
        c = _liang(a, b, W, H)
        if c is None:
            continue
        (x0, y0), (x1, y1) = c
        n = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / passo)))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)]
    return out


def _meno(a, b):
    """L'intervallo a meno l'intervallo b: [intervalli]."""
    if a is None:
        return []
    if b is None:
        return [a]
    out = []
    if b[0] > a[0]:
        out.append((a[0], min(a[1], b[0])))
    if b[1] < a[1]:
        out.append((max(a[0], b[1]), a[1]))
    return [(x, y) for x, y in out if y - x > 1e-9]


def _orienta(V, T, verso):
    """I triangoli col verso giusto: la normale lungo `verso` (uno per
    triangolo o uno per tutti)."""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    rovesci = (np.cross(b - a, c - a) * np.broadcast_to(verso, a.shape)).sum(1) < 0
    T = T.copy()
    T[rovesci] = T[rovesci][:, [0, 2, 1]]
    return T


def _piatta(V, T, N, UV=None):
    """Una maglia a facce piatte: un vertice per angolo di triangolo."""
    Vt = V[T].reshape(-1, 3)
    UVt = (UV[T].reshape(-1, 2) if UV is not None else np.zeros((len(Vt), 2)))
    Nt = np.repeat(np.broadcast_to(N, (len(T), 3)), 3, axis=0)
    return Vt, Nt, UVt, np.arange(len(Vt)).reshape(-1, 3)


def _unisci(parti):
    """Piu' maglie (V, N, UV, T) in una sola, o None."""
    parti = [p for p in parti if p is not None and len(p[3])]
    if not parti:
        return None
    V, N, UV, T, base = [], [], [], [], 0
    for v, n, uv, t in parti:
        V.append(np.asarray(v, float))
        N.append(np.asarray(n, float))
        UV.append(np.asarray(uv, float))
        T.append(np.asarray(t) + base)
        base += len(v)
    return np.vstack(V), np.vstack(N), np.vstack(UV), np.vstack(T)


def _ruota(maglia, R, centro=None):
    if maglia is None:
        return None
    V, N, UV, T = maglia
    c = np.zeros(3) if centro is None else np.asarray(centro, float)
    return c + (np.asarray(V) - c) @ R.T, np.asarray(N) @ R.T, UV, T


def _rodrigues(k, theta):
    k = np.asarray(k, float) / np.linalg.norm(k)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(theta) * K + (1 - math.cos(theta)) * (K @ K)


# --------------------------------------------------------------------------- #
# una faccia aperta
# --------------------------------------------------------------------------- #
def _apri_faccia(quad, p, giro, P, Pin, lunette, spessore):
    """Una faccia attraversata dal contorno, divisa per zone.

    Torna {pezzo: {materiale: maglia}}, pezzo "scatola" o "finestra",
    materiale "stampa" (la texture della faccia), "interno" o "taglio"; le
    maglie sono gia' nello spazio del modello, la finestra ancora chiusa.
    """
    from scipy.spatial import Delaunay
    from .folding import _normale

    q = np.asarray(quad, float)
    e1, e2 = q[1] - q[0], q[3] - q[0]
    W, H = float(np.linalg.norm(e1)), float(np.linalg.norm(e2))
    n = _normale(q)

    def mm(punti):
        uv = np.asarray(incisioni._uv_faccia(punti, p, giro), float)
        return uv * [W, H]

    Pm, Pinm = mm(P), mm(Pin)
    Rm = [mm(r) for r in lunette]
    punti = [(0.0, 0.0), (W, 0.0), (W, H), (0.0, H)]
    for poli in [Pm, Pinm] + Rm:
        punti += _campioni_dentro(poli, W, H)
    S = np.unique(np.round(np.array(punti) / 0.002).astype(np.int64), axis=0) * 0.002
    S = np.clip(S, [0.0, 0.0], [W, H])
    tri = Delaunay(S).simplices
    C = S[tri].mean(1)
    zona = np.full(len(tri), "A")
    inR = np.zeros(len(tri), bool)
    for r in Rm:
        inR |= _dentro_poligono(C, r)
    inP, inPin = _dentro_poligono(C, Pm), _dentro_poligono(C, Pinm)
    zona[inR] = "R"
    zona[inP & ~inPin] = "C"
    zona[inPin & ~inP] = "D"
    zona[inP & inPin] = "B"

    def al3d(P2, prof):
        return (q[0] + P2[:, :1] / W * e1 + P2[:, 1:] / H * e2
                - (prof * spessore) * n)

    UV = S / [W, H]
    # gli spigoli fra due zone diverse: li' stanno i bordi del taglio
    lati = {}
    for t, (a, b, c) in enumerate(tri):
        for u, v in ((a, b), (b, c), (c, a)):
            lati.setdefault((min(u, v), max(u, v)), []).append(t)
    confini = [(u, v, ts) for (u, v), ts in lati.items()
               if len(ts) == 2 and zona[ts[0]] != zona[ts[1]]]
    out = {"scatola": {}, "finestra": {}}
    for pezzo, strati in (("scatola", SCATOLA), ("finestra", FINESTRA)):
        maglie = {"stampa": [], "interno": [], "taglio": []}
        # le superfici: sopra lo strato piu' esterno, sotto quello piu' interno
        for z, (lo, hi) in strati.items():
            T = tri[zona == z]
            if not len(T):
                continue
            for prof, verso, mat in ((lo, n, "stampa" if lo == 0 else "taglio"),
                                     (hi, -n, "interno" if hi == 1 else "taglio")):
                V = al3d(S, prof)
                Tz = _orienta(V, T, verso)
                usati, inv = np.unique(Tz, return_inverse=True)
                maglie[mat].append((V[usati], np.tile(verso, (len(usati), 1)),
                                    UV[usati], inv.reshape(-1, 3)))
        # i bordi del taglio: dove due zone si toccano, per ogni profondita'
        # in cui da una parte c'e' cartoncino e dall'altra no
        pareti = []
        for u, v, ts in confini:
            for x, y in ((ts[0], ts[1]), (ts[1], ts[0])):
                # cartoncino dalla parte di x che dalla parte di y manca
                for lo, hi in _meno(strati.get(zona[x]), strati.get(zona[y])):
                    d = S[v] - S[u]
                    perp = np.array([-d[1], d[0]])
                    if perp @ (C[y] - S[u]) < 0:
                        perp = -perp
                    verso = perp[0] / W * e1 + perp[1] / H * e2
                    verso /= np.linalg.norm(verso)
                    A = al3d(S[[u, v]], lo)
                    B = al3d(S[[u, v]], hi)
                    V = np.array([A[0], A[1], B[1], B[0]])
                    T = _orienta(V, np.array([[0, 1, 2], [0, 2, 3]]), verso)
                    pareti.append(_piatta(V, T, verso))
        maglie["taglio"] += pareti
        for mat, lista in maglie.items():
            m = _unisci(lista)
            if m is not None:
                out[pezzo][mat] = m
    return out


# --------------------------------------------------------------------------- #
# l'astuccio aperto
# --------------------------------------------------------------------------- #
def apri(pdf, panels, facce, faces, gradi, girate=None, spessore=None):
    """L'astuccio con la finestra aperta di `gradi`, appoggiato sulla faccia
    opposta alla cerniera. In place su `faces`, che devono essere le facce
    finite - dopo `folding.gira_facce` - col loro guscio.

    Torna None, senza toccare niente, se l'astuccio non ha un'apertura a
    strappo con la sua cerniera; altrimenti un dizionario con quello che si
    e' fatto, per gli avvisi.
    """
    from PIL import Image
    from .folding import INTERNO, SPESSORE_CRT, TAGLIO, _normale

    gradi = float(gradi)
    if not 0 < gradi <= GRADI_MAX:
        raise ValueError("l'apertura va da 1 a %d gradi" % GRADI_MAX)
    spessore = float(spessore or SPESSORE_CRT)
    girate = girate or {}
    trovata = incisioni.firma(pdf, panels, facce)
    if trovata is None:
        return None
    aperture, vicini, rovescio = trovata
    if len(aperture) != 1:
        return None
    catena = _cuci(aperture[0])
    if catena is None:
        return None
    cerniera = _cerniera(catena, panels, facce)
    if cerniera is None:
        return None
    nome_c, piega, lato, oltre = cerniera
    p_c = panels[nome_c]
    dentro, sfogliati = _strato_di_dentro(catena, rovescio, lato)
    lunette, liberi = _lunette(catena, vicini)
    # i poligoni chiusi: il contorno torna lungo la cerniera
    P, Pin = catena, dentro

    per_nome = {f["name"]: f for f in faces}
    if nome_c not in per_nome:
        return None
    toccate = []
    for nome in facce:
        p = panels.get(nome)
        f = per_nome.get(nome)
        if p is None or f is None:
            continue
        if not any(_dentro_pannello(q, p, -0.5) for poli in [P] + lunette for q in poli):
            continue
        toccate.append(nome)
    if nome_c not in toccate:
        return None

    pezzi = {nome: _apri_faccia(per_nome[nome]["quad"], panels[nome],
                                girate.get(nome, 0), P, Pin, lunette, spessore)
             for nome in toccate}

    # la cerniera nel modello, sulla faccia stampata
    qc = np.asarray(per_nome[nome_c]["quad"], float)
    e1, e2 = qc[1] - qc[0], qc[3] - qc[0]
    uv = np.asarray(incisioni._uv_faccia(list(piega), p_c, girate.get(nome_c, 0)), float)
    Ha = qc[0] + uv[0, 0] * e1 + uv[0, 1] * e2
    Hb = qc[0] + uv[1, 0] * e1 + uv[1, 1] * e2
    asse = (Hb - Ha) / np.linalg.norm(Hb - Ha)
    n_c = _normale(qc)
    # il baricentro della finestra chiusa, per il verso
    stampa_f = _unisci([pezzi[n]["finestra"].get("stampa") for n in toccate])
    if stampa_f is None:
        return None
    g = stampa_f[0].mean(0)
    r = (g - Ha) - ((g - Ha) @ asse) * asse
    theta = math.radians(gradi)
    if np.cross(asse, r) @ n_c < 0:
        theta = -theta
    Rf = _rodrigues(asse, theta)

    # la posa: la faccia della cerniera guarda in alto (+y), e dalla cerniera
    # la finestra viene verso chi guarda (+z)
    ez = r / np.linalg.norm(r)
    ey = n_c
    ex = np.cross(ey, ez)
    Rp = np.array([ex, ey, ez])

    # tutto calcolato: da qui si cambia `faces`
    tinte = {"interno": Image.new("RGB", (4, 4), INTERNO),
             "taglio": Image.new("RGB", (4, 4), TAGLIO)}
    coste = []
    for nome in toccate:
        parti = pezzi[nome]
        fin = {m: _ruota(x, Rf, Ha) for m, x in parti["finestra"].items()}
        f = per_nome[nome]
        f["maglia"] = (_unisci([parti["scatola"].get("stampa"), fin.get("stampa")]), None)
        interno = _unisci([parti["scatola"].get("interno"), fin.get("interno")])
        fi = per_nome.get(nome + " interno")
        if fi is not None:
            if interno is None:
                faces.remove(fi)
            else:
                fi["maglia"] = (interno, None)
                fi["tex"] = tinte["interno"]
        elif interno is not None:
            faces.append({"name": nome + " interno", "quad": f["quad"],
                          "uv": f.get("uv"), "tex": tinte["interno"],
                          "maglia": (interno, None)})
        coste += [parti["scatola"].get("taglio"), fin.get("taglio")]
    taglio = _unisci(coste)
    if taglio is not None:
        faces.append({"name": "apertura taglio", "quad": per_nome[nome_c]["quad"],
                      "uv": per_nome[nome_c].get("uv"), "tex": tinte["taglio"],
                      "maglia": (taglio, None)})
    for f in faces:
        f["quad"] = [tuple(float(c) for c in v) for v in np.asarray(f["quad"], float) @ Rp.T]
        if f.get("maglia"):
            sup, inc = f["maglia"]
            f["maglia"] = (_ruota(sup, Rp), _ruota(inc, Rp))

    sfoglia = [_proietta(q, catena)[2] * PT2MM for r in rovescio
               for q in r[1:-1]] if sfogliati else []
    # la faccia su cui appoggia: quella che dopo la posa guarda in basso
    sotto = min((f for f in faces if f["name"] in panels and not f.get("maglia")),
                key=lambda f: _normale(f["quad"])[1], default=None)
    return {
        "gradi": gradi,
        "cerniera": nome_c,
        "piega_con": oltre,
        "appoggia": sotto["name"] if sotto else None,
        "cerniera_mm": float(np.linalg.norm(Hb - Ha)),
        "facce": toccate,
        "sfogliatura_mm": float(np.median(sfoglia)) if sfoglia else 0.0,
        "lunette": len(lunette),
        "tagli_liberi": len(liberi),
    }
