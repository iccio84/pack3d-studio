"""
Preparare l'artwork prima di ritagliarne la texture.

Tre passaggi, e sono tre REGOLE, non tre comodita':

1. **le coperture si tolgono per nome.** Vernici, bianchi coprenti e cold seal
   sono pieni grandi quanto la grafica: nessuna euristica sul tratto li vede, e
   pdfium li rende opachi. Il nome invece lo dice senza ambiguita'.
2. **il modello segue la grafica, non il disegno tecnico.** Il DT dice come e'
   impaginato il foglio, la grafica dice come si legge il pack in mano.
3. **la grafica non si distorce mai**, che e' il limite della seconda: dove
   girare stirerebbe il pannello non si gira, e lo si dichiara.

E due regole che valgono per tutte le famiglie - flowpack, astucci, vassoi:
la grafica si prende dal suo livello, col disegno tecnico spento oggetto per
oggetto (`folding.rasterize_panels` con `clean`, vedi `strati.py`), e la
texture e' HD (`risoluzione`).

Stanno qui, e non nel server, perche' non sono questioni di HTTP: sono
dell'artwork. Finche' stavano nel server le applicava solo lui, e la riga di
comando consegnava astucci diversi da quelli del prodotto - sul Nutella Donut
una scatola rosa piena, con la vernice ancora sopra.
"""
from __future__ import annotations

import os
import tempfile

from PIL import Image

from .dieline import PT2MM


# La risoluzione della texture, (dpi, lato massimo in px), per qualita'.
#
# Di serie e' HD, per tutte le famiglie. Sul piano Free di Render la texture
# di un flowpack stava in 1700 px, e un foglio come Colazione - 460 mm di
# nastro - usciva a 3,7 px/mm, meno di 100 dpi: sgranato appena ci si
# avvicinava. Il limite era la memoria, e sugli Spaces non c'e' piu' (vedi
# DEPLOY.md). A 300 dpi quel foglio fa 5433 px di lato; il tetto a 8192 e'
# quello che le schede video da scrivania reggono tutte, e sotto il quale
# three.js non deve ridimensionare niente.
#
# "web" resta per chi vuole un GLB leggero, e sono i numeri di prima.
TEXTURE = {"web": (200, 1700), "hd": (300, 8192)}


def qualita(q):
    """"web", "hd" o "alta" - che e' HD con la maglia piu' fitta."""
    q = str(q or "").strip().lower()
    return q if q in ("web", "hd", "alta") else "hd"


def risoluzione(quality):
    """(dpi, lato massimo) della texture per quella qualita'."""
    return TEXTURE["web" if qualita(quality) == "web" else "hd"]


# Le copie a pagina unica gia' fatte: impronta del file -> (copia, pagine).
# L'interfaccia chiede /api/analyze e subito dopo /api/build sullo stesso
# file, e l'analisi in memoria si ritrova solo se la copia e' la stessa.
_UNA_PAGINA = {}
_UNA_PAGINA_MAX = 8


def pagina_unica(pdf):
    """`(pdf con la sola prima pagina, quante pagine aveva il file)`.

    Si lavora sulla PRIMA pagina e basta: un artwork su piu' pagine e' quasi
    sempre lo stesso pack ripetuto per lingua - sul Kinder Cards T2
    "64-GERMANY" e "01-ITALY", identici tranne il piede. Leggere sempre la
    pagina 0 non bastava a dirlo: le altre restavano nel file, e chi lo
    passava tutto a Ghostscript senza limiti le rendeva tutte. Tolte qui,
    all'ingresso, non le vede piu' nessuno.

    `clone_from` e non una pagina aggiunta a un file nuovo, per la stessa
    ragione di `strip_separations`: cosi' restano i livelli. Un file di una
    pagina sola torna com'e', senza copie.

    E una pagina salvata con **/Rotate** torna col giro cotto nel contenuto
    (`pagina_girata` di zero gradi): pdfplumber e la resa di pdfium /Rotate
    lo applicano, il testo di pdfium e le passate di pypdf no, e lo stesso
    foglio si misurava in due telai diversi. E' un altro modo di stare sulla
    tavola, e da qui in avanti non lo vede piu' nessuno.
    """
    p, n = _pagina_unica(pdf)
    try:
        import pypdf
        if int(pypdf.PdfReader(p).pages[0].rotation or 0) % 360:
            p = pagina_girata(p, 0)
    except Exception:
        pass
    return p, n


def _pagina_unica(pdf):
    import pypdf
    imp = _impronta(pdf)
    if imp is None:
        return pdf, 1
    fatta = _UNA_PAGINA.get(imp)
    if fatta is not None and os.path.exists(fatta[0]):
        return fatta
    try:
        n = len(pypdf.PdfReader(pdf).pages)
    except Exception:
        return pdf, 1
    if n <= 1:
        return pdf, n
    try:
        w = pypdf.PdfWriter(clone_from=pdf)
        for i in range(len(w.pages) - 1, 0, -1):
            w.remove_page(i)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        with open(tmp.name, "wb") as fh:
            w.write(fh)
    except Exception:
        return pdf, n
    while len(_UNA_PAGINA) >= _UNA_PAGINA_MAX:
        vecchia, _n = _UNA_PAGINA.pop(next(iter(_UNA_PAGINA)))
        try:
            os.unlink(vecchia)
        except OSError:
            pass
    _UNA_PAGINA[imp] = (tmp.name, n)
    return tmp.name, n


def _impronta(pdf):
    """sha256 del file, o None se non si legge."""
    import hashlib
    try:
        h = hashlib.sha256()
        with open(pdf, "rb") as fh:
            for blocco in iter(lambda: fh.read(1 << 20), b""):
                h.update(blocco)
        return h.hexdigest()
    except OSError:
        return None


def riquadro_girato(pdf, riq, gradi):
    """Il riquadro `(x_mm, y_mm, w_mm, h_mm)` - y dall'alto, come lo danno
    l'agente e l'interfaccia - portato sulla pagina di `pdf` girata di
    `gradi` in senso orario da `pagina_girata`. Chi ha guardato il foglio l'ha
    guardato com'era: se la costruzione lo gira, gira anche il riquadro."""
    gradi = int(gradi) % 360
    if not riq or not gradi:
        return riq
    import pypdf
    mb = pypdf.PdfReader(pdf).pages[0].mediabox
    W, H = float(mb.width) * PT2MM, float(mb.height) * PT2MM
    x, y, w, h = riq
    if gradi == 90:
        return (H - (y + h), x, h, w)
    if gradi == 180:
        return (W - (x + w), H - (y + h), w, h)
    return (y, W - (x + w), h, w)


# Le copie girate gia' fatte: (impronta del file, gradi) -> copia. Stessa
# ragione di _UNA_PAGINA: /api/analyze e /api/build girano lo stesso file.
_GIRATE = {}
_GIRATE_MAX = 8


def _matrice_giro(giro, x0, y0, x1, y1):
    """La `cm` che gira di `giro` gradi in senso orario, a vista, il riquadro
    (x0, y0, x1, y1) nello spazio del PDF (y in su) e lo riporta a partire da
    (0, 0). Serve anche a portare i riquadri della pagina."""
    if giro == 90:      # il lato alto diventa il lato destro
        return (0.0, -1.0, 1.0, 0.0, -y0, x1)
    if giro == 180:
        return (-1.0, 0.0, 0.0, -1.0, x1, y1)
    if giro == 270:     # il lato alto diventa il lato sinistro
        return (0.0, 1.0, -1.0, 0.0, y1, -x0)
    return (1.0, 0.0, 0.0, 1.0, -x0, -y0)


