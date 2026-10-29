# Regole: Vassoi, display con plancia, display a scatola

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Vassoi espositori

La terza famiglia: un **fondo** rettangolare con una parete attaccata a
ciascuno dei suoi quattro lati, e le alette agli angoli che tengono su le
pareti.

Si riconosce dalla griglia della fustella, e non per euristica: **cinque
colonne e tre fasce**, con le due colonne sottili fra fondo e pareti che sono
la cordonatura. Sul display T1x40:

    colonne (mm)   98,6 | 2,0 | 145,5 | 2,0 | 98,5
    fasce   (mm)   40,0 | 385,9 | 40,5

cioe' fondo **145,5 x 385,4**, fianchi lunghi alti **98,5 e 98,7**, pareti
corte **40,5 e 40,6**.

**Le quattro pareti non sono alte uguali, ed e' normale.** Su un display da
scaffale i fianchi lunghi reggono la pila e la parete davanti e' bassa perche'
il prodotto si deve vedere. Il build lo dichiara invece di sospettare un
errore.

**Le alette angolari sono dei laterali, non delle testate.** Piegano di 90
gradi rispetto al laterale, e quando il laterale a sua volta piega di 90
rispetto alla base si ritrovano in posizione frontale e posteriore: sono lo
strato interno del fronte e del retro, che poi ci si chiudono sopra e le
incollano — le macchie tratteggiate che il DT disegna agli angoli sono proprio
quegli incollaggi. E' il modo in cui un vassoio sta in piedi, e sbagliarlo vuol
dire costruire quattro pareti che non si tengono.

### Le testate del vassoio

Le testate sono **fronte e retro**, le due pareti sulle fasce nord e sud della
griglia; le colonne sono i laterali. Valgono le regole di tutte le famiglie:

- **le misure dal DT.** Fondo e pareti si leggono dalla griglia della
  fustella, e la sagoma - che viene dall'impronta di stampa, vedi sotto - non
  va mai oltre la fustella: un'ombra o una sbavatura fuori dal taglio non e'
  cartoncino (`sagoma_e_creste`);
- **il fronte e' la testata piu' bassa**, perche' su un espositore il davanti
  lascia vedere il prodotto e il dietro, se e' piu' alto, regge il cartello
  (`vassoio.testata_davanti`). Se la bassa e' la sud il vassoio si gira di
  mezzo giro, e lo si dice. Con le due testate alte uguali entro 2 mm - il
  display T1x40, 40,5 e 40,6 - davanti resta la nord;
- **le verifiche**: ogni parete sulla sua fascia del DT e il fronte sul
  fronte (`verifica.vassoio`), e le quote scritte (`quote.riscontro_vassoio`).
  Sul display T1x40 le pareti cadono sulle loro fasce entro 0,3 mm; le quote
  sono vettorializzate e non si leggono come testo, e lo si dice.

### Il contorno non e' un rettangolo, e il DT lo dice

La prima versione del vassoio faceva quattro rettangoli dalla griglia. Era
"completamente sbagliato" a vederlo, perche' il contorno di un display e'
sagomato: sul display T1x40 i fianchi rientrano a meta' altezza e gli angoli
sporgono. Il DT sul foglio porta le quote — **346,5 x 466,5**, colonne
98,5 | 149,5 | 98,5 e fasce 40,0 | 386,5 | 40,0 — e il contorno va preso da
li', non inventato dalla griglia.

**Le cordonature orizzontali non stanno tutte alla stessa quota**: sul
display T1x40 quella della colonna di mezzo sta a 148,3 e quelle delle colonne
laterali a 149,2, nove decimi piu' in basso. Non e' un errore del file, e' il
compenso dello spessore del cartoncino.

### Il foglio si riconosce da dove sta, non da quanto inchiostro ha

La sagoma della cartotecnica si prende dall'**impronta di stampa**, perche' la
penna della fustella ha interruzioni — sul display T1x40 da 3 mm — e
riempiendo il tracciato si prende solo la colonna centrale. Ma "impronta di
stampa" non vuol dire "dove c'e' inchiostro".

Attorno a quel display il file ha un'**ombra sfumata**: un abbellimento della
presentazione, che in macchina non ci va. Scende da 253 a 170 su quattro
millimetri e mezzo, quindi qualunque soglia sull'inchiostro se la prende tutta.
La cartotecnica usciva 4,5 mm piu' larga del vero, e quella fascia — che sulla
texture pulita e' foglio bianco — finiva stesa sul bordo dei fianchi. E' il
difetto che si vedeva come **"bianco sui laterali"**.

Il foglio si riconosce invece da DOVE STA: e' il chiaro che si raggiunge
partendo dal bordo della pagina. Un chiaro circondato dalla grafica — il bianco
dentro le lettere del marchio, un pannello chiaro in mezzo — non si raggiunge e
resta cartoncino, e non serve piu' tapparlo a posteriori con `fill_holes`. E il
tratto della fustella, che e' colorato, ferma la macchia da solo: dove la penna
c'e', anche un cartoncino stampato chiaro fino al taglio si salva.

**Il controllo che lo dice**: la misura dell'impronta va confrontata con il
riquadro della fustella, che viene dai vettori. Se ballano di piu' di 2 mm il
build lo scrive, invece di consegnare un modello piu' grande del pack.

### Una texture sola, e uno specchio solo

Lo steso intero e' **una** texture, con in fondo due righe di colore piatto per
l'interno e per il taglio; le UV sono la posizione nel piano. Le due righe
servono alla costruzione: nel GLB finale il vassoio ha come texture il DT con
un millimetro attorno, e l'interno e il taglio sono colori pieni (*La texture
e' lo steso*). La piega sposta i
vertici e la grafica se li porta dietro, quindi non c'e' nessun ritaglio da
ruotare pannello per pannello.

**Piegando lo steso com'e', la stampa finisce dentro**: la faccia stampata
guardava in su e piegando in su va a guardare l'interno, e il marchio si legge
attraverso il cartone. Ci vuole uno specchio per rimetterla fuori, e **uno
solo**: con due — x e z — e' una rotazione, e torna specchiata.

