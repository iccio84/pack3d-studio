# Regole della pipeline pack3d

Regole accumulate caso per caso, con il punto del codice che le applica e i
controesempi che le giustificano.

Questo file ha i principi, che valgono per tutte le famiglie, le domande
all'utente e l'indice. Le regole di ogni famiglia e di ogni passaggio stanno
in `regole/`, un file per argomento: chi corregge un caso legge questo file
e poi solo il pezzo che gli serve del file della sua famiglia. Una sezione
citata altrove - «REGOLE.md, *La scatola a punta*» - si trova nell'indice in
fondo, che dice in che file sta.

I prodotti dei casi hanno nomi neutri - il T1 al mandarino, la brioche STD,
il display T1x48 - perche' nel repository pubblico non vanno i nomi dei
clienti. Quale prodotto e' ognuno, col suo caso del parco e i suoi PDF, lo
dice `regole/nomi.md` nel repository privato dei casi.

## Tre regole, per tutte le famiglie

Vengono prima di ogni altra regola, qui e in `regole/`, e valgono per **flowpack,
astucci e vassoi** su ogni percorso: l'interfaccia, la riga di comando,
l'agente AI e i casi tarati a mano. Nessuna famiglia e nessun percorso ha una
versione ridotta.

| regola | flowpack | astuccio | vassoio |
|---|---|---|---|
| **Grafica** | si' | si' | si' |
| ↳ **box colorati via (i bianchi restano), e la GDA** | si' | si' | si' |
| **Testate dal DT** | pinna e gola | pannelli e alette | fondo, testate e laterali |
| **Pinne** | si' | - | - |

**1. Grafica.** La grafica si prende dal suo livello: disegno tecnico e note
si spengono oggetto per oggetto, in pdfium, prima di rendere, e sotto resta la
grafica intera (`strati.py`, `folding.rasterize_panels` con `clean`). La
texture e' **HD** di serie, 300 dpi fino a 8192 px (`artwork.risoluzione`, la
stessa per server e riga di comando). Colata in sovrastampa e `k` nera del
marchio restano quelle del file. Vedi *I due livelli li fa la
costruzione, oggetto per oggetto* e *La texture e' HD di serie*.

**I box area si tolgono sempre, come la GDA** - anche quelli verdi - su ogni
modello 3D, flowpack e astucci compresi: `TEXT AREA`, `GDA`, `BEST BEFORE`,
`BAR CODE`/`EAN`, `COVERED`, `PIN CODE`, `PRINT FREE`, `NEUTRAL` e ogni altra
lastra che si chiama area, **insieme alle loro didascalie** - il nome del box e
le scritte segnaposto che ci stanno dentro, "INGREDIENTS", "WEIGHT", "F8 LEGAL
TEXT". Sotto resta la grafica che il file ci ha messo. Si riconoscono dal nome
della lastra, e quando la lastra ha per nome un numero di Pantone dalla
didascalia scritta sul box o dalla legenda. Resta solo l'`AREA PROMO`, che e'
la grafica della promo e si stampa. Vedi *Le aree riservate non compaiono mai
nel render*.

**2. Testate dal DT.** Il pack si misura dal **disegno tecnico**, e il
contenuto - dove c'e' inchiostro - viene per ultimo e non misura niente: la
grafica puo' avere del bianco. Le testate sono le estremita' di ogni famiglia:
pinna e gola del flowpack, le alette di testa dell'astuccio con i suoi
pannelli, fronte e retro del vassoio con i laterali. Poi tre controlli, a ogni
costruzione:

- le misure contro le **quote scritte** nel file, quando si leggono come testo
  (`quote.riscontro_testate`, `riscontro_astuccio`, `riscontro_vassoio`): una
  catena di quote che torna le conferma, una catena o una terna del cartiglio
  che parla di questo pack e dice altro si **grida**, e quando le quote sono
  vettorializzate lo si dice e l'occhio le guarda sulla miniatura; sul
  flowpack, allora, pieghe e testate si ritrovano anche sulle copie in scala
  del DT (`quote.riscontro_miniature`, vedi *Prima delle tre regole*);
