# I gadget: le regole

Un **gadget** e' un oggetto promozionale - un premio, un omaggio - fatto in
3D e renderizzato: un dispenser di vetro col rubinetto, una tazza, una
borraccia, un barattolo. Non e' un pack e non si piega da una fustella: per
questo **un gadget spesso non ha un DT**. Le informazioni che arrivano sono
immagini, testo, a volte un file di misure, e spesso immagini esempio che
**non rispecchiano in pieno il prodotto finale** (un oggetto simile, un
render del fornitore, una foto ambientata presa altrove).

La categoria **non e' ancora nella pagina** (nessuna domanda, nessun posto
per i file) e non entra nella coda dei casi (CODA.md, *Cosa si risolve*):
queste regole vengono dal primo gadget lavorato a mano, un dispenser di
vetro da circa 3 litri col tappo a vite e il rubinetto, in tre varianti
(succo d'arancia; acqua con limone e menta; vuoto) e due viste (frontale e
dall'alto). Valgono per i gadget che verranno, finche' un caso non mostra
che vanno cambiate: allora si cambiano qui, col caso che lo mostra.

## Le fonti, e quale comanda

Senza DT le fonti sono tante e dicono cose diverse. Ognuna decide **solo**
quello che sa:

| | fonte | decide | non decide |
|---|---|---|---|
| 1 | **misure scritte** da chi ha il campione in mano (un file di misure, quote scritte sulle foto) | le dimensioni | - |
| 2 | **foto del campione con un riferimento** nella stessa foto (un righello accanto, una misura nota) | forme e proporzioni, misurate in scala (*Misurare da una foto*) | colori e materiali esatti: cambiano con la luce |
| 3 | **vettoriale del marchio** (PDF, AI, SVG) | il disegno di loghi e scritte, ® compreso | quanto sono grandi e dove stanno: lo dicono le misure |
| 4 | **testo** di chi chiede | cos'e', il contenuto, le varianti, l'uso del render | le misure, se non le scrive |
| 5 | **immagini esempio** (prodotti simili, ambientazioni, render altrui) | stile, materiali, atmosfera, inquadratura | **misure e forme**: non sono il prodotto |

- **Una misura non si prende mai da un'immagine esempio.** La prima spalla
  del dispenser veniva da una foto ambientata di un dispenser simile: lunga e
  spiovente, curvava gia' da 11 cm. La foto del campione col righello la
  mostrava dritta fino a 12,3 cm e poi tonda e piena, stretta in fretta sotto
  il tappo.
- **Un logo non si ricalca da una foto.** Ricalcata dalla foto, la «a» del
  marchio veniva deformata: la prospettiva e la lente del vetro curvo.
  Dal vettoriale e' giusta, ® compreso. Se il vettoriale non c'e', si chiede.
- **Le fonti che non tornano si dicono**, con i numeri, e vince quella piu'
  in alto nella tabella. Mai una media.

### Le deviazioni volute

Una richiesta che si allontana dalle misure («facciamolo piu' alto»,
«stringi il tappo») e' una **deviazione voluta**: si fa, e si scrive nel
registro del caso con la frase, la data e il numero (+3 cm; tappo 11 invece
di 12,3). Quando poi arrivano misure nuove, o si verifica, la deviazione
compare nella tabella come tale - non come errore - e **si chiede quale
vince**: non si sceglie da soli. Sul dispenser le misure del campione sono
arrivate dopo il +3 cm e il tappo stretto, e chi le ha mandate ha scelto le
misure.

## Cosa chiedere subito

Un gadget non ha un DT che risponda da se'. Le domande si fanno **prima di
modellare**, tutte insieme, con quello che manca dalle fonti (come la
scatola a punta, FORME.md: una domanda all'inizio evita le versioni dopo):

- **altezza totale** e **ingombro massimo** (larghezza), e la **sezione**:
  tonda o ovale, e la profondita'. Dal davanti non si vede;
- le misure di **ogni pezzo che si monta**: del tappo diametro e altezza; del
  rubinetto l'altezza, quanto sporge, la leva;
- il **marchio**: a che altezza dalla base, quanto e' alta una lettera di
  riferimento (la «t» va bene: e' la piu' alta fra le minuscole senza
  asta), da che parte; e se ce n'e' uno anche sul tappo, con le sue distanze
  dai bordi;
- **due foto del campione**, una di fronte e una di lato, con un righello
  accanto e alla stessa distanza dalla camera dell'oggetto;
- il **vettoriale** del marchio;
- **materiali e finiture**: vetro, metallo lucido o satinato, plastica
  opaca; i colori;
- il **contenuto** e le **varianti**: pieno di cosa, quanto pieno, vuoto;
- le **parti mobili** (una leva su o giu', un tappo aperto o chiuso);
- **l'uso del render**: ambientato o scontornato su sfondo trasparente, la
  vista, il formato e la risoluzione, il PSD a livelli.

## Il registro del caso

Ogni gadget ha la sua cartella nel repository privato (`pack3d-casi`), mai
in questo: qui non vanno foto, PDF, viste o nomi di clienti, e il caso si
chiama col suo codice. Nella cartella:

- le fonti come sono arrivate (foto, file di misure, vettoriali, immagini
  esempio), senza toccarle;
- `misure.md`: una riga per misura - elemento, misura, fonte, modello, esito
  - e sotto le **deviazioni volute** (*Le fonti*) con la frase che le ha
  chieste;
- le decisioni prese a occhio, con il perche' (la leva a 30 gradi, il
  livello del liquido, la profondita' quando nessuno l'ha data);
- i file da consegnare (*I render*).

## Misurare da una foto

Quando le misure scritte non bastano - una curva, un raccordo, una forma -
si misurano sulla foto del campione col riferimento:

- **la scala** viene da una misura nota nello stesso piano dell'oggetto:
  il righello accanto, l'ingombro massimo. Due scale - in larghezza e in
  altezza, da due misure note - devono tornare entro il 2-3%: se non
  tornano, la prospettiva conta e la foto vale meno;
- **si misura il contorno**, riga per riga, sui due lati; dove lo sfondo
  stacca bene vale di piu'. Il dispenser: il contorno destro, su fondo
  scuro, ogni 10 pixel della foto, con la scala dal righello da 19,5 cm e
  dalla larghezza di 16;
- la camera di una foto fatta a mano sta quasi sempre **piu' in alto** del
  centro dell'oggetto: quello che guarda in su (spalle, tappo) si accorcia.
  La precisione realistica e' di un millimetro;
- **il controllo** e' il render accanto alla foto, alla stessa altezza
  dell'oggetto: il profilo deve tornare a colpo d'occhio, e coi numeri
  entro mezzo millimetro.

## Il modello

- **I profili di rivoluzione** (o ovali) si fanno da punti di controllo con
  una spline: i punti **a passo regolare**, uno ogni mezzo centimetro circa,
  anche sui tratti dritti. Due punti a 4 cm l'uno dall'altro accanto a due a
  mezzo centimetro fanno tornare la curva indietro su se stessa: sul
  dispenser era un gradino di 0,2 mm all'attacco della spalla, invisibile
  col succo e una riga netta nel vetro vuoto.
- **Dove un tratto dritto incontra una curva**, la curva parte in tangenza.
  Vale anche quando un pezzo si allunga (+3 cm inseriti nel fianco dritto):
  il taglio va dove il profilo e' dritto, o resta uno spigolo.
- **Il controllo del profilo**, a ogni modifica: l'altezza sempre crescente
  lungo la sagoma (niente ripiegamenti), niente sporgenze oltre la misura
  massima, e lo spessore della parete costante dove deve.
- **Un pezzo che sta dentro un altro ha il suo gioco**: il collo del vetro
  passa sotto il bordino del tappo, mai attraverso.
- **I liquidi** entrano di poco nella parete del vetro: un velo d'aria fra
  vetro e liquido, in un path tracer, fa riflessione totale e il vetro
  diventa argentato. I volumi sono chiusi.
- **Le parti mobili** hanno una posizione scelta e scritta nel registro (la
  leva del rubinetto a 30 gradi: e' quella in cui l'altezza del rubinetto e
  la sporgenza della leva tornano insieme con le misure).
- **Il logo in rilievo** viene dal vettoriale, alto e messo come dicono le
  misure; il bordo delle lettere e' arrotondato, non a gradino.

## La verifica: si misura il modello, non il render

Dopo ogni modifica della geometria **si misura il modello esportato** (il
GLB), con uno script, e si riempie la tabella del registro: altezza totale,
ingombro, tappo (diametro, altezza, inizio), marchio (distanza dalla base,
altezza della lettera di riferimento), rubinetto (altezza, sporgenza, leva
dal perno), le distanze del logo sul tappo dai bordi. La tolleranza e' mezzo
millimetro sulle misure scritte, un millimetro su quelle prese da foto.

- La tabella elenca **tutte** le misure, anche quelle che tornano, e le
  deviazioni volute col loro perche'.
- Due misure che non possono tornare insieme per le proporzioni del logo (la
  «t» alta 2 cm e la scritta a 2 cm dai bordi del tappo) si avvicinano tutte
  e due e si dice di quanto (1,98 e 2,00).
- **Il vuoto mostra tutto**: a ogni modifica della forma si guarda anche la
  variante senza contenuto, ingrandita sui bordi del vetro. Il liquido
  nasconde i difetti della parete.

## I render

- **Anteprime a bassa risoluzione** (800 x 1000) si fanno liberamente per
  ogni prova. **Il render in HD si fa solo dopo la conferma** di chi l'ha
  chiesto: sulla CPU sono ore.
- Le **varianti** (i contenuti) e le **viste** stanno sullo stesso modello e
  con le stesse luci; ambientato e scontornato sono due modi della stessa
  scena, non due scene. Cambiare la vista non cambia la scena: si gira la
  camera; girare l'oggetto si fa a parte, e si dice quale dei due.
- **Riflessi sul vetro**: le luci non si specchiano (fanno rettangoli
  bianchi); si specchiano solo finestre finte tenui, invisibili alla
  camera; il metallo ha luci sue (light linking).
- **Il vetro vuoto** non ha lo scurimento del fondo che imita l'ombra del
  contenuto, e dietro un vetro vuoto non si mette niente: si vede, scuro,
  attraverso.
- **Lo scontornato** (sfondo trasparente, senza ombra): il vetro e' trasparente
  anche nell'alfa, comprese le lettere appena satinate; l'ambiente e' uno
  studio chiaro e quasi uniforme - quello dell'ambientato e' scuro sotto
  l'orizzonte, coperto da tavolo e parete, e senza di loro fa aloni neri
  sui bordi - e nei riflessi e' piu' chiaro che nella luce che da' alla
  scena; niente finestre finte; piu' rimbalzi, per il vetro spesso del
  fondo.
- **La consegna dell'HD**: un `.blend` per variante e vista, autosufficiente
  (texture dentro), con nomi senza spazi, da renderizzare su una GPU (un
  notebook Colab che li trova tutti nella cartella). Prima di consegnarlo,
  un render ridotto del `.blend` accanto all'anteprima approvata: la
  differenza media deve stare sotto 2/255.
- **Il PSD** per la post produzione: il render intero in fondo e sopra un
  livello per materiale con la sua maschera di livello (vetro, tappo,
  rubinetto, contenuto, frutta, tavolo, parete). Le maschere si fanno con la
  stessa camera, ogni materiale bianco o nero; il vetro, quando non e' lui
  il gruppo, e' del tutto trasparente, cosi' la maschera di quello che sta
  dentro copre anche quello che si vede attraverso.

## Cosa manca

- **La pagina**: la categoria, le domande di *Cosa chiedere subito*, un posto
  per ogni fonte.
- **Il codice**: il modello del primo gadget (profilo di rivoluzione, tappo a
  vite col logo, rubinetto, contenuti) e la misura del GLB sono script del
  caso, non moduli. Diventano `pack3d/` quando arriva il secondo gadget e si
  vede cosa hanno in comune.
- **Un caso solo**: queste regole vengono da un oggetto di vetro di
  rivoluzione. Una tazza con il manico, una borraccia, un oggetto che non e'
  di rivoluzione aspettano il loro caso.
