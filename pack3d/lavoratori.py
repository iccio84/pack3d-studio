"""
I lavoratori: le analisi e le costruzioni in processi a parte, con una fila.

pdfium non si chiama da due thread, nemmeno su documenti diversi: due
costruzioni insieme nello stesso processo lo facevano morire tutto intero, e
lo Space ne faceva una alla volta - la seconda persona riceveva «Server
occupato» (REGOLE.md, *pdfium non si chiama da due thread*). Per farne due
davvero servono due processi. Lo Space tiene `LAVORATORI` processi Python che
hanno caricato `server.py`, e ognuno fa un lavoro alla volta, dall'inizio
alla fine: la stessa richiesta di prima - /api/analyze, /api/build,
/api/segnala - col codice di prima (`server.esegui_lavoro`).

Il processo del server tiene le connessioni e quello che deve restare suo:
i casi in attesa della conferma di chi li ha caricati (`coda.metti`), che un
lavoratore rimanda indietro invece di tenerli, e le letture del PDF che la
pagina chiede dopo il modello (`server.LETTURE`). Chi arriva coi lavoratori
tutti occupati entra in fila, invece del «Server occupato», e la pagina sa
quanti lavori ha davanti (`posizione`).

- Un lavoratore che cade - un int3 dentro pdfium - si porta via solo il suo
  lavoro: chi l'aveva chiesto riceve un errore che lo dice (`Caduto`), e il
  lavoratore riparte. Prima cadeva il server, con tutti quelli collegati.
- Lo stesso PDF va, se e' libero, al lavoratore che l'ha gia' letto: l'analisi
  di un flowpack si fa una volta per processo (`famiglie.flowpack.analisi_flowpack`), e
  la pagina chiede /api/analyze e subito dopo /api/build con lo stesso corpo.
- La fila ha un limite (`FILA_MAX`) e un'attesa massima (`ATTESA_MAX`):
  oltre, si risponde «occupato» come prima (`Occupato`).
- Un lavoro che non finisce in `LAVORO_MAX` secondi si ferma, e il lavoratore
  riparte.
- Una costruzione col controllo dell'AI manda il modello prima di finire
  (`anticipo`): parte subito verso chi l'ha chiesto, e il lavoratore resta
  occupato col verdetto, che torna al processo del server alla fine.
- `PACK3D_LAVORATORI=0`: niente lavoratori, tutto nel processo del server e
  una costruzione alla volta, come prima.

I processi partono con `spawn`, non con `fork`: un lavoratore che riparte
dopo una caduta nasce mentre il server ha gia' i suoi thread, e un `fork` a
quel punto si porta dietro i lucchetti presi da loro.
"""
from __future__ import annotations

import multiprocessing
import os
import sys
import threading
import time
import traceback
from collections import OrderedDict, deque
from contextlib import contextmanager

# Quanti: un numero, o `auto` (di serie) per contarli dal container - una
# vCPU ciascuno, e non piu' di quanti ne stanno nella memoria (`quanti`).
LAVORATORI = os.environ.get("PACK3D_LAVORATORI", "auto")
# il picco peggiore di una costruzione e' 1,2 GB; il resto e' margine
MEMORIA_LAVORATORE = 1.5 * 1024 ** 3
# il processo del server, con le connessioni e i casi in attesa
MEMORIA_SERVER = 1.0 * 1024 ** 3
LAVORATORI_MAX = 8
FILA_MAX = int(os.environ.get("PACK3D_FILA_MAX", "12"))
ATTESA_MAX = float(os.environ.get("PACK3D_ATTESA_MAX", "600"))
LAVORO_MAX = float(os.environ.get("PACK3D_LAVORO_MAX", "1200"))
# quante impronte di PDF ricordare per mandarle al lavoratore che le ha lette
AFFINITA_MAX = 64


class Occupato(Exception):
    """La fila e' piena, o l'attesa e' stata troppo lunga."""


class Caduto(Exception):
    """Il lavoratore e' morto durante il lavoro, o non ha finito in tempo."""