**Le UV dell'interno e del taglio si misurano sulla TEXTURE, non sulla
sagoma.** Sono due griglie diverse: sul display T1x40 la sagoma sta a 4 px/mm
e la texture a 2,4. Prendendo l'altezza della sagoma la riga dell'interno
cascava su quella del taglio, e tutto il dentro del vassoio usciva del colore
sbagliato.

### Il verso dell'avvolgimento si misura, non si indovina

Un visualizzatore glTF scarta le facce che guardano dall'altra parte
(`doubleSided` non c'e', quindi vale il default). Se un pezzo esce avvolto al
contrario, da fuori si vede la **faccia interna** — il cartoncino — e la stampa
resta nascosta: il fronte e il retro uscivano bianchi mentre i fianchi erano
giusti, perche' sono gli unici due pezzi presi *per colonne*, dove la riga
corre in X e il tratto in Y, e la normale esce rovesciata.

Non si aggiusta a mano pezzo per pezzo: la faccia esterna deve guardare dalla
parte opposta al dentro, e il piano lo dice da solo — basta chiedere alla
mappatura dove vanno un passo in X e uno in Y, e girare i triangoli quando la
normale punta dentro.

**E non si vede rendendo in casa**: il rasterizzatore di `raster.py` non fa
culling, quindi sulle sei viste il modello sembrava giusto. Per accorgersene
bisogna scartare le facce voltate, come fa il visualizzatore vero.

### Il cartoncino fra due righe e' quello che hanno in comune

Prendendo il primo e l'ultimo pixel pieno di ogni riga, all'altezza
dell'angolo il fianco ha **due** tratti — il pezzo dell'aletta e quello della
parete, separati da foglio — e la striscia faceva ponte stendendoci sopra il
bianco. Quindi i tratti si tengono uno per uno.

Il primo rimedio era: due righe si cuciono solo se hanno **lo stesso numero**
di tratti. Sbagliato, e si vedeva. Sul fronte del display la sagoma si apre —
l'aletta si stacca dalla parete — il conto cambia, e quella regola lasciava li'
una colonna scucita larga un pixel: un quarto di millimetro, che nel modello
era una **feritoia in mezzo all'aletta del fronte**. Quattro, contando anche i
bordi esterni.

La regola giusta non guarda i conti, guarda la superficie: il cartoncino fra
due righe vicine c'e' **dove c'e' su tutte e due**. Si prende
l'**intersezione**, si spezza nei suoi tratti, e ognuno diventa una fascia.
Cosi' il pezzo resta uno anche dove la sagoma si apre o si chiude, e il ponte
non torna, perche' fra due tratti il cartoncino non c'e' su nessuna delle due
righe.

**Il capo di una fascia non e' sempre un taglio.** Dove la fascia finisce solo
perche' l'altra riga e' piu' corta, il cartoncino continua: metterci la costa
vorrebbe dire disegnare una riga di spessore in mezzo al pezzo. La costa va
solo dove fuori non c'e' cartoncino su nessuna delle due righe — e comunque
mai su una cordonatura, dove il cartoncino continua nel pezzo accanto.

**Le fasce che non cambiano si stendono in una sola.** Sulla base e su buona
parte delle pareti il tratto e' lo stesso per centinaia di righe, e farne un
quad per riga e' geometria pagata per niente: il display T1x40 passa da
55.588 vertici a **24.736** e da 2,47 a 1,13 MB. Si uniscono solo se il tratto
e i capi coincidono, quindi la superficie e' la stessa — verificato al pixel,
zero differenze su 5,8 milioni di pixel resi da sette angolazioni.

### Un blocco unico, senza feritoie

**Vassoi e display si costruiscono come UN BLOCCO solo: fondo, pareti e alette
si toccano dappertutto, e fra una parte e l'altra non resta nessuno spazio
vuoto. Le plance sono l'eccezione: sono elementi a se', e restano separate**
(vedi *La plancia e' un elemento a se'*).

Il cartoncino piegato non ha fessure: fra il fondo e una parete c'e' la
cordonatura, e il cartone continua; agli spigoli le pareti si incontrano e si
incollano. Nel modello, invece, anche un quarto di millimetro di vuoto da
vicino si vede — una riga di luce lungo una piega, uno spigolo aperto, il vuoto
fra la faccia stampata e quella interna — ed e' un difetto che il pack vero non
ha. Da dove venivano:

| la feritoia | dove | perche' |
|---|---|---|
| fra il fondo e le pareti, lungo tutta la piega, un quarto di millimetro | display T1x40, display T1x48 | ogni pezzo messo al suo posto sulla griglia di pixel, e non sulla sua piega |
| su ogni spigolo, un millimetro e mezzo | display T1x48 | i fianchi sono 3 mm piu' corti del fondo — lo spessore, che il DT compensa — e finivano prima dello spigolo |
| fra la faccia esterna e quella interna | tutti | la costa solo sui capi delle fasce: le teste dei fianchi e i lati del fronte restavano aperti |
| due righe a trattini sul retro, dentro | display T1x48 | le alette mezzo millimetro fuori dalla parete, coi bordi a vista |

Come si costruisce il blocco (`vassoio.corpo`, lo stesso per il vassoio e per
il display):

1. **ogni pezzo si ancora alla sua cordonatura**: il suo bordo sulla piega va
   esattamente sulla piega. E il bordo e' fin dove arriva davvero la sua maglia
   (`vassoio._ingombro`), non l'ingombro dei pixel: un pixel isolato sul
   contorno — l'antialias di un angolo — allarga i pixel ma non la maglia.
   Ancorato ai pixel, il fianco ovest del display T1x40 usciva un quarto di millimetro
   piu' basso del DT, e sul fondo lo stesso quarto e' una feritoia;
2. **fianchi, fronte e retro si stirano fino agli spigoli**: la loro faccia
   esterna arriva sulla faccia esterna della parete accanto, e la pelle del
   blocco e' continua. Sul display T1x48 la grafica dei fianchi si allunga dell'1,5%,
   che non si vede;
