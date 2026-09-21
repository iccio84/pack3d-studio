"""
La colata Kinder: toglierla dall'artwork e rimetterla fatta bene.

Perche' serve: la colata e' costruita in SOVRASTAMPA - una lastra che
moltiplica il fondo, e da quella moltiplicazione vengono l'ombra sulle gocce e
il volume del getto. Quando arriva in RGB la sovrastampa non esiste, non c'e'
niente da simulare, e quello che esce e' una macchia piatta con l'onda
circondata da un alone azzurro sfumato invece che da un'ombra. A valle non si
aggiusta: reinventare l'ombra vorrebbe dire dipingere colore che nel file non
c'e'. Si sostituisce, con la colata gia' resa come deve venire.

Perche' si puo' fare in modo preciso: solo se la colata sta su un **livello
suo**. Allora il livello dice dove va, e non si indovina niente. Il file che ha
aperto la strada e' `KP_T1_Mandarino`, che ha un OCG chiamato `Colata`.

I tre passi, tutti misurati:

1. **dove.** Si spegne il livello in una copia, aggiungendo il suo OCG a
   `/OCProperties/D/OFF`. E' una modifica di DIZIONARIO: non costa la passata
   di pypdf sul flusso di contenuto, che su Colazione vale 7 secondi e 100 MB.
   La differenza fra le due rese da' l'impronta esatta del livello.
2. **quanto e in che punto.** La risorsa e' un master, non il ritaglio di un
   pack: la sua onda va portata al PASSO di quella dell'artwork. La scala
   esce dal rapporto fra i due periodi, presi dallo spettro; la fase da una
   correlazione fra le due curve rosso/bianco; la quota dalla mediana della
   differenza. Su KP T1 Mandarino l'errore mediano e' 0,1 mm su 1351 colonne,
   e la goccia - che nell'allineamento non entra - cade al suo posto: e' la
   verifica che il disegno e' lo stesso.
3. **come.** La risorsa si incolla dentro l'IMPRONTA del livello vecchio, e
   solo li'. Cosi' quello che nell'artwork sta sopra la colata - un bicchiere,
   uno spicchio, la fascia di fondo - resta dov'e' senza dover sapere in che
   ordine sono i livelli.
"""
from __future__ import annotations

import os
import tempfile

import numpy as np
from PIL import Image

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

    `PdfWriter().append()` PERDE `/OCProperties`, e senza quello non c'e'
    niente da spegnere: si clona.
    """
    import pypdf
    from pypdf.generic import ArrayObject, NameObject
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


def foglio(pdf, scala, page_no=0, note=None):
    """Il foglio reso, con la colata sostituita se si puo'.

    Se il file non ha il livello, o la risorsa non e' quel disegno, torna la
    resa normale: non si consegna una colata messa a caso. E il file che il
    livello non ce l'ha non paga niente - una lettura dei dizionari e via.
    """
    nomi = set(livelli(pdf)) & NOMI
    if not nomi or not os.path.exists(RISORSA):
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

        ris = Image.open(RISORSA).convert("RGB")
        acc = allinea(_su_bianco(a2[my0:my1, mx0:mx1]), np.asarray(ris))
        if acc is None:
            return render_page(pdf, page_no, scala)
        s, dx, dy, err = acc
        banda = _su_bianco(a2[my0:my1, mx0:mx1])
        pr = _periodo(_curva(np.asarray(ris)))
        if pr:
            dx = _fase(banda, np.asarray(ris), s, dx, dy, pr)
        err_mm = err / MISURA * PT2MM
        if err_mm > ERRORE_MAX_MM:
            if note is not None:
                note.append("colata: la risorsa non combacia col disegno del "
                            "file (errore %.2f mm), lasciata com'e'" % err_mm)
            return render_page(pdf, page_no, scala)

        base = np.asarray(render_page(tmp.name, page_no, scala).convert("RGB"))
        k = scala / MISURA
        # la banda alla risoluzione della texture, in pixel del foglio
        bx0, bx1 = int(round(mx0 * k)), int(round(mx1 * k))
        by0, by1 = int(round(my0 * k)), int(round(my1 * k))
        bx0, by0 = max(bx0, 0), max(by0, 0)
        bx1, by1 = min(bx1, base.shape[1]), min(by1, base.shape[0])
        if bx1 <= bx0 or by1 <= by0:
            return Image.fromarray(base)
        riq = (mx0 / MISURA, mx1 / MISURA, my0 / MISURA, my1 / MISURA)
        ba = _rgba(pdf, page_no, scala, riq)
        bb = _rgba(tmp.name, page_no, scala, riq)
        h = min(ba.shape[0], bb.shape[0], base.shape[0] - by0)
        w = min(ba.shape[1], bb.shape[1], base.shape[1] - bx0)
        imp = _impronta(ba[:h, :w], bb[:h, :w])
        if imp is None:
            return Image.fromarray(base)
        maschera, _riq = imp

        nw = max(1, int(round(ris.width * s * k)))
        nh = max(1, int(round(ris.height * s * k)))
        r = np.asarray(ris.resize((nw, nh), Image.LANCZOS))
        tela = np.full((h, w, 3), 255, np.uint8)
        rx, ry = int(round(dx * k)), int(round(dy * k))
        x0, y0 = max(rx, 0), max(ry, 0)
        x1, y1 = min(rx + nw, w), min(ry + nh, h)
        if x1 <= x0 or y1 <= y0:
            return Image.fromarray(base)
        tela[y0:y1, x0:x1] = r[y0 - ry:y1 - ry, x0 - rx:x1 - rx]

        fuori = base.copy()
        pezzo = fuori[by0:by0 + h, bx0:bx0 + w]
        pezzo[maschera] = tela[maschera]
        fuori[by0:by0 + h, bx0:bx0 + w] = pezzo
        if note is not None:
            note.append("colata sostituita dal livello '%s': %.1f x %.1f mm, "
                        "allineata a %.2f mm"
                        % (spenti[0], (mx1 - mx0) / MISURA * PT2MM,
                           (my1 - my0) / MISURA * PT2MM, err_mm))
        return Image.fromarray(fuori)
    except Exception as e:
        if note is not None:
            note.append("colata: sostituzione non riuscita (%s), lasciata "
                        "com'e'" % str(e)[:60])
        return render_page(pdf, page_no, scala)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
