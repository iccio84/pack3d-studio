"""Un PDF che e' solo una foto della tavola, rifatto vettoriale.

Ogni famiglia legge forma e misure dai tratti vettoriali della fustella. Un
PDF esportato come immagine non ne ha: la fustella, la grafica e il DT sono
pixel di una foto (`artwork.solo_immagine`). Ma la fustella nella foto si
vede: e' disegnata con una penna di un colore pieno, sottile, che la grafica
non usa per righe lunghe. Questo modulo la ritrova e ne rifa' i tratti:

1. la penna: fra i colori saturi della foto, quello che fa piu' righe
   sottili e lunghe (`_penna`). Le campiture dello stesso colore (una
   tabella, un fondo) non sono sottili e restano fuori;
2. i tratti: la maschera della penna assottigliata a un pixel (`_scheletro`)
   e seguita in polilinee (`_polilinee`), che si semplificano tenendo gli
   spigoli. Un tratteggio resta a pezzi, come nel PDF vettoriale: la
   cerniera si riconosce dai suoi pezzi;
3. la scala: una foto non sa quanto e' grande il foglio (il PDF dice 72 ppi
   anche quando la foto e' a 150). La misura la da' chi conosce il pack: la
   larghezza della fustella aperta, la quota piu' esterna del DT
   (`larghezza_fustella`, in mm). Senza, la foto non si legge e l'errore lo
   dice;
4. il PDF nuovo: la stessa foto, scalata alla misura vera, e sopra i tratti
   della fustella con la penna della foto. Da qui in poi e' un PDF come gli
   altri: le famiglie lo leggono, la texture e' la foto.

Vedi regole/pdf.md, *Un PDF che e' una foto*.
"""
from __future__ import annotations

import io

import numpy as np
from scipy import ndimage as ndi

MM2PT = 72.0 / 25.4

# la penna: saturazione e luce minime di un pixel della fustella
SATURA = 0.28
LUCE = 0.45
# una riga e' sottile: sparisce con un'apertura di tanti pixel di lato
APERTURA = 5
# una riga lunga, per scegliere la penna: almeno tanti pixel di fila
LUNGA = 60
# i pezzi piu' corti di cosi' (px) sono rumore, non tratti
CORTO = 4
# semplificazione delle polilinee: scarto massimo (px)
SCARTO = 0.8
# tratti della stessa fustella: non piu' lontani di cosi' (px)
VICINI = 40


def _hsv(rgb):
    a = rgb.astype(np.float32) / 255.0
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.zeros_like(mx)
    dd = np.maximum(d, 1e-6)
    h = np.where(mx == r, ((g - b) / dd) % 6, h)
    h = np.where(mx == g, (b - r) / dd + 2, h)
    h = np.where(mx == b, (r - g) / dd + 4, h)
    return h * 60.0, s, mx


def _sottile(m):
    return m & ~ndi.binary_opening(m, np.ones((APERTURA, APERTURA), bool))


def _righe_lunghe(m):
    """Quanti pixel della maschera stanno in corse orizzontali o verticali
    di almeno `LUNGA` pixel."""
    tot = 0
    for mm in (m, m.T):
        x = mm.astype(np.int8)
        d = np.diff(np.pad(x, ((0, 0), (1, 1))), axis=1)
        for r in range(x.shape[0]):
            ini = np.flatnonzero(d[r] == 1)
            fin = np.flatnonzero(d[r] == -1)
            lun = fin - ini
            tot += int(lun[lun >= LUNGA].sum())
    return tot


def _penna(rgb):
    """(maschera sottile della fustella, tinta della penna in gradi)."""
    h, s, v = _hsv(rgb)
    satura = (s >= SATURA) & (v >= LUCE)
    meglio = None
    for t in range(0, 360, 20):
        dentro = satura & (((h - t) % 360) < 20)
        if dentro.sum() < 200:
            continue
        sott = _sottile(dentro)
        punti = _righe_lunghe(sott)
        if meglio is None or punti > meglio[0]:
            meglio = (punti, t)
    if meglio is None or meglio[0] == 0:
        raise ValueError("nella foto non c'e' una fustella: nessun colore "
                         "fa righe sottili e lunghe")
    t = meglio[1]
    # la tinta piena della penna, e un margine attorno
    dentro = satura & (((h - t) % 360) < 20)
    tinta = float(np.median(h[_sottile(dentro)]))
    vicino = np.minimum((h - tinta) % 360, (tinta - h) % 360) <= 22
    pieno = satura & vicino
    sott = _sottile(pieno)
    # le campiture della penna (una tabella) si tolgono con un bordo attorno:
    # i loro contorni e le scritte dentro non sono fustella
    camp = ndi.binary_dilation(ndi.binary_opening(pieno, np.ones((APERTURA,) * 2, bool)),
                               iterations=4)
    return sott & ~camp, tinta


