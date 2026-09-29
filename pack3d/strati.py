"""
I livelli dell'artwork: il modo giusto di separare il disegno tecnico.

Il disegno tecnico non si indovina dal colore. E' la lezione piu' cara di
questo progetto, e adesso e' misurata: la maschera sceglieva pieni e scritte
in base alla tinta - "cromatica e non di una tinta piatta, quindi tecnica" - e
su tutto il parco quella regola non ha mai tolto un solo pixel di disegno
tecnico che i tratti non togliessero gia'. Su sei file su nove non cambia
niente; sugli altri tre cancella **grafica**:

    K Brioss STD   il logo `Brioss`, la tabella nutrizionale, "CON LATTE",
                   il testo legale - il 4,4% del foglio
    K Pingui T6    il bollino "x6" e l'icona del pack
    K Brioss       lo 0,75% del foglio, tutto grafica

Il motivo non e' una soglia sbagliata: e' che **una lastra tecnica usa colori
che usa anche la grafica**. Il ciano di processo che traccia una quota e' lo
stesso ciano del logo Brioss; la Pantone di servizio e' la stessa del marchio;
il registro `All` e' nero come il testo. Nessuna soglia separa due cose che
hanno lo stesso colore.

Quello che invece lo dice senza ambiguita' e' il **livello**. Su K Brioss STD
il file ha otto OCG, e due si chiamano `Cutter` e `Legend`: spegnendo quelli si
toglie l'1,61% - la fustella e il cartiglio, esattamente - e il logo resta
intero. E' la stessa scala di certezza che REGOLE.md descrive da sempre, solo
usata anche per la maschera e non piu' solo per la diagnosi.

Restano i **tratti**: un filo di capello e' tecnico per geometria, non per
colore, e quello continua a valere anche senza livelli.

Quando il file i livelli non li ha, li fa la costruzione: vedi *i due livelli*
in fondo al modulo. Un oggetto spento non si rende, e sotto resta la grafica
che c'era davvero - niente maschera, niente pixel inventati.
"""
from __future__ import annotations

import ctypes
import os
import re
import tempfile


def livelli(pdf):
    """{nome minuscolo: riferimento} degli OCG della pagina."""
    import pypdf
    try:
        r = pypdf.PdfReader(pdf)
        oc = r.trailer["/Root"].get("/OCProperties")
        if not oc:
            return {}
        return {str(g.get_object().get("/Name", "")).strip().lower(): g
                for g in oc.get("/OCGs", [])}
    except Exception:
        return {}


def spegni(src, dst, nomi):
    """Scrive `dst` con quei livelli spenti. Restituisce i nomi spenti.

    E' una modifica di DIZIONARIO - l'OCG finisce in `/OCProperties/D/OFF` -
    e non costa la passata di pypdf sul flusso di contenuto, che su Colazione
    vale 7 secondi e 100 MB.

    `PdfWriter().append()` PERDE `/OCProperties`, e senza quello non c'e'
    niente da spegnere: si clona.
    """
    import pypdf
    from pypdf.generic import ArrayObject, NameObject
    nomi = {n.strip().lower() for n in nomi}
    w = pypdf.PdfWriter(clone_from=src)
    oc = w._root_object.get("/OCProperties")
    if oc is None:
        return []
    via = [g for g in oc.get("/OCGs", [])
           if str(g.get_object().get("/Name", "")).strip().lower() in nomi]
    if not via:
        return []
    d = oc.get("/D")
    d = d.get_object() if hasattr(d, "get_object") else d
    off = ArrayObject(list(d.get("/OFF") or []))
    off.extend(via)
    d[NameObject("/OFF")] = off
    with open(dst, "wb") as fh:
        w.write(fh)
    return [str(g.get_object().get("/Name")) for g in via]


def tecnici(pdf, page_no=0):
    """I nomi dei livelli che NON vanno stampati sul modello.

    Tre criteri, tutti per nome e nessuno per colore: i Processing Steps
    ISO 19593-1, i nomi di livello dichiaratamente tecnici
    (`techink.OCG_TECH`) e i nomi che collocano una separazione fra le lastre
    tecniche (`techink.tecnica`) - `Cutter` passa di li'.
    """
    from . import techink
    nomi = set(livelli(pdf))
    if not nomi:
        return set()
    fuori = set()
    try:
        import pypdf
        r = pypdf.PdfReader(pdf)
        for v in techink.processing_steps(r, r.pages[page_no]).values():
            n = (v.get("name") or "").strip().lower()
            if n in nomi:
                fuori.add(n)
    except Exception:
        pass
    for n in nomi:
        if n in techink.OCG_TECH or techink.tecnica(n):
            fuori.add(n)
    return fuori


# I riquadri dei box area che la costruzione ha tolto, per file: chi rende la
# texture ci spegne dentro le didascalie. Li scrive
# `artwork.senza_coperture`, che e' l'unico che li conosce - li misura mentre
# toglie la lastra - e li legge `rendi`, che la lastra non la vede piu'.
# Chiave come per le penne: un file temporaneo puo' riprendere il nome di uno
# cancellato.
_RISERVATE = {}


