# Mettere pack3d studio online

Serve un servizio che esegua il container: la pipeline e' Python e nel browser
non gira. Sotto la strada piu' rapida e una alternativa.

## A. Hugging Face Spaces — PRO, senza git, ~10 minuti

E' dove sta il servizio. I file si caricano dal browser, e l'hardware e' la
ragione per cui ci siamo spostati: **2 vCPU e 16 GB di RAM**, contro lo 0,1
CPU e i 512 MB del piano gratuito di Render.

**Serve un account PRO** (circa 9 $/mese). Gli Spaces con SDK **Docker**
girano su calcolo, e da meta' 2026 non sono piu' nel piano gratuito: li'
resta solo lo *Static*, che non ci serve - a noi servono Python, pdfium e
ghostscript.

1. Vai su https://huggingface.co/new-space
2. **Owner** il tuo account, **Space name** `pack3d-studio`
3. **License** a piacere, **Space SDK** scegli **Docker** -> *Blank*
4. **Hardware** CPU basic, visibilita' **Private**
5. Crea lo Space, poi apri la scheda **Files** -> **Add file** -> **Upload files**
6. Trascina dentro **tutto il contenuto** della cartella `studio`:
   `Dockerfile`, `README.md`, `requirements.txt`, `server.py`,
   `pack3d_studio.html` e la cartella `pack3d/` intera
7. Conferma con **Commit changes to main**

La build parte da sola (5-10 minuti la prima volta). Quando lo stato diventa
*Running*, il link e':

```
https://huggingface.co/spaces/TUO-UTENTE/pack3d-studio
```

Non c'e' niente da adattare: il `README.md` ha gia' l'intestazione che gli
Spaces si aspettano (`sdk: docker`, `app_port: 7860`) e il `Dockerfile` gira
gia' come utente 1000, che e' l'utente con cui gli Spaces eseguono il
container.

**Private, non Public.** Dentro ci passano artwork di clienti. Uno Space
pubblico lo apre e lo usa chiunque.

**Pausa.** Gli Spaces si mettono in pausa dopo 48 ore di inattivita' e si
risvegliano alla prima visita. Sono due giorni, non i quindici minuti di
Render: la rotella dell'interfaccia resta al suo posto, ma non la vedrai
quasi mai.

### Variabili d'ambiente

Dalle impostazioni dello Space, **Variables and secrets**. Nessuna e'
obbligatoria: senza, il servizio costruisce lo stesso.

| nome | dove | valore | a cosa serve |
|---|---|---|---|
| `PACK3D_MAX_JOBS` | Variables | `1` | e' gia' il default dell'immagine. **Non alzarlo**, vedi sotto |
| `ANTHROPIC_API_KEY` | Secrets | la chiave | il **controllo dell'AI** su ogni costruzione, il rigonfiamento "Scegli tu", e `/api/analyze-ai`. Senza, si costruisce come prima e un cartellino dice che il controllo e' spento |
| `PACK3D_MODEL` | Variables | il modello di Claude | quello dell'agente e del controllo; senza, quello scritto in `agent.py` |
| `PACK3D_MODEL_CONTROLLO` | Variables | un modello di Claude | solo se il controllo deve usare un modello diverso dall'agente |
| `PACK3D_EFFORT_CONTROLLO` | Variables | `low`, `medium`, `high` | quanto ragiona il controllo; `medium` se manca. Vuoto per non mandarlo, coi modelli che non lo accettano |
| `PACK3D_CONTROLLO` | Variables | `0` | spegne il controllo apposta, senza togliere la chiave |
| `PACK3D_CORREZIONE` | Variables | `0` | spegne solo la correzione degli inchiostri tecnici, e lascia il controllo |
| `PACK3D_CODA_REPO` | Variables | `utente/repository` | dove vanno i **casi nuovi**: un repository GitHub **privato**, vedi sotto |
| `PACK3D_CODA_TOKEN` | Secrets | un token GitHub | scrittura su contenuti e issue di quel repository, e di nient'altro |
| `PACK3D_ROUTINE_URL` | Variables | l'indirizzo `/fire` della routine | un caso appena entrato in coda **avvia subito** la routine che la lavora, vedi sotto |
| `PACK3D_ROUTINE_TOKEN` | Secrets | il token della routine | quello generato nel trigger API della routine; serve solo ad avviarla |
| `OPENAI_API_KEY` | Secrets | la chiave | solo il controllo visivo dell'agente |

