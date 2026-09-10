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
import sys

from pack3d.tools import TOOLS, RUN

MODEL = os.environ.get("PACK3D_MODEL", "claude-sonnet-5")
MAX_STEPS = int(os.environ.get("PACK3D_MAX_STEPS", "16"))
# max_tokens e' un budget solo, diviso fra ragionamento e risposta. Al primo
# collaudo vero il log ha detto blocchi ['thinking'] con 8000/8000 token: il
# modello aveva speso tutto a ragionare e non gliene restava per chiamare
# presenta_risultato. Il ragionamento e' adattivo e attivo di default su
# questo modello, quindi il tetto va tenuto sopra a quanto chiede da solo: se
# il log torna a dire 'thinking' col budget esaurito, alzarlo ancora.
# Alzarlo riduce il caso, non lo elimina: vedi MAX_TRONCAMENTI
MAX_TOKENS = int(os.environ.get("PACK3D_MAX_TOKENS", "24000"))
# con un tetto alto l'SDK rifiuta da solo una richiesta non-streaming che
# stima possa sforare i dieci minuti. Un timeout esplicito disattiva quella
# stima e lascia il limite vero: quanto il chiamante e' disposto ad aspettare
TIMEOUT = float(os.environ.get("PACK3D_TIMEOUT", "600"))
# un troncamento non deve costare l'intera analisi: si riprova chiedendo una
# conclusione compatta. Due volte basta - se si tronca ancora il modello sta
# girando a vuoto, e insistere costa solo un'altra chiamata da 20-60 secondi
MAX_TRONCAMENTI = int(os.environ.get("PACK3D_MAX_TRONCAMENTI", "2"))

RIPRESA = (
    "La tua risposta precedente e' stata troncata perche' troppo lunga, quindi"
    " e' andata perduta: non l'ho ricevuta. Concludi ORA chiamando"
    " presenta_risultato con i dati che hai gia' misurato. Tieni \"avvisi\""
    " a poche righe e non ripetere le misure nel testo: quello che conta sono"
    " i campi numerici."
)

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


def _log_troncamento(r, traccia):
    """Cosa c'era nel turno perduto.

    Il testo grezzo da solo non basta: quando il troncamento arriva prima del
    primo blocco completo e' vuoto, e nei log non resta niente da leggere. I
    tipi di blocco e i token consumati dicono se il modello stava scrivendo
    prosa o una chiamata, e se ha davvero speso tutto il budget."""
    tipi = [getattr(b, "type", "?") for b in r.content] or ["nessuno"]
    u = getattr(r, "usage", None)
    sys.stderr.write(
        "  risposta troncata (max_tokens): blocchi %s, token in/out %s/%s,"
        " strumenti finora %s\n"
        % (tipi, getattr(u, "input_tokens", "?"),
           getattr(u, "output_tokens", "?"), [t["tool"] for t in traccia]))


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
        with open(p, encoding="utf-8") as fh:
            regole = fh.read()

    msgs = [{"role": "user", "content":
             "Tipologia dichiarata dall'utente: %s.\nRisposte alle domande: %s.\n"
             "Ricava le quote e i parametri di costruzione." % (kind, json.dumps(answers or {}, ensure_ascii=False))}]
    traccia = []
    troncati = 0
    system = ISTRUZIONI + "\n\n# Regole del progetto\n\n" + regole + "\n\n" + extra_system
    all_tools = TOOLS + [_conclude_tool(require_flowpack)]

    for _ in range(MAX_STEPS):
        r = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, timeout=TIMEOUT,
            system=system,
            tools=all_tools, messages=msgs)
        msgs.append({"role": "assistant", "content": r.content})

        calls = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
        finale = next((b for b in calls if b.name == "presenta_risultato"), None)
        if finale is not None:
            traccia.append({"tool": finale.name, "input": finale.input, "output": "conclusione"})
            return finale.input, traccia

        if r.stop_reason == "max_tokens":
            # Il turno troncato non si puo' rimandare indietro cosi' com'e':
            # se contiene un tool_use senza il suo tool_result la richiesta
            # dopo fallisce. Quindi si butta e si chiede la conclusione al
            # giro seguente, aggiungendo la richiesta al turno utente che c'e'
            # gia' - due turni utente di fila non sono una conversazione
            # valida. Le misure fatte restano: sono nella cronologia.
            _log_troncamento(r, traccia)
            msgs.pop()
            if troncati >= MAX_TRONCAMENTI:
                return {"errore": "risposta troncata a ogni tentativo",
                        "stop_reason": "max_tokens",
                        "strumenti_chiamati": [t["tool"] for t in traccia]}, traccia
            troncati += 1
            coda = msgs[-1]["content"]          # dopo la pop e' sempre utente
            if isinstance(coda, list):
                coda.append({"type": "text", "text": RIPRESA})
            else:
                msgs[-1]["content"] = coda + "\n\n" + RIPRESA
            continue

        if r.stop_reason != "tool_use":
            # rete di sicurezza: il modello ha risposto in prosa invece di
            # chiamare presenta_risultato. Qui stop_reason e' "end_turn": il
            # troncamento e' gestito sopra e non arriva fino a questo punto.
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
