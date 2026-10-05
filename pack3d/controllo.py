"""
Il controllo dell'AI: prima di consegnare un modello, Claude lo guarda.

Il codice costruisce, e sui pack che conosce costruisce bene. Su un pack che
non conosce pero' non si ferma: costruisce la cosa piu' vicina che sa fare e
la consegna come se fosse giusta. Il cono Camy caricato in un pezzo usciva
come un astuccio, e il solutore non aveva modo di accorgersene: i suoi conti
tornavano, sul pack sbagliato.

Qui Claude guarda quello che guarderebbe una persona - la pagina del PDF e il
modello da quattro lati - e dice se e' il pack giusto. E' una chiamata sola,
con le immagini. Se il modello non torna, all'utente non arriva come buono:
la pagina dice "caso nuovo" e il caso va in coda (`coda.py`), per chi poi
insegna al codice a costruirlo.

Il controllo non rompe mai la costruzione per colpa sua. Senza chiave, con la
rete giu', con una risposta che non si capisce, il modello si consegna come
prima e un avviso dice che il controllo non c'e' stato.

Il modello di Claude e' quello dell'agente (`PACK3D_MODEL`, vedi agent.py), o
`PACK3D_MODEL_CONTROLLO` se si vuole un modello diverso per il solo controllo.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time

from . import vista

ESITI = ("ok", "dubbio", "sbagliato")
NON_CONTROLLATO = "non controllato"

# Quanto si aspetta la risposta. Il controllo arriva dopo una costruzione che
# ha gia' fatto aspettare l'utente: oltre questo il modello si consegna senza.
TIMEOUT = float(os.environ.get("PACK3D_CONTROLLO_TIMEOUT", "120"))

SCHEMA_VERDETTO = {
    "type": "object",
    "properties": {
        "esito": {"type": "string", "enum": list(ESITI)},
        "pack_nel_pdf": {"type": "string"},
        "modello": {"type": "string"},
        "motivo": {"type": "string"},
        "difetti": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["esito", "pack_nel_pdf", "modello", "motivo", "difetti"],
    "additionalProperties": False,
}

ISTRUZIONI = """\
Sei il controllo qualita' di pack3d, un servizio che da un artwork PDF di
packaging costruisce il modello 3D del pack montato. Ricevi:
- la prima pagina di ogni PDF del pack, uno per pezzo: e' il foglio steso,
  con la grafica e quasi sempre il disegno tecnico (fustella, quote, note,
  barre colore);
- quattro viste del modello 3D costruito (fronte, tre quarti, retro, dall'alto)
  in un'immagine sola. Sono rese al computer: luce semplice, sfondo grigio, e
  solo le facce rivolte verso chi guarda, come nel visore del servizio;
- un riassunto della costruzione: la tipologia dichiarata dall'utente, quella
  riconosciuta dal codice, le misure del modello, gli avvisi del codice.

Devi dire se il modello e' il pack di quel PDF, montato.

"sbagliato" quando chi ha caricato il PDF, guardando il modello, direbbe che
non e' il suo pack:
- forma o famiglia sbagliata: il foglio e' un cono e il modello e' una scatola,
  il foglio e' un astuccio e il modello e' un flowpack;
- manca un pezzo che il PDF ha (un tappo, un lid, una plancia), o ce n'e' uno
  che il PDF non ha;
- proporzioni lontane da quelle del foglio: un pannello lungo il doppio, una
  scatola schiacciata;
- grafica evidentemente fuori posto: il fronte sul retro o capovolto, pannelli
  scambiati, grafica tagliata a meta' o deformata, facce bianche dove il
  foglio e' stampato;
- geometria rotta: buchi, facce mancanti, pezzi che si compenetrano, superfici
  che si vedono da dentro.

"dubbio" quando qualcosa potrebbe non tornare ma dalle immagini non si puo'
dire con certezza.

"ok" quando il modello e' il pack del PDF, montato, con la grafica al suo
posto. Non cercare la perfezione: e' un modello di presentazione, non una
prova colore.

Non sono difetti, perche' il servizio li toglie o li lascia di proposito:
- il disegno tecnico, le quote, le note, le barre e le patch di colore, i
  crocini, i testi fuori dal pack;
- i box colorati delle aree riservate (lotto, scadenza, EAN) e la tabella GDA:
  sul modello restano vuoti o bianchi;
- l'interno del cartone, grigio o color carta, dove il pack e' aperto o ha una
  finestra;
- le parti non stampate del foglio (alette di colla, linguette) che nel pack
  montato stanno dentro.

Scrivi in italiano semplice, per chi lavora nel packaging e non per un
programmatore:
- pack_nel_pdf: che pack c'e' nel PDF (tipo, pezzi, forma), in una frase;
- modello: cosa mostra il modello, in una frase;
- motivo: perche' l'esito, in una o due frasi;
- difetti: i difetti che vedi, uno per voce; vuoto se non ce ne sono.
"""


def _spento_apposta():
    return os.environ.get("PACK3D_CONTROLLO", "1").strip().lower() in ("0", "no", "off", "false")


def _chiave():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def attivo():
    """C'e' una chiave e nessuno ha spento il controllo con PACK3D_CONTROLLO=0."""
    return _chiave() and not _spento_apposta()


def manca_la_chiave():
    """Spento solo perche' la chiave non c'e': chi gestisce lo Space va avvisato."""
    return not _chiave() and not _spento_apposta()


def modello_ai():
    """Il modello di Claude per il controllo: quello dell'agente, se non c'e' altro."""
    scelto = os.environ.get("PACK3D_MODEL_CONTROLLO", "").strip()
    if scelto:
        return scelto
    import agent
    return agent.MODEL


def _jpeg(im, qualita=88):
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=qualita)
    return b.getvalue()