def pagina_girata(pdf, gradi):
    """Una copia di `pdf` con la prima pagina girata di `gradi` in senso
    orario, a vista, e il giro COTTO nel contenuto.

    Serve a mettere il foglio nel verso della grafica prima di risolverlo:
    vedi `astuccio_sulla_grafica`. Cotto e non dichiarato con /Rotate,
    perche' /Rotate qui non lo leggono tutti - pdfplumber e la resa di pdfium
    si', il testo di pdfium e le passate di pypdf no - e un foglio girato solo
    a parole darebbe misure, raster e testo in telai diversi. Per la stessa
    ragione un /Rotate che il file ha gia' si somma al giro e sparisce: la
    copia ha /Rotate 0 e si vede com'era, girata di `gradi`. Con zero gradi
    cuoce soltanto il /Rotate, se c'e' (vedi `pagina_unica`).

    Il contenuto si avvolge fra `q cm` e `Q` senza rileggerlo: su un foglio
    come Colazione sono centinaia di migliaia di operazioni, e qui basta
    spostarle tutte insieme. MediaBox e gli altri riquadri si portano con la
    stessa matrice; livelli, separazioni e risorse restano quelli che erano.
    Un giro nullo torna il file com'e'.
    """
    import pypdf
    from pypdf.generic import NameObject, NumberObject, RectangleObject, StreamObject
    impronta = _impronta(pdf)
    if impronta is None:
        return pdf
    chiave = (impronta, int(gradi) % 360)
    fatta = _GIRATE.get(chiave)
    if fatta is not None and os.path.exists(fatta):
        return fatta
    w = pypdf.PdfWriter(clone_from=pdf)
    page = w.pages[0]
    giro = (chiave[1] + int(page.rotation or 0)) % 360
    if giro == 0:
        return pdf
    mb = page.mediabox
    m = _matrice_giro(giro, float(mb.left), float(mb.bottom),
                      float(mb.right), float(mb.top))

    def porta(r):
        xs, ys = [], []
        for x, y in ((float(r.left), float(r.bottom)), (float(r.right), float(r.top))):
            xs.append(m[0] * x + m[2] * y + m[4])
            ys.append(m[1] * x + m[3] * y + m[5])
        return RectangleObject([min(xs), min(ys), max(xs), max(ys)])

    for nome in ("/CropBox", "/BleedBox", "/TrimBox", "/ArtBox"):
        if nome in page:
            page[NameObject(nome)] = porta(RectangleObject(page[nome]))
    page[NameObject("/MediaBox")] = porta(mb)
    page[NameObject("/Rotate")] = NumberObject(0)
    cs = page.get_contents()
    dati = cs.get_data() if cs is not None else b""
    nuovo = StreamObject()
    nuovo.set_data(b"q " + " ".join("%.6f" % v for v in m).encode()
                   + b" cm\n" + dati + b"\nQ\n")
    page.replace_contents(nuovo.flate_encode())
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    with open(tmp.name, "wb") as fh:
        w.write(fh)
    while len(_GIRATE) >= _GIRATE_MAX:
        vecchia = _GIRATE.pop(next(iter(_GIRATE)))
        try:
            os.unlink(vecchia)
        except OSError:
            pass
    _GIRATE[chiave] = tmp.name
    return tmp.name


# Quanto oltre il DT puo' stare un oggetto e restare, in punti. La grafica
# sborda di qualche millimetro oltre il taglio, e un oggetto che tocca il DT
# o il suo margine e' del DT; le quote, le copie tecniche, la legenda, il
# cartiglio e le miniature stanno piu' in la'.
MARGINE_DT = 3.0 / PT2MM

# Quanto e' grande al piu' la testa di un richiamo - il pallino in fondo alla
# linea che porta una nota dentro il DT - in punti (3 mm).
TESTA_RICHIAMO = 8.5

# Quanto e' largo al piu' un glifo, in corpi, per dire se una scritta sta
# tutta fuori dal DT senza leggere le larghezze del font. Largo apposta: una
# nota stimata per eccesso resta sul file e non fa danni, una scritta della
# grafica tolta si'.
GLIFO_MAX = 1.5


