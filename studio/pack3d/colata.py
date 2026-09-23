"""
La colata Kinder: rimetterle l'ombra che il nostro rasterizzatore le toglie.

La colata e' costruita in **sovrastampa**: una lastra di ciano che moltiplica
il rosso sotto, e da quella moltiplicazione vengono l'ombra sulle gocce e il
volume del getto. pdfium la sovrastampa non la simula - verificato con un PDF
costruito apposta, un ciano sopra un magenta con `/OP true` e senza: esce
identico, (0, 174, 239) tutte e due le volte. Il ciano copre il rosso invece
di moltiplicarlo, e l'ombra diventa un alone azzurro piatto.

Due strade, e la prima e' sempre meglio della seconda perche' usa
**l'inchiostro del file** invece di roba portata da fuori:

1. **la banda resa in quadricromia.** Ghostscript la sovrastampa la simula
   (stessa prova: (46, 48, 146), cioe' C+M, il blu giusto). Si rende con lui
   la sola banda della colata e la si incolla dentro l'impronta del livello.
   Quello che viene fuori e' la colata del file, resa come la vedrebbe una
   macchina da stampa.
2. **la risorsa**, se la prima non ha niente da correggere. Quando l'ombra nel
   file e' FUSTELLATA invece che in sovrastampa - il ciano toglie il rosso
   invece di moltiplicarlo - sotto non c'e' piu' niente da moltiplicare, e
   nessun rasterizzatore la puo' recuperare: misurato su KP T1 Mandarino, dove
   l'ombra ha Cyan al 34,9% e PANTONE Warm Red al 2,6%, contro il 98,1% del
   rosso pieno accanto. Li' si sostituisce con `risorse/colata_kinder.png`.

Tutte e due vogliono la colata su un **livello suo**: il livello dice dove va,
e non si indovina niente. Il file che ha aperto la strada e'
`KP_T1_Mandarino`, che ha un OCG chiamato `Colata`.

Si incolla sempre e solo dentro l'**impronta** del livello. Non e' pignoleria:
e' quello che tiene fuori i guai. Su KP T1 la stessa resa in quadricromia fa
diventare NERO il bicchierino di latte che sta sopra la colata - lui la
sovrastampa ce l'ha davvero - ma il bicchiere sul livello `Colata` non sta, e
fuori dall'impronta non lo tocca nessuno.

Come si trova l'impronta:

- si spegne il livello in una copia, aggiungendo il suo OCG a
  `/OCProperties/D/OFF`. E' una modifica di DIZIONARIO: non costa la passata
  di pypdf sul flusso di contenuto, che su Colazione vale 7 secondi e 100 MB;
- si rendono le due pagine su fondo TRASPARENTE e si confronta anche l'alfa.
  Sul colore soltanto la maschera avrebbe dei buchi dove la colata e' bianca -
  la cresta e le gocce - perche' bianco su bianco non fa differenza.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image

from . import strati
from .dieline import PT2MM, render_page

# I nomi di livello che portano la colata, confrontati per nome intero.
NOMI = {"colata", "colata kinder", "milk splash", "splash"}

RISORSE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "risorse")
RISORSA = os.path.join(RISORSE, "colata_kinder.png")

# Scala della resa usata per trovare l'impronta e l'allineamento, in px per
# punto PDF. Non e' la scala della texture: serve solo a misurare, e a 2 px/pt
# l'onda ha un periodo di un centinaio di pixel, abbastanza per lo spettro.
MISURA = 2.0

# Oltre questo errore mediano l'allineamento non si crede: vuol dire che la
# risorsa non e' il disegno che sta nel file. Mezzo millimetro e' dieci volte
# quello misurato sul caso buono.
ERRORE_MAX_MM = 0.5

# Ghostscript, se c'e'. Senza, resta solo la risorsa: il codice non si rompe,
# si limita a fare meno.
GS = shutil.which("gs")

# Quante delle ombre azzurre deve cambiare la sovrastampa perche' la colata si
# possa dire davvero in sovrastampa. La soglia sta larga fra i due casi
# misurati: 1,1% su KP T1 Mandarino, dove l'ombra e' fustellata, e 49,6% sul
# Kinder Pingui T6 BOX, dove e' in sovrastampa.
CAMBIO_MINIMO = 0.10


# I livelli stanno in `strati.py`, che e' il modulo che li usa per separare il
# disegno tecnico: qui servono le stesse due funzioni, e averne due copie
# vorrebbe dire correggere due volte lo stesso difetto - `append` che perde
# `/OCProperties` l'ho gia' corretto una volta.
livelli = strati.livelli
spegni = strati.spegni


def _curva(a):
    """Per ogni colonna, la prima riga in cui comincia il rosso.

    E' la linea dell'onda, ed e' quello su cui si allinea: e' l'unica cosa che
    la risorsa e l'artwork hanno in comune pixel per pixel.
    """
    rosso = ((a[:, :, 0].astype(np.int16) > 140)
             & (a[:, :, 1].astype(np.int16) < 140)
             & (a[:, :, 2].astype(np.int16) < 140))
    y = np.full(a.shape[1], np.nan)
    primo = rosso.argmax(0)
    c = rosso.any(0)
    y[c] = primo[c]
    return y


def _periodo(y):
    """Il periodo dominante dell'onda, in pixel."""
    v = np.where(np.isfinite(y), y, np.nanmean(y))
    v = v - v.mean()
    F = np.abs(np.fft.rfft(v * np.hanning(len(v))))
    f = np.fft.rfftfreq(len(v))
    lo = (f > 3.0 / len(v)) & (f < 0.3)
    if not lo.any():
        return None
    return 1.0 / f[lo][np.argmax(F[lo])]


