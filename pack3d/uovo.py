"""
L'incarto avvolto: l'uovo di cioccolato incartato col collarino.

Il foglio quadrato di film avvolge tutto l'uovo, si raccoglie sopra in un
collo e si apre in un ciuffo di quattro petali; il collarino di cartoncino
stringe il collo e gli fa l'ovale sul davanti. Arriva in due PDF, in
qualunque ordine: il foglio (il DT e' un quadrato) e il collarino (un ovale
con le due braccia). In ogni PDF il DT si ripete in piu' viste, una per
lastra: la prima e' la grafica, poi le lastre degli effetti - per il foglio
il bianco (il film metallizzato resta a vista dove non c'e' il bianco), per
il collarino la vernice lucida e il rilievo. L'oro del collarino e' la lamina
a freddo: si riconosce dal colore. Vedi regole/incarti.md, *L'uovo avvolto*.

Ogni colonna del foglio sta in un suo semipiano verticale attorno all'asse
(un angolo per colonna, che cresce nel giro): due colonne diverse non si
toccano mai, e il foglio non puo' attraversare se stesso. Le pieghe e le
grinze spostano i punti dentro il loro semipiano, mai fuori, e non piu' del
raggio della curva (la colonna non si ripiega). In alto il davanti e il
dietro si chiudono uno verso l'altro: z si stringe con l'altezza, una
deformazione dello spazio che non crea intersezioni. Il rovescio del foglio
sta sugli stessi vertici della stampa. Il collarino sta sempre fuori dal
foglio.

La sagoma dell'uovo e quella del ciuffo vengono dalle foto del primo caso
(l'uovo appoggia sulla valva con un fondo piatto); il foglio e il collarino
vengono dai PDF. Il fronte guarda +Z, la cima +Y, il fondo sta a Y = 0.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass, field

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as R
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from . import exporters
from . import rilievo
from .materiali import _lineare, _srgb

MM = 25.4 / 72.0



# ---------------------------------------------------------------- il PDF: gli strati, le zone, la resa
def _strato(h):
    """Il nome dello strato (contenuto facoltativo, /OC) di un oggetto della
    pagina di pdfium, o None se non sta in uno strato."""
    import ctypes
    import pypdfium2.raw as R
    for i in range(R.FPDFPageObj_CountMarks(h)):
        mk = R.FPDFPageObj_GetMark(h, i)
        buf = (ctypes.c_ushort * 512)()
        n = ctypes.c_ulong()
        if R.FPDFPageObjMark_GetParamStringValue(mk, b"Title", buf, 1024, ctypes.byref(n)):
            return bytes(buf)[:n.value].decode("utf-16-le").rstrip("\x00")
    return None


class _Griglia:
    """La pagina in pixel (`px` pixel per mm) sul riquadro `zona` (mm)."""

    def __init__(self, zona, px_mm=1.0):
        self.zona = tuple(float(v) for v in zona)
        self.px = float(px_mm)
        self.W = int(np.ceil((self.zona[2] - self.zona[0]) * self.px))
        self.H = int(np.ceil((self.zona[3] - self.zona[1]) * self.px))



def _rendi(pg, griglia):
    PT = 1.0 / MM
    W, Hh = pg.get_size()
    x0, y0, x1, y1 = griglia.zona
    im = pg.render(scale=griglia.px / PT,
                   crop=(x0 * PT, Hh - y1 * PT, W - x1 * PT, y0 * PT)).to_pil()
    return im.convert("RGB").resize((griglia.W, griglia.H))


def contorni(masc):
    """Gli anelli del contorno di una maschera, in pixel (x, y) sui bordi dei
    pixel: un anello per ogni bordo chiuso, il cartone a destra di chi lo
    percorre. Sono a gradini: `aggancia` li porta sulle linee vere."""
    m = np.pad(np.asarray(masc, bool), 1)
    dentro = m[1:-1, 1:-1]
    i, j = np.nonzero(dentro)
    uscite = {}

    def lato(a, b):
        uscite.setdefault(a, []).append(b)

    for di, dj, da, db in ((-1, 0, (0, 0), (1, 0)), (0, 1, (1, 0), (1, 1)),
                           (1, 0, (1, 1), (0, 1)), (0, -1, (0, 1), (0, 0))):
        fuori = ~m[1 + i + di, 1 + j + dj]
        for ii, jj in zip(i[fuori], j[fuori]):
            lato((jj + da[0], ii + da[1]), (jj + db[0], ii + db[1]))
    anelli = []
    while uscite:
        inizio = next(iter(uscite))
        anello = [inizio]
        prec = None
        cur = inizio
        while True:
            lista = uscite.get(cur)
            if not lista:
                break
            if len(lista) > 1 and prec is not None:
                # a un incrocio (due pixel in diagonale) si gira a destra:
                # il cartone resta da una parte sola e gli anelli non si toccano
                dx0, dy0 = cur[0] - prec[0], cur[1] - prec[1]

                def svolta(b):
                    dx1, dy1 = b[0] - cur[0], b[1] - cur[1]
                    return -(dx0 * dy1 - dy0 * dx1)
                lista.sort(key=svolta)
            nxt = lista.pop()
            if not lista:
                del uscite[cur]
            prec, cur = cur, nxt
            if cur == inizio:
                break
            anello.append(cur)
        if len(anello) >= 4:
            anelli.append(np.array(anello, float))
    return anelli


def _campiona(polilinee, passo=0.25):
    """I punti delle polilinee, uno ogni `passo` mm."""
    pts = []
    for pl in polilinee:
        a = np.asarray(pl, float)
        for p, q in zip(a[:-1], a[1:]):
            n = max(1, int(np.ceil(np.hypot(*(q - p)) / passo)))
            t = np.linspace(0.0, 1.0, n + 1)[:, None]
            pts.append(p + (q - p) * t)
    return np.vstack(pts) if pts else np.zeros((0, 2))


def _douglas(a, tol):
    """Douglas-Peucker su un tratto aperto."""
    if len(a) < 3:
        return a
    p, q = a[0], a[-1]
    d = q - p
    L = float(np.hypot(*d))
    if L < 1e-9:
        dist = np.hypot(*(a - p).T)
    else:
        dist = np.abs(d[0] * (a[:, 1] - p[1]) - d[1] * (a[:, 0] - p[0])) / L
    k = int(np.argmax(dist))
    if dist[k] <= tol:
        return np.array([p, q])
    return np.vstack([_douglas(a[:k + 1], tol)[:-1], _douglas(a[k:], tol)])


def semplifica(anello, tol=0.15):
    """Un anello chiuso con meno punti: via quelli che stanno sulla linea
    dei vicini entro `tol` mm. Le curve tengono i loro punti."""
    a = np.asarray(anello, float)
    if len(a) < 4:
        return a
    # si parte dal punto piu' lontano dal primo, cosi' i due tratti sono buoni
    k = int(np.argmax(np.hypot(*(a - a[0]).T)))
    uno = _douglas(np.vstack([a[:k + 1]]), tol)
    due = _douglas(np.vstack([a[k:], a[:1]]), tol)
    return np.vstack([uno[:-1], due[:-1]])


def triangola(anelli, extra=None, griglia=None, giri=14, minimo=0.2):
    """(punti Nx2, triangoli Mx3) del poligono: il primo anello e' il
    contorno, gli altri i buchi (pari-dispari, il verso non conta). Come
    `ballotin.triangola`, che il POP usa e non cambia, con in piu' i punti
    `extra` (i campioni dei solchi delle incisioni) e una griglia dentro
    solo se si chiede. I lati del contorno che Delaunay non tiene si
    spezzano a meta' finche' ci sono tutti; si tengono i triangoli col
    baricentro dentro."""
    from scipy.spatial import Delaunay, cKDTree
    from .ballotin import _pulisci, dentro
    anelli = [_pulisci(np.asarray(a, float)) for a in anelli]
    anelli = [a for a in anelli if len(a) >= 3]
    if not anelli:
        return np.zeros((0, 2)), np.zeros((0, 3), int)
    lati, pts = [], []
    for an in anelli:
        base = len(pts)
        pts.extend(an)
        lati.extend((base + i, base + (i + 1) % len(an)) for i in range(len(an)))
    pts = np.array(pts)
    lo, hi = pts.min(0), pts.max(0)
    bordo = cKDTree(_campiona([np.vstack([a, a[:1]]) for a in anelli], 0.2))
    aggiunti = []
    if griglia:
        xs = np.arange(lo[0] + griglia / 2, hi[0], griglia)
        ys = np.arange(lo[1] + griglia / 2, hi[1], griglia)
        if len(xs) and len(ys):
            aggiunti.append(np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2))
    if extra is not None and len(extra):
        aggiunti.append(np.asarray(extra, float))
    if aggiunti:
        g = np.vstack(aggiunti)
        g = g[dentro(g, anelli)]
        if len(g):
            d, _ = bordo.query(g)
            g = g[d > 0.12]
            if len(g):
                pts = np.vstack([pts, np.unique(np.round(g / 1e-3).astype(np.int64), axis=0) * 1e-3])
    m = 10.0
    cornice = np.array([[lo[0] - m, lo[1] - m], [hi[0] + m, lo[1] - m],
                        [hi[0] + m, hi[1] + m], [lo[0] - m, hi[1] + m]])
    pts = np.vstack([pts, cornice])
    for _ in range(giri):
        tri = Delaunay(pts).simplices
        presenti = set()
        for a, b, c in tri:
            presenti.update(((min(a, b), max(a, b)), (min(b, c), max(b, c)),
                             (min(c, a), max(c, a))))
        # un lato piu' corto di `minimo` non si spezza piu': i due bordi di
        # un taglio dentro il pannello stanno sulla stessa linea, e quel lato
        # Delaunay non lo tiene mai - spezzato a ogni giro, un pannello
        # arrivava a centomila triangoli
        mancano = [(u, v) for u, v in lati if (min(u, v), max(u, v)) not in presenti
                   and np.hypot(*(pts[u] - pts[v])) > minimo]
        if not mancano:
            break
        nuovi, punti = [], []
        for u, v in mancano:
            k = len(pts) + len(punti)
            punti.append((pts[u] + pts[v]) / 2)
            nuovi += [(u, k), (k, v)]
        via = set(mancano)
        lati = [l for l in lati if l not in via] + nuovi
        pts = np.vstack([pts, np.array(punti)])
    tri = Delaunay(pts).simplices
    tri = tri[dentro(pts[tri].mean(1), anelli)]
    usati, nuovo = np.unique(tri, return_inverse=True)
    return pts[usati], nuovo.reshape(tri.shape)


ARANCIO = (224, 103, 39)


class Pagina:
    def __init__(self, pdf):
        self.doc = pdfium.PdfDocument(pdf)
        self.pg = self.doc[0]
        self.H = self.pg.get_size()[1]
        self.ogg = list(self.pg.get_objects(max_depth=0))
        self.strato = [_strato(o.raw) for o in self.ogg]

    def riquadro(self, o):
        l, b, r, t = (ctypes.c_float() for _ in range(4))
        R.FPDFPageObj_GetBounds(o.raw, *(ctypes.byref(v) for v in (l, b, r, t)))
        return (l.value * MM, (self.H - t.value) * MM, r.value * MM, (self.H - b.value) * MM)

    def colori(self, o):
        c = [ctypes.c_uint() for _ in range(4)]
        fm, st = ctypes.c_int(), ctypes.c_int()
        if o.type == 2:
            R.FPDFPath_GetDrawMode(o.raw, ctypes.byref(fm), ctypes.byref(st))
        R.FPDFPageObj_GetFillColor(o.raw, *(ctypes.byref(v) for v in c))
        f = tuple(v.value for v in c[:3]) if fm.value else None
        R.FPDFPageObj_GetStrokeColor(o.raw, *(ctypes.byref(v) for v in c))
        s = tuple(v.value for v in c[:3]) if st.value else None
        return f, s

    def rendi(self, zona, px_mm, via=("notes", "technical-drawing")):
        """La zona (mm) senza gli strati `via`, spostati fuori pagina."""
        prima = []
        for o, s in zip(self.ogg, self.strato):
            if s in via:
                m = R.FS_MATRIX()
                R.FPDFPageObj_GetMatrix(o.raw, m)
                prima.append((o.raw, m))
                R.FPDFPageObj_Transform(o.raw, 1, 0, 0, 1, 1e5, 1e5)
        try:
            G = _Griglia(zona, px_mm)
            return _rendi(self.pg, G)
        finally:
            for h, m in prima:
                R.FPDFPageObj_SetMatrix(h, m)

    def rendi_tutto(self, zona, px_mm):
        return _rendi(self.pg, _Griglia(zona, px_mm))

    def zone_testo(self):
        """[(riquadro)] delle zone di testo arancioni (note)."""
        out = []
        for o, s in zip(self.ogg, self.strato):
            if s == "notes" and o.type == 2 and self.colori(o)[0] == ARANCIO:
                out.append(self.riquadro(o))
        return out

    def linee_note(self):
        out = []
        for o, s in zip(self.ogg, self.strato):
            if s != "notes" or o.type != 2:
                continue
            f, st = self.colori(o)
            if f is None and st is not None:
                out.append(self.riquadro(o))
        return out


def campione(pag, box, px_mm=12.0):
    box = (box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1)
    """Il testo d'esempio nel riquadro della nota: RGBA, solo i pixel colorati
    (il nero e il grigio della descrizione no)."""
    im = np.asarray(pag.rendi_tutto(box, px_mm), np.int16)
    croma = im.max(-1) - im.min(-1)
    alfa = np.clip((croma.astype(np.float32) - 18.0) * 255.0 / 40.0, 0, 255).astype(np.uint8)
    ys, xs = np.nonzero(alfa > 60)
    if not len(ys):
        return None
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([im.astype(np.uint8), alfa])[y0:y1, x0:x1]
    return Image.fromarray(rgba, "RGBA")


def riquadri_note(pag):
    """I riquadri delle note: rettangoli fatti da tre o quattro linee nere."""
    linee = pag.linee_note()
    h = [l for l in linee if l[3] - l[1] < 1.0 and l[2] - l[0] > 30]
    v = [l for l in linee if l[2] - l[0] < 1.0 and l[3] - l[1] > 30]
    out = []
    for a in h:
        for b in h:
            if b[1] > a[1] + 30 and abs(a[0] - b[0]) < 3:
                for c in v:
                    if abs(c[0] - a[0]) < 3 and abs(c[1] - a[1]) < 3 and abs(c[3] - b[1]) < 3:
                        out.append((a[0], a[1], max(a[2], b[2]), b[3]))
    # anche il riquadro largo sopra (incarto): un rettangolo intero
    for l in linee:
        if l[2] - l[0] > 300 and l[3] - l[1] > 40:
            out.append(l)
    return out


def guide(pag, pdf):
    """Le linee guida: i segmenti obliqui neri, coi loro due capi (mm)."""
    import pdfplumber
    out = []
    with pdfplumber.open(pdf) as doc:
        pg = doc.pages[0]
        for o in pg.lines + pg.curves:
            pts = o.get("pts") or []
            if len(pts) != 2:
                continue
            (x0, y0), (x1, y1) = [(float(x) * MM, float(y) * MM) for x, y in pts]
            if abs(x1 - x0) > 3 and abs(y1 - y0) > 3 and np.hypot(x1 - x0, y1 - y0) > 15:
                out.append(((x0, y0), (x1, y1)))
    return out


def colorati(pag):
    """[(riquadro, colore)] degli oggetti colorati delle note (i testi
    d'esempio), non le zone arancioni."""
    out = []
    for o, s in zip(pag.ogg, pag.strato):
        if s != "notes":
            continue
        f, st = pag.colori(o)
        for c in (f, st):
            if c and c != ARANCIO and max(c) - min(c) > 25:
                out.append((pag.riquadro(o), c))
                break
    return out


def _dentro(p, r, m):
    return r[0] - m <= p[0] <= r[2] + m and r[1] - m <= p[1] <= r[3] + m


def _unione(rr):
    return (min(r[0] for r in rr), min(r[1] for r in rr), max(r[2] for r in rr), max(r[3] for r in rr))


def abbina(pag, pdf, zone, riquadri):
    """{zona: riquadro del testo d'esempio}: la guida parte dalla zona e
    arriva al riquadro della nota, o al testo d'esempio senza riquadro."""
    col = colorati(pag)
    out = {}
    for P, Q in guide(pag, pdf):
        for A, B in ((P, Q), (Q, P)):
            zz = [z for z in zone if _dentro(A, z, 6.0)]
            if not zz:
                continue
            z = zz[0]
            qq = [q for q in riquadri if _dentro(B, q, 4.0)]
            if qq:
                dentro = [r for r, c in col if _dentro(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), qq[0], 0)]
                if dentro:
                    out.setdefault(z, _unione(dentro))
                continue
            # senza riquadro: il gruppo di oggetti colorati vicino al capo
            vicini = [r for r, c in col if not any(_dentro(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), w, 0) for w in zone)]
            if not vicini:
                continue
            dist = [np.hypot(max(r[0] - B[0], 0, B[0] - r[2]), max(r[1] - B[1], 0, B[1] - r[3])) for r in vicini]
            k = int(np.argmin(dist))
            if dist[k] > 15:
                continue
            gruppo = [vicini[k]]
            cresce = True
            while cresce:
                cresce = False
                g = _unione(gruppo)
                for r in vicini:
                    if r not in gruppo and r[0] < g[2] + 6 and g[0] < r[2] + 6 and r[1] < g[3] + 6 and g[1] < r[3] + 6:
                        gruppo.append(r)
                        cresce = True
            out.setdefault(z, _unione(gruppo))
    return out