def strip_separations(src, dst, drop, riquadri=None, aree=None,
                      regione=None, conti=None, coperte=None, zone=None):
    """Toglie le lastre tecniche eliminando le operazioni di disegno.

    Colorarle di bianco non basta: un tratto tecnico sopra la grafica
    lascerebbe una riga bianca. Il filtro scende anche dentro i Form XObject,
    dove spesso stanno cold seal e bianco coprente.

    Se `riquadri` e' una lista, ci finiscono i riquadri dei BOX AREA che si
    sono tolti - le lastre `aree`, o se non vengono date quelle il cui nome lo
    dice (`techink.area`) - nel telaio di misura (punti, MediaBox, y in giu'),
    piu' un quinto numero: 1 se l'area e' fra le `coperte`, 0 se no. Sono i
    posti dove la loro didascalia sta, e chi rende la texture la spegne. Vedi
    `strati.segna_riservate` e `strati.dividi`.

    Con `regione` - il riquadro del DT, `(x0, y0, x1, y1)` nello stesso
    telaio - nella stessa passata va via anche tutto quello che sta TUTTO
    fuori dal DT, piu' `MARGINE_DT`: tracciati, scritte, immagini e form
    della pagina. Sono quote, copie tecniche, legenda, cartiglio, miniature:
    servono a leggere le quote, e le quote a quel punto sono gia' lette. Un
    oggetto che tocca il DT resta intero. `conti`, se e' un dizionario, dice
    quanti oggetti sono andati via per tipo.

    `zone` sono le GDA del foglio, `[(nucleo, zona)]` nello stesso telaio -
    vedi `techink.zone_gda`: nella stessa passata va via quello che e' della
    GDA, scritte, icone e il pannello su cui stanno (`techink.dentro_gda`),
    e `conti["gda"]` dice quanti oggetti.
    """
    import pypdf
    from pypdf.generic import ContentStream, NumberObject
    from .techink import area, dentro_gda

    # `clone_from` e non `append`: append PERDE /OCProperties, e con quello
    # perde i livelli. Un astuccio che ha insieme una vernice e la colata su un
    # livello suo usciva dallo strappo senza livelli, e la sostituzione della
    # colata non partiva - in silenzio, perche' a quel punto il livello non
    # c'era piu' davvero.
    w = pypdf.PdfWriter(clone_from=src)
    drop = {d.lower() for d in drop}
    if riquadri is None:
        aree = set()
    elif aree is None:
        aree = {d for d in drop if area(d)}
    else:
        aree = {v.lower() for v in aree} & drop
    coperte = {v.lower() for v in (coperte or ())} & aree
    if conti is None:
        conti = {}
    zone = list(zone or ())
    if zone and regione is None:
        # la GDA si cerca con lo stesso filtro del DT: un DT grande quanto
        # tutto, da cui non esce niente
        regione = (-1e12, -1e12, 1e12, 1e12)

    def gda(r):
        return bool(zone) and dentro_gda(r, zone)

    def names(res, quali=drop):
        out = set()
        cs = res.get("/ColorSpace")
        if not cs:
            return out
        for k, v in cs.get_object().items():
            try:
                o = v.get_object()
                if o[0] == "/Separation":
                    if str(o[1]).lstrip("/").replace("#20", " ").lower() in quali:
                        out.add(str(k))
                elif o[0] == "/DeviceN":
                    nm = [str(x).lstrip("/").replace("#20", " ").lower() for x in o[1]]
                    if nm and all(n in quali for n in nm):
                        out.add(str(k))
            except Exception:
                pass
        return out

    FILL, STROKE = {b"f", b"F", b"f*"}, {b"S", b"s"}
    BOTH = {b"B", b"B*", b"b", b"b*"}
    # Lo spazio colore e' STATO GRAFICO, come la matrice: lo cambiano anche
    # g, rg e k - che dipingono in grigio, RGB e quadricromia - e Q lo
    # riporta a com'era al q. Seguendo solo `cs`, dopo il riempimento di
    # un'area riservata tutto quello che veniva in quadricromia con `k` era
    # ancora "di quella lastra" e veniva tolto: sul Kinder Cards T2 106
    # riempimenti su 112, per fortuna tutti fuori dal DT - il fondo del
    # cartiglio, le pastiglie della legenda - ma sulla grafica sarebbe stato
    # lo stesso.
    DISPOSITIVO = {b"g": "/DeviceGray", b"rg": "/DeviceRGB",
                   b"k": "/DeviceCMYK"}
    DISPOSITIVO_TRATTO = {b"G": "/DeviceGray", b"RG": "/DeviceRGB",
                          b"K": "/DeviceCMYK"}
    PERCORSO = {b"m", b"l", b"c", b"v", b"y", b"re"}
    MOSTRA = {b"Tj", b"TJ", b"'", b'"'}
    IDENTITA = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    # dove i form sono disegnati: matrice al momento del Do, per i riquadri
    matrici = {}
    # quante volte ogni form e' disegnato: dentro un form si pota solo se e'
    # disegnato una volta, perche' una seconda copia starebbe altrove
    usi = {}

    def per(m, n):
        """m e poi n, come compone il PDF."""
        a1, b1, c1, d1, e1, f1 = m
        a2, b2, c2, d2, e2, f2 = n
        return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
                c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
                e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)

    def punti(ops, op, m):
        v = [float(x) for x in ops]
        if op == b"re":
            x, y, a, b = v
            v = [x, y, x + a, y, x, y + b, x + a, y + b]
        return [(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])
                for x, y in zip(v[0::2], v[1::2])]

    def angoli(x0, y0, x1, y1, m):
        return [(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])
                for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]

    def riquadro(pts, allarga=0.0):
        """Il riquadro di punti della pagina, nel telaio di misura."""
        xs = [x - mx0 for x, _y in pts]
        ys = [my1 - y for _x, y in pts]
        return (min(xs) - allarga, min(ys) - allarga,
                max(xs) + allarga, max(ys) + allarga)

    def fuori(r, m=MARGINE_DT):
        x0, y0, x1, y1 = regione
        return r[2] < x0 - m or r[0] > x1 + m or r[3] < y0 - m or r[1] > y1 + m

    def conta(chi, n=1):
        conti[chi] = conti.get(chi, 0) + n

    def conta_scritte(via):
        n = sum(1 for x in via if fuori(x[4]))
        if n:
            conta("scritte", n)
        if len(via) > n:
            conta("gda", len(via) - n)

    def lunghezza(s):
        """Quanti byte ha una stringa di testo: al piu' tanti glifi."""
        try:
            return len(s.get_original_bytes())
        except AttributeError:
            try:
                return len(bytes(s))
            except Exception:
                return len(str(s))

    def xobject(o, ctm):
        """Il riquadro di un'immagine o di un form disegnati con `ctm`."""
        sub = o.get("/Subtype")
        if sub == "/Image":
            return riquadro(angoli(0.0, 0.0, 1.0, 1.0, ctm)), "immagini"
        if sub == "/Form":
            bb = [float(v) for v in o.get("/BBox")]
            mat = tuple(float(x) for x in o.get("/Matrix", IDENTITA))
            return riquadro(angoli(min(bb[0], bb[2]), min(bb[1], bb[3]),
                                   max(bb[0], bb[2]), max(bb[1], bb[3]),
                                   per(mat, ctm))), "form"
        return None, None

    def filt(obj, res, base=None, regione=None, pagina=False, singolo=True):
        bad = names(res)
        var = names(res, aree) if base is not None and aree else set()
        cop = names(res, coperte) if var and coperte else set()
        cs = ContentStream(obj, w)
        ncs = scs = None
        # Anche il testo e lo spessore del tratto sono stato grafico: q li
        # salva e Q li rimette, come lo spazio colore e la matrice.
        ts = dict(corpo=0.0, tc=0.0, tw=0.0, th=1.0, tl=0.0, rise=0.0, modo=0)
        lw = 1.0
        pila = []
        ctm, tracciato = base, []
        segui = bool(var) or regione is not None
        inizio = None     # dove comincia in `out` il tracciato in corso
        pezzi = []        # i suoi sottotracciati: [indice in out, punti]
        tm = tlm = None   # le matrici del testo, dentro BT
        # quanto il testo puo' essere andato avanti e indietro dall'ultima
        # posizione certa: avanti lo spinge ogni glifo, indietro solo le
        # spaziature negative e i numeri positivi di TJ, che stringono
        avanti = indietro = 0.0
        scritte = []      # (indice in out, operatore, operandi, modo, riquadro)
        ritaglio = False  # una scritta del BT fa da tracciato di ritaglio
        tolti = set()     # XObject non piu' disegnati
        teste = []        # dove finiscono, dentro il DT, i richiami delle note
        out = []
        for ops, op in cs.operations:
            if op in PERCORSO or op == b"h":
                if inizio is None:
                    inizio = len(out)
            if op == b"cs":
                ncs = str(ops[0])
            elif op == b"CS":
                scs = str(ops[0])
            elif op in DISPOSITIVO:
                ncs = DISPOSITIVO[op]
            elif op in DISPOSITIVO_TRATTO:
                scs = DISPOSITIVO_TRATTO[op]
            elif op == b"q":
                pila.append((ncs, scs, ctm, dict(ts), lw))
            elif op == b"Q":
                if pila:
                    ncs, scs, ctm, ts, lw = pila.pop()
            elif op == b"w":
                try:
                    lw = abs(float(ops[0]))
                except (TypeError, ValueError, IndexError):
                    pass
            elif ctm is not None:
                if op == b"cm":
                    ctm = per(tuple(float(x) for x in ops), ctm)
                elif op in PERCORSO and segui:
                    try:
                        pt = punti(ops, op, ctm)
                    except (TypeError, ValueError):
                        pt = []
                    tracciato.extend(pt)
                    if op in (b"m", b"re") or not pezzi:
                        pezzi.append([len(out), []])
                    pezzi[-1][1].extend(pt)
                elif op == b"Do":
                    try:
                        o = res["/XObject"].get_object()[str(ops[0])].get_object()
                        mat = tuple(float(x) for x in
                                    o.get("/Matrix", IDENTITA))
                        matrici.setdefault(id(o), per(mat, ctm))
                        # dentro un contenuto disegnato piu' volte, anche il
                        # form che disegna compare piu' volte
                        usi[id(o)] = usi.get(id(o), 0) + (1 if singolo else 2)
                    except Exception:
                        o = None
                    if regione is not None and o is not None:
                        try:
                            r, chi = xobject(o, ctm)
                        except Exception:
                            r = None
                        if r is not None and (fuori(r) or gda(r)):
                            tolti.add(str(ops[0]))
                            conta(chi if fuori(r) else "gda")
                            continue
                elif op == b"INLINE IMAGE" and regione is not None:
                    r = riquadro(angoli(0.0, 0.0, 1.0, 1.0, ctm))
                    if fuori(r) or gda(r):
                        conta("immagini" if fuori(r) else "gda")
                        continue
                elif regione is not None:
                    # Il testo. Si decide alla fine del BT, perche' una
                    # scritta fa avanzare le successive: se stanno fuori
                    # tutte si tolgono, se solo alcune quelle si rendono
                    # invisibili, e le altre restano dove sono.
                    try:
                        if op == b"BT":
                            tm = tlm = IDENTITA
                            avanti = indietro = 0.0
                            scritte, ritaglio = [], False
                        elif op == b"ET":
                            via = [x for x in scritte
                                   if fuori(x[4]) or gda(x[5])]
                            if ritaglio or not via:
                                pass
                            elif len(via) == len(scritte):
                                for i, o, p, _m, _r, _o in reversed(scritte):
                                    if o == b'"':
                                        # Tw e Tc restano: valgono anche dopo
                                        out[i:i + 1] = [([p[0]], b"Tw"),
                                                        ([p[1]], b"Tc")]
                                    else:
                                        del out[i]
                                conta_scritte(via)
                            else:
                                # Un BT con scritte dentro e fuori - sul
                                # Kinder Country "Bar Code Area" sul DT e le
                                # didascalie delle copie tecniche sotto: le
                                # scritte fuori non si tolgono, si rendono
                                # invisibili (modo 3), cosi' quelle dopo non
                                # si spostano.
                                for i, _o, _p, modo, _r, _q in reversed(via):
                                    out[i:i + 1] = [([NumberObject(3)], b"Tr"),
                                                    out[i],
                                                    ([NumberObject(modo)],
                                                     b"Tr")]
                                conta_scritte(via)
                            tm = tlm = None
                            scritte = []
                        elif op == b"Tf":
                            ts["corpo"] = abs(float(ops[1]))
                        elif op == b"Tc":
                            ts["tc"] = float(ops[0])
                        elif op == b"Tw":
                            ts["tw"] = float(ops[0])
                        elif op == b"Tz":
                            ts["th"] = abs(float(ops[0])) / 100.0
                        elif op == b"TL":
                            ts["tl"] = float(ops[0])
                        elif op == b"Ts":
                            ts["rise"] = float(ops[0])
                        elif op == b"Tr":
                            ts["modo"] = int(ops[0])
                        elif tm is not None and op in (b"Td", b"TD"):
                            tx, ty = float(ops[0]), float(ops[1])
                            if op == b"TD":
                                ts["tl"] = -ty
                            tlm = tm = per((1.0, 0.0, 0.0, 1.0, tx, ty), tlm)
                            avanti = indietro = 0.0
                        elif tm is not None and op == b"Tm":
                            tlm = tm = tuple(float(x) for x in ops)
                            avanti = indietro = 0.0
                        elif tm is not None and op == b"T*":
                            tlm = tm = per((1.0, 0.0, 0.0, 1.0, 0.0,
                                            -ts["tl"]), tlm)
                            avanti = indietro = 0.0
                        elif tm is not None and op in MOSTRA:
                            if op == b'"':
                                ts["tw"], ts["tc"] = float(ops[0]), float(ops[1])
                            if op in (b"'", b'"'):
                                tlm = tm = per((1.0, 0.0, 0.0, 1.0, 0.0,
                                                -ts["tl"]), tlm)
                                avanti = indietro = 0.0
                            n, stringe, allarga = 0, 0.0, 0.0
                            for x in (ops[0] if op == b"TJ" else ops[-1:]):
                                if isinstance(x, (int, float)):
                                    # in TJ un numero positivo torna indietro
                                    if x > 0:
                                        stringe += float(x)
                                    else:
                                        allarga -= float(x)
                                else:
                                    n += lunghezza(x)
                            corpo = ts["corpo"] or 1.0
                            th = ts["th"] or 1.0
                            avanti += (n * (GLIFO_MAX * corpo
                                            + max(ts["tc"], 0.0)
                                            + max(ts["tw"], 0.0))
                                       + allarga / 1000.0 * corpo) * th
                            indietro += (n * (max(-ts["tc"], 0.0)
                                              + max(-ts["tw"], 0.0))
                                         + stringe / 1000.0 * corpo) * th
                            if ts["modo"] >= 4:
                                ritaglio = True
                            # in altezza da mezzo corpo sotto la linea di
                            # base a un corpo e mezzo sopra: le discendenti e
                            # gli accenti ci stanno con largo margine
                            r = riquadro(angoli(-indietro,
                                                ts["rise"] - 0.5 * corpo,
                                                avanti,
                                                ts["rise"] + 1.5 * corpo,
                                                per(tm, ctm)))
                            # Per la GDA si guarda dove comincia la riga,
                            # dalla linea di base a un corpo sopra: il
                            # riquadro qui sopra e' largo quanto il glifo piu'
                            # largo per ogni carattere, giusto per non toccare
                            # il DT, e le scritte della GDA ne uscivano.
                            o = riquadro(angoli(0.0, ts["rise"], 0.0,
                                                ts["rise"] + corpo,
                                                per(tm, ctm)))
                            scritte.append((len(out), op, list(ops),
                                            ts["modo"], r, o))
                    except (TypeError, ValueError, IndexError):
                        # un testo che non si capisce resta com'e'
                        ritaglio = True
            if op in FILL or op in BOTH or op in STROKE or op == b"n":
                if ncs in var and op not in STROKE and op != b"n" and tracciato:
                    xs = [p[0] for p in tracciato]
                    ys = [p[1] for p in tracciato]
                    riquadri.append((min(xs) - mx0, my1 - max(ys),
                                     max(xs) - mx0, my1 - min(ys),
                                     1.0 if ncs in cop else 0.0))
                via = richiamo = False
                coda = out[inizio:] if inizio is not None else []
                solo_percorso = bool(coda) and all(o in PERCORSO or o == b"h"
                                                   for _p, o in coda)
                della_gda = False
                if regione is not None and op != b"n" and tracciato:
                    grosso = (lw * max(abs(v) for v in ctm[:4]) / 2.0
                              if op not in FILL else 0.0)
                    via = fuori(riquadro(tracciato, grosso))
                    if not via and gda(riquadro(tracciato, grosso)):
                        via = della_gda = True
                    if not via and op in STROKE:
                        # Un tratto che esce dal DT e ci entra e' il richiamo
                        # di una nota: la penna lo spegne come DT, ma il
                        # pallino pieno sulla sua punta resterebbe grafica.
                        # Si segna la punta che sta dentro.
                        # Fuori basta un millimetro: sul B-ready un richiamo
                        # finisce sul bordo del riquadro della sua nota, 2,5
                        # mm oltre il DT, dentro il margine.
                        a, z = tracciato[0], tracciato[-1]
                        for punta, altra in ((a, z), (z, a)):
                            if (not fuori(riquadro([punta]))
                                    and fuori(riquadro([altra]), 1.0 / PT2MM)):
                                teste.append(riquadro([punta]))
                    elif not via and op in FILL and teste:
                        # Sul Nutella B-ready T2 ogni richiamo delle note
                        # finisce con un pallino di 0,7 mm, disegnato subito
                        # dopo la sua linea: sulla texture erano punti neri
                        # sparsi.
                        r = riquadro(tracciato, 1.0)
                        richiamo = (max(r[2] - r[0], r[3] - r[1])
                                    <= TESTA_RICHIAMO + 2.0
                                    and any(r[0] <= t[0] <= r[2]
                                            and r[1] <= t[1] <= r[3]
                                            for t in teste))
                        via = richiamo
                    if not via and solo_percorso and len(pezzi) > 1:
                        # Un tracciato solo puo' disegnare il DT e, nello
                        # stesso colpo, la vista tecnica accanto o una quota:
                        # sul Kinder Country la penna del DT traccia anche la
                        # vista interna. Via i sottotracciati tutti fuori: un
                        # sottotracciato non tocca nulla fuori dal suo
                        # riquadro, ne' col riempimento ne' col tratto, e
                        # dentro il DT non cambia un pixel.
                        fine = len(out)
                        for k in range(len(pezzi) - 1, -1, -1):
                            da, pt = pezzi[k]
                            if pt and fuori(riquadro(pt, grosso)):
                                del out[da:fine]
                                conta("sottotracciati")
                            elif pt and gda(riquadro(pt, grosso)):
                                del out[da:fine]
                                conta("gda")
                            fine = da
                tracciato = []
                pezzi = []
                if via:
                    conta("gda" if della_gda else
                          "richiami" if richiamo else "tracciati")
                    inizio = None
                    if solo_percorso:
                        # via anche il tracciato, non solo il colore: meno
                        # flusso da rileggere per chi viene dopo
                        del out[len(out) - len(coda):]
                    else:
                        out.append(([], b"n"))
                    continue
                inizio = None
            if op in FILL and ncs in bad:
                out.append(([], b"n")); continue
            if op in STROKE and scs in bad:
                out.append(([], b"n")); continue
            if op in BOTH:
                fd, sd = ncs in bad, scs in bad
                if fd and sd:
                    out.append(([], b"n")); continue
                if fd:
                    out.append((ops, b"S")); continue
                if sd:
                    out.append((ops, b"f")); continue
            if op == b"sh" and ncs in bad:
                continue
            out.append((ops, op))
        cs.operations = out
        if tolti and pagina:
            # Un'immagine che non si disegna piu' non deve restare fra le
            # risorse: chi le conta - l'avviso sull'RGB - la conterebbe
            # ancora. Solo sulla pagina, le cui risorse non sono di nessun
            # altro, e solo se nessun form eredita le sue.
            try:
                usati = {str(p[0]) for p, o in out if o == b"Do"}
                xo = res["/XObject"].get_object()
                orfani = [v.get_object() for v in xo.values()]
                if not any(f.get("/Subtype") == "/Form"
                           and "/Resources" not in f for f in orfani):
                    for nome in tolti - usati:
                        if nome in xo:
                            del xo[nome]
            except Exception:
                pass
        return cs

    def walk(res, seen):
        xo = res.get("/XObject")
        if not xo:
            return
        for _, v in xo.get_object().items():
            o = v.get_object()
            if o.get("/Subtype") != "/Form" or id(o) in seen:
                continue
            seen.add(id(o))
            sub = o.get("/Resources")
            if sub is None:
                continue
            # Un form che sta a cavallo del DT si pota dentro: il suo /BBox
            # puo' essere grande quanto la pagina anche se disegna una copia
            # tecnica sola, fuori dal DT, e allora dal Do non si vede. Solo
            # se il form e' disegnato UNA volta e da un posto solo: una
            # seconda copia starebbe altrove, e la si poterebbe al buio.
            dentro = (regione if regione is not None and id(o) in matrici
                      and usi.get(id(o)) == 1 and riferiti.get(id(o)) == 1
                      and not ereditano else None)
            o.set_data(filt(o, sub.get_object(), matrici.get(id(o)),
                            dentro, singolo=dentro is not None).get_data())
            walk(sub.get_object(), seen)

    def riferimenti(res, visti):
        """Da quanti dizionari di risorse e' nominato ogni form."""
        xo = res.get("/XObject")
        if not xo:
            return False
        eredita = False
        for _, v in xo.get_object().items():
            o = v.get_object()
            if o.get("/Subtype") != "/Form":
                continue
            riferiti[id(o)] = riferiti.get(id(o), 0) + 1
            sub = o.get("/Resources")
            if sub is None:
                eredita = True
            if id(o) in visti or sub is None:
                continue
            visti.add(id(o))
            eredita = riferimenti(sub.get_object(), visti) or eredita
        return eredita

    page = w.pages[0]
    mb = page.mediabox
    mx0, my1 = float(mb.left), float(mb.top)
    res = page["/Resources"]
    riferiti = {}
    ereditano = False
    if regione is not None:
        try:
            ereditano = riferimenti(res, set())
        except Exception:
            ereditano = True
    # la matrice si segue solo se serve - un'area riservata da cercare, un DT
    # fuori dal quale togliere: su un foglio come Colazione il flusso sono
    # centinaia di migliaia di operazioni
    page.replace_contents(filt(page.get_contents(), res,
                               IDENTITA if aree or regione is not None
                               else None, regione, pagina=True))
    walk(res, set())
    with open(dst, "wb") as fh:
        w.write(fh)
    return dst


