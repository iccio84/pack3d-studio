# Le schede dei difetti

Per chi corregge un caso della coda (CODA.md): i difetti che tornano, uno per
scheda - come si riconoscono, dove si guarda, cosa si prova prima, e quali
regole li hanno gia' risolti. Servono a partire dal punto giusto invece che
da zero. `prove/parco.py prepara` le cerca da solo: confronta i difetti del
verdetto e le voci di chi ha caricato il PDF con le **parole** di ogni scheda
e stampa quelle che toccano il caso. Una scheda e' un punto di partenza, non
la risposta: la causa si conferma sul caso (CODA.md, *Il giro*, punto 5).

Ogni scheda ha una riga `Parole:` - pezzi di parola, in minuscolo, separati
da virgole - che `prepara` cerca nel testo. Una scheda nuova si aggiunge
quando un difetto torna la seconda volta, con le sue parole.

## La famiglia sbagliata

Parole: costruito come, invece di un, invece che, tubo, pinne inventate, dentellat, non esistono, famiglia

- **Si riconosce**: un astuccio costruito come flowpack (un tubo con le
  pinne seghettate), un flowpack piegato a scatola; la grafica dei pannelli
  avvolta su un tubo.
- **Dove**: `pack3d/famiglie/registro.py`, `RICONOSCIMENTO`: le prove in
  ordine, ognuna con le tipologie dichiarate per cui vale. La riga che ha
  preso il caso la dice la lettura (`prove/parco.py letture --solo <nome>`).
- **Prima prova**: il caso aveva una tipologia dichiarata? Una dichiarazione
  vale anche quando dice di no (REGOLE.md, indice). Se il solutore della
  famiglia giusta ha rifiutato la fustella, la correzione e' li', non
  nell'ordine delle prove.
- **Regole**: `regole/pulizia.md` *La tipologia non riconosciuta e' un
  errore, non un ripiego* e *Un file che si dichiara film prova prima il
  flowpack*; `regole/pdf.md` *Perche' un file nuovo non si costruisce*.

## Costruito sulla miniatura o sul disegno sbagliato

Parole: miniatura, cartiglio, misure di, contro i circa, troppo piccol, quota, tratteggio diagonale

- **Si riconosce**: il modello e' di pochi centimetri, o porta i tratteggi e
  le quote di uno schema; le misure non hanno niente a che fare col pack.
- **Dove**: `pack3d/tools.py` `dt_della_tavola`, `pack3d/artwork.py`
  `pagina_unica`: quale disegno della tavola si prende.
- **Prima prova**: guardare nel foglio di `prepara` quanti disegni ci sono
  sulla tavola e quale e' quello in scala 1:1 (il piu' grande, con la
  grafica dentro).
- **Regole**: `regole/pdf.md` *Prima delle tre regole: una pagina, un DT* e
  *Prima le quote, poi via tutto quello che sta fuori dal DT*.

## Il fronte sul retro, la grafica capovolta

Parole: fronte, retro, capovolt, sottosopra, logo, marchio, dietro

- **Si riconosce**: il marchio finisce sul retro o sulla cima, la scritta si
  legge al contrario, la vista di fronte mostra un fianco.
- **Dove**: `pack3d/artwork.py` `verso_della_grafica` e
  `astuccio_sulla_grafica` (il foglio girato prima di risolverlo),
  `pack3d/verifica.py` `fronte_flowpack` e `giro_del_marchio` (il fronte e il
  marchio sul modello finito).
- **Prima prova**: il foglio era girato prima di risolverlo? Se le misure del
  modello sono giuste ma il fronte no, il difetto e' quasi sempre nella
  scelta del fronte, non nella piegatura.
- **Regole**: `regole/pdf.md` *Il foglio nel verso della grafica, prima di
  risolverlo* e *Il modello finito si gira: il marchio orizzontale e dritto*;
  `regole/flowpack.md` *A pari scarto il fronte lo dice la stampa*;
  `regole/astucci.md` *Il retro e' la faccia che porta i fianchi*.

## Ruotato di 90 gradi, proporzioni scambiate

Parole: ruotat, 90 gradi, di traverso, proporzion, lungo nel verso, girato

- **Si riconosce**: il pack e' giusto ma girato (lo stecco di traverso, il
  pack alto invece che lungo), oppure largo e basso dove dovrebbe essere
  stretto e alto.
- **Dove**: per il flowpack `pack3d/flowpack.py` (il passo e il nastro, le
  guide) e `pack3d/dieline.py`; per l'astuccio `dieline.solve_carton`.
- **Prima prova**: confrontare le tre misure del modello (`misure` nel JSON
  del caso) con quelle del DT: se sono le stesse in un altro ordine, e' il
  verso; se una e' diversa, e' la lettura del DT (scheda *Le misure non
  tornano*).
