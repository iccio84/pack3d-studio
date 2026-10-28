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

Il servizio fa **una costruzione alla volta**, e il motivo non e' la memoria.

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