# Come si rimette dritta una grafica girata. Il verso e' lo STESSO
# dell'angolo, non l'opposto: pdfium misura l'angolo nello spazio del PDF, con
# la y in su, mentre la texture ha la y in giu', quindi il senso e' gia'
# rovesciato una volta. Verificato guardando le due direzioni affiancate.
GIRO_TEXTURE = {90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}

# Quanto puo' essere lontano da quadrato un pannello perche' girarlo di 90
# gradi non lo stiri. Vedi gira_sulla_grafica.
QUADRATO = float(os.environ.get("PACK3D_QUADRATO", "0.9"))


def verso_della_grafica(pdf, panels, page_no=0):
    """Di quanto e' girata la grafica in ogni pannello. {} se non lo dice."""
    from . import tracciati
    try:
        return tracciati.verso_grafica(
            pdf, {n: (p.x0, p.y0, p.x1, p.y1) for n, p in panels.items()}, page_no)
    except Exception:
        return {}


def gira_sulla_grafica(tex, panels, verso, attesi=None, restano=None):
    """Rimette dritte le texture seguendo la grafica. (fatte, non fatte).

    La regola e' che il modello segue la GRAFICA e non il disegno tecnico: il
    DT dice come e' impaginato il foglio, la grafica dice come si legge il
    pack in mano.

    Un solo limite, e non e' un compromesso: e' l'altra regola, quella che dice
    di non distorcere mai la grafica. Il pannello sul foglio e la faccia sul
    solido hanno le stesse proporzioni - vengono dalla stessa fustella - quindi
    girare la texture di 90 gradi la mappa su una faccia con le proporzioni
    scambiate. Su un pannello quasi quadrato non si vede; su un fianco stretto
    si', ed e' anche il caso in cui girare sarebbe sbagliato: su un fianco da
    38 x 191 il testo verticale E' il progetto, non un errore di impaginato,
    mentre su un pannello da 188 x 191 vuol dire che il foglio e' girato.
    Il rapporto di forma distingue i due casi.

    Dove non si puo' girare senza stirare, non si gira e lo si dichiara: la
    regola dice di seguire la grafica, non di consegnare grafica deformata.

    "Dritta" vuol dire dritta SUL PACK, non sul foglio: il retro di una
    fasciatura verticale si stampa capovolto, perche' la piega gli fa fare
    mezzo giro, e letto a 180 gradi sul foglio e' gia' giusto. Si gira solo
    lo scarto dal verso atteso per la faccia, `attesi` (vedi `verso_atteso`).
    Prima si girava ogni verso diverso da zero, e sul Kinder Pingui T6 la
    falda del retro con "6 Pezzi - 180 g", stampata giusta, finiva a testa
    in giu'.

    In `restano`, se e' un dizionario, finiscono le facce lasciate girate e
    di quanto (gradi orari): quella del fronte la raddrizza poi il modello
    intero, vedi `folding.gira_facce`.
    """
    attesi = attesi or {}
    fatte, no = [], []
    for nome, letto in sorted(verso.items()):
        gradi = (letto - attesi.get(nome, 0)) % 360
        if not gradi or nome not in tex:
            continue
        p = panels[nome]
        lati = abs(p.x1 - p.x0), abs(p.y1 - p.y0)
        quadrato = min(lati) / max(max(lati), 1e-9) >= QUADRATO
        if gradi == 180 or quadrato:
            tex[nome] = tex[nome].transpose(GIRO_TEXTURE[gradi])
            fatte.append("%s di %d" % (nome, gradi))
        else:
            no.append("%s (%d gradi, %.0f x %.0f)"
                      % (nome, gradi, lati[0] * PT2MM, lati[1] * PT2MM))
            if restano is not None:
                restano[nome] = gradi
    return fatte, no


