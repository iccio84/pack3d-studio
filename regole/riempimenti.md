# Regole: Riempimenti

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## I riempimenti

Un vassoio espositore pieno dei suoi flowpack. Due PDF, il vassoio e il
flowpack, e un GLB solo (`pack3d/riempimento.py`).

### Si dichiara, e i PDF si riconoscono da soli

Il riempimento non si indovina: lo dichiara chi carica, scegliendo
*Riempimenti*. La pagina ha due posti, il **pack (CU)** e il **vassoio o
display**, e finche' non ci sono tutti e due non si procede. Quale dei due e'
il vassoio lo verifica comunque la lettura: si prova il vassoio su tutti e due
(`analisi_riempimento`), e deve passare **uno solo**. Se passano tutti e due,
o nessuno, ci si ferma e lo si dice. L'altro si legge come flowpack, con le
domande di sempre: zigrinatura, gonfiore, pinne.

### Quanti: la domanda, e il vuoto vuol dire pieno

Prima di costruire la pagina chiede **quanti flowpack mettere**. Vuoto vuol
dire pieno: quanti ne stanno, frontali. Il numero va da 1 a 2000.
Se se ne chiedono piu' di quanti ne stanno, si mettono quelli che ci stanno e
lo si dice in cima agli avvisi: il modello esce lo stesso. Se non ne sta
neanche uno, ci si ferma con le misure del vano e del pezzo.

### I due modelli, ognuno dalla sua famiglia

Il vassoio si costruisce come vassoio, il flowpack come flowpack, con tutte le
loro regole. Il riempimento non tocca nessuna delle due costruzioni, e i loro
avvisi arrivano nei dettagli tecnici, uno dopo l'altro.

### Il vano

Il vano e' l'ingombro del vassoio meno lo spessore del cartoncino (1 mm) su
ogni lato e sul fondo. Si impila fino alla **parete piu' alta**: su un display
il fronte e' basso perche' il prodotto si deve vedere, e la pila la reggono i
fianchi. Sul display T1x40 il vano e' 145,5 x 383,4 mm, alto 98,6.

**Il display si misura senza la plancia.** Il display esce come due nodi, la
scatola e la plancia, sugli stessi vertici: si distinguono solo dai
triangoli. Il vano si misura sui vertici che i triangoli della scatola usano
davvero, plancia esclusa; con la plancia il vano arrivava in cima al cartello,
244 mm sul biscotto T3 invece di 104. Il biscotto T3 nel suo
display: 2 file da 13; il wafer T1 nel suo: 4 file da 10.

### Il flowpack si misura sulla sua maglia

- L'**asse lungo** e' il lato piu' lungo dell'ingombro.
- La **sezione a meta'** da' la larghezza e lo spessore del corpo pieno,
  rigonfiamento compreso. Lo spessore e' il piu' piccolo dei due.
- Il **corpo** finisce dove lo spessore scende sotto meta' di quello a meta';
  oltre ci sono le pinne.

Sul T1 della barretta fresca: 152,5 x 47,4 x 17,0 mm, corpo 127.

### Le CU: flowpack o astucci

Nei riempimenti la pagina chiede che cosa e' il pack (CU): **flowpack** o
**astuccio**, un cartotecnico di un pezzo solo (`cu` nell'intestazione,
`flowpack` di serie). L'astuccio si costruisce come astuccio, chiuso, con lo
spessore della carta che si sceglie nello stesso passo; se ha l'apertura a
strappo, la pagina chiede se se ne vuole la fustella modellata (`incisioni`).
Aperto no: in un espositore il pack e' chiuso.

L'astuccio e' **rigido**, e si tratta da rigido (`componi(rigido=True)`):

- si misura sul suo **ingombro**. La sezione a meta' qui non dice niente: le
  facce sono quadrilateri grandi, e a meta' non ci sono vertici - sul T10 la
  sezione dava 7,5 x 0,2 mm;
