# Regole: Leggere il PDF

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Prima delle tre regole: una pagina, un DT

Prima di misurare qualunque cosa si sceglie **cosa** misurare. Vale per tutte
le famiglie.

**Solo la prima pagina.** Un PDF su piu' pagine e' quasi sempre lo stesso pack
ripetuto per lingua: il T2 di cialde ne ha due, `64-GERMANY` e `01-ITALY`,
identiche tranne il piede; il T1 ai cereali tre. Le altre pagine si
**tolgono dal file** all'ingresso di analisi e costruzione, per tutte le
famiglie (`artwork.pagina_unica`, che clona per tenere i livelli e ricorda la
copia, cosi' l'analisi in memoria si ritrova fra /api/analyze e /api/build).
Leggere sempre la pagina 0 non bastava: le altre restavano nel file, e chi lo
passava tutto a Ghostscript senza limiti le rendeva tutte - `colata.quadricromia`
le metteva nello stesso PNG. Il primo cartellino dice quante pagine aveva il
file (`server.avviso_pagine`), perche' chi l'ha caricato sappia quale e'
diventata il modello.

**Un DT solo: quello con la grafica, che di norma e' il piu' grosso.** Sulla
stessa pagina lo stesso disegno puo' tornare piu' volte: le copie per i
tecnicismi di stampa - supporto trasparente, alluminio, battuta di bianco,
aree coperte - la vista interna, e la miniatura nel cartiglio. Si misura solo
quello con la grafica, e lo si sceglie dal DISEGNO, non dal colore
(`tools.dt_principale`):

- i DT della tavola sono i gruppi di linee tecniche collegate che fanno una
  **griglia** - almeno due righe e due colonne lunghe, sei in tutto
  (`tools.dt_della_tavola`). Una cornice ne ha quattro: la legenda, il
  cartiglio, il bordo dell'area di stampa non sono DT;
- un gruppo che non fa griglia si riguarda **penna per penna**, perche' puo'
  essere un DT fuso con le note. Sul pane ripieno T2 le linee di richiamo
  delle note entrano nel DT da ogni lato, e vista esterna, vista interna e
  riquadri delle note venivano fuori come un gruppo solo largo 573 mm, in cui
  le pieghe da 226 mm non erano piu' "lunghe": restava come DT la sola copia
  per la vernice opaca, in scala 1:2, e il pack usciva **113 x 95** invece di
  **226 x 190**. Il richiamo e' nero, il DT verde: penna per penna si
  separano. Non basta cercare le griglie per estensione invece che per
  contatto - le pieghe interne di un DT non cominciano e non finiscono tutte
  insieme (wafer T1, T1 al cioccolato fresco) - e il contatto resta il criterio;
- fra i DT si prendono quelli **a pari scala col piu' grosso** (almeno l'85%
  della sua area), e fra questi quello **con piu' grafica**, cioe' con piu'
  colori distinti dentro. L'ordine conta: sul T1 ai cereali il DT con la
  grafica e le sue tre copie tecniche sono grandi uguali (122 x 119 mm), e la
  vista interna e' anche un po' piu' alta - vince la grafica, 148 colori contro
  12-24; sul T1 della barretta fresca la miniatura ha piu' colori del DT (279 contro 183), ma e'
  un diciassettesimo della sua area - vince la taglia;
- `find_blocks` mette **sempre in cima** il blocco che porta quel DT
  (`dt_principale`), anche quando un altro e' piu' colorato. Il colore da solo
  sbaglia in due modi. Una grafica **argento o metallizzata** ha poco colore:
  sul T2 di cialde la vista stampata e' colorata al 34%, contro il 35% che
  serve per dirsi stampato, e l'analisi misurava **tutta la tavola** - il DT
  con la grafica piu' le quattro copie tecniche sotto - con **nastro 260 x
  passo 168** invece di **148 x 108**. E una legenda o una copia tecnica
  colorate passano la soglia anche loro: sul T1 farcito la cornice della
  legenda racchiude 233 colori, il DT 177. Con un artwork argento sarebbero
  passate davanti, e l'analisi sarebbe finita sulla legenda. Il blocco del DT
  che non arriva alla soglia si promuove a stampato (`promosso`);
- fra un blocco e la cornice che lo racchiude - sulla brioche STD il bordo
  dell'area di stampa, 460 x 336 attorno ai 420 x 290 dello steso - vince il
  blocco piu' simile al DT, per sovrapposizione su unione;
- se il blocco che porta il DT e' molto piu' grande di lui - sovrapposizione
  su unione sotto 0,5 (`tools.DT_NEL_BLOCCO`) - non e' il DT: e' il DT fuso
  con le note. Sul pane ripieno un blocco di 573 x 350 mm con vista esterna, vista
  interna, riquadri delle note e legenda, e misurato cosi' il pack usciva
  **572 x 207**, cioe' le note dentro il modello. Allora si misura il DT: il
  suo riquadro, unito al rettangolo chiuso della fustella che gli somiglia
  di piu', cercato solo attorno a lui (`tools._riquadro_del_dt`,
  `riquadro_fustella(entro=...)` - sulla tavola intera la ricerca non
  finiva). Sul parco il blocco e il suo DT stanno tutti sopra 0,78;
- lo strumento dell'agente `analyze_flowpack` misura sullo stesso blocco
  della costruzione (`tools.riquadro_artwork`), e non piu' sulla pagina
  intera, dove sul T2 di cialde dava gli stessi 260 x 168.

Sul parco la scelta e' la stessa di prima su tutti i tredici file: quello che
cambia e' che non dipende piu' dal colore. Sulla vernice dell'astuccio della ciambella,
che la grafica non ce l'ha, prende il DT e non la miniatura colorata, che e'
un quindicesimo dell'area.

