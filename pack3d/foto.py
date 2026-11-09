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
# pulizia della foto: una campitura della penna (una tabella) e' larga
# almeno tanti mm, e si copre con un bordo di tanti mm attorno
CAMPITURA_MM = 2.5
BORDO_MM = 3.0
# il fondo tenue di una tabella della penna: saturazione minima
TENUE = 0.06
# la GDA vuota (techink.icone_gda): un anello chiuso della tinta della penna,
# col lato corto fra questi mm e la proporzione fra questi valori, pieno
# almeno di tanto rispetto ai pixel del suo bordo. Il bordo e' celeste
# chiaro (ciano al 35%), e col rumore della JPEG alla saturazione della penna
# si spezza: si cerca a una saturazione piu' bassa
ICONA_LATO_MM = (5.0, 20.0)
ICONA_PROPORZIONE = (1.2, 1.8)
ICONA_CHIUSA = 3.0
ICONA_SATURA = 0.10
# quanti pixel buoni per lato fanno l'estremo di una riga, nella copertura
ESTREMI = 5


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


def icone_gda(rgb, tinta, mm_px):
    """Le GDA vuote della foto (vedi `techink.icone_gda`): le maschere delle
    icone, bordo compreso. E' un'icona un anello chiuso della tinta della
    penna, anche chiara (`ICONA_SATURA`) - pieno, coi buchi chiusi, almeno
    `ICONA_CHIUSA` volte i pixel del bordo - col lato corto fra
    `ICONA_LATO_MM` e la proporzione fra `ICONA_PROPORZIONE`."""
    lo, hi = ICONA_LATO_MM
    plo, phi = ICONA_PROPORZIONE
    h, s, v = _hsv(rgb)
    vicino = np.minimum((h - tinta) % 360, (tinta - h) % 360) <= 22
    chiaro = (s >= ICONA_SATURA) & (v >= LUCE) & vicino
    lab, n = ndi.label(chiaro, np.ones((3, 3), bool))
    icone = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None:
            continue
        corto, lungo = sorted(((sl[0].stop - sl[0].start) * mm_px,
                               (sl[1].stop - sl[1].start) * mm_px))
        if not (lo <= corto <= hi and plo * corto <= lungo <= phi * corto):
            continue
        bordo = lab[sl] == k
        chiusa = ndi.binary_fill_holes(bordo)
        if chiusa.sum() < ICONA_CHIUSA * bordo.sum():
            continue
        m = np.zeros(chiaro.shape, bool)
        m[sl] = chiusa
        icone.append(m)
    return icone


def _ricopri(out, m, bordo):
    """`out` con i pixel di `m` rifatti da quelli attorno, riga per riga: fra
    il pixel buono a sinistra e quello a destra. Le venature del legno e le
    sfumature dall'alto in basso continuano sotto l'icona; con la media di
    tutto l'anello restava un tassello liscio sul fondo che cambia. Gli
    estremi sono la mediana dei `ESTREMI` pixel buoni piu' vicini da ogni
    lato: un pixel storto all'estremo tingeva tutta la riga (un filo celeste
    sopra l'icona del T1x10)."""
    # e l'alone della JPEG attorno al bordo
    m = ndi.binary_dilation(m, iterations=6)
    ys, xs = np.nonzero(m)
    H, W = m.shape
    y0, y1 = max(0, ys.min() - bordo), min(H, ys.max() + bordo + 1)
    x0, x1 = max(0, xs.min() - bordo), min(W, xs.max() + bordo + 1)
    dentro = m[y0:y1, x0:x1]
    pezzo = out[y0:y1, x0:x1].astype(np.float32)
    colonne = np.arange(dentro.shape[1])
    for r in range(dentro.shape[0]):
        via = dentro[r]
        if not via.any() or via.all():
            continue
        buone = colonne[~via]
        riga = pezzo[r].copy()
        for j in np.flatnonzero(np.diff(via.astype(np.int8)) != 0):
            # j e' l'ultimo pixel prima di un salto: l'estremo buono e' j o j+1
            e = j if not via[j] else j + 1
            lato = buone[buone <= e][-ESTREMI:] if e == j else buone[buone >= e][:ESTREMI]
            riga[e] = np.median(pezzo[r, lato], axis=0)
        for c in range(pezzo.shape[2]):
            pezzo[r, via, c] = np.interp(colonne[via], buone, riga[~via, c])
    out = out.copy()
    out[y0:y1, x0:x1] = np.clip(np.rint(pezzo), 0, 255).astype(out.dtype)
    return out