- **non si schiaccia**: il 2% vale per un film gonfio;
- non ha pinne da stringere ne' da piegare: la sua maglia si richiama com'e',
  e il GLB non ne copia i vertici.

Il T10 al lampone nel suo vassoio T10x7: 7 astucci frontali in fila dal
davanti al fondo, 187,4 mm di traverso nei 190 del vano.

### Piu' alto delle pareti: sta in piedi e sporge

Gli strati si contano fino alla parete piu' alta, ma **almeno uno ce n'e'
sempre**: un pack piu' alto delle pareti sta in piedi lo stesso e sporge dal
vassoio, che gli tiene il piede. Il T10 e' alto 146,5 mm e le pareti del suo
vassoio 40,5: e' il display vero, e il cartellino lo dice. Prima lo strato
non c'era, e il pack frontale non entrava mai in un vassoio basso.

### I pack sono frontali

**Nel vassoio i pack stanno frontali**: la faccia stampata verso il davanti
del vassoio, il marchio dritto, come li vede chi passa davanti allo scaffale.
Il davanti del vassoio e' quello del suo modello, il lato corto con la parete
bassa (+Z); il pack sta come sta nel suo modello, anche lui col fronte su +Z e
il marchio dritto. La posa frontale e' quindi il pack **senza rotazioni**:

- il T1 della barretta fresca e' una barretta coricata sul fianco, l'asse lungo di
  traverso nel vassoio;
- il T1 al cioccolato fresco sta in piedi.

I pezzi vanno **in file dal davanti al fondo**, uno dietro l'altro, e a strati.
Sul display T1x40: le pareti lunghe sono alte 98,6 mm, due barrette da
47,4 una sull'altra; in profondita' 383 mm, 20 barrette. **2 file da 20.**

La prima versione li metteva sdraiati con la faccia in su, 8 di traverso per 5
strati: anche loro 40, ma da davanti si vedeva solo il bordo del film, e il
vassoio vero non si riempie cosi'. Sdraiati si va solo se frontali non ci
stanno in pianta - il pack piu' largo del vassoio, o piu' profondo - e lo si
dice: piu' alto delle pareti non basta, sta in piedi e sporge. Di taglio, con
la faccia verso i fianchi, mai. Un'eccezione: i pezzi contati che frontali non fanno
strati uguali e sdraiati fanno una griglia piena (*Il display e' fatto per il
suo numero*).

### Quanti ne stanno

Lungo ogni asse del vano si conta quanti pezzi ci stanno:

- **lungo l'asse lungo del pack** conta la lunghezza intera, pinne comprese.
  Due pezzi vicini non infilano le pinne uno nell'altro; si piegano solo
  quelle contro le pareti, e la fila ne recupera la lunghezza. Basta che ci
  stia il corpo;
- **lungo gli altri due**, un pezzo gonfio si schiaccia del 2% fra i vicini
  (`COMPRIME`).

**Il display fatto per N pezzi li tiene tutti** (`riempimento.schiaccia`).
Nata col rigonfiamento nello spessore, che faceva il flowpack piu' spesso e
il vassoio da 40 ne teneva 38, il display da 26 ne teneva 20; tolto quel
rigonfiamento, quei due ci stanno di nuovo senza schiacciarsi, e la regola
resta per il vassoio da 36 del caso 838cbae0ac. Il display e' fatto
per il suo numero, e i flowpack pieni d'aria ci stanno stretti: se i pezzi
chiesti non ci stanno, il flowpack si schiaccia nello spessore a passi di
mezzo per cento finche' ci stanno, nella stessa posa che aveva (frontali
restano frontali: al primo passo il vassoio da 40 trovava sdraiati una
griglia 8 x 5), al massimo del 25% (`SCHIACCIA_MAX`). Oltre, il pezzo e'
davvero troppo grande e se ne mettono meno, come prima. Sul vassoio da 36: il
T1 da 22,2 a 20,7 mm (94%), 3 per fila in 12 file. Un astuccio non si
schiaccia; i riempimenti senza un numero chiesto non cambiano.

