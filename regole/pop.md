# I materiali POP

I materiali per il punto vendita: **totem** ed **espositori**, e poi
dondolini, strip, vele, angolari, portaprezzi, sticker. Si caricano dalla
loro finestra di Glam, «Crea materiali POP 3D da PDF», e il codice sta in
`pack3d/pop/`. Qui le loro regole, a parte da quelle dei pack.

## Il confine

**Il POP e i pack non si toccano.** Dal proprietario: «Per ogni caso pop
nuovo con relative regole non bisogna però coinvolgere le altre famiglie
(flowpack crt etc). Quindi eventuali aggiornamenti pr merge dovranno essere
limitati a pop e viceversa».

Il repository e' diviso in tre parti (`prove/confini.py`):

| parte | cosa | chi la tocca |
|---|---|---|
| **POP** | `pack3d/pop/`, `regole/pop.md`, `prove/test_pop.py` | solo le PR del POP |
| **comune** | la pagina, `server.py`, la coda (`pack3d/coda.py`), il registro e i tipi dichiarati (`pack3d/famiglie/registro.py`, `comune.py`), il parco (`prove/parco.py`), le prove comuni (`prove/test_veloci.py`), il workflow, i documenti in cima al repository | tutte e due, per l'aggancio |
| **pack** | tutto il resto: `pack3d/` (flowpack, astucci, vassoi, coppe, incarti... e i moduli che usano: fustella, piegatura, texture, GLB), `regole/` | solo le PR dei pack |

- **Una PR verso `coda-settimana` o e' del POP o e' dei pack.** Puo' toccare il
  comune con l'una o con l'altra, mai il POP e i pack insieme. Nelle Actions
  `prove/confini.py` la ferma (`.github/workflows/prove.yml`).
- **Il POP usa i moduli dei pack, non li cambia.** Leggere la fustella,
  piegare, scrivere il GLB, fare la texture e il template: il POP li chiama.
  Se gli serve una modifica in uno di quei moduli, e' una PR dei pack a
  parte, prima, col parco che prova che nessun pack cambia.
- **Il comune legge il POP, non lo nomina.** Il registro e i tipi dichiarati
  prendono da `pack3d.pop` i materiali (`MATERIALI_POP`, `NOMI_POP`), la
  lettura (`analisi`) e le costruzioni (`COSTRUZIONI`): un materiale nuovo
  entra in `pack3d/pop/`, nella sua voce della pagina e qui, senza toccare
  il registro.
- **Il parco lo prova.** Dopo una PR del POP nessun caso dei pack cambia, e
  dopo una dei pack nessun caso POP (RILASCIO.md).
- **Le prove a parte**: quelle del POP in `prove/test_pop.py`, non in
  `prove/test_veloci.py`.

## La finestra

La pagina dello Space con `pop=1` nell'indirizzo (GLAM.md, sezione 10):
chiede «Che tipo di materiale POP intendi realizzare?» e ha le voci dei
materiali. Un materiale che il codice non sa ancora costruire si ferma alla
lettura (`pop.analisi`) e diventa un caso, che chi l'ha caricato manda con
«Invia il caso». Il modello corretto torna nella finestra POP di Glam
(`X-Model-Section: pop`).

## Il totem

Espositore da terra: un pannello in piedi sulla sua base. Ancora da
costruire: ogni PDF caricato e' un caso in coda (CODA.md, *Un caso che non
si costruisce*). Quello che sappiamo dal proprietario:

- **piatto o curvato.** Per il proprietario «lenticolare» vuol dire il
  **pannello curvato**, non la stampa lenticolare. La curva si legge dal PDF:
  le centine ad arco in fustella, o le quote del raggio o della freccia; la
  larghezza del pannello steso e' la lunghezza dell'arco. Se il PDF non la
  dice, e' una scelta del pack, non una regola per tutti;
- **i popup**: sagome in rilievo applicate davanti al totem, staccate da un
  distanziale (una linguetta piegata a Z o a ponte). Dove stanno e quanto
  sporgono lo dice il disegno di montaggio, o una scelta del pack;
- la sezione puo' avere una faccia curva e il retro piatto, o due facce
  curve: lo dice la fustella.

Il totem curvo si costruisce come il fronte curvo della scatola a punta o il
cono del tubo: un foglio piegato ad arco, nella sua casa (`pack3d/pop/`),
che usa quei moduli senza cambiarli.

## L'espositore

Da banco o da terra: la struttura coi ripiani o i vani dove stanno i
prodotti. Si comincia da qui (dal proprietario, 13 novembre 2026: «aggiungiamo
oltre al pulsante totem anche il pulsante Espositore e poi iniziamo da
quello»). Ancora da costruire: ogni PDF caricato e' un caso in coda.

- **Il nome.** Per i pack «espositore» e' un sinonimo di vassoio
  (`famiglie.comune.SINONIMI_KIND`): il materiale POP si chiama
  `espositore_pop`, e sul pulsante «Espositore». Nessun materiale POP puo'
  avere il nome di un tipo o di un sinonimo dei pack: lo controlla
  `prove/test_pop.py`.
