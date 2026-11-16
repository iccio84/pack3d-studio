# I materiali POP

I materiali per il punto vendita: **totem** ed **espositori**, e poi
dondolini, strip, vele, angolari, portaprezzi, sticker. Si caricano dalla
loro finestra di Glam, «Crea materiali POP 3D da PDF», e il codice sta in
`pack3d/pop/`. Qui le loro regole, a parte da quelle dei pack.

## Il confine

**Il POP e i pack non si toccano.** Dal proprietario: «Per ogni caso pop
nuovo con relative regole non bisogna però coinvolgere le altre famiglie
(flowpack crt etc). Quindi eventuali aggiornamenti pr merge dovranno essere
limitati a pop e viceversa».

Il repository e' diviso in tre parti (`prove/confini.py`):

| parte | cosa | chi la tocca |
|---|---|---|
| **POP** | `pack3d/pop/`, `regole/pop.md`, `prove/test_pop.py` | solo le PR del POP |
| **comune** | la pagina, `server.py`, la coda (`pack3d/coda.py`), il registro e i tipi dichiarati (`pack3d/famiglie/registro.py`, `comune.py`), il parco (`prove/parco.py`), le prove comuni (`prove/test_veloci.py`), il workflow, i documenti in cima al repository | tutte e due, per l'aggancio |
| **pack** | tutto il resto: `pack3d/` (flowpack, astucci, vassoi, coppe, incarti... e i moduli che usano: fustella, piegatura, texture, GLB), `regole/` | solo le PR dei pack |

- **Una PR verso `coda-settimana` o e' del POP o e' dei pack.** Puo' toccare il
  comune con l'una o con l'altra, mai il POP e i pack insieme. Nelle Actions
  `prove/confini.py` la ferma (`.github/workflows/prove.yml`).
- **Il POP usa i moduli dei pack, non li cambia.** Leggere la fustella,
  piegare, scrivere il GLB, fare la texture e il template: il POP li chiama.
  Se gli serve una modifica in uno di quei moduli, e' una PR dei pack a
  parte, prima, col parco che prova che nessun pack cambia.
- **Il comune legge il POP, non lo nomina.** Il registro e i tipi dichiarati
  prendono da `pack3d.pop` i materiali (`MATERIALI_POP`, `NOMI_POP`), la
  lettura (`analisi`) e le costruzioni (`COSTRUZIONI`): un materiale nuovo
  entra in `pack3d/pop/`, nella sua voce della pagina e qui, senza toccare
  il registro.
- **Il parco lo prova.** Dopo una PR del POP nessun caso dei pack cambia, e
  dopo una dei pack nessun caso POP (RILASCIO.md).
- **Le prove a parte**: quelle del POP in `prove/test_pop.py`, non in
  `prove/test_veloci.py`.

## La finestra

La pagina dello Space con `pop=1` nell'indirizzo (GLAM.md, sezione 10):
chiede «Che tipo di materiale POP intendi realizzare?» e ha le voci dei
materiali. Lo Space costruisce il totem e l'espositore: `pop.analisi` legge
i PDF del materiale - tutti, il totem ne ha due - e `pop.COSTRUZIONI` porta
le costruzioni nel registro delle famiglie (dal 15 novembre 2026, chiesto
dal proprietario: «aggiorna le 2 famiglie»). Un PDF che non si legge, o un
materiale che il codice non sa ancora costruire, si ferma alla lettura e
diventa un caso, che chi l'ha caricato manda con «Invia il caso». Il modello
torna nella finestra POP di Glam (`X-Model-Section: pop`).

## Il totem

Espositore da terra: un pannello in piedi sulla sua base. Il totem
lenticolare lo costruisce lo Space (`pack3d/pop/totem.py`): la pagina
chiede due PDF, il pannello del fronte e quello del retro, e con un PDF solo
il totem si ferma e lo dice. Quello che sappiamo dal proprietario:

- **piatto o curvato.** Per il proprietario «lenticolare» vuol dire il
  **pannello curvato**, non la stampa lenticolare. La curva si legge dal PDF:
  le centine ad arco in fustella, o le quote del raggio o della freccia; la
  larghezza del pannello steso e' la lunghezza dell'arco. Se il PDF non la
  dice, e' una scelta del pack, non una regola per tutti;
- **i popup**: sagome in rilievo applicate davanti al totem, staccate da un
  distanziale (una linguetta piegata a Z o a ponte). Dove stanno e quanto
  sporgono lo dice il disegno di montaggio, o una scelta del pack;
- la sezione puo' avere una faccia curva e il retro piatto, o due facce
  curve: lo dice la fustella.