- **prima della mappatura**, le UV sul DT: le linee del modello sulle linee
  del disegno;
- **dopo**, il fronte sul fronte: centrato, normale verso chi guarda, niente
  di specchiato.

Vedi *Prima le misure, poi il contenuto* e *Le verifiche*.

**3. Pinne**, solo flowpack. La pinna e' il tubo appiattito: sulla pinna e
sulla gola la grafica cade come il film, che non si allunga - il giro si
misura sul film dal centro del fronte, la spalla e' lunga quanto serve al film
per coprire il calo del tubo, e sulla spalla il film si stende sulla
superficie. Senza ritagliare niente dalla texture. La terza verifica dice
quanto si stira. Vedi *La grafica sulle pinne: il film non si allunga*.

## Una regola per tutti, o una scelta del pack

Una regola nasce da un caso, e il caso la giustifica solo per se'. Fra il 26
e il 27 ottobre 2026 ne sono entrate e uscite quattro, tutte per tutti i
pack: il rigonfiamento nello spessore, la `pressa`, il cuscino e il fronte
rimappato. Ognuna sistemava il caso per cui era nata e ne rompeva un altro.
Il rigonfiamento nello spessore e' uscito col rilascio del 26 ottobre ed e'
stato tolto lo stesso giorno: sul T1 del vassoio da 36 la faccia passava da
40,1 a 37,1 mm e una lettera del marchio si vedeva schiacciata. Ha
funzionato lo stesso rigonfiamento come **scelta del singolo pack**
(`"gonfio": "spessore"`, vedi *Nello spessore, se lo si sceglie per il
pack*): il display da 15 che ne aveva bisogno l'ha avuto, e gli altri
modelli del parco sono rimasti identici al byte.

Quindi:

- **Una regola diventa di tutti solo se tutto il parco resta approvato.**
  `prove/parco.py costruisci` prima e dopo: nessuna misura approvata
  cambiata (`prove/parco.py misure`, *Le misure approvate: cambiato non vuol
  dire peggiorato*) e nessun modello cambiato che non sia voluto, guardato e
  approvato caso per caso.
- **Altrimenti e' una scelta del pack**, con un valore di serie che lascia i
  modelli di prima identici al byte. La scelta sta fra le opzioni del caso
  (`OPZIONI_CASO` in `server.py`, `opzioni` del caso nel parco); la pagina
  la chiede o la offre per la sua famiglia; il caso che l'ha voluta la
  tiene nel parco, e ogni rilascio la riprova.
- **Il valore di serie non cambia in silenzio**: cambiarlo e' una regola per
  tutti, e vale il primo punto.
