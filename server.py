#!/usr/bin/env python3
"""
Backend locale di pack3d studio.

    python server.py            # poi apri http://localhost:8000

Solo libreria standard: serve l'interfaccia e due endpoint che girano la
pipeline `pack3d`. Il PDF arriva come corpo binario grezzo, non come
multipart: dentro un iframe la fetch viene inoltrata con postMessage e una
FormData non e' clonabile, mentre un ArrayBuffer lo e'.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import sys
from urllib.parse import quote, unquote
import tempfile
import time
import traceback
import threading
from types import SimpleNamespace
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)      # il pacchetto pack3d/ sta accanto a questo file

try:
    import numpy as np
    from PIL import Image
except ImportError as e:                       # messaggio utile, non uno stack trace
    sys.exit("Manca una libreria (%s).\n"
             "Installa con:  pip install -r requirements.txt" % e.name)

from pack3d import coda, controllo, gelato, strati, verifica, versione
from pack3d import lettura as lettura_pdf
from pack3d import lavoratori
from pack3d import stato
from pack3d import template as il_template
# La risoluzione della texture per qualita' - HD di serie, per tutte le
# famiglie - sta in `pack3d.artwork`, perche' la applichi anche la riga di
# comando: finche' stava qui, gli astucci fatti da li' uscivano a 2048 px.
from pack3d.artwork import qualita
# le famiglie: come si riconoscono e come si costruiscono
from pack3d.famiglie.comune import KIND_NOTI, dichiarazione, normalizza_kind
from pack3d.famiglie.flowpack import (
    CASI,
    _sig,
    aree_da_agente,
    colata_da_agente,
    livello_da_agente,
    materiali_dichiarati,
    pinne_da_agente,
    scatola_da_agente)
from pack3d.famiglie.astuccio import (
    APERTA,
    CHIUSURA,
    INCISA,
    apertura_gradi,
    incisioni_scelte,
    pellicola_scelta,
    spessore_carta)
from pack3d.famiglie.coppa import analisi_coppa, in_piu_pezzi
from pack3d.famiglie.tubo import GELATO
from pack3d.famiglie.incarto import analisi_incarto_dichiarato, chiusura_incarto
from pack3d.famiglie.riempimento import (
    analisi_riempimento,
    cu_riempimento,
    per_fila_scelti,
    quanti_pezzi)
from pack3d.famiglie.registro import COSTRUZIONI, _costruisci_flowpack, analyze_pdf


def nota_incisioni(meta):
    """La riga "da sapere" per il controllo, se il modello ha i solchi."""
    righe = [str(m) for m in meta or ()]
    quali = [q for q, c in (("dell'apertura a strappo", INCISA),
                            ("della linguetta di chiusura", CHIUSURA))
             if any(c in r for r in righe)]
    if not quali:
        return None
    return ("le righe sottili color cartone sulle facce sono i tagli %s, "
            "incisi nel cartone come solchi, come si vedono sulla scatola "
            "vera chiusa: non sono disegno tecnico rimasto stampato, e la "
            "grafica sotto e' intera." % " e ".join(quali))


def nota_riempimento(info, nomi):
    """La riga "da sapere" per il controllo di un riempimento: e' un
    RIEMPIMENTO, e quale PDF e' il contenitore e quale il pack."""
    def nome(k):
        return nomi[k] if isinstance(k, int) and 0 <= k < len(nomi) else None
    contenitore, pack = nome(info.get("vassoio")), nome(info.get("flowpack"))
    cosa = "un astuccio" if info.get("cu") == "carton" else "un flowpack"
    if contenitore and pack:
        return ("e' un RIEMPIMENTO: il PDF \"%s\" e' il contenitore, il PDF \"%s\" "
                "e' il pack, %s, di cui il contenitore e' pieno." % (contenitore, pack, cosa))
    return "e' un RIEMPIMENTO: un contenitore pieno di %s." % (
        "astucci" if info.get("cu") == "carton" else "flowpack")


def nota_gelato(meta):
    """La riga "da sapere" per il controllo, se il tubo ha il gelato."""
    riga = next((str(m) for m in meta or () if str(m).startswith(GELATO)), None)
    if riga is None:
        return None
    return ("il tubo e' mostrato col ghiacciolo che esce dalla bocca, come l'ha "
            "chiesto chi l'ha caricato (%s). Il ghiaccio colorato in cima non e' "
            "nel PDF e non e' un difetto: la grafica va confrontata sul tubo, "
            "sotto l'orlo." % riga)


def nota_materiali(meta):
    """La riga "da sapere" per il controllo, se il film ha i materiali dei DT."""
    righe = [str(m) for m in meta or () if str(m).startswith("materiali dai DT: ")
             and " - " in str(m) and "resta plastica" not in str(m)]
    if not righe:
        return None
    return ("il materiale del film viene dai DT secondari del file (%s). Dove il "
            "film e' alluminio senza white plate il modello e' METALLO, che "
            "rimanda l'ambiente: nelle viste e' un grigio con riflessi e bande, "
            "non il grigio piatto con cui il DT disegna l'alluminio, e gli "
            "inchiostri li' sono metallizzati. La vernice opaca e' resa satinata, "
            "piu' chiara del metallo lucido intorno. Non sono difetti: la grafica "
            "va confrontata col PDF, il materiale no." % righe[0].split(": ", 1)[1])


def nota_apertura(meta):
    """La riga "da sapere" per il controllo, se l'astuccio e' aperto."""
    riga = next((str(m) for m in meta or () if str(m).startswith(APERTA)), None)
    if riga is None:
        return None
    return ("l'astuccio e' mostrato APERTO, come l'ha chiesto chi l'ha "
            "caricato (%s). Le viste lo mostrano quindi sdraiato, con la "
            "finestra sollevata: nella vista 'fronte' si vede il rovescio non "
            "stampato della finestra, e il suo lato stampato si vede dal "
            "retro, con la grafica capovolta come sulla scatola vera. Dentro "
            "e' cartoncino non stampato, e la cornice chiara attorno al buco e "
            "sotto la finestra e' il cartoncino sfogliato dallo strappo. Non "
            "sono difetti: il modello va confrontato col PDF per la grafica "
            "di ogni faccia, non per la posa." % riga)


def _rss():
    """La memoria che il processo sta usando adesso, in MB. 0 se non si sa."""
    try:
        with open("/proc/self/statm") as fh:
            return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576.0
    except (OSError, IndexError, ValueError):
        return 0.0


def traccia(fase, da=None, dettaglio=""):
    """Una riga sul log: quanto e' durata la fase e a che memoria siamo.

    Serve quando la costruzione NON arriva in fondo. Se il processo muore -
    ucciso per memoria, o tagliato dalla piattaforma perche' ci mette troppo -
    la risposta non arriva e chi guarda vede un 502 senza niente dentro: non
    si sa nemmeno in quale pezzo e' morto. Le righe gia' stampate invece
    restano nel log del servizio, e dicono l'ultimo passo cominciato.

    E' la differenza che conta su un piano da 0,1 CPU, dove un file che qui
    costa 9 secondi di CPU la' ne prende 94 di orologio: senza traccia,
    memoria e tempo si distinguono solo a indovinare.

    Scrive su stderr perche' e' li' che finisce gia' `log_message`, e torna il
    tempo di adesso cosi' le fasi si incatenano senza contarlo due volte.
    """
    import resource
    ora = time.time()
    if da is not None:
        # DUE numeri, e servono tutti e due. `ru_maxrss` e' il massimo del
        # processo da quando e' partito e non scende mai: dopo tre costruzioni
        # dice 681 MB anche se nessuna singola ci e' arrivata vicino, quindi
        # da solo inganna. Quello che si sta usando ADESSO lo dice /proc, e in
        # coppia i due raccontano la cosa giusta: quanto pesa questa fase, e
        # quanto ha pesato il peggio fin qui.
        sys.stderr.write(
            "  [pack3d] %-22s %6.1f s  %5.0f MB ora, %5.0f max%s\n"
            % (fase, ora - da, _rss(),
               resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
               ("  " + dettaglio) if dettaglio else ""))
        sys.stderr.flush()
    return ora