def _scheletro(m):
    """Zhang-Suen: la maschera assottigliata a un pixel."""
    img = np.pad(m.astype(np.uint8), 1)
    while True:
        cambiato = False
        for passo in (0, 1):
            P = img
            p2, p3, p4 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:]
            p5, p6, p7 = P[2:, 2:], P[2:, 1:-1], P[2:, :-2]
            p8, p9 = P[1:-1, :-2], P[:-2, :-2]
            vic = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(x.astype(np.int16) for x in vic)
            seq = vic + [p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int16)
                    for i in range(8))
            if passo == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            via = (P[1:-1, 1:-1] == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if via.any():
                img[1:-1, 1:-1][via] = 0
                cambiato = True
        if not cambiato:
            return img[1:-1, 1:-1].astype(bool)


_PASSI = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _polilinee(sk):
    """Le polilinee dello scheletro, in (x, y) pixel: da un estremo o da un
    incrocio all'altro, e gli anelli chiusi."""
    H, W = sk.shape
    pad = np.pad(sk, 1)
    ys, xs = np.nonzero(sk)
    vicini = sum(np.roll(np.roll(pad, -dy, 0), -dx, 1)[1:-1, 1:-1].astype(np.int8)
                 for dy, dx in _PASSI)
    # un incrocio vero divide i vicini in tre gruppi o piu' (i passaggi da
    # vuoto a pieno attorno al pixel); uno scalino ha tre vicini ma due gruppi
    giro = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0)]
    anello = [np.roll(np.roll(pad, -dy, 0), -dx, 1)[1:-1, 1:-1] for dy, dx in giro]
    passaggi = sum((~anello[i] & anello[i + 1]).astype(np.int8) for i in range(8))
    nodo = sk & ((vicini == 1) | (passaggi >= 3))
    visto = set()
    linee = []

    def avanti(y, x, py, px):
        pts = [(x, y)]
        while True:
            nxt = None
            for dy, dx in _PASSI:
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and sk[ny, nx] and (ny, nx) != (py, px):
                    e = ((y, x), (ny, nx)) if (y, x) < (ny, nx) else ((ny, nx), (y, x))
                    if e in visto:
                        continue
                    nxt = (ny, nx, e)
                    break
            if nxt is None:
                return pts
            ny, nx, e = nxt
            visto.add(e)
            py, px, y, x = y, x, ny, nx
            pts.append((x, y))
            if nodo[y, x]:
                return pts

    for y, x in zip(*np.nonzero(nodo)):
        for dy, dx in _PASSI:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and sk[ny, nx]:
                e = ((y, x), (ny, nx)) if (y, x) < (ny, nx) else ((ny, nx), (y, x))
                if e in visto:
                    continue
                visto.add(e)
                linee.append([(x, y)] + avanti(ny, nx, y, x))
    # gli anelli senza nodi
    for y, x in zip(ys, xs):
        for dy, dx in _PASSI:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and sk[ny, nx]:
                e = ((y, x), (ny, nx)) if (y, x) < (ny, nx) else ((ny, nx), (y, x))
                if e not in visto:
                    visto.add(e)
                    linee.append([(x, y)] + avanti(ny, nx, y, x))
    return [np.asarray(p, float) for p in linee if len(p) >= 2]


def _semplifica(p, eps=SCARTO):
    """Douglas-Peucker."""
    if len(p) <= 2:
        return p
    a, b = p[0], p[-1]
    d = b - a
    n = np.hypot(*d)
    if n < 1e-9:
        dist = np.hypot(*(p - a).T)
    else:
        dist = np.abs(d[0] * (p[:, 1] - a[1]) - d[1] * (p[:, 0] - a[0])) / n
    i = int(np.argmax(dist))
    if dist[i] <= eps:
        return np.stack([a, b])
    return np.concatenate([_semplifica(p[:i + 1], eps)[:-1], _semplifica(p[i:], eps)])


def _raddrizza(p, tol=1.2):
    """Un lato quasi orizzontale o verticale, per un pixel di scalino, e'
    dritto: lo si porta alla sua riga media."""
    q = p.copy()
    for i in range(len(q) - 1):
        d = q[i + 1] - q[i]
        if abs(d[1]) <= tol and abs(d[0]) > 4 * abs(d[1]):
            q[i, 1] = q[i + 1, 1] = (q[i, 1] + q[i + 1, 1]) / 2
        elif abs(d[0]) <= tol and abs(d[1]) > 4 * abs(d[0]):
            q[i, 0] = q[i + 1, 0] = (q[i, 0] + q[i + 1, 0]) / 2
    return q