**Se lo spessore non basta, di lato** (`riempimento.stringe`). Affiancati, i
flowpack si schiacciano anche di lato fra i vicini. Il display a scatola da 15
del caso c5b98dfbee, al rigonfiamento 10 chiesto dal proprietario: il
flowpack e' largo 38,7 a meta' corpo, e sdraiati nei 189 mm del vano ne
stavano 4 per strato invece di 5 (il posto e' fino a 38,5, col 2% di
`COMPRIME`); restavano 8 in piedi, e schiacciarli nello spessore non li
stringeva. Ora, se lo spessore non basta, la larghezza cala a passi di mezzo
per cento, a UV ferme, al massimo del 3% (`STRINGE_MAX`): stretta del 7% la
grafica si vedeva schiacciata (caso 838cbae0ac). Vince la prima disposizione
che li tiene tutti, in qualunque posa, perche' quella del pezzo largo non li
teneva. Sul caso: 38,7 -> 38,5 mm (99,5%), 5 x 3 per il lungo in 3 strati.
Gli altri riempimenti del parco non cambiano.

### Strati uguali, file su tutta la profondita'

- **Frontali, gli strati sono uguali**: 40 pezzi in strati da 22 al massimo
  fanno 20 e 20, non 22 e 18. Se avanzano, quello in piu' va sotto (41: 21 e
  20).
- **Ogni fila si allarga su tutta la profondita'**, dal davanti: 20 barrette
  in 383 mm stanno a 19,2 mm l'una dall'altra, poco piu' dello spessore, come
  nel vassoio vero. Fra due pezzi pero' al massimo un quinto di spessore
  d'aria (`PASSO_MAX`): con pochi pezzi stanno appoggiati al davanti, e il
  fondo resta vuoto.
- Se l'ultima fila non e' piena, i pezzi vanno nei posti piu' vicini al
  centro.
- Sdraiati, gli strati si riempiono pieni dal fondo, e l'ultimo mette i pezzi
  al centro.

### Il flowpack si adatta al vano, una volta per tutti

- **Le pinne si stringono** quanto il passo fra due pezzi lungo la loro
  larghezza, sfumando dal corpo alla punta. Il film e' piu' largo del corpo:
  due pinne vicine sullo stesso piano si compenetravano, e nel viewer
  sfarfallavano. Frontali, il passo e' fra i due strati; sdraiati, fra due
  file.
- **Le punte che uscirebbero dal posto del pezzo si piegano** di 80 gradi a
  0,6 mm dalla parete, come fa il film vero. Si piegano sullo spessore, intorno
  alla larghezza della pinna: frontali verso il dietro, cosi' il davanti resta
  pulito; sdraiati in su, contro la parete.
- **Il pezzo poggia col corpo.** L'altezza da terra si misura sul pack gia'
  adattato: con le pinne larghe la barretta frontale stava 5 mm sopra il
  fondo.

Il corpo non si tocca: e' quello che si vede. Con una sola eccezione, qui
sotto.

### Se non ci sta in nessuna posa, il flowpack si accorcia

Il caso e1b3cc77a7: un flowpack con 119 mm di corpo (150 di passo) in un
display da 81 x 111 x 26 mm, vano 79 x 109 x 25,5. Nessun lato del vano
tiene il corpo, e il riempimento si fermava con «non ci sta in nessuna
posa». Chi l'ha caricato ha confermato le misure del display e ha chiesto
di schiacciare il flowpack finche' non entra.

La regola (`riempimento.accorcia`): se nessuna posa tiene il corpo, il
flowpack si **accorcia lungo il suo asse lungo**, pinne e corpo insieme,
fino al lato del vano su cui va, meno quattro volte il gioco (2,4 mm): le
punte delle pinne si piegano contro la parete a 0,6 mm da lei, e col corpo
lungo quanto il lato non c'era dove piegarle, e uscivano dalle pareti. Le
pose si provano nell'ordine di sempre - frontali, poi sdraiati per il largo e
per il lungo - e vince la prima in cui il pezzo accorciato ci sta: si
espone come gli altri riempimenti, anche se costa accorciarlo di piu'. Sul
caso: frontali, corpo da 119 a 77 mm (64 per cento), 8 pezzi in fila dal
davanti al fondo, alti 33 mm su pareti da 25,5 (sporgono, come sopra). Le
altre due misure non cambiano. Un astuccio non si accorcia mai.

