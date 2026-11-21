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

**Il foglio si legge dritto** (`incarto.sulla_tavola`): il passo in
orizzontale e la scritta della faccia con la testa in su. Se le cinque
fasce non si trovano in orizzontale si prova la pagina girata di un quarto;
e capovolta - le fasce sono simmetriche e si riconosce lo stesso - si gira
di mezzo giro se il testo vivo della faccia, o senza quello il testo della
tavola fuori dal foglio, si legge a 180 gradi: la stessa regola del verso
del flowpack. Prima la barretta incartata T1 girata di un quarto non si
riconosceva, e capovolta usciva con la scritta a testa in giu'
(`prove/parco.py varianti`, 1 novembre 2026). Il quarto di giro si prova
solo sull'incarto dichiarato: quello non dichiarato si cerca su ogni
flowpack, che non paga una lettura in piu'.

Dal 29 ottobre 2026 la barretta incartata T1 e' nel parco
(`barretta_incartata_t1`), col suo PDF e l'immagine del prodotto, chiusa a
pieghe: gli incarti erano l'unica famiglia senza un caso, e nessuna
modifica poteva romperli senza che si vedesse. `prove/parco.py stesi` salta
l'immagine del prodotto, che non e' un foglio.

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

- **Di quanti pezzi e' composto**, prima di tutto: dal 20 novembre 2026,
  chiesto dal proprietario («abbiamo visto con l'uovo che gli incarti
  possono avere piu' elementi»). Poi come si chiude (`chiusura`: `pieghe` o
  `avvolto`), poi i posti: un PDF per pezzo e l'immagine. Un pezzo solo e'
  il PDF dello steso; l'avvolto in due pezzi ha il foglio e il collarino
  (in qualunque ordine: `uovo.riconosci`); con altri numeri i posti sono
  «Pezzo 1», «Pezzo 2»... Cambiando i pezzi o la chiusura i file gia'
  caricati restano, ognuno nel primo posto del suo tipo. Il numero va al
  server in `pezzi`, che controlla che i PDF siano tanti quanti. Il tasto
  del posto dell'immagine apre la scelta delle immagini. Un file trascinato va nel posto
  del suo tipo. L'immagine si rimpicciolisce a 1600 px sul lato lungo, in
  JPEG, come la foto della nota.
- **Un pezzo senza grafica** (dal 21 novembre 2026, con la pralina): nel
  posto di ogni pezzo c'e' il tasto **«Senza grafica»**, che riempie il
  posto senza file («senza grafica: stagnola dorata»); compare solo se un
  altro pezzo resta con la grafica. I numeri di questi pezzi, da 1, vanno
  al server in `senza_grafica` (`server.senza_grafica`), e allora i file
  devono essere i pezzi meno quelli senza grafica.
- **La grafica di un pezzo puo' essere un'immagine** (JPEG, PNG o WebP),
  non solo un PDF: il bollino e il pirottino della pralina sono arrivati
  cosi'. Il posto di un pezzo prende tutti e due («Carica PDF o
  immagine»), e l'immagine va coi suoi pixel, senza rimpicciolirla. Sul
  server, solo per gli incarti, un pezzo che e' un'immagine (dai primi
  byte: `server._immagine`) diventa subito un PDF di una pagina
  (`famiglie.incarto.immagine_in_pdf`: il JPEG coi suoi byte, le altre
  senza perdita), e da li' segue la strada dei PDF - la lettura, il
  controllo, la coda, il parco - senza cambiare nient'altro; il caso in
  coda tiene l'immagine com'e' arrivata. Un'immagine trascinata va prima
  nel posto del prodotto, poi in quello di un pezzo vuoto: per sceglierlo
  si usa il tasto del posto.
