# Regole: Il servizio

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Un servizio che si sveglia non e' un servizio rotto

Un servizio ospitato si mette in pausa quando nessuno lo usa, e a svegliarlo
e' la prima richiesta che arriva: un'attesa che si misura in decine di
secondi. Quanto sia lunga la quiete prima della pausa cambia con chi ospita —
quindici minuti sul piano gratuito di Render, dove questa regola e' nata,
quarantotto ore su uno Space — ma il momento in cui capita e' sempre lo
stesso, ed e' il peggiore: e' la prima persona che torna a lavorare dopo una
pausa, non una a caso.

La sonda del frontend scadeva dopo **un secondo e mezzo**, quindi scriveva
*"Backend non raggiungibile"* di un servizio che stava benissimo e si stava
solo alzando — e per riprovare bisognava ricaricare la pagina.

Percio' la ricerca del backend e' in **due tempi**:

1. **Il giro veloce**, un secondo e mezzo per candidato: trova subito un
   server locale, o uno remoto gia' sveglio, e non fa aspettare nessuno.
2. **L'attesa vera**, fino a due minuti, con la rotella che gira e i secondi
   che scorrono — ma solo se c'e' un candidato **remoto** da svegliare. Sulle
   porte di `localhost` non c'e' niente da aspettare: o il server c'e' o non
   c'e', e far girare una rotella per due minuti sarebbe una bugia.

Tre cose che non sono dettagli:

- **Il tentativo resta aperto a lungo** (30 s). E' la richiesta stessa che
  sveglia il servizio: chiuderla presto butterebbe via il lavoro gia' fatto
  per farlo salire.
- **Fra un tentativo e l'altro ci vuole un respiro** (2 s). Un 502 del proxy
  davanti al servizio torna subito, e senza pausa il ciclo martellerebbe la
  macchina proprio mentre sta partendo.
- **Se alla fine non risponde, ci vuole un bottone.** Senza, l'unico modo di
  riprovare era ricaricare la pagina, e chi ha appena aspettato due minuti non
  se lo merita.

La rotella **non si spegne** con `prefers-reduced-motion`: e' l'unica cosa che
dice che il servizio sta salendo. Si rallenta, che e' quello che quella
preferenza chiede davvero.

### Dove la rotella NON arriva

Aprendo l'indirizzo del servizio **direttamente** mentre dorme, la rotella non
si vede: quella schermata — il *SERVICE WAKING UP* nero di Render, la pagina
di avvio di uno Space — e' di chi ospita, che tiene la richiesta mentre il
container si accende. Il nostro HTML — e quindi il nostro JavaScript — arriva
DAL container, che in quel momento non c'e' ancora. Non e' una cosa da
sistemare nel frontend: e' fuori dalla sua portata, sempre, con qualunque
host.

La rotella serve l'altro caso, che e' quello vero di chi usa lo strumento: la
pagina sta altrove — dentro il viewer glamlab, o su un host statico — e punta
al servizio con `?api=`. Li' la pagina compare subito e l'attesa la racconta
la rotella.

Per far sparire anche la schermata dell'host bisogna **separare la pagina
dall'API** (la pagina su un host statico, il servizio dove sta), tenere il
servizio sveglio con una chiamata periodica, o pagare un piano che non
sospende. Nessuna delle tre e' una modifica al frontend, e la scelta e' di
chi paga il servizio.

Spostandoci sugli Spaces la cosa e' diventata rara senza che toccassimo una
riga: la pausa arriva dopo due giorni di silenzio, non dopo un quarto d'ora.
Rara non vuol dire mai, e il codice della rotella resta dov'e'.

## pdfium non si chiama da due thread

Il servizio faceva **una costruzione alla volta** in un processo solo, e il
motivo non era la memoria. Adesso le fa in piu' processi: *Due processi: i
lavoratori*, qui sotto.

