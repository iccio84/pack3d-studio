# Regole: Astucci, finestre e rilievi

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Astucci

`dieline.py` isola il tratto della fustella scegliendo la penna che accumula
piu' lunghezza **e** piu' cordonature distinte; scarta i riquadri dell'artwork
riconoscendoli dalla coppia contorno+riempimento; isola il gruppo connesso piu'
esteso per escludere i cartigli, recuperando pero' i gruppi che cadono
nell'ingombro (le alette con fianchi obliqui non toccano il corpo con tratti
dritti); valida le cordonature fascia per fascia, altrimenti le alette di presa
del cielo vengono scambiate per fianchi. Il verso di fasciatura, verticale o
orizzontale, si deduce dalla struttura, e cosi' la **famiglia**: chiuso o
aperto, vedi sotto.

Le tre regole di tutte le famiglie valgono anche qui, meno le pinne. Le
**testate** dell'astuccio sono le alette di chiusura sopra e sotto: si
prendono dalla fustella - il bordo piu' esterno compatibile con la profondita'
della scatola - e mai da dove finisce la stampa. La grafica decide una cosa
sola, quale dei due pannelli larghi e' il fronte, e non misura niente. Poi le
facce contro i pannelli del DT e il fronte sul fronte (`verifica.facce_astuccio`)
e le quote scritte (`quote.riscontro_astuccio`), dal server come dalla riga di
comando, che fa gli stessi controlli e la stessa texture HD.

### La griglia non tollera un intruso

Righe e colonne sono la cosa piu' fragile della pipeline astucci: **una sola
riga in piu' e i ruoli cadono tutti sul pannello sbagliato**, senza che niente
lanci un'eccezione. Due modi in cui un intruso ci entrava, trovati sullo stesso
file (T6 aperto):

- **il gruppo di fianco.** `_largest_cluster` recuperava i gruppi contenuti
  nell'ingombro della fustella con un test su **un asse solo**, che serve per
  le alette a fianchi obliqui: quelle sporgono da un lato e sono contenute
  nell'altro. Ma un cartiglio a 90 mm dalla fustella e' contenuto nella sua
  ALTEZZA, e tanto bastava a tirarlo dentro: il riquadro usciva **679 mm invece
  di 261**, e `solve_carton` moriva su `KeyError: 'left'`. Ora serve contenuto
  in un asse **e** attaccato al corpo nell'altro: un'aletta lo e' per
  definizione, un cartiglio no.
- **la penna che non e' fustella.** `_technical_pens` tiene tutti i tratti
  sottili che contribuiscono linee lunghe, e fa bene — molti artwork separano
  taglio, cordonatura e mezzo taglio su colori diversi. Ma per la GRIGLIA un
  intruso e' fatale, e su questo file c'era un rettangolo nero CMYK da 0,76 pt,
  quattro segmenti in tutto, che non e' fustella: creava due colonne e una riga
  finte, e la riga spaccava il fronte in due. Si scartano quindi, dopo il
  raggruppamento spaziale, le penne che non "sanno" di fustella
  (`penne_di_fustella`). Il punteggio non e' la lunghezza ma **lunghezza per
  numero di cordonature distinte**: una penna di piega vera porta molti tratti
  su molte quote, un rettangolo solo no. Misurato: su tutto il parco la penna
  di fustella e' una sola e sta a 1,00, quell'intruso a 0,14.

  Nota: la funzione che da' questo punteggio, `_dieline_pen`, era scritta da
  tempo e **non la chiamava nessuno**.

### Quando il solutore non sa, deve dirlo

`solve_carton` non prova a indovinare: **legge la sequenza delle fasce e
decide a quale famiglia appartiene**. Se non e' nessuna delle due, solleva un
errore che riporta le fasce misurate in millimetri, e l'errore dice quale
condizione e' mancata.

Prima di leggere le fasce, pero', bisogna sapere **quali linee sono fasce**. Le
`ys` del foglio sono l'unione di tutte le cordonature, e ci finisce anche
quello che non piega il corpo: sul T6 aperto una linea a 27 mm dal fondo — dove le
alette laterali cambiano profilo — spezzava la faccia da 125 in 98 + 27, e il
fronte spariva dalla lettura. Una cordonatura che separa due fasce della
fasciatura **deve attraversare la colonna del corpo**; quelle che non lo fanno
appartengono alle alette (`_fasce_del_corpo`). E' lo stesso criterio che si
usava gia' per le colonne, applicato anche alle righe.

I controlli che decidono la famiglia:

- **astuccio chiuso**: retro e fronte devono avere la **stessa altezza**. Sono
  la stessa faccia vista da due parti. Il solutore prende come retro e fronte
  le due fasce piu' alte e ne fa la media: sul T6 aperto erano 40,5 e 125,0 e la
  media, 82,8, non e' l'altezza di niente. Quaranta contro centoventicinque
  vuol dire che questa non e' la lettura giusta. Delle due, il **retro e'
  quella che porta i fianchi**: vedi *Il retro e' la faccia che porta i
  fianchi*;
- **astuccio aperto**: cielo e fondo devono essere **uguali attorno a una
  faccia sola**, e i **fianchi devono tornare con la profondita'**;
- in tutti i casi **cielo o fianco devono esistere**, altrimenti la profondita'
  non e' ricavabile e prima si leggeva un `KeyError: 'left'`.

### Un astuccio puo' non chiudersi

**Un astuccio non e' obbligato ad avere il retro.** Un vassoio non ce l'ha per
definizione; un espositore da banco nemmeno; un pack con finestra ce l'ha a
meta', chiuso da due falde che lasciano in mezzo l'apertura da cui si vede il
prodotto. Trattare il retro come obbligatorio non e' prudenza: e' rifiutare una
famiglia di astucci che esiste.

La firma in fustella di un astuccio aperto e' netta e non si confonde con
quella di uno chiuso:

    chiuso   [aletta] RETRO | CIELO | FRONTE | FONDO     fianchi accanto al RETRO
    chiuso   CIELO | FRONTE | FONDO | RETRO [colla]      fianchi accanto al RETRO
    chiuso   FONDO | RETRO | CIELO | FRONTE [aletta]     fianchi stampati sul FRONTE
    aperto   [falda] CIELO | FRONTE | FONDO [falda]      fianchi accanto al FRONTE

