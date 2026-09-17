# Regole della pipeline pack3d

Regole accumulate caso per caso, con il punto del codice che le applica e i
controesempi che le giustificano.

## Domande all'utente

| regola | dove |
|---|---|
| Su **ogni** PDF chiedere prima la tipologia: Cartotecnico, Flowpack, Coppa conica, Altro. La tipologia si dichiara, non si indovina. | pannello del frontend + `analyze_pdf(pdf, kind)` |
| Solo flowpack: chiedere il **numero esatto** di dentini, digitato dall'utente. Nessuna alternativa proposta, 0 = pinne lisce. | campo numerico senza valore predefinito |
| Solo flowpack: chiedere il **rigonfiamento** fra quattro opzioni: Rigido (1-3), Medio (4-6), Morbido (7-10), "Scegli tu". | `gonfiore()` in `server.py` |

Il rigonfiamento e' una **scala 1-10**, non tre gradini: Rigido 1-3 (pack teso e
aderente, aria minima), Medio 4-6 (volume standard, leggero cuscino d'aria),
Morbido 7-10 (volumetrico e visibilmente gonfio, gas o liquidi). I parametri di
forma si interpolano sul livello.

Riferimenti: FULFIL = morbido, Milch-Schnitte e Kinder Bueno Dark = rigido.

**Opzione "Scegli tu".** Claude assegna il livello dalla natura del prodotto:

| prodotto | livello | perche' |
|---|---|---|
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

## Regole comuni a tutte le tipologie

- **Confrontare sempre il modello finito con lo steso.** La grafica sul 3D deve
  avere lo stesso orientamento del PDF, mai specchiata o capovolta.
- **Non distorcere mai la grafica.** I bollini circolari restano cerchi. Ogni
  pannello va sulla faccia corrispondente e centrato.
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
3. **Legenda del documento** — quando il DT non sta su un livello separato, lo si
   riconosce dalle note o dal riquadro tipo "Job Colors": la legenda affianca il
   **nome della lastra alla sua pastiglia colore**, quindi campionando la
   pastiglia si associa il nome alla separazione, senza indovinare. Nomi
   ricorrenti: Technical Drawing, Dimensions, Print Free Area, Best Before Area,
   Bar Code Area, COVERED Area, Neutral Area, Eyemark, Coldseal, White, Varnish.
4. **Registro di lastre note** — scorciatoia quando la legenda manca. Negli
   artwork Ferrero ricorrono identici: Pantone 3405 C = Technical Drawing,
   346 C = Dimensions, 571 C = Print Free Area, 350 C = Best Before Area,
   341 C = Bar Code Area, 1565 C = COVERED Area. Anche `All` e' tecnica.
5. **Euristica** su spessore (filo di capello, <= 0,8 pt) e colore. E' una stima
   e va dichiarata come tale.

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

**Metodo:** una modifica alla volta, con verifica in mezzo. Cambiandone due
insieme si perde il risultato buono gia' raggiunto senza capire quale delle due
ha rotto cosa.

## Il controllo visivo e' obbligatorio

Dopo ogni pulizia va **guardato** il confronto prima/dopo, non solo lette le
metriche. Le metriche dicono quanto hai tolto, non se hai tolto la cosa
sbagliata: sul Kinder Bueno T2 la K del logo e' sparita con tutti i numeri in
ordine, e me ne sono accorto solo perche' me l'ha detto l'utente.

Lo strumento `visual_check` restituisce l'immagine affiancata: va chiamato
sempre dopo `clean_artwork` e prima di costruire.

Priorita' negli errori: **un logo perso e' grave, un residuo tecnico no.** Nel
dubbio si toglie meno.

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

## Astucci

`dieline.py` isola il tratto della fustella scegliendo la penna che accumula
piu' lunghezza **e** piu' cordonature distinte; scarta i riquadri dell'artwork
riconoscendoli dalla coppia contorno+riempimento; isola il gruppo connesso piu'
esteso per escludere i cartigli, recuperando pero' i gruppi che cadono
nell'ingombro (le alette con fianchi obliqui non toccano il corpo con tratti
dritti); valida le cordonature fascia per fascia, altrimenti le alette di presa
del cielo vengono scambiate per fianchi. Il verso di fasciatura, verticale o
orizzontale, si deduce dalla struttura.

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

**Niente soglie assolute sulla lunghezza delle linee.** Fra il nastro di K
Tronky (83 mm) e quello di K Brioss (420 mm) c'e' un fattore cinque: una
cordonatura che attraversa tutto il nastro del Tronky e' lunga 83 mm, sotto gli
88,2 mm che `analyze_auto` pretendeva, e nessun pack piccolo poteva passare il
cancello. Le soglie vanno prese in frazione del tratto piu' lungo.

