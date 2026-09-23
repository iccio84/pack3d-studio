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

Il modulo serve a due mestieri, tutti e due misurati nel telaio della
MediaBox con la y contata dall'alto - lo stesso in cui rasterizza
dieline.render_page e in cui contava pdfplumber (vedi _telaio):

- `segmenti`, per il solutore: segmenti orizzontali e verticali con
  spessore e colore del tratto, nel formato di dieline._segments;
- `tecnici`, per la texture: gli elementi del disegno tecnico da togliere
  dalla grafica - tratti di fustella, retini print-free, quote.

Un avvertimento sui colori. pdfplumber li da' nello spazio originale del
PDF (CMYK, RGB, grigio); pdfium li da' sempre convertiti in RGB a 8 bit.
Qui i colori servono solo come chiavi, per dire "questo pieno e' della
stessa tinta di quel tratto": finche' penne, tavolozza e riempimenti
vengono letti tutti dalla stessa parte, il confronto resta valido.
"""
import ctypes

import pypdfium2 as pdfium
import pypdfium2.raw as raw

_MOVE = raw.FPDF_SEGMENT_MOVETO
_BEZIER = raw.FPDF_SEGMENT_BEZIERTO

# pt: sotto questa soglia il tratto e' disegno tecnico, non grafica
FILO = 0.8


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


def _colore(o, prendi):
    """Il colore come chiave: "(r, g, b)" a 8 bit, come lo da' pdfium."""
    canali = [ctypes.c_uint() for _ in range(4)]
    prendi(o, *(ctypes.byref(v) for v in canali))
    return "(%d, %d, %d)" % tuple(v.value for v in canali[:3])


def _canali(c):
    """I tre numeri di una chiave colore, o None se non e' nel formato."""
    try:
        return [int(v) for v in c.strip("()").split(",")]
    except (AttributeError, ValueError):
        return None


def tinte(colori):
    """I colori con tinta: esclude nero, grigi e neutri, che possono
    appartenere anche alla grafica e non solo al disegno tecnico."""
    fuori = set()
    for c in colori:
        v = _canali(c)
        if v and len(v) == 3 and max(v) - min(v) > 38:   # 15% di 255
            fuori.add(c)
    return fuori


_LATO = 4