Arrivando su una macchina da 16 GB la prima cosa che ho fatto e' stata alzare
`PACK3D_MAX_JOBS` da 1 a 2: i conti tornavano - la costruzione piu' cara ne usa
648 MB, due insieme 1,3 GB, l'8% del tetto - e i core erano due. Provato con
due flowpack lanciati insieme, il server e' morto **tutto intero** a meta'
della seconda costruzione. Nessun traceback, nessun 503, nessun OOM: la prima
costruzione era gia' tornata col suo GLB buono, la seconda ha chiuso la
connessione senza dire niente.

Il perche' non stava nel log del servizio ma nel `dmesg` della macchina:

    traps: python3 trap int3 in libpdfium.so

**pdfium non e' thread-safe, e non lo e' nemmeno su documenti diversi.** Due
chiamate insieme sporcano l'heap nativo e si portano via il processo - cioe'
anche il lavoro di chi non c'entrava niente, e la sessione di chiunque altro
stesse usando il servizio in quel momento.

Tre cose da tenere a mente:

- **Il limite e' strutturale, non di budget.** Non si compra con un piano piu'
  grande, perche' non e' la RAM a metterlo. Per farne due davvero servono due
  **processi**, non due thread; un lock unico attorno a ogni chiamata a pdfium
  funzionerebbe, ma rimette in fila proprio quello che si voleva
  parallelizzare.
- **Muore senza dire niente.** Un crash nel C non lascia traceback in Python.
  Se il servizio sparisce e il log finisce a meta', la traccia per fase dice
  dov'era arrivato ma non perche' e' caduto: quello e' nel `dmesg`.
- **Il conto della memoria tornava.** E' il punto: i numeri giusti su una
  domanda sbagliata non salvano da niente. La prova con due file veri ha
  trovato in quaranta secondi quello che l'aritmetica non poteva trovare.

### Due processi: i lavoratori

Dal 28 ottobre 2026 le analisi e le costruzioni girano in processi a parte,
i lavoratori (`pack3d/lavoratori.py`): ognuno ha il suo pdfium e fa un
lavoro alla volta, con lo stesso codice di prima - il lavoratore rifa' la
richiesta com'era (`server.esegui_lavoro`). Il processo del server tiene le
connessioni, i casi in attesa della conferma di chi li ha caricati - un
lavoratore li rimanda indietro (`lavoratori.casi_rimandati`) - e le letture
del PDF per la pagina. Chi arriva coi lavoratori tutti occupati entra in
fila, invece di prendere «Server occupato»; la pagina chiede a che punto e'
(`/api/lavori`) e lo scrive nella riga di stato.

Provato in locale, coi PDF del parco:

- due costruzioni insieme, il flowpack piu' caro del parco e il film su
  scatola: 200 e 200 in 66 s, invece di circa 85 una dopo l'altra, coi GLB
  identici al parco;
- tre insieme con due lavoratori: la terza aspetta in fila e parte appena
  uno si libera, 200 tutte e tre;
- un lavoratore ucciso con un SIGSEGV a meta' costruzione, come fa pdfium:
  quella costruzione risponde 500, «il processo che la faceva e' caduto»,
  l'altra finisce, il lavoratore riparte e le costruzioni dopo escono
  identiche. Prima cadeva il server, con chiunque fosse collegato;
- il parco intero passando dai lavoratori: 43 modelli su 43 identici al
  byte, 43 letture del PDF, nessun lavoratore caduto.

Da tenere a mente:

- **Anche l'analisi passa da pdfium.** /api/analyze girava fuori dal posto di
  costruzione: un'analisi insieme a una costruzione poteva far cadere il
  server come due costruzioni. Adesso va a un lavoratore come la
  costruzione. /api/segnala no: prepara il caso e basta.
- **Lo stesso PDF allo stesso lavoratore.** L'analisi di un flowpack si
  ricorda per processo (`analisi_flowpack`), e la pagina chiede /api/analyze
  e subito dopo /api/build con lo stesso corpo: la costruzione va, se e'
  libero, al lavoratore che ha fatto l'analisi (l'impronta del corpo). Lo
  stesso T1 la seconda volta: 3,7 s invece di 5,9.