def allinea(banda, risorsa):
    """Scala, sfasamento e quota che portano la risorsa sulla banda.

    Restituisce `(s, dx, dy, errore_px)`, con `dx` e `dy` in pixel della banda.

    Il rapporto fra i periodi da' la scala solo APPROSSIMATA: su KP T1
    Mandarino lo spettro, che su sette cicli ha poca risoluzione, sbaglia
    dell'8%. E un'onda e' periodica, quindi con la scala sbagliata si trova
    comunque una fase che sembra buona - un ottimo locale a 0,27 mm invece dei
    0,10 del vero. La scala si cerca quindi in una finestra larga attorno alla
    stima, e per ogni scala la fase viene da una correlazione, che e' esatta e
    costa una FFT su qualche centinaio di punti.
    """
    ca, cr = _curva(banda), _curva(risorsa)
    pa, pr = _periodo(ca), _periodo(cr)
    if not pa or not pr:
        return None
    W = banda.shape[1]
    va = np.where(np.isfinite(ca), ca, np.nanmean(ca))
    va = va - va.mean()

    def errore(s, dx):
        xs = (np.arange(W) - dx) / s
        ok = (xs >= 0) & (xs < len(cr) - 1) & np.isfinite(ca)
        if ok.sum() < 0.5 * W:
            return None
        v = np.interp(xs[ok], np.arange(len(cr)), cr) * s
        d = ca[ok] - v
        dy = np.median(d)
        return float(np.median(np.abs(d - dy))), dy

    best = None
    for s in (pa / pr) * np.linspace(0.82, 1.22, 81):
        lungo = int(round(len(cr) * s))
        if lungo < W:
            continue
        vr = np.interp(np.arange(lungo) / s, np.arange(len(cr)), cr) * s
        vr = vr - vr.mean()
        corr = np.correlate(vr, va, mode="valid")
        for dx in (-float(np.argmax(corr)),
                   -float(np.argsort(corr)[-2]) if len(corr) > 1 else None):
            if dx is None:
                continue
            for d in (-2.0, -1.0, 0.0, 1.0, 2.0):
                r = errore(s, dx + d)
                if r and (best is None or r[0] < best[0]):
                    best = (r[0], s, dx + d, r[1])
    if best is None:
        return None
    e, s, dx, dy = best
    for ss in s * np.linspace(0.995, 1.005, 21):
        for ddx in np.arange(dx - 4, dx + 4.01, 0.5):
            r = errore(ss, ddx)
            if r and r[0] < e:
                e, s, dx, dy = r[0], ss, ddx, r[1]
    return s, dx, dy, e


