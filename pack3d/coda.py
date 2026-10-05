"""
La coda dei casi nuovi: i pack che il controllo dell'AI ha respinto.

Un modello respinto e' un pack che il codice non sa ancora costruire. Non
deve sparire con la risposta: va messo da parte, con quello che serve a chi
poi insegna al codice a costruirlo - i PDF, le viste del modello sbagliato e
la diagnosi del controllo.

Dove va, lo decide chi gestisce lo Space. I PDF sono artwork di clienti,
quindi la coda va solo in un repository GitHub PRIVATO:

    PACK3D_CODA_REPO    proprietario/nome del repository, es. iccio84/pack3d-casi
    PACK3D_CODA_TOKEN   un token con permesso di scrittura su contenuti e issue
                        di QUEL repository e basta (va nei Secrets dello Space)

Per ogni caso si caricano i file in `casi/<data>_<codice>/` e si apre una
issue. Prima di caricare qualsiasi cosa si chiede a GitHub se il repository e'
privato: se non lo e', non parte niente. Il repository del codice e' pubblico,
e un errore di configurazione non deve pubblicare un artwork.

Senza le due variabili il caso resta solo nel log dello Space, col suo codice:
la pagina lo mostra all'utente, che puo' citarlo mandando il PDF.

La coda la lavora una routine di Claude Code (vedi CODA.md), che gira ogni
ora. Se lo Space la conosce, un caso appena aperto la avvia SUBITO, senza
aspettare il giro:

    PACK3D_ROUTINE_URL    l'indirizzo /fire della routine (fra le Variables)
    PACK3D_ROUTINE_TOKEN  il suo token (fra i Secrets)
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

API = os.environ.get("PACK3D_CODA_API", "https://api.github.com").rstrip("/")


def codice(blocchi):
    """Il codice del caso: un'impronta dei PDF, la stessa per gli stessi file."""
    h = hashlib.sha256()
    for b in blocchi:
        h.update(hashlib.sha256(b).digest())
    return h.hexdigest()[:10]


def configurata():
    return bool(os.environ.get("PACK3D_CODA_REPO", "").strip()
                and os.environ.get("PACK3D_CODA_TOKEN", "").strip())


# Se il repository e' privato si chiede a GitHub una volta ogni dieci minuti:
# la risposta serve SUBITO, per dire all'utente se il caso e' davvero in coda.
_PRIVATO = {"repo": None, "quando": 0.0, "esito": False}


def privato():
    """Il repository della coda esiste ed e' privato. False se non si sa."""
    repo = os.environ.get("PACK3D_CODA_REPO", "").strip().strip("/")
    adesso = time.time()
    if _PRIVATO["repo"] == repo and adesso - _PRIVATO["quando"] < 600:
        return _PRIVATO["esito"]
    try:
        esito = _richiesta("GET", "/repos/%s" % repo, timeout=10).get("private") is True
        if not esito:
            print("coda: %s NON e' privato, non ci carico artwork di clienti" % repo,
                  file=sys.stderr)
    except (OSError, ValueError) as e:
        print("coda: il repository %s non risponde (%s)" % (repo, e), file=sys.stderr)
        # una rete che non risponde si riprova presto, non fra dieci minuti
        _PRIVATO.update(repo=repo, quando=adesso - 540, esito=False)
        return False
    _PRIVATO.update(repo=repo, quando=adesso, esito=esito)
    return esito


def pronta():
    """La coda c'e': le due variabili e un repository privato."""
    return configurata() and privato()