def incolla(im, zona_px, camp, girare=0):
    """Il campione dentro la zona (pixel dell'immagine), centrato e intero."""
    if girare:
        camp = camp.rotate(girare, expand=True)
    x0, y0, x1, y1 = zona_px
    W, H = x1 - x0, y1 - y0
    s = min(W / camp.width, H / camp.height)
    c = camp.resize((max(1, int(camp.width * s)), max(1, int(camp.height * s))), Image.LANCZOS)
    im.alpha_composite(c, (int(x0 + (W - c.width) / 2), int(y0 + (H - c.height) / 2)))


def grafica_vista(pag, zona, px_mm, zone_abbinate, colore=True):
    """La vista resa, con i testi d'esempio nelle zone di testo."""
    im = pag.rendi(zona, px_mm).convert("RGBA")
    if not colore:
        im = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for z, q in zone_abbinate.items():
        if not (zona[0] <= z[0] and z[2] <= zona[2] and zona[1] <= z[1] and z[3] <= zona[3]):
            continue
        camp = campione(pag, q)
        if camp is None:
            continue
        zp = tuple(int(round(v)) for v in ((z[0] - zona[0]) * px_mm, (z[1] - zona[1]) * px_mm,
                                            (z[2] - zona[0]) * px_mm, (z[3] - zona[1]) * px_mm))
        girare = 0
        if (z[3] - z[1]) > 3 * (z[2] - z[0]) and camp.width > camp.height:
            # una striscia verticale: il testo gira come le colonne vicine
            girare = 90 if (z[0] + z[2]) / 2 < (zona[0] + zona[2]) / 2 else -90
        incolla(im, zp, camp, girare)
    return im

# ---------------------------------------------------------------- il foglio
def bordo(ang):
    return (LATO / 2) / np.maximum(np.maximum(np.abs(np.cos(ang)), np.abs(np.sin(ang))), 1e-6)


def uv_foglio(rho, ang):
    """Il punto del foglio (raggio, angolo) in uv del foglio, 0..1."""
    return np.stack([(LATO / 2 + rho * np.cos(ang)) / LATO, (LATO / 2 + rho * np.sin(ang)) / LATO], -1)


