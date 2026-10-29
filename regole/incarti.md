# Regole: Incarti

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## L'incarto a triangolo

Il foglio di film che avvolge una barretta rigida e si chiude sulle testate
ripiegato, senza saldature ne' pinne: la barretta incartata T1 (il
disegno dice «WRAPPING (DOUBLE FOIL)»). Il codice sta in `pack3d/incarto.py`, il montaggio in
`famiglie.incarto.build_incarto`. Dalla pagina si dichiara **Incarti**, chiuso **a
pieghe** (vedi *Gli incarti nella pagina*, sotto); dichiarato flowpack (e' un
film) o senza tipo, lo si riconosce lo stesso: l'analisi
lo prova **prima** del flowpack, perche' il flowpack non lo rifiuta ma lo
risolve male - un tubo gonfio con le pinne seghettate al posto delle testate
- e sui flowpack esce subito (`famiglie.incarto._analisi_incarto`; su tutto il parco
non scatta mai, in qualche decimo di secondo). La pagina non chiede denti,
rigonfiamento e pinne: costruisce subito.

- Il **DT** e' un rettangolo, il passo lungo la barretta (141 mm) e il nastro
  attorno (70). Le righe intere, da un taglio all'altro, sono gli spigoli
  della barretta: cinque fasce, 18,75 | 10,5 | 17,5 | 10,5 | 12,75. Una riga a
  meno di 3 mm da un taglio non fa fascia (sulla barretta incartata T1 quella a 1 mm,
  dove l'eye-mark non e' stampato).
- La **faccia** e' la fascia di mezzo, quella con le testate dritte: la
  barretta li' e' lunga 108 mm (16,5 di lembo per parte). Sui **fianchi** le
  testate sono inclinate, da 16,5 a 14 mm dal taglio: la barretta alla base
  e' lunga 113, e la testata e' un piano inclinato di 14 gradi. Le due fasce
  di fuori sono il **fondo**, con le testate in diagonale fino al taglio.
- Il **sormonto** del fondo e' la riga intera piu' lontana dal suo taglio
  dentro una delle due fasce del fondo (tratteggiata, sulla barretta incartata T1 a 10
  mm): li' arriva il taglio dell'altra fascia, che sta sopra, a vista. Se il
  DT non la disegna, 0,8 volte la fascia del fondo piu' stretta, ed e'
  dichiarato stimato.
- La **sezione** e' un trapezio: la faccia (17,5) in cima, il fondo largo
  quanto avanza del nastro (31,5 - 10 = 21,5), i fianchi (10,5) inclinati;
  alta 10,3 mm.