cioe' **una faccia grande sola**, con cielo e fondo **uguali** sopra e sotto, e
i fianchi agganciati al fronte — al retro che non c'e' non possono esserlo. Le
due fasce oltre il cielo e il fondo, se ci sono, sono le **falde del retro**, e
quello che non coprono e' la **finestra**.

Su un astuccio aperto i fianchi **sono** la profondita', e devono tornare con
cielo e fondo. Questo controllo non e' una cintura di sicurezza, e' quello che
tiene fuori i flowpack: sul wafer da colazione la fascia grande e' il nastro, cielo e
fondo sono due falde da 5 mm perfettamente uguali, e senza il controllo ne
usciva un astuccio profondo cinque millimetri. I fianchi da 7 lo smentiscono, e
il solutore si ferma.

#### Il retro e' la faccia che porta i fianchi

Un astuccio chiuso ha due facce alte uguali, e quale sia il retro non lo dice
l'altezza. Il solutore prendeva sempre per retro **quella in alto** sul foglio,
che e' lo schema `[aletta] RETRO | CIELO | FRONTE | FONDO`. L'**astuccio
T8** (disegno 17435) e' montato al contrario:

    fasce (mm)   12 | 82 | 12,5 | 82 | 10
                 cielo  fronte  fondo  retro  colla
    fianchi      11,5 x 82 sulla faccia BASSA, con le alette colla da 10,5

Letto alla solita maniera il modello usciva sbagliato senza nessun errore: sul
fronte il pannello bianco, il bambino sul retro e capovolto, per fondo la
linguetta della colla, i fianchi senza grafica, e la fascia del cielo col
marchio e il "100g" spariva.

Quale e' il retro lo dice la fustella, senza guardare la grafica: **i fianchi
stanno sul retro** - e' la stessa ipotesi su cui `FOLD_V` costruisce le pieghe.
Se li porta solo la faccia bassa, il retro e' lei (`dieline._chiuso` con
`_ha_fianchi`). Cielo e fondo restano quello che sono per il **fronte**: il
cielo e' la fascia sopra il fronte, se e' profonda come il fondo, e il fondo
quella fra fronte e retro. Le pieghe non cambiano: il cielo tocca il fronte col
bordo basso, il fondo col bordo alto, e il retro ha comunque il bordo alto in
fondo alla scatola - nello schema solito perche' scavalca il cielo, qui perche'
risale dal fondo. La linguetta della colla non e' una faccia e resta fuori.

Verificato guardando il modello: il cielo col marchio si legge dal
davanti, l'onda rossa del fronte gira sul fondo e si ricongiunge con quella in
basso sul retro, e le verifiche - UV sul DT e fronte sul fronte - passano. Il
cielo e' 12 mm e il fondo 12,5: la scatola esce profonda 12, e il fondo e i
fianchi da 11,5 si stirano del 4-5%.

#### Se i fianchi li portano tutte e due, si vedono quelli stampati

Il retro che porta i fianchi e' la regola della fustella, e vale quando i
fianchi li porta una faccia sola. Quando li portano **tutte e due** le facce
alte, una coppia si vede e l'altra sono alette che finiscono dentro - bianche,
o tratteggiate per la colla - e quale sia lo dice la **stampa**: il solutore
prepara tutte e due le coppie (`Dieline.fianchi_alt`) e la texture sceglie
quella con piu' croma, con lo stesso margine con cui si sceglie il fronte di
una fasciatura orizzontale, un quarto in piu' e quattro punti
(`artwork.scegli_fianchi`). E la quinta dei fianchi segue la faccia a cui sono
agganciati (`Dieline.fianchi_su`, `folding.build_faces` con
`fianchi_sul_fronte`): quelli del retro ne ereditano il mezzo giro, quelli del
fronte no, come su un astuccio aperto.

Il caso e' l'**astuccio della ciambella**, letto nel verso della grafica - che sul
foglio e' girato di 90 gradi rispetto al DT:

    fasce (mm)   38,1 | 187,7 | 38,1 | 188,5 [aletta]
                 fondo  retro   cielo  fronte
    fianchi      36,9 sul retro, tratteggiati per la colla (croma 5)
                 36,9 sul fronte, arancio col marchio (croma 154)

Oltre il fronte c'e' solo l'aletta: **il fondo sta oltre il retro**, ed e' la
fascia marrone che continua l'onda del retro (`dieline._chiuso`, se e'
profonda come il cielo). Prima l'astuccio si leggeva come fasciatura
orizzontale nel verso del DT, e il modello aveva il cielo capovolto, un
fianco tutto marrone e per fondo un'aletta; adesso il cielo col
marchio si legge dal davanti, i fianchi arancio continuano l'onda marrone del
fronte e il fondo e' marrone.

#### Le falde del retro sono fasce, non facce

Sul solido le due falde non sono facce intere: sono **fasce del retro**, e in
mezzo resta il buco. Gli angoli si interpolano lungo i due lati verticali del
retro (`folding._fascia`), e non serve rifare i conti sul ribaltamento della
fasciatura: una fascia del retro **eredita la quinta del retro**, basta
accorciarla dal lato giusto. Con la fascia intera — da 0 a 1 — la formula
ridiventa esattamente il quad del retro, che e' la prova che l'interpolazione
non ha invertito niente.

Da che lato si accorcia lo dice la piega, non il gusto:

- la falda **alta** arriva scavalcando il cielo, quindi il suo bordo di
  cordonatura sta **in cima** al retro e il bordo libero scende verso la
  finestra;
- la falda **bassa** risale dal fondo, quindi il suo bordo di cordonatura sta
  **in fondo** e il bordo libero sale verso la finestra.

Verificato guardando il modello: la fascia rossa con l'onda di latte gira
attorno al fondo del pack e **si ricongiunge** — sul fronte si legge
`latte | onda | rosso` scendendo, sulla falda bassa del retro si legge
`bianco | onda | rosso` scendendo, che e' la stessa banda vista dall'altra
parte. Se il ribaltamento fosse invertito la banda non combacerebbe col fondo.

#### I fianchi di un astuccio aperto non si ribaltano

Su un astuccio chiuso i fianchi sono agganciati al **retro**, e il retro si
ribalta perche' la fasciatura scavalca il cielo: i fianchi ereditano quel
ribaltamento, ed e' quello che `FOLD_V` mette in tabella. Su un astuccio aperto
il retro non c'e' e i fianchi sono agganciati al **fronte**, che non si ribalta.
La quinta dei fianchi va quindi ruotata di 180 gradi (`FIANCHI_SUL_FRONTE`),
altrimenti la loro grafica esce capovolta — ed e' quello che si vedeva sul
T6 aperto, con la foto del prodotto e il QR a testa in giu'.