Le chiavi vanno in **Secrets**, non in Variables: le Variables si leggono in
chiaro dalla pagina dello Space.

### Il controllo dell'AI e la coda dei casi nuovi

Con `ANTHROPIC_API_KEY` ogni costruzione finisce con una chiamata a Claude:
le prime pagine dei PDF e quattro viste del modello, e Claude dice se e' il
pack giusto (vedi REGOLE.md, *Il controllo dell'AI prima della consegna*).
Costa qualche centesimo di dollaro a costruzione, a seconda del modello; con
"Scegli tu" sul flowpack le chiamate sono due. Quando il controllo vede segni
del disegno tecnico rimasti, Claude sceglie gli inchiostri tecnici e il modello
si rifa' senza: una costruzione e due chiamate in piu', solo su quei modelli. La costruzione si allunga dei
secondi della risposta, ma il posto di costruzione si libera prima: il
prossimo utente non aspetta Claude.

I modelli respinti vanno in coda solo se c'e' un repository **privato**:

1. Su GitHub crea un repository **privato**, per esempio `pack3d-casi`.
2. Crea un token *fine-grained* (Settings -> Developer settings -> Personal
   access tokens) con accesso **solo** a quel repository, e i permessi
   *Contents: Read and write* e *Issues: Read and write*.
3. Nello Space: `PACK3D_CODA_REPO` = `tuo-utente/pack3d-casi` fra le
   Variables, `PACK3D_CODA_TOKEN` = il token fra i Secrets.

Ogni caso respinto diventa una cartella `casi/<data>_<codice>/` coi PDF, le
viste e la diagnosi, piu' una issue. Se il repository non e' privato non si
carica niente, e il log lo dice.

La coda la lavora una **routine di Claude Code** (claude.ai/code, Routines):
una sessione nuova che segue CODA.md, prova ogni correzione sul
parco del repository privato (`parco/`) e, se tutto torna, unisce da sola la
PR - quindi pubblica sullo Space. Poi prova il caso sullo Space vero
(`prove/parco.py spazio`), aspettando che `/api/ping` dica l'impronta del
codice appena unito. Per questo nella rete dell'ambiente cloud e' consentito
il dominio dello Space: Network access **Custom**, `iccio-maurizio.hf.space`
fra gli Allowed domains, con la lista di base dei package manager.

La routine parte **subito**: quando un caso entra in coda, lo Space la avvia
col suo trigger API (`coda.avvia_routine`). Parte anche una volta al giorno,
alle 6:56, come rete di sicurezza. Per collegarli:

1. Su claude.ai/code/routines apri la routine, menu accanto al nome ->
   **Edit**; in **Select a trigger** clicca **Add another trigger** ->
   **API**.
2. Copia l'**URL** (finisce con `/fire`) e clicca **Generate token**: il
   token si vede una volta sola.
3. Nello Space: `PACK3D_ROUTINE_URL` = l'URL fra le Variables,
   `PACK3D_ROUTINE_TOKEN` = il token fra i Secrets.

Lo Space la avvia solo per un caso nuovo, non quando lo stesso PDF viene
ricaricato mentre la sua issue e' aperta. Nel testo della chiamata c'e' solo
il codice del caso e il link alla issue. Se la chiamata non va, il log dello
Space dice perche' e il caso aspetta il giro di sicurezza. L'endpoint e' in
anteprima e la sua intestazione beta puo' cambiare: la nuova si mette in
`PACK3D_ROUTINE_BETA`, senza toccare il codice.

### I 16 GB non comprano due costruzioni insieme

E' la prima cosa che ho provato arrivando su una macchina grande, e non
funziona. Con `PACK3D_MAX_JOBS=2` e due flowpack lanciati insieme il server
muore **tutto intero**, a meta' della seconda costruzione, senza traceback. Il
motivo sta nel `dmesg` della macchina, non nel log del servizio:

    traps: python3 trap int3 in libpdfium.so

pdfium non e' thread-safe, e non lo e' **nemmeno su documenti diversi**: due
chiamate insieme sporcano l'heap nativo e si portano via il processo, cioe'
anche il lavoro di chi non c'entrava niente. La memoria non c'entra - nella
prova ne restavano quindici GB liberi.

Quindi il limite di **una costruzione alla volta resta**, ed e' strutturale:
non si compra con un piano piu' grande. Per farne due davvero servono due
**processi**, non due thread - o un lock unico attorno a ogni chiamata a
pdfium, che pero' rimette in fila esattamente quello che si voleva
parallelizzare. Nessuna delle due e' fatta.

## B. Render — dove stava prima

Funziona ed e' gratis, ma il piano Free da' **0,1 CPU e 512 MB**, e i file
grandi non ci stanno. Misurato: Colazione (flowpack, foglio steso 460 x 330
mm) tocca **648 MB di picco** e costa **67 secondi di CPU**, che a un decimo
di core sono **oltre undici minuti**. Il kernel lo uccide prima e chi aspetta
riceve un 502 vuoto.

Lo Starter costa 7 $/mese e porta la CPU a 0,5: divide l'attesa per cinque e
lascia la RAM a 512 MB. Cioe' aggiusta il sintomo che si vede e non quello
che uccide il processo. E' il motivo per cui ce ne siamo andati.

1. Metti la cartella `studio` in un repository GitHub
2. https://dashboard.render.com -> **New** -> **Web Service**
3. Collega il repository, **Language: Docker**, piano **Free**
4. Crea: Render assegna `PORT` da solo, il server la legge

URL finale: `https://pack3d-studio.onrender.com`. Il piano gratuito va in
sospensione dopo 15 minuti di inattivita'.

Il risveglio non e' muto: se la pagina sta altrove e punta qui con `?api=`,
l'interfaccia mostra una rotella con i secondi che scorrono - *"Sto svegliando
il servizio"* - invece di dichiararlo irraggiungibile dopo un secondo e mezzo.
Aspetta fino a due minuti, e se non risponde lascia un bottone **Riprova**
invece di obbligare a ricaricare.


## Aggiornare dopo una nuova regola

Quando la pipeline cambia, sostituisci i file modificati (di solito qualcosa
dentro `pack3d/`) e fai commit: la build riparte e il link resta lo stesso.

## Verifiche fatte in locale prima della consegna

| prova | esito |
|---|---|
| Porta 7860 e `PORT` da ambiente | ok |
| Astuccio KMS T10 | 200, 915 kB, 5,5 s |
| Flowpack FULFIL, 20 denti morbido | 200, 3591 kB, 3,4 s |
| Tre costruzioni insieme | 200, 200, 503 (coda piena) |
| Ripresa dopo il carico | 200 |
| Preflight CORS da altro dominio | 204 |
| File non PDF | 400 con messaggio |

## Dipendenze di sistema

Oltre a quelle Python del `requirements.txt`, l'immagine installa
**ghostscript**. Serve a leggere le **lastre**, che pdfium non separa: dove il
file e' nero (`nero`), le aree riservate (`techink`) e cosa c'e' sotto
un'immagine in sovrastampa (`strati.sovrastampa`, a 36 dpi, mezzo secondo).
Vedi in REGOLE.md *Un'immagine in sovrastampa si somma a quello che trova*.

Costa una quarantina di MB di immagine e passate brevi a bassa risoluzione. Se
manca, il codice se ne accorge (`shutil.which`) e fa meno: non si rompe niente,
e la sovrastampa resta simulata per le Separation e i DeviceN, cioe' per la
colata di quasi tutti i file.

## Quando una costruzione non arriva in fondo

Se il processo muore - ucciso per memoria, o tagliato dalla piattaforma
perche' ci mette troppo - la risposta non arriva e nel browser esce un **502
senza niente dentro**. Non si sa nemmeno in quale pezzo sia morto.

Per questo ogni costruzione lascia una traccia sul log del servizio, una riga
per fase, scritta **appena la fase finisce**: se il processo muore dopo, le
righe gia' stampate restano. Sulla dashboard di Render stanno sotto **Logs**.

    [pack3d] analisi           0.4 s     69 MB ora,    69 max  vassoio, 3077 kB
    [pack3d] costruzione       4.6 s    164 MB ora,   260 max  1106 kB
    [pack3d] totale            5.0 s    164 MB ora,   260 max

I numeri di memoria sono due perche' servono tutti e due: *ora* e' quello che
il processo sta usando in quel momento, *max* il peggio da quando e' partito -
e quello non scende mai, quindi dopo tre costruzioni dice il massimo delle tre
anche se nessuna ci e' arrivata vicino.

**Come si legge:**

- l'ultima riga e' `totale` → la costruzione e' arrivata in fondo, il 502 e'
  venuto da altro;
- l'ultima riga e' `analisi` → e' morta costruendo;
- non c'e' nessuna riga → e' morta prima, cioe' nell'analisi;
- `ora` vicino al tetto della macchina sull'ultima riga → e' la memoria;
- `ora` basso e i secondi alti → e' il tempo.

**I secondi scritti sono secondi di CPU, non di attesa.** Per sapere quanto
dura davvero si dividono per la CPU che la macchina da': su uno Space (2 vCPU,
ma la pipeline e' a un thread sola) restano quelli; sul piano Free di Render,
che ne dava 0,1, andavano moltiplicati per dieci.

### Quanto costa ogni file, per fase

Misurato il 23 settembre 2026, un file per processo, processo pulito ogni
volta. *Vivi* e' la memoria ancora in mano a fine analisi, *picco* il massimo
del processo.

| file | tipo | analisi | costruzione | CPU totale | vivi | picco |
|---|---|---|---|---|---|---|
| Colazione | flowpack | 41,5 s (41,0 cpu) | 28,9 s (25,7 cpu) | 66,7 s | 460 MB | **648 MB** |
| K Brioss STD | flowpack | 18,3 s (18,4 cpu) | 7,9 s (3,2 cpu) | 21,6 s | 279 MB | 387 MB |
| K Pingui T6 BOX | astuccio | 2,2 s (2,1 cpu) | 4,4 s (3,7 cpu) | 5,8 s | 90 MB | 361 MB |
| KMS Display | vassoio | 0,4 s (0,4 cpu) | 4,4 s (3,7 cpu) | 4,1 s | 63 MB | 240 MB |

Questi numeri **non tornano** con la tabella qui sotto, che per Colazione dava
434 MB e 20 s di CPU. Non so quale delle due misure sia sbagliata e non l'ho
cercato: sono state prese a mesi di distanza, con il codice cambiato in mezzo
e in un solo caso una per volta in un processo pulito. Mi fido di queste, e
quelle restano per gli altri quattro file che qui non ci sono. Il numero piu'
solido di tutti e' comunque un altro: i **460 MB ancora vivi** a fine analisi
di Colazione, che su una macchina da 512 MB non lasciano spazio per costruire.

### In HD, di serie

Dal 27 settembre 2026 la texture e' a 300 dpi con un tetto di 8192 px di lato
(`TEXTURE` in `pack3d/artwork.py`, per tutte le famiglie e anche dalla riga di
comando; `quality: "web"` rida' i 200 dpi e i 1700 px di
prima). Costa tempo e memoria, e sugli Spaces l'uno e l'altra ci sono. Misurato
su questo container, un file per processo, due processi alla volta sui quattro
core:

| file | tipo | analisi | costruzione | picco | texture | GLB |
|---|---|---|---|---|---|---|
| Colazione | flowpack | 23,5 s | 85,6 s | 987 MB | 3897 x 5433 | 5,3 MB |
| K Brioss STD | flowpack | 4,2 s | 25,8 s | 1186 MB | 3425 x 4960 | 5,9 MB |
| K Brioss Latte e Cacao | flowpack | 4,3 s | 13,0 s | 536 MB | 3425 x 4959 | 5,5 MB |
| KMS T1 | flowpack | 1,6 s | 13,3 s | 486 MB | 1801 x 1700 | 4,3 MB |
| K Tronky T1 | flowpack | 1,3 s | 9,1 s | 873 MB | 1701 x 980 | 3,6 MB |
| KP T1 Mandarino | flowpack | 1,6 s | 7,5 s | 316 MB | 1759 x 1599 | 4,1 MB |
| Kinder Country | flowpack | 2,5 s | 4,3 s | 409 MB | 1406 x 1441 | 4,4 MB |
| Kinder Paradiso T1 | flowpack | 1,6 s | 2,6 s | 307 MB | 1831 x 1949 | 4,3 MB |
| KCF T1 | flowpack | 14,0 s | 1,9 s | 212 MB | 1358 x 1193 | 3,6 MB |
| K Pingui T6 BOX | astuccio | 2,7 s | 6,1 s | 579 MB | fronte 1659 x 1476 | 0,8 MB |
| Nutella Donut | astuccio | 3,5 s | 8,5 s | 625 MB | fronte 2254 x 2226 | 2,2 MB |
| KMS Display | vassoio | 0,5 s | 12,9 s | 874 MB | 5846 x 8192 | 3,4 MB |

Il file lento e' sempre Colazione: quasi due minuti, dei quali una sessantina
sono la resa del foglio a 300 dpi. Non sono i tratti, sono le 21 immagini con
trasparenza della grafica, e ritagliare la resa sul foglio non aiuta perche'
stanno tutte dentro il foglio. Vedi REGOLE.md, *La texture e' HD di serie*.

## Limiti

- **Una** costruzione alla volta (`PACK3D_MAX_JOBS`), la seconda riceve 503
  con invito a riprovare. Meglio respingere che far cadere il servizio.

  Il numero **non si alza**, su nessuna macchina: pdfium non e' thread-safe e
  due costruzioni insieme fanno morire il processo intero. Vedi sopra, *I 16
  GB non comprano due costruzioni insieme*. La memoria qui sotto dice quanto
  serve per **una**, ed e' l'altro motivo per cui su 512 MB i file grandi non
  passavano.

  Il numero viene dalla memoria, non dalla CPU. Picchi misurati su
  `/api/analyze` piu' `/api/build` nello stesso processo, qualita' web - cioe'
  prima dell'HD: per quelli di adesso vedi *In HD, di serie*.
  Lo steso e' nastro x passo sui flowpack, ingombro della fustella sugli
  astucci:

  | pack | tipologia | steso | picco | CPU |
  |---|---|---|---|---|
  | Colazione | flowpack | 460 x 330 mm | 434 MB | 20,0 s |
  | Nutella Donut | astuccio | 452 x 265 mm | 402 MB | 6,8 s |
  | K Pingui T6 | astuccio aperto | 261 x 270 mm | 354 MB | 4,6 s |
  | K Country | flowpack | 122 x 119 mm | 274 MB | 3,2 s |
  | K Brioss | flowpack | 420 x 290 mm | 247 MB | 4,4 s |
  | K Paradiso | flowpack | 165 x 155 mm | 233 MB | 2,4 s |
  | K Brioss STD | flowpack | 420 x 290 mm | 216 MB | 4,7 s |
  | K Tronky T1 | flowpack | 83 x 144 mm | 199 MB | 1,7 s |

  Presi tutti nello stesso giro e sulla stessa macchina, perche' il picco varia
  di qualche decina di MB col carico: Colazione, misurata prima, dava 386 MB
  contro i 434 di adesso, e il codice di allora rimisurato oggi da' 442. Le
  cifre servono a dimensionare, non a confrontare due versioni: per quello si
  misurano prima e dopo di seguito.

  Sui flowpack il picco e' quasi tutto nella rasterizzazione della pagina per
  l'analisi, e la costruzione costa fra 0,5 e 2,1 s. Sugli astucci e'
  rovesciato: l'analisi e' un paio di secondi e la costruzione se ne prende
  cinque, perche' ogni pannello si ritaglia dalla resa della grafica - allora
  a 200 dpi, oggi a 300.

  Le istanze Free e Starter di Render hanno 512 MB: li' non ci stava nemmeno
  una costruzione sola dei file piu' grandi. Il kernel uccideva il processo a
  meta' e chi aspettava riceveva una risposta senza corpo, che nel browser
  diventa un errore senza testo.
- PDF fino a 60 MB.
- Nessuno stato conservato: i PDF finiscono in una cartella temporanea e
  vengono cancellati.
