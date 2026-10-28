# Regole: Coppe e coni

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Coppe e contenitori conici

La coppa da gelato da 500 arriva in **due PDF**: il
contenitore (sleeve e fondo) e il tappo (corpo e anello). Si dichiara
**Cartotecnico in due pezzi**, un PDF ciascuno (vedi *Il cartotecnico dice di
quanti pezzi e' fatto*): l'ordine non conta, quale e' quale lo dice la pagina
(`server._pezzi_tondi`). Con lo sleeve solo - cartotecnico in un pezzo -
esce la coppa aperta, col tappo solo il tappo, e il primo cartellino lo dice.
Nella home non c'e' un pulsante della coppa: era un secondo modo di dire la
stessa cosa. L'API accetta ancora `coppa` come tipologia.
La costruzione e' `pack3d/coppa.py`; nel GLB la coppa e il tappo sono **due
nodi**, e il tappo si toglie. La texture e' una: l'atlante coi due stesi, una
zona per foglio (*La texture e' lo steso*).

Ogni PDF ha due disegni che dicono due cose diverse, e servono tutti e due:

| | dice | si legge da |
|---|---|---|
| lo **steso** in grande | dove sta la grafica | il settore anulare dello sleeve, il cerchio del corpo, il rettangolo dell'anello |
| la **vista montata** in miniatura | la forma | i tratti neri: altezza, bocca, fondo, ricciolo, rientro; la sezione del tappo |

### Lo steso

Lo steso e' un **settore anulare**. Il contorno va letto appiattendo le bezier
dal content stream (`cup.py`): ne' la silhouette rasterizzata ne' i punti che
pdfplumber espone per le curve vanno bene, i secondi includono i punti di
controllo.

```
r_bocca = R2 * alpha / 2pi     r_fondo = R1 * alpha / 2pi
apotema = R2 - R1              altezza = radice(apotema^2 - (r_bocca - r_fondo)^2)
```

Queste formule valgono per un cono che si chiude senza sormonto e con la
carta tutta sulla parete. Lo sleeve vero ha il bordo arrotolato in cima, il
risvolto sotto il fondo e il lembo incollato sul lato: sulla coppa da 500 danno
un'altezza di 122,9 mm contro i 106 della coppa montata. **Lo steso non dice
la forma: la dice la vista montata.**

- Su `fit_sector` guardare **due numeri**, non uno. Residuo basso non basta se
  lo scarto fra gli angoli dei due archi e' alto: 0,001 mm con 14,5 gradi di
  scarto significa cerchio adattato al pezzo sbagliato di contorno. Sulla
  coppa da 500 i tratteggi del DT passano con 0,020 mm e 9,5 gradi; il taglio
  vero con 0,564 mm e 0,8 gradi, perche' ha gli spigoli arrotondati. Si guarda
  prima lo scarto (`coppa.leggi_steso`).
- I **lati di taglio** sono due rette, misurate lontano dagli spigoli; non
  passano esattamente per il centro, e la carta fra i due si misura arco per
  arco (`Steso.arco`).
- La **piega del fondo** e' l'arco concentrico del DT piu' vicino al taglio di
  sotto: 424,15 mm sulla coppa da 500, sopra la fascia neutra del risvolto. Senza
  quell'arco la parete parte dal taglio e il cartellino lo dice.

### La vista montata: la scala dai cerchi gemelli

Le quote della vista montata sono vettorializzate - le legge solo un occhio -
ma i tratti no. Manca solo la scala, e la danno **i cerchi del fondo**, che il
foglio disegna in grande e in miniatura: il rapporto fra i due e' la scala, e
deve tornare su OGNI anello entro lo 0,4% (`coppa.gemello`). Sulla coppa da 500
87,5 / 72,5 / 67,2 mm tornano a 1:8,169; sul tappo il corpo da 104,14 a
1:4,26. Misurata cosi', la miniatura rende le quote scritte:

| | quota scritta | misurata sui tratti |
|---|---|---|
| altezza | 106 ± 0,38 | 105,96 |
| bocca | 96,2 ± 0,25 | 96,17 |
| fondo | 73,3 | 73,29 |
| ricciolo | 3,81 ± 0,25 | 3,81 |
| rientro del fondo | 8,29 ± 0,2 | 8,30 |
| gonna del tappo, dentro | 96,1 ± 0,6 | 96,13 |
| altezza del tappo | 15,71 ± 0,5 | 15,71 |

Le pareti si riconoscono perche' pendono come il cono che lo steso impone e
sono simmetriche; il resto della miniatura - cartiglio, legenda, quote - non
ha due rette cosi'.

Le viste montate si leggono DRITTE, quindi un foglio girato sulla tavola si
gira prima di leggerlo (`coppa.orienta`), come gli astucci. Lo sleeve il verso
lo dice da se': la bocca sta sopra, dalla parte opposta al centro degli
archi. Il tappo si prova girato finche' la sezione si trova col piano nella
meta' alta. Coi due fogli girati di 90, 180 e 270 gradi il modello esce
identico: vertici a 0,0 mm, colori sui vertici identici.

### La grafica sulla coppa senza stirarla

La coppa e' il solido di rivoluzione del profilo misurato. Ogni altezza della
parete prende l'arco dello steso che sta alla **stessa distanza dalla piega**,
e lungo quell'arco **tanta carta quanta e' la circonferenza** della coppa li'
(a mezzo spessore), a partire dal taglio sinistro. Quello che avanza e' il
sormonto incollato sotto il lembo: **non si impone, si misura**, e deve
tornare con la riga che il DT disegna lungo il taglio destro. Sulla coppa da 500
avanzano 8,6 mm al fondo e 7,7 alla bocca, e il DT ha la riga del lembo a
8,05: torna. Torna anche il cono: la parete della miniatura pende 4,98 gradi,
lo steso ne svolge 4,90.

### Il bordo arrotolato e' bianco fuori

In cima allo steso il DT ha 8,5 mm di **fascia neutra**: niente inchiostro,
perche' la carta li' si arrotola. Si arrotola verso fuori partendo dal lembo,
quindi la fascia neutra finisce al CENTRO del rotolo, e il giro che si vede e'
l'ultimo, quello attaccato alla parete. Lungo quel giro la carta sale dal lato
interno, passa sopra e scende fuori: il marrone della fascia alta copre il
lato interno e la cima, e **il fuori del bordo resta bianco**. Mappato nel
verso sbagliato - dalla parete verso fuori - il bordo usciva marrone fuori e
bianco dentro. Col tappo chiuso il bordo non si vede: conta a coppa aperta.

### Il fronte e' il marchio, non la mezzeria

Il fronte si ancora alla grafica, non alla mezzeria geometrica del settore:
**il gruppo piu' grande di colori vivi**, con i buchi fra lettere vicine
chiusi entro 4 mm (`coppa.fronte`). E' il marchio, con la scritta NEW, a +6,8
gradi dalla mezzeria dello steso. Il baricentro di TUTTI i colori vivi lo
tirava verso il box del formato, 20 mm a sinistra, e il marchio usciva
spostato a destra. Il marrone delle fasce gira tutto attorno e non conta: i
colori vivi sono quelli che hanno almeno 115 livelli fra il canale piu' alto
e il piu' basso.

### Il tappo

- **La sezione e' l'unico posto che dice com'e' fatto il tappo montato**: la
  gonna, la nervatura che si aggancia sotto il bordo della coppa, il gradino,
  il ricciolo che stringe il corpo, il piano incassato. Le orizzontali nere
  della sezione sono gli spigoli del giro visti di fronte, e **la piu' lunga
  e' l'interno della gonna**: e' su quella che il DT scrive Ø96,1. Il profilo
  esterno e' il nero piu' a sinistra a ogni altezza; il piano e' la riga
  rossa del corpo.
- Il **piano** si apre sulla cordonatura del corpo appena dentro la gonna:
  Ø88,5 sulla coppa da 500.
- Il tappo **poggia col piano sul sommo del bordo**: e' cosi' che la
  nervatura cade subito sotto il ricciolo. Il pack chiuso e' alto 112,2 mm.
  La verifica dice se la gonna calza sulla bocca: 96,13 dentro contro 96,17.
- L'**anello** e' il rettangolo del DT alto quanto la gonna: 97,4 x 15,7.
  La sua stampa e' casuale - il DT lo scrive - e sul modello il motivo si
  ripete attorno, quattro volte, e sul retro si interrompe.

### Senza dichiarazione la coppa si prova per ultima

Dichiarata, la coppa non passa da nessun altro solutore. Senza dichiarazione
si prova solo quando tutto il resto ha fallito, cosi' gli altri pack non ne
pagano la lettura e non possono esserne scambiati: prima il ripiego flowpack
la rifiutava dopo 170 secondi con "saldature di testa non riconosciute".

## Il cono gelato col lid

Il cono gelato T1 macaron e' un cartotecnico in **due
pezzi**: lo steso del cono e il lid, il disco che lo chiude, ognuno nel suo
PDF. Si dichiara come la coppa, e la costruzione e' in `pack3d/coppa.py`
(`leggi_cono`, `leggi_disco`, `costruisci_cono`); nel GLB il cono e il lid
sono due nodi, con una texture sola: l'atlante coi due stesi (*La texture e'
lo steso*). Il DT del cono sta sulla lastra **TROQUEL**, che e' la
fustella in spagnolo: senza quel nome in `techink` il DT finiva nella
grafica.

### Lo steso: un settore pieno, con l'apice sul foglio

Lo steso del cono non e' un settore anulare: l'arco e' uno solo, e il suo
centro - l'apice - sta sul foglio. Il taglio e' il tracciato chiuso che ha:

- un **arco** che passa per piu' contorno di qualsiasi altro cerchio:
  R 172,88 mm sul cono, apice a (588,20; 826,99) pt, scarto 0,18 mm. I
  cerchi di prova passano per tre punti presi a passi fissi: la stessa
  pagina da' sempre lo stesso arco (`_arco_grande`);
- il **lato radiale**, una retta che passa a 4 mm al piu' dall'apice e arriva
  all'arco: sul cono passa a 2,0 mm, ed e' una bezier quasi dritta, 0,6 pt
  fuori corda (`_rette` le prende entro un punto);
- il **lembo**: l'altro lato lungo, parallelo all'ultimo raggio e scostato
  quanto il lembo e' largo - 22,0 mm - con una linguetta.

Il contorno dell'abbondanza della grafica ha lo stesso apice: dei due il
taglio e' quello dentro. Il raggio che chiude il cono e' l'**ultimo taglio**
del DT ("last cutting of cone"), un pieno sottile del colore del taglio a R
169,33 +- 0,4: e' la bocca, e la fascia di 3,5 mm fino al taglio e' il
risvolto (vedi sotto).

### La forma dal disegno 1:1

Accanto allo steso il DT disegna il cono montato **in scala 1:1**: due rette
lunghe uguali che convergono con l'angolo del cono (`_disegno_cono`). Ai capi
larghi distano la bocca, a quelli stretti la punta: 64,40 e 2,00 mm, alto
160,51, apotema 163,51, 22,0 gradi - le quote scritte, che sono
vettorializzate, tornano tutte. La riga della quota dell'apotema e' parallela
a un lato e con l'altro fa lo stesso angolo: la si scarta perche' la sua
"bocca" non e' quella che l'ultimo taglio arrotolato da'. Riscontri:

| | disegno | steso |
|---|---|---|
| angolo del cono | 22,0 | 21,8 svolti alla bocca |
| bocca | 64,4 | 64,1 dall'ultimo taglio |
| sormonto | lembo largo 22,0 | 21,2 mm avanzano al giro |

Senza il disegno la forma viene dallo steso - bocca all'ultimo taglio, punta
dove la carta arriva all'apice - e il cartellino lo dice.

### Quale lato sta sopra: lo dice la colla

La colla non tiene sull'inchiostro: il lato che va **sotto** ha lungo il
taglio una fascia di carta non stampata. Sul cono e' lungo il lato radiale,
larga 12,0 mm per tutta la lunghezza, e il sormonto di 21,2 la copre: il
radiale va sotto, e **sopra resta il lembo**, quello con la linguetta, da cui
il cono si sbuccia (`lato_sopra`). Con il radiale sopra - la prima prova - la
fascia bianca usciva come una striscia lungo il retro del cono. Senza una
fascia su un lato solo resta sopra il radiale, e si dichiara.

Il bordo del lembo e' parallelo all'ultimo raggio, non e' un raggio: sul cono
**gira attorno**, 37 gradi dalla bocca a meta' altezza e sempre piu' stretto
verso la punta, con lo scalino della linguetta. E' la cucitura vera.

### La grafica sulle generatrici

Le generatrici dello steso - i raggi dall'apice - vanno sulle generatrici del
cono: l'angolo dello steso e quello del cono stanno in un **rapporto fisso**,
e alla bocca un giro del cono e' tanta carta quanta la sua circonferenza. La
carta che si vede e' un giro che comincia all'orlo, **riga per riga**
(`orli`): la cucitura segue l'orlo del lembo, e le righe del modello si
infittiscono dove l'orlo gira in fretta (`Maglia.falda`). Ancorare ogni riga
all'orlo senza il rapporto fisso - come sulla coppa, dove il lato di sopra e'
un raggio - torceva la grafica con la cucitura: 37 gradi attorno al cono fra
la bocca e meta' altezza. Con una griglia polare al posto della grafica i
raggi escono dritti e gli archi orizzontali.

### Il risvolto accoppiato

Il cono si chiude **a risvolto**: la fascia fra l'ultimo taglio e il taglio
piega dentro sul lid e lo tiene chiuso. Sul modello e' un anello in piano
alla quota della bocca, stampato sopra - e' la stessa carta della parete, e
la grafica continua - e il lid ci sta **sotto**: piegato, il risvolto arriva
a 28,9 mm dal centro e il lid ne ha 30,5, lo tiene per 1,7 mm e se ne vede un
disco di 57,7. Il riscontro lo dice, e se il risvolto non arriva al lid
l'anello che resta e' bianco e il cartellino dice NON TORNA. Senza il lid il
risvolto resta dritto sopra la bocca, com'e' prima della chiusura.

### Il lid

Il lid e' un disco: il gruppo di cerchi concentrici piu' grande della pagina
(`leggi_disco`). Il cono ne disegna tre - abbondanza, taglio, area di
sicurezza: 67, 61 e 51 mm - e l'abbondanza e' il cerchio di fuori se il
secondo le sta da 1,5 a 3,2 mm dentro. Un disco da solo non dice di essere un
lid: si cerca solo fra piu' PDF (`orienta(dischi=True)`). Il sopra del
foglio va dietro: guardando il cono dal davanti e dall'alto il lid si legge
dritto.

### Il fronte senza il fondo giallo

Il fronte e' il marchio, come sulla coppa, ma sul cono il colore vivo piu'
esteso e' il **fondo giallo**, due terzi dello steso: un colore vivo che copre
piu' del 30% della carta e' fondo, e si toglie prima di cercare il gruppo piu'
grande (`FONDO_VIVO`). Resta il marchio, a +4,9 gradi dalla
mezzeria dello steso.