Che siano quelli i quad giusti non serve crederlo: `FOLD_H` lo dice. Nella
fasciatura orizzontale i fianchi sono agganciati al fronte per costruzione, e le
sue due voci `left` e `right` sono **identiche** a queste.

#### Il caso calibrato: T6 aperto

    colonne (mm)   16 | 4 | 8 | 32,3 | 140,5 | 32,3 | 8 | 4 | 16
    fasce   (mm)   33,5 | 40,5 | 125,0 | 40,5 | 30,0
    fianchi        40,3 x 125,0, accanto al FRONTE
    quote          140,5 x 125,0 x 40,5 mm
    finestra       61,5 mm di altezza, fra le due falde da 33,5 e 30,0
    guscio         7 facce esterne + 7 interne + 8 coste

E' un pack cartotecnico con il **retro a finestra**, che lascia intravedere i
sei merendine dentro. Il riscontro che chiude il conto e' la profondita' letta due
volte da due posti diversi: cielo e fondo danno **40,5**, i fianchi **40,3**.
Costruisce in 3,9 s con 354 MB di picco.

**L'orientamento e' verificato sul pack vero, e non va piu' toccato.** I
fianchi erano girati di 180 gradi e sono stati corretti — vedi *I fianchi di
un astuccio aperto non si ribaltano*; dopo quella correzione e' arrivata la
segnalazione che fosse il **fronte** a essere girato, e il modello e' stato
riguardato dai sei lati con chi il pack ce l'ha in mano: **fronte e cielo
leggono dritti, ed e' giusto cosi'**. Nessun pannello e' stato ruotato per
quella segnalazione. Se ricapita, si guarda il GLB prima di girare qualcosa:
girare un pannello che e' gia' a posto costa due errori invece di uno.

### Un astuccio ha uno spessore

Un astuccio non e' una superficie, e trattarlo come tale si paga proprio dove
il pack e' aperto: ogni faccia ha una normale sola, da dietro il culling la fa
sparire, e guardando dentro la finestra del T6 aperto non si vedeva niente.
Il pack diventava un guscio di carta zero.

Con lo spessore l'interno c'e', ed e' cartoncino. Per ogni faccia si aggiunge:

- la **faccia interna**, spostata di `PACK3D_SPESSORE_CRT` (0,45 mm, o lo
  spessore che l'utente ha dichiarato, vedi *Il cartotecnico dice di che
  carta e' fatto*) lungo la normale entrante e con l'avvolgimento
  rovesciato, perche' la sua normale guardi dentro;
- su ogni spigolo **aperto**, la **costa** del taglio: e' la parte che fa
  leggere lo spessore sul bordo di una finestra.

Gli avvolgimenti non si ragionano, si derivano. Su una superficie orientata due
facce adiacenti percorrono lo spigolo in comune in senso **opposto**: quindi
rovesciare l'ordine di un quad da' una faccia interna coerente, e una costa
percorre lo spigolo condiviso al contrario della faccia da cui nasce. Cosi' il
verso viene giusto senza dipendere da quale convenzione usano gli esportatori —
che qui e' `n = -(q1-q0) x (q3-q0)`, verificata sul fronte.

Uno spigolo e' "aperto" se non confina con nessun'altra faccia, e si riconosce
per coincidenza dei vertici su una griglia da 0,02 mm. Misurato:

    T6 aperto                          7 facce esterne + 7 interne + 8 coste
    astuccio della ciambella (chiuso)  6 facce esterne + 6 interne + 0 coste

e le otto coste del T6 aperto sono esattamente quelle che deve avere: il bordo
dietro dei due fianchi e i tre lati liberi di ognuna delle due falde. Su un
astuccio chiuso di coste non ce n'e' nessuna, che e' il controllo che la
ricerca degli spigoli aperti funziona.

Il rovescio del cartoncino e il taglio **non stanno nell'artwork**: il PDF dice
solo la faccia stampata. Sono due tinte neutre, e vanno dichiarate per quello
che sono — una stima, non una misura.

#### Lo spessore ha scoperto che il rasterizzatore dipinge e basta

`raster.render` — quello del render di presentazione, non quello a z-buffer
delle superfici curve — non ha profondita': dipinge le facce nell'ordine della
lista, e chi dipinge dopo copre. Finche' un astuccio era sei facce senza
spessore non si vedeva, perche' il culling ne lascia tre e tre facce di una
scatola convessa non si sovrappongono mai.

Col guscio si vede eccome. L'**interno della parete lontana** guarda la camera,
quindi sopravvive al culling, e stando in fondo alla lista dipingeva sopra
l'esterno della parete vicina: i due astucci uscivano **grigi pieni**. Adesso le
facce si ordinano per profondita' del baricentro, dal fondo in avanti. Basta
l'ordinamento per baricentro: sono quad piani che non si compenetrano.

E' anche un promemoria sul metodo: le normali le avevo verificate una per una e
tornavano tutte: la faccia interna guarda dentro, quella esterna fuori, le
coste sono spesse 0,45 mm. Il modello era giusto e il render sbagliato lo
stesso, perche' il difetto non stava nella geometria. Il controllo visivo
**dopo** quello numerico non e' una ripetizione.

### L'apertura a strappo si incide, non si disegna

Un astuccio con l'apertura a strappo - il T5 a strappo "with frontal
opening": una finestra sul fronte che si stacca tirando la linguetta sotto il
fondo - chiuso, in mano, fa vedere i suoi tagli: i due lati e le due
diagonali della finestra, la linguetta, la mezzaluna per il dito. Il modello
li fa vedere allo stesso modo: **solchi** nella faccia, modellati, che la luce
fa leggere. Non righe disegnate sopra la grafica: la grafica resta quella del
file, intera, perche' sul cartone il taglio non e' stampato. L'astuccio resta
chiuso. Lo fa `pack3d/incisioni.py`.

#### Si incide solo quello che ha la firma dell'apertura

Dentro le facce la fustella ha anche altro: il contorno di un pannello
disegnato un millimetro dentro la sua cella, gli smussi agli angoli dei
fianchi, i tratti di un riquadro d'area. Incidere ogni tratto che sta dentro
una faccia li incideva tutti, e quattro astucci del parco uscivano con solchi
che sulla scatola vera non ci sono. Un tratto qualsiasi non dice cos'e', e un
solco sbagliato e' peggio di nessun solco.

L'apertura a strappo invece si riconosce, perche' e' fatta di **due** tagli:

- quello sul lato stampato, che si vede;
- accanto, fra 1,5 e 5 mm e per almeno 10 mm, il **taglio parziale dal
  rovescio**. Nella legenda dei disegni del cliente e' la riga con le stanghette,
  e cosi' lo si legge: un tratto attraversato quasi di traverso (piu' di 60
  gradi) da almeno due spunte, trattini piu' corti di 2,6 mm.