# Come sta sul foglio, rispetto al fronte, la grafica delle facce che lo dicono
# senza ambiguita'. Fasciatura verticale: il cielo si piega dal lato alto del
# fronte e si legge col fronte davanti, quindi sul foglio sta dritto; il retro
# e le falde del retro fanno mezzo giro attorno all'asse orizzontale, quindi
# sul foglio stanno capovolti. Fasciatura orizzontale: retro e fianchi girano
# attorno all'asse verticale, e il cielo si piega dal fronte come sopra: sul
# foglio stanno dritti. Il fondo e i fianchi non votano: il fondo si stampa in
# tutti e due i versi, e sui fianchi il testo verticale e' spesso il progetto.
VERSO_ATTESO = {
    "vwrap": {"front": 0, "top": 0, "back": 180, "back_top": 180,
              "back_bottom": 180},
    "hwrap": {"front": 0, "top": 0, "back": 0},
}


def voti_della_grafica(pdf, d, page_no=0):
    """Faccia -> di quanto la sua grafica e' girata, in gradi orari, rispetto
    a come deve stare sul foglio (`VERSO_ATTESO`) per l'astuccio risolto `d`.
    0 vuol dire che si legge come deve; le facce senza testo vivo non
    compaiono, perche' non dicono niente."""
    attesi = VERSO_ATTESO.get(d.layout, {"front": 0})
    verso = verso_della_grafica(
        pdf, {n: p for n, p in d.panels.items() if n in attesi}, page_no)
    return {n: (g - attesi[n]) % 360 for n, g in verso.items()}


