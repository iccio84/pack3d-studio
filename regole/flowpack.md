# Regole: Flowpack

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

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
*background color*. Sul T1 della merendina la catena e' 8 | 10 | 113 | 10 | 8: le
fasce da 10 sono zona grinze, le pinne sono quelle da 8.

**Il DT che marca un pannello ha la precedenza.** Se il disegno segna
esplicitamente una fascia — due linee con una quota e l'indicazione
*TEXT ORIENTATION* — quella e' l'informazione autorevole: va cercata **prima**
di dedurre le fasce dalle cordonature, e la grafica va centrata in quella zona.
Sul croccante T2 la fascia marcata da 50 mm ha fatto uscire fianchi uguali
(11,01 e 11,01) e cucitura centrata sul retro, dove la mia deduzione dava 46,4
con fianchi diversi.

**L'artwork e' il blocco piu' vario, non il piu' grande.** Una tavola porta
spesso le lastre di separazione a fianco della vista stampata, e una campitura
piatta di tinta e' colorata al 99% pur essendo una lastra: sul T1 ai cereali le
tre lastre (Aluminium, Transparent Support, White Plate) sono piu' larghe della
OUTSIDE VIEW e la scaletta per ingombro metteva davanti quella del bianco.
Il discrimine e' quanti colori distinti porta il blocco: 149 sull'artwork vero
contro 14-26 sulle lastre e sui cartigli. `find_blocks` riporta
`colori_distinti` e ordina per quello.

**Niente soglie assolute sulla lunghezza delle linee — ma la frazione puo'
solo abbassarle, mai alzarle.** Fra il nastro del wafer T1 (83 mm) e quello della
brioche (420 mm) c'e' un fattore cinque: una cordonatura che attraversa tutto il
nastro del wafer T1 e' lunga 83 mm, sotto gli 88,2 mm che `analyze_auto`
pretendeva, e nessun pack piccolo poteva passare il cancello.

Sostituire le costanti con una frazione pero' le **alza** sugli steso piu'
lunghi del riferimento, ed e' un modo nuovo di rompere le cose vecchie: sul
T1 della barretta fresca, passo 152,5 mm, la soglia saliva da 88,2 a 91,5 e si perdeva
la cordonatura a 108,5 mm, il cui gruppo sta giusto in mezzo. Senza quella
piega `solve_bands` non chiude, la costruzione ripiega sul solutore vecchio e
la grafica scivola. Le costanti restano la taratura buona sugli impaginati gia'
coperti: si prende il **minimo** fra costante e frazione.

**Una linea disegnata a pezzi e' una linea sola.** La soglia si applica ai
tratti uno per uno, e un file puo' disegnare una linea in piu' pezzi di fila.
Sul **T1 cheesecake** il taglio in fondo allo steso e' nove
segmenti consecutivi - il piu' lungo 96 punti contro una soglia di 135 - mentre
sul T1 al mandarino, stesso identico disegno, e' uno solo da 340. Scartati i
pezzi, lo steso si fermava sulla saldatura: passo **141 invece di 149**, corpo
125 invece di 133, e la verifica delle UV che gridava "rientri diversi (8 e 10
mm)". Prima della soglia, i tratti della stessa penna sullo stesso asse che si
toccano si ricuciono (`flowpack._ricuci`): mezzo punto di vuoto al massimo.
Col taglio ricucito il T1 cheesecake esce identico al T1 al mandarino, 136 x 149, corpo
133, pinne 8 e gola 10 (135,5 prima che i capi dello steso si prendessero sul
taglio: vedi *I capi dello steso sono il taglio, non il centro del gruppo*).

**Un tratteggio e' una linea, comunque sia disegnato.** Una piega tratteggiata
si disegna in due modi che a vederli sono identici: un tracciato solo con il
motivo del tratteggio, che il PDF tratteggia quando stampa, o un tracciato per
ogni trattino. Il primo il solutore lo legge come una linea; il secondo erano
trattini da pochi millimetri, tutti sotto la soglia, e la piega spariva. Sul
**gelato su stecco** (file 1688..., il primo caso arrivato dalla
coda) le quattro pieghe del prodotto sono 23 trattini da 6 mm ciascuna, con
vuoti da 1,5: sparite tutte e quattro, nessuna chiusura a pinna tornava, e
l'unica lettura rimasta era il tubo piatto **girato di 90 gradi** - le fasce
della pinna lunga prese per le saldature di testa, il gelato di traverso, il
logo capovolto sul retro. Il controllo dell'AI l'ha respinto e il caso e'
finito in coda.

