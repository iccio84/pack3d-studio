"""
Contenitori conici (coppe, secchielli, bicchieri).

Lo steso di una coppa non e' un rettangolo ma un settore anulare: due archi
concentrici e due lati radiali. Da raggi e angolo il tronco di cono esce con
formule chiuse, senza assunzioni:

    r_bocca = R2 * alpha / 2pi      r_fondo = R1 * alpha / 2pi
    apotema = R2 - R1               altezza = sqrt(apotema^2 - (r_bocca - r_fondo)^2)

Il punto delicato e' arrivare al contorno esatto. Ne' la silhouette
rasterizzata ne' i punti che pdfplumber espone per le curve vanno bene: la
prima non coincide col tratto di taglio perche' la grafica lo tocca, i secondi
includono i punti di controllo delle bezier. Qui il tracciato viene letto dal
content stream e le bezier vengono appiattite, quindi si lavora sul contorno
vero.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

PT2MM = 25.4 / 72.0


# --------------------------------------------------------------------------- #
# lettura del tracciato
# --------------------------------------------------------------------------- #
def _mat(a, b, c, d, e, f):
    return np.array([[a, b, 0.0], [c, d, 0.0], [e, f, 1.0]])


def _apply(M, x, y):
    v = np.array([x, y, 1.0]) @ M
    return float(v[0]), float(v[1])


def _bezier(p0, p1, p2, p3, n=24):
    t = np.linspace(0.0, 1.0, n + 1)[1:]
    mt = 1.0 - t
    x = (mt ** 3 * p0[0] + 3 * mt ** 2 * t * p1[0]
         + 3 * mt * t ** 2 * p2[0] + t ** 3 * p3[0])
    y = (mt ** 3 * p0[1] + 3 * mt ** 2 * t * p1[1]
         + 3 * mt * t ** 2 * p2[1] + t ** 3 * p3[1])
    return list(zip(x, y))


def flatten_paths(pdf_path, page_no: int = 0, min_pts: int = 8):
    """Tutti i sottotracciati della pagina, gia' appiattiti, in coordinate
    con origine in alto a sinistra e unita' di punto PDF."""
    import pypdf
    from pypdf.generic import ContentStream

    r = pypdf.PdfReader(pdf_path)
    page = r.pages[page_no]
    h = float(page.mediabox.height)
    cs = ContentStream(page.get_contents(), r)

    ctm = _mat(1, 0, 0, 1, 0, 0)
    stack = []
    paths, cur, start, pos = [], [], None, None

    def flush():
        nonlocal cur
        if len(cur) >= min_pts:
            paths.append(np.array([(x, h - y) for x, y in cur]))
        cur = []

    for ops, op in cs.operations:
        try:
            if op == b"q":
                stack.append(ctm.copy())
            elif op == b"Q":
                ctm = stack.pop() if stack else ctm
            elif op == b"cm":
                ctm = _mat(*[float(v) for v in ops]) @ ctm
            elif op == b"m":
                flush()
                pos = start = _apply(ctm, float(ops[0]), float(ops[1]))
                cur = [pos]
            elif op == b"l":
                pos = _apply(ctm, float(ops[0]), float(ops[1]))
                cur.append(pos)
            elif op in (b"c", b"v", b"y"):
                v = [float(x) for x in ops]
                if op == b"c":
                    p1 = _apply(ctm, v[0], v[1]); p2 = _apply(ctm, v[2], v[3])
                    p3 = _apply(ctm, v[4], v[5])
                elif op == b"v":
                    p1 = pos; p2 = _apply(ctm, v[0], v[1]); p3 = _apply(ctm, v[2], v[3])
                else:
                    p1 = _apply(ctm, v[0], v[1]); p3 = _apply(ctm, v[2], v[3]); p2 = p3
                cur.extend(_bezier(pos, p1, p2, p3))
                pos = p3
            elif op == b"h":
                if start:
                    cur.append(start); pos = start
            elif op == b"re":
                flush()
                x, y, w, hh = [float(v) for v in ops]
                pts = [(x, y), (x + w, y), (x + w, y + hh), (x, y + hh), (x, y)]
                cur = [_apply(ctm, px, py) for px, py in pts]
                flush()
            elif op in (b"S", b"s", b"f", b"F", b"f*", b"B", b"B*",
                        b"b", b"b*", b"n"):
                flush()
        except Exception:
            continue
    flush()
    return paths


# --------------------------------------------------------------------------- #
# riconoscimento del settore anulare
# --------------------------------------------------------------------------- #
@dataclass
class Sector:
    cx: float
    cy: float
    R1: float          # raggio interno, mm
    R2: float          # raggio esterno, mm
    alpha: float       # apertura, radianti
    resid_mm: float
    ang_check: float   # scarto fra l'angolo dei due archi, radianti


