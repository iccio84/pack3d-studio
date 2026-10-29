# Regole: Il tubo a cono

Una parte di REGOLE.md, che ha i principi, le domande all'utente e l'indice
di tutte le sezioni.

## Il tubo a cono

Uno sleeve di cartoncino arrotolato in un cono lungo e stretto, aperto in
cima, col fondo schiacciato e saldato piatto: il tubo di un gelato da
spremere. Un pezzo, cartotecnico (`pack3d/tubo.py`, `server.build_tubo`).
E' nato dal caso 84c854d6a5: dichiarato cartotecnico in un pezzo, il solutore
astuccio lo rifiutava («la sequenza delle fasce non e' ne' quella di un
astuccio chiuso...», fasce 331, 15, 15, 24...), la scatola a punta e la coppa
non lo prendevano, e il caso finiva in errore. Chi l'ha caricato: «la parte
bassa e' saldata/incollata, poi sale e prende forma di un cono allungato;
il PDF e' uno sleeve come il cono gelato».

Si prova dopo l'astuccio, dopo la scatola a punta e dopo la coppa
(`server.RICONOSCIMENTO`): i casi che quelli prendono non cambiano strada.

### La firma in fustella

In uno stile di tratto (penna e colore) solo, tutte vere:

- un centro, dagli archi curvi (freccia di almeno 0,8 mm);
- due rette lunghe almeno 80 mm che puntano al centro entro 3 gradi - il
  lato della pattina e' parallelo al raggio, scostato di qualche mm - coi
  capi a due raggi uguali entro 6 mm: il fondo e la bocca;
- un tratto curvo a ciascuno dei due raggi (la mediana dello scarto entro
  3 mm): gli archi possono essere spezzati in piu' tratti;
- l'arco del fondo lungo almeno 20 mm (due lati dello stesso fianco no);
- il lato lungo almeno 1,2 volte il diametro della bocca: piu' tozzo e' una
  coppa.

Se i contorni sono due, uno dentro l'altro nella stessa penna - sul
84c854d6a5 l'abbondanza di stampa a 2 mm fuori dal taglio - il taglio e'
quello dentro: la coppia di lati piu' stretta.

### Il solido

Con Phi l'angolo del settore, p la pattina e rho il raggio sul foglio, il
giro del tubo e' C(rho) = rho Phi - p, il raggio C / 2 pi, l'altezza
(rho - R_base) sqrt(1 - (Phi / 2 pi)^2), dal fondo rifilato (sotto). Sul
84c854d6a5: lati 197 mm, archi 122,6 e 60,6; montato alto 178,4, bocca
36,2, fondo 18,3.

- La **pattina** la scrive il cartiglio («Pattina 8 mm»), se il testo si
  legge; se no 8 mm. Sta dal lato dove la stampa massima e' piu' lontana dal
  taglio (11 mm contro 4 sul caso), e va sotto l'altro bordo, sul retro,
  mezzo spessore dentro.
- Il **fronte** e' il mezzo della parte che si vede; la destra del foglio,
  guardando dal centro verso la bocca, e' la destra del pack: la stampa e'
  fuori, niente specchiatura.