- Il corpo della richiesta e' il PDF e poi l'immagine, di fila: `parti`
  ne da' le lunghezze e `prodotto` (`nome`, `tipo`) dice che l'ultimo
  pezzo e' l'immagine. Il server la separa subito (`_separa_prodotto`: deve
  essere davvero una JPEG, PNG o WebP, al massimo 12 MB). Senza immagine un
  incarto si ferma con 400; un'immagine con un'altra famiglia pure.
- **I pezzi che il codice non sa ancora montare** - a pieghe piu' d'uno (un
  foglio interno e uno esterno, una fascetta), avvolto diverso da due - si
  fermano nella lettura col messaggio che dice cosa sa costruire
  (`analisi_incarto_dichiarato`), e il caso va in coda coi PDF e
  l'immagine: e' la routine a imparare il pezzo nuovo.
- **A pieghe** si costruisce come l'incarto a triangolo; se il PDF non e'
  un incarto a triangolo, si ferma e va in coda. **Avvolto** si costruisce
  l'uovo incartato col collarino (*L'uovo avvolto*, sotto); due PDF che non
  sono il suo foglio e il suo collarino si fermano col messaggio che dice
  cosa sa montare, e il caso va in coda coi PDF e l'immagine. **Avvolto in
  tre pezzi, uno senza grafica**, si costruisce la pralina (*La pralina
  avvolta*, sotto); un pezzo senza grafica in ogni altra combinazione si
  ferma col messaggio della pralina, e va in coda.
- L'immagine **va col caso** (`prodotto_<nome>.jpg`, accanto al PDF) e nei
  dettagli tecnici c'e' una riga che la nomina, con le sue misure in pixel.
  **Per ora la misura del modello la da' il DT** (per l'uovo, il primo
  caso): l'immagine non entra ancora nella costruzione.
- Gli **incarti parzialmente scartati** (la barretta che esce dal foglio
  aperto) nella pagina non ci sono ancora: come chiederli si decide dopo,
  per esempio con un'immagine guida.

### Cosa manca

- Sul fondo il DT segna due pieghe diagonali per testata, dagli spigoli del
  fondo verso il mezzo: la carta li' e' piegata su se stessa. Il modello ha
  il fondo liscio.
- L'incarto **avvolto** si costruisce solo com'e' l'uovo del primo caso:
  vedi *L'uovo avvolto*, *Cosa manca all'uovo*.
- L'immagine del prodotto non entra ancora nella misura del modello.
- Gli incarti parzialmente scartati nella pagina.
- La pralina: vedi *La pralina avvolta*, *Cosa manca alla pralina*.

## L'uovo avvolto

