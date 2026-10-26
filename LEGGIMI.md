# pack3d studio

Interfaccia web con viewer 3D centrale, un pulsante per caricare l'artwork PDF
e uno per scaricare il modello GLB.

Il ciclo completo — carica PDF, costruisci, scarica — richiede il backend
Python: la pipeline usa numpy, scipy e i lettori PDF, che nel browser non
girano. La pagina da sola resta un visualizzatore.

## 1. In locale

```bash
pip install -r requirements.txt
python server.py                 # http://localhost:8000
```

Il doppio clic sul file HTML **non** funziona: senza server non esiste `/api`.

## 2. Condividere un link, subito

Il server ascolta su `0.0.0.0`, quindi basta esporlo con un tunnel:

```bash
python server.py &
cloudflared tunnel --url http://localhost:8000     # oppure: ngrok http 8000
```

Il tunnel stampa un indirizzo pubblico: quello e' il link da condividere,
funzionante al 100% finche' il tuo computer resta acceso.

## 3. Metterlo online

```bash
docker build -t pack3d-studio .
docker run -p 8000:8000 pack3d-studio
```

Il `Dockerfile` va cosi' com'e' su Render, Railway, Fly.io o una VM: il server
legge `PORT` e `HOST` dall'ambiente, come si aspettano quei servizi. Nessun
database, nessuno stato: i PDF vengono elaborati in una cartella temporanea e
buttati.

## Interfaccia e backend separati

Se metti la pagina su un hosting statico e il backend altrove:

```
https://tuo-sito/pack3d_studio.html?api=https://tuo-backend
```

Il server risponde con CORS aperto e gestisce il preflight, quindi la
combinazione funziona.

## Cosa fa l'interfaccia

1. Per prima cosa la pagina chiede **che tipo di Pack/Riempimento** si vuole
   realizzare: Flowpack, Pouch, Cartotecnico, Vassoio, Riempimenti, Incarti.
   Poi il passo della famiglia, con un posto per ogni PDF (solo PDF, tranne
   l'immagine del prodotto degli incarti):
   - **Flowpack**: il PDF, poi le domande obbligatorie - numero dei denti
     della zigrinatura, rigonfiamento, apertura delle pinne - la saldatura
     delle pinne (da 0, lisce, a 3, le righe delle ganasce piene) e la
     casella per dire se il film avvolge una scatola;
   - **Pouch** e **Vassoio** (display compresi): il PDF, e il modello parte;
   - **Cartotecnico**: astuccio o scatola e lo spessore della carta;
     l'astuccio un PDF, la scatola di quante parti e' fatta e un PDF per
     parte. Se l'astuccio ha un'apertura a strappo, chiuso (con o senza la
     fustella dell'apertura modellata) o aperto di quanti gradi; se il pack
     ha una finestra, se ci va la pellicola trasparente;
   - **Riempimenti**: che cosa e' il pack (CU), flowpack o astuccio; il pack
     e il vassoio o display; poi quanti pack mettere e le domande del
     flowpack, o la fustella dell'apertura a strappo dell'astuccio;
   - **Incarti**: come si chiude il foglio, a pieghe (le barrette) o
     avvolto (tipo l'ovetto); il PDF dello steso e l'immagine del prodotto
     da incartare (JPEG, PNG o WebP). L'avvolto il codice non lo costruisce
     ancora: il caso va in coda col PDF e l'immagine.
2. Il viewer mostra il risultato scartando le facce posteriori, quindi un
   modello con le normali girate si riconosce a colpo d'occhio.
3. **Scarica GLB** salva il file appena costruito.

Si puo' anche trascinare un GLB gia' pronto per guardarlo senza backend.

## Qualita'

Di default la texture esce **HD**: 300 dpi, fino a 8192 px di lato, cioe'
quasi 12 pixel per millimetro di foglio. Con `{"quality":"web"}` nell'header
`X-Pack3d` si torna alla texture leggera di prima - 200 dpi e al massimo 1700
px, che sui fogli grandi scende sotto i 4 px/mm - e con `{"quality":"alta"}`
si aggiunge all'HD la maglia piu' fitta usata per i render.

| | web | HD, di serie |
|---|---|---|
| Astuccio | 0,5 - 1,2 MB | 0,8 - 2,2 MB |
| Flowpack | 3,5 - 4,2 MB | 3,6 - 5,9 MB |
| Vassoio | 1,1 MB | 3,4 MB |

## Rigonfiamento

Una scala da 1 a 10, non tre gradini. Nell'interfaccia e' un cursore, con la
casella **Scegli tu** che passa la decisione all'AI in base al prodotto.

Il livello cambia la **forma** della sezione, non la sua taglia: il perimetro e'
fissato dal foglio stampato, quindi a parita' di steso un pack piu' morbido non
e' piu' grande, e' piu' tondo. La sezione e' una superellisse il cui esponente
scende da 10 (rettangolo) a 2 (ellisse): la larghezza resta quella della
faccia nel DT e il film che gli spigoli tondi lasciano va nello **spessore**,
come in un pack pieno. Un flowpack 30 x 12 esce 30 x 15,3 al livello 5 e 30 x
19,7 al livello 9. La grafica sta sul giro alla sua distanza dal centro del
fronte, come il film, che non si allunga.

Gli altri parametri si interpolano su tre ancore:

| livello | raccordo | esponente | grinza | pancia | rastremazione |
|---|---|---|---|---|---|
| 1 | 4,5 mm | 2,0 | – | 0,8% | 6 mm |
| 5 | 7,5 mm | 2,4 | 0,35 mm | 3,0% | 16 mm |
| 10 | 11,0 mm | 2,8 | 0,75 mm | 6,0% | 30 mm |

## Apertura pinne

Da 1 a 3, ed e' una domanda separata dal rigonfiamento: dice come si comporta
il film **alle ganasce**, non che forma prende il corpo.

| | bordo della pinna |
|---|---|
| 3 | meta' perimetro, la pinna e' piu' alta del pack (Milch-Schnitte) |
| 2 | in mezzo |
| 1 | quanto la faccia del pack, senza svaso (Kinder Brioss) |

La casella **"Il film avvolge una scatola"** propone rigonfiamento 1 e pinne 1,
e in piu' tiene la sezione a quella della fustella invece di riscalarla, e
sposta la gola del tubo oltre il corpo invece che dentro. Entrambi i valori
restano modificabili.

## Etichette

Le etichette vecchie continuano a funzionare nell'API: `rigido` = 2,
`medio` = 5, `morbido` = 8. Gli estremi vengono da Milch-Schnitte (teso) e
FULFIL (gonfio); il centro scala e' interpolato e va ritarato sul prossimo
flowpack di prova.

## Limiti noti

- Il riconoscimento automatico dei flowpack copre l'impaginato tipo
  Milch-Schnitte. Gli artwork risolti a mano stanno nel registro `CASI` dentro
  `server.py`, riconosciuti dalla firma della pagina; ogni nuovo flowpack
  risolto va aggiunto li'.
- Una costruzione impegna un thread per 3-15 secondi. Per uso condiviso da piu'
  persone in contemporanea serve una coda, che oggi non c'e'.
- Limite di caricamento 60 MB per PDF.
