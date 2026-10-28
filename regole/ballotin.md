# Regole: Ballotin

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Ballotin

Il ballotin e' la scatola a tronco di piramide rovesciato - piu' larga in
cima che sul fondo - con gli spigoli verticali fatti da **lenti** e due
coperchi che chiudono la cima stesi. Si dichiara **Cartotecnico in un pezzo**:
lo riconosce l'analisi prima del solutore astuccio, che lo risolverebbe, e
male - sul ballotin al frutto della passione una torre da 465 x 120,7 x 90 mm.
Il codice sta in `pack3d/ballotin.py`; costruisce in 14 s, rilievo compreso.

### La fustella si legge a facce

Le righe e le colonne del solutore astuccio qui non servono: i lati sono
obliqui e gli spigoli curvi. La fustella si legge come **grafo planare**: i
tratti delle penne del DT, spezzati dove un tratto arriva su un altro - su un
vertice o a meta' di un segmento - coi capi uniti entro 0,3 mm, i buchi del
disegno sotto i 2,5 mm chiusi e i rami morti potati; poi si percorrono le
facce una per una.

- **Le penne.** La principale la sceglie `strati.penne`, come per ogni DT, e
  da lei si prende il **colore**: tutti i tratti di quel colore e di spessore
  vicino sono fustella. Sul ballotin le finestre sono tagliate con penne da
  0,71 e 0,85 pt, cinque tratti in tutto, e nessuna soglia sul numero di
  segmenti le terrebbe.
- **Il tratteggio** - famiglie di segmenti paralleli a pochi millimetri - si
  toglie prima di fare il grafo, e serve dopo: ogni faccia sa quanti segni ha
  dentro, e una faccia tratteggiata e' una zona coperta o di colla.
- **I capi si uniscono per componenti connesse**, non al primo nodo vicino:
  un capo a 0,29 mm da due nodi li unisce tutti e due. Sul ballotin
  l'angolo del fondo si spezzava in due nodi, e una lente si fondeva col
  fronte.
- **Un tratto ripassato e' un tratto solo.** Due archi uguali fra gli stessi
  nodi hanno lo stesso angolo d'uscita, e l'ordine fra i due e' a caso: la
  cordonatura fra L1 e T1, con un pezzo disegnato due volte, non divideva
  piu' le due facce.
- **I buchi del disegno si chiudono.** Sul ballotin la cupola di L2 si ferma
  a 1,9 mm dal bordo da una parte sola; dall'altra c'e' il tratto che la
  chiude.
- **Un pezzo staccato dentro una faccia e' un suo buco** - una finestra
  chiusa su se stessa, un'ellisse di colla - e resta; quelli fuori dal pezzo
  principale - cartiglio, legenda, scritte fatte a tratti - se ne vanno.

### Cosa si riconosce

- il **fondo**: il quadrato con una lente a ogni angolo;
- la **colonna**: i due lati del fondo da cui le lenti partono in fuori.
  Sopra ciascuno, fra le sue due lenti, un trapezio largo in cima: il
  **fronte** e' quello che porta i **fianchi** - oltre le sue lenti, due ali
  grandi quanto lui, con la grafica - e il **retro** quello che porta due
  alette di colla, che a scatola montata stanno dentro i fianchi;
- i **coperchi** oltre la cima di fronte e retro, e oltre ciascuno la sua
  **linguetta**; le **alette** in cima ai fianchi, sulla loro cerniera;
- le **finestre**: le facce senza tratteggio chiuse dentro un pannello o fra
  un pannello e il suo coperchio.

Se manca qualcosa il pack non e' un ballotin come quelli che conosciamo, e
prova l'astuccio. Prima del grafo c'e' un prefiltro - quattro coppie di curve
con gli stessi due capi, una per spigolo - e su un astuccio la prova si ferma
li': sugli astucci del parco costa da 0,15 a 0,7 s, quasi tutti per leggere
le penne del DT. Dei tratti si leggono solo quelli del colore delle penne:
leggerli tutti, grafica compresa, costava secondi sui fogli grandi. Il verso viene dal fondo e dal fronte, mai dagli assi
della tavola: girato di 90, 180 e 270 gradi, il ballotin da' lo stesso
modello.

### Gli spigoli: la lente rientra nel pack

Una lente sono due cordonature curve che partono e arrivano negli stessi due
punti, l'angolo del fondo e quello della cima. La **corda** fra i due capi e'
lo spigolo del tronco, ma lo spigolo vivo c'e' solo ai due capi: piegata, la
lente **curva e rientra nel pack**, e lo spigolo e' una gola. Le facce si
fermano ciascuna sulla sua curva, a 7,4 mm dalla corda a meta' altezza, e fra
le due curve la lente fa in ogni sezione un arco lungo quanto e' larga stesa,
con la pancia verso l'interno: su 15 mm di lente e 10,5 di corda entra di 4,5
mm. Ai capi la lente non ha larghezza, e lo spigolo torna vivo. Sul ballotin
le lenti sono magenta piene: sul modello sono le quattro gole degli spigoli.

Le due curve della lente si mettono dove le mettono le mappe delle facce
accanto, cosi' i bordi combaciano senza fessure. Sul retro la curva dalla
parte dell'aletta e' la stessa del bordo dietro del fianco: si porta sul DT
del fianco, girata sulla corda, e si mappa col fianco. L'aletta, dentro, non
si vede. La prima versione aveva gli spigoli vivi, mezza lente per faccia: la
correzione e' venuta da chi il pack lo ha in mano.

