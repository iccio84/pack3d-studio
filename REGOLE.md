# Regole della pipeline pack3d

Regole accumulate caso per caso, con il punto del codice che le applica e i
controesempi che le giustificano.

## Tre regole, per tutte le famiglie

Vengono prima di ogni altra regola di questo file, e valgono per **flowpack,
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
marchio `kinder` restano quelle del file. Vedi *I due livelli li fa la
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

## Prima delle tre regole: una pagina, un DT

Prima di misurare qualunque cosa si sceglie **cosa** misurare. Vale per tutte
le famiglie.

**Solo la prima pagina.** Un PDF su piu' pagine e' quasi sempre lo stesso pack
ripetuto per lingua: il Kinder Cards T2 ne ha due, `64-GERMANY` e `01-ITALY`,
identiche tranne il piede; il Kinder Country tre. Le altre pagine si
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
  essere un DT fuso con le note. Sul Nutella B-ready T2 le linee di richiamo
  delle note entrano nel DT da ogni lato, e vista esterna, vista interna e
  riquadri delle note venivano fuori come un gruppo solo largo 573 mm, in cui
  le pieghe da 226 mm non erano piu' "lunghe": restava come DT la sola copia
  per la vernice opaca, in scala 1:2, e il pack usciva **113 x 95** invece di
  **226 x 190**. Il richiamo e' nero, il DT verde: penna per penna si
  separano. Non basta cercare le griglie per estensione invece che per
  contatto - le pieghe interne di un DT non cominciano e non finiscono tutte
  insieme (K Tronky, Choco Fresh) - e il contatto resta il criterio;
- fra i DT si prendono quelli **a pari scala col piu' grosso** (almeno l'85%
  della sua area), e fra questi quello **con piu' grafica**, cioe' con piu'
  colori distinti dentro. L'ordine conta: sul Kinder Country il DT con la
  grafica e le sue tre copie tecniche sono grandi uguali (122 x 119 mm), e la
  vista interna e' anche un po' piu' alta - vince la grafica, 148 colori contro
  12-24; sul KMS T1 la miniatura ha piu' colori del DT (279 contro 183), ma e'
  un diciassettesimo della sua area - vince la taglia;
- `find_blocks` mette **sempre in cima** il blocco che porta quel DT
  (`dt_principale`), anche quando un altro e' piu' colorato. Il colore da solo
  sbaglia in due modi. Una grafica **argento o metallizzata** ha poco colore:
  sul Kinder Cards la vista stampata e' colorata al 34%, contro il 35% che
  serve per dirsi stampato, e l'analisi misurava **tutta la tavola** - il DT
  con la grafica piu' le quattro copie tecniche sotto - con **nastro 260 x
  passo 168** invece di **148 x 108**. E una legenda o una copia tecnica
  colorate passano la soglia anche loro: sul Kinder Paradiso la cornice della
  legenda racchiude 233 colori, il DT 177. Con un artwork argento sarebbero
  passate davanti, e l'analisi sarebbe finita sulla legenda. Il blocco del DT
  che non arriva alla soglia si promuove a stampato (`promosso`);
- fra un blocco e la cornice che lo racchiude - sul Brioss STD il bordo
  dell'area di stampa, 460 x 336 attorno ai 420 x 290 dello steso - vince il
  blocco piu' simile al DT, per sovrapposizione su unione;
- se il blocco che porta il DT e' molto piu' grande di lui - sovrapposizione
  su unione sotto 0,5 (`tools.DT_NEL_BLOCCO`) - non e' il DT: e' il DT fuso
  con le note. Sul B-ready un blocco di 573 x 350 mm con vista esterna, vista
  interna, riquadri delle note e legenda, e misurato cosi' il pack usciva
  **572 x 207**, cioe' le note dentro il modello. Allora si misura il DT: il
  suo riquadro, unito al rettangolo chiuso della fustella che gli somiglia
  di piu', cercato solo attorno a lui (`tools._riquadro_del_dt`,
  `riquadro_fustella(entro=...)` - sulla tavola intera la ricerca non
  finiva). Sul parco il blocco e il suo DT stanno tutti sopra 0,78;
- lo strumento dell'agente `analyze_flowpack` misura sullo stesso blocco
  della costruzione (`tools.riquadro_artwork`), e non piu' sulla pagina
  intera, dove sul Kinder Cards dava gli stessi 260 x 168.

Sul parco la scelta e' la stessa di prima su tutti i tredici file: quello che
cambia e' che non dipende piu' dal colore. Sulla vernice del Nutella Donut,
che la grafica non ce l'ha, prende il DT e non la miniatura colorata, che e'
un quindicesimo dell'area.

**La miniatura come riferimento.** "Forma e proporzioni dalla miniatura, scala
dal disegno grande" (vedi *Cercare sempre il disegno tecnico in miniatura*).
Quando le quote sono in curve e il codice non le legge - sul Kinder Cards anche
il 148 e il 108 - il riscontro e' la miniatura stessa, e le copie tecniche
valgono quanto lei: sono lo stesso disegno in scala. `quote.riscontro_miniature`
cerca i contorni chiusi con le proporzioni del DT letto, fra l'8 e il 92% della
sua taglia, fuori da lui, e controlla che le pieghe e le testate lette ci
cadano sopra:

    Kinder Cards T2     5 copie, 1:2 (le quattro tecniche) e 1:5,3
    Milch-Schnitte T1   1 copia, 1:4,0
    Kinder Paradiso T1  1 copia, 1:11,0
    K Tronky T1         1 copia, 1:4,6
    K Brioss T10        1 copia, 1:7,2

Serve a **confermare**, mai a gridare. Di rettangoli con le proporzioni giuste
una tavola ne ha anche altri - sul Kinder Country le cornici delle lastre, sul
Paradiso i riquadri della legenda - e dentro non c'e' il disegno: una copia
che non torna puo' non essere una copia. Le radici delle pinne non si
chiedono, perche' non tutte le miniature le disegnano (Milch-Schnitte e
Paradiso no). E conferma che le linee **ci sono**, non che siano pieghe: una
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
del DT, e sul Kinder Cards la copia 1:2 da' nastro 147,4 invece di 148. E il
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

- **Le penne del disegno tecnico** si contano sulla pagina: sul Kinder Cards
  i tratti spenti come DT erano 3734, quasi tutti delle quattro copie
  tecniche; tolte le copie sono 9. Una penna che vince perche' traccia le
  tabelle del cartiglio spegnerebbe, dentro il DT, la grafica disegnata con
  lei.
- **Il nero** si decide su una quota della pagina: le scritte nere della
  legenda e del cartiglio sono nero pieno che il render fa nero, e abbassano
  la quota della `k` tradita. Sul Brioss STD, senza note, la quota passa dal
  6,6 al 12,7%: sopra la soglia del 5% in tutti e due i casi, ma un file al
  limite la correzione l'avrebbe persa. Adesso `nero.spia` gira sul file
  pulito.
- **L'avviso sull'RGB** contava anche il logo dello studio nel cartiglio:
  adesso contano solo le immagini disegnate sul DT
  (`tracciati.immagini_nel_riquadro`), e dal file pulito le immagini tolte
  spariscono anche dalle risorse.

Cosa si toglie e cosa no, misurato sui dieci flowpack del parco: **dentro il
DT la resa e' identica al pixel** su tutti, e fuori non resta niente oltre i
5 mm, salvo le linee del DT che escono dallo steso (sul Brioss STD il bordo
dell'area di stampa, sul Choco Fresh il tratteggio sotto la pinna).

- Un oggetto che **tocca** il DT resta intero. Si toglie solo quello che sta
  tutto fuori: tracciati, immagini, form, scritte.
- Un tracciato solo puo' disegnare il DT e, nello stesso colpo, la vista
  tecnica accanto: sul Kinder Country la penna del DT traccia anche la vista
  interna. Si tolgono i **sottotracciati** tutti fuori - un sottotracciato non
  tocca niente fuori dal suo riquadro, ne' col riempimento ne' col tratto -
  e dentro non cambia un pixel.
- Le **scritte** si stimano per eccesso, un glifo largo un corpo e mezzo,
  senza leggere il font: una nota stimata troppo grande resta, una scritta
  della grafica tolta sarebbe un danno. Se un blocco di testo ha scritte
  dentro e fuori - sul Kinder Country "Bar Code Area" sul DT e le didascalie
  delle copie tecniche sotto - quelle fuori non si tolgono ma si rendono
  **invisibili** (modo 3), perche' togliendole le altre si sposterebbero.
- Un **form** si toglie se il suo riquadro dichiarato sta fuori; se sta a
  cavallo, dentro si pota solo se e' disegnato una volta sola e da un posto
  solo, perche' una seconda copia starebbe altrove.
- Il **richiamo** di una nota tocca il DT, quindi resta: la sua linea la
  spegne il livello DT come tratto, ma il pallino in fondo, un pieno, restava
  grafica. Un pieno piccolo (fino a 3 mm) sulla punta interna di un tratto
  che esce dal DT - basta un millimetro - e' la testa di un richiamo, e va
  via con la nota: sul B-ready 9 pallini neri da 0,7 mm. Se il pallino non
  sta sulla punta di nessun tratto non si tocca: sul B-ready ne restava uno,
  orfano nel template, e adesso va via con le didascalie del box area in cui
  sta (vedi *Tolto il box, via anche la sua didascalia*).

Costa una passata di pypdf sul flusso, la stessa delle coperture: da 0,2 a
6 secondi, Colazione il piu' caro. E visto che la passata c'e' comunque, per
nome si tolgono anche le lastre che **disegnano** il DT, non piu' le sole
coperture: vedi *Le coperture si tolgono per nome, non per euristica*.

Sul parco, tredici file contro la versione di prima: **dodici GLB identici al
byte**. Il tredicesimo, il KMS Display, cambia 6.483 pixel della texture e
nessuno dentro la fustella: e' il logo FERRERO del cartiglio, che il vassoio
si portava dietro perche' la sua texture e' il foglio intero. Quello che
cambia davvero sono le penne del DT - sul Kinder Cards 9 tratti spenti invece
di 3734, sul Choco Fresh 1 invece di 4942 - e la quota del nero, vedi *La `k`
nera si rimette dalla lastra*.

E il caso per cui e' nata, provato: il Kinder Cards col cartiglio riempito di
colore. Col codice di prima il blocco piu' colorato era il cartiglio, e ne
usciva un pack di **28 x 34 mm** con la texture della legenda; adesso esce il
Kinder Cards, **148 x 108**.

### Il foglio nel verso della grafica, prima di risolverlo

**Uno steso deve dare lo stesso pack comunque stia sulla tavola da disegno** -
girato di 90, 180 o 270 gradi, spostato, con qualche aggiunta tecnica intorno.
Come un DT sta sulla tavola lo decide chi impagina, e non e' il pack.

Il caso che l'ha imposto: il **Kinder Pingui T6** arriva in due impaginati.
Sul FERRERO_1742… il foglio e' dritto sulla grafica e le scritte tecniche -
*OUTSIDE VIEW*, le quote - stanno capovolte; sul **KPI_T6_base** e' dritto il
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
si misurava in due telai diversi. Un KC T8 salvato con `/Rotate 90` da' lo
stesso modello dell'originale, al pixel. Da li' in avanti
tutto - quote, colata, nero, texture, testate - lavora sul foglio girato, e il
riquadro della colata indicato dall'agente gira con lui
(`artwork.riquadro_girato`).

Il verso lo da' il **testo vivo** (`tracciati.verso_grafica`), e non il
disegno tecnico, che sul KPI_T6_base e' dritto proprio mentre la grafica e'
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
  dritto col fronte: sul Nutella Donut girato di 90 gradi il fronte era la
  faccia di PREPARAZIONE, e il cielo capovolto l'ha detto;
- **flowpack** (`server.flowpack_sulla_grafica`): vota la fascia del fronte
  (`flowpack.fronte_in_pagina`), e il giro vale se sullo steso girato
  l'analisi si risolve senza ripiego e il fronte si legge dritto. Il solutore
  i 90 gradi li reggeva gia' - traspone i suoi ingressi - ma la texture
  seguiva il foglio: girato di mezzo giro, il Milch-Schnitte usciva a testa in
  giu'; girato di un quarto il KP T1 Mandarino perdeva la fascia rossa,
  perche' la colata si allinea su un'onda orizzontale e verticale si
  incollava storta - con un errore sotto il mezzo millimetro, cioe' senza
  nessun allarme. Un caso calibrato non passa di qui: le sue quote sono
  scritte a mano sul foglio com'e'.

Se sul foglio com'e' l'astuccio **non si risolve**, prima di arrendersi lo si
prova girato: il solutore conosce meglio certi versi di altri. Il KC T8 girato
di 90 gradi non si costruiva ("i fianchi non tornano con la profondita'"),
girato si'. Lo stesso per il **vassoio** (`vassoio.riconosci_sulla_tavola`): la
griglia si riconosce in un verso solo - cinque colonne e tre fasce - e il KMS
Display girato di un quarto ne aveva tre e cinque; se non torna si prova il
foglio girato di 90 e 270 gradi, ma solo quando il vassoio e' dichiarato,
perche' la prova la pagherebbe ogni astuccio e ogni flowpack. Mezzo giro
invece il vassoio lo regge da se': e' simmetrico, e quale testata va davanti
lo dicono le altezze (`vassoio.testata_davanti`) - anche di un decimo di
millimetro, 40,5 contro 40,6 sul KMS Display, perche' con la nord di serie
davanti andava la testata che stava in alto sulla TAVOLA.

**Il testo storto non vota.** Una scritta messa di sbieco e' un tratto della
grafica: sul fronte del K Brioss "RICICLAMI nella CARTA" sta a 303 gradi e,
col suo corpo grande, pesava piu' di tutto il testo dritto. Vota solo chi sta
entro 10 gradi da un multiplo di 90.

**Il limite: senza testo vivo il verso non si legge**, e il foglio resta com'e'
sulla tavola - il modello segue il foglio, come prima - e **lo si dice**:
"verso della grafica non letto ... il verso va controllato sul modello". E'
l'unico caso in cui il pack puo' ancora dipendere da come lo steso sta sulla
tavola. Sul parco il testo vivo sul fronte ce l'hanno tutti gli astucci e
sette flowpack su dodici; Kinder Country, Kinder Cards, Kinder Choco Fresh,
K Tronky e Kinder Bueno Dark hanno il marchio e le scritte vettorializzati.
Leggere il verso dalle lettere disegnate - la linea di base allineata, le
aste che sporgono - e' la strada per loro; con le poche lettere di un marchio
non e' affidabile, e un verso sbagliato con sicurezza e' peggio di uno
dichiarato non letto.

Provato girando la pagina dei file del parco di 90, 180 e 270 gradi e
costruendo ogni copia, cinque viste per modello contro quelle dell'originale:

    identiche al pixel in tutti e quattro i versi
      astucci   Pingui T6 (tutti e due gli impaginati), KC T8, Nutella Donut
      flowpack  KP T1 Mandarino, KP T1 Cheesecake, Milch-Schnitte T1,
                Colazione, Kinder Paradiso, K Brioss STD, K Brioss T10
    lo stesso vassoio, a meno di un pixel di ricampionamento
      vassoio   KMS Display (prima a 90 e 270 gradi non si costruiva)
    capovolti in due versi su quattro: senza testo vivo sul fronte
      flowpack  Kinder Country, Kinder Cards, Kinder Choco Fresh, K Tronky,
                Kinder Bueno Dark

E un file salvato con `/Rotate 90` - il KC T8 - da' il modello dell'originale.
Sul parco nel verso di sempre cambia un solo modello, il Nutella Donut, che
adesso si legge nel verso della sua grafica: vedi *Se i fianchi li portano
tutte e due, si vedono quelli stampati*.

### Il modello finito si gira: il marchio orizzontale e dritto

**Il marchio del fronte si legge sempre orizzontale e nel verso giusto.**
Quando il modello e' finito e verificato, lo si gira tutto intero attorno alla
normale del fronte - il fronte resta davanti, il centro al centro - finche'
l'alto della grafica punta in alto.

Il caso sono i flowpack. Il tubo si costruisce sempre **coricato**, l'asse
lungo la x e le pinne a destra e a sinistra, ma il marchio sta come sta sullo
steso: sul KP T1 Mandarino, sul Cheesecake, sui K Brioss, su Colazione, sul
Kinder Cards, sul Kinder Country, sul Kinder Choco Fresh e sul Nutella B-ready
il testo corre **attraverso** il passo, e sul pack coricato "Kinder Pingui" si
leggeva dall'alto in basso. Girati di un quarto, stanno **in piedi** con le
pinne in alto e in basso, come in mano. Milch-Schnitte, Paradiso, K Tronky e
Bueno Dark, col testo lungo il passo, restano coricati. Gli astucci, il vassoio
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

## Domande all'utente

| regola | dove |
|---|---|
| Su **ogni** PDF chiedere prima la tipologia: Cartotecnico, Flowpack, Vassoio espositore, Altro. La tipologia si dichiara, non si indovina — **e la dichiarazione vale anche quando dice di no**, vedi sotto. | pannello del frontend + `analyze_pdf(pdf, kind)` |
| Solo cartotecnico: chiedere **di quanti pezzi** e' fatto il pack, digitato e senza valore proposto. **Ogni pezzo e' un PDF**: se ne sono arrivati meno si chiedono gli altri, se di piu' ci si ferma. Vedi *Il cartotecnico dice di quanti pezzi e' fatto*. | pannello `pezzi`, `pezzi` nell'intestazione; `server.in_piu_pezzi` |
| Solo flowpack: chiedere il **numero esatto** di dentini, digitato dall'utente. Nessuna alternativa proposta, 0 = pinne lisce. | campo numerico senza valore predefinito |
| Solo flowpack: chiedere il **rigonfiamento** fra quattro opzioni: Rigido (1-3), Medio (4-6), Morbido (7-10), "Scegli tu". | `gonfiore()` in `server.py` |
| Solo flowpack: chiedere l'**apertura delle pinne**, da 1 a 3. Non si deduce dal rigonfiamento. | cursore `pinne`, `build_flowpack` |
| Solo flowpack: chiedere se il **film avvolge una scatola**. | casella `scatola`, `parametri_costruzione.avvolge_scatola` |

### Il cartotecnico dice di quanti pezzi e' fatto

Scelto **Cartotecnico**, la pagina chiede di quanti pezzi e' fatto il pack, e
il numero va digitato: come i dentini, non si deduce. Ogni pezzo e' un PDF,
e il risolutore lo deve sapere prima di cominciare - un astuccio e' un file
solo, la coppa col tappo sono due, lo sleeve e il tappo, e da un file solo
non c'e' modo di sapere che l'altro esiste. Se i PDF caricati sono meno dei
pezzi la pagina chiede gli altri, e li aggiunge a quelli che ci sono; se
sono di piu' si ferma. Il server ricontrolla: `pezzi` nell'intestazione deve
essere il numero dei PDF arrivati, o la richiesta torna indietro.

- **Un pezzo**: l'astuccio, come sempre - ma prima si guarda se e' lo steso
  di un cono, dai soli tratti, in due decimi di secondo (`coppa.e_un_cono`):
  sul cono Camy il solutore astuccio trovava fra le icone un "astuccio" di
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

Nello stesso pannello la pagina chiede lo **spessore della carta**, da 1 a
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
0,45 l'astuccio (`PACK3D_SPESSORE_CRT`), 0,35 la coppa (dal cartiglio del
Nutella POT), 0,10 il cono, e i modelli restano quelli di prima byte per
byte.

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
| 3 | meta' perimetro: la pinna e' piu' alta del pack | il caso normale, il tubo si appiattisce. Milch-Schnitte |
| 2 | in mezzo | il prodotto occupa quasi tutta la sezione ma lascia respiro alle estremita' |
| 1 | quanto la faccia del pack, senza svaso | il film avvolge un corpo rigido fino alla saldatura: non c'e' niente da appiattire. Kinder Brioss |