class _Lavoratore:
    def __init__(self, k):
        self.k = k
        self.occupato = False
        self._avvia()

    def _avvia(self):
        ctx = multiprocessing.get_context("spawn")
        self.conn, figlio = ctx.Pipe()
        self.proc = ctx.Process(target=_ciclo, args=(figlio,), daemon=True,
                                name="lavoratore-%d" % self.k)
        self.proc.start()
        figlio.close()

    def esegui(self, lavoro, durata, anticipo=None):
        fine = time.time() + durata
        try:
            self.conn.send(lavoro)
            while True:
                # poll torna True anche quando il processo e' morto: recv lo dice
                if not self.conn.poll(max(0.0, fine - time.time())):
                    self._riavvia("non ha finito in %d s" % durata)
                    raise Caduto("non ha finito in %d s" % durata)
                m = self.conn.recv()
                if m.get("tipo") != "anticipo":
                    return m
                # il modello prima del verdetto: parte subito, e il lavoro
                # va avanti
                if anticipo is not None:
                    anticipo(m)
        except (EOFError, OSError, BrokenPipeError):
            self.proc.join(5)
            perche = "uscito con %s" % self.proc.exitcode
            self._riavvia(perche)
            raise Caduto(perche) from None

    def _riavvia(self, perche):
        print("lavoratore %d (pid %s) %s: lo riavvio" % (self.k, self.proc.pid, perche),
              file=sys.stderr)
        if self.proc.is_alive():
            self.proc.kill()
            self.proc.join(5)
        try:
            self.conn.close()
        except OSError:
            pass
        self._avvia()


_fila_cv = threading.Condition()
_lavoratori = []
_fila = deque()                 # i lavori in attesa, in ordine d'arrivo
_affinita = OrderedDict()       # impronta del corpo -> lavoratore che l'ha letto
_chi = {}                       # id della pagina -> il suo lavoro, per `posizione`