Adesso un **motivo regolare** di almeno quattro trattini sulla stessa retta,
della stessa penna, con i vuoti tutti uguali e i trattini tutti uguali (il
primo e l'ultimo possono essere piu' corti, il motivo si ferma dove finisce la
linea) diventa una linea sola, da capo a capo (`flowpack._tratteggi`). Pezzi
diversi che per caso stanno sulla stessa retta un motivo non ce l'hanno, e
restano pezzi. Con le pieghe il gelato su stecco chiude a pinna nel verso giusto, e
torna al millimetro: nastro 165 = 17,5 | 20 | 25 | 40 | 25 | 20 | 17,5,
fronte 40 x 25, passo 170 con saldature da 13, corpo 144. Sugli altri
diciassette file del confronto (parco e caricati) l'analisi esce identica: i
loro tratteggi, se ci sono, sono disegnati col motivo del tratto.

**Un ripiego non deve mai essere muto.** Se `analyze_auto` fallisce, la
costruzione passa al solutore vecchio: il modello che ne esce non e' sbagliato
in modo evidente, e' **plausibile**, che e' peggio. Sul T1 della barretta fresca la
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
sul MediaBox, pdfium rende il CropBox. Quando i due riquadri non coincidono — sul
wafer T1 il CropBox e' 459 x 271 pt dentro un MediaBox di 1332 x 958, spostato di
(419, 471) — le coordinate dei segmenti indicizzano un'immagine che comincia da
un'altra parte: nessuna eccezione, solo misure prese nel posto sbagliato, e
intere viste tecniche che restano fuori dalla resa. Si rasterizza sempre con
`dieline.render_page`, mai con `pdfium.PdfDocument(...).render()` diretto.

Vale anche in **lettura**, e li' e' meno evidente: `page.get_size()` di pdfium
da' la CropBox, mentre le coordinate dei tracciati sono nello spazio del PDF.
Chi ribalta la y su quell'altezza ottiene una pagina intera fuori posto — sul
wafer T1 le due maschere, vecchia e nuova, non avevano un pixel in comune. Il
telaio si prende sempre dalla MediaBox (`tracciati._telaio`).

**I pannelli della fustella non sono la sezione del pack chiuso.** Le
cordonature dicono dove il film e' cordonato, non che forma prende una volta
riempito. Sul croccante T2 i pannelli danno 50 x 11, ma il pack in mano e'
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
  Sulla brioche T10 lo svaso passa da +25% a zero. E' il caso raro in cui
  la regola dello svaso a meta' perimetro non vale.
- **La sezione la detta la scatola.** Il riscalo a perimetro costante dice che
  una forma piu' tonda, a parita' di film, e' piu' grande: vale quando dentro
  c'e' aria. Con la scatola i pochi millimetri che la superellisse taglia agli
  spigoli se li prende la piega, non il pack. Senza questa eccezione la brioche
  usciva 155,9 x 59,7 invece dei 148,9 x 57,0 della fustella.

Dal PDF non si vede: e' il prodotto a dirlo. Va riportato in
`parametri_costruzione.avvolge_scatola`, e nell'interfaccia c'e' la casella
"Il film avvolge una scatola". Un pack cosi' e' rigonfiamento 1.

- **La pinna e' corta, e la gola sta oltre la scatola.** Quello che la
  fustella misura oltre il corpo non e' tutto pinna: prima il tubo deve
  collassare, e la gola piegata sullo spigolo costa mezzo spessore. Sulla
  brioche i 37,6 mm oltre il corpo sono 22,8 di gola piu' 14,8 di pinna. Il
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
  (brioche). Quando il DT disegna la saldatura E dove finisce il prodotto, la
  testata e' gia' divisa: pinna fino alla saldatura, gola fino al prodotto, e
  il corpo la comprende. Sul **wafer da colazione T10** le quote del file sono
  `20 | 37,5 | 215 | 37,5 | 20`, e il ramo della scatola divideva lo stesso
  la pinna da 20 mm: 18 di gola in piu' e **2 mm di pinna**. Il pack usciva
  una scatola senza pinne, con la grafica delle testate stirata di 2,07 volte,
  e nessun errore. Era cosi' dal 27 settembre, da quando le testate si
  leggono dal DT (vedi *Prima le misure, poi il contenuto*), e nessun
  controllo lo prendeva: la verifica delle UV con la scatola cercava la
  piega, e sul wafer da colazione la prima linea e' la saldatura. Adesso: gola dal DT,
  pinna 20, verifica UV a 0,0 mm, film stirato 1,38 invece di 2,07. I due
  brioche restano identici al byte.

Resta fuori dal modello il fatto che su questi pack la pinna, oltre a non
allargarsi, viene **ripiegata sulla testata** invece di sporgere: nelle foto
della brioche si vede piegata, nel modello sporge dritta. Piegarla e' geometria
nuova, non un parametro.

**Il rigonfiamento cambia la forma, non la taglia.** Il perimetro e' fissato dal
foglio stampato: a parita' di steso un pack piu' morbido non e' piu' grande, e'
piu' tondo. La sezione e' una superellisse `|y/a|^n + |z/b|^n = 1` con n che
scende da 10 (rettangolo, livello 1) a 2 (ellisse, livello 10), e il perimetro
torna quello del film. Gonfiare aumentando le dimensioni e' il modo sbagliato:
fa crescere il perimetro e la grafica non torna piu'.

