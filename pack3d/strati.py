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


# I riquadri delle aree riservate ai dati variabili che la costruzione ha tolto,
# per file: chi rende la texture ci spegne dentro le didascalie. Li scrive
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
# codice - non la sua didascalia.
SBORDO_ETICHETTA = 1.0
QUOTA_ETICHETTA = 0.8


def dividi(page, penne_dt, nomi_tecnici, stampato=None, riservate=()):
    """`(dt, contorni, grafica, dai_livelli, etichette)`: gli oggetti nei due
    livelli.

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

    Con un'eccezione, per le aree riservate ai dati variabili che la
    costruzione ha tolto (`riservate`, i loro riquadri: vedi
    `artwork.strip_separations`). Tolta l'area resta la sua DIDASCALIA - sul
    Kinder Cards T2 "Best Before Area" e "POSITIONING AREA FOR EAN CODE (if
    requested)" in marrone scuro, stampate sui fianchi del pack - e la
    didascalia e' il nome del posto, non si stampa mai. Dentro un riquadro
    tolto:

    - un testo che dice il nome di un'area riservata (`techink.NOME_RISERVATA`)
      e' una didascalia: lo dice quello che c'e' scritto, non il colore;
    - ma non tutte sono testo: quella del codice a barre del Kinder Cards e'
      in curve, 38 tracciati. Un oggetto tutto dentro il riquadro e del
      COLORE di una didascalia scritta e' una didascalia anche lui. Un codice a
      barre vero - nero, e la didascalia e' di un'altra tinta - resta dov'e';
      e senza nessuna didascalia scritta non si impara nessun colore e non si
      toglie niente.

    Fuori dai riquadri tolti non si tocca niente: dove l'area riservata resta
    - succede, sul Kinder Country e' dipinta con una Pantone qualsiasi - la
    sua scritta resta con lei, e un riquadro verde senza nome sembrerebbe
    grafica. `etichette` e' quante didascalie sono finite nel DT.
    """
    import pypdfium2.raw as raw
    from .techink import NOME_RISERVATA
    from .tracciati import FILO, _componi, _matrice, _stile, _telaio
    dt, contorni, grafica = [], [], []
    dai_livelli = [0]
    etichette = [0]
    # (oggetto, colore) tutti dentro un riquadro riservato, e i colori delle
    # didascalie scritte dentro un riquadro riservato
    dentro, tinte = [], set()
    tp = raw.FPDFText_LoadPage(page.raw) if riservate else None

    def nel_riservato(o, m):
        r = _riquadro(o, m) if riservate else None
        if r is None:
            return False
        x0, y0, x1, y1 = r
        for a0, b0, a1, b1 in riservate:
            if (x0 >= a0 - SBORDO_ETICHETTA and y0 >= b0 - SBORDO_ETICHETTA
                    and x1 <= a1 + SBORDO_ETICHETTA
                    and y1 <= b1 + SBORDO_ETICHETTA
                    and (x1 - x0) * (y1 - y0)
                    < QUOTA_ETICHETTA * (a1 - a0) * (b1 - b0)):
                return True
        return False

    def giro(cont, quanti, prendi, ereditati, m):
        for i in range(quanti(cont)):
            o = prendi(cont, i)
            liv = ereditati | _livelli_oggetto(o)
            if liv & nomi_tecnici:
                dt.append(o)
                dai_livelli[0] += 1
                continue
            t = raw.FPDFPageObj_GetType(o)
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
            # sarebbe grafica: se sta dentro un'area riservata tolta, puo'
            # essere la sua didascalia, e si decide alla fine
            if (riservate and t in (raw.FPDF_PAGEOBJ_TEXT,
                                    raw.FPDF_PAGEOBJ_PATH)
                    and nel_riservato(o, m)):
                if (t == raw.FPDF_PAGEOBJ_TEXT
                        and NOME_RISERVATA.search(_testo(o, tp))):
                    dt.append(o)
                    etichette[0] += 1
                    tinte.add(_colore(o))
                else:
                    dentro.append((o, _colore(o)))
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
    return dt, contorni, grafica, dai_livelli[0], etichette[0]


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
        dt, contorni, grafica, dai_livelli, etichette = dividi(
            page, pen, nomi, stampato, riservate(pdf))
        CONTI.clear()
        CONTI.update(livelli=dai_livelli, etichette=etichette,
                     tratti=len(dt) - dai_livelli - etichette,
                     contorni=len(contorni), grafica=len(grafica))
        if livello == GRAFICA:
            for o in dt:
                raw.FPDFPageObj_SetIsActive(o, False)
            for o, pieno in contorni:
                raw.FPDFPath_SetDrawMode(o, pieno, False)
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