### Il totem lenticolare

Dal proprietario (13 novembre 2026): «Ora proviamo un totem lenticolare: in
allegato 2 pdf fronte e retro più un render di riferimento. I pannelli
devono essere piegati in modo da essere curvo (la geometria non deve essere
sfaccettata) e alla base ci deve essere una piattina in plastica bianca che
permette al totem di stare su».

Poi (15 novembre 2026): «Il totem deve essere composto dai 2 pannelli
piegati allo stesso modo, uno poi va girato di 180 gradi in modo che diventi
il retro dell'altro formando così una struttura unica di forma ellittica
(visto dall'alto). Ovviamente geometricamente devono essere separati. La
parte posteriore di ogni singolo pannello va bianca. Inoltre ogni volta che
riconosci un popup elimina l'elemento grafico dalla struttura in modo che
rimanga solo nel popup. Il popup va più spesso e non va mai piegato»; «il
basamento deve essere ovale in modo da ospitare fronte e retro»; la colata
«come per i pack, in quadricromia (ombra nera e non ciano)».

- **Due PDF, due pannelli.** Ognuno e' una pagina col pannello steso: il
  contorno di taglio (il tracciato chiuso piu' grande del colore del
  taglio, `fustella.contorni_di_taglio`, con le Bezier vere di pdfium) e,
  dentro, i contorni dei popup.
- **Curvi uguali, il retro girato.** Ogni pannello e' un cilindro con la
  stampa fuori (la larghezza stesa e' l'arco); il retro e' lo stesso girato
  di 180 gradi: da sopra un'ellisse. I bordi dei due archi stanno a 1 mm
  (`totem.FESSURA`): due pezzi, mai compenetrati. Il dietro di ogni pannello
  e' bianco. Lisci: una fila di vertici ogni 6 mm lungo l'arco.
- **La freccia**, se il PDF non la dice, e' una scelta (`totem.FRECCIA`, un
  sesto della larghezza, dal render di riferimento).
- **I popup** sono piatti, mai piegati, spessi 5 mm (`totem.SPESSORE_POPUP`),
  a 12 mm dal pannello nel loro punto di mezzo, perpendicolari al raggio, con
  un distanziale bianco. La loro grafica esce dal pannello: gli oggetti del
  PDF col centro dentro il contorno del popup (`fustella.oggetti_dentro`) si
  tolgono dalla resa del pannello e restano su quella del popup.
- **In quadricromia.** La grafica si rende con la resa dei pack
  (`strati.rendi`), che simula la sovrastampa: l'ombra della colata esce
  nera, non ciano come con pdfium (`fustella.resa_quadricromia`). Il taglio,
  le note e la grafica dei popup si tolgono confrontando le rese di pdfium.
- **La base**: un ovale di plastica bianca spesso 6 mm che contiene i due
  pannelli con 40 mm attorno; i pannelli ci stanno sopra.

## L'espositore

Da banco o da terra: la struttura coi ripiani o i vani dove stanno i
prodotti. Si comincia da qui (dal proprietario, 13 novembre 2026: «aggiungiamo
oltre al pulsante totem anche il pulsante Espositore e poi iniziamo da
quello»). Ancora da costruire: ogni PDF caricato e' un caso in coda.

- **Il nome.** Per i pack «espositore» e' un sinonimo di vassoio
  (`famiglie.comune.SINONIMI_KIND`): il materiale POP si chiama
  `espositore_pop`, e sul pulsante «Espositore». Nessun materiale POP puo'
  avere il nome di un tipo o di un sinonimo dei pack: lo controlla
  `prove/test_pop.py`.
- **Non e' il vassoio.** Il vassoio espositore e il display con plancia sono
  pack (regole/vassoi.md): l'espositore POP ne puo' usare i moduli - la
  fustella, la piegatura, il GLB - ma non li cambia (*Il confine*).

### Come si costruisce (`pack3d/pop/espositore.py`)

Dal PDF della fustella: i pezzi si riconoscono dalle pieghe e dalla stampa,
e ognuno si piega e si monta con le misure che legge (`misure`). Lo Space lo
costruisce da un PDF solo; se nella fustella non ci sono i due fianchi e lo
schienale la lettura si ferma, e il PDF va in coda.

- **La grafica senza il disegno tecnico.** Dal proprietario: «Elimina il dt
  senza intaccare la grafica». Non si ritocca l'immagine (un ritocco attorno
  ai segni rovinava i loghi e i testi vicini): si tolgono dal PDF gli
  OGGETTI del DT prima di renderlo (`fustella.resa_senza_dt`). Se il DT ha
  uno strato suo, si toglie tutto lo strato, con le quote e i triangoli di
  orientamento; se non ce l'ha, o lo strato ha anche la grafica, solo i
  tracciati che stanno sulle linee dei tagli e delle pieghe.