3. **la faccia interna rientra di uno spessore** dove il pezzo incontra gli
   altri: agli spigoli le coste si incontrano a 45 gradi e il bordo alto gira
   l'angolo chiuso;
4. **la costa va su ogni taglio** — anche sui lati che corrono nel verso delle
   fasce — e **mai su una cordonatura**, dove il cartone continua nel pezzo
   accanto (`Maglia.pezzo`);
5. **le alette stanno dentro lo spessore** della parete a cui sono incollate:
   la faccia esterna mezzo spessore dietro quella della parete, l'interna sul
   suo piano interno, e dove c'e' la parete non si vedono. Dove la parete e'
   piu' bassa — il fronte del display T1x40 — l'aletta sporge sopra ed e' un pannello a
   se', chiuso dalle sue coste: la riga chiara sopra il fronte basso del display T1x40 e'
   la costa del cartone, e c'e' anche sul pack vero;
6. **le misure sono quelle del DT, non dei pixel**: il fondo e l'altezza di
   ogni parete si stirano sulle quote del disegno, dalla piega al bordo. Sul
   vassoio le pieghe delle colonne stanno a META' della cordonatura, come la
   maglia (`vassoio.misure_blocco`): le fasce della griglia danno un fondo di
   145,5 mm, e fra le due meta' ce ne sono 147,5. Cosi' il blocco esce uguale
   comunque stia il foglio sulla tavola: sul display T1x48, preso dai pixel, la cima
   della plancia che sta sul retro ballava di mezzo millimetro fra un verso e
   l'altro, 215,9 contro 216,5.

**Di traverso alle fasce una riga di pixel si prende al suo centro**, lungo la
fascia da bordo a bordo (`dove` in `Maglia.pezzo`). Presa sul bordo alto, di
traverso l'ultima riga si perdeva, e sempre dalla stessa parte del foglio: con
le misure del DT il pezzo arriva comunque dove deve, ma girato il foglio di
mezzo giro la grafica ci scivolava sopra, fino a un pixel.

Nel GLB il blocco e' **un nodo solo**, `vassoio` o `display`; la plancia e' un
nodo a parte, `plancia`, sugli stessi vertici e sulla stessa texture
(`exporters.write_glb_mesh` con `parti`).

**Il visore della pagina legge TUTTE le mesh del GLB.** Leggeva solo la
prima: il display nello Space usciva senza la plancia, e la coppa senza il
tappo, mentre il file scaricato li aveva tutti e due. Un pezzo a parte si
controlla nel visore, non solo nel file.

**La verifica che lo dice**, a ogni costruzione (`verifica.blocco`): sulla
faccia stampata i fianchi coprono tutta la profondita' del fondo, fronte e
retro tutta la larghezza, e ogni parete scende fino al piano del fondo, entro
0,05 mm. Se no il build lo grida — "FERITOIA: la parete est non arriva allo
spigolo, mancano 1.50 mm". Sul display T1x40 e sul display T1x48: 0,00 mm, e il
blocco del display T1x48 e' lo stesso al centesimo nei quattro versi del foglio.

### Il vassoio sagomato: il fondo fra quattro cordonature

Il caso 838cbae0ac, un display da 36 pezzi per un riempimento, non si
costruiva: "dei due PDF nessuno si legge come vassoio espositore". La griglia
della fustella aveva 7 colonne e 8 fasce invece di 5 e 3, perche' le pareti
non sono rettangoli: i fianchi sono trapezi (51 mm al fronte, 76 al retro),
il fronte ha un incavo in mezzo (51 agli angoli, 41 al centro) e ogni capo
obliquo, ogni gradino aggiunge una riga. E le cordonature dei fianchi sono
7,6 mm, oltre i 6 di `CORDONATURA_MAX`: e' un ondulato, non un solid board.

La regola (`vassoio.riconosci_sagomato`): di un vassoio resta sempre il
**fondo**, la luce piu' larga della griglia nei due versi, chiusa su tutti e
quattro i lati da una **cordonatura** - due righe vicine, fino a 10 mm
(`CORDONATURA_LARGA`), larghe uguali entro un millimetro sui lati opposti. La
piega sta a meta' della cordonatura; ogni parete va dalla sua piega alla riga
piu' esterna, e la sua forma - obliqui, incavi, alette sagomate - la da' la
sagoma della stampa, come su ogni vassoio. Sul caso: fondo 150,4 x 247,0,
pareti 51,0 / 76,3 / 81,0 / 76,3. Il fronte resta la testata bassa.

- Si prova **per ultimo**, dichiarato vassoio (o riempimento): dopo la
  griglia stretta, la plancia, lo sportello e la scatola. I casi che quelli
  leggono non cambiano strada.
- Le cordonature servono **su tutti e quattro i lati**: senza, anche un
  flowpack ha una luce piu' larga delle altre, e nel riempimento tutti e due
  i PDF si leggevano come vassoio.
- La verifica delle pareti prende la prima e l'ultima riga della griglia,
  non la sesta e la quarta: sul sagomato le righe sono di piu'.
- **Nel riempimento perde con un vassoio letto prima**
  (`server.analisi_riempimento`). Le quattro cordonature non bastavano: il
  film del flowpack del display da 26 del parco ha un fondo chiuso da
  quattro coppie di righe, si leggeva come vassoio sagomato, e il
  riempimento, che si costruiva, si fermava su «tutti e due si leggono come
  vassoi». Se tutti e due i PDF si leggono come vassoio e uno solo e' letto
  prima del sagomato (griglia, plancia, sportello, scatola), il vassoio e'
  quello e l'altro e' il pack. Il display da 26 torna identico al byte a
  quello pubblicato; i tre vassoi del parco non cambiano.

## Display con plancia