Il rigonfiamento e' una **scala 1-10**, non tre gradini: Rigido 1-3 (pack teso e
aderente, aria minima), Medio 4-6 (volume standard, leggero cuscino d'aria),
Morbido 7-10 (volumetrico e visibilmente gonfio, gas o liquidi). I parametri di
forma si interpolano sul livello.

Riferimenti: FULFIL = morbido, Milch-Schnitte e Kinder Bueno Dark = rigido.

Attenzione pero': Milch-Schnitte e' film teso su un prodotto, non su una
scatola, e **non e' l'estremo rigido della scala**. Kinder Brioss lo e' di
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
flowpack e restituisce numeri plausibili ma sbagliati. Su Kinder Bueno Dark
dava 275,0 x 101,9 x 31,0 invece di 150,5 x 41,0.

**Perche' i dentini non si deducono:** il passo del dente varia enormemente.

| | bordo pinna | denti | base |
|---|---|---|---|
| Milch-Schnitte T1 | 55 mm | 30 | 1,83 mm |
| Kinder Bueno Dark | 181,5 mm | 30 | 6,05 mm |

Fattore 3,3 a parita' di conteggio. Ogni tentativo di calcolarli e' sbagliato.

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
sbagliare: il criterio del colore ha cancellato il logo `Brioss`, la tabella
nutrizionale e il testo legale del K Brioss STD — il 4,4% del foglio — perche'
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
Kinder perde l'ombra sulle gocce e diventa una macchia di ciano piatto, e a
valle non si recupera. Vedi *La grafica va in quadricromia, non in RGB*.

Nello stesso spirito: la **GDA** appartiene al disegno tecnico e nel livello
della grafica non va mai messa. Vedi *La GDA sta nel disegno tecnico*.

## Regole comuni a tutte le tipologie

- **Il modello segue la GRAFICA, non il disegno tecnico.** Sono due cose
  diverse: il DT dice come e' impaginato il foglio, la grafica dice come si
  legge il pack in mano. Su un astuccio Nutella Donut il pannello fronte ha
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
  da zero, e la falda del retro del Pingui T6 finiva a testa in giu'.
- **Il marchio `kinder` e' `k` NERA + `inder` ARANCIO KINDER.** Due colori, e
  vanno tutti e due: la `k` in nero, le altre cinque lettere nell'arancio di
  marchio, che nei file e' una tinta piatta col suo nome — `Kinder ORANGE`,
  `226983 Kinder ORANGE`. E' l'invariante piu' facile da controllare di tutto
  il parco: si guarda il marchio e si sa subito se il render tiene.

  Quando non torna dice sempre la stessa cosa: la **sovrastampa non e' stata
  simulata**. Sul K Brioss STD la `k` esce azzurra, perche' e' costruita come
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
  Sulla coppa Nutella la miniatura da' residuo **0,000 mm** contro **0,564** del
  contorno sotto la grafica. Attenzione: e' in scala ridotta, quindi **forma e
  proporzioni dalla miniatura, scala dal disegno grande o dalle quote**.

  Le sue **quote** sono il riscontro piu' forte che esista: numeri scritti da
  chi ha progettato il pack, non dedotti da noi. Quando sono testo le legge
  `quote.py` - catene allineate sullo stesso asse che sommano alla misura
  totale, come i `20 | 37,5 | 215 | 37,5 | 20 = 330` di Colazione - e la
  costruzione dice se le misure del disegno tornano. Quando sono
  vettorializzate, come sul K Tronky, le legge solo un occhio: lo strumento
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
| K Brioss **Promo** | 341,31 / 345,15 / 348,31 | 0,67 mm | tre pieghe |
| K Brioss **STD** | 341,31 / 344,81 / 348,31 | 0,00 mm | fuse in una |

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
   per riconoscere, mai per strappare**. Negli artwork Ferrero questi numeri
   ricorrono: Pantone 3405 C = Technical Drawing, 346 C = Dimensions,
   571 C = Print Free Area, 350 C = Best Before Area, 341 C = Bar Code Area,
   1565 C = COVERED Area. Anche `All` e' tecnica.

   **Ma ricorrono meno di quanto sembri, ed e' misurato.** Su K Colazione Piu'
   il registro sbaglia due volte su due: `350 C` li' e' il **disegno tecnico**,
   `346 C` e' la **BEST BEFORE AREA**. E fidarsene per strappare costa: sul
   cartotecnico Pingui T6, strappare le lastre che il registro chiama tecniche
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

    K Brioss STD   il logo `Brioss`, la tabella nutrizionale, "CON LATTE" e
                   il testo legale — il 4,4% del foglio
    K Pingui T6    il bollino "x6" e l'icona del pack
    K Brioss       lo 0,75% del foglio, tutto grafica

Non era una soglia sbagliata, e non si aggiusta con una soglia migliore: **una
lastra tecnica usa i colori che usa anche la grafica**. Sul K Brioss STD
l'unica tinta "tecnica" rimasta era `(0, 174, 239)`, cioe' **ciano di processo
al 100%** — lo stesso ciano del logo `Brioss`. Il registro `All` e' nero come
il testo legale; la Pantone di servizio e' la stessa del marchio. Nessuna
soglia separa due cose che hanno lo stesso colore, e la campionatura delle
tinte piatte (`tracciati.piatte`) aiuta ma non basta: prende il pieno, non le
percentuali, e su K Brioss otto tinte della grafica passavano lo stesso.

Quindi pieni e scritte **non si scelgono piu' per colore**. Restano i
**tratti**: un filo di capello e' tecnico per **geometria**, non per tinta, e
quella regola vale anche quando di livelli non ce n'e' nessuno.

### Chi lo dice davvero e' il livello

Se il file ha OCG che dicono cosa e' tecnico, si **spengono** prima di
rasterizzare (`strati.senza_tecnici`), e quel che resta del DT fuori dai
livelli si spegne oggetto per oggetto (*I due livelli li fa la costruzione*).
E' il livello 1-2 della scala qui sopra usato anche per la texture, non solo
per la diagnosi — che e' dove stava da sempre senza servire a niente.

Su K Brioss STD gli otto OCG si chiamano `background, code, cutter, layout,
legend, mat, preview, promo`: due sono tecnici e spegnendoli si toglie
l'1,61% — la fustella e il cartiglio, esattamente quelli — con il logo intero.

    K Brioss STD   euristica col colore   4,43% tolto, logo distrutto
                   livelli spenti         1,87% tolto, logo intero

Spegnere un livello e' una modifica di **dizionario** - l'OCG finisce in
`/OCProperties/D/OFF` - e non costa la passata di pypdf sul flusso di
contenuto, che su Colazione vale 7 secondi e 100 MB. **Attenzione**:
`PdfWriter().append()` perde `/OCProperties`, serve `PdfWriter(clone_from=...)`.

Da qui la richiesta a chi prepara il file: **il disegno tecnico su un livello
suo**, vedi *Cosa chiediamo a chi prepara l'artwork*. E' la stessa richiesta
della colata, e per la stessa ragione — quello che il file dichiara non si
deve indovinare.

Un nome di livello e' tecnico se e' un Processing Step ISO, se sta in
`techink.OCG_TECH` o se `techink.tecnica` lo riconosce — `Cutter` passa di li'.
Sul parco: K Brioss STD `Cutter, Legend`; KP T1 Mandarino `check, notes,
technical-drawing`; K Country `Guides and Grids, check`. Gli altri sei file
livelli non ne hanno, e per loro resta la regola dei tratti.

### I due livelli li fa la costruzione, oggetto per oggetto

Il file i livelli li dichiara quando vuole: K Brioss STD `Cutter` e `Legend`,
KMS T1 `Fustella` e `Note`, Colazione nessuno. Quello che serve alla
costruzione invece sono sempre **due livelli**, e sempre gli stessi: il
**DT/note**, da cui si misura il pack e si controllano le UV, e la
**grafica**, da cui si prende la texture. Quando il file non li ha, li fa la
costruzione (`strati.dividi`), e li fa sugli **oggetti**, non sui pixel.

Prima non era cosi', ed era la texture che l'utente descriveva **"ritagliata in
piu' punti"**. Senza livelli il disegno tecnico si toglieva DOPO la resa: una
maschera sui tratti sottili, larga il tratto piu' 1,2 pt per parte, e il pixel
valido piu' vicino a riempire. Lungo ogni cordonatura spariva un millimetro di
grafica, rifatto coi bordi:

    Colazione    l'angolo del cedolino blu del marchio a gradini, e degli
                 incroci del retino delle saldature i puntini sul bianco
    KP T1        il bordo alto del foglio strappato
    ogni file    una riga di grafica stirata dove il DT l'attraversava

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
  (`strati._velo`, le linee da `strati.linee_dt`). Sul Kinder Pingui T1
  Cheesecake le due gole da 10 mm e le fasce coperte sono velate cosi',
  bianco al 50% dentro quattro form, senza nessun livello: sul modello pinne e
  fianchi uscivano sbiaditi. Sul T1 Mandarino, stesso DT, i veli non ci sono.
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
secondi, anche sui 32.757 percorsi di Colazione.

### La texture e' HD di serie

L'altra meta' di "ritagliata e sgranata" era la risoluzione. Sul piano Free di
Render la texture di un flowpack stava in **1700 px** di lato, e l'interfaccia
la qualita' alta non la chiedeva mai: i fogli grandi uscivano sotto i 100 dpi.
Il limite era la memoria, e sugli Spaces non c'e' piu'. Di serie adesso la
texture e' a **300 dpi**, con un tetto a **8192 px** di lato; `web` resta,
per chi vuole un GLB leggero, ed e' quella di prima.

    |                | prima            | adesso            | tempo      | GLB           |
    | Colazione      | 1219 x 1700  3,7 | 3897 x 5433  11,8 | 63 -> 109 s | 3,9 -> 5,3 MB |
    | K Brioss STD   | 1174 x 1700  4,0 | 3425 x 4960  11,8 | 16 -> 30 s  | 4,0 -> 5,9 MB |
    | KMS T1         | 1201 x 1134  7,9 | 1801 x 1700  11,8 | 11 -> 15 s  | 4,1 -> 4,3 MB |
    | Pingui T6 BOX  | fronte 1106  7,9 | fronte 1659  11,8 |  9 -> 9 s   | 0,5 -> 0,8 MB |
    | Display KMS    | 1209 x 1700      | 5846 x 8192       |  7 -> 13 s  | 1,1 -> 3,4 MB |

(px per mm dopo le dimensioni; tempi di analisi piu' costruzione, un file per
processo, su questo container.) Il picco di memoria arriva a 1,2 GB sul Brioss
STD: sugli Spaces non e' un tema.

Il tempo in piu' sta quasi tutto nelle **immagini con trasparenza** dentro la
grafica, non nei tratti: su Colazione a 100 dpi, spente le 21 immagini, la
resa passa da 11 a 2 secondi; spenti i 32.757 percorsi, da 11 a 10. E ritagliare la resa sul
solo foglio non aiuta, perche' le immagini stanno tutte dentro il foglio:
Colazione a 300 dpi fa 61 secondi pagina intera e 61 il foglio da solo.

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

Su un astuccio Nutella Donut la lastra si chiama `Water Based Gloss Varnish` e
copre tutto il pannello: la texture usciva rosa piena, con la grafica sotto e
invisibile. Il nome lo diceva senza ambiguita', ma nessuno lo leggeva: la
lettura per nome stava solo in `tools.classify_technical`, che e' uno strumento
per l'agente, e la costruzione deterministica strappava separazioni solo se un
caso calibrato le elencava a mano.

Adesso `artwork.senza_coperture` le strappa da sola, su ogni file, e lo dichiara
nei cartellini. **Solo le coperture**, pero', e la ragione e' misurata: strappare
per nome anche fustella e quote costa una passata di pypdf sul flusso di
contenuto, e su Colazione erano **7 secondi e 100 MB di picco in piu'** - 584
contro 484, cioe' oltre il tetto dei 512 - per togliere tratti che la maschera
del disegno tecnico prendeva gia'. Il giorno che un pack mostra una fustella
che l'euristica non prende, si allarga con quello in mano. (Oggi quei tratti
li spegne il livello DT in pdfium, oggetto per oggetto, e la passata di pypdf
resta per i soli pieni: vedi *I due livelli li fa la costruzione*.)

**Con la pulizia fuori dal DT la passata c'e' comunque**, e il costo non e'
piu' una ragione: per nome si tolgono adesso anche le lastre che DISEGNANO il
DT (`techink.disegno`: technical, dieline, cutter, crease, fustella,
dimension, legend...). Il caso che l'ha chiesto: sul Nutella B-ready T2 la
lastra `Technical Drawing light` dipinge anche una banda piena di 2 mm sul
fianco, contornata da due tratti del DT. I tratti li spegneva il livello DT, la
banda no - e' un pieno - e sul modello era una riga verde da un capo
all'altro.

Sul parco cambia un file solo, il Kinder Cards, e in meglio: dalla tacca di
fotocentratura sparisce il contorno verde, della stessa lastra. Gli altri
dodici escono identici al byte.

Non tutte le tecniche, pero', e anche questo e' misurato. Con la lista intera
di `techink.tecnica` sul parco cambiavano cinque texture: le **tinte imparate**
da un file (`LASTRE_NOTE`: il Pantone 346 e' le quote su un Kinder e grafica
su un altro) cancellavano il 9% di un pannello del Pingui T6 e mezzo punto del
KP Mandarino, e il registro `All`, che sul K Brioss STD dipinge anche testo, il
2% della sua texture. Restano fuori anche la tacca di fotocentratura, che si
stampa, e le sigle corte.

Attenzione a non leggerlo come "strappare costa memoria": dipende da cosa si
strappa. Togliere **tratti** aggiunge una passata e non alleggerisce il
rendering, quindi il picco sale. Togliere **pieni** toglie anche il lavoro di
dipingerli: le tre aree riservate di Colazione portano il picco da 613 a 473
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
comando costruiva lo stesso astuccio senza toglierci niente, e il Nutella Donut
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
`fisse`). E' la regola come l'ha detta l'utente dopo il Nutella B-ready T2:
"i box area vanno sempre tolti come la gda, anche quelli verdi".

**Per nome e' un box area ogni lastra che si chiama area** (`techink.area`,
la parola `area` intera), non solo le frasi di un elenco: sul B-ready c'e'
`PIN CODE Area`, che nell'elenco non c'era e restava. Nessun inchiostro si
chiama cosi'. L'unica eccezione e' la **promo**: l'`AREA PROMO` della legenda
del K Brioss (FERRERO_1765...) e' tutta la fascia gialla con "Scopri il mondo
di Quelli della COLAZIONE" e "VINCI l'esclusivo SET COLAZIONE", cioe' la
grafica della promo, che si stampa.

Stanno fra le **coperture** e non fra i soli nomi tecnici, per la ragione che
vale per la GDA: sono PIENI grandi quanto la casella, non tratti, e l'euristica
su spessore e colore un pieno non lo vede. Finche' sono state solo "nomi
tecnici", la texture di **K Colazione Piu'** usciva con due fasce `TEXT AREA`,
una `COVERED AREA` e un riquadro `BEST BEFORE AREA` stampati sul pack, a
lettere bianche.

##### Quando il file le nomina

