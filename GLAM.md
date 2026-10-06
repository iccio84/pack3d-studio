# Glam Lab e i casi in correzione

Chi carica un PDF lo fa da **Glam Lab** (`glam-lab-view.lovable.app`), che
ospita la pagina dello Space nella sezione "Costruisci modello 3D da PDF".
Quando il modello non si costruisce, o il controllo dell'AI lo respinge, il
caso va in coda e lo corregge una routine di Claude Code (CODA.md). Chi ha
caricato il PDF non vede la coda: tutto quello che gli serve deve arrivargli
in Glam. Cioè:

- quanto aspettare, e dove arriverà il modello;
- a che punto è il caso;
- le **domande** della routine, quando dal PDF non si capisce come è fatto o
  come si monta il pack, e la possibilità di rispondere, anche con una foto;
- il modello corretto, nel **suo** account.

Qui c'è il contratto fra Glam e lo Space, e in fondo il testo da dare a
Lovable per la parte di Glam. Le altre parti stanno nello Space (pagina e
`server.py`), nella routine (`prove/parco.py caso` e `glam`) e in CODA.md.

## 1. Il caso entra in coda: dalla pagina a Glam

La pagina dello Space vive in un iframe servito dal dominio di Glam (il proxy
`/api/public/pack3d`). Quando un caso entra in coda manda alla finestra che la
ospita, solo se è della stessa origine, questo messaggio:

```js
{ type: "pack3d:caso",
  codice: "b312f1e238",                 // 10 cifre esadecimali
  nome: "FERRERO_158074379880291532",   // il nome che avrà il modello in Glam
  cartella: "Casi risolti",             // dove arriverà
  esito: "errore",                      // "errore", "sbagliato" o "dubbio"
  stima: "Di solito arriva entro un’ora." }
```

Glam lo riceve come oggi riceve `pack3d:built`: controlla `e.origin`, controlla
il codice, e lega il caso all'utente collegato. Se lo stesso PDF lo carica un
altro utente, il caso è anche suo: il codice è un'impronta dei PDF.

Glam aggiunge `casi=1` all'indirizzo dell'iframe. Per la pagina è il segnale
che Glam sa mostrare i casi: solo allora, nel riquadro del caso, promette che
le domande arriveranno «qui in Glam Lab, fra i tuoi casi in correzione».

## 2. Lo stato e le domande: dalla routine a Glam