def _fase(banda, ris, s, dx, dy, periodo):
    """Fra le fasi che distano un periodo, quella giusta la dice la GOCCIA.

    L'onda e' periodica: spostare la risorsa di un periodo intero lascia le
    due curve sovrapposte, e una misura robusta come la mediana non se ne
    accorge - la goccia, che e' l'unica cosa aperiodica del disegno, la scarta
    come fosse rumore. Sul KP T1 Mandarino l'allineamento tornava a 0,22 mm con
    la goccia a mezzo pack di distanza, cioe' sparita.

    Qui si confrontano le IMMAGINI, non le curve, e si sceglie la fase che
    somiglia di piu'. La goccia pesa poco in percentuale ma e' l'unica cosa che
    cambia da una fase all'altra, quindi decide lei.
    """
    H, W = banda.shape[:2]
    a = banda.astype(np.int16)
    nw, nh = max(1, int(round(ris.shape[1] * s))), max(1, int(round(ris.shape[0] * s)))
    r = np.asarray(Image.fromarray(ris).resize((nw, nh), Image.LANCZOS)).astype(np.int16)
    passo = periodo * s
    best = None
    n = int(np.ceil(W / max(passo, 1.0))) + 1
    for k in range(-n, n + 1):
        d = dx + k * passo
        rx, ry = int(round(d)), int(round(dy))
        x0, y0 = max(rx, 0), max(ry, 0)
        x1, y1 = min(rx + nw, W), min(ry + nh, H)
        if x1 - x0 < 0.8 * W or y1 - y0 < 0.5 * H:
            continue
        pezzo = r[y0 - ry:y1 - ry, x0 - rx:x1 - rx]
        err = float(np.abs(a[y0:y1, x0:x1] - pezzo).mean())
        if best is None or err < best[0]:
            best = (err, d)
    return dx if best is None else best[1]


def _impronta(a, b, soglia=10):
    """Dove le due rese differiscono, e il riquadro. `(maschera, (x0,x1,y0,y1))`.

    Le rese vanno passate in RGBA su fondo TRASPARENTE, e il confronto guarda
    anche l'alfa. Sul colore soltanto la maschera ha dei buchi, e non sono
    dettagli: il bianco della colata sopra il bianco del foglio non fa
    differenza, quindi la cresta e le gocce - che sono bianche - risultavano
    scoperte, e al loro posto restava il fondo. Sul KP T1 Mandarino si vedeva
    come una mezzaluna bianca sul rosso, attorno alla goccia.

    Canale per canale e su uint8: `abs(a - b).max(2)` su una pagina intera
    vorrebbe quattro copie a 16 bit del foglio tutte insieme.
    """
    if a.shape != b.shape:
        return None
    m = np.zeros(a.shape[:2], bool)
    for c in range(a.shape[2]):
        d = np.abs(a[:, :, c].astype(np.int16) - b[:, :, c].astype(np.int16))
        np.logical_or(m, d > soglia, out=m)
    if not m.any():
        return None
    ys, xs = np.where(m)
    return m, (int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1)


def _rgba(pdf, page_no, scala, riq=None):
    """La pagina - o solo `riq`, in punti con la y in giu' - su fondo trasparente.

    Non passa dalla cassa di `render_page`: quella tiene una pagina sola e, se
    gliene chiedi una piu' piccola, te la RIDUCE invece di rifarla. Una ridotta
    e una nativa differiscono su tutto il foglio, e l'impronta del livello
    diventa la pagina intera.
    """
    import pypdfium2 as pdfium
    page = pdfium.PdfDocument(pdf)[page_no]
    page.set_cropbox(*page.get_mediabox())
    mx0, my0, mx1, my1 = page.get_mediabox()
    W, H = mx1 - mx0, my1 - my0
    opz = {}
    if riq is not None:
        x0, x1, y0, y1 = riq
        opz["crop"] = (x0, H - y1, W - x1, y0)
    im = page.render(scale=scala, fill_color=(255, 255, 255, 0), **opz).to_pil()
    return np.asarray(im.convert("RGBA"))


