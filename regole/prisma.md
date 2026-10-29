# Regole: La scatola a prisma

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## La scatola a prisma

Una scatola di cartoncino con il fondo a poligono - esagono, ottagono,
pentagono - e una parete dritta su ogni lato, chiusa da un coperchio fatto
allo stesso modo che calza sopra. Ogni pezzo e' un PDF suo: si dichiara
**Cartotecnico in 2 pezzi** (o in un pezzo solo, il fondo aperto); il codice
sta in `pack3d/prisma.py`, il montaggio in `server.build_prisma`.

Il primo caso e' arrivato dalla coda (8f67b58f3d) come costruzione ferma:
«cartotecnico in 2 pezzi: per ora so montare lo sleeve e il tappo di una
coppa, o il cono col suo lid». Era un esagono: il fondo con il piano da
141,2 x 122,3 mm (70,6 di lato) e sei pareti da 46, il coperchio con il
piano da 145,0 x 125,6 e sei pareti da 16, coi risvolti dentro. Prima la
sessione l'aveva lasciato a mano, preso per una famiglia nuova: e' un
cartotecnico.

### La firma in fustella

Si prova **solo dopo** che i pezzi tondi hanno rifiutato i PDF
(`server._pezzi_prisma`, chiamato quando `_pezzi_tondi` alza l'errore), solo
sul cartotecnico dichiarato in pezzi, e solo se **ogni** PDF si legge come
un prisma; altrimenti resta l'errore di prima. La fustella si legge come
quella del ballotin, a grafo (`ballotin.tratti_fustella`, `grafo`, `facce`):

- il **piano** e' la faccia piu' grande; i suoi spigoli sono quelli
  dell'inviluppo convesso, senza i vertici dove il contorno gira meno di 12
  gradi (sul coperchio una tacca dava sette vertici a un esagono). Il piano
  deve riempire almeno il 93% del suo inviluppo, avere da 5 a 12 lati (4 sono
  l'astuccio e il vassoio) e nessun lato sotto i 15 mm;
- su **ogni lato** c'e' una parete: una faccia attaccata appena fuori dal
  lato, anche al 12% e all'88% della sua lunghezza. L'altezza e' quanto la
  faccia si allunga lungo la perpendicolare, la mediana di tre misure al 30,
  50 e 70% del lato; sotto i 5 mm non e' una parete;
- dei **due pezzi** il coperchio e' quello col piano piu' largo (l'apotema
  medio: 62,8 contro 61,1 mm), e deve avere gli stessi lati del fondo.

### La vista di fuori, non quella di dentro

Il PDF del fondo porta due disegni della fustella affiancati, OUTSIDE e
INSIDE, lunghi quasi uguali (2059 e 1690 mm di tratti), e il piu' lungo era
quello di DENTRO: col pezzo connesso piu' lungo, come fa il ballotin, le
pareti uscivano viola pieno e il piano specchiato. Quando un secondo disegno
e' lungo almeno l'80% del primo si tiene quello con piu' grafica sotto
(`prisma._dettaglio`: la media del gradiente della pagina a 30 dpi
nell'ingombro): 31,7 la vista di fuori, 11,2 quella di dentro.

**Vale anche per l'astuccio** (`dieline._largest_cluster`, `ALTRA_VISTA`).
Un astuccio con OUTSIDE e INSIDE affiancate: i contorni delle zone segnaposto
della vista di dentro sono tracciati con la penna della fustella e la
allungavano (1781 mm contro 1493, l'84%). Vinceva la vista di dentro, quei
contorni diventavano pieghe (una larghezza vera di 143 divisa in 24,5 + 94 +
24,7) e la grafica era bianca. Fra i gruppi lunghi almeno l'80% del primo si
tiene quello con piu' colori distinti nella pagina a 50 dpi (`_colori`, come
`tools.dt_della_tavola`): 104-153 la vista di fuori, 34-41 quella di dentro.
Il gradiente medio di prisma qui non separa (9,55 contro 9,22).

**La falda di chiusura e' il fondo, e i suoi lati non sono dritti.** Nello
stesso astuccio la falda in fondo al fronte si stringe di circa 2 gradi verso
la linguetta (138,1 -> 139,4 su 36 mm), e `_segments` buttava i tratti non
orizzontali o verticali entro 0,7 pt: il bordo libero restava un pezzo
staccato e la scatola usciva senza fondo. Un tratto conta H o V anche quando
devia meno di 3 gradi (`QUASI_DRITTO = 0.05`, la tangente). E il bordo libero,
interrotto da linguetta e angoli tondi, copre il 60% della colonna: la prima e
l'ultima riga del riquadro bastano col 50% (`rows_in_col`, `bordo`), le altre
restano all'80%. Sette astucci del parco escono identici (md5).

### Il montaggio e il verso

Ogni parete si alza di 90 gradi sul suo lato; linguette e risvolti stanno
dentro e non si portano. Il fondo ha il piano a Y = 0 e le pareti in su; il
coperchio sta capovolto sopra, col piano a filo delle pareti del fondo piu'
lo spessore della carta e le pareti in giu'.

- Il piano del **coperchio** si guarda dall'alto, e lo steso cosi' com'e' sul
  foglio e' gia' la vista dall'alto col fronte in basso: (X, Z) = (x, y).
- Il **fondo** si guarda da sotto: il foglio si specchia in y e poi si gira,
  fra le rotazioni che portano i suoi lati su quelli del coperchio, su
  quella che mette davanti la parete piu' in basso sul foglio. E' una
  rotazione, non un altro specchio: la stampa delle pareti resta leggibile,
  dritta e non specchiata.

La texture di ogni pezzo e' il suo DT intero, come per il ballotin, con sotto
le strisce del rovescio e del taglio; il bordo libero di ogni parete prende
la costa. Due nodi nel GLB, `fondo` e `coperchio`, e i due stesi
nell'atlante.

### La lamina e' metallo

Il caso: la scatola esagonale al cioccolato fondente, approvata nella forma e
respinta da chi l'aveva caricata perche' la cornice del coperchio, che la
legenda dice `cold foil copper Kurz 404`, sul modello era arancio piatto. Il
PDF del coperchio ha una tinta piatta `..._ColdFoilCopper_Kurz404`, con
un'alternativa arancio che finge il rame: nessuna regola la riconosceva, ne'
per toglierla ne' per farla metallo, e pdfium la rendeva come un inchiostro
qualsiasi.

La regola (`pack3d/lamina.py`): una lastra che si chiama come una lamina -
foil (anche dentro una parola sola, `ColdFoilCopper`), Folie, lamina, hot
stamping, stampa a caldo - e' un film metallico sul cartoncino. Il colore
resta quello della texture, l'alternativa scelta dal grafico e gli inchiostri
sopra; quello che cambia e' il materiale: dove c'e' la lastra (piena dal 25%
d'inchiostro) e' metallo, ruvidita' 0,22, e attorno resta carta con la
ruvidita' di prima (0,42). Sul GLB e' la `metallicRoughnessTexture` di glTF,
in PNG, una per pezzo, che l'atlante unisce come il colore
(`exporters.write_glb_mesh` con `mr` in lista). La maschera viene dalla
lastra sul riquadro del DT (`techink.mappe_lastre`, 150 dpi al piu'), cosi'
il campione della legenda fuori dal DT non conta; sotto lo 0,2% non c'e'
metallo. Sulla scatola esagonale il foil e' il 38,4% del coperchio: la cornice, le
falde e le scritte arancio. Un "Silver" o un PANTONE 877 C sono inchiostri
metallici stampati, non una lamina, e qui non si trattano. La lamina si fa
sulla scatola a prisma e sull'astuccio.

### La lamina che dice solo la legenda

Il caso: un astuccio di cioccolatini da 16, respinto da chi l'aveva caricato perche'
il foil oro della legenda - "Coldfoil Gold ... KURZ 220" - sul
modello era giallo piatto. Qui nessuna lastra si chiama come una lamina: il
foil e' una tinta piatta qualsiasi, `PANTONE 113 C`, e il nome sta solo nella
voce della legenda, accanto al suo campione. E l'astuccio non aveva la
lamina per niente: la faceva solo il prisma.

Le regole:

- se nessuna lastra si chiama come una lamina, `lamina.lastre` legge la
  legenda come le aree riservate (`techink.aree_riservate` con `cerca`): la
  voce che dice foil, Folie, lamina, hot stamping, stampa a caldo, e la
  lastra piena del campione DAVANTI alla voce (solo quello, non quello che
  c'e' sotto la scritta). La resa costa solo se nel testo della pagina c'e'
  una di quelle parole;
- un campione puo' essere una cornice bianca col colore dentro (36 punti di
  quadro, 21 di colore): conta il pieno che ci sta dentro, se copre almeno
  un quarto della cornice;
- a pari stacco dalla voce vince il campione che copre di piu' la sua riga:
  una voce su due righe toccava anche il campione della voce sopra (TEXT
  Area, `PANTONE 1595 C`);
- l'astuccio ha la sua mappa metallo/ruvidita' sullo steso
  (`exporters._write_glb_steso`, terzo elemento di `steso`), girata come la
  texture, col cartoncino a ruvidita' 0,85 attorno.

Su quell'astuccio il foil e' l'1,5% dello steso: le scritte oro di fronte,
fianchi, cielo e fondo. Le due correzioni della legenda trovano anche, da
sole, le quattro aree riservate del file (`COVERED`, `TEXT`, `Bar Code`,
`Best Before`), che prima andavano dichiarate a mano.

### La linguetta di chiusura si incide

Lo stesso caso: il fondo e' la falda di chiusura, e il suo bordo libero ha
due tacche e fra loro la linguetta che si infila nella fessura dell'altra
falda. La faccia e' il rettangolo pieno del pannello, e il taglio - 47 mm di
catena su 34 di bordo, che entra di 6,6 mm - spariva: "manca la linguetta di
chiusura".

La regola (`incisioni.chiusura`): un tratto della fustella che parte da un
lato LIBERO della faccia - non una piega con un'altra faccia -, entra almeno
2 mm (`LINGUETTA_MIN`) e torna sullo stesso lato e' il taglio di una
chiusura, e sul cartone chiuso si vede: si incide come i tagli
dell'apertura a strappo (stesso solco, 0,35 x 0,22 mm), e la riga per il
controllo dice che quelle righe sono la linguetta. I lati obliqui della
falda vanno da un lato a un altro, e il filo dei fianchi corre a 0,3 mm dal
bordo: restano come sono.

### Il fondo a sormonto si ritaglia, sopra la falda

Lo stesso caso, respinto di nuovo: "la linguetta non e' incisa ma
fustellata/tagliata, cosi' come i bordi smussati; il lato della linguetta
deve andare sopra l'altro lato e non intersecarsi". La colonna e' falda -
RETRO - CIELO - FRONTE - FONDO: il fondo (41,0 mm) chiude sul retro
sormontando dall'esterno la falda del retro (41,2 mm, con la fessura a 9 mm
dalla piega), e il suo bordo libero ha gli angoli smussati e due tacche a
mezzaluna che entrano 7,1 mm. Il modello aveva il fondo pieno col solco e
nessuna falda.

La regola (`pack3d/sormonto.py`): astuccio chiuso col fondo dopo il fronte e
il retro prima, una falda sopra il retro lunga almeno meta' del fondo, e il
contorno di taglio del fondo - la catena della fustella attorno al pannello,
dalla piega col fronte alla piega - che entra dal bordo libero almeno 2 mm
(`SAGOMA_MIN`) lontano dai fianchi. Allora il fondo si ritaglia su quel
contorno (smussi e tacche sono vuoti, con la costa del cartoncino) e non si
incide; la falda va sotto di lui, a uno spessore, al posto della sua faccia
interna, stampata col riquadro alto quanto il fondo sopra il retro, nello
stesso verso: dalle tacche e dagli smussi si vede lei. Nel parco lo fa solo
questo astuccio; gli altri restano identici (la regola non scatta).

Il contorno si legge **sulla curva**: le mezzelune e gli smussi sono tratti
di Bezier, e la lettura dei tracciati ne teneva i tre punti - due di
controllo e l'arrivo - come vertici. I punti di controllo non stanno sulla
curva, e il ritaglio usciva a zig-zag: una tacca di 7 mm erano 5 punti.
`tracciati._cammina(curve=True)` campiona la cubica ogni 0,85 pt (0,3 mm);
la tacca diventa un arco di una ventina di punti, lo smusso di 18. La
lettura di sempre, per pieghe e bordi dritti, resta senza `curve`.
