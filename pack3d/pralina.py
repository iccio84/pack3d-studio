"""
La pralina incartata: una pralina avvolta in un quadrato di stagnola dorata
stropicciata, senza grafica, con un bollino ovale in cima e un pirottino di
carta plissettata sotto (regole/incarti.md, *La pralina avvolta*).

E' nata da un modello fatto a mano il 20 novembre 2026 e approvato dal
proprietario (pack3d-casi, `lavori/pralina`): la geometria qui e' quella
dello script approvato, numero per numero, con gli stessi semi. Le misure
vengono dalle foto del pack (la sagoma confrontata riga per riga con la foto
di lato), come la sagoma dell'uovo: la grafica dei due pezzi la danno i loro
file, un PDF o un'immagine.

- **La stagnola**: una sfera di 14,8 mm di raggio, stropicciata da 280
  pieghe lunghe e morbide (archi da 8 a 20 mm, sezione 1/cosh^2), liscia e
  appena schiacciata sotto il bollino. Oro satinato, metallo pieno, con la
  trama a rettangolini nella mappa delle normali.
- **Il pirottino**: la ciotola di carta a 52 pieghe, a dente di sega in
  basso e arrotondate in cima, col fondo piatto; due facce, 0,1 mm fra
  l'una e l'altra. La grafica e' il disco della carta stesa.
- **Il bollino**: l'ovale di 9,5 x 7,7 mm sulla cima, la grafica dritta.

Il fondo del pirottino sta a Y = 0, la cima in +Y; il davanti del bollino
(la testa della scritta) guarda -Z, come nel modello approvato.
"""
from __future__ import annotations

import io
import json
import struct

import numpy as np
from PIL import Image

# ---------------------------------------------------------------- misure ---
R = 14.8                       # raggio della pralina incartata: ~30 mm di stagnola
CY = 16.9                      # il suo centro
RB, H, RT = 10.6, 15.2, 17.6   # pirottino: raggio del fondo, altezza, raggio in cima
NPIEGHE = 52                   # le pieghe del pirottino
LA, LB = 4.75, 3.85            # semiassi del bollino (x, z): 9,5 x 7,7 mm
TOP = CY + R - 0.7             # la cima appena schiacciata sotto il bollino
TILE = 3.5                     # la tegola della trama a rettangolini, in mm
# l'ingombro del modello approvato, per i cartellini (lo da' `costruisci`)
LARGA, LARGO_PIROTTINO, ALTA = 31.6, 36.4, 31.1

# l'oro satinato della stagnola (sRGB), approvato: «trama piu' fitta, oro
# satinato»
ORO = (206, 166, 98)
METALLO, RUVIDO = 1.0, 0.46

# la grafica: un bollino e' piu' largo che alto (l'ovale), un pirottino e' un
# disco. Sotto questo rapporto fra i lati e' un disco
OVALE = 1.10
# la texture: il pirottino a sinistra, il bollino a destra in cima
LATO_PIROTTINO = 2048
BORDO = 16                     # pixel bianchi attorno al bollino nell'atlante
# il bollino largo 1024 px utili, come nel modello approvato
LATO_BOLLINO = 1024 + 2 * BORDO
# un pixel e' bianco (fuori dalla grafica) sopra questo valore in tutti i
# canali
BIANCO = 245


def _lineare(c):
    """sRGB 0-255 -> lineare 0-1, come vuole glTF per i colori pieni."""
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).tolist()


# ------------------------------------------------------------- la grafica ---
class Grafica:
    """La grafica di un pezzo: l'immagine ritagliata sulla sua parte stampata
    (`immagine`), cos'e' (`pezzo`: "bollino" o "pirottino"), da quale file e
    come si e' letta."""

    def __init__(self, immagine, pezzo, origine, nota):
        self.immagine = immagine
        self.pezzo = pezzo
        self.origine = origine
        self.nota = nota


def immagine_del_pdf(pdf, lato=2048):
    """L'immagine della prima pagina del PDF: se la pagina e' un'immagine
    sola (una grafica mandata come foto, che il server ha messo in un PDF:
    `famiglie.incarto.immagine_in_pdf`), quella, coi suoi pixel; se no la
    pagina resa con `lato` pixel sul lato lungo."""
    import pypdf
    r = pypdf.PdfReader(pdf)
    pg = r.pages[0]
    w, h = float(pg.mediabox.width), float(pg.mediabox.height)
    im = _immagine_sola(pg)
    if im is not None and abs(im.width / im.height - w / h) < 0.01 * (w / h):
        return im.convert("RGB"), "un'immagine di %d x %d px" % im.size
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        pagina = doc[0]
        scala = lato / max(w, h)
        im = pagina.render(scale=scala).to_pil().convert("RGB")
    finally:
        doc.close()
    return im, "la pagina resa a %d x %d px" % im.size