Se la lastra si chiama per quello che e' — `Covered Area`, `GDA Area`, `Best
Before Area` — si strappa per nome, e il conto lo paga solo il file che ce
l'ha. Se sta su un livello con quel nome, si spegne il livello e non si paga
niente. Questa e' la strada buona, ed e' meta' di *Cosa chiediamo a chi prepara
l'artwork*.

##### Quando il file NON le nomina: la scritta dice quello che il nome tace

K Colazione Piu' non nomina niente. Nessun livello, e le lastre si chiamano
`PANTONE 1595 C`, `PANTONE 1565 C`, `PANTONE 346 C`: numeri di colore, non nomi
di mestiere.

**Il registro `LASTRE_NOTE` non serve, e mente.** E' costruito su altri file, e
su questo sbaglia due volte su due: dice `PANTONE 350 C = Best Before Area` e
li' quella lastra e' il **disegno tecnico**; dice `PANTONE 346 C = Dimensions`
e li' e' la **BEST BEFORE AREA**. E' la lezione di sempre, nella sua forma piu'
netta: un numero Pantone e' un colore, e **un colore non dice mai a cosa serve
una lastra**.

Misurato, per togliersi la tentazione: strappare tutte le separazioni che il
registro chiama tecniche sul cartotecnico Pingui T6 fa sparire le aree
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
sotto**. La grafica di Colazione resta intera — logo, wordmark, wafer, tazza,
bollino `x10`, `100% LATTE ITALIANO` — e le tre aree spariscono.

Sul parco lo stesso passaggio ripulisce anche l'astuccio **Kinder Brioss Latte
e cacao**, che aveva una fascia `COVERED AREA` sul fianco sinistro e un
riquadro `BEST BEFORE AREA` a destra: via quelle due, e restano interi il logo
`Brioss`, il bollino `x10`, i pannelli promo con i QR code e il
`100% LATTE ITALIANO`. Sei GLB su otto non cambiano di un byte, e i due che
cambiano sono esattamente questi.

**Il prefiltro.** Prima di estrarre il testo con pypdf si guarda se nel testo
della pagina compare la parola `area`. Il testo lo legge **pdfium**, che
decodifica i font e scende nei form: costa da 0,01 a 0,15 secondi, contro i
2,9 che l'estrazione di pypdf costa su ogni K Brioss STD. Prima si cercava
`AREA` nei byte grezzi del flusso della pagina, e un font a glifi codificati
la nascondeva: sul **Kinder Paradiso T1** la legenda dice "Covered Area",
"Print Free Area", "Best Before Area", "Bar Code Area" e "Pin code area", il
prefiltro diceva di no, e i cinque box - la fascia verde acqua, quella
arancione, i due verdi e il quadratino rosa - restavano stampati sul pack.
Stessa cosa sull'astuccio **Pingui T6**, che ha "Neutral Area" e "Best Before
Area" in legenda. La parola si cerca anche dentro altre, perche' pdfium su una
didascalia girata e spezzata restituisce "BESAREA": un falso si' costa una
lettura, un falso no costa un box stampato.

Adesso il Paradiso impara dalla legenda Covered = 1565 C, Print Free = 571 C,
Best Before = 346 C, Bar Code = 3405 C, Pin code = 7436 C, e il Pingui T6
Neutral = 571 C - la stessa lastra che l'agente toglieva a occhio, vedi
sotto - e Best Before = 346 C. Sul Paradiso spariscono tutti i box, e logo,
prodotto, "FATTA CON LATTE FRESCO" e l'icona del riciclo restano interi; sul
Pingui T6 sparisce il box verde nella fascia rossa del retro, e il fronte -
logo, bollino `x6`, QR code - non cambia di un pixel.

**Su ogni file, anche con i livelli tecnici.** All'inizio la ricerca partiva
solo sui file senza livelli tecnici, per risparmiare la lettura del testo. Sul
Kinder Country e' stato un errore: i suoi livelli tecnici sono `Check` e
`Guides and grids`, i box non ci stanno, e i due box verdi `Best Before Area`
e `Bar Code Area` - PANTONE 346 C e 3405 C - restavano stampati con le loro
scritte. Adesso la ricerca parte sempre; il prefiltro sulla parola `AREA` la
tiene a zero sui file che non la scrivono, e sul parco costa 1,3-2,2 secondi
ai quattro che la scrivono e hanno i livelli.

**Si guarda al centro della scritta, non dove comincia.** "Bar Code Area" sul
Kinder Country e' girata e comincia a un millimetro dal bordo del suo box: i
2 mm attorno all'inizio erano pieni al 57%, sotto la soglia del 60, e il box
restava. La posizione, la direzione e il corpo si leggono dalle due matrici
del testo (`cm` e `tm`, non la sola `tm`), la lunghezza si stima a 0,55 corpi
per carattere: basta a trovare il centro, e li' il box e' pieno all'81%.

**E si controlla pypdf.** A volte ripete una scritta con la posizione di
un'altra: sul Kinder Cards T2 "Best Before Area" torna una seconda volta sulla
banda rossa, dove non c'e' scritto niente, e sotto c'era il **Kinder ORANGE**
- la grafica. Una didascalia vale solo se pdfium vede davvero un oggetto testo
dove pypdf dice che comincia (`techink._oggetti`).

**Il costo, detto per intero.** Sul parco i file senza etichette restano al
loro tempo — K Brioss STD 1,9 -> 2,0 s, crt_nuovo 2,4 -> 2,4, vernice 4,1 ->
3,8 — mentre quelli che le hanno pagano: **Brioss Latte e cacao 0,9 -> 4,5
s**, **Colazione 2,1 -> 19,7 s**. Quei diciotto secondi sono quasi tutti lo
strappo delle tre lastre, che su un flusso da 3,6 MB e' la parte cara; la
lettura del testo ne vale 3,8 e la passata `tiffsep` uno.

E' tanto, e su un piano Free a 0,1 CPU si sente. In cambio il pack non esce
con `TEXT AREA` scritto sopra, e la memoria **scende**: sul solo Colazione il
picco va da **613 a 473 MB**, cioe' da sopra a sotto il tetto dei 512 —
togliere tre lastre piene dal flusso costa meno di quanto costi renderle.

##### Quando il nome sta solo in legenda: il campione davanti alla scritta

Sul Kinder Country la fascia arancione a tratteggio sotto la pinna non ha
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
da': Country `COVERED Area` = 1565 C, `Best Before Area` = 346 C, `Bar Code
Area` = 3405 C; Colazione e K Brioss `TEXT AREA` = 1595 C, `COVERED AREA` =
1565 C; Paradiso e Pingui T6 come sopra, nel prefiltro. Le legende del
B-ready e del Kinder Cards danno le lastre che gia' si chiamano area. Una legenda col campione dietro la scritta, o lontano, non da'
niente: si perde un'occasione, non si strappa la lastra sbagliata.

##### Quando il file non le scrive nemmeno: allora si guarda

Se il nome dell'area non si legge ne' sopra il riquadro ne' in un campione di
legenda, non c'e' piu' niente da leggere. Era il caso del Kinder Bueno Dark T2
e del cartotecnico Pingui T6 prima che si leggesse il campione: il Pingui T6
adesso lo prende (vedi *Il prefiltro*), il Bueno Dark T2 non e' nel parco di
prova e non e' verificato.
A **occhio** pero' sono ovvie: un rettangolo pieno, verde o arancione,
appoggiato sulle falde.

Quindi si guarda, ed e' lavoro dell'agente — *il modello dice DOVE, il codice
fa COSA*, vedi *Cosa passare al modello, e cosa no*. Lo strumento e'
`tools.area_riservata`: prende un **riquadro in mm** indicato a occhio, cerca
quale lastra ci mette l'inchiostro pieno, e la toglie per nome. Il bordo esatto
non lo decide l'agente, lo decide la lastra: sbagliare il riquadro di **3 mm**
in dentro o in fuori da lo stesso risultato, misurato sul Pingui T6.

**La conferma e' l'immagine, e non puo' essere un numero.** Puntare la fascia
rossa del Pingui invece della falda verde da' `Pantone Warm Red C` pieno al
100% e al 3,29% del foglio; la vera area riservata, `Pantone 571 C`, da' pieno
al 100% e 3,08%. Indistinguibili. E su Colazione la fascia `TEXT AREA` copre il
6,5% del foglio mentre `Kinder ORANGE`, che e' grafica, il 7,9%: **nessuna
soglia separa le due cose**. Per questo lo strumento restituisce il foglio in
grigio con in **rosso tutto quello che quella lastra dipinge**, e l'istruzione
e' guardare: se il rosso tocca un logo, una foto o il fondo del pack, la
proposta si lascia cadere. Il rosso su fondo a colori non si leggeva — il
Pingui ha mezza grafica rossa — quindi la base va in grigio e tutto cio' che
resta colorato e' la lastra.

Le lastre confermate viaggiano in `parametri_costruzione.aree_riservate` e la
costruzione le strappa insieme alle altre, una passata sola: `aree_da_agente`
in `server.py`, come `livello_da_agente` e gli altri. Senza quell'elenco il
file resta com'era, che e' il comportamento di sempre.

Sul Pingui T6 sparisce il 9,7% della texture — i blocchi sulle falde e il
riquadro nella fascia rossa — e restano interi il logo, i due bollini `x6`, il
`FATTO CON LATTE FRESCO`, la bustina e il QR code. Che e' esattamente quello
che il registro di lastre note portava via.

##### Tolto il box, via anche la sua didascalia

Tolta la lastra resta la **scritta**, quando non e' in bianco. Sul Kinder
Cards T2 `Best Before Area` e `POSITIONING AREA FOR EAN CODE (if requested)`
sono in marrone scuro, CMYK 0/81/100/77: via i riquadri verdi, le due scritte
restavano stampate sui fianchi del pack. Sul Nutella B-ready T2, tolti i box
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
  casella, e quella del codice a barre del Kinder Cards e' in curve, 38
  tracciati. Una scritta, o un **segno** - un tracciato che copre meno di un
  quarto del box (`QUOTA_SEGNO`): una lettera in curve, il pallino di un
  richiamo - tutto dentro il riquadro e di quel colore. Un tracciato piu'
  grande e' un fondo, e resta: sul K Brioss (FERRERO_1765...) le didascalie
  sono bianche, e dentro la Best Before Area c'e' il riquadro bianco dove si
  stampera' la data. Un codice a barre vero, nero, resta dov'e' se la
  didascalia e' di un'altra tinta; e senza una didascalia scritta non si
  impara nessun colore e non si toglie niente.

L'area **coperta** e' l'eccezione: e' la fascia che la pinna nasconde, e sotto
la grafica continua - sul Kinder Cards la cialda e la banda rossa. Si toglie
come le altre, ma dentro si spegne solo il testo che dice il suo nome, e il
colore si impara solo dai box **vuoti per definizione** (`techink.vuota`):
il posto di un testo, di un codice, di una data, o dove non si stampa - TEXT,
GDA, BEST BEFORE, BAR CODE, EAN, PIN CODE, LOT, PRINT FREE, NEUTRAL. Ogni
altra area, anche una che non si conosce - una `Emboss Area`, una `Varnish
Free Area` - si tratta come la coperta: puo' avere grafica sotto.

Sul B-ready vanno nel livello DT 15 oggetti: le dodici scritte rosso bruno,
"BEST BEFORE AREA", "EAN CODE" e il pallino nero orfano, che ha il colore di
quelle due. Sul Kinder Country 2, "Best Before Area" e "Bar Code Area"; sul
Kinder Cards restano le 39 di prima. Solo dentro i riquadri **tolti**: la
didascalia di un box che nessuno ha riconosciuto resta con lui, perche' un
riquadro senza nome sembrerebbe grafica.

##### Lo spazio colore e' stato grafico

`strip_separations` riconosceva la lastra da togliere solo dall'operatore
`cs`. Ma lo spazio colore lo cambiano anche `g`, `rg` e `k` - che dipingono in
grigio, RGB e quadricromia - e lo rimette `Q` a com'era al `q`. Dopo il
riempimento di un'area riservata tutto quello che veniva in quadricromia con
`k` risultava ancora di quella lastra, e veniva tolto: **106 riempimenti su 112**
sul Kinder Cards, 41 su 51 su Colazione, 5 su 7 sulla vernice del Nutella
Donut. Per fortuna tutti fuori dal DT - il fondo del cartiglio, le pastiglie
della legenda - e infatti sul parco nessuna texture cambia; ma su un file con
la grafica dopo l'area riservata sarebbe sparita la grafica. Adesso lo stato
si segue come lo segue il PDF.

##### I box colorati via, i bianchi restano

"Vanno eliminati dalle grafiche tutti i box colorati - verde, arancio - e
lasciati quelli bianchi": e' la regola come l'ha detta l'utente col Kinder
Happy Hippo T1 (FERRERO_1579...), che ha il box verde `Best Before Area` in
mezzo al fronte.

I segnaposto hanno colori vivi apposta, per farsi vedere: sul Nutella B-ready
`Best Before Area` e `Bar Code Area` sono verdi, `TEXT Area` e `COVERED Area`
arancio, `PIN CODE Area` rosa; sul Happy Hippo il Best Before e' PANTONE 346 C,
verde, e la legenda lo dice. Tutti questi si tolgono, per le strade di sopra.

Un box **bianco** invece non e' un segnaposto: e' il posto stampato in bianco
dove la macchina scrivera' data e lotto - il Best Before del Milch-Schnitte T1,
46 x 17 col data matrix, o i riquadri del Kinder Bueno Dark - e si stampa.
Resta anche quando la sua lastra si chiama area: prima di strapparla si guarda
di che colore la dipinge il file, cioe' il colore a tinta piena dello spazio
alternativo della Separation (`techink.lastre_bianche`: Lab con L* da 94 in su
e a*, b* entro 6, o inchiostro al 4% al piu'). Se e' bianca resta, e il build
lo dice: "box bianchi lasciati". Provato su un PDF fatto apposta, un box verde
e uno bianco sullo stesso fondo rosso: il verde sparisce e sotto torna il
rosso, il bianco resta. Sul parco nessuna area riservata e' bianca, e nessun
modello cambia.

Non sono box i pannelli colorati della grafica: il riquadro giallo con le
frecce del B-ready e' l'istruzione di apertura, il blocco giallo sul retro del
Milch-Schnitte T1 e' la PANTONE 108 su cui va il testo legale. Si stampano e
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
114 kcal 6%" - che cambiano da un paese all'altro e sul modello non vanno. Sul
Nutella Donut e' l'icona dell'energia sul fianco, sul K Brioss il pannello
bianco con le cinque icone sul retro, sul Nutella B-ready l'icona dentro una
nota del grafico, fuori dal DT.

Non ha una lastra ne' un livello: sono tracciati e scritte sciolti nella
grafica, in quadricromia. Si riconosce dal **testo** (`techink.zone_gda`): da
ogni `kcal` si cresce sulle scritte vicine, meno di 7 mm fra l'una e l'altra,
ed e' GDA il gruppo che ha anche kJ e una percentuale e sta in 90 mm. Sul
Brioss le etichette delle icone - ENERGIA, GRASSI - sono vettorializzate, e fra
il titolo "Ciascuna porzione (27g) contiene:" e i valori restano 6 mm senza
testo: a 5 il titolo restava fuori.

**La tabella nutrizionale resta**: e' grafica e si stampa. Si riconosce da
quello che le icone non hanno mai - le colonne in grammi, `(g)`, e le righe di
proteine e carboidrati. Sul Nutella Donut il gruppo del retro, "(kJ / kcal)
(g) (g) (g)", resta intero.

Si toglie quello che sta nella zona - il gruppo allargato di 4 mm, il bordo
dell'icona - e il pannello su cui le scritte stanno, anche se sborda dal
margine, purche' non sia piu' grande di due volte la zona: il fondo bianco
arrotondato del Brioss si', il fondo rosso del retro no (`techink.dentro_gda`).
Per le scritte conta dove comincia la riga, non il riquadro che serve al DT,
che a ogni carattere da' la larghezza del glifo piu' largo: con quello le
scritte uscivano dalla zona e restavano stampate senza piu' il pannello sotto.
Sul Brioss vanno via 101 oggetti, sul Nutella Donut 14, e sotto torna il fondo,
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
flowpack. Ma il solutore astuccio risolve anche certi film: sul Kinder Happy
Hippo T1 la griglia 1 | 15 | 83 | 15 | 1 per 15 | 85 | 15 gli dava un astuccio
vwrap 52,5 x 51,2 x 9,7, e il flowpack non veniva mai provato. Il file pero' lo
dice da se': il cartiglio Artworkr dei Ferrero scrive "WRAPPING/FILM" nella
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
  identici alle aree tecniche. Applicandolo e' sparita la "k" di kinder e il
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
lo stesso colore: sul K Brioss STD la maschera ha cancellato le lettere di
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
lo spessore a zero, cioe' a filo di capello, cioe' tecnico. Sul K Brioss STD un
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

Il marchio e' `k` nera + `inder` arancio Kinder, e sul K Brioss STD la `k`
usciva azzurra. Non e' un errore del file: nelle sue separazioni quella `k` e'
nero al 100%, ma **nero in sovrastampa** sopra l'azzurro, e pdfium la
sovrastampa la ignora.

**La strada larga non funziona, ed e' misurato.** Rendere tutto il foglio con
Ghostscript e `-sOverprint=simulate` la `k` la fa nera, ma su **KP T1
Mandarino cancella il logo `kinder Pingui` e la scritta `MANDARINE`, e fa
azzurra la fascia rossa**: quel file ha solo tinte piatte e gs le compone
male. Il 16% della pagina cambia, e cambia in peggio. Niente interruttore
globale, quindi.

**La strada che funziona e' locale, e non indovina niente: la lastra del nero
dice dov'e' nero.** Dove la lastra e' piena e il render mette invece un colore
chiaro e saturo, il render ha torto, e si riporta il tono della lastra. Non si
inventa inchiostro: si mette quello che il file dichiara, e solo li'.

    K Brioss STD     nero pieno su 18.839 px, il render ne tradisce il 6,8%
    Brioss astuccio                                                   2,3%
    Colazione                                                         0,8%
    Pingui T6                                                         0,7%
    KP T1 Mandarino                                                   0,0%

Sul Brioss STD la zona tradita piu' grande e' proprio la `k`: 3.764 px su
4.938. Il difetto e' quello, non un'inezia sparsa.

**E l'orlo.** Il pieno si riporta dove la lastra supera l'85%, e l'orlo della
lettera - dove la lastra sfuma - restava com'era: il nero sfumato con
l'azzurro dipinto sopra, pixel scuri color petrolio, (30, 66, 71). A 1700 px
non si vedeva; in HD attorno alla `k` c'era un filo petrolio. Adesso si
riporta il tono della lastra anche li', a due pixel dal pieno tradito, dove la
lastra ha almeno il 10% e il pixel e' tinto: sul Brioss STD i pixel petrolio
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
difetto — su Colazione la riparazione muoverebbe 18 pixel, e su FERRERO
159013 il GLB resta identico dopo quasi sei secondi di passata.

**E la quota si conta sull'interno del pieno, sul solo DT.** Col bordo dentro
la quota dipendeva da quanta altra roba nera c'era sulla tavola: le scritte
nere della legenda e del cartiglio, che il render fa nere, la tenevano bassa.
Tolte le note fuori dal DT (vedi *Prima le quote, poi via tutto quello che sta
fuori dal DT*) sul K Brioss T10 il 3,2% e' diventato 13,5%, la correzione e'
partita, e sui bordi delle scritte nere sul giallo ha messo pixel neri a
scalini: la lastra, presa a 144 dpi e ingrandita, sborda di un pixel. Il
difetto vero, la `k` azzurra, e' tradito anche DENTRO la lettera; il bordo
no. Contata un pixel dentro dal bordo (`nero._traditi` con `interno`):

    K Brioss STD     10,2% sul foglio intero, 15,9% sul DT: si ripara
    K Brioss T10      0,1% e 0,7%: niente da riparare, GLB identico
    K Tronky T1      60,9%: le linee del DT, nere piene, che la riparazione
                     poi esclude col livello DT - GLB identico
    tutti gli altri   sotto l'1%

La soglia resta il cinque per cento, e adesso sta larga in mezzo.

**Niente prefiltro sul flag di sovrastampa**, e non per dimenticanza: tutti e
otto i file del parco la sovrastampa la dichiarano. Guardare `/OP` non scarta
nessuno. Il costo e' quindi la passata spia a 36 dpi su ogni build, da mezzo
secondo a uno e tre, piu' la passata a 144 dpi solo sopra soglia.

##### Ghostscript costa 105 MB anche a vuoto, e conta QUANDO lo chiami

Questa riparazione, appena messa, ha fatto morire il build del Kinder Pingui
T6 sul piano Free: `Failed to fetch` nel browser, che e' come si vede da fuori
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

**La colata Kinder.** L'ombra sotto l'onda del latte e le ombre delle gocce
sono immagini di ciano in sovrastampa sul rosso: in stampa ciano sul rosso fa
l'ombra rosso scuro, coprente esce un alone azzurro. Sul parco la colata e'
sempre fatta cosi' - la banda lunga e le due gocce - e di spazio colore in tre
modi diversi:

    DeviceN di solo Cyan      KMS, crt, Tronky, FERRERO 159/174/154/1742/1777,
                              KP Cheesecake, KB Dark, KC T8
    RGB indicizzato           Kinder Choco Fresh T1
    RGB ICC indicizzato       KP T1 Mandarino

Non e' LAB: lo spazio colore non c'entra, c'entra la sovrastampa. E prima
l'ombra si riparava solo col livello `Colata` o col riquadro indicato a occhio
(vedi *La colata si rimette con l'inchiostro del file*): sui file che non
avevano ne' l'uno ne' l'altro - crt, Tronky, i FERRERO - restava azzurra.

**La merendina del Kinder Choco Fresh T1.** La foto e' in RGB, e sopra, grande
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

L'ombra del KCF e del Mandarino e' RGB con la maschera, e la pagina del KCF e'
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

Sul KMS contro Ghostscript, che li' ha ragione perche' l'ombra e' DeviceN e
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
niente banda di Ghostscript, niente risorsa. Non e' solo risparmio. Sul KP T1
Mandarino Ghostscript diceva "ombra fustellata" e faceva sostituire la colata
del file con la risorsa, ma sotto l'ombra il PANTONE Warm Red c'e' al 90%,
nelle lastre senza immagini: era lui a cancellarlo, portandolo al 31%.

**Il flag di sovrastampa pdfium non lo espone**: si legge dal flusso di
contenuto, seguendo q/Q e gs anche dentro i form, e le immagini si accoppiano a
quelle di pdfium nell'ordine in cui si disegnano. Se i due elenchi non tornano
- quante sono, o le loro misure in pixel - non si tocca niente, e il modello lo
dice. Su ventitre file provati tornano sempre. Dentro un form pdfium da' i
confini delle immagini nelle coordinate del form: il riquadro sulla pagina si
fa componendo le matrici dei form, come in `dividi`.

**Il flusso non si legge con pypdf.** Sul K Brioss STD sono 231.000 operazioni
in 7 MB: tre secondi e mezzo solo per trovarne una manciata. Un'espressione
regolare che cerca i soli operatori che servono - q, Q, gs, Do e le immagini
in linea - e salta intere le stringhe, i commenti e i byte delle immagini da'
lo stesso elenco su tutti e ventitre i file, in mezzo secondo sul Brioss STD.
Un file senza nessuno stato grafico in sovrastampa non la paga nemmeno.

**Occhio ai booleani di pypdf**: `bool(BooleanObject(False))` e' `True`, perche'
la classe non ha `__bool__`. La prima ricognizione li leggeva cosi', e dava in
sovrastampa quasi tutte le immagini del parco: 20 su 21 su Colazione, 38 su 40
sul crt. Letti per valore (`strati._vero`) sono 0 e 12, e sono le colate.

### La grafica va in quadricromia, non in RGB

Un'immagine RGB in macchina la **converte chi stampa**, e il colore lo decide
lui e non il file. E' una regola della stampa, non del gusto, e il nostro
compito e' accorgersene e dirlo prima che l'utente guardi il modello
(`techink.avviso_rgb`, un decimo di secondo e niente in memoria).

**Qui c'era scritto che in RGB la sovrastampa non esiste, e che per questo la
colata usciva di ciano piatto. Era sbagliato.** Un oggetto RGB in sovrastampa
stampa la quadricromia e lascia stare le tinte piatte che trova: sul Kinder
Choco Fresh T1 e sul KP T1 Mandarino l'ombra della colata e' un'immagine RGB
indicizzata in sovrastampa sul rosso in tinta piatta, e il rosso sotto resta.
Sembrava di no perche' Ghostscript, sotto un'immagine RGB con una maschera
morbida, la tinta piatta la cancella: vedi *Un'immagine in sovrastampa si somma
a quello che trova*. L'avviso sull'RGB resta, ma per il colore: la colata non
c'entra piu'.

Si guardano le **immagini**, non gli spazi colore dichiarati, e per un motivo
misurato: uno spazio RGB dichiarato c'e' quasi sempre — sul K Tronky T1 ce n'e'
uno usato 23 volte, e quel file e' validato — perche' lo usa anche l'arte
tecnica, che dalla texture viene via comunque. Una immagine **grande** in RGB
invece e' grafica che si vede: sotto il mezzo megapixel si tace, sopra si
avvisa. Sul parco l'avviso esce su tre file — la colata del Pingui e due foto
di prodotto in RGB su altrettanti astucci Ferrero — e tace sui cinque validati.

Attenzione a non confondere **tre canali** con **RGB**: un `/DeviceN` di tre
inchiostri ha tre canali ed e' tinta piatta in tutto e per tutto, sovrastampa
compresa. Contano solo `/DeviceRGB`, `/CalRGB`, un `/ICCBased` con `N 3` e un
`/Indexed` che ha uno di questi per base.

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

## Il controllo visivo e' obbligatorio

Dopo ogni pulizia va **guardato** il confronto prima/dopo, non solo lette le
metriche. Le metriche dicono quanto hai tolto, non se hai tolto la cosa
sbagliata: sul Kinder Bueno T2 la K del logo e' sparita con tutti i numeri in
ordine, e me ne sono accorto solo perche' me l'ha detto l'utente.

Lo strumento `visual_check` restituisce l'immagine affiancata: va chiamato
sempre dopo `clean_artwork` e prima di costruire.

Priorita' negli errori: **un logo perso e' grave, un residuo tecnico no.** Nel
dubbio si toglie meno.

## Le verifiche: le UV sul DT prima, il fronte sul fronte dopo

Il lavoro va nell'ordine in cui lo si fa a mano: si costruisce dal DT, si
controlla che le UV del modello siano il DT steso, **poi** si spegne il livello
del DT, si accende quello della grafica e si mappa, e alla fine si controlla
che il fronte dell'AW stia sul fronte del modello. Le verifiche stanno in
`verifica.py`, girano su ogni costruzione di **tutte e tre le famiglie**, e
il loro esito va negli avvisi.

**1. Le UV sul DT, prima della mappatura.** Per un flowpack lungo il passo le
UV non si muovono mai ai confini - `L/2 + end_fin` non cambia, e sulla spalla
il film si ridistribuisce solo fra la saldatura e la sezione piena - quindi
quello che puo' sbagliare sono i due confini delle testate: dove comincia la
pinna e dove comincia il prodotto. Tutti e due devono cadere su una linea del
DT, dai due lati. Quando la spalla comincia dentro il prodotto la riga lo
dice, e non e' uno scarto: le linee restano sulle loro. Lungo il giro c'era
gia' la misura degli spigoli contro le pieghe del disegno (*Verificare il
modello mappato contro l'AW*). Per un astuccio le UV sono i quattro angoli del
ritaglio, e il confronto e' sulle proporzioni: la faccia e il pannello del DT
devono avere gli stessi lati. Per un vassoio le UV sono la posizione sullo
steso, e si confrontano direttamente: il bordo esterno di ogni parete,
riportato in mm con la scala vera della texture, deve cadere sulla linea della
sua fascia del DT (`verifica.vassoio`).

**2. Il fronte sul fronte, dopo.** Il centro del pannello fronte dell'AW - dove
lo dice il DT - deve cadere al centro della faccia fronte del modello, con la
normale verso il davanti, e **non specchiato**. La regola di mano: vista da
fuori la texture ha la u a destra e la v in giu', perche' glTF conta le v
dall'alto, quindi `du x dv` punta dentro; dove punta fuori, la grafica e'
specchiata. E in quel punto, e in quattro attorno, la texture deve essere la
grafica dell'AW: un giro di troppo fra pagina e texture lo tradisce subito,
perche' una grafica non e' mai uguale a se stessa girata. Sul vassoio il
fronte e' la testata che guarda davanti - la piu' bassa, vedi *Le testate del
vassoio* - e nessuna parete deve essere specchiata.

**E le quote scritte**, su tutte e tre: le misure del disegno contro le
catene di quote e la terna del cartiglio, quando si leggono come testo. Vedi
*Regole comuni a tutte le tipologie*.

**Hanno i denti, e sono stati provati.** Rimettendo la pinna dal margine su
KMS T1 la prima grida `UVW NON CORRISPONDE AL DT - il DT segna 8,0 mm, il
modello 6,9`. Girando la texture di 90 gradi invece che di 270 su KP T1 la
seconda grida `FRONTE NON SUL FRONTE`, con uno scarto di colore di 166 contro
i 5 della mappatura giusta. Le sonde del colore mediano su due millimetri: a
cinque pixel un gradiente con mezzo pixel di sfasamento dava 33 anche a
mappatura giusta. Sul display Milch-Schnitte, giusto, le pareti cadono sulle
loro fasce entro 0,3 mm; spostando le UV di 3 mm grida `UVW NON CORRISPONDE AL
DT - parete nord: il bordo cade 2,7 mm dentro la linea del disegno`,
specchiandole grida `FACCIA SPECCHIATA`, e girando il vassoio di 90 gradi
`FRONTE NON SUL FRONTE: nessuna testata guarda davanti`. Delle quote, provate
su catene e terne costruite apposta, grida la catena che somma giusto ma ha
pezzi diversi, e tace su quella che somma per caso.

Sul parco passano tutte e due quasi dappertutto, e dove no dicono una cosa
vera:

- **KCF T1** e **Kinder Country**: il DT non e' speculare sulle testate - 6
  mm da un taglio e 10 dall'altro sul primo, 10 e 7 sul secondo. Una
  saldatura e' disegnata corta o manca, il modello prende il rientro piu'
  stretto, e la verifica lo dice. E' il punto 4 di *Perche' un file nuovo
  non si costruisce*;
- **Nutella Donut**: cielo e fondo sul DT sono 36,9 mm, la faccia del solido
  38,1. La grafica di quelle falde si stira del 3%, e prima nessuno lo
  vedeva.

Nessuna cambia il modello: dicono se e' giusto, e quando non lo e' lo
gridano. Un modello plausibile e sbagliato e' il difetto peggiore che
questo progetto possa avere.

Sul flowpack ce n'e' una terza, dopo: **il film sulle testate**, quanto la
grafica si stira su pinne e spalle. Sta con la regola che la chiede, in *La
grafica sulle pinne: il film non si allunga*.

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
  originali ovunque altrove. Sul Kinder Bueno T2 significa rigenerare lo 0,6%
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
E' il caso delle aree riservate rimaste: sul cartotecnico Pingui T6 e sul
Kinder Bueno Dark T2 il nome dell'area sta solo nella legenda, non sopra il
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
pixel originali. Sul Kinder Bueno T2 sono lo 0,6% dell'immagine.

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

**4. Quello che non va mai al modello.** I loghi, la `k` nera di `kinder`, i
marchi, il testo di prodotto: non si rigenerano nemmeno dentro una maschera,
e se la maschera li tocca la maschera e' sbagliata. E nessuna misura: una
quota si misura, non si chiede a un'immagine.

**5. E il modello non copre mai quello che il file poteva dichiarare.**
Se manca il livello del disegno tecnico, la risposta e' *Cosa chiediamo a chi
prepara l'artwork*, non una chiamata API su ogni build. Il piano B costa una
chiamata e un rischio: si usa dove il file non poteva dire di meglio, non
dove non gliel'abbiamo chiesto.

## Perche' un file nuovo non si costruisce: la lista

Due file arrivati insieme, tutti e due fermi con lo stesso messaggio -
`saldature di testa non riconosciute` - e due cause che non c'entrano niente
l'una con l'altra. Da li' questa lista, che e' quella da girare a chi prepara
l'artwork **prima** di mandare un pack nuovo.

### 1. La fustella deve CHIUDERE un rettangolo

E' il riferimento da cui si misura tutto, e si riconosce senza euristiche:
**due orizzontali della stessa larghezza, due verticali della stessa altezza,
e i quattro lati che si coprono**. Non serve che gli estremi combacino — una
fustella sborda, e sul Kinder Choco Fresh la verticale di destra scende 6 mm
sotto l'orizzontale di sotto — serve che i quattro tratti chiudano.

Una tavola di rettangoli chiusi ne ha parecchi: la cornice del foglio, i
cartigli, i riquadri della legenda. Vince quello che **somiglia di piu'
all'ingombro stampato**, perche' la fustella e' il rettangolo in cui la
grafica sta. Vedi `flowpack.riquadro_fustella`.

### 2. La grafica non deve uscire dal tracciato

Sul Choco Fresh T1 esce: c'e' una striscia di fondo bianco che scende sotto la
fustella, e chi misura *lo stampato* invece della fustella trova un nastro di
**121 mm invece di 115**. Con quel numero le fasce non chiudono piu' e il file
non si costruisce. Oggi c'e' un secondo tentativo che ripiega sulla fustella,
ma costa otto secondi di rilettura dei tracciati: meglio non doverlo fare.

Se il fondo deve sbordare - e a volte deve, per l'abbondanza - la fustella
vada comunque tracciata chiusa, cosi' il secondo tentativo ha da leggere.

### 3. Le quote stanno FUORI dal tracciato, o su un livello loro

La linea di quota del Choco Fresh sta sopra il pack, disegnata con la stessa
penna della fustella, e misurando dagli estremi il nastro diventava 136,8 mm
invece di 115. Una quota dentro l'ingombro, con la penna del disegno, e' un
tratto indistinguibile da una cordonatura.

E' lo stesso identico discorso di *Cosa chiediamo a chi prepara l'artwork*:
quello che non si stampa va su un livello suo. `Dimensions` e' un nome che il
codice riconosce gia'.

### 4. Le saldature vanno disegnate per intero

Sempre sul Choco Fresh: la saldatura di sinistra e' tracciata a tutta altezza
(115 mm), quella di destra solo attraverso il corpo (95 mm). Due tratti che
descrivono la stessa cosa e sono lunghi diversi. Il solutore che cerca
"quattro verticali a tutta altezza" ne trova tre e si ferma.

Non e' pignoleria: da quella asimmetria non si capisce piu' se la linea corta
e' una saldatura o una cordonatura del corpo.

### 5. La tipologia va dichiarata quando non e' una di quelle note

Le famiglie che il codice risolve sono **astuccio**, **flowpack** e
**vassoio**. Un pack che non e' nessuna delle tre non va indovinato: il
display del Milch-Schnitte Raspberry cadeva nel ramo flowpack e usciva
`saldature di testa non riconosciute`, un messaggio che a chi ha in mano un
vassoio non dice niente. Vedi *La tipologia non riconosciuta e' un errore, non
un ripiego*.

### 6. Il confronto finale lo fa l'occhio, sul modello

Nessuna di queste regole sostituisce il passaggio finale: si apre il GLB e si
guarda. Le misure dicono che i conti tornano, non che il pack e' giusto — e
l'unica volta in cui una segnalazione di rotazione e' stata smentita, a
smentirla e' stato il modello aperto e guardato, non un numero. Vedi *Il
caso calibrato: Kinder Pingui T6 BOX*.

## Vassoi espositori

La terza famiglia: un **fondo** rettangolare con una parete attaccata a
ciascuno dei suoi quattro lati, e le alette agli angoli che tengono su le
pareti.

Si riconosce dalla griglia della fustella, e non per euristica: **cinque
colonne e tre fasce**, con le due colonne sottili fra fondo e pareti che sono
la cordonatura. Sul display Milch-Schnitte Raspberry:

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
  Milch-Schnitte, 40,5 e 40,6 - davanti resta la nord;
- **le verifiche**: ogni parete sulla sua fascia del DT e il fronte sul
  fronte (`verifica.vassoio`), e le quote scritte (`quote.riscontro_vassoio`).
  Sul Milch-Schnitte le pareti cadono sulle loro fasce entro 0,3 mm; le quote
  sono vettorializzate e non si leggono come testo, e lo si dice.

### Il contorno non e' un rettangolo, e il DT lo dice

La prima versione del vassoio faceva quattro rettangoli dalla griglia. Era
"completamente sbagliato" a vederlo, perche' il contorno di un display e'
sagomato: sul Milch-Schnitte i fianchi rientrano a meta' altezza e gli angoli
sporgono. Il DT sul foglio porta le quote — **346,5 x 466,5**, colonne
98,5 | 149,5 | 98,5 e fasce 40,0 | 386,5 | 40,0 — e il contorno va preso da
li', non inventato dalla griglia.

**Le cordonature orizzontali non stanno tutte alla stessa quota**: sul
Milch-Schnitte quella della colonna di mezzo sta a 148,3 e quelle delle colonne
laterali a 149,2, nove decimi piu' in basso. Non e' un errore del file, e' il
compenso dello spessore del cartoncino.

### Il foglio si riconosce da dove sta, non da quanto inchiostro ha

La sagoma della cartotecnica si prende dall'**impronta di stampa**, perche' la
penna della fustella ha interruzioni — sul Milch-Schnitte da 3 mm — e
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
dentro le lettere di `kinder`, un pannello chiaro in mezzo — non si raggiunge e
resta cartoncino, e non serve piu' tapparlo a posteriori con `fill_holes`. E il
tratto della fustella, che e' colorato, ferma la macchia da solo: dove la penna
c'e', anche un cartoncino stampato chiaro fino al taglio si salva.

**Il controllo che lo dice**: la misura dell'impronta va confrontata con il
riquadro della fustella, che viene dai vettori. Se ballano di piu' di 2 mm il
build lo scrive, invece di consegnare un modello piu' grande del pack.

### Una texture sola, e uno specchio solo

Lo steso intero e' **una** texture, con in fondo due righe di colore piatto per
l'interno e per il taglio; le UV sono la posizione nel piano. La piega sposta i
vertici e la grafica se li porta dietro, quindi non c'e' nessun ritaglio da
ruotare pannello per pannello.

**Piegando lo steso com'e', la stampa finisce dentro**: la faccia stampata
guardava in su e piegando in su va a guardare l'interno, e il marchio si legge
attraverso il cartone. Ci vuole uno specchio per rimetterla fuori, e **uno
solo**: con due — x e z — e' una rotazione, e torna specchiata.

**Le UV dell'interno e del taglio si misurano sulla TEXTURE, non sulla
sagoma.** Sono due griglie diverse: sul Milch-Schnitte la sagoma sta a 4 px/mm
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
quad per riga e' geometria pagata per niente: il Milch-Schnitte passa da
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
| fra il fondo e le pareti, lungo tutta la piega, un quarto di millimetro | KMS, Tronky | ogni pezzo messo al suo posto sulla griglia di pixel, e non sulla sua piega |
| su ogni spigolo, un millimetro e mezzo | Tronky | i fianchi sono 3 mm piu' corti del fondo — lo spessore, che il DT compensa — e finivano prima dello spigolo |
| fra la faccia esterna e quella interna | tutti | la costa solo sui capi delle fasce: le teste dei fianchi e i lati del fronte restavano aperti |
| due righe a trattini sul retro, dentro | Tronky | le alette mezzo millimetro fuori dalla parete, coi bordi a vista |

Come si costruisce il blocco (`vassoio.corpo`, lo stesso per il vassoio e per
il display):

1. **ogni pezzo si ancora alla sua cordonatura**: il suo bordo sulla piega va
   esattamente sulla piega. E il bordo e' fin dove arriva davvero la sua maglia
   (`vassoio._ingombro`), non l'ingombro dei pixel: un pixel isolato sul
   contorno — l'antialias di un angolo — allarga i pixel ma non la maglia.
   Ancorato ai pixel, il fianco ovest del KMS usciva un quarto di millimetro
   piu' basso del DT, e sul fondo lo stesso quarto e' una feritoia;
2. **fianchi, fronte e retro si stirano fino agli spigoli**: la loro faccia
   esterna arriva sulla faccia esterna della parete accanto, e la pelle del
   blocco e' continua. Sul Tronky la grafica dei fianchi si allunga dell'1,5%,
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
   piu' bassa — il fronte del KMS — l'aletta sporge sopra ed e' un pannello a
   se', chiuso dalle sue coste: la riga chiara sopra il fronte basso del KMS e'
   la costa del cartone, e c'e' anche sul pack vero;
6. **le misure sono quelle del DT, non dei pixel**: il fondo e l'altezza di
   ogni parete si stirano sulle quote del disegno, dalla piega al bordo. Sul
   vassoio le pieghe delle colonne stanno a META' della cordonatura, come la
   maglia (`vassoio.misure_blocco`): le fasce della griglia danno un fondo di
   145,5 mm, e fra le due meta' ce ne sono 147,5. Cosi' il blocco esce uguale
   comunque stia il foglio sulla tavola: sul Tronky, preso dai pixel, la cima
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
spigolo, mancano 1.50 mm". Sul Milch-Schnitte e sul Tronky: 0,00 mm, e il
blocco del Tronky e' lo stesso al centesimo nei quattro versi del foglio.

## Display con plancia

La quarta famiglia, e sta accanto al vassoio: una scatola che arriva CHIUSA e
che, aperta, perde dei pezzi e diventa un espositore da banco, con uno dei
pezzi in piedi dietro al prodotto a fare da cartello. Quel pezzo e' la
**plancia**. Il caso e' il Tronky T48, Ferrero CT4977 "Display con plancia per
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
sotto. Sul Tronky, in mm:

    colonne   15 | 116 | 134 | 117 | 133      falda, fianco, fondo, fianco, coperchio
    fasce     25 | 116 | 204 | 116 | 25       falda, fronte, fondo, retro, falda

Il riconoscimento guarda la griglia e basta, come quello del vassoio, e non
stima niente:

- il **fondo** e' il rettangolo di cordonature con una parete su ogni lato: il
  bordo esterno di una parete e' la prima riga parallela che la attraversa
  TUTTA - il fondo della finestra e il riquadro della scadenza, che la
  attraversano a meta', non sono bordi;
- il **coperchio** e' il pannello oltre uno dei due fianchi largo quanto il
  fondo, fra il 90 e il 110% (sul Tronky 133 contro 134). Oltre l'altro fianco
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
  pezzo di fronte, e sul Tronky la cresta della plancia saliva di 0,28 mm. Si
  guarda anche la griglia capovolta, e dove le due scelte non coincidono vince
  la zona piu' grande, che e' la stessa in tutti e due i versi. Non la piu'
  piccola: provata, lasciava sul fianco della plancia i denti della
  perforazione della cerniera.

### La texture, sul solo riquadro della fustella

Lo steso e' uno, come nel vassoio, ma si rende sul riquadro della fustella e
non sulla pagina intera: la pagina del Tronky e' 940 x 800 mm e la fustella
515 x 486, e con lo stesso lato massimo la texture tiene quasi il doppio dei
punti per millimetro.

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

Le quote del Tronky sono vettorializzate e non si leggono come testo, e il
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
file (Kinder Pingui T6 BOX):

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
quello che non piega il corpo: sul Pingui una linea a 27 mm dal fondo — dove le
alette laterali cambiano profilo — spezzava la faccia da 125 in 98 + 27, e il
fronte spariva dalla lettura. Una cordonatura che separa due fasce della
fasciatura **deve attraversare la colonna del corpo**; quelle che non lo fanno
appartengono alle alette (`_fasce_del_corpo`). E' lo stesso criterio che si
usava gia' per le colonne, applicato anche alle righe.

I controlli che decidono la famiglia:

- **astuccio chiuso**: retro e fronte devono avere la **stessa altezza**. Sono
  la stessa faccia vista da due parti. Il solutore prende come retro e fronte
  le due fasce piu' alte e ne fa la media: sul Pingui erano 40,5 e 125,0 e la
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
tiene fuori i flowpack: su Colazione la fascia grande e' il nastro, cielo e
fondo sono due falde da 5 mm perfettamente uguali, e senza il controllo ne
usciva un astuccio profondo cinque millimetri. I fianchi da 7 lo smentiscono, e
il solutore si ferma.

#### Il retro e' la faccia che porta i fianchi

Un astuccio chiuso ha due facce alte uguali, e quale sia il retro non lo dice
l'altezza. Il solutore prendeva sempre per retro **quella in alto** sul foglio,
che e' lo schema `[aletta] RETRO | CIELO | FRONTE | FONDO`. Il **Kinder
Cioccolato T8** (disegno 17435, KC_T8_GER) e' montato al contrario:

    fasce (mm)   12 | 82 | 12,5 | 82 | 10
                 cielo  fronte  fondo  retro  colla
    fianchi      11,5 x 82 sulla faccia BASSA, con le alette colla da 10,5

Letto alla solita maniera il modello usciva sbagliato senza nessun errore: sul
fronte il pannello bianco, il bambino sul retro e capovolto, per fondo la
linguetta della colla, i fianchi senza grafica, e la fascia del cielo con
"kinder SCHOKOLADE" e il "100g" spariva.

Quale e' il retro lo dice la fustella, senza guardare la grafica: **i fianchi
stanno sul retro** - e' la stessa ipotesi su cui `FOLD_V` costruisce le pieghe.
Se li porta solo la faccia bassa, il retro e' lei (`dieline._chiuso` con
`_ha_fianchi`). Cielo e fondo restano quello che sono per il **fronte**: il
cielo e' la fascia sopra il fronte, se e' profonda come il fondo, e il fondo
quella fra fronte e retro. Le pieghe non cambiano: il cielo tocca il fronte col
bordo basso, il fondo col bordo alto, e il retro ha comunque il bordo alto in
fondo alla scatola - nello schema solito perche' scavalca il cielo, qui perche'
risale dal fondo. La linguetta della colla non e' una faccia e resta fuori.

Verificato guardando il modello: il cielo con "kinder SCHOKOLADE" si legge dal
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

Il caso e' il **Nutella Donut**, letto nel verso della grafica - che sul
foglio e' girato di 90 gradi rispetto al DT:

    fasce (mm)   38,1 | 187,7 | 38,1 | 188,5 [aletta]
                 fondo  retro   cielo  fronte
    fianchi      36,9 sul retro, tratteggiati per la colla (croma 5)
                 36,9 sul fronte, arancio con "nutella donut" (croma 154)

Oltre il fronte c'e' solo l'aletta: **il fondo sta oltre il retro**, ed e' la
fascia marrone che continua l'onda del retro (`dieline._chiuso`, se e'
profonda come il cielo). Prima il Donut si leggeva come fasciatura
orizzontale nel verso del DT, e il modello aveva il cielo capovolto, un
fianco tutto marrone e per fondo un'aletta; adesso il cielo con "nutella
donut" si legge dal davanti, i fianchi arancio continuano l'onda marrone del
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
Pingui T6, con la foto del prodotto e il QR a testa in giu'.

Che siano quelli i quad giusti non serve crederlo: `FOLD_H` lo dice. Nella
fasciatura orizzontale i fianchi sono agganciati al fronte per costruzione, e le
sue due voci `left` e `right` sono **identiche** a queste.

#### Il caso calibrato: Kinder Pingui T6 BOX

    colonne (mm)   16 | 4 | 8 | 32,3 | 140,5 | 32,3 | 8 | 4 | 16
    fasce   (mm)   33,5 | 40,5 | 125,0 | 40,5 | 30,0
    fianchi        40,3 x 125,0, accanto al FRONTE
    quote          140,5 x 125,0 x 40,5 mm
    finestra       61,5 mm di altezza, fra le due falde da 33,5 e 30,0
    guscio         7 facce esterne + 7 interne + 8 coste

E' un pack cartotecnico con il **retro a finestra**, che lascia intravedere i
sei Pingui dentro. Il riscontro che chiude il conto e' la profondita' letta due
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
sparire, e guardando dentro la finestra del Pingui T6 non si vedeva niente.
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

    Pingui T6 (aperto)      7 facce esterne + 7 interne + 8 coste
    Nutella Donut (chiuso)  6 facce esterne + 6 interne + 0 coste

e le otto coste del Pingui sono esattamente quelle che deve avere: il bordo
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

### La colata si rimette con l'inchiostro del file

**Adesso di solito non serve.** L'ombra della colata e' sempre un'immagine in
sovrastampa, e la simula il livello della grafica su tutti i file, livello
`Colata` o no: vedi *Un'immagine in sovrastampa si somma a quello che trova*.
Quando lo fa, qui non si tocca niente. Quello che segue resta per le colate che
la grafica non copre e per la pagina resa com'e'.

**E una correzione.** Il KP T1 Mandarino qui sotto e' dato per ombra
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
via per costruzione. La colata Kinder e' costruita proprio cosi' - una lastra
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
2. **la risorsa** `risorse/colata_kinder.png`, solo se la prima non ha niente
   da correggere.

Se Ghostscript non c'e', il codice se ne accorge e resta la seconda: non si
rompe niente, si fa meno.

#### Solo dentro l'impronta del livello, e non per pignoleria

La banda in quadricromia si incolla **solo dentro l'impronta del livello
`Colata`**, mai su tutta la banda e mai su tutta la pagina. Il motivo e'
misurato: rendendo in quadricromia l'intera pagina del KP T1 Mandarino il
marchio `kinder` e il bicchierino di latte diventano **neri**. Non e' un
difetto di Ghostscript ne' l'appiattimento in CMYK - ricomponendo lastra per
lastra con i colori veri delle Pantone il nero resta - e' che quegli elementi
la sovrastampa ce l'hanno davvero. Ma sul livello `Colata` non stanno, e fuori
dall'impronta non li tocca nessuno.

#### Quanto conta la sovrastampa non si misura ad area

La domanda non e' quanta parte della banda cambia. Quella e' area, e sui due
casi misurati da' lo stesso 5% pur essendo casi **opposti**. La domanda e':
delle zone che senza sovrastampa escono azzurre - cioe' delle ombre sbagliate
- quante ne rimette a posto?

    KP T1 Mandarino      13.248 px azzurri, ne recupera l' 1,1%
    Kinder Pingui T6 BOX  7.672 px azzurri, ne recupera il 49,6%

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
marchio `kinder` e il bicchierino di latte, che rendendo in quadricromia
diventano neri, azzurri non sono mai. Sbagliare il bordo di qualche
millimetro non cambia il risultato.

**E l'azzurro da solo non riconosce niente.** Sul Kinder Pingui T6 BOX la
macchia azzurra piu' grande del foglio non e' un'ombra rotta: e' il FONDO del
pack, gocce d'acqua su azzurro, 15.800 px che vanno lasciati in pace. Per
questo lo strumento torna la banda **due volte, prima e dopo**, e chiede di
guardarle: se cambia un fondo, un marchio o una foto, il riquadro e' fuori
posto.

Misurato sul T6 BOX, che la colata in sovrastampa ce l'ha ma il livello no:

    banda indicata a occhio    187 x 58 mm
    zone azzurre               41.821
    rimesse dalla sovrastampa  24%     -> si sostituisce
    fondo azzurro del pack      0,1%   -> si rifiuta da solo

Il secondo numero e' la prova che il meccanismo si limita da se': puntandolo
sul fondo del pack, sotto soglia non fa niente.

#### Il foglio in cassa va buttato appena qualcuno se l'e' preso

La sostituzione della colata restituisce **un'immagine nuova**, e quella resa
da `render_page` resta in cassa: due fogli interi vivi insieme. Sul T6 BOX
sono 6516 x 3923 px, 76 MB, e il picco della costruzione passava da 351 a 456
MB - dentro il tetto di 512 del piano Free, ma per un margine che non vale la
pena di spendere.

`dieline.scarta_resa()` va chiamata **subito dopo la colata**, non dopo il
nero: `nero` la sua resa se la fa da se', fuori dalla cassa, quindi da li' in
giu' la cassa non serve a nessuno. Col foglio buttato al momento giusto la
colata costa **13 MB**, non 105.

#### Il caso calibrato

    KP T1 Mandarino       livello `Colata`, 120,5 x 36,3 mm
                          Ghostscript recupera lo 0,2% -> era la risorsa;
                          adesso l'ombra la simula la grafica
    Kinder Pingui T6 BOX  ombra in sovrastampa: recupera il 49,6% -> quadricromia

Il T6 BOX il livello `Colata` non ce l'ha, e per questo non lo prende: la
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

## Flowpack

**Invariante strutturale.** Ogni flowpack e' composto **esclusivamente da due
pinne di saldatura piu' una saldatura longitudinale sul retro**: avvolgimento
del prodotto e sigillatura a tre punti. Le pinne possono essere disposte in
verticale o in orizzontale a seconda delle proporzioni, ma la funzione non
cambia.

Davanti a un disegno mai visto: ruotarlo mentalmente di 90 gradi o
specularmente — la saldatura puo' stare a destra invece che a sinistra — e
ricondurre sempre il layout allo schema standard, due pinne piu' una saldatura
posteriore. Le uniche due variabili che cambiano la resa sono il **numero di
zigrinature** e il **rigonfiamento**.

**Le fasce vicino alle saldature vanno lette per funzione, non per posizione.**
Una fascia adiacente alla pinna puo' essere **zona senza prodotto**, dove il
film si deforma fino alla saldatura: il DT la annota come *PRINT AREA TENDING TO
WRINKLE* e appartiene al corpo, non alla pinna. Le pinne vere sono definite come
*background color*. Su Kinder Pingui T1 la catena e' 8 | 10 | 113 | 10 | 8: le
fasce da 10 sono zona grinze, le pinne sono quelle da 8.

**Il DT che marca un pannello ha la precedenza.** Se il disegno segna
esplicitamente una fascia — due linee con una quota e l'indicazione
*TEXT ORIENTATION* — quella e' l'informazione autorevole: va cercata **prima**
di dedurre le fasce dalle cordonature, e la grafica va centrata in quella zona.
Su Kinder Bueno T2 la fascia marcata da 50 mm ha fatto uscire fianchi uguali
(11,01 e 11,01) e cucitura centrata sul retro, dove la mia deduzione dava 46,4
con fianchi diversi.

**L'artwork e' il blocco piu' vario, non il piu' grande.** Una tavola porta
spesso le lastre di separazione a fianco della vista stampata, e una campitura
piatta di tinta e' colorata al 99% pur essendo una lastra: su Kinder Country le
tre lastre (Aluminium, Transparent Support, White Plate) sono piu' larghe della
OUTSIDE VIEW e la scaletta per ingombro metteva davanti quella del bianco.
Il discrimine e' quanti colori distinti porta il blocco: 149 sull'artwork vero
contro 14-26 sulle lastre e sui cartigli. `find_blocks` riporta
`colori_distinti` e ordina per quello.

**Niente soglie assolute sulla lunghezza delle linee — ma la frazione puo'
solo abbassarle, mai alzarle.** Fra il nastro di K Tronky (83 mm) e quello di K
Brioss (420 mm) c'e' un fattore cinque: una cordonatura che attraversa tutto il
nastro del Tronky e' lunga 83 mm, sotto gli 88,2 mm che `analyze_auto`
pretendeva, e nessun pack piccolo poteva passare il cancello.

Sostituire le costanti con una frazione pero' le **alza** sugli steso piu'
lunghi del riferimento, ed e' un modo nuovo di rompere le cose vecchie: su
Milch-Schnitte T1, passo 152,5 mm, la soglia saliva da 88,2 a 91,5 e si perdeva
la cordonatura a 108,5 mm, il cui gruppo sta giusto in mezzo. Senza quella
piega `solve_bands` non chiude, la costruzione ripiega sul solutore vecchio e
la grafica scivola. Le costanti restano la taratura buona sugli impaginati gia'
coperti: si prende il **minimo** fra costante e frazione.

**Una linea disegnata a pezzi e' una linea sola.** La soglia si applica ai
tratti uno per uno, e un file puo' disegnare una linea in piu' pezzi di fila.
Sul **Kinder Pingui T1 Cheesecake** il taglio in fondo allo steso e' nove
segmenti consecutivi - il piu' lungo 96 punti contro una soglia di 135 - mentre
sul T1 Mandarino, stesso identico disegno, e' uno solo da 340. Scartati i
pezzi, lo steso si fermava sulla saldatura: passo **141 invece di 149**, corpo
125 invece di 133, e la verifica delle UV che gridava "rientri diversi (8 e 10
mm)". Prima della soglia, i tratti della stessa penna sullo stesso asse che si
toccano si ricuciono (`flowpack._ricuci`): mezzo punto di vuoto al massimo,
cosi' un tratteggio vero resta tratteggio. Col taglio ricucito il Cheesecake
esce identico al Mandarino, 136 x 149, corpo 133, pinne 8 e gola 10 (135,5
prima che i capi dello steso si prendessero sul taglio: vedi *I capi dello
steso sono il taglio, non il centro del gruppo*).

**Un ripiego non deve mai essere muto.** Se `analyze_auto` fallisce, la
costruzione passa al solutore vecchio: il modello che ne esce non e' sbagliato
in modo evidente, e' **plausibile**, che e' peggio. Su Milch-Schnitte T1 la
grafica scivolava sul fronte, senza che niente lo dicesse. Ogni ripiego va
dichiarato negli avvisi della costruzione.

Qui c'era scritto che a scivolare erano corpo e pinne - 136,5 e 8,0 invece di
138,7 e 6,9 - e non era vero. Il solutore vecchio le pinne le leggeva dalle
saldature del DT, che su quel file stanno a 8,0 mm dal taglio: era
`analyze_auto` a sbagliarle, prendendole dal margine non stampato (vedi *Prima
le misure, poi il contenuto*). Quello che faceva scivolare la grafica era la
cucitura: `back_a` 8,5 invece di 21,5 mm, tredici millimetri di rotazione
attorno al tubo. Rimisurato mettendo le due analisi una accanto all'altra.

**Gli avvisi della costruzione devono arrivare all'utente.** Viaggiano
nell'header `X-Pack3d-Meta` della risposta di `/api/build`, perche' il corpo e'
il GLB. Per un po' sono stati calcolati e buttati: il chiamante HTTP non
raccoglieva il valore di ritorno, e con lui sparivano la verifica della
mappatura, la sezione dall'agente e tutto il resto.

**Il raster e il tracciato devono stare nello stesso telaio.** pdfplumber misura
sul MediaBox, pdfium rende il CropBox. Quando i due riquadri non coincidono — su
K Tronky il CropBox e' 459 x 271 pt dentro un MediaBox di 1332 x 958, spostato di
(419, 471) — le coordinate dei segmenti indicizzano un'immagine che comincia da
un'altra parte: nessuna eccezione, solo misure prese nel posto sbagliato, e
intere viste tecniche che restano fuori dalla resa. Si rasterizza sempre con
`dieline.render_page`, mai con `pdfium.PdfDocument(...).render()` diretto.

Vale anche in **lettura**, e li' e' meno evidente: `page.get_size()` di pdfium
da' la CropBox, mentre le coordinate dei tracciati sono nello spazio del PDF.
Chi ribalta la y su quell'altezza ottiene una pagina intera fuori posto — sul
K Tronky le due maschere, vecchia e nuova, non avevano un pixel in comune. Il
telaio si prende sempre dalla MediaBox (`tracciati._telaio`).

**I pannelli della fustella non sono la sezione del pack chiuso.** Le
cordonature dicono dove il film e' cordonato, non che forma prende una volta
riempito. Su Kinder Bueno T2 i pannelli danno 50 x 11, ma il pack in mano e'
41 x 20: **stesso perimetro**, 122 mm, quindi dall'artwork i due non si
distinguono e il solutore non sbaglia — gli manca proprio il dato. Il rapporto
larghezza/spessore va cercato sulle quote annotate del disegno tecnico e
riportato in `quote.larghezza` e `quote.spessore`; la costruzione lo riporta poi
sul perimetro misurato dalla fustella, che resta l'autorita' sulla taglia.
Senza quei due numeri il pack esce largo e piatto, con l'aria giusta ma la
forma sbagliata.

**Il film su scatola e' un caso a parte, e non basta il rigonfiamento a
dirlo.** Un pack puo' essere teso sul prodotto senza contenere niente di
rigido: il film si appoggia alla tavoletta, ma alle estremita' il tubo resta
vuoto e le ganasce lo appiattiscono. Quando invece il film avvolge un corpo
rigido che arriva fino alla saldatura — un multipack in astuccio, una
vaschetta, un blister — cambiano due cose:

- **La pinna non si allarga.** Un tubo si appiattisce perche' dentro c'e'
  aria; con la scatola non c'e' niente da appiattire, la pellicola si ripiega
  sugli spigoli e la pinna esce larga esattamente quanto la faccia del pack.
  Su Kinder Brioss T10 lo svaso passa da +25% a zero. E' il caso raro in cui
  la regola dello svaso a meta' perimetro non vale.
- **La sezione la detta la scatola.** Il riscalo a perimetro costante dice che
  una forma piu' tonda, a parita' di film, e' piu' grande: vale quando dentro
  c'e' aria. Con la scatola i pochi millimetri che la superellisse taglia agli
  spigoli se li prende la piega, non il pack. Senza questa eccezione il Brioss
  usciva 155,9 x 59,7 invece dei 148,9 x 57,0 della fustella.

Dal PDF non si vede: e' il prodotto a dirlo. Va riportato in
`parametri_costruzione.avvolge_scatola`, e nell'interfaccia c'e' la casella
"Il film avvolge una scatola". Un pack cosi' e' rigonfiamento 1.

- **La pinna e' corta, e la gola sta oltre la scatola.** Quello che la
  fustella misura oltre il corpo non e' tutto pinna: prima il tubo deve
  collassare, e la gola piegata sullo spigolo costa mezzo spessore. Su Kinder
  Brioss i 37,6 mm oltre il corpo sono 22,8 di gola piu' 14,8 di pinna. Il
  limite geometrico della gola e' mezzo spessore, la piega a 45 gradi sullo
  spigolo; sul pack vero pero' parte di quel film si ripiega di lato come
  orecchia invece di accorciare la pinna, quindi la frazione utile e' piu'
  bassa. `GOLA_SU_SPESSORE` vale 0,40, tarato sulle foto di un pack solo e
  regolabile con `PACK3D_GOLA`. Con una scatola dentro la gola non
  puo' mangiare il corpo, perche' la scatola tiene la sezione fino alla sua
  faccia: il pack resta squadrato fino in fondo e poi salda subito. Nel modello
  si sposta massa da `end_fin` a `L` tenendo ferma la somma `L/2 + end_fin`,
  cosi' le UV non cambiano e la grafica non si muove.
- **Ma se la gola la disegna il DT, vale quella.** La stima dallo spessore
  serve quando la saldatura non e' disegnata e la testata arriva alla piega
  (Brioss). Quando il DT disegna la saldatura E dove finisce il prodotto, la
  testata e' gia' divisa: pinna fino alla saldatura, gola fino al prodotto, e
  il corpo la comprende. Su **K Colazione Piu' T10** le quote del file sono
  `20 | 37,5 | 215 | 37,5 | 20`, e il ramo della scatola divideva lo stesso
  la pinna da 20 mm: 18 di gola in piu' e **2 mm di pinna**. Il pack usciva
  una scatola senza pinne, con la grafica delle testate stirata di 2,07 volte,
  e nessun errore. Era cosi' dal 27 settembre, da quando le testate si
  leggono dal DT (vedi *Prima le misure, poi il contenuto*), e nessun
  controllo lo prendeva: la verifica delle UV con la scatola cercava la
  piega, e sul Colazione la prima linea e' la saldatura. Adesso: gola dal DT,
  pinna 20, verifica UV a 0,0 mm, film stirato 1,38 invece di 2,07. I due
  Brioss restano identici al byte.

Resta fuori dal modello il fatto che su questi pack la pinna, oltre a non
allargarsi, viene **ripiegata sulla testata** invece di sporgere: nelle foto
del Brioss si vede piegata, nel modello sporge dritta. Piegarla e' geometria
nuova, non un parametro.

**Il rigonfiamento cambia la forma, non la taglia.** Il perimetro e' fissato dal
foglio stampato: a parita' di steso un pack piu' morbido non e' piu' grande, e'
piu' tondo. La sezione e' una superellisse `|y/a|^n + |z/b|^n = 1` con n che
scende da 10 (rettangolo, livello 1) a 2 (ellisse, livello 10), riscalata in
modo che il perimetro torni quello del film. Gonfiare aumentando le dimensioni
e' il modo sbagliato: fa crescere il perimetro e la grafica non torna piu'.

**Mappare per pannello, non per arco uniforme.** Gli spigoli della sezione si
trovano dalla curvatura e si usano come nodi di interpolazione: ogni fascia
dello steso finisce sul suo pannello, indipendentemente da come i raccordi
ridistribuiscono il film. Con la mappatura per arco ogni fascia scivola — su
Kinder Bueno T2 lo scarto era 18,51 mm, il 12,7% del giro.

**Attenzione ai filtri troppo aggressivi sui dati in ingresso.** Una cordonatura
puo' sfuggire perche' il suo segmento sta sotto la soglia di peso, e allora
nessun solutore a valle puo' trovare la soluzione giusta: su Kinder Bueno T2 la
piega a 102,40 mm veniva scartata da un taglio `peso > 300`.

**Verificare il modello mappato contro l'AW con una misura**, fascia per fascia,
prima di finalizzare. Non basta controllare che la grafica sia diritta.

Adesso la misura la fa la costruzione da sola e finisce negli avvisi: per ogni
spigolo della sezione, lo scarto fra dove cade e dove lo vuole la fasciatura
dello steso. Dentro ci stanno due cose diverse, e vanno lette separate.

- **Scarti a segni alterni** sono la superellisse che taglia gli spigoli: il
  film sopra l'arrotondamento appartiene un po' al fianco e un po' al retro.
  E' fisiologico, e l'interpolazione per pannello lo sistema.
- **Scarti tutti dallo stesso lato** sono una **rotazione dell'origine**:
  grafica che scivola attorno al tubo. Quella l'interpolazione non la puo'
  correggere, perche' le si spostano anche i riferimenti. La media degli
  scarti distingue i due casi, e sopra l'1% del giro la costruzione lo grida.

**L'origine del giro sta sulla cucitura, `back_a` prima dello SPIGOLO.** Non
prima del punto di larghezza massima: quello e' il centro della faccia
laterale, e fra i due c'e' mezzo spessore. `superellipse_section` ancorava li',
e la grafica girava di altrettanto — 4,2 mm su Kinder Country, 12,9 su Kinder
Paradiso, 25,7 su K Brioss. Il difetto stava nel codice da prima ma era
dormiente: la costruzione passava per `soft_section_fit`, che parte esplicito
da `(W/2 - back_a, -T/2)`. E' stato il passaggio alla superellisse ad
accenderlo, e nessuno se n'e' accorto perche' la misura fascia per fascia non
esisteva. Su un tubo piatto lo spigolo non esiste e il punto giusto e' la
piega: vedi *La cucitura si ancora alla PIEGA, non allo spigolo*.

**La cucitura non e' sempre centrata sul retro** (Kinder Pingui: 16 + 18), e
**lo steso puo' essere ruotato di 90 gradi** rispetto alla convenzione della
pipeline. Entrambi i casi mandavano in errore `solve_bands`, che cercava coppie
simmetriche. Oggi `solve_bands_any` enumera tutte le quaterne di pieghe e tiene
quella dove il retro somma al fronte e i fianchi coincidono; se su quell'asse le
fasce non chiudono, `analyze_auto` ritenta con lo steso trasposto e segna
`ruotato`, che a valle ruota anche la texture. La formula finale non richiede
simmetria.

`flowpack.analyze_auto`:

1. le cordonature sono spesso tracciate con due guide equidistanti: tre linee
   ravvicinate e ugualmente spaziate sono **una piega sola, quella di mezzo**;
2. la fasciatura e' **simmetrica rispetto alla mezzeria del nastro**, quindi le
   pieghe stanno a coppie speculari: la coppia esterna separa retro e fianco,
   quella interna fianco e fronte;
3. le pinne di testa si misurano dalle **saldature del DT**, e il margine non
   stampato si guarda solo dove il disegno non le segna: vedi *Prima le
   misure, poi il contenuto*. Era il contrario, e il margine sbagliava in
   tutti e due i versi: su artwork **al vivo** non c'e' - su Kinder Bueno T2
   la grafica copre 923 colonne su 1010, la misura dava `end_fin = 0` e il
   modello usciva con il 21% di triangoli degeneri - e su una grafica col
   bianco vicino alla testata e' troppo lungo - su Colazione 41,2 mm contro i
   20 della saldatura.

Verifica: perimetro + 2 falde deve dare la larghezza del nastro.

| | nastro | fronte | fianco | falda | somma |
|---|---|---|---|---|---|
| Milch-Schnitte T1 | 144,0 | 43,0 | 15,0 | 14,0 | 144,0 |
| FULFIL | 141,0 | 36,0 | 19,5 | 15,0 | 141,0 |
| Kinder Bueno Dark | 415,0 | 150,5 | 41,0 | 16,0 | 415,0 |

Regole di forma, da applicare senza chiedere:

- denti **equilateri**, contati sul **bordo della pinna** e non sul perimetro
  della sezione: base = bordo / numero denti, altezza = base x V3/2. Il taglio
  agisce solo sul bordo esterno, l'interno resta piano con le nervature delle
  ganasce;
- la **pinna longitudinale segue la forma del pack**, costruita come superficie
  offset della sezione; se troppo complessa va eliminata;
- **pinne laterali verso l'alto**;
- morbidezza e fedelta' della grafica tirano in direzioni opposte: la sezione a
  superellisse piena comprime il fronte del 17%. Serve **curvatura continua
  agli spigoli con centro piano**;
- l'apertura della pinna va concentrata vicino alla saldatura (rampa di quinto
  grado): con una rampa corta il gonfiore invade il corpo e deforma i bollini;
- la grafica **non segue lo svaso**: sulla pinna e sulla spalla il giro si
  misura sul film dal centro del fronte, e lungo il passo il film si stende
  sulla spalla (vedi *La grafica sulle pinne*).
### Prima le misure, poi il contenuto

Il pack si costruisce dal **disegno tecnico**, e il disegno tecnico si
controlla con le **quote**. Il contenuto - dove c'e' inchiostro e dove no -
viene per ultimo, perche' **la grafica puo' avere del bianco**: una fascia
bianca vicino alla testata e il margine "non stampato" si allunga fino a lei,
e il margine non e' piu' la pinna.

Le testate si leggono cosi' (`flowpack.testate_dal_dt`), da ciascun taglio
verso l'interno, entro un terzo del passo:

- la **prima linea** del DT e' la saldatura: li' finisce la pinna;
- la **seconda** e' dove finisce il prodotto, e fra le due c'e' la **gola**, il
  tubo che si schiaccia verso la pinna. E' la zona che il DT chiama "grinze"
  (KMS, KP: 10 mm) o "superficie inclinata verso saldatura" e quota a parte
  (Colazione: 37,5). E' li' che il modello si rastrema, o da prima quando il
  calo del tubo vuole piu' film (vedi *La grafica sulle pinne*);
- se la prima struttura e' una **piega con le sue due guide**, la saldatura
  non e' disegnata: e' il film su scatola (Brioss), e la testata arriva alla
  piega. Da li' in fuori la gola la decide lo spessore, come prima. Se invece
  il DT disegna saldatura e gola e il film avvolge una scatola (K Colazione
  Piu'), la gola resta quella del DT: vedi *Il film su scatola*.

I due lati devono dire la stessa cosa. Se non la dicono, la pinna prende il
rientro piu' stretto - la regola di sempre - la gola non si usa, e la
verifica delle UV lo grida (vedi *Le verifiche*).

Il margine non stampato resta come **ripiego**, dichiarato, solo dove il DT
sulle testate non segna niente.

Sul parco, pinna di testa prima e dopo, in mm:

    |                        | dal margine | dal DT                 | quote della miniatura          |
    | Colazione              | 41,2        | 20 + gola 37,5         | 20 | 37,5 | 215 | 37,5 | 20, testo |
    | Kinder Paradiso T1     | 3,4         | 15 + gola 10           | 15 | 10 | 105 | 10 | 15, a occhio |
    | K Brioss STD           | 32,6        | piega a 37,6           | -                              |
    | K Brioss Latte e Cacao | 32,6        | piega a 37,6           | -                              |
    | KMS T1                 | 6,9         | 8,0 + gola 10          | -                              |
    | K Tronky T1            | 9,8         | 10,0                   | 10 | 124 | 10, a occhio        |
    | KP T1, KCF T1, Kinder Country: uguali, 8,0 - 6,0 - 7,0                                    |

Dove le quote ci sono, danno ragione al DT, e al decimo. Il Paradiso e' il
caso peggiore di prima: la grafica sborda di una decina di millimetri dentro
la saldatura, il margine non stampato era di 3,4 mm, e il pack usciva con un
corpo di 148 mm e le pinne da 3 invece di 125 e 15 - ventitre millimetri di
prodotto in piu'. Sul Brioss la piega a 37,6 e' **esattamente** la misura su
cui la gola e' stata tarata - "37,6 = 22,8 di gola piu' 14,8 di pinna",
scritto sotto in *Il film su scatola* - mentre il margine dava 32,6 e la pinna
usciva 9,8: la taratura era rimasta giusta e la misura sotto era scivolata,
senza che niente lo dicesse.

Le quote del file la costruzione le legge da sola quando sono testo
(`quote.riscontro_testate`): una CATENA di numeri allineati sullo stesso asse
che somma al passo, e **simmetrica**, perche' lungo il passo il pack lo e'. Un
numero solo non conferma niente - un "20" lo scrive anche la tabella
nutrizionale - e con una quarantina di numeri sul foglio una fila che somma al
passo si trova anche per caso: su Colazione `7 | 135 | 7 | 57 | 7 | 71,5 | 40
| 5` fa 330 ed e' fatta di pezzi del nastro. Una fila simmetrica per caso no.

Se la catena del file non torna con le testate lette dal DT, la costruzione lo
**grida**: vuol dire che il disegno e' stato letto male. Provato rimettendo la
lettura dal margine su Colazione: `QUOTE DEL FILE DIVERSE DALLE TESTATE LETTE:
il file scrive 20 | 37,5 | 215 | 37,5 | 20 = 330, dal disegno esce 41,2 |
247,6 | 41,2`.

### La grafica sulle pinne: il film non si allunga

Sul Paradiso e sul Pingui la grafica vicino alle pinne **sterzava**: il bollino
"Fatta con latte fresco", che parte sulla pinna e passa sulla spalla, girava
verso il bordo lungo la gola e sulla pinna arrivava allargato. Succedeva su
ogni pack con scritte o elementi grafici sulle testate, e le cause erano due,
tutte e due nella UVW e nessuna nella texture.

**1. Lungo il giro.** La pinna si otteneva scalando la sezione: stretta in
altezza, allargata in larghezza fino al bordo della pinna. Le fasce del film
seguivano la scala, quindi il fronte si allargava con la pinna - del 46% sul
Paradiso - e i fianchi si schiacciavano a zero sul bordo. Ma la pinna e' il
**tubo appiattito**: il film non si allunga, un punto del fronte a 20 mm dal
centro sta a 20 mm dal centro anche sulla pinna, e le pieghe del bordo cadono a
meta' dei fianchi. Adesso ogni anello della gola e della pinna si rimisura sul
film a partire dal centro del fronte e da quello del retro
(`flowpack._GiroSulFilm`): la forma non cambia, i vertici scorrono
sull'anello. La differenza di lunghezza fra anello e film la prende la fascia
della piega: poca a pinne aperte, tutto il fianco a pinne strette, dove il
fianco si ripiega **a soffietto** - che e' quello che fa il film vero con una
scatola dentro. Nel corpo resta la mappatura per pannello, e il passaggio e'
graduale lungo la gola.

**2. Lungo il passo.** Dalla sezione piena alla saldatura il tubo cala di mezzo
spessore, e il film deve bastare a coprire la discesa. Sul Paradiso la gola
del DT e' 10 mm e il calo 14,1: dieci millimetri di film su una discesa di
quattordici sono la scritta LATTE stirata fino a 3,7 volte. Due correzioni:

- la **spalla** e' lunga almeno 1,7 volte il calo (`SPALLA_SU_CALO`, regolabile
  con `PACK3D_SPALLA`), e se la gola del DT non basta comincia **dentro il
  prodotto**, come un prodotto morbido che il film tira giu' sugli spigoli. La
  saldatura resta sulla sua linea, e con lei tutte le linee del DT. Con una
  scatola no: li' la sezione la tiene la scatola fino alla sua faccia;
- sulla spalla il film si **stende sulla superficie** (`_stendi_spalla`):
  colonna per colonna, fra l'ultimo anello a sezione piena e la saldatura, in
  proporzione alla lunghezza vera. I due capi restano fermi, quindi della
  texture non si perde niente, e lo stiro che il film non puo' evitare diventa
  uguale su tutta la spalla invece di fare picco dove scende di piu'.

La falda longitudinale prende la u dal tubo sotto di lei, perche' e' lo stesso
film.

Il bollino del Paradiso, triangolo per triangolo:

| | pinna, giro | spalla, passo | anisotropia massima |
|---|---|---|---|
| prima | 1,51 | 2,47 in media, 3,67 di punta | 6,1 |
| dopo | 1,00 | 1,21 in media, 1,22 di punta | 1,3 |

E sul parco, con la misura della terza verifica: pinne e spalle meno i denti,
la stessa zona prima e dopo, fra il 5 e il 95% dei triangoli:

| pack | giro prima | giro dopo | passo prima | passo dopo |
|---|---|---|---|---|
| Kinder Paradiso T1 | 0,05 - 1,55 | 0,82 - 1,07 | 2,97 | 1,23 |
| KP T1 Mandarino | 0,06 - 1,68 | 0,83 - 1,14 | 2,28 | 1,23 |
| KMS T1 | 0,07 - 1,32 | 0,84 - 1,06 | 1,87 | 1,22 |
| K Tronky T1 | 0,33 - 1,32 | 0,89 - 1,05 | 1,70 | 1,22 |
| KCF T1 | 0,46 - 1,34 | 0,83 - 1,05 | 2,53 | 1,22 |
| Kinder Country | 0,08 - 1,30 | 0,84 - 1,07 | 1,79 | 1,23 |
| Colazione | 0,07 - 1,39 | 0,81 - 1,07 | 2,11 | 1,22 |
| K Brioss STD, scatola | 0,04 - 1,05 | 0,24 - 1,05 | 2,49 | 1,67 |

Sul Brioss il giro si chiude ancora a 0,24: e' il soffietto dei fianchi a
pinne strette, voluto. E il passo resta a 1,67 perche' con la scatola la spalla
non si allunga: il film vero li' fa le orecchie, che una superficie liscia non
sa fare. Restano fuori i denti, che il film lo tagliano davvero.

La misura gira da sola su ogni costruzione (`verifica.testate_flowpack`, la
terza verifica) e ha i denti: sul vecchio modo di mappare grida `GRAFICA
STIRATA SULLE TESTATE - 3,10 lungo il passo, la spalla e' troppo ripida per il
film che ha; 1,55 lungo il giro, la grafica si allarga con la pinna; il giro si
chiude a 0,05, i fianchi spariscono sul bordo della pinna` sul Paradiso, e
grida su KP, Tronky e Brioss.

### La falda dice se la soluzione e' sbagliata

La falda non scala col nastro: e' il lembo che schiacciano le ganasce, e le
ganasce non diventano piu' grandi perche' il sacchetto lo e'. Misurate:

| pack | nastro | falda |
|---|---|---|
| Kinder Country | 122 | 16,0 |
| FULFIL | 141 | 15,0 |
| Milch-Schnitte T1 | 144 | 14,0 |
| Kinder Paradiso | 165 | 12,5 |
| K Brioss T10 | 420 | 4,1 |

Da 122 a 420 mm di nastro, sempre fra 4 e 16. **Una falda molto piu' grande
non e' una falda: e' il segno che il solutore ha preso la quaterna di pieghe
sbagliata.** Nastro, passo e corpo restano giusti anche cosi', quindi la
soluzione sembra buona e il pack esce piatto.

E' l'unica quantita' fisica che distingue due soluzioni entrambe coerenti, ed
e' per questo che viene **prima della simmetria** nella scelta della quaterna.
Su K Brioss STD erano in gara:

    W 134,93   T  7,00   falda 68,02   simmetria 0,12
    W 134,93   T 67,73   falda  7,29   simmetria 0,65

e vinceva la prima, per mezzo millimetro di simmetria fra le due meta' del
retro. A quella scala mezzo millimetro e' rumore del disegno; una falda da 68
mm no.

### Due chiusure, non una: pinna e sovrapposizione

La pipeline nasce sul flowpack a **pinna longitudinale**: i due bordi del film
escono fuori e si saldano fra loro, il giro e' il perimetro della sezione e
l'invariante e' `perimetro + 2 falde = nastro`. La sezione e' un rettangolo
W x T arrotondato.

Non tutti i wrap sono cosi'. Su una barretta il film si chiude spesso a
**sovrapposizione**: un bordo passa sotto l'altro e non sporge niente. Il pack
non ha allora fianchi — e' un tubo piatto, fronte e retro — e l'invariante
cambia:

    fronte + retro + lembo coperto = nastro        con fronte = retro

cioe' il fronte misura **mezzo giro**. Sul K Tronky T1 chiude al millimetro:

    23 (retro) + 36 (FRONTE) + 12 (retro) + 12 (lembo) = 83
    giro 71,  fronte 36,  mezzo giro 35,5

e la fascia da 36 e' proprio quella che il disegno marca *TEXT ORIENTATION*,
come vuole la regola del pannello marcato. Il lembo da 12 e' la fascia che la
legenda chiama *Covered Area*: si chiama coperta perche' finisce sotto.

**Forzare un pack a sovrapposizione nel solutore a pinna da' una risposta
plausibile e sbagliata.** Sul Tronky usciva falda 5,5 per lato — 11 mm di
nastro nell'aletta invece che intorno al prodotto, giro 72 invece di 71 — con
fianchi da 12 e fronte da 24 invece di 36. Il pack veniva sottile, squadrato e
con la grafica ruotata, e nessun controllo se ne accorgeva perche' i conti
tornavano tutti. Lo ha visto l'utente, confrontandolo col pack vero.

Corollario, imparato buttando via un'ora di lavoro: **un ripiego che allarga il
solutore va misurato contro un pack vero prima di tenerlo.** Avevo aggiunto la
deduzione della quarta piega dall'invariante dei fianchi uguali: matematicamente
giusta, e sul Tronky dava 24 x 12 con tutti i conti in ordine. Era la famiglia
sbagliata. E' stata rimossa: era nata per il Tronky, il Tronky non ne ha
bisogno, e restava una strada capace di produrre in silenzio una sezione
sbagliata su qualche pack futuro.

#### La terza chiusura: il tubo piatto a pinna

Il **Kinder Happy Hippo T1** (Ferrero 12402, "KHH Film T1", cold seal) non e'
ne' l'una ne' l'altra. Il DT, di traverso al nastro, segna 1 | 15 | 83 | 15 |
1: il margine, le due fasce di cold seal che si saldano a pinna, e in mezzo il
giro, che e' proprio l'area di stampa del cartiglio. Nessuna piega fra fronte e
fianchi: il film avvolge un biscotto, e non ha spigoli. A pinna non chiude -
mancano le quattro pieghe - e a sovrapposizione nemmeno, perche' il lembo non
sta da una parte sola. Lo Space non lo costruiva.

E' un **tubo piatto chiuso a pinna** (`risolvi_pinna_piatta`,
`Flowpack.piatto`): `giro + 2 falde = nastro`, con le due linee della pinna
speculari e nessuna linea fra loro, che sarebbe una piega. Il fronte e' mezzo
giro, centrato, e la pinna sta a meta' del retro: 115 = 16 + 83 + 16, fronte
41,5. La sezione la da' il rigonfiamento, come a sovrapposizione - dalla lente
al cerchio - ma la pinna c'e', e si appoggia sul retro.

Tutte e due le letture del foglio trovano due linee speculari: le fasce della
pinna in un verso, le saldature di testa nell'altro (15 | 85 | 15). Il verso
giusto lo dicono le **testate**: solo li' il DT le segna uguali ai due capi, 15
e 15; nell'altro verso le "testate" sono le fasce della pinna viste di
traverso, e i margini le sbilanciano, 12,9 contro 15,5 (`_testate_speculari`).

Sul modello: nastro 115 x passo 115, giro 83, fronte 41,5, pinna 16, testate
15, corpo 85, e la miniatura del cartiglio lo conferma su due copie (16 | 83 |
16 e 15 | 85 | 15). Senza il box verde Best Before e senza il tratteggio del
cold seal. Un biscotto piatto sta meglio a rigonfiamento basso: al 5 la
sezione e' 31 x 21 e il marchio, largo 39 mm su un fronte di 41,5, gira un po'
sul fianco.

#### Come si sceglie la chiusura

Sei tentativi in ordine: pinna nei due versi dello steso, poi sovrapposizione
nei due versi, e per ultimo il tubo piatto a pinna, che chiede meno al disegno
- due linee speculari - e quindi viene dopo chi ne chiede di piu'. L'ordine
conta. "Le fasce non chiudono" non
segnala solo la chiusura sbagliata: segnala **anche** che lo steso va letto
ruotato di 90 gradi. Provando l'altra chiusura prima dell'altro verso, il K
Brioss — che va letto ruotato — trovava una lettura plausibile nel verso
sbagliato e il verso giusto non veniva mai provato.

#### Il rigonfiamento di un tubo piatto

Un tubo piatto non ha un rapporto larghezza/spessore da tenere fermo:
gonfiandosi passa dalla lente al **cerchio**, e il cerchio e' il massimo fisico
— con quel film non si puo' essere piu' tondi. Il livello dice quanto ci si
avvicina, in frazione del diametro del cerchio, da 0,65 a 1,00.

La scala e' tarata sull'unica misura che esiste per questa famiglia, il GLB di
riferimento del Tronky: sezione a ellisse di rapporto **1,466** e ingombro
**26,7 x 18,2** su un giro di 71. Il livello 5 ci cade sopra (1,461 misurato).
La scala e' volutamente **stretta** e non copre i wrap davvero piatti:
allargarla vorrebbe dire inventare numeri che nessun pack misurato conferma, e
spostare il centro della scala via dall'unico riferimento che c'e'.

#### La cucitura si ancora alla PIEGA, non allo spigolo

`superellipse_section` ancorava l'origine del giro al punto a 45 gradi della
parametrizzazione. Su una sezione squadrata quello **e'** lo spigolo. Su un
tubo piatto non ci sono spigoli: ci sono le due pieghe del tubo appiattito,
che sono gli estremi dell'asse maggiore. Ancorare comunque ai 45 gradi ruotava
la grafica di tutto l'arco fra i due punti: **7,55 mm su un giro di 71, il
10,6%**, con il fronte che finiva mezzo sul fianco.

E la verifica non scattava. `_panel_knots` cerca quattro spigoli per curvatura
e un'ellisse non ne ha, quindi tornava `None`, la mappatura passava "per arco"
e nessuno misurava la rotazione. Ora un tubo piatto ha i suoi due nodi — le
pieghe — e la verifica c'e': dopo la correzione la rotazione misurata e' 0,1 mm
invece di 7,55.

Lezione generale: **una verifica che non si applica e una verifica che passa
non sono la stessa cosa, e nel resoconto devono leggersi diverse.**

#### A pari scarto il fronte lo dice la stampa

`risolvi_pillow` cerca la fascia fra due pieghe che misura mezzo giro. Sul
**Kinder Choco Fresh** - nastro 101, pieghe a 13, 26, 42 e 81, lembo di 20 in
fondo - ne trova due, e a pari scarto, 1,48 mm dal mezzo giro:

    fronte  0 - 42   retro 0 / 39    striscia tecnica e tratteggio
    fronte 42 - 81   retro 42 / 0    "kinder CHOCO fresh"

Vinceva la prima trovata, e "CHOCO fresh" finiva sul **retro** del modello - da
sempre, e la verifica del fronte passava, perche' confronta la texture con la
fascia che il solutore ha chiamato fronte. L'ordine in cui le pieghe si
incontrano non e' un criterio: dipende dal verso del foglio, e girato di mezzo
giro il solutore sceglieva l'altra. A pari scarto il DT non decide, e decide
la **stampa**, come per il fronte di un astuccio a fasciatura orizzontale: il
fronte e' la fascia con piu' grafica (`_risolvi_steso`).

E il retro tutto da un lato ha fatto vedere l'ultimo appiglio del tubo piatto:
la cucitura sta `back_a` prima della piega, e con 42 mm di retro su 40,5 di
mezza ellisse cadeva oltre la piega opposta, sul fronte. Il retro e' mezzo
giro, e la cucitura non va piu' in la' della piega (`superellipse_section`);
e le due pieghe si prendono nell'ordine in cui le incontra il film, non per
valore (`_panel_knots`), perche' con la cucitura sulla piega una delle due
viene a zero. Sul K Tronky e sul Bueno Dark, col retro diviso in due, non cambia
niente.

### Le guide ravvicinate: due letture, non una scelta

Tre linee ravvicinate ed equidistanti **possono** essere una piega sola
disegnata con due guide ai lati - senza fonderle le fasce escono assurde
(5 | 63 | 5) - ma possono anche essere tre pieghe vere, e il disegno non lo
dice. Decidere con una soglia sullo scarto fra i passi e' quello che ha reso
piatto il K Brioss STD (vedi "Mezzo millimetro non puo' cambiare il pack").

Quindi non si decide: si tengono **tutte e due le letture**, fusa e intera, si
risolvono entrambe e vince quella con la falda plausibile. Verificato
spostando la linea di mezzo attraverso la vecchia soglia, da 0,00 a 1,80 mm di
scarto: il pack non cambia mai.

### Pieghe e guide: la piega attraversa il passo

Tre linee ravvicinate sono una piega con le sue guide o tre pieghe, e il
solutore prova tutte e due le letture. Sul Kinder Cards T2 c'e' un caso che
le due letture non bastano a decidere: ogni piega ha due guide dell'area di
stampa a 1,5 mm, e prendendo le guide al posto delle pieghe i conti chiudono
lo stesso. Con la cucitura centrata la simmetria e' zero in tutti e due i
casi, e a parita' vinceva il fronte piu' largo:

    guide     fronte 46,5  fianchi 15,0 e 16,5   falda 11,8
    pieghe    fronte 45,0  fianchi 15,0 e 15,0   falda 14,0

La differenza la dice la lunghezza. Una **piega** corre lungo tutto il tubo e
attraversa il passo, 108 mm; una **guida** dell'area di stampa si ferma alle
saldature, dove la stampa finisce: 88 mm. La miniatura del file lo conferma
coi colori - pieghe in rosso a tutta altezza, area di stampa in arancio - e le
pieghe lette sono proprio quelle rosse.

Quindi `merito` guarda, dopo la simmetria e prima del fronte, **quanto passo
attraversa la piega piu' corta delle quattro** (`_copre`: l'unione dei tratti,
non la somma, arrotondata al 5%). Dove tutte le pieghe sono uguali - Colazione,
Paradiso, i Brioss - pareggia e decide il fronte come prima: sul parco nessun
altro file cambia. Non vale come regola assoluta, e per questo viene dopo la
simmetria: sul Milch-Schnitte e sul Kinder Bueno Dark una piega vera e' piu'
corta delle altre (0,59 e 0,38 del passo).

### I capi dello steso sono il taglio, non il centro del gruppo

Le linee a meno di 3 punti fanno gruppo, e il gruppo vale il suo centro: per
una piega disegnata due volte va bene. Per i due capi dello steso no. Sul Happy
Hippo il taglio e la riga del margine, a un millimetro, finivano nello stesso
gruppo, e il capo cadeva a mezzo millimetro dal taglio: nastro 114 invece di
115. Il capo e' la linea **piu' esterna** del suo gruppo.

Sul parco cambia il **KP T1 Mandarino**, da 135,5 a **136,0**: ed e' la sua
catena di quote a dirlo, 1 | 15 | 14 | 20 | 2 | 32 | 2 | 19 | 16 | 13 | 2 =
136. Il taglio a sinistra copre il passo come quello a destra e come le
pieghe, 149 mm; la linea a un millimetro e' lunga 152 e sporge oltre il passo,
quindi e' un'altra cosa. Il Brioss promo si sposta di un decimo di punto, e
tutti gli altri restano al byte.

### La falda sta sopra il retro anche nelle testate

Oltre il corpo la falda si posava a distanza zero sul retro schiacciato nella
saldatura, e due superfici alla stessa distanza si contendono i pixel: sul
Happy Hippo la falda bianca e la testata marrone uscivano a puntini. Adesso
resta sempre un ventesimo di millimetro sopra (`FALDA_SOPRA`): non si vede, e
decide chi sta sopra - la falda, come nel pack vero. Sui flowpack a pinna del
parco si spostano solo quei vertici, di 0,05 mm, e texture e UV non cambiano.

## Coppe e contenitori conici

La coppa da gelato - il Nutella POT 500 - arriva in **due PDF**: il
contenitore (sleeve e fondo) e il tappo (corpo e anello). Si dichiara
**Cartotecnico in due pezzi**, un PDF ciascuno (vedi *Il cartotecnico dice di
quanti pezzi e' fatto*): l'ordine non conta, quale e' quale lo dice la pagina
(`server._pezzi_tondi`). Con lo sleeve solo - cartotecnico in un pezzo -
esce la coppa aperta, col tappo solo il tappo, e il primo cartellino lo dice.
Nella home non c'e' un pulsante della coppa: era un secondo modo di dire la
stessa cosa. L'API accetta ancora `coppa` come tipologia.
La costruzione e' `pack3d/coppa.py`; nel GLB la coppa e il tappo sono **due
nodi**, e il tappo si toglie.

Ogni PDF ha due disegni che dicono due cose diverse, e servono tutti e due:

| | dice | si legge da |
|---|---|---|
| lo **steso** in grande | dove sta la grafica | il settore anulare dello sleeve, il cerchio del corpo, il rettangolo dell'anello |
| la **vista montata** in miniatura | la forma | i tratti neri: altezza, bocca, fondo, ricciolo, rientro; la sezione del tappo |

### Lo steso

Lo steso e' un **settore anulare**. Il contorno va letto appiattendo le bezier
dal content stream (`cup.py`): ne' la silhouette rasterizzata ne' i punti che
pdfplumber espone per le curve vanno bene, i secondi includono i punti di
controllo.

```
r_bocca = R2 * alpha / 2pi     r_fondo = R1 * alpha / 2pi
apotema = R2 - R1              altezza = radice(apotema^2 - (r_bocca - r_fondo)^2)
```

Queste formule valgono per un cono che si chiude senza sormonto e con la
carta tutta sulla parete. Lo sleeve vero ha il bordo arrotolato in cima, il
risvolto sotto il fondo e il lembo incollato sul lato: sul Nutella POT danno
un'altezza di 122,9 mm contro i 106 della coppa montata. **Lo steso non dice
la forma: la dice la vista montata.**

- Su `fit_sector` guardare **due numeri**, non uno. Residuo basso non basta se
  lo scarto fra gli angoli dei due archi e' alto: 0,001 mm con 14,5 gradi di
  scarto significa cerchio adattato al pezzo sbagliato di contorno. Sul
  Nutella POT i tratteggi del DT passano con 0,020 mm e 9,5 gradi; il taglio
  vero con 0,564 mm e 0,8 gradi, perche' ha gli spigoli arrotondati. Si guarda
  prima lo scarto (`coppa.leggi_steso`).
- I **lati di taglio** sono due rette, misurate lontano dagli spigoli; non
  passano esattamente per il centro, e la carta fra i due si misura arco per
  arco (`Steso.arco`).
- La **piega del fondo** e' l'arco concentrico del DT piu' vicino al taglio di
  sotto: 424,15 mm sul Nutella POT, sopra la fascia neutra del risvolto. Senza
  quell'arco la parete parte dal taglio e il cartellino lo dice.

### La vista montata: la scala dai cerchi gemelli

Le quote della vista montata sono vettorializzate - le legge solo un occhio -
ma i tratti no. Manca solo la scala, e la danno **i cerchi del fondo**, che il
foglio disegna in grande e in miniatura: il rapporto fra i due e' la scala, e
deve tornare su OGNI anello entro lo 0,4% (`coppa.gemello`). Sul Nutella POT
87,5 / 72,5 / 67,2 mm tornano a 1:8,169; sul tappo il corpo da 104,14 a
1:4,26. Misurata cosi', la miniatura rende le quote scritte:

| | quota scritta | misurata sui tratti |
|---|---|---|
| altezza | 106 ± 0,38 | 105,96 |
| bocca | 96,2 ± 0,25 | 96,17 |
| fondo | 73,3 | 73,29 |
| ricciolo | 3,81 ± 0,25 | 3,81 |
| rientro del fondo | 8,29 ± 0,2 | 8,30 |
| gonna del tappo, dentro | 96,1 ± 0,6 | 96,13 |
| altezza del tappo | 15,71 ± 0,5 | 15,71 |

Le pareti si riconoscono perche' pendono come il cono che lo steso impone e
sono simmetriche; il resto della miniatura - cartiglio, legenda, quote - non
ha due rette cosi'.

Le viste montate si leggono DRITTE, quindi un foglio girato sulla tavola si
gira prima di leggerlo (`coppa.orienta`), come gli astucci. Lo sleeve il verso
lo dice da se': la bocca sta sopra, dalla parte opposta al centro degli
archi. Il tappo si prova girato finche' la sezione si trova col piano nella
meta' alta. Coi due fogli girati di 90, 180 e 270 gradi il modello esce
identico: vertici a 0,0 mm, colori sui vertici identici.

### La grafica sulla coppa senza stirarla

La coppa e' il solido di rivoluzione del profilo misurato. Ogni altezza della
parete prende l'arco dello steso che sta alla **stessa distanza dalla piega**,
e lungo quell'arco **tanta carta quanta e' la circonferenza** della coppa li'
(a mezzo spessore), a partire dal taglio sinistro. Quello che avanza e' il
sormonto incollato sotto il lembo: **non si impone, si misura**, e deve
tornare con la riga che il DT disegna lungo il taglio destro. Sul Nutella POT
avanzano 8,6 mm al fondo e 7,7 alla bocca, e il DT ha la riga del lembo a
8,05: torna. Torna anche il cono: la parete della miniatura pende 4,98 gradi,
lo steso ne svolge 4,90.

### Il bordo arrotolato e' bianco fuori

In cima allo steso il DT ha 8,5 mm di **fascia neutra**: niente inchiostro,
perche' la carta li' si arrotola. Si arrotola verso fuori partendo dal lembo,
quindi la fascia neutra finisce al CENTRO del rotolo, e il giro che si vede e'
l'ultimo, quello attaccato alla parete. Lungo quel giro la carta sale dal lato
interno, passa sopra e scende fuori: il marrone della fascia alta copre il
lato interno e la cima, e **il fuori del bordo resta bianco**. Mappato nel
verso sbagliato - dalla parete verso fuori - il bordo usciva marrone fuori e
bianco dentro. Col tappo chiuso il bordo non si vede: conta a coppa aperta.

### Il fronte e' il marchio, non la mezzeria

Il fronte si ancora alla grafica, non alla mezzeria geometrica del settore:
**il gruppo piu' grande di colori vivi**, con i buchi fra lettere vicine
chiusi entro 4 mm (`coppa.fronte`). E' il marchio - NEW e nutella - a +6,8
gradi dalla mezzeria dello steso. Il baricentro di TUTTI i colori vivi lo
tirava verso il box "nutella 60", 20 mm a sinistra, e il marchio usciva
spostato a destra. Il marrone delle fasce gira tutto attorno e non conta: i
colori vivi sono quelli che hanno almeno 115 livelli fra il canale piu' alto
e il piu' basso.

### Il tappo

- **La sezione e' l'unico posto che dice com'e' fatto il tappo montato**: la
  gonna, la nervatura che si aggancia sotto il bordo della coppa, il gradino,
  il ricciolo che stringe il corpo, il piano incassato. Le orizzontali nere
  della sezione sono gli spigoli del giro visti di fronte, e **la piu' lunga
  e' l'interno della gonna**: e' su quella che il DT scrive Ø96,1. Il profilo
  esterno e' il nero piu' a sinistra a ogni altezza; il piano e' la riga
  rossa del corpo.
- Il **piano** si apre sulla cordonatura del corpo appena dentro la gonna:
  Ø88,5 sul Nutella POT.
- Il tappo **poggia col piano sul sommo del bordo**: e' cosi' che la
  nervatura cade subito sotto il ricciolo. Il pack chiuso e' alto 112,2 mm.
  La verifica dice se la gonna calza sulla bocca: 96,13 dentro contro 96,17.
- L'**anello** e' il rettangolo del DT alto quanto la gonna: 97,4 x 15,7.
  La sua stampa e' casuale - il DT lo scrive - e sul modello il motivo si
  ripete attorno, quattro volte, e sul retro si interrompe.

### Senza dichiarazione la coppa si prova per ultima

Dichiarata, la coppa non passa da nessun altro solutore. Senza dichiarazione
si prova solo quando tutto il resto ha fallito, cosi' gli altri pack non ne
pagano la lettura e non possono esserne scambiati: prima il ripiego flowpack
la rifiutava dopo 170 secondi con "saldature di testa non riconosciute".

## Il cono gelato col lid

Il cono gelato - il Camy Apolo T1 Macaron - e' un cartotecnico in **due
pezzi**: lo steso del cono e il lid, il disco che lo chiude, ognuno nel suo
PDF. Si dichiara come la coppa, e la costruzione e' in `pack3d/coppa.py`
(`leggi_cono`, `leggi_disco`, `costruisci_cono`); nel GLB il cono e il lid
sono due nodi. Il DT del cono sta sulla lastra **TROQUEL**, che e' la
fustella in spagnolo: senza quel nome in `techink` il DT finiva nella
grafica.

### Lo steso: un settore pieno, con l'apice sul foglio

Lo steso del cono non e' un settore anulare: l'arco e' uno solo, e il suo
centro - l'apice - sta sul foglio. Il taglio e' il tracciato chiuso che ha:

- un **arco** che passa per piu' contorno di qualsiasi altro cerchio:
  R 172,88 mm sul Camy, apice a (588,20; 826,99) pt, scarto 0,18 mm. I
  cerchi di prova passano per tre punti presi a passi fissi: la stessa
  pagina da' sempre lo stesso arco (`_arco_grande`);
- il **lato radiale**, una retta che passa a 4 mm al piu' dall'apice e arriva
  all'arco: sul Camy passa a 2,0 mm, ed e' una bezier quasi dritta, 0,6 pt
  fuori corda (`_rette` le prende entro un punto);
- il **lembo**: l'altro lato lungo, parallelo all'ultimo raggio e scostato
  quanto il lembo e' largo - 22,0 mm - con una linguetta.

Il contorno dell'abbondanza della grafica ha lo stesso apice: dei due il
taglio e' quello dentro. Il raggio che chiude il cono e' l'**ultimo taglio**
del DT ("last cutting of cone"), un pieno sottile del colore del taglio a R
169,33 +- 0,4: e' la bocca, e la fascia di 3,5 mm fino al taglio e' il
risvolto (vedi sotto).

### La forma dal disegno 1:1

Accanto allo steso il DT disegna il cono montato **in scala 1:1**: due rette
lunghe uguali che convergono con l'angolo del cono (`_disegno_cono`). Ai capi
larghi distano la bocca, a quelli stretti la punta: 64,40 e 2,00 mm, alto
160,51, apotema 163,51, 22,0 gradi - le quote scritte, che sono
vettorializzate, tornano tutte. La riga della quota dell'apotema e' parallela
a un lato e con l'altro fa lo stesso angolo: la si scarta perche' la sua
"bocca" non e' quella che l'ultimo taglio arrotolato da'. Riscontri:

| | disegno | steso |
|---|---|---|
| angolo del cono | 22,0 | 21,8 svolti alla bocca |
| bocca | 64,4 | 64,1 dall'ultimo taglio |
| sormonto | lembo largo 22,0 | 21,2 mm avanzano al giro |

Senza il disegno la forma viene dallo steso - bocca all'ultimo taglio, punta
dove la carta arriva all'apice - e il cartellino lo dice.

### Quale lato sta sopra: lo dice la colla

La colla non tiene sull'inchiostro: il lato che va **sotto** ha lungo il
taglio una fascia di carta non stampata. Sul Camy e' lungo il lato radiale,
larga 12,0 mm per tutta la lunghezza, e il sormonto di 21,2 la copre: il
radiale va sotto, e **sopra resta il lembo**, quello con la linguetta, da cui
il cono si sbuccia (`lato_sopra`). Con il radiale sopra - la prima prova - la
fascia bianca usciva come una striscia lungo il retro del cono. Senza una
fascia su un lato solo resta sopra il radiale, e si dichiara.

Il bordo del lembo e' parallelo all'ultimo raggio, non e' un raggio: sul cono
**gira attorno**, 37 gradi dalla bocca a meta' altezza e sempre piu' stretto
verso la punta, con lo scalino della linguetta. E' la cucitura vera.

### La grafica sulle generatrici

Le generatrici dello steso - i raggi dall'apice - vanno sulle generatrici del
cono: l'angolo dello steso e quello del cono stanno in un **rapporto fisso**,
e alla bocca un giro del cono e' tanta carta quanta la sua circonferenza. La
carta che si vede e' un giro che comincia all'orlo, **riga per riga**
(`orli`): la cucitura segue l'orlo del lembo, e le righe del modello si
infittiscono dove l'orlo gira in fretta (`Maglia.falda`). Ancorare ogni riga
all'orlo senza il rapporto fisso - come sulla coppa, dove il lato di sopra e'
un raggio - torceva la grafica con la cucitura: 37 gradi attorno al cono fra
la bocca e meta' altezza. Con una griglia polare al posto della grafica i
raggi escono dritti e gli archi orizzontali.

### Il risvolto accoppiato

Il cono si chiude **a risvolto**: la fascia fra l'ultimo taglio e il taglio
piega dentro sul lid e lo tiene chiuso. Sul modello e' un anello in piano
alla quota della bocca, stampato sopra - e' la stessa carta della parete, e
la grafica continua - e il lid ci sta **sotto**: piegato, il risvolto arriva
a 28,9 mm dal centro e il lid ne ha 30,5, lo tiene per 1,7 mm e se ne vede un
disco di 57,7. Il riscontro lo dice, e se il risvolto non arriva al lid
l'anello che resta e' bianco e il cartellino dice NON TORNA. Senza il lid il
risvolto resta dritto sopra la bocca, com'e' prima della chiusura.

### Il lid

Il lid e' un disco: il gruppo di cerchi concentrici piu' grande della pagina
(`leggi_disco`). Il Camy ne disegna tre - abbondanza, taglio, area di
sicurezza: 67, 61 e 51 mm - e l'abbondanza e' il cerchio di fuori se il
secondo le sta da 1,5 a 3,2 mm dentro. Un disco da solo non dice di essere un
lid: si cerca solo fra piu' PDF (`orienta(dischi=True)`). Il sopra del
foglio va dietro: guardando il cono dal davanti e dall'alto il lid si legge
dritto.

### Il fronte senza il fondo giallo

Il fronte e' il marchio, come sulla coppa, ma sul cono il colore vivo piu'
esteso e' il **fondo giallo**, due terzi dello steso: un colore vivo che copre
piu' del 30% della carta e' fondo, e si toglie prima di cercare il gruppo piu'
grande (`FONDO_VIVO`). Resta il marchio Camy Apolo, a +4,9 gradi dalla
mezzeria dello steso.

## Casi calibrati

Gli artwork il cui impaginato non rientra nei solutori automatici stanno nel
registro `CASI` in `server.py`, riconosciuti dalla firma della pagina. Oggi
contiene FULFIL Chocolate Hazelnut Whip.

Un caso tarato segue le tre regole come gli altri. Prima ne era fuori: la
grafica si prendeva senza spegnere il disegno tecnico, e le UV non si
confrontavano col DT. Adesso la grafica viene dal suo livello, e le testate
del caso si verificano sulle linee che l'analisi legge nel suo DT; se il
disegno non si legge in automatico - spesso e' il motivo per cui il caso e'
stato tarato - lo si dice, e le testate si controllano sulla miniatura. Il
FULFIL non e' nel parco: su di lui questo non e' stato ancora provato.

Risolti dall'analisi automatica, con l'invariante che chiude:

| | nastro | passo | fronte | spessore | falda |
|---|---|---|---|---|---|
| Milch-Schnitte T1 | 144,0 | 152,5 | 43,0 | 15,0 | 14,0 |
| Kinder Country | 122,0 | 119,0 | 35,0 | 10,0 | 16,0 |
| Kinder Paradiso T1 | 165,0 | 155,0 | 43,0 | 27,0 | 12,5 |
| K Brioss Latte e Cacao T10 | 419,9 | 290,0 | 148,9 | 57,0 | 4,1 |

Risolti come tubo piatto a sovrapposizione, dove non c'e' falda e la sezione la
decide il rigonfiamento:

| | nastro | passo | giro | fronte | lembo coperto |
|---|---|---|---|---|---|
| K Tronky T1 | 83,0 | 144,0 | 71,0 | 36,0 | 12,0 |

Tubo piatto a pinna, con la miniatura che conferma le catene:

| | nastro | passo | giro | fronte | pinna | testate |
|---|---|---|---|---|---|---|
| K Happy Hippo T1 | 115,0 | 115,0 | 83,0 | 41,5 | 16,0 | 15,0 |

Nota sul Tronky: le quote del cartiglio sono testo vettorializzato, non
estraibile — sulla pagina intera pdfplumber trova 20 parole. Sono state lette a
occhio dalla miniatura per verificare il risultato, non per produrlo: 144 = 10 +
124 + 10, 83 = 23 + 36 + 12 + 12.

Display con plancia, con la miniatura che conferma le catene:

| | fondo | pareti | coperchio | plancia sopra il retro | piede |
|---|---|---|---|---|---|
| K Tronky Display T1x48 | 134,0 x 204,0 | 116 / 117 / 116 / 116 | 133,0 x 201,0 | 86,4 + cresta 13,8 | 20,1 |

Astucci, con la quota letta due volte che chiude il conto:

| | fasciatura | L x H x P | riscontro |
|---|---|---|---|
| Nutella Donut | orizzontale, chiuso | 188,1 x 190,8 x 38,1 | fianchi 38,1 = 38,1 |
| K Pingui T6 BOX | verticale, aperto | 140,5 x 125,0 x 40,5 | cielo e fondo 40,5, fianchi 40,3 |

## Assunzioni non verificate

- Il **cono** e' stato costruito su un file solo, il Camy Apolo. Da li'
  vengono la lettura dell'ultimo taglio come piega del **risvolto** (il DT
  lo chiama "last cutting of cone", e la fascia sopra e' larga 3,5 mm), il
  lid che sta **sotto** il risvolto a filo della bocca, e la regola della
  **fascia senza inchiostro** che decide quale lato sta sopra. Un cono col
  lato radiale sopra, o con un risvolto che il DT disegna in un altro modo,
  aspetta un file che lo mostri.
- Gli **spessori dei livelli** 1-3 (0,10 / 0,40 / 0,70 mm) sono valori
  tipici, non misure: la carta del cono non ha cartiglio, e il livello
  l'utente lo sceglie guardando il pack, non un micrometro.

- La **piega della plancia** del display e' dedotta dal DT e dalla grafica, non
  vista su un display vero: e' l'unica in cui tutto torna (vedi *Perche'
  proprio questa piega*), ma se il Tronky T48 in negozio si monta in un altro
  modo, e' su quel file che va corretta.
- La **gola** e' la zona fra la saldatura e la seconda linea del DT dalla
  testata. Confermata dalle quote su Colazione (37,5) e sul Paradiso (10), e
  coerente con la zona grinze di KMS e KP; sul Tronky le due testate non
  tornano (8 e 4 mm) e non si usa. Un DT dove la seconda linea sia un'altra
  cosa - un limite di stampa, un riferimento grafico - aspetta un pack che lo
  mostri.

- Il **DT con la grafica** si sceglie per taglia e poi per colori distinti.
  Le copie a pari scala sul parco sono tecniche - campiture piatte, 12-32
  colori - contro i 142-261 dei DT con la grafica. Una copia a pari scala con
  una grafica vera sopra - una prova colore, un'altra versione del pack -
  non e' ancora passata: li' vincerebbe la piu' colorata, che puo' non essere
  quella giusta. E un DT che non faccia griglia - meno di sei linee lunghe -
  non conta come DT: si torna alla scelta per colore.

- La **pulizia fuori dal DT** e' esatta quanto e' giusto il DT: se l'analisi
  legge uno steso sbagliato, fuori va anche grafica vera. Ma quella grafica
  non sarebbe finita comunque sul modello, che si ritaglia dallo stesso
  steso. Le scritte si stimano larghe al piu' un corpo e mezzo a glifo: un
  font con glifi piu' larghi, che parta fuori dal DT e ci entri, verrebbe
  tolto. Non e' ancora passato.

- Il **colore della didascalia** come chiave per le didascalie che non dicono
  "area" e' stato visto su due file: il Kinder Cards (in curve) e il B-ready
  ("INGREDIENTS", "WEIGHT", "F8 LEGAL TEXT", tutte nel colore di "Text Area").
  Se la didascalia scritta fosse nera come un codice a barre vero dentro lo
  stesso riquadro, il codice a barre se ne andrebbe con lei; e se un file
  finito avesse il testo legale vero dentro il box `TEXT AREA` e nello
  stesso colore della sua didascalia, se ne andrebbe il testo. Sul B-ready
  "BEST BEFORE AREA" ed "EAN CODE" sono nere, e i box non hanno codici veri.
- La **promo** e' l'unica area che resta, ed e' una scelta su un file solo:
  l'`AREA PROMO` del K Brioss (FERRERO_1765...) e' grafica. Un file con un
  box promo vuoto, segnaposto, lo lascerebbe stampato.
- Il **campione di legenda** e' letto solo DAVANTI alla scritta, sulla sua
  riga: le legende del parco sono tutte cosi'. Una legenda col campione
  dietro, sopra o in una colonna lontana non insegna niente.

- La **tacca di fotocentratura** del Kinder Cards restava sulla texture col
  suo contorno verde e la diagonale, tratti da 1 pt che le penne della
  fustella (0,35 e 0,7) non prendevano. Sono della lastra `Technical Drawing
  light`, e adesso vanno via per nome con lei (`techink.disegno`). La tacca
  nera, che si stampa davvero, resta; resta anche un filo chiaro lungo la
  diagonale, dove si toccano i due triangoli neri che la diagonale copriva.

- Che il **fronte di un vassoio sia la testata piu' bassa** e' la logica di un
  espositore, non una misura: sul parco le due testate sono alte uguali, e un
  display con fronte e retro diversi non e' ancora passato.

- La **spalla lunga 1,7 volte il calo** e' tarata su un bollino solo, quello
  del Paradiso: e' il punto in cui la discesa piu' ripida sta sui 48 gradi e
  il film si stira di 1,2 in modo uniforme. Che la spalla cominci dentro il
  prodotto quando la gola del DT non basta e' fisica - il film non si allunga
  - ma di quanto lo faccia un pack vero, a seconda di quanto e' morbido il
  prodotto, manca una foto che lo misuri.

- Il livello **Medio** di gonfiore e' interpolato fra Rigido e Morbido: manca un
  caso reale.
- Il **raggio di raccordo** e' trattato come proprieta' del film, quindi
  assoluto e non proporzionale allo spessore.
- L'**apertura della pinna** non e' piu' una costante: e' una scelta 1-3.
  Il fondo scala 3 vale meta' perimetro pieno (`PACK3D_FIN_OPEN = 1.0`); il
  94,8% misurato su un solo render e' stato scartato perche' non era lui a
  produrre le punte degeneri. Il gradino 2 e' interpolato e non ha un caso
  reale dietro.
- Lo **steso ruotato** e' stato visto su un artwork solo, Kinder Pingui T1: la
  regola "se le fasce non chiudono, ritenta trasposto" non ha un secondo caso.
- Su disegno speculare, quando i due rientri di saldatura differiscono di piu'
  di 0,5 mm si tiene **il piu' stretto**. Anche questa viene da un campione
  solo, e la scelta opposta sarebbe altrettanto difendibile.
- Il canale `quote.larghezza` / `quote.spessore` dall'analisi AI alla
  costruzione **non e' mai stato percorso con una chiave API vera**: e'
  verificato end-to-end con l'agente simulato, non con l'agente.
- La **coppa** ha un caso solo dietro, il Nutella POT 500: lo steso a
  settore, la vista montata accanto ai cerchi del fondo, la sezione del tappo
  accanto al corpo. Un disegno con la vista montata altrove, o senza cerchi
  gemelli, oggi non si costruisce e lo dice.
- Lo **spessore della carta della coppa** e' 0,35 mm: 260 g/m2 piu' il PE,
  dal cartiglio, ma lo spessore il DT non lo scrive. Sposta i diametri di
  mezzo spessore, e il sormonto misurato di un millimetro scarso.
- Il **ricciolo** e' un cerchio alto quanto la quota, come nella miniatura;
  quello vero e' arrotolato e un po' schiacciato. Il lato interno del
  ricciolo del tappo, troppo piccolo nella sezione per leggerlo tratto per
  tratto, e' una discesa dritta dal sommo al piano.
- L'**astuccio aperto** ha un caso solo dietro, il Kinder Pingui T6 BOX, e ha
  due falde di retro. Il vassoio vero — nessuna falda, retro del tutto assente
  — il codice lo prevede ma **non l'ha mai visto**: la faccia del retro
  semplicemente non viene costruita, e nei cartellini si dichiara.
- L'avviso sull'**RGB** guarda le immagini sopra il mezzo megapixel. La soglia
  e' scelta perche' separa il parco validato dai tre file con grafica in RGB,
  non perche' un documento la fissi; e una colata **vettoriale** in RGB, se
  esiste, passerebbe inosservata.
- Lo **spessore del cartoncino** e' 0,45 mm, che e' un cartoncino teso da
  astuccio plausibile e non una misura su questo pack. Il PDF non lo dice, e
  nessuno l'ha misurato col calibro.
- Il **colore del rovescio** del cartoncino e quello del **taglio** sono due
  tinte neutre scelte a occhio: l'artwork descrive solo la faccia stampata.
  Su un cartoncino patinato su un lato il rovescio e' grigio, su un GC1
  bianco, e dal PDF non si distingue.
