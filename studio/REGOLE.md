# Regole della pipeline pack3d

Regole accumulate caso per caso, con il punto del codice che le applica e i
controesempi che le giustificano.

## Domande all'utente

| regola | dove |
|---|---|
| Su **ogni** PDF chiedere prima la tipologia: Cartotecnico, Flowpack, Coppa conica, Altro. La tipologia si dichiara, non si indovina. | pannello del frontend + `analyze_pdf(pdf, kind)` |
| Solo flowpack: chiedere il **numero esatto** di dentini, digitato dall'utente. Nessuna alternativa proposta, 0 = pinne lisce. | campo numerico senza valore predefinito |
| Solo flowpack: chiedere il **rigonfiamento** fra quattro opzioni: Rigido (1-3), Medio (4-6), Morbido (7-10), "Scegli tu". | `gonfiore()` in `server.py` |
| Solo flowpack: chiedere l'**apertura delle pinne**, da 1 a 3. Non si deduce dal rigonfiamento. | cursore `pinne`, `build_flowpack` |
| Solo flowpack: chiedere se il **film avvolge una scatola**. | casella `scatola`, `parametri_costruzione.avvolge_scatola` |

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
  niente e si lascia com'e': indovinare sarebbe peggio.
- **La `k` di `kinder` e' NERA.** E' l'invariante piu' facile da controllare di
  tutto il parco, e quando non torna dice sempre la stessa cosa: la
  **sovrastampa non e' stata simulata**. Sul K Brioss STD la `k` esce azzurra,
  perche' e' costruita come un ciano che sovrastampa un nero: senza
  sovrastampa il ciano lo copre invece di sommarcisi. Verificato affiancando
  tre rese dello stesso marchio — pdfium azzurra, Ghostscript con
  `-sOverprint=disable` azzurra, Ghostscript con `-sOverprint=simulate`
  **nera**. Qui l'artwork e' giusto: sbaglia chi lo rende. Vedi *La colata si
  rimette con l'inchiostro del file*.
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
  servirebbe trasporre anche le quote del solido — aspetta un pack che lo
  mostri.
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
rasterizzare (`strati.senza_tecnici`) e non resta niente da mascherare a mano.
E' il livello 1-2 della scala qui sopra usato anche per la MASCHERA, non solo
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
che l'euristica non prende, si allarga con quello in mano.

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
CODE AREA`, `PRINT FREE AREA`, `NEUTRAL AREA` sono la stessa cosa fatta per
un'altra ragione: **posto tenuto**, non grafica. Nessuna di loro si stampa, e
**nessuna deve comparire nel render finale**.

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

**Il prefiltro.** Prima di estrarre il testo si guarda se nel flusso della
pagina compare la parola `AREA`: costa da 0,00 a 0,05 secondi e divide netto -
zero occorrenze sui sei file del parco senza etichette, 2, 6 e 11 sui tre che
le hanno. Senza, l'estrazione del testo sarebbero 2,9 secondi buttati su ogni
K Brioss STD. Se un file scrivesse `AREA` in una codifica che il prefiltro non
vede si resterebbe alla pulizia di prima: puo' far perdere un'occasione, non
puo' far strappare la lastra sbagliata.

**Il costo, detto per intero.** La ricerca parte solo se il file **non ha
livelli tecnici**: dove i livelli ci sono la pulizia e' gia' esatta e non si
paga niente. Sul parco i sei file senza etichette restano al loro tempo — K
Brioss STD 1,9 -> 2,0 s, crt_nuovo 2,4 -> 2,4, vernice 4,1 -> 3,8 — mentre i
due che le hanno pagano: **Brioss Latte e cacao 0,9 -> 4,5 s**, **Colazione
2,1 -> 19,7 s**. Quei diciotto secondi sono quasi tutti lo strappo delle tre
lastre, che su un flusso da 3,6 MB e' la parte cara; la lettura del testo ne
vale 3,8 e la passata `tiffsep` uno.

E' tanto, e su un piano Free a 0,1 CPU si sente. In cambio il pack non esce
con `TEXT AREA` scritto sopra, e la memoria **scende**: sul solo Colazione il
picco va da **613 a 473 MB**, cioe' da sopra a sotto il tetto dei 512 —
togliere tre lastre piene dal flusso costa meno di quanto costi renderle.

**Quello che resta fuori.** Se il nome dell'area sta solo nella legenda e non
sopra il riquadro — Kinder Bueno Dark T2, il cartotecnico Pingui T6 — non c'e'
niente di sicuro da leggere: la legenda e' un accostamento di posizione, e
sbagliare accostamento vuol dire strappare la lastra della grafica. Li' si
resta all'euristica, il build lo dichiara, e la risposta e' la richiesta a chi
prepara il file.

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

### La tipologia non riconosciuta e' un errore, non un ripiego

`kind` si dichiara e non si indovina, e c'era gia' la nota sul sinonimo
mancante: il viewer glamlab manda `cartotecnico` e senza sinonimo ogni astuccio
finiva dal solutore flowpack. Lo stesso difetto sta all'altro capo: un valore
qualsiasi non riconosciuto - `auto`, per esempio - non entrava in nessun ramo e
cadeva **in silenzio** su quello flowpack. Oggi risponde 400 e dice cosa
dichiarare.

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

### La grafica va in quadricromia, non in RGB

**In RGB la sovrastampa non esiste**, quindi non c'e' niente da simulare: ne'
dal nostro rasterizzatore, ne' da quello di chi guardera' il file. E la
sovrastampa non e' un effetto facoltativo, e' come sono costruite certe
grafiche.

Il caso che lo dimostra e' la **colata di latte Kinder**. Nasce come una lastra
che sovrastampa il fondo: dove passa, moltiplica quello che c'e' sotto, e da
quella moltiplicazione vengono l'ombra sulle gocce e il volume del getto. Sul
Kinder Pingui T6 BOX quella colata e' arrivata come **immagine indicizzata su
base ICC a tre canali, con la tavolozza fatta di ciano**: senza sovrastampa la
moltiplicazione non avviene, le gocce perdono l'ombra e la colata esce come una
macchia di **ciano piatto**.

Non e' una cosa che si aggiusta a valle: reinventare l'ombra vorrebbe dire
dipingere colore che nel file non c'e'. La regola e' sull'ingresso — **la colata
va fornita in quadricromia** — e il nostro compito e' accorgersene e dirlo
prima che l'utente guardi il modello e non capisca cosa e' andato storto
(`techink.avviso_rgb`, un decimo di secondo e niente in memoria).

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
orizzontale, si deduce dalla struttura, e cosi' la **famiglia**: chiuso o
aperto, vedi sotto.

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
  vuol dire che questa non e' la lettura giusta;
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

### Un astuccio ha uno spessore

Un astuccio non e' una superficie, e trattarlo come tale si paga proprio dove
il pack e' aperto: ogni faccia ha una normale sola, da dietro il culling la fa
sparire, e guardando dentro la finestra del Pingui T6 non si vedeva niente.
Il pack diventava un guscio di carta zero.

Con lo spessore l'interno c'e', ed e' cartoncino. Per ogni faccia si aggiunge:

- la **faccia interna**, spostata di `PACK3D_SPESSORE_CRT` (0,45 mm) lungo la
  normale entrante e con l'avvolgimento rovesciato, perche' la sua normale
  guardi dentro;
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

#### Il caso calibrato

    KP T1 Mandarino       livello `Colata`, 120,5 x 36,3 mm
                          ombra fustellata: recupera lo 0,2% -> risorsa
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

**Un ripiego non deve mai essere muto.** Se `analyze_auto` fallisce, la
costruzione passa al solutore vecchio: il modello che ne esce non e' sbagliato
in modo evidente, e' **plausibile**, che e' peggio. Su Milch-Schnitte T1
cambiavano corpo e pinne — 136,5 e 8,0 invece di 138,7 e 6,9 — e la grafica
scivolava sul fronte, senza che niente lo dicesse. Ogni ripiego va dichiarato
negli avvisi della costruzione.

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

#### Come si sceglie la chiusura

Quattro tentativi in ordine: pinna nei due versi dello steso, poi
sovrapposizione nei due versi. L'ordine conta. "Le fasce non chiudono" non
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
| Milch-Schnitte T1 | 144,0 | 152,5 | 43,0 | 15,0 | 14,0 |
| Kinder Country | 122,0 | 119,0 | 35,0 | 10,0 | 16,0 |
| Kinder Paradiso T1 | 165,0 | 155,0 | 43,0 | 27,0 | 12,5 |
| K Brioss Latte e Cacao T10 | 419,9 | 290,0 | 148,9 | 57,0 | 4,1 |

Risolti come tubo piatto a sovrapposizione, dove non c'e' falda e la sezione la
decide il rigonfiamento:

| | nastro | passo | giro | fronte | lembo coperto |
|---|---|---|---|---|---|
| K Tronky T1 | 83,0 | 144,0 | 71,0 | 36,0 | 12,0 |

Nota sul Tronky: le quote del cartiglio sono testo vettorializzato, non
estraibile — sulla pagina intera pdfplumber trova 20 parole. Sono state lette a
occhio dalla miniatura per verificare il risultato, non per produrlo: 144 = 10 +
124 + 10, 83 = 23 + 36 + 12 + 12.

Astucci, con la quota letta due volte che chiude il conto:

| | fasciatura | L x H x P | riscontro |
|---|---|---|---|
| Nutella Donut | orizzontale, chiuso | 188,1 x 190,8 x 38,1 | fianchi 38,1 = 38,1 |
| K Pingui T6 BOX | verticale, aperto | 140,5 x 125,0 x 40,5 | cielo e fondo 40,5, fianchi 40,3 |

## Assunzioni non verificate

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
- Il **profilo del tappo** della coppa (cordonatura, arrotolatura, rientranza)
  e' stimato dal render: nessun documento lo riporta.
- Un'eventuale **sovrapposizione incollata** dello sleeve non e' misurabile dal
  PDF: se c'e', tutti i diametri calano.
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