E' la coppia che fa staccare il cartone pulito fra i due tagli. Con l'apertura
si incidono i tagli che la continuano - che ne toccano un estremo: la
linguetta, anche quando gira su un'altra faccia - e quelli a meno di 3 mm,
come la mezzaluna. Il taglio dal rovescio **non** si incide: sta sulla faccia
interna del cartoncino, da fuori non si vede. Le spunte nemmeno: sono un segno
del disegno, non un taglio.

I tratti sono quelli della penna del disegno tecnico (`dieline._technical_pens`)
che stanno **dentro** un pannello di una faccia del solido, almeno 0,6 punti
dentro il bordo: il bordo e' una piega o il contorno. Un rettangolo chiuso non
c'entra mai: e' il riquadro di un'area. Le linee si cuciono sul foglio intero,
attraverso le pieghe, e si tagliano alle facce solo alla fine: la linguetta
che gira sotto il fondo esce in due pezzi, uno sul fronte e uno sul fondo.
Misurato sul T5 a strappo: due linee da 125,2 mm sul fronte, lati e diagonali
compresi; sul fondo la linguetta (52,1 mm) e la mezzaluna (25,0 mm). Il
T5 a strappo e' nel parco; nessun altro astuccio del parco ha la firma, e
tutti escono identici al byte.

#### Il solco

- A V: largo 0,35 mm in superficie, profondo 0,22 mm sulla linea, e mai piu'
  di meta' dello spessore del cartoncino (vedi *Un astuccio ha uno spessore*):
  la faccia interna non si tocca.
- Le pareti hanno la tinta della costa (`folding.TAGLIO`): sono cartoncino
  tagliato. In un materiale suo, "solco".
- La faccia incisa si triangola con Delaunay sui campioni del solco - la linea
  e i suoi due bordi, ogni 0,15 mm - piu' i quattro angoli. I campioni sono
  piu' fitti della larghezza del solco: un triangolo che lo scavalcasse avrebbe
  nel cerchio circoscritto i punti della linea, e Delaunay non lo fa.
- I bordi del solco stanno **a fior di faccia**: una profondita' sotto un
  quinto di quella piena si azzera. Senza, l'arrotondamento dei punti dava ai
  bordi qualche micron, e ogni triangolo grande che li toccava - mezza faccia
  - finiva nel solco, grigio e storto.
- Le linee passano dal foglio alla texture della faccia col **giro** che
  `artwork.gira_sulla_grafica` ha dato alla texture (`esito["girate"]`), e si
  incide sulle facce finite, dopo `folding.gira_facce`. Provato col foglio
  girato di 90, 180 e 270 gradi: stesso modello, stesse viste.
- La faccia tiene il suo `quad`, che serve alle verifiche, al guscio e alle
  viste; l'esportatore GLB, se c'e' `maglia`, scrive quella. Il GLB del T5
  a strappo passa da 1,2 a 2,3 MB. L'OBJ e il render della riga di comando restano
  lisci.
- Un guasto nell'incisione non ferma la costruzione: l'astuccio esce chiuso e
  liscio, e l'avviso lo dice.

#### Il controllo dell'AI deve sapere cosa sono quelle righe

Nelle viste i solchi sono righe sottili color cartone che seguono la fustella:
a chi non lo sa sembrano disegno tecnico rimasto stampato, che e' un difetto.
Quando il modello e' inciso, il contesto del controllo porta un "Da sapere":
sono i tagli dell'apertura a strappo, incisi come sulla scatola vera, e la
grafica sotto e' intera. Non cambia cosa e' un difetto; dice cosa sono quelle
righe. Vale anche per la correzione, che la nota la somma alla sua.
Sullo Space il T5 a strappo e' passato al primo colpo, ok: "Le righe sottili
sul fronte sono i tagli dell'apertura a strappo incisi nel cartone, non
residui stampati".

#### La perforazione e' l'altra firma

Sul T10 al lampone l'apertura non ha il taglio dal rovescio: e' una
**perforazione**, una fila di trattini - 13 mm di taglio e 1,7 di ponticello -
che parte dalla piega fra fronte e cielo, scende sui due lati del fronte,
passa sul fondo, corre in orizzontale con la mezzaluna per il dito e torna
sulla stessa piega. La firma di prima non la vedeva, e l'astuccio usciva
liscio, senza nessuna domanda sull'apertura.

`incisioni.perforata` la segue di trattino in trattino: il prossimo e' quello
il cui capo sta a meno di 2,5 mm (`PONTE`) e che gira di meno, al piu' di 60
gradi; cosi' alla mezzaluna la fila prende la corda dritta, e il mezzo cerchio
resta un taglio vicino, la lunetta. Vale come apertura solo se:

- ha almeno 8 ponticelli veri (`PONTI_MIN`), piu' lunghi di mezzo millimetro;
- e' lunga almeno 80 mm (`PERFORATA_MIN`);
- i due capi stanno **sulla stessa piega**, quella da cui parte.

Una riga tratteggiata qualunque dentro una faccia - una piega di servizio, il
riquadro di un'area - non torna sulla piega da cui parte. I tratti che corrono
lungo il bordo di un pannello sono pieghe, e non si seguono.

Chiusa, la perforazione si incide **trattino per trattino**: i ponticelli sono
cartone intero, e sul modello il solco e' tratteggiato come sulla scatola. Per
aprirla, il contorno e' la fila coi ponticelli colmati, senza taglio dal
rovescio e quindi senza cartoncino sfogliato: la finestra si alza sulla piega
col cielo, la linguetta gira sotto il fondo, la lunetta si spinge dentro. Sul
T10: 37 trattini e la mezzaluna, 463 mm di contorno, cerniera di 144 mm.

### L'apertura a strappo, aperta