def _liscia(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _onda(x):
    """Onda a punta, fra -1 e 1: la piega del film."""
    return (2 / np.pi) * np.arcsin(np.sin(x))


def _pieghe_creste(rng, n):
    """Le grinze grandi: creste e valli dritte, finite, sparse sul foglio."""
    ang = rng.uniform(0, 2 * np.pi, n * 3)
    rr = np.sqrt(rng.uniform(RHO_K ** 2, (LATO * 0.71) ** 2, n * 3))
    c = np.stack([rr * np.cos(ang), rr * np.sin(ang)], 1)
    dentro = (np.abs(c) < LATO / 2).all(1)
    c = c[dentro][:n]
    d = rng.uniform(0, np.pi, len(c))
    e = np.stack([np.cos(d), np.sin(d)], 1)
    lung = rng.uniform(30, 150, len(c))
    larg = rng.uniform(5, 24, len(c))
    alt = rng.choice([-1, 1], len(c)) * rng.uniform(0.12, 0.32, len(c)) * larg
    return c, e, lung, larg, alt


def _grinze(p, creste):
    """L'altezza delle grinze (mm) nei punti p del foglio (mm dal centro)."""
    c, e, lung, larg, alt = creste
    out = np.zeros(len(p))
    for k in range(len(c)):
        q = p - c[k]
        lungo = q @ e[k]
        trav = q[:, 0] * -e[k, 1] + q[:, 1] * e[k, 0]
        m = (np.abs(lungo) < lung[k]) & (np.abs(trav) < larg[k])
        if not m.any():
            continue
        f = (1 - np.abs(trav[m]) / larg[k]) * (1 - (lungo[m] / lung[k]) ** 2) ** 2
        out[m] += alt[k] * f
    return out


# ---------------------------------------------------------------- le grinze fini
def faccette(rho_px, ang_px, rng, forza=1.0):
    """Le grinze fini del film: faccette piane inclinate a caso (due
    misure), come una mappa delle normali. Sull'uovo il film e' liscio."""
    # le grinze del film raccolto corrono dal collo verso il bordo: le
    # faccette sono lunghe nel raggio e strette nel giro
    p = np.stack([rho_px * 0.32, rho_px * ang_px], -1).reshape(-1, 2)
    gx = np.zeros(len(p))
    gy = np.zeros(len(p))
    for passo, sigma in ((26.0, 0.16), (9.0, 0.07)):
        n = int((LATO / passo) ** 2)
        semi = np.stack([rng.uniform(0, LATO * 0.71 * 0.32, n), rng.uniform(-np.pi * LATO * 0.71, np.pi * LATO * 0.71, n)], 1)
        n = len(semi)
        _d, i = cKDTree(semi).query(p, workers=-1)
        tx, ty = rng.normal(0, sigma * forza, n), rng.normal(0, sigma * forza, n)
        gx += tx[i]
        gy += ty[i]
    peso = _liscia((rho_px.reshape(-1) - (RHO_K - 25)) / 50.0)
    n = np.stack([-gx * peso, gy * peso, np.ones(len(p))], -1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    return np.round((n * 0.5 + 0.5) * 255).astype(np.uint8)


def normali(V, T):
    n = np.zeros_like(V)
    f = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    for k in range(3):
        np.add.at(n, T[:, k], f)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


def collarino_maschera(pag, zona, px):
    """La maschera del collarino: dentro il taglio del disegno tecnico."""
    from scipy import ndimage
    tutto = np.asarray(pag.rendi(zona, px, via=("notes", "shared")), np.int16)
    linee = tutto.sum(-1) < 720          # nella resa ci sono solo le linee del DT
    # i tratti a punteggiato (la perforazione del talloncino): le linee si
    # ingrossano finche' i buchi si chiudono, e poi il bordo torna sul taglio
    k = 6
    grosse = ndimage.binary_dilation(np.pad(linee, k + 2), iterations=k)
    lab, n = ndimage.label(~grosse)
    bordo = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    fuori = np.isin(lab, list(bordo))
    dentro = ndimage.binary_erosion(~fuori, iterations=k)[k + 2:-(k + 2), k + 2:-(k + 2)]
    return ndimage.binary_fill_holes(dentro)


LATO = 880.0
PX_F, PX_R, PX_COLL = 2.0, 1.0, 4.0
# la sagoma dalla foto di dietro: (altezza, mezza larghezza) in mm, col foglio
SAGOMA = [(5.5, 19.0), (8.3, 20.9), (11.0, 22.5), (13.8, 24.0), (20.7, 27.1), (27.6, 30.1),
          (34.5, 33.1), (41.4, 36.3), (48.3, 39.5), (55.2, 42.7), (62.1, 45.8), (69.0, 48.7),
          (75.9, 50.3), (82.8, 51.8), (89.7, 52.7), (96.6, 52.8), (103.5, 51.9), (110.4, 51.2),
          (117.3, 50.1), (124.2, 49.0), (131.1, 47.6), (138.0, 46.4), (144.9, 45.6)]
BASE = 15.0             # il fondo piatto: l'uovo appoggia sulla valva
SPIGOLO = 4.0           # lo spigolo arrotondato del fondo
CIMA_UOVO = 178.0       # la cima dell'uovo: la parte larga, sotto la fascia del collarino
Y_LASCIA = 150.0        # dove il foglio lascia l'uovo per raccogliersi nel collo
Y_COLLO = 182.0         # l'anello del collo
COLLO = 39.0            # il raggio del foglio raccolto dentro la fascia
PIEGA = 3.0             # quanto sporge la piega schiacciata sull'uovo
SPESSORE = 0.25
N_PIEGHE, K_PIEGA = 30, 10
RHO_K = 290.0           # il raggio del foglio all'anello del collo
ROT = np.radians(-45)   # una punta del foglio sta davanti
# il ciuffo
M_VENT, R_VENT, N_VENT = 720, 110, 16
PHI_M = np.radians(24)  # i lembi di lato stanno fra -24 e 24 gradi, e attorno a 180
AMP_MAX = 14.0
GRINZE_K = 0.6
BOMBA = 0.12
# il contorno dei lembi davanti e dietro, dalle foto (mezza larghezza, altezza
# dal collo), dall'ala alla punta; la punta e' spostata un poco a destra
ARCO = [(118, -27), (123, -12), (125, 18), (125, 48), (122.5, 78), (118.5, 108), (108.5, 138),
        (94.5, 168), (78.5, 198), (61.5, 228), (40.5, 258), (18.5, 288), (0, 310)]
ARCO_DIETRO = [(111, -24), (119, -12), (118, 18), (115.5, 48), (109, 78), (101, 108), (91, 138),
               (83, 168), (74, 198), (52.5, 228), (37, 258), (19, 288), (0, 309)]
X_PUNTA, X_PUNTA_DIETRO = 12.0, 24.0
# la profondita' del bordo dei lembi (altezza dal collo, z), dalle foto di fianco
PROF_DAVANTI = [(-27, 52.5), (78, 55), (108, 63), (138, 75), (168, 78), (198, 83), (228, 88),
                (258, 94), (288, 98), (310, 102)]
PROF_DIETRO = [(-24, 75), (48, 73), (78, 66), (108, 72), (138, 72), (168, 64), (198, 70), (228, 78),
               (258, 87), (288, 100), (309, 105)]
PHI_F, PHI_B = np.radians(24), np.radians(34)   # le ali davanti e dietro, dall'asse x
Y_PUNTA_LATO, H_PUNTA_LATO = 279.0, 40.0
MARGINE = 2.0           # quanto il ciuffo sta lontano da uovo e collarino
# sopra Y_PUNTE (dal collo) i petali si piegano verso il centro: davanti e dietro
# la profondita' fino a S_PROF in punta, di lato la distanza fino a S_LATO
Y_PUNTE, S_PROF, S_LATO = 130.0, 0.3, 0.5
# sopra Y_STRINGE (dal collo) il ciuffo si chiude in profondita' come mani giunte:
# z si stringe con l'altezza fino a S_CIMA in cima. Visto di fronte non cambia nulla
Y_STRINGE, Y_CIMA, S_CIMA = 140.0, 310.0, 0.05
# il collarino
SOPRA = 1.2             # quanto sta sopra le pieghe del foglio
ATTACCO = 75.0          # nel piatto, l'altezza dove le braccia escono dall'ovale: sta sulla fascia
PIANO_SOPRA = 50.0      # sopra la fascia l'ovale sale davanti alla base del ciuffo, a questa distanza dall'asse
PENDENZA = 0.07         # la linea davanti dell'ovale: dritta, indietro di 0,07 mm per mm salendo
Y_FASCIA = 161.0        # l'altezza dove le braccia escono dall'ovale (il logo come nella foto)
Y_BANDA, K_BANDA = 168.5, 0.94  # la fascia delle braccia: da 157 a 180 mm, fino all'inizio del ciuffo
DTH_SALITA, DTH_RAGGIO, DTH_ATTACCO = 30.0, 5.0, 5.0   # gradi d'arco: il braccio sale alla fascia, si stringe all'uovo, lascia l'ovale
ORO = (255, 222, 84)
DENTRO = (53, 194, 224)
METALLO = 0.35
RUVIDO = 0.2


# ---------------------------------------------------------------- la sagoma
def _profilo():
    """La linea del meridiano (r, y), dal centro del fondo alla cima, e la sua lunghezza."""
    ys = np.array([p[0] for p in SAGOMA])
    rs = np.array([p[1] for p in SAGOMA])
    rs = rs - (SPESSORE + PIEGA) * np.clip((ys - 3.0) / 12.0, 0, 1)   # il foglio sta sopra
    # la cupola: un'ellisse che continua il fianco con la stessa pendenza
    y1, r1 = ys[-1], rs[-1]
    m1 = (rs[-1] - rs[-4]) / (ys[-1] - ys[-4])
    D = CIMA_UOVO - y1
    u = -m1 * D / (r1 + m1 * D)
    b = D / (1 - u)
    yc = y1 - u * b
    a = r1 / np.sqrt(1 - u * u)
    yd = np.linspace(y1, CIMA_UOVO, 200)[1:]
    rd = a * np.sqrt(np.clip(1 - ((yd - yc) / b) ** 2, 0, 1))
    # il fondo piatto e lo spigolo, fino alla pendenza del fianco
    t0 = np.array([rs[1] - rs[0], ys[1] - ys[0]])
    beta = np.arctan2(t0[1], t0[0])
    th = np.linspace(-np.pi / 2, beta - np.pi / 2, 30)
    ra = BASE + SPIGOLO * np.cos(th)
    ya = SPIGOLO + SPIGOLO * np.sin(th)
    fianco = ys > ya[-1] + 0.5
    r = np.concatenate([np.linspace(0, BASE, 40)[:-1], ra, rs[fianco], rd])
    y = np.concatenate([np.zeros(39), ya, ys[fianco], yd])
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(r), np.diff(y)))])
    # ricampiona e liscia appena (gli estremi restano sull'asse)
    S = np.linspace(0, s[-1], 4000)
    R = np.interp(S, s, r)
    Yy = np.interp(S, s, y)
    k = 6
    R = gaussian_filter1d(R, k, mode="nearest")
    Yy = gaussian_filter1d(Yy, k, mode="nearest")
    R[0], Yy[0] = 0.0, 0.0
    R[-1] = 0.0
    Yy[Yy < 0] = 0.0
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(R), np.diff(Yy)))])
    return R, Yy, s


RR, YY, SS = _profilo()
L_MER = SS[-1]
Y_PANCIA = YY[np.argmax(RR)]


def r_uovo(y):
    """Il raggio dell'uovo all'altezza y (sopra il fondo: il fondo e' piatto)."""
    sopra = YY > 1e-3
    return np.interp(y, YY[sopra], RR[sopra], left=0.0, right=0.0)


def _curva(P):
    """Tangenti, normali (la tangente girata a destra) e curvatura di una
    linea (n, 2), coi punti a passo qualsiasi."""
    d = np.gradient(P, axis=0)
    ds = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
    t = d / ds[:, None]
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    th = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    k = np.gradient(th) / ds
    return t, n, k


def _limita(d, k, quanto=0.75):
    """Lo spostamento d lungo la normale (a destra della tangente) senza che
    la linea si ripieghi: verso il centro di curvatura non piu' del raggio."""
    lo = np.where(k > 1e-9, -quanto / np.maximum(k, 1e-9), -np.inf)
    hi = np.where(k < -1e-9, quanto / np.maximum(-k, 1e-9), np.inf)
    return np.clip(d, lo, hi)