La quarta famiglia, e sta accanto al vassoio: una scatola che arriva CHIUSA e
che, aperta, perde dei pezzi e diventa un espositore da banco, con uno dei
pezzi in piedi dietro al prodotto a fare da cartello. Quel pezzo e' la
**plancia**. Il caso e' il display T1x48, disegno CT4977 "Display con plancia per
T48" (`pack3d/plancia.py`).

Prima non si costruiva in nessun modo. Dichiarato "vassoio" o "display" la
griglia aveva cinque colonne e dieci fasce, e il vassoio ne vuole cinque e
tre. Senza dichiarazione usciva un **flowpack** - nastro 515 x passo 486 mm,
sezione 134 x 116,5 - cioe' un modello plausibile della famiglia sbagliata, il
difetto peggiore che questo progetto possa avere.

### Si riconosce dalla croce, non dalla grafica

Fondo, pareti e alette agli angoli sono quelle del vassoio, e si stendono con
la stessa maglia (`vassoio.Maglia`). In piu' c'e' un **coperchio** grande quanto
il fondo, attaccato al bordo di un fianco, e le falde che ci si incollano
sotto. Sul display T1x48, in mm:

    colonne   15 | 116 | 134 | 117 | 133      falda, fianco, fondo, fianco, coperchio
    fasce     25 | 116 | 204 | 116 | 25       falda, fronte, fondo, retro, falda

Il riconoscimento guarda la griglia e basta, come quello del vassoio, e non
stima niente:

- il **fondo** e' il rettangolo di cordonature con una parete su ogni lato: il
  bordo esterno di una parete e' la prima riga parallela che la attraversa
  TUTTA - il fondo della finestra e il riquadro della scadenza, che la
  attraversano a meta', non sono bordi;
- il **coperchio** e' il pannello oltre uno dei due fianchi largo quanto il
  fondo, fra il 90 e il 110% (sul display T1x48 133 contro 134). Oltre l'altro fianco
  c'e' la falda, 15 mm;
- la **doppia cordonatura** attraversa il coperchio: due righe che toccano
  tutti e due i suoi bordi, fra 3 e 20 mm l'una dall'altra;
- il **fronte** e' la parete con la **finestra**, cioe' con due lati lunghi che
  partono dal bordo alto. Deve essere una sola: con due o nessuna non si sa
  dove sta il davanti, e non si costruisce.

Le cordonature perforate il file le disegna A PEZZI: la cerniera del coperchio
e' 124 tratti da uno, due e tre millimetri, tutti di fila. Per la griglia e'
una riga sola, e cosi' si legge (`plancia._corse`).

Riconosciuto anche senza dichiarazione, e di traverso: l'analisi automatica il
foglio non lo gira - costerebbe un'estrazione per verso su ogni astuccio e ogni
flowpack - ma scambiare righe e colonne della griglia gia' letta non costa
niente (`plancia.di_traverso`). Su tutti gli altri file del parco e degli extra
il display non lo vede nessuno: zero falsi.

### Come si apre: lo dice il DT

Il file non ha un livello per le linee, e tagli, cordonature e perforazioni
sono tutti la stessa penna ciano. Letto sulla miniatura del DT, dove i colori
ci sono (rosso piega, nero taglio):

1. la **finestra** del fronte si strappa via: contorno perforato dal bordo
   alto, 89,5 x 75 mm, e in basso un mezzo tondo da 28 mm per metterci il dito;
2. il coperchio si stacca dal fianco e dalla falda del fianco opposto -
   cordonature perforate, a pezzi - e resta attaccato solo al **retro**, con la
   falda del retro incollata sotto: quella e' la cerniera;
3. si alza sul retro, e la parte che stava sul fronte si ripiega IN AVANTI
   sulla doppia cordonatura. Le due righe sono a 8,1 mm: la piega a 180 gradi
   di un cartone da 4 mm. Fra le due, un taglio a onda con i punti di tenuta
   stacca l'una dall'altra le due parti;
4. la parte davanti finisce davanti a quella dietro, con la stampa verso chi
   guarda, e il suo piede - 106,5 contro 86,4 mm, cioe' 20 mm in piu' - entra
   nella scatola davanti alla parete del retro e la blocca. La falda del fronte
   incollata al piede riempie gli 8 mm fra le due: 8,1 = due cartoni da 4.

### Perche' proprio questa piega

Perche' e' l'UNICA in cui tutte e due le facce si leggono dritte, e la grafica
del file e' fatta per lei.

La parte del coperchio sul fronte, sul foglio, sta a testa in giu', con le
barrette, il bicchiere e il marchio - il DT lo dice con le frecce "TEXT
ORIENTATION" - mentre quella sul retro sta dritta, col solo marchio. Ripiegata
cosi', la prima va dritta davanti e la seconda dritta dietro; e l'onda del
taglio, che sporge dalla parte davanti, diventa la CRESTA della plancia con la
stampa verso chi guarda. Ogni altra piega tradisce qualcosa:

| la piega | cosa non torna |
|---|---|
| alzato dal fronte | la plancia sta davanti al prodotto e lo copre |
| alzato dal retro, senza ripiegarlo | guarda il muro: un pannello alzato sul lato lontano mostra la faccia di sopra a chi sta DIETRO |
| alzato dal retro, ripiegato indietro | davanti il marchio va bene, ma sopra spunta il rovescio bianco dell'onda, 20 mm |
| alzato dal retro, buttando la parte davanti | si butta la parte con le barrette, il bicchiere e l'onda, e le due righe sono pieghe, non un taglio da strappare |

Una lezione da tenere: **un pannello che si alza ruotando sul lato lontano
mostra la faccia di sopra a chi sta dall'altra parte**, non a chi guarda. A
intuito sembra il contrario, e il primo ragionamento su questo file ha preso
proprio quella strada.

### I pezzi vengono dai tratti, non dall'impronta di stampa

Il vassoio prende la sagoma dall'impronta di stampa (vedi *Il foglio si
riconosce da dove sta*). Qui non si puo': le falde non sono stampate e
l'impronta non le vede, e i tagli che contano - la finestra, l'onda - stanno
in mezzo alla stampa, che ci passa sopra senza fermarsi.

