# Mappa del codice: dove guardare

Per chi corregge un caso della coda (CODA.md): dove sta quello che serve,
senza aprire i file interi. `server.py` e la pagina sono lunghi (decine di
migliaia di parole): si cerca con `grep -n` e si legge solo il pezzo
(`sed -n 'A,Bp'`, o Read con offset e limit). Le regole stanno in REGOLE.md,
i principi e l'indice, e in `regole/`, un file per famiglia. Per una
forma che il codice non conosce ancora, la ricetta e' in FORME.md. I gadget
(oggetti promozionali senza DT) non hanno ancora codice qui: le loro regole
sono in GADGET.md.

## Il giro di una costruzione

- `server.py`, `RICONOSCIMENTO`: la **lettura** del PDF e il riconoscimento
  della famiglia, una riga per prova nell'ordine in cui si fanno, ognuna
  con le tipologie dichiarate per cui vale e la sua `_prova_<forma>`: le
  dichiarate sole (coppa, riempimento, incarto, pouch), il caso calibrato,
  vassoio e display, cono, ballotin, il film che lo dice, l'astuccio, poi -
  solo se il solutore astuccio ha rifiutato un cartotecnico - punta, pezzo
  di coppa e tubo, l'incarto a triangolo e per ultimo il flowpack.
  `_analyze_pdf` prova le righe in ordine. Un pack che esce della famiglia
  sbagliata si guarda qui. `COSTRUZIONI` dice, per la famiglia letta, quale
  `build_*` si chiama e con quali scelte della pagina. La famiglia **Incarti** dichiarata dalla pagina passa da
  `analisi_incarto_dichiarato` (la chiusura: `pieghe` o `avvolto`); la sua
  immagine del prodotto la separa dal PDF `_separa_prodotto`, all'inizio di
  `do_POST`, e va col caso (`blocchi_caso`).
- `server.py`, `build_carton`, `build_vassoio`, `build_plancia`,
  `build_scatola_plancia`, `build_coppa`, `build_prisma`, `build_pouch`, `build_ballotin`, `build_punta`,
  `build_tubo`, `build_incarto`,
  `build_flowpack`: la **costruzione** di ogni famiglia, dal PDF al GLB.
- `pack3d/lavoratori.py`: le analisi e le costruzioni in processi a parte,
  uno per lavoro, con la fila al posto del «Server occupato».
  `server._a_un_lavoratore` passa la richiesta, `server.esegui_lavoro` la
  rifa' nel lavoratore com'era, e i casi da mettere in coda e la lettura del
  PDF tornano al processo del server. `/api/lavori` dice alla pagina a che
  punto e' in fila, e quanti lavoratori ci sono: uno per vCPU del container
  (`lavoratori.quanti`).
- `pack3d/stato.py`: un lavoro, una cartella e uno stato. I file temporanei
  di un'analisi o di una costruzione vanno in `stato.cartella()`, le casse
  che valgono per un lavoro solo si dichiarano con `stato.per_lavoro`, e
  `Handler.do_POST` apre il lavoro (`stato.lavoro`) e alla fine butta tutto.
- `pack3d/dieline.py`, `tratti`: i tratti di una pagina come li da'
  pdfplumber, letti una volta per file e per pagina e tenuti in memoria e su
  disco (`PACK3D_CACHE`), per tutti i lavoratori. Chi vuole i tracciati della
  fustella li chiede li' (`extract`, `plancia.tratti`, il ripiego del
  flowpack), non a pdfplumber.
- Il modello prima del verdetto: nella costruzione (`server.py`, il ramo di
  `/api/build`) il GLB parte con `verdetto_dopo`, e il giudizio, la
  correzione e il caso in coda vengono dopo; `nuovo_verdetto` e
  `metti_verdetto` li tengono per `/api/verdetto`, e la pagina li aspetta in
  `seguiVerdetto`.