Lo stesso astuccio si puo' volere **aperto**: la finestra sollevata di tot
gradi, come quando la si e' appena strappata. Lo sceglie chi carica: la
pagina lo chiede quando l'analisi trova l'apertura (vedi *L'apertura a
strappo: chiusa o aperta*), e la costruzione riceve l'opzione `apertura` in
gradi (0 chiusa, fino a 180); senza, resta chiuso, coi solchi. Quanto aprire lo dice l'utente; da dove si apre, come si strappa e
come sta la scatola aperta lo dice la fustella, e lo fa `pack3d/apertura.py`.

- **La cerniera** e' la piega su cui finiscono i due capi del contorno dei
  tagli d'apertura: il contorno parte da una piega, gira attorno alla finestra
  e alla linguetta e torna sulla stessa piega, e fra i due capi la finestra
  resta attaccata. Sul T5 a strappo e' la piega fra fronte e cielo, 126 mm. Se
  i capi non stanno sulla stessa piega - o la piega e' un bordo libero - la
  cerniera non c'e', e l'astuccio esce chiuso con l'avviso che lo dice.
- **La finestra si porta dietro la linguetta**: il contorno attraversa la
  piega col fondo, e il pezzo che si solleva e' finestra piu' linguetta, piegate
  come erano. Ruota rigido attorno alla cerniera, verso fuori.
- **Il cartoncino si sfoglia fra i due tagli.** Il taglio davanti e quello dal
  rovescio corrono a 3 mm, e strappando il cartoncino si divide nello spessore:
  la scatola tiene lo strato di dentro fino al taglio dal rovescio, la
  finestra lo strato di fuori fino al taglio davanti. Attorno al buco resta una
  cornice di 3 mm di cartoncino chiaro a mezzo spessore, e sotto la finestra la
  stessa cornice rovesciata. Sul T5 a strappo il taglio dal rovescio si ferma
  2 mm prima della cerniera: si allunga fino alla piega (fino a 5 mm, oltre non
  si sa dove vada e il taglio si fa passante).
- **La lunetta va dentro.** La mezzaluna per il dito si attacca coi due capi
  alla punta della linguetta e chiude con lei un pezzo a se': e' quello che si
  spinge col dito per prendere la linguetta. Aperta la scatola, al suo posto
  c'e' il buco, e la tacca nel fondo segue la mezzaluna. Un taglio vicino che
  non si attacca coi due capi non si disegna, e l'avviso lo conta.
- **La scatola appoggia sulla faccia opposta alla cerniera**, cioe' sul retro:
  la finestra guarda in alto, la cerniera sta dietro e la linguetta viene
  verso chi guarda. Della finestra sollevata, dal davanti si vede il rovescio;
  la grafica, guardata dal lato stampato, si legge capovolta. E' come sta la
  scatola vera: la cerniera e' in cima alla grafica.

Ogni faccia attraversata dal contorno si **triangola una volta sola**, con
Delaunay sui bordi campionati ogni 0,25 mm - il contorno, il taglio dal
rovescio, la lunetta - e ogni triangolo prende una zona: scatola intera,
finestra intera, striscia sfogliata, lunetta. La zona dice chi ha cartoncino
e fra quali profondita': da li' vengono la superficie stampata (la texture
della faccia), il rovescio, la cornice sfogliata e i bordi del taglio, che
stanno esattamente dove due zone si toccano e solo per lo spessore che da una
parte c'e' e dall'altra no. Niente si incolla dopo: scatola e finestra
escono dagli stessi triangoli, e chiuse coinciderebbero.

Misurato sul T5 a strappo: il foglio girato di 90, 180 e 270 gradi da' lo
stesso modello aperto (viste identiche). A 60 gradi l'ingombro e' 168 x 109 x
95 mm, la scatola sdraiata e la finestra che sale di 82 mm; il GLB passa da
2,3 a 2,6 MB. Un astuccio senza apertura a strappo, chiesto aperto, esce
chiuso e lo dice.

Il controllo dell'AI riceve un "Da sapere": l'astuccio e' mostrato aperto come
l'ha chiesto chi l'ha caricato, sdraiato, con la grafica della finestra
capovolta vista dal lato stampato, l'interno di cartoncino non stampato e la
cornice sfogliata. Come per i solchi, non cambia cosa e' un difetto.

### La colata si rimette con l'inchiostro del file

**Adesso di solito non serve.** L'ombra della colata e' sempre un'immagine in
sovrastampa, e la simula il livello della grafica su tutti i file, livello
`Colata` o no: vedi *Un'immagine in sovrastampa si somma a quello che trova*.
Quando lo fa, qui non si tocca niente. Quello che segue resta per le colate che
la grafica non copre e per la pagina resa com'e'.

**E una correzione.** Il T1 al mandarino qui sotto e' dato per ombra
"fustellata", e non lo e'. Le lastre erano quelle di Ghostscript, che sotto
un'immagine RGB con una maschera morbida la tinta piatta la cancella: sulle
lastre rese senza immagini, sotto l'ombra il PANTONE Warm Red c'e' al 90%.
L'ombra e' in sovrastampa come sugli altri file, e il file non aveva niente
da farsi perdonare.

Il nostro rasterizzatore **non simula la sovrastampa**. Verificato con un PDF
costruito apposta - un ciano sopra un magenta, disegnato due volte, una con
`/OP true` e una senza:

    pdfium       con sovrastampa (0, 174, 239)   senza (0, 174, 239)
    ghostscript  con sovrastampa  (46, 48, 146)  senza (0, 174, 239)

Identico tutte e due le volte, con pdfium. E non e' un caso limite: la
sovrastampa e' una cosa da device separato, e un rasterizzatore RGB la butta
via per costruzione. La colata e' costruita proprio cosi' - una lastra
di ciano che **moltiplica** il rosso sotto, e da quella moltiplicazione
vengono l'ombra sulle gocce e il volume del getto - quindi il ciano copre il
rosso invece di moltiplicarlo, e l'ombra diventa un alone azzurro piatto.

Ghostscript con `-sOverprint=simulate` la simula, e da' il blu giusto. Da qui
due strade, in quest'ordine, perche' **l'inchiostro del file viene prima di
qualunque cosa portata da fuori**:

1. **la banda resa in quadricromia**, con Ghostscript. Si ritaglia il MediaBox
   sulla sola banda della colata e si rende quella: 120 x 36 mm su un foglio
   da 300 x 250, un paio di secondi e una quarantina di MB invece dei dieci
   secondi della pagina intera.
2. **la risorsa** della colata in `risorse/`, solo se la prima non ha niente
   da correggere.