def piatte(pdf_path, page_no=0):
    """I colori che nascono da una tinta piatta, cioe' da una separazione.

    Serve a non confondere il disegno tecnico con la grafica. La fustella e
    i retini print-free sono quasi sempre su una lastra a se' - /Cutter,
    /Die, una Pantone di servizio - e le stesse Pantone le usa anche il
    marchio: sul Kinder Brioss le lettere del logo sono PANTONE 361 U. Se
    una tinta piatta entrasse nella tavolozza tecnica, mascherarla
    vorrebbe dire cancellare il logo dalla texture.

    pdfium le separazioni le risolve fino all'RGB e non dice piu' da dove
    vengono. Invece di rifare i conti a mano - qui ci sono funzioni di tipo
    2 e 4 e alternative ICC e Lab - si fa dipingere a lui una campionatura:
    una paginetta con un quadretto per separazione, a inchiostro pieno,
    resa con lo stesso motore che rende l'artwork. Costa qualche
    centesimo di secondo.

    Si campiona il pieno perche' e' li' che stanno le lastre tecniche. Si
    guardano solo le separazioni a uno o due inchiostri: con tre o piu' il
    colore e' un colore vero, non una tinta di servizio.
    """
    try:
        import io

        import pypdf
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        pagina = pypdf.PdfReader(pdf_path).pages[page_no]
        sep, visti = [], set()

        def giro(res):
            if res is None:
                return
            res = res.get_object()
            if id(res) in visti:     # un form puo' rimandare a se stesso
                return
            visti.add(id(res))
            cs = res.get("/ColorSpace")
            if cs:
                for _, v in cs.get_object().items():
                    try:
                        o = v.get_object()
                        if str(o[0]) == "/Separation":
                            sep.append((1, o))
                        elif str(o[0]) == "/DeviceN" and len(o[1]) <= 2:
                            sep.append((len(o[1]), o))
                    except Exception:
                        pass
            xo = res.get("/XObject")
            if xo:
                for _, v in xo.get_object().items():
                    try:
                        o = v.get_object()
                        if o.get("/Subtype") == "/Form":
                            giro(o.get("/Resources"))
                    except Exception:
                        pass

        giro(pagina.get("/Resources"))
        if not sep:
            return set()

        w = pypdf.PdfWriter()
        spazi, disegno = DictionaryObject(), []
        for i, (n, o) in enumerate(sep):
            spazi[NameObject("/P%d" % i)] = o.clone(w)
            disegno.append("/P%d cs %s scn %d 0 %d %d re f"
                           % (i, " ".join(["1"] * n), i * _LATO, _LATO, _LATO))
        pag = w.add_blank_page(len(sep) * _LATO, _LATO)
        pag[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/ColorSpace"): spazi})
        flusso = DecodedStreamObject()
        flusso.set_data("\n".join(disegno).encode("latin1"))
        pag[NameObject("/Contents")] = w._add_object(flusso)
        buf = io.BytesIO()
        w.write(buf)

        doc = pdfium.PdfDocument(buf.getvalue())
        try:
            im = doc[0].render(scale=1).to_pil().convert("RGB")
        finally:
            doc.close()
        mezzo = _LATO // 2
        return {"(%d, %d, %d)" % im.getpixel((i * _LATO + mezzo, mezzo))
                for i in range(len(sep))}
    except Exception:
        # senza la campionatura si rischia di mascherare un po' di grafica,
        # ma non di rompere la costruzione: meglio una texture imperfetta
        # che nessun modello
        return set()


def _stile(o):
    """(spessore, colore) del tratto, nella forma che usa _technical_pens."""
    w = ctypes.c_float()
    raw.FPDFPageObj_GetStrokeWidth(o, ctypes.byref(w))
    return (round(w.value, 2), _colore(o, raw.FPDFPageObj_GetStrokeColor))


def _ingombro(sp):
    return (min(x for x, _ in sp), min(y for _, y in sp),
            max(x for x, _ in sp), max(y for _, y in sp))


def _telaio(page):
    """La matrice che porta dallo spazio del PDF a quello in cui si misura:
    origine in alto a sinistra della MediaBox, y crescente verso il basso.

    Il telaio e' quello della MediaBox e non della CropBox, perche' e'
    quello che impone dieline.render_page al rasterizzatore ed e' quello su
    cui pdfplumber conta le sue coordinate. Non e' un dettaglio da poco: il
    K Tronky ha la CropBox piu' stretta della MediaBox, e chi si fida di
    page.get_size() ribalta la pagina sull'altezza sbagliata.
    """
    x0, _y0, _x1, y1 = page.get_mediabox()
    return (1.0, 0.0, 0.0, -1.0, -x0, y1)


def _misure(page):
    x0, y0, x1, y1 = page.get_mediabox()
    return x1 - x0, y1 - y0


def _discendi(contenitore, quanti, prendi, m, visita):
    """Scende nella pagina componendo le matrici come fa il PDF.

    I form object vanno seguiti: sul K Brioss le cordonature piu' esterne
    stanno dentro un form, e chi si ferma al primo livello le perde.
    """
    for i in range(quanti(contenitore)):
        o = prendi(contenitore, i)
        t = raw.FPDFPageObj_GetType(o)
        if t == raw.FPDF_PAGEOBJ_FORM:
            _discendi(o, raw.FPDFFormObj_CountObjects, raw.FPDFFormObj_GetObject,
                      _componi(m, _matrice(o)), visita)
        else:
            visita(o, t, m)


def _pagina(page, visita):
    _discendi(page.raw, raw.FPDFPage_CountObjects, raw.FPDFPage_GetObject,
              _telaio(page), visita)


def _cammina(page, pieni, tratti, tavolozza=None):
    """Una passata sola sulla pagina, tenendo il minimo indispensabile.

    Misurato su Colazione: la pagina ha 32.757 percorsi e 408.341 punti, e
    di tutto quello sopravvivono 1.040 segmenti H/V. Materializzarli tutti
    come oggetti Python costava 93 MB per tenerne qualche centinaio di kB.

    Qui non si materializza niente che non possa servire, e il criterio non
    e' un'euristica:

    - un percorso CON TRATTO puo' dare segmenti, quindi i suoi punti
      servono. Sono il 4,9% del totale su Colazione, lo 0,7% sul K Brioss;
    - un percorso SENZA TRATTO conta solo se qualche sua figura e' un
      rettangolo pieno, perche' serve a riconoscere le cornici
      dell'artwork. E _rettangolo() accetta solo figure da 4 o 5 punti:
      appena una ne supera 5 non puo' piu' essere un rettangolo e si butta
      senza nemmeno leggerne le coordinate.

    Il disegno tecnico e la grafica non vengono toccati: il PDF si legge e
    basta. Quello che cambia e' solo cosa ci teniamo in mano.
    """
    def visita(o, t, m):
        if t != raw.FPDF_PAGEOBJ_PATH:
            return
        n = raw.FPDFPath_CountSegments(o)
        if not n:
            return
        fill, stroke = ctypes.c_int(), ctypes.c_int()
        raw.FPDFPath_GetDrawMode(o, ctypes.byref(fill), ctypes.byref(stroke))
        fill, stroke = fill.value, bool(stroke.value)
        if not fill and not stroke:
            return                         # invisibile: non puo' contare
        st = _stile(o) if stroke else None
        if tavolozza is not None and st is not None and st[0] <= FILO:
            # un tratto a filo di capello e' disegno tecnico: il suo colore
            # serve a riconoscere i retini pieni della stessa tinta
            tavolozza.add(st[1])
        if tratti is None and not fill:
            return                         # prima passata: solo i pieni
        a, b, c, d, e, f = _componi(m, _matrice(o))
        buf, troppo = [], False
        x, y = ctypes.c_float(), ctypes.c_float()

        def chiudi(sp):
            if not sp:
                return
            r = _rettangolo(sp)
            if r is not None and fill:
                pieni.append(r)
            if tratti is not None and stroke:
                tratti.append((sp, r, st))

        for k in range(n):
            seg = raw.FPDFPath_GetPathSegment(o, k)
            if not seg:
                continue
            tipo = raw.FPDFPathSegment_GetType(seg)
            if tipo == _MOVE and buf:
                chiudi(buf)
                buf, troppo = [], False
            elif tipo == _MOVE:
                troppo = False
            if troppo:
                continue
            raw.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y))
            px, py = x.value, y.value
            buf.append((a * px + c * py + e, b * px + d * py + f))
            if not stroke and len(buf) > 5:
                # senza tratto e con piu' di cinque punti non puo' essere
                # un rettangolo: si butta senza leggere il resto
                buf, troppo = [], True
        chiudi(buf)

    _pagina(page, visita)


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