def _fustella(linee):
    """Le polilinee della fustella: il gruppo di tratti vicini piu' lungo
    (il DT in un angolo, le scritte e i segni sparsi restano fuori)."""
    if not linee:
        return []
    box = np.array([[p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()]
                    for p in linee])
    n = len(linee)
    padre = list(range(n))

    def radice(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    ordine = np.argsort(box[:, 0])
    for k, i in enumerate(ordine):
        for j in ordine[k + 1:]:
            if box[j, 0] > box[i, 2] + VICINI:
                break
            if box[j, 1] <= box[i, 3] + VICINI and box[i, 1] <= box[j, 3] + VICINI:
                padre[radice(i)] = radice(j)
    lung = {}
    for i, p in enumerate(linee):
        r = radice(i)
        lung[r] = lung.get(r, 0.0) + float(np.hypot(*np.diff(p, axis=0).T).sum())
    best = max(lung, key=lung.get)
    return [p for i, p in enumerate(linee) if radice(i) == best]


def tratti_della_foto(rgb):
    """(polilinee della fustella in pixel, tinta della penna)."""
    m, tinta = _penna(rgb)
    sk = _scheletro(m)
    linee = []
    for p in _polilinee(sk):
        if np.hypot(*np.diff(p, axis=0).T).sum() < CORTO:
            continue
        linee.append(_raddrizza(_semplifica(p)))
    return _fustella(linee), tinta


def _rgb_tinta(t):
    import colorsys
    return colorsys.hsv_to_rgb((t % 360) / 360.0, 1.0, 1.0)


def vettoriale(pdf_in, pdf_out, larghezza_mm, page_no=0):
    """Rifa' vettoriale il PDF-foto `pdf_in` in `pdf_out`: la foto scalata
    perche' la fustella sia larga `larghezza_mm`, e sopra i suoi tratti.
    Torna i millimetri per pixel."""
    import pypdfium2 as pdfium
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import ContentStream, DecodedStreamObject, NameObject, RectangleObject

    larghezza_mm = float(larghezza_mm)
    if not 20 <= larghezza_mm <= 3000:
        raise ValueError("larghezza della fustella fuori misura: %r mm" % larghezza_mm)
    doc = pdfium.PdfDocument(pdf_in)
    try:
        pagina = doc[page_no]
        pw, ph = pagina.get_size()
        # la foto alla sua risoluzione: un pixel per punto, o di piu' se la
        # foto e' piu' fitta della pagina
        scala = 1.0
        for o in pagina.get_objects(max_depth=3):
            try:
                w, h = o.get_px_size()
                scala = max(scala, w / pw, h / ph)
            except Exception:
                continue
        rgb = np.asarray(pagina.render(scale=min(scala, 4.0)).to_pil().convert("RGB"))
    finally:
        doc.close()
    linee, tinta = tratti_della_foto(rgb)
    if not linee:
        raise ValueError("nella foto non c'e' una fustella")
    xs = np.concatenate([p[:, 0] for p in linee])
    largo_px = float(xs.max() - xs.min())
    mm_px = larghezza_mm / largo_px
    # i pixel della resa -> punti del PDF nuovo
    f = mm_px * MM2PT
    Hpx = rgb.shape[0]
    # la pagina: la foto scalata di quanto serve
    lettore = PdfReader(pdf_in)
    pag = lettore.pages[page_no]
    k = f * rgb.shape[1] / float(pw)
    pag.add_transformation(Transformation().scale(k, k))
    pag.mediabox = RectangleObject([0, 0, float(pw) * k, float(ph) * k])
    for box in ("/CropBox", "/TrimBox", "/BleedBox", "/ArtBox"):
        if box in pag:
            del pag[box]
    r, g, b = _rgb_tinta(tinta)
    righe = ["q", "%.3f %.3f %.3f RG" % (r, g, b), "0.5 w", "1 J", "1 j"]
    for p in linee:
        x = p[:, 0] * f
        y = (Hpx - p[:, 1]) * f
        righe.append("%.3f %.3f m" % (x[0], y[0]))
        righe.extend("%.3f %.3f l" % (u, v) for u, v in zip(x[1:], y[1:]))
        righe.append("S")
    righe.append("Q")
    scrittore = PdfWriter()
    scrittore.add_page(pag)
    nuova = scrittore.pages[0]
    flusso = DecodedStreamObject()
    flusso.set_data("\n".join(righe).encode("ascii"))
    cont = nuova.get_contents()
    base = cont.get_data() if cont is not None else b""
    tutto = DecodedStreamObject()
    tutto.set_data(base + b"\n" + flusso.get_data())
    nuova[NameObject("/Contents")] = scrittore._add_object(tutto)
    buf = io.BytesIO()
    scrittore.write(buf)
    with open(pdf_out, "wb") as fh:
        fh.write(buf.getvalue())
    return mm_px