- **Non e' il vassoio.** Il vassoio espositore e il display con plancia sono
  pack (regole/vassoi.md): l'espositore POP ne puo' usare i moduli - la
  fustella, la piegatura, il GLB - ma non li cambia (*Il confine*).

### Come si costruisce (in prova, `pack3d/pop/espositore.py`)

Dal PDF della fustella: i pezzi si riconoscono dalle pieghe e dalla stampa,
e ognuno si piega e si monta con le misure che legge (`misure`). Ancora in
prova: lo Space non lo costruisce, il PDF va in coda.

- **La grafica senza il disegno tecnico.** Dal proprietario: «Elimina il dt
  senza intaccare la grafica». Non si ritocca l'immagine (un ritocco attorno
  ai segni rovinava i loghi e i testi vicini): si tolgono dal PDF gli
  OGGETTI del DT prima di renderlo (`fustella.resa_senza_dt`). Se il DT ha
  uno strato suo, si toglie tutto lo strato, con le quote e i triangoli di
  orientamento; se non ce l'ha, o lo strato ha anche la grafica, solo i
  tracciati che stanno sulle linee dei tagli e delle pieghe.
- **Le note si tolgono.** Dal proprietario: «le note rosa vanno tolte». Lo
  strato delle note (le zone rosa della colla e di quello che non si
  stampa, le scritte dei pezzi) non e' stampa: si toglie dal PDF come il DT
  (`fustella.NOTE`, dal nome dello strato). Dove non c'e' grafica resta il
  cartone bianco, come sul fondello.
- **I triangoli di orientamento** non sono tagli (`fustella._triangolo`).
- **I contorni morbidi.** Dal proprietario: «i tracciati sono seghettati.
  Usa le curve di bezier». Il bordo di ogni pannello e' quello del PDF: le
  curve di Bezier campionate ogni 1,5 mm (`fustella.PASSO_CURVA`), non i
  gradini dei pixel della maschera.
- **Lo spessore col colore della grafica.** Dal proprietario: «fai in modo
  che gli spessori siano arancioni (o comunque in linea con la grafica)».
  Il bordo tagliato prende il colore della stampa a 3 mm dal bordo.
- **Lo spessore dalle pieghe doppie.** Le due cordonature di una piega a
  180 gradi stanno a due spessori: la mediana di quelle dei fianchi, dei
  ripiani e del divisorio, divisa per due (`espositore.spessore`). Sul primo
  PDF 4 mm, onda EB; prima era fisso a 6, troppo (dal proprietario: «fare
  gli spessori piu' bassi»).
- **Le pieghe tonde.** Dal proprietario: «simulando la piega del cartone
  (bordi arrotondati)». Le pieghe doppie diventano archi
  (`espositore.piega_tonda`): mezzo giro sul bordo davanti dei fianchi, in
  cima ai fianchi, sul davanti dei ripiani e sul dorso del divisorio; un
  quarto di giro fra il davanti e i lati della testata. Fuori la stampa,
  dentro il raggio meno lo spessore. La testata appoggia sopra la cima
  tonda.
- **Anche le pieghe semplici, con la stessa curvatura.** Dal proprietario:
  «le curvature delle pieghe teniamo queste anche per gli altri». Una piega
  semplice fra due pannelli piatti diventa tonda, raggio fuori uguale allo
  spessore (`Montaggio.arrotonda`): gli angoli del frontalino e del
  riempitivo, il fondo dei fianchi, le alette e le linguette dei ripiani,
  il bordo davanti del fondello (a 180 gradi). Solo dove la stampa sta
  fuori dalla piega, lo spigolo che si vede: dove sta dentro (gli angoli
  della schiena, le alette del divisorio) il cartone vero fa lo spigolo
  vivo sulla stampa, e resta vivo. La curvatura e' una regola del POP:
  vale anche per i materiali che verranno.
- **La prefustella incisa.** Dal proprietario: «il lato del crowner ha le
  fustelle incise come i pack ... (prefustella stampata)». Sui lati della
  testata l'arco e le diagonali non tagliano e non piegano: sono solchi a V
  nella faccia stampata (largo 1 mm, profondo 0,9), con la grafica dentro,
  come l'apertura a strappo degli astucci e dei vassoi
  (`incisioni.maglia_incisa`). Sono i tagli che non toccano il contorno
  (`fustella.tagli_interni`) e le pieghe oblique.
- **Nessuna compenetrazione fra parti diverse.** Dal proprietario: «evita
  intersezioni tra le diverse parti». Dove due cartoni starebbero nello
  stesso posto, quello che viene dopo nell'ordine (`espositore.ORDINE`: il
  corpo, il divisorio, i ripiani, la testata, il riempitivo, il frontalino,
  il fondello; le alette sul pavimento per ultime) si intaglia, come la
  feritoia vera. `espositore.intersezioni` controlla il modello fatto.
- **Da verificare col proprietario**: il fondo della colonna di sinistra e'
  il fondello (largo quanto l'interno, con la feritoia del divisorio), non
  un terzo ripiano; il frontalino sta sul davanti dei ripiani; i piedi
  della testata entrano nei fianchi e non si vedono; i lati della testata
  sono piatti, con la prefustella incisa.
