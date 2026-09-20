"""Tracciati di una pagina PDF letti con pypdfium2.

Perche' non pdfplumber: pdfplumber costruisce un oggetto Python per ogni
elemento della pagina, e su un impaginato grande sono decine di migliaia.
Misurato sul solo parsing:

    K Brioss STD  (21.038 elementi)   pdfplumber 6,6 s  251 MB
                                      pypdfium2  0,9 s   41 MB
    Colazione     (34.381 elementi)   pdfplumber 9,5 s  278 MB
                                      pypdfium2  0,7 s   43 MB

pypdfium2 e' gia' una dipendenza - ci rasterizziamo le pagine - e la sua
licenza e' permissiva, a differenza di PyMuPDF che e' AGPL.

Quello che serve al solutore e' poco: segmenti orizzontali e verticali con
spessore e colore del tratto. Questo modulo da' quelli, nello stesso
formato e nello stesso verso (y dall'alto) di dieline._segments.
"""
import ctypes

import pypdfium2 as pdfium
import pypdfium2.raw as raw

_MOVE = raw.FPDF_SEGMENT_MOVETO


def _matrice(o):
    m = raw.FS_MATRIX()
    if not raw.FPDFPageObj_GetMatrix(o, ctypes.byref(m)):
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    return (m.a, m.b, m.c, m.d, m.e, m.f)


def _componi(p, q):
    """q applicata dentro p, come fa il PDF con le matrici annidate."""
    a1, b1, c1, d1, e1, f1 = p
    a2, b2, c2, d2, e2, f2 = q
    return (a2 * a1 + b2 * c1, a2 * b1 + b2 * d1,
            c2 * a1 + d2 * c1, c2 * b1 + d2 * d1,
            e2 * a1 + f2 * c1 + e1, e2 * b1 + f2 * d1 + f1)


def _stile(o):
    """(spessore, colore) del tratto, nella forma che usa _technical_pens."""
    w = ctypes.c_float()
    raw.FPDFPageObj_GetStrokeWidth(o, ctypes.byref(w))
    canali = [ctypes.c_uint() for _ in range(4)]
    raw.FPDFPageObj_GetStrokeColor(o, *(ctypes.byref(v) for v in canali))
    return (round(w.value, 2),
            "(%d, %d, %d)" % tuple(v.value for v in canali[:3]))


def _percorsi(page):
    """Tutti i percorsi della pagina, con dentro anche quelli dei form.

    I form vanno attraversati: sul K Brioss ne contiene diciassette, e le
    cordonature piu' esterne - quelle che danno il nastro - stanno li'
    dentro. Un estrattore che si ferma al primo livello le perde e il pack
    esce con il nastro sbagliato.
    """
    fuori = []

    def giro(contenitore, quanti, prendi, m):
        for i in range(quanti(contenitore)):
            o = prendi(contenitore, i)
            t = raw.FPDFPageObj_GetType(o)
            if t == raw.FPDF_PAGEOBJ_FORM:
                giro(o, raw.FPDFFormObj_CountObjects, raw.FPDFFormObj_GetObject,
                     _componi(m, _matrice(o)))
            elif t == raw.FPDF_PAGEOBJ_PATH:
                n = raw.FPDFPath_CountSegments(o)
                if not n:
                    continue
                mm = _componi(m, _matrice(o))
                a, b, c, d, e, f = mm
                pts, tipi = [], []
                for k in range(n):
                    s = raw.FPDFPath_GetPathSegment(o, k)
                    if not s:
                        continue
                    x, y = ctypes.c_float(), ctypes.c_float()
                    raw.FPDFPathSegment_GetPoint(s, ctypes.byref(x), ctypes.byref(y))
                    pts.append((a * x.value + c * y.value + e,
                                b * x.value + d * y.value + f))
                    tipi.append(raw.FPDFPathSegment_GetType(s))
                fill, stroke = ctypes.c_int(), ctypes.c_int()
                raw.FPDFPath_GetDrawMode(o, ctypes.byref(fill), ctypes.byref(stroke))
                fuori.append((pts, tipi, fill.value, bool(stroke.value), _stile(o)))

    giro(page.raw, raw.FPDFPage_CountObjects, raw.FPDFPage_GetObject,
         (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    return fuori


def _sottopercorsi(pts, tipi):
    """Spezza sui MOVETO: un percorso PDF contiene piu' figure staccate."""
    fuori, cur = [], []
    for punto, t in zip(pts, tipi):
        if t == _MOVE and cur:
            fuori.append(cur)
            cur = []
        cur.append(punto)
    if cur:
        fuori.append(cur)
    return fuori


def _rettangolo(sp):
    """Il bbox se il sottopercorso e' un rettangolo con i lati agli assi."""
    chiuso = (len(sp) == 5 and abs(sp[0][0] - sp[-1][0]) < 0.01
              and abs(sp[0][1] - sp[-1][1]) < 0.01)
    q = sp[:-1] if chiuso else sp
    if len(q) != 4:
        return None
    xs = sorted({round(x, 2) for x, _ in q})
    ys = sorted({round(y, 2) for _, y in q})
    if len(xs) != 2 or len(ys) != 2:
        return None
    return (xs[0], ys[0], xs[1], ys[1])


def segmenti(pdf_path, page_no=0):
    """(segmenti, larghezza, altezza) della pagina.

    I segmenti hanno la forma di dieline._segments: (orient, coord, a, b,
    stile), con la y contata dall'alto.
    """
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_no]
        larghezza, altezza = page.get_size()
        pc = _percorsi(page)
    finally:
        doc.close()

    segs = []

    def add(x0, y0, x1, y1, st):
        if abs(x1 - x0) < 0.7 and abs(y1 - y0) > 1.0:
            segs.append(("V", (x0 + x1) / 2, min(y0, y1), max(y0, y1), st))
        elif abs(y1 - y0) < 0.7 and abs(x1 - x0) > 1.0:
            segs.append(("H", (y0 + y1) / 2, min(x0, x1), max(x0, x1), st))

    # i riquadri dell'artwork compaiono come coppia contorno+riempimento sullo
    # stesso bbox: un tratto di fustella non e' mai anche riempito
    pieni = []
    for pts, tipi, fill, _stroke, _st in pc:
        if not fill:
            continue
        for sp in _sottopercorsi(pts, tipi):
            r = _rettangolo(sp)
            if r:
                pieni.append(r)

    def cornice(r):
        return any(all(abs(u - v) < 1.0 for u, v in zip(r, f)) for f in pieni)

    for pts, tipi, _fill, stroke, st in pc:
        for sp in _sottopercorsi(pts, tipi):
            r = _rettangolo(sp)
            if r is not None:
                if not stroke or cornice(r):
                    continue
                x0, x1 = r[0], r[2]
                t, b = altezza - r[3], altezza - r[1]
                add(x0, t, x1, t, st)
                add(x0, b, x1, b, st)
                add(x0, t, x0, b, st)
                add(x1, t, x1, b, st)
            elif len(sp) == 2:
                (ax, ay), (bx, by) = sp
                add(ax, altezza - ay, bx, altezza - by, st)
            elif stroke:
                alto = [(x, altezza - y) for x, y in sp]
                for (ax, ay), (bx, by) in zip(alto, alto[1:]):
                    add(ax, ay, bx, by, st)
    return segs, larghezza, altezza