def _chiave(pdf):
    try:
        st = os.stat(pdf)
    except OSError:
        return None
    return (pdf, st.st_mtime_ns, st.st_size)


def segna_riservate(pdf, riquadri):
    """Registra i riquadri riservati di `pdf`: vedi `dividi`."""
    k = _chiave(pdf)
    if k is None:
        return
    while len(_RISERVATE) >= 8:
        _RISERVATE.pop(next(iter(_RISERVATE)))
    _RISERVATE[k] = [tuple(float(v) for v in r) for r in riquadri]


def riservate(pdf):
    """I riquadri riservati registrati per `pdf`, o lista vuota."""
    return _RISERVATE.get(_chiave(pdf), [])


def senza_tecnici(pdf, page_no=0):
    """`(pdf da cui ritagliare la texture, nomi dei livelli spenti)`.

    Se il file i livelli non ce li ha, o nessuno e' tecnico, torna il file
    com'e': chi non ha livelli non paga niente.
    """
    nomi = tecnici(pdf, page_no)
    if not nomi:
        return pdf, []
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    try:
        spenti = spegni(pdf, tmp.name, nomi)
        if not spenti:
            os.unlink(tmp.name)
            return pdf, []
        # la copia coi livelli spenti ha le stesse aree riservate
        if riservate(pdf):
            segna_riservate(tmp.name, riservate(pdf))
        return tmp.name, spenti
    except Exception:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        return pdf, []


# --------------------------------------------------------------------------- #
# i due livelli: il disegno tecnico e la grafica, oggetto per oggetto
# --------------------------------------------------------------------------- #
#
# Spegnere un OCG e' la strada esatta, ma la puo' prendere solo il file che
# l'ha preparata: Colazione di livelli non ne ha nessuno. Li' il disegno tecnico
# si toglieva DOPO la resa, con una maschera sui tratti sottili e il pixel
# valido piu' vicino a riempire - ed e' quella la texture "ritagliata in piu'
# punti". Dove una cordonatura attraversa la grafica il riempimento mangia una
# fascia larga un millimetro e la rifa' coi bordi: sul cedolino blu di Colazione
# l'angolo usciva a gradini, e degli incroci del retino delle saldature
# restavano i puntini sul bianco.
#
# pdfium invece gli oggetti li conosce uno per uno, e li sa spegnere
# (`FPDFPageObj_SetIsActive`): un oggetto spento non si rende, e sotto resta
# quello che il file ci ha messo. Sono i due livelli che il file avrebbe dovuto
# avere, fatti dalla costruzione:
#
#   DT       i livelli tecnici del file, piu' i tratti a filo di capello e le
#            penne della fustella - la stessa scelta della maschera di prima,
#            ma sugli oggetti invece che sui pixel;
#   GRAFICA  tutto il resto: e' da qui, e solo da qui, che viene la texture.
#
# Un percorso pieno con un contorno tecnico e' tutte e due le cose: il pieno e'
# grafica, il contorno no. Si spegne solo il contorno.

DT = "dt"
GRAFICA = "grafica"