- Il **fondo**: la fascia fuori dalla stampa massima e' quella fra il fondo
  e la fine delle linee della stampa massima (rette di un altro stile
  parallele ai lati), 23,8 mm sul caso; se il DT non le disegna, il 12% del
  lato. La saldatura **comincia dove finisce la grafica**: a vista resta
  solo il terzo della fascia subito sotto la stampa massima (`SALDATA`, 7,9
  mm sul caso), il resto (15,9 mm) e' rifilato e il tubo finisce li'
  (`Tubo.R_base`). La saldatura e' **tutta piatta** e **larga quanto il
  tubo**: le due pareti una contro l'altra, ognuna col suo spessore, i
  fianchi ripiegati dentro. Non si appiattisce a perimetro costante (due
  pareti larghe C/2, 1,57 volte il diametro): faceva un piede che sporgeva
  dal tubo, con un gradino, e le foto di chi l'ha caricato non ce l'hanno.
  Sopra la saldatura, di lato, il tubo e' **schiacciato e si apre in linea
  retta fino all'orlo** (`tubo.tondezza`): lo spessore cresce dritto - un
  cuneo - da uno spessore di carta alla saldatura fino al diametro del tubo
  all'orlo, l'unico punto dove e' tondo. Di lato il profilo e' una retta
  sola, di fronte il cono: nessuna curva, nessuna pancia. Di fronte non
  cambia. Prima: con 3 mm di raccordo il tubo finiva in un ago; con un
  diametro del fondo (18,3 mm) e la S dello smoothstep tornava tondo di
  colpo, gonfio sopra la saldatura; con una curva che rallenta sempre
  (1 - (1-t)^2) sui sei decimi della lunghezza faceva una pancia lunga
  («dalla saldatura deve salire ancora un po' schiacciato e poi dritto fino
  al risvolto, senza bombature»); col cuneo fino al 35% della lunghezza e
  poi il cono, «tra prima e adesso non vedo differenza». Fra quattro prove
  messe a confronto (il cuneo fino a un terzo, a meta', a due terzi e fino
  all'orlo) chi ha caricato il caso ha scelto il cuneo fino all'orlo. Il
  gelato si schiaccia come la parete. La saldatura e' rigata dalle
  ganasce (righe orizzontali, passo 0,8 mm, 0,08 mm di fondo) e ha gli
  angoli tagliati a 45 gradi: ai fianchi il fondo sale di un triangolo di
  lato 0,2 volte la larghezza (3,7 mm sul caso; al massimo 0,8 volte
  l'altezza della saldatura).
- La **bocca** ha l'**orlo arrotolato a sezione tonda**: un tubetto tutto
  attorno, come l'orlo di un vasetto (chiesto cosi' da chi ha caricato il
  caso: il risvolto a sezione tubolare, come la coppa da 500). La parete
  finisce alla stampa massima in cima; la carta sale, gira in fuori e torna
  alla parete, e il tubetto e' centrato li', mezzo sopra e mezzo sotto. Il
  **diametro** e' 0,7 volte (`ORLO`) la fascia che il DT lascia in cima fuori
  dalla stampa massima: l'arco di un altro stile concentrico alla bocca,
  entro 10 mm sotto il taglio (`_risvolto`: 2,5 mm sul caso, l'arco rosso a
  387,6 mm contro il taglio a 390,1), quindi 1,77 mm. Alto quanto la fascia
  era troppo grosso: «un po' piu' piccolo». Se il DT non disegna la fascia,
  3 mm (`RISVOLTO`, valore d'uso). Arrotolato in fuori, da fuori si
  vede il rovescio: **bianco carta** in piena luce (`folding.INTERNO`, la
  tinta "rovescio"), non il rovescio in ombra dell'interno
  (`ballotin.INTERNO`, scurito per le scatole chiuse), che lo faceva grigio.
  Arrotolare 2,5 mm di carta darebbe un tubetto di 0,8 mm: il diametro e'
  quello che si vede, non la carta che serve a farlo.
- Il tubo e' **carta**, come il cono: lo spessore 3 (0,7 mm) fa un bordo e
  un risvolto da scatola. Chi lo carica sceglie lo spessore 1.
- Il fondo e la cima della parete, dentro l'orlo, hanno la costa; dentro,
  il rovescio.

Il caso 84c854d6a5 e' stato respinto la prima volta proprio qui: la
saldatura piatta lunga quanto tutta la fascia fuori stampa, piu' un raccordo
alto uguale (47,6 mm su 196,8), e la bocca tagliata netta. Chi l'ha caricato:
"un risvolto bianco nella parte superiore", "in basso la saldatura e' molto
piu' piccola ed ha i lati tagliati".

La seconda volta (saldatura piatta 7,9 mm piu' un raccordo fino alla stampa
massima, 23,8 mm sotto la grafica; risvolto 6 mm; spessore 3, alto 191 mm):
"il risvolto e' troppo grande (guarda il dt), usa un cartoncino piu'
sottile, il calippo e' troppo alto: fare partire la saldatura appena finisce
la grafica". Da qui la fascia rifilata, il risvolto letto dal DT e lo
spessore 1: alto 178,4 mm, fondo 18,3 mm.

La terza versione, ripresa a mano: le misure giuste, ma il fondo era un
piede piatto piu' largo del tubo (il giro schiacciato a perimetro costante,
29 mm contro 18) che spuntava con un gradino da 3 mm di raccordo, e di lato
il tubo finiva in un ago; l'orlo della bocca era grigio. Da qui la
saldatura larga quanto il tubo, il tubo che si schiaccia per un diametro e
l'orlo bianco, poi a tubetto, poi piu' sottile; dopo l'approvazione, il
tubo schiacciato a cuneo fino all'orlo, al posto del rigonfiamento sopra
la saldatura. Alto 179,3 mm alla cima
dell'orlo. Le foto di chi l'ha caricato sono piu' tozze del DT
(alte circa tre volte la bocca, il DT 4,9): sono illustrazioni, e le misure
restano quelle del DT al vero.

### Il gelato

Il tubo si mostra vuoto o **con il gelato**: dopo la lettura la pagina
chiede «vuoto o con il gelato che esce dalla bocca?», con un tasto per gusto
(lime, limone, arancia, fragola, cola), e la scelta costruisce subito
(opzione `gelato` di /api/build, in `OPZIONI_CASO`). E' `pack3d/gelato.py`,
aggiunto al GLB del tubo come mesh e materiale a parte; il tubo resta
identico al byte.

- La **forma**: il ghiaccio e' aderente al tubo - dentro la bocca il raggio
  di dentro della parete meno 0,06 mm, schiacciato come lei, sopra esce dritto, largo quanto la
  bocca, per 0,7 volte il suo diametro (24,5 mm sul caso 84c854d6a5) -, la
  cima appena bombata (0,4 mm) col bordo tondo (1,6 mm) e qualche
  irregolarita'. L'orlo a tubetto resta tutto a vista. Continuando la
  conicita' del tubo, in cima il ghiaccio arrivava a 38 mm, copriva meta'
  dell'orlo e sembrava piu' largo del calippo; staccato dalle pareti di
  mezzo millimetro, fra ghiaccio e orlo restava una fessura scura.
- **Niente texture del colore** sul ghiaccio. Glam mette la texture del pack
  su tutti i materiali con un colore da immagine (GLAM.md, sezione 8), e la
  texture a parte e il template PSD contano le immagini del colore
  (`pack3d.texture`): con una sua texture il modello ne avrebbe avute due,
  la pagina non avrebbe mandato a Glam ne' texture ne' template, e Glam ci
  avrebbe stampato sopra l'artwork. Il colore e' pieno (`baseColorFactor`,
  il chiaro del gusto) con le macchie e l'ombra della bocca nei colori dei
  vertici (COLOR_0); il dettaglio sta nelle normali (la grana satinata dei
  fianchi, le scaglie di cristallo in cima), nella ruvidita' col bagnato
  (che fa anche da clearcoat: tutto lucido, le scaglie di piu') e
  nell'emissione (il sorbetto lascia passare un poco di luce, le scaglie
  brillano).
- I **colori dei vertici sono RGBA**, con l'alfa a 1. Il render di Glam (il
  path tracer three-gpu-pathtracer, «Anteprima Render» e «Render HD») unisce
  tutte le mesh in una sola e da' a quelle senza colori, il tubo, un RGBA di
  serie; quando trova un COLOR_0 RGB le misure non tornano, la libreria
  copia al contrario e il ghiaccio resta a zero: nero, col solo bagliore
  dell'emissione, piu' o meno visibile secondo il lato e le luci. Il viewer
  interattivo non unisce le mesh e lo mostrava giusto.