def _corners(P, k=4):
    """I quattro spigoli del settore: i punti dove la direzione gira di piu'."""
    n = len(P)
    d = np.zeros(n)
    w = max(3, n // 120)
    for i in range(n):
        a = P[i] - P[(i - w) % n]
        b = P[(i + w) % n] - P[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            continue
        cosv = np.clip(np.dot(a, b) / (na * nb), -1, 1)
        d[i] = math.acos(cosv)
    idx = []
    for i in np.argsort(-d):
        if all(min(abs(i - j), n - abs(i - j)) > n * 0.06 for j in idx):
            idx.append(int(i))
        if len(idx) == k:
            break
    return sorted(idx)


def fit_sector(P) -> Sector:
    """Adatta due archi concentrici e i due lati radiali al contorno."""
    P = np.asarray(P, float)
    if np.linalg.norm(P[0] - P[-1]) < 1e-6:
        P = P[:-1]
    ci = _corners(P)
    n = len(P)
    edges = []
    for a, b in zip(ci, ci[1:] + [ci[0] + n]):
        seg = np.array([P[i % n] for i in range(a + 2, b - 1)])
        if len(seg) >= 6:
            edges.append(seg)
    edges.sort(key=lambda s: -np.linalg.norm(s[-1] - s[0]))
    A, B = edges[0], edges[1]          # i due archi sono i lati piu' lunghi

    from scipy.optimize import least_squares

    def guess(S):
        p, q, r = S[0], S[len(S) // 2], S[-1]
        ax, ay = q - p; bx, by = r - q
        d = 2 * (ax * by - ay * bx)
        if abs(d) < 1e-9:
            return np.array([S[:, 0].mean(), S[:, 1].mean() + 1e4])
        ux = ((np.dot(q, q) - np.dot(p, p)) * by
              - (np.dot(r, r) - np.dot(q, q)) * ay) / d
        uy = ((np.dot(r, r) - np.dot(q, q)) * ax
              - (np.dot(q, q) - np.dot(p, p)) * bx) / d
        return np.array([ux, uy])

    c0 = guess(A)
    p0 = [c0[0], c0[1],
          np.hypot(*(A[len(A) // 2] - c0)), np.hypot(*(B[len(B) // 2] - c0))]

    def res(p):
        cx, cy, r1, r2 = p
        return np.r_[np.hypot(A[:, 0] - cx, A[:, 1] - cy) - r1,
                     np.hypot(B[:, 0] - cx, B[:, 1] - cy) - r2]

    sol = least_squares(res, p0, xtol=1e-14, ftol=1e-14, max_nfev=20000)
    cx, cy, ra, rb = sol.x
    Rout, Rin = (ra, rb) if ra > rb else (rb, ra)
    Aout, Ain = (A, B) if ra > rb else (B, A)

    def span(S):
        t = np.unwrap(np.arctan2(S[:, 1] - cy, S[:, 0] - cx))
        return abs(t[-1] - t[0])

    a_out, a_in = span(Aout), span(Ain)
    return Sector(cx, cy, Rin * PT2MM, Rout * PT2MM,
                  (a_out + a_in) / 2.0,
                  float(np.abs(sol.fun).max() * PT2MM),
                  abs(a_out - a_in))


@dataclass
class Cup:
    d_mouth: float
    d_base: float
    height: float
    slant: float
    sector: Sector

    def __str__(self):
        return ("bocca %.2f  fondo %.2f  altezza %.2f  apotema %.2f mm"
                % (self.d_mouth, self.d_base, self.height, self.slant))


def sector_to_cup(s: Sector) -> Cup:
    rt = s.R2 * s.alpha / (2 * math.pi)
    rb = s.R1 * s.alpha / (2 * math.pi)
    slant = s.R2 - s.R1
    dr = rt - rb
    if slant <= abs(dr):
        raise ValueError("settore incoerente: apotema %.2f, differenza raggi %.2f"
                         % (slant, dr))
    return Cup(2 * rt, 2 * rb, math.sqrt(slant ** 2 - dr ** 2), slant, s)


def analyze_cup(pdf_path, page_no: int = 0) -> Cup:
    """Il settore e' il tracciato chiuso di area maggiore della pagina."""
    paths = flatten_paths(pdf_path, page_no)
    if not paths:
        raise ValueError("nessun tracciato leggibile")

    def area(P):
        return ((P[:, 0].max() - P[:, 0].min()) * (P[:, 1].max() - P[:, 1].min()))

    best, cup = None, None
    for P in sorted(paths, key=area, reverse=True)[:6]:
        try:
            c = sector_to_cup(fit_sector(P))
        except Exception:
            continue
        if best is None or c.sector.resid_mm < best:
            best, cup = c.sector.resid_mm, c
    if cup is None:
        raise ValueError("settore anulare non riconosciuto")
    return cup