**Il rigonfiamento resta nel rapporto del DT: provato nello spessore, e
tolto.** Il 26 ottobre il rigonfiamento a pinna ha tenuto la larghezza della
faccia del DT (`a = W/2`) e mandato nello spessore il film che gli spigoli
tondi lasciano, con la grafica sul giro dalla distanza dal centro del fronte
invece che per pannello: il flowpack del display T15, «piu' gonfio come
l'immagine», veniva 30 x 19,7 al livello 9. E' uscito col rilascio del 26
ottobre e lo stesso giorno e' stato tolto: sul T1 del vassoio da 36 la
faccia passava da 40,1 a 37,1 mm e la grafica del fronte da +6% a +2%
sull'artwork, e chi l'ha caricato, accanto al T1 approvato, vedeva una
lettera del marchio schiacciata.
Il T1 approvato e' la misura: si torna al rapporto larghezza/spessore del DT
e alla mappatura per pannello, e i flowpack del parco tornano identici al
byte a quelli approvati prima del rilascio. Chi vuole un pack piu' spesso
sceglie il livello, e la faccia si allarga con lui.

**Nello spessore, se lo si sceglie per il pack** (`"gonfio": "spessore"`
fra le opzioni del caso; `Flowpack.nello_spessore`). Il display a scatola da
15 del caso c5b98dfbee e' fatto per 3 strati del pack vero: 70,5 mm di vano.
Nel rapporto del DT il flowpack 30 x 12 al livello 10 e' spesso 15,9 a
meta' corpo, i 3 strati arrivano a 47,7 mm, e lo strato di sopra resta sotto
il taglio del fronte (49 mm al centro): da davanti i pezzi quasi non si
vedono, «sono troppo bassi». Nello spessore al livello 9 e' 30 x 19,7 (21,3
a meta' corpo): 3 strati da 64 mm, sopra il taglio come nel display vero.
Al livello 10 sarebbe 25,1 a meta' corpo, e 3 strati non ci stanno. Cosi'
il rigonfiamento nello spessore torna, ma solo per il pack che lo sceglie:
la regola di prima, con la faccia ferma, la cucitura al centro del fronte e
gli spigoli solo per la verifica, identica al byte (il display al livello 9
e' `43cfbbfe`, quello approvato il 26 ottobre). Senza la scelta niente
cambia: il T1 del vassoio da 36 resta largo 40,1.

**Mappare per pannello, non per arco uniforme.** Gli spigoli della sezione si
trovano dalla curvatura e si usano come nodi di interpolazione: ogni fascia
dello steso finisce sul suo pannello, indipendentemente da come i raccordi
ridistribuiscono il film. Con la mappatura per arco ogni fascia scivola — sul
croccante T2 lo scarto era 18,51 mm, il 12,7% del giro.

**Attenzione ai filtri troppo aggressivi sui dati in ingresso.** Una cordonatura
puo' sfuggire perche' il suo segmento sta sotto la soglia di peso, e allora
nessun solutore a valle puo' trovare la soluzione giusta: sul croccante T2 la
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
e la grafica girava di altrettanto — 4,2 mm sul T1 ai cereali, 12,9 sul
T1 farcito, 25,7 sulla brioche. Il difetto stava nel codice da prima ma era
dormiente: la costruzione passava per `soft_section_fit`, che parte esplicito
da `(W/2 - back_a, -T/2)`. E' stato il passaggio alla superellisse ad
accenderlo, e nessuno se n'e' accorto perche' la misura fascia per fascia non
esisteva. Su un tubo piatto lo spigolo non esiste e il punto giusto e' la
piega: vedi *La cucitura si ancora alla PIEGA, non allo spigolo*.

**La cucitura non e' sempre centrata sul retro** (T1 della merendina: 16 + 18), e
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
   tutti e due i versi: su artwork **al vivo** non c'e' - sul croccante T2
   la grafica copre 923 colonne su 1010, la misura dava `end_fin = 0` e il
   modello usciva con il 21% di triangoli degeneri - e su una grafica col
   bianco vicino alla testata e' troppo lungo - sul wafer da colazione 41,2 mm contro i
   20 della saldatura.

Verifica: perimetro + 2 falde deve dare la larghezza del nastro.

| | nastro | fronte | fianco | falda | somma |
|---|---|---|---|---|---|
| T1 della barretta fresca | 144,0 | 43,0 | 15,0 | 14,0 | 144,0 |
| barretta proteica | 141,0 | 36,0 | 19,5 | 15,0 | 141,0 |
| croccante T2 fondente | 415,0 | 150,5 | 41,0 | 16,0 | 415,0 |

Regole di forma, da applicare senza chiedere:

- denti contati sul **bordo della pinna** e non sul perimetro della sezione:
  base = bordo / numero denti, altezza = **2/3 dell'equilatero** (base x
  V3/2 x 2/3), con la punta e la gola **appena smussate**. Il taglio agisce
  solo sul bordo esterno, l'interno resta piano con le nervature delle
  ganasce. Il bordo dentato e' una striscia a parte, oltre la griglia, con
  l'anello della pinna suddiviso finche' ogni dente ha almeno 16 punti: con
  i vertici della griglia un dente di 5 mm ne aveva 6, e la punta cadeva fra
  due, mozzata (`flowpack.PUNTI_PER_DENTE`);