# ---------------------------------------------------------------- l'uovo e il collo
def uovo_e_collo():
    """Il foglio sull'uovo e nel collo: ogni colonna nel semipiano del suo
    angolo; le pieghe schiacciate la spostano lungo la sua normale."""
    i_p = int(np.argmax(RR))
    s_top = float(np.interp(Y_LASCIA, YY[i_p:], SS[i_p:]))      # sopra la pancia y cresce
    # la linea di base: il meridiano fino a s_top, poi il collo (Bezier) fino all'anello
    n_u, n_c = 140, 22
    su = np.linspace(0, s_top, n_u)
    Pu = np.stack([np.interp(su, SS, RR), np.interp(su, SS, YY)], 1)
    tu, _n, _k = _curva(Pu)
    P0, T0 = Pu[-1], tu[-1]
    P3 = np.array([COLLO, Y_COLLO])
    lun = np.linalg.norm(P3 - P0)
    # il foglio raccolto sale a cono dalla spalla dell'uovo all'anello
    corda = (P3 - P0) / lun
    C1 = P0 + 0.3 * lun * (0.5 * T0 + 0.5 * corda)
    C2 = P3 - 0.3 * lun * (0.6 * corda + 0.4 * np.array([0.0, 1.0]))
    t = np.linspace(0, 1, 400)[:, None]
    Bz = (1 - t) ** 3 * P0 + 3 * t * (1 - t) ** 2 * C1 + 3 * t ** 2 * (1 - t) * C2 + t ** 3 * P3
    sb = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Bz, axis=0), axis=1))])
    sc = np.linspace(0, sb[-1], n_c)[1:]
    Pc = np.stack([np.interp(sc, sb, Bz[:, 0]), np.interp(sc, sb, Bz[:, 1])], 1)
    P = np.concatenate([Pu, Pc])
    v = np.concatenate([np.zeros(n_u), sc / sb[-1]])                 # 0 sull'uovo, 1 all'anello
    rho = np.concatenate([su, s_top + (sc / sb[-1]) * (RHO_K - s_top)])
    t_, n_, k_ = _curva(P)
    NC = N_PIEGHE * (K_PIEGA + 1)
    j = np.tile(np.arange(K_PIEGA + 1), N_PIEGHE)
    kk = np.repeat(np.arange(N_PIEGHE), K_PIEGA + 1)
    tau = j / K_PIEGA
    b = (kk + tau) * 2 * np.pi / N_PIEGHE
    onda = np.minimum(tau / 0.82, (1 - tau) / 0.18)                 # la scaglia
    r = np.maximum(P[:, 0], 1e-6)
    c = np.where(rho > 1e-6, np.maximum(rho / r, 1.0), 1.0)
    forza = np.minimum(1.0, (c - 1) / 0.6)
    calo = (1 - v) ** 0.8                                            # all'anello il collo e' liscio
    h = (SPESSORE + PIEGA * onda[None, :] * forza[:, None]) * calo[:, None]
    h = _limita(h, k_[:, None])
    Q = P[:, None, :] + h[..., None] * n_[:, None, :]
    rr = np.maximum(Q[..., 0], 0.0)
    V = np.stack([rr * np.cos(b)[None, :], Q[..., 1], rr * np.sin(b)[None, :]], -1)
    th = (kk[None, :] + 0.5 + (tau[None, :] - 0.5) / c[:, None]) * 2 * np.pi / N_PIEGHE
    UV = uv_foglio(np.broadcast_to(rho[:, None], th.shape), ROT - th)
    idx = np.arange(len(P) * NC).reshape(len(P), NC)
    T = []
    for q in range(N_PIEGHE):
        c0 = q * (K_PIEGA + 1)
        a = idx[:-1, c0:c0 + K_PIEGA].ravel()
        b1 = idx[:-1, c0 + 1:c0 + K_PIEGA + 1].ravel()
        c1 = idx[1:, c0 + 1:c0 + K_PIEGA + 1].ravel()
        d1 = idx[1:, c0:c0 + K_PIEGA].ravel()
        T += [np.stack([a, b1, c1], 1), np.stack([a, c1, d1], 1)]
    T = np.concatenate(T)
    V = V.reshape(-1, 3)
    # il raggio piu' grande del foglio a ogni altezza: il collarino sta fuori
    yb = np.arange(-1.0, Y_COLLO + 2.0, 0.5)
    hv = np.hypot(V[:, 0], V[:, 2])
    iv = np.clip(((V[:, 1] + 1.0) / 0.5).astype(int), 0, len(yb) - 1)
    rmax = np.zeros(len(yb))
    np.maximum.at(rmax, iv, hv)
    return V, UV.reshape(-1, 2), T, s_top, (yb, rmax)


# ---------------------------------------------------------------- il bordo del ciuffo
def _lungo(poli, lam):
    """Il punto alla frazione lam della lunghezza di una spezzata (x, y)."""
    p = np.array(poli, float)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    s /= s[-1]
    return np.interp(lam, s, p[:, 0]), np.interp(lam, s, p[:, 1])


def _larghezza(poli, y):
    p = np.array(poli, float)
    o = np.argsort(p[:, 1])
    return np.interp(y, p[o, 1], p[o, 0])


def stringi_z(y):
    """Il fattore della profondita' alla altezza y dal collo."""
    return 1 - (1 - S_CIMA) * _liscia((y - Y_STRINGE) / (Y_CIMA - Y_STRINGE))


def bordo_ciuffo(b):
    """L'angolo nel giro (phi), la distanza dall'asse (h) e l'altezza dal collo
    (y) del bordo del foglio, per l'angolo b del foglio. phi cresce con b."""
    bd = np.degrees(b) % 360.0
    phi = np.zeros_like(bd)
    h = np.zeros_like(bd)
    y = np.zeros_like(bd)
    ali = {}
    for nome, centro, arco, prof, xp, segno in (("davanti", 90.0, ARCO, PROF_DAVANTI, X_PUNTA, 1.0),
                                               ("dietro", 270.0, ARCO_DIETRO, PROF_DIETRO, X_PUNTA_DIETRO, -1.0)):
        sel = np.abs(bd - centro) <= 45.0
        lam = 1 - np.abs(bd[sel] - centro) / 45.0                     # 0 all'ala, 1 alla punta
        xa, ya = _lungo(arco, lam)
        p = np.array(prof, float)
        y_t = arco[-1][1]
        # in alto il petalo si piega verso il centro solo in profondita': visto
        # di fronte resta largo com'e' (non si stringe su se stesso)
        piega = 1 - (1 - S_PROF) * _liscia((ya - Y_PUNTE) / (y_t - Y_PUNTE))
        za = np.interp(ya, p[:, 0], p[:, 1]) * piega
        lato = np.where(bd[sel] < centro, 1.0, -1.0) * segno          # a destra prima della punta
        x = lato * xa + xp * np.clip((ya - 100.0) / (y_t - 100.0), 0, 1) ** 2
        z = segno * za
        h[sel] = np.hypot(x, z)
        y[sel] = ya
        # l'angolo: quello del bordo misurato, con un poco di angolo regolare dall'ala
        # alla punta, cosi' le colonne non si affollano dove il bordo sale dritto
        ph_t = np.unwrap(np.arctan2(z, x)[np.argsort(bd[sel])])[np.argsort(np.argsort(bd[sel]))]
        ph_ala = np.arctan2(segno * p[0, 1], lato * arco[0][0])
        ph_punta = np.arctan2(segno * p[-1, 1] * S_PROF, xp)
        ph_u = ph_ala + np.angle(np.exp(1j * (ph_punta - ph_ala))) * lam
        dd = np.angle(np.exp(1j * (ph_u - ph_t)))
        phi[sel] = np.degrees(ph_t + 0.3 * dd) % 360.0
        ali[nome] = (np.hypot(arco[0][0], prof[0][1]), arco[0][1])
    # i lembi di lato: phi va dritto da un'ala all'altra, il bordo sale presto
    pf, pb = np.degrees(PHI_F), np.degrees(PHI_B)
    for centro in (0.0, 180.0):
        rel = ((bd - centro + 180.0) % 360.0) - 180.0
        sel = np.abs(rel) < 45.0
        r_ = rel[sel]
        w = 1 - np.abs(r_) / 45.0
        davanti = (r_ > 0) == (centro == 0.0)
        ampiezza = np.where(davanti, pf, pb)
        verso = 1.0 if centro == 0.0 else -1.0
        phi[sel] = (centro + verso * np.where(davanti, 1.0, -1.0) * ampiezza * np.abs(r_) / 45.0) % 360.0
        h_ala = np.where(davanti, ali["davanti"][0], ali["dietro"][0])
        y_ala = np.where(davanti, ali["davanti"][1], ali["dietro"][1])
        yy = y_ala + (Y_PUNTA_LATO - y_ala) * (1 - (1 - w) ** 2.5)
        hl = h_ala + (H_PUNTA_LATO - h_ala) * w
        # dentro i contorni dei lembi davanti e dietro, visti di fronte
        cap = np.minimum(_larghezza(ARCO, yy), _larghezza(ARCO_DIETRO, yy))
        ang = np.radians(ampiezza * np.abs(r_) / 45.0)
        cap = cap * (0.85 + 0.15 * (1 - w) ** 4) / np.cos(ang)
        h[sel] = np.minimum(hl, np.maximum(cap, 1.5 * COLLO))
        # le punte dei lembi di lato si avvicinano appena al centro
        h[sel] *= 1 - (1 - S_LATO) * _liscia((yy - Y_PUNTE) / (Y_PUNTA_LATO - Y_PUNTE))
        y[sel] = yy
    # phi deve crescere con b: si aggiusta dove tornasse indietro
    o = np.argsort(bd)
    ph = np.unwrap(np.radians(phi[o]))
    for i in range(1, len(ph)):
        if ph[i] <= ph[i - 1]:
            ph[i] = ph[i - 1] + 1e-5
    # fra due colonne almeno un poco d'angolo: lo si prende ai passi grandi
    d = np.diff(ph)
    minimo = np.radians(0.06)
    d2 = np.maximum(d, minimo)
    grandi = d2 > 1.5 * minimo
    d2[grandi] -= (d2.sum() - d.sum()) * d2[grandi] / d2[grandi].sum()
    ph = ph[0] + np.concatenate([[0.0], np.cumsum(d2)])
    out = np.empty_like(ph)
    out[o] = ph
    return out, h, y