- **Le note si tolgono.** Dal proprietario: «le note rosa vanno tolte». Lo
  strato delle note (le zone rosa della colla e di quello che non si
  stampa, le scritte dei pezzi) non e' stampa: si toglie dal PDF come il DT
  (`fustella.NOTE`, dal nome dello strato). Dove non c'e' grafica resta il
  cartone bianco, come sul fondello.
- **I triangoli di orientamento** non sono tagli (`fustella._triangolo`).
- **I contorni morbidi.** Dal proprietario: «i tracciati sono seghettati.
  Usa le curve di bezier». Il bordo di ogni pannello e' quello del PDF: le
  curve di Bezier campionate ogni 1,5 mm (`fustella.PASSO_CURVA`), non i
  gradini dei pixel della maschera.
- **Lo spessore col colore della grafica.** Dal proprietario: «fai in modo
  che gli spessori siano arancioni (o comunque in linea con la grafica)».
  Il bordo tagliato prende il colore della stampa a 3 mm dal bordo.
- **Lo spessore dalle pieghe doppie.** Le due cordonature di una piega a
  180 gradi stanno a due spessori: la mediana di quelle dei fianchi, dei
  ripiani e del divisorio, divisa per due (`espositore.spessore`). Sul primo
  PDF 4 mm, onda EB; prima era fisso a 6, troppo (dal proprietario: «fare
  gli spessori piu' bassi»).
- **Le pieghe tonde.** Dal proprietario: «simulando la piega del cartone
  (bordi arrotondati)». Le pieghe doppie diventano archi
  (`espositore.piega_tonda`): mezzo giro sul bordo davanti dei fianchi, in
  cima ai fianchi, sul davanti dei ripiani e sul dorso del divisorio; un
  quarto di giro fra il davanti e i lati della testata. Fuori la stampa,
  dentro il raggio meno lo spessore. La testata appoggia sopra la cima
  tonda.
- **Anche le pieghe semplici, con la stessa curvatura.** Dal proprietario:
  «le curvature delle pieghe teniamo queste anche per gli altri». Una piega
  semplice fra due pannelli piatti diventa tonda, raggio fuori uguale allo
  spessore (`Montaggio.arrotonda`): gli angoli del frontalino e del
  riempitivo, il fondo dei fianchi, le alette e le linguette dei ripiani,
  il bordo davanti del fondello (a 180 gradi). Solo dove la stampa sta
  fuori dalla piega, lo spigolo che si vede: dove sta dentro (gli angoli
  della schiena, le alette del divisorio) il cartone vero fa lo spigolo
  vivo sulla stampa, e resta vivo. La curvatura e' una regola del POP:
  vale anche per i materiali che verranno.
- **La prefustella incisa.** Dal proprietario: «il lato del crowner ha le
  fustelle incise come i pack ... (prefustella stampata)». Sui lati della
  testata l'arco e le diagonali non tagliano e non piegano: sono solchi a V
  nella faccia stampata (largo 1 mm, profondo 0,9), con la grafica dentro,
  come l'apertura a strappo degli astucci e dei vassoi
  (`incisioni.maglia_incisa`). Sono i tagli che non toccano il contorno
  (`fustella.tagli_interni`) e le pieghe oblique.
- **Nessuna compenetrazione fra parti diverse.** Dal proprietario: «evita
  intersezioni tra le diverse parti». Dove due cartoni starebbero nello
  stesso posto, quello che viene dopo nell'ordine (`espositore.ORDINE`: il
  corpo, il divisorio, i ripiani, la testata, il riempitivo, il frontalino,
  il fondello; le alette sul pavimento per ultime) si intaglia, come la
  feritoia vera. `espositore.intersezioni` controlla il modello fatto.
