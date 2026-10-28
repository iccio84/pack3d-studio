# Regole: Togliere il disegno tecnico

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Togliere il disegno tecnico: cinque livelli

Dal certo allo stimato. I primi tre portano **l'intenzione dichiarata dal file**,
gli ultimi due la indovinano. Il livello usato va sempre riportato nel resoconto.

1. **Processing Steps ISO 19593-1** — oggetti non stampati su livelli marcati con
   metadati normalizzati, in sette gruppi: Structural, Dimensions, Braille,
   Legend, Position, White, Varnish. Lettura esatta.
2. **Livelli OCG con nome tecnico** — non e' lo standard ma i nomi sono
   espliciti: `technical-drawing`, `notes`, `check`, `Coldseal`, `White`,
   `Eyemark`, `Infopanel`, `VARNISH`, gia' separati dall'artwork.
   **Attenzione a pypdf:** `PdfWriter.append()` NON copia il catalogo, quindi le
   `/OCProperties` spariscono e i livelli diventano irraggiungibili. Serve
   `PdfWriter(clone_from=...)`. Poi si leggono le `/Properties` della pagina,
   che mappano `/MC0 /MC1 ...` agli OCG, e si scartano i blocchi `BDC`/`EMC`
   marcati `/OC` sui livelli tecnici.
3. **La scritta sull'area** — quando il DT non sta su un livello e le lastre
   si chiamano solo col numero Pantone, resta una cosa scritta: dentro ogni
   area riservata c'e' il suo nome, in bianco, come testo vero. La lastra e'
   quella che **dipinge sotto la scritta**, e sotto ogni etichetta ce n'e' una
   sola. Non e' indovinare: e' leggere. Vedi *Le aree riservate non compaiono
   mai nel render*. La **legenda** del documento — il riquadro tipo "Job
   Colors", che affianca il nome della lastra alla sua pastiglia — dice le
   stesse cose ma per **accostamento di posizione**, che e' un'assunzione di
   impaginato: usarla per strappare una lastra e' un rischio che non abbiamo
   preso. Nomi ricorrenti: Technical Drawing, Dimensions, Print Free Area,
   Best Before Area, Bar Code Area, COVERED Area, Neutral Area, Text Area,
   Eyemark, Coldseal, White, Varnish.
4. **Registro di lastre note** — scorciatoia quando non c'e' altro, e **solo
   per riconoscere, mai per strappare**. Negli artwork del cliente questi numeri
   ricorrono: Pantone 3405 C = Technical Drawing, 346 C = Dimensions,
   571 C = Print Free Area, 350 C = Best Before Area, 341 C = Bar Code Area,
   1565 C = COVERED Area. Anche `All` e' tecnica.

   **Ma ricorrono meno di quanto sembri, ed e' misurato.** Sul wafer da colazione
   il registro sbaglia due volte su due: `350 C` li' e' il **disegno tecnico**,
   `346 C` e' la **BEST BEFORE AREA**. E fidarsene per strappare costa: sul
   cartotecnico T6 aperto, strappare le lastre che il registro chiama tecniche
   porta via anche il **bollino `x6`** e il **QR code**, che sono grafica
   stampata. Un numero Pantone e' un colore, e un colore non dice mai a cosa
   serve una lastra — e' la stessa regola qui sotto, nella sua forma piu'
   netta.
5. **Euristica** su spessore (filo di capello, <= 0,8 pt). E' una stima e va
   dichiarata come tale. Sul **colore** vedi la regola qui sotto: non e' una
   stima debole, e' una stima che non si puo' fare.

### Il colore non dice mai cos'e' disegno tecnico

La maschera sceglieva anche pieni e scritte, e il criterio era la tinta:
"cromatica e non di una tinta piatta, quindi tecnica". Misurata su tutto il
parco, quella regola non ha mai tolto un solo pixel di disegno tecnico che i
tratti non togliessero gia'. Su **sei file su nove** non cambia niente. Sugli
altri tre cancella **grafica**:

    brioche STD   il logo, la tabella nutrizionale, "CON LATTE" e
                  il testo legale — il 4,4% del foglio
    T6 aperto     il bollino "x6" e l'icona del pack
    brioche       lo 0,75% del foglio, tutto grafica

Non era una soglia sbagliata, e non si aggiusta con una soglia migliore: **una
lastra tecnica usa i colori che usa anche la grafica**. Sulla brioche STD
l'unica tinta "tecnica" rimasta era `(0, 174, 239)`, cioe' **ciano di processo
al 100%** — lo stesso ciano del logo. Il registro `All` e' nero come
il testo legale; la Pantone di servizio e' la stessa del marchio. Nessuna
soglia separa due cose che hanno lo stesso colore, e la campionatura delle
tinte piatte (`tracciati.piatte`) aiuta ma non basta: prende il pieno, non le
percentuali, e sulla brioche otto tinte della grafica passavano lo stesso.

Quindi pieni e scritte **non si scelgono piu' per colore**. Restano i
**tratti**: un filo di capello e' tecnico per **geometria**, non per tinta, e
quella regola vale anche quando di livelli non ce n'e' nessuno.

### Chi lo dice davvero e' il livello

Se il file ha OCG che dicono cosa e' tecnico, si **spengono** prima di
rasterizzare (`strati.senza_tecnici`), e quel che resta del DT fuori dai
livelli si spegne oggetto per oggetto (*I due livelli li fa la costruzione*).
E' il livello 1-2 della scala qui sopra usato anche per la texture, non solo
per la diagnosi — che e' dove stava da sempre senza servire a niente.

Sulla brioche STD gli otto OCG si chiamano `background, code, cutter, layout,
legend, mat, preview, promo`: due sono tecnici e spegnendoli si toglie
l'1,61% — la fustella e il cartiglio, esattamente quelli — con il logo intero.

    brioche STD   euristica col colore   4,43% tolto, logo distrutto
                  livelli spenti         1,87% tolto, logo intero

Spegnere un livello e' una modifica di **dizionario** - l'OCG finisce in
`/OCProperties/D/OFF` - e non costa la passata di pypdf sul flusso di
contenuto, che sul wafer da colazione vale 7 secondi e 100 MB. **Attenzione**:
`PdfWriter().append()` perde `/OCProperties`, serve `PdfWriter(clone_from=...)`.

Da qui la richiesta a chi prepara il file: **il disegno tecnico su un livello
suo**, vedi *Cosa chiediamo a chi prepara l'artwork*. E' la stessa richiesta
della colata, e per la stessa ragione — quello che il file dichiara non si
deve indovinare.

Un nome di livello e' tecnico se e' un Processing Step ISO, se sta in
`techink.OCG_TECH` o se `techink.tecnica` lo riconosce — `Cutter` passa di li'.
Sul parco: brioche STD `Cutter, Legend`; T1 al mandarino `check, notes,
technical-drawing`; T1 ai cereali `Guides and Grids, check`. Gli altri sei file
livelli non ne hanno, e per loro resta la regola dei tratti.

### I due livelli li fa la costruzione, oggetto per oggetto

Il file i livelli li dichiara quando vuole: brioche STD `Cutter` e `Legend`,
T1 della barretta fresca `Fustella` e `Note`, wafer da colazione nessuno. Quello che serve alla
costruzione invece sono sempre **due livelli**, e sempre gli stessi: il
**DT/note**, da cui si misura il pack e si controllano le UV, e la
**grafica**, da cui si prende la texture. Quando il file non li ha, li fa la
costruzione (`strati.dividi`), e li fa sugli **oggetti**, non sui pixel.

Prima non era cosi', ed era la texture che l'utente descriveva **"ritagliata in
piu' punti"**. Senza livelli il disegno tecnico si toglieva DOPO la resa: una
maschera sui tratti sottili, larga il tratto piu' 1,2 pt per parte, e il pixel
valido piu' vicino a riempire. Lungo ogni cordonatura spariva un millimetro di
grafica, rifatto coi bordi:

    wafer da colazione   l'angolo del cedolino blu del marchio a gradini, e degli
                         incroci del retino delle saldature i puntini sul bianco
    T1 della merendina   il bordo alto del foglio strappato
    ogni file            una riga di grafica stirata dove il DT l'attraversava

pdfium gli oggetti li conosce uno per uno e li sa **spegnere**
(`FPDFPageObj_SetIsActive`): un oggetto spento non si rende, e sotto resta
quello che il file ci ha messo. Nel livello DT va:

- tutto quello che sta su un **livello tecnico del file**. pdfium lo dice con
  la marca `OC`, che porta il nome dell'OCG; dentro un form la marca ce l'ha
  il form, e i figli la ereditano;
- ogni **tratto a filo di capello** (<= 0,8 pt) e ogni tratto nelle **penne
  della fustella** - la stessa scelta che faceva la maschera, ma sull'oggetto.
  Di un percorso **pieno** con un contorno tecnico si spegne solo il contorno:
  il pieno e' grafica;