Se Ghostscript non c'e', il codice se ne accorge e resta la seconda: non si
rompe niente, si fa meno.

#### Solo dentro l'impronta del livello, e non per pignoleria

La banda in quadricromia si incolla **solo dentro l'impronta del livello
`Colata`**, mai su tutta la banda e mai su tutta la pagina. Il motivo e'
misurato: rendendo in quadricromia l'intera pagina del T1 al mandarino il
marchio e il bicchierino di latte diventano **neri**. Non e' un
difetto di Ghostscript ne' l'appiattimento in CMYK - ricomponendo lastra per
lastra con i colori veri delle Pantone il nero resta - e' che quegli elementi
la sovrastampa ce l'hanno davvero. Ma sul livello `Colata` non stanno, e fuori
dall'impronta non li tocca nessuno.

#### Quanto conta la sovrastampa non si misura ad area

La domanda non e' quanta parte della banda cambia. Quella e' area, e sui due
casi misurati da' lo stesso 5% pur essendo casi **opposti**. La domanda e':
delle zone che senza sovrastampa escono azzurre - cioe' delle ombre sbagliate
- quante ne rimette a posto?

    T1 al mandarino      13.248 px azzurri, ne recupera l' 1,1%
    T6 aperto            7.672 px azzurri, ne recupera il 49,6%

Il secondo ha l'ombra in sovrastampa e si recupera meta'. Il primo ce l'ha
**fustellata**: il ciano toglie il rosso invece di moltiplicarlo, e sotto non
c'e' piu' niente da moltiplicare. Lo dicono le lastre, dove pdfium vede
l'azzurro:

    Cyan 34,9%   PANTONE Warm Red C 2,6%     (nel rosso pieno accanto: 98,1%)

Quel file non lo aggiusta nessun rasterizzatore, e li' si passa alla risorsa.
E' anche l'informazione che serve a chi prepara l'artwork, e infatti viene
dichiarata nei cartellini invece di restare dentro il codice.

#### Il file che il livello non ce l'ha: lo indica l'occhio

Tutto quello che c'e' scritto sopra parte dal livello `Colata`: e' il livello
che dice DOVE sta la colata, e senza di lui non c'e' niente da misurare. Sul
parco di prova il livello ce l'ha **un file su nove**, e su tutti gli altri
non succedeva niente: l'ombra restava azzurra e nessuno lo diceva.

Li' l'unica cosa che resta e' guardare, ed e' il caso in cui il modello serve
davvero: **indica la banda, e l'inchiostro fa il resto**. Lo strumento e'
`tools.colata_a_occhio`, e la divisione del lavoro e' quella di sempre - il
modello dice DOVE, il codice decide CHE COSA.

Dentro il riquadro non si tocca il riquadro: si toccano **i pixel azzurri che
la sovrastampa cambia**. E' una maschera piu' stretta dell'impronta del
livello e piu' sicura, perche' non puo' toccare quello che azzurro non e' - il
marchio e il bicchierino di latte, che rendendo in quadricromia
diventano neri, azzurri non sono mai. Sbagliare il bordo di qualche
millimetro non cambia il risultato.

**E l'azzurro da solo non riconosce niente.** Sul T6 aperto la
macchia azzurra piu' grande del foglio non e' un'ombra rotta: e' il FONDO del
pack, gocce d'acqua su azzurro, 15.800 px che vanno lasciati in pace. Per
questo lo strumento torna la banda **due volte, prima e dopo**, e chiede di
guardarle: se cambia un fondo, un marchio o una foto, il riquadro e' fuori
posto.

Misurato sul T6 aperto, che la colata in sovrastampa ce l'ha ma il livello no:

    banda indicata a occhio    187 x 58 mm
    zone azzurre               41.821
    rimesse dalla sovrastampa  24%     -> si sostituisce
    fondo azzurro del pack      0,1%   -> si rifiuta da solo

Il secondo numero e' la prova che il meccanismo si limita da se': puntandolo
sul fondo del pack, sotto soglia non fa niente.

#### Il foglio in cassa va buttato appena qualcuno se l'e' preso

La sostituzione della colata restituisce **un'immagine nuova**, e quella resa
da `render_page` resta in cassa: due fogli interi vivi insieme. Sul T6 aperto
sono 6516 x 3923 px, 76 MB, e il picco della costruzione passava da 351 a 456
MB - dentro il tetto di 512 del piano Free, ma per un margine che non vale la
pena di spendere.

`dieline.scarta_resa()` va chiamata **subito dopo la colata**, non dopo il
nero: `nero` la sua resa se la fa da se', fuori dalla cassa, quindi da li' in
giu' la cassa non serve a nessuno. Col foglio buttato al momento giusto la
colata costa **13 MB**, non 105.

#### Il caso calibrato

    T1 al mandarino       livello `Colata`, 120,5 x 36,3 mm
                          Ghostscript recupera lo 0,2% -> era la risorsa;
                          adesso l'ombra la simula la grafica
    T6 aperto             ombra in sovrastampa: recupera il 49,6% -> quadricromia

Il T6 aperto il livello `Colata` non ce l'ha, e per questo non lo prende: la
regola sulla preparazione del file - la colata su un livello suo - e' quella
che apre tutte e due le strade, non solo la sostituzione.

#### Tre difetti che solo questa cosa poteva far vedere

Ognuno dei tre e' passato indenne dal controllo precedente, ed e' per questo che
vanno scritti.

**La cassa delle rese RIDUCE invece di rifare.** `render_page` ne tiene una
sola e, se gliene chiedi una piu' piccola, te la ridimensiona. Una ridotta e una
nativa differiscono su **tutta** la pagina: l'impronta del livello veniva 1265 x
1389 px invece di 141 x 681, e l'allineamento finiva a 13 pixel. Le due rese da
confrontare vanno prodotte allo stesso modo, e qui si rendono a parte.

**Il bianco sul bianco non fa differenza.** L'impronta presa sul colore aveva
dei buchi esattamente dove la colata e' BIANCA - la cresta e le gocce - perche'
bianco su foglio bianco e' indistinguibile. Al loro posto restava il fondo, e
sul modello si vedeva una mezzaluna bianca sul rosso attorno alla goccia. Le due
rese si fanno su **fondo trasparente** e il confronto guarda anche l'alfa.