- **Quanti.** `PACK3D_LAVORATORI`, `auto` di serie: uno per vCPU del
  container (`lavoratori.quanti`), finche' stanno nella memoria - 1,5 GB
  ciascuno, il picco peggiore e' 1,2 - e al massimo otto. Le vCPU si leggono
  dal tetto del cgroup, che e' quello che lo Space vende: non da
  `os.cpu_count()`, che in un container dice i processori della macchina e
  non i suoi. Un container senza tetto ne prende due, come prima. Cosa ha
  visto lo dice `/api/lavori` (`macchina`) e la prima riga del log. Un
  numero al posto di `auto` vale quello; con `0` torna tutto nel processo del
  server, una costruzione alla volta. Dentro ogni lavoratore
  `PACK3D_MAX_JOBS` resta 1.
- **I processi nascono con `spawn`.** Un lavoratore che riparte dopo una
  caduta nasce mentre il server ha gia' i suoi thread, e un `fork` a quel
  punto si porterebbe dietro i lucchetti presi da loro.

### I tracciati di un PDF si leggono una volta

pdfplumber, per dare i tratti di una pagina, ne interpreta tutto il
contenuto, grafica compresa: da mezzo secondo a sette per pagina. E la
stessa pagina la chiedevano in tanti, ognuno riaprendo il file: `extract`, il
riconoscimento di vassoi, sportelli e plance, la fustella della punta, il
ripiego del flowpack. Misurato col profilatore sul riempimento della T1
caramel cheesecake: 47 letture di due PDF in una costruzione, 98 secondi su
115; e /api/build le rifaceva tutte dopo /api/analyze.

Dal 28 ottobre 2026 i tratti di una pagina si leggono una volta per file
(`dieline.tratti`) e si tengono in memoria e su disco (`PACK3D_CACHE`), dove
li trova anche l'altro lavoratore e quello che riparte dopo una caduta. Il
parco intero, prima e dopo: 43 modelli su 43 identici al byte, 910 s
invece di 1013 in tutto; il riempimento della T1 caramel cheesecake da 43 s a
22, la scatola a punta T6 da 45 a 31, il riempimento del display del
biscotto T3 da 60 a 43.

Il parco chiede solo /api/build. La pagina chiede /api/analyze e poi
/api/build, e li' si guadagna di piu', perche' la costruzione trova i tratti
gia' letti dall'analisi. Misurato in un processo solo, analisi piu'
costruzione, coi modelli identici al byte:

| caso | prima | dopo | un altro processo, col disco gia' pieno |
|---|---|---|---|
| riempimento della T1 caramel cheesecake | 23 + 44 s | 8 + 17 s | 3 + 16 s |
| scatola a punta T6 | 29 + 48 s | 18 + 17 s | 2 + 15 s |
| vassoio del biscotto T3 | 5 + 31 s | 4 + 22 s | |

L'ultima colonna e' l'altro lavoratore, o quello ripartito: l'analisi gli
costa due o tre secondi invece di venti o trenta.

- **La chiave e' il contenuto del file, non il nome.** Un PDF caricato vive
  in un file temporaneo, e lo stesso nome torna con un altro foglio.
- **Sul disco anche la versione.** Nella chiave c'e' l'impronta di
  `dieline.py` e le versioni di pdfplumber e pdfminer: una cartella tenuta
  fra due versioni del codice non da' i tratti letti da quella vecchia.
- **Chi vuole i tracciati li chiede a `dieline.tratti`**, non a pdfplumber:
  una lettura nuova e' una lettura che si paga a ogni costruzione.
- **Gli astucci non cambiano.** Il loro tempo e' la resa di pdfium - la
  texture a livelli, la colata, la spia del nero, la lettura - non i
  tracciati: sul T10 al lampone nove rese, 78 secondi su 100 col
  profilatore. Per quelle c'e' la cassa delle rese, qui sotto.

### Le rese di pdfium su disco

