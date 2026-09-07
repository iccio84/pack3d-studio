"""
Flowpack: dallo steso di stampa alla forma tridimensionale.

Un flowpack non e' un poliedro. Il film esce da una bobina, si avvolge attorno
al prodotto e viene saldato in tre punti: una pinna longitudinale dove i due
bordi del nastro si incontrano, e due pinne trasversali alle estremita', dove
la sezione si schiaccia fino a diventare piatta. Le pinne trasversali sono
tagliate a zigzag dalle ganasce (zingrinatura).

Lo steso va quindi letto come una fascia: la direzione trasversale al nastro e'
lo sviluppo del perimetro della sezione, quella longitudinale e' la lunghezza.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pdfplumber

from .dieline import _segments, _cluster, PT2MM


@dataclass
class Flowpack:
    W: float = 0.0            # larghezza del prodotto (faccia fronte)
    T: float = 0.0            # spessore del prodotto
    L: float = 0.0            # lunghezza fra le due saldature di testa
    end_fin: float = 0.0      # sporgenza della pinna trasversale
    side_fin: float = 0.0     # altezza della pinna longitudinale
    back_a: float = 0.0       # tratto di retro fra pinna e primo spigolo
    back_b: float = 0.0       # tratto di retro dall'altro lato
    web_mm: float = 0.0
    step_mm: float = 0.0
    # riquadro dello steso, in punti PDF: (x0, y0, x1, y1)
    sheet: tuple = (0.0, 0.0, 0.0, 0.0)
    girth_span: tuple = (0.0, 0.0)   # y del perimetro utile, in punti
    warnings: list = field(default_factory=list)

    @property
    def girth(self):
        return 2.0 * (self.W + self.T)


def _technical_segments(page, min_len=25.0):
    """Il tracciato tecnico dello steso: tratti sottili, i piu' lunghi."""
    segs = [s for s in _segments(page) if s[3] - s[2] > min_len and s[4][0] <= 0.8]
    score = {}
    for k, c, a, b, st in segs:
        score[st] = score.get(st, 0.0) + (b - a)
    pen = max(score, key=score.get)
    return [s for s in segs if s[4] == pen]


def analyze(pdf_path: str, page_no: int = 0, tol: float = 0.02) -> Flowpack:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no]
        segs = _technical_segments(page)

        V = _cluster([(c, b - a) for k, c, a, b, st in segs if k == "V"], 2.0)
        H = _cluster([(c, b - a) for k, c, a, b, st in segs if k == "H"], 2.0)
        if not V or not H:
            raise ValueError("nessun tracciato tecnico riconoscibile")

        ys = [c for c, w in H]
        web_pt = ys[-1] - ys[0]
        # le linee a tutta altezza segnano taglio di ripetizione e saldature
        full = sorted(c for c, w in V if w > web_pt * 0.9)
        if len(full) < 4:
            raise ValueError("saldature di testa non riconosciute")
        cut0, seal0, seal1, cut1 = full[0], full[1], full[-2], full[-1]

        steps = [(ys[i + 1] - ys[i]) * PT2MM for i in range(len(ys) - 1)]
        i = int(np.argmax(steps))
        W = steps[i]

        # lo spessore e' la fascia adiacente al fronte su entrambi i lati; puo'
        # essere spezzata in piu' tratti dalle linee di riferimento grafiche
        def run(start, direction, target):
            tot, n = 0.0, 0
            j = start
            while 0 <= j < len(steps) and tot < target * (1 + tol):
                tot += steps[j]
                n += 1
                if abs(tot - target) <= max(0.4, target * tol):
                    return n, tot
                j += direction
            return None, None

        best = None
        for cand in sorted({round(s, 1) for s in steps}, reverse=True):
            if cand >= W or cand <= 0:
                continue
            nl, tl = run(i - 1, -1, cand)
            nr, tr = run(i + 1, +1, cand)
            if nl is None or nr is None:
                continue
            girth = 2 * (W + cand)
            # la fascia del perimetro deve chiudere su 2*(W+T)
            for a in range(0, i - nl + 1):
                for b in range(i + nr, len(steps)):
                    tot = sum(steps[a:b + 1])
                    if abs(tot - girth) <= max(1.0, girth * tol):
                        err = abs(tot - girth)
                        if best is None or err < best[0]:
                            best = (err, cand, a, b, nl, nr)
        if best is None:
            raise ValueError("perimetro della sezione non riconosciuto")
        _, T, a, b, nl, nr = best

        back_a = sum(steps[a:i - nl])
        back_b = sum(steps[i + nr + 1:b + 1])
        fin_material = sum(steps[:a]) + sum(steps[b + 1:])

        fp = Flowpack(
            W=round(W, 1), T=round(T, 1),
            L=round((seal1 - seal0) * PT2MM, 1),
            end_fin=round((seal0 - cut0) * PT2MM, 1),
            side_fin=round(fin_material / 2.0, 1),
            back_a=round(back_a, 1), back_b=round(back_b, 1),
            web_mm=round(web_pt * PT2MM, 1),
            step_mm=round((cut1 - cut0) * PT2MM, 1),
            sheet=(cut0, ys[0], cut1, ys[-1]),
            girth_span=(ys[a], ys[b + 1]),
        )
        if abs(back_a + back_b - W) > max(1.0, W * 0.03):
            fp.warnings.append(
                f"il retro misura {back_a + back_b:.1f} mm contro {W:.1f} mm di fronte")
        if abs(fp.end_fin - (cut1 - seal1) * PT2MM) > 0.5:
            fp.warnings.append("le due pinne di testa hanno larghezza diversa")
        return fp