- `pack3d/verifica.py`: le verifiche della costruzione, nell'ordine in cui si
  fanno a mano (UVW contro il DT, fronte sul fronte, marchio dritto, facce
  dell'astuccio, testate del flowpack, vassoio, plancia), e quelle che
  fermano il modello: la grafica del fronte stirata, e il segno `DIFETTO`
  che il server conta come un dubbio (`con_difetti`).
- `pack3d/lettura.py`: la lettura del PDF da mettere accanto al modello -
  la pagina con le parti lette e le misure (flowpack, astuccio, vassoio,
  display con plancia, coppa e cono; le altre famiglie il disegno usato e
  le righe che dichiarano); il server la serve da `/api/lettura/<gettone>`, e «letto male» va a
  `/api/segnala`.
- `pack3d/misure.py`: le misure del modello finito (ingombro, pezzi, il
  flowpack lungo, largo e spesso, lo stiro del fronte) e il confronto con
  quelle approvate nel parco (`prove/parco.py misure`).
- `pack3d/exporters.py`: il GLB (`write_glb_mesh`; per l'astuccio
  `write_glb`, con lo steso al posto delle immagini delle facce).
- `pack3d/steso.py`: la texture e' lo steso del PDF. Le famiglie ci arrivano
  alla fine della costruzione: giro indietro, ritaglio sul DT, strisce delle
  tinte tolte; per l'astuccio il telaio di ogni faccia e il riscontro.
- `pack3d/texture.py`: la texture a parte, dal GLB: quella che la pagina fa
  scaricare e che va nella sezione texture di Glam.
- `pack3d/atlante.py`: l'atlante dei modelli di piu' fogli (coppa, cono,
  riempimento): gli stesi in un'immagine sola, le UV nella zona di ogni
  pezzo, le zone negli `extras` dell'immagine.
- `pack3d/template.py`: il template PSD, dal GLB, per «Scarica Template» di
  Glam: la texture e le guide UV a livelli, come il template ufficiale.
  Lo chiede la pagina (`/api/template`), lo mandano la routine e lo Space.
- `pack3d/controllo.py`: il controllo dell'AI. **Non si cambia da soli**:
  quello che considera un difetto si propone in bozza (CODA.md).

## Le famiglie

| famiglia | moduli |
|---|---|
| astuccio | `dieline.py` (fustella: `extract`, `solve_carton`), `folding.py` (piegatura, `build_faces`), `incisioni.py` (tagli dentro le facce), `apertura.py` (strappo aperto), `rilievo.py` (embossing), `lamina.py` (foil: metallo sulla scatola a prisma) |
| scatola a punta | `punta.py` |
| tubo a cono (settore di corona, fondo saldato piatto) | `tubo.py`, montato in `server.build_tubo`; `gelato.py` (il ghiacciolo che esce dalla bocca, a scelta) |
| scatola a prisma (fondo poligonale e coperchio a calzare) | `prisma.py`, montata in `server.build_prisma` |
| flowpack | `flowpack.py`, `materiali.py` (alluminio, white plate, vernice) |
| incarto a triangolo (film attorno a una barretta, testate ripiegate) | `incarto.py`, montato in `server.build_incarto` |
| vassoio espositore | `vassoio.py` |
| vassoio sagomato (pareti oblique o con incavi, il fondo fra quattro cordonature; si prova per ultimo) | `vassoio.riconosci_sagomato` |
| display con plancia | `plancia.py` |
<<<<<<< HEAD
| display a scatola (la plancia nel coperchio, disegnata in CAD a fessure e cerniera tratteggiata; si prova dopo lo sportello) | `scatola_plancia.py`, montato in `server.build_scatola_plancia` |
=======
| display con la plancia dentro il coperchio | `sportello.py`; costruito da `build_plancia` con `forma=sportello` |
>>>>>>> origin/coda-settimana
| ballotin | `ballotin.py` (finestre e pellicola comprese) |
| coppa e cono | `coppa.py`, `cup.py` |
| pouch | `pouch.py` |
| riempimento (vassoio + flowpack) | `riempimento.py` (vano, pose, il CU schiacciato a UV ferme, il pezzo uguale al suo modello e dentro il vano, GLB composto); in `server.py` `analisi_riempimento` e `build_riempimento` |

## La grafica e le misure

| difetto | dove |
|---|---|
| segni tecnici, quote o note sulla texture | `strati.py` (livelli, `senza_tecnici`), `techink.py` (inchiostri tecnici), `artwork.py` (aree riservate, GDA, box) |
| grafica girata, fronte sul retro | `artwork.py` (`verso_della_grafica`, `astuccio_sulla_grafica`), `verifica.py` |
| misure sbagliate | `dieline.py`, `quote.py` (il riscontro con le quote scritte), `tracciati.py` |
| colori: colata, nero, sovrastampa | `colata.py`, `nero.py`, `strati.py` (`sovrastampe`) |
| pagine in piu', DT scelto male | `artwork.py` (`pagina_unica`), `tools.py` (`dt_della_tavola`) |

## Le regole gia' scritte

REGOLE.md ha i principi - le tre regole per tutte le famiglie, *Una regola
per tutti, o una scelta del pack* - le domande all'utente e l'indice; le
regole di ogni famiglia stanno in `regole/<famiglia>.md`. Per trovare quella
del caso: l'indice in fondo a REGOLE.md dice il file, poi
`grep -n '^##' regole/<famiglia>.md` e leggi solo la sezione che serve. Per
aggiungere la regola nuova: leggi solo le righe intorno a dove va, aggiungila
li', e se e' una sezione nuova mettila anche nell'indice. I prodotti hanno
nomi neutri: quale prodotto e' ognuno lo dice `regole/nomi.md` nel
repository dei casi.

## Gli strumenti del caso

- `prove/parco.py prepara`: prende il caso, lo mette nel parco, lo
  costruisce e fa un foglio solo da guardare (CODA.md).
- `prove/parco.py consegna`: manda il modello corretto da approvare.
- `prove/parco.py approvato`: dopo l'approvazione, in Glam e `da-rilasciare`
  (se lo Space non l'ha gia' fatto da solo).
- `prove/test_veloci.py`: le prove veloci, in meno di un secondo e senza
  file dei clienti (lettura della fustella, misure, registro delle famiglie,
  stato, lavoratori); girano su ogni PR.
- `prove/parco.py letture`: la lettura di ogni caso del parco contro quella
  approvata, senza costruire: a quale caso una correzione ha cambiato strada.