def pulisci(rgb, tinta, mm_px):
    """La foto senza i segni della penna (regole/pulizia.md, *Il PDF-foto*).
    Le campiture della penna - una tabella, i valori - si coprono col colore
    che hanno attorno, rettangolo per rettangolo, con le scritte dentro; i
    tratti sottili (la fustella) si riempiono coi pixel vicini."""
    h, s, v = _hsv(rgb)
    vicino = np.minimum((h - tinta) % 360, (tinta - h) % 360) <= 22
    pieno = (s >= SATURA) & (v >= LUCE) & vicino
    out = rgb.copy()
    lato = max(3, int(round(CAMPITURA_MM / mm_px)))
    camp = ndi.binary_opening(pieno, np.ones((lato, lato), bool))
    bordo = max(2, int(round(BORDO_MM / mm_px)))
    H, W = pieno.shape
    # le celle vicine sono una tabella sola, col suo fondo della stessa
    # tinta ma tenue (il riquadro chiaro attorno ai valori)
    tenue = vicino & (s >= TENUE) & (v >= LUCE)
    gruppi, n = ndi.label(ndi.binary_dilation(camp, iterations=bordo) | tenue)
    tocca = np.unique(gruppi[camp])
    gruppi = np.where(np.isin(gruppi, tocca[tocca > 0]), gruppi, 0)
    for sl in ndi.find_objects(gruppi):
        if sl is None:
            continue
        y0, y1 = max(0, sl[0].start - bordo), min(H, sl[0].stop + bordo)
        x0, x1 = max(0, sl[1].start - bordo), min(W, sl[1].stop + bordo)
        anello = np.zeros((H, W), bool)
        anello[max(0, y0 - bordo):min(H, y1 + bordo), max(0, x0 - bordo):min(W, x1 + bordo)] = True
        anello[y0:y1, x0:x1] = False
        anello &= ~pieno
        colore = np.median(rgb[anello], axis=0) if anello.any() else (255, 255, 255)
        out[y0:y1, x0:x1] = np.asarray(colore, dtype=rgb.dtype)
        pieno[y0:y1, x0:x1] = False
    # la GDA vuota: la sagoma dell'icona dell'energia, bordata con la penna e
    # bianca dentro. Tolto il bordo come un tratto, il bianco restava sulla
    # grafica (la plancia del display T1x10): si toglie intera
    for dentro in icone_gda(rgb, tinta, mm_px):
        out = _ricopri(out, dentro, bordo)
        pieno &= ~dentro
    # i tratti: col pixel buono piu' vicino
    tratti = ndi.binary_dilation(pieno, iterations=2)
    if tratti.any():
        _, (iy, ix) = ndi.distance_transform_edt(tratti, return_indices=True)
        out[tratti] = out[iy[tratti], ix[tratti]]
    return out


def _rgb_tinta(t):
    import colorsys
    return colorsys.hsv_to_rgb((t % 360) / 360.0, 1.0, 1.0)


def _in_quadricromia(pdf_in, page_no):
    """Se le immagini della pagina sono in quadricromia."""
    from pypdf import PdfReader
    try:
        modi = {im.image.mode for im in PdfReader(pdf_in).pages[page_no].images}
    except Exception:
        return False
    return bool(modi) and modi <= {"CMYK"}


def vettoriale(pdf_in, pdf_out, larghezza_mm, page_no=0):
    """Rifa' vettoriale il PDF-foto `pdf_in` in `pdf_out`: la foto scalata
    perche' la fustella sia larga `larghezza_mm`, e sopra i suoi tratti.
    Torna i millimetri per pixel."""
    import pypdfium2 as pdfium
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

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
    # la pagina: la foto senza i segni della penna, scalata di quanto serve
    from PIL import Image
    pulita = io.BytesIO()
    im = Image.fromarray(pulisci(rgb, tinta, mm_px))
    if _in_quadricromia(pdf_in, page_no):
        # come la foto di prima: in quadricromia, se no la pulizia fa
        # comparire l'avviso della grafica in RGB, che nel file non c'era
        im = im.convert("CMYK")
    im.save(pulita, "PDF", resolution=72.0 / f, quality=92)
    pag = PdfReader(io.BytesIO(pulita.getvalue())).pages[0]
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