**La miniatura come riferimento.** "Forma e proporzioni dalla miniatura, scala
dal disegno grande" (vedi *Cercare sempre il disegno tecnico in miniatura*).
Quando le quote sono in curve e il codice non le legge - sul T2 di cialde anche
il 148 e il 108 - il riscontro e' la miniatura stessa, e le copie tecniche
valgono quanto lei: sono lo stesso disegno in scala. `quote.riscontro_miniature`
cerca i contorni chiusi con le proporzioni del DT letto, fra l'8 e il 92% della
sua taglia, fuori da lui, e controlla che le pieghe e le testate lette ci
cadano sopra:

    T2 di cialde               5 copie, 1:2 (le quattro tecniche) e 1:5,3
    T1 della barretta fresca   1 copia, 1:4,0
    T1 farcito                 1 copia, 1:11,0
    wafer T1                   1 copia, 1:4,6
    brioche T10                1 copia, 1:7,2

Serve a **confermare**, mai a gridare. Di rettangoli con le proporzioni giuste
una tavola ne ha anche altri - sul T1 ai cereali le cornici delle lastre, sul
T1 farcito i riquadri della legenda - e dentro non c'e' il disegno: una copia
che non torna puo' non essere una copia. Le radici delle pinne non si
chiedono, perche' non tutte le miniature le disegnano (T1 della barretta fresca e
T1 farcito no). E conferma che le linee **ci sono**, non che siano pieghe: una
guida dell'area di stampa sta nella copia quanto una piega. Quella scelta la
fa il solutore, vedi *Pieghe e guide: la piega attraversa il passo*.

**Se il DT con la grafica non si legge, le quote dalla copia.** "Se non capisci
le dimensioni prendi come riferimento la miniatura": quando sul DT con la
grafica le fasce non chiudono ne' sul blocco ne' sulla fustella, prima del
solutore vecchio si leggono le quote su una sua **copia** - una copia tecnica
o la miniatura, un DT della tavola con le stesse proporzioni e piu' piccolo -
e si riportano sul DT con l'affinita' che porta un riquadro sull'altro
(`tools.quote_dalla_copia`, `flowpack.riporta_da_copia`). Lo dice un avviso,
"QUOTE DALLA COPIA ... da controllare": una copia e' disegnata con meno cura
del DT, e sul T2 di cialde la copia 1:2 da' nastro 147,4 invece di 148. E il
solutore vecchio, l'ultimo ripiego, guarda solo il blocco del DT: sulla
pagina intera misurava anche quote, copie tecniche e cartiglio.

### Prima le quote, poi via tutto quello che sta fuori dal DT

L'ordine della costruzione, per tutte le famiglie:

1. **una pagina sola** (vedi sopra);
2. **il foglio nel verso della grafica**, girato se sulla tavola stava girato
   (vedi *Il foglio nel verso della grafica, prima di risolverlo*);
3. **le quote**, lette sul file intero: il DT con la grafica, le sue copie,
   la miniatura, i numeri del cartiglio. E' li' che le note servono;
4. **via tutto quello che sta TUTTO fuori dal DT**, nella stessa passata che
   toglie le coperture per nome (`artwork.strip_separations` con `regione`):
   quote, copie tecniche, legenda, cartiglio, miniature. Il DT e' lo steso del
   flowpack (`flowpack.foglio_in_pagina`), il riquadro della fustella per
   astucci e vassoi (`Dieline.bbox`), piu' 3 mm (`MARGINE_DT`);
5. **la costruzione**, come prima, sul file cosi' pulito.

Le informazioni si leggono PRIMA della pulizia, sul file intero: le
coperture per nome, le aree riservate - la cui didascalia puo' stare nella
legenda - e i riscontri con le quote e con la miniatura. Tutto il resto dopo.

Perche' non bastava ritagliare la texture sullo steso: le note fuori dal DT
entravano nella costruzione da altre porte.

- **Le penne del disegno tecnico** si contano sulla pagina: sul T2 di cialde
  i tratti spenti come DT erano 3734, quasi tutti delle quattro copie
  tecniche; tolte le copie sono 9. Una penna che vince perche' traccia le
  tabelle del cartiglio spegnerebbe, dentro il DT, la grafica disegnata con
  lei.
- **Il nero** si decide su una quota della pagina: le scritte nere della
  legenda e del cartiglio sono nero pieno che il render fa nero, e abbassano
  la quota della `k` tradita. Sulla brioche STD, senza note, la quota passa dal
  6,6 al 12,7%: sopra la soglia del 5% in tutti e due i casi, ma un file al
  limite la correzione l'avrebbe persa. Adesso `nero.spia` gira sul file
  pulito.
- **L'avviso sull'RGB** contava anche il logo dello studio nel cartiglio:
  adesso contano solo le immagini disegnate sul DT
  (`tracciati.immagini_nel_riquadro`), e dal file pulito le immagini tolte
  spariscono anche dalle risorse.