- Una scelta che solo chi ha il pack puo' dire - la zigrinatura, il
  rigonfiamento, l'apertura delle pinne, quanti per fila - si chiede, non si
  indovina (*Domande all'utente*).
- La regola si scrive come sempre, nel file della sua famiglia: il caso, la
  causa, la regola, con i numeri. Se e' una scelta del pack, anche quale
  caso la usa e con che valore.

## Domande all'utente

**La prima domanda e' la famiglia, prima di ogni PDF.** Appena aperta, la
pagina chiede: *Che tipo di Pack/Riempimento intendi realizzare?* - Flowpack,
Pouch, Cartotecnico, Vassoio, Riempimenti, Incarti - ognuna con la sua
descrizione in una riga. Senza la famiglia non si carica niente: un PDF trascinato prima
riceve solo la richiesta di sceglierla, e al server non parte nulla. Scelta
la famiglia, il passo della famiglia chiede il resto e ha **un posto per ogni
PDF**, col suo nome: si sa sempre quali file mancano.

| famiglia | cosa chiede, in ordine | dove |
|---|---|---|
| **Flowpack** - pack con saldature e pinne laterali | il PDF; dopo lo studio della fustella: il **numero dei denti** della zigrinatura, digitato e senza valore proposto (0 = pinne lisce); il **rigonfiamento**, da 1 (molto rigido, effetto sottovuoto) a 10 (molto gonfio, per prodotti tondeggianti o con aria), o "Scegli tu" e lo sceglie Claude guardando l'artwork; l'**apertura delle pinne**, da 1 (chiuse, alte quanto il pack) a 3 (molto aperte, a farfalla), che non si deduce dal rigonfiamento; la **saldatura delle pinne**, da 0 (pinne lisce) a 3 (le righe delle ganasce ben marcate, di serie); se il **film avvolge una scatola** | pannello `params`; `gonfiore()`, `controllo.rigonfiamento`, `build_flowpack` |
| **Pouch** - fondo a soffietto ed estremita' saldata | il PDF, e si costruisce | `build_pouch` |
| **Cartotecnico** | **astuccio** (un solo elemento che si chiude da solo) o **scatola** (due o piu' elementi, per esempio base piu' coperchio); lo **spessore della carta**, da 1 a 3; l'astuccio un PDF, la scatola **di quante parti** e' fatta e poi **esattamente quei PDF**, uno per parte. Dopo lo studio, se l'astuccio ha un'**apertura a strappo**: chiuso - e allora se si vuole la **fustella dell'apertura modellata** - o aperto, e allora di **quanti gradi** si apre il coperchio. Se ha una finestra, la **pellicola** | passo `carto`, `parti`, `spessore`; pannelli `strappo` e `pellicola`; `pezzi`, `spessore`, `apertura`, `incisioni`, `pellicola` nell'intestazione |
| **Vassoio** - contenitore espositivo per le CU, display con plancia compresi, realizzati vuoti | il PDF, e si costruisce | `build_vassoio`, `build_plancia` |
| **Riempimenti** - TU: un vassoio o un display con dentro le CU | che cosa e' il **pack (CU)**: flowpack o astuccio, e dell'astuccio lo spessore della carta; due posti, il **pack (CU)** e il **vassoio o display**, e finche' non ci sono tutti e due non si procede. Poi **quanti pack** mettere (vuoto = pieno) e le domande del flowpack, o - per l'astuccio con l'apertura a strappo - se se ne vuole la fustella modellata | `cu`, `analisi_riempimento`, `build_riempimento` |
| **Incarti** - un foglio di carta, alluminio o plastica che avvolge un prodotto | come si **chiude**: **a pieghe** (le barrette) o **avvolto** (tipo l'ovetto); due posti, il **PDF dello steso** e l'**immagine del prodotto** da incartare (JPEG, PNG o WebP), e finche' non ci sono tutti e due non si procede. Poi si costruisce, senza altre domande | passo `incarto-scelta`; `chiusura` e `prodotto` nell'intestazione; `analisi_incarto_dichiarato`, `build_incarto` |

Le famiglie da un PDF solo partono appena il PDF c'e'. Se la lettura o la
costruzione si ferma, si torna al passo coi PDF ancora al loro posto: se ne
cambia uno, o si riprova. *Annulla* e *Cambia tipo* tornano alla prima
domanda.

### Il cartotecnico dice di quanti pezzi e' fatto

Scelto **Cartotecnico**, la pagina chiede se e' un **astuccio** - un pezzo
solo - o una **scatola**, e della scatola di quante parti e' fatta, da 2 a 8:
come i dentini, non si deduce. Ogni parte e' un PDF, e il risolutore lo deve
sapere prima di cominciare - un astuccio e' un file solo, la coppa col tappo
sono due, lo sleeve e il tappo, e da un file solo non c'e' modo di sapere che
l'altro esiste. La pagina mostra un posto per parte e si va avanti solo con
tutti i PDF; se ne arrivano di piu' insieme, quelli in piu' non si prendono e
lo si dice. Il server ricontrolla: `pezzi` nell'intestazione deve essere il
numero dei PDF arrivati, o la richiesta torna indietro.

- **Un pezzo**: l'astuccio, come sempre - ma prima si guarda se e' lo steso
  di un cono, dai soli tratti, in due decimi di secondo (`coppa.e_un_cono`):
  sul cono il solutore astuccio trovava fra le icone un "astuccio" di
  18,7 x 5,9 x 2,5 mm e il cono non veniva mai provato. Se l'astuccio non si
  risolve e il PDF e' un pezzo di una coppa - che e' cartotecnica anche lei -
  esce la coppa, e il primo cartellino lo dice; se il PDF e' un disco, il
  messaggio consiglia di caricarlo col suo cono, perche' un lid da solo non
  dice di essere un lid; se no resta l'errore dell'astuccio.
- **Piu' pezzi**: va al risolutore dei pack in piu' PDF (`in_piu_pezzi`).
  Oggi sa montare la coppa col tappo e il cono col lid, e quale PDF e' quale
  pezzo lo dice la pagina, non l'ordine (`server._pezzi_tondi`). Un PDF che
  non e' un pezzo che sappia montare ferma la costruzione e il messaggio dice
  quale, e cosi' due PDF di pack diversi - lo sleeve di una coppa col lid di
  un cono: un pack plausibile coi pezzi sbagliati e' il difetto peggiore,
  vedi sotto.

### Il cartotecnico dice di che carta e' fatto

Nello stesso passo la pagina chiede lo **spessore della carta**, da 1 a
3, e anche questo non si deduce: senza la scelta non si va avanti. Il cono
gelato e' poco piu' spesso di un foglio di carta, un astuccio no, e dal PDF
non si legge - il cartiglio della coppa lo scrive, quello del cono no.

| livello | carta | mm | per esempio |
|---|---|---|---|
| 1 | carta | 0,10 | il cono gelato, carta e alluminio |
| 2 | cartoncino | 0,40 | astucci e coppe |
| 3 | cartoncino spesso | 0,70 | |

Il livello arriva al server come `spessore` (`SPESSORI_CARTA`), un valore
fuori da 1-3 torna indietro, e lo spessore fa le coste e il rovescio
dell'astuccio (`folding.build_faces`), il rovescio, il fondo e il sormonto
della coppa, il rovescio, il risvolto e il sormonto del cono; il cartellino
lo dice. **Senza dichiarazione** - dall'API - ogni famiglia tiene il suo:
0,45 l'astuccio (`PACK3D_SPESSORE_CRT`), 0,35 la coppa (dal cartiglio della
coppa da 500), 0,10 il cono, e i modelli restano quelli di prima byte per
byte.

### L'apertura a strappo: chiusa o aperta

Quando l'astuccio ha un'apertura a strappo, la pagina chiede come lo si
vuole, senza proporre niente:

- **chiuso**, e allora se si vuole la **fustella dell'apertura modellata**:
  si', i tagli come solchi nel cartone (vedi *L'apertura a strappo si incide,
  non si disegna*); no, l'astuccio liscio, come se l'apertura non ci fosse
  (`incisioni: 0`);
