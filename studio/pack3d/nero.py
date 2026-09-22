"""
La `k` di `kinder` e' nera, e il rasterizzatore la fa azzurra.

Il marchio e' un'invariante che si controlla a occhio in un secondo: la `k`
e' **nera** e `inder` e' **arancio Kinder**. Sul K Brioss STD la `k` uscliva
azzurra, e non per un errore del file: nelle sue separazioni la `k` e' nero
al 100%, ma e' nero **in sovrastampa** sopra l'azzurro, e pdfium la
sovrastampa la ignora - misurato, vedi `REGOLE.md`.

La strada larga non funziona. Rendere tutto il foglio con Ghostscript e
`-sOverprint=simulate` la `k` la fa nera, ma su KP T1 Mandarino **cancella il
logo `kinder Pingui` e la scritta `MANDARINE`, e fa azzurra la fascia rossa**:
quel file ha solo tinte piatte, e gs le compone male. Il 16% della pagina
cambia, e cambia in peggio. Quindi niente interruttore globale.

La strada che funziona e' locale e non indovina niente: **la lastra del nero
dice dov'e' nero**. Dove la lastra e' piena e il render mette invece un
colore chiaro e saturo, il render ha torto e si riporta il nero. Non si
inventa inchiostro: si mette quello che il file dichiara, e solo li'.

    K Brioss STD     nero pieno su 18.839 px, il render ne tradisce il 6,8%
    Brioss astuccio                                                   2,3%
    Colazione                                                         0,8%
    Pingui T6                                                         0,7%
    KP T1 Mandarino                                                   0,0%

Sul Brioss STD la zona tradita piu' grande e' proprio la `k`, 3.764 px su
4.938: il difetto e' quello, non un'inezia sparsa.

Niente prefiltro sul flag di sovrastampa, e non per dimenticanza: **tutti e
otto i file del parco la sovrastampa la dichiarano**. Guardare `/OP` non
scarta nessuno, quindi il costo e' la passata spia e basta.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from . import techink

# quota d'inchiostro oltre la quale la lastra dice "qui e' nero"
SOLIDO = 0.85
# luminosita' sopra la quale il render non sta facendo il nero
CHIARO = 120
# croma sopra la quale il render ci ha messo un colore, non un grigio
SATURO = 40
# Sotto questa quota il difetto non c'e' e non si paga la passata alla
# risoluzione della texture. Cinque per cento perche' sotto sono i bordi:
# l'antialiasing del rasterizzatore sfuma la lettera e quei pixel di frangia
# risultano "traditi" senza che ci sia niente da riparare. Sul parco, quota
# misurata e quanto poi cambia davvero dentro i pannelli:
#
#     K Brioss STD     10,1%  ->  cambia lo 0,14%, ed e' la `k`
#     Brioss astuccio   8,8%  ->  cambia lo 0,026%, gia' nera in partenza
#     Colazione         3,4%  ->  cambia lo 0,001%: 18 pixel. Sotto soglia
#     FERRERO 159013    1,8%  ->  GLB identico. Sotto soglia
#
# Sopra il cinque per cento non e' detto che serva, sotto e' detto che non
# serve: e la passata sprecata su FERRERO 159013 erano quasi sei secondi.
QUOTA_MINIMA = 0.05
# la lastra si prende a questa risoluzione e si ingrandisce: una `k` e' una
# lettera grande, e prenderla a 300 dpi costerebbe secondi per nulla
DPI_LASTRA = 144.0
DPI_SPIA = 36.0


def _lastra(pdf, page_no, dpi):
    """La mappa d'inchiostro della lastra del nero, o None.

    Si chiede **solo** quella: un foglio ha una dozzina di lastre e tenerle
    tutte per buttarne undici, su un container da 512 MB, e' il genere di
    spreco che fa fallire un build.
    """
    try:
        mappe = techink.mappe_lastre(pdf, page_no, dpi, processo=True,
                                     solo="black")
    except Exception:
        return None
    return mappe.get("black")


def _traditi(lastra, reso):
    """Maschera dei pixel che la lastra dice neri e il render fa colorati."""
    h = min(lastra.shape[0], reso.shape[0])
    w = min(lastra.shape[1], reso.shape[1])
    if h == 0 or w == 0:
        return None, 0.0
    inchiostro = (255 - lastra[:h, :w].astype(np.int16)) / 255.0
    pieno = inchiostro >= SOLIDO
    if not pieno.any():
        return None, 0.0
    px = reso[:h, :w].astype(np.int16)
    chiaro = px.mean(2) > CHIARO
    saturo = (px.max(2) - px.min(2)) > SATURO
    tradito = pieno & chiaro & saturo
    return tradito, float(tradito.sum()) / float(pieno.sum())


def spia(pdf, page_no=0, scala=None):
    """Decide TUTTO prima che il foglio grande esista. `(lastra, quota)`.

    Il momento conta piu' del metodo. Ghostscript lo si lancia con un `fork`,
    e il figlio parte ereditando lo spazio di indirizzi del padre: se il padre
    in quel momento tiene un foglio da 25 megapixel, quella memoria viene
    contata due volte finche' il figlio non la rilascia. Misurato sul Pingui
    T6: forkando a foglio pieno il conto e' 362 + 362 MB, forkando prima
    362 + 105. Su un container da 512 e' la differenza fra un modello e un
    `Failed to fetch`, che e' come si vede un processo ucciso dall'OOM.

    Quindi qui si fa tutto: la lastra spia, un render **piccolo** della pagina
    per il confronto - pdfium a 36 dpi, meno di un megabyte - e, se il difetto
    supera la soglia, anche la lastra alla risoluzione buona. Chi chiama si
    porta dietro un array da pochi MB e non fa piu' partire nessun processo.

    Torna `(None, 0.0)` quando non c'e' niente da riparare.
    """
    bassa = _lastra(pdf, page_no, DPI_SPIA)
    if bassa is None:
        return None, 0.0
    try:
        from .dieline import render_page, scarta_resa
        pagina = render_page(pdf, page_no, DPI_SPIA / 72.0).convert("RGB")
        piccolo = np.asarray(pagina.resize((bassa.shape[1], bassa.shape[0]),
                                           Image.BILINEAR))
        scarta_resa()
        _m, quota = _traditi(bassa, piccolo)
    except Exception:
        return None, 0.0
    if quota < QUOTA_MINIMA:
        return None, quota
    alta = _lastra(pdf, page_no,
                   DPI_LASTRA if scala is None else min(DPI_LASTRA, scala * 72.0))
    return alta, quota


def riporta(pdf, foglio, scala, page_no=0, note=None, deciso=None):
    """Rimette il nero dove la lastra dice nero e il render ha messo un colore.

    `foglio` e' quello che esce dal rasterizzatore, immagine o array; torna
    sempre un'immagine PIL, cosi' chi chiama non deve saperlo.

    Due passate, come per le aree riservate: una spia a bassa risoluzione che
    costa poco e dice se il difetto c'e', e solo allora la lastra alla
    risoluzione che serve. Un file senza lastra del nero, o senza difetto, non
    paga la seconda.

    `deciso` e' quello che ha restituito `spia`: la lastra buona e la quota.
    Se non c'e' la si chiede qui, ma il posto giusto per chiederla e' prima -
    vedi `spia` per il perche', che e' misurato in megabyte.

    **Non si tocca mai il foglio grande se non serve.** Sta sui 25 megapixel:
    ogni copia sono 76 MB, e la prima versione ne faceva tre solo per
    rimpicciolirlo. Adesso rimpicciolisce PIL, che alloca solo la
    destinazione, e l'array grande si materializza solo quando c'e' davvero
    da riparare.
    """
    img = foglio if hasattr(foglio, "convert") else Image.fromarray(
        np.asarray(foglio).astype(np.uint8))
    try:
        img = img.convert("RGB")
        alta, quota = deciso if deciso is not None else spia(pdf, page_no, scala)
        if alta is None:
            return img
        grande = np.asarray(Image.fromarray(alta).resize(
            (img.width, img.height), Image.BILINEAR))
        del alta
        arr = np.array(img, dtype=np.uint8)      # qui, e solo qui, la copia
        tradito, _q = _traditi(grande, arr)
        if tradito is None or not tradito.any():
            return img
        h, w = tradito.shape
        # il tono e' quello della lastra: pieno vuol dire nero, e i bordi
        # sfumati restano come li ha disegnati il rasterizzatore
        arr[:h, :w][tradito] = grande[:h, :w][tradito][:, None]
        if note is not None:
            note.append("nero riportato dalla lastra sul %.1f%% dei pixel che "
                        "il file dichiara neri: il rasterizzatore ignora la "
                        "sovrastampa e li faceva colorati" % (100 * quota))
        return Image.fromarray(arr)
    except Exception:
        # meglio la `k` azzurra che nessun modello
        return img