def _su_bianco(a):
    """RGBA appiattito su fondo bianco, per misurarci sopra l'onda."""
    al = a[:, :, 3:4].astype(np.uint16)
    return ((a[:, :, :3].astype(np.uint16) * al + 255 * (255 - al)) // 255
            ).astype(np.uint8)


def quadricromia(pdf, page_no, scala, riq, sovrastampa="simulate"):
    """La banda `riq` resa da Ghostscript con la sovrastampa simulata.

    `riq` e' (x0, x1, y0, y1) in punti, y in giu'. Si ritaglia il MediaBox
    sulla banda e si rende solo quella: la colata e' una striscia di 120 x 36
    mm su un foglio da 300 x 250, e renderla da sola costa un paio di secondi
    invece di dieci, con una quarantina di MB.

    None se Ghostscript non c'e' o se qualcosa non torna: il modello si
    costruisce comunque.
    """
    if not GS:
        return None
    import pypdf
    x0, x1, y0, y1 = riq
    sorgente = destinazione = None
    try:
        r = pypdf.PdfReader(pdf)
        mb = r.pages[page_no].mediabox
        alt = float(mb.top) - float(mb.bottom)
        bx, by = float(mb.left), float(mb.bottom)
        w = pypdf.PdfWriter(clone_from=pdf)
        pg = w.pages[page_no]
        pg.mediabox.lower_left = (bx + x0, by + alt - y1)
        pg.mediabox.upper_right = (bx + x1, by + alt - y0)
        pg.cropbox = pg.mediabox
        sorgente = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        sorgente.close()
        destinazione = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        destinazione.close()
        with open(sorgente.name, "wb") as fh:
            w.write(fh)
        esito = subprocess.run(
            [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
             "-sOverprint=" + sovrastampa, "-sDEVICE=png16m",
             "-r%g" % (scala * 72.0), "-dTextAlphaBits=4",
             "-dGraphicsAlphaBits=4", "-sOutputFile=" + destinazione.name,
             sorgente.name], capture_output=True, timeout=120)
        if esito.returncode != 0 or not os.path.getsize(destinazione.name):
            return None
        return np.asarray(Image.open(destinazione.name).convert("RGB"))
    except Exception:
        return None
    finally:
        for t in (sorgente, destinazione):
            try:
                if t is not None:
                    os.unlink(t.name)
            except OSError:
                pass


def _azzurro(a):
    """I pixel dell'ombra sbagliata: chiari, con molto piu' blu che rosso.

    E' l'aspetto che prende l'ombra della colata quando la sovrastampa non
    viene simulata: il ciano copre il rosso invece di moltiplicarlo, e
    l'ombra diventa un alone azzurro piatto.

    **Da solo non distingue niente.** Sul Kinder Pingui T6 BOX la macchia
    azzurra piu' grande del foglio non e' un'ombra rotta: e' il fondo del
    pack, gocce d'acqua su azzurro, 15.800 px che vanno lasciati in pace.
    Serve percio' sempre dentro un riquadro che qualcuno ha guardato - il
    livello `Colata`, o l'occhio - e mai come riconoscitore.
    """
    b = a.astype(np.int16)
    return ((b[:, :, 2] - b[:, :, 0] > 45) & (b[:, :, 2] > 190)
            & (b[:, :, 1] > 170))