# --------------------------------------------------------------------------- #
# costruzione della mesh
# --------------------------------------------------------------------------- #
def _section_path(fp: Flowpack, r: float, n_arc: int = 10, section_w=None):
    """Sezione trasversale: rettangolo W x T con spigoli raccordati.

    Il cammino parte dalla pinna longitudinale e gira nello stesso ordine in cui
    lo steso scorre dall'alto verso il basso: retro, fianco, fronte, fianco,
    retro. Restituisce i punti e l'ascissa curvilinea."""
    W, T = (section_w or fp.W), fp.T
    r = min(r, W / 2 - 0.1, T / 2 - 0.1)
    hy, hz = W / 2, T / 2
    y_fin = hy - fp.back_a

    corners = [(+hy, -hz), (+hy, +hz), (-hy, +hz), (-hy, -hz)]
    pts = [(y_fin, -hz)]
    for k, (cy, cz) in enumerate(corners):
        sy = 1 if cy > 0 else -1
        sz = 1 if cz > 0 else -1
        # ingresso e uscita dello spigolo
        if k in (0, 2):      # spigoli sul lato del retro/fronte -> arrivo in y
            pts.append((cy - sy * r, cz))
            centre = (cy - sy * r, cz + (-sz) * 0 + sz * 0)
        pts.append((cy, cz))
    # ricostruzione esplicita con archi
    path = []

    def arc(cy, cz, a0, a1):
        for t in np.linspace(a0, a1, n_arc):
            path.append((cy + r * np.cos(t), cz + r * np.sin(t)))

    path.append((y_fin, -hz))
    path.append((hy - r, -hz))
    arc(hy - r, -hz + r, -np.pi / 2, 0.0)
    path.append((hy, hz - r))
    arc(hy - r, hz - r, 0.0, np.pi / 2)
    path.append((-hy + r, hz))
    arc(-hy + r, hz - r, np.pi / 2, np.pi)
    path.append((-hy, -hz + r))
    arc(-hy + r, -hz + r, np.pi, 1.5 * np.pi)
    path.append((y_fin, -hz))

    P = np.array(path, float)
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return P, d