Quindi si disegnano i tratti della fustella - linee, rettangoli e CURVE
spianate - e ogni zona chiusa fra un tratto e l'altro e' un pezzo di cartone;
quella che tocca il bordo e' il foglio attorno. I pixel del tratto vanno al
pezzo piu' vicino, cosi' due pezzi che si toccano non lasciano fessure
(`plancia.pezzi`). Tre cose da sapere:

- ogni cella tiene solo le zone che stanno PER LO PIU' dentro di lei. Tagliata
  sul rettangolo, l'aletta nord-est si prendeva il bordo destro di tutto il
  fronte, un pixel per 116 mm;
- della finestra si toglie la zona sotto il bordo alto, e con lei le zone che
  la toccano e ci stanno dentro: il mezzo tondo per il dito, che senza la
  finestra resterebbe appeso;
- **a pari distanza il pixel va alla zona piu' grande** (`plancia._al_piu_vicino`).
  La riga di mezzo di un tratto largo tre pixel e' a pari distanza dai due
  pezzi che divide, e la trasformata di distanza, a pari merito, sceglie sempre
  dalla stessa parte della griglia: col foglio capovolto quella riga passava al
  pezzo di fronte, e sul display T1x48 la cresta della plancia saliva di 0,28 mm. Si
  guarda anche la griglia capovolta, e dove le due scelte non coincidono vince
  la zona piu' grande, che e' la stessa in tutti e due i versi. Non la piu'
  piccola: provata, lasciava sul fianco della plancia i denti della
  perforazione della cerniera.

### La texture, sul solo riquadro della fustella

Lo steso e' uno, come nel vassoio, ma si rende sul riquadro della fustella e
non sulla pagina intera: la pagina del display T1x48 e' 940 x 800 mm e la fustella
515 x 486, e con lo stesso lato massimo la texture tiene quasi il doppio dei
punti per millimetro. Nel GLB finale lo steso e' il DT intero con un
millimetro attorno, anche oltre i pezzi della maglia (*La texture e' lo
steso*).

### La plancia e' un elemento a se'

Fondo, pareti e alette sono il blocco del vassoio (vedi *Un blocco unico,
senza feritoie*), col fronte senza la finestra. La plancia no: sta in piedi
sul retro ma non e' incollata al blocco, e nel GLB e' un nodo a parte,
`plancia`, accanto al nodo `display`.

Dentro, pero', e' un pezzo solo anche lei, senza feritoie: la parte dietro, il
dorso e la parte davanti si ancorano l'una all'altra sulle loro pieghe, come i
pezzi del blocco, e si stirano sulle loro lunghezze del DT
(`Plancia.parti_coperchio`) e sulla larghezza del coperchio. La piega della
parte davanti e' la riga dove lei e il dorso si toccano **piu' a lungo**: non
la sua ultima riga sopra il dorso, perche' fra le due pieghe l'onda tocca il
dorso anche lei, di sbieco. Ancorata li', la plancia scendeva di 8 mm, e la
cresta con lei.

### Le verifiche

`verifica.plancia`: le pareti sulle loro righe del DT, misurate sulle UV con la
scala vera della texture, e nessuna faccia specchiata, come nel vassoio; e in
piu' la plancia al suo posto - la faccia davanti che guarda davanti, quella
dietro che guarda dietro, la parete con la finestra davanti, e la cima sopra il
retro. Se la piega fosse quella sbagliata e' qui che si vedrebbe. E
`verifica.blocco`, come nel vassoio: nessuna feritoia fra fondo e pareti.

Le quote del display T1x48 sono vettorializzate e non si leggono come testo, e il
riscontro lo dice (`quote.riscontro_plancia`). Lette a occhio sulla miniatura,
per verificare e non per costruire, tornano tutte: 515 = 15 + 116 + 134 + 117 +
133; 486 = 25 + 117,5 + 201 + 117,5 + 25, dove il DT misura fronte e retro
fino alla riga dei fianchi e non a quella del fondo; finestra 89,5 x 75; onda
larga 93; dal bordo del coperchio alla prima piega 94,5 = 86,4 + 8,1.

E i quattro versi sulla tavola danno lo stesso modello: il blocco uguale al
centesimo, 134,0 x 204,0 x 117,0 mm, e la plancia pure, con la punta dell'onda
entro 3 centesimi (216,16 contro 216,19). A 270 gradi la vista davanti e'
uguale pixel per pixel; a 90 e a 180 cambiano solo i contorni della grafica,
perche' la texture si rende dal foglio girato e i suoi pixel cadono altrove, di
meno di un pixel della texture - come prima del blocco unico.

Col foglio capovolto, fra la plancia e il retro si vede una riga chiara di un
pixel della texture: il bordo di taglio della parte dietro campiona il pixel di
confine fra la stampa e la carta. Non e' una feritoia - con i pezzi a colori
piatti la giunta e' chiusa - e sta fra due elementi separati, dove sul display
vero la giunta c'e'; c'era gia' prima. Se su un file si vedesse nel verso
giusto, il rimedio e' allargare la stampa oltre il taglio nella texture, come
si fa ai bordi delle isole UV.

### Il coperchio sul retro

Il secondo display con plancia del parco arriva da un altro studio di
fustelle, ed e' montato in un altro modo: un display da banco "ready to
display" per tre file di trenta pezzi. Dichiarato "vassoio" si fermava con un
errore -
dieci colonne e quattro fasce - e dichiarato cartotecnico usciva una scatola
chiusa sbagliata, col pannello del coperchio stirato a fare da fronte.

E' un vassoio col fronte basso, e il coperchio e' incernierato sul bordo alto
del **retro**: sul foglio continua il retro, oltre la sua riga esterna. In mm,
col foglio girato di un quarto:

    colonne   103,5 | 174 | 103,5              fianco, fondo, fianco
    fasce     65 | 215 | 104 | 99 | 113        fronte, fondo, retro, coperchio