Su un artwork pesante la resa di pdfium e' quasi tutta la costruzione, e
non dipende dalla risoluzione: sul T10 al lampone ogni resa costa dieci
secondi fissi, anche a un decimo di scala, e una costruzione ne fa nove -
74 secondi su 93. Ricostruire lo stesso PDF con un'altra opzione le rifaceva
tutte: le casse di prima tenevano una pagina sola, per nome di file e per la
costruzione in corso, e i file temporanei cambiano nome a ogni costruzione.
Sul wafer da colazione erano 32 secondi su 48.

Dal 29 ottobre 2026 le rese costose restano su disco (`pack3d/rese.py`),
sotto la cartella dei tratti (`PACK3D_CACHE`), per tutti i lavoratori: la
lettura del PDF (`vista.pagina`), la spia del nero, le due rese della
colata, la scelta della sovrastampa, la texture a livelli (`strati.rendi`) e
la pagina com'e' (`dieline.render_page`). Misurato in un processo solo, coi
modelli identici al byte a quelli del parco:

| caso | prima costruzione | lo stesso PDF con un'altra opzione |
|---|---|---|
| T10 al lampone, apertura 60 | 92 s | 16 s |
| wafer da colazione, saldatura 1 | 48 s | 15 s |

Il parco intero, con la cassa vuota e poi piena: 43 modelli su 43 identici
al byte tutte e due le volte, letture uguali. Con la cassa vuota 732 s
invece di 801, perche' tre casi trovano le rese di quello prima: il T10
aperto da 88 s a 16, il riempimento col T10 da 91 a 24, il riempimento del
display del biscotto T3 da 41 a 33. Al secondo giro poco di piu', 656 s: le
rese di tutto il parco sono 1,9 GB, e prima di tornare ai primi casi il tetto
le ha gia' buttate. Chi ricostruisce lo stesso PDF le trova, ed e' quello
che conta.

- **La chiave e' il contenuto del file, e tutto quello che decide i pixel.**
  I file temporanei - la pagina unica, la copia coi livelli spenti, quella
  senza le coperture - hanno sempre gli stessi byte, misurato. Nella chiave
  ci sono poi la pagina, i parametri della resa e lo stato che chi rende ci
  mette intorno: per la texture a livelli i livelli tecnici, il riquadro
  stampato, le aree riservate e i segni scelti dall'AI (`strati.spegnendo`),
  con i CONTI che la resa lascia agli avvisi.
- **E la versione.** Il codice di `pack3d`, pypdfium2 e pdfium, Pillow,
  numpy, Ghostscript (`rese.versione`): un codice cambiato non trova le rese
  di quello di prima, e una resa presa dalla cassa e' identica al byte a una
  rifatta.
- **Solo le rese costose.** Si tengono quelle costate almeno un secondo
  (`rese.SOGLIA_S`): sugli altri PDF del parco una resa costa meno, e si
  rifa' prima di quanto si scriva.
- **Un tetto.** `PACK3D_RESE_MB`, di serie 2048: le rese di un PDF pesante
  sono 160-180 MB, e oltre il tetto se ne vanno le meno usate. Una resa che
  non si legge si butta e si rifa'.
- **Chi aggiunge una resa costosa la mette in cassa** con `rese.chiave`, e
  nella chiave mette tutto quello che, oltre al file, cambia i suoi pixel.

### Un lavoro, una cartella e uno stato

Un'analisi o una costruzione crea file temporanei - le copie a pagina unica
e girate, quella senza le lastre tecniche, quella coi livelli spenti, le
rese di Ghostscript - e i moduli tengono in cassa quello che ne ricavano. I
file finivano nella cartella temporanea del sistema e nessuno li cancellava:
con le prove di due settimane erano 2639 PDF, 18 GB, finche' il disco si e'
riempito e le costruzioni rispondevano 500. Misurato dopo: 32 file e 279 MB
lasciati da venti lavori, una quindicina di MB ognuno. E le casse passavano
da un lavoro all'altro: un lavoratore che vive a lungo si teneva un'immagine
della pagina per ogni astuccio costruito (`dieline._PREVIEW`), e l'agente
una resa a 300 dpi per ogni PDF (`tools._CLEAN`).