def segmenti(pdf_path, page_no=0, tavolozza=None):
    """(segmenti, larghezza, altezza) della pagina.

    I segmenti hanno la forma di dieline._segments: (orient, coord, a, b,
    stile), con la y contata dall'alto.

    Se `tavolozza` e' un insieme, ci finiscono dentro i colori di ogni
    tratto a filo di capello. Servono a `tecnici` e si raccolgono in questa
    stessa passata: la pagina si legge una volta sola.
    """
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_no]
        larghezza, altezza = _misure(page)
        pieni, tratti = [], []
        _cammina(page, pieni, tratti, tavolozza)
    finally:
        doc.close()

    segs = []

    def add(x0, y0, x1, y1, st):
        if abs(x1 - x0) < 0.7 and abs(y1 - y0) > 1.0:
            segs.append(("V", (x0 + x1) / 2, min(y0, y1), max(y0, y1), st))
        elif abs(y1 - y0) < 0.7 and abs(x1 - x0) > 1.0:
            segs.append(("H", (y0 + y1) / 2, min(x0, x1), max(x0, x1), st))

    def cornice(r):
        # i riquadri dell'artwork compaiono come coppia contorno+riempimento
        # sullo stesso bbox: un tratto di fustella non e' mai anche riempito
        return any(all(abs(u - v) < 1.0 for u, v in zip(r, f)) for f in pieni)

    for sp, r, st in tratti:
        if r is not None:
            if cornice(r):
                continue
            x0, t, x1, b = r
            add(x0, t, x1, t, st)
            add(x0, b, x1, b, st)
            add(x0, t, x0, b, st)
            add(x1, t, x1, b, st)
        elif len(sp) == 2:
            (ax, ay), (bx, by) = sp
            add(ax, ay, bx, by, st)
        else:
            for (ax, ay), (bx, by) in zip(sp, sp[1:]):
                add(ax, ay, bx, by, st)
    return segs, larghezza, altezza