# ---------------------------------------------------------------- gli ostacoli
class Ostacoli:
    """Quanto sono lontani dall'asse uovo e collarino, per angolo e altezza:
    sotto l'anello del collo il ciuffo deve stare piu' fuori."""
    PASSO_A, PASSO_Y = 2.0, 1.0

    def __init__(self, *nuvole, davanti=None, collare=None, ovale=None):
        from scipy.spatial import cKDTree
        from scipy.ndimage import maximum_filter1d
        # i punti del collarino: le pieghe del ciuffo si smorzano vicino
        self.albero = cKDTree(collare) if collare is not None else None
        na, ny = int(360 / self.PASSO_A), int((Y_COLLO + 40) / self.PASSO_Y)
        # la cima dell'ovale a ogni angolo: dietro l'ovale il ciuffo sale fin sopra
        self.cima = None
        if ovale is not None:
            az = (np.degrees(np.arctan2(ovale[:, 2], ovale[:, 0])) % 360.0 / self.PASSO_A).astype(int) % na
            cima = np.full(na, -np.inf)
            np.maximum.at(cima, az, ovale[:, 1])
            self.cima = maximum_filter1d(cima, 3, mode="wrap")
        T = np.zeros((na, ny))
        for V in nuvole:
            az = (np.degrees(np.arctan2(V[:, 2], V[:, 0])) % 360.0 / self.PASSO_A).astype(int) % na
            iy = np.clip((V[:, 1] / self.PASSO_Y).astype(int), 0, ny - 1)
            np.maximum.at(T, (az, iy), np.hypot(V[:, 0], V[:, 2]))
        from scipy.ndimage import maximum_filter
        self.T = maximum_filter(T, size=(5, 5), mode=("wrap", "nearest"))
        self.na, self.ny = na, ny
        # il solo collarino: sopra l'anello, il ciuffo che ha scavalcato l'ovale gli sta fuori
        self.Tc = np.zeros((na, ny))
        if collare is not None:
            az = (np.degrees(np.arctan2(collare[:, 2], collare[:, 0])) % 360.0 / self.PASSO_A).astype(int) % na
            iy = np.clip((collare[:, 1] / self.PASSO_Y).astype(int), 0, ny - 1)
            np.maximum.at(self.Tc, (az, iy), np.hypot(collare[:, 0], collare[:, 2]))
            self.Tc = maximum_filter(self.Tc, size=(5, 5), mode=("wrap", "nearest"))
        # il collarino davanti al collo: sopra l'anello il ciuffo gli sta dietro
        self.D = np.full((na, ny), np.inf)
        if davanti is not None:
            V = davanti
            az = (np.degrees(np.arctan2(V[:, 2], V[:, 0])) % 360.0 / self.PASSO_A).astype(int) % na
            iy = np.clip((V[:, 1] / self.PASSO_Y).astype(int), 0, ny - 1)
            np.minimum.at(self.D, (az, iy), np.hypot(V[:, 0], V[:, 2]))
            from scipy.ndimage import minimum_filter
            self.D = minimum_filter(self.D, size=(3, 3), mode=("wrap", "nearest"))

    def cima_ovale(self, phi):
        """L'altezza piu' alta dell'ovale nel semipiano phi (-inf dove non c'e')."""
        az = (np.degrees(phi) % 360.0 / self.PASSO_A).astype(int) % self.na
        return self.cima[az]

    def h_davanti(self, phi, y):
        """Il raggio da non superare (inf dove il collarino non c'e')."""
        az = (np.degrees(phi) % 360.0 / self.PASSO_A).astype(int) % self.na
        iy = (y / self.PASSO_Y).astype(int)
        dentro = (iy >= 0) & (iy < self.ny)
        out = np.full(np.broadcast(az, iy).shape, np.inf)
        out[dentro] = self.D[np.broadcast_to(az, out.shape)[dentro], iy[dentro]]
        return out

    def h(self, phi, y, tab=None):
        """Il raggio da superare nel semipiano phi (radianti) all'altezza y (assoluta)."""
        tab = self.T if tab is None else tab
        az = (np.degrees(phi) % 360.0 / self.PASSO_A).astype(int) % self.na
        iy = (y / self.PASSO_Y).astype(int)
        dentro = (iy >= 0) & (iy < self.ny)
        out = np.zeros(np.broadcast(az, iy).shape)
        out[dentro] = tab[np.broadcast_to(az, out.shape)[dentro], iy[dentro]]
        return out

    def h_collare(self, phi, y):
        return self.h(phi, y, self.Tc)


# ---------------------------------------------------------------- il ciuffo
def ciuffo(rng, ostacoli=None, pieghe=True, grinze=True):
    """Il ciuffo sopra il collo. Ogni colonna e' una curva nel semipiano del
    suo angolo phi, dall'anello del collo al bordo del foglio."""
    b = np.linspace(0, 2 * np.pi, M_VENT + 1)[:-1]
    ang_u = ROT - b
    d = bordo(ang_u) - RHO_K
    phi, hR, yR = bordo_ciuffo(b)
    A = np.array([COLLO, 0.4])
    f = np.linspace(0, 1, R_VENT + 1)
    P0 = np.zeros((R_VENT + 1, M_VENT, 2))
    # vicino ai mezzi dei lati il foglio raccolto scende sulle spalle dell'uovo
    # (fuori da uovo e collarino) e poi va all'ala: di fronte copre i fianchi
    bd = np.degrees(b) % 90.0
    drappo = np.exp(-((bd - 45.0) / 16.0) ** 2)
    # i lembi davanti e dietro sono appena incavati al centro: di fianco il
    # ciuffo resta pieno fra i due
    bg = np.degrees(b) % 360.0
    lam = np.clip(1 - np.minimum(np.abs(bg - 90.0), np.abs(bg - 270.0)) / 45.0, 0, 1)
    bomba = BOMBA * (1 - 1.8 * lam ** 2)
    for i in range(M_VENT):
        R = np.array([hR[i], yR[i]])
        # dove davanti c'e' l'ovale, la colonna sale dietro l'ovale fin sopra la
        # sua cima (a quest'angolo) e solo da li' esce: il ciuffo parte da dentro
        W, salita = A, None
        if ostacoli is not None and ostacoli.cima is not None:
            yw = float(ostacoli.cima_ovale(np.array([phi[i]]))[0]) - Y_COLLO + MARGINE + 1.5
            if yw > A[1] + 0.3:
                yy = Y_COLLO + np.linspace(A[1], yw, 80)
                dd = ostacoli.h_davanti(np.full(80, phi[i]), yy)
                dmin = float(dd[np.isfinite(dd)].min()) if np.isfinite(dd).any() else COLLO + 8.0
                W = np.array([float(np.clip(dmin - MARGINE - 1.0, COLLO, COLLO + 12.0)), yw])
                n_s = 60
                salita = np.stack([np.linspace(A[0], W[0], n_s), np.linspace(A[1], W[1], n_s)], 1)
        corda = R - W
        lun = np.linalg.norm(corda)
        elev = np.degrees(np.arctan2(corda[1], corda[0]))
        al = np.radians(5 + 77 * _liscia((elev + 25) / 105))
        nb = np.array([corda[1], -corda[0]]) / lun
        if nb @ np.array([0.7071, 0.7071]) < 0:
            nb = -nb
        C1 = W + 0.35 * lun * np.array([np.cos(al), np.sin(al)])
        C2 = R - 0.35 * corda + bomba[i] * lun * nb
        if drappo[i] > 0.01 and R[1] < 30:
            # parte in orizzontale sopra l'anello, poi scende fuori da uovo e collarino
            h_k = 50.0
            if ostacoli is not None:
                yy = Y_COLLO + np.linspace(R[1], 0.0, 40)
                h_k = max(h_k, float(ostacoli.h(np.full(40, phi[i]), yy).max()) + 10.0)
            D1 = W + np.array([46.0, 6.0])
            D2 = np.array([h_k, R[1] + 10.0])
            C1 = (1 - drappo[i]) * C1 + drappo[i] * D1
            C2 = (1 - drappo[i]) * C2 + drappo[i] * D2
        t = np.linspace(0, 1, 500)[:, None]
        Bz = (1 - t) ** 3 * W + 3 * t * (1 - t) ** 2 * C1 + 3 * t ** 2 * (1 - t) * C2 + t ** 3 * R
        if salita is not None:
            Bz = np.concatenate([salita[:-1], Bz])
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Bz, axis=0), axis=1))])
        col = np.stack([np.interp(f * s[-1], s, Bz[:, 0]), np.interp(f * s[-1], s, Bz[:, 1])], 1)
        if salita is not None:
            # lo spigolo sopra la cima dell'ovale si arrotonda appena
            liscia = np.stack([gaussian_filter1d(col[:, 0], 1.5, mode="nearest"),
                               gaussian_filter1d(col[:, 1], 1.5, mode="nearest")], 1)
            liscia[0], liscia[-1] = col[0], col[-1]
            col = liscia
        P0[:, i] = col
    rho = RHO_K + f[:, None] * d[None, :]
    # la base in 3D, per sapere quanto e' lungo il giro
    X0 = np.stack([P0[..., 0] * np.cos(phi), P0[..., 1], P0[..., 0] * np.sin(phi)], -1)
    db = 2 * np.pi / M_VENT
    g = np.linalg.norm(np.roll(X0, -1, 1) - np.roll(X0, 1, 1), axis=2) / (2 * db)
    fase = N_VENT * b
    dfase = np.full_like(b, float(N_VENT))
    for kk in (1, 2, 3, 5):
        a_, p_ = rng.uniform(0.6, 1.4) * N_VENT / (kk * 5.0), rng.uniform(0, 2 * np.pi)
        fase = fase + a_ * np.sin(kk * b + p_)
        dfase = dfase + a_ * kk * np.cos(kk * b + p_)
    amp = np.pi * np.sqrt(np.maximum(rho ** 2 - g ** 2, 0)) / (2 * np.maximum(dfase, 4.0))
    mezza = g * np.pi / np.maximum(dfase, 4.0)
    amp = np.minimum(np.minimum(amp, 0.45 * mezza), AMP_MAX)
    amp *= _liscia(f / 0.2)[:, None]
    # vicino a uovo e collarino le pieghe si smorzano: non ci entrano
    if ostacoli is not None:
        ya = Y_COLLO + P0[..., 1]
        luce = P0[..., 0] - (ostacoli.h(np.broadcast_to(phi, ya.shape), ya) + MARGINE)
        luce = np.where(ya < Y_COLLO - 1.0, luce, 1e3)
        amp = np.minimum(amp, np.maximum(luce * 0.8, 0.0))
        smorza = np.clip(luce / 6.0, 0.0, 1.0)
    else:
        smorza = np.ones_like(amp)
    # ogni punto della colonna, prima che scavalchi la cima dell'ovale, sta
    # dietro l'ovale; dopo gli sta fuori
    if ostacoli is not None and ostacoli.cima is not None:
        cima_i = ostacoli.cima_ovale(phi)
        sopra = (Y_COLLO + P0[..., 1]) > cima_i[None, :] + 2.0
        k_su = np.where(sopra.any(0), sopra.argmax(0), R_VENT + 1)
        dietro = np.arange(R_VENT + 1)[:, None] < k_su[None, :]
    else:
        cima_i = np.full(M_VENT, np.inf)
        dietro = np.ones(P0.shape[:2], bool)

    def regole(Q, phi_, dt, ci):
        """Dove il punto (h, y) di una colonna sta male: il raggio minimo e massimo."""
        ya = Y_COLLO + Q[..., 1]
        sotto = ya < Y_COLLO - 1.0
        lo = np.where(sotto, ostacoli.h(phi_, ya) + MARGINE, -np.inf)
        # sopra l'anello: dietro l'ovale finche' non lo scavalca, poi fuori dal collarino
        hd = ostacoli.h_davanti(phi_, ya) - MARGINE
        hi = np.where(~sotto & dt, np.maximum(hd, COLLO + 0.5), np.inf)
        lo = np.where(~sotto & ~dt & (ya < ci), ostacoli.h_collare(phi_, ya) + MARGINE, lo)
        return lo, hi

    def fuori(Q):
        if ostacoli is None:
            return Q
        lo, hi = regole(Q, np.broadcast_to(phi, Q.shape[:2]), dietro, np.broadcast_to(cima_i, Q.shape[:2]))
        Q[..., 0] = np.minimum(np.maximum(Q[..., 0], lo), hi)
        return Q

    # vicino al collarino (anche dove non c'e' una regola: gli attacchi delle
    # braccia) le pieghe si smorzano: la linea di base sta gia' fuori
    dist_c = None
    if ostacoli is not None and ostacoli.albero is not None:
        Pf = fuori(P0.copy())
        Xf = np.stack([Pf[..., 0] * np.cos(phi), Y_COLLO + Pf[..., 1], Pf[..., 0] * np.sin(phi)], -1)
        dist_c = ostacoli.albero.query(Xf.reshape(-1, 3))[0].reshape(Pf.shape[:2])
        spazio = np.maximum(dist_c - MARGINE - 1.5, 0.0)
        amp = np.minimum(amp, 0.8 * spazio)
        smorza = np.minimum(smorza, np.clip(spazio / 6.0, 0.0, 1.0))
    amp *= 0.85 + 0.15 * np.sin(2.3 * f[:, None] * np.pi + 3 * b[None, :])
    spost = amp * _onda(fase)[None, :] * pieghe
    if grinze:
        pf = np.stack([rho * np.cos(ang_u)[None, :], rho * np.sin(ang_u)[None, :]], -1).reshape(-1, 2)
        gr = _grinze(pf, _pieghe_creste(rng, 560)).reshape(rho.shape)
        spost = spost + GRINZE_K * gr * _liscia((f - 0.04) / 0.15)[:, None]
    spost = spost * smorza

    P0 = fuori(P0)
    P = np.zeros_like(P0)
    for i in range(M_VENT):
        t_, n_, k_ = _curva(P0[:, i])
        dd = _limita(spost[:, i], k_)
        dd[0] = 0.0
        Q = P0[:, i] + dd[:, None] * n_
        if ostacoli is not None:
            # una piega che entrerebbe in uovo o collarino si accorcia
            for _ in range(8):
                lo, hi = regole(Q, np.full(len(Q), phi[i]), dietro[:, i], np.full(len(Q), cima_i[i]))
                dentro = (Q[:, 0] < lo) | (Q[:, 0] > hi)
                if dist_c is not None:
                    Xq = np.stack([Q[:, 0] * np.cos(phi[i]), Y_COLLO + Q[:, 1], Q[:, 0] * np.sin(phi[i])], -1)
                    dq = ostacoli.albero.query(Xq)[0]
                    dentro |= (dq < 2.0) & (dq < dist_c[:, i] - 0.2)
                if not dentro.any():
                    break
                dd = np.where(dentro, dd * 0.5, dd)
                Q = P0[:, i] + dd[:, None] * n_
        P[:, i] = Q
    P[..., 0] = np.maximum(P[..., 0], 0.3 * COLLO)
    P = fuori(P)
    V = np.stack([P[..., 0] * np.cos(phi), Y_COLLO + P[..., 1], P[..., 0] * np.sin(phi)], -1).reshape(-1, 3)
    # in alto il davanti e il dietro si avvicinano fino a toccarsi: a ogni altezza z
    # si scala dello stesso fattore, una deformazione dello spazio che non crea
    # intersezioni (sotto Y_STRINGE, dove ci sono uovo e collarino, non cambia nulla)
    V[:, 2] *= stringi_z(V[:, 1] - Y_COLLO)
    UV = uv_foglio(rho, np.broadcast_to(ang_u, rho.shape)).reshape(-1, 2)
    idx = np.arange((R_VENT + 1) * M_VENT).reshape(R_VENT + 1, M_VENT)
    a = idx[:-1].ravel()
    b1 = np.roll(idx, -1, 1)[:-1].ravel()
    c1 = np.roll(idx, -1, 1)[1:].ravel()
    d1 = idx[1:].ravel()
    T = np.concatenate([np.stack([a, b1, c1], 1), np.stack([a, c1, d1], 1)])
    return V, UV, T, phi