Dal 28 ottobre 2026 ogni lavoro - /api/analyze, /api/analyze-ai,
/api/build - ha la sua cartella e il suo stato (`pack3d/stato.py`):

- **I file temporanei vanno nella cartella del lavoro**: ogni
  `NamedTemporaryFile`, `mkdtemp` o `TemporaryDirectory` di un modulo che
  lavora sul PDF prende `dir=stato.cartella()`. Alla fine del lavoro la
  cartella si butta con tutto quello che c'e' dentro. Fuori da un lavoro -
  il parco, una prova a mano - `cartella()` e' None e vale quella del
  sistema.
- **Le casse di un lavoro solo si registrano**: `_X = stato.per_lavoro({})`.
  Partono vuote e si vuotano alla fine. Sono quelle che tengono un file
  temporaneo, o hanno la chiave sul percorso, o fanno da canale fra due
  funzioni dello stesso lavoro (`strati._SPENTI`, `strati._RISERVATE`).
- **Restano da un lavoro all'altro solo le casse con la chiave sul
  contenuto del file e un valore che non dipende da chi l'ha chiesto
  prima**: i tratti della pagina (`dieline.tratti`), le analisi del
  flowpack (`famiglie.flowpack._ANALISI`), i versi gia' decisi. Le copie girate e a
  pagina unica la costruzione le rifa', ma pypdf le riscrive identiche al
  byte, e le analisi in cassa si ritrovano.
- **Un lavoro alla volta per processo.** In un lavoratore lo e' gia'; nel
  processo del server (`PACK3D_LAVORATORI=0`) il secondo aspetta il primo,
  anche durante l'attesa del verdetto dell'AI. Lo chiede pdfium, e lo
  chiedono le casse: due lavori insieme se le vuoterebbero a vicenda.

Provato prima di cambiare: dieci casi del parco, ognuno in un processo
nuovo, costruiti da soli e dopo l'analisi dello stesso PDF, danno lo stesso
modello al byte. Lo stato non cambiava i modelli; lasciava i file e la
memoria. Il parco intero coi lavoratori, prima e dopo: 43 modelli su 43
identici al byte, nessuna misura approvata cambiata, 841 s invece di 850; e
nella cartella temporanea restavano 64 file e 397 MB, ora niente.

### Il registro delle famiglie

Il riconoscimento era una catena di `if` in `_analyze_pdf`, trecento righe
con la tipologia dichiarata intrecciata in ogni ramo: per sapere chi si
provava prima di chi bisognava leggerla tutta, e una forma nuova ci si
infilava a meta'. La scelta della costruzione, in /api/build, era un'altra
catena di `elif`.

Dal 29 ottobre 2026 sono due tabelle, oggi in `pack3d/famiglie/registro.py`:

- **`RICONOSCIMENTO`**: una riga per prova, nell'ordine in cui si fanno,
  con le tipologie dichiarate per cui vale e la sua `_prova_<forma>`. La
  prima che dice «e' mio» da' la lettura; una che dice «e' mio ma non si
  legge» ferma tutto. Le forme che il solutore astuccio rifiuta si provano
  solo se e' stato lui a rifiutarle (`errore_astuccio`), e leggono il
  foglio come l'ha lasciato lui, girato nel verso della grafica.
- **`COSTRUZIONI`**: per ogni famiglia letta, la funzione che prepara
  `costruisci(lastre, uscita)` con le scelte della pagina; una famiglia che
  non c'e' si costruisce come flowpack.

**L'ordine e' la regola**, e non e' cambiato: niente punteggi, perche' un
punteggio cambierebbe strada a qualche caso. Una forma nuova e' una
funzione e una riga per tabella, dopo quelle che ci sono (FORME.md).

Provato contro la catena di prima: ogni PDF del parco letto con ogni
tipologia dichiarata e senza, 440 letture su 440 identiche, i 303 errori
compresi parola per parola; le undici costruzioni chiamate con gli stessi
argomenti, incarto compreso, che il parco non ha; il parco intero, 43
modelli su 43 identici al byte.