def dal_riquadro(pdf, page_no, scala, riq):
    """La banda riparata e la maschera, partendo da un RIQUADRO.

    Sul file che la colata la dichiara la maschera viene dall'impronta del
    livello. Su quello che non la dichiara il livello non c'e' e l'impronta
    non si puo' misurare: resta il riquadro indicato a occhio. Ma il riquadro
    da solo e' troppo grosso - dentro una banda di 186 x 57 mm non c'e' solo
    l'ombra - quindi la maschera sono **i pixel azzurri che la sovrastampa
    cambia**, dentro quel riquadro.

    Piu' stretta dell'impronta del livello, e piu' sicura: non puo' toccare
    quello che azzurro non e'. Il marchio `kinder` e il bicchierino di latte,
    che rendendo in quadricromia diventano neri, azzurri non sono mai.

    Torna `(banda, maschera, quota, quanti)`, o `None` se Ghostscript non c'e'
    o se una delle due rese non viene.
    """
    from scipy.ndimage import binary_dilation

    q = quadricromia(pdf, page_no, scala, riq, "simulate")
    piatta = quadricromia(pdf, page_no, scala, riq, "disable")
    if q is None or piatta is None:
        return None
    h = min(q.shape[0], piatta.shape[0])
    w = min(q.shape[1], piatta.shape[1])
    q, piatta = q[:h, :w], piatta[:h, :w]
    azzurro = _azzurro(piatta)
    quante = int(azzurro.sum())
    if not quante:
        return q, np.zeros((h, w), bool), 0.0, 0
    cambia = np.abs(q.astype(np.int16) - piatta.astype(np.int16)).max(2) > 20
    # L'orlo dell'ombra e' sfumato, e un pixel mezzo azzurro la prova
    # dell'azzurro non la passa: si tiene anche quello che CONFINA con
    # l'azzurro e cambia, se no attorno all'ombra rimessa resta un filo
    # chiaro largo un pixel, che e' il difetto di prima in miniatura.
    maschera = cambia & binary_dilation(azzurro, np.ones((3, 3), bool))
    return q, maschera, float((azzurro & cambia).sum()) / quante, quante


def _peso_sovrastampa(simulata, piatta, maschera):
    """Quanto conta la sovrastampa, e su quanti pixel. `(quota, quanti)`.

    La domanda giusta non e' quanta parte della banda cambia - quella e' area,
    e sui due casi misurati da' lo stesso 5% pur essendo casi opposti. La
    domanda e': delle zone che senza sovrastampa escono AZZURRE, cioe' delle
    ombre sbagliate, quante ne rimette a posto?

        KP T1 Mandarino   13.248 px azzurri, ne cambia l'1,1%
        Kinder Pingui T6   7.672 px azzurri, ne cambia il 49,6%

    Il primo ha l'ombra fustellata: il ciano toglie il rosso invece di
    moltiplicarlo, sotto non c'e' piu' niente, e non c'e' niente da
    recuperare. Il secondo ce l'ha in sovrastampa, e si recupera meta'.
    """
    if simulata is None or piatta is None:
        return 0.0, 0
    h = min(simulata.shape[0], piatta.shape[0], maschera.shape[0])
    w = min(simulata.shape[1], piatta.shape[1], maschera.shape[1])
    a = simulata[:h, :w].astype(np.int16)
    b = piatta[:h, :w].astype(np.int16)
    azzurro = _azzurro(b) & maschera[:h, :w]
    quante = int(azzurro.sum())
    if not quante:
        return 0.0, 0
    cambia = np.abs(a - b).max(2) > 20
    return float((azzurro & cambia).sum()) / quante, quante


def _incolla(base, banda, maschera, bx0, by0):
    """La banda dentro la maschera, alla sua posizione sul foglio.

    Si incolla su un'immagine PIL, **in posto**, e chi chiama deve possederla
    - `render_page` la sua resa la tiene in cassa e restituisce quella, quindi
    scriverci dentro vorrebbe dire sporcare la cassa; `convert` una copia
    fresca la fa gia'.

    Passando per numpy servirebbe invece una copia SCRIVIBILE dell'intero
    foglio: sul Kinder Pingui T6 BOX sono 6516 x 3923 px, 76 MB, sommati ai 76
    che `convert` ha appena fatto. Il picco della costruzione andava a 500 MB,
    cioe' a un soffio dal tetto di 512 del piano Free, per incollarne uno da
    1474 x 457.
    """
    h = min(banda.shape[0], maschera.shape[0])
    w = min(banda.shape[1], maschera.shape[1])
    if h <= 0 or w <= 0:
        return
    base.paste(Image.fromarray(banda[:h, :w]), (bx0, by0),
               Image.fromarray(maschera[:h, :w]))