def caso_fermo(e, kind, pdfs, nomi, opts, blocchi, info=None):
    """`(errore, verdetto)` di una lettura o di una costruzione che si e'
    fermata, col caso gia' messo in coda.

    Il codice non ha saputo leggerlo o costruirlo: e' un caso nuovo come un
    modello respinto, e senza modello il controllo dell'AI non ha niente da
    guardare. Prima finiva solo nel log, e nessuno lo riprendeva: va in coda
    coi PDF e l'errore, e la pagina lo dice. Vale per la lettura come per la
    costruzione, perche' la pagina chiede prima la lettura: un PDF che si
    ferma li' la costruzione non la vede mai.
    """
    traceback.print_exc()
    errore = "%s: %s" % (type(e).__name__, e)
    verdetto = dict(esito="errore", motivo=errore, difetti=[], pack_nel_pdf="",
                    modello="nessuno: la costruzione si e' fermata")
    ctx = dict(dichiarato=dichiarazione(kind, len(pdfs)),
               riconosciuto=(info.get("title") or info.get("kind")) if info else "-",
               avvisi=[errore], nomi=nomi,
               opzioni={k: opts[k] for k in OPZIONI_CASO if k in opts})
    verdetto["codice"], verdetto["in_coda"] = coda.metti(blocchi, nomi, verdetto,
                                                         None, ctx)
    verdetto["in_attesa"] = coda.in_attesa(verdetto["codice"])
    return errore, verdetto


# Le scelte dell'utente che cambiano il modello: vanno in coda col caso, e chi
# lo riprende lo ricostruisce con le stesse (vedi prove/parco.py e CODA.md).
# L'impronta dei file del codice in esecuzione, calcolata una volta all'avvio:
# la restituisce /api/ping (vedi pack3d/versione.py).
VERSIONE = versione.impronta(HERE)

OPZIONI_CASO = ("kind", "teeth", "soft", "pinne", "saldatura", "scatola",
                "pezzi", "spessore", "apertura", "pellicola", "quality", "materiali",
                "quanti", "per_fila", "incisioni", "cu", "gelato", "chiusura",
                "gonfio")


# l'immagine del prodotto da incartare: la pagina la rimpicciolisce a 1600 px
PRODOTTO_MAX = 12 * 1024 * 1024