def _leggi(percorso):
    try:
        with open(percorso) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _cpu():
    """Le vCPU che il container puo' usare: il tetto del cgroup, che e' quello
    che lo Space vende. Non `os.cpu_count()`, che in un container dice i
    processori della macchina, non i suoi. None se il tetto non c'e'."""
    v2 = _leggi("/sys/fs/cgroup/cpu.max")
    if v2:
        quota, periodo = (v2.split() + ["100000"])[:2]
        if quota != "max":
            return int(quota) / int(periodo)
    quota = _leggi("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    periodo = _leggi("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota and periodo and int(quota) > 0:
        return int(quota) / int(periodo)
    return None


def _memoria():
    """I byte che il container puo' usare: il tetto del cgroup, o se non c'e'
    la memoria della macchina."""
    for f in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        v = _leggi(f)
        # senza tetto il v1 scrive un numero enorme, il v2 "max"
        if v and v.isdigit() and int(v) < 1 << 60:
            return int(v)
    for riga in (_leggi("/proc/meminfo") or "").splitlines():
        if riga.startswith("MemTotal:"):
            return int(riga.split()[1]) * 1024
    return None


def quanti():
    """(quanti lavoratori, la macchina come la vede il container). Con `auto`
    uno per vCPU, non piu' di quanti ne stanno nella memoria, al massimo
    `LAVORATORI_MAX`; un container senza tetto di CPU ne prende due, quelli
    dello Space gratuito, come prima."""
    cpu, mem = _cpu(), _memoria()
    macchina = {"vcpu": cpu, "memoria_gb": round(mem / 1024 ** 3, 1) if mem else None}
    if LAVORATORI != "auto":
        return int(LAVORATORI), dict(macchina, da="PACK3D_LAVORATORI")
    n = max(1, int(cpu + 0.01)) if cpu else 2
    if mem:
        n = min(n, max(1, int((mem - MEMORIA_SERVER) // MEMORIA_LAVORATORE)))
    return min(n, LAVORATORI_MAX), dict(macchina, da="auto")


_macchina = {}


def avvia(n=None):
    """Fa partire i lavoratori. Nel processo del server, prima di servire."""
    if n is None:
        n, m = quanti()
        _macchina.update(m)
    with _fila_cv:
        for k in range(len(_lavoratori), n):
            _lavoratori.append(_Lavoratore(k))
    if n:
        print("lavoratori: %d processi, fila di %d al massimo (%s)"
              % (n, FILA_MAX, ", ".join("%s %s" % kv for kv in _macchina.items())),
              file=sys.stderr)


def attivi():
    return bool(_lavoratori)


def esegui(lavoro, impronta=None, chi=None, anticipo=None):
    """Il lavoro su un lavoratore libero, aspettando in fila se non ce n'e'.
    Torna quello che il lavoratore restituisce; Occupato o Caduto. Se il
    lavoratore manda una risposta prima di finire - il modello prima del
    verdetto del controllo - va ad `anticipo`, e il lavoratore resta occupato
    fino alla fine."""
    voce = {"impronta": impronta, "w": None, "dal": time.time()}
    with _fila_cv:
        if len(_fila) >= FILA_MAX:
            raise Occupato("%d lavori gia' in fila" % len(_fila))
        _fila.append(voce)
        if chi:
            _chi[chi] = voce
        try:
            while True:
                w = _scegli(voce)
                if w is not None:
                    break
                resta = ATTESA_MAX - (time.time() - voce["dal"])
                if resta <= 0:
                    raise Occupato("in fila da %d s" % ATTESA_MAX)
                _fila_cv.wait(resta)
        except BaseException:
            _fila.remove(voce)
            _chi.pop(chi, None)
            _fila_cv.notify_all()
            raise
        _fila.remove(voce)
        w.occupato = True
        voce["w"] = w
        # il prossimo della fila puo' avere un altro lavoratore libero
        _fila_cv.notify_all()
    try:
        return w.esegui(lavoro, LAVORO_MAX, anticipo)
    finally:
        with _fila_cv:
            w.occupato = False
            if impronta:
                _affinita[impronta] = w.k
                _affinita.move_to_end(impronta)
                while len(_affinita) > AFFINITA_MAX:
                    _affinita.popitem(last=False)
            _chi.pop(chi, None)
            _fila_cv.notify_all()


def _scegli(voce):
    """Il lavoratore per `voce`, se tocca a lei e ce n'e' uno libero: quello
    che ha gia' letto lo stesso PDF, se e' libero, se no il primo libero."""
    if not _fila or _fila[0] is not voce:
        return None
    liberi = [w for w in _lavoratori if not w.occupato]
    if not liberi:
        return None
    k = _affinita.get(voce["impronta"])
    return next((w for w in liberi if w.k == k), liberi[0])


def posizione(chi):
    """Per la pagina che aspetta: 0 se il suo lavoro e' gia' su un
    lavoratore, n se e' l'n-esimo della fila (1: il prossimo), None se non
    c'e'."""
    with _fila_cv:
        v = _chi.get(chi)
        if v is None:
            return None
        if v["w"] is not None:
            return 0
        return list(_fila).index(v) + 1


def stato():
    with _fila_cv:
        return {"lavoratori": len(_lavoratori),
                "occupati": sum(1 for w in _lavoratori if w.occupato),
                "in_fila": len(_fila),
                "macchina": dict(_macchina)}


# ---------------------------------------------------------------------------
# Nel lavoratore.

def _ciclo(conn):
    """Il lavoratore: aspetta un lavoro, lo fa, rimanda l'esito; per sempre.

    Con `spawn` il figlio carica come `__mp_main__` lo script che il padre
    ha lanciato: se e' server.py, e' gia' li', e non si carica una seconda
    volta."""
    srv = sys.modules.get("__mp_main__")
    if not hasattr(srv, "esegui_lavoro"):
        import server as srv
    while True:
        try:
            lavoro = conn.recv()
        except (EOFError, OSError):
            return
        try:
            esito = srv.esegui_lavoro(
                lavoro, lambda pacco: conn.send(dict(pacco, tipo="anticipo")))
        except BaseException as e:              # noqa: BLE001
            traceback.print_exc()
            esito = {"risposta": {"code": 500, "body": ("%s: %s" % (type(e).__name__, e)).encode(),
                                  "ctype": "text/plain; charset=utf-8"},
                     "casi": []}
        conn.send(esito)


@contextmanager
def casi_rimandati(coda, casi):
    """Nel lavoratore, `coda.metti` non tiene il caso: lo scrive in `casi`,
    perche' il processo del server lo rimetta col suo `coda.metti` - e' li'
    che chi l'ha caricato lo conferma. `coda.in_attesa` dice di si' ai casi
    messi cosi', se la coda c'e' (`coda.pronta`, chiesta solo quando serve)."""
    vera_metti, vera_attesa = coda.metti, coda.in_attesa
    messi = set()

    def metti(blocchi, nomi, verdetto, *a, **k):
        cod = coda.codice(blocchi)
        casi.append(((list(blocchi), list(nomi), dict(verdetto)) + tuple(a), dict(k)))
        if not k.get("subito"):
            messi.add(cod)
        return cod, bool(k.get("subito")) and coda.pronta()

    def in_attesa(cod):
        return cod in messi and coda.pronta()

    coda.metti, coda.in_attesa = metti, in_attesa
    try:
        yield
    finally:
        coda.metti, coda.in_attesa = vera_metti, vera_attesa
