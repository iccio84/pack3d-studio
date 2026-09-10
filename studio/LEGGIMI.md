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

1. **Carica PDF** accetta solo PDF. Se e' un astuccio il modello parte subito;
   se e' un flowpack compaiono prima le due domande obbligatorie, zigrinatura e
   tipo di gonfiore.
2. Il viewer mostra il risultato scartando le facce posteriori, quindi un
   modello con le normali girate si riconosce a colpo d'occhio.
3. **Scarica GLB** salva il file appena costruito.

Si puo' anche trascinare un GLB gia' pronto per guardarlo senza backend.

## Il resoconto della costruzione

`POST /api/build` risponde col GLB nel corpo, quindi il resoconto viaggia
nell'header **`X-Pack3d-Meta`**: un array JSON con le quote effettive, gli
avvisi di coerenza e — quando c'e' — l'avvertenza che la geometria e' stimata
dall'AI invece di misurata. Il preflight lo dichiara in
`Access-Control-Expose-Headers`, altrimenti cross-origin il browser non lo
lascerebbe leggere.

Vale la pena leggerlo sempre: senza, un modello costruito su una geometria
stimata e uno misurato arrivano identici.

## Riusare l'analisi invece di rifarla

Passando a `/api/build` l'esito di `/api/analyze-ai` nel campo `params`, il
backend riusa la geometria gia' misurata:

```json
{"kind":"flowpack","teeth":20,"soft":"morbido","params":{"flowpack":{...}}}
```

Senza, su un impaginato non riconosciuto la costruzione rifa' l'analisi da
zero: una seconda chiamata a pagamento di 20-60 secondi per misurare quello
che era gia' stato misurato.

La geometria in `params` arriva dal browser, quindi e' input non fidato: passa
dalle stesse tre coerenze fisiche che rifiutano una geometria AI incoerente
(perimetro+falde=nastro, retro=fronte, corpo+pinne=passo) e un conto che non
torna restituisce `400`, non un modello sbagliato. I solutori automatici
restano prima: quando riconoscono l'impaginato misurano, e una misura batte
sempre un numero arrivato da fuori.

## Le prove

```bash
python -m unittest discover -s tests
```

Solo libreria standard, come il server: girano anche nel container. Coprono il
livello di trasporto, il gate di validazione della geometria e il ciclo di
tool use (con un client Anthropic finto: nessuna chiamata di rete, nessuna
spesa).

Non coprono la geometria: per quella servono gli artwork di riferimento, che
non stanno nel repository. `tests/fixtures/LEGGIMI.md` dice quali sono e con
che nome copiarli.

## Qualita'

Di default i modelli escono in qualita' web: mesh e texture ridotte, per stare
in pochi MB su una connessione qualsiasi. Con `{"quality":"alta"}` nell'header
`X-Pack3d` si ottiene la densita' piena usata per i render.

| | qualita' web | qualita' alta |
|---|---|---|
| Astuccio | ~0,9 MB | ~1,5 MB |
| Flowpack | ~3,6 MB | ~12 MB |

## Tipo di gonfiore

| | raccordo | esponente | grinza | pancia | rastremazione |
|---|---|---|---|---|---|
| Rigido | 5,2 mm | 2,0 | – | 1,5% | 8 mm |
| Medio | 7,5 mm | 2,4 | 0,35 mm | 3,0% | 16 mm |
| Morbido | 9,5 mm | 2,6 | 0,60 mm | 4,5% | 26 mm |

Il livello "medio" e' interpolato fra i due estremi, Milch-Schnitte (rigido) e
FULFIL (morbido), e va ritarato sul prossimo flowpack di prova.

## Limiti noti

- Il riconoscimento automatico dei flowpack copre l'impaginato tipo
  Milch-Schnitte. Gli artwork risolti a mano stanno nel registro `CASI` dentro
  `server.py`, riconosciuti dalla firma della pagina; ogni nuovo flowpack
  risolto va aggiunto li'.
- Una costruzione impegna un thread per 3-15 secondi. Per uso condiviso da piu'
  persone in contemporanea serve una coda, che oggi non c'e'.
- Limite di caricamento 60 MB per PDF.
