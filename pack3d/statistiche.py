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
va a ogni ripartenza: il rilascio della settimana lo salva nel registro dei
casi prima di pubblicare (RILASCIO.md). `PACK3D_STATISTICHE=0` lo spegne (il
parco non conta: sono prove, non utenti).
"""
from __future__ import annotations

import json
import os
import re
import time

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


def riassunto():
    """Le righe sommate: per evento, i conti per famiglia dichiarata e letta,
    per esito e per motivo, piu' la prima e l'ultima volta."""
    conti, prima, ultima, n = {}, None, None, 0
    for f in (FILE + ".1", FILE) if FILE else ():
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