# ---------------------------------------------------------------- il collarino
def _sopra_liscio(r, sigma, giri=60):
    """Una curva liscia che sta sopra r (mai sotto): si alza e si liscia a turno."""
    e = r.copy()
    for _ in range(giri):
        e = gaussian_filter1d(np.maximum(e, r), sigma, mode="nearest")
    return e + max(0.0, float((r - e).max()))


def maglia_collarino(masc, raggi):
    """Il collarino, liscio: l'ovale davanti e le braccia nella fascia attorno
    al collo. Nessun punto si sposta da solo: e' il foglio (o il ciuffo) che
    si schiaccia sotto, se serve."""
    cont = [c for c in contorni(masc)]
    anello = max(cont, key=len)
    mm = np.stack([anello[:, 0] / PX_COLL, anello[:, 1] / PX_COLL], 1)
    mm = semplifica(mm, 0.2)
    pts, tri = triangola([mm], griglia=2.5)
    H, W = masc.shape
    xs = np.nonzero(masc.any(0))[0]
    xc = (xs.min() + xs.max()) / 2 / PX_COLL
    col = masc[:, int(round(xc * PX_COLL))]
    oy = np.nonzero(col)[0]
    oy0, oy1 = oy.min() / PX_COLL, oy.max() / PX_COLL
    ocy = (oy0 + oy1) / 2
    # il bordo vero dell'ovale, riga per riga (dove escono le braccia si
    # raccorda con le righe vicine)
    righe = np.arange(int(oy0 * PX_COLL), int(oy1 * PX_COLL) + 1)
    mezza = np.full(len(righe), np.nan)
    ic = int(round(xc * PX_COLL))
    for k, r in enumerate(righe):
        x = np.nonzero(masc[r])[0]
        if not len(x):
            continue
        seg = np.split(x, np.nonzero(np.diff(x) > 1)[0] + 1)
        s = [q for q in seg if q.min() <= ic <= q.max()]
        if s:
            mezza[k] = max(ic - s[0].min(), s[0].max() - ic) / PX_COLL
    yr = righe / PX_COLL
    # le righe con le braccia: la larghezza salta oltre quella delle righe attorno
    liscia_m = gaussian_filter1d(np.nan_to_num(mezza, nan=0.0), 3 * PX_COLL)
    con_braccia = mezza > np.minimum(liscia_m, np.nanmax(mezza[yr > ocy])) + 4.0
    con_braccia = gaussian_filter1d(con_braccia.astype(float), 2 * PX_COLL) > 0.01
    buone = ~np.isnan(mezza) & ~con_braccia
    from scipy.interpolate import PchipInterpolator
    hw_f = PchipInterpolator(yr[buone], mezza[buone], extrapolate=True)
    hx = float(np.nanmax(mezza[buone]))
    cx, cy = [], []
    for x in np.arange(0, W / PX_COLL, 2.0):
        if xc - hx - 4 < x < xc + hx + 4:
            continue
        c = np.nonzero(masc[:, int(x * PX_COLL)])[0]
        if len(c) < 8:
            continue
        stacco = np.nonzero(np.diff(c) > 1)[0]
        fine = c[stacco[0]] if len(stacco) else c[-1]
        cx.append(x)
        cy.append((c[0] + fine) / 2 / PX_COLL)
    cx, cy = np.array(cx), np.array(cy)
    A_ = np.stack([2 * cy, np.ones_like(cy)], 1)
    (yc, k), *_ = np.linalg.lstsq(A_, (cx - xc) ** 2 + cy ** 2, rcond=None)
    r_c = np.sqrt(k + yc ** 2)
    dx = pts[:, 0] - xc
    rr = np.hypot(dx, pts[:, 1] - yc)
    phi = np.arctan2(dx, pts[:, 1] - yc)
    th = np.abs(phi)
    fuori = np.abs(dx) - hw_f(np.clip(pts[:, 1], oy0, oy1))
    sole = th > np.radians(45)
    braccio = (fuori > 0.3) & (pts[:, 1] < ocy)
    yb, rmax = raggi

    # il raggio piu' grande del foglio a ogni altezza, liscio e mai sotto il foglio
    ok = rmax > 0
    r_f = np.interp(yb, yb[ok], rmax[ok])
    inviluppo = _sopra_liscio(r_f, 3.0 / (yb[1] - yb[0])) + 0.3

    def foglio(y):
        return np.interp(y, yb, inviluppo)

    # l'ovale: la linea davanti, liscia. Sotto la pancia pende, dalla fascia in
    # su sale dritto appena inclinato in avanti
    yl = np.linspace(Y_COLLO + 90, -40, 2600)
    r_p = float(foglio(Y_PANCIA))
    r_u = np.where(yl > Y_PANCIA, foglio(yl), r_p + 0.07 * (Y_PANCIA - yl))
    rl0 = r_u + SOPRA + 1.0
    # il cartoncino e' rigido: la linea davanti e' una retta, appena inclinata
    # indietro (come nelle foto di fianco), che passa fuori dal foglio dappertutto
    retta = PENDENZA * (Y_PANCIA - yl)
    rl = retta + float((rl0 - retta).max())
    sl = np.concatenate([[0], np.cumsum(np.hypot(np.diff(yl), np.diff(rl)))])
    s_att = float(np.interp(Y_FASCIA, yl[::-1], sl[::-1]))

    def ovale_3d(dx_, yp):
        """Il punto dell'ovale per il punto del piatto (dx_, yp)."""
        sc = s_att + (yp - ATTACCO)
        yo = np.interp(sc, sl, yl)
        ro = np.interp(sc, sl, rl)
        # la stessa curva a tutte le altezze (un cono quasi cilindro, come un
        # cartoncino avvolto): in cima non si chiude attorno al ciuffo
        Rb = ro + 3.0
        ps = dx_ / Rb
        return np.stack([Rb * np.sin(ps), yo, (ro - Rb) + Rb * np.cos(ps)], -1)

    Vo = ovale_3d(dx, pts[:, 1])

    # dove ogni cerchio attorno al centro dell'arco esce dall'ovale: l'attacco
    rq = np.arange(rr[braccio].min() - 2.0, rr[braccio].max() + 2.0, 0.25)
    tq = np.linspace(0.0, np.pi / 2, 4000)
    th_j = np.empty(len(rq))
    for k_, r_ in enumerate(rq):
        yy = yc + r_ * np.cos(tq)
        f_ = r_ * np.sin(tq) - hw_f(np.clip(yy, oy0, oy1))
        fuori_q = (f_ > 0) | (yy < oy0) | (yy > oy1)
        th_j[k_] = tq[np.argmax(fuori_q)] if fuori_q.any() else np.pi / 2
    th_j = gaussian_filter1d(th_j, 4)
    tj = np.interp(rr, rq, th_j)
    segno = np.sign(dx)
    # il punto dell'attacco sull'ovale, per ogni raggio
    Vj = ovale_3d(segno * rr * np.sin(tj), yc + rr * np.cos(tj))
    y_j = Vj[:, 1]
    r_j = np.hypot(Vj[:, 0], Vj[:, 2])
    a_j = np.arctan2(Vj[:, 0], Vj[:, 2])
    # la linea di mezzo di ogni braccio, angolo per angolo
    gr = np.round(np.degrees(th)).astype(int)
    mezzo = np.full(200, np.nan)
    for g in np.unique(gr[braccio & sole]):
        m = braccio & (gr == g)
        mezzo[g] = (rr[m].min() + rr[m].max()) / 2
    okm = ~np.isnan(mezzo)
    mezzo = gaussian_filter1d(np.interp(np.arange(200), np.nonzero(okm)[0], mezzo[okm]), 2.0)
    rmid = np.interp(np.degrees(th), np.arange(200), mezzo)
    # la fascia: la larghezza del braccio diventa altezza (sul cono attorno al
    # collo); la punta tonda, piu' larga del braccio, si stringe piano
    q = rr - rmid
    q = np.where(np.abs(q) > 12.0, np.sign(q) * (12.0 + 4.0 * np.tanh((np.abs(q) - 12.0) / 4.0)), q)
    ya = Y_BANDA - K_BANDA * q
    # dall'attacco il braccio sale piano alla fascia e gira attorno al collo
    oltre = np.maximum(th - tj, 0.0)
    lam = _liscia(oltre / np.radians(DTH_SALITA))
    y_p = y_j + (ya - y_j) * lam
    r_t = foglio(y_p) + SOPRA + 0.6 * (dx > 0)
    # appena lasciato l'ovale il braccio si stringe all'uovo (di fronte il
    # contorno resta quello dell'ovale), poi sale alla fascia
    r_p = r_j + (r_t - r_j) * _liscia(oltre / np.radians(DTH_RAGGIO))
    # attorno al collo ogni punto del braccio gira dello stesso angolo (come
    # sul cono): dall'attacco del suo raggio, e piu' avanti da quello della linea di mezzo
    k_psi = r_c / (foglio(Y_BANDA) + SOPRA)
    tj_m = np.interp(rmid, rq, th_j)
    Vm = ovale_3d(segno * rmid * np.sin(tj_m), yc + rmid * np.cos(tj_m))
    a_jm = np.arctan2(Vm[:, 0], Vm[:, 2])
    a_loc = a_j + segno * oltre * k_psi
    a_cen = a_jm + segno * np.maximum(th - tj_m, 0.0) * k_psi
    mu = _liscia(oltre / np.radians(15.0))
    a_p = (1 - mu) * a_loc + mu * a_cen
    Pb = np.stack([r_p * np.sin(a_p), y_p, r_p * np.cos(a_p)], 1)
    w = _liscia(oltre / np.radians(DTH_ATTACCO)) * braccio
    Vc = Vo * (1 - w[:, None]) + Pb * w[:, None]
    ovale = w < 0.3
    return pts, tri, Vc, ovale