def prepara(pdfs, glb_path, lato_pagina=1400, lato_vista=512):
    """Le immagini del controllo.

    Rasterizza le pagine con pdfium, quindi va chiamata DENTRO il posto di
    costruzione, come ogni altra rasterizzazione. Il resto del controllo - la
    chiamata, che e' solo attesa di rete - sta fuori, cosi' il prossimo
    utente non aspetta la risposta di Claude per costruire.
    """
    pagine, fogli = [], []
    for p in pdfs:
        im, foglio = vista.pagina(p, lato_pagina, misure=True)
        pagine.append(_jpeg(im))
        fogli.append(foglio)
    tav, ingombro = vista.viste(glb_path, lato_vista)
    return dict(pagine=pagine, fogli=fogli, viste=_jpeg(tav), ingombro=ingombro)


def _immagine(dati):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(dati).decode("ascii")}}


def _riassunto(contesto, ingombro, fogli=()):
    righe = []
    for k, (w, h) in enumerate(fogli or ()):
        quale = " %d" % (k + 1) if len(fogli) > 1 else ""
        righe.append("Foglio del PDF%s: %.0f x %.0f mm." % (quale, w, h))
    if contesto.get("dichiarato"):
        righe.append("Tipologia dichiarata dall'utente: %s." % contesto["dichiarato"])
    if contesto.get("riconosciuto"):
        righe.append("Riconosciuta dal codice: %s." % contesto["riconosciuto"])
    if ingombro:
        righe.append("Misure del modello: %.0f x %.0f x %.0f mm (larghezza x altezza x "
                     "profondita')." % tuple(ingombro))
    avvisi = [str(a)[:240] for a in contesto.get("avvisi") or []][:40]
    if avvisi:
        righe.append("Avvisi della costruzione:")
        righe.extend("- " + a for a in avvisi)
    return "\n".join(righe)


def _non_controllato(motivo, t0=None):
    v = {"esito": NON_CONTROLLATO, "pack_nel_pdf": "", "modello": "",
         "motivo": motivo, "difetti": []}
    if t0 is not None:
        v["secondi"] = round(time.time() - t0, 1)
    return v


def _errore_api(e, modello):
    """L'errore della chiamata detto in modo che chi gestisce lo Space sappia cosa fare."""
    import anthropic
    if isinstance(e, anthropic.AuthenticationError):
        return "la chiave API non e' valida (ANTHROPIC_API_KEY)"
    if isinstance(e, anthropic.PermissionDeniedError):
        return "la chiave API non ha il permesso di usare il modello %s" % modello
    if isinstance(e, anthropic.NotFoundError):
        return "il modello %s non esiste: controlla PACK3D_MODEL" % modello
    if isinstance(e, anthropic.RateLimitError):
        return "troppe richieste o credito esaurito sulla chiave API"
    if isinstance(e, anthropic.BadRequestError):
        corpo = getattr(e, "body", None)
        dettaglio = (corpo.get("error") or {}).get("message") if isinstance(corpo, dict) else None
        return "richiesta rifiutata: %s" % str(dettaglio or getattr(e, "message", e))[:200]
    if isinstance(e, anthropic.APITimeoutError):
        return "nessuna risposta in %.0f s" % TIMEOUT
    if isinstance(e, anthropic.APIConnectionError):
        return "rete non raggiungibile"
    if isinstance(e, anthropic.APIStatusError):
        return "errore del servizio (HTTP %s)" % getattr(e, "status_code", "?")
    return "%s: %s" % (type(e).__name__, str(e)[:200])


