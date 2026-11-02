"""
Le statistiche del servizio: dove il codice si ferma sui PDF veri.

Il parco dice come vanno i casi che conosciamo; questo conta quelli che
arrivano. Per ogni lettura e costruzione, la famiglia dichiarata e quella
letta; per ogni fermata, perche'; per ogni modello, cosa ha detto il
controllo dell'AI. Cosi' si sa dove conviene rendere il codice piu'
tollerante, invece di indovinarlo.

Senza nomi ne' file: una riga JSON per evento (`conta`), in append su
`FILE` - i lavoratori sono processi a parte, e una riga corta in append non
si mescola con quella di un altro. `riassunto` le somma, e `/api/statistiche`
lo restituisce. Il motivo di una fermata si accorcia e perde i numeri
(`motivo`), perche' l'endpoint e' pubblico.

Il file sta nella cartella delle casse (`PACK3D_CACHE`) e sullo Space se ne
va a ogni ripartenza, compresa quella del rilascio e quella dopo due giorni
fermo. Per questo lo Space lo salva da solo nel registro dei casi
(`salva_nel_registro`): una volta al giorno e quando si spegne (il server,
al SIGTERM), se ci sono eventi nuovi. Un file per ogni vita dello Space,
`statistiche/spazio/<avvio>.jsonl`, riscritto a ogni salvataggio con tutti
gli eventi da quando e' partito: sommare tutti i file non conta niente due
volte (`python3 -m pack3d.statistiche FILE...`). Serve la coda configurata
(`pack3d.coda`, `PACK3D_CODA_REPO` e `PACK3D_CODA_TOKEN`); non serve che il
registro sia privato - sono gli stessi conti che `/api/statistiche` da' a
tutti - e cosi' alla chiusura basta una richiesta sola.

`PACK3D_STATISTICHE=0` lo spegne (il parco non conta: sono prove, non
utenti); `PACK3D_STATISTICHE_OGNI` cambia l'intervallo, in secondi.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.error

from . import dieline

_DOVE = os.environ.get("PACK3D_STATISTICHE", "")
FILE = (None if _DOVE == "0" else _DOVE or os.path.join(
    dieline.CACHE if dieline.CACHE and dieline.CACHE != "0" else "/tmp",
    "statistiche.jsonl"))
# oltre, il file diventa `.1` e si ricomincia: le ultime due settimane o giu' di li'
MAX_BYTE = 8 * 1024 * 1024


def motivo(e):
    """Il motivo di una fermata, accorciato: il tipo dell'errore e la prima
    frase, senza i numeri e senza quello che sta fra parentesi, che sono le
    misure del PDF e non il perche'."""
    t = str(e).strip().split("\n")[0]
    for _ in range(3):       # anche le parentesi dentro le parentesi
        t = re.sub(r"\([^()]*\)|\[[^\[\]]*\]", "", t)
    t = re.sub(r"\d+(?:[.,]\d+)?", "#", t)
    t = re.split(r"(?<=[^#])\. ", t)[0]
    t = re.sub(r"\s+", " ", t).strip(" :;,.-")
    return "%s: %s" % (type(e).__name__, t[:140]) if isinstance(e, BaseException) else t[:140]


def conta(evento, **campi):
    """Una riga: `evento` (lettura, costruzione, fermata, verdetto) e i suoi
    campi. Mai un errore: le statistiche non fermano niente."""
    if not FILE:
        return
    riga = dict(t=int(time.time()), e=evento)
    riga.update({k: v for k, v in campi.items() if v is not None})
    try:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        if os.path.exists(FILE) and os.path.getsize(FILE) > MAX_BYTE:
            os.replace(FILE, FILE + ".1")
        with open(FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(riga, ensure_ascii=False) + "\n")
    except OSError:
        pass


def riassunto(file=None):
    """Le righe sommate: per evento, i conti per famiglia dichiarata e letta,
    per esito e per motivo, piu' la prima e l'ultima volta. `file`: quali
    sommare (quelli salvati nel registro); senza, quelli di questo Space."""
    conti, prima, ultima, n = {}, None, None, 0
    if file is None:
        file = (FILE + ".1", FILE) if FILE else ()
    for f in file:
        try:
            with open(f, encoding="utf-8") as fh:
                righe = fh.readlines()
        except OSError:
            continue
        for r in righe:
            try:
                d = json.loads(r)
            except ValueError:
                continue
            n += 1
            prima = d["t"] if prima is None else min(prima, d["t"])
            ultima = d["t"] if ultima is None else max(ultima, d["t"])
            chiave = " | ".join(str(d[k]) for k in ("dichiarato", "letto", "fase",
                                                     "esito", "motivo") if k in d)
            per = conti.setdefault(d.get("e", "?"), {})
            per[chiave] = per.get(chiave, 0) + 1
    fuori = {e: [dict(cosa=k, quante=v) for k, v in
                 sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))]
             for e, c in sorted(conti.items())}
    return dict(eventi=n,
                dal=time.strftime("%Y-%m-%d %H:%M", time.gmtime(prima)) if prima else None,
                al=time.strftime("%Y-%m-%d %H:%M", time.gmtime(ultima)) if ultima else None,
                conti=fuori)


