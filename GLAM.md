# Glam Lab e i casi in correzione

Chi carica un PDF lo fa da **Glam Lab** (`iccio-3d-viewer.lovable.app`), che
ospita la pagina dello Space nella sezione "Costruisci modello 3D da PDF".
Quando il modello non si costruisce, o il controllo dell'AI lo respinge, il
caso va in coda e lo corregge una routine di Claude Code (CODA.md). Chi ha
caricato il PDF non vede la coda: tutto quello che gli serve deve arrivargli
in Glam. Cioè:

- quanto aspettare, e dove arriverà il modello;
- a che punto è il caso;
- le **domande** della routine, quando dal PDF non si capisce come è fatto o
  come si monta il pack, e la possibilità di rispondere, anche con una foto;
- il modello corretto, nel **suo** account, con la sua texture nella sezione
  texture del modello (sezione 8) e il suo template PSD dietro «Scarica
  Template» (sezione 9);
- un caso che non serve più, da eliminare: lo può fare un admin, o l'account
  design per i suoi (sezione 7).

Qui c'è il contratto fra Glam e lo Space, e in fondo il testo da dare a
Lovable per la parte di Glam. Le altre parti stanno nello Space (pagina e
`server.py`), nella routine (`prove/parco.py caso` e `glam`) e in CODA.md.

## 1. Il caso entra in coda: dalla pagina a Glam