# ---------------------------------------------------------------- il fondo del collo
def tappo(rng):
    """Il foglio raccolto dentro il collo, appena sotto l'anello e dentro la
    fascia: da fuori non si vede, dall'alto copre il vuoto fra le punte. Un
    imbuto pieghettato che scende al centro, con la stampa del foglio."""
    n_a, n_r = 360, 28
    th = np.linspace(0, 2 * np.pi, n_a + 1)[:-1]
    t = np.linspace(0, 1, n_r + 1)[:-1]
    r = (COLLO - 1.0) * (1 - t) + 0.8 * t
    y = Y_COLLO - 0.8 - 12.0 * t ** 1.3
    onda = _onda(N_VENT * th + 0.4 * np.sin(3 * th))
    alto = 1.4 * np.sin(np.pi * t)[:, None] * onda[None, :] + 0.6 * np.sin(2 * th + 5 * t[:, None])
    R = r[:, None] + 0 * th[None, :]
    Y = y[:, None] + alto
    V = np.stack([R * np.cos(th)[None, :], Y, R * np.sin(th)[None, :]], -1).reshape(-1, 3)
    V = np.concatenate([V, [[0.0, Y_COLLO - 13.5, 0.0]]])
    rho = RHO_K - 45.0 * t
    UV = uv_foglio(np.broadcast_to(rho[:, None], R.shape), np.broadcast_to(ROT - th[None, :], R.shape)).reshape(-1, 2)
    UV = np.concatenate([UV, UV[-1:]])
    idx = np.arange(n_r * n_a).reshape(n_r, n_a)
    a = idx[:-1].ravel(); b1 = np.roll(idx, -1, 1)[:-1].ravel()
    c1 = np.roll(idx, -1, 1)[1:].ravel(); d1 = idx[1:].ravel()
    T = [np.stack([a, b1, c1], 1), np.stack([a, c1, d1], 1)]
    ult = idx[-1]
    T.append(np.stack([ult, np.roll(ult, -1), np.full(n_a, n_r * n_a)], 1))
    T = np.concatenate(T)
    # le facce guardano in su: dall'alto si vede la stampa
    N = normali(V, T)
    if N[:, 1].mean() < 0:
        T = T[:, ::-1]
    return V, UV, T


# ---------------------------------------------------------------- tutto


# ---------------------------------------------------------------- la lettura
# gli strati (contenuto facoltativo) dei due PDF: il DT e le note
STRATO_DT, STRATO_NOTE = "technical-drawing", "notes"
# il foglio e il collarino che il codice sa montare, in mm: il lato del
# quadrato, e la larghezza e l'altezza del DT del collarino
LATO_TOLL = 0.01
COLLARINO_MM, COLLARINO_TOLL = (264.2, 205.3), 3.0


def _viste(pag, gap=10.0):
    """I riquadri (mm, y dall'alto) delle viste del DT: gli oggetti dello
    strato del DT uniti finche' si toccano (a meno di `gap` mm), in ordine
    di lettura - per righe, poi da sinistra."""
    g = [list(pag.riquadro(o)) for o, s in zip(pag.ogg, pag.strato) if s == STRATO_DT]

    def tocca(r, q):
        return r[0] < q[2] + gap and q[0] < r[2] + gap and r[1] < q[3] + gap and q[1] < r[3] + gap

    cambia = True
    while cambia:
        cambia = False
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                if tocca(g[i], g[j]):
                    r, q = g[i], g.pop(j)
                    g[i] = [min(r[0], q[0]), min(r[1], q[1]), max(r[2], q[2]), max(r[3], q[3])]
                    cambia = True
                    break
            if cambia:
                break
    righe = sorted(g, key=lambda r: r[1])
    out, riga = [], []
    for r in righe:
        if riga and r[1] > riga[0][3]:
            out.extend(sorted(riga, key=lambda q: q[0]))
            riga = []
        riga.append(r)
    out.extend(sorted(riga, key=lambda q: q[0]))
    return [tuple(r) for r in out]


def _uguali(viste, toll=1.0):
    """Le viste lunghe e larghe come la prima (entro `toll` mm)."""
    w0, h0 = viste[0][2] - viste[0][0], viste[0][3] - viste[0][1]
    return [v for v in viste if abs(v[2] - v[0] - w0) <= toll and abs(v[3] - v[1] - h0) <= toll]


@dataclass
class Foglio:
    """Il foglio quadrato: le viste (mm, y dall'alto, arrotondate al mm),
    la grafica e poi il bianco."""
    pdf: str
    viste: list
    lato: float
    avvisi: list = field(default_factory=list)

    @property
    def regione(self):
        """La vista della grafica in punti, con la y dall'alto."""
        return tuple(v / MM for v in self.viste[0])


@dataclass
class Collarino:
    """Il collarino: le viste (mm), la grafica, la vernice e il rilievo.
    Le zone si allargano di 3 mm ai lati e 5 sopra e sotto, attorno al DT."""
    pdf: str
    viste: list
    larghezza: float
    altezza: float
    avvisi: list = field(default_factory=list)


def leggi(pdf):
    """Il `Foglio` o il `Collarino` di questo PDF, o None se non e' nessuno
    dei due. Il foglio: almeno due viste quadrate uguali, del lato che il
    codice sa avvolgere. Il collarino: almeno tre viste uguali, della misura
    del collarino che sa montare."""
    try:
        pag = Pagina(pdf)
    except Exception:
        return None
    if STRATO_DT not in pag.strato:
        return None
    viste = _viste(pag)
    if not viste:
        return None
    uguali = _uguali(viste)
    w = viste[0][2] - viste[0][0]
    h = viste[0][3] - viste[0][1]
    if abs(w - h) <= LATO_TOLL * w and abs(w - LATO) <= LATO_TOLL * LATO and len(uguali) >= 2:
        tonde = [tuple(float(round(c)) for c in v) for v in uguali]
        avvisi = []
        if len(uguali) > 2:
            avvisi.append("foglio: %d viste del DT, servono le prime due (la grafica e il "
                          "bianco); le altre non entrano nel modello" % len(uguali))
        return Foglio(pdf, tonde, float(w), avvisi)
    if (abs(w - COLLARINO_MM[0]) <= COLLARINO_TOLL and abs(h - COLLARINO_MM[1]) <= COLLARINO_TOLL
            and len(uguali) >= 3):
        zone = [(float(np.floor(v[0])) - 3, float(np.floor(v[1])) - 5,
                 float(np.ceil(v[2])) + 3, float(np.ceil(v[3])) + 5) for v in uguali]
        # le lastre stanno dove sta la vista della grafica, spostate della loro
        # vista (al decimo di mm: le zone devono avere gli stessi pixel)
        z0 = zone[0]
        sp = [(round(v[0] - uguali[0][0], 1), round(v[1] - uguali[0][1], 1)) for v in uguali[1:3]]
        zone = [z0] + [(z0[0] + dx, z0[1] + dy, z0[2] + dx, z0[3] + dy) for dx, dy in sp]
        avvisi = []
        if len(uguali) > 3:
            avvisi.append("collarino: %d viste del DT, servono le prime tre (la grafica, la "
                          "vernice e il rilievo)" % len(uguali))
        return Collarino(pdf, zone, float(w), float(h), avvisi)
    return None


