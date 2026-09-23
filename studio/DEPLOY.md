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
| `ANTHROPIC_API_KEY` | Secrets | la chiave | solo `/api/analyze-ai`, l'agente che legge la fustella |
| `OPENAI_API_KEY` | Secrets | la chiave | solo il controllo visivo dell'agente |

Le chiavi vanno in **Secrets**, non in Variables: le Variables si leggono in
chiaro dalla pagina dello Space.

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
**ghostscript**. Serve a una cosa sola e non c'e' altro modo di farla: simulare
la sovrastampa, che pdfium non simula. Vedi in REGOLE.md *La colata si rimette
con l'inchiostro del file*.

Costa una quarantina di MB di immagine e non si vede mai al lavoro: gira solo
sui file che hanno la colata su un livello suo, e solo sulla sua banda - misurato,
un paio di secondi e una quarantina di MB di processo figlio. Se manca, il
codice se ne accorge (`shutil.which`) e usa la risorsa: non si rompe niente.

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

## Limiti

- **Una** costruzione alla volta (`PACK3D_MAX_JOBS`), la seconda riceve 503
  con invito a riprovare. Meglio respingere che far cadere il servizio.

  Il numero **non si alza**, su nessuna macchina: pdfium non e' thread-safe e
  due costruzioni insieme fanno morire il processo intero. Vedi sopra, *I 16
  GB non comprano due costruzioni insieme*. La memoria qui sotto dice quanto
  serve per **una**, ed e' l'altro motivo per cui su 512 MB i file grandi non
  passavano.

  Il numero viene dalla memoria, non dalla CPU. Picchi misurati su
  `/api/analyze` piu' `/api/build` nello stesso processo, qualita' web.
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
  cinque, perche' ogni pannello si ritaglia e si ripulisce a 200 dpi.

  Le istanze Free e Starter di Render hanno 512 MB: li' non ci stava nemmeno
  una costruzione sola dei file piu' grandi. Il kernel uccideva il processo a
  meta' e chi aspettava riceveva una risposta senza corpo, che nel browser
  diventa un errore senza testo.
- PDF fino a 60 MB.
- Nessuno stato conservato: i PDF finiscono in una cartella temporanea e
  vengono cancellati.