def _immagine_sola(pg):
    """L'immagine della pagina, se ne ha una sola, o None. Un JPEG coi suoi
    byte (pypdf lo ricomprimerebbe), le altre come le da' pypdf."""
    try:
        risorse = pg["/Resources"].get_object()
        xo = risorse.get("/XObject")
        xo = xo.get_object() if xo is not None else {}
        imm = [o.get_object() for o in xo.values()
               if o.get_object().get("/Subtype") == "/Image"]
        if len(imm) != 1:
            return None
        filtro = imm[0].get("/Filter")
        if filtro == "/DCTDecode":
            return Image.open(io.BytesIO(imm[0]._data))
        figure = list(pg.images)
        return figure[0].image if len(figure) == 1 else None
    except Exception:                    # noqa: BLE001
        return None


def stampato(im):
    """Il riquadro (x0, y0, x1, y1) della parte stampata: i pixel non
    bianchi. None se la pagina e' bianca."""
    a = np.asarray(im.convert("RGB"))
    pieno = (a < BIANCO).any(axis=2)
    righe, colonne = np.flatnonzero(pieno.any(axis=1)), np.flatnonzero(pieno.any(axis=0))
    if not len(righe):
        return None
    return int(colonne[0]), int(righe[0]), int(colonne[-1]) + 1, int(righe[-1]) + 1


def leggi(pdf, nome=""):
    """La `Grafica` di un pezzo dal suo PDF: ritagliata sulla parte
    stampata, il bollino se e' piu' larga che alta (un ovale), il pirottino
    se e' quadrata (un disco). Un ovale piu' alto che largo si gira di un
    quarto. ValueError se il file non ha niente di stampato."""
    im, come = immagine_del_pdf(pdf)
    box = stampato(im)
    if box is None:
        raise ValueError("pralina: %s e' bianco, non ha la grafica di un "
                         "pezzo" % (nome or "un file"))
    im = im.crop(box)
    giro = ""
    if im.height > im.width * OVALE:
        im = im.transpose(Image.Transpose.ROTATE_90)
        giro = ", girato di un quarto"
    pezzo = "bollino" if im.width > im.height * OVALE else "pirottino"
    return Grafica(im, pezzo, nome, "%s: %s, la parte stampata %d x %d px%s"
                   % (nome or "il file", come, im.width, im.height, giro))


def riconosci(pdfs, nomi=None):
    """`(bollino, pirottino)`, due `Grafica`, dai due file dei pezzi con la
    grafica, in qualunque ordine: ognuno dice da se' cos'e' (l'ovale e' il
    bollino, il disco il pirottino). ValueError se non sono uno e uno."""
    nomi = list(nomi or [])
    if len(pdfs) != 2:
        raise ValueError("pralina: servono due grafiche, il bollino e il "
                         "pirottino; ne sono arrivate %d" % len(pdfs))
    g = [leggi(p, nomi[k] if k < len(nomi) else "pezzo %d" % (k + 1))
         for k, p in enumerate(pdfs)]
    tipi = sorted(x.pezzo for x in g)
    if tipi != ["bollino", "pirottino"]:
        raise ValueError("pralina: le due grafiche sembrano tutte e due %s "
                         "(il bollino e' un ovale piu' largo che alto, il "
                         "pirottino il disco della carta stesa): %s"
                         % ("bollini" if tipi[0] == "bollino" else "pirottini",
                            "; ".join(x.nota for x in g)))
    bollino = next(x for x in g if x.pezzo == "bollino")
    pirottino = next(x for x in g if x.pezzo == "pirottino")
    return bollino, pirottino


