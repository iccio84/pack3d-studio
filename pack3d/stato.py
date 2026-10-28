"""
Un lavoro, una cartella e uno stato.

Un'analisi o una costruzione crea file temporanei - le copie a pagina unica e
girate, quella senza le lastre tecniche, quella coi livelli spenti, le rese di
Ghostscript - e i moduli tengono in cassa quello che ne ricavano. I file
finivano nella cartella temporanea del sistema e nessuno li cancellava: con le
prove di due settimane erano 2639 PDF, 18 GB, finche' il disco si e' riempito
e le costruzioni rispondevano 500. E le casse passavano da un lavoro
all'altro: una costruzione chiesta dopo l'analisi dello stesso PDF trovava la
resa lasciata dall'analisi, e un lavoratore che vive a lungo si teneva
un'immagine per ogni astuccio costruito.

Ora ogni lavoro - /api/analyze, /api/analyze-ai, /api/build - ha la sua
cartella (`cartella`), dove vanno i suoi file temporanei, e le casse che
valgono per un lavoro solo (`per_lavoro`) partono vuote e si vuotano alla
fine, quando la cartella si butta (`lavoro`). Restano da un lavoro all'altro
solo le casse con la chiave sul CONTENUTO del file e un valore che non
dipende da chi l'ha chiesto prima: i tratti della pagina (`dieline.tratti`),
le analisi del flowpack, i versi gia' decisi.

Un processo fa un lavoro alla volta: in un lavoratore e' gia' cosi', e nel
processo del server (`PACK3D_LAVORATORI=0`) il secondo aspetta il primo. Lo
chiede pdfium, che non si chiama da due thread, e lo chiedono le casse: due
lavori insieme si vuoterebbero le casse a vicenda.
"""
from __future__ import annotations

import shutil
import tempfile
import threading
from contextlib import contextmanager

_uno_alla_volta = threading.RLock()
_qui = threading.local()
_casse = []


def per_lavoro(cassa):
    """Registra una cassa - un dict, un OrderedDict, una lista - che vale per
    un lavoro solo: si vuota all'inizio e alla fine di ogni lavoro. Torna la
    cassa, per scriverla dove la si dichiara."""
    _casse.append(cassa)
    return cassa


def cartella():
    """La cartella dei file temporanei del lavoro in corso, o None fuori da un
    lavoro (allora vale quella del sistema). Va passata come `dir=` a ogni
    file o cartella temporanea che il lavoro crea."""
    return getattr(_qui, "cartella", None)


def dimentica():
    for cassa in _casse:
        cassa.clear()


@contextmanager
def lavoro():
    """Un lavoro: la sua cartella e le casse vuote. Dentro un altro lavoro non
    ne apre un secondo."""
    if cartella() is not None:
        yield cartella()
        return
    with _uno_alla_volta:
        dimentica()
        _qui.cartella = tempfile.mkdtemp(prefix="lavoro_")
        try:
            yield _qui.cartella
        finally:
            c, _qui.cartella = _qui.cartella, None
            dimentica()
            shutil.rmtree(c, ignore_errors=True)