`POST /api/pack3d-case`, con la stessa autorizzazione di `/api/import-model`
(`Authorization: Bearer <PACK3D_IMPORT_TOKEN>`, che alla routine aggiunge
l'ambiente cloud) e un corpo JSON:

```json
{ "codice": "b312f1e238",
  "nome": "FERRERO_158074379880291532",
  "stato": "domanda",
  "messaggio": "…",
  "domanda": "Come sta il coperchio quando il display è montato?",
  "opzioni": ["Si alza sul retro e fa da cartello", "Resta chiuso", "Si stacca e si butta"] }
```

| campo | |
|---|---|
| `codice` | obbligatorio, 10 cifre esadecimali |
| `nome` | il nome del modello, al massimo 120 caratteri |
| `stato` | `in-lavorazione`, `domanda`, `risolto` o `non-risolto` |
| `messaggio` | facoltativo, al massimo 500 caratteri: due righe per l'utente |
| `domanda` | solo con `domanda`, al massimo 500 caratteri |
| `opzioni` | solo con `domanda`, da 0 a 4, al massimo 120 caratteri l'una |

Glam aggiorna il caso per **ogni** utente che ce l'ha. Se non ce l'ha
nessuno (il PDF è stato caricato fuori da Glam), il caso va all'account di
`PACK3D_IMPORT_OWNER_EMAIL`, come oggi i modelli: così le domande le vede
almeno chi gestisce il servizio. Risponde `200 {"ok": true, "utenti": N}`, o
`400` con il motivo se il corpo non va.

## 3. Il modello corretto: a chi ha caricato il caso

`POST /api/import-model` come oggi, più un'intestazione facoltativa
`X-Pack3d-Codice: b312f1e238`. Se il caso ha utenti, il modello va a
**ciascuno** di loro, nella sezione dei modelli da PDF (`<utente>/pdf/<uuid>.glb`)
e nella cartella di `X-Model-Category`, al posto del loro modello con lo
stesso nome nella stessa cartella; e il loro caso passa a `risolto`. Senza
intestazione, o senza utenti, va all'account di `PACK3D_IMPORT_OWNER_EMAIL`
come oggi. La risposta aggiunge `"utenti": N`.

## 4. La risposta: da Glam allo Space

Quando l'utente risponde, il **server** di Glam - mai il browser: il token
resta nei segreti - chiama lo Space:

```
POST https://iccio-maurizio.hf.space/api/risposta
Authorization: Bearer <PACK3D_RISPOSTE_TOKEN>
Content-Type: application/json

{ "codice": "b312f1e238",
  "scelta": "Si alza sul retro e fa da cartello",
  "risposta": "e la linguetta col logo spunta sopra",
  "foto": "data:image/jpeg;base64,…" }
```

`scelta` è l'opzione scelta, se c'era; `risposta` il testo libero, al massimo
4000 caratteri; `foto` facoltativa, JPEG, PNG o WebP, al massimo 6 MB: nel
browser conviene rimpicciolirla a 1600 px sul lato lungo, come fa la pagina
dello Space con la nota. Ci vuole almeno uno dei tre.

Lo Space scrive la risposta sulla issue del caso, toglie l'etichetta
`da-guardare` e rilancia la routine, che riprende il caso con la risposta
fra i commenti.

| risposta dello Space | |
|---|---|
| `200 {"ok": true, "issue": 3, "rilanciata": true}` | arrivata: il caso torna `in-lavorazione` |
| `400` | il corpo non va (vuoto, foto illeggibile): il motivo è nel testo |
| `401` | il token non è quello dello Space |
| `404` | il caso non è più in coda: già risolto o chiuso |
| `429` | troppe risposte su questo caso: riprovare più tardi |
| `502` / `503` | il repository dei casi non risponde, o la coda non è configurata |

## 5. Cosa vede l'utente

- Sul tasto "Costruisci modello 3D da PDF", un **numero** quando un suo caso
  aspetta una risposta.
- Nella sezione, l'elenco **I tuoi casi in correzione**: per ognuno il nome,
  lo stato a parole sue, quando è cambiato, e il messaggio:
  - `in-coda`: «In coda: di solito arriva entro un'ora»;
  - `in-lavorazione`: «In lavorazione»;
  - `domanda`: la domanda, le risposte fra cui scegliere, un campo per
    scrivere a parole sue, «Aggiungi una foto», «Invia la risposta»;
  - `risolto`: «Risolto: il modello è in Casi risolti col nome …», e il tasto
    per aprirlo;
  - `non-risolto`: il messaggio, che dice chi lo riprende.
- Un avviso, all'apertura di Glam, se un suo caso è cambiato dall'ultima
  volta che l'ha guardato: una domanda nuova, o il modello arrivato.

La domanda e il messaggio sono testo: si mostrano come testo, mai come HTML.

## Il testo per Lovable

Da incollare in Lovable così com'è. Dei due segreti, `PACK3D_IMPORT_TOKEN`
c'è già; `PACK3D_RISPOSTE_TOKEN` è nuovo, va in Cloud → Secrets, ed è lo
stesso valore messo nei Secrets dello Space (DEPLOY.md).

```text
Voglio che chi carica un PDF in "Costruisci modello 3D da PDF" possa seguire in Glam i casi che lo Space mette in correzione. Il contratto completo è in GLAM.md del repository iccio84/pack3d-studio; qui quello che serve.

1. Tabella pack3d_cases (Supabase): id uuid, codice text (10 cifre esadecimali), user_id uuid (utente), nome text, esito text, stato text ('in-coda', 'in-lavorazione', 'domanda', 'risolto', 'non-risolto'), messaggio text, domanda text, opzioni jsonb, risposta text, model_id uuid nullable, created_at, updated_at, seen_at. Unica la coppia (codice, user_id). RLS: ogni utente vede solo i suoi casi e può crearli per sé; il resto lo scrivono le funzioni del server.

2. Nel dialog di "Costruisci modello 3D da PDF", accanto all'ascolto di "pack3d:built", ascolta anche i messaggi { type: "pack3d:caso", codice, nome, cartella, esito, stima } dall'iframe, con lo stesso controllo e.origin === window.location.origin e con codice che rispetta /^[0-9a-f]{10}$/. Per ognuno crea (o aggiorna) il caso dell'utente collegato con stato 'in-coda'. Aggiungi anche casi=1 all'indirizzo dell'iframe (.../api/public/pack3d?api=...&casi=1).

3. Nuovo endpoint server POST /api/pack3d-case, autorizzato esattamente come /api/import-model (Bearer PACK3D_IMPORT_TOKEN). Corpo JSON: codice, nome, stato (in-lavorazione | domanda | risolto | non-risolto), messaggio facoltativo (max 500), domanda (max 500) e opzioni (array di 0-4 stringhe, max 120) solo con stato domanda. Aggiorna il caso di ogni utente che ha quel codice (stato, messaggio, domanda, opzioni, updated_at; seen_at a null). Se nessun utente ha il codice, crea il caso per l'utente di PACK3D_IMPORT_OWNER_EMAIL. Risposta 200 {"ok": true, "utenti": N}; 400 col motivo se il corpo non va.

4. /api/import-model: se arriva l'intestazione X-Pack3d-Codice e ci sono utenti con quel caso, salva il modello per ciascuno di loro (come modello costruito da PDF: percorso <user_id>/pdf/<uuid>.glb, categoria da X-Model-Category, al posto del loro modello con lo stesso nome nella stessa categoria), metti il loro caso a 'risolto' con model_id, e restituisci anche "utenti": N. Senza intestazione o senza utenti, tutto come adesso (utente di PACK3D_IMPORT_OWNER_EMAIL). Assicurati che anche questo caso salvi in <user_id>/pdf/, così i modelli finiscono nella sezione "Costruisci modello 3D da PDF".

5. Nella sezione "Costruisci modello 3D da PDF": un elenco "I tuoi casi in correzione" con nome, stato a parole (in-coda: "In coda: di solito arriva entro un'ora"; in-lavorazione: "In lavorazione"; domanda: "Serve una tua risposta"; risolto: "Risolto: il modello è in Casi risolti" con un tasto per aprirlo; non-risolto: il messaggio), quando è cambiato e il messaggio. I casi risolti da più di 30 giorni si nascondono. Sul tasto "Costruisci modello 3D da PDF" un badge col numero di casi in stato domanda. All'apertura di Glam, un toast se un caso è cambiato dopo seen_at; quando l'utente apre l'elenco, aggiorna seen_at. Domande e messaggi si mostrano come testo, mai come HTML.

6. Per un caso in stato domanda: la domanda, le opzioni come scelte (una sola), un campo "Scrivi a parole tue" (max 4000), "Aggiungi una foto" (rimpicciolita nel browser a 1600 px sul lato lungo, JPEG qualità 0.85) e "Invia la risposta". Ci vuole almeno una scelta, un testo o una foto. L'invio passa da una funzione del server, mai dal browser: POST all'indirizzo dello Space che usi già per l'iframe + "/api/risposta", con Authorization: Bearer PACK3D_RISPOSTE_TOKEN (nuovo secret) e corpo JSON { codice, scelta, risposta, foto } (foto come data URL). Se lo Space risponde 200, salva la risposta e metti il caso a 'in-lavorazione' con messaggio "Risposta inviata: il caso è ripartito". Se risponde altro, mostra all'utente il testo della risposta e lascia il modulo com'era (401: token sbagliato; 404: il caso non è più in correzione; 429: troppe risposte, riprova più tardi).
```