- **Regole**: `regole/flowpack.md` *Prima le misure, poi il contenuto* e *Le
  guide ravvicinate: due letture, non una scelta*; `regole/pdf.md` *Il
  modello finito si gira*.

## Le misure non tornano, un pannello stirato

Parole: misure, non tornano, stirat, stiro, mm contro, pannello di, profondit, spessore

- **Si riconosce**: una faccia molto piu' larga o stretta del pannello del
  DT, la grafica stirata (il controllo la ferma da solo sopra una soglia),
  uno spessore sbagliato.
- **Dove**: `pack3d/dieline.py` (la fustella letta), `pack3d/quote.py` (il
  riscontro con le quote scritte), `pack3d/tracciati.py`; per lo stiro del
  fronte `pack3d/verifica.py` `stiri_flowpack`.
- **Prima prova**: la lettura del PDF del caso (`<nome>_lettura.jpg` nella
  cartella di `prepara`): se le misure lette sono gia' sbagliate, il difetto
  e' nella lettura, non nella costruzione.
- **Regole**: `regole/pdf.md` *Mezzo millimetro non puo' cambiare il pack*;
  `regole/astucci.md` *La griglia non tollera un intruso* e *Un astuccio ha
  uno spessore*; `regole/flowpack.md` *La falda dice se la soluzione e'
  sbagliata*.

## La grafica manca, le facce bianche

Parole: bianc, grigi, manca tutta, non compare, non compaiono, vuot, senza grafica

- **Si riconosce**: il modello ha la forma giusta ma e' bianco o grigio, o
  una parte della grafica (un logo, una fascia) manca.
- **Dove**: `pack3d/strati.py` (i livelli spenti, `senza_tecnici`,
  `sovrastampe`), `pack3d/colata.py`, `pack3d/steso.py` (la texture e' lo
  steso), `pack3d/artwork.py` (le coperture tolte).
- **Prima prova**: `prove/parco.py stesi --solo <nome>`: se la texture non
  e' lo steso, il difetto e' nel giro della texture; se lo e', e' un livello
  spento di troppo o una copertura tolta per sbaglio.
- **Regole**: `regole/pulizia.md` *Chi lo dice davvero e' il livello* e *Le
  coperture si tolgono per nome, non per euristica*; `regole/pdf.md` *La
  texture e' lo steso*.

## Segni tecnici sulla texture

Parole: quota, tratteggi, segni tecnic, cartiglio, legenda, crocin, linee di piega, gda

- **Si riconosce**: sulle facce restano quote, tratteggi, legende, il
  tracciato della fustella o la GDA.
- **Dove**: `pack3d/strati.py` `senza_tecnici`, `pack3d/techink.py` (gli
  inchiostri tecnici), `pack3d/artwork.py` (aree riservate, GDA, box).
- **Prima prova**: il segno sta su un livello suo? Se si', e' il nome del
  livello che non si riconosce; se no, il colore da solo non basta mai.
- **Regole**: `regole/pulizia.md`, tutta la parte *Togliere il disegno
  tecnico: cinque livelli*, e *La GDA si toglie da tutte le grafiche*.

## La scatola aperta, una chiusura che manca

Parole: aperta, chiusura, coperchio, fessura, aletta, falda, interno grigio, non chiusa

- **Si riconosce**: l'astuccio aperto in cima o sul fondo, una fessura fra
  due coperchi, un'aletta stampata che non c'e'.
- **Dove**: `pack3d/dieline.py` `solve_carton` (quali pannelli sono le
  chiusure), `pack3d/folding.py` `build_faces` (come si piegano).
- **Prima prova**: le alette e i coperchi sono nella fustella letta? Se il
  solutore li ha scartati, il difetto e' nella lettura; se ci sono, nella
  piegatura.
- **Regole**: `regole/astucci.md` *Un astuccio puo' non chiudersi*, *Le
  falde del retro sono fasce, non facce* e *Quando il solutore non sa, deve
  dirlo*; `regole/ballotin.md` *La cima: chi sta sotto lo dice il
  tratteggio*.

## Le pinne e le saldature del flowpack

Parole: pinna, pinne, saldatur, testat, zigrin, sovrapposizion, fasce

- **Si riconosce**: le fasce della pinna lunga diventano le saldature di
  testa, le testate sono dove non devono, la chiusura e' quella sbagliata.
- **Dove**: `pack3d/flowpack.py` (la chiusura, le testate), `pack3d/famiglie/flowpack.py`
  `build_flowpack`, `pack3d/verifica.py` `testate_flowpack`.
- **Prima prova**: la chiusura letta (pinna, sovrapposizione o tubo piatto)
  e' quella del PDF? Poi dove sono i capi dello steso.
- **Regole**: `regole/flowpack.md` *Due chiusure, non una*, *Come si sceglie
  la chiusura*, *I capi dello steso sono il taglio, non il centro del
  gruppo*, *La grafica sulle pinne: il film non si allunga*.