- la pinna e' **saldata**: i due strati del film si toccano (fra le facce
  0,08 mm, `PINNA_SALDATA_MM`, perche' un viewer a doppia faccia non le
  confonda), e le nervature delle ganasce li ondulano **insieme**. Prima
  restava il 3,5% del mezzo spessore e le nervature spingevano i due strati
  in fuori: la pinna usciva aperta, col bordo doppio. Quanto si vedono le
  nervature lo sceglie l'utente, **saldatura da 0 a 3** (`NERVATURA_MM` a 3);
- le nervature sono un'**onda morbida** (passo 1,4 mm) che parte piana dalla
  saldatura, con almeno **sei stazioni per nervatura**: con tre l'onda usciva
  a gradini e il bordo della pinna, visto di taglio, seghettato. Si spengono
  nei **3 mm prima delle pieghe** ai lati della pinna (`BORDO_LISCIO`): accese
  fino alla piega il bordo usciva ondulato come una seconda fila di denti,
  spente in 1,2 mm facevano una tacca a ogni cresta. Il bordo dentato
  comincia su una cresta, dove l'onda e' piana e la cucitura non si vede;
- la **falda** si stacca dal tubo lungo la **normale dell'anello**, non lungo
  il raggio: sulla pinna l'anello e' piatto e il raggio va di lato, la falda
  restava sul film e con le nervature gli passava sopra e sotto a righe. E
  sul **bordo dentato**, che la griglia della falda non raggiunge, le colonne
  sotto la falda prendono la **grafica della falda** (`falda_sui_denti`):
  senza, li' si vedeva la zona coperta del film - sul T1 farcito le tacche
  nere della fotocellula, sul gelato su stecco il bianco al posto del marrone;
- **niente gradino fra pack e pinna**: tutto quello che il corpo ha e la
  pinna no - la pancia, le grinze - si spegne sulla spalla e alla saldatura
  vale zero. Accese fino all'ultimo anello davano sul bordo un gradino di
  qualche decimo di millimetro, diverso in ogni angolo come le grinze (sul
  pane ripieno da 0,26 a 0,43 mm);
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
  (T1 della barretta fresca e della merendina: 10 mm) o "superficie inclinata verso saldatura" e quota a parte
  (wafer da colazione: 37,5). E' li' che il modello si rastrema, o da prima quando il
  calo del tubo vuole piu' film (vedi *La grafica sulle pinne*);
- se la prima struttura e' una **piega con le sue due guide**, la saldatura
  non e' disegnata: e' il film su scatola (brioche), e la testata arriva alla
  piega. Da li' in fuori la gola la decide lo spessore, come prima. Se invece
  il DT disegna saldatura e gola e il film avvolge una scatola (il wafer da
  colazione), la gola resta quella del DT: vedi *Il film su scatola*.

I due lati devono dire la stessa cosa. Se non la dicono, la pinna prende il
rientro piu' stretto - la regola di sempre - la gola non si usa, e la
verifica delle UV lo grida (vedi *Le verifiche*).

Il margine non stampato resta come **ripiego**, dichiarato, solo dove il DT
sulle testate non segna niente.

Sul parco, pinna di testa prima e dopo, in mm:

    |                          | dal margine | dal DT                 | quote della miniatura          |
    | wafer da colazione       | 41,2        | 20 + gola 37,5         | 20 | 37,5 | 215 | 37,5 | 20, testo |
    | T1 farcito               | 3,4         | 15 + gola 10           | 15 | 10 | 105 | 10 | 15, a occhio |
    | brioche STD              | 32,6        | piega a 37,6           | -                              |
    | brioche latte e cacao    | 32,6        | piega a 37,6           | -                              |
    | T1 della barretta fresca | 6,9         | 8,0 + gola 10          | -                              |
    | wafer T1                 | 9,8         | 10,0                   | 10 | 124 | 10, a occhio        |
    | T1 della merendina, T1 al cioccolato fresco, T1 ai cereali: uguali, 8,0 - 6,0 - 7,0 |

Dove le quote ci sono, danno ragione al DT, e al decimo. Il T1 farcito e' il
caso peggiore di prima: la grafica sborda di una decina di millimetri dentro
la saldatura, il margine non stampato era di 3,4 mm, e il pack usciva con un
corpo di 148 mm e le pinne da 3 invece di 125 e 15 - ventitre millimetri di
prodotto in piu'. Sulla brioche la piega a 37,6 e' **esattamente** la misura su
cui la gola e' stata tarata - "37,6 = 22,8 di gola piu' 14,8 di pinna",
scritto sotto in *Il film su scatola* - mentre il margine dava 32,6 e la pinna
usciva 9,8: la taratura era rimasta giusta e la misura sotto era scivolata,
senza che niente lo dicesse.

