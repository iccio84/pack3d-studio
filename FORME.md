# Una forma nuova: la ricetta

Per la sessione della routine - e per chi lavora a mano - quando un caso e'
una forma che il codice non conosce dentro una famiglia che c'e': una scatola
esagonale, una base col coperchio a calzare, un coperchio a cerniera. Va
fatta (CODA.md, *Cosa si risolve*), e questa e' la strada gia' percorsa due
volte: la scatola a punta (`pack3d/punta.py`) e il ballotin
(`pack3d/ballotin.py`). I pezzi che servono stanno gia' nel codice: si
usano, non si riscrivono.

Il percorso, in breve: capire la forma, scegliere dove entra, scrivere il
modulo (riconoscere e piegare), la funzione che costruisce, le prove, le
regole. Texture, template, atlante e controllo dell'AI vengono da se'.

## 1. Capire la forma, prima del codice

- **Il foglio di `prepara`** (il PDF e il modello di adesso), la
  **descrizione** di chi l'ha caricato - la pagina la chiede sempre, ed e' in
  `voci.md` - e la sua foto, se c'e'.
- **Sulla fustella** conta ogni tratto: le **cordonature** sono pieghe, i
  **tagli** sono bordi liberi. Nel modello ogni piega sta su una cordonatura
  e ogni bordo libero su un taglio: un ripiano senza cordonatura non ha dove
  piegarsi. La quarta versione della scatola a punta leggeva due tagli a 45
  gradi come il bordo di un ripiano che non c'era, e di tre quarti si vedeva
  uno scalino.
- **Le misure vengono dal DT**, mai da una foto: la terza versione della
  scatola a punta teneva fronte e retro dritti 29 mm sopra la piega, una
  stima dalla foto, ed era sbagliata.
- Scrivi in `come_deve_venire` (`parco/parco.json`) la forma con le misure:
  ingombro, quanti lati, le altezze delle pareti, come si chiude, quali
  pezzi.
- **Se c'e' una cosa che solo chi ha il pack sa** - come sta un'aletta, da
  che parte e' la stampa di un pezzo piegato, se il coperchio calza fino in
  fondo - **chiedila subito** (CODA.md, *Un caso che non si risolve*), con
  una foto del pack montato: non dopo aver scritto il codice. La scatola a
  punta ha avuto cinque versioni, e tre sono state correzioni di chi l'aveva
  in mano che una domanda all'inizio avrebbe evitato.

## 2. Dove entra

Il modulo nuovo si prova **dopo** quelli che ci sono, quando l'hanno
rifiutata: cosi' i casi del parco non cambiano strada e non pagano la prova.

- **Un pezzo solo** (un PDF): una riga in `RICONOSCIMENTO` (`server.py`),
  dopo `astuccio` e accanto a `scatola a punta`, per `["carton"]`, con la
  sua `_prova_<forma>`: torna None subito se `lettura.errore_astuccio` e'
  None - si prova solo se il solutore astuccio ha rifiutato il foglio - e
  torna None anche se il foglio non e' suo, cosi' si passa alla riga dopo.
  L'eccezione e' una forma che il solutore astuccio **risolve male** invece
  di rifiutare: allora la riga va prima di `astuccio`, con un prefiltro che
  su un astuccio esce subito (il ballotin cerca le lenti agli spigoli, il
  cono il settore pieno, in qualche decimo di secondo).
- **Piu' pezzi** (un PDF per pezzo, dichiarato cartotecnico in N pezzi): la
  richiesta passa da `server.in_piu_pezzi` ad `analisi_coppa` e a
  `_pezzi_tondi`, che oggi riconosce lo sleeve e il tappo della coppa, il
  cono e il lid, e per qualunque altro foglio si ferma con «per ora so
  montare...». Il riconoscimento dei pezzi nuovi va li', **dopo**
  `coppa.orienta`; ogni PDF dice da se' che pezzo e', e l'ordine in cui
  arrivano non conta. Il messaggio d'errore si aggiorna con la forma nuova.
  Se la funzione cresce, rinominala per quello che fa (i pezzi, non solo i
  tondi), con tutti i chiamanti.

