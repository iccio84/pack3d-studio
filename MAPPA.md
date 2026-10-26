# Mappa del codice: dove guardare

Per chi corregge un caso della coda (CODA.md): dove sta quello che serve,
senza aprire i file interi. `server.py` e la pagina sono lunghi (decine di
migliaia di parole), REGOLE.md ancora di piu': si cerca con `grep -n` e si
legge solo il pezzo (`sed -n 'A,Bp'`, o Read con offset e limit). Per una
forma che il codice non conosce ancora, la ricetta e' in FORME.md. I gadget
(oggetti promozionali senza DT) non hanno ancora codice qui: le loro regole
sono in GADGET.md.

## Il giro di una costruzione

- `server.py`, `_analyze_pdf`: la **lettura** del PDF e il riconoscimento
  della famiglia, in quest'ordine: coppa, pouch, flowpack dichiarato,
  vassoio e display con plancia, cono, ballotin, film che si dichiara
  flowpack, astuccio; l'incarto a triangolo si prova prima del flowpack
  (`_analisi_incarto`). Un pack che esce della famiglia sbagliata si guarda
  qui. La famiglia **Incarti** dichiarata dalla pagina passa da
  `analisi_incarto_dichiarato` (la chiusura: `pieghe` o `avvolto`); la sua
  immagine del prodotto la separa dal PDF `_separa_prodotto`, all'inizio di
  `do_POST`, e va col caso (`blocchi_caso`).
- `server.py`, `build_carton`, `build_vassoio`, `build_plancia`,
  `build_scatola_plancia`, `build_coppa`, `build_prisma`, `build_pouch`, `build_ballotin`, `build_punta`,
  `build_tubo`, `build_incarto`,
  `build_flowpack`: la **costruzione** di ogni famiglia, dal PDF al GLB.
- `pack3d/verifica.py`: le verifiche della costruzione, nell'ordine in cui si
  fanno a mano (UVW contro il DT, fronte sul fronte, marchio dritto, facce
  dell'astuccio, testate del flowpack, vassoio, plancia).
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
| riempimento (vassoio + flowpack) | `riempimento.py` (vano, pose, GLB composto); in `server.py` `analisi_riempimento` e `build_riempimento` |

## La grafica e le misure

| difetto | dove |
|---|---|
| segni tecnici, quote o note sulla texture | `strati.py` (livelli, `senza_tecnici`), `techink.py` (inchiostri tecnici), `artwork.py` (aree riservate, GDA, box) |
| grafica girata, fronte sul retro | `artwork.py` (`verso_della_grafica`, `astuccio_sulla_grafica`), `verifica.py` |
| misure sbagliate | `dieline.py`, `quote.py` (il riscontro con le quote scritte), `tracciati.py` |
| colori: colata, nero, sovrastampa | `colata.py`, `nero.py`, `strati.py` (`sovrastampe`) |
| pagine in piu', DT scelto male | `artwork.py` (`pagina_unica`), `tools.py` (`dt_della_tavola`) |

## Le regole gia' scritte

REGOLE.md ha una sezione per ogni famiglia e per ogni regola (`### ...`).
Per trovare quella del caso: `grep -n '^##' REGOLE.md`, poi leggi solo la
sezione che serve. Per aggiungere la regola nuova: leggi solo le righe
intorno a dove va, e aggiungila li'.

## Gli strumenti del caso

- `prove/parco.py prepara`: prende il caso, lo mette nel parco, lo
  costruisce e fa un foglio solo da guardare (CODA.md).
- `prove/parco.py consegna`: manda il modello corretto da approvare.
- `prove/parco.py approvato`: dopo l'approvazione, in Glam e `da-rilasciare`
  (se lo Space non l'ha gia' fatto da solo).
