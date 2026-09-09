"""
Il ciclo che porta il ragionamento della chat dentro l'app.

Claude non produce geometria: orchestra. Riceve le regole nel system prompt,
chiama gli strumenti di misura, controlla che i conti chiudano e restituisce un
JSON piccolo di parametri. La mesh la costruisce il codice.
"""
from __future__ import annotations

import json
import os
import re

from pack3d.tools import TOOLS, RUN

MODEL = os.environ.get("PACK3D_MODEL", "claude-sonnet-4-6")
MAX_STEPS = int(os.environ.get("PACK3D_MAX_STEPS", "16"))

ISTRUZIONI = """
Sei l'analista di pack3d: da un artwork PDF ricavi i parametri per costruire un
modello 3D. Non disegni la mesh, decidi i numeri.

Metodo:
- Non stimare mai una quota che puoi misurare con uno strumento.
- Cerca sempre il disegno tecnico in miniatura con list_paths: sta fuori
  dall'ingombro dell'artwork ed e' piu' pulito del contorno sotto la grafica.
  Su piu' candidati scegli quello con il RESIDUO piu' basso.
- Verifica che i conti chiudano. Se due misure discordano, dillo: indica quale
  hai scelto e perche'.
- Su fit_sector guarda DUE numeri, non uno: residuo_mm basso non basta se
  scarto_archi_gradi e' alto. Un residuo di 0,001 mm con 14 gradi di scarto
  significa che hai adattato il cerchio a un pezzo sbagliato di contorno.
- Le domande all'utente sono gia' state poste: usa le risposte che ricevi e non
  chiederne altre.

Quando hai finito rispondi SOLO con un blocco ```json contenente:
{"famiglia": "...", "quote": {...}, "pulizia": {"livello": n, "metodo": "..."},
 "parametri_costruzione": {...}, "avvisi": ["..."], "provenienza": {"quota": "come e' stata ricavata"}}
"""


def _json_from(text):
    m = re.search(r"```json\s*(.+?)```", text, re.S)
    raw = m.group(1) if m else text
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {"errore": "risposta non interpretabile"}


def analyse(pdf_path, kind, answers=None, regole_path=None, client=None):
    """Esegue il ciclo e restituisce (parametri, traccia delle chiamate)."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()      # ANTHROPIC_API_KEY dall'ambiente

    regole = ""
    p = regole_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "REGOLE.md")
    if os.path.exists(p):
        regole = open(p, encoding="utf-8").read()

    msgs = [{"role": "user", "content":
             "Tipologia dichiarata dall'utente: %s.\nRisposte alle domande: %s.\n"
             "Ricava le quote e i parametri di costruzione." % (kind, json.dumps(answers or {}, ensure_ascii=False))}]
    traccia = []

    for _ in range(MAX_STEPS):
        r = client.messages.create(
            model=MODEL, max_tokens=4000,
            system=ISTRUZIONI + "\n\n# Regole del progetto\n\n" + regole,
            tools=TOOLS, messages=msgs)
        msgs.append({"role": "assistant", "content": r.content})

        if r.stop_reason != "tool_use":
            testo = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            return _json_from(testo), traccia

        risultati = []
        for b in r.content:
            if getattr(b, "type", "") != "tool_use":
                continue
            fn = RUN.get(b.name)
            out = fn(pdf_path, **(b.input or {})) if fn else {"errore": "tool sconosciuto"}
            traccia.append({"tool": b.name, "input": b.input, "output": out})
            risultati.append({"type": "tool_result", "tool_use_id": b.id,
                              "content": json.dumps(out, ensure_ascii=False)})
        msgs.append({"role": "user", "content": risultati})

    return {"errore": "troppi passi senza conclusione"}, traccia