Le quote del file la costruzione le legge da sola quando sono testo
(`quote.riscontro_testate`): una CATENA di numeri allineati sullo stesso asse
che somma al passo, e **simmetrica**, perche' lungo il passo il pack lo e'. Un
numero solo non conferma niente - un "20" lo scrive anche la tabella
nutrizionale - e con una quarantina di numeri sul foglio una fila che somma al
passo si trova anche per caso: sul wafer da colazione `7 | 135 | 7 | 57 | 7 | 71,5 | 40
| 5` fa 330 ed e' fatta di pezzi del nastro. Una fila simmetrica per caso no.

Se la catena del file non torna con le testate lette dal DT, la costruzione lo
**grida**: vuol dire che il disegno e' stato letto male. Provato rimettendo la
lettura dal margine sul wafer da colazione: `QUOTE DEL FILE DIVERSE DALLE TESTATE LETTE:
il file scrive 20 | 37,5 | 215 | 37,5 | 20 = 330, dal disegno esce 41,2 |
247,6 | 41,2`.

### La grafica sulle pinne: il film non si allunga

Sul T1 farcito e sul T1 della merendina la grafica vicino alle pinne **sterzava**: il bollino
"Fatta con latte fresco", che parte sulla pinna e passa sulla spalla, girava
verso il bordo lungo la gola e sulla pinna arrivava allargato. Succedeva su
ogni pack con scritte o elementi grafici sulle testate, e le cause erano due,
tutte e due nella UVW e nessuna nella texture.

**1. Lungo il giro.** La pinna si otteneva scalando la sezione: stretta in
altezza, allargata in larghezza fino al bordo della pinna. Le fasce del film
seguivano la scala, quindi il fronte si allargava con la pinna - del 46% sul
T1 farcito - e i fianchi si schiacciavano a zero sul bordo. Ma la pinna e' il
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
spessore, e il film deve bastare a coprire la discesa. Sul T1 farcito la gola
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

Il bollino del T1 farcito, triangolo per triangolo:

| | pinna, giro | spalla, passo | anisotropia massima |
|---|---|---|---|
| prima | 1,51 | 2,47 in media, 3,67 di punta | 6,1 |
| dopo | 1,00 | 1,21 in media, 1,22 di punta | 1,3 |

E sul parco, con la misura della terza verifica: pinne e spalle meno i denti,
la stessa zona prima e dopo, fra il 5 e il 95% dei triangoli:

| pack | giro prima | giro dopo | passo prima | passo dopo |
|---|---|---|---|---|
| T1 farcito | 0,05 - 1,55 | 0,82 - 1,07 | 2,97 | 1,23 |
| T1 al mandarino | 0,06 - 1,68 | 0,83 - 1,14 | 2,28 | 1,23 |
| T1 della barretta fresca | 0,07 - 1,32 | 0,84 - 1,06 | 1,87 | 1,22 |
| wafer T1 | 0,33 - 1,32 | 0,89 - 1,05 | 1,70 | 1,22 |
| T1 al cioccolato fresco | 0,46 - 1,34 | 0,83 - 1,05 | 2,53 | 1,22 |
| T1 ai cereali | 0,08 - 1,30 | 0,84 - 1,07 | 1,79 | 1,23 |
| wafer da colazione | 0,07 - 1,39 | 0,81 - 1,07 | 2,11 | 1,22 |
| brioche STD, scatola | 0,04 - 1,05 | 0,24 - 1,05 | 2,49 | 1,67 |

Sulla brioche il giro si chiude ancora a 0,24: e' il soffietto dei fianchi a
pinne strette, voluto. E il passo resta a 1,67 perche' con la scatola la spalla
non si allunga: il film vero li' fa le orecchie, che una superficie liscia non
sa fare. Restano fuori i denti, che il film lo tagliano davvero.

La misura gira da sola su ogni costruzione (`verifica.testate_flowpack`, la
terza verifica) e ha i denti: sul vecchio modo di mappare grida `GRAFICA
STIRATA SULLE TESTATE - 3,10 lungo il passo, la spalla e' troppo ripida per il
film che ha; 1,55 lungo il giro, la grafica si allarga con la pinna; il giro si
chiude a 0,05, i fianchi spariscono sul bordo della pinna` sul T1 farcito, e
grida sul T1 della merendina, sul wafer T1 e sulla brioche.

### La falda dice se la soluzione e' sbagliata

La falda non scala col nastro: e' il lembo che schiacciano le ganasce, e le
ganasce non diventano piu' grandi perche' il sacchetto lo e'. Misurate:

| pack | nastro | falda |
|---|---|---|
| T1 ai cereali | 122 | 16,0 |
| barretta proteica | 141 | 15,0 |
| T1 della barretta fresca | 144 | 14,0 |
| T1 farcito | 165 | 12,5 |
| brioche T10 | 420 | 4,1 |