- **aperto**, e allora di **quanti gradi** si apre il coperchio, da 1 a 180
  (proposti 60), con la finestra sollevata sulla sua cerniera e la scatola
  appoggiata sulla faccia opposta (vedi *L'apertura a strappo, aperta*).

Dall'API, senza `incisioni`, l'astuccio chiuso porta i solchi come prima.

La domanda si fa solo se c'e' qualcosa da chiedere. L'analisi che la pagina
chiede prima di costruire (`/api/analyze`) cerca l'apertura con la **stessa
lettura** della costruzione (`apertura.trova`, che e' `apertura._leggi`): la
firma del taglio davanti col taglio dal rovescio accanto, e la cerniera su
una piega. Se la trova, la risposta porta `strappo` - dove sta la finestra, a
quale piega resta attaccata, su che faccia gira la linguetta - e un
cartellino; la pagina mostra il pannello con quella frase, e la costruzione
riceve `apertura` in gradi (0 chiusa). Un astuccio senza apertura non vede
nessun pannello, e si costruisce subito come prima.

La lettura costa: sul T1 al cioccolato fresco 2,5 secondi in piu' nell'analisi, mezzo
secondo su un astuccio senza apertura. Per questo la fa solo l'analisi
chiesta dalla pagina, e non quella che `/api/build` rifa' prima di
costruire. In Glam Lab la pagina e' la stessa, dentro la cornice: la domanda
arriva anche li', senza toccare Glam.

### La dichiarazione vale anche quando dice di no

Una tipologia dichiarata non serve solo a scegliere il solutore: serve a
**fermarsi**. Chi ha detto "vassoio" e si sente rispondere con un flowpack non
ha ricevuto un ripiego, ha ricevuto la famiglia sbagliata senza saperlo — ed e'
il difetto peggiore che questo progetto possa avere, perche' il modello esce
plausibile.

Il ramo del vassoio ce l'aveva: se la griglia non era quella di un espositore
la funzione scivolava fino in fondo e usciva un flowpack. Adesso si ferma
dicendo che ci vogliono cinque colonne e tre fasce e quante se ne leggono
davvero, cosi' chi guarda impara che cos'e' che non torna. E sta **dentro i
200 caratteri** che l'interfaccia mostra: piu' lungo, e veniva tagliato via
proprio il consiglio finale, cioe' l'unico pezzo che dice cosa fare.

Lo stesso vale per i nomi. `SINONIMI_KIND` traduce le etichette con cui la
tipologia puo' arrivare — `cartotecnico` e `astuccio` per l'astuccio,
`espositore`, `display` e `tray` per il vassoio — perche' **una dichiarazione
che non viene riconosciuta e' come non averla**: il viewer glamlab mandava
`cartotecnico` e ogni astuccio finiva dal solutore flowpack. E il messaggio
che elenca le tipologie accettate si scrive da `KIND_NOTI`, non a mano: quando
ne e' arrivata una terza il messaggio ne nominava ancora due.

L'apertura delle pinne dice come si comporta il film **alle ganasce**, il
rigonfiamento che forma prende il **corpo**: sono due cose diverse e vanno
chieste separatamente.

| | bordo della pinna | quando |
|---|---|---|
| 3 | meta' perimetro: la pinna e' piu' alta del pack | il caso normale, il tubo si appiattisce. Il T1 della barretta fresca |
| 2 | in mezzo | il prodotto occupa quasi tutta la sezione ma lascia respiro alle estremita' |
| 1 | quanto la faccia del pack, senza svaso | il film avvolge un corpo rigido fino alla saldatura: non c'e' niente da appiattire. La brioche |

Il rigonfiamento e' una **scala 1-10**, non tre gradini: Rigido 1-3 (pack teso e
aderente, aria minima), Medio 4-6 (volume standard, leggero cuscino d'aria),
Morbido 7-10 (volumetrico e visibilmente gonfio, gas o liquidi). I parametri di
forma si interpolano sul livello.

Riferimenti: la barretta proteica = morbido; il T1 della barretta fresca (una merenda al latte in
film teso) e il croccante T2 fondente (un wafer) = rigido.

Attenzione pero': il T1 della barretta fresca e' film teso su un prodotto, non su una
scatola, e **non e' l'estremo rigido della scala**. La brioche lo e' di
piu': il film avvolge un astuccio, quindi la sezione e' dettata dalla scatola e
la pinna non si apre. Quel caso non si ottiene abbassando il rigonfiamento,
perche' il rigonfiamento cambia solo la forma del corpo; serve la casella
apposita. Il livello 1 resta "teso e aderente", il gradino oltre e' un'altra
domanda.

**Opzione "Scegli tu".** Claude assegna il livello dalla natura del prodotto:

| prodotto | livello | perche' |
|---|---|---|
| In astuccio o vaschetta rigida (multipack di merendine, blister) | Rigido 1 **e avvolge_scatola** | la sezione la detta la scatola, non il film: senza la casella il pack esce gonfio e con le pinne svasate |
| Piatto, squadrato, compatto, rigido (crackers, biscotti, tavolette) | Rigido 1-3 | il film deve adagiarsi sulla struttura e minimizzare gli ingombri |
| Irregolare, fragile, da forno (croissant, merendine, tramezzini) | Medio 4-6 | margine d'aria moderato contro lo schiacciamento, senza eccedere |
| Sferico, tridimensionale, fresco o in ATM (mozzarella, insalata, formaggi freschi) | Morbido 7-10 | forma tozza e spinta interna richiedono involucro ampio e gonfio |

Con "Scegli tu" la decisione va sempre dichiarata in questo formato:

> Ho analizzato il prodotto ([Nome]) e ho impostato il rigonfiamento su
> [Rigido / Medio / Morbido] (Livello [X]/10) perche' [Motivazione].

Nessun'altra domanda durante la costruzione.

**Perche' la tipologia non si indovina:** il solutore astuccio risolve anche i
flowpack e restituisce numeri plausibili ma sbagliati. Sul croccante T2 fondente
dava 275,0 x 101,9 x 31,0 invece di 150,5 x 41,0.

**Perche' i dentini non si deducono:** il passo del dente varia enormemente.

| | bordo pinna | denti | base |
|---|---|---|---|
| T1 della barretta fresca | 55 mm | 30 | 1,83 mm |
| croccante T2 fondente | 181,5 mm | 30 | 6,05 mm |

Fattore 3,3 a parita' di conteggio. Ogni tentativo di calcolarli e' sbagliato.

## I gadget

Gli oggetti promozionali fatti in 3D - un dispenser, una tazza, una
borraccia - non sono pack e spesso non hanno un DT: arrivano foto, testo,
misure e immagini esempio che non sono il prodotto. Le tre regole qui sopra
non si applicano; le loro regole stanno in GADGET.md (le fonti e quale
comanda, cosa chiedere subito, misurare da una foto, il modello, la
verifica sul modello, i render). La categoria non e' ancora nella pagina.

## Indice

Le sezioni di ogni file, nell'ordine in cui stanno.


**`regole/pdf.md`** - leggere il PDF: una pagina, un DT, il verso, le regole comuni, la texture

- Prima delle tre regole: una pagina, un DT
  - Prima le quote, poi via tutto quello che sta fuori dal DT
  - Il foglio nel verso della grafica, prima di risolverlo
  - Il modello finito si gira: il marchio orizzontale e dritto
- Cosa chiediamo a chi prepara l'artwork
  - 1. Il disegno tecnico su un livello suo
  - 2. La colata su un livello suo
  - 3. La grafica in quadricromia, non in RGB
- Regole comuni a tutte le tipologie
  - Mezzo millimetro non puo' cambiare il pack
- Perche' un file nuovo non si costruisce: la lista
  - 1. La fustella deve CHIUDERE un rettangolo
  - 2. La grafica non deve uscire dal tracciato
  - 3. Le quote stanno FUORI dal tracciato, o su un livello loro
  - 4. Le saldature vanno disegnate per intero
  - 5. La tipologia va dichiarata quando non e' una di quelle note
  - 6. Il confronto finale lo fa l'occhio, sul modello
- La texture e' lo steso
  - La texture a parte
  - Il template PSD

**`regole/pulizia.md`** - togliere il disegno tecnico, le aree riservate, i colori

- Togliere il disegno tecnico: cinque livelli
  - Il colore non dice mai cos'e' disegno tecnico
  - Chi lo dice davvero e' il livello
  - I due livelli li fa la costruzione, oggetto per oggetto
  - La texture e' HD di serie
  - Le coperture si tolgono per nome, non per euristica
    - Le aree riservate non compaiono mai nel render
      - Quando il file le nomina
      - Quando il file NON le nomina: la scritta dice quello che il nome tace
      - Quando il nome sta solo in legenda: il campione davanti alla scritta
      - Quando il file non le scrive nemmeno: allora si guarda
      - Tolto il box, via anche la sua didascalia
      - Lo spazio colore e' stato grafico
      - I box colorati via, i bianchi restano
    - La GDA sta nel disegno tecnico, e si scarta
    - La GDA si toglie da tutte le grafiche, anche stampata
  - La tipologia non riconosciuta e' un errore, non un ripiego
  - Un file che si dichiara film prova prima il flowpack
  - Regole sempre valide
  - Cosa NON funziona, verificato sul campo
  - Il colore e lo spessore dipendono da chi legge il PDF
  - La `k` nera si rimette dalla lastra, non rendendo tutto con Ghostscript
      - Ghostscript costa 105 MB anche a vuoto, e conta QUANDO lo chiami
  - Un'immagine in sovrastampa si somma a quello che trova
  - La grafica va in quadricromia, non in RGB
- Quando la pulizia deterministica non basta
  - Cosa passare al modello, e cosa no

**`regole/verifiche.md`** - le verifiche, la lettura accanto al modello, il controllo dell'AI, la coda

- Il controllo visivo e' obbligatorio
- Le verifiche: le UV sul DT prima, il fronte sul fronte dopo
- Le verifiche che fermano il modello
- Le misure approvate: cambiato non vuol dire peggiorato
- La lettura del PDF accanto al modello
- Il controllo dell'AI prima della consegna
  - La correzione: gli inchiostri tecnici li sceglie chi li vede
  - La coda dei casi nuovi
  - Chi lavora la coda, e il parco che la protegge
  - Chi ha caricato il PDF segue il caso, e risponde

**`regole/servizio.md`** - lo Space e pdfium

- Un servizio che si sveglia non e' un servizio rotto
  - Dove la rotella NON arriva
- pdfium non si chiama da due thread
  - Due processi: i lavoratori

**`regole/flowpack.md`** - flowpack

- Flowpack
  - Prima le misure, poi il contenuto
  - La grafica sulle pinne: il film non si allunga
  - La falda dice se la soluzione e' sbagliata
  - Due chiusure, non una: pinna e sovrapposizione
    - La terza chiusura: il tubo piatto a pinna
    - Come si sceglie la chiusura
    - Il rigonfiamento di un tubo piatto
    - La cucitura si ancora alla PIEGA, non allo spigolo
    - A pari scarto il fronte lo dice la stampa
  - Le guide ravvicinate: due letture, non una scelta
  - Pieghe e guide: la piega attraversa il passo
  - I capi dello steso sono il taglio, non il centro del gruppo
  - La falda sta sopra il retro anche nelle testate
  - Della falda si vede la fascia dell'altro capo del nastro
  - Il materiale del film lo dicono i DT secondari

**`regole/pouch.md`** - pouch

- Pouch
  - Si legge dalla piega
  - Il fronte lo dice la grafica, il verso lo dice la piega
  - La forma della busta piena
  - Cosa manca

**`regole/astucci.md`** - astucci, finestre e rilievi

- Astucci
  - La griglia non tollera un intruso
  - Quando il solutore non sa, deve dirlo
  - Un astuccio puo' non chiudersi
    - Il retro e' la faccia che porta i fianchi
    - Se i fianchi li portano tutte e due, si vedono quelli stampati
    - Le falde del retro sono fasce, non facce
    - I fianchi di un astuccio aperto non si ribaltano
    - Il caso calibrato: T6 aperto
  - Un astuccio ha uno spessore
    - Lo spessore ha scoperto che il rasterizzatore dipinge e basta
  - L'apertura a strappo si incide, non si disegna
    - Si incide solo quello che ha la firma dell'apertura
    - Il solco
    - Il controllo dell'AI deve sapere cosa sono quelle righe
    - La perforazione e' l'altra firma
  - L'apertura a strappo, aperta
  - La colata si rimette con l'inchiostro del file
    - Solo dentro l'impronta del livello, e non per pignoleria
    - Quanto conta la sovrastampa non si misura ad area
    - Il file che il livello non ce l'ha: lo indica l'occhio
    - Il foglio in cassa va buttato appena qualcuno se l'e' preso
    - Il caso calibrato
    - Tre difetti che solo questa cosa poteva far vedere
    - La fila della fasciatura orizzontale puo' cominciare da un fianco
    - Il fronte curvo: cielo e fondo a D
  - La texture e' lo steso
- Finestre e rilievi
  - La pellicola delle finestre si chiede, ogni volta
  - Il rilievo dell'embossing

**`regole/vassoi.md`** - vassoi, display con plancia, display a scatola

- Vassoi espositori
  - Le testate del vassoio
  - Il contorno non e' un rettangolo, e il DT lo dice
  - Il foglio si riconosce da dove sta, non da quanto inchiostro ha
  - Una texture sola, e uno specchio solo
  - Il verso dell'avvolgimento si misura, non si indovina
  - Il cartoncino fra due righe e' quello che hanno in comune
  - Un blocco unico, senza feritoie
  - Il vassoio sagomato: il fondo fra quattro cordonature
- Display con plancia
  - Si riconosce dalla croce, non dalla grafica
  - Come si apre: lo dice il DT
  - Perche' proprio questa piega
  - I pezzi vengono dai tratti, non dall'impronta di stampa
  - La texture, sul solo riquadro della fustella
  - La plancia e' un elemento a se'
  - Le verifiche
  - Il coperchio sul retro
  - La plancia dentro il coperchio
- Il display a scatola
  - La firma in fustella
  - Come si alza: la stampa lo dice
  - Il solido
  - Il fronte e' fustellato: segue i tagli della plancia
  - Dove entra
  - Cosa manca

**`regole/ballotin.md`** - ballotin

- Ballotin
  - La fustella si legge a facce
  - Cosa si riconosce
  - Gli spigoli: la lente rientra nel pack
  - La cima: chi sta sotto lo dice il tratteggio
  - Le finestre si vedono
  - Niente feritoie
  - Cosa manca

**`regole/punta.md`** - la scatola a punta

- La scatola a punta
  - La firma in fustella
  - Il solido
  - Cosa manca

**`regole/tubo.md`** - il tubo a cono

- Il tubo a cono
  - La firma in fustella
  - Il solido
  - Il gelato
  - Cosa manca

**`regole/prisma.md`** - la scatola a prisma

- La scatola a prisma
  - La firma in fustella
  - La vista di fuori, non quella di dentro
  - Il montaggio e il verso
  - La lamina e' metallo
  - La lamina che dice solo la legenda
  - La linguetta di chiusura si incide
  - Il fondo a sormonto si ritaglia, sopra la falda

**`regole/coppe.md`** - coppe e coni gelato

- Coppe e contenitori conici
  - Lo steso
  - La vista montata: la scala dai cerchi gemelli
  - La grafica sulla coppa senza stirarla
  - Il bordo arrotolato e' bianco fuori
  - Il fronte e' il marchio, non la mezzeria
  - Il tappo
  - Senza dichiarazione la coppa si prova per ultima
- Il cono gelato col lid
  - Lo steso: un settore pieno, con l'apice sul foglio
  - La forma dal disegno 1:1
  - Quale lato sta sopra: lo dice la colla
  - La grafica sulle generatrici
  - Il risvolto accoppiato
  - Il lid
  - Il fronte senza il fondo giallo

**`regole/incarti.md`** - l'incarto a triangolo

- L'incarto a triangolo
  - Gli incarti nella pagina
  - Cosa manca

**`regole/riempimenti.md`** - riempimenti

- I riempimenti
  - Si dichiara, e i PDF si riconoscono da soli
  - Quanti: la domanda, e il vuoto vuol dire pieno
  - I due modelli, ognuno dalla sua famiglia
  - Il vano
  - Il flowpack si misura sulla sua maglia
  - Le CU: flowpack o astucci
  - Piu' alto delle pareti: sta in piedi e sporge
  - I pack sono frontali
  - Quanti ne stanno
  - Strati uguali, file su tutta la profondita'
  - Il flowpack si adatta al vano, una volta per tutti
  - Se non ci sta in nessuna posa, il flowpack si accorcia
  - Il GLB: il flowpack una volta, un nodo per pezzo
  - Il controllo dell'AI non c'e' ancora
  - Cosa manca
  - Il display e' fatto per il suo numero: la griglia piena
  - Sdraiati, stanno in piano
  - Nel display il flowpack resta quello del DT, con le pinne aperte
  - Nel riempimento il CU resta il suo modello: si schiaccia, non si allarga

**`regole/casi.md`** - i casi calibrati e le assunzioni non verificate

- Casi calibrati
- Assunzioni non verificate