def _chiama(contenuto, istruzioni, schema, modello, client, max_tokens=16000):
    """Una chiamata con risposta JSON vincolata allo schema. Torna (dati, None) o (None, motivo)."""
    try:
        import anthropic
    except ImportError:
        return None, "manca la libreria anthropic"
    try:
        if client is None:
            client = anthropic.Anthropic(timeout=TIMEOUT, max_retries=1)
        config = {"format": {"type": "json_schema", "schema": schema}}
        sforzo = os.environ.get("PACK3D_EFFORT_CONTROLLO", "medium").strip()
        if sforzo:
            config["effort"] = sforzo
        r = client.messages.create(
            model=modello, max_tokens=max_tokens, system=istruzioni,
            output_config=config,
            messages=[{"role": "user", "content": contenuto}])
    except Exception as e:                        # noqa: BLE001 - mai rompere la costruzione
        return None, _errore_api(e, modello)
    if r.stop_reason == "refusal":
        return None, "Claude ha rifiutato di rispondere"
    if r.stop_reason == "max_tokens":
        return None, "risposta troncata"
    testo = "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text")
    try:
        return json.loads(testo), None
    except ValueError:
        return None, "risposta non interpretabile"


def giudica(quadro, contesto, modello=None, client=None):
    """Il verdetto sul modello: dict con esito (ok, dubbio, sbagliato o
    "non controllato"), pack_nel_pdf, modello, motivo, difetti, secondi.

    `quadro` viene da `prepara`; `contesto` ha dichiarato, riconosciuto,
    avvisi e nomi (i nomi dei PDF, nell'ordine delle pagine). Non lancia mai:
    il modello e' gia' costruito, e un guasto del controllo non lo deve
    portare via con se'.
    """
    t0 = time.time()
    try:
        return _giudica(quadro, contesto, modello, client, t0)
    except Exception as e:                        # noqa: BLE001
        return _non_controllato("%s: %s" % (type(e).__name__, str(e)[:200]), t0)


def _giudica(quadro, contesto, modello, client, t0):
    modello = modello or modello_ai()
    nomi = contesto.get("nomi") or []
    pagine = quadro["pagine"]
    contenuto = []
    for k, dati in enumerate(pagine):
        nome = nomi[k] if k < len(nomi) else "PDF %d" % (k + 1)
        if len(pagine) > 1:
            didascalia = "Prima pagina del PDF \"%s\" (pezzo %d di %d):" % (nome, k + 1, len(pagine))
        else:
            didascalia = "Prima pagina del PDF \"%s\":" % nome
        contenuto += [{"type": "text", "text": didascalia}, _immagine(dati)]
    contenuto += [{"type": "text", "text": "Le quattro viste del modello 3D costruito:"},
                  _immagine(quadro["viste"]),
                  {"type": "text", "text": _riassunto(contesto, quadro.get("ingombro"), quadro.get("fogli"))
                   + "\n\nE' il pack del PDF, montato?"}]
    dati, errore = _chiama(contenuto, ISTRUZIONI, SCHEMA_VERDETTO, modello, client)
    if errore:
        return _non_controllato(errore, t0)
    if not isinstance(dati, dict) or dati.get("esito") not in ESITI:
        return _non_controllato("risposta senza esito", t0)
    v = {k: dati.get(k, "") for k in ("esito", "pack_nel_pdf", "modello", "motivo")}
    v = {k: str(x).strip() for k, x in v.items()}
    v["difetti"] = [str(d).strip() for d in dati.get("difetti") or [] if str(d).strip()][:12]
    v["secondi"] = round(time.time() - t0, 1)
    return v


def avviso(verdetto):
    """La riga per gli avvisi della costruzione: cosa ha detto il controllo."""
    esito = verdetto.get("esito")
    motivo = verdetto.get("motivo", "")
    if esito == "ok":
        return "controllo AI: il modello corrisponde al PDF - %s" % motivo
    if esito == "dubbio":
        return "CONTROLLO AI IN DUBBIO: %s" % motivo
    if esito == "sbagliato":
        return "CASO NUOVO, MODELLO RESPINTO DAL CONTROLLO AI: %s" % motivo
    return "controllo AI non fatto: %s" % motivo