def _a_occhio(pdf, scala, page_no, note, riquadro):
    """La colata riparata dentro un riquadro indicato a occhio.

    E' la strada per i file che il livello `Colata` non ce l'hanno - sul
    parco di prova otto su nove - dove oggi non succedeva niente e l'ombra
    restava azzurra. Il riquadro lo da' chi ha guardato il foglio; dentro,
    quello che si tocca lo decide l'inchiostro, non il rettangolo.
    """
    x_mm, y_mm, w_mm, h_mm = riquadro
    riq = (x_mm / PT2MM, (x_mm + w_mm) / PT2MM,
           y_mm / PT2MM, (y_mm + h_mm) / PT2MM)
    # Ghostscript prima del foglio, per l'abitudine di `nero.spia`: costa 105
    # MB fissi e parte con un fork, quindi il momento in cui lo chiami conta.
    # Qui non cambia il picco - la resa della pagina a questo punto e' gia' in
    # cassa, quindi `render_page` non alloca niente - ma non costa niente
    # neanche a tenerlo cosi', e su un file che in cassa non ce l'ha conta.
    esito = dal_riquadro(pdf, page_no, scala, riq)
    base = render_page(pdf, page_no, scala)
    if esito is None:
        if note is not None:
            note.append("colata indicata a occhio: Ghostscript non c'e' o la "
                        "banda non si rende, l'ombra resta com'e'")
        return base
    banda, maschera, quota, quante = esito
    if quota < CAMBIO_MINIMO:
        if note is not None:
            note.append(
                "colata indicata a occhio a %.0f,%.0f mm: delle %d zone "
                "azzurre la sovrastampa ne cambia solo il %.1f%%, quindi li' "
                "l'ombra non e' in sovrastampa e non c'e' niente da rimettere"
                % (x_mm, y_mm, quante, 100 * quota))
        return base
    fuori = base.convert("RGB")
    _incolla(fuori, banda, maschera,
             max(int(round(riq[0] * scala)), 0), max(int(round(riq[2] * scala)), 0))
    if note is not None:
        note.append(
            "colata indicata a occhio, resa in quadricromia: %.0f x %.0f mm, "
            "e la sovrastampa rimette l'ombra al %.0f%% delle %d zone che "
            "uscivano azzurre" % (w_mm, h_mm, 100 * quota, quante))
    return fuori