Da 122 a 420 mm di nastro, sempre fra 4 e 16. **Una falda molto piu' grande
non e' una falda: e' il segno che il solutore ha preso la quaterna di pieghe
sbagliata.** Nastro, passo e corpo restano giusti anche cosi', quindi la
soluzione sembra buona e il pack esce piatto.

E' l'unica quantita' fisica che distingue due soluzioni entrambe coerenti, ed
e' per questo che viene **prima della simmetria** nella scelta della quaterna.
Sulla brioche STD erano in gara:

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

cioe' il fronte misura **mezzo giro**. Sul wafer T1 chiude al millimetro:

    23 (retro) + 36 (FRONTE) + 12 (retro) + 12 (lembo) = 83
    giro 71,  fronte 36,  mezzo giro 35,5

e la fascia da 36 e' proprio quella che il disegno marca *TEXT ORIENTATION*,
come vuole la regola del pannello marcato. Il lembo da 12 e' la fascia che la
legenda chiama *Covered Area*: si chiama coperta perche' finisce sotto.

**Forzare un pack a sovrapposizione nel solutore a pinna da' una risposta
plausibile e sbagliata.** Sul wafer T1 usciva falda 5,5 per lato — 11 mm di
nastro nell'aletta invece che intorno al prodotto, giro 72 invece di 71 — con
fianchi da 12 e fronte da 24 invece di 36. Il pack veniva sottile, squadrato e
con la grafica ruotata, e nessun controllo se ne accorgeva perche' i conti
tornavano tutti. Lo ha visto l'utente, confrontandolo col pack vero.

Corollario, imparato buttando via un'ora di lavoro: **un ripiego che allarga il
solutore va misurato contro un pack vero prima di tenerlo.** Avevo aggiunto la
deduzione della quarta piega dall'invariante dei fianchi uguali: matematicamente
giusta, e sul wafer T1 dava 24 x 12 con tutti i conti in ordine. Era la famiglia
sbagliata. E' stata rimossa: era nata per il wafer T1, il wafer T1 non ne ha
bisogno, e restava una strada capace di produrre in silenzio una sezione
sbagliata su qualche pack futuro.

#### La terza chiusura: il tubo piatto a pinna

Il **T1 cold seal** (disegno 12402) non e'
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
ruotato di 90 gradi. Provando l'altra chiusura prima dell'altro verso, la
brioche — che va letta ruotata — trovava una lettura plausibile nel verso
sbagliato e il verso giusto non veniva mai provato.

#### Il rigonfiamento di un tubo piatto

Un tubo piatto non ha un rapporto larghezza/spessore da tenere fermo:
gonfiandosi passa dalla lente al **cerchio**, e il cerchio e' il massimo fisico
— con quel film non si puo' essere piu' tondi. Il livello dice quanto ci si
avvicina, in frazione del diametro del cerchio, da 0,65 a 1,00.

La scala e' tarata sull'unica misura che esiste per questa famiglia, il GLB di
riferimento del wafer T1: sezione a ellisse di rapporto **1,466** e ingombro
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
**T1 al cioccolato fresco** - nastro 101, pieghe a 13, 26, 42 e 81, lembo di 20 in
fondo - ne trova due, e a pari scarto, 1,48 mm dal mezzo giro:

    fronte  0 - 42   retro 0 / 39    striscia tecnica e tratteggio
    fronte 42 - 81   retro 42 / 0    il marchio

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
viene a zero. Sul wafer T1 e sul croccante T2 fondente, col retro diviso in due, non cambia
niente.

### Le guide ravvicinate: due letture, non una scelta

Tre linee ravvicinate ed equidistanti **possono** essere una piega sola
disegnata con due guide ai lati - senza fonderle le fasce escono assurde
(5 | 63 | 5) - ma possono anche essere tre pieghe vere, e il disegno non lo
dice. Decidere con una soglia sullo scarto fra i passi e' quello che ha reso
piatto la brioche STD (vedi "Mezzo millimetro non puo' cambiare il pack").

Quindi non si decide: si tengono **tutte e due le letture**, fusa e intera, si
risolvono entrambe e vince quella con la falda plausibile. Verificato
spostando la linea di mezzo attraverso la vecchia soglia, da 0,00 a 1,80 mm di
scarto: il pack non cambia mai.

### Pieghe e guide: la piega attraversa il passo

Tre linee ravvicinate sono una piega con le sue guide o tre pieghe, e il
solutore prova tutte e due le letture. Sul T2 di cialde c'e' un caso che
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
non la somma, arrotondata al 5%). Dove tutte le pieghe sono uguali - wafer da colazione,
T1 farcito, le brioche - pareggia e decide il fronte come prima: sul parco nessun
altro file cambia. Non vale come regola assoluta, e per questo viene dopo la
simmetria: sul T1 della barretta fresca e sul croccante T2 fondente una piega vera e' piu'
corta delle altre (0,59 e 0,38 del passo).

### I capi dello steso sono il taglio, non il centro del gruppo