def superellipse_section(fp: Flowpack, n: float, thickness=None, npts: int = 1600):
    """Sezione a superellisse |y/a|^n + |z/b|^n = 1.

    Il rettangolo raccordato ha la curvatura che salta di colpo nei punti di
    tangenza, e il salto si legge come una piega netta. La superellisse ha
    curvatura continua: e' la forma che da' l'aspetto morbido del pack reale.
    Lo spessore lo fissa il prodotto; la semilarghezza `a` viene ricavata
    imponendo che il perimetro sia quello del film.
    """
    b = (thickness if thickness is not None else fp.T) / 2.0
    t = np.linspace(0.0, 2.0 * np.pi, npts, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    uy = np.sign(ct) * np.abs(ct) ** (2.0 / n)
    uz = np.sign(st) * np.abs(st) ** (2.0 / n)

    def perim(a):
        P = np.stack([a * uy, b * uz], 1)
        return float(np.sum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)))

    lo, hi = b, 4.0 * fp.girth
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if perim(mid) < fp.girth:
            lo = mid
        else:
            hi = mid
    a = 0.5 * (lo + hi)
    P = np.stack([a * uy, b * uz], 1)
    # L'origine di v deve cadere sulla cucitura, come nel profilo raccordato:
    # altrimenti la grafica ruota attorno al tubo e il fronte non guarda piu'
    # davanti. La cucitura sta a `back_a` di arco prima dello spigolo +y.
    dd = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(dd)])
    per = cum[-1]
    imax = int(np.argmax(P[:, 0]))
    s0 = (cum[imax] - fp.back_a) % per
    i0 = int(np.searchsorted(cum, s0)) % len(P)
    P = np.roll(P, -i0, axis=0)
    P = np.vstack([P, P[:1]])           # contorno chiuso
    dd = np.linalg.norm(np.diff(P, axis=0), axis=1)
    d = np.concatenate([[0.0], np.cumsum(dd)])
    return P, d, a