# --------------------------------------------------------------------------- #
# il rigonfiamento "Scegli tu"
# --------------------------------------------------------------------------- #
SCHEMA_GONFIO = {
    "type": "object",
    "properties": {
        "prodotto": {"type": "string"},
        "livello": {"type": "integer"},
        "avvolge_scatola": {"type": "boolean"},
        "motivo": {"type": "string"},
    },
    "required": ["prodotto", "livello", "avvolge_scatola", "motivo"],
    "additionalProperties": False,
}

# Se REGOLE.md non c'e' o la sezione ha cambiato forma, si usa questa. La
# fonte vera resta REGOLE.md: e' quella che si legge per prima.
_REGOLE_GONFIO = """\
Il rigonfiamento e' una scala 1-10: Rigido 1-3 (pack teso e aderente, aria
minima), Medio 4-6 (volume standard, leggero cuscino d'aria), Morbido 7-10
(volumetrico e visibilmente gonfio, gas o liquidi).
- In astuccio o vaschetta rigida (multipack di merendine, blister): Rigido 1 e
  il film avvolge una scatola.
- Piatto, squadrato, compatto, rigido (crackers, biscotti, tavolette): Rigido 1-3.
- Irregolare, fragile, da forno (croissant, merendine, tramezzini): Medio 4-6.
- Sferico, tridimensionale, fresco o in ATM (mozzarella, insalata, formaggi
  freschi): Morbido 7-10.
"""


def regole_rigonfiamento(percorso=None):
    """La parte di REGOLE.md che dice come si sceglie il rigonfiamento."""
    p = percorso or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "REGOLE.md")
    try:
        with open(p, encoding="utf-8") as fh:
            testo = fh.read()
    except OSError:
        return _REGOLE_GONFIO
    m = re.search(r"Il rigonfiamento e' una \*\*scala 1-10\*\*.*?Nessun'altra domanda", testo, re.S)
    return m.group(0) if m else _REGOLE_GONFIO


def fascia(livello):
    return "Rigido" if livello <= 3 else ("Medio" if livello <= 6 else "Morbido")


def rigonfiamento(pdf_path, nome, modello=None, client=None):
    """Il livello di rigonfiamento scelto da Claude guardando l'artwork.

    Torna dict(livello, avvolge_scatola, prodotto, motivo) o dict(errore=...),
    e non lancia mai: senza la scelta dell'AI la costruzione ripiega sul 5.
    Rasterizza la pagina: va chiamata dentro il posto di costruzione.
    """
    try:
        return _rigonfiamento(pdf_path, nome, modello, client)
    except Exception as e:                        # noqa: BLE001
        return {"errore": "%s: %s" % (type(e).__name__, str(e)[:200])}


def _rigonfiamento(pdf_path, nome, modello, client):
    modello = modello or modello_ai()
    istruzioni = ("Scegli il rigonfiamento di un flowpack guardando il suo artwork, "
                  "seguendo queste regole del progetto:\n\n" + regole_rigonfiamento()
                  + "\n\nprodotto: il nome del prodotto come si legge sul pack; livello: "
                  "un intero da 1 a 10; avvolge_scatola: vero solo se il film avvolge "
                  "un astuccio o una vaschetta rigida; motivo: la motivazione in una "
                  "frase, in italiano semplice.")
    contenuto = [{"type": "text", "text": "Artwork del flowpack, file \"%s\":" % nome},
                 _immagine(_jpeg(vista.pagina(pdf_path, 1400))),
                 {"type": "text", "text": "Che rigonfiamento ha questo pack?"}]
    dati, errore = _chiama(contenuto, istruzioni, SCHEMA_GONFIO, modello, client)
    if errore:
        return {"errore": errore}
    try:
        livello = int(max(1, min(10, int(dati["livello"]))))
    except (KeyError, TypeError, ValueError):
        return {"errore": "risposta senza livello"}
    return {"livello": livello, "avvolge_scatola": bool(dati.get("avvolge_scatola")),
            "prodotto": str(dati.get("prodotto", "")).strip(),
            "motivo": str(dati.get("motivo", "")).strip()}


def dichiarazione(scelta):
    """La frase che REGOLE.md vuole per la scelta "Scegli tu"."""
    return ("Ho analizzato il prodotto (%s) e ho impostato il rigonfiamento su %s "
            "(Livello %d/10) perche' %s"
            % (scelta.get("prodotto") or "senza nome", fascia(scelta["livello"]),
               scelta["livello"], scelta.get("motivo") or "-"))