Le misure vengono dalle corde: fondo 90, cima 114,6, fianchi 100 lungo la
pendenza, alto 99,1 mm. I fianchi sono un millimetro piu' bassi di fronte e
retro (99 contro 100 sul DT): le alette, che si chiudono sotto i coperchi,
partono un millimetro piu' in basso.

### La cima: chi sta sotto lo dice il tratteggio

I due coperchi si chiudono stesi e insieme non coprono la cima - sul
ballotin 43 + 61 mm su 115 - e il resto lo coprono le linguette. Quale
coperchio sta **sotto** lo dice il disegno tecnico: quello con la linguetta
**tratteggiata**, cioe' coperta. Sul ballotin e' L2, del retro, con T2 stesa
verso il fronte; sopra L1 con T1, il medaglione col marchio, steso su L2: si
legge dal fronte. Le alette dei fianchi si chiudono per prime e si vedono
nelle fessure ai lati, perche' i coperchi si stringono verso la linguetta (L1
da 114,4 a 97,8 mm). Gli strati si appoggiano uno sull'altro, a uno spessore
di cartoncino l'uno dall'altro: vedi *Niente feritoie*.

### Le finestre si vedono

Una finestra e' un buco nella maglia, e dentro si vede il rovescio del
cartoncino: la tinta neutra di `folding`, in **ombra** (tre quarti). Dentro
una scatola chiusa arriva poca luce, e un viewer senza occlusione ambientale
dipingeva l'interno chiaro come fuori: le finestre del ballotin sparivano
nel bianco della grafica. Sono quattro: le due smerlate su fronte e retro - le
praline vere dentro la coppa disegnata - e le due che girano lo spigolo fra
pannello e coperchio. Se chi carica il PDF la vuole, ognuna ha la sua
pellicola trasparente: vedi *La pellicola delle finestre si chiede, ogni
volta*. Nel parco il ballotin ce l'ha.

La texture e' il DT intero, pulito come quello di un pouch, e ogni faccia
della maglia prende la grafica dal suo posto sul DT: niente ritagli per
pannello, perche' le lenti stanno a cavallo di due facce.

### Niente feritoie

La prima versione aveva le feritoie: guardato di taglio, il modello lasciava
passare la luce. Tre cause, e per ciascuna una regola.

- **Gli strati della cima galleggiavano.** Alette, coperchio di sotto e
  coperchio di sopra stavano a quote fisse sopra il bordo, e niente li legava
  alle pareti: fra il bordo di una parete e il coperchio che ci si piega
  sopra restava una fessura lunga quanto la cerniera. Adesso gli strati si
  **appoggiano** uno sull'altro: le alette a uno spessore sopra il bordo, il
  coperchio di sotto a due, quello di sopra a tre (la linguetta di sotto lo
  tiene su). Su ogni cerniera c'e' la **piega**: una striscia nel piano della
  parete, dal suo bordo allo strato, col colore della cordonatura.
- **I bordi di taglio erano aperti.** Fra la faccia stampata e il rovescio,
  uno spessore piu' in dentro, non c'era niente, e di taglio si vedeva il
  fondo. Ogni bordo che non combacia per tutta la sua lunghezza con quello di
  un altro pezzo - entro un decimo di mm - prende la **costa** del taglio,
  nella tinta di `folding.TAGLIO`: finestre, tagli di coperchi, linguette e
  alette, i capi delle pieghe.
- **Sulle pieghe i rovesci non si toccavano.** Ogni rovescio si sposta lungo
  la normale del suo pezzo, e dove due pezzi si piegano uno sull'altro fra i
  due rovesci restava uno spessore di fessura: dentro, ma le finestre la
  mostrano. La chiude una striscia dal rovescio di un pezzo a quello del
  pezzo accanto.

Tre aggiustamenti chiudono anche gli angoli in cima: il fianco si appende al
suo angolo e non alla punta della lente, che sul DT sta 0,9 mm piu' su; i
coperchi si allargano come la cima del tronco, a cui la mappa porta la cima
di fronte e retro; il bordo della lente dalla parte del fianco si prende dal
bordo del fianco, davanti come dietro. E nella triangolazione una cornice di
punti attorno al poligono: senza, qhull lasciava fuori i punti allineati sui
lati dritti del contorno, che stanno sul guscio convesso, e il lato di 61 mm
del fondo restava un lato solo - dritto sul DT, non piu' dritto dopo la mappa,
e il pezzo accanto non lo ritrovava.

Misurato con la distanza di ogni bordo della maglia dal bordo di un altro
pezzo: prima 4,8 m di bordi stampati lontani piu' di un centesimo di mm da
ogni altro, dopo 1,4 mm in tutto, il piu' largo 0,07 mm. Dalle due finestre
in cima, che stanno in fila, si vede attraverso la scatola: e' vuota.

### Cosa manca

Le facce vere, piegate su due cordonature curve, si incurvano un poco, e il
modello le tiene piane; la gola della lente e' un arco di cerchio, che e' una
stima della forma vera. I marchi e le coppe dell'embossing sono in rilievo
(vedi *Il rilievo dell'embossing*), ma solo fuori: dentro il cartoncino
spinto in fuori fa un incavo, e il rovescio resta piano. Delle parti nascoste c'e' lo stretto necessario: T2
stesa sotto L1, e niente alette di colla del fondo e del retro. Il prodotto
non c'e': dalle finestre si vede l'interno vuoto.