- Il **lime** e' misurato sulla foto del caso: giallo-verde, il rosso quasi
  quanto il verde e poco blu (180, 200, 40 circa in sRGB). Il primo, piu'
  verde e piu' chiaro, sembrava pistacchio.
- La **traslucenza vera** (KHR_materials_transmission) e' stata provata e
  tolta: attraverso il ghiaccio si rifrangeva l'interno bianco del tubo,
  una striscia chiara sopra l'orlo.
- Le mappe sono 1024 x 512 px (`LATO`), 0,1 mm per pixel sul giro: a 2048
  la differenza non si vede nemmeno da vicino, e costavano 47 secondi
  invece di 2. Il rumore e' una funzione del punto 3D di ogni texel: niente
  cuciture, niente stiramenti al polo della cima, e lo stesso PDF da' lo
  stesso GLB.
- Il controllo dell'AI lo sa (`server.nota_gelato`): il ghiaccio non e' nel
  PDF e non e' un difetto. Nelle sue viste il ghiaccio e' del colore pieno.
- Il viewer della pagina legge i colori dei vertici, il clearcoat e
  l'emissione, che e' in sRGB e va letta lineare; per un colore pieno non
  metallico l'ambiente riflesso e' a 0,35 (la luce ambiente del viewer e'
  gia' forte, e lo bruciava di giallo).

### Cosa manca

- Quanto della fascia fuori stampa resta a vista come saldatura (un terzo)
  e' un valore d'uso: il DT non lo disegna. Il diametro dell'orlo e' un valore d'uso
  solo se il DT non disegna la stampa massima in cima.
- Il lid, il tappo che chiude la bocca, non c'e': se arriva, sara' un
  secondo pezzo come il lid del cono.
