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

MODEL = os.environ.get("PACK3D_MODEL", "claude-sonnet-5")
MAX_STEPS = int(os.environ.get("PACK3D_MAX_STEPS", "16"))
# una conclusione con molte misure e avvisi articolati puo' superare i 4000
# token di prima: con una cronologia lunga (analisi a fondo, piu' candidati
# confrontati) il rischio e' un troncamento a meta' di presenta_risultato,
# che lascia stop_reason diverso da "tool_use" e nessun testo utilizzabile
MAX_TOKENS = int(os.environ.get("PACK3D_MAX_TOKENS", "8000"))

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

Quando hai finito, concludi SEMPRE chiamando lo strumento presenta_risultato:
mai una risposta libera, nemmeno per spiegare un dubbio o un'incertezza (quello
ci va dentro "avvisi", che presenta_risultato ha comunque). E' l'unico modo per
concludere l'analisi.
"""

# strumento di chiusura: forzare la risposta finale come chiamata di uno
# strumento tipizzato è molto più affidabile che chiedere nel prompt di
# scrivere un blocco ```json — un modello che esita puo' sempre decidere di
# spiegarsi in prosa invece di seguire un formato descritto a parole, ma non
# puo' "quasi" chiamare uno strumento: o lo chiama con argomenti che rispettano
# lo schema, o non lo chiama.
_CONCLUDE_BASE = {
    "name": "presenta_risultato",
    "description": "Conclude l'analisi. Non e' uno strumento di misura: e' la "
                   "risposta finale, va chiamato una volta sola quando i dati "
                   "sono pronti.",
    "input_schema": {
        "type": "object",
        "properties": {
            "famiglia": {"type": "string"},
            "quote": {"type": "object"},
            "pulizia": {"type": "object", "properties": {
                "livello": {"type": "integer"}, "metodo": {"type": "string"}}},
            "parametri_costruzione": {"type": "object"},
            "avvisi": {"type": "array", "items": {"type": "string"}},
            "provenienza": {"type": "object"},
        },
        "required": ["famiglia", "quote", "avvisi"],
    },
}

FLOWPACK_SCHEMA = {
    "type": "object",
    "description": "Geometria del flowpack, tutti i valori in millimetri, misurati.",
    "properties": {
        "W": {"type": "number"}, "T": {"type": "number"}, "L": {"type": "number"},
        "end_fin": {"type": "number"}, "side_fin": {"type": "number"},
        "back_a": {"type": "number"}, "back_b": {"type": "number"},
        "web_mm": {"type": "number"}, "step_mm": {"type": "number"},
        "sheet_x0_mm": {"type": "number"}, "sheet_y0_mm": {"type": "number"},
    },
    "required": ["W", "T", "L", "end_fin", "side_fin", "back_a", "back_b",
                "web_mm", "step_mm", "sheet_x0_mm", "sheet_y0_mm"],
}


def _conclude_tool(require_flowpack):
    t = json.loads(json.dumps(_CONCLUDE_BASE))    # copia profonda
    if require_flowpack:
        t["input_schema"]["properties"]["flowpack"] = FLOWPACK_SCHEMA
        t["input_schema"]["required"].append("flowpack")
    return t


def _json_from(text):
    """Rete di sicurezza per quando il modello risponde in prosa nonostante
    tutto, invece di chiamare presenta_risultato: prova comunque a salvare un
    JSON dal testo, e se non ci riesce restituisce il testo grezzo per poterlo
    almeno leggere nei log invece di perderlo."""
    m = re.search(r"```json\s*(.+?)```", text, re.S)
    raw = m.group(1) if m else text
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {"errore": "risposta non interpretabile", "testo_grezzo": text[:2000]}


def analyse(pdf_path, kind, answers=None, regole_path=None, client=None,
           extra_system="", require_flowpack=False):
    """Esegue il ciclo e restituisce (parametri, traccia delle chiamate).

    `extra_system` aggiunge istruzioni in coda al system prompt senza toccare
    quello standard: serve ai chiamanti che hanno bisogno di uno schema JSON
    piu' rigido di quello generico (es. il ripiego AI del flowpack).
    `require_flowpack` rende obbligatorio il campo "flowpack" (con lo schema
    tipizzato) nello strumento di chiusura presenta_risultato."""
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
    system = ISTRUZIONI + "\n\n# Regole del progetto\n\n" + regole + "\n\n" + extra_system
    all_tools = TOOLS + [_conclude_tool(require_flowpack)]

    for _ in range(MAX_STEPS):
        r = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            system=system,
            tools=all_tools, messages=msgs)
        msgs.append({"role": "assistant", "content": r.content})

        calls = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
        finale = next((b for b in calls if b.name == "presenta_risultato"), None)
        if finale is not None:
            traccia.append({"tool": finale.name, "input": finale.input, "output": "conclusione"})
            return finale.input, traccia

        if r.stop_reason != "tool_use":
            # rete di sicurezza: il modello ha risposto in prosa (o e' stato
            # troncato) invece di chiamare presenta_risultato. stop_reason
            # distingue i due casi nei log: "max_tokens" e' un troncamento,
            # "end_turn" e' davvero prosa.
            testo = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            risultato = _json_from(testo)
            if isinstance(risultato, dict) and "errore" in risultato:
                risultato["stop_reason"] = r.stop_reason
            return risultato, traccia

        risultati = []
        for b in calls:
            fn = RUN.get(b.name)
            out = fn(pdf_path, **(b.input or {})) if fn else {"errore": "tool sconosciuto"}
            traccia.append({"tool": b.name, "input": b.input, "output": out})
            risultati.append({"type": "tool_result", "tool_use_id": b.id,
                              "content": json.dumps(out, ensure_ascii=False)})
        msgs.append({"role": "user", "content": risultati})

    return {"errore": "troppi passi senza conclusione"}, traccia