- i **testi fuori dall'artwork stampato** - quote delle miniature, legenda,
  cartiglio - ma solo nella vista del DT, e solo fuori: dentro l'artwork un
  testo e' grafica anche quando ha il colore di una quota;
- i **veli tecnici**: un rettangolo pieno, **semitrasparente**, con i quattro
  lati sulle linee del DT - che ricalca una cella del disegno
  (`strati._velo`, le linee da `strati.linee_dt`). Sul T1
  cheesecake le due gole da 10 mm e le fasce coperte sono velate cosi',
  bianco al 50% dentro quattro form, senza nessun livello: sul modello pinne e
  fianchi uscivano sbiaditi. Sul T1 al mandarino, stesso DT, i veli non ci sono.
  Una grafica semitrasparente - il fondino del bollino "LIMITED EDITION" dello
  stesso file - non ha i lati sulle linee del DT, e resta.

Il colore non si guarda mai, come sempre.

**Ghostscript gli oggetti spenti non li vede.** Due cose della texture le rende
lui - la lastra del nero e la banda della colata - e un tratto di fustella in
nero pieno per la lastra e' nero come la `k`: senza precauzioni tornerebbe
sulla texture proprio da li'. Percio' `nero.riporta` e la colata non
incollano niente dentro l'**impronta del DT** (`strati.impronta_dt`, la resa
del solo livello DT su fondo trasparente).

Col DT spento cade anche il **margine** dei pannelli degli astucci: il ritaglio
si ingrandiva di 4 px per parte per non portarsi sul bordo della faccia la
cordonatura dipinta, e cosi' stirava la grafica. La cordonatura non c'e' piu',
e sul bordo resta quello che ci va: la grafica che gira sullo spigolo.

Quello che si paga e' una passata sugli oggetti prima di rendere: da 0,1 a 0,3
secondi, anche sui 32.757 percorsi del wafer da colazione.

### La texture e' HD di serie

L'altra meta' di "ritagliata e sgranata" era la risoluzione. Sul piano Free di
Render la texture di un flowpack stava in **1700 px** di lato, e l'interfaccia
la qualita' alta non la chiedeva mai: i fogli grandi uscivano sotto i 100 dpi.
Il limite era la memoria, e sugli Spaces non c'e' piu'. Di serie adesso la
texture e' a **300 dpi**, con un tetto a **8192 px** di lato; `web` resta,
per chi vuole un GLB leggero, ed e' quella di prima.

    |                          | prima            | adesso            | tempo       | GLB           |
    | wafer da colazione       | 1219 x 1700  3,7 | 3897 x 5433  11,8 | 63 -> 109 s | 3,9 -> 5,3 MB |
    | brioche STD              | 1174 x 1700  4,0 | 3425 x 4960  11,8 | 16 -> 30 s  | 4,0 -> 5,9 MB |
    | T1 della barretta fresca | 1201 x 1134  7,9 | 1801 x 1700  11,8 | 11 -> 15 s  | 4,1 -> 4,3 MB |
    | T6 aperto                | fronte 1106  7,9 | fronte 1659  11,8 |  9 -> 9 s   | 0,5 -> 0,8 MB |
    | display T1x40            | 1209 x 1700      | 5846 x 8192       |  7 -> 13 s  | 1,1 -> 3,4 MB |

(px per mm dopo le dimensioni; tempi di analisi piu' costruzione, un file per
processo, su questo container.) Il picco di memoria arriva a 1,2 GB sulla brioche
STD: sugli Spaces non e' un tema.

Il tempo in piu' sta quasi tutto nelle **immagini con trasparenza** dentro la
grafica, non nei tratti: sul wafer da colazione a 100 dpi, spente le 21 immagini, la
resa passa da 11 a 2 secondi; spenti i 32.757 percorsi, da 11 a 10. E ritagliare la resa sul
solo foglio non aiuta, perche' le immagini stanno tutte dentro il foglio:
il wafer da colazione a 300 dpi fa 61 secondi pagina intera e 61 il foglio da solo.

Il tetto a 8192 e' quello che le schede video da scrivania reggono tutte. Su
un telefono con un limite piu' basso three.js la riduce da se' al caricamento:
si perde definizione su quel telefono, non il modello.

### Le coperture si tolgono per nome, non per euristica

I cinque livelli sopra sono un ordine di **certezza**, ma non tutti i livelli
sanno vedere le stesse cose, e questa e' una divisione diversa:

- una **fustella**, una **quota**, un **retino print-free** sono TRATTI:
  sottili, e l'euristica su spessore e colore li prende;
- una **vernice**, un **bianco coprente**, un **cold seal** sono PIENI grandi
  quanto la grafica. Nessuna euristica sul tratto li puo' vedere - non c'e'
  nessun tratto - e pdfium li rende **opachi**.

Sull'astuccio della ciambella la lastra si chiama `Water Based Gloss Varnish` e
copre tutto il pannello: la texture usciva rosa piena, con la grafica sotto e
invisibile. Il nome lo diceva senza ambiguita', ma nessuno lo leggeva: la
lettura per nome stava solo in `tools.classify_technical`, che e' uno strumento
per l'agente, e la costruzione deterministica strappava separazioni solo se un
caso calibrato le elencava a mano.

Adesso `artwork.senza_coperture` le strappa da sola, su ogni file, e lo dichiara
nei cartellini. **Solo le coperture**, pero', e la ragione e' misurata: strappare
per nome anche fustella e quote costa una passata di pypdf sul flusso di
contenuto, e sul wafer da colazione erano **7 secondi e 100 MB di picco in piu'** - 584
contro 484, cioe' oltre il tetto dei 512 - per togliere tratti che la maschera
del disegno tecnico prendeva gia'. Il giorno che un pack mostra una fustella
che l'euristica non prende, si allarga con quello in mano. (Oggi quei tratti
li spegne il livello DT in pdfium, oggetto per oggetto, e la passata di pypdf
resta per i soli pieni: vedi *I due livelli li fa la costruzione*.)

**Con la pulizia fuori dal DT la passata c'e' comunque**, e il costo non e'
piu' una ragione: per nome si tolgono adesso anche le lastre che DISEGNANO il
DT (`techink.disegno`: technical, dieline, cutter, crease, fustella,
dimension, legend...). Il caso che l'ha chiesto: sul pane ripieno T2 la
lastra `Technical Drawing light` dipinge anche una banda piena di 2 mm sul
fianco, contornata da due tratti del DT. I tratti li spegneva il livello DT, la
banda no - e' un pieno - e sul modello era una riga verde da un capo
all'altro.

Sul parco cambia un file solo, il T2 di cialde, e in meglio: dalla tacca di
fotocentratura sparisce il contorno verde, della stessa lastra. Gli altri
dodici escono identici al byte.

Non tutte le tecniche, pero', e anche questo e' misurato. Con la lista intera
di `techink.tecnica` sul parco cambiavano cinque texture: le **tinte imparate**
da un file (`LASTRE_NOTE`: il Pantone 346 e' le quote su un file e grafica
su un altro) cancellavano il 9% di un pannello del T6 aperto e mezzo punto del
T1 al mandarino, e il registro `All`, che sulla brioche STD dipinge anche testo, il
2% della sua texture. Restano fuori anche la tacca di fotocentratura, che si
stampa, e le sigle corte.

Attenzione a non leggerlo come "strappare costa memoria": dipende da cosa si
strappa. Togliere **tratti** aggiunge una passata e non alleggerisce il
rendering, quindi il picco sale. Togliere **pieni** toglie anche il lavoro di
dipingerli: le tre aree riservate del wafer da colazione portano il picco da 613 a 473
MB. La divisione tratti/pieni di sopra decide tutte e due le cose.

Due precauzioni:

- **il confronto sul nome e' per sottostringa, non per nome intero.** I nomi
  veri sono composti: l'insieme conteneva `varnish`, `gloss varnish` e
  `waterbased varnish` - tre voci, e nessuna delle tre e' "Water Based Gloss
  Varnish". Restano per nome intero solo le sigle dove la sottostringa
  farebbe danni: `white` come sottostringa prenderebbe "White Chocolate", che
  e' un colore dell'artwork;
- **si toglie solo per la texture, mai per l'analisi.** Il disegno tecnico e'
  quello che fa misurare il pack: togliendolo prima, non si misura piu' niente.

E si toglie in **un posto solo**. Finche' questo passaggio e il verso della
grafica sono stati dentro `server.py`, li applicava solo il server: la riga di
comando costruiva lo stesso astuccio senza toglierci niente, e l'astuccio della ciambella
usciva una scatola rosa piena, con la vernice ancora sopra. Non e' roba di
HTTP, e' roba di artwork: sta in `pack3d/artwork.py`, e chi vuole le texture di
un astuccio chiama `texture_astuccio`, che fa i tre passaggi nell'ordine giusto
e restituisce gia' scritti gli avvisi da mostrare.