Il riempimento lo dice nella prima riga, con le misure: e' una scelta di
chi l'ha chiesto, non la misura del pack. Sul parco cambiano solo i casi
che prima si fermavano: dove una posa c'e', la strada e' quella di prima.

### Il GLB: il flowpack una volta, un nodo per pezzo

Il GLB e' il vassoio com'e', con dentro il flowpack **una volta sola** come
maglia e un nodo per pezzo, ognuno con la sua rotazione e traslazione. La
texture del flowpack c'e' una volta: con 40 pezzi il riempimento T1x40 pesa 9,8 MB. Le
texture del vassoio e del pack vanno poi in un'immagine sola, l'atlante, una
zona per pezzo (*La texture e' lo steso*): Glam e il template ne vogliono una.

**Il viewer della pagina deve seguire i nodi.** Il suo lettore GLB metteva in
scena ogni mesh una volta, e dei nodi non sapeva niente: di un riempimento
mostrava solo il vassoio. Ora percorre i nodi della scena, con le loro
trasformazioni e i figli. I modelli di un pezzo solo e la coppa si vedono
uguali al pixel.

Il flowpack si misura nella scena e si adatta nella sua maglia: le due cose
coincidono solo se i suoi nodi non spostano niente, ed e' cosi' che li fa
`build_flowpack`. Un flowpack coi nodi trasformati ferma il riempimento.

### Il controllo dell'AI non c'e' ancora

Il controllo confronta il modello con l'artwork di un pack solo: sul vassoio
pieno non saprebbe cosa guardare. Il riempimento lo salta, e lo dice nel
riquadro del controllo.

### Cosa manca

- Il pack frontale ruotato: oggi frontale vuol dire come sta nel suo modello.
  Un pack lungo che nel suo modello e' coricato non si prova in piedi.
- Le CU che non sono flowpack ne' astucci: pouch, coppe, scatole in piu' pezzi.
- L'astuccio aperto dentro l'espositore.
- Il vassoio coi separatori: oggi il vano e' uno solo.

### Il display e' fatto per il suo numero: la griglia piena

Il caso c5b98dfbee, display a scatola T15 (191 x 139,5 x 71,5; vano 189 x
137,5, alto 70,5) con flowpack 150 x 35 x 14,6 (pinne comprese; corpo 117).
Chi l'ha caricato: «in totale ci devono essere 15 CU (5X3 Flowpack)». Frontali
ne stavano 20, due strati da 10, e i 15 chiesti venivano 8 e 7: dall'alto se
ne vedevano 8, e le file sfalsate dei due strati facevano i gradini.

**Regola** (`riempimento._griglia`). Un display e' fatto per il numero che
porta. Se si chiedono N pezzi e frontali vengono a strati diversi, si cerca
una posa sdraiata che li metta in una **griglia piena**: a per strato, s
strati, a x s = N, con a che sta in pianta (gx non piu' di quanti ne stanno
di traverso, gz non piu' di quanti in profondita') e s non piu' degli strati
che stanno in altezza; vince quella con meno strati. I pezzi di uno strato si
allargano su tutto il vano (passo = lato / gx). Sul T15: sdraiati per il
lungo del vano, 5 di traverso (passo 37,8) e 3 strati: 5 x 3, e da davanti si
contano le 15 testate. Il 3 x 5 (sdraiati per il largo, 3 file di 5 strati)
perde: piu' strati, e da davanti si vede la prima pila sola. Frontali a
strati uguali non cambiano: un display da 40 resta 2 file da 20, uno da 26
2 file da 13.

Al livello 9, scelto da chi l'ha caricato con la foto del pack vero, il
flowpack e' 34,8 x 13,9 (36,6 x 15,1 a meta' corpo): 5 strati non entrano
nei 70,5 mm del vano e la griglia e' una sola, 5 x 3 per il lungo in 3
strati. Una regola che preferiva il 3 x 5 perche' il pezzo ci stava intero
e' stata provata e tolta; anche il rigonfiamento nello spessore (30 x 19,7)
e' stato provato e tolto (*Il rigonfiamento resta nel rapporto del DT*).
Poi il proprietario ha chiesto il livello 10: 36,5 x 14,6 (38,7 x 15,9 a
meta' corpo), stretto di lato a 38,5 perche' ne stiano 5 per strato (*Se lo
spessore non basta, di lato*). Ma cosi' i pezzi stavano troppo bassi, e alla
fine il pack ha il rigonfiamento nello spessore, al livello 9 (*Nello
spessore, se lo si sceglie per il pack*): 3 strati da 21,3 mm, 64 dei 70,5.

### Sdraiati, stanno in piano

Il T15 al primo «Non approvo» chiedeva i pezzi «leggermente inclinati
all'indietro», e la pila si inclinava sul bordo dietro del fondo di quanto
lasciava l'aria sopra (10 gradi). Al secondo: «Annullare l'inclinazione».
Sdraiati, i pezzi stanno **in piano** sul fondo, come nel DT del display;
l'inclinazione non c'e' piu' (ne' `riempimento.inclina` ne' il perno sul
bordo dietro). Frontali stanno dritti, come sempre.

Dopo, coi pezzi spessi 21,3 mm, la rotazione di 10 gradi e' stata chiesta di
nuovo e provata nei due versi. Ruotata, la pila prende in altezza la
lunghezza per il seno: 113 x sin 10 = 19,6 mm in piu', 82 mm contro i 70,5 del
vano, e i pezzi passavano nel coperchio e nella cornice della finestra. Chi
l'ha caricato ha risposto di non inclinare: inclinato, il flowpack si
interseca con il display. Se un pezzo ruotato non sta nel vano, non si ruota.

### Nel display il flowpack resta quello del DT, con le pinne aperte

«I flowpack non sono venuti bene. Devono essere piu' gonfi, avere le pinne
aperte e senza gradini.» E dopo: «Il T1 non corrisponde al DT. La grafica
viene strecciata.»

- **Il livello 9**: con la foto del pack vero, «e' piu' gonfio, come
  l'immagine», il livello e' passato a 9: 34,8 x 13,9 nel rapporto del DT.
  Il rigonfiamento nello spessore, che lo faceva 30 x 19,7, e' stato tolto
  (*Il rigonfiamento resta nel rapporto del DT*). Quello che segue e' la
  storia di prima.
- **Al rigonfiamento scelto, non di piu'**: per il primo «Non approvo» il
  flowpack nel display si costruiva 3 livelli piu' gonfio (5 -> 8). Ma il
  rigonfiamento tiene il perimetro e arrotonda la sezione, che si allarga:
  sul T15 33,7 x 13,5 invece dei 30 x 12 del DT (32,2 x 12,9 al livello 5),
  e la grafica del fronte, misurata in mm per unita' di texture a meta' del
  corpo, si stira dell'8,5% rispetto al pezzo quasi squadrato (livello 1),
  contro il 2% del livello 5. Il T1 non tornava piu' col suo DT. Nel display
  il flowpack si costruisce **al livello scelto, come da solo**: il gonfio in
  piu' (`GONFIO_DISPLAY`, `componi(esatti=True)`) non c'e' piu'. Chi lo vuole
  piu' gonfio sceglie il livello. Tenere la taglia del DT a forma piu' tonda
  (scala 1) non serve: la faccia a meta' corpo si stira di piu', non di meno.
- **Pinne aperte, senza gradini**: sdraiati, le punte che uscivano dal posto
  del pezzo si piegavano di 80 gradi in su e stavano davanti alla faccia come
  un gradino, la pinna chiusa. Ora il film si **accartoccia in lunghezza**: la
  pinna oltre il corpo si accorcia quanto basta (per (meta - corpo/2) /
  (lungo/2 - corpo/2)) e resta distesa e aperta, con la sua zigrinatura.
  Frontali le punte si piegano verso il dietro come prima.

### Nel riempimento il CU resta il suo modello: si schiaccia, non si allarga

Il caso 838cbae0ac, un display sagomato col fondo di 150,4 x 247,0 mm e 36
flowpack T1, 3 per fila in 12 file. Il T1 al rigonfiamento 5 e' 40,1 x 22,2
mm (47,1 sulle pinne all'apertura 2): nel vano ne stanno 3 per fila, e 12
file da 22,2 fanno 266 mm contro 245. (Col rigonfiamento nello spessore,
poi tolto, era 37,1 x 25,4 e ne stavano 4 per fila.)

La routine ci ha provato tre volte, e tre volte ha cambiato il T1:
- 4 file da 9, il T1 come da solo: «il vassoio contiene 3 pack per 12
  file»;
- premuto fra i vicini a cuscino, un'ellisse 49,6 x 20,2 a giro fermo
  (`pressa`): la grafica stretta al centro, i fianchi bianchi sul fronte;
- lo stesso cuscino col T1 scalato nel largo: marchio e barretta stirati
  del 34%. Poi, ripreso a mano, le UV spostate per rimettere il fronte a
  misura vera.

Chi l'ha caricato: «quando si costruisce un vassoio con riempimento i CU
(flowpack, cartotecnici, incarti) non devono mai essere modificati»; nel
T1 premuto vedeva «protuberanze e grafiche stirate». E poi: «essendo dei
flowpack si possono schiacciare, ma senza modificare la mappatura».

**Regola.**
- Il CU e' il modello che si costruisce da solo con le sue scelte -
  zigrinatura, rigonfiamento, apertura delle pinne, che si chiedono come per
  un flowpack - e nel vassoio si posa. Non si allarga, non si scala nel
  largo, le sue UV non si toccano. `pressa`, il cuscino e il fronte
  rimappato non ci sono piu'.
- Un flowpack si puo' **schiacciare** fra i vicini come il film vero, a UV
  ferme: nello spessore (`schiaccia`, al massimo del 25%), le pinne strette
  al passo, le punte piegate contro una parete. Sul caso: 22,2 -> 20,7 mm
  (94%), 3 per fila in 12 file. Il fronte e' quello del T1 da solo.
- **Quanti per fila** li dice chi l'ha caricato (`per_fila`, opzione del
  caso; `riempimento._per_fila`): il pack non si allarga per riempire il
  posto, le file si allargano sul vano e fra un pack e l'altro resta l'aria.
  Senza, quanti ce ne stanno.
- Piu' alto delle pareti, sopra non c'e' niente contro cui piegare le
  punte: il posto in altezza e' il pezzo intero e le pinne restano com'erano
  (i T1 in piedi piegavano 0,6 mm di punta per niente).
- **Le aree riservate del T1**: l'area dell'EAN e quella del lotto, due
  riquadri pieni di PANTONE 3405 C e 346 C senza didascalia leggibile (la
  scritta EAN e' in curve), si vedevano verdi sui fianchi. Guardate lastra
  per lastra - ognuna dipinge solo il suo riquadro - e confermate a occhio
  da chi l'ha caricato («bianco, come l'etichetta»), stanno nelle opzioni del
  caso nel parco (`params.parametri_costruzione.aree_riservate`, come fa
  l'agente). Per numero di Pantone non si tolgono mai (*Le aree riservate
  che il file scrive, ma non nomina*): una regola sulla forma - una tinta
  che dipinge solo uno o due rettangoli pieni - provata sui 44 PDF del parco
  prendeva anche grafica vera.

Gli altri riempimenti e i vassoi del parco restano identici al byte a quelli
pubblicati.