**Una funzione periodica non ha una fase sola.** Spostare la risorsa di un
periodo intero lascia le due curve sovrapposte, e una misura robusta come la
mediana non se ne accorge: l'allineamento tornava a 0,22 mm con la goccia a
mezzo pack di distanza, cioe' sparita. La fase la decide la **goccia**, che e'
l'unica cosa aperiodica del disegno: fra le fasi che distano un periodo si
sceglie quella che somiglia di piu' confrontando le IMMAGINI, dove la goccia
pesa poco in percentuale ma e' l'unica cosa che cambia.

#### La fila della fasciatura orizzontale puo' cominciare da un fianco

`detect_layout` riconosce la fasciatura orizzontale da quattro colonne che si
alternano larga-stretta, ma l'alternanza vale nei due versi: `W D W D` e
`D W D W` passano tutte e due. `solve_carton_h` invece dava per scontato che la
prima delle quattro fosse larga, e chiamava fronte la colonna 0. Su un DT
disegnato `fianco | retro | fianco | fronte | patta` - la patta rastremata non
attraversa la fascia per il 96% e non entra fra le colonne, quindi la sola
quaterna trovata comincia dal fianco - il fronte era il fianco da 15,5 mm,
l'astuccio usciva 15,8 x 100,3 x 139,0 invece di 139,0 x 100,3 x 15,8, girato
col fianco verso chi guarda, e la scelta del fronte dall'aletta stampata
confrontava due fianchi senza aletta.

La regola: **fronte e retro sono sempre le due colonne larghe**. Se la prima
della quaterna e' piu' stretta della seconda il giro dei nomi parte dalla
seconda (`fronte, fianco destro, retro, fianco sinistro` restano in ordine
ciclico), e la scelta fra le due larghe con l'aletta stampata guarda quelle
due. La profondita' e' la media delle due strette, dovunque stiano.

Sul parco: 29 casi identici al byte, cambia solo il caso nuovo (DT che
comincia dal fianco), che adesso ha il fronte davanti, il retro dietro e le
quote giuste.

#### Il fronte curvo: cielo e fondo a D

Lo stesso astuccio, girato giusto, restava aperto sopra e sotto: le alette del
fronte sono lunghe 25,0 e 25,2 mm su una scatola profonda 15,8, e `flap`
accetta al massimo 1,3 volte la profondita'. Non erano alette sbagliate: chi
ha il pack in mano l'ha detto - "e' un mastello, il fronte curva per chiudere
il pack". Il fronte si incurva verso fuori, i fianchi restano piani, e cielo e
fondo sono a D: profondi quanto la scatola ai lati, di piu' in mezzo. Le
alette lo disegnano da sole: il loro taglio e' curvo, circa 15,5 mm ai capi e
25 in mezzo, e nessuna piega a D le divide.

La regola (`dieline._fronte_curvo`), solo quando nessuna aletta si trova
entro 1,3 volte la profondita': il fronte e' curvo se due misure indipendenti
tornano insieme -

- le alette alta e bassa del fronte sono lunghe uguali (entro il 10%), fra
  1,3 e 2,5 volte la profondita'; la **freccia** e' quello che avanza;
- il fronte e' piu' largo del retro di quanto un arco con quella freccia e'
  piu' lungo della sua corda, `8 f^2 / 3 c`, entro un millimetro.

Sul caso nuovo: freccia 25,1 - 15,75 = 9,4 mm, retro 138,0, arco previsto 139,7,
fronte misurato 140,0. Un astuccio piatto ha fronte e retro uguali, e la
seconda prova lo esclude anche con alette lunghe.

Il solido (`folding.curva_fronte`) e' la scatola di sempre deformata: ogni
punto avanza di `f * b(x) * (z + D/2) / D`, con `b(x) = 1 - (2x/W)^2`. Sul
retro e sui fianchi lo spostamento e' zero, sul fronte e' la freccia in
mezzo; la parabola e l'arco con la stessa freccia differiscono meno della
carta. Le facce toccate diventano maglie a 48 colonne, interno e coste
compresi. Le texture seguono la carta:

- lungo il fronte e lungo la piega di cielo e fondo la u va per lunghezza
  d'arco;
- su cielo e fondo, dalla piega col fronte si prende tanta aletta quanto il
  cielo e' profondo in quel punto: 15,8 mm ai lati, 25 in mezzo, cioe' dove
  la fustella la taglia.

`verifica.facce_astuccio` confronta cielo e fondo col pannello nel loro punto
piu' profondo, e una riga d'avviso dice il fronte curvo anche al controllo
dell'AI. Sul fronte curvo l'apertura a strappo non si apre ne' si incide (le
facce sono gia' maglie): oggi nessun astuccio del parco ha le due cose.

Sul parco: 29 casi identici al byte; cambia solo il caso nuovo, che adesso e'
chiuso sopra e sotto, col logo dell'aletta dritto sul cielo e il fronte curvo
con i biscotti davanti.

### La texture e' lo steso