def _consenso(voti):
    """Quanto una lettura dell'astuccio va d'accordo con la sua grafica: uno
    per ogni faccia che si legge come deve, meno uno per ogni faccia che no.
    Il fronte conta doppio: e' la faccia che si guarda."""
    return sum((2 if n == "front" else 1) * (1 if g == 0 else -1)
               for n, g in voti.items())


def verso_atteso(layout, fianchi_su="back"):
    """Come deve stare sul foglio la grafica di ogni faccia che lo dice, per
    girare le texture (`gira_sulla_grafica`): `VERSO_ATTESO` piu' i fianchi,
    che non votano il verso del foglio ma vanno girati giusti. Su una
    fasciatura verticale quelli agganciati al retro ne ereditano il mezzo
    giro, e sul foglio stanno capovolti come lui."""
    attesi = dict(VERSO_ATTESO.get(layout, {}))
    if layout == "vwrap" and fianchi_su == "back":
        attesi.update(left=180, right=180)
    return attesi


def _croma(immagini):
    """Quanta grafica c'e' in un gruppo di texture: la croma media, come
    `dieline._ink`. Un'aletta di colla e' bianca o tratteggiata in nero, una
    faccia stampata no."""
    import numpy as np
    somma = pixel = 0.0
    for im in immagini:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        a = np.asarray(im).astype(np.int16)
        somma += float((a.max(2) - a.min(2)).sum())
        pixel += a.shape[0] * a.shape[1]
    return somma / pixel if pixel else 0.0


def scegli_fianchi(tex, panels, d, altri):
    """Fra le due coppie di fianchi di un astuccio chiuso, quella stampata.

    Quando tutte e due le fasce alte portano i fianchi, una coppia si vede e
    l'altra sono alette che finiscono dentro, di solito bianche o tratteggiate
    per la colla. Il solutore prende quella del retro (`_chiuso`); qui la
    stampa puo' smentirlo, con lo stesso margine con cui sceglie il fronte di
    una fasciatura orizzontale: un quarto in piu' e quattro punti di croma.
    `tex`, `panels` e `d.fianchi_su` si aggiornano sul posto; torna l'avviso,
    o None se resta la coppia del solutore."""
    nostri = [tex[k] for k in altri if k in tex]
    a, b = _croma(nostri), _croma(altri.values())
    if not (b > a * 1.25 and b > a + 4.0):
        return None
    prima = d.fianchi_su
    tex.update(altri)
    panels.update(d.fianchi_alt)
    d.fianchi_alt = {}
    d.fianchi_su = "front" if prima == "back" else "back"
    return ("fianchi presi dalla fascia del %s: quelli del %s sono alette "
            "che finiscono dentro, non stampate (croma %.0f contro %.0f)"
            % ("fronte" if d.fianchi_su == "front" else "retro",
               "retro" if prima == "back" else "fronte", b, a))


# Le letture gia' decise: impronta del file -> (giro, avviso). L'analisi e la
# costruzione dello stesso file la chiedono tutte e due, e le prove costano
# un'analisi l'una.
_SULLA_GRAFICA = {}
_SULLA_GRAFICA_MAX = 16