- La **testata** si chiude come nelle foto del pack (la barretta
  appoggiata sul fondo, vista dal davanti): in mezzo il **lembo bianco
  della faccia**, che scende sulla testata e finisce a punta poco sopra la
  base; ai lati le due **alette rosse dei fianchi**. **Il rosso sta
  sopra**: le alette sono ripiegate sul lembo della faccia («il rosso deve
  stare sopra», dopo una versione col bianco sopra le alette). E sulla base
  **un'aletta sta sopra l'altra**, come una chiusura di carta: ognuna ha il
  bordo sulla retta dal suo angolo in cima a un punto della base oltre la
  meta' (fra le due 4 mm di sormonto, `SORMONTO_ALETTE`); le due rette si
  incrociano poco sopra la base, e li' finisce la punta del lembo bianco;
  sotto, l'aletta di sopra copre quella di sotto e il suo bordo arriva fino
  alla base. Sopra sta quella col retro (`ALETTA_SOPRA`): nella foto il
  bordo arricciato, a vista, e' il suo. Il lembo del fondo sta sotto tutto
  e non si vede. Ogni pezzo e' il foglio piegato sulla sua piega, senza
  stirarsi; le alette prendono la grafica dal loro lembo sulla riga di
  mezzo della fascia, a un millimetro dal taglio (vicino alle righe della
  faccia il lembo ha le onde bianche della faccia, che nel pack piegato
  finiscono nelle pieghe; sul taglio la texture ha il suo orlo). Le
  versioni prima: il triangolo del lembo sopra le alette; staccato verso la
  punta («deve essere un pezzo unico e i risvolti visibili sono i due
  laterali rossi»); a filo, piatto; le due alette una sopra l'altra a
  coprire tutta la testata (da «un'aletta deve finire sopra l'altra come
  una chiusura di carta»), corretta con le foto («le alette devono essere
  come in foto»); il triangolo con le due alette unite alla punta («una
  aletta deve stare sopra l'altra. qui sono unite»).
- **Un monoblocco con tutti gli spigoli e gli angoli arrotondati**: una
  superficie sola e chiusa (nessuno spigolo libero, le normali tutte fuori),
  gli spigoli lunghi tondi di 1,5 mm (`RAGGIO`) e quelli delle testate pure
  (1,5 mm, `RAGGIO_TESTA`): agli angoli i due raccordi si incontrano e anche
  l'angolo e' tondo. A spigoli vivi sembrava un blocchetto di legno. La
  grafica gira attorno agli spigoli senza stirarsi (la piega del foglio sta
  a meta' dell'arco).
- La **testata** e' piana sotto i lembi: tre zone, divise dalle due rette
  delle alette. E' fatta coi punti stessi del bordo del raccordo, compresi
  i tre dove i lembi si incontrano (le due rette in cima e quella
  dell'aletta di sopra sulla base): fra testata e raccordo non resta fessura (con un bordo
  semplificato ne restava una di 0,14 mm). Il fondo non ha il gradino del
  sormonto: i due capi della sezione cadono nello stesso punto. La
  versione prima aveva i risvolti a strati di 0,3 mm, staccati e col bordo
  a vista («fai i risvolti piu' a vista, spessi»), e il gradino del
  sormonto sotto; poi e' stata chiesta cosi': «un monoblocco con tutti gli
  angoli/spigoli smussati».
- **Lo spessore delle alette**: stanno su, sul lembo della faccia, come un
  foglio un po' spesso che si piega - zero in cima, piu' spesse verso la
  base (fino a 0,9 mm, `SPESSORE_ALETTE`), e di nuovo zero entro 2,5 mm dal
  bordo della testata (`BORDO_ALETTE`), dove l'aletta e' il foglio che gira
  sullo spigolo del suo fianco o della base. L'aletta di sotto torna a zero
  anche sotto il bordo di quella di sopra, che le si appoggia: il bordo di
  quella di sopra e' a vista tutto, dall'angolo in cima alla base. Sotto i
  3 millesimi di mm lo spessore e' zero (`NETTO`): i bordi di un niente
  lasciavano vertici quasi uguali e triangoli girati male. Sul bordo della
  testata lo spessore e' zero, e i raccordi restano tutti di 1,5 mm.
  Chiesto dopo il monoblocco piatto: «fai in modo che si veda di piu' lo
  spessore delle pieghe, lasciando invariati gli smussi; piu' spesse le
  alette verso la base e meno sugli angoli smussati».
- **I bordi delle alette sono smussati**, come il foglio spesso che si
  ripiega: una parete alta quanto sporge l'aletta (fino a circa 0,7 mm),
  dal suo sopra fino a quello che c'e' sotto, con gli spigoli tondi di un
  quinto della sua altezza (`SMUSSO_BORDO`), e sporge di altrettanto. Le
  versioni prima: un gradino vivo, che sembrava tagliato («riesci a fare lo
  spessore piu' morbido/smussato come in foto?»); poi mezzo cerchio, troppo
  morbido («fai i bordi meno morbidi come da foto»).
- **Il taglio del fondo sulla testata**: il taglio del sormonto ha un orlo
  bianco, che lungo il fondo si vede come una riga. Sulla testata il fondo
  sta sotto le alette: la piega del raccordo parte dalla riga di mezzo
  della fascia del fondo, e l'orlo resta sul corpo (prima ne arrivava un
  rettangolo bianco vicino alla base della testata).
- **Un buco bianco sugli angoli** (corretto): a meta' di ogni spigolo tondo
  il raccordo passa da un lembo all'altro, e un triangolo solo fra i due
  prendeva la grafica da due punti lontani del foglio, portando sull'angolo
  il bianco della faccia. Li' la riga del raccordo e' doppia, una per lembo.
  Sul fondo la meta' della grafica si prende dalla fascia, non dalla
  posizione: sul taglio del sormonto cade fra le due.
- La barretta si modella con le sue facce, senza l'interno. Il fronte (la
  faccia col marchio) guarda +Z, la testa della scritta +Y.

### Gli incarti nella pagina

La famiglia **Incarti**: un foglio di carta, alluminio o plastica che avvolge
un prodotto e si chiude **con le pieghe** (le barrette) o **avvolgendolo**
tutto (tipo l'ovetto con la sorpresa). La misura finale del 3D non dipende
solo dallo steso ma anche dal **prodotto**: per questo la pagina, oltre al
PDF, chiede **l'immagine del prodotto da incartare**.

- La pagina chiede prima come si chiude (`chiusura`: `pieghe` o `avvolto`),
  poi mostra due posti, il PDF dello steso e l'immagine; il tasto del
  secondo apre la scelta delle immagini. Un file trascinato va nel posto
  del suo tipo. L'immagine si rimpicciolisce a 1600 px sul lato lungo, in
  JPEG, come la foto della nota.
- Il corpo della richiesta e' il PDF e poi l'immagine, di fila: `parti`
  ne da' le lunghezze e `prodotto` (`nome`, `tipo`) dice che l'ultimo
  pezzo e' l'immagine. Il server la separa subito (`_separa_prodotto`: deve
  essere davvero una JPEG, PNG o WebP, al massimo 12 MB). Senza immagine un
  incarto si ferma con 400; un'immagine con un'altra famiglia pure.
- **A pieghe** si costruisce come l'incarto a triangolo; se il PDF non e'
  un incarto a triangolo, si ferma e va in coda. **Avvolto** il codice non
  lo sa ancora costruire: si ferma subito, e il caso va in coda col PDF e
  l'immagine.
- L'immagine **va col caso** (`prodotto_<nome>.jpg`, accanto al PDF) e nei
  dettagli tecnici c'e' una riga che la nomina, con le sue misure in pixel.
  **Per ora la misura del modello la da' il DT**: l'immagine non entra
  ancora nella costruzione.
- Gli **incarti parzialmente scartati** (la barretta che esce dal foglio
  aperto) nella pagina non ci sono ancora: come chiederli si decide dopo,
  per esempio con un'immagine guida.

### Cosa manca

- Sul fondo il DT segna due pieghe diagonali per testata, dagli spigoli del
  fondo verso il mezzo: la carta li' e' piegata su se stessa. Il modello ha
  il fondo liscio.
- Il foglio deve stare dritto sulla tavola, il passo in orizzontale; e la
  scritta della faccia si legge con la testa verso la fascia di sopra.
- L'incarto **avvolto** (l'ovetto) non si costruisce: va in coda.
- L'immagine del prodotto non entra ancora nella misura del modello.
- Gli incarti parzialmente scartati nella pagina.