Lo attraversa UNA riga, parallela alla cerniera: un mezzo taglio, non la
doppia cordonatura del display T1x48. Oltre la riga c'e' la parte con la grafica
grande; una sua linguetta, 114 mm di larghezza, entra per 41 mm nella parte
attaccata al retro e se ne stacca su un contorno perforato.

Come sta a display montato dal DT non si capiva con certezza, e l'ha detto
chi lo monta (issue #3 dei casi): il coperchio ruota di 90 gradi sulla
cerniera e la parte da 99 diventa il prolungamento del retro, con la stampa
verso dietro - solo il fondo colore; la parte da 113 si ripiega di 180 gradi
in avanti sulla riga e le scende davanti, con la stampa verso chi guarda; la
linguetta spunta sopra la riga come cresta, col marchio, e il piede entra 14
mm nella scatola davanti al retro (99 + 104 - 113 = 90). E' la plancia del
display T1x48 con il dorso largo uno spessore e la cerniera sul retro, e la grafica
lo conferma: sul foglio la parte da 113 ha l'alto verso la riga, e ripiegata
cosi' va dritta.

La regola (`plancia._sul_retro`), per questa famiglia e non per il file:

- il fondo e le pareti come per il display T1x48, ma il bordo di un **fianco** basta
  che ne copra il 75%: gli angoli dei fianchi sono stondati, e la riga dritta
  qui e' l'83% del fondo. Il fianco finisce sulla riga della sua aletta, 2 mm
  dentro il fondo, come sul display T1x48 finiva 1,5 mm dentro (`_fine_fianco`);
- il **coperchio** sta oltre UNA sola delle due testate, lungo quanto il fondo
  fra il 90 e il 110% (212 contro 215) e largo quanto lui: quella testata e'
  il retro, l'altra il fronte;
- il fronte e' la testata **bassa**, al piu' l'80% del retro (65 contro 104):
  e' da li' che si prende il prodotto, e non ha una finestra da strappare;
- la riga che attraversa il coperchio e' UNA, e arriva ai due lati a meno di
  10 mm: fra la riga e il lato c'e' l'intaglio a V della piega. Due righe
  sono la doppia cordonatura del display T1x48, e il suo coperchio sta sul fianco.

Il display T1x48 non cade qui: oltre fronte e retro ha due falde da 25 mm, non un
coperchio, e girato di un quarto la sua plancia avrebbe due righe e le testate
alte uguali.

Le due parti del coperchio non si separano sui tratti cosi' come sono: il
contorno della linguetta e' perforato, e la punta ha i punti di tenuta da 2
mm. Si chiudono i tratti di 1,25 mm per lato, solo per dividere il coperchio
(`plancia._coperchio_sul_retro`): la parte davanti e' la zona oltre la riga,
con dentro la linguetta; la parte dietro e' il resto, col buco della
linguetta, che si vede solo da dietro.

Nella maglia (`plancia._plancia_sul_retro`) la parte dietro sta nel piano del
retro dalla sua cima in su, la parte davanti due spessori piu' avanti - le
due facce interne si toccano - e la cima di ognuna e' un taglio con la sua
costa, non una piega: le due parti stanno su due piani. In larghezza il
coperchio sta dove sta sul foglio rispetto al fondo, perche' continua il
retro.

Sul parco cambia solo questo caso: prima si fermava, ora il display e' 174 x
215 x 244 mm - retro 104, plancia 99 sopra, linguetta 41 sopra la plancia -
con le pareti sulle loro righe entro 0,3 mm, la plancia che guarda davanti e
nessuna feritoia. Il fronte resta intero: il DT ci disegna una V perforata
dal bordo alto al mezzo tondo da 12 mm, ma il montaggio confermato non la
strappa, e il modello non la toglie.

### La plancia dentro il coperchio

Il caso e1b3cc77a7, un display per dieci flowpack (`pack3d/sportello.py`).
Arriva come una scatola chiusa bassa - coperchio stampato, quattro pareti,
fondo bianco - e si apre da uno **sportello perforato tutto dentro il
coperchio**: il lato dritto sulla cordonatura del retro, che fa da cerniera,
i fianchi lungo i fianchi del coperchio a 1,8 mm da loro, gli angoli
smussati, e davanti una linguetta che sconfina nella parete del fronte,
l'attacco per il dito. Una riga lo attraversa a meta'. Non e' la plancia del
display T1x48 ne' quella sul retro: li' il coperchio e' un pannello oltre una
parete, e si stacca intero; qui il coperchio resta e la plancia e' un pezzo
ritagliato dentro di lui.

**Come si apre**, confermato da chi l'ha caricato («la meta' con la scritta
dritta si alza, piegata sulla riga di mezzo»): lo sportello si alza sulla
cerniera del retro, e la meta' davanti si ripiega sulla riga verso chi
guarda. La plancia sta in piedi sul retro, alta mezzo sportello (55,6 mm),
con la meta' davanti stampata verso chi guarda - la scritta che sul foglio
e' dritta resta dritta - e la meta' dietro verso il retro, dove la scritta
che sul foglio e' capovolta si legge dritta. La linguetta finisce dentro la
scatola, dietro il prodotto. Del coperchio resta la cornice: gli angoli
fuori dallo sportello e le strisce lungo i fianchi.

**La firma** (`sportello.riconosci`), tutte, nel verso col retro in alto -
`riconosci_sulla_tavola` gira il foglio di un quarto, mezzo e tre quarti:

- il coperchio, un rettangolo di righe di almeno 40 mm, con una parete su
  ogni lato;
- il fondo, un pannello largo 0,9-1,1 il coperchio, chiuso in testa da due
  righe sulle righe del coperchio, oltre la parete di UN fianco solo, a non
  piu' di 0,75 della larghezza del coperchio. Le righe non sono per forza di
  fila: dentro il fondo del caso c'e' il riquadro della colla, e la
  cordonatura in mezzo alla parete est piu' il riquadro facevano un «fondo»
  largo 81,2 mm, piu' giusto di quello vero (80,6). Per questo il pannello
  deve essere chiuso in testa, e fra i lati liberi possibili vince quello
  che fa il fondo piu' simile al coperchio;