#### Le aree riservate non compaiono mai nel render

La **GDA** non e' sola. `COVERED AREA`, `TEXT AREA`, `BEST BEFORE AREA`, `BAR
CODE AREA`, `PRINT FREE AREA`, `NEUTRAL AREA`, `PIN CODE AREA` sono la stessa
cosa fatta per un'altra ragione: **posto tenuto**, non grafica. Nessuna di
loro si stampa, e **nessuna deve comparire nel render finale**: i box area si
tolgono **sempre**, come la GDA, e su **tutti i modelli 3D** - flowpack,
astucci e vassoi, e anche i casi tarati a mano (`senza_coperture` con
`fisse`). E' la regola come l'ha detta l'utente dopo il pane ripieno T2:
"i box area vanno sempre tolti come la gda, anche quelli verdi".

**Per nome e' un box area ogni lastra che si chiama area** (`techink.area`,
la parola `area` intera), non solo le frasi di un elenco: sul pane ripieno c'e'
`PIN CODE Area`, che nell'elenco non c'era e restava. Nessun inchiostro si
chiama cosi'. L'unica eccezione e' la **promo**: l'`AREA PROMO` della legenda
della brioche (file 1765...) e' tutta la fascia gialla con le scritte del
concorso e del premio in palio, cioe' la
grafica della promo, che si stampa.

Stanno fra le **coperture** e non fra i soli nomi tecnici, per la ragione che
vale per la GDA: sono PIENI grandi quanto la casella, non tratti, e l'euristica
su spessore e colore un pieno non lo vede. Finche' sono state solo "nomi
tecnici", la texture del **wafer da colazione** usciva con due fasce `TEXT AREA`,
una `COVERED AREA` e un riquadro `BEST BEFORE AREA` stampati sul pack, a
lettere bianche.

##### Quando il file le nomina

Se la lastra si chiama per quello che e' — `Covered Area`, `GDA Area`, `Best
Before Area` — si strappa per nome, e il conto lo paga solo il file che ce
l'ha. Se sta su un livello con quel nome, si spegne il livello e non si paga
niente. Questa e' la strada buona, ed e' meta' di *Cosa chiediamo a chi prepara
l'artwork*.

##### Quando il file NON le nomina: la scritta dice quello che il nome tace

Il wafer da colazione non nomina niente. Nessun livello, e le lastre si chiamano
`PANTONE 1595 C`, `PANTONE 1565 C`, `PANTONE 346 C`: numeri di colore, non nomi
di mestiere.

**Il registro `LASTRE_NOTE` non serve, e mente.** E' costruito su altri file, e
su questo sbaglia due volte su due: dice `PANTONE 350 C = Best Before Area` e
li' quella lastra e' il **disegno tecnico**; dice `PANTONE 346 C = Dimensions`
e li' e' la **BEST BEFORE AREA**. E' la lezione di sempre, nella sua forma piu'
netta: un numero Pantone e' un colore, e **un colore non dice mai a cosa serve
una lastra**.

Misurato, per togliersi la tentazione: strappare tutte le separazioni che il
registro chiama tecniche sul cartotecnico T6 aperto fa sparire le aree
riservate **e anche il bollino `x6` e il QR code**. Grafica stampata, tolta da
un registro che parlava di un altro file.

Quello che il file dice davvero **e' scritto sopra l'area**: dentro ogni
riquadro c'e' il suo nome, in bianco, come testo vero ed estraibile. Da li' si
parte, e la lastra si trova guardando **chi dipinge sotto la scritta** — una
passata `tiffsep` di Ghostscript a bassa risoluzione da' una mappa d'inchiostro
per separazione, e sotto ogni etichetta c'e' una lastra sola:

    TEXT AREA (x2)     ->  PANTONE 1595 C     inchiostro 93%
    COVERED AREA       ->  PANTONE 1565 C     inchiostro 89%
    BEST BEFORE AREA   ->  PANTONE 346 C      inchiostro 89%

Niente colore, niente geometria, niente registro: **l'etichetta e la lastra
sotto**. La grafica del wafer da colazione resta intera — logo, wordmark, wafer, tazza,
bollino `x10`, `100% LATTE ITALIANO` — e le tre aree spariscono.

Sul parco lo stesso passaggio ripulisce anche l'astuccio della **brioche latte
e cacao**, che aveva una fascia `COVERED AREA` sul fianco sinistro e un
riquadro `BEST BEFORE AREA` a destra: via quelle due, e restano interi il logo
del marchio, il bollino `x10`, i pannelli promo con i QR code e il
`100% LATTE ITALIANO`. Sei GLB su otto non cambiano di un byte, e i due che
cambiano sono esattamente questi.

**Il prefiltro.** Prima di estrarre il testo con pypdf si guarda se nel testo
della pagina compare la parola `area`. Il testo lo legge **pdfium**, che
decodifica i font e scende nei form: costa da 0,01 a 0,15 secondi, contro i
2,9 che l'estrazione di pypdf costa su ogni brioche STD. Prima si cercava
`AREA` nei byte grezzi del flusso della pagina, e un font a glifi codificati
la nascondeva: sul **T1 farcito** la legenda dice "Covered Area",
"Print Free Area", "Best Before Area", "Bar Code Area" e "Pin code area", il
prefiltro diceva di no, e i cinque box - la fascia verde acqua, quella
arancione, i due verdi e il quadratino rosa - restavano stampati sul pack.
Stessa cosa sull'astuccio **T6 aperto**, che ha "Neutral Area" e "Best Before
Area" in legenda. La parola si cerca anche dentro altre, perche' pdfium su una
didascalia girata e spezzata restituisce "BESAREA": un falso si' costa una
lettura, un falso no costa un box stampato.

Adesso il T1 farcito impara dalla legenda Covered = 1565 C, Print Free = 571 C,
Best Before = 346 C, Bar Code = 3405 C, Pin code = 7436 C, e il T6 aperto
Neutral = 571 C - la stessa lastra che l'agente toglieva a occhio, vedi
sotto - e Best Before = 346 C. Sul T1 farcito spariscono tutti i box, e logo,
prodotto, "FATTA CON LATTE FRESCO" e l'icona del riciclo restano interi; sul
T6 aperto sparisce il box verde nella fascia rossa del retro, e il fronte -
logo, bollino `x6`, QR code - non cambia di un pixel.

**Su ogni file, anche con i livelli tecnici.** All'inizio la ricerca partiva
solo sui file senza livelli tecnici, per risparmiare la lettura del testo. Sul
T1 ai cereali e' stato un errore: i suoi livelli tecnici sono `Check` e
`Guides and grids`, i box non ci stanno, e i due box verdi `Best Before Area`
e `Bar Code Area` - PANTONE 346 C e 3405 C - restavano stampati con le loro
scritte. Adesso la ricerca parte sempre; il prefiltro sulla parola `AREA` la
tiene a zero sui file che non la scrivono, e sul parco costa 1,3-2,2 secondi
ai quattro che la scrivono e hanno i livelli.

**Si guarda al centro della scritta, non dove comincia.** "Bar Code Area" sul
T1 ai cereali e' girata e comincia a un millimetro dal bordo del suo box: i
2 mm attorno all'inizio erano pieni al 57%, sotto la soglia del 60, e il box
restava. La posizione, la direzione e il corpo si leggono dalle due matrici
del testo (`cm` e `tm`, non la sola `tm`), la lunghezza si stima a 0,55 corpi
per carattere: basta a trovare il centro, e li' il box e' pieno all'81%.

**E si controlla pypdf.** A volte ripete una scritta con la posizione di
un'altra: sul T2 di cialde "Best Before Area" torna una seconda volta sulla
banda rossa, dove non c'e' scritto niente, e sotto c'era l'**arancio del marchio**
- la grafica. Una didascalia vale solo se pdfium vede davvero un oggetto testo
dove pypdf dice che comincia (`techink._oggetti`).

**Il costo, detto per intero.** Sul parco i file senza etichette restano al
loro tempo — brioche STD 1,9 -> 2,0 s, crt_nuovo 2,4 -> 2,4, vernice 4,1 ->
3,8 — mentre quelli che le hanno pagano: **brioche latte e cacao 0,9 -> 4,5
s**, **wafer da colazione 2,1 -> 19,7 s**. Quei diciotto secondi sono quasi tutti lo
strappo delle tre lastre, che su un flusso da 3,6 MB e' la parte cara; la
lettura del testo ne vale 3,8 e la passata `tiffsep` uno.

E' tanto, e su un piano Free a 0,1 CPU si sente. In cambio il pack non esce
con `TEXT AREA` scritto sopra, e la memoria **scende**: sul solo wafer da colazione il
picco va da **613 a 473 MB**, cioe' da sopra a sotto il tetto dei 512 —
togliere tre lastre piene dal flusso costa meno di quanto costi renderle.

##### Quando il nome sta solo in legenda: il campione davanti alla scritta

Sul T1 ai cereali la fascia arancione a tratteggio sotto la pinna non ha
nessuna scritta sopra. Il suo nome sta solo in legenda: "COVERED Area", e
davanti un quadrato di 14 punti di PANTONE 1565 C. Leggere la legenda in
generale e' un accostamento di posizione, e sbagliare accostamento vuol dire
strappare la lastra della grafica; ma il **campione** di una voce e' una cosa
stretta, e si legge solo quella (`techink._campione`):

- un percorso **pieno**, grande da 0,8 a 10 corpi della scritta per lato;
- **davanti** alla scritta, sulla sua riga - copre almeno un terzo del corpo
  del testo - e staccato al piu' di 4 corpi: il piu' vicino;
- e la lastra deve riempirlo al **60%**, come sotto una didascalia.

Si guarda il campione solo se sotto la scritta non c'e' una lastra piena, e
solo per le scritte che dicono un box area. Sul parco da' quello che l'occhio
da': il T1 ai cereali `COVERED Area` = 1565 C, `Best Before Area` = 346 C, `Bar Code
Area` = 3405 C; wafer da colazione e brioche `TEXT AREA` = 1595 C, `COVERED AREA` =
1565 C; T1 farcito e T6 aperto come sopra, nel prefiltro. Le legende del
pane ripieno e del T2 di cialde danno le lastre che gia' si chiamano area. Una legenda col campione dietro la scritta, o lontano, non da'
niente: si perde un'occasione, non si strappa la lastra sbagliata.

##### Quando il file non le scrive nemmeno: allora si guarda

Se il nome dell'area non si legge ne' sopra il riquadro ne' in un campione di
legenda, non c'e' piu' niente da leggere. Era il caso del croccante T2 fondente
e del cartotecnico T6 aperto prima che si leggesse il campione: il T6 aperto
adesso lo prende (vedi *Il prefiltro*), il croccante T2 fondente non e' nel parco di
prova e non e' verificato.
A **occhio** pero' sono ovvie: un rettangolo pieno, verde o arancione,
appoggiato sulle falde.

Quindi si guarda, ed e' lavoro dell'agente — *il modello dice DOVE, il codice
fa COSA*, vedi *Cosa passare al modello, e cosa no*. Lo strumento e'
`tools.area_riservata`: prende un **riquadro in mm** indicato a occhio, cerca
quale lastra ci mette l'inchiostro pieno, e la toglie per nome. Il bordo esatto
non lo decide l'agente, lo decide la lastra: sbagliare il riquadro di **3 mm**
in dentro o in fuori da lo stesso risultato, misurato sul T6 aperto.

**La conferma e' l'immagine, e non puo' essere un numero.** Puntare la fascia
rossa del T6 aperto invece della falda verde da' `Pantone Warm Red C` pieno al
100% e al 3,29% del foglio; la vera area riservata, `Pantone 571 C`, da' pieno
al 100% e 3,08%. Indistinguibili. E sul wafer da colazione la fascia `TEXT AREA` copre il
6,5% del foglio mentre l'arancio del marchio, che e' grafica, il 7,9%: **nessuna
soglia separa le due cose**. Per questo lo strumento restituisce il foglio in
grigio con in **rosso tutto quello che quella lastra dipinge**, e l'istruzione
e' guardare: se il rosso tocca un logo, una foto o il fondo del pack, la
proposta si lascia cadere. Il rosso su fondo a colori non si leggeva — il
T6 aperto ha mezza grafica rossa — quindi la base va in grigio e tutto cio' che
resta colorato e' la lastra.

Le lastre confermate viaggiano in `parametri_costruzione.aree_riservate` e la
costruzione le strappa insieme alle altre, una passata sola: `aree_da_agente`
in `server.py`, come `livello_da_agente` e gli altri. Senza quell'elenco il
file resta com'era, che e' il comportamento di sempre.

Sul T6 aperto sparisce il 9,7% della texture — i blocchi sulle falde e il
riquadro nella fascia rossa — e restano interi il logo, i due bollini `x6`, il
`FATTO CON LATTE FRESCO`, la bustina e il QR code. Che e' esattamente quello
che il registro di lastre note portava via.

##### Tolto il box, via anche la sua didascalia

Tolta la lastra resta la **scritta**, quando non e' in bianco. Sul T2
di cialde `Best Before Area` e `POSITIONING AREA FOR EAN CODE (if requested)`
sono in marrone scuro, CMYK 0/81/100/77: via i riquadri verdi, le due scritte
restavano stampate sui fianchi del pack. Sul pane ripieno T2, tolti i box
arancioni `TEXT Area`, sul retro restavano "INGREDIENTS", "F8 LEGAL TEXT",
"Text Area TABELLA NUTRIZIONALE", "WEIGHT", "COMMERCIAL DESCRIPTION" e, sul
fronte, "TEXT AREA" e "GDA".

Mentre `strip_separations` toglie un **box area** - uno qualunque: prima erano
solo quelli dei dati variabili, scadenza, lotto e codice a barre - ne misura
il riquadro, seguendo la matrice e i form, e lo passa a chi rende la texture
(`strati.segna_riservate`), con un segno se l'area e' **coperta**. Dentro un
riquadro tolto `strati.dividi` manda nel livello DT:

- il testo che dice il nome di un'area riservata (`techink.NOME_RISERVATA`,
  che conosce anche "EAN CODE" da solo): lo dice quello che c'e' scritto, non
  il colore;
- e cio' che ha il **colore di una di quelle scritte**, perche' non tutte le
  didascalie dicono "area": "INGREDIENTS" e "WEIGHT" sono solo il nome della
  casella, e quella del codice a barre del T2 di cialde e' in curve, 38
  tracciati. Una scritta, o un **segno** - un tracciato che copre meno di un
  quarto del box (`QUOTA_SEGNO`): una lettera in curve, il pallino di un
  richiamo - tutto dentro il riquadro e di quel colore. Un tracciato piu'
  grande e' un fondo, e resta: sulla brioche (file 1765...) le didascalie
  sono bianche, e dentro la Best Before Area c'e' il riquadro bianco dove si
  stampera' la data. Un codice a barre vero, nero, resta dov'e' se la
  didascalia e' di un'altra tinta; e senza una didascalia scritta non si
  impara nessun colore e non si toglie niente.

L'area **coperta** e' l'eccezione: e' la fascia che la pinna nasconde, e sotto
la grafica continua - sul T2 di cialde la cialda e la banda rossa. Si toglie
come le altre, ma dentro si spegne solo il testo che dice il suo nome, e il
colore si impara solo dai box **vuoti per definizione** (`techink.vuota`):
il posto di un testo, di un codice, di una data, o dove non si stampa - TEXT,
GDA, BEST BEFORE, BAR CODE, EAN, PIN CODE, LOT, PRINT FREE, NEUTRAL. Ogni
altra area, anche una che non si conosce - una `Emboss Area`, una `Varnish
Free Area` - si tratta come la coperta: puo' avere grafica sotto.

Sul pane ripieno vanno nel livello DT 15 oggetti: le dodici scritte rosso bruno,
"BEST BEFORE AREA", "EAN CODE" e il pallino nero orfano, che ha il colore di
quelle due. Sul T1 ai cereali 2, "Best Before Area" e "Bar Code Area"; sul
T2 di cialde restano le 39 di prima. Solo dentro i riquadri **tolti**: la
didascalia di un box che nessuno ha riconosciuto resta con lui, perche' un
riquadro senza nome sembrerebbe grafica.

##### Lo spazio colore e' stato grafico

`strip_separations` riconosceva la lastra da togliere solo dall'operatore
`cs`. Ma lo spazio colore lo cambiano anche `g`, `rg` e `k` - che dipingono in
grigio, RGB e quadricromia - e lo rimette `Q` a com'era al `q`. Dopo il
riempimento di un'area riservata tutto quello che veniva in quadricromia con
`k` risultava ancora di quella lastra, e veniva tolto: **106 riempimenti su 112**
sul T2 di cialde, 41 su 51 sul wafer da colazione, 5 su 7 sulla vernice dell'astuccio
della ciambella. Per fortuna tutti fuori dal DT - il fondo del cartiglio, le pastiglie
della legenda - e infatti sul parco nessuna texture cambia; ma su un file con
la grafica dopo l'area riservata sarebbe sparita la grafica. Adesso lo stato
si segue come lo segue il PDF.

##### I box colorati via, i bianchi restano

"Vanno eliminati dalle grafiche tutti i box colorati - verde, arancio - e
lasciati quelli bianchi": e' la regola come l'ha detta l'utente col
T1 cold seal (file 1579...), che ha il box verde `Best Before Area` in
mezzo al fronte.

I segnaposto hanno colori vivi apposta, per farsi vedere: sul pane ripieno
`Best Before Area` e `Bar Code Area` sono verdi, `TEXT Area` e `COVERED Area`
arancio, `PIN CODE Area` rosa; sul T1 cold seal il Best Before e' PANTONE 346 C,
verde, e la legenda lo dice. Tutti questi si tolgono, per le strade di sopra.

Un box **bianco** invece non e' un segnaposto: e' il posto stampato in bianco
dove la macchina scrivera' data e lotto - il Best Before del T1 della barretta fresca,
46 x 17 col data matrix, o i riquadri del croccante T2 fondente - e si stampa.
Resta anche quando la sua lastra si chiama area: prima di strapparla si guarda
di che colore la dipinge il file, cioe' il colore a tinta piena dello spazio
alternativo della Separation (`techink.lastre_bianche`: Lab con L* da 94 in su
e a*, b* entro 6, o inchiostro al 4% al piu'). Se e' bianca resta, e il build
lo dice: "box bianchi lasciati". Provato su un PDF fatto apposta, un box verde
e uno bianco sullo stesso fondo rosso: il verde sparisce e sotto torna il
rosso, il bianco resta. Sul parco nessuna area riservata e' bianca, e nessun
modello cambia.

Non sono box i pannelli colorati della grafica: il riquadro giallo con le
frecce del pane ripieno e' l'istruzione di apertura, il blocco giallo sul retro del
T1 della barretta fresca e' la PANTONE 108 su cui va il testo legale. Si stampano e
restano. Un box si toglie perche' il file dice che e' un'area riservata - per
nome, per didascalia, per legenda, per livello - o perche' l'agente l'ha
visto: mai per il colore.

#### La GDA sta nel disegno tecnico, e si scarta

La **GDA** — il riquadro che tiene il posto alla dichiarazione nutrizionale
con le sue caselle — appartiene al disegno tecnico: e' il tecnico che ne
riserva il posto, non il grafico che la disegna. Nel livello della grafica
**non va mai messa**, e quando ci finisce comunque, e capita, va **scartata**
come qualunque altra arte tecnica. **Nel render finale non deve comparire**:
e' la regola, e vale prima di ogni altra considerazione.

Da non confondere con la **tabella nutrizionale stampata**, che e' grafica, si
stampa e resta. La GDA e' il posto tenuto, non la cosa. Per tutta la sua
famiglia vedi *Le aree riservate non compaiono mai nel render*.

Sta fra le **coperture** e non fra i soli nomi tecnici, ed e' la stessa
distinzione di sopra: un riquadro GDA e' un PIENO grande come la casella, non
un tratto, quindi l'euristica su spessore e colore non lo vede e sul modello
resterebbe stampato. Toglierlo per nome e' l'unico modo, e il costo della
passata lo paga solo il file che la GDA ce l'ha davvero. Come `white`, `gda` si
confronta per **nome intero**: intero non e' il nome di nessun inchiostro,
mentre come sottostringa prenderebbe parole qualunque.

#### La GDA si toglie da tutte le grafiche, anche stampata

"Togliere anche la GDA da tutte le grafiche": non solo il posto tenuto, ma
anche le **icone stampate** delle Assunzioni di Riferimento - "Energia 476 kJ
114 kcal 6%" - che cambiano da un paese all'altro e sul modello non vanno. Sull'astuccio
della ciambella e' l'icona dell'energia sul fianco, sulla brioche il pannello
bianco con le cinque icone sul retro, sul pane ripieno l'icona dentro una
nota del grafico, fuori dal DT.

Non ha una lastra ne' un livello: sono tracciati e scritte sciolti nella
grafica, in quadricromia. Si riconosce dal **testo** (`techink.zone_gda`): da
ogni `kcal` si cresce sulle scritte vicine, meno di 7 mm fra l'una e l'altra,
ed e' GDA il gruppo che ha anche kJ e una percentuale e sta in 90 mm. Sulla
brioche le etichette delle icone - ENERGIA, GRASSI - sono vettorializzate, e fra
il titolo "Ciascuna porzione (27g) contiene:" e i valori restano 6 mm senza
testo: a 5 il titolo restava fuori.

**La tabella nutrizionale resta**: e' grafica e si stampa. Si riconosce da
quello che le icone non hanno mai - le colonne in grammi, `(g)`, e le righe di
proteine e carboidrati. Sull'astuccio della ciambella il gruppo del retro, "(kJ / kcal)
(g) (g) (g)", resta intero.

Si toglie quello che sta nella zona - il gruppo allargato di 4 mm, il bordo
dell'icona - e il pannello su cui le scritte stanno, anche se sborda dal
margine, purche' non sia piu' grande di due volte la zona: il fondo bianco
arrotondato della brioche si', il fondo rosso del retro no (`techink.dentro_gda`).
Per le scritte conta dove comincia la riga, non il riquadro che serve al DT,
che a ogni carattere da' la larghezza del glifo piu' largo: con quello le
scritte uscivano dalla zona e restavano stampate senza piu' il pannello sotto.
Sulla brioche vanno via 101 oggetti, sull'astuccio della ciambella 14, e sotto torna il fondo,
rosso e marrone.

Una GDA vettorializzata, senza testo vivo, non si legge e non si tocca: li' la
puo' vedere solo l'agente, e lo dice.

### La tipologia non riconosciuta e' un errore, non un ripiego

`kind` si dichiara e non si indovina, e c'era gia' la nota sul sinonimo
mancante: il viewer glamlab manda `cartotecnico` e senza sinonimo ogni astuccio
finiva dal solutore flowpack. Lo stesso difetto sta all'altro capo: un valore
qualsiasi non riconosciuto - `auto`, per esempio - non entrava in nessun ramo e
cadeva **in silenzio** su quello flowpack. Oggi risponde 400 e dice cosa
dichiarare.

### Un file che si dichiara film prova prima il flowpack

Senza dichiarazione l'analisi prova il vassoio, poi l'astuccio, poi il
flowpack. Ma il solutore astuccio risolve anche certi film: sul T1
cold seal la griglia 1 | 15 | 83 | 15 | 1 per 15 | 85 | 15 gli dava un astuccio
vwrap 52,5 x 51,2 x 9,7, e il flowpack non veniva mai provato. Il file pero' lo
dice da se': il cartiglio Artworkr del cliente scrive "WRAPPING/FILM" nella
descrizione, e il disegno di un film ha FASCIA e PASSO. Su tutti i file che
abbiamo, WRAPPING lo porta ogni flowpack e nessun astuccio.

Allora, se il testo lo dice, il flowpack si prova per primo, e vince solo se
l'analisi automatica si risolve davvero, senza ripiegare sul solutore vecchio
(`server._dice_film`). Se non si risolve, si va avanti come sempre.

### Regole sempre valide

- **Neutral Area** sempre a bianco.
- **Eyemark** sempre eliminati: rettangoli neri pieni sui bordi del giro, non
  nelle pinne di saldatura. Sono i riferimenti per la fotocellula.
- **Aree riservate alle note legali** sempre eliminate: non fanno parte della
  grafica da mappare.
- **Fondo esteso fino al bordo** nelle pinne, a tinta unita nel colore di fondo
  campionato dal corpo.

### Cosa NON funziona, verificato sul campo

Ogni criterio **indiretto** confonde grafica e tecnica, perche' sul piano del
disegno sono indistinguibili e differiscono solo per intenzione:

- **tinta dichiarata nel PDF**: un fondo rosso pieno e un'area riservata bianca
  risultano entrambi `1.0`, indistinguibili;
- **forma geometrica** (es. "rettangolo a tinta piatta"): i fondi di stampa sono
  identici alle aree tecniche. Applicandolo e' sparita la "k" del marchio e il
  rosso del pack;
- **colore renderizzato**: distingue rosso da bianco su quattro rettangoli noti,
  ma su tutta la pagina trova 15 forme bianche di cui la maggior parte e'
  grafica (bicchiere del latte, schizzata, riflessi);
- **spessore del tratto**: la soglia 0,8 pt copre i flowpack ma non i file dove
  il filetto tecnico e' piu' spesso.

Due divieti operativi:

- **non colorare di bianco per neutralizzare** una separazione: un tratto
  tecnico sopra la grafica lascia una riga bianca opaca. Vanno eliminate le
  operazioni di disegno, anche dentro i **Form XObject**;
- **non ricostruire aree ampie** col pixel valido piu' vicino: funziona su
  tratti sottili e retini, su aree grandi spalma la grafica. Applicato al 23%
  di un'immagine ha distrutto logo e prodotto. Se restano buchi veri, mostrarli.

### Il colore e lo spessore dipendono da chi legge il PDF

Cambiando lettore cambia quello che si vede, e due differenze sono costate
grafica vera.

**Le tinte piatte.** pdfminer, e quindi pdfplumber, di una separazione da' solo
il valore di inchiostro: uno scalare, `1.0`. Uno scalare non e' mai "un colore
con tinta", percio' le Pantone restavano fuori dalla tavolozza tecnica per una
proprieta' della rappresentazione, non per una scelta. pdfium le risolve fino
all'RGB, e da quel momento la Pantone della fustella e la Pantone del logo sono
lo stesso colore: sulla brioche STD la maschera ha cancellato le lettere di
"kInder", disegnate in PANTONE 361 U come il tracciato `/Cutter`, insieme a
2.327 altre forme.

Rifare i conti a mano non e' praticabile — in questi artwork ci sono funzioni di
tipo 2 e di tipo 4 e alternative ICC, Lab e CMYK. Si fa invece dipingere la
campionatura a pdfium: una paginetta con un quadretto per separazione a
inchiostro pieno, resa con lo stesso motore che rende l'artwork, e quegli RGB si
escludono dalla tavolozza (`tracciati.piatte`, 0,01-0,04 s). Con
l'esclusione i riempimenti mascherati tornano **esattamente** quelli di prima su
cinque pack su sei, e sul sesto differiscono di 11 pixel.

**Lo spessore del tratto.** pdfminer non legge il `/LW` di un ExtGState e lascia
lo spessore a zero, cioe' a filo di capello, cioe' tecnico. Sulla brioche STD un
rettangolo nero da 1 pt attorno all'area di stampa — che per giunta non viene
nemmeno stampato — faceva togliere due bande verticali di grafica lunghe quanto
il pack. pdfium lo spessore lo legge giusto, e su uno `0 w` vero risponde 0,0
come deve: verificato con un PDF costruito apposta con tratti a 0, 0,5, 1 e 2 pt.

**Come si verifica un cambio di maschera.** Non basta il PSNR sulla texture: le
differenze sono poche e localizzate, e una media le nasconde. Si confrontano le
due maschere come array booleani, separando i tre livelli (tratti, pieni,
scritte), si contano i pixel `solo-vecchia` e `solo-nuova`, e si **guardano** i
gruppi piu' grandi ritagliati sulla pagina. E' cosi' che si e' visto che tutto
quello che la maschera nuova non copre piu' era grafica o roba invisibile.

**Metodo:** una modifica alla volta, con verifica in mezzo. Cambiandone due
insieme si perde il risultato buono gia' raggiunto senza capire quale delle due
ha rotto cosa.

### La `k` nera si rimette dalla lastra, non rendendo tutto con Ghostscript

Il marchio e' la `k` nera e le altre lettere arancio, e sulla brioche STD la `k`
usciva azzurra. Non e' un errore del file: nelle sue separazioni quella `k` e'
nero al 100%, ma **nero in sovrastampa** sopra l'azzurro, e pdfium la
sovrastampa la ignora.

**La strada larga non funziona, ed e' misurato.** Rendere tutto il foglio con
Ghostscript e `-sOverprint=simulate` la `k` la fa nera, ma sul **T1 al
mandarino cancella il marchio e la scritta del gusto, e fa
azzurra la fascia rossa**: quel file ha solo tinte piatte e gs le compone
male. Il 16% della pagina cambia, e cambia in peggio. Niente interruttore
globale, quindi.

**La strada che funziona e' locale, e non indovina niente: la lastra del nero
dice dov'e' nero.** Dove la lastra e' piena e il render mette invece un colore
chiaro e saturo, il render ha torto, e si riporta il tono della lastra. Non si
inventa inchiostro: si mette quello che il file dichiara, e solo li'.

    brioche STD              nero pieno su 18.839 px, il render ne tradisce il 6,8%
    astuccio della brioche                                                   2,3%
    wafer da colazione                                                       0,8%
    T6 aperto                                                                0,7%
    T1 al mandarino                                                          0,0%

Sulla brioche STD la zona tradita piu' grande e' proprio la `k`: 3.764 px su
4.938. Il difetto e' quello, non un'inezia sparsa.

**E l'orlo.** Il pieno si riporta dove la lastra supera l'85%, e l'orlo della
lettera - dove la lastra sfuma - restava com'era: il nero sfumato con
l'azzurro dipinto sopra, pixel scuri color petrolio, (30, 66, 71). A 1700 px
non si vedeva; in HD attorno alla `k` c'era un filo petrolio. Adesso si
riporta il tono della lastra anche li', a due pixel dal pieno tradito, dove la
lastra ha almeno il 10% e il pixel e' tinto: sulla brioche STD i pixel petrolio
attorno alla `k` passano da 218 a 0.

Ma solo attorno ai traditi **pieni**, quelli che un'erosione di due pixel non
cancella: le lettere. La lastra arriva da 144 dpi ingrandita, sfuma oltre ogni
lettera, e sul bordo di un testo nero su azzurro da' traditi a strisce larghe
un pixel. Allargando l'orlo anche li' - la prima versione lo faceva - si
toccavano 4.499 pixel invece di 665, e i bordi del testo della tabella
nutrizionale uscivano grigi invece che neri sfumati sull'azzurro, che e' il
loro colore giusto. Misurato sulla maschera, non sulla texture: il JPEG
ricodifica il blocco 8 x 8 appena un pixel cambia, e contare i pixel diversi
fra due texture conta anche quello.

**La soglia e' il cinque per cento**, e il motivo e' l'antialiasing: il
rasterizzatore sfuma il bordo della lettera e quei pixel di frangia risultano
"traditi" senza che ci sia niente da riparare. Sotto il cinque non c'e'
difetto — sul wafer da colazione la riparazione muoverebbe 18 pixel, e sul file
159013 il GLB resta identico dopo quasi sei secondi di passata.

**E la quota si conta sull'interno del pieno, sul solo DT.** Col bordo dentro
la quota dipendeva da quanta altra roba nera c'era sulla tavola: le scritte
nere della legenda e del cartiglio, che il render fa nere, la tenevano bassa.
Tolte le note fuori dal DT (vedi *Prima le quote, poi via tutto quello che sta
fuori dal DT*) sulla brioche T10 il 3,2% e' diventato 13,5%, la correzione e'
partita, e sui bordi delle scritte nere sul giallo ha messo pixel neri a
scalini: la lastra, presa a 144 dpi e ingrandita, sborda di un pixel. Il
difetto vero, la `k` azzurra, e' tradito anche DENTRO la lettera; il bordo
no. Contata un pixel dentro dal bordo (`nero._traditi` con `interno`):

    brioche STD   10,2% sul foglio intero, 15,9% sul DT: si ripara
    brioche T10    0,1% e 0,7%: niente da riparare, GLB identico
    wafer T1      60,9%: le linee del DT, nere piene, che la riparazione
                  poi esclude col livello DT - GLB identico
    tutti gli altri   sotto l'1%

La soglia resta il cinque per cento, e adesso sta larga in mezzo.

**Niente prefiltro sul flag di sovrastampa**, e non per dimenticanza: tutti e
otto i file del parco la sovrastampa la dichiarano. Guardare `/OP` non scarta
nessuno. Il costo e' quindi la passata spia a 36 dpi su ogni build, da mezzo
secondo a uno e tre, piu' la passata a 144 dpi solo sopra soglia.

##### Ghostscript costa 105 MB anche a vuoto, e conta QUANDO lo chiami

Questa riparazione, appena messa, ha fatto morire il build del T6
aperto sul piano Free: `Failed to fetch` nel browser, che e' come si vede da fuori
un processo ucciso dall'OOM. Due difetti, tutti e due sul **momento** piu' che
sul metodo.

**Uno: le copie.** Il foglio di un cartotecnico sta sui 25 megapixel, cioe' 76
MB a copia. La prima versione ne faceva tre soltanto per rimpicciolirlo e
confrontarlo. Python passava da 359 a 483 MB. Adesso rimpicciolisce PIL, che
alloca solo la destinazione, e l'array grande si materializza **solo** quando
c'e' davvero da riparare.

**Due, ed e' quello che conta: il fork.** Ghostscript costa **105 MB fissi** -
li costa anche con `-sDEVICE=nullpage`, cioe' senza produrre niente: e'
l'interprete, i font, i profili ICC. Non si limano, misurato a 36 e a 12 dpi e
con quattro device diversi, sempre 105. E si lancia con un `fork`: il figlio
parte ereditando lo spazio del padre, quindi chiamarlo **a foglio gia' reso**
lo raddoppia.

La differenza e' tutta li':

    lastra presa DENTRO la rasterizzazione   python 483 + gs 483
    lastra presa PRIMA dell'analisi          python 345 + gs 105

Per questo `nero.spia` decide **tutto** - lastra spia, confronto su un render
piccolo di pdfium, ed eventualmente la lastra buona - e veniva chiamata come
**prima riga** di `build_carton` e `build_flowpack`, prima ancora
dell'analisi. Li' Python pesa 95 MB su un astuccio e 260 su un flowpack: gs
finisce e rilascia molto prima che il foglio grande esista, quindi **il picco
del build non si sposta di un megabyte**. Chi costruisce si porta dietro un
array da pochi MB, e `rasterize_panels` non fa piu' partire nessun processo.

La lezione e' piu' larga della `k`: su un container da 512 MB, *quando* lanci
un processo figlio conta quanto *cosa* gli fai fare.

Adesso `spia` si chiama DOPO l'analisi, sul file senza le note fuori dal DT:
e' la regola "prima le quote, poi via tutto il resto, poi la costruzione", e
la quota del nero e' costruzione. Sugli Spaces (16 GB) il fork costa quello
che costa: sul parco il picco massimo resta sotto 1,4 GB.

### Un'immagine in sovrastampa si somma a quello che trova

In macchina un oggetto in **sovrastampa** stampa solo sulle lastre dei suoi
inchiostri, e le altre restano come sono: il suo inchiostro si aggiunge a
quello che trova. pdfium la sovrastampa la ignora, come per la `k`, e dipinge
ogni oggetto coprente. Sul parco questo rompeva due cose.

**La colata.** L'ombra sotto l'onda del latte e le ombre delle gocce
sono immagini di ciano in sovrastampa sul rosso: in stampa ciano sul rosso fa
l'ombra rosso scuro, coprente esce un alone azzurro. Sul parco la colata e'
sempre fatta cosi' - la banda lunga e le due gocce - e di spazio colore in tre
modi diversi:

    DeviceN di solo Cyan      T1 della barretta fresca, crt, wafer T1, file 159/174/154/1742/1777,
                              T1 cheesecake, croccante T2 fondente, astuccio T8
    RGB indicizzato           T1 al cioccolato fresco
    RGB ICC indicizzato       T1 al mandarino

Non e' LAB: lo spazio colore non c'entra, c'entra la sovrastampa. E prima
l'ombra si riparava solo col livello `Colata` o col riquadro indicato a occhio
(vedi *La colata si rimette con l'inchiostro del file*): sui file che non
avevano ne' l'uno ne' l'altro - crt, wafer T1, i file numerati - restava azzurra.

**La merendina del T1 al cioccolato fresco.** La foto e' in RGB, e sopra, grande
quanto lei, c'e' un'immagine in **PANTONE Cool Gray 8 C in sovrastampa**: un
canale in tinta piatta della foto. Coprente, dove il grigio e' a zero viene
bianco, e un rettangolo bianco copriva la merendina e il latte.

**Ghostscript la sovrastampa la sa simulare, ma proprio qui sbaglia.**
Misurato con PDF fatti apposta - un rosso in tinta piatta e sopra un ciano in
sovrastampa in RGB, RGB indicizzato, CMYK e DeviceN - guardando la lastra del
rosso sotto il ciano:

                                   RGB   indicizzato   CMYK   DeviceN
    senza maschera                resta     resta      resta   resta
    con maschera morbida          via       via        resta   resta
    con maschera, pagina in RGB   via       via        via     resta

L'ombra del T1 al cioccolato fresco e del T1 al mandarino e' RGB con la maschera, e la pagina del T1 al cioccolato fresco e'
un gruppo di trasparenza RGB: Ghostscript il rosso sotto lo cancella, e l'ombra
esce azzurra anche a lui. Per la stessa ragione la merendina: coi gruppi
dichiarati in CMYK la fa vedere anche lui. Non si puo' prendere la sua resa: la
sovrastampa si simula in `strati` (*la sovrastampa delle immagini*).

**Dove sotto non ci sono i suoi inchiostri, la sovrastampa e' Moltiplica.**
L'inchiostro dell'immagine si somma a quello che trova, dove l'immagine e'
bianca non cambia niente, e con la trasparenza della maschera fa esattamente
quello che fa la macchina. `strati.rendi` la chiede a pdfium immagine per
immagine (`FPDFPageObj_SetBlendMode`), sul solo livello della grafica, per le
immagini **disegnate con la sovrastampa accesa** (`/op`, o `/OP` quando `/op`
manca) e la fusione normale - se il file ne dichiara un'altra vale la sua - e
mai per `/All`, che copre anche in macchina. Separation e DeviceN stampano i
loro inchiostri; RGB, CMYK, grigio, Lab e ICC in macchina diventano
quadricromia.

Sul T1 della barretta fresca contro Ghostscript, che li' ha ragione perche' l'ombra e' DeviceN e
la pagina CMYK, sui pixel d'ombra sul rosso:

    Ghostscript (giusto)   (141, 68, 69)
    Moltiplica             (123, 85, 77)
    coprente, pdfium       (104, 196, 229)   l'alone azzurro

**Dove sotto ci sono gli STESSI inchiostri, Moltiplica sbaglia**: in macchina
l'immagine li sostituisce. Una foto in quadricromia in sovrastampa su un fondo
in quadricromia copre, e a moltiplica il fondo si vedrebbe attraverso. Quindi
prima si guarda sotto, dove l'immagine si vede:

- le **lastre di Ghostscript rese senza immagini** (`-dFILTERIMAGE`, 36 dpi,
  mezzo secondo): se c'e' il suo inchiostro sopra il 10%;
- per chi stampa in quadricromia, anche le **altre immagini disegnate prima**
  della prima in sovrastampa, che si presumono in quadricromia. Solo prima: la
  prima versione contava tutte le immagini non in sovrastampa, e sopra la
  colata c'e' sempre un'altra immagine - le sfumature del latte, disegnate
  dopo l'ombra. La contava come fondo, e scartava la colata su tutti i file.

Se ce l'ha sotto in piu' di un terzo dei pixel dove si vede resta coprente, e
il modello lo dice. I due casi stanno lontani: su un PDF di prova la foto CMYK
sul fondo CMYK e il ciano sul fondo ciano ce l'hanno sotto al 98% e restano
coprenti, l'RGB sulla tinta piatta e il ciano sul rosso di magenta e giallo
allo 0-2% e vanno a moltiplica. Sul parco la colata ce l'ha sotto quasi da
nessuna parte, e va a moltiplica su tutti i file: il rosso sotto e' una tinta
piatta o e' magenta e giallo, mai ciano. **Senza Ghostscript** vanno a
moltiplica solo le Separation e i DeviceN, che in sovrastampa ci vanno apposta.

**Quando la simula lei, `colata` non tocca niente** (`colata._gia_simulata`):
niente banda di Ghostscript, niente risorsa. Non e' solo risparmio. Sul T1 al
mandarino Ghostscript diceva "ombra fustellata" e faceva sostituire la colata
del file con la risorsa, ma sotto l'ombra il PANTONE Warm Red c'e' al 90%,
nelle lastre senza immagini: era lui a cancellarlo, portandolo al 31%.

**Il flag di sovrastampa pdfium non lo espone**: si legge dal flusso di
contenuto, seguendo q/Q e gs anche dentro i form, e le immagini si accoppiano a
quelle di pdfium nell'ordine in cui si disegnano. Se i due elenchi non tornano
- quante sono, o le loro misure in pixel - non si tocca niente, e il modello lo
dice. Su ventitre file provati tornano sempre. Dentro un form pdfium da' i
confini delle immagini nelle coordinate del form: il riquadro sulla pagina si
fa componendo le matrici dei form, come in `dividi`.

**Il flusso non si legge con pypdf.** Sulla brioche STD sono 231.000 operazioni
in 7 MB: tre secondi e mezzo solo per trovarne una manciata. Un'espressione
regolare che cerca i soli operatori che servono - q, Q, gs, Do e le immagini
in linea - e salta intere le stringhe, i commenti e i byte delle immagini da'
lo stesso elenco su tutti e ventitre i file, in mezzo secondo sulla brioche STD.
Un file senza nessuno stato grafico in sovrastampa non la paga nemmeno.

**Occhio ai booleani di pypdf**: `bool(BooleanObject(False))` e' `True`, perche'
la classe non ha `__bool__`. La prima ricognizione li leggeva cosi', e dava in
sovrastampa quasi tutte le immagini del parco: 20 su 21 sul wafer da colazione, 38 su 40
sul crt. Letti per valore (`strati._vero`) sono 0 e 12, e sono le colate.

### La grafica va in quadricromia, non in RGB

Un'immagine RGB in macchina la **converte chi stampa**, e il colore lo decide
lui e non il file. E' una regola della stampa, non del gusto, e il nostro
compito e' accorgersene e dirlo prima che l'utente guardi il modello
(`techink.avviso_rgb`, un decimo di secondo e niente in memoria).

**Qui c'era scritto che in RGB la sovrastampa non esiste, e che per questo la
colata usciva di ciano piatto. Era sbagliato.** Un oggetto RGB in sovrastampa
stampa la quadricromia e lascia stare le tinte piatte che trova: sul
T1 al cioccolato fresco e sul T1 al mandarino l'ombra della colata e' un'immagine RGB
indicizzata in sovrastampa sul rosso in tinta piatta, e il rosso sotto resta.
Sembrava di no perche' Ghostscript, sotto un'immagine RGB con una maschera
morbida, la tinta piatta la cancella: vedi *Un'immagine in sovrastampa si somma
a quello che trova*. L'avviso sull'RGB resta, ma per il colore: la colata non
c'entra piu'.

Si guardano le **immagini**, non gli spazi colore dichiarati, e per un motivo
misurato: uno spazio RGB dichiarato c'e' quasi sempre — sul wafer T1 ce n'e'
uno usato 23 volte, e quel file e' validato — perche' lo usa anche l'arte
tecnica, che dalla texture viene via comunque. Una immagine **grande** in RGB
invece e' grafica che si vede: sotto il mezzo megapixel si tace, sopra si
avvisa. Sul parco l'avviso esce su tre file — la colata del T1 al mandarino e due foto
di prodotto in RGB su altrettanti astucci del cliente — e tace sui cinque validati.

Attenzione a non confondere **tre canali** con **RGB**: un `/DeviceN` di tre
inchiostri ha tre canali ed e' tinta piatta in tutto e per tutto, sovrastampa
compresa. Contano solo `/DeviceRGB`, `/CalRGB`, un `/ICCBased` con `N 3` e un
`/Indexed` che ha uno di questi per base.

## Quando la pulizia deterministica non basta

Alcune pulizie non si chiudono con criteri numerici, e non per mancanza di
ingegno: grafica e disegno tecnico, sul piano del disegno, sono la stessa cosa e
differiscono solo per intenzione. Se il file non la dichiara — livelli, legenda,
separazioni con nome — nessuna misura la ricostruisce.

In quel caso si passa alla **post-produzione con un modello di immagine**, con
un'istruzione semplice del tipo "elimina il disegno tecnico dallo steso". Due
vincoli:

- e' un **piano B**, non la strada principale: un modello generativo rigenera i
  pixel, quindi bordi e posizioni possono spostarsi, e il logo e' proprio la
  cosa che non va toccata;
- va applicato **solo dentro la maschera del disegno tecnico**, tenendo i pixel
  originali ovunque altrove. Sul croccante T2 significa rigenerare lo 0,6%
  dell'immagine invece del 100%.

Nel codice il piano B e' lo strumento `reconstruct_area`, che usa
**GPT-Image-2.5 Sunburst** — la variante di precisione rilasciata l'8 settembre
2026 — attraverso `/v1/images/edits`. Con GPT Image il mascheramento e' guidato
dal prompt e il modello puo' non seguirne la forma con precisione, quindi la
ricomposizione la fa il codice: dal risultato si prendono **solo** i pixel
dentro la maschera, fuori restano gli originali. Cosi' logo e grafica non
possono essere riscritti.

La metrica che decide e' `dt_su_immagine_pct`: quanto disegno tecnico cade su
foto, cioe' dove la riverniciatura a tinta piatta non puo' arrivare.

**Da quando il DT si spegne oggetto per oggetto, il piano B serve molto meno.**
Una cordonatura che attraversa una foto e' un tratto vettoriale SOPRA la foto:
spento il tratto, la foto sotto c'e' intera, e non c'e' niente da rigenerare -
ne' a tinta piatta ne' col modello. Resta per il caso che lo spegnimento non
puo' toccare: il disegno tecnico stampato DENTRO un'immagine raster, dove non
e' un oggetto ma dei pixel. Vedi *I due livelli li fa la costruzione*.

### Cosa passare al modello, e cosa no

Le API OpenAI ci sono e sono configurate; la chiave si legge da
`OPENAI_API_KEY` e il modello da `PACK3D_IMAGE_MODEL`. Da tenere distinti,
perche' sono due cose diverse: **chi ragiona e guarda** e' l'agente, che gira
su `PACK3D_MODEL`, e **chi ridipinge** e' il modello di immagine OpenAI dentro
`reconstruct_area`. Quasi tutto quello che segue e' lavoro del primo. Ma "c'e'
il modello"
non e' una risposta: il modello e' bravo a **vedere** e pessimo a **non
toccare**, e la grafica finale e' l'unica cosa che conta. Quindi si divide per
mestiere, non per comodita'.

**La regola che tiene tutto insieme: il modello dice DOVE, il codice fa COSA.**
Un riquadro, una quota, un giudizio "questa ombra e' azzurra" sono risposte
piccole, verificabili e reversibili. Un'immagine rigenerata non lo e': una
volta riscritti, i pixel del logo non tornano.

**1. Quello che il codice non riesce a TROVARE → si', al modello.** *Fatto:
`tools.area_riservata`.*
E' il caso delle aree riservate rimaste: sul cartotecnico T6 aperto e sul
croccante T2 fondente il nome dell'area sta solo nella legenda, non sopra il
riquadro, e nel file non c'e' niente di sicuro da leggere — vedi *Le aree
riservate non compaiono mai nel render*. Per un occhio invece sono ovvie: un
rettangolo pieno con scritto `BEST BEFORE AREA` in bianco dentro. Questo e'
lavoro da modello, ed e' **piu' semplice** di qualunque euristica.

Ma quello che torna indietro e' un **riquadro in mm**, non un'immagine: un'area
riservata e' un rettangolo pieno, quindi il riquadro approssimativo basta come
innesco e il bordo esatto lo trova il codice attaccandosi alla lastra. Cosi'
l'errore del modello vale qualche millimetro di innesco — **3 mm non cambiano
niente**, misurato — invece di un logo riscritto. E prima di confermare il
modello **guarda** cosa sta per togliere: vedi *Quando il file non le scrive
nemmeno: allora si guarda*.

*Lo strumento e' `tools.area_riservata`*, e restituisce l'immagine da
guardare prima di confermare. Vedi *Quando il file non le scrive nemmeno:
allora si guarda*.

**2. Quello che il codice trova ma non sa RIPARARE → si', al modello.**
Disegno tecnico che attraversa una foto: li' la riverniciatura a tinta piatta
non arriva e non c'e' niente da inventare a mano. E' `reconstruct_area`, e la
cautela e' gia' scritta sopra: **solo dentro la maschera**, fuori restano i
pixel originali. Sul croccante T2 sono lo 0,6% dell'immagine.

**3. La colata → no al pennello, si' all'occhio.**
La colata non ha pixel mancanti: ha l'inchiostro sbagliato. L'ombra sulle
gocce esce azzurra invece che scura, e quello si risolve con la quadricromia e
la sovrastampa, non ridipingendo — vedi *La colata si rimette con l'inchiostro
del file*. Un modello generativo la reinventerebbe: gocce diverse, ombre
diverse, e la cosa che si stava giudicando sparisce dentro la riscrittura. Per
un marchio, ridisegnare non e' riparare. E non saprebbe nemmeno QUALE scuro:
quello giusto e' il prodotto del ciano del file per il rosso sotto, un numero
che il file porta e che Ghostscript calcola.

Il modello sulla colata serve a **guardarla**, e serve due volte:

- a **trovarla**, sui file che non la mettono su un livello suo — otto su
  nove, sul parco — dove il codice non ha niente da misurare. Il modello
  indica la banda, il codice rilegge l'inchiostro: `tools.colata_a_occhio`.
- a **giudicarla**: "questa ombra e' azzurra o e' scura?" e' esattamente la
  domanda che le metriche hanno sbagliato piu' volte, e che l'occhio risolve
  in un secondo. Per questo lo strumento torna la banda prima e dopo.

Giudizio si', pennello no.

**4. Quello che non va mai al modello.** I loghi, la `k` nera del marchio, i
marchi, il testo di prodotto: non si rigenerano nemmeno dentro una maschera,
e se la maschera li tocca la maschera e' sbagliata. E nessuna misura: una
quota si misura, non si chiede a un'immagine.

**5. E il modello non copre mai quello che il file poteva dichiarare.**
Se manca il livello del disegno tecnico, la risposta e' *Cosa chiediamo a chi
prepara l'artwork*, non una chiamata API su ogni build. Il piano B costa una
chiamata e un rischio: si usa dove il file non poteva dire di meglio, non
dove non gliel'abbiamo chiesto.