def astuccio_sulla_grafica(pdf, page_no=0):
    """`(pdf, dieline, giro, avviso)`: l'astuccio risolto nel verso della
    grafica, `giro` i gradi orari di cui si e' girato il foglio.

    Il solutore legge il foglio come sta sulla tavola: il cielo e' la fascia
    SOPRA il fronte, il fondo quella sotto, le falde del retro nell'ordine in
    cui le incontra. Ma come un DT sta sulla tavola lo decide chi impagina: il
    Kinder Pingui T6 arriva con il foglio dritto sulla grafica (FERRERO_1742…)
    e con il DT dritto sul disegno tecnico e la grafica capovolta
    (KPI_T6_base). Stesso astuccio, e il secondo usciva rovesciato: il fronte
    lo raddrizzava la texture, ma cielo e fondo erano scambiati, il retro
    aveva la fascia rossa in alto e i fianchi erano a testa in giu'.

    La regola e' quella di sempre - il modello segue la grafica, non il
    disegno tecnico - applicata al FOGLIO invece che alla texture: se la
    grafica non si legge come deve, si prova a girare il foglio
    (`pagina_girata`) e a risolverlo di nuovo, e vince la lettura in cui piu'
    facce si leggono come devono (`voti_della_grafica`). Cosi' uno steso da'
    lo stesso astuccio comunque sia messo sulla tavola.

    Il fronte da solo non basta. Su un astuccio chiuso fronte e retro sono
    alti uguali, e quale dei due e' il fronte il solutore lo decide dalla
    fustella; girato il foglio di mezzo giro puo' scegliere l'altro, e il
    retro - stampato capovolto - si legge dritto come un fronte. Lo smentisce
    il cielo, che fra i due deve leggersi dritto col fronte: sul Nutella Donut
    girato di 90 gradi il fronte era la faccia di PREPARAZIONE, e il cielo
    capovolto l'ha detto.

    Si prova solo quando serve: se ogni faccia che ha testo vivo si legge come
    deve - o se nessuna ne ha - il foglio resta com'e' e non costa niente. E
    se sul foglio com'e' l'astuccio non si risolve, si prova girato prima di
    arrendersi: il solutore conosce meglio certi versi di altri.
    """
    from . import dieline as dl
    from . import tracciati
    chiave = _impronta(pdf)
    noto = _SULLA_GRAFICA.get(chiave) if chiave else None
    if noto is not None:
        giro, avviso = noto
        scelto = pagina_girata(pdf, giro) if giro else pdf
        return scelto, dl.analyze(scelto), giro, avviso

    def ricorda(giro, avviso):
        if chiave:
            while len(_SULLA_GRAFICA) >= _SULLA_GRAFICA_MAX:
                _SULLA_GRAFICA.pop(next(iter(_SULLA_GRAFICA)))
            _SULLA_GRAFICA[chiave] = (giro, avviso)

    letture = []                     # (giro, pdf, dieline, voti)
    ordine = []
    try:
        d0 = dl.analyze(pdf)
        errore = None
    except Exception as e:
        d0, errore = None, e
    if d0 is not None:
        if not d0.panels:
            return pdf, d0, 0, None
        v0 = voti_della_grafica(pdf, d0, page_no)
        if not v0:
            # Detto, non taciuto: e' l'unico caso in cui il pack puo' ancora
            # dipendere da come il DT sta sulla tavola.
            avviso = ("verso della grafica non letto: nessuna faccia ha testo "
                      "vivo (scritte vettorializzate), e il foglio resta com'e' "
                      "sulla tavola - il verso va controllato sul modello")
            ricorda(0, avviso)
            return pdf, d0, 0, avviso
        if all(g == 0 for g in v0.values()):
            ricorda(0, None)
            return pdf, d0, 0, None  # ogni faccia che parla si legge come deve
        letture.append((0, pdf, d0, v0))
        # prima i giri che la grafica suggerisce, quello del fronte in testa
        ordine = [(360 - g) % 360 for n, g in
                  sorted(v0.items(), key=lambda kv: kv[0] != "front") if g]
    else:
        # nessuna lettura sul foglio com'e': prima il giro del testo del DT
        try:
            g = tracciati.verso_grafica(pdf, {"dt": dl.extract(pdf).bbox},
                                        page_no).get("dt")
        except Exception:
            g = None
        if g:
            ordine = [(360 - g) % 360]
    for giro in ordine + [90, 180, 270]:
        if any(giro == l[0] for l in letture):
            continue
        girato = pagina_girata(pdf, giro)
        try:
            d = dl.analyze(girato)
        except Exception:
            d = None
        if d is None or not d.panels:
            letture.append((giro, girato, None, {}))
            continue
        v = voti_della_grafica(girato, d, page_no)
        letture.append((giro, girato, d, v))
        if v and all(g == 0 for g in v.values()):
            break                    # ogni faccia che parla si legge come deve
    risolte = [l for l in letture if l[2] is not None]
    if not risolte:
        raise errore
    # a parita' vince il foglio com'e', poi il primo giro provato
    giro, scelto, d, v = max(risolte,
                             key=lambda l: (_consenso(l[3]), l[0] == 0))
    if giro == 0:
        avviso = ("la grafica non si legge come deve in nessun verso del "
                  "foglio: l'astuccio resta letto com'e' sulla tavola, con "
                  "le texture raddrizzate faccia per faccia")
    elif d0 is None:
        avviso = ("sul foglio com'e' l'astuccio non si risolveva (%s): "
                  "girato di %d gradi si'%s"
                  % (str(errore)[:60], giro,
                     "" if _consenso(v) > 0 else
                     ", ma senza testo vivo il verso non e' confermato dalla "
                     "grafica"))
    else:
        avviso = ("foglio girato di %d gradi prima di risolvere: sulla tavola "
                  "il DT stava girato rispetto alla grafica, e cielo, fondo, "
                  "retro e fianchi si leggono nel suo verso" % giro)
    ricorda(giro, avviso)
    return scelto, d, giro, avviso


def senza_coperture(pdf, page_no=0, extra=(), regione=None, conti=None,
                    fisse=None):
    """(pdf da cui ritagliare la texture, nomi delle coperture togliute).

    Le lastre tecniche dichiarate per nome sono l'informazione piu' attendibile
    che un file possa dare, dopo i Processing Steps: `REGOLE.md` le mette al
    livello 3-4 dei cinque, sopra l'euristica su spessore e colore. Finora
    pero' le leggeva solo `tools.classify_technical`, che e' uno strumento per
    l'agente: la costruzione deterministica non le guardava, e strappava le
    separazioni solo se un caso calibrato le elencava a mano.

    Il caso che l'ha fatto vedere: su un astuccio Nutella Donut la vernice si
    chiama `Water Based Gloss Varnish` e copre tutto il pannello. pdfium la
    rende opaca, quindi la texture uscirebbe rosa piena. Nessuna euristica su
    spessore e colore la puo' prendere - non e' un tratto sottile, e' un pieno
    grande quanto la grafica - mentre il nome lo dice senza ambiguita'.

    Si strappano solo le COPERTURE - vernice, bianco coprente, cold seal - e
    non tutte le lastre tecniche: vedi techink.COPERTURE_FRASI per il perche',
    che e' misurato in secondi e in MB.

    E si toglie SOLO per la texture, mai per l'analisi: il disegno tecnico e'
    quello che fa misurare il pack, e togliendolo prima non si misura piu'
    niente.

    I **BOX AREA** si tolgono sempre, come la GDA, su ogni modello: quelli che
    si chiamano area sono gia' fra le coperture (`techink.area`), e a loro si
    aggiungono quelli che il file scrive ma non nomina - una Pantone per
    nome, e una didascalia sul disegno o in legenda: vedi
    `techink.aree_riservate`. Si cercano su OGNI file. Prima solo su quelli
    senza livelli tecnici, per risparmiare una passata di testo, e sul Kinder
    Country i due box verdi e la fascia coperta restavano stampati: i suoi
    livelli tecnici sono `Check` e `Guides and grids`, e i box non ci sono.
    Il prefiltro sulla parola AREA tiene il costo a zero sui file che non la
    scrivono.

    `extra` sono le lastre che l'agente ha riconosciuto GUARDANDO, per i file
    che l'area riservata non la scrivono da nessuna parte - vedi
    `tools.area_riservata`. Arrivano gia' confermate a occhio, e qui si
    strappano insieme alle altre: una passata sola invece di due.

    `regione` e' il riquadro del DT nel telaio di misura: se c'e', nella
    stessa passata va via tutto quello che ne sta fuori - vedi
    `strip_separations` - e il file si riscrive anche senza coperture. Le
    informazioni si leggono PRIMA, sul file intero: le coperture per nome e
    le aree riservate, la cui didascalia puo' stare nella legenda. `conti`
    riceve quanti oggetti sono andati via.

    `fisse` sono le lastre di un caso calibrato: prendono il posto di quelle
    scelte per nome, ma i box area si aggiungono lo stesso, perche' la
    regola vale per tutti i modelli.
    """
    from . import strati, techink
    try:
        import pypdf
        pagina = pypdf.PdfReader(pdf).pages[page_no]
        # Con la pulizia fuori dal DT la passata sul flusso si fa comunque,
        # e allora vanno via per nome anche le lastre che DISEGNANO il DT, non
        # solo le coperture: il limite era il costo della passata. Vedi
        # `techink.disegno` per quali, e perche' non tutte le tecniche.
        if fisse is not None:
            lastre = {techink._norm(n) for n in fisse if str(n).strip()}
            lastre |= set(techink.technical_separations(
                pagina, prova=techink.area).values())
        else:
            lastre = set(techink.technical_separations(
                pagina, prova=techink.disegno if regione is not None
                else techink.copertura).values())
    except Exception:
        return pdf, []
    # {lastra: didascalia} dei box area trovati leggendo la scritta: si
    # chiamano con un numero di Pantone, e che cosa siano lo dice solo la
    # didascalia
    etichettate = {}
    try:
        etichettate = techink.aree_riservate(pdf, page_no)
    except Exception:
        pass
    lastre |= set(etichettate)
    confermate = {techink._norm(n) for n in (extra or ()) if str(n).strip()}
    lastre |= confermate
    # I box colorati si tolgono, quelli BIANCHI restano: un'area riservata
    # dipinta in bianco non e' un segnaposto, e' il posto stampato in bianco
    # dove andranno la data o il lotto. Vedi `techink.lastre_bianche`.
    try:
        bianche = techink.lastre_bianche(pagina)
    except Exception:
        bianche = set()
    lasciate = sorted(n for n in lastre if n in bianche and (
        techink.area(n) or n in etichettate or n in confermate))
    if lasciate:
        lastre -= set(lasciate)
        for n in lasciate:
            etichettate.pop(n, None)
            confermate.discard(n)
        if conti is not None:
            conti["bianchi"] = lasciate
    # La GDA va via da tutte le grafiche, dovunque stia: vedi
    # `techink.zone_gda`.
    try:
        zone = techink.zone_gda(pdf, page_no)
    except Exception:
        zone = []
    lastre = sorted(lastre)
    if not lastre and regione is None and not zone:
        return pdf, []
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        # Tolto il box resta la sua DIDASCALIA, se non e' scritta in bianco:
        # sul Kinder Cards T2 "Best Before Area" e "POSITIONING AREA FOR EAN
        # CODE (if requested)", marrone scuro, restavano stampate sui fianchi
        # del pack; sul Nutella B-ready T2 "INGREDIENTS", "WEIGHT", "GDA",
        # "F8 LEGAL TEXT" sul retro. I riquadri dei box tolti vanno a chi
        # rende la texture, che dentro spegne le scritte: vedi `strati.dividi`.
        riquadri = []
        aree = ({n for n in lastre if techink.area(n)} | set(etichettate)
                | confermate)
        # coperte: le aree che possono avere grafica sotto, cioe' tutte
        # quelle che non sono vuote per definizione (`techink.vuota`)
        coperte = {n for n in aree if not (
            techink.vuota(n) or techink.vuota(etichettate.get(n, "")))}
        pulito = strip_separations(pdf, tmp.name, lastre, riquadri=riquadri,
                                   aree=aree, regione=regione, conti=conti,
                                   coperte=coperte, zone=zone)
        if riquadri:
            strati.segna_riservate(pulito, riquadri)
        return pulito, lastre
    except Exception:
        # meglio una texture con un residuo tecnico che nessun modello
        return pdf, []