L'astuccio non ha piu' un'immagine per faccia: la sua texture e' lo steso del
PDF, come per tutte le famiglie (*La texture e' lo steso*). Lo steso si
ritaglia dallo stesso foglio da cui escono le facce (`texture_astuccio`,
`steso`): il riquadro del DT con un millimetro attorno, pixel per pixel come
le facce. Ogni faccia stampata ci arriva dal suo pannello (`steso.
facce_sullo_steso`): la sua UV passa per il giro della sua immagine
(`girate`), per il riquadro del pannello sul foglio e per il giro del foglio
(`gradi`), e lo steso torna nel verso del PDF. Ogni faccia tiene il suo
materiale, col suo nome; l'interno, il taglio e il solco sono colori pieni.

- **Il riscontro**: per ogni faccia, 400 pixel presi a caso devono essere
  quelli dello steso nel suo telaio (`steso.riscontro`); se una faccia non
  torna, il build lo scrive con «STESO». Sul parco tornano tutte.
- **Il rilievo** e' una mappa delle normali sullo steso (`rilievo.
  mappa_dello_steso`): si gira l'altezza, poi si fanno le normali, perche' i
  vettori di una mappa girata starebbero nel telaio di prima.
- **La risoluzione** e' quella delle facce: lo steso esce dallo stesso foglio
  a 300 dpi, entro gli 8192 px di lato.

## Finestre e rilievi

Due cose che il PDF dice solo in parte, e che sul modello si vedono: la
pellicola sulle finestre, che il file di solito non disegna, e il rilievo
dell'embossing, che il file disegna su una lastra sua ma che non e' un
inchiostro.

### La pellicola delle finestre si chiede, ogni volta

Un pack con la finestra di solito ha una **pellicola**: una lastra di plastica
trasparente sottilissima, PET o OPP, incollata dall'interno e piu' grande
della finestra. Non sempre, e il DT non lo dice. Per questo **si chiede a
chi carica il PDF, ogni volta che l'analisi trova una finestra**: la pagina
mostra la domanda (con la pellicola, o finestra aperta) prima di costruire,
come per l'apertura a strappo, e la risposta arriva alla costruzione come
opzione `pellicola` (1 o 0). Va in coda col caso, e la routine lo ricostruisce
con la stessa scelta (`OPZIONI_CASO`). Senza opzione - chi chiama l'API e non
lo dice - le finestre restano aperte, come sono sempre state.

Le finestre che l'analisi conosce:

- sul **ballotin** i buchi dei pannelli e quelli che girano lo spigolo fra un
  pannello e il suo coperchio (`ballotin.finestre`);
- sull'**astuccio aperto** il retro fra le due falde, la finestra del
  T6 aperto (`finestra_astuccio`). Un astuccio senza retro, tipo vassoio, non
  ha una finestra: e' aperto. L'apertura a strappo non e' una finestra: e'
  una porta che si apre, e ha la sua domanda.

La pellicola sul modello:

- e' **incollata al rovescio**, uno spessore di cartoncino piu' in dentro della
  faccia piu' cinque centesimi (il suo spessore), cosi' non si confonde col
  rovescio. Da fuori la si vede nella finestra, un poco incassata come sul
  pack vero;
- **va oltre il bordo**: sul ballotin il guscio convesso della finestra
  allargato di 5 mm, tagliato dove esce dalla sua faccia; sull'astuccio tutta
  la larghezza del retro, meno lo spessore dei fianchi, e 8 mm sotto ogni
  falda (mai oltre i quattro quinti della falda);
- una finestra che **gira lo spigolo** fra parete e coperchio ha la pellicola
  piegata con lei: una parte sotto la parete, una sotto il coperchio, e fra
  le due una striscia lungo la cordonatura;
- nel GLB e' un **nodo suo**, `pellicola`, con un materiale suo: trasparente
  (BLEND, 22% di copertura), a due facce, liscio (ruvidita' 0,05), bianco
  appena azzurro. Provati in model-viewer sul ballotin: al 16% non si vedeva,
  al 40% la finestra era lattiginosa. Niente `KHR_materials_transmission`, che
  sarebbe il vetro vero: un viewer che non la conosce mostrerebbe un foglio
  bianco opaco;
- il **controllo dell'AI non la guarda**: `vista.leggi_glb` salta i materiali
  trasparenti. Il suo rasterizzatore li dipingerebbe opachi, e il controllo
  guarda la grafica e la forma, che con la pellicola sono quelle di prima.

### Il rilievo dell'embossing

Un rilievo non e' un inchiostro: e' il cartoncino spinto in fuori
(embossing) o in dentro (debossing) da una matrice a secco, quasi sempre a
registro con la grafica. Il file lo dice con una **tinta piatta che si
chiama come la lavorazione** - sul ballotin `Embossing`, su un
livello con lo stesso nome - e la riconosce `rilievo.segno` dal nome:
emboss, rilievo, goffratura, Pragung, gaufrage, relieve; deboss, incavo e
Tiefpragung vanno in dentro.

- **Dalla texture la lastra va via**, come una vernice
  (`techink.RILIEVO_FRASI` fra le coperture): pdfium la dipingerebbe col
  colore di ripiego sopra i marchi. Sul ballotin stava gia' sul suo livello
  tecnico, spento, e la texture e' identica.
- **Sul modello il rilievo e' luce**: una mappa delle normali (la
  `normalTexture` di glTF) nel telaio della texture, che piega la normale
  lungo le spalle del rilievo come la piega la carta. La maglia resta
  quella: mezzo millimetro su una scatola di dieci centimetri non cambia la
  sagoma, cambia come la luce scivola sul marchio. E la mappa la leggono
  tutti i viewer, senza estensioni.
- **La forma viene dalla lastra**, letta da Ghostscript (`tiffsep`) sul file
  originale, non su quello pulito: dove l'inchiostro e' pieno il cartoncino
  sta 0,5 mm sopra il piano (sotto per un debossing), con la spalla morbida
  di una gaussiana larga 0,2 mm. Provati accanto allo stesso modello senza
  mappa: con 0,35 e 0,25 il marchio in rilievo quasi non si distingueva da
  quello piatto; con 0,5 e 0,2 le lettere hanno il bordo alto in luce e
  quello basso in ombra.
- **La risoluzione** e' 150 dpi, sei pixel per mm, anche quando la texture
  ne ha dodici: bastano a una spalla di mezzo millimetro, e Ghostscript sul
  foglio del ballotin ci mette tre secondi invece di undici. La mappa ha la
  sua misura: le UV sono le stesse, il viewer la stira da se'.
- **Il verso** e' quello di glTF: rosso +X a destra, verde +Y in alto
  nell'immagine. Il GLB non ha le tangenti, e i viewer le ricavano: provato
  con una lastra di prova - un disco in rilievo e uno in incavo - in
  model-viewer e nel viewer della pagina, che con l'origine UV in alto gira
  il verde (`normalScale` (1, -1)), come fa GLTFLoader.
- **Sugli astucci** la mappa e' una sola, sullo steso, come la texture
  (*Astucci*, *La texture e' lo steso*): l'altezza si prende sul riquadro
  dello steso, si gira nel verso del PDF e solo dopo si fanno le normali -
  girare una mappa delle normali vorrebbe dire girarne anche i vettori
  (`rilievo.mappa_dello_steso`). Provato su una copia dell'astuccio T8 con la tinta
  arancio del marchio rinominata `Embossing`: le lettere arancio spariscono dalla
  texture e restano in rilievo bianco, al loro posto, sul fronte e sul cielo.
- **Il controllo dell'AI non lo vede**: il suo rasterizzatore non legge le
  normali. Guarda la grafica, che e' quella di prima.

Il rilievo lo fanno il ballotin e l'astuccio. Flowpack, vassoi, pouch e coppe
non lo fanno ancora: il parco non ha un file che lo chieda, e il primo che
arriva dice come. Il parco ha un solo file con la lastra di rilievo, il
ballotin; sugli altri la mappa non c'e' e il GLB e' identico al byte.