def build_mesh(fp: Flowpack, nu: int = 72, nv: int = 108, corner_r: float = 3.5,
               taper: float = 24.0, flat_end: float = 0.035, width_end: float = 0.93,
               section_w=None,
               crimp_period: float = 1.6, crimp_mm: float = 0.30,
               serration: bool = True, serr_period: float = 0.85,
               serr_amp: float = 0.45, bulge: float = 0.0,
               serr_teeth: int = 0, fin_stations: int = 44,
               sec_exp: float = 0.0, soft: bool = False,
               soft_r: float = 0.0, soft_n: float = 3.0, flare_pow: float = 2.0,
               wrinkle_mm: float = 0.0, wrinkle_v: float = 3.0, wrinkle_u: float = 2.5):
    """Mesh del flowpack con UV riferite allo steso.

    u percorre la lunghezza (comprese le pinne di testa), v il perimetro. Dove
    la sezione si schiaccia la stampa si comprime da sola, perche' le UV restano
    quelle del piano: e' esattamente quello che succede sul pack reale.
    """
    if soft_r > 0:
        P, d, section_w = soft_section_fit(fp, soft_r, soft_n)
    elif sec_exp > 0:
        P, d, _a = superellipse_section(fp, sec_exp)
    else:
        P, d = _section_path(fp, corner_r, section_w=section_w)
    G = d[-1]
    v = np.linspace(0.0, 1.0, nv + 1)
    sec = np.stack([np.interp(v * G, d, P[:, 0]), np.interp(v * G, d, P[:, 1])], 1)

    half = fp.L / 2.0
    total = half + fp.end_fin
    # sezioni fitte dentro le pinne: il dente e' profondo circa 1,6 mm e con il
    # passo del corpo verrebbe fuori a gradini invece che a punta
    body = np.linspace(-half, half, nu + 1)
    fin = np.linspace(half, total, max(fin_stations, 2) + 1)[1:]
    u = np.concatenate([-fin[::-1], body, fin])

    # zigzag della zigrinatura sul bordo esterno delle pinne
    if serration and serr_teeth > 0:
        # Il dente va contato sul bordo della pinna, non sul perimetro della
        # sezione: la pinna e' schiacciata, quindi il suo bordo misura due
        # volte l'apertura. Passo e altezza danno triangoli equilateri.
        y_fin = sec[:, 0] * width_end
        hy = float(np.max(np.abs(y_fin)))
        base = 2.0 * hy / serr_teeth
        depth = base * math.sqrt(3.0) / 2.0
        phase = (y_fin + hy) / base
        saw = 2.0 * np.abs(phase - np.floor(phase + 0.5))
        trim = depth * saw
    elif serration and serr_period > 0:
        phase = (v * G) / serr_period
        saw = 2.0 * np.abs(phase - np.floor(phase + 0.5))
        trim = serr_amp * saw
    else:
        trim = np.zeros_like(v)

    # normale 2D del contorno: serve per le grinze, che vanno date lungo la
    # normale, non in verticale, altrimenti la sezione si deforma
    tang = np.gradient(sec, axis=0)
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
    nrm = np.stack([tang[:, 1], -tang[:, 0]], 1)
    if float(np.sum(nrm * sec)) < 0:
        nrm = -nrm

    verts = np.zeros((len(u), nv + 1, 3))
    uvs = np.zeros((len(u), nv + 1, 2))
    for i, ui in enumerate(u):
        a = abs(ui)
        if a <= half - taper:
            k = 0.0
        elif a <= half:
            k = (a - (half - taper)) / taper
            if soft:
                k = k * k * (3.0 - 2.0 * k)   # raccordo senza spigolo di spalla
        else:
            k = 1.0
        sz = (1.0 - k * k) * (1.0 - flat_end) + flat_end
        if a > half and crimp_mm > 0:
            # nervature delle ganasce: sono loro a dare alla pinna il grigio
            # rigato che la stacca dal fondo, altrimenti resta bianco su bianco
            ridge = abs(np.sin(np.pi * (a - half) / crimp_period))
            sz += (crimp_mm / max(fp.T / 2.0, 1e-6)) * ridge
        # l'apertura della pinna si concentra vicino alla saldatura: con una
        # rampa quadratica il gonfiore invade il corpo e deforma la grafica
        sy = 1.0 - (1.0 - width_end) * k ** flare_pow
        # leggera pancia al centro
        sw = 1.0 + bulge * (1.0 - (ui / max(total, 1e-6)) ** 2)
        uu = ui
        if a > half:                       # dentro la pinna: taglio a zigzag
            # il taglio tocca solo il bordo: l'interno della pinna resta piano,
            # altrimenti il dente si trasforma in una scanalatura lunga 8 mm
            uu = np.sign(ui) * np.minimum(a, total - trim)
        yy = sec[:, 0] * sy * (sw if a <= half else 1.0)
        zz = sec[:, 1] * sz * (sw if a <= half else 1.0)
        if wrinkle_mm > 0 and a <= half:
            # il film e' lasco e si increspa soprattutto verso le saldature.
            # La grinza va data lungo la normale del contorno: spostando in
            # verticale si schiaccerebbe la sezione e la grafica ne risentirebbe.
            g = (a / max(half, 1e-6)) ** 2
            ph = 2.0 * np.pi * ui / max(fp.L, 1e-6)
            wob = (np.sin(2.0 * np.pi * wrinkle_v * v + 1.7 * ph)
                   + 0.6 * np.sin(2.0 * np.pi * wrinkle_v * 1.9 * v - 1.1 * ph)
                   + 0.5 * np.sin(wrinkle_u * ph + 2.0 * np.pi * v))
            wv = wrinkle_mm * g * wob / 2.1
            yy = yy + wv * nrm[:, 0]
            zz = zz + wv * nrm[:, 1]
        verts[i, :, 0] = uu
        verts[i, :, 1] = yy
        verts[i, :, 2] = zz
        uvs[i, :, 0] = (ui + total) / (2 * total)
        uvs[i, :, 1] = v

    V = verts.reshape(-1, 3)
    UV = uvs.reshape(-1, 2)
    idx = lambda i, j: i * (nv + 1) + j
    tris = []
    for i in range(len(u) - 1):
        for j in range(nv):
            a_, b_, c_, e_ = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            # avvolgimento antiorario visto da fuori: con l'ordine opposto il
            # modello si vede rovesciato in ogni viewer che scarta le facce
            # posteriori, ed e' cosi' che la grafica appare capovolta e riflessa
            tris.append((a_, c_, b_))
            tris.append((a_, e_, c_))
    return V, UV, np.array(tris, np.int32)


