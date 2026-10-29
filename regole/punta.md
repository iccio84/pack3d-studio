# Regole: La scatola a punta

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## La scatola a punta

Una scatola in un pezzo che in cima non ha cielo: fronte e retro salgono
dritti, poi si inclinano uno verso l'altro e si toccano, come il tetto di una
casetta. I fianchi rientrano a soffietto fra le due falde, e un'aletta oltre
la cima scende sul retro e ci si incolla. Si dichiara **Cartotecnico in un
pezzo**; il codice sta in `pack3d/punta.py`.

Il primo caso e' arrivato dalla coda (852ecafec7) come costruzione ferma: il
solutore astuccio la rifiutava, e faceva bene. Lungo la colonna del corpo le
fasce erano 32 | 3,4 | 169,6 | 5,0 | 23,3 | 28,2 | 140 | 26 | 3 mm: niente
cielo, e il retro spezzato in tre dall'area di colla dell'aletta. Non e'
ne' un astuccio chiuso ne' uno aperto.

### La firma in fustella

Si prova **solo dopo** che l'astuccio ha rifiutato la fustella, e solo se il
pack e' dichiarato cartotecnico: gli astucci non pagano la prova e non ne
possono essere scambiati. Deve tornare tutto:

- **il fronte** e' la fascia piu' alta con un fianco per parte, larghi uguali
  (entro 1,5 mm o l'8%) e di almeno 10 mm;
- **la piega del soffietto**: una cordonatura orizzontale, una sola, che
  attraversa tutti e due i fianchi (60% della larghezza) e non il corpo
  (meno del 30%), nella fascia del fronte lontano dai capi. Sul primo caso e'
  tratteggiata a 102 mm dal piede, e i tratti corti non entrano nella
  griglia `d.ys`: si legge dalle cordonature stesse. **La cima e' il capo del
  fronte piu' vicino alla piega**: cosi' la scatola si legge anche col foglio
  capovolto;
- **oltre la cima** al massimo due fasce: la cresta (fino a 6 mm, una doppia
  cordonatura: 3,4 sul primo caso) e l'aletta (almeno 8 mm), poi il foglio
  finisce;
- **oltre il piede** il fondo e poi il retro, alto come il fronte (entro
  3 mm o il 3%) fino alla fine del foglio: le cordonature dell'area di colla
  dentro il retro non contano. Il fondo e' lungo fra 0,8 e 1,5 volte la
  profondita';
- **la falda** - la parte del fronte sopra la piega - deve poter chiudere mezza
  profondita' meno la cresta, e l'aletta starci sopra;
- **il soffietto**: sopra la piega, su ognuno dei due fianchi, almeno tanti
  mm di cordonature oblique quanto e' lunga la falda. Sul primo caso 95 mm per
  fianco contro 67,6 di falda: le due gambe della V. E' questo che distingue
  una scatola a punta da una scatola con una piega qualunque sui fianchi.

### Il solido

Dritta per l'altezza dal piede alla piega (102 mm); sopra, le falde
(67,6 mm) chiudono `(D - cresta) / 2` di profondita' ciascuna e salgono di
`sqrt(falda^2 - ((D - cresta)/2)^2)`, 63,1 mm sul primo caso: 131,5 x 166,2 x
45,3 mm. In cima la cresta fa da colmo; l'aletta scende sul retro, uno
spessore fuori, per la sua lunghezza. I fianchi sono dritti fino alla piega.

**Sopra la piega il fianco rientra.** La prima versione lo teneva piano, un
trapezio dalla base alla cresta, e chi aveva il pack in mano l'ha detto
subito: "il laterale deve rientrare", con la foto. Il triangolo fra le due
gambe della V - la base sulla piega, la punta in cima al fianco - si spinge
dentro fino alla cresta, di `(D - cresta) / 2` (20,9 mm sul primo caso), e i
due spicchi fra la V e i bordi del fianco si piegano verso di lui.

**Rientra, e poi sale.** La seconda versione portava il triangolo dritto
dalla piega alla punta, e la gola restava quasi a filo; la terza teneva fronte
e retro dritti 29 mm sopra la piega dei fianchi, una stima presa dalla foto, e
chi aveva il pack l'ha corretta: il soffietto deve cominciare a piegarsi dove
si piega il fronte, rientrare e poi salire fino alla chiusura. Fronte, retro e
soffietto si piegano quindi tutti alla stessa altezza, la piega dei fianchi.

**Un piano solo, come il fianco di un cartone del latte.** La quarta
versione, fatta dalla routine, leggeva i due **tagli a 45 gradi** che dagli
angoli della piega arrivano sulle gambe della V (10,2 mm dentro dal bordo,
10,1 mm sopra la piega) come il bordo di un **ripiano** piatto: il fianco
andava dentro in orizzontale per 10 mm e solo li' il triangolo saliva. Di
tre quarti si vedeva uno scalino, con una tasca scura, e chi ha il pack l'ha
detto con due foto: il soffietto non e' cosi'. Sulla fustella, fra la piega e
la fine dei tagli, non c'e' nessuna cordonatura: un ripiano non ha dove
piegarsi. E sopra la piega i bordi del fianco sono **tagli**, non
cordonature: il fianco li' e' staccato dal fronte e dal retro e resta
attaccato solo alla piega.

Quindi il soffietto sono tre pezzi. Il **pezzo centrale** - fra la piega, i
tagli e le gambe della V - gira intero sulla piega e si inclina dentro fino
alla punta sotto la cresta, in un piano solo, inclinato di
`asin(chiude / falda)` (18 gradi sul primo caso: la punta va dentro di
20,9 mm salendo di 64,3). E' largo quanto il fianco alla piega, si stringe
lungo i tagli e poi lungo le gambe della V: le gambe partono dalla **fine dei
tagli**, non dagli angoli (`punta._tagli` segue la catena di tratti dritti da
ogni angolo). Le due **ali**, fuori dalle gambe, girano sulle gambe e
riempiono lo spazio fino al bordo delle falde, contro il loro rovescio, con la
**stampa verso il soffietto**: guardando la scatola dall'alto, nella foto, fra
la gamba della V e il bordo della falda di dietro si vede la stampa dell'ala,
in ombra, fino alla cresta. Un'ala rigida con il bordo libero sul bordo
della falda e l'altro lato sulla gamba della V ha le misure del foglio a uno
o due mm: il cartoncino si incurva appena, e il modello fa l'ala a strisce.

La quinta versione aveva il pezzo centrale a triangolo dagli angoli alla
punta e le ali dagli angoli: di tre quarti andava, ma dall'alto il pezzo
centrale era troppo largo e le ali erano solo una striscia. Una prova con le
ali girate verso l'interno, rovescio in vista, non torna con la foto: in cima
al soffietto si vede stampa, non cartone.

**La piega del fronte e' smussata.** Sul DT il fronte non ha cordonatura
all'altezza della piega dei fianchi, e li' passa il marchio: lo spigolo lo
tagliava a meta' con un segno netto. Chi ha il pack ha chiesto di ammorbidire
solo quella piega, "come se curvasse senza lasciare il segno". E' un arco di
`SMUSSO` (20 mm di raggio) tangente al fronte dritto e alla falda, che
restano dove sono: la forma non cambia, lo spigolo rientra di 0,25 mm. Sul
foglio l'arco prende i 3,2 mm prima e dopo la piega. Il retro e tutte le
cordonature vere - gli angoli, la piega dei fianchi, le gambe della V, la
cresta - restano spigoli. Una prova con fronte e retro curvi per un terzo
della falda cambiava la pendenza e l'altezza: non era quello che serviva.

**Il cartoncino ha spessore.** Oltre al rovescio, ogni bordo che non combacia
con quello di un altro pezzo prende la **costa** del taglio, come
nell'astuccio e nel ballotin: i bordi delle falde e delle ali lungo il
soffietto, la cresta, l'aletta, i tagli a 45 gradi. Quanto e' spessa la dice
lo spessore dichiarato nella pagina (1-3); chi ha il pack ha chiesto il
cartone spesso, e nel parco la scatola a punta T6 e' col livello 3, 0,7 mm.

**L'aletta sta appoggiata sul retro.** Dal disegno non si capiva se stesse
dritta in su, come la cresta di un cartone del latte, o piegata su una
faccia: e' stata la prima domanda fatta in Glam, e chi aveva il pack in mano
ha risposto "piegata giu', appoggiata sul retro", con la foto. Lo conferma la
fustella, con l'area di colla in cima al retro lunga quanto l'aletta.

**Il fondo e' piatto.** La sua fascia e' un soffietto - 56,5 mm stesi per
45,3 di profondita', con una cordonatura in mezzo - e montato si appiattisce;
sul modello la sua grafica e' portata alla profondita' della scatola.

La texture e' il DT intero, come per il ballotin (`ballotin.con_interno`):
ogni pezzo della maglia prende la grafica dal suo posto sul foglio, e il retro
stampato capovolto esce dritto da se'.

### Cosa manca

Il pezzo centrale del soffietto e' piano, e le ali sono a strisce: il
cartoncino vero si incurva un poco anche li'. Anche il retro, che sul DT non
ha cordonatura alla piega, resta a spigolo. Non sono modellate le alette di
colla del retro e del fondo, che stanno dentro. Gli angoli arrotondati dell'aletta restano squadrati.