- **Da verificare col proprietario**: il fondo della colonna di sinistra e'
  il fondello (largo quanto l'interno, con la feritoia del divisorio), non
  un terzo ripiano; il frontalino sta sul davanti dei ripiani; i piedi
  della testata entrano nei fianchi e non si vedono; i lati della testata
  sono piatti, con la prefustella incisa.

### L'espositore in più PDF: a ripiani (`pack3d/pop/ripiani.py`)

Dal proprietario (16 novembre 2026): «Questo espositore è composto da più
pdf. Può capitare che un espositore possa essere in un unica pagina o più
pdf». La pagina prende tutti i PDF insieme, nel posto dell'espositore, e lo
Space li riceve tutti. Con un PDF solo l'espositore è quello di sopra; con
più PDF, uno per pezzo, è l'espositore da terra a ripiani:

- **quale pezzo è quale** lo dicono i pezzi del PDF, non il nome del file
  (`_ruolo`): due pezzi uguali sono i laterali, due diversi il ripiano (il
  vassoio e il suo risvolto), uno più alto che largo la schiena, uno largo
  più del doppio dell'altezza la base, l'altro il crowner. Di un PDF di più
  pagine si monta la prima: il crowner del caso ha tre grafiche, ed è stata
  scelta del proprietario («Solo la prima pagina»);
- **la tavola comune**: ogni PDF si legge da solo e si mette accanto agli
  altri con la sua grafica, in quadricromia; da lì il montaggio è quello
  del primo espositore (`espositore.Montaggio`);
- **il fianco**: l'ala della schiena (la striscia e l'ala, il fianco
  interno) sta fra la parte stampata del laterale, fuori, e la sua aletta
  con le asole, dentro; la piega doppia del laterale è lo spigolo davanti.
  La parte stampata a destra della piega è il fianco destro, a sinistra il
  sinistro: così le bottiglie si leggono dritte da fuori;
- **i ripiani**: tanti quanti ne dice il proprietario («si i ripiani sono 4»),
  alle asole dell'aletta dei laterali: il piano poggia sul fondo
  dell'asola. Un'asola disegnata a tratti separati conta una volta (`_asole`).
  Il vassoio è stampato fuori: sotto il piano, sulle sponde e sul fronte col
  marchio; dentro resta senza stampa, e il risvolto del fronte si ripiega
  dentro. Sul PDF il risvolto e il resto sono due pezzi e i lati del fronte
  non hanno linee: si fa un pezzo solo, coi lati chiusi da due pieghe
  (`_vassoio`), che dà le misure. Dal proprietario: «il vassoio sembra
  bucato sugli spessori. Deve essere un pezzo unico», poi «il vassoio non va
  bene. Vedo troppi fori e artefatti. Fai cartoncino spesso con angoli
  smussati». Il vassoio non si stende più a pannelli: è un solido solo
  (`_vassoio_solido`), chiuso, di cartoncino spesso (`SPESSORE_VASSOIO`,
  4 mm), con gli angoli tondi in pianta (`RAGGIO_VASSOIO`, 10 mm) e lo
  spigolo del fondo smussato (`SMUSSO_VASSOIO`, 4 mm). Le misure sono quelle
  del PDF: il piano, la fascetta alta quanto il fronte, la sponda di dietro,
  i fianchi che scendono in obliquo verso il fondo come sul PDF. Fuori la
  grafica del PDF (la fascetta col marchio, i fianchi, il fondo), dentro il
  cartone senza stampa. Il risvolto, le orecchie e gli angoli non si vedono
  e non si fanno;
- **la base**: lo zoccolo davanti, col fronte inclinato. Dal proprietario,
  col render di riferimento: «Crowner è basamento sono montati male». Il
  fianco e la sua aletta oltre la piega obliqua sono un trapezio solo,
  piatto sulla faccia stampata del laterale (il tratteggio in basso sul
  laterale è la colla): montato, il bordo in cima e quello sul pavimento
  stanno in orizzontale e il bordo di fondo in verticale, contro la
  schiena. Per questo il fronte pende quanto quei bordi sul PDF (25 gradi
  sul caso, `_pendenza`), non quanto la piega obliqua, che è più ripida.
  Il cielo dello zoccolo sta davanti allo spigolo del laterale; davanti
  allo spigolo resta il triangolo del fianco. Il ripiano più basso poggia
  sul cielo quando l'asola è più bassa del cielo (sul caso 202 mm invece
  di 186: l'asola è alta 35 mm, il vassoio ci sta lo stesso);
- **l'aletta in cima alla schiena**, con la feritoia: dal proprietario,
  «anche la schiena ha la aletta che va dietro (quella superiore dove c'è
  il crowner)». È girata di 180 gradi dietro la schiena, e fra le due resta
  la tasca della linguetta del crowner;
- **il crowner**: dietro la cima della schiena, il piede del pannello (dove
  finiscono le pieghe doppie) al filo del corpo, il pannello nella tasca
  fra la schiena e la sua aletta. Dal proprietario: «il
  crowner ha le alette girate di 180 gradi come rinforzo». La piega doppia
  è larga quanto il cartone: le alette si ripiegano piatte dietro il
  pannello e abbracciano l'aletta della schiena, e la striscia oltre la
  piega a tratti si ripiega ancora, piatta dietro l'aletta. Ogni strato ha
  il suo spessore: pannello, aletta della schiena, alette del crowner,
  strisce («Il crowner ha anche delle intersezioni sui lati della grafica»:
  le alette stavano nello spessore del pannello). Da davanti si vede solo il pannello, come nel render del
  proprietario; la linguetta scende dietro la schiena;