La tabella ha fatto vedere una cosa che la catena nascondeva: un
cartotecnico dichiarato, se il solutore astuccio non trovava pannelli senza
fermarsi, arrivava fino alla prova del flowpack. Ora e' un rifiuto come gli
altri: si provano punta, coppa e tubo, e se nessuno e' suo si ferma
(REGOLE.md, *La dichiarazione vale anche quando dice di no*). Dei 44 PDF del
parco, letti dichiarati cartotecnico, nessuno passava da li'.

### Le famiglie fuori da server.py

`server.py` era arrivato a cinquemila righe: il servizio - le richieste, i
lavoratori, il controllo dell'AI, il verdetto, la coda - e insieme la
lettura e la costruzione di ogni famiglia, `build_flowpack` da sola
cinquecento. Per correggere un flowpack si apriva il file del server, e
ogni correzione di una famiglia toccava il file di tutte.

Dal 29 ottobre 2026 le famiglie stanno in `pack3d/famiglie/`, un modulo per
famiglia - `flowpack`, `astuccio`, `vassoio` (con la plancia e la scatola),
`coppa` (col cono e il prisma), `pouch`, `ballotin`, `punta`, `tubo`,
`incarto`, `riempimento` - piu' `comune` e il `registro` (`RICONOSCIMENTO`
e `COSTRUZIONI`). `server.py` e' il servizio, millecinquecento righe, e
importa dalle famiglie solo quello che usa.

- **Spostate parola per parola.** Uno script ha preso ogni funzione e ogni
  costante coi commenti che la precedono, e un controllo sull'albero del
  codice dice che sono uguali a prima tranne una: `analisi_riempimento`
  importa `analyze_pdf` dentro la funzione, perche' il registro usa il
  riempimento e il riempimento il registro. Il parco intero, prima e dopo:
  43 modelli su 43 identici al byte, letture uguali.
- **Una famiglia nuova va nel suo modulo**, con la riga in `RICONOSCIMENTO`
  e la voce in `COSTRUZIONI` (FORME.md), non in `server.py`.
- **`comune` non importa nessuna famiglia, e le famiglie non importano
  `server`**: il servizio usa le famiglie, mai il contrario.

### Le prove veloci

Il parco dice CHE cosa si e' rotto, ma ci mette da venti a quaranta minuti e
non dice dove. Due prove lo dicono prima:

- **`prove/test_veloci.py`**, meno di un secondo e nessun file dei clienti:
  la lettura della fustella (la griglia di un foglio disegnato dalla prova, i
  tratti in cassa uguali a quelli letti, la chiave sul contenuto), le misure
  del modello (l'ingombro di un GLB costruito dalla prova, le tolleranze), il
  registro delle famiglie (l'ordine, le dichiarazioni che fermano, una
  costruzione per famiglia), lo stato di un lavoro, i lavoratori. Girano su
  ogni PR e su ogni unione nel ramo della settimana
  (`.github/workflows/prove.yml`):

      python3 -m unittest discover -s prove -p "test_*.py"

- **`prove/parco.py letture CASI`**: la lettura di ogni caso del parco -
  famiglia, misure, cartellini, come la chiede la pagina prima di costruire
  - contro quella approvata in `parco/letture.json` del repository dei
  casi, senza costruire. Dice a quale caso una correzione ha cambiato strada,
  e come. Su questa macchina da due a sei minuti, secondo il carico (113 s,
  307 s, 388 s su tre corse uguali). `--approva` le scrive approvate, come
  le misure: le letture cambiate apposta si approvano nella PR del caso.

Una prova veloce che fallisce si guarda prima del parco: il parco dice lo
stesso, mezz'ora dopo. Provate: sul codice di prima della correzione del
cartotecnico le due prove della dichiarazione falliscono, su questo
passano; e le 43 letture del parco col codice nuovo sono uguali a quelle
approvate col codice di prima.
