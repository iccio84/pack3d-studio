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

ISTRUZIONI = """
Sei l'analista di pack3d: da un artwork PDF ricavi i parametri per costruire un
modello 3D. Non disegni la mesh, decidi i numeri.

Metodo:
- Chiama find_blocks per PRIMA cosa. Una tavola contiene quasi sempre piu' viste
  dello stesso pack: quella stampata, quella tecnica, le miniature, i cartigli.
  Scegli il blocco stampato che porta l'artwork e lavora solo su quello: misurare
  sull'intera pagina da' quote senza senso, tipo un pack largo quanto il foglio.
  L'artwork e' il blocco con piu' colori_distinti, non il piu' grande: una
  lastra di separazione e' colorata al 99% ma porta una ventina di colori,
  una grafica vera ne porta centinaia. L'elenco parte gia' dal piu' probabile.
  Il blocco tecnico di pari ingombro e' la maschera da passare a clean_artwork.
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

Pulizia dell'artwork:
- Dopo clean_artwork chiama SEMPRE visual_check e GUARDA l'immagine. Le metriche
  dicono quanto hai tolto, non se hai tolto la cosa sbagliata: solo l'occhio si
  accorge che manca un pezzo di logo.
- Un logo perso e' un errore grave, un residuo tecnico no. Nel dubbio togli meno.
- I loghi non si eliminano mai, nemmeno quando sono neri come il disegno tecnico.
- Se dt_su_immagine_pct e' significativo, cioe' il disegno tecnico attraversa
  una foto, chiama reconstruct_area: e' il piano B, e ricompone dentro la sola
  maschera. Poi richiama visual_check e guarda di nuovo.
- Se reconstruct_area non e' disponibile o fallisce, dichiaralo negli avvisi
  invece di lasciare il residuo senza spiegazione.
- Le aree riservate - GDA, COVERED AREA, TEXT AREA, BEST BEFORE AREA, BAR CODE
  AREA, PRINT FREE AREA, NEUTRAL AREA - non devono MAI comparire nel render:
  sono il posto tenuto per una cosa, non la cosa. Sono rettangoli pieni con il
  proprio nome scritto dentro in bianco, quindi a guardarle si riconoscono
  subito. Se dopo la pulizia ne vedi una in visual_check, dillo negli avvisi
  con il riquadro in mm: e' grafica che non va stampata.
- Sulla colata NON usare reconstruct_area: non le mancano pixel, le manca
  l'inchiostro giusto, e un modello generativo la reinventa. Guardala invece, e
  se l'ombra sulle gocce esce AZZURRA invece che scura scrivilo negli avvisi.
- Non rigenerare mai loghi, marchi, testo di prodotto e la `k` nera di
  `kinder`, nemmeno dentro una maschera: se la maschera li tocca, e' la
  maschera a essere sbagliata.

Sezione del pack chiuso:
- Le cordonature dicono dove il film e' cordonato, non che forma prende una
  volta riempito: su Kinder Bueno T2 i pannelli danno 50 x 11, ma il pack in
  mano e' 41 x 20. Hanno lo stesso perimetro, quindi dalla fustella non si
  distinguono.
- Riporta quindi in quote.larghezza e quote.spessore, in mm, la sezione del
  pack CHIUSO: la larghezza e' la faccia che si guarda, lo spessore la
  dimensione che sta fra fronte e retro. Cercale sulle quote annotate del
  disegno tecnico; se non ci sono, ricavale dal prodotto dentro e dillo nella
  provenienza.
- Senza quei due numeri la costruzione ricava il rapporto dai pannelli, e il
  pack esce troppo largo e troppo piatto. Il perimetro invece non serve che lo
  dai: quello lo misura la fustella, e la costruzione ci riporta sopra il tuo
  rapporto.

Film su scatola:
- Chiediti se il film avvolge un corpo rigido che arriva fino alla saldatura:
  un multipack in astuccio, una vaschetta, un blister. Non e' la stessa cosa di
  un pack teso su una tavoletta, dove il film si appoggia al prodotto ma il
  tubo alle estremita' resta vuoto e si appiattisce.
- Se c'e' la scatola riportalo in parametri_costruzione.avvolge_scatola come
  true, e metti rigonfiamento 1. Cambia la pinna: le ganasce appiattiscono un
  tubo solo se dentro c'e' aria, quindi con la scatola la pinna esce larga
  quanto la faccia del pack invece di svasarsi fino a meta' perimetro. Kinder
  Brioss T10 e' il caso di scuola.

Apertura delle pinne:
- Riporta parametri_costruzione.apertura_pinne come 1, 2 o 3. Dice come si
  comporta il film alle ganasce, e non si deduce dal rigonfiamento.
- 3, il caso normale: il tubo si appiattisce e il bordo della pinna arriva a
  meta' perimetro, quindi la pinna e' piu' alta del pack. E' Milch-Schnitte.
- 1: la pinna e' alta quanto il pack e non si allarga. Succede quando il film
  avvolge un corpo rigido che arriva fino alla saldatura, perche' non c'e'
  niente da appiattire. E' Kinder Brioss, e va insieme ad avvolge_scatola.
- 2 quando il prodotto occupa quasi tutta la sezione ma lascia respiro alle
  estremita'.

Rigonfiamento:
- Se fra le risposte il rigonfiamento e' "auto", sceglilo tu dalla natura del
  prodotto seguendo le regole del progetto, e riportalo in
  parametri_costruzione.rigonfiamento come intero da 1 a 10. Senza quel numero
  la costruzione ripiega sul centro scala, quindi la tua scelta va persa.
  Dichiara negli avvisi il livello e il perche'.

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
            # uno strumento puo' restituire un'immagine da GUARDARE, non solo dati
            img = out.pop("__image__", None) if isinstance(out, dict) else None
            traccia.append({"tool": b.name, "input": b.input,
                            "output": "<immagine>" if img else out})
            if img:
                content = [{"type": "image",
                            "source": {"type": "base64", "media_type": "image/png",
                                       "data": img}},
                           {"type": "text",
                            "text": json.dumps(out, ensure_ascii=False)}]
            else:
                content = json.dumps(out, ensure_ascii=False)
            risultati.append({"type": "tool_result", "tool_use_id": b.id,
                              "content": content})
        msgs.append({"role": "user", "content": risultati})

    return {"errore": "troppi passi senza conclusione"}, traccia