def build_side_fin(fp: Flowpack, nu: int = 120, nv: int = 8, gap: float = 0.45,
                   fade: float = 12.0):
    """Pinna longitudinale ripiegata sul retro.

    I due bordi del nastro si saldano fra loro e la falda viene coricata contro
    il retro. La grafica della falda e' il film che prosegue oltre la cucitura,
    quindi sullo steso sta subito fuori dalla fascia del perimetro.
    """
    hy, hz = fp.W / 2.0, fp.T / 2.0
    y_seam = hy - fp.back_a
    half = fp.L / 2.0
    x = np.linspace(-half, half, nu + 1)
    s = np.linspace(0.0, 1.0, nv + 1)          # 0 alla piega, 1 alla cimosa

    y0s, y1s, web = fp.sheet[1], fp.sheet[3], fp.sheet[3] - fp.sheet[1]
    g0 = fp.girth_span[0]
    fin_pt = fp.side_fin / PT2MM

    V = np.zeros((nu + 1, nv + 1, 3))
    UV = np.zeros((nu + 1, nv + 1, 2))
    for i, xi in enumerate(x):
        k = min(1.0, (half - abs(xi)) / fade)    # la falda si spegne nelle teste
        h = fp.side_fin * (k * k * (3 - 2 * k))
        V[i, :, 0] = xi
        V[i, :, 1] = y_seam - s * h
        V[i, :, 2] = -(hz + gap)
        UV[i, :, 0] = (xi + half + fp.end_fin) / (fp.L + 2 * fp.end_fin)
        UV[i, :, 1] = (g0 - y0s - s * fin_pt) / web

    Vf = V.reshape(-1, 3)
    UVf = UV.reshape(-1, 2)
    idx = lambda i, j: i * (nv + 1) + j
    tris = []
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            tris.append((a, c, b))
            tris.append((a, d, c))
    return Vf, UVf, np.array(tris, np.int32)


def remap_to_sheet(UV, fp: Flowpack):
    """Porta le v del tubo dalla fascia del perimetro all'intero steso."""
    y0s, web = fp.sheet[1], fp.sheet[3] - fp.sheet[1]
    g0, g1 = fp.girth_span
    out = UV.copy()
    out[:, 1] = (g0 - y0s + UV[:, 1] * (g1 - g0)) / web
    return out


def _soft_section(fp: Flowpack, r: float, section_w: float, n_corner: float = 3.0,
                  n_pts: int = 40):
    """Sezione con centro piano e spigoli a curvatura continua.

    Il raccordo circolare lascia un salto di curvatura dove incontra il tratto
    dritto, e sotto luce quel salto si legge come una piega netta. Qui lo
    spigolo e' un quarto di superellisse con esponente > 2: entra ed esce con
    curvatura nulla, quindi la piega si ammorbidisce senza rinunciare al centro
    piano che serve a non deformare la grafica.
    """
    hy, hz = section_w / 2.0, fp.T / 2.0
    y_fin = fp.W / 2.0 - fp.back_a
    p = 2.0 / n_corner

    def corner(cy, cz, sy, sz):
        """Quarto di spigolo dal tratto orizzontale a quello verticale."""
        t = np.linspace(0.0, np.pi / 2.0, n_pts)
        return np.stack([cy + sy * r * np.sin(t) ** p,
                         cz + sz * r * (1.0 - np.cos(t) ** p)], 1)

    path = [np.array([[y_fin, -hz]]), np.array([[hy - r, -hz]])]
    path.append(corner(hy - r, -hz, +1, +1))          # basso destra
    path.append(np.array([[hy, hz - r]]))
    path.append(corner(hy - r, hz, +1, -1)[::-1])     # alto destra
    path.append(np.array([[-(hy - r), hz]]))
    path.append(corner(-(hy - r), hz, -1, -1))        # alto sinistra
    path.append(np.array([[-hy, -hz + r]]))
    path.append(corner(-(hy - r), -hz, -1, +1)[::-1])  # basso sinistra
    path.append(np.array([[y_fin, -hz]]))
    P = np.vstack(path)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9]
    P = P[keep]
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return P, d


