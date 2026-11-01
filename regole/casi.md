# Regole: Casi calibrati e assunzioni non verificate

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Casi calibrati

Gli artwork il cui impaginato non rientra nei solutori automatici stanno nel
registro `CASI` in `pack3d/famiglie/flowpack.py`, riconosciuti dalla firma della pagina. Oggi
contiene una barretta proteica.

Un caso tarato segue le tre regole come gli altri. Prima ne era fuori: la
grafica si prendeva senza spegnere il disegno tecnico, e le UV non si
confrontavano col DT. Adesso la grafica viene dal suo livello, e le testate
del caso si verificano sulle linee che l'analisi legge nel suo DT; se il
disegno non si legge in automatico - spesso e' il motivo per cui il caso e'
stato tarato - lo si dice, e le testate si controllano sulla miniatura. La
barretta proteica non e' nel parco: su di lei questo non e' stato ancora provato.

Risolti dall'analisi automatica, con l'invariante che chiude:

| | nastro | passo | fronte | spessore | falda |
|---|---|---|---|---|---|
| T1 della barretta fresca | 144,0 | 152,5 | 43,0 | 15,0 | 14,0 |
| T1 ai cereali | 122,0 | 119,0 | 35,0 | 10,0 | 16,0 |
| T1 farcito | 165,0 | 155,0 | 43,0 | 27,0 | 12,5 |
| brioche latte e cacao | 419,9 | 290,0 | 148,9 | 57,0 | 4,1 |

Risolti come tubo piatto a sovrapposizione, dove non c'e' falda e la sezione la
decide il rigonfiamento:

| | nastro | passo | giro | fronte | lembo coperto |
|---|---|---|---|---|---|
| wafer T1 | 83,0 | 144,0 | 71,0 | 36,0 | 12,0 |

Tubo piatto a pinna, con la miniatura che conferma le catene:

| | nastro | passo | giro | fronte | pinna | testate |
|---|---|---|---|---|---|---|
| T1 cold seal | 115,0 | 115,0 | 83,0 | 41,5 | 16,0 | 15,0 |

Nota sul wafer T1: le quote del cartiglio sono testo vettorializzato, non
estraibile — sulla pagina intera pdfplumber trova 20 parole. Sono state lette a
occhio dalla miniatura per verificare il risultato, non per produrlo: 144 = 10 +
124 + 10, 83 = 23 + 36 + 12 + 12.

Display con plancia, con la miniatura che conferma le catene:

| | fondo | pareti | coperchio | plancia sopra il retro | piede |
|---|---|---|---|---|---|
| display T1x48 | 134,0 x 204,0 | 116 / 117 / 116 / 116 | 133,0 x 201,0 | 86,4 + cresta 13,8 | 20,1 |

Astucci, con la quota letta due volte che chiude il conto:

| | fasciatura | L x H x P | riscontro |
|---|---|---|---|
| astuccio della ciambella | orizzontale, chiuso | 188,1 x 190,8 x 38,1 | fianchi 38,1 = 38,1 |
| T6 aperto | verticale, aperto | 140,5 x 125,0 x 40,5 | cielo e fondo 40,5, fianchi 40,3 |

## Assunzioni non verificate

- Il **controllo dell'AI** e la scelta del **rigonfiamento** sono stati
  provati con un'API finta, che risponde come quella vera, e guardando a mano
  le immagini che ricevono: il cono letto come astuccio, messo accanto al suo
  artwork, si vede sbagliato a colpo d'occhio. Con una chiave vera non sono
  ancora passati. Le prime costruzioni sullo Space vanno guardate insieme al
  verdetto.