# --------------------------------------------------------------------------- #
# il disegno tecnico, per toglierlo dalla texture
# --------------------------------------------------------------------------- #
def _sottopercorsi(o, m):
    """I sottopercorsi dell'oggetto, nel telaio di misura e con i
    sottopercorsi chiusi richiusi sul primo punto.

    Dei tre punti con cui pdfium memorizza una Bezier si tiene solo
    l'estremo: gli altri due sono punti di controllo, per cui il tratto non
    passa. E' la stessa scelta di pdfminer, quindi i punti che escono di
    qui sono quelli che escono da pdfplumber.
    """
    a, b, c, d, e, f = m
    fuori, sp, bez = [], [], 0
    x, y = ctypes.c_float(), ctypes.c_float()
    for k in range(raw.FPDFPath_CountSegments(o)):
        seg = raw.FPDFPath_GetPathSegment(o, k)
        if not seg:
            continue
        tipo = raw.FPDFPathSegment_GetType(seg)
        if tipo == _MOVE:
            if sp:
                fuori.append(sp)
            sp, bez = [], 0
        if tipo == _BEZIER:
            bez += 1
            if bez % 3:
                continue
        else:
            bez = 0
        raw.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y))
        px, py = x.value, y.value
        sp.append((a * px + c * py + e, b * px + d * py + f))
        if len(sp) > 1 and raw.FPDFPathSegment_GetClose(seg):
            sp.append(sp[0])
    if sp:
        fuori.append(sp)
    return fuori


def _scritte(page, tinte_tec):
    """Gli ingombri dei caratteri scritti in una tinta tecnica.

    Le quote e le diciture si tolgono per ingombro, non per tratto: il
    segno sottile del carattere lascerebbe in piedi mezza cifra.

    Si passa dalla pagina di testo e non dagli oggetti perche' un oggetto
    di testo e' un pezzo di riga intero, e il suo ingombro coprirebbe anche
    gli spazi e i pezzi di grafica in mezzo. Costa un centesimo di secondo.

    Il riquadro e' quello stretto, non quello "largo": il largo arriva fino
    all'altezza del font e la fascia in piu' finisce sulla grafica sopra la
    riga. Il margine lo mette chi disegna la maschera.
    """
    fuori = []
    tp = raw.FPDFText_LoadPage(page.raw)
    if not tp:
        return fuori
    try:
        a, b, c, d, e, f = _telaio(page)
        lati = [ctypes.c_double() for _ in range(4)]   # sx, dx, giu', su
        canali = [ctypes.c_uint() for _ in range(4)]
        for i in range(raw.FPDFText_CountChars(tp)):
            raw.FPDFText_GetFillColor(tp, i, *(ctypes.byref(v) for v in canali))
            if ("(%d, %d, %d)" % tuple(v.value for v in canali[:3])) not in tinte_tec:
                continue
            if not raw.FPDFText_GetCharBox(
                    tp, i, *(ctypes.byref(v) for v in lati)):
                continue
            sx, dx, giu, su = (v.value for v in lati)
            xs = [a * px + c * py + e for px, py in ((sx, giu), (dx, su))]
            ys = [b * px + d * py + f for px, py in ((sx, giu), (dx, su))]
            fuori.append((min(xs), min(ys), max(xs), max(ys)))
    finally:
        raw.FPDFText_ClosePage(tp)
    return fuori