def soft_section_fit(fp: Flowpack, r: float, n_corner: float = 3.0):
    """Larghezza che porta il perimetro della sezione morbida a coincidere con
    la circonferenza del film."""
    lo, hi = fp.T, 3.0 * fp.girth
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        _, d = _soft_section(fp, r, mid, n_corner)
        if d[-1] < fp.girth:
            lo = mid
        else:
            hi = mid
    w = 0.5 * (lo + hi)
    P, d = _soft_section(fp, r, w, n_corner)
    return P, d, w


def fin_on_surface(grid, fp: Flowpack, G: float, nv: int, gap: float = 0.5,
                   fade: float = 10.0):
    """Pinna longitudinale appoggiata sul retro, che ne segue la forma.

    La falda non e' un rettangolo piatto sospeso: e' film incollato sul retro,
    quindi va costruita come superficie offset della sezione a partire dalla
    cucitura. Cosi' segue pancia, raccordi e grinze del pack invece di
    tagliarli.
    """
    jmax = max(2, int(round(fp.side_fin / G * nv)))
    y0s, web = fp.sheet[1], fp.sheet[3] - fp.sheet[1]
    g0 = fp.girth_span[0]
    half = fp.L / 2.0
    nu = grid.shape[0]

    V = np.zeros((nu, jmax + 1, 3))
    UV = np.zeros((nu, jmax + 1, 2))
    for i in range(nu):
        x = grid[i, 0, 0]
        t = min(1.0, max(0.0, (half - abs(x)) / fade))
        lift = gap * (t * t * (3 - 2 * t))
        for j in range(jmax + 1):
            p = grid[i, j]
            n = np.array([0.0, p[1], p[2]])
            nn = np.linalg.norm(n)
            n = n / nn if nn > 1e-9 else np.array([0.0, 0.0, -1.0])
            V[i, j] = p + lift * n
            s = j / nv * G                      # arco dalla cucitura
            UV[i, j] = (grid[i, j, 0] - grid[0, 0, 0]) / (grid[-1, 0, 0] - grid[0, 0, 0]), \
                       (g0 - y0s - s / PT2MM) / web
        UV[i, :, 0] = (x - grid[0, 0, 0]) / (grid[-1, 0, 0] - grid[0, 0, 0])

    Vf = V.reshape(-1, 3); UVf = UV.reshape(-1, 2)
    idx = lambda i, j: i * (jmax + 1) + j
    tris = []
    for i in range(nu - 1):
        for j in range(jmax):
            a_, b_, c_, e_ = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            tris.append((a_, c_, b_))
            tris.append((a_, e_, c_))
    return Vf, UVf, np.array(tris, np.int32)


def _collapse_guides(vals, max_gap=8.0, tol=0.6):
    """Le cordonature sono spesso tracciate con due guide equidistanti: tre
    linee ravvicinate e ugualmente spaziate sono una piega sola, quella di
    mezzo. Senza questo passaggio le fasce escono assurde (5 | 63 | 5)."""
    out, i = [], 0
    v = sorted(vals)
    while i < len(v):
        if (i + 2 < len(v) and v[i + 1] - v[i] <= max_gap
                and abs((v[i + 2] - v[i + 1]) - (v[i + 1] - v[i])) <= tol):
            out.append(v[i + 1]); i += 3
        else:
            out.append(v[i]); i += 1
    return out