# --- il salvataggio nel registro dei casi ---------------------------------

CARTELLA = "statistiche/spazio"
OGNI_S = int(os.environ.get("PACK3D_STATISTICHE_OGNI") or 24 * 3600)
# la vita di questo Space: la fissa `avvia_salvataggio`, nel processo del server
_VITA = {"t": None, "nome": None, "parte": 1, "righe": 0, "sha": None}
_CHIAVE = threading.Lock()


def _righe_di_questa_vita():
    """Gli eventi da quando lo Space e' partito: se il file sopravvive a una
    ripartenza, quelli di prima stanno gia' nel file della vita di prima."""
    fuori = []
    for f in (FILE + ".1", FILE):
        try:
            with open(f, encoding="utf-8") as fh:
                righe = fh.readlines()
        except OSError:
            continue
        for r in righe:
            try:
                if json.loads(r)["t"] >= _VITA["t"]:
                    fuori.append(r if r.endswith("\n") else r + "\n")
            except (ValueError, KeyError, TypeError):
                continue
    return fuori


def salva_nel_registro(timeout=20):
    """Mette gli eventi di questa vita nel registro dei casi, se ce ne sono
    di nuovi. True se li ha salvati. Mai un errore: le statistiche non
    fermano niente, nemmeno la chiusura."""
    from . import coda
    if not FILE or _VITA["t"] is None or not coda.configurata():
        return False
    if not _CHIAVE.acquire(timeout=timeout):
        return False
    try:
        righe = _righe_di_questa_vita()
        if len(righe) == _VITA["righe"]:
            return False
        if len(righe) < _VITA["righe"]:
            # il file e' ruotato due volte e ha perso le righe gia' salvate:
            # quelle restano nel file di prima, le nuove in uno nuovo
            _VITA.update(parte=_VITA["parte"] + 1, sha=None)
        repo = os.environ["PACK3D_CODA_REPO"].strip().strip("/")
        nome = _VITA["nome"] + ("" if _VITA["parte"] == 1 else "_%d" % _VITA["parte"])
        percorso = "/repos/%s/contents/%s/%s.jsonl" % (repo, CARTELLA, nome)
        corpo = {"message": "Statistiche dello Space partito il %s: %d %s"
                            % (time.strftime("%Y-%m-%d alle %H:%M UTC", time.gmtime(_VITA["t"])),
                               len(righe), "evento" if len(righe) == 1 else "eventi"),
                 "content": base64.b64encode("".join(righe).encode("utf-8")).decode("ascii")}
        for k in range(2):
            corpo.pop("sha", None)
            if _VITA["sha"]:
                corpo["sha"] = _VITA["sha"]
            try:
                r = coda._richiesta("PUT", percorso, corpo, timeout=timeout)
                _VITA.update(righe=len(righe), sha=(r.get("content") or {}).get("sha"))
                return True
            except urllib.error.HTTPError as e:
                # 409 o 422: il file c'e' con un'altra impronta (un salvataggio
                # la cui risposta non e' arrivata) - si chiede quella giusta
                if k or e.code not in (409, 422):
                    raise
                try:
                    _VITA["sha"] = coda._richiesta("GET", percorso, timeout=timeout).get("sha")
                except urllib.error.HTTPError as e2:
                    if e2.code != 404:
                        raise
                    _VITA["sha"] = None
    except Exception as e:
        print("statistiche: non salvate nel registro (%s)" % e, file=sys.stderr)
    finally:
        _CHIAVE.release()
    return False


def avvia_salvataggio():
    """Nel processo del server, una volta: fissa la vita di questo Space e
    la salva nel registro ogni OGNI_S secondi (se ci sono eventi nuovi). La
    chiusura la salva il server, al SIGTERM."""
    if not FILE or _VITA["t"] is not None:
        return
    adesso = int(time.time())
    _VITA.update(t=adesso, nome=time.strftime("%Y-%m-%d_%H%M%S", time.gmtime(adesso)))

    def giro():
        while True:
            time.sleep(OGNI_S)
            try:
                salva_nel_registro()
            except Exception:
                traceback.print_exc()

    threading.Thread(target=giro, name="statistiche", daemon=True).start()


if __name__ == "__main__":
    # i file salvati nel registro, sommati:
    #     python3 -m pack3d.statistiche ../pack3d-casi/statistiche/spazio/*.jsonl
    print(json.dumps(riassunto(sys.argv[1:] or None), ensure_ascii=False, indent=1))