Cosa si toglie e cosa no, misurato sui dieci flowpack del parco: **dentro il
DT la resa e' identica al pixel** su tutti, e fuori non resta niente oltre i
5 mm, salvo le linee del DT che escono dallo steso (sulla brioche STD il bordo
dell'area di stampa, sul T1 al cioccolato fresco il tratteggio sotto la pinna).

- Un oggetto che **tocca** il DT resta intero. Si toglie solo quello che sta
  tutto fuori: tracciati, immagini, form, scritte.
- Un tracciato solo puo' disegnare il DT e, nello stesso colpo, la vista
  tecnica accanto: sul T1 ai cereali la penna del DT traccia anche la vista
  interna. Si tolgono i **sottotracciati** tutti fuori - un sottotracciato non
  tocca niente fuori dal suo riquadro, ne' col riempimento ne' col tratto -
  e dentro non cambia un pixel.
- Le **scritte** si stimano per eccesso, un glifo largo un corpo e mezzo,
  senza leggere il font: una nota stimata troppo grande resta, una scritta
  della grafica tolta sarebbe un danno. Se un blocco di testo ha scritte
  dentro e fuori - sul T1 ai cereali "Bar Code Area" sul DT e le didascalie
  delle copie tecniche sotto - quelle fuori non si tolgono ma si rendono
  **invisibili** (modo 3), perche' togliendole le altre si sposterebbero.
- Un **form** si toglie se il suo riquadro dichiarato sta fuori; se sta a
  cavallo, dentro si pota solo se e' disegnato una volta sola e da un posto
  solo, perche' una seconda copia starebbe altrove.
- Il **richiamo** di una nota tocca il DT, quindi resta: la sua linea la
  spegne il livello DT come tratto, ma il pallino in fondo, un pieno, restava
  grafica. Un pieno piccolo (fino a 3 mm) sulla punta interna di un tratto
  che esce dal DT - basta un millimetro - e' la testa di un richiamo, e va
  via con la nota: sul pane ripieno 9 pallini neri da 0,7 mm. Se il pallino non
  sta sulla punta di nessun tratto non si tocca: sul pane ripieno ne restava uno,
  orfano nel template, e adesso va via con le didascalie del box area in cui
  sta (vedi *Tolto il box, via anche la sua didascalia*).

Costa una passata di pypdf sul flusso, la stessa delle coperture: da 0,2 a
6 secondi, wafer da colazione il piu' caro. E visto che la passata c'e' comunque, per
nome si tolgono anche le lastre che **disegnano** il DT, non piu' le sole
coperture: vedi *Le coperture si tolgono per nome, non per euristica*.

Sul parco, tredici file contro la versione di prima: **dodici GLB identici al
byte**. Il tredicesimo, il display T1x40, cambia 6.483 pixel della texture e
nessuno dentro la fustella: e' il logo del cliente nel cartiglio, che il vassoio
si portava dietro perche' la sua texture e' il foglio intero. Quello che
cambia davvero sono le penne del DT - sul T2 di cialde 9 tratti spenti invece
di 3734, sul T1 al cioccolato fresco 1 invece di 4942 - e la quota del nero, vedi *La `k`
nera si rimette dalla lastra*.

E il caso per cui e' nata, provato: il T2 di cialde col cartiglio riempito di
colore. Col codice di prima il blocco piu' colorato era il cartiglio, e ne
usciva un pack di **28 x 34 mm** con la texture della legenda; adesso esce il
T2 di cialde, **148 x 108**.

### Il foglio nel verso della grafica, prima di risolverlo

**Uno steso deve dare lo stesso pack comunque stia sulla tavola da disegno** -
girato di 90, 180 o 270 gradi, spostato, con qualche aggiunta tecnica intorno.
Come un DT sta sulla tavola lo decide chi impagina, e non e' il pack.

Il caso che l'ha imposto: il **T6 aperto** arriva in due impaginati.
Sul file 1742… il foglio e' dritto sulla grafica e le scritte tecniche -
*OUTSIDE VIEW*, le quote - stanno capovolte; sul **file T6_base** e' dritto il
disegno tecnico, e la grafica e' capovolta. Stessa fustella, stesse misure, e
il secondo usciva **rovesciato**: il solutore legge il cielo come la fascia
SOPRA il fronte e le falde del retro nell'ordine in cui le incontra, cioe' nel
verso del FOGLIO. Il fronte lo raddrizzava la texture, faccia per faccia, ma il
cielo e il fondo erano scambiati, il retro aveva la fascia rossa in alto e la
falda con "6 Pezzi - 180 g" capovolta, i fianchi a testa in giu'.

La regola e' quella di sempre - **il modello segue la grafica** - applicata al
FOGLIO invece che alla texture: prima si gira la pagina nel verso della
grafica, poi si risolve. Il giro si **cuoce** nel contenuto
(`artwork.pagina_girata`: il flusso avvolto fra `q cm` e `Q`, senza rileggerlo,
e MediaBox e riquadri portati con la stessa matrice), perche' qui nessuno legge
`/Rotate`: pdfplumber misura nello spazio del PDF, pdfium ci rende sopra, e un
foglio girato solo a parole darebbe misure e raster in due telai diversi. Un
`/Rotate` che il file ha gia' si somma al giro e sparisce, e anche senza giro
si cuoce all'ingresso (`artwork.pagina_unica`): pdfplumber e la resa di pdfium
lo applicano, il testo di pdfium e le passate di pypdf no, e lo stesso foglio
si misurava in due telai diversi. Un astuccio T8 salvato con `/Rotate 90` da' lo
stesso modello dell'originale, al pixel. Da li' in avanti
tutto - quote, colata, nero, texture, testate - lavora sul foglio girato, e il
riquadro della colata indicato dall'agente gira con lui
(`artwork.riquadro_girato`).

Il verso lo da' il **testo vivo** (`tracciati.verso_grafica`), e non il
disegno tecnico, che sul file T6_base e' dritto proprio mentre la grafica e'
capovolta:

- **astucci** (`artwork.astuccio_sulla_grafica`): ogni faccia che ha testo
  vota contro il verso che DEVE avere sul foglio (`VERSO_ATTESO`): il fronte e
  il cielo dritti; il retro e le falde del retro, su una fasciatura verticale,
  **capovolti**, perche' la piega fa loro mezzo giro; su una orizzontale il
  retro dritto come il fronte. Fondo e fianchi non votano. Se tutte le facce
  che parlano si leggono come devono, il foglio resta com'e' e non costa
  niente; altrimenti si prova a girarlo e a risolverlo di nuovo, prima nei
  giri che i voti suggeriscono, e vince la lettura con piu' facce giuste - il
  fronte conta doppio. **Il fronte da solo non basta**: su un astuccio chiuso
  fronte e retro sono alti uguali, e girato il foglio di mezzo giro il
  solutore puo' prendere l'altro, e il retro, stampato capovolto, si legge
  dritto come un fronte. Lo smentisce il cielo, che fra i due deve leggersi
  dritto col fronte: sull'astuccio della ciambella girato di 90 gradi il fronte era la
  faccia di PREPARAZIONE, e il cielo capovolto l'ha detto;
- **flowpack** (`server.flowpack_sulla_grafica`): vota la fascia del fronte
  (`flowpack.fronte_in_pagina`), e il giro vale se sullo steso girato
  l'analisi si risolve senza ripiego e il fronte si legge dritto. Il solutore
  i 90 gradi li reggeva gia' - traspone i suoi ingressi - ma la texture
  seguiva il foglio: girato di mezzo giro, il T1 della barretta fresca usciva a testa in
  giu'; girato di un quarto il T1 al mandarino perdeva la fascia rossa,
  perche' la colata si allinea su un'onda orizzontale e verticale si
  incollava storta - con un errore sotto il mezzo millimetro, cioe' senza
  nessun allarme. Un caso calibrato non passa di qui: le sue quote sono
  scritte a mano sul foglio com'e'.

Se sul foglio com'e' l'astuccio **non si risolve**, prima di arrendersi lo si
prova girato: il solutore conosce meglio certi versi di altri. L'astuccio T8 girato
di 90 gradi non si costruiva ("i fianchi non tornano con la profondita'"),
girato si'. Lo stesso per il **vassoio** (`vassoio.riconosci_sulla_tavola`): la
griglia si riconosce in un verso solo - cinque colonne e tre fasce - e il display
T1x40 girato di un quarto ne aveva tre e cinque; se non torna si prova il
foglio girato di 90 e 270 gradi, ma solo quando il vassoio e' dichiarato,
perche' la prova la pagherebbe ogni astuccio e ogni flowpack. Mezzo giro
invece il vassoio lo regge da se': e' simmetrico, e quale testata va davanti
lo dicono le altezze (`vassoio.testata_davanti`) - anche di un decimo di
millimetro, 40,5 contro 40,6 sul display T1x40, perche' con la nord di serie
davanti andava la testata che stava in alto sulla TAVOLA.

**Il testo storto non vota.** Una scritta messa di sbieco e' un tratto della
grafica: sul fronte della brioche "RICICLAMI nella CARTA" sta a 303 gradi e,
col suo corpo grande, pesava piu' di tutto il testo dritto. Vota solo chi sta
entro 10 gradi da un multiplo di 90.

**Il limite: senza testo vivo il verso non si legge**, e il foglio resta com'e'
sulla tavola - il modello segue il foglio, come prima - e **lo si dice**:
"verso della grafica non letto ... il verso va controllato sul modello". E'
l'unico caso in cui il pack puo' ancora dipendere da come lo steso sta sulla
tavola. Sul parco il testo vivo sul fronte ce l'hanno tutti gli astucci e
sette flowpack su dodici; T1 ai cereali, T2 di cialde, T1 al cioccolato fresco,
wafer T1 e croccante T2 fondente hanno il marchio e le scritte vettorializzati.
Leggere il verso dalle lettere disegnate - la linea di base allineata, le
aste che sporgono - e' la strada per loro; con le poche lettere di un marchio
non e' affidabile, e un verso sbagliato con sicurezza e' peggio di uno
dichiarato non letto.

Provato girando la pagina dei file del parco di 90, 180 e 270 gradi e
costruendo ogni copia, cinque viste per modello contro quelle dell'originale:

    identiche al pixel in tutti e quattro i versi
      astucci   T6 aperto (tutti e due gli impaginati), astuccio T8, astuccio della ciambella
      flowpack  T1 al mandarino, T1 cheesecake, T1 della barretta fresca,
                wafer da colazione, T1 farcito, brioche STD, brioche T10
    lo stesso vassoio, a meno di un pixel di ricampionamento
      vassoio   display T1x40 (prima a 90 e 270 gradi non si costruiva)
    capovolti in due versi su quattro: senza testo vivo sul fronte
      flowpack  T1 ai cereali, T2 di cialde, T1 al cioccolato fresco, wafer T1,
                croccante T2 fondente

E un file salvato con `/Rotate 90` - l'astuccio T8 - da' il modello dell'originale.
Sul parco nel verso di sempre cambia un solo modello, l'astuccio della ciambella, che
adesso si legge nel verso della sua grafica: vedi *Se i fianchi li portano
tutte e due, si vedono quelli stampati*.

### Il modello finito si gira: il marchio orizzontale e dritto

**Il marchio del fronte si legge sempre orizzontale e nel verso giusto.**
Quando il modello e' finito e verificato, lo si gira tutto intero attorno alla
normale del fronte - il fronte resta davanti, il centro al centro - finche'
l'alto della grafica punta in alto.

Il caso sono i flowpack. Il tubo si costruisce sempre **coricato**, l'asse
lungo la x e le pinne a destra e a sinistra, ma il marchio sta come sta sullo
steso: sul T1 al mandarino, sul T1 cheesecake, sulle brioche, sul wafer da colazione, sul
T2 di cialde, sul T1 ai cereali, sul T1 al cioccolato fresco e sul pane ripieno
il testo corre **attraverso** il passo, e sul pack coricato il marchio si
leggeva dall'alto in basso. Girati di un quarto, stanno **in piedi** con le
pinne in alto e in basso, come in mano. T1 della barretta fresca, T1 farcito, wafer T1 e
croccante T2 fondente, col testo lungo il passo, restano coricati. Gli astucci, il vassoio
e i flowpack coricati escono identici al byte: il giro e' zero.

Il giro non si ragiona sulle convenzioni, si **misura**
(`verifica.giro_del_marchio`): al centro del fronte, dove guarda la verifica
del fronte, l'alto della grafica sulla pagina si porta nella texture - lo
steso ruotato ci entra girato di un quarto in senso orario - e con le derivate
della griglia lungo u e v sul modello; il giro e' quello che lo rimette
sull'asse y. L'alto della grafica e' quello del testo vivo del fronte; senza
testo vivo e' l'alto del foglio, che dopo *Il foglio nel verso della grafica*
e' la stessa cosa per tutti i file che si leggono. Si gira DOPO le verifiche,
che il giro attorno al fronte non tocca.

Sugli astucci il fronte si raddrizza gia' con la texture; resta da girare solo
la scatola il cui fronte non si poteva girare senza stirarlo - un pannello non
quadrato con la grafica a 90 gradi, vedi *Non distorcere mai la grafica* - e
allora si gira la scatola intera, guscio, interno e coste
(`folding.gira_facce`). Il vassoio ha il fronte dritto per costruzione.

## Cosa chiediamo a chi prepara l'artwork

Tre richieste, e non sono di comodo: sono le tre cose che dal PDF **non si
possono dedurre**, e ogni volta che si e' provato a indovinarle si e' rotto
qualcosa di vero. Questa pagina e' quella da girare al prestampa.

### 1. Il disegno tecnico su un livello suo

**La richiesta.** Fustella, cordonature, quote, retini delle aree riservate,
cartiglio, note, crocini di registro: tutto quello che non si stampa va su un
**livello separato**, nominato, e non mescolato al livello della grafica.

**Perche'.** Nella texture ci va solo la grafica. Se il disegno tecnico e'
mescolato, l'unico modo di toglierlo e' indovinarlo, e indovinare vuol dire
sbagliare: il criterio del colore ha cancellato il logo, la tabella
nutrizionale e il testo legale della brioche STD — il 4,4% del foglio — perche'
la quota e il logo erano lo stesso ciano. Vedi *Il colore non dice mai cos'e'
disegno tecnico*. Con il livello si spegne e basta: nessuna maschera, nessun
ritocco, nessuna grafica persa.

**Come nominarlo, perche' venga riconosciuto.** Meglio di tutto un
**Processing Step ISO 19593-1** (gruppi `Structural`, `Dimensions`, `Legend`,
`Position`, `Braille`, `White`, `Varnish`): quello e' lo standard e la lettura
e' esatta. In mancanza, uno di questi nomi di livello:

    technical drawing   technical-drawing   dieline   die line   cutter
    fustella   tracciato   dt   dimensions   legend   notes   check
    guides and grids   print free area   best before area   bar code area
    covered area   eyemark   infopanel   braille   reg marks   white   varnish

Un nome fuori da questa lista non viene riconosciuto e il file ricade
sull'euristica. Se serve un nome diverso si aggiunge a `techink.OCG_TECH`: e'
una riga, ma va chiesta.

**Cosa NON va su quel livello.** Solo quello che non si stampa. Il codice a
barre stampato, la tabella nutrizionale stampata sul retro, il testo legale, i
bollini: quella e' grafica, si stampa, e deve restare.

**Da non confondere con le aree riservate.** `GDA`, `COVERED AREA`, `TEXT
AREA`, `BEST BEFORE AREA`, `BAR CODE AREA`, `PRINT FREE AREA`, `NEUTRAL AREA`
non sono la cosa stampata: sono il **posto tenuto** per quella cosa, riquadri
pieni che il tecnico mette per dire dove andra'. Non si stampano e **non
devono comparire nel render finale**: vanno sul livello del disegno tecnico
con tutto il resto che non si stampa, oppure su una lastra chiamata col
proprio nome. Vedi *Le aree riservate non compaiono mai nel render*.

### 2. La colata su un livello suo

Stessa forma, altra ragione: il livello dice **dove** va la colata, e senza
quello non si puo' ne' renderla in quadricromia ne' sostituirla senza
indovinare il riquadro. Il nome che si cerca e' `Colata`. Vedi *La colata si
rimette con l'inchiostro del file*.

### 3. La grafica in quadricromia, non in RGB

In RGB la sovrastampa non esiste e non c'e' niente da simulare: la colata
perde l'ombra sulle gocce e diventa una macchia di ciano piatto, e a
valle non si recupera. Vedi *La grafica va in quadricromia, non in RGB*.

Nello stesso spirito: la **GDA** appartiene al disegno tecnico e nel livello
della grafica non va mai messa. Vedi *La GDA sta nel disegno tecnico*.

## Regole comuni a tutte le tipologie

- **Il modello segue la GRAFICA, non il disegno tecnico.** Sono due cose
  diverse: il DT dice come e' impaginato il foglio, la grafica dice come si
  legge il pack in mano. Sull'astuccio della ciambella il pannello fronte ha
  tutto il testo a 90 gradi e il retro a 270 — sul foglio, non sul pack — e il
  modello usciva col marchio coricato. Il verso lo danno i **caratteri
  stampati**, pesati sull'area: una riga di marchio a corpo 40 conta piu' di
  venti righe di legale a corpo 5, che e' come la legge un occhio
  (`tracciati.verso_grafica`). Un pannello senza testo abbastanza non dice
  niente e si lascia com'e': indovinare sarebbe peggio. E prima delle facce
  il FOGLIO: se la grafica dice che sta girato sulla tavola, si gira lui e
  poi si risolve - vedi *Il foglio nel verso della grafica, prima di
  risolverlo*. Faccia per faccia resta da raddrizzare solo quello che scarta
  dal verso che la faccia deve avere: il retro di una fasciatura verticale e
  i fianchi agganciati a lui si stampano capovolti, e letti a 180 gradi sono
  gia' giusti (`artwork.verso_atteso`). Prima si girava ogni verso diverso
  da zero, e la falda del retro del T6 aperto finiva a testa in giu'.
- **Il marchio del cliente e' la `k` NERA + le altre lettere ARANCIO.** Due colori, e
  vanno tutti e due: la `k` in nero, le altre cinque lettere nell'arancio di
  marchio, che nei file e' una tinta piatta col suo nome - il nome del
  marchio e `ORANGE`, a volte con un numero davanti. E' l'invariante piu' facile da controllare di tutto
  il parco: si guarda il marchio e si sa subito se il render tiene.

  Quando non torna dice sempre la stessa cosa: la **sovrastampa non e' stata
  simulata**. Sulla brioche STD la `k` esce azzurra, perche' e' costruita come
  un ciano che sovrastampa un nero: senza sovrastampa il ciano lo copre invece
  di sommarcisi. Verificato affiancando tre rese dello stesso marchio — pdfium
  azzurra, Ghostscript con `-sOverprint=disable` azzurra, Ghostscript con
  `-sOverprint=simulate` **nera**. Qui l'artwork e' giusto: sbaglia chi lo
  rende, e si rimedia riportando il nero dalla lastra — vedi *La `k` nera si
  rimette dalla lastra, non rendendo tutto con Ghostscript*.
- **Confrontare sempre il modello finito con lo steso.** Mai specchiata ne'
  capovolta.
- **Non distorcere mai la grafica.** I bollini circolari restano cerchi. Ogni
  pannello va sulla faccia corrispondente e centrato.

  Questa regola e' anche il limite della precedente, e il confine lo da' il
  rapporto di forma. Pannello sul foglio e faccia sul solido hanno le stesse
  proporzioni — vengono dalla stessa fustella — quindi girare una texture di 90
  gradi la mappa su una faccia con le proporzioni scambiate. Su un pannello
  quasi quadrato non si vede; su un fianco stretto si', **ed e' anche il caso
  in cui girare sarebbe sbagliato**: su un fianco da 38 x 191 il testo
  verticale E' il progetto, mentre su un pannello da 188 x 191 vuol dire che il
  foglio e' impaginato girato. Dove girare stirerebbe, non si gira e lo si
  **dichiara**: la regola dice di seguire la grafica, non di consegnare grafica
  deformata. Il caso generale — un pack non quadrato impaginato girato, dove
  servirebbe trasporre anche le quote del solido — lo risolve il foglio
  girato prima di risolvere: le quote escono gia' nel verso della grafica.
- **Verificare il verso delle normali.** L'attributo NORMAL non basta: conta
  l'avvolgimento dei triangoli, ed e' quello che i viewer usano per il culling.
  Gli astucci sono stati consegnati due volte con le facce rivolte all'interno
  perche' il rasterizzatore interno non fa culling e non se ne accorgeva.
- **Cercare sempre il disegno tecnico in miniatura.** Negli artwork c'e' spesso
  un DT completo senza grafica, di solito in basso o a lato, con piu'
  informazioni di quello sovrapposto alla grafica. E' molto piu' pulito.
  Sulla coppa da 500 la miniatura da' residuo **0,000 mm** contro **0,564** del
  contorno sotto la grafica. Attenzione: e' in scala ridotta, quindi **forma e
  proporzioni dalla miniatura, scala dal disegno grande o dalle quote**.

  Le sue **quote** sono il riscontro piu' forte che esista: numeri scritti da
  chi ha progettato il pack, non dedotti da noi. Quando sono testo le legge
  `quote.py` - catene allineate sullo stesso asse che sommano alla misura
  totale, come i `20 | 37,5 | 215 | 37,5 | 20 = 330` del wafer da colazione - e la
  costruzione dice se le misure del disegno tornano. Quando sono
  vettorializzate, come sul wafer T1, le legge solo un occhio: lo strumento
  `livelli` mostra il livello del DT con le miniature, ingrandibile. **Servono
  a verificare, non a costruire**: una quota si misura dal disegno, vedi *Prima
  le misure, poi il contenuto*.

  Vale per tutte le famiglie. Sul flowpack la catena e' quella delle testate
  lungo il passo; sull'astuccio sono la fila del fronte e la sua colonna con
  le alette (`quote.riscontro_astuccio`), sul vassoio le cinque colonne e le
  tre fasce della griglia (`riscontro_vassoio`); e su tutti e due anche la
  terna del cartiglio, `70 x 40 x 150`, che torna entro 1,5 mm perche' fra
  misure interne ed esterne c'e' lo spessore del cartoncino. Si grida solo
  quando il file parla **di questo pack** e dice un'altra cosa - una catena
  lunga uguale, con la stessa somma e almeno meta' dei pezzi uguali, o una
  terna che ci somiglia entro il 20% ma non torna - perche' un numero preso a
  caso dal foglio non ci arriva. Sul parco nessun astuccio e nessun vassoio
  scrive le sue quote come testo: lo si dice, e le guarda l'occhio.

### Mezzo millimetro non puo' cambiare il pack

**Due disegni tecnici simili devono dare pack simili.** Se due AW dello stesso
formato differiscono di qualche decimo di millimetro su una linea, il modello
che ne esce deve essere lo stesso: quei decimi sono il rumore con cui e'
disegnato un file, non una scelta di chi ha progettato il pack.

E' successo il contrario, misurato:

| | terna di linee | scarto fra i passi | esito |
|---|---|---|---|
| brioche **promo** | 341,31 / 345,15 / 348,31 | 0,67 mm | tre pieghe |
| brioche **STD** | 341,31 / 344,81 / 348,31 | 0,00 mm | fuse in una |

Stesso pack, stesso disegno tecnico, stesse quote a cartiglio. La soglia stava
a 0,60 mm: il Promo passava per **sette centesimi di millimetro**, lo STD no.
E fuse, quella piega spariva e il pack usciva spesso **7 mm invece di 57** -
piatto - con nastro, passo e corpo tutti giusti.

Da qui tre regole, in ordine di forza:

1. **Nessuna soglia numerica puo' essere l'unica cosa che decide.** Se una
   scelta dipende da uno scarto vicino alla soglia, la soglia e' sbagliata
   comunque la si tari: il problema non e' il valore, e' che ci sia un
   precipizio.
2. **Quando una lettura e' ambigua, si tengono tutte le letture** e si
   risolvono tutte. A scegliere e' la credibilita' del risultato, non un
   confronto fatto prima di sapere dove porta.
3. **A decidere dev'essere una quantita' fisica.** Fra due soluzioni entrambe
   coerenti con l'invariante, vince quella con la quota plausibile - non
   quella che vince per un decimo di millimetro su uno scarto numerico.

Un invariante soddisfatto **per costruzione** da tutte le candidate, come
`perimetro + 2 falde = nastro`, non distingue niente e non puo' fare da
controllo: torna sempre, anche sulla soluzione sbagliata.

## Perche' un file nuovo non si costruisce: la lista

Due file arrivati insieme, tutti e due fermi con lo stesso messaggio -
`saldature di testa non riconosciute` - e due cause che non c'entrano niente
l'una con l'altra. Da li' questa lista, che e' quella da girare a chi prepara
l'artwork **prima** di mandare un pack nuovo.

### 1. La fustella deve CHIUDERE un rettangolo

E' il riferimento da cui si misura tutto, e si riconosce senza euristiche:
**due orizzontali della stessa larghezza, due verticali della stessa altezza,
e i quattro lati che si coprono**. Non serve che gli estremi combacino — una
fustella sborda, e sul T1 al cioccolato fresco la verticale di destra scende 6 mm
sotto l'orizzontale di sotto — serve che i quattro tratti chiudano.

Una tavola di rettangoli chiusi ne ha parecchi: la cornice del foglio, i
cartigli, i riquadri della legenda. Vince quello che **somiglia di piu'
all'ingombro stampato**, perche' la fustella e' il rettangolo in cui la
grafica sta. Vedi `flowpack.riquadro_fustella`.

### 2. La grafica non deve uscire dal tracciato

Sul T1 al cioccolato fresco esce: c'e' una striscia di fondo bianco che scende sotto la
fustella, e chi misura *lo stampato* invece della fustella trova un nastro di
**121 mm invece di 115**. Con quel numero le fasce non chiudono piu' e il file
non si costruisce. Oggi c'e' un secondo tentativo che ripiega sulla fustella,
ma costa otto secondi di rilettura dei tracciati: meglio non doverlo fare.

Se il fondo deve sbordare - e a volte deve, per l'abbondanza - la fustella
vada comunque tracciata chiusa, cosi' il secondo tentativo ha da leggere.

### 3. Le quote stanno FUORI dal tracciato, o su un livello loro

La linea di quota del T1 al cioccolato fresco sta sopra il pack, disegnata con la stessa
penna della fustella, e misurando dagli estremi il nastro diventava 136,8 mm
invece di 115. Una quota dentro l'ingombro, con la penna del disegno, e' un
tratto indistinguibile da una cordonatura.

E' lo stesso identico discorso di *Cosa chiediamo a chi prepara l'artwork*:
quello che non si stampa va su un livello suo. `Dimensions` e' un nome che il
codice riconosce gia'.

### 4. Le saldature vanno disegnate per intero

Sempre sul T1 al cioccolato fresco: la saldatura di sinistra e' tracciata a tutta altezza
(115 mm), quella di destra solo attraverso il corpo (95 mm). Due tratti che
descrivono la stessa cosa e sono lunghi diversi. Il solutore che cerca
"quattro verticali a tutta altezza" ne trova tre e si ferma.

Non e' pignoleria: da quella asimmetria non si capisce piu' se la linea corta
e' una saldatura o una cordonatura del corpo.

### 5. La tipologia va dichiarata quando non e' una di quelle note

Le famiglie che il codice risolve sono **astuccio**, **flowpack** e
**vassoio**. Un pack che non e' nessuna delle tre non va indovinato: il
display T1x40 cadeva nel ramo flowpack e usciva
`saldature di testa non riconosciute`, un messaggio che a chi ha in mano un
vassoio non dice niente. Vedi *La tipologia non riconosciuta e' un errore, non
un ripiego*.

### 6. Il confronto finale lo fa l'occhio, sul modello

Nessuna di queste regole sostituisce il passaggio finale: si apre il GLB e si
guarda. Le misure dicono che i conti tornano, non che il pack e' giusto — e
l'unica volta in cui una segnalazione di rotazione e' stata smentita, a
smentirla e' stato il modello aperto e guardato, non un numero. Vedi *Il
caso calibrato: T6 aperto*.

## La texture e' lo steso

La texture di ogni modello e' **lo steso del PDF**: la grafica pulita - senza
disegno tecnico, quote, legende, aree riservate, come la pulisce la pipeline -
**nel verso in cui sta nel PDF**, **inquadrata sul DT**, a scala uniforme. Le
UV del modello puntano li'. Chi vuole una variante prende la texture, ci
sovrappone il nuovo artwork - stesso DT, stesso verso, stessa scala - e la
rimette sul modello: ogni cosa torna al suo posto.

Le famiglie lavorano ognuna nel suo telaio - il foglio girato sul verso della
grafica (`artwork.pagina_girata`), il film coricato, con sotto le strisce delle
tinte - e alla fine si riporta tutto allo steso (`pack3d/steso.py`), senza
toccare la costruzione: le verifiche girano prima, sui telai di sempre.

| famiglia | lo steso | cosa si fa alla fine |
|---|---|---|
| flowpack | il rettangolo del film | si gira indietro dei gradi del foglio, e dei 90 del film coricato; con lei la mappa del metallo |
| pouch | il foglio della busta | niente: era gia' lo steso |
| vassoio | il DT con un millimetro attorno, invece della pagina intera | via la coda delle tinte, ritaglio, giro indietro |
| display con plancia | il DT con un millimetro attorno, anche oltre i pezzi della maglia | via la coda delle tinte, le UV portate sul DT (`steso.allarga`), giro indietro |
| ballotin, scatola a punta | il DT con un millimetro attorno | via le strisce del rovescio e del taglio |
| astuccio | il DT con un millimetro attorno | lo steso al posto delle facce (*Astucci*, *La texture e' lo steso*) |
| coppa, cono | uno per foglio: lo sleeve e il fondo, il tappo; il cono, il lid - in un atlante | il foglio che `coppa.orienta` aveva girato sulla tavola torna nel verso del suo PDF; il rovescio bianco e' un colore pieno; l'anello del tappo, che sullo steso c'e' una volta, attorno si ripete a settori, uno per modulo, e nessun triangolo ne scavalca il bordo |
| riempimento | quello del vassoio e quello del pack - in un atlante | i due modelli com'escono, e i loro stesi nell'atlante |

- **Le tinte piene** - il rovescio, il taglio, il solco - non stanno nella
  texture: sono materiali senza texture, col colore in `baseColorFactor`,
  lineare come vuole glTF (`steso.lineare`). Il viewer della pagina e le viste
  del controllo lo riportano in sRGB.
- **Una texture sola, anche per piu' fogli**: la coppa col tappo, il cono col
  lid e il riempimento vengono da due PDF, e ognuno ha il suo steso; i due
  stesi stanno in un'immagine sola, l'**atlante** (`pack3d/atlante.py`). Ogni
  zona e' lo steso del suo foglio, intero, nel suo verso e alla sua
  risoluzione - coppa e cono rendono i due fogli allo stesso dpi, e le zone
  hanno la stessa scala; nel riempimento vassoio e pack hanno ognuno la sua.
  Le zone si dispongono col lato piu' corto (in fila, in colonna, il pezzo
  grande con gli altri accanto o sotto), con 16 px di margine coi pixel del
  bordo ripetuti, perche' da lontano il filtro della texture non mescoli i
  pezzi; le UV di ogni triangolo puntano alla sua zona, e il metallo e il
  rilievo vanno in un atlante loro con la stessa disposizione. Le zone sono
  scritte nel GLB (`extras.pack3d_zone` dell'immagine): il template ci
  scrive il nome dei pezzi, e `prove/parco.py stesi` cerca ogni zona nel suo
  PDF. Glam mette una texture sola su tutto il modello: cosi' la texture e il
  template ce l'hanno tutti.
- **Il modello non cambia**: sul parco le viste del controllo sono quelle di
  prima, a meno della compressione JPEG. Cambiano solo il file della texture e
  le UV, insieme.
- **Si controlla** con `prove/parco.py stesi`: ogni texture si cerca sulla
  pagina del suo PDF, pulita come la pulisce la costruzione, girata di 0, 90,
  180 e 270 gradi e a scale diverse, e deve combaciare dritta. Un film quasi
  simmetrico pareggia dritto e capovolto, e lo strumento lo dice «incerta»:
  si guarda a occhio.

### La texture a parte

Oltre al GLB, la texture si da' **a parte**. La regola e' in
`pack3d/texture.py` e, uguale, nella pagina (`textureDelGlb`): un file per
immagine di colore, coi nomi delle mesh se sono piu' d'una
(`..._texture_coppa.jpg`, `..._texture_tappo.jpg`).

- **Al massimo 5000 px di lato** (`LATO_GLAM`), il limite di Glam Lab: una
  texture piu' grande - un display in HD arriva a 7000 - si riduce in
  proporzione, e le UV, che sono frazioni dell'immagine, restano giuste.
  Sotto il limite esce coi byte del GLB, senza ricomprimerla.
- **Solo il colore**: le mappe del metallo, della ruvidita' e del rilievo
  restano nel modello. Glam cambia solo il colore.
- **Nella pagina** c'e' «Scarica texture» («Scarica le texture» se sono piu'
  d'una) accanto a «Scarica GLB»; a differenza di quello non svuota la
  pagina.
- **In Glam** va nella sezione texture del modello (GLAM.md, sezione 8): dalla
  pagina con `pack3d:texture`, dalla routine e dallo Space con
  `/api/import-texture`, dopo il modello. **Solo se e' una**: Glam mette la
  texture scelta su tutti i materiali con una texture, e due non saprebbe
  dove metterle - per questo i modelli di piu' fogli hanno l'atlante. Se
  Glam non la prende, il modello c'e' lo stesso: si scrive e si va avanti.

### Il template PSD

Per «Scarica Template» di Glam ogni modello - con una texture sola, e coi
modelli di piu' fogli in atlante sono tutti - ha anche il suo **template**:
un PSD fatto dal GLB (`pack3d/template.py`), con la struttura del template
ufficiale del cliente per un vasetto da 750 g. Sotto, il gruppo «La tua
grafica» con la texture, cioe' lo steso; sopra, le «Guide UV»: tutti gli
spigoli della mappatura e la scacchiera A0-J9 (nascosti), l'area che il
modello non prende velata di nero al 60%, i contorni in magenta, i nomi
delle facce di un astuccio e, in un atlante, il nome di ogni pezzo (COPPA,
TAPPO, VASSOIO, FLOWPACK...) nella sua zona.

- **I contorni sono quelli che servono a chi disegna**: il bordo di quello
  che il modello prende - il DT, le finestre, i solchi - preso dalla
  maschera dei triangoli e non dagli spigoli, perche' una triangolazione con
  le giunte a T (la plancia di un display, dal bordo ondulato) ha spigoli
  liberi anche in mezzo a una faccia; e le pieghe, dove i piani girano di
  piu' di 20 gradi, se fanno una linea lunga almeno il 3% del template. Due
  pannelli separati dallo spessore del cartone, nello steso di un display,
  sono attaccati dalla loro piega. La zigrinatura della saldatura di un
  flowpack, fatta di pieghe corte che cambiano verso a ogni dente, non c'e'.
- **Ogni faccia stampata e' sullo steso**, anche quella di un colore solo -
  il fondo tutto rosso di un astuccio: in Glam la texture di una variante
  deve arrivare anche li', e il template ne disegna il contorno. Restano di
  colore pieno solo l'interno, il taglio, il rovescio e la pellicola.
- **Al massimo 45 MB**: lo storage di Glam non prende file oltre i 50. Un
  template piu' grande si rifa' piu' piccolo; le UV sono frazioni, e torna.
- **In Glam** arriva come la texture (GLAM.md, sezione 9): dalla pagina con
  `pack3d:template` (lo Space lo fa con `/api/template`), dalla routine e
  dallo Space con `/api/import-template`. Se non passa, modello e texture ci
  sono lo stesso.