**Il raster e il tracciato devono stare nello stesso telaio.** pdfplumber misura
sul MediaBox, pdfium rende il CropBox. Quando i due riquadri non coincidono — su
K Tronky il CropBox e' 459 x 271 pt dentro un MediaBox di 1332 x 958, spostato di
(419, 471) — le coordinate dei segmenti indicizzano un'immagine che comincia da
un'altra parte: nessuna eccezione, solo misure prese nel posto sbagliato, e
intere viste tecniche che restano fuori dalla resa. Si rasterizza sempre con
`dieline.render_page`, mai con `pdfium.PdfDocument(...).render()` diretto.

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
  Brioss i 37,5 mm oltre il corpo sono 28,5 di gola piu' 9,0 di pinna, e 9 mm
  e' quanto si misura sulle foto del pack. Con una scatola dentro la gola non
  puo' mangiare il corpo, perche' la scatola tiene la sezione fino alla sua
  faccia: il pack resta squadrato fino in fondo e poi salda subito. Nel modello
  si sposta massa da `end_fin` a `L` tenendo ferma la somma `L/2 + end_fin`,
  cosi' le UV non cambiano e la grafica non si muove.

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
3. le pinne di testa si misurano dal **margine non stampato**, non dalle linee
   di quota — ma solo se quel margine esiste. Su artwork **al vivo** non c'e':
   su Kinder Bueno T2 la grafica copre 923 colonne su 1010 da bordo a bordo, la
   misura per margine dava `end_fin = 0` e il modello usciva con il 21% di
   triangoli degeneri, tutti collassati sulla punta della pinna. Sotto 1 mm la
   misura non e' piccola, e' assente: `analyze_auto` la ricava allora dalle
   **coppie di linee di taglio e saldatura**, cioe' dal rientro fra le due
   linee piu' esterne di ciascun lato.

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
  grado): con una rampa corta il gonfiore invade il corpo e deforma i bollini.

## Coppe e contenitori conici

Lo steso e' un **settore anulare**. Il contorno va letto appiattendo le bezier
dal content stream (`cup.py`): ne' la silhouette rasterizzata ne' i punti che
pdfplumber espone per le curve vanno bene, i secondi includono i punti di
controllo.

```
r_bocca = R2 * alpha / 2pi     r_fondo = R1 * alpha / 2pi
apotema = R2 - R1              altezza = radice(apotema^2 - (r_bocca - r_fondo)^2)
```

- **Il fronte si ancora al baricentro angolare della grafica**, non alla
  mezzeria geometrica del settore. Sulla coppa Nutella il baricentro dei pixel
  rossi cade a +8,86 gradi.
- **Con un render disponibile il fondo si allinea alla silhouette**: l'arco
  interno puo' non essere concentrico con l'esterno. Nutella POT: 72,0 mm da
  silhouette, poi confermati dal DT a 72,32, contro i 69,3 dell'artwork.
- Su `fit_sector` guardare **due numeri**, non uno. Residuo basso non basta se
  lo scarto fra gli angoli dei due archi e' alto: 0,001 mm con 14,5 gradi di
  scarto significa cerchio adattato al pezzo sbagliato di contorno.
- Il **fondo ha una cordonatura con rientranza**, leggibile dai cerchi
  concentrici del DT.

## Casi calibrati

Gli artwork il cui impaginato non rientra nei solutori automatici stanno nel
registro `CASI` in `server.py`, riconosciuti dalla firma della pagina. Oggi
contiene FULFIL Chocolate Hazelnut Whip.

Risolti dall'analisi automatica, con l'invariante che chiude:

| | nastro | passo | fronte | spessore | falda |
|---|---|---|---|---|---|
| Kinder Country | 122,0 | 119,0 | 35,0 | 10,0 | 16,0 |
| Kinder Paradiso T1 | 165,0 | 155,0 | 43,0 | 27,0 | 12,5 |
| K Brioss Latte e Cacao T10 | 419,9 | 290,0 | 148,9 | 57,0 | 4,1 |

**K Tronky T1 non e' coperto.** Nastro e passo si leggono giusti — 83,0 e 144,0,
gli stessi numeri che il cartiglio della miniatura scrive come WEB WIDTH e STEP —
ma la fasciatura non chiude: le fasce lette sono 8,5 | 14,5 | 36 | 7 | 5 | 3,5 |
8,5 e nessuna quaterna soddisfa l'invariante. Le tre fasce strette in fondo sono
probabilmente zona di saldatura e eyemark, non cordonature, ma senza il pack in
mano e' una congettura. Nota: le quote del cartiglio sono testo vettorializzato,
non estraibile — sulla pagina intera pdfplumber trova 20 parole.

## Assunzioni non verificate

- Il livello **Medio** di gonfiore e' interpolato fra Rigido e Morbido: manca un
  caso reale.
- Il **raggio di raccordo** e' trattato come proprieta' del film, quindi
  assoluto e non proporzionale allo spessore.
- L'**apertura della pinna** vale oggi meta' perimetro pieno
  (`PACK3D_FIN_OPEN = 1.0`): il 94,8% misurato su un solo render e' stato
  scartato perche' non era lui a produrre le punte degeneri.
- Lo **steso ruotato** e' stato visto su un artwork solo, Kinder Pingui T1: la
  regola "se le fasce non chiudono, ritenta trasposto" non ha un secondo caso.
- Su disegno speculare, quando i due rientri di saldatura differiscono di piu'
  di 0,5 mm si tiene **il piu' stretto**. Anche questa viene da un campione
  solo, e la scelta opposta sarebbe altrettanto difendibile.
- Il canale `quote.larghezza` / `quote.spessore` dall'analisi AI alla
  costruzione **non e' mai stato percorso con una chiave API vera**: e'
  verificato end-to-end con l'agente simulato, non con l'agente.
- Il **profilo del tappo** della coppa (cordonatura, arrotolatura, rientranza)
  e' stimato dal render: nessun documento lo riporta.
- Un'eventuale **sovrapposizione incollata** dello sleeve non e' misurabile dal
  PDF: se c'e', tutti i diametri calano.