def _separa_prodotto(data, opts):
    """`(corpo dei PDF, loro parti, immagine o None)`.

    L'immagine del prodotto da incartare arriva in coda al corpo, dopo i PDF:
    l'ultima delle `parti`, quando `opts["prodotto"]` c'e'. ValueError se le
    parti non tornano o se non e' una foto JPEG, PNG o WebP."""
    if not opts.get("prodotto"):
        return data, opts.get("parti"), None
    try:
        parti = [int(k) for k in (opts.get("parti") or [])]
    except (TypeError, ValueError):
        parti = []
    if len(parti) < 2 or any(k <= 0 for k in parti) or sum(parti) != len(data):
        raise ValueError("L'immagine del prodotto non torna col corpo: "
                         "manda il PDF e poi l'immagine, con le loro lunghezze")
    n = parti[-1]
    if n > PRODOTTO_MAX:
        raise ValueError("L'immagine del prodotto e' troppo grande (al massimo "
                         "%d MB)" % (PRODOTTO_MAX // (1024 * 1024)))
    immagine = data[-n:]
    coda.tipo_foto(immagine)
    resto = parti[:-1]
    return data[:-n], (resto if len(resto) > 1 else None), immagine


def riga_prodotto(immagine, nome):
    """La riga per chi guarda il modello: l'immagine del prodotto ricevuta."""
    try:
        from PIL import Image
        import io
        w, h = Image.open(io.BytesIO(immagine)).size
        misura = "%d x %d px" % (w, h)
    except Exception:
        misura = "%d kB" % (len(immagine) // 1024)
    return ("il prodotto da incartare: %s, immagine %s (va col caso, se finisce "
            "in coda; la misura del modello per ora la da' il DT)"
            % ("\u00ab%s\u00bb" % nome if nome else "senza nome", misura))


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #
def _dividi(data, parti):
    """I PDF di un corpo solo: `[bytes]`, o None se `parti` non torna.

    Senza `parti` il corpo e' un PDF solo, com'e' sempre stato.
    """
    if not parti:
        return [data]
    try:
        lunghe = [int(k) for k in parti]
    except (TypeError, ValueError):
        return None
    if any(k <= 0 for k in lunghe) or sum(lunghe) != len(data):
        return None
    blocchi, o = [], 0
    for k in lunghe:
        blocchi.append(data[o:o + k])
        o += k
    if not all(b.startswith(b"%PDF") for b in blocchi):
        return None
    return blocchi


class Handler(BaseHTTPRequestHandler):
    # HEAD risponde con le stesse intestazioni di GET e senza corpo. Il flag
    # lo dice a _send, cosi' le due risposte non possono divergere.
    _senza_corpo = False

    def log_message(self, fmt, *a):
        sys.stderr.write("  %s\n" % (fmt % a))

    def handle_one_request(self):
        # una risposta per richiesta (`_send`): si riparte da capo a ognuna
        self._inviata = False
        super().handle_one_request()

    def _cors(self):
        # l'interfaccia puo' stare su un dominio diverso dal backend
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Pack3d")
        # senza questo il browser nasconde l'header alla pagina, su altra origine
        self.send_header("Access-Control-Expose-Headers",
                         "X-Pack3d-Meta, X-Pack3d-Controllo, X-Pack3d-AI, "
                         "X-Pack3d-Lettura, X-Pack3d-Verdetto")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code, body, ctype="application/json", filename=None,
              meta=None, controllo=None, ai=None, lettura=None, verdetto_dopo=None):
        if getattr(self, "_inviata", False):
            # il modello e' partito prima del verdetto (`verdetto_dopo`): una
            # seconda risposta finirebbe in coda alla prima, sulla stessa
            # connessione
            print("risposta %d non mandata: la richiesta ha gia' avuto la sua" % code,
                  file=sys.stderr)
            return
        self._inviata = True
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if meta:
            # percent-encoded: un header HTTP e' latin-1 e non tollera accenti
            self.send_header("X-Pack3d-Meta", quote(
                json.dumps(meta, ensure_ascii=False)))
        if controllo:
            self.send_header("X-Pack3d-Controllo", quote(
                json.dumps(controllo, ensure_ascii=False)))
        if ai:
            # quali righe di `meta` sono dell'AI: la pagina le tiene in vista
            self.send_header("X-Pack3d-AI", quote(
                json.dumps(ai, ensure_ascii=False)))
        if lettura:
            # il gettone della lettura del PDF: la pagina la chiede a parte
            self.send_header("X-Pack3d-Lettura", lettura)
        if verdetto_dopo:
            # il verdetto del controllo arriva dopo il modello: la pagina lo
            # chiede con questo gettone (/api/verdetto)
            self.send_header("X-Pack3d-Verdetto", verdetto_dopo)
        if filename:
            self.send_header("Content-Disposition",
                             'attachment; filename="%s"' % filename)
        self._cors()
        self.end_headers()
        if not self._senza_corpo:
            self.wfile.write(body)

    def do_HEAD(self):
        # Render controlla la salute del servizio con HEAD, e
        # BaseHTTPRequestHandler senza do_HEAD risponde 501 a ogni controllo:
        # nel log di produzione si vede "Unsupported method ('HEAD')" a ogni
        # giro, dal primo istante dopo il deploy.
        self._senza_corpo = True
        try:
            self.do_GET()
        finally:
            self._senza_corpo = False

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            # con l'impronta del codice: dopo una pubblicazione dice se lo
            # Space e' gia' ripartito con quello nuovo (prove/parco.py spazio)
            # e se le email delle domande partono: senza, la pagina non chiede
            # l'email a chi manda un caso. `glam` dice se lo Space ha il token
            # d'import di Glam, per mandare da solo i modelli approvati (mai
            # il token: solo se c'e'). `colata` dice se e' arrivata la
            # risorsa della colata, che viene dal repository privato
            from pack3d import avvisi, colata as la_colata
            return self._send(200, json.dumps({"ok": True, "versione": VERSIONE,
                                               "email": avvisi.configurato(),
                                               "glam": coda.glam_configurato(),
                                               "colata": os.path.exists(la_colata.RISORSA)}))
        if self.path.startswith("/api/casi"):
            return self._stati()
        if self.path.startswith("/api/modello"):
            return self._modello()
        if self.path.startswith("/api/anteprima"):
            return self._anteprima()
        if self.path.startswith("/api/verdetto"):
            # il verdetto del controllo che arriva dopo il modello, e il GLB
            # corretto se la correzione l'ha rifatto (/api/verdetto/glb)
            from urllib.parse import parse_qs, urlparse
            gettone = (parse_qs(urlparse(self.path).query).get("id") or [""])[0][:40]
            v = verdetto_di(gettone)
            if v is None:
                return self._send(404, "Il verdetto non c'e' piu': ricostruisci il "
                                       "modello per riaverlo",
                                  "text/plain; charset=utf-8")
            if self.path.startswith("/api/verdetto/glb"):
                if not v["glb"]:
                    return self._send(404, "Nessun modello corretto", "text/plain; charset=utf-8")
                return self._send(200, v["glb"], "model/gltf-binary", filename="modello.glb")
            return self._send(200, json.dumps(dict(v, glb=bool(v["glb"])), ensure_ascii=False))
        if self.path.startswith("/api/lavori"):
            # a che punto e' il lavoro di chi aspetta: in fila, o in corso
            from urllib.parse import parse_qs, urlparse
            chi = (parse_qs(urlparse(self.path).query).get("id") or [""])[0][:40]
            return self._send(200, json.dumps(dict(lavoratori.stato(),
                                                   posizione=lavoratori.posizione(chi))))
        if self.path.startswith("/api/lettura/"):
            gettone = self.path.split("/api/lettura/", 1)[1].split("?")[0]
            with _LETTURE_LOCK:
                v = LETTURE.get(gettone)
            if v is None:
                return self._send(404, "La lettura del PDF non c'e' piu': "
                                       "ricostruisci il modello per rivederla",
                                  "text/plain; charset=utf-8")
            return self._send(200, v[1], "image/jpeg")
        path = os.path.join(HERE, "pack3d_studio.html")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), "text/html; charset=utf-8")

    # I casi della pagina: lo stato di quelli che ha mandato lei, per la
    # finestra dei casi e le notifiche (`coda.stati`). Solo per codice: chi
    # non ha il codice di un caso non lo vede.
    def _stati(self):
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(self.path).query)
        codici = [c for v in q.get("codici", []) for c in v.split(",") if c.strip()]
        try:
            casi = coda.stati(codici)
        except RuntimeError as e:
            return self._send(503, str(e))
        except (OSError, ValueError) as e:
            print("stato dei casi non letto: %s" % e, file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        return self._send(200, json.dumps({"casi": casi}, ensure_ascii=False))

    # Il modello corretto che un caso aspetta di far approvare (`coda.modello`):
    # la finestra dei casi lo carica nel visore. Solo per codice.
    def _modello(self):
        from urllib.parse import parse_qs, urlparse
        cod = (parse_qs(urlparse(self.path).query).get("codice") or [""])[0].strip().lower()
        try:
            glb = coda.modello(cod)
        except (OSError, ValueError) as e:
            print("modello del caso %s non letto: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        if glb is None:
            return self._send(404, "Nessun modello da approvare per questo caso")
        return self._send(200, glb, "model/gltf-binary")

    # L'anteprima di una domanda della routine (`coda.anteprima`): il modello
    # di adesso e la lettura del PDF, che la finestra dei casi mostra sopra la
    # domanda. Solo per codice.
    def _anteprima(self):
        from urllib.parse import parse_qs, urlparse
        cod = (parse_qs(urlparse(self.path).query).get("codice") or [""])[0].strip().lower()
        try:
            jpg = coda.anteprima(cod)
        except (OSError, ValueError) as e:
            print("anteprima del caso %s non letta: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        if jpg is None:
            return self._send(404, "Nessuna anteprima per questo caso")
        return self._send(200, jpg, "image/jpeg")

    # Un'analisi o una costruzione a un lavoratore (`pack3d.lavoratori`): qui
    # si legge la richiesta, li' si fa, e qui tornano la risposta, i casi da
    # mettere in coda e la lettura del PDF.
    def _a_un_lavoratore(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        if n <= 0:
            return self._send(400, "Nessun file ricevuto")
        if n > MAX_UPLOAD:
            return self._send(413, "PDF troppo grande (limite %d MB)"
                              % (MAX_UPLOAD // (1024 * 1024)))
        corpo = self.rfile.read(n)
        try:
            chi = str(json.loads(self.headers.get("X-Pack3d") or "{}").get("lavoro") or "")[:40]
        except (ValueError, AttributeError):
            chi = ""
        lavoro = {"path": self.path, "corpo": corpo,
                  "intestazioni": {"Content-Length": str(n),
                                   "X-Pack3d": self.headers.get("X-Pack3d") or ""}}
        # il modello che parte prima del verdetto: col suo gettone, che vale
        # «in corso» finche' il lavoratore non manda il verdetto
        attesa = []

        def anticipo(pacco):
            attesa.append(pacco["risposta"].get("verdetto_dopo"))
            metti_verdetto(attesa[-1], pronto=False)
            self._da_lavoratore(pacco)
        try:
            esito = lavoratori.esegui(lavoro, hashlib.sha256(corpo).hexdigest(), chi,
                                      anticipo)
        except lavoratori.Occupato as e:
            print("lavoratori: occupati, %s" % e, file=sys.stderr)
            return self._send(503, "Server occupato: troppe costruzioni in fila, "
                                   "riprova fra qualche minuto")
        except lavoratori.Caduto as e:
            if attesa:
                # il modello e' gia' arrivato: manca solo il verdetto
                metti_verdetto(attesa[-1], None, ["controllo AI non fatto: il processo "
                                                  "che lo faceva e' caduto (%s)" % e], [])
                return None
            return self._send(500, "La costruzione si e' fermata: il processo che "
                                   "la faceva e' caduto (%s). Le altre non ne "
                                   "risentono: riprova, e se ricapita con questo "
                                   "PDF mandalo come caso" % e)
        for gettone, voce in esito.get("verdetti", {}).items():
            metti_verdetto(gettone, **voce)
        return self._da_lavoratore(esito)

    def _da_lavoratore(self, pacco):
        """Quello che un lavoratore rimanda: i casi in coda, la lettura e la
        risposta, se c'e' (la risposta anticipata e' gia' partita)."""
        for a, k in pacco["casi"]:
            coda.metti(*a, **k)
        r = pacco["risposta"]
        if r is None:
            return None
        if r.get("lettura") and pacco.get("lettura"):
            metti_lettura(r["lettura"], pacco["lettura"])
        return self._send(r["code"], r["body"], r.get("ctype") or "application/json",
                          filename=r.get("filename"), meta=r.get("meta"),
                          controllo=r.get("controllo"), ai=r.get("ai"),
                          lettura=r.get("lettura") if pacco.get("lettura") else None,
                          verdetto_dopo=r.get("verdetto_dopo"))

    def _json_corpo(self, massimo=64 * 1024):
        """Il corpo JSON di una richiesta piccola, o (codice, errore)."""
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        if n <= 0:
            return None, (400, "Corpo vuoto")
        if n > massimo:
            return None, (413, "Troppo grande")
        try:
            corpo = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None, (400, "JSON non valido")
        if not isinstance(corpo, dict):
            return None, (400, "serve un oggetto JSON")
        return corpo, None

    # Un caso nuovo aspetta chi l'ha caricato (`coda.metti`): "invia" lo manda
    # alla routine, con l'email facoltativa per le domande; "annulla" lo
    # cancella, e senza scelta scade da solo.
    def _caso(self):
        from pack3d import avvisi
        corpo, errore = self._json_corpo()
        if errore:
            return self._send(*errore)
        cod = str(corpo.get("codice") or "").strip().lower()
        if not coda.CODICE_RE.match(cod):
            return self._send(404, "codice del caso non valido")
        azione = corpo.get("azione")
        if azione == "annulla":
            return self._send(200, json.dumps({"ok": True,
                                               "cancellato": coda.scarta(cod)}))
        if azione != "invia":
            return self._send(400, "azione sconosciuta: invia o annulla")
        email = None
        if str(corpo.get("email") or "").strip():
            email = avvisi.email_valida(corpo.get("email"))
            if not email:
                return self._send(400, "L'email non sembra un indirizzo valido")
        try:
            coda.conferma(cod, email)
        except coda.Assente as e:
            return self._send(404, str(e))
        return self._send(200, json.dumps({"ok": True, "in_coda": True,
                                           "email": bool(email)}))

    # La routine ha fatto una domanda (`prove/parco.py caso --stato domanda`):
    # lo Space la manda per email a chi l'ha chiesto (`coda.avvisa`).
    def _avviso(self):
        corpo, errore = self._json_corpo()
        if errore:
            return self._send(*errore)
        cod = str(corpo.get("codice") or "").strip().lower()
        pagina = (os.environ.get("PACK3D_PAGINA_URL", "").strip()
                  or ("https://" + os.environ["SPACE_HOST"].strip()
                      if os.environ.get("SPACE_HOST", "").strip()
                      else "https://" + (self.headers.get("Host") or "localhost")))
        try:
            esito = coda.avvisa(cod, pagina)
        except coda.Assente as e:
            return self._send(404, str(e))
        except coda.Troppe as e:
            return self._send(429, str(e))
        except RuntimeError as e:
            return self._send(503, str(e))
        except (OSError, ValueError) as e:
            print("avviso del caso %s non mandato: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        return self._send(200, json.dumps(esito, ensure_ascii=False))

    # La routine ha finito un caso e chiede se ce n'e' un altro libero: se si',
    # lo Space avvia una sessione nuova per lui (`coda.prossimo`). Senza
    # token: lo Space guarda la coda da se', al massimo ogni quindici secondi,
    # e non avvia due volte lo stesso caso in dieci minuti.
    def _prossimo(self):
        corpo, errore = self._json_corpo()
        if errore:
            return self._send(*errore)
        cod = str(corpo.get("codice") or "").strip().lower()
        try:
            esito = coda.prossimo(cod)
        except coda.Assente as e:
            return self._send(404, str(e))
        except coda.Troppe as e:
            return self._send(429, str(e))
        except RuntimeError as e:
            return self._send(503, str(e))
        except (OSError, ValueError) as e:
            print("prossimo caso dopo %s non cercato: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        return self._send(200, json.dumps(esito, ensure_ascii=False))

    # Il template PSD di un modello (`pack3d.template`): il corpo e' il GLB
    # che la pagina ha appena ricevuto, la risposta il PSD, o 204 se il
    # modello non ha una texture sola. La pagina lo chiede solo dentro Glam,
    # per «Scarica Template» (GLAM.md, sezione 9). Uno alla volta: un
    # template da 5000 px tiene in memoria qualche livello grande.
    _un_template = threading.Semaphore(1)

    def _template(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        if n <= 0:
            return self._send(400, "Nessun modello ricevuto")
        if n > MAX_UPLOAD:
            return self._send(413, "Modello troppo grande (limite %d MB)"
                              % (MAX_UPLOAD // (1024 * 1024)))
        glb = self.rfile.read(n)
        if glb[:4] != b"glTF":
            return self._send(400, "Il file non e' un GLB")
        try:
            with self._un_template:
                t = il_template.template(glb)
        except Exception as e:                          # noqa: BLE001
            traceback.print_exc()
            return self._send(500, "Template non riuscito: %s" % e)
        if t is None:
            return self._send(204, b"")
        return self._send(200, t["dati"], ctype=il_template.MIME)

    # La voce di chi ha caricato il PDF, dopo che il caso e' entrato in coda
    # (`coda.aggiungi`): una nota dalla pagina, o la risposta a una domanda
    # della routine, da Glam Lab. Corpi JSON, non PDF; la foto e' un data URL.
    # fino a coda.FOTO_N foto per voce, in base64
    VOCE_MAX = 40 * 1024 * 1024

    def _voce(self):
        risposta = self.path.startswith("/api/risposta")
        if risposta:
            # Solo Glam. La nota invece arriva dalla pagina, che e' pubblica,
            # e porta solo il codice del caso.
            errore = self._da_glam()
            if errore:
                return self._send(*errore)
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        if n <= 0:
            return self._send(400, "Corpo vuoto")
        corpo, foto, errore = self._corpo_con_foto(n)
        if errore:
            return self._send(*errore)
        cod = str(corpo.get("codice") or "").strip().lower()
        # La pagina risponde anche lei alle domande della routine, dalla
        # finestra dei casi: come una nota (col solo codice), ma con la scelta,
        # e rilancia la routine come una risposta da Glam.
        dalla_pagina = not risposta and corpo.get("risposta") is True
        try:
            esito = coda.aggiungi(
                cod, corpo.get("risposta" if risposta else "nota"), foto,
                via="risposta" if risposta or dalla_pagina else "nota",
                scelta=corpo.get("scelta") if risposta or dalla_pagina else None,
                fonte="pagina dello Space" if dalla_pagina else None)
        except coda.Assente as e:
            return self._send(404, str(e))
        except coda.Troppe as e:
            return self._send(429, str(e))
        except RuntimeError as e:
            return self._send(503, str(e))
        except ValueError as e:
            return self._send(400, str(e))
        except OSError as e:
            print("voce sul caso %s non arrivata: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        return self._send(200, json.dumps(esito))

    def _da_glam(self):
        """None se la richiesta porta il token di Glam Lab, se no (codice,
        errore). Il token sta nei segreti di Glam e in quelli dello Space, e
        da nessun'altra parte."""
        atteso = os.environ.get("PACK3D_RISPOSTE_TOKEN", "").strip()
        if not atteso:
            return 503, "Le chiamate da Glam Lab non sono configurate (PACK3D_RISPOSTE_TOKEN)"
        dato = (self.headers.get("Authorization") or "").strip()
        if not hmac.compare_digest(dato.encode("utf-8"),
                                   ("Bearer " + atteso).encode("utf-8")):
            return 401, "Token non valido"
        return None

    # Un caso eliminato dall'app (`coda.elimina`). Solo da Glam, col token:
    # chi puo' eliminare quale caso lo decide Glam, che sa chi e' collegato -
    # un admin tutti, l'account design i suoi, il guest nessuno.
    def _elimina(self):
        errore = self._da_glam()
        if errore:
            return self._send(*errore)
        corpo, errore = self._json_corpo()
        if errore:
            return self._send(*errore)
        cod = str(corpo.get("codice") or "").strip().lower()
        try:
            esito = coda.elimina(cod, corpo.get("ruolo"))
        except coda.Assente as e:
            return self._send(404, str(e))
        except coda.Occupato as e:
            return self._send(409, str(e))
        except RuntimeError as e:
            return self._send(503, str(e))
        except (OSError, ValueError) as e:
            print("caso %s non eliminato: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        return self._send(200, json.dumps(esito))

    def _corpo_con_foto(self, n):
        """(corpo JSON, foto in byte, None) o (None, None, (codice, errore)).
        `foto` nel corpo e' un data URL o una lista, al massimo coda.FOTO_N."""
        if n <= 0:
            return None, None, (400, "Corpo vuoto")
        if n > self.VOCE_MAX:
            return None, None, (413, "Troppo grande: al massimo %d foto da %d MB"
                                % (coda.FOTO_N, coda.FOTO_MAX // (1024 * 1024)))
        try:
            corpo = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(corpo, dict):
                raise ValueError("serve un oggetto JSON")
            foto = coda.fotos_da_testo(corpo.get("foto"))
        except (ValueError, UnicodeDecodeError) as e:
            return None, None, (400, str(e) or "JSON non valido")
        return corpo, foto, None

    # Il modello corretto, approvato o no da chi ha caricato il PDF, dalla
    # finestra dei casi (`coda.esito_modello`). Se no, col motivo e le foto.
    def _approva(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        corpo, foto, errore = self._corpo_con_foto(n)
        if errore:
            return self._send(*errore)
        cod = str(corpo.get("codice") or "").strip().lower()
        if not isinstance(corpo.get("approvato"), bool):
            return self._send(400, "approvato: true o false")
        try:
            esito = coda.esito_modello(cod, corpo["approvato"], corpo.get("motivo"), foto)
        except coda.Assente as e:
            return self._send(404, str(e))
        except coda.Troppe as e:
            return self._send(429, str(e))
        except RuntimeError as e:
            return self._send(503, str(e))
        except ValueError as e:
            return self._send(400, str(e))
        except OSError as e:
            print("approvazione del caso %s non arrivata: %s" % (cod, e), file=sys.stderr)
            return self._send(502, "Il repository dei casi non risponde: riprova "
                                   "fra poco")
        return self._send(200, json.dumps(esito))

    def do_POST(self):
        if self.path.startswith("/api/nota") or self.path.startswith("/api/risposta"):
            return self._voce()
        if self.path.startswith("/api/approva"):
            return self._approva()
        if self.path.startswith("/api/elimina"):
            return self._elimina()
        if self.path.startswith("/api/caso"):
            return self._caso()
        if self.path.startswith("/api/avviso"):
            return self._avviso()
        if self.path.startswith("/api/prossimo"):
            return self._prossimo()
        if self.path.startswith("/api/template"):
            return self._template()
        if lavoratori.attivi() and self.path.startswith(AI_LAVORATORI):
            return self._a_un_lavoratore()
        if self.path.startswith(AI_LAVORATORI):
            # un lavoro: la sua cartella per i file temporanei e le casse
            # vuote, uno alla volta per processo (`pack3d.stato`)
            with stato.lavoro():
                return self._col_pdf()
        return self._col_pdf()

    def _col_pdf(self):
        """Le richieste che portano il PDF: analisi, costruzione, segnalazione."""
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, "Nessun file ricevuto")
            if n > MAX_UPLOAD:
                return self._send(413, "PDF troppo grande (limite %d MB)"
                                  % (MAX_UPLOAD // (1024 * 1024)))
            data = self.rfile.read(n)
            if not data.startswith(b"%PDF"):
                return self._send(400, "Il file caricato non e' un PDF")
            opts = json.loads(self.headers.get("X-Pack3d") or "{}")
            # L'immagine del prodotto da incartare arriva in coda, dopo i PDF
            # (vedi `_separa_prodotto`): gli incarti la chiedono, perche' la
            # misura finale del 3D dipende anche dal prodotto.
            try:
                data, parti_pdf, prodotto = _separa_prodotto(data, opts)
            except ValueError as e:
                return self._send(400, str(e))
            dichiarato = opts.get("prodotto")
            nome_prodotto = (unquote(str(dichiarato.get("nome") or ""))[:200]
                             if isinstance(dichiarato, dict) else "")
            # Piu' PDF in un corpo solo, uno dopo l'altro: `parti` ne dice le
            # lunghezze. Serve alla coppa, che arriva in due file - lo sleeve
            # e il tappo - e si costruisce intera solo con tutti e due.
            blocchi = _dividi(data, parti_pdf)
            if blocchi is None:
                return self._send(400, "Le parti dichiarate non tornano col "
                                       "corpo, o una non e' un PDF")
            with tempfile.TemporaryDirectory(dir=stato.cartella()) as td:
                pdfs = []
                for k, blocco in enumerate(blocchi):
                    pdfs.append(os.path.join(td, "in.pdf" if k == 0
                                             else "in%d.pdf" % k))
                    with open(pdfs[-1], "wb") as fh:
                        fh.write(blocco)
                pdf = pdfs[0]
                # i nomi dei file servono al controllo e alla coda dei casi
                # nuovi; arrivano percent-encoded, perche' un header HTTP e'
                # latin-1 e un nome di file puo' essere qualsiasi cosa
                nomi = [unquote(str(n))[:200] for n in (opts.get("nomi") or [])][:len(pdfs)]
                nomi += ["artwork%d.pdf" % (k + 1) for k in range(len(nomi), len(pdfs))]
                kind = normalizza_kind(opts.get("kind") or None)
                if kind == "altro":
                    return self._send(400, "Tipologia non ancora supportata")
                if kind is not None and kind not in KIND_NOTI:
                    return self._send(400, "Tipologia '%s' non riconosciuta: "
                                           "dichiara %s"
                                           % (kind, " o ".join("'%s'" % k
                                                               for k in KIND_NOTI)))
                if kind == "incarto" and prodotto is None:
                    return self._send(400, "Incarti: carica anche l'immagine del "
                                           "prodotto da incartare. La misura "
                                           "finale del 3D dipende anche dal "
                                           "prodotto, non solo dallo steso")
                if prodotto is not None and kind != "incarto":
                    return self._send(400, "L'immagine del prodotto serve solo "
                                           "agli incarti")
                # il caso in coda porta anche l'immagine del prodotto
                blocchi_caso, nomi_caso = list(blocchi), list(nomi)
                if prodotto is not None:
                    base = os.path.splitext(nome_prodotto)[0] or "immagine"
                    blocchi_caso.append(prodotto)
                    nomi_caso.append("prodotto_%s.%s" % (base, coda.tipo_foto(prodotto)))
                # Il cartotecnico dice di quanti pezzi e' fatto, e ogni pezzo
                # e' un PDF: se i conti non tornano non si indovina quale
                # manca, si dice.
                pezzi = opts.get("pezzi")
                if pezzi not in (None, ""):
                    try:
                        pezzi = int(pezzi)
                    except (TypeError, ValueError):
                        return self._send(400, "Il numero di pezzi va digitato "
                                               "come numero intero")
                    if pezzi < 1:
                        return self._send(400, "Un pack ha almeno un pezzo")
                    if pezzi != len(pdfs):
                        return self._send(400, "Il pack e' di %d %s ma sono "
                                               "arrivati %d PDF: ne serve uno "
                                               "per pezzo"
                                          % (pezzi, "pezzo" if pezzi == 1
                                             else "pezzi", len(pdfs)))
                try:
                    carta = spessore_carta(opts.get("spessore"))
                    gradi_aperta = apertura_gradi(opts.get("apertura"))
                    con_pellicola = pellicola_scelta(opts.get("pellicola"))
                    con_incisioni = incisioni_scelte(opts.get("incisioni"))
                    con_gelato = gelato.gusto(opts.get("gelato"))
                    chiusura = chiusura_incarto(opts.get("chiusura"))
                    quanti = quanti_pezzi(opts.get("quanti"))
                    per_fila = per_fila_scelti(opts.get("per_fila"))
                    cu = cu_riempimento(opts.get("cu"))
                except ValueError as e:
                    return self._send(400, str(e))
                # (`coppa` resta per chi chiama l'API: dalla pagina la coppa
                # e' un cartotecnico in due pezzi)
                if kind == "riempimento" and len(pdfs) != 2:
                    return self._send(400, "Riempimento: carica due PDF, il "
                                           "vassoio e il pack (CU)")
                if len(pdfs) > 1 and kind not in ("coppa", "carton", "riempimento"):
                    return self._send(400, "Piu' PDF insieme solo per un "
                                           "cartotecnico in piu' pezzi: per "
                                           "questa tipologia caricane uno")
                if self.path.startswith("/api/segnala"):
                    # «Letto male»: chi ha costruito il modello guarda la
                    # lettura del PDF accanto (`pack3d.lettura`) e dice che non
                    # torna. La pagina rimanda gli stessi PDF e le stesse
                    # opzioni, col motivo: il caso si prepara come quelli che
                    # il controllo respinge, e parte quando lo conferma con
                    # la descrizione. Niente costruzione: la rifa' la routine.
                    motivo = str(opts.get("motivo") or "").strip()[:300] or "letto male"
                    verdetto = {"esito": "sbagliato", "segnalato": True,
                                "motivo": "Segnalato da chi l'ha costruito: il PDF e' "
                                          "stato letto male - %s" % motivo,
                                "difetti": ["letto male: %s" % motivo]}
                    ctx = dict(dichiarato=dichiarazione(kind, len(pdfs)),
                               riconosciuto="-", avvisi=[], nomi=nomi,
                               opzioni={k: opts[k] for k in OPZIONI_CASO
                                        if k in opts})
                    verdetto["codice"], verdetto["in_coda"] = coda.metti(
                        blocchi_caso, nomi_caso, verdetto, None, ctx)
                    verdetto["in_attesa"] = coda.in_attesa(verdetto["codice"])
                    return self._send(200, json.dumps(verdetto, ensure_ascii=False))
                if kind == "riempimento" and self.path.startswith("/api/analyze"):
                    try:
                        letto = analisi_riempimento(pdfs, cu)
                    except Exception as e:
                        errore, verdetto = caso_fermo(e, kind, pdfs, nomi_caso, opts,
                                                      blocchi_caso)
                        return self._send(500, errore, controllo=verdetto)
                    return self._send(200, json.dumps(letto))
                if (in_piu_pezzi(kind, pdfs)
                        and self.path.startswith("/api/analyze")):
                    # anche da /api/analyze-ai: i pezzi li misura il codice,
                    # l'agente non ha niente da aggiungere
                    try:
                        letto = analisi_coppa(pdfs, kind)
                    except Exception as e:
                        errore, verdetto = caso_fermo(e, kind, pdfs, nomi_caso, opts,
                                                      blocchi_caso)
                        return self._send(500, errore, controllo=verdetto)
                    return self._send(200, json.dumps(letto))
                if self.path.startswith("/api/analyze-ai"):
                    import agent
                    par, tr = agent.analyse(pdf, kind, opts)
                    par["_chiamate"] = [t["tool"] for t in tr]
                    return self._send(200, json.dumps(par, ensure_ascii=False))
                if self.path.startswith("/api/analyze"):
                    # La pagina chiede la lettura prima della costruzione: un
                    # PDF che il codice non sa leggere si ferma qui, e la
                    # costruzione non parte mai. Va in coda da qui.
                    try:
                        if kind == "incarto":
                            letto = analisi_incarto_dichiarato(pdf, chiusura)
                            letto = dict(letto, meta=list(letto.get("meta") or [])
                                         + [riga_prodotto(prodotto, nome_prodotto)])
                        else:
                            letto = analyze_pdf(pdf, kind, domande=True)
                    except Exception as e:
                        errore, verdetto = caso_fermo(e, kind, pdfs, nomi_caso, opts,
                                                      blocchi_caso)
                        return self._send(500, errore, controllo=verdetto)
                    return self._send(200, json.dumps(letto))
                if self.path.startswith("/api/build"):
                    if not _slots.acquire(blocking=False):
                        return self._send(503, "Server occupato: riprova fra qualche "
                                               "secondo")
                    # Da qui in giu' il posto e' preso e va restituito comunque
                    # vada. Prima analyze_pdf stava FUORI da qualsiasi
                    # protezione: su un PDF che non sa risolvere (wafer T1,
                    # "saldature di testa non riconosciute") lanciava, il posto
                    # non tornava indietro, e dopo MAX_JOBS tentativi il server
                    # rispondeva 503 a chiunque fino al riavvio.
                    info = None
                    try:
                        out = os.path.join(td, "out.glb")
                        t0 = traccia("inizio")
                        case = CASI.get(_sig(pdf))
                        info = (analisi_incarto_dichiarato(pdf, chiusura)
                                if kind == "incarto"
                                else analisi_riempimento(pdfs, cu) if kind == "riempimento"
                                else analisi_coppa(pdfs, kind)
                                if in_piu_pezzi(kind, pdfs)
                                else analyze_pdf(pdf, kind))
                        t1 = traccia("analisi", t0,
                                     "%s, %d kB" % (info["kind"], len(data) // 1024))
                        q = qualita(opts.get("quality"))
                        # Su TUTTI i rami: e' proprio sul ramo che se ne
                        # dimenticava che nasceva l'UnboundLocalError.
                        avvisi_ingresso = []
                        # l'immagine del prodotto da incartare: nei dettagli
                        # tecnici, non fra le righe dell'AI
                        righe_prodotto = ([riga_prodotto(prodotto, nome_prodotto)]
                                          if prodotto is not None else [])
                        # Le aree riservate che l'agente ha visto: valgono su
                        # tutte e due le famiglie, quindi si leggono una volta
                        # sola prima di scegliere il ramo.
                        aree = aree_da_agente(opts.get("params"))
                        # stessa storia delle aree riservate: il file non
                        # dichiara la colata, e l'unica cosa che resta e'
                        # quello che l'agente ha guardato
                        col_riq = colata_da_agente(opts.get("params"))
                        # i ruoli delle lastre di materiale che l'AI legge
                        # costruendo un flowpack: vedi leggi_materiali
                        mat_ai = {}
                        # La costruzione e' una funzione delle lastre da
                        # togliere e del file d'uscita: la correzione dell'AI
                        # la rifa' con le lastre tecniche che ha riconosciuto,
                        # con tutto il resto uguale.
                        def parametri_flowpack(pdf_fp, nome_fp):
                            """Rigonfiamento, scatola, pinne e materiali del
                            flowpack: dalla pagina, o scelti dall'AI."""
                            soft = opts.get("soft", "medio")
                            if str(soft).strip().lower() == "auto":
                                # "Scegli tu": il livello lo decide l'agente in
                                # /api/analyze-ai e torna qui dentro params
                                scelto = livello_da_agente(opts.get("params"))
                                perche = "nessuna analisi AI allegata alla richiesta"
                                if scelto is None and controllo.attivo():
                                    # La pagina non chiama /api/analyze-ai: la
                                    # scelta la fa qui Claude guardando
                                    # l'artwork, con le regole di REGOLE.md.
                                    # Si e' dentro il posto di costruzione, e
                                    # deve essere cosi': la pagina passa da
                                    # pdfium.
                                    sc = controllo.rigonfiamento(pdf_fp, nome_fp)
                                    if "errore" in sc:
                                        perche = "l'AI non ha risposto (%s)" % sc["errore"]
                                    else:
                                        scelto = sc["livello"]
                                        avvisi_ingresso.append(
                                            controllo.dichiarazione(sc))
                                        if sc["avvolge_scatola"] and not opts.get("scatola"):
                                            opts["scatola"] = True
                                            avvisi_ingresso.append(
                                                "il film avvolge una scatola: "
                                                "l'ha visto l'AI, la casella "
                                                "non era spuntata")
                                if scelto is None:
                                    # Nessuna analisi allegata: gonfiore() cade
                                    # su 5 in silenzio mentre l'interfaccia ha
                                    # appena promesso che sceglieva l'AI. Un
                                    # ripiego muto che produce un modello
                                    # plausibile e' il difetto peggiore che
                                    # questo progetto possa avere.
                                    avvisi_ingresso.append(
                                        "RIGONFIAMENTO NON SCELTO DA NESSUNO: "
                                        "%s, uso il livello medio 5" % perche)
                                    soft = 5
                                else:
                                    soft = scelto
                            # la scatola puo' dirla l'agente o la casella
                            # dell'interfaccia: basta una delle due
                            scatola = (bool(opts.get("scatola"))
                                       or scatola_da_agente(opts.get("params")))
                            pinne = opts.get("pinne")
                            if pinne in (None, "", "auto"):
                                pinne = pinne_da_agente(opts.get("params"))
                            return (soft, scatola, pinne,
                                    materiali_dichiarati(opts.get("materiali")))

                        # la costruzione della famiglia letta: `COSTRUZIONI`
                        r = SimpleNamespace(
                            pdf=pdf, pdfs=pdfs, nomi=nomi, kind=kind, opts=opts,
                            q=q, col_riq=col_riq, carta=carta,
                            apertura=gradi_aperta, pellicola=con_pellicola,
                            incisioni=con_incisioni, gelato=con_gelato,
                            quanti=quanti, per_fila=per_fila, case=case,
                            mat_ai=mat_ai, parametri_flowpack=parametri_flowpack)
                        costruisci = COSTRUZIONI.get(
                            info["kind"], _costruisci_flowpack)(r, info)
                        avvisi = costruisci(aree, out)
                        if mat_ai and not opts.get("materiali"):
                            # col caso in coda, perche' la routine lo rifaccia
                            # col materiale che ha visto l'utente
                            opts["materiali"] = dict(mat_ai)
                        traccia("costruzione", t1,
                                "%d kB" % (os.path.getsize(out) // 1024))
                        with open(out, "rb") as fh:
                            glb = fh.read()
                        lettura = lettura_accanto(out)
                        meta = righe_prodotto + avvisi_ingresso + list(avvisi)
                        # Le righe dell'AI - le sue scelte, il verdetto del
                        # controllo, la correzione - viaggiano anche in un
                        # header loro: la pagina le tiene in vista, e il
                        # resto lo mette nei dettagli tecnici.
                        righe_ai = list(avvisi_ingresso)
                        # Le immagini del controllo si fanno qui dentro: le
                        # pagine passano da pdfium, che non si chiama da due
                        # thread. La risposta di Claude invece si aspetta
                        # fuori, a posto restituito: e' solo attesa di rete, e
                        # chi viene dopo intanto costruisce.
                        quadro = None
                        if controllo.attivo():
                            try:
                                quadro = controllo.prepara(pdfs, out)
                            except Exception as e:
                                traceback.print_exc()
                                righe_ai.append("controllo AI non fatto: le viste "
                                                "del modello non sono riuscite "
                                                "(%s)" % e)
                                meta.append(righe_ai[-1])
                        traccia("totale", t0)
                    except Exception as e:
                        errore, verdetto = caso_fermo(e, kind, pdfs, nomi_caso, opts,
                                                      blocchi_caso, info)
                        return self._send(500, errore, controllo=verdetto)
                    finally:
                        _slots.release()
                    verdetto = None
                    ctx = dict(dichiarato=dichiarazione(kind, len(pdfs)),
                               riconosciuto=info.get("title") or info["kind"],
                               avvisi=list(meta), nomi=nomi,
                               # col caso in coda, perche' chi lo riprende
                               # lo ricostruisca uguale
                               opzioni={k: opts[k] for k in OPZIONI_CASO
                                        if k in opts})
                    nota = (nota_apertura(meta) or nota_incisioni(meta)
                            or nota_materiali(meta) or nota_gelato(meta))
                    if info["kind"] == "riempimento":
                        # il controllo sa che e' un riempimento, e quale PDF
                        # e' il contenitore e quale il pack
                        nota = " ".join(n for n in (nota_riempimento(info, nomi), nota) if n)
                    if nota:
                        ctx["nota"] = nota
                    if quadro is not None:
                        # Il modello va subito a chi l'ha chiesto, e il
                        # verdetto dell'AI - con la correzione, se serve -
                        # arriva dopo: la pagina lo chiede col gettone
                        # (`/api/verdetto`). Prima si aspettava qui la
                        # risposta di Claude, e quando c'era la seconda
                        # costruzione.
                        attesa = nuovo_verdetto()
                        in_corso = "controllo AI: in corso, il verdetto arriva fra poco"
                        self._send(200, glb, "model/gltf-binary",
                                   filename="modello.glb", meta=[in_corso] + meta,
                                   ai=[in_corso] + righe_ai, lettura=lettura,
                                   verdetto_dopo=attesa)
                        glb_prima = glb
                        try:
                            t2 = traccia("controllo")
                            verdetto = controllo.giudica(quadro, ctx)
                            traccia("controllo", t2, verdetto["esito"])
                            riga = None
                            if (controllo.correggibile(verdetto)
                                    and controllo.correzione_attiva()):
                                nuovo, riga = correggi(costruisci, aree, pdfs, td,
                                                       quadro, verdetto, ctx)
                                if nuovo is not None:
                                    glb, avvisi_corr, quadro, verdetto, ctx = nuovo
                                    meta = (righe_prodotto + avvisi_ingresso
                                            + list(avvisi_corr))
                                ctx = dict(ctx, avvisi=[riga] + list(ctx["avvisi"]))
                            # i difetti misurati dalle verifiche valgono come
                            # un dubbio, anche col controllo che dice ok
                            verdetto = con_difetti(verdetto, meta)
                            # anche il dubbio: il modello all'utente arriva lo
                            # stesso, ma qualcuno deve guardarlo, e se ha un
                            # difetto vero correggerlo come un caso respinto
                            if verdetto["esito"] in ("sbagliato", "dubbio"):
                                verdetto["codice"], verdetto["in_coda"] = coda.metti(
                                    blocchi_caso, nomi_caso, verdetto, quadro["viste"],
                                    ctx)
                                verdetto["in_attesa"] = coda.in_attesa(verdetto["codice"])
                            if riga:
                                meta.insert(0, riga)
                                righe_ai.insert(0, riga)
                            meta.insert(0, controllo.avviso(verdetto))
                            righe_ai.insert(0, meta[0])
                        except Exception as e:
                            # il modello e' gia' partito: l'errore lo dice il
                            # verdetto, non una seconda risposta
                            traceback.print_exc()
                            verdetto = None
                            righe_ai.insert(0, "controllo AI non fatto: %s" % e)
                            meta.insert(0, righe_ai[0])
                        metti_verdetto(attesa, verdetto, meta, righe_ai,
                                       glb if glb is not glb_prima else None)
                        return None
                    elif (controllo.manca_la_chiave()
                          and info["kind"] != "riempimento"):
                        # spento perche' manca la chiave, non perche' qualcuno
                        # l'ha spento apposta: chi gestisce lo Space lo deve sapere
                        righe_ai.append("controllo AI spento: manca la chiave "
                                        "ANTHROPIC_API_KEY fra i Secrets dello "
                                        "Space")
                        meta.append(righe_ai[-1])
                    if quadro is None and verifica.difetti(meta):
                        # senza controllo AI - la chiave che manca, o le viste
                        # che non riescono - il verdetto lo danno le verifiche: il caso
                        # va in coda senza le viste del controllo, la routine
                        # lo ricostruisce comunque
                        verdetto = con_difetti(None, meta)
                        verdetto["codice"], verdetto["in_coda"] = coda.metti(
                            blocchi_caso, nomi_caso, verdetto, None, ctx)
                        verdetto["in_attesa"] = coda.in_attesa(verdetto["codice"])
                        meta.insert(0, "VERIFICHE: il modello ha dei difetti misurati - %s"
                                    % verdetto["motivo"])
                        righe_ai.insert(0, meta[0])
                    # gli avvisi della costruzione viaggiano in un header: il
                    # corpo e' il GLB. Finivano nel nulla, e con loro ogni
                    # diagnostica. Il verdetto del controllo in un altro.
                    return self._send(200, glb, "model/gltf-binary",
                                      filename="modello.glb", meta=meta,
                                      controllo=verdetto, ai=righe_ai,
                                      lettura=lettura)
            return self._send(404, "endpoint sconosciuto")
        except Exception as e:
            traceback.print_exc()
            return self._send(500, "%s: %s" % (type(e).__name__, e))

MAX_UPLOAD = 60 * 1024 * 1024
# Uno per processo, e non e' un numero da tarare sulla macchina: pdfium non e'
# thread-safe nemmeno su documenti diversi, e due costruzioni insieme fanno
# morire il processo intero con un int3 dentro libpdfium.so. Provato su 16 GB,
# dove la memoria non c'entrava niente. Le costruzioni insieme le fanno i
# lavoratori, un processo ciascuno (`pack3d.lavoratori`). Vedi REGOLE.md,
# *pdfium non si chiama da due thread*, e DEPLOY.md per i numeri per fase.
MAX_JOBS = int(os.environ.get("PACK3D_MAX_JOBS", "1"))
_slots = threading.Semaphore(MAX_JOBS)

# Quanto la correzione aspetta che il posto di costruzione si liberi. Chi ha
# chiesto il modello sta gia' aspettando: oltre, si consegna quello di prima.
CORREZIONE_ATTESA = float(os.environ.get("PACK3D_CORREZIONE_ATTESA", "240"))


# Le letture del PDF delle ultime costruzioni (`pack3d.lettura`), per la
# pagina: la chiede subito dopo il modello, col gettone che le arriva in
# X-Pack3d-Lettura. Poche e per poco: un'immagine sui 300 kB.
LETTURE = {}
LETTURE_MAX = 40
LETTURE_ORE = 2 * 3600
_LETTURE_LOCK = threading.Lock()


def lettura_accanto(out_glb):
    """La lettura che la costruzione ha lasciato accanto al GLB, messa da
    parte per la pagina: il suo gettone, o None se non c'e'."""
    import secrets
    try:
        with open(out_glb + lettura_pdf.ACCANTO, "rb") as fh:
            dati = fh.read()
    except OSError:
        return None
    gettone = secrets.token_hex(12)
    metti_lettura(gettone, dati)
    return gettone


def metti_lettura(gettone, dati):
    """La lettura `dati` fra quelle che la pagina puo' chiedere, col suo
    gettone: anche quella fatta da un lavoratore, che il processo del server
    tiene per lui (`esegui_lavoro`)."""
    with _LETTURE_LOCK:
        adesso = time.time()
        for k in [k for k, (t, _d) in LETTURE.items() if adesso - t > LETTURE_ORE]:
            del LETTURE[k]
        while len(LETTURE) >= LETTURE_MAX:
            del LETTURE[min(LETTURE, key=lambda k: LETTURE[k][0])]
        LETTURE[gettone] = (adesso, dati)


# ---------------------------------------------------------------------------
# I lavoratori (`pack3d.lavoratori`): le analisi e le costruzioni in processi
# a parte. Il processo del server legge la richiesta e la passa intera a un
# lavoratore, che la fa con lo stesso codice di sempre (`Handler.do_POST`) e
# rimanda la risposta, i casi da mettere in coda e la lettura del PDF.

# le richieste che passano da pdfium vanno ai lavoratori (/api/analyze-ai
# compresa); /api/segnala no, prepara solo il caso
AI_LAVORATORI = ("/api/analyze", "/api/build")


class _Lavoro(Handler):
    """Una richiesta POST rifatta nel lavoratore: niente socket, la risposta
    resta qui per tornare al processo del server."""

    def __init__(self, path, intestazioni, corpo, casi, anticipa=None):  # pylint: disable=super-init-not-called
        self.path = path
        self.headers = intestazioni
        self.rfile = io.BytesIO(corpo)
        self.risposta = None
        self._casi = casi
        self._anticipa = anticipa

    def _send(self, code, body, ctype="application/json", filename=None,
              meta=None, controllo=None, ai=None, lettura=None, verdetto_dopo=None):
        if getattr(self, "_inviata", False):
            print("risposta %d non mandata: la richiesta ha gia' avuto la sua" % code,
                  file=sys.stderr)
            return
        self._inviata = True
        if isinstance(body, str):
            body = body.encode()
        r = dict(code=code, body=body, ctype=ctype, filename=filename, meta=meta,
                 controllo=controllo, ai=ai, lettura=lettura, verdetto_dopo=verdetto_dopo)
        if verdetto_dopo and self._anticipa:
            # il modello parte subito, e il lavoratore va avanti col verdetto
            self._anticipa(_pacco(r, self._casi))
            return
        self.risposta = r


def _pacco(r, casi):
    """La risposta di un lavoratore per il processo del server: coi casi da
    mettere in coda finora (e poi via, per non rimetterli) e la lettura."""
    lettura = None
    if r.get("lettura"):
        with _LETTURE_LOCK:
            lettura = (LETTURE.pop(r["lettura"], None) or (0, None))[1]
    pacco = {"risposta": r, "casi": list(casi), "lettura": lettura}
    del casi[:]
    return pacco


def esegui_lavoro(lavoro, anticipa=None):
    """Nel lavoratore: la richiesta com'era, rifatta da `Handler.do_POST`.
    Torna la risposta, i casi che il processo del server deve mettere in coda
    (`lavoratori.casi_rimandati`), i dati della lettura del PDF e i verdetti
    del controllo. Con `anticipa` il modello parte prima del verdetto: la
    risposta va li', e alla fine restano i casi e i verdetti."""
    casi = []
    h = _Lavoro(lavoro["path"], lavoro["intestazioni"], lavoro["corpo"], casi, anticipa)
    with _VERDETTI_LOCK:
        prima = set(VERDETTI)
    with lavoratori.casi_rimandati(coda, casi):
        Handler.do_POST(h)
    esito = _pacco(h.risposta, casi) if h.risposta else {"risposta": None, "casi": list(casi),
                                                         "lettura": None}
    with _VERDETTI_LOCK:
        esito["verdetti"] = {k: VERDETTI.pop(k)[1] for k in list(VERDETTI) if k not in prima}
    return esito


# I verdetti del controllo che arrivano dopo il modello: la pagina li chiede
# col gettone di X-Pack3d-Verdetto (/api/verdetto). Come le letture: pochi e
# per poco. Il GLB corretto, se la correzione l'ha rifatto, sta con loro.
VERDETTI = {}
VERDETTI_MAX = 40
_VERDETTI_LOCK = threading.Lock()


def nuovo_verdetto():
    """Il gettone di un verdetto che arrivera': intanto e' «in corso»."""
    import secrets
    gettone = secrets.token_hex(12)
    metti_verdetto(gettone, pronto=False)
    return gettone


def metti_verdetto(gettone, verdetto=None, meta=None, ai=None, glb=None, pronto=True):
    with _VERDETTI_LOCK:
        adesso = time.time()
        for k in [k for k, (t, _v) in VERDETTI.items() if adesso - t > LETTURE_ORE]:
            del VERDETTI[k]
        while len(VERDETTI) >= VERDETTI_MAX and gettone not in VERDETTI:
            del VERDETTI[min(VERDETTI, key=lambda k: VERDETTI[k][0])]
        VERDETTI[gettone] = (adesso, {"pronto": pronto, "verdetto": verdetto,
                                      "meta": meta, "ai": ai, "glb": glb})


def verdetto_di(gettone):
    with _VERDETTI_LOCK:
        v = VERDETTI.get(gettone)
    return v[1] if v else None


def con_difetti(verdetto, meta):
    """Il verdetto con i difetti che le verifiche hanno misurato sul modello
    (`verifica.difetti`). Un difetto vale come un dubbio del controllo AI: il
    modello arriva lo stesso, con l'avviso, e il caso va in coda. Senza
    controllo AI - la chiave che manca, o le viste che non riescono - il
    verdetto lo danno le verifiche da sole. None se non ce n'e' nessuno e non c'era verdetto."""
    trovati = verifica.difetti(meta)
    if not trovati:
        return verdetto
    v = dict(verdetto or {"esito": "dubbio", "motivo": ""})
    misurato = "le verifiche hanno misurato: " + "; ".join(trovati)
    v["motivo"] = misurato + (" - " + v["motivo"] if v.get("motivo") else "")
    if v.get("esito") != "sbagliato":
        v["esito"] = "dubbio"
    v["difetti"] = list(trovati) + list(v.get("difetti") or [])
    v["verifiche"] = list(trovati)
    return v


def correggi(costruisci, aree, pdfs, cartella, quadro, verdetto, ctx):
    """La seconda costruzione, senza le lastre tecniche che Claude riconosce.

    Il controllo ha visto segni del disegno tecnico rimasti stampati: Claude
    guarda dove dipinge ogni inchiostro spot e dice quali sono solo tecnici
    (`controllo.inchiostri_tecnici`), la costruzione si rifa' senza, e il
    modello nuovo ripassa dal controllo. Si consegna il nuovo se il verdetto
    non e' peggiore, se no resta il primo.

    Torna `(nuovo, riga)`: `nuovo` e' (glb, avvisi, quadro, verdetto, ctx) del
    modello corretto, o None se resta il primo; `riga` dice com'e' andata.
    Non lancia: una correzione che non riesce lascia il modello di prima.
    """
    t = traccia("correzione")
    # i pieni candidati si cercano con pdfium: dentro il posto
    candidati = []
    if _slots.acquire(timeout=CORREZIONE_ATTESA):
        try:
            candidati = [_candidati(p) for p in pdfs]
        finally:
            _slots.release()
    scelta = controllo.segni_tecnici(pdfs, quadro, verdetto, candidati)
    if "errore" in scelta:
        return None, "correzione AI non fatta: %s" % scelta["errore"]
    if not scelta["tecnici"] and not scelta["oggetti"]:
        return None, ("correzione AI non fatta: niente nel file e' solo disegno "
                      "tecnico (%s)" % (scelta.get("motivo") or "-"))
    # la seconda costruzione usa pdfium come la prima: dentro il posto
    if not _slots.acquire(timeout=CORREZIONE_ATTESA):
        return None, "correzione AI non fatta: il server era occupato"
    try:
        uscita = os.path.join(cartella, "corretto.glb")
        with strati.spegnendo(scelta["oggetti"]):
            avvisi = costruisci(list(aree) + scelta["tecnici"], uscita)
        with open(uscita, "rb") as fh:
            glb = fh.read()
        quadro2 = controllo.prepara(pdfs, uscita)
    except Exception as e:
        traceback.print_exc()
        return None, "correzione AI non riuscita: %s" % e
    finally:
        _slots.release()
    ctx2 = dict(ctx, avvisi=list(avvisi),
                nota=" ".join(n for n in (ctx.get("nota"),
                                          controllo.nota_correzione(scelta)) if n))
    verdetto2 = controllo.giudica(quadro2, ctx2)
    traccia("correzione", t, verdetto2["esito"])
    tenuto = controllo.migliore(verdetto, verdetto2)
    riga = controllo.avviso_correzione(scelta, verdetto, verdetto2, tenuto)
    if not tenuto:
        return None, riga
    verdetto2["corretto"] = True
    verdetto2["tolti"] = list(scelta["tecnici"]) + (
        ["%d segni in quadricromia" % len(scelta["oggetti"])] if scelta["oggetti"] else [])
    return (glb, avvisi, quadro2, verdetto2, ctx2), riga


def _candidati(pdf):
    """I pieni allineati al disegno, dentro il DT con la grafica: vedi
    `strati.candidati_tecnici`. Vuoto se il DT non si trova."""
    try:
        from pack3d import tools
        dt = tools.dt_principale(pdf)
        if not dt:
            return []
        k = 72.0 / 25.4
        x, y, w, h = dt
        return strati.candidati_tecnici(pdf, (x * k, y * k, (x + w) * k, (y + h) * k))
    except Exception:
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # PORT e HOST arrivano dall'ambiente sui servizi di hosting; in locale
    # bastano gli argomenti. 0.0.0.0 serve per essere raggiungibili da fuori.
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("pack3d studio in ascolto su %s:%d" % (host, port))
    if host in ("0.0.0.0", "::"):
        print("  in locale:  http://localhost:%d" % port)
    # le analisi e le costruzioni in processi a parte, prima di aprire la
    # porta: i lavoratori nascono da un processo che non ha ancora thread
    lavoratori.avvia()
    ThreadingHTTPServer((host, port), Handler).serve_forever()