Le linee a meno di 3 punti fanno gruppo, e il gruppo vale il suo centro: per
una piega disegnata due volte va bene. Per i due capi dello steso no. Sul T1
cold seal il taglio e la riga del margine, a un millimetro, finivano nello stesso
gruppo, e il capo cadeva a mezzo millimetro dal taglio: nastro 114 invece di
115. Il capo e' la linea **piu' esterna** del suo gruppo.

Sul parco cambia il **T1 al mandarino**, da 135,5 a **136,0**: ed e' la sua
catena di quote a dirlo, 1 | 15 | 14 | 20 | 2 | 32 | 2 | 19 | 16 | 13 | 2 =
136. Il taglio a sinistra copre il passo come quello a destra e come le
pieghe, 149 mm; la linea a un millimetro e' lunga 152 e sporge oltre il passo,
quindi e' un'altra cosa. La brioche promo si sposta di un decimo di punto, e
tutti gli altri restano al byte.

### La falda sta sopra il retro anche nelle testate

Oltre il corpo la falda si posava a distanza zero sul retro schiacciato nella
saldatura, e due superfici alla stessa distanza si contendono i pixel: sul
T1 cold seal la falda bianca e la testata marrone uscivano a puntini. Adesso
resta sempre un ventesimo di millimetro sopra (`FALDA_SOPRA`): non si vede, e
decide chi sta sopra - la falda, come nel pack vero. Sui flowpack a pinna del
parco si spostano solo quei vertici, di 0,05 mm, e texture e UV non cambiano.

### Della falda si vede la fascia dell'altro capo del nastro

I due bordi del nastro si saldano a pinna, e la pinna si corica sul retro. Ma
**quale faccia resta in vista** non e' una scelta: e' geometria. Dalla
cucitura ogni fascia sale con la faccia stampata rivolta verso il retro da cui
arriva. Coricandosi su un retro, la fascia che viene da li' gli va contro e
sparisce; resta in vista l'altra, che continua il retro dall'altra parte della
cucitura come un film ripiegato su se stesso.

Il modello corica la falda sul primo tratto del retro, quello che parte da g0,
e la texture ci metteva la fascia di g0: la faccia **nascosta**. Il DT del
gelato su stecco lo dice con i nomi - la fascia di g0 e' "Neutral Area", bianca, la
striscia del retro sotto la falda e' "Covered Area", e la fascia di g1 e'
marrone come la zona della scadenza accanto alla cucitura, col box bianco
della scadenza che attraversa la piega. Sul modello c'era una striscia bianca
dove il pack ha 27 mm di marrone, e il box tagliato a meta'.

Adesso la falda prende la fascia oltre **g1** (`fin_on_surface`), a partire
dalla cucitura. Cambiano tutti i dodici flowpack a pinna che ho, e in meglio:
dove le due fasce sono diverse, quella di g0 e' la neutra - bianca,
tratteggiata (T1 della barretta fresca, pane ripieno), con le **tacche nere della
fotocellula** (T2 di cialde, file 159 e 174, gelato su stecco) - e quelle tacche
finivano sul retro e nei denti delle testate. Adesso il retro continua sulla falda: arancio
e rosso sul T1 al mandarino e sul T1 cheesecake, rosso sul T1 della barretta fresca, marrone e
rosso nelle testate del T1 cold seal. Sul wafer da colazione, sulla brioche e sul file 176 le due
fasce sono stampate uguali e non si vede differenza. Pillow, astucci e vassoi
restano al byte.

Un'assunzione non verificata: in tutti i file visti la fascia neutra sta dalla
parte di g0, e la falda va coricata li'. Se un file la avesse dall'altro capo,
la falda andrebbe coricata sull'altro retro, e sul modello si vedrebbe la
fascia neutra. Il segno da cercare e' quello: tacche della fotocellula o
tratteggio sulla falda vista.

### Il materiale del film lo dicono i DT secondari

Un flowpack e' film di plastica, e la riflessione di serie - lucida, uguale su
tutto il pack - gli va bene. Ma il film puo' essere **metallizzato**, o avere
una **vernice opaca**, e il file lo dice: accanto al DT con la grafica mette
altre copie del DT, una per lastra, e una legenda. Sul biscotto T3:

- l'**alluminio** e' il grigio che il DT principale mette dove la grafica non
  copre (un PANTONE 423 C, in legenda «Aluminium»). E' scavato sotto la
  grafica: copre il 35% del foglio, quello che resta scoperto;
- il **white plate** e' una copia del DT 200 mm piu' sotto, campita di
  PANTONE 317 C. Dove c'e', sotto gli inchiostri c'e' il bianco coprente e il
  film resta plastica bianca. Sotto le foto della sleeve e del biscotto il
  bianco non e' un tracciato ma un'**immagine** in DeviceN col canale 317 C;
- la **vernice opaca** e' un'altra copia, 200 mm anche a destra: i raggi
  attorno al biscotto, in PANTONE 674 C.