La pagina dello Space vive in un iframe servito dal dominio di Glam (il proxy
`/api/public/pack3d`). Un caso nuovo entra in coda solo quando chi ha caricato
il PDF preme **Invia il caso** (con l'email per le domande, se vuole): Annulla,
o la pagina chiusa senza scegliere, lo cancellano. Quando entra, la pagina
manda alla finestra che la ospita, solo se è della stessa origine, questo
messaggio:

```js
{ type: "pack3d:caso",
  codice: "b312f1e238",                 // 10 cifre esadecimali
  nome: "NOME_DEL_PDF",                 // il nome che avrà il modello in Glam
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

### Il caso inviato chiude la finestra

Mandato il caso, chi l'ha caricato deve vedere che il suo lavoro è finito.
Se nella pagina non c'è un modello da tenere (il controllo l'ha respinto, o
la costruzione si è fermata), subito dopo `pack3d:caso` la pagina manda:

```js
{ type: "pack3d:chiudi",
  codice: "b312f1e238",                 // lo stesso di pack3d:caso
  titolo: "Caso inviato",
  testo: "«NOME_DEL_PDF»: quando sarà corretto, lo trovi in «Costruisci modello 3D da PDF», cartella «Casi risolti». Di solito arriva entro un’ora." }
```

Glam chiude il dialog di «Costruisci modello 3D da PDF», come dopo aver
salvato un modello, e mostra un toast con titolo e testo. Vedi *Il testo per
Lovable: il caso inviato chiude la finestra*.

- **La nota** per chi corregge (com'è fatto il pack, come si monta, una foto)
  sta nel modulo d'invio, chiusa dietro un link, e parte con il caso: dopo,
  la pagina non c'è più. Se la nota non arriva il caso è partito lo stesso:
  la pagina resta aperta con la nota e il suo tasto per riprovare, e
  `pack3d:chiudi` parte quando arriva lei.
- **Con un modello in vista** - un dubbio del controllo, o un respinto
  mostrato lo stesso - `pack3d:chiudi` non parte: il modello si può ancora
  salvare in Glam, e il salvataggio chiude il dialog come sempre.
- **La pagina torna all'inizio** in ogni caso, anche dentro un Glam che non
  ascolta ancora `pack3d:chiudi`; da sola apre anche la sua finestra dei
  casi, con quello appena mandato.

## 2. Lo stato e le domande: dalla routine a Glam

`POST /api/pack3d-case`, con la stessa autorizzazione di `/api/import-model`
(`Authorization: Bearer <PACK3D_IMPORT_TOKEN>`, che alla routine aggiunge
l'ambiente cloud) e un corpo JSON:

```json
{ "codice": "b312f1e238",
  "nome": "NOME_DEL_PDF",
  "stato": "domanda",
  "messaggio": "…",
  "domanda": "Come sta il coperchio quando il display è montato?",
  "opzioni": ["Si alza sul retro e fa da cartello", "Resta chiuso", "Si stacca e si butta"] }
```

| campo | |
|---|---|
| `codice` | obbligatorio, 10 cifre esadecimali |
| `nome` | il nome del modello, al massimo 120 caratteri |
| `stato` | `in-lavorazione`, `domanda`, `da-approvare`, `risolto` o `non-risolto` |
| `messaggio` | facoltativo, al massimo 500 caratteri: due righe per l'utente |
| `domanda` | solo con `domanda`, al massimo 500 caratteri |
| `opzioni` | solo con `domanda`, da 0 a 4, al massimo 120 caratteri l'una |

Glam aggiorna il caso per **ogni** utente che ce l'ha. Se non ce l'ha
nessuno (il PDF è stato caricato fuori da Glam), il caso va all'account di
`PACK3D_IMPORT_OWNER_EMAIL`, come oggi i modelli: così le domande le vede
almeno chi gestisce il servizio. Risponde `200 {"ok": true, "utenti": N}`, o
`400` con il motivo se il corpo non va.

`da-approvare`: il modello corretto è pronto, e chi ha caricato il PDF lo deve
approvare prima che vada nei Casi risolti. Si approva (o si dice cosa non va,
con le foto) dalla finestra dei casi della pagina dello Space, non da Glam:
Glam ne fa solo una notifica. Finché Glam non conosce lo stato e risponde
`400`, `prove/parco.py caso` glielo manda come `in-lavorazione`, col messaggio
che dice dove approvarlo.

## 3. Il modello corretto: a chi ha caricato il caso

Arriva **solo dopo l'approvazione** di chi ha caricato il PDF. Lo manda lo
Space stesso, nel momento dell'approvazione, con lo stesso token
(`PACK3D_IMPORT_TOKEN` fra i suoi Secrets, vedi DEPLOY.md); se non lo ha, o
Glam non risponde, lo manda la routine.

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
- Quando manda un caso, il dialog si chiude da solo con un toast «Caso
  inviato» che dice dove arriverà il modello (sezione 1).
- **L'elenco dei casi sta in un posto solo: la finestra «Casi» della pagina
  dello Space**, dentro la sezione. Per ognuno il nome, lo stato a parole
  sue, quando è cambiato, il messaggio e, se c'è una domanda, il modulo per
  rispondere. Glam **non** disegna un suo elenco «I tuoi casi in correzione»
  sotto il visore: c'era, e i casi comparivano due volte. Vedi *Il testo per
  Lovable: un elenco solo*.
- Glam tiene la tabella dei casi (serve alle notifiche, al numero sul tasto
  e al modello corretto che arriva all'utente giusto) e le **notifiche** della
  busta (punto 6), con il modulo di risposta che si apre da una domanda.
- Un avviso, all'apertura di Glam, se un suo caso è cambiato dall'ultima
  volta che l'ha guardato: una domanda nuova, o il modello arrivato.

La domanda e il messaggio sono testo: si mostrano come testo, mai come HTML.

## 6. Le notifiche: la busta nella barra

Chi ha un caso in correzione non deve andare a cercarlo: nella barra verde in
alto c'è una **busta** col numero delle notifiche non lette, in ogni pagina
dell'app. Ogni cambio di stato di un suo caso (punto 2, e il modello arrivato
del punto 3) gli lascia una notifica; Glam ne tiene le ultime dieci per
utente. Premendo la busta si apre l'elenco; premendo una **domanda** si apre
il modulo per rispondere (punto 4), e la risposta va allo Space come prima.
Una domanda resta evidenziata finché non ha risposta; il modello arrivato
apre il modello.

Con l'accesso guest condiviso le notifiche sono dell'account guest: le vede
chiunque entri come guest. Chi vuole le sue entra col suo account.

## 7. Eliminare un caso

Un caso in sospeso - in coda, in lavorazione, con una domanda, da approvare,
non risolto - si elimina dalla finestra «Casi» della pagina dello Space,
dentro Glam. Chi può farlo lo decide Glam, che sa chi è collegato, con la
regola dei ruoli che l'app usa già:

| ruolo | nella finestra dei casi | può eliminare |
|---|---|---|
| admin | tutti i casi in sospeso, di tutti | tutti |
| design | i casi caricati da lui | solo i suoi |
| guest | i casi mandati da quel browser | niente: il tasto non c'è |

Fuori da Glam (la pagina dello Space aperta da sola) il tasto non c'è.

Il giro passa fra la pagina e Glam, finestre della stessa origine (Glam serve
la pagina dal suo dominio), e poi dal server di Glam allo Space:

1. La pagina chiede il ruolo alla finestra che la ospita,
   `{type: "pack3d:ruolo?"}`, all'avvio e quando si apre la finestra dei casi.
2. Glam risponde all'iframe
   `{type: "pack3d:ruolo", ruolo: "admin" | "design" | "guest", casi: [{codice, nome, creato}]}`.
   `casi` sono i casi in sospeso (stato diverso da `risolto`) che quel ruolo
   vede, al massimo 100: per l'admin quelli di tutti gli utenti, per il
   design i suoi, per il guest nessuno. La pagina li mette nella finestra,
   anche se sono stati mandati da un altro browser, e mostra **Elimina il
   caso** dove il ruolo lo permette.
3. Elimina chiede conferma nella riga; poi la pagina manda
   `{type: "pack3d:elimina", codice}`. Glam non chiede di nuovo.
4. Il **server** di Glam rifà il controllo dall'utente collegato, mai da
   quello che dice il messaggio: admin sì; design solo se il caso è suo (una
   riga di `pack3d_cases` con quel codice e il suo `user_id`); guest no. Poi
   chiama lo Space:

```
POST https://iccio-maurizio.hf.space/api/elimina
Authorization: Bearer <PACK3D_RISPOSTE_TOKEN>
Content-Type: application/json

{ "codice": "b312f1e238", "ruolo": "admin" }
```

5. Con `200`, o `404` (nella coda il caso non c'è più), Glam cancella il caso
   - tutte le righe di `pack3d_cases` con quel codice, di tutti gli utenti, e
   le loro notifiche - e risponde all'iframe
   `{type: "pack3d:eliminato", codice, ok: true}`. Con un'altra risposta non
   cancella niente e manda `{…, ok: false, errore: <il testo dello Space>}`,
   che la pagina mostra nella riga.

| risposta dello Space | |
|---|---|
| `200 {"ok": true, "issue": 3}` | eliminato: la issue è chiusa (`issue` è null per un caso che aspettava ancora Invia) |
| `401` | il token non è quello dello Space |
| `404` | nella coda il caso non c'è più: già chiuso, risolto o eliminato |
| `409` | la routine ci sta lavorando adesso: riprovare quando ha finito |
| `502` / `503` | il repository dei casi non risponde, o la coda non è configurata |

Lo Space chiude la issue come "not planned", con l'etichetta `eliminato` e un
commento che dice chi l'ha eliminato (un admin o l'account design, non il
nome), e la routine non la lavora più. I file restano nel registro: lo stesso
PDF, ricaricato, apre un caso nuovo. Chi aveva il caso nella finestra di un
altro browser lo vede uscire, con la notifica «il caso è stato eliminato».

Un caso che Glam elenca ancora ma che nella coda non c'è più - chiuso o
eliminato fuori dall'app, per esempio da chi gestisce il servizio - la pagina
lo toglie e manda lo stesso `pack3d:elimina`: lo Space risponde `404`, e Glam
cancella il suo. Così in Glam non restano casi fantasma.

## 8. La texture del modello

Oltre al GLB, ogni modello ha la sua **texture a parte**: l'immagine che il
GLB usa come colore, con le stesse UV. È **lo steso del PDF**: la grafica
senza disegno tecnico, nel verso in cui sta nel file, inquadrata sul DT
(REGOLE.md, *La texture è lo steso*). Chi vuole una variante ci sovrappone il
nuovo artwork - stesso DT, stesso verso, stessa scala - e la carica sullo
stesso modello: ogni cosa torna al suo posto. In Glam va nella **sezione
texture del modello** - il riquadro «Texture modello selezionato», la tabella
`user_textures` col `model_key` del modello (`up_<id>`), il file nel bucket
`textures` - come una texture caricata a mano con «Carica texture».

Glam mette la texture scelta su tutti i materiali del modello che hanno un
colore da immagine; il rovescio e il taglio del cartoncino sono colori pieni,
senza texture, e restano come sono. Per questo ogni modello ha **una**
texture: anche quelli fatti di più fogli - la coppa col tappo, il cono col
lid, il riempimento col vassoio e il pack - che hanno gli stesi dei loro PDF
in un'immagine sola, l'atlante, una zona per pezzo (REGOLE.md, *La texture
è lo steso*). La variante di un pezzo si fa sostituendo la sua zona. Al
massimo 5000 px per lato, il
limite di «Carica texture»: lo Space riduce in proporzione quelle più
grandi.

**Dalla pagina** - il modello costruito nell'iframe. Quando il modello è
pronto la pagina manda alla finestra che la ospita, solo se è della stessa
origine:

```js
{ type: "pack3d:texture",
  nome: "NOME_DEL_PDF_texture.jpg",   // il nome della texture in Glam
  blob: Blob,                         // image/jpeg, o image/png
  larghezza: 1801, altezza: 1700,     // px, al massimo 5000 per lato
  glb: 4447372 }                      // la misura in byte del GLB del modello
```

Arriva subito prima o subito dopo il `pack3d:built` dello stesso modello, a
volte più di una volta. Glam tiene l'ultima; quando salva il modello di
`pack3d:built`, se `glb` è uguale alla misura di quel GLB salva anche la
texture, per lui. Una texture con un'altra misura è di un altro modello e non
si salva.

**Dalla routine e dallo Space** - il modello corretto di un caso, o uno del
parco. Subito dopo `/api/import-model`, con la stessa autorizzazione:

```
POST /api/import-texture
Authorization: Bearer <PACK3D_IMPORT_TOKEN>
Content-Type: image/jpeg
X-Model-Name: NOME_DEL_PDF                    (encodeURIComponent, come per l'import)
X-Model-Category: Casi%20risolti
X-Texture-Name: NOME_DEL_PDF_texture.jpg
X-Pack3d-Codice: b312f1e238                   (facoltativa, come per l'import)

<i byte dell'immagine>
```

I destinatari sono quelli di `/api/import-model`: gli utenti del caso, o
l'account di `PACK3D_IMPORT_OWNER_EMAIL`. Per ognuno Glam prende il suo
modello con quel nome in quella cartella - quello appena arrivato - e gli
mette la texture, al posto di quella con lo stesso nome se c'era.

| risposta di Glam | |
|---|---|
| `200 {"ok": true, "utenti": N}` | salvata per N utenti |
| `400` | il corpo non è un'immagine PNG, JPEG o WebP, o è più di 25 MB: il motivo è nel testo |
| `401` | il token non è quello di Glam |
| `404` | nessun destinatario ha un modello con quel nome in quella cartella |

Se la texture non passa, il modello resta dov'è: lo Space e la routine
(`prove/parco.py glam`) lo scrivono e vanno avanti.

## 9. Il template del modello

In Glam ogni modello ha **«Scarica Template»**: un PSD su cui il grafico
appoggia il nuovo artwork, e da cui esporta la texture da caricare sul
modello. Oggi c'è solo per il Nutella 750 g, caricato a mano con «Carica
Template» (bucket `templates`). Per i modelli costruiti dal PDF il template
lo fa lo Space dal GLB (`pack3d/template.py`), con la struttura di quello
del Nutella 750 g:

| gruppo | livello | |
|---|---|---|
| La tua grafica | La tua grafica | la texture del modello: lo steso del PDF (sezione 8), alla misura della texture che va a Glam |
| Guide UV | Sovrapposizione modello | nascosto: tutti gli spigoli della mappatura, grigi |
| | Griglia texture | nascosto: la scacchiera A0-J9, per provare il verso sul modello |
| | Area non modificabile | nero al 60% dove il modello non prende la texture |
| | Contorni | il bordo del DT, finestre e solchi, e le pieghe, in magenta |
| | Nomi delle facce | FRONTE, RETRO, FIANCO SX, FIANCO DX, CIELO, FONDO sulle facce di un astuccio |
| | Nomi dei pezzi | in un atlante, il nome di ogni pezzo nella sua zona: COPPA, TAPPO, CONO, LID, VASSOIO, FLOWPACK... |

Il PSD è RGB a 8 bit, con la composizione salvata (i livelli accesi). Come
la texture, c'è per tutti i modelli: in quelli di più fogli la texture è un
atlante, e il template scrive il nome del pezzo su ogni zona (livello «Nomi
dei pezzi»); al massimo
45 MB: uno più grande lo Space lo rifà più piccolo, e le UV, che sono
frazioni dell'immagine, restano giuste.

**Dalla pagina** - dentro Glam, quando il modello è pronto, la pagina chiede
il template allo Space (`POST /api/template` col GLB) e lo manda alla
finestra che la ospita:

```js
{ type: "pack3d:template",
  nome: "NOME_DEL_PDF_template.psd",
  blob: Blob,                         // image/vnd.adobe.photoshop
  glb: 4447372 }                      // la misura in byte del GLB del modello
```

Arriva dopo la texture, qualche secondo dopo `pack3d:built` (lo Space ci
mette fino a una decina di secondi), e si lega al modello come la texture:
con `glb` uguale alla misura del suo GLB.

**Dalla routine e dallo Space** - subito dopo la texture, con la stessa
autorizzazione:

```
POST /api/import-template
Authorization: Bearer <PACK3D_IMPORT_TOKEN>
Content-Type: image/vnd.adobe.photoshop
X-Model-Name: NOME_DEL_PDF                    (encodeURIComponent, come per l'import)
X-Model-Category: Casi%20risolti
X-Template-Name: NOME_DEL_PDF_template.psd
X-Pack3d-Codice: b312f1e238                   (facoltativa, come per l'import)

<i byte del PSD>
```

I destinatari e le risposte sono quelli di `/api/import-texture`; il
template sostituisce quello che il modello aveva. Se non passa, il modello e
la texture restano: lo Space e la routine lo scrivono e vanno avanti.

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

### Il testo per Lovable: le notifiche

Da incollare dopo che il testo qui sopra è pubblicato. Non servono segreti
nuovi.

```text
Aggiungi le notifiche dei casi in correzione, con una busta nella barra verde in alto. Tutto il resto (endpoint, token, tabella pack3d_cases, elenco "I tuoi casi in correzione", modulo di risposta) resta com'è.

1. Tabella pack3d_notifications (Supabase): id uuid, user_id uuid, case_id uuid (riferimento a pack3d_cases), codice text, tipo text ('in-lavorazione', 'domanda', 'risolto', 'non-risolto', 'risposta-inviata'), titolo text, testo text, created_at, read_at nullable. RLS: ogni utente legge solo le sue e può solo segnarle come lette (read_at); le crea solo il server.

2. Quando /api/pack3d-case cambia lo stato di un caso, e quando /api/import-model mette un caso a 'risolto', crea una notifica per ciascun utente di quel caso:
   - domanda: titolo "Serve una tua risposta", testo = la domanda;
   - in-lavorazione: titolo "Il tuo caso è in lavorazione", testo = il messaggio se c'è;
   - risolto: titolo "Il modello corretto è pronto", testo "Lo trovi in Casi risolti col nome …";
   - non-risolto: titolo "Il caso non si risolve per ora", testo = il messaggio.
   Per ogni utente tieni solo le ultime 10 notifiche: le più vecchie si cancellano.

3. Nella barra verde in alto, a destra, in tutte le pagine dell'app per l'utente collegato: un'icona a forma di busta (lucide "Mail"), con un badge numerico delle notifiche non lette. Se fra le non lette c'è una domanda, il badge è più evidente (colore di avviso). Il numero si aggiorna da solo, senza ricaricare: Supabase Realtime sulla tabella pack3d_notifications, oppure un controllo ogni 60 secondi.

4. Premendo la busta si apre un pannello (popover sotto la busta, o drawer a destra sul telefono) con le notifiche dalla più recente: titolo, testo, nome del caso e da quanto tempo. Le non lette sono evidenziate. Aprendo il pannello le notifiche si segnano lette (read_at), tranne le domande ancora senza risposta, che restano evidenziate finché il caso è in stato 'domanda'. Se non ci sono notifiche: "Nessuna notifica".

5. Premendo una notifica di tipo domanda si apre, in un dialog, il modulo di risposta di quel caso: la domanda, le opzioni come scelte (una sola), "Scrivi a parole tue", "Aggiungi una foto", "Invia la risposta" (lo stesso modulo e la stessa funzione del server che manda allo Space /api/risposta). Dopo un invio riuscito chiudi il dialog, crea la notifica 'risposta-inviata' ("Risposta inviata: il caso è ripartito") e togli l'evidenza alla domanda. Se lo Space risponde con un errore, mostralo nel dialog e lascia il modulo com'era.

6. Premendo una notifica 'risolto' apri il modello nella sezione "Costruisci modello 3D da PDF", cartella "Casi risolti". Le altre notifiche aprono la sezione "Costruisci modello 3D da PDF", dove la pagina dello Space ha la finestra dei casi.

7. Titoli e testi delle notifiche si mostrano sempre come testo, mai come HTML.
```

### Il testo per Lovable: un elenco solo

Da incollare dopo i due testi qui sopra. I casi comparivano due volte: nella
finestra «Casi» della pagina dello Space, dentro l'iframe, e nell'elenco che
Glam disegnava sotto il visore. Resta la finestra; l'elenco di Glam se ne va.

```text
Nella sezione "Costruisci modello 3D da PDF" togli l'elenco "I tuoi casi in correzione" che sta sotto il visore (l'iframe della pagina dello Space): i casi in correzione li mostra già la pagina dello Space, nella sua finestra "Casi", e comparivano due volte. Togli solo l'elenco e il suo contenitore, senza lasciare spazio vuoto sotto il visore.

Resta tutto il resto: la tabella pack3d_cases, l'ascolto dei messaggi "pack3d:caso" dall'iframe, gli endpoint /api/pack3d-case e /api/import-model, il parametro casi=1 nell'indirizzo dell'iframe, il badge sul tasto "Costruisci modello 3D da PDF", il toast all'apertura, la busta delle notifiche e il modulo di risposta che si apre premendo una notifica di tipo domanda.

Le notifiche che prima aprivano l'elenco "I tuoi casi in correzione" (tutte tranne 'risolto' e 'domanda') ora aprono la sezione "Costruisci modello 3D da PDF". Il seen_at dei casi si aggiorna quando l'utente apre quella sezione, invece che quando apriva l'elenco.
```

### Il testo per Lovable: il modello da approvare

Da incollare dopo i testi qui sopra. Un caso risolto non va più dritto nei
Casi risolti: prima lo approva chi l'ha caricato, dalla finestra dei casi
della pagina dello Space. Glam deve solo conoscere il nuovo stato e
avvisarlo.

```text
I casi in correzione hanno un nuovo stato, 'da-approvare': il modello corretto è pronto e chi ha caricato il PDF lo deve approvare. Si approva dalla finestra "Casi" della pagina dello Space, dentro l'iframe di "Costruisci modello 3D da PDF", non da Glam.

1. /api/pack3d-case accetta anche stato = 'da-approvare' (con messaggio facoltativo, come gli altri), e lo salva nel caso come gli altri stati. Aggiorna anche il vincolo o la validazione di pack3d_cases.stato e di pack3d_notifications.tipo per accettarlo.

2. Quando un caso passa a 'da-approvare', crea per ciascun utente del caso la notifica: titolo "Il modello corretto è da approvare", testo = il messaggio se c'è, altrimenti "Guardalo e approvalo nella finestra Casi di Costruisci modello 3D da PDF". Nel badge del tasto "Costruisci modello 3D da PDF" conta anche i casi in stato 'da-approvare', come quelli in stato 'domanda', e la notifica resta evidenziata finché il caso è in quello stato.

3. Premendo questa notifica apri la sezione "Costruisci modello 3D da PDF" (dove la pagina dello Space ha la finestra dei casi). Non serve nessun modulo in Glam: l'approvazione passa dalla pagina dello Space.

4. Tutto il resto resta com'è: il modello arriva con /api/import-model dopo l'approvazione e mette il caso a 'risolto', come oggi.
```

### Il testo per Lovable: eliminare i casi

Da incollare dopo i testi qui sopra. Non servono segreti nuovi:
`PACK3D_RISPOSTE_TOKEN` c'è già.

```text
Aggiungi l'eliminazione dei casi in correzione. I casi li mostra la pagina dello Space nell'iframe di "Costruisci modello 3D da PDF", nella sua finestra "Casi", e il tasto Elimina sta lì; Glam decide chi può eliminare cosa e chiama lo Space dal server. Il contratto completo è in GLAM.md, sezione 7, del repository iccio84/pack3d-studio.

1. Ruoli: usa la regola che l'app usa già. design = l'utente collegato con l'email dell'account design; admin = qualunque altro utente collegato; guest = nessun utente collegato (l'accesso guest con la password). L'admin può eliminare tutti i casi, il design solo quelli caricati da lui (quelli con una riga in pack3d_cases col suo user_id), il guest nessuno.

2. Nel componente di "Costruisci modello 3D da PDF", dove ascolti già i messaggi "pack3d:caso" dall'iframe, con lo stesso controllo (e.origin === window.location.origin, e e.source uguale alla contentWindow dell'iframe), ascolta anche:
   - { type: "pack3d:ruolo?" }: rispondi all'iframe con postMessage({ type: "pack3d:ruolo", ruolo, casi }, window.location.origin). ruolo è "admin", "design" o "guest". casi sono i casi in sospeso che quel ruolo vede, al massimo 100, dal più recente, come { codice, nome, creato } (creato = created_at). Per l'admin: tutti i casi di pack3d_cases, di tutti gli utenti, con stato diverso da 'risolto', uno per codice (serve una funzione del server: la RLS mostra a ognuno solo i suoi). Per il design: i suoi casi con stato diverso da 'risolto'. Per il guest: [].
   - { type: "pack3d:elimina", codice } (codice di 10 cifre esadecimali): chiama una nuova funzione del server deletePack3dCase({ codice }) e rispondi all'iframe con postMessage({ type: "pack3d:eliminato", codice, ok, errore }, window.location.origin). Non chiedere conferma: l'ha già chiesta la pagina.

3. deletePack3dCase, funzione del server con l'utente autenticato:
   - Ricava il ruolo dall'utente collegato, sul server, mai da quello che dice il browser. Guest (nessun utente collegato): rifiuta con "Il guest non può eliminare i casi". Design senza una riga in pack3d_cases con quel codice e il suo user_id: rifiuta con "Puoi eliminare solo i casi caricati da te".
   - Chiama lo Space: POST all'indirizzo dello Space che usi già per l'iframe + "/api/elimina", con Authorization: Bearer PACK3D_RISPOSTE_TOKEN (il secret che c'è già per /api/risposta) e corpo JSON { codice, ruolo }.
   - Se lo Space risponde 200, o 404 (nella coda il caso non c'è più), cancella tutte le righe di pack3d_cases con quel codice, di tutti gli utenti, e le notifiche di pack3d_notifications con quel codice, e torna { ok: true }.
   - Se risponde altro, non cancellare niente e torna { ok: false, errore: il testo della risposta dello Space } (409 vuol dire che la routine ci sta lavorando adesso: riprovare quando ha finito).

4. Dopo un'eliminazione riuscita aggiorna il badge sul tasto "Costruisci modello 3D da PDF" e la busta delle notifiche (invalida le query dei casi e delle notifiche).

5. Tutto il resto resta com'è: endpoint, token, tabelle, notifiche e modulo di risposta.
```

### Il testo per Lovable: la texture del modello

Da incollare dopo i testi qui sopra. Non servono segreti nuovi:
`PACK3D_IMPORT_TOKEN` c'è già.

```text
Ogni modello costruito da PDF deve avere anche la sua texture nella sezione texture del modello ("Texture modello selezionato"), come se l'utente l'avesse caricata con "Carica texture". La texture è lo steso del PDF, senza disegno tecnico: chi vuole una variante ci sovrappone il nuovo artwork e la carica sullo stesso modello. Il contratto completo è in GLAM.md, sezione 8, del repository iccio84/pack3d-studio.

1. Dalla pagina dello Space. Nel componente di "Costruisci modello 3D da PDF", dove ascolti già "pack3d:built" dall'iframe, ascolta anche { type: "pack3d:texture", nome, blob, larghezza, altezza, glb }, con lo stesso controllo e.origin === window.location.origin, e solo se blob è un Blob di tipo image/jpeg, image/png o image/webp. Tieni l'ultima ricevuta (può arrivare prima o dopo "pack3d:built", e più di una volta). Quando salvi il modello arrivato con "pack3d:built", se la texture tenuta ha glb uguale a blob.size di quel modello, subito dopo aver salvato il modello salva anche la texture per lui, con le stesse funzioni del server di "Carica texture": file nel bucket "textures", riga in user_textures con model_key = "up_" + id del modello appena salvato, name = nome, mime_type = il tipo del blob. Se la texture non si salva, il modello resta salvato: mostra solo un toast "Texture non salvata". Quando arriva un "pack3d:built" con un GLB nuovo, la texture tenuta vale solo se il suo glb è uguale alla misura del nuovo GLB.

2. Nuovo endpoint server POST /api/import-texture, autorizzato esattamente come /api/import-model (Bearer PACK3D_IMPORT_TOKEN). Il corpo sono i byte dell'immagine: Content-Type image/jpeg, image/png o image/webp, al massimo 25 MB (le misure le garantisce lo Space: al massimo 5000 px per lato). Intestazioni: X-Model-Name e X-Model-Category (decodeURIComponent, come in /api/import-model), X-Texture-Name (decodeURIComponent, al massimo 160 caratteri) e X-Pack3d-Codice facoltativa (10 cifre esadecimali). I destinatari sono gli stessi di /api/import-model: gli utenti che hanno il caso X-Pack3d-Codice in pack3d_cases, oppure, se l'intestazione manca o il caso non ha utenti, l'utente di PACK3D_IMPORT_OWNER_EMAIL. Per ciascuno trova il suo modello in user_models con quel nome e quella categoria (il più recente, se sono più d'uno) e salva l'immagine come fa "Carica texture": file nel bucket "textures", riga in user_textures con model_key = "up_" + id del modello, name = X-Texture-Name, mime_type, user_id del destinatario. Se quel modello ha già una texture con lo stesso nome, sostituiscila (cancella la riga e il file vecchi). Risposta 200 {"ok": true, "utenti": N}; 400 col motivo se il corpo non va; 401 se il token non è quello; 404 {"error": "nessun modello con quel nome in quella categoria"} se nessun destinatario ha il modello.

3. Tutto il resto resta com'è: /api/import-model, "pack3d:built", la sezione texture, "Carica texture" e i suoi limiti per chi carica a mano.
```

### Il testo per Lovable: il template del modello

Da incollare dopo il testo della texture. Non servono segreti nuovi.

```text
Ogni modello costruito da PDF deve avere anche il suo template, scaricabile con "Scarica Template" come quello del Nutella 750 g: un PSD con la texture del modello e le guide UV, fatto dallo Space. Il contratto completo è in GLAM.md, sezione 9, del repository iccio84/pack3d-studio.

1. Dalla pagina dello Space. Nel componente di "Costruisci modello 3D da PDF", dove ascolti già "pack3d:built" e "pack3d:texture", ascolta anche { type: "pack3d:template", nome, blob, glb }, con lo stesso controllo e.origin === window.location.origin, e solo se blob è un Blob (tipo image/vnd.adobe.photoshop) di al massimo 50 MB e nome finisce in .psd. Trattalo come la texture: tieni l'ultimo ricevuto, e quando salvi il modello di "pack3d:built" con blob.size uguale a glb, salva il template per quel modello con le stesse funzioni del server di "Carica Template": file nel bucket "templates", registrato per il model_key del modello appena salvato ("up_" + id), col nome del file = nome. Può arrivare anche dopo che il modello è stato salvato (lo Space ci mette qualche secondo): se il modello con quella misura è già salvato, salvalo subito per lui. Se non si salva, il modello resta: toast "Template non salvato".

2. Nuovo endpoint server POST /api/import-template, autorizzato esattamente come /api/import-model (Bearer PACK3D_IMPORT_TOKEN). Il corpo sono i byte del PSD: Content-Type image/vnd.adobe.photoshop, al massimo 50 MB, e deve cominciare con i quattro byte "8BPS". Intestazioni: X-Model-Name e X-Model-Category (decodeURIComponent, come in /api/import-model), X-Template-Name (decodeURIComponent, al massimo 160 caratteri, finisce in .psd) e X-Pack3d-Codice facoltativa. I destinatari sono quelli di /api/import-texture. Per ciascuno trova il suo modello con quel nome e quella categoria (il più recente) e salva il PSD come fa "Carica Template": bucket "templates", registrato per il model_key "up_" + id del modello, al posto del template che aveva. Risposte come /api/import-texture: 200 {"ok": true, "utenti": N}; 400 col motivo; 401 token sbagliato; 404 se nessun destinatario ha il modello.

3. "Scarica Template" scarica il template del modello selezionato col suo nome di file. Tutto il resto resta com'è: il template del Nutella 750 g, "Carica Template" per chi carica a mano, la texture e il suo "Carica texture".
```

### Il testo per Lovable: il caso inviato chiude la finestra

Da incollare dopo i testi qui sopra. Non servono segreti nuovi.

```text
Quando chi ha caricato un PDF manda un caso nuovo dalla pagina dello Space ("Invia il caso"), il dialog di "Costruisci modello 3D da PDF" deve chiudersi da solo, così si vede che il lavoro è finito. Il contratto completo è in GLAM.md, sezione 1, del repository iccio84/pack3d-studio.

1. Nel componente di "Costruisci modello 3D da PDF", dove ascolti già "pack3d:caso" dall'iframe, ascolta anche { type: "pack3d:chiudi", codice, titolo, testo }, con lo stesso controllo: e.origin === window.location.origin ed e.source uguale alla contentWindow dell'iframe. Arriva subito dopo il "pack3d:caso" dello stesso caso: il caso registralo come fai già, senza aspettare che la registrazione finisca per chiudere.

2. Quando arriva, chiudi il dialog come fai dopo aver salvato un modello, e mostra un toast di successo con titolo (testo semplice, al massimo 120 caratteri; "Caso inviato" se manca) e, come descrizione, testo (testo semplice, al massimo 300 caratteri). Mostrali come testo, mai come HTML.

3. Tutto il resto resta com'è: "pack3d:caso", "pack3d:built" e il salvataggio del modello con texture e template, i casi, le notifiche e il badge.
```
