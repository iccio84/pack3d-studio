"""La chiusura a sormonto dell'astuccio: il fondo col bordo sagomato sopra la
falda del retro.

Il caso: un astuccio di cioccolatini da 16, colonna RETRO - CIELO - FRONTE -
FONDO, con una falda sopra il retro. Il fondo ha il bordo libero sagomato -
gli angoli smussati e due tacche a mezzaluna con la linguetta fra loro - e
chiude sormontando la falda, che fa da fondo dentro di lui. Il modello aveva
il fondo pieno, rettangolare, con la linguetta incisa come un solco, e la
falda non c'era: chi l'ha caricato l'ha respinto, perche' la linguetta e gli
smussi sono fustellati, tagliati, e il lato della linguetta va sopra l'altro.

La regola: se il fondo viene dopo il fronte, il retro prima, sopra il retro
c'e' una falda lunga almeno meta' del fondo e il contorno di taglio del fondo
entra dal suo bordo libero almeno `SAGOMA_MIN` mm, allora il fondo si
ritaglia sul contorno vero della fustella - le tacche e gli smussi sono vuoti,
con la costa del cartoncino - e sotto di lui, a uno spessore, c'e' la falda,
stampata col suo pannello: dalle tacche e dagli smussi si vede lei.
"""

import math

import numpy as np
from PIL import Image

from .dieline import Panel, PT2MM

MM = 1.0 / PT2MM
# Quanto deve entrare nella faccia il contorno del bordo libero, in mm: meno
# e' il bordo appena storto, che resta com'e'.
SAGOMA_MIN = 2.0
# La falda sopra il retro: lunga almeno questa frazione del fondo.
FALDA_MIN = 0.5
# Il margine attorno al pannello in cui si raccoglie il suo contorno, in punti.
BORDO = 4.0


def _contorno(tratti, b):
    """Il contorno di taglio del pannello `b` dalla piega in su: una linea di
    punti PDF che parte dalla piega, gira lungo il bordo libero e torna sulla
    piega. None se non c'e'."""
    from . import incisioni

    dentro = [s for s in tratti if all(
        b.x0 - BORDO <= q[0] <= b.x1 + BORDO and b.y0 - 1.0 <= q[1] <= b.y1 + BORDO
        for q in s)]
    catene = incisioni._catene(dentro)
    if not catene:
        return None
    linea = max(catene, key=incisioni._lunghezza)
    xs = [q[0] for q in linea]
    if (max(xs) - min(xs)) < 0.9 * (b.x1 - b.x0):
        return None
    pts = list(linea)
    chiusa = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= 1.0
    if chiusa:
        pts = pts[:-1]
    sulla_piega = [q[1] <= b.y0 + 1.0 for q in pts]
    if chiusa:
        if all(sulla_piega) or not any(sulla_piega):
            return None
        k = sulla_piega.index(True)
        pts, sulla_piega = pts[k:] + pts[:k], sulla_piega[k:] + sulla_piega[:k]
    # il tratto piu' lungo lontano dalla piega, coi due punti di piega ai capi
    corse, i = [], 0
    while i < len(pts):
        if sulla_piega[i]:
            i += 1
            continue
        j = i
        while j < len(pts) and not sulla_piega[j]:
            j += 1
        corse.append((i, j))
        i = j
    if not corse:
        return None
    i, j = max(corse, key=lambda c: c[1] - c[0])
    corsa = pts[i:j]
    capi = [pts[i - 1] if i > 0 else (pts[-1] if chiusa else corsa[0]),
            pts[j] if j < len(pts) else (pts[0] if chiusa else corsa[-1])]
    out = [(capi[0][0], b.y0)] + corsa + [(capi[1][0], b.y0)]
    if abs(out[0][0] - out[-1][0]) < 0.9 * (b.x1 - b.x0):
        return None
    return out


def trova(pdf, d, page_no=0):
    """{"contorno": [punti PDF], "falda": Panel} del fondo a sormonto, o None.

    Solo l'astuccio chiuso RETRO - CIELO - FRONTE - FONDO letto nel verso
    della grafica, col fondo che chiude sul retro: e' l'unico in cui il bordo
    libero del fondo incontra la falda del retro.
    """
    from . import incisioni

    if not getattr(d, "chiuso", False) or d.layout != "vwrap":
        return None
    b, r, f = (d.panels.get(k) for k in ("bottom", "back", "front"))
    if b is None or r is None or f is None:
        return None
    tol = 1.0 * MM
    if not (r.y1 <= f.y0 + tol and b.y0 >= f.y1 - tol):
        return None
    tratti = incisioni._segmenti(incisioni._tratti_tecnici(pdf, page_no))
    if not tratti:
        return None
    contorno = _contorno(tratti, b)
    if contorno is None:
        return None
    # quanto entra il bordo libero nella faccia, lontano dai fianchi
    w = b.x1 - b.x0
    entra = max([b.y1 - q[1] for q in contorno
                 if b.x0 + 0.1 * w < q[0] < b.x1 - 0.1 * w
                 and q[1] > (b.y0 + b.y1) / 2.0] or [0.0])
    if entra * PT2MM < SAGOMA_MIN:
        return None
    # la falda sopra il retro: i tratti della fustella nella sua colonna
    h = b.y1 - b.y0
    sopra = [q[1] for s in tratti for q in s
             if r.x0 - BORDO <= q[0] <= r.x1 + BORDO
             and r.y0 - 1.5 * h <= q[1] < r.y0 - 1.0]
    if not sopra or (r.y0 - min(sopra)) < FALDA_MIN * h:
        return None
    return {"contorno": contorno,
            "falda": Panel(b.x0, r.y0 - h, b.x1, r.y0, "falda"),
            "entra_mm": entra * PT2MM}