def verso_grafica(pdf_path, riquadri, page_no=0, minimo=3, quorum=0.6):
    """Di quanto e' ruotata la grafica in ciascun riquadro, in gradi.

    Il verso lo danno i CARATTERI STAMPATI, e non il disegno tecnico. Sono due
    cose diverse: il disegno tecnico dice come e' impaginato il foglio, la
    grafica dice come si legge il pack in mano, e il modello deve seguire la
    seconda. Su un astuccio Nutella Donut il pannello fronte ha tutto il testo
    a 90 gradi e il retro a 270: sul foglio e' cosi', sul pack no.

    `riquadri` e' un dizionario nome -> (x0, y0, x1, y1) nel telaio di misura.
    Torna nome -> gradi, con solo 0, 90, 180 o 270; i riquadri senza testo
    abbastanza non compaiono, perche' non dicono niente e indovinare sarebbe
    peggio che lasciare com'e'.

    Il peso e' l'AREA del carattere: una riga di marchio a corpo 40 conta piu'
    di venti righe di legale a corpo 5, che e' come la legge un occhio.
    """
    import math
    fuori = {}
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_no]
        tp = raw.FPDFText_LoadPage(page.raw)
        if not tp:
            return fuori
        try:
            a, b, c, d, e, f = _telaio(page)
            lati = [ctypes.c_double() for _ in range(4)]
            peso = {k: {} for k in riquadri}
            quanti = {k: 0 for k in riquadri}
            for i in range(raw.FPDFText_CountChars(tp)):
                ang = raw.FPDFText_GetCharAngle(tp, i)
                if ang < 0:
                    continue
                if not raw.FPDFText_GetCharBox(
                        tp, i, *(ctypes.byref(v) for v in lati)):
                    continue
                sx, dx, giu, su = (v.value for v in lati)
                x = a * (sx + dx) / 2.0 + c * (giu + su) / 2.0 + e
                y = b * (sx + dx) / 2.0 + d * (giu + su) / 2.0 + f
                area = max(1e-9, abs(dx - sx) * abs(su - giu))
                gradi = int(round(math.degrees(ang) / 90.0)) * 90 % 360
                for nome, (x0, y0, x1, y1) in riquadri.items():
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        peso[nome][gradi] = peso[nome].get(gradi, 0.0) + area
                        quanti[nome] += 1
                        break
            for nome, conto in peso.items():
                tot = sum(conto.values())
                if quanti[nome] < minimo or tot <= 0:
                    continue
                g, w = max(conto.items(), key=lambda kv: kv[1])
                if w / tot >= quorum:
                    fuori[nome] = g
        finally:
            raw.FPDFText_ClosePage(tp)
    finally:
        doc.close()
    return fuori


def tecnici(pdf_path, page_no=0, penne=(), tinte_tec=(), filo=FILO,
            minuto=25.0):
    """Gli elementi del disegno tecnico della pagina, gia' scremati.

    Torna (tratti, pieni, scritte):

      tratti   [(punti, spessore)]   fustella, quote, retini: da ripassare
      pieni    [(riquadro, punti)]   aree piene in una tinta tecnica; i
                                     punti solo per le figure non
                                     rettangolari piu' grandi di `minuto`
      scritte  [riquadro]            quote e diciture in una tinta tecnica

    Il filtro sta qui dentro e non nel chiamante, ed e' una questione di
    memoria: un impaginato ha decine di migliaia di percorsi e al disegno
    tecnico ne servono qualche migliaio. Quelli che non passano non
    diventano mai un oggetto Python - non se ne leggono nemmeno i punti.
    """
    penne, tinte_tec = set(penne), set(tinte_tec)
    tratti, pieni, scritte = [], [], []
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_no]

        scritte.extend(_scritte(page, tinte_tec))

        def visita(o, t, m):
            if t != raw.FPDF_PAGEOBJ_PATH or not raw.FPDFPath_CountSegments(o):
                return
            fill, stroke = ctypes.c_int(), ctypes.c_int()
            raw.FPDFPath_GetDrawMode(o, ctypes.byref(fill), ctypes.byref(stroke))
            fill, stroke = bool(fill.value), bool(stroke.value)
            lw, col = _stile(o) if stroke else (0.0, None)
            riga = stroke and (lw <= filo or (lw, col) in penne)
            area = fill and _colore(o, raw.FPDFPageObj_GetFillColor) in tinte_tec
            if not riga and not area:
                return
            for sp in _sottopercorsi(o, _componi(m, _matrice(o))):
                r = _rettangolo(sp)
                if riga:
                    if r is not None:
                        x0, y0, x1, y1 = r
                        sp = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
                    if len(sp) > 1:
                        tratti.append((sp, lw))
                elif r is not None:
                    pieni.append((r, None))
                else:
                    b = _ingombro(sp)
                    if max(b[2] - b[0], b[3] - b[1]) < minuto:
                        # i simboli tecnici (frecce di orientamento) sono
                        # piccoli e spesso fatti di piu' sottopercorsi: si
                        # coprono per ingombro
                        pieni.append((b, None))
                    elif len(sp) > 2:
                        pieni.append((b, sp))

        _pagina(page, visita)
    finally:
        doc.close()
    return tratti, pieni, scritte