- **un contorno aperto** (il davanti del ripiano è una cordonatura, gli
  angoli hanno i tagli aperti) si chiude con le pieghe disegnate, solo
  quando dai soli tagli il cartone non c'è (`Griglia.pannelli`,
  `PIENO_MIN`): il primo espositore e il totem escono uguali al byte;
- **le alette nascoste** (la linguetta in cima ai laterali, quelle sotto la
  schiena e la base) non si montano.

### L'espositore a scaffale, tutti i pezzi su una pagina (`pack3d/pop/scaffale.py`)

Dal proprietario (16 novembre 2026), con un PDF solo: «Genera questo
espositore». Nessun render di riferimento («No, procedi tu»): i pezzi
visibili si montano come si leggono dal PDF, e chi guarda il modello lo
corregge. Il PDF ha tutti i pezzi su una pagina, ognuno col suo nome e la sua
quantità, e un disegno tecnico diverso dagli altri espositori:

- **i tagli neri e le pieghe rosse**, linee continue (`tratti`; il colore in
  grigio, RGB o CMYK, `_tipo`). Una piega può essere disegnata a «L», due
  lati di un rettangolo in un tratto solo: si spezza in tratti dritti
  (`_dritti`). Un PDF col disegno tecnico degli altri espositori (le pieghe
  tratteggiate del colore dei tagli) resta all'espositore di sopra, anche se
  ha linee nere e rosse (`e_scaffale`);
- **la scala**: la pagina del caso è 2,97 x 2,10 m, e ogni pezzo misura
  0,5015 volte la sua scritta (le scritte sono curve, non testo: non si
  leggono). Una pagina più grande di due A0 è in scala 1:2 (`scala`): le
  misure vengono a meno di 5 mm dalle scritte;
- **il tratteggio delle zone incollate** (arancio, verde acqua) non è stampa.
  Sta negli stessi gruppi della grafica: togliendo i gruppi spariva anche il
  marchio sulla fascetta dei ripiani. Si fa trasparente il tratto, in
  memoria, insieme ai tagli e alle pieghe (`_Resa`); riscritta, la pagina
  usciva nera.

**Quale pezzo è quale** lo dice la forma (`riconosci`), non il nome: i
fianchi sono i due pezzi grandi uguali con le pieghe lunghe; la schiena è
alta quanto loro e stretta; il ripiano è il pezzo stampato con più pieghe
orizzontali lunghe; il dekl è stampato, largo poco più della schiena e
basso; il topper è stampato, senza pieghe e senza tratteggio (un pezzo tutto
tratteggiato è un rinforzo, `_tratteggiati`). Il montaggio:

- **il fianco** è a doppia parete: la faccia stampata fuori, la piega doppia
  davanti (10 mm: lo spessore del fianco), la parete di dentro con le asole
  dei ripiani; dietro, oltre l'ultima piega, la striscia che gira sul retro
  della schiena, dove si avvita. La faccia stampata a destra della piega
  doppia è il fianco destro;
- **la schiena** sta dietro, alta quanto i fianchi (1434 mm sul caso);
- **i ripiani**: uno per asola dei fianchi (5 sul caso, a 303 mm l'uno
  dall'altro). L'asola è alta 11 mm, quanto il ripiano: il fondo stampato
  sotto, il pannello di dietro girato di 180 gradi sopra il fondo e
  stampato sopra (in mezzo i rinforzi, il tratteggio), la fascetta col
  marchio che sale davanti. Le alette ai lati stanno nelle asole e non si
  vedono;
- **il dekl** chiude lo zoccolo sotto il ripiano più basso: le orecchie
  contro i fianchi (i fori combaciano con quelli dei fianchi, dove si
  avvita), il bordo in cima sotto il ripiano;
- **il topper** sta davanti alla schiena, così la grafica si vede (dal
  proprietario: «tira più in avanti il crowner in modo che si possa vedere
  la grafica (davanti alla schiena)»). È largo più dello spazio fra le pareti
  di dentro dei fianchi (600 contro 592 mm sul caso): poggia sulla loro
  cima dietro (1384 mm sul caso);
- **non si montano** i pezzi dentro le pareti (i rinforzi dei fianchi e dei
  ripiani, le croci dello zoccolo), i tappi, i portaprezzi e la scatola di
  trasporto.