L'uovo di cioccolato incartato: il foglio quadrato di film lo avvolge tutto,
si raccoglie sopra in un collo e si apre in un ciuffo; il collarino di
cartoncino stringe il collo e gli fa sul davanti l'ovale col marchio. Il
codice sta in `pack3d/uovo.py`, il montaggio in
`famiglie.incarto.build_uovo`; dalla pagina si dichiara **Incarti**,
chiuso **avvolto**, coi due PDF e l'immagine del prodotto. La lettura e'
`dict(kind="uovo", title="Uovo incartato col collarino")`, la costruzione
`"uovo"` in `COSTRUZIONI`. E' nato dal primo uovo incartato al latte
(`uovo_incartato_latte` nel parco), arrivato coi due PDF e cinque foto del
pack montato (davanti, i due fianchi, dietro, dall'alto), dal 18 novembre
2026.

**I due PDF**, in qualunque ordine (`uovo.riconosci`): ognuno dice da se'
cos'e'. In tutti e due il DT sta nello strato `technical-drawing` e le note
in `notes`, e il DT si ripete in piu' **viste**, una per lastra: i pezzi del
DT che si toccano (a meno di 10 mm) fanno una vista, in ordine di lettura -
per righe, poi da sinistra (`uovo._viste`).

- **Il foglio**: almeno due viste quadrate uguali, di 880 mm (all'1 per
  cento, `LATO_TOLL`). La prima e' la grafica, la seconda il **bianco**
  (white plate): dove c'e' il bianco la stampa e' opaca, altrove resta a
  vista il **film metallizzato** (PET argento). Le viste sono arrotondate
  al mm. Le altre due viste del primo caso (l'argento e il dentro) non
  servono: lo dice un avviso.
- **Il collarino**: almeno tre viste uguali di 264,2 x 205,3 mm (entro 3
  mm, `COLLARINO_MM`): la grafica, la **vernice lucida** e il **rilievo**.
  La zona di ogni vista e' il suo DT allargato di 3 mm ai lati e di 5 sopra
  e sotto; le lastre sono la zona della grafica spostata della loro vista,
  al decimo di mm (le tre zone devono avere gli stessi pixel). L'**oro** e'
  la lamina a freddo: si riconosce dal colore della grafica (`ORO`).
- Le **note** del DT con un testo d'esempio (una zona arancione, una guida
  fino al riquadro col testo) mettono il testo nella zona (`abbina`,
  `grafica_vista`).

**Il solido** (il fronte guarda +Z, la cima +Y, il fondo a Y = 0):

- **L'uovo** ha la sagoma della foto di dietro (`SAGOMA`): appoggia sulla
  valva con un fondo piatto (`BASE`, 15 mm, con lo spigolo tondo di 4) e si
  allarga a cono fino alla pancia, poi si chiude sotto il collo; il foglio lo
  segue con le pieghe schiacciate sull'uovo (`N_PIEGHE`). Il collo, l'anello
  dove il foglio si raccoglie, sta a 182 mm (`Y_COLLO`), col foglio raccolto
  di 39 mm di raggio (`COLLO`).
- **Il ciuffo** e' il resto del foglio sopra il collo: quattro petali, il
  davanti e il dietro coi contorni delle foto (`ARCO`, `ARCO_DIETRO`, la
  profondita' `PROF_DAVANTI`, `PROF_DIETRO`) e i due di lato piu' bassi.
  **Ogni colonna del foglio sta nel suo semipiano verticale** attorno
  all'asse, con l'angolo che cresce nel giro: due colonne non si toccano
  mai, e le pieghe e le grinze spostano i punti dentro il loro semipiano,
  non piu' del raggio della curva. Il ciuffo parte da dentro il collarino,
  che ne copre un pezzo, e sale dietro l'ovale (`Ostacoli`).
- **In cima davanti e dietro si chiudono come mani giunte**: sopra 140 mm
  dal collo (`Y_STRINGE`) z si scala dello stesso fattore a ogni altezza,
  fino a 0,05 in cima (`S_CIMA`, `stringi_z`). E' una deformazione dello
  spazio che si inverte, quindi non crea intersezioni, e visto di fronte il
  ciuffo non cambia. Le punte grandi arrivano a circa 3 mm una dall'altra.
- **Dentro il collo** un imbuto pieghettato copre il fondo dell'uovo (`tappo`):
  dall'alto non si vede il vuoto.
- **Il collarino e' di cartoncino rigido**: dritto, senza scalini, senza
  curvare in alto. Il davanti dell'ovale e' una linea dritta che sale
  indietro di 0,07 mm per mm (`PENDENZA`), il resto un cono; le braccia
  escono dall'ovale all'altezza della fascia (`Y_FASCIA`) e girano attorno
  al collo sulla fascia (`Y_BANDA`), sempre fuori dal foglio. Dove si
  toccherebbero si schiaccia il ciuffo, mai il collarino.
- **Nessuna compenetrazione**: il controllo delle intersezioni (una faccia
  per superficie, i vertici saldati al micron) torna zero coppie.
- **La texture** e' un atlante: la grafica del foglio, quella del collarino e
  il rovescio del film (azzurro metallizzato, `DENTRO`); il rovescio sta
  sugli stessi vertici della stampa, coi triangoli girati. I lembi di lato
  mostrano fuori il rovescio, come nelle foto di fianco. La mappa di metallo
  e ruvidezza porta il film metallizzato fuori dal bianco, la vernice
  lucida e l'oro del collarino; la mappa delle normali le grinze fini del
  film e il rilievo del collarino.

**Le versioni**, dalle correzioni di chi aveva il pack: un uovo che non
somigliava a un uovo di Pasqua; poi le foto («deve essere un uovo di
pasqua»); il fondo stretto, perche' l'uovo appoggia su una valva («il fondo
non puo' essere ovale»); niente intersezioni fra le superfici; il collarino
piu' in alto, senza stringere in alto, col ciuffo che parte da dentro;
il collarino senza scalini («al massimo schiaccia il fiocco»), rigido e
dritto («essendo di cartoncino e' rigido»); il ciuffo chiuso, che dall'alto
non mostri il buco. Per chiuderlo: una cupola (rifiutata, «torna alla
versione precedente»), le punte verso il centro (che pizzicavano i petali
su se stessi), le punte che si toccano tirate fino all'asse (in disordine:
una V in mezzo al petalo davanti, «i petali si intersecano o comunque
fanno casino»), e infine la chiusura in profondita' qui sopra, approvata
come versione ufficiale.

### Cosa manca all'uovo

- La sagoma dell'uovo e quella del ciuffo vengono dalle foto del primo
  caso: un uovo di un'altra misura, o un foglio che non e' di 880 mm, si
  ferma e va in coda. L'immagine del prodotto non entra nella misura.
- Un avvolto senza collarino (l'ovetto, una caramella) non si costruisce:
  si ferma col messaggio di quello che il codice sa montare.
- Le viste del foglio dopo il bianco (l'argento, il dentro) non si usano:
  il rovescio e' una tinta piena.
- Fra i petali restano fessure strette: nel modello a semipiani due petali
  vicini non si sovrappongono.

## La pralina avvolta

La pralina incartata: una pralina avvolta in un quadrato di stagnola dorata
stropicciata, senza grafica, con un **bollino** ovale in cima e un
**pirottino** di carta plissettata sotto. Il codice sta in
`pack3d/pralina.py`, il montaggio in `famiglie.incarto.build_pralina`; dalla
pagina si dichiara **Incarti**, **3 pezzi**, chiuso **avvolto**, col pezzo
della stagnola **«Senza grafica»**, i file del bollino e del pirottino (PDF
o immagini) e l'immagine del prodotto. La lettura e'
`dict(kind="pralina", title="Pralina incartata")`, la costruzione
`"pralina"` in `COSTRUZIONI`. Nel parco e' `pralina_incartata`.

E' nata da un modello **fatto a mano** il 20 novembre 2026, fuori dal
codice, e approvato dal proprietario (pack3d-casi, `lavori/pralina`: lo
script, le immagini e cosa ha chiesto, in ordine); il 21 novembre e' entrata
nel codice. **La geometria e' quella dello script approvato**, numero per
numero e con gli stessi semi: i vertici dei triangoli tornano uguali al
micron (confrontati sul GLB finito, dopo `primitive.rifinisci`).

**I due file**, in qualunque ordine (`pralina.riconosci`): ognuno dice da
se' cos'e'. Un PDF che e' un'immagine sola (quello che il server fa da
un'immagine) da' quell'immagine coi suoi pixel; un PDF vero si rende a 2048
px sul lato lungo (`immagine_del_pdf`). Poi si ritaglia sulla parte
stampata, i pixel non bianchi (`stampato`, sotto 245 in un canale):

- **il bollino** e' piu' largo che alto, di piu' del 10% (`OVALE`): l'ovale
  stampato su bianco. Un ovale piu' alto che largo si gira di un quarto.
- **il pirottino** e' quadrato: il disco della carta stesa (anche tutto
  pieno, com'e' l'immagine del primo caso: marrone fino agli angoli).
- Due bollini o due pirottini si fermano, col messaggio che dice cosa si e'
  letto, e il caso va in coda.

**Il solido** (il fondo del pirottino a Y = 0, la cima +Y; la testa della
scritta del bollino verso -Z, come nel modello approvato):

- **La stagnola**: una sfera di 14,8 mm di raggio (`R`, centro a 16,9),
  circa 31,6 mm stropicciata, dall'icosaedro diviso 6 volte (~82 mila
  triangoli), con le normali lisce. Le pieghe sono quelle approvate: un
  fondo appena ondulato (12 onde da 9 a 16 mm, 0,06 mm) e 280 pieghe lunghe
  (`pieghe_lunghe`): archi sulla sfera da 8 a 20 mm, sezione 1/cosh^2 larga
  0,9-2,2 mm, profonde 0,22-0,58 mm, creste e valli, il 45% lungo il
  meridiano verso il bollino, che si assottigliano alle punte. Sotto il
  bollino la stagnola e' liscia, e la cima e' schiacciata a una cupola
  appena bombata col minimo morbido (nessuno spigolo).
- **L'oro satinato**: colore pieno (sRGB 206 166 98), metallo 1, ruvidita'
  0,46, e la **trama a rettangolini** nella mappa delle normali: una tegola
  di 3,5 mm con 10 x 14 rettangolini appena bombati, ripetuta, sulle UV
  azimutali dall'alto (nessuna cucitura).
- **Il pirottino**: la ciotola di carta a 52 pieghe a dente di sega,
  arrotondate in cima (il bordo ondeggia senza punte); 21,2 mm sul fondo,
  circa 36,4 in cima, alto 15,2, con le normali piatte (le pieghe nette).
  Ha **due facce**, 0,1 mm fra l'una e l'altra, coi triangoli al contrario:
  i visori che scartano il retro lo mostravano bucato da dentro. La
  grafica e' il disco della carta stesa: il raggio di carta dal centro del
  fondo, 2% in piu' del piu' lungo (circa 28,3 mm), e' il bordo del
  quadrato della grafica.
- **Il bollino**: l'ovale di 9,5 x 7,7 mm (`LA`, `LB`) 0,14 mm sopra la
  cupola, la grafica sul riquadro dell'ovale. Alta col bollino 31,1 mm.

**La texture e' una sola**, un atlante (`atlante`): il pirottino a sinistra
(2048 px), il bollino a destra in cima (1024 px utili, con 16 px bianchi
attorno). Cosi' in Glam il modello ha la texture e il **template**, che il
modello fatto a mano non aveva (ne aveva due: «Si per l'atlante», il
proprietario, 21 novembre 2026). La stagnola non prende la texture: e'
colore pieno, e la sua mappa delle normali e' una seconda immagine,
ripetuta (`scrivi_glb`, un GLB coi suoi tre materiali: lo scrittore comune
ne fa uno solo). A vista il modello e' quello approvato: le viste di
`lavori/strumenti` differiscono solo nei pixel del bollino ricampionato.

**Le misure** sono quelle del modello approvato, prese dalle foto del pack
(la sagoma confrontata riga per riga con la foto di lato), come la sagoma
dell'uovo: i file danno solo la grafica.

### Cosa manca alla pralina

- Le misure sono fisse: una pralina di un'altra misura, o un bollino di
  un'altra forma, viene come la prima. La misura dal DT di un PDF vero (il
  cerchio del pirottino, l'ovale del bollino) non si legge ancora: finora
  sono arrivate solo immagini. L'immagine del prodotto non entra nella
  misura.
- La stagnola e' solo dorata: altri colori (argento, rosso) si
  dichiarerebbero col pezzo senza grafica.
- Un bollino tondo e il pirottino sono due dischi: non si distinguono, e
  il caso va in coda.
- Gli altri avvolti in tre pezzi con un pezzo senza grafica (una caramella
  col sigillo, per esempio) si costruiscono come la pralina, o si fermano
  se le grafiche non sono un ovale e un disco.