def avvisi_gda(conti):
    """Le righe sulla GDA tolta e sui box bianchi lasciati, per chi guarda
    il modello."""
    fuori = []
    if conti.get("gda"):
        fuori.append("GDA tolta dalla grafica: %d oggetti - le icone delle "
                     "Assunzioni di Riferimento (kJ, kcal, %%) col loro "
                     "pannello, che sul modello non vanno" % conti["gda"])
    if conti.get("bianchi"):
        fuori.append("box bianchi lasciati: %s - un'area riservata bianca e' "
                     "il posto stampato in bianco per data e lotto, e resta"
                     % ", ".join(conti["bianchi"]))
    return fuori


def avviso_fuori_dt(conti):
    """La riga su quello che e' andato via fuori dal DT, o None."""
    nomi = (("tracciati", "tracciati"), ("sottotracciati", "pezzi di tracciato"),
            ("scritte", "scritte"), ("immagini", "immagini"),
            ("form", "gruppi"), ("richiami", "teste di richiamo"))
    parti = ["%d %s" % (conti[k], nome) for k, nome in nomi if conti.get(k)]
    if not parti:
        return None
    return ("fuori dal DT tolto tutto, a quote gia' lette: %s - quote, copie "
            "tecniche, legenda, cartiglio, miniature. La costruzione vede "
            "solo il DT e la sua grafica" % ", ".join(parti))


def texture_astuccio(pdf, panels, dpi, page_no=0, clean=True, lastre_extra=(),
                     nero_deciso=None, colata_riquadro=None, regione=None,
                     esito=None, dieline=None):
    """Le texture di un astuccio, pulite e girate sul verso della grafica.

    L'unico punto in cui i tre passaggi si applicano, cosi' non possono piu'
    divergere fra il server e la riga di comando.

    `regione` e' il riquadro del DT: fuori va via tutto prima di rendere, e
    il nero si decide sul file cosi' pulito - le scritte nere della legenda e
    del cartiglio non sono grafica, e contate col resto abbassavano la quota
    della `k` tradita. In `esito`, se e' un dizionario, finiscono il file
    pulito (`pdf`) e quanti oggetti sono andati via (`conti`).

    `dieline` e' l'astuccio risolto, se `panels` sono i suoi: dice il verso
    atteso di ogni faccia (`verso_atteso`) e, se tutte e due le fasce alte
    portano i fianchi, qui si sceglie la coppia STAMPATA (`scegli_fianchi`):
    `panels` e `dieline.fianchi_su` si aggiornano sul posto.

    Restituisce `(texture, avvisi)`, con gli avvisi gia' scritti come vanno
    mostrati a chi guarda il modello.
    """
    from . import folding, nero
    conti = {}
    pulito, lastre = senza_coperture(pdf, page_no, lastre_extra,
                                     regione=regione, conti=conti)
    if regione is not None and nero_deciso is None:
        nero_deciso = nero.spia(pulito, page_no, dpi / 72.0)
    if esito is not None:
        esito["pdf"], esito["conti"] = pulito, conti
    avvisi = []
    fuori = avviso_fuori_dt(conti)
    if fuori:
        avvisi.append(fuori)
    avvisi.extend(avvisi_gda(conti))
    alt = dict(dieline.fianchi_alt) if dieline is not None else {}
    da_rendere = dict(panels)
    da_rendere.update({k + "~": p for k, p in alt.items()})
    tex = folding.rasterize_panels(pulito, da_rendere, dpi=dpi, page_no=page_no,
                                   clean=clean, note=avvisi,
                                   nero_deciso=nero_deciso,
                                   colata_riquadro=colata_riquadro)
    if alt:
        scelta = scegli_fianchi(tex, panels, dieline,
                                {k: tex.pop(k + "~") for k in alt})
        if scelta:
            avvisi.append(scelta)
    attesi = (verso_atteso(dieline.layout, dieline.fianchi_su)
              if dieline is not None else {})
    restano = {}
    giri, storti = gira_sulla_grafica(
        tex, panels, verso_della_grafica(pulito, panels, page_no), attesi,
        restano)
    if esito is not None:
        # il fronte che non si e' potuto girare senza stirarlo: lo raddrizza
        # il modello intero, girato attorno alla normale del fronte
        esito["marchio"] = restano.get("front", 0)
    if lastre:
        avvisi.append("lastre tecniche e coperture tolte per nome: %s"
                      % ", ".join(lastre))
    if giri:
        avvisi.append("girato sul verso della grafica: %s" % ", ".join(giri))
    if storti:
        avvisi.append("GRAFICA GIRATA ma il pannello non e' quadrato, lasciato "
                      "com'e' per non stirarla: %s" % ", ".join(storti))
    return tex, avvisi