def dichiara(bollino=None, pirottino=None):
    """I cartellini della pralina, per la lettura e i dettagli tecnici."""
    righe = ["pralina incartata: la stagnola dorata senza grafica, il bollino "
             "in cima, il pirottino plissettato sotto",
             "stagnola: circa %.1f mm, stropicciata, oro satinato" % LARGA,
             "pirottino: %d pieghe, circa %.1f mm in cima, alto %.1f; la "
             "pralina alta %.1f col bollino" % (NPIEGHE, LARGO_PIROTTINO, H, ALTA),
             "bollino: ovale %.1f x %.1f mm" % (2 * LA, 2 * LB),
             "le misure sono quelle del modello approvato (dalle foto del pack)"]
    for g in (bollino, pirottino):
        if g is not None:
            righe.append("%s: %s" % (g.pezzo, g.nota))
    return righe


# ------------------------------------------------------------ la stagnola ---
def icosfera(sub):
    """La sfera unitaria dall'icosaedro, `sub` volte divisa."""
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t),
         (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4),
         (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8),
         (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    for _ in range(sub):
        cache = {}
        NF = []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = V[a] + V[b]
                V.append(m / np.linalg.norm(m))
                cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            NF += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = NF
    return np.array(V), np.array(F)


def pieghe_lunghe(D, n, seme):
    """Pieghe lunghe e morbide sulla sfera unitaria `D`: archi da 8 a 20 mm,
    a sezione 1/cosh^2 (larghe 0,9-2,2 mm), che si assottigliano alle punte;
    creste e valli. Il 45% sale verso il bollino, come la stagnola raccolta
    in cima. Lo spostamento lungo il raggio, in mm."""
    g = np.random.default_rng(seme)
    out = np.zeros(len(D))
    for _ in range(n):
        # il punto di partenza, piu' spesso nella meta' alta
        p = g.normal(size=3)
        p[1] = abs(p[1]) * (1 if g.random() < 0.75 else -0.4)
        p /= np.linalg.norm(p)
        if g.random() < 0.45:          # verso la cima: lungo il meridiano
            t = np.array([0.0, 1.0, 0.0]) - p * p[1]
        else:
            t = np.cross(p, g.normal(size=3))
        t /= np.linalg.norm(t) + 1e-12
        L = g.uniform(8.0, 20.0) / R              # lunghezza in radianti
        w = g.uniform(0.45, 1.1) / R              # mezza larghezza
        a = g.uniform(0.22, 0.58) * g.choice([-1.0, 1.0], p=[0.45, 0.55])
        k = 8
        s_ = np.linspace(0, L, k + 1)
        pts = np.cos(s_)[:, None] * p + np.sin(s_)[:, None] * t   # l'arco
        best = np.full(len(D), np.inf)
        lungo = np.zeros(len(D))
        for j in range(k):
            A, B = pts[j], pts[j + 1]
            ab = B - A
            q = np.clip(((D - A) @ ab) / (ab @ ab), 0, 1)
            d = np.linalg.norm(D - (A + q[:, None] * ab), axis=1)
            m = d < best
            best[m] = d[m]
            lungo[m] = (j + q[m]) / k
        punta = np.sin(np.pi * np.clip(lungo, 0, 1)) ** 0.8
        out += a * punta / np.cosh(best / w) ** 2
    return out


def stagnola():
    """(P, F, UV) della stagnola: la sfera stropicciata, la cima appena
    bombata sotto il bollino (un minimo morbido, senza spigolo), e le UV
    della trama a rettangolini (azimutale equidistante dall'alto, in tegole:
    nessuna cucitura)."""
    rng = np.random.default_rng(7)
    D, F = icosfera(6)                       # ~82k triangoli
    P = D * R
    # un fondo appena ondulato, poi le pieghe lunghe
    fondo = np.zeros(len(D))
    for _k in range(12):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        fondo += np.sin(2 * np.pi * (P @ d) / rng.uniform(9, 16) + rng.uniform(0, 6.3))
    spost = 0.06 * fondo / fondo.std() + pieghe_lunghe(D, 280, 11)
    spost -= spost.mean()
    ang = np.arctan2(D[:, 2], D[:, 0])
    # sotto il bollino la stagnola e' schiacciata e liscia
    x, z = D[:, 0] * R, D[:, 2] * R
    e = (x / (LA + 1.2)) ** 2 + (z / (LB + 1.2)) ** 2
    liscio = np.clip((e - 0.75) / 0.6, 0, 1)
    liscio = np.where(D[:, 1] > 0, liscio, 1.0)
    rad = R + spost * liscio
    Pf = D * rad[:, None]
    Pf[:, 1] += CY
    cupola = TOP - 0.032 * (x ** 2 + z ** 2)          # la cima piatta, appena bombata
    kk = 0.5                                           # il minimo morbido
    Pf[:, 1] = -kk * np.logaddexp(-Pf[:, 1] / kk, -cupola / kk)
    arco = R * np.arccos(np.clip(D[:, 1], -1, 1))
    UV = np.stack([arco * np.cos(ang) / TILE, arco * np.sin(ang) / TILE], -1)
    return Pf, F, UV


# ----------------------------------------------------------- il pirottino ---
def pirottino():
    """(P, F, UV) del pirottino, con le due facce della carta. Le UV vanno
    sul disco della carta stesa, nel quadrato [0, 1]: il raggio di carta dal
    centro del fondo, 2% in piu' del piu' lungo, e' il bordo del quadrato."""
    NA, NH, NB = NPIEGHE * 4, 22, 10
    th = np.linspace(0, 2 * np.pi, NA + 1)
    t = np.linspace(0, 1, NH)
    TT, TH = np.meshgrid(t, th, indexing="ij")
    onda = 2 * np.abs((TH * NPIEGHE / (2 * np.pi)) % 1 - 0.5)   # i triangolini
    # in cima la piega si arrotonda: il bordo ondeggia senza punte
    onda = (1 - 0.4 * TT ** 2) * onda + 0.4 * TT ** 2 * (0.5 + 0.5 * np.cos(TH * NPIEGHE))
    r0 = RB + (RT - RB) * (TT ** 0.75)     # a ciotola, come in foto
    amp = 0.25 + 0.95 * TT ** 1.2
    rr = r0 + amp * (onda - 0.5)
    yy = H * TT + 0.15 * TT ** 3 * (onda - 0.5)
    Pw = np.stack([rr * np.cos(TH), yy, rr * np.sin(TH)], -1).reshape(-1, 3)
    # la lunghezza della carta dal centro del disco, per la grafica stesa
    dl = np.sqrt(np.diff(rr, axis=0) ** 2 + np.diff(yy, axis=0) ** 2)
    s = RB + np.vstack([np.zeros((1, NA + 1)), np.cumsum(dl, 0)])
    smax = s.max() * 1.02
    Ww = np.stack([0.5 + 0.5 * s / smax * np.cos(TH),
                   0.5 - 0.5 * s / smax * np.sin(TH)], -1).reshape(-1, 2)
    Fw = []
    for i in range(NH - 1):
        for j in range(NA):
            a = i * (NA + 1) + j
            b, c = a + 1, a + NA + 1
            Fw += [(a, c, b), (b, c, c + 1)]
    Fw = np.array(Fw)
    # il fondo: un disco, appena ondulato sul bordo
    rb = np.linspace(0, 1, NB)
    RBB, THB = np.meshgrid(rb, th, indexing="ij")
    rB = RB * RBB + 0.25 * RBB ** 4 * (2 * np.abs((THB * NPIEGHE / (2 * np.pi)) % 1 - 0.5) - 0.5)
    Pb = np.stack([rB * np.cos(THB), np.zeros_like(rB) + 0.02, rB * np.sin(THB)], -1).reshape(-1, 3)
    sB = RB * RBB
    Wb = np.stack([0.5 + 0.5 * sB / smax * np.cos(THB),
                   0.5 - 0.5 * sB / smax * np.sin(THB)], -1).reshape(-1, 2)
    Fb = []
    for i in range(NB - 1):
        for j in range(NA):
            a = i * (NA + 1) + j
            b, c = a + 1, a + NA + 1
            Fb += [(a, b, c), (b, c + 1, c)]
    Fb = np.array(Fb) + len(Pw)
    Pc, Wc, Fc = np.vstack([Pw, Pb]), np.vstack([Ww, Wb]), np.vstack([Fw, Fb])
    # la carta ha due facce: dentro, una copia spostata di 0,1 mm verso
    # l'interno, coi triangoli al contrario (i visori che scartano il retro
    # la mostravano bucata)
    n = np.zeros_like(Pc)
    fn = np.cross(Pc[Fc[:, 1]] - Pc[Fc[:, 0]], Pc[Fc[:, 2]] - Pc[Fc[:, 0]])
    for k in range(3):
        np.add.at(n, Fc[:, k], fn)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    verso = np.where(((Pc - np.array([0, 20.0, 0])) * n).sum(1, keepdims=True) > 0, 1.0, -1.0)
    Pin = Pc - n * 0.1 * verso
    return (np.vstack([Pc, Pin]), np.vstack([Fc, Fc[:, ::-1] + len(Pin)]),
            np.vstack([Wc, Wc]))


# ------------------------------------------------------------- il bollino ---
def bollino():
    """(P, F, UV) del bollino: l'ovale sulla cima, 0,14 mm sopra la
    stagnola. Le UV nel riquadro [0, 1] dell'ovale, la testa della grafica
    verso -Z."""
    NR, NT = 14, 128
    rr_ = np.linspace(0, 1, NR)
    tt_ = np.linspace(0, 2 * np.pi, NT + 1)
    RR_, TT_ = np.meshgrid(rr_, tt_, indexing="ij")
    xl, zl = LA * RR_ * np.cos(TT_), LB * RR_ * np.sin(TT_)
    yl = TOP - 0.032 * (xl ** 2 + zl ** 2) + 0.14
    P = np.stack([xl, yl, zl], -1).reshape(-1, 3)
    UV = np.stack([0.5 + 0.5 * xl / LA, 0.5 + 0.5 * zl / LB], -1).reshape(-1, 2)
    F = []
    for i in range(NR - 1):
        for j in range(NT):
            a = i * (NT + 1) + j
            b, c = a + 1, a + NT + 1
            F += [(a, b, c), (b, c + 1, c)]
    return P, np.array(F), UV


# ------------------------------------------------------- texture e mappe ---
def atlante(bol, pir):
    """(immagine, mappa_pirottino, mappa_bollino): le due grafiche in una
    texture sola, perche' Glam ne mette una su tutto il modello e il template
    e' la sua tela. Il pirottino a sinistra, quadrato; il bollino a destra in
    cima, coi pixel bianchi attorno. Ogni mappa porta le UV [0, 1] di un pezzo
    nell'atlante."""
    lp, lb = LATO_PIROTTINO, LATO_BOLLINO
    W, Ht = lp + lb, lp
    atl = Image.new("RGB", (W, Ht), (255, 255, 255))
    atl.paste(pir.convert("RGB").resize((lp, lp), Image.LANCZOS), (0, 0))
    wb = lb - 2 * BORDO
    hb = max(1, round(wb * bol.height / bol.width))
    atl.paste(bol.convert("RGB").resize((wb, hb), Image.LANCZOS), (lp + BORDO, BORDO))

    def m_pir(uv):
        return np.stack([uv[:, 0] * lp / W, uv[:, 1] * lp / Ht], -1)

    def m_bol(uv):
        return np.stack([(lp + BORDO + uv[:, 0] * wb) / W,
                         (BORDO + uv[:, 1] * hb) / Ht], -1)
    return atl, m_pir, m_bol


def normal_rettangolini(px=512, nx=10, ny=14, forza=2.0):
    """La trama a rettangolini della stagnola: una tegola di 10 x 14
    rettangolini appena bombati, coi solchi fra l'uno e l'altro."""
    yy_, xx_ = np.mgrid[0:px, 0:px] / px
    cx, cy = (xx_ * nx) % 1, (yy_ * ny) % 1
    hx, hy = np.minimum(cx, 1 - cx) * 2, np.minimum(cy, 1 - cy) * 2
    h = np.minimum(np.clip(hx / 0.25, 0, 1), np.clip(hy / 0.25, 0, 1)) ** 0.7
    h += 0.25 * (1 - (2 * cx - 1) ** 2) * (1 - (2 * cy - 1) ** 2)
    gy, gx = np.gradient(h * forza)
    n = np.stack([-gx * px / 40, -gy * px / 40, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))


# ------------------------------------------------------------------- GLB ---
def _piatte(P, F, W):
    """Vertici non condivisi: la normale di ogni faccetta (le pieghe nette
    della carta)."""
    Q = P[F].reshape(-1, 3)
    n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return Q, np.repeat(n, 3, axis=0), W[F].reshape(-1, 2), np.arange(len(Q)).reshape(-1, 3)


def _lisce(P, F, W):
    n = np.zeros_like(P)
    fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    for k in range(3):
        np.add.at(n, F[:, k], fn)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return P, n, W, F


def scrivi_glb(uscita, parti, atl, nmap, tex_max=4096, qualita=90):
    """Il GLB: tre mesh (`parti`: `[(nome, Q, N, UV, T, materiale)]`), la
    texture dell'atlante per il pirottino e il bollino, la stagnola di
    colore pieno con la trama ripetuta nella mappa delle normali."""
    buf = bytearray()
    views, acc = [], []

    def vista(b, tgt=None):
        while len(buf) % 4:
            buf.append(0)
        v = {"buffer": 0, "byteOffset": len(buf), "byteLength": len(b)}
        if tgt:
            v["target"] = tgt
        buf.extend(b)
        views.append(v)
        return len(views) - 1

    def accessor(a, tipo, comp=5126, tgt=34962, mm=False):
        d = {"bufferView": vista(a.tobytes(), tgt), "componentType": comp,
             "count": len(a), "type": tipo}
        if mm:
            d["min"], d["max"] = a.min(0).tolist(), a.max(0).tolist()
        acc.append(d)
        return len(acc) - 1

    imgs, texs = [], []

    def immagine(im, fmt, sampler):
        bio = io.BytesIO()
        im.convert("RGB").save(bio, fmt, **({"quality": qualita, "subsampling": 0}
                                             if fmt == "JPEG" else {}))
        imgs.append({"bufferView": vista(bio.getvalue()), "mimeType": "image/" + fmt.lower()})
        texs.append({"source": len(imgs) - 1, "sampler": sampler})
        return len(texs) - 1

    if max(atl.size) > tex_max:
        r = tex_max / max(atl.size)
        atl = atl.resize((int(atl.width * r), int(atl.height * r)), Image.LANCZOS)
    t_atl = immagine(atl, "JPEG", 0)
    t_norm = immagine(nmap, "PNG", 1)
    mats = {
        "stagnola": {"name": "stagnola", "pbrMetallicRoughness": {
            "baseColorFactor": _lineare(ORO) + [1], "metallicFactor": METALLO,
            "roughnessFactor": RUVIDO},
            "normalTexture": {"index": t_norm, "scale": 0.55}},
        "pirottino": {"name": "pirottino", "doubleSided": True, "pbrMetallicRoughness": {
            "baseColorTexture": {"index": t_atl}, "metallicFactor": 0.0,
            "roughnessFactor": 0.55}},
        "bollino": {"name": "bollino", "pbrMetallicRoughness": {
            "baseColorTexture": {"index": t_atl}, "metallicFactor": 0.0,
            "roughnessFactor": 0.45}},
    }
    nomi_mat = list(mats)
    meshes = []
    for nome, Q, N, UV, T, mat in parti:
        a = {"POSITION": accessor((Q / 1000).astype(np.float32), "VEC3", mm=True),
             "NORMAL": accessor(N.astype(np.float32), "VEC3"),
             "TEXCOORD_0": accessor(UV.astype(np.float32), "VEC2")}
        ix = accessor(T.astype(np.uint32).ravel(), "SCALAR", 5125, 34963)
        meshes.append({"name": nome, "primitives": [{"attributes": a, "indices": ix,
                                                     "material": nomi_mat.index(mat)}]})
    g = {"asset": {"version": "2.0", "generator": "pack3d pralina"}, "scene": 0,
         "scenes": [{"nodes": list(range(len(meshes)))}],
         "nodes": [{"mesh": k, "name": m["name"]} for k, m in enumerate(meshes)],
         "meshes": meshes, "materials": [mats[m] for m in nomi_mat],
         "textures": texs, "images": imgs,
         "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071},
                      {"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
         "accessors": acc, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bb = bytes(buf) + b"\0" * ((4 - len(buf) % 4) % 4)
    with open(uscita, "wb") as fh:
        fh.write(b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(bb)))
        fh.write(struct.pack("<I", len(js)) + b"JSON" + js)
        fh.write(struct.pack("<I", len(bb)) + b"BIN\0" + bb)


def costruisci(bol, pir, uscita, tex_max=4096):
    """Il GLB della pralina dalle due `Grafica` (il bollino e il pirottino).
    I cartellini della costruzione."""
    atl, m_pir, m_bol = atlante(bol.immagine, pir.immagine)
    Pf, Ff, UVf = stagnola()
    Pc, Fc, Wc = pirottino()
    Pl, Fl, Wl = bollino()
    parti = [("stagnola",) + _lisce(Pf, Ff, UVf) + ("stagnola",),
             ("pirottino",) + _piatte(Pc, Fc, m_pir(Wc)) + ("pirottino",),
             ("bollino",) + _lisce(Pl, Fl, m_bol(Wl)) + ("bollino",)]
    scrivi_glb(uscita, parti, atl, normal_rettangolini(), tex_max=tex_max)
    return dichiara(bol, pir)