def falda(faces, s, spessore, tela, box, scala, girate):
    """La falda sotto il fondo, a uno spessore dentro, al posto della faccia
    interna del fondo. In place; torna il pannello della falda per lo steso.

    La falda e' piegata dal retro e continua la fasciatura: sul piano del
    fondo sta nel suo stesso verso, con la piega sul bordo libero del fondo.
    Il suo pannello e' quindi il riquadro alto quanto il fondo sopra il retro,
    e la sua immagine e' quella dello steso, girata come il fondo.
    """
    from .artwork import GIRO_TEXTURE
    from .folding import INTERNO, _normale, _tinta

    fondo = next((f for f in faces if f["name"] == "bottom"), None)
    if fondo is None:
        return None
    p = s["falda"]
    q = np.array(fondo["quad"], float)
    n = _normale([tuple(v) for v in q])
    sx0, sy0 = box[0], box[1]
    ritaglio = tela.crop(tuple(round(c * scala) - o for c, o in
                               zip((p.x0, p.y0, p.x1, p.y1), (sx0, sy0, sx0, sy0))))
    g = (girate or {}).get("bottom")
    if g:
        ritaglio = ritaglio.transpose(GIRO_TEXTURE[g])
    faces[:] = [f for f in faces if f["name"] != "bottom interno"]
    fuori = [tuple(v) for v in q - n * spessore]
    dentro = [tuple(v) for v in q - n * 2 * spessore]
    faces.append({"name": "falda", "quad": fuori, "uv": list(fondo["uv"]),
                  "tex": ritaglio.convert("RGB")})
    faces.append({"name": "falda interno", "quad": list(reversed(dentro)),
                  "uv": list(fondo["uv"]), "tex": _tinta(INTERNO)})
    return p


def _dentro(P, poli):
    """Vero per i punti di P dentro il poligono (pari e dispari)."""
    x, y = P[:, 0], P[:, 1]
    ok = np.zeros(len(P), bool)
    for (x0, y0), (x1, y1) in zip(poli, np.roll(poli, -1, axis=0)):
        if y0 == y1:
            continue
        c = ((y0 > y) != (y1 > y)) & (x < x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        ok ^= c
    return ok


def ritaglia(faces, s, panels, girate, spessore):
    """Il fondo ritagliato sul suo contorno, con la costa del taglio. In
    place; vero se l'ha fatto. Un fondo che e' gia' una maglia (inciso dai
    tagli dell'apertura) resta com'e'."""
    from . import ballotin, incisioni

    fondo = next((f for f in faces if f["name"] == "bottom"), None)
    b = panels.get("bottom")
    if fondo is None or b is None or fondo.get("maglia"):
        return False
    q = np.array(fondo["quad"], float)
    es, et = q[1] - q[0], q[3] - q[0]
    W, H = float(np.linalg.norm(es)), float(np.linalg.norm(et))
    es, et = es / W, et / H
    n = -np.cross(q[1] - q[0], q[3] - q[0])
    n /= np.linalg.norm(n)
    uv = np.clip(np.array(incisioni._uv_faccia(s["contorno"], b,
                                               (girate or {}).get("bottom", 0)),
                          float), 0.0, 1.0)
    poli = uv * (W, H)
    P, T = ballotin.triangola([poli], bordo=0.8, griglia=4.0)
    if not len(T):
        return False
    P = np.asarray(P, float)
    V = q[0] + P[:, :1] * es + P[:, 1:] * et
    a3, b3, c3 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    T = np.array(T)
    rov = (np.cross(b3 - a3, c3 - a3) @ n) < 0
    T[rov] = T[rov][:, [0, 2, 1]]
    usati, inv = np.unique(T, return_inverse=True)
    sup = (V[usati], np.tile(n, (len(usati), 1)), P[usati] / (W, H),
           inv.reshape(-1, 3))
    # la costa: un lato del contorno che non sta su un lato della faccia
    eps = 0.05
    Vc, Nc = [], []
    for a, c in zip(poli, np.roll(poli, -1, axis=0)):
        if np.hypot(*(c - a)) < 1e-6:
            continue
        sul_lato = any(abs(a[k] - v) < eps and abs(c[k] - v) < eps
                       for k, v in ((0, 0.0), (0, W), (1, 0.0), (1, H)))
        if sul_lato:
            continue
        A = q[0] + a[0] * es + a[1] * et
        C = q[0] + c[0] * es + c[1] * et
        A2, C2 = A - n * spessore, C - n * spessore
        m2 = (a + c) / 2.0
        t2 = (c - a) / np.hypot(*(c - a))
        sx = np.array([-t2[1], t2[0]])
        # la costa guarda fuori dal cartoncino: la sinistra del lato, o la
        # destra se a sinistra c'e' il fondo
        if _dentro(np.array([m2 + sx * 0.01]), poli)[0]:
            sx = -sx
        nn = sx[0] * es + sx[1] * et
        nn /= max(np.linalg.norm(nn), 1e-12)
        tri = [(A, C, C2), (A, C2, A2)]
        for t in tri:
            if np.cross(t[1] - t[0], t[2] - t[0]) @ nn < 0:
                t = (t[0], t[2], t[1])
            Vc.extend(t)
            Nc.extend([nn] * 3)
    inc = None
    if Vc:
        Vc = np.array(Vc)
        inc = (Vc, np.array(Nc), np.zeros((len(Vc), 2)),
               np.arange(len(Vc)).reshape(-1, 3))
    fondo["maglia"] = (sup, inc)
    return True