- la riga di mezzo, una sola, fra il 35 e il 65 per cento della lunghezza,
  lunga 0,9 della larghezza;
- i fianchi dello sportello, due righe a meno di 5 mm dai fianchi del
  coperchio, lunghe almeno meta' del coperchio, attraverso la riga;
- il fronte: tratti dentro la parete sud, lontani 2 mm dai bordi e nel 60
  per cento di mezzo (la linguetta); la parete nord non ne ha.

Si prova solo dichiarato vassoio, e solo dopo il vassoio e la plancia:
`build_vassoio` e `_prova_vassoio` ci arrivano quando gli altri due hanno
rifiutato il foglio.

**Il solido** (`sportello.mesh`, costruito da `build_plancia` con
`forma=sportello`: stessa texture, stessi due nodi `display` e `plancia`).
L'altezza della scatola e' la **mediana** delle quattro pareti: sul caso
ovest 26,8, nord 26,1, sud 26,2 e est 32,9 - la parete est porta una
cordonatura in piu' a meta' - e la scatola e' alta 26,5; ogni parete si
stende su quell'altezza, e una che ne differisce di piu' di 1,5 mm si dice
negli avvisi. Il fondo sta a Y = 0, girato sotto dal fianco del suo lato. Le
alette, le falde incollate e la linguetta di chiusura stanno dentro la
scatola chiusa e non si stendono.

**I pezzi** vengono dai tratti, come nella plancia, ma le pareti e il fondo
sono il cartone nei **riquadri della griglia**, non zone intere: le
cordonature si fermano a mezzo millimetro dagli angoli, e il fianco est, il
fondo e le sue falde erano una zona sola. Anche lo sportello si taglia
sulla griglia - fra i suoi fianchi, e diviso dalla riga - perche' la
striscia fra il fianco del coperchio e quello dello sportello si attaccava
alle sue zone dove i tratti non si chiudono.

**Cosa manca**: le alette dentro la scatola; la cornice del coperchio sta
dove stanno i pack piu' alti delle pareti (il caso: 33 mm su 26,5), che la
attraversano.

## Il display a scatola

La stessa forma della *plancia dentro il coperchio* qui sopra, disegnata
come fustella in CAD: una scatola che arriva chiusa e che **resta chiusa**. Nel
coperchio due fessure lungo i fianchi e la cima sul fronte staccano un
pannello attaccato solo a una cordonatura tratteggiata verso il retro: si
alza sulla cerniera, si piega a meta' e fa la plancia; nel coperchio resta la
finestra da cui si vede il prodotto. Il caso e' c5b98dfbee, un display T15
con quindici flowpack, dichiarato *Riempimenti* (`pack3d/scatola_plancia.py`,
`server.build_scatola_plancia`).

Prima non si costruiva: ne' vassoio (la griglia ha 9 colonne e 16 fasce) ne'
display con plancia (non c'e' un coperchio che diventa plancia: il coperchio
resta), e il riempimento si fermava con «dei due PDF nessuno si legge come
vassoio espositore». Lo sportello (`pack3d.sportello`) non lo vede: cerca i
fianchi dello sportello a pochi mm da quelli del coperchio e la linguetta
dentro il fronte sulla griglia, e qui le fessure stanno a 23 mm dai fianchi
e la griglia della fustella CAD ha 16 fasce. I due moduli si provano uno
dopo l'altro, prima lo sportello. Non e' una famiglia nuova: e' un cartotecnico, un
modulo nuovo dentro il display.

### La firma in fustella