## 3. Il modulo: `pack3d/<forma>.py`

Come `punta.py`, in quattro parti.

**I dati letti dal foglio.** Una classe con quello che serve per piegare, in
mm: la `regione` del DT in punti PDF (serve a pulire e a ritagliare la
texture), i pannelli, le pieghe, le misure del solido.

**`riconosci(pdf, page_no=0)`**: l'oggetto, o `None` se il foglio non e'
quella forma - mai un'eccezione per dire "non sono io". La **firma** e' un
elenco di condizioni che devono tornare **tutte**, ognuna con la sua
tolleranza in mm e in percento: la scatola a punta ne ha sei (REGOLE.md, *La
firma in fustella*), ed e' la firma che la distingue da un astuccio con una
piega in piu'. Gli attrezzi ci sono:

| serve | dove |
|---|---|
| i tratti della fustella, con la penna e il tipo | `ballotin.polilinee`, `ballotin.tratti_fustella` |
| il grafo della fustella e le sue facce chiuse, di qualunque forma (un fondo esagonale e' una faccia a sei lati) | `ballotin.grafo`, `ripara`, `pota`, `facce`, `principale`, `componi` |
| le cordonature tratteggiate | `ballotin.tratteggi` |
| gli angoli di una faccia | `ballotin._angoli`, `ballotin.area` |
| la griglia a fasce, se la forma e' a fasce come un astuccio | `dieline.extract` (`d.ys`, `d.panels`) |
| il verso della grafica | `artwork.verso_della_grafica`; o, come la scatola a punta, un riferimento letto dal disegno stesso (la cima e' il capo del fronte piu' vicino alla piega) |

**La forma si legge comunque stia il foglio sulla tavola** - girato di 90,
180 o 270 gradi, capovolto (REGOLE.md, *Il foglio nel verso della grafica,
prima di risolverlo*): nessuna condizione della firma dipende da dove sta
"su" nel PDF.

**`dichiara(p)`**: le righe per i dettagli tecnici, la forma e le misure in
mm, come `punta.dichiara`.

**`maglia(p, origine_mm, px_mm, misura_tex, spessore=None)`**: `(V, UV, T)`
del pack montato, come `punta.maglia` e `ballotin.maglia`:

- `V` in mm: il fronte guarda +Z, la cima +Y, il fondo sta a Y = 0;
- ogni faccia del foglio gira **rigida** sulla sua piega fino al suo posto,
  e i suoi vertici tengono come UV il punto da cui vengono sul foglio
  (`uv(sx, sy)` in `punta.maglia`): la texture e' il DT intero, e ogni pezzo
  prende la grafica dal suo posto;
- il **rovescio**, uno spessore piu' in dentro, e la **costa** su ogni bordo
  che non combacia con quello di un altro pezzo, con le UV sulle strisce di
  `ballotin.con_interno` (tinta del rovescio e del taglio): vedi i pezzi
  `interno` e `pezzo` di `punta.maglia`, e `ballotin._bordi`;
- quello che sta sopra un'altra faccia - un'aletta incollata, un coperchio
  calzato - sta a uno spessore di distanza, mai alla stessa quota:
  altrimenti le due facce si contendono i pixel;
- una faccia non piana (una parete curva, un'ala che si incurva) si fa a
  strisce, come le ali della scatola a punta.

**Piu' pezzi**: una `maglia` per pezzo, ognuno sulla sua texture. Il
coperchio che calza sulla base sta **sopra la base**, centrato, con le sue
pareti fuori da quelle della base di uno spessore piu' il gioco; i pezzi
sono **nodi separati** del GLB (il coperchio in Glam si toglie).

## 4. La costruzione: `server.build_<forma>`

**Un pezzo**: copia `build_punta`, che fa tutto nell'ordine giusto -
`artwork.pagina_unica`, `riconosci`, `artwork.senza_coperture` sulla
`regione` del DT, gli avvisi (pagine in piu', fuori dal DT, GDA,
quadricromia, lastre tolte), il DT intero rasterizzato
(`folding.rasterize_panels` con un pannello solo), `ballotin.con_interno`,
la `maglia`, `lo_steso.senza_strisce` (le strisce diventano colori pieni) e
`exporters.write_glb_mesh`. Restituisce `dichiara(p) + avvisi`.

**Piu' pezzi**: come `build_coppa` - per ogni pezzo la sua texture, i pezzi
come `parti=[(nome, primo, ultimo)]` in `write_glb_mesh`, e alla fine
`atlante.unisci_file(out_glb)`, che mette le texture in un'immagine sola.
Se un foglio e' stato girato per leggerlo, le sue UV tornano nel verso del
PDF con `lo_steso.INDIETRO`, come in `build_coppa`.

**I due fili da collegare in `server.py`**:

- la lettura (`_prova_<forma>` in `RICONOSCIMENTO`, o `analisi_coppa` per
  i pezzi) restituisce `dict(kind="<forma>", title="...", meta=dichiara(p))`;
- la costruzione: una voce in `COSTRUZIONI` (`server.py`), accanto a
  `"punta": _costruisci_punta`, e la sua `_costruisci_<forma>(r, info)` che
  chiama `build_<forma>` con lo spessore della carta (`carta=r.carta`). `r`
  ha il PDF e le scelte della pagina.

La pagina non si tocca: legge `title` e `meta` per qualunque forma.

## 5. Quello che viene da se'

Se la texture e' il DT intero (o un atlante, per piu' pezzi), funzionano
senza toccarli: la texture a parte (`texture.py`), il template PSD
(`template.py`, con i contorni e le pieghe letti dal GLB), lo steso
(`parco.py stesi`), Glam. **Il controllo dell'AI (`controllo.py`) non si
tocca**: guarda il modello accanto al PDF qualunque forma abbia.

## 6. Le prove

Prima di unire (CODA.md, *Quando si unisce nel ramo della settimana*), in
quest'ordine:

1. `python3 -m py_compile` su ogni file toccato.
2. **Il caso**: `costruisci --solo <nome>` e le viste accanto al PDF, con
   l'occhio del controllo - forma, misure, verso, fronte sul fronte, nessun
   segno tecnico - e `stesi --solo <nome>`: la texture e' lo steso, dritto.
3. **I vicini**: i casi del parco che passano dallo stesso punto devono
   restare **uguali al byte**. Costruiscili col codice di prima e con quello
   nuovo e confrontali:

       git worktree add /tmp/prima origin/coda-settimana     # o origin/main, se il ramo non c'e'
       python3 prove/parco.py costruisci ../pack3d-casi /tmp/vicini_prima --codice /tmp/prima --solo <vicini>
       python3 prove/parco.py costruisci ../pack3d-casi /tmp/vicini_dopo --solo <vicini>
       python3 prove/parco.py confronta /tmp/vicini_prima /tmp/vicini_dopo

   I vicini: per piu' pezzi la coppa e il cono; per una forma provata prima
   dell'astuccio tutti i cartotecnici del parco; per una forma provata dopo
   l'astuccio la scatola a punta. Il parco intero lo fa il rilascio.
4. **Il messaggio d'errore**: un foglio che non e' la forma nuova deve
   ancora fermarsi con un messaggio che dice cosa il codice sa montare.

## 7. Le regole

- **Le regole**: un file nuovo in `regole/`, come `regole/punta.md` per
  *La scatola a punta*, e le sue sezioni nell'indice di REGOLE.md: cos'e' e come
  si dichiara, il caso da cui e' nata (il codice del caso, mai il nome del
  cliente), *La firma in fustella* coi numeri, *Il solido* con le formule,
  la texture, e *Cosa manca*.
- **MAPPA.md**: la riga della forma nella tabella delle famiglie, e
  `build_<forma>` nell'elenco delle costruzioni.
- **La correzione dopo la consegna**: se chi ha il pack dice che qualcosa
  non torna («Non approvo», con la foto), la nuova versione va nella stessa
  sezione, con cosa era sbagliato e perche' - come le cinque versioni della
  scatola a punta. E' da li' che la sessione dopo impara.