- La **coda** e' stata provata con un GitHub finto, e poi dal vero col primo
  caso, il gelato su stecco: PDF, verdetto e viste nel repository privato, e la sua
  issue. Il caso si e' risolto insegnando al solutore i tratteggi a trattini
  separati e la faccia giusta della falda (vedi *Un tratteggio e' una linea* e
  *Della falda si vede la fascia dell'altro capo del nastro*).
- La **falda** si corica sempre dalla parte di g0, dove in tutti i file visti
  sta la fascia neutra. Un file con la fascia neutra dall'altro capo non l'ho
  mai visto: sul modello si riconoscerebbe dalle tacche della fotocellula o
  dal tratteggio sulla falda.
- La **correzione degli inchiostri** e' provata su un file solo, il T1 al mandarino
  senza livelli: sullo Space il Claude vero ha scelto le stesse sette lastre
  scelte a mano guardando la tavola. Un file dove il disegno tecnico usa le
  stesse Pantone della grafica non si corregge cosi', e il controllo lo lascia
  in dubbio.
- I **pieni candidati** sono solo rettangoli allineati alle linee del
  disegno. Un segno tecnico in quadricromia di un'altra forma - un tratteggio
  a mano, un cerchio - non arriva a Claude, e resta.
- Il **cono** e' stato costruito su un file solo, il cono T1 macaron. Da li'
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
  proprio questa piega*), ma se il display T1x48 in negozio si monta in un altro
  modo, e' su quel file che va corretta.
- La **gola** e' la zona fra la saldatura e la seconda linea del DT dalla
  testata. Confermata dalle quote sul wafer da colazione (37,5) e sul T1 farcito (10), e
  coerente con la zona grinze dei T1 della barretta fresca e della merendina; sul wafer T1 le due testate non
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
  "area" e' stato visto su due file: il T2 di cialde (in curve) e il pane ripieno
  ("INGREDIENTS", "WEIGHT", "F8 LEGAL TEXT", tutte nel colore di "Text Area").
  Se la didascalia scritta fosse nera come un codice a barre vero dentro lo
  stesso riquadro, il codice a barre se ne andrebbe con lei; e se un file
  finito avesse il testo legale vero dentro il box `TEXT AREA` e nello
  stesso colore della sua didascalia, se ne andrebbe il testo. Sul pane ripieno
  "BEST BEFORE AREA" ed "EAN CODE" sono nere, e i box non hanno codici veri.
- La **promo** e' l'unica area che resta, ed e' una scelta su un file solo:
  l'`AREA PROMO` della brioche (file 1765...) e' grafica. Un file con un
  box promo vuoto, segnaposto, lo lascerebbe stampato.
- Il **campione di legenda** e' letto solo DAVANTI alla scritta, sulla sua
  riga: le legende del parco sono tutte cosi'. Una legenda col campione
  dietro, sopra o in una colonna lontana non insegna niente.

- La **tacca di fotocentratura** del T2 di cialde restava sulla texture col
  suo contorno verde e la diagonale, tratti da 1 pt che le penne della
  fustella (0,35 e 0,7) non prendevano. Sono della lastra `Technical Drawing
  light`, e adesso vanno via per nome con lei (`techink.disegno`). La tacca
  nera, che si stampa davvero, resta; resta anche un filo chiaro lungo la
  diagonale, dove si toccano i due triangoli neri che la diagonale copriva.

- Che il **fronte di un vassoio sia la testata piu' bassa** e' la logica di un
  espositore, non una misura: sul parco le due testate sono alte uguali, e un
  display con fronte e retro diversi non e' ancora passato.

- La **spalla lunga 1,7 volte il calo** e' tarata su un bollino solo, quello
  del T1 farcito: e' il punto in cui la discesa piu' ripida sta sui 48 gradi e
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
- Lo **steso ruotato** e' stato visto su un artwork solo, T1 della merendina: la
  regola "se le fasce non chiudono, ritenta trasposto" non ha un secondo caso.
- Su disegno speculare, quando i due rientri di saldatura differiscono di piu'
  di 0,5 mm si tiene **il piu' stretto**. Anche questa viene da un campione
  solo, e la scelta opposta sarebbe altrettanto difendibile.
- Il canale `quote.larghezza` / `quote.spessore` dall'analisi AI alla
  costruzione **non e' mai stato percorso con una chiave API vera**: e'
  verificato end-to-end con l'agente simulato, non con l'agente.
- La **coppa** ha un caso solo dietro, la coppa da 500: lo steso a
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
- L'**astuccio aperto** ha un caso solo dietro, il T6 aperto, e ha
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