Si legge dai tratti della penna della fustella (`ballotin.tratti_fustella`),
righe orizzontali e verticali unite in corse (pezzi a meno di 4 mm: la
cerniera tratteggiata e' una corsa sola di 25 pezzi). Nel telaio di lettura il
fronte sta in alto; il foglio si prova nei quattro versi sulla tavola, e la
firma non dipende da dove sta "su" nel PDF. Devono tornare tutte:

- il **bordo dietro del coperchio** e' una riga sola da un fianco all'altro
  (sul T15 334 mm = 71,5 + 191 + 71,5). Quello davanti no: le fessure della
  plancia lo interrompono, e il suo posto lo danno i fianchi;
- i **fianchi**: il bordo fuori e la piega, tutti e due dal bordo davanti al
  bordo dietro del coperchio, alla stessa distanza dai due lati: e' l'altezza
  della scatola (71,5);
- il **fronte**: una riga larga quanto il coperchio, fra l'85 e il 115%
  dell'altezza sopra il coperchio (72,5);
- il **fondo**: l'ultima riga intera della colonna oltre il retro, e la riga
  prima di lei lontana quanto il coperchio e' profondo, fra il 93 e il 105%
  (138 contro 139,5). Fra il coperchio e il fondo c'e' il retro con le sue
  falde incollate (98 mm sul T15); il modello ne usa l'altezza della scatola;
- la **plancia**: due coppie di fessure verticali dentro la colonna,
  simmetriche attorno al centro entro 3 mm e lunghe almeno il 40% del
  coperchio; la coppia interna e' il bordo della plancia (139 mm), quella
  esterna il bordo della finestra (145);
- la **cerniera**: una riga di almeno cinque tratti fra le fessure, verso il
  retro (a 20,2 mm dal bordo dietro);
- la **riga di mezzo**: una riga intera da fessura a fessura fra la cima della
  plancia e la cerniera (60 mm dalla cerniera, 65,6 dalla cima).

Le misure sono quelle quotate sul DT: 191, 139,5, 71,5, 105 = 32,5 + 72,5.

### Come si alza: la stampa lo dice

Un pannello che si alza ruotando sul lato lontano mostra la faccia di sopra a
chi sta **dietro** (la lezione del display T1x48, *Perche' proprio questa piega*). La
cerniera e' verso il retro, quindi alzata la plancia mostra la stampa al
retro, col fronte del foglio in alto. Sul DT la meta' verso la cerniera ha la
scritta dritta e quella verso il fronte la scritta capovolta, e la piega che
le fa leggere tutte e due e' una sola: la meta' verso la cerniera sta in
piedi, dritta per chi sta dietro; la meta' verso il fronte si ripiega **in
avanti** sulla riga di mezzo e scende davanti, dritta per chi guarda. E' la
piega del display T1x48. Il piede della parte davanti (5,7 mm piu' lunga, la parte
che stava nel fronte, con la linguetta per il dito) scende nella finestra,
dove non tocca niente. Alzata dietro, la parte davanti sarebbe entrata nel
coperchio dietro la cerniera.

### Il solido

Telaio della scatola: fronte +Z, cima +Y, fondo a Y = 0. Il foglio si guarda
dalla parte stampata col fronte in alto, quindi la destra di chi sta davanti
e' la sinistra del foglio: X = centro - u. Alla prima prova il fronte usciva
specchiato.

- coperchio a Y = H, attorno alla finestra: due strisce sui fianchi e quella
  dietro la cerniera;
- fronte giu' dal bordo davanti, la sua altezza sul foglio portata a H; se la
  plancia comincia nel fronte, li' il fronte ha la tacca;
- fianchi giu' dai lati del coperchio, retro giu' dal bordo dietro, fondo dal
  retro al fronte;
- la plancia: la parte dietro in piedi sulla cerniera, quella davanti due
  spessori piu' avanti, rovescio contro rovescio. Ogni pezzo ha il rovescio e
  i bordi liberi la costa (`ballotin.con_interno`).

Nel GLB la plancia e' il nodo `plancia`, coi suoi triangoli per ultimi,
accanto al nodo `display`: il riempimento misura il vano senza di lei (*I
riempimenti*, *Il display si misura senza la plancia*). Sul T15 il vano e'
189 x 137,5, alto 70,5: quindici flowpack sdraiati per il lungo, 5 x 3,
in piano (*I riempimenti*, *Il display e' fatto per
il suo numero*).

### Il fronte e' fustellato: segue i tagli della plancia

Il caso c5b98dfbee, seconda prova: «il fronte deve essere fustellato e non
dritto (guardare DT)». Sul DT il contorno della plancia non si ferma sul bordo
del coperchio: le fessure esterne salgono nel pannello del fronte (5,6 mm),
girano in una spalla tonda (raggio 9) e salgono in diagonale verso il centro
(da 16 a 23 mm dentro il fronte); al centro un arco largo 20 mm, la presa per
il dito, arriva a 32 mm. Parallelo, 3 mm piu' dentro, c'e' il contorno interno
della plancia, e sotto l'arco della presa un secondo arco (a 26 mm): la presa
e' un buco nel fronte, non una linguetta della plancia. Il modello faceva il
fronte dritto, alto quanto la scatola, e il pezzo dentro il contorno restava
li'.

**Regola.** Alzata la plancia, il pezzo di fronte dentro il contorno va via
con lei. Il bordo alto del fronte fra le fessure esterne si legge dai tratti
della fustella (`scatola_plancia._taglio`, nel campo `taglio`): a ogni u fra
le fessure (ogni 2 mm circa, e su ogni vertice dei tratti) il taglio piu'
lontano dal coperchio (v piu' piccola) fra quelli dentro il pannello del
fronte, a piu' di 1 mm dal bordo del coperchio (la cordonatura del bordo sta
a 0,5 mm e non conta). Cosi' passa il contorno esterno, e nella presa il suo
arco. Fuori dalle fessure esterne il fronte resta alto quanto la scatola; il
bordo tagliato ha la costa. Nessuna forma cucita: se la plancia comincia sul
bordo del coperchio non c'e' taglio e il fronte resta dritto; se la cima e'
una riga dritta dentro il fronte esce la tacca di prima. Sul T15: 226 punti,
il fronte alto 71,5 ai lati, 65 dove la fessura entra, 49 vicino al centro,
40 in fondo alla presa.

**I ponticelli non si leggono come taglio** (`scatola_plancia._senza_ponticelli`).
Un taglio a strappo e' interrotto da ponticelli, meno di un millimetro di
cartone che tiene la plancia finche' non la si strappa. Nel ponticello il
contorno esterno non c'e', e il taglio piu' lontano dal coperchio diventava
la riga dietro: sul T15 l'arco della presa ne ha due, a 6,5 mm dal centro,
larghi 0,7 mm, e li' il fronte risaliva da 29 a 24 mm dal bordo. Erano due
spuntoni sottili di cartone dentro la presa, «due linee sulla parte
fustellata del fronte». Una corsa di campioni piu' vicina al coperchio di
quelli che la chiudono di oltre 1 mm, su non piu' di 2 mm, e' un ponticello:
il bordo ci passa dritto. Sul T15 cambiano 4 campioni su 226, i due
ponticelli, e nient'altro.

La plancia resta un rettangolo fino alla cima delle fessure interne: la sua
parte nel fronte, con la stampa capovolta, scende davanti nella finestra.

### Dove entra

Solo dichiarato: nel vassoio dichiarato (e quindi nel riempimento), dopo il
vassoio, il display con plancia e lo sportello, quando hanno rifiutato tutti
(`server._prova_vassoio`, `build_vassoio`). I casi del parco che passavano non
cambiano strada.

### Cosa manca

- La cima della plancia segue il contorno interno sul DT (le spalle, e
  l'arco sopra la presa); nel modello la plancia e' un rettangolo fra le
  fessure interne, fino alla loro cima. Il fronte invece segue i tagli.
- Il retro e le sue falde incollate sono un pannello solo, alto quanto la
  scatola: sul T15 sono bianchi, dentro e fuori.
- Il display T10 dello stesso prodotto (caso e1b3cc77a7) e' disegnato
  diverso e passa dallo sportello: la firma di qui non lo vede, e va bene.
  Le due firme leggono la stessa forma da due disegni: se ne arriva un
  terzo, vale la pena di farne una sola.