def foglio(pdf, scala, page_no=0, note=None, riquadro=None):
    """Il foglio reso, con la colata rimessa a posto se si puo'.

    Prima si prova con l'inchiostro del file - la banda resa in quadricromia,
    con la sovrastampa simulata - e solo se li' non c'era niente da correggere
    si passa alla risorsa. Il file che il livello non ce l'ha non paga niente:
    una lettura dei dizionari e via.

    `riquadro` e' `(x_mm, y_mm, w_mm, h_mm)` e serve ai file che il livello
    non ce l'hanno: lo indica chi ha GUARDATO il foglio, vedi
    `tools.colata_a_occhio`. Il livello, quando c'e', viene prima: e' una cosa
    che il file dichiara, e quello che il file dichiara batte quello che si
    vede.
    """
    nomi = set(livelli(pdf)) & NOMI
    if not nomi:
        if riquadro:
            return _a_occhio(pdf, scala, page_no, note, riquadro)
        return render_page(pdf, page_no, scala)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    try:
        spenti = spegni(pdf, tmp.name, nomi)
        if not spenti:
            return render_page(pdf, page_no, scala)

        a2 = _rgba(pdf, page_no, MISURA)
        b2 = _rgba(tmp.name, page_no, MISURA)
        imp = _impronta(a2, b2)
        if imp is None:
            return render_page(pdf, page_no, scala)
        _m2, (mx0, mx1, my0, my1) = imp
        larg = (mx1 - mx0) / MISURA * PT2MM
        alt = (my1 - my0) / MISURA * PT2MM
        riq = (mx0 / MISURA, mx1 / MISURA, my0 / MISURA, my1 / MISURA)

        # l'impronta alla risoluzione della texture
        k = scala / MISURA
        ba = _rgba(pdf, page_no, scala, riq)
        bb = _rgba(tmp.name, page_no, scala, riq)
        imp = _impronta(ba, bb)
        if imp is None:
            return render_page(pdf, page_no, scala)
        maschera, _r = imp
        bx0 = max(int(round(mx0 * k)), 0)
        by0 = max(int(round(my0 * k)), 0)

        # --- 1. l'inchiostro del file ------------------------------------ #
        #
        # Quanto pesa la sovrastampa lo dicono DUE rese di Ghostscript, una
        # con e una senza, confrontate dentro l'impronta. Confrontare invece
        # Ghostscript con pdfium direbbe un'altra cosa: quei due rasterizzano
        # diverso comunque - bordi, antialiasing - e il 6% di scarto che ne
        # esce non distingue una sovrastampa che conta da due motori che non
        # si somigliano.
        q = quadricromia(pdf, page_no, scala, riq)
        if q is not None:
            piatta = quadricromia(pdf, page_no, scala, riq, "disable")
            peso, quante = _peso_sovrastampa(q, piatta, maschera)
            if peso >= CAMBIO_MINIMO:
                fuori = render_page(pdf, page_no, scala).convert("RGB")
                _incolla(fuori, q, maschera, bx0, by0)
                if note is not None:
                    note.append(
                        "colata dal livello '%s' resa in quadricromia: %.1f x "
                        "%.1f mm, e la sovrastampa rimette l'ombra al %.0f%% "
                        "delle zone che uscivano azzurre"
                        % (spenti[0], larg, alt, 100 * peso))
                return fuori
            if note is not None:
                note.append(
                    "colata dal livello '%s': l'ombra e' FUSTELLATA, non in "
                    "sovrastampa - delle %d zone azzurre la quadricromia ne "
                    "recupera solo il %.1f%%, perche' sotto il fondo non c'e' "
                    "da moltiplicare" % (spenti[0], quante, 100 * peso))

        # --- 2. ripiego: la risorsa -------------------------------------- #
        if not os.path.exists(RISORSA):
            return render_page(pdf, page_no, scala)
        ris = Image.open(RISORSA).convert("RGB")
        banda = _su_bianco(a2[my0:my1, mx0:mx1])
        acc = allinea(banda, np.asarray(ris))
        if acc is None:
            return render_page(pdf, page_no, scala)
        s, dx, dy, err = acc
        pr = _periodo(_curva(np.asarray(ris)))
        if pr:
            dx = _fase(banda, np.asarray(ris), s, dx, dy, pr)
        err_mm = err / MISURA * PT2MM
        if err_mm > ERRORE_MAX_MM:
            if note is not None:
                note.append("colata: la risorsa non combacia col disegno del "
                            "file (errore %.2f mm), lasciata com'e'" % err_mm)
            return render_page(pdf, page_no, scala)

        base = render_page(tmp.name, page_no, scala).convert("RGB")
        h = min(maschera.shape[0], base.height - by0)
        w = min(maschera.shape[1], base.width - bx0)
        if h <= 0 or w <= 0:
            return base
        nw = max(1, int(round(ris.width * s * k)))
        nh = max(1, int(round(ris.height * s * k)))
        r = np.asarray(ris.resize((nw, nh), Image.LANCZOS))
        tela = np.full((h, w, 3), 255, np.uint8)
        rx, ry = int(round(dx * k)), int(round(dy * k))
        x0, y0 = max(rx, 0), max(ry, 0)
        x1, y1 = min(rx + nw, w), min(ry + nh, h)
        if x1 <= x0 or y1 <= y0:
            return base
        tela[y0:y1, x0:x1] = r[y0 - ry:y1 - ry, x0 - rx:x1 - rx]
        _incolla(base, tela, maschera, bx0, by0)
        if note is not None:
            note.append("colata sostituita con la risorsa: %.1f x %.1f mm, "
                        "allineata a %.2f mm" % (larg, alt, err_mm))
        return base
    except Exception as e:
        if note is not None:
            note.append("colata: non riuscita (%s), lasciata com'e'"
                        % str(e)[:60])
        return render_page(pdf, page_no, scala)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