def _utf16(chiama, *args):
    """Una stringa UTF-16 da una funzione pdfium del tipo (..., buf, n, &n)."""
    n = ctypes.c_ulong()
    if not chiama(*args, None, 0, ctypes.byref(n)) or n.value < 2:
        return ""
    buf = (ctypes.c_ushort * (n.value // 2 + 1))()
    chiama(*args, buf, n.value, ctypes.byref(n))
    return bytes(buf)[:n.value].decode("utf-16-le", "ignore").rstrip("\x00")


def _livelli_oggetto(o):
    """I nomi, minuscoli, dei livelli che marcano l'oggetto.

    pdfium li espone come marca `OC` con il dizionario dell'OCG fra i
    parametri: `Name` e' il nome del livello. Dentro un form le marche le ha il
    form, e i figli le ereditano: se ne occupa chi scende.
    """
    import pypdfium2.raw as raw
    fuori = set()
    for k in range(raw.FPDFPageObj_CountMarks(o)):
        m = raw.FPDFPageObj_GetMark(o, k)
        if _utf16(raw.FPDFPageObjMark_GetName, m) != "OC":
            continue
        nome = _utf16(raw.FPDFPageObjMark_GetParamStringValue, m, b"Name")
        if nome:
            fuori.add(nome.strip().lower())
    return fuori


# (file, pagina, mtime, taglia) -> penne. Un file temporaneo puo' riprendere il
# nome di uno cancellato: la chiave sul solo nome darebbe le penne di un altro.
_PENNE = {}


def penne(pdf, page_no=0):
    """Le penne del disegno tecnico, come le sceglie `_technical_pens`."""
    from .dieline import _technical_pens
    from .tracciati import segmenti
    st = os.stat(pdf)
    chiave = (pdf, page_no, st.st_mtime_ns, st.st_size)
    if chiave not in _PENNE:
        segs, larghezza, altezza = segmenti(pdf, page_no)
        _PENNE.clear()
        _PENNE[chiave] = frozenset(_technical_pens(segs, larghezza, altezza))
    return _PENNE[chiave]


# Un VELO tecnico: un rettangolo pieno e semitrasparente che copre esattamente
# una cella del DT, con i quattro lati sulle sue linee. Sul Kinder Pingui T1
# Cheesecake le due gole da 10 mm e le due strisce coperte sono velate cosi',
# bianco al 50% dentro quattro form, e non stanno su un livello: sul modello
# le pinne e i fianchi uscivano sbiaditi. Sul T1 Mandarino, stesso DT, i veli
# non ci sono. Una grafica semitrasparente - il fondino del bollino "LIMITED
# EDITION" sullo stesso file - non ha i lati sulle linee del DT, e resta.
VELO_TOLLERANZA = 1.0   # punti fra un lato del velo e la linea del DT
VELO_LATO_MIN = 5.0     # punti: sotto e' un segno, non una zona
_LINEE = {}


def linee_dt(pdf, page_no=0, pen=None):
    """`(xs, ys)`: dove stanno le linee verticali e orizzontali del DT, nel
    telaio di misura. Sono i tratti delle penne del DT, piu' lunghi di un
    centimetro: bastano a dire se un rettangolo ne ricalca una cella."""
    from .tracciati import FILO, segmenti
    st = os.stat(pdf)
    chiave = (pdf, page_no, st.st_mtime_ns, st.st_size)
    if chiave not in _LINEE:
        pen = penne(pdf, page_no) if pen is None else pen
        segs, _w, _h = segmenti(pdf, page_no)
        xs, ys = set(), set()
        for k, c, a, b, s in segs:
            if b - a > 28.0 and (s in pen or s[0] <= FILO):
                (xs if k == "V" else ys).add(round(c, 1))
        _LINEE.clear()
        _LINEE[chiave] = (sorted(xs), sorted(ys))
    return _LINEE[chiave]


def _velo(o, m, t, linee):
    """Se l'oggetto e' un velo tecnico: vedi VELO_TOLLERANZA."""
    import bisect
    import pypdfium2.raw as raw
    v = [ctypes.c_uint() for _ in range(4)]
    raw.FPDFPageObj_GetFillColor(o, *(ctypes.byref(c) for c in v))
    if v[3].value >= 255:
        return False
    if t == raw.FPDF_PAGEOBJ_FORM:
        if raw.FPDFFormObj_CountObjects(o) != 1:
            return False
    else:
        pieno, tratto = ctypes.c_int(), ctypes.c_int()
        raw.FPDFPath_GetDrawMode(o, ctypes.byref(pieno), ctypes.byref(tratto))
        if not pieno.value:
            return False
    r = _riquadro(o, m)
    if r is None:
        return False
    x0, y0, x1, y1 = r
    if x1 - x0 < VELO_LATO_MIN or y1 - y0 < VELO_LATO_MIN:
        return False

    def sulla_linea(val, linee_asse):
        i = bisect.bisect_left(linee_asse, val - VELO_TOLLERANZA)
        return i < len(linee_asse) and linee_asse[i] <= val + VELO_TOLLERANZA

    xs, ys = linee
    return (sulla_linea(x0, xs) and sulla_linea(x1, xs)
            and sulla_linea(y0, ys) and sulla_linea(y1, ys))


def _fuori(o, m, riquadro):
    """Se l'oggetto sta tutto fuori da `riquadro`, nel telaio di misura."""
    import pypdfium2.raw as raw
    lati = [ctypes.c_float() for _ in range(4)]
    if not raw.FPDFPageObj_GetBounds(o, *(ctypes.byref(v) for v in lati)):
        return False
    sx, giu, dx, su = (v.value for v in lati)
    a, b, c, d, e, f = m
    xs = [a * x + c * y + e for x, y in ((sx, giu), (dx, su))]
    ys = [b * x + d * y + f for x, y in ((sx, giu), (dx, su))]
    x0, y0, x1, y1 = riquadro
    return max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1


def _riquadro(o, m):
    """Il riquadro dell'oggetto nel telaio di misura, o None."""
    import pypdfium2.raw as raw
    lati = [ctypes.c_float() for _ in range(4)]
    if not raw.FPDFPageObj_GetBounds(o, *(ctypes.byref(v) for v in lati)):
        return None
    sx, giu, dx, su = (v.value for v in lati)
    a, b, c, d, e, f = m
    xs = [a * x + c * y + e for x, y in ((sx, giu), (dx, su))]
    ys = [b * x + d * y + f for x, y in ((sx, giu), (dx, su))]
    return min(xs), min(ys), max(xs), max(ys)


def _testo(o, tp):
    """Il testo di un oggetto testo, o stringa vuota."""
    import pypdfium2.raw as raw
    n = raw.FPDFTextObj_GetText(o, tp, None, 0)
    if n <= 2:
        return ""
    buf = (ctypes.c_ushort * (n // 2 + 1))()
    raw.FPDFTextObj_GetText(o, tp, buf, n)
    return bytes(buf)[:n].decode("utf-16-le", "ignore").rstrip("\x00")


def _colore(o):
    import pypdfium2.raw as raw
    v = [ctypes.c_uint() for _ in range(4)]
    raw.FPDFPageObj_GetFillColor(o, *(ctypes.byref(c) for c in v))
    return tuple(c.value for c in v[:3])


# Quanto puo' sbordare un'etichetta dal suo riquadro, in punti, e quanto del
# riquadro puo' coprire: il fondo bianco che sta sotto un'area riservata e'
# grande quanto lei, ed e' grafica - il posto bianco dove si stampera' il
# codice - non la sua didascalia. Per una scritta basta che non lo riempia;
# un tracciato deve essere un SEGNO - una lettera in curve, il punto di un
# richiamo - e non un fondo: sul K Brioss (FERRERO_1765...) le didascalie
# sono bianche, e dentro la Best Before Area c'e' il riquadro bianco dove si
# stampera' la data.
SBORDO_ETICHETTA = 1.0
QUOTA_ETICHETTA = 0.8
QUOTA_SEGNO = 0.25


def dividi(page, penne_dt, nomi_tecnici, stampato=None, riservate=(),
           linee=None):
    """`(dt, contorni, grafica, dai_livelli, etichette, veli)`: gli oggetti
    nei due livelli.

    `contorni` sono coppie `(oggetto, modo di riempimento)`: percorsi pieni
    con un contorno tecnico, di cui e' tecnico solo il contorno.
    `dai_livelli` e' quanti degli oggetti in `dt` ci stanno perche' il file li
    mette su un livello tecnico: gli altri sono la stima sui tratti. `page` e'
    una pagina pypdfium2 aperta; gli oggetti valgono finche' resta aperta lei.

    `stampato` e' il riquadro dell'artwork stampato, in punti e y in giu': i
    TESTI che ne stanno fuori sono note - quote delle miniature, legenda,
    cartiglio - e vanno nel livello DT. Dentro no: li' il testo e' grafica
    anche quando e' dello stesso colore di una quota, e il colore non si
    guarda mai.

    Con un'eccezione, per i BOX AREA che la costruzione ha tolto
    (`riservate`, i loro riquadri: vedi `artwork.strip_separations`). Tolto
    il box resta la sua DIDASCALIA - sul Kinder Cards T2 "Best Before Area" e
    "POSITIONING AREA FOR EAN CODE (if requested)" in marrone scuro, sul
    Nutella B-ready T2 "INGREDIENTS", "WEIGHT", "GDA", "F8 LEGAL TEXT" - e la
    didascalia e' il nome del posto, non si stampa mai. Dentro un riquadro
    tolto:

    - un testo che dice il nome di un'area riservata (`techink.NOME_RISERVATA`)
      e' una didascalia: lo dice quello che c'e' scritto, non il colore;
    - ma non tutte dicono "area": sul B-ready "INGREDIENTS" e "WEIGHT" sono
      il nome della casella e basta, e quella del codice a barre del Kinder
      Cards e' in curve, 38 tracciati. Una scritta, o un SEGNO piccolo (vedi
      `QUOTA_SEGNO`), tutto dentro il riquadro e del COLORE di una didascalia
      scritta e' una didascalia anche lui. Un codice a barre vero - nero, e la
      didascalia e' di un'altra tinta - resta dov'e'; e senza nessuna
      didascalia scritta non si impara nessun colore e non si toglie niente.

    Nell'area COPERTA no: sotto la pinna la grafica continua - sul Kinder
    Cards T2 la cialda e la banda rossa - e li' si spegne solo il testo che
    dice il nome dell'area. Coperta, per prudenza, e' ogni area che non e'
    vuota per definizione (`techink.vuota`): una che non si conosce puo'
    avere grafica sotto. Il colore si impara solo dai box vuoti.

    Fuori dai riquadri tolti non si tocca niente: la didascalia di un box
    che nessuno ha riconosciuto resta con lui, e un riquadro senza nome
    sembrerebbe grafica. `etichette` e' quante didascalie sono finite nel DT.

    Con `linee` - le linee del DT, vedi `linee_dt` - vanno nel DT anche i
    VELI: rettangoli semitrasparenti che ricalcano una cella del disegno.
    `veli` e' quanti.
    """
    import pypdfium2.raw as raw
    from .techink import NOME_RISERVATA
    from .tracciati import FILO, _componi, _matrice, _stile, _telaio
    dt, contorni, grafica = [], [], []
    dai_livelli = [0]
    etichette = [0]
    veli = [0]
    # (oggetto, colore) tutti dentro un box tolto dove sotto non c'e'
    # grafica, e i colori delle didascalie scritte dentro uno di quei box
    dentro, tinte = [], set()
    tp = raw.FPDFText_LoadPage(page.raw) if riservate else None

    def nel_riservato(o, m, testo):
        """None fuori dai box tolti; "coperta" se sta solo in aree coperte;
        "vuota" se sta in un box dove sotto non c'e' grafica."""
        r = _riquadro(o, m) if riservate else None
        if r is None:
            return None
        x0, y0, x1, y1 = r
        quota = QUOTA_ETICHETTA if testo else QUOTA_SEGNO
        dove = None
        for a0, b0, a1, b1, *resto in riservate:
            if (x0 >= a0 - SBORDO_ETICHETTA and y0 >= b0 - SBORDO_ETICHETTA
                    and x1 <= a1 + SBORDO_ETICHETTA
                    and y1 <= b1 + SBORDO_ETICHETTA
                    and (x1 - x0) * (y1 - y0) < quota * (a1 - a0) * (b1 - b0)):
                if not (resto and resto[0]):
                    return "vuota"
                dove = "coperta"
        return dove

    def giro(cont, quanti, prendi, ereditati, m):
        for i in range(quanti(cont)):
            o = prendi(cont, i)
            liv = ereditati | _livelli_oggetto(o)
            if liv & nomi_tecnici:
                dt.append(o)
                dai_livelli[0] += 1
                continue
            t = raw.FPDFPageObj_GetType(o)
            if (linee is not None
                    and t in (raw.FPDF_PAGEOBJ_FORM, raw.FPDF_PAGEOBJ_PATH)
                    and _velo(o, m, t, linee)):
                dt.append(o)
                veli[0] += 1
                continue
            if t == raw.FPDF_PAGEOBJ_FORM:
                giro(o, raw.FPDFFormObj_CountObjects, raw.FPDFFormObj_GetObject,
                     liv, _componi(m, _matrice(o)))
                continue
            if (t == raw.FPDF_PAGEOBJ_TEXT and stampato is not None
                    and _fuori(o, m, stampato)):
                dt.append(o)
                continue
            if t == raw.FPDF_PAGEOBJ_PATH:
                pieno, tratto = ctypes.c_int(), ctypes.c_int()
                raw.FPDFPath_GetDrawMode(o, ctypes.byref(pieno),
                                         ctypes.byref(tratto))
                if tratto.value:
                    st = _stile(o)
                    if st[0] <= FILO or st in penne_dt:
                        if pieno.value:
                            contorni.append((o, pieno.value))
                        else:
                            dt.append(o)
                        continue
            # sarebbe grafica: se sta dentro un box tolto, puo' essere la sua
            # didascalia, e si decide alla fine
            dove = (nel_riservato(o, m, t == raw.FPDF_PAGEOBJ_TEXT)
                    if riservate and t in (raw.FPDF_PAGEOBJ_TEXT,
                                           raw.FPDF_PAGEOBJ_PATH) else None)
            if dove is not None:
                if (t == raw.FPDF_PAGEOBJ_TEXT
                        and NOME_RISERVATA.search(_testo(o, tp))):
                    dt.append(o)
                    etichette[0] += 1
                    if dove == "vuota":
                        tinte.add(_colore(o))
                elif dove == "vuota":
                    dentro.append((o, _colore(o)))
                else:
                    grafica.append(o)
                continue
            grafica.append(o)

    try:
        giro(page.raw, raw.FPDFPage_CountObjects, raw.FPDFPage_GetObject,
             set(), _telaio(page))
    finally:
        if tp is not None:
            raw.FPDFText_ClosePage(tp)
    for o, colore in dentro:
        if colore in tinte:
            dt.append(o)
            etichette[0] += 1
        else:
            grafica.append(o)
    return dt, contorni, grafica, dai_livelli[0], etichette[0], veli[0]


# --------------------------------------------------------------------------- #
# la sovrastampa delle tinte piatte
# --------------------------------------------------------------------------- #
#
# Sul Kinder Choco Fresh T1 la merendina nel file c'e', e sul modello no. La
# foto e' in RGB, e sopra, grande quanto lei, il file ci disegna un'immagine
# in PANTONE Cool Gray 8 C IN SOVRASTAMPA: in macchina il grigio va sulla sua
# lastra e le altre restano come sono, quindi la foto si vede, velata di
# grigio dove il grigio c'e'. pdfium la sovrastampa la ignora - e' lo stesso
# difetto della `k` di `nero` - e la tinta piatta la dipinge coprente: dove il
# grigio e' a zero viene bianco, e un rettangolo bianco copre la merendina e
# il latte. Anche Ghostscript con la sovrastampa simulata la copre, ma solo
# perche' la foto e il grigio stanno in gruppi di trasparenza in RGB, dove la
# sua simulazione non arriva: con gli stessi gruppi dichiarati in CMYK la
# merendina la fa vedere anche lui. Non e' il file a nasconderla.
#
# Una tinta piatta in sovrastampa l'inchiostro lo AGGIUNGE a quello che trova:
# a video e' la fusione Moltiplica - dove la tinta e' a zero non cambia niente,
# dove c'e' scurisce. Si dice a pdfium immagine per immagine
# (`FPDFPageObj_SetBlendMode`), e solo per quelle:
#
# - di sole tinte piatte: Separation, anche come base di un Indexed, o
#   DeviceN senza colori di processo. Un DeviceN che porta anche C, M, Y o K
#   in sovrastampa quei canali li SOSTITUISCE, non li somma: le onde della
#   colata sono cosi', e le rende `colata`. Neanche /All, che va su tutte le
#   lastre e copre come in macchina;
# - disegnate con la sovrastampa accesa (`/op`, o `/OP` quando `/op` manca)
#   e con la fusione normale: se il file ne dichiara un'altra vale la sua.
#
# pdfium il flag di sovrastampa non lo espone: lo si legge dal flusso di
# contenuto, seguendo q/Q e gs anche dentro i form, e le immagini si
# accoppiano a quelle di pdfium nell'ordine in cui si disegnano. Se i due
# elenchi non tornano - quante sono, o le loro misure in pixel - non si tocca
# niente. Il flusso si legge solo se fra le risorse c'e' almeno un'immagine in
# tinta piatta. Su ventitre file provati ce l'hanno in sedici, sempre
# accoppiate a quelle di pdfium, e solo il KCF le disegna in sovrastampa: le
# altre sono coprenti anche in macchina, e restano come sono.

_PROCESSO = frozenset(("/Cyan", "/Magenta", "/Yellow", "/Black"))
# (file, mtime, taglia, pagina) -> disegni: il flusso si legge una volta sola
_SOVRASTAMPE = {}


def _oggetto(v):
    return v.get_object() if hasattr(v, "get_object") else v


def _vero(v):
    """Il valore di verita' di un booleano pypdf: `bool(BooleanObject(False))`
    e' True, perche' la classe non ha `__bool__`."""
    v = _oggetto(v)
    return bool(getattr(v, "value", v))


def _tinta_piatta(cs, nominati=None, fondo=0):
    """True se lo spazio colore `cs` stampa solo tinte piatte.

    `nominati` e' il dizionario `/ColorSpace` delle risorse, per gli spazi
    chiamati per nome (le immagini in linea, e i file che lo fanno anche
    sulle XObject).
    """
    cs = _oggetto(cs)
    if fondo > 4 or cs is None:
        return False
    if isinstance(cs, str):
        if nominati and cs in nominati:
            return _tinta_piatta(nominati[cs], None, fondo + 1)
        return False
    if not isinstance(cs, list) or len(cs) < 2:
        return False
    famiglia = _oggetto(cs[0])
    if famiglia in ("/Indexed", "/I"):
        return _tinta_piatta(cs[1], nominati, fondo + 1)
    if famiglia == "/Separation":
        return str(_oggetto(cs[1])) not in _PROCESSO | {"/All", "/None"}
    if famiglia == "/DeviceN":
        nomi = [str(_oggetto(n)) for n in _oggetto(cs[1]) or ()]
        return (any(n != "/None" for n in nomi)
                and not any(n in _PROCESSO or n == "/All" for n in nomi))
    return False


def _risorsa(risorse, nome):
    v = _oggetto(risorse.get(nome)) if isinstance(risorse, dict) else None
    return v if isinstance(v, dict) else {}


def _con_tinte_piatte(risorse, visti, fondo=0):
    """C'e' un'immagine in tinta piatta fra queste risorse, o nei form?"""
    if fondo > 32:
        return False
    xo = _risorsa(risorse, "/XObject")
    spazi = _risorsa(risorse, "/ColorSpace")
    for rif in xo.values():
        chiave = getattr(rif, "idnum", None)
        if chiave is not None:
            if chiave in visti:
                continue
            visti.add(chiave)
        o = _oggetto(rif)
        if not isinstance(o, dict):
            continue
        tipo = o.get("/Subtype")
        if tipo == "/Image":
            if _tinta_piatta(o.get("/ColorSpace"), spazi):
                return True
        elif tipo == "/Form" and _con_tinte_piatte(
                o.get("/Resources", risorse), visti, fondo + 1):
            return True
    return False


def sovrastampe(pdf, page_no=0):
    """Le immagini della pagina nell'ordine in cui si disegnano, `[(larghezza,
    altezza, a moltiplica)]`: vedi *la sovrastampa delle tinte piatte*.

    None se sulla pagina non ce n'e' nessuna da moltiplicare, o se il flusso
    di contenuto non si legge.
    """
    k = _chiave(pdf)
    chiave = k + (page_no,) if k else None
    if chiave is not None and chiave in _SOVRASTAMPE:
        return _SOVRASTAMPE[chiave]
    try:
        disegni = _disegni(pdf, page_no)
    except Exception:
        disegni = None
    if disegni is not None and not any(m for _w, _h, m in disegni):
        disegni = None
    if chiave is not None:
        while len(_SOVRASTAMPE) >= 8:
            _SOVRASTAMPE.pop(next(iter(_SOVRASTAMPE)))
        _SOVRASTAMPE[chiave] = disegni
    return disegni


# Del flusso servono pochi operatori, e pypdf li leggerebbe tutti: sul K Brioss
# STD sono 231.000 operazioni in 7 MB, tre secondi solo per trovare le poche
# che contano. Qui li trova un'espressione regolare, che salta intero quello
# dentro cui ci si confonderebbe - i commenti, le stringhe (annidate fino a
# tre livelli) e i byte delle immagini in linea - e che dagli operandi prende
# solo il nome che precede `gs` e `Do`. Il primo carattere si guarda prima di
# tutto il resto: cinque volte piu' veloce, mezzo secondo sul Brioss STD.
_DELIMITA = rb"(?![^\s()<>\[\]{}/%])"
_FLUSSO = re.compile(
    rb"(?=[%(B/qQ])(?:%[^\r\n]*"
    rb"|\((?:[^()\\]|\\.|\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\))*\)"
    rb"|(?<![^\s)>\]}])BI(?P<bi>[\s/].*?)\sID\s.*?\sEI" + _DELIMITA +
    rb"|(?P<nome>/[^\s()<>\[\]{}/%]*)\s+(?P<op>gs|Do)" + _DELIMITA +
    rb"|(?<![^\s)>\]}])(?P<qQ>[qQ])" + _DELIMITA + rb")", re.S)
_VALORE_IN_LINEA = rb"\s*(\[[^\]]*\]|/[^\s()<>\[\]{}/%]*|[^\s()<>\[\]{}/%]+)"


def _nome(b):
    """Un nome PDF dal flusso, come lo scrive pypdf nelle chiavi: `#xx`
    decodificato."""
    b = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes((int(m.group(1), 16),)), b)
    return b.decode("utf-8", "replace")


def _in_linea(testo, spazi):
    """`(larghezza, altezza, tinta piatta)` di un'immagine in linea, dal suo
    dizionario."""
    def valore(*chiavi):
        for k in chiavi:
            m = re.search(re.escape(b"/" + k) + _DELIMITA + _VALORE_IN_LINEA,
                          testo)
            if m:
                return m.group(1)
        return None

    def intero(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    cs = valore(b"CS", b"ColorSpace") or b""
    if cs.startswith(b"["):
        parti = re.findall(rb"/[^\s()<>\[\]{}/%]*", cs)
        # un Indexed in linea: la base e' il secondo nome
        tinta = (len(parti) > 1 and _nome(parti[0]) in ("/I", "/Indexed")
                 and _tinta_piatta(_nome(parti[1]), spazi))
    else:
        tinta = bool(cs) and _tinta_piatta(_nome(cs), spazi)
    return (intero(valore(b"W", b"Width")), intero(valore(b"H", b"Height")),
            bool(tinta))


def _disegni(pdf, page_no):
    import pypdf
    r = pypdf.PdfReader(pdf)
    pagina = r.pages[page_no]
    if not _con_tinte_piatte(_oggetto(pagina.get("/Resources")), set()):
        return None
    fuori = []

    def giro(dati, risorse, stato, fondo):
        if fondo > 32:
            raise ValueError("form annidati troppo a fondo")
        risorse = _oggetto(risorse)
        gs = _risorsa(risorse, "/ExtGState")
        xo = _risorsa(risorse, "/XObject")
        spazi = _risorsa(risorse, "/ColorSpace")
        pila = []
        st = dict(stato)
        for m in _FLUSSO.finditer(dati):
            q, op = m.group("qQ"), m.group("op")
            if q == b"q":
                pila.append(dict(st))
            elif q == b"Q":
                if pila:
                    st = pila.pop()
            elif op == b"gs":
                g = _oggetto(gs.get(_nome(m.group("nome"))))
                if not isinstance(g, dict):
                    continue
                if "/OP" in g:
                    st["OP"] = _vero(g["/OP"])
                if "/op" in g:
                    st["op"] = _vero(g["/op"])
                elif "/OP" in g:
                    st["op"] = st["OP"]
                if "/BM" in g:
                    bm = _oggetto(g["/BM"])
                    if isinstance(bm, list):
                        bm = _oggetto(bm[0]) if bm else "/Normal"
                    st["normale"] = str(bm) in ("/Normal", "/Compatible")
            elif op == b"Do":
                o = _oggetto(xo.get(_nome(m.group("nome"))))
                if not isinstance(o, dict):
                    continue
                tipo = o.get("/Subtype")
                if tipo == "/Image":
                    # una maschera prende il colore corrente: non si segue
                    tinta = (not _vero(o.get("/ImageMask"))
                             and _tinta_piatta(o.get("/ColorSpace"), spazi))
                    fuori.append((int(_oggetto(o.get("/Width", 0))),
                                  int(_oggetto(o.get("/Height", 0))),
                                  bool(tinta and st["op"] and st["normale"])))
                elif tipo == "/Form":
                    giro(o.get_data(), o.get("/Resources", risorse), st,
                         fondo + 1)
            elif m.group("bi") is not None:
                larga, alta, tinta = _in_linea(m.group("bi"), spazi)
                fuori.append((larga, alta,
                              bool(tinta and st["op"] and st["normale"])))

    contenuto = pagina.get_contents()
    if contenuto is None:
        return None
    giro(contenuto.get_data(), pagina.get("/Resources"),
         {"OP": False, "op": False, "normale": True}, 0)
    return fuori


def _moltiplica(page, disegni):
    """Mette a Moltiplica le immagini che `disegni` segna. Torna quante, o
    None se le immagini di pdfium non sono quelle del flusso."""
    import pypdfium2.raw as raw
    immagini = []

    def giro(cont, quanti, prendi):
        for i in range(quanti(cont)):
            o = prendi(cont, i)
            t = raw.FPDFPageObj_GetType(o)
            if t == raw.FPDF_PAGEOBJ_IMAGE:
                immagini.append(o)
            elif t == raw.FPDF_PAGEOBJ_FORM:
                giro(o, raw.FPDFFormObj_CountObjects, raw.FPDFFormObj_GetObject)

    giro(page.raw, raw.FPDFPage_CountObjects, raw.FPDFPage_GetObject)
    if len(immagini) != len(disegni):
        return None
    w, h = ctypes.c_uint(), ctypes.c_uint()
    for o, (larga, alta, _m) in zip(immagini, disegni):
        if (not raw.FPDFImageObj_GetImagePixelSize(o, ctypes.byref(w),
                                                   ctypes.byref(h))
                or (w.value, h.value) != (larga, alta)):
            return None
    n = 0
    for o, (_l, _a, moltiplica) in zip(immagini, disegni):
        if moltiplica:
            raw.FPDFPageObj_SetBlendMode(o, b"Multiply")
            n += 1
    return n


# L'ultimo conteggio fatto: lo legge chi scrive gli avvisi, senza una seconda
# passata sulla pagina. Uno solo e non uno per file, perche' la colata il
# foglio lo puo' rendere da una COPIA del file - quella col suo livello
# spento - e chi scrive l'avviso il nome della copia non lo conosce.
CONTI = {}


def rendi(pdf, page_no=0, scala=1.0, livello=GRAFICA, riquadro=None,
          trasparente=False, nomi_tecnici=None, stampato=None):
    """La pagina resa con un livello solo acceso. Torna un'immagine PIL.

    `riquadro` e' `(x0, y0, x1, y1)` in punti, nel telaio della MediaBox con
    la y in giu' - quello di `render_page` e dei tracciati. `trasparente` rende
    su fondo trasparente, per sapere DOVE un livello dipinge: vedi
    `impronta_dt`.

    I livelli tecnici del file qui si spengono di nuovo anche se chi chiama li
    ha gia' spenti nel dizionario: costa niente, e cosi' la funzione da' lo
    stesso livello anche sul file originale. `stampato` e' il riquadro
    dell'artwork, per mandare nel DT i testi che ne stanno fuori: vedi
    `dividi`.
    """
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    nomi = set(tecnici(pdf, page_no) if nomi_tecnici is None else nomi_tecnici)
    pen = penne(pdf, page_no)
    doc = pdfium.PdfDocument(pdf)
    try:
        page = doc[page_no]
        page.set_cropbox(*page.get_mediabox())
        dt, contorni, grafica, dai_livelli, etichette, veli = dividi(
            page, pen, nomi, stampato, riservate(pdf),
            linee_dt(pdf, page_no, pen))
        CONTI.clear()
        CONTI.update(livelli=dai_livelli, etichette=etichette, veli=veli,
                     tratti=len(dt) - dai_livelli - etichette - veli,
                     contorni=len(contorni), grafica=len(grafica))
        if livello == GRAFICA:
            for o in dt:
                raw.FPDFPageObj_SetIsActive(o, False)
            for o, pieno in contorni:
                raw.FPDFPath_SetDrawMode(o, pieno, False)
            # le tinte piatte in sovrastampa: vedi sopra
            disegni = sovrastampe(pdf, page_no)
            if disegni:
                n = _moltiplica(page, disegni)
                CONTI.update(moltiplica=n or 0, spaiate=n is None)
        elif livello == DT:
            for o in grafica:
                raw.FPDFPageObj_SetIsActive(o, False)
            for o, _pieno in contorni:
                raw.FPDFPath_SetDrawMode(o, 0, True)
        else:
            raise ValueError("livello sconosciuto: %r" % (livello,))
        opz = {}
        if riquadro is not None:
            mx0, my0, mx1, my1 = page.get_mediabox()
            x0, y0, x1, y1 = riquadro
            opz["crop"] = (x0, (my1 - my0) - y1, (mx1 - mx0) - x1, y0)
        fondo = (255, 255, 255, 0) if trasparente else (255, 255, 255, 255)
        im = page.render(scale=scala, fill_color=fondo, **opz).to_pil()
        return im.convert("RGBA" if trasparente else "RGB")
    finally:
        doc.close()


def impronta_dt(pdf, page_no=0, scala=1.0, riquadro=None, misura=None,
                allarga=1):
    """Dove dipinge il livello DT: maschera booleana, o None se non dipinge.

    Serve a chi incolla sulla texture pixel resi da un ALTRO motore: la lastra
    del nero e la banda della colata vengono da Ghostscript, che gli oggetti
    spenti in pdfium non li vede, e un tratto di fustella in nero pieno
    tornerebbe sulla grafica proprio dalla porta di servizio.

    `misura` e' `(larghezza, altezza)` in pixel se la maschera va portata su
    un'immagine di un'altra risoluzione; `allarga` sono i pixel di margine,
    per l'antialiasing che l'altro motore fa a modo suo.
    """
    import numpy as np
    from PIL import Image
    from scipy.ndimage import binary_dilation
    im = rendi(pdf, page_no, scala, DT, riquadro, trasparente=True)
    alfa = im.getchannel("A")
    if misura is not None and alfa.size != tuple(misura):
        alfa = alfa.resize(tuple(misura), Image.BILINEAR)
    m = np.asarray(alfa) > 0
    if not m.any():
        return None
    if allarga:
        m = binary_dilation(m, np.ones((3, 3), bool), iterations=allarga)
    return m