def riconosci(pdfs):
    """`(foglio, collarino)` dai PDF dell'avvolto, in qualunque ordine.
    ValueError che dice cosa manca."""
    fogli, collari, altri = [], [], []
    for k, p in enumerate(pdfs):
        letto = leggi(p)
        (fogli if isinstance(letto, Foglio) else collari if isinstance(letto, Collarino)
         else altri).append(letto if letto is not None else k + 1)
    if len(fogli) == 1 and len(collari) == 1 and not altri:
        return fogli[0], collari[0]
    sa = ("per ora l'avvolto e' l'uovo incartato col collarino: due PDF, il foglio "
          "quadrato di %.0f mm (il DT ripetuto per la grafica e il bianco) e il "
          "collarino di %.0f x %.0f mm (il DT ripetuto per la grafica, la vernice e "
          "il rilievo), con lo strato %r" % (LATO, COLLARINO_MM[0], COLLARINO_MM[1], STRATO_DT))
    if altri:
        raise ValueError("incarto avvolto: il PDF %s non e' ne' il foglio ne' il "
                         "collarino; %s" % (", ".join(str(a) for a in altri), sa))
    if not fogli:
        raise ValueError("incarto avvolto: manca il PDF del foglio; " + sa)
    if not collari:
        raise ValueError("incarto avvolto: manca il PDF del collarino; " + sa)
    raise ValueError("incarto avvolto: un foglio e un collarino soli; " + sa)


def dichiara(foglio, collarino):
    """Le righe dei dettagli tecnici."""
    return ["Incarto avvolto: l'uovo incartato col collarino",
            "foglio quadrato %.0f x %.0f mm: la grafica e il bianco (il film "
            "metallizzato resta a vista dove non c'e' il bianco)" % (foglio.lato, foglio.lato),
            "collarino %.0f x %.0f mm: la grafica, la vernice lucida, il rilievo e "
            "l'oro a freddo" % (collarino.larghezza, collarino.altezza),
            "uovo alto %.0f mm fino al collo, in tutto %.0f mm col ciuffo: la sagoma "
            "dell'uovo e del ciuffo e' quella del primo caso" % (Y_COLLO, Y_COLLO + Y_CIMA)]


# ---------------------------------------------------------------- tutto
def costruisci(foglio, collarino, uscita, tex_max=4096, maglia=None):
    """Il GLB dell'uovo incartato in `uscita`. `maglia`: dove salvare la
    maglia per il controllo delle intersezioni (un .npz), se serve."""
    rng = np.random.default_rng(11)
    a = Pagina(collarino.pdf)
    b = Pagina(foglio.pdf)
    zf, zb = foglio.viste[0], foglio.viste[1]
    ab_b = abbina(b, foglio.pdf, b.zone_testo(), riquadri_note(b))
    art_f = grafica_vista(b, zf, PX_F, ab_b).convert("RGB")
    bianco = np.asarray(b.rendi(zb, PX_F), np.int16)
    bianco = (bianco.max(-1) - bianco.min(-1) > 12) | (bianco.sum(-1) < 700)
    zc, zv, zr = collarino.viste[:3]
    ab_a = abbina(a, collarino.pdf, a.zone_testo(), riquadri_note(a))
    art_c = grafica_vista(a, zc, PX_COLL, ab_a).convert("RGB")
    vern = np.asarray(grafica_vista(a, zv, PX_COLL, ab_a).convert("RGB"), np.int16)
    vern = (vern.max(-1) - vern.min(-1)) > 40
    rilv = np.asarray(grafica_vista(a, zr, PX_COLL, ab_a).convert("RGB"), np.int16)
    rilv = (rilv.max(-1) - rilv.min(-1)) > 40
    masc = collarino_maschera(a, zc, PX_COLL)
    Wf, Hf = art_f.size
    Wc, Hc = art_c.size
    Wr = int(LATO * PX_R)
    X2, X3 = Wf, Wf + Wc
    AW, AH = Wf + Wc + Wr, max(Hf, Hc + 64, Wr)
    atl = Image.new("RGB", (AW, AH), (255, 255, 255))
    atl.paste(art_f, (0, 0))
    atl.paste(art_c, (X2, 0))
    atl.paste(Image.new("RGB", (32, 32), (236, 232, 224)), (X2 + 48, Hc + 16))
    atl.paste(Image.new("RGB", (Wr, Wr), DENTRO), (X3, 0))
    rgb = np.asarray(atl, np.float32)
    metallo = np.zeros((AH, AW), np.float32)
    ruv = np.full((AH, AW), 0.55, np.float32)
    metallo[:Hf, :Wf] = (1.0 - bianco[:Hf, :Wf]) * METALLO
    ruv[:Hf, :Wf] = np.where(bianco[:Hf, :Wf], 0.4, RUVIDO)
    metallo[:Wr, X3:X3 + Wr] = 0.55
    ruv[:Wr, X3:X3 + Wr] = 0.1
    ac = np.asarray(art_c, np.int16)
    oro = np.abs(ac - np.array(ORO)).sum(-1) < 90
    sub_r = np.where(vern, 0.3, 0.65)
    sub_r = np.where(oro, 0.2, sub_r)
    ruv[:Hc, X2:X2 + Wc] = sub_r
    metallo[:Hc, X2:X2 + Wc] = np.where(oro, 1.0, 0.0)
    lin = _lineare(rgb) * (1.0 - metallo[..., None] * 0.08)
    lin[:Hc, X2:X2 + Wc] *= np.where(oro, 1.0, 0.72)[..., None]
    base = Image.fromarray(np.round(_srgb(lin)).astype(np.uint8))
    mr = np.zeros((AH, AW, 3), np.uint8)
    mr[..., 0] = 255
    mr[..., 1] = np.round(ruv * 255).astype(np.uint8)
    mr[..., 2] = np.round(metallo * 255).astype(np.uint8)
    nrm = np.zeros((AH, AW, 3), np.uint8)
    nrm[...] = (128, 128, 255)
    for x0, w, px, forza in ((0, Wf, PX_F, 1.0), (X3, Wr, PX_R, 1.5)):
        yy, xx = np.mgrid[0:w, 0:w]
        u = (xx + 0.5) / px - LATO / 2
        v = (yy + 0.5) / px - LATO / 2
        nrm[:w, x0:x0 + w] = faccette(np.hypot(u, v), np.arctan2(v, u), np.random.default_rng(5), forza).reshape(w, w, 3)
    h = np.zeros((Hc, Wc), np.float32)
    h[:] = np.where(rilv, 0.35, 0.0)
    nrm[:Hc, X2:X2 + Wc] = np.asarray(rilievo.normali(h, PX_COLL))

    # il foglio: l'uovo col collo, e il ciuffo (le facce verso fuori)
    Ve, UVe, Te, s_top, raggi = uovo_e_collo()
    Ne = normali(Ve, Te)
    lato_ = Ve[:, 1] > 20
    if (Ne[lato_] * np.stack([Ve[lato_, 0], 0 * Ve[lato_, 1], Ve[lato_, 2]], 1)).sum() < 0:
        Te = Te[:, ::-1]
    pts, tri, Vc, ovale = maglia_collarino(masc, raggi)
    # davanti al ciuffo c'e' solo la parte frontale dell'ovale (non gli attacchi delle braccia)
    fronte = ovale & (Vc[:, 1] > Y_COLLO - 3.0)
    Vv, UVv, Tv, phi = ciuffo(rng, Ostacoli(Ve, Vc, davanti=Vc[fronte], collare=Vc, ovale=Vc[ovale]))
    Nv = normali(Vv, Tv)
    # all'anello la faccia di fuori guarda via dall'asse
    anello = np.arange(M_VENT * 3)
    if (Nv[anello] * np.stack([Vv[anello, 0], 0 * Vv[anello, 1], Vv[anello, 2]], 1)).sum() < 0:
        Tv = Tv[:, ::-1]
    # dentro il collo, sotto l'anello, il foglio raccolto: dall'alto non c'e' vuoto
    Vt, UVt, Tt = tappo(rng)
    Vf = np.concatenate([Ve, Vv, Vt])
    UVs = np.concatenate([UVe, UVv, UVt])
    uv_fuori = UVs * [Wf / AW, Hf / AH]
    uv_dentro = np.stack([(X3 + UVs[:, 0] * Wr) / AW, (UVs[:, 1] * Wr) / AH], 1)
    uv_specchio = np.stack([1 - UVs[:, 1], 1 - UVs[:, 0]], 1) * [Wf / AW, Hf / AH]
    # i lembi di lato mostrano fuori il rovescio (nelle foto di fianco il ciuffo e' azzurro)
    col = (Tv % M_VENT).astype(float)
    bb = col * 2 * np.pi / M_VENT
    cb = np.cos(np.arctan2(np.sin(bb).mean(1), np.cos(bb).mean(1)))
    lato = np.abs(cb) > np.cos(np.radians(45))
    Tv = Tv + len(Ve)
    T_dritto = np.concatenate([Te, Tv[~lato], Tt + len(Ve) + len(Vv)])
    T_rovescio = Tv[lato]

    # il collarino
    Nc = normali(Vc, tri)
    fuori_c = np.stack([Vc[:, 0], 0 * Vc[:, 1], Vc[:, 2]], 1)
    if (Nc * fuori_c).sum() < 0:
        tri = tri[:, ::-1]
    uvc = np.stack([(X2 + pts[:, 0] * PX_COLL) / AW, (pts[:, 1] * PX_COLL) / AH], 1)
    uv_retro = np.tile([(X2 + 64) / AW, (Hc + 32) / AH], (len(Vc), 1))

    NOMI = ["uovo", "ciuffo", "collarino"]
    ne = len(Te)
    et_d = np.full(len(T_dritto), 1)
    et_d[:ne] = 0
    pezzi, V, UVl, T, ET, n0 = [], [], [], [], [], 0
    # il rovescio sugli stessi vertici, coi triangoli girati: si vede da dietro
    for nome, blocchi in (("incarto", [(Vf, uv_fuori, T_dritto, et_d), (Vf, uv_dentro, T_dritto[:, ::-1], None),
                                         (Vf, uv_dentro, T_rovescio, 1), (Vf, uv_specchio, T_rovescio[:, ::-1], None)]),
                          ("collarino", [(Vc, uvc, tri, 2), (Vc, uv_retro, tri[:, ::-1], None)])):
        t0 = sum(len(t) for t in T)
        for v, uv, t, et in blocchi:
            usati, t = np.unique(t, return_inverse=True)
            t = t.reshape(-1, 3)
            V.append(v[usati])
            UVl.append(uv[usati])
            T.append(t + n0)
            ET.append(et if et is not None else np.full(len(t), -1))
            if np.isscalar(et):
                ET[-1] = np.full(len(t), et)
            n0 += len(usati)
        pezzi.append((nome, t0, sum(len(t) for t in T)))
    V = np.concatenate(V)
    UV = np.concatenate(UVl)
    T = np.concatenate(T)
    ET = np.concatenate(ET)
    # per il controllo delle intersezioni basta una faccia per superficie
    una = ET >= 0
    if maglia:
        np.savez(maglia, V=V, T=T[una], etichetta=ET[una], nomi=np.array(NOMI))
    exporters.write_glb_mesh(V, UV, T, base, uscita, tex_max=tex_max, parti=pezzi,
                             mr=Image.fromarray(mr), normale=Image.fromarray(nrm))
    return dichiara(foglio, collarino) + foglio.avvisi + collarino.avvisi