La regola: **dove c'e' l'alluminio e non c'e' il white plate, il film e'
metallo**. Gli inchiostri li' sono trasparenti sul metallo, quindi il pack e'
metallizzato del loro colore - il colore stampato sul bianco per l'argento -
e argento dove non c'e' inchiostro. Il grigio con cui il DT disegna
l'alluminio non e' un inchiostro, e dalla texture va via. La vernice opaca fa
opaca la plastica e satinato il metallo: sul biscotto T3 e' la traccia
chiara dei raggi, che la grafica disegna in grigio chiaro sull'alluminio.

Nel GLB vanno il colore base, con gli inchiostri sul metallo, e la mappa
metallo/ruvidita' di glTF, in PNG perche' il JPEG sui bordi di una maschera
inventa metallo: metallo dove l'alluminio e' scoperto, ruvidita' 0,16 il
metallo lucido e 0,50 satinato, 0,30 la plastica lucida e 0,72 opaca. Glam
la mostra con le sue luci HDR (`model-viewer`); la pagina dello Space passa al
materiale PBR, con uno studio da riflettere, solo per i modelli che la
hanno; le viste del controllo dell'AI simulano il riflesso, perche' il
metallo senza ambiente usciva bianco latte, e al controllo arriva una nota
che il metallo non e' il grigio piatto del DT.

**Come si leggono** (`pack3d/materiali.py`):

1. **Le copie del DT** si trovano dalle linee: rettangoli col rapporto del
   foglio, in qualunque scala - 1:2 sul T2 di cialde, 0,62 sul T1 cold seal,
   1:1 sul biscotto T3 - confermati solo se dentro hanno le linee lunghe
   del DT nello stesso posto. Basta una coppia di bordi: sul pane ripieno il bordo
   sinistro della copia della vernice e' interrotto dalle fasce delle pinne.
   Specchiata solo se rovesciata combacia nettamente meglio: un DT di
   flowpack e' quasi simmetrico, e le copie del biscotto T3 tornavano
   uguali nei due versi.
2. **Dove dipinge ogni lastra** lo dice Ghostscript, lastra per lastra,
   anche dentro le immagini DeviceN.
3. **Il ruolo** viene dal nome della lastra (`Aluminium`, `White Plate`,
   `Matt Varnish` - T2 di cialde, pane ripieno T2), poi dal **titolo**
   scritto accanto alla copia («Aluminium Support», «White Plate» sotto le
   copie del T1 cold seal e del T1 ai cereali). I titoli di una pagina stanno
   tutti dallo stesso lato: sul T2 di cialde quello di una copia e' sopra di
   lei e sotto quella di prima, e il lato giusto e' quello dove ce ne sono di
   piu'. Un titolo che dice altro - «Cold Seal», «Transparent Support» -
   chiude la lastra. Quando i titoli sono **in curve**, come sul biscotto
   T3, i ruoli li legge l'AI, dalla legenda e dalla tavola degli
   inchiostri (`controllo.ruoli_lastre`), una volta per file. Il caso li puo'
   dichiarare (`materiali` nelle opzioni) e vince su tutto: e' cosi' che il
   parco, che non ha l'AI, costruisce il biscotto T3.
4. **Le maschere**: ogni copia si separa da sola, ritagliata e senza le
   altre tinte. Le linee del DT bucano la lastra, e il white plate usciva
   rigato di metallo lungo ogni piega.

**Quando non cambia niente.** Alluminio senza white plate: non si sa dove il
film resta bianco, il modello resta plastica e lo dice. Un materiale che non
cambia il film - meno di mezzo punto di metallo, meno di un millesimo di
vernice - lascia il GLB com'era. Un inchiostro metallico stampato (`Silver`,
PANTONE 877 C) non e' il supporto metallizzato, e qui non si tratta. Per ora
solo i flowpack: la pouch e gli astucci verniciati hanno le stesse lastre, e
verranno.

Sul parco cambiano tre casi su trenta, tutti in meglio, gli altri restano al
byte:

- **T2 di cialde** (e la sua voce senza tipologia): le lastre si chiamano
  `Aluminum` e `White Plate`, in copie a 1:2. Il metallo e' il 39% del film:
  lo sfondo dietro le cialde e le saldature, che prima erano un grigio piatto
  e ora sono argento; la banda rossa, la fascia bianca col marchio e le
  cialde restano plastica;
- **pane ripieno T2**: la `Matt Varnish` copre l'88,6% del film, tutto
  tranne marchio, prodotto e il bollino x2, che restano lucidi.

**T1 ai cereali** e **T1 cold seal** hanno alluminio e white plate, letti dai
titoli delle copie, ma sulla stessa parte del film: niente metallo, il GLB e'
quello di prima e la riga lo dice. Il **biscotto T3** entra nel parco
coi ruoli dichiarati, perche' il parco non ha l'AI: metallo sul 37% del film,
vernice opaca sull'1%. Lo stesso file senza dichiarazione, e senza AI, esce
al byte com'era, con la riga che dice quali lastre non hanno un titolo
leggibile; con l'AI esce identico a quello dichiarato.