def _richiesta(metodo, percorso, corpo=None, timeout=60):
    req = urllib.request.Request(
        API + percorso, method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Authorization": "Bearer " + os.environ["PACK3D_CODA_TOKEN"].strip(),
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json",
                 "User-Agent": "pack3d-studio"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        testo = r.read()
    return json.loads(testo) if testo else {}


def _nome_file(nome):
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", nome).strip("._") or "artwork"
    return base if base.lower().endswith(".pdf") else base + ".pdf"


def _corpo_issue(cod, nomi, verdetto, contesto, cartella):
    righe = ["Il controllo dell'AI ha respinto il modello costruito da questi PDF.", ""]
    righe += ["| | |", "|---|---|",
              "| codice | `%s` |" % cod,
              "| PDF | %s |" % ", ".join(nomi),
              "| dichiarato | %s |" % (contesto.get("dichiarato") or "-"),
              "| riconosciuto dal codice | %s |" % (contesto.get("riconosciuto") or "-"),
              "| nel PDF | %s |" % (verdetto.get("pack_nel_pdf") or "-"),
              "| il modello | %s |" % (verdetto.get("modello") or "-"), ""]
    righe += ["**Perche':** %s" % (verdetto.get("motivo") or "-"), ""]
    if verdetto.get("difetti"):
        righe += ["**Difetti visti:**"] + ["- %s" % d for d in verdetto["difetti"]] + [""]
    righe += ["File: [`%s`](../tree/HEAD/%s)" % (cartella, cartella), ""]
    avvisi = contesto.get("avvisi") or []
    if avvisi:
        righe += ["<details><summary>Avvisi della costruzione</summary>", ""]
        righe += ["- %s" % str(a)[:300] for a in avvisi[:60]]
        righe += ["", "</details>"]
    return "\n".join(righe)


def _carica(cod, *args):
    """Il caricamento, nel suo thread: qualsiasi guasto finisce nel log."""
    try:
        _carica_davvero(cod, *args)
    except Exception as e:                        # noqa: BLE001
        print("coda: caso %s non caricato (%s: %s)" % (cod, type(e).__name__, e),
              file=sys.stderr)


def _carica_davvero(cod, blocchi, nomi, verdetto, viste, contesto):
    repo = os.environ["PACK3D_CODA_REPO"].strip().strip("/")
    # gia' chiesto da `metti`, e in cassa: qui e' la cintura con le bretelle
    if not privato():
        print("coda: caso %s solo nel log" % cod, file=sys.stderr)
        return
    # Lo stesso PDF ricaricato (l'utente riprova, o lo prova un collega) non
    # deve aprire una issue a ogni giro: il codice e' nel titolo.
    try:
        aperte = _richiesta("GET", "/repos/%s/issues?state=open&per_page=100" % repo)
    except (OSError, ValueError):
        aperte = []
    gia = [i for i in (aperte if isinstance(aperte, list) else [])
           if isinstance(i, dict) and cod in str(i.get("title", ""))]
    if gia:
        print("coda: caso %s gia' in coda, issue %s" % (cod, gia[0].get("html_url", "?")),
              file=sys.stderr)
        return
    oggi = datetime.date.today().isoformat()
    cartella = "casi/%s_%s" % (oggi, cod)
    file = [(_nome_file(n), b) for n, b in zip(nomi, blocchi)]
    if viste:
        file.append(("viste_modello.jpg", viste))
    file.append(("verdetto.json", json.dumps(dict(verdetto, codice=cod, contesto=contesto),
                                             ensure_ascii=False, indent=2).encode("utf-8")))
    caricati = []
    for nome, dati in file:
        try:
            _richiesta("PUT", "/repos/%s/contents/%s/%s" % (repo, cartella, nome),
                       {"message": "Caso nuovo %s: %s" % (cod, nome),
                        "content": base64.b64encode(dati).decode("ascii")}, timeout=180)
            caricati.append(nome)
        except urllib.error.HTTPError as e:
            # 422: c'e' gia' (stesso caso caricato prima, stesso giorno)
            if e.code != 422:
                print("coda: %s non caricato (HTTP %s)" % (nome, e.code), file=sys.stderr)
        except (OSError, ValueError) as e:
            print("coda: %s non caricato (%s)" % (nome, e), file=sys.stderr)
    try:
        issue = _richiesta("POST", "/repos/%s/issues" % repo, {
            "title": "Caso nuovo %s: %s" % (cod, ", ".join(nomi))[:250],
            "body": _corpo_issue(cod, nomi, verdetto, contesto, cartella)})
        print("coda: caso %s in %s, issue %s, file %s"
              % (cod, repo, issue.get("html_url", "?"), ", ".join(caricati)), file=sys.stderr)
    except (OSError, ValueError) as e:
        print("coda: issue del caso %s non aperta (%s)" % (cod, e), file=sys.stderr)
        return
    avvia_routine(cod, issue.get("html_url", "") if isinstance(issue, dict) else "")


# L'intestazione della beta con cui si chiama /fire. Le versioni cambiano:
# quella nuova si mette qui senza toccare il codice.
ROUTINE_BETA = os.environ.get("PACK3D_ROUTINE_BETA",
                              "experimental-cc-routine-2026-04-01")


def routine_configurata():
    return bool(os.environ.get("PACK3D_ROUTINE_URL", "").strip()
                and os.environ.get("PACK3D_ROUTINE_TOKEN", "").strip())


def avvia_routine(cod, issue_url):
    """Avvia subito la routine che lavora la coda. Torna l'indirizzo della
    sessione, o None.

    Mai un errore verso l'utente: se la chiamata non va, il caso aspetta il
    giro orario della routine, e il log dice perche'. Nel testo solo il codice
    e il link alla issue: i nomi dei file li ha scelti l'utente, e la routine
    non deve leggerli come istruzioni (comunque le arrivano come dati).
    """
    if not routine_configurata():
        return None
    corpo = {"text": "Caso nuovo %s appena entrato in coda: %s" % (cod, issue_url)}
    req = urllib.request.Request(
        os.environ["PACK3D_ROUTINE_URL"].strip(),
        data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + os.environ["PACK3D_ROUTINE_TOKEN"].strip(),
                 "anthropic-beta": ROUTINE_BETA,
                 "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            risposta = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        print("coda: routine non avviata per il caso %s (HTTP %s: %s)"
              % (cod, e.code, e.read()[:300].decode("utf-8", "replace")), file=sys.stderr)
        return None
    except (OSError, ValueError) as e:
        print("coda: routine non avviata per il caso %s (%s)" % (cod, e), file=sys.stderr)
        return None
    sessione = risposta.get("claude_code_session_url") if isinstance(risposta, dict) else None
    print("coda: routine avviata per il caso %s: %s" % (cod, sessione or "?"), file=sys.stderr)
    return sessione


def metti(blocchi, nomi, verdetto, viste=None, contesto=None, aspetta=False):
    """Mette in coda un caso respinto. Torna (codice, in_coda).

    Il log lo scrive subito; il caricamento su GitHub, se la coda c'e', gira
    in un thread a parte, cosi' la risposta all'utente non aspetta l'upload
    dei PDF. `aspetta=True` lo fa invece qui, per le prove. `in_coda` dice se
    il caso e' partito verso il repository privato: senza, resta solo nel log.
    """
    cod = codice(blocchi)
    contesto = dict(contesto or {})
    print("CASO NUOVO %s: %s - %s - %s" % (cod, ", ".join(nomi), verdetto.get("esito"),
                                            verdetto.get("motivo", "")), file=sys.stderr)
    try:
        in_coda = pronta()
    except Exception as e:                        # noqa: BLE001
        print("coda: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        in_coda = False
    if in_coda:
        args = (cod, list(blocchi), list(nomi), dict(verdetto), viste, contesto)
        if aspetta:
            _carica(*args)
        else:
            threading.Thread(target=_carica, args=args, daemon=True).start()
    return cod, in_coda