def solve_bands(web_mm, folds_mm, tol=1.5):
    """Ricava fronte, fianco e falda longitudinale dalle pieghe.

    Su un flowpack la fasciatura e' simmetrica rispetto alla mezzeria del
    nastro, quindi le pieghe stanno a coppie speculari: quella esterna separa
    retro e fianco, quella interna fianco e fronte. Verificato su
    Milch-Schnitte, FULFIL e Kinder Bueno Dark.
    """
    mid = web_mm / 2.0
    pairs = []
    for a in folds_mm:
        if a >= mid:
            continue
        b = min((x for x in folds_mm if abs(x - (web_mm - a)) <= tol),
                key=lambda x: abs(x - (web_mm - a)), default=None)
        if b is not None:
            pairs.append((a, b))
    pairs.sort()

    best = None
    for i, (y1, y4) in enumerate(pairs):
        for y2, y3 in pairs[i + 1:]:
            T = ((y2 - y1) + (y4 - y3)) / 2.0
            front = y3 - y2
            fin = (y1 + web_mm - y4 - front) / 2.0
            if T <= 0 or front <= T or not (2.0 < fin < web_mm * 0.2):
                continue
            back_a, back_b = y1 - fin, (web_mm - fin) - y4
            if abs((back_a + back_b) - front) > tol:
                continue
            cand = dict(front=round(front, 2), thick=round(T, 2),
                        side_fin=round(fin, 2), back_a=round(back_a, 2),
                        back_b=round(back_b, 2), folds=(y1, y2, y3, y4))
            if best is None or cand["front"] > best["front"]:
                best = cand
    return best


def analyze_auto(pdf_path, page_no: int = 0):
    """Analisi automatica di un flowpack: nastro, passo, fasce e saldature.

    Copre gli impaginati in cui il disegno tecnico traccia le cordonature; per
    gli artwork che non rientrano resta il registro dei casi calibrati.
    """
    import pdfplumber
    import numpy as np
    import pypdfium2 as pdfium
    from .dieline import _segments, _technical_pens, _cluster

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no]
        segs = _segments(page)
        pens = _technical_pens(segs, page.width, page.height)
        S = [s for s in segs if s[4] in pens]
        H = [(c, b - a) for k, c, a, b, st in S if k == "H" and b - a > 150]
        V = [(c, b - a) for k, c, a, b, st in S if k == "V" and b - a > 150]
        hs = [c for c, w in _cluster(H, 3.0) if w > 250]
        vs = [c for c, w in _cluster(V, 3.0) if w > 250]
    if len(hs) < 4 or len(vs) < 2:
        raise ValueError("cordonature non riconosciute: impaginato non coperto")

    y0, y1 = min(hs), max(hs)
    x0, x1 = min(vs), max(vs)
    web, step = (y1 - y0) * PT2MM, (x1 - x0) * PT2MM
    folds = _collapse_guides([(c - y0) * PT2MM for c in hs])
    b = solve_bands(web, folds)
    if b is None:
        raise ValueError("fasce non risolvibili: nastro %.1f mm" % web)

    # pinne di testa: la zona non stampata e' quella che finisce nelle ganasce
    sc = 150 / 72.0
    im = pdfium.PdfDocument(pdf_path)[page_no].render(scale=sc).to_pil().convert("RGB")
    a = np.asarray(im).astype(int)
    fy0 = y0 + (b["side_fin"] + b["back_a"] + b["thick"]) / PT2MM
    fy1 = fy0 + b["front"] / PT2MM
    band = a[int(fy0 * sc):int(fy1 * sc), int(x0 * sc):int(x1 * sc)]
    ch = (band.max(2) - band.min(2)).mean(0)
    mm = np.arange(len(ch)) / sc * PT2MM
    idx = np.nonzero(ch > 25)[0]
    end_fin = round(float((mm[idx[0]] + (mm[-1] - mm[idx[-1]])) / 2.0), 1) if len(idx) else 0.0

    return Flowpack(W=b["front"], T=b["thick"], L=round(step - 2 * end_fin, 1),
                    end_fin=end_fin, side_fin=b["side_fin"],
                    back_a=b["back_a"], back_b=b["back_b"],
                    web_mm=round(web, 1), step_mm=round(step, 1),
                    sheet=(x0, y0, x1, y1),
                    girth_span=(y0 + b["side_fin"] / PT2MM, y1 - b["side_fin"] / PT2MM))
