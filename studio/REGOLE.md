# Regole della pipeline pack3d

Regole accumulate caso per caso, con il punto del codice che le applica e i
controesempi che le giustificano.

## Domande all'utente

| regola | dove |
|---|---|
| Su **ogni** PDF chiedere prima la tipologia: Cartotecnico, Flowpack, Coppa conica, Altro. La tipologia si dichiara, non si indovina. | pannello del frontend + `analyze_pdf(pdf, kind)` |
| Solo flowpack: chiedere il **numero esatto** di dentini, digitato dall'utente. Nessuna alternativa proposta, 0 = pinne lisce. | campo numerico senza valore predefinito |
| Solo flowpack: chiedere il gonfiore fra Rigido, Medio, Morbido. | `GONFIORE` in `server.py` |

Nessun'altra domanda durante la costruzione.

**Perche' la tipologia non si indovina:** il solutore astuccio risolve anche i
flowpack e restituisce numeri plausibili ma sbagliati. Su Kinder Bueno Dark
dava 275,0 x 101,9 x 31,0 invece di 150,5 x 41,0.

**Perche' i dentini non si deducono:** il passo del dente varia enormemente.

| | bordo pinna | denti | base |
|---|---|---|---|
| Milch-Schnitte T1 | 55 mm | 30 | 1,83 mm |
| Kinder Bueno Dark | 181,5 mm | 30 | 6,05 mm |

Fattore 3,3 a parita' di conteggio. Ogni tentativo di calcolarli e' sbagliato.

## Regole comuni a tutte le tipologie

- **Confrontare sempre il modello finito con lo steso.** La grafica sul 3D deve
  avere lo stesso orientamento del PDF, mai specchiata o capovolta.
- **Non distorcere mai la grafica.** I bollini circolari restano cerchi. Ogni
  pannello va sulla faccia corrispondente e centrato.
- **Verificare il verso delle normali.** L'attributo NORMAL non basta: conta
  l'avvolgimento dei triangoli, ed e' quello che i viewer usano per il culling.
  Gli astucci sono stati consegnati due volte con le facce rivolte all'interno
  perche' il rasterizzatore interno non fa culling e non se ne accorgeva.
- **Cercare sempre il disegno tecnico in miniatura.** Negli artwork c'e' spesso
  un DT completo senza grafica, di solito in basso o a lato, con piu'
  informazioni di quello sovrapposto alla grafica. E' molto piu' pulito.
  Sulla coppa Nutella la miniatura da' residuo **0,000 mm** contro **0,564** del
  contorno sotto la grafica. Attenzione: e' in scala ridotta, quindi **forma e
  proporzioni dalla miniatura, scala dal disegno grande o dalle quote**.

## Togliere il disegno tecnico: quattro livelli

Dal certo allo stimato. Il livello usato va sempre riportato nel resoconto.

1. **Processing Steps ISO 19593-1** — gli oggetti non stampati stanno su livelli
   marcati con metadati normalizzati, in sette gruppi: Structural, Dimensions,
   Braille, Legend, Position, White, Varnish. Lettura esatta.
2. **Nomi dei livelli OCG** — non e' lo standard ma i nomi sono espliciti:
   `Coldseal`, `White`, `Technical Drawing`, `Info Mad-e`, `Eyemark`,
   `Infopanel`, `VARNISH`, gia' separati dall'`Artwork`.
3. **Nomi delle separazioni** — la norma aiuta: un oggetto tecnico sovrapposto
   alla grafica *deve* essere tinta piatta in sovrastampa e *non puo'*
   chiamarsi All, None, Cyan, Magenta, Yellow o Black.
4. **Euristica** su spessore (filo di capello, <= 0,8 pt) e colore. Stima.

Due trappole viste sul campo:

- **Non colorare di bianco per neutralizzare.** Un tratto tecnico sopra la
  grafica lascia una riga bianca opaca. Vanno eliminate le operazioni di
  disegno, anche dentro i **Form XObject**: senza la ricorsione restano fuori
  cold seal e bianco coprente.
- **Il nome non basta.** Su Kinder Bueno Dark il nero era davvero fustella. Il
  criterio va incrociato con lo spessore.

Su stesi curvi il riconoscimento della penna non funziona: cerca segmenti
dritti lunghi, che su un settore non esistono. La regola dello spessore va
applicata anche senza penna riconosciuta.

## Astucci

`dieline.py` isola il tratto della fustella scegliendo la penna che accumula
piu' lunghezza **e** piu' cordonature distinte; scarta i riquadri dell'artwork
riconoscendoli dalla coppia contorno+riempimento; isola il gruppo connesso piu'
esteso per escludere i cartigli, recuperando pero' i gruppi che cadono
nell'ingombro (le alette con fianchi obliqui non toccano il corpo con tratti
dritti); valida le cordonature fascia per fascia, altrimenti le alette di presa
del cielo vengono scambiate per fianchi. Il verso di fasciatura, verticale o
orizzontale, si deduce dalla struttura.

## Flowpack

`flowpack.analyze_auto`:

1. le cordonature sono spesso tracciate con due guide equidistanti: tre linee
   ravvicinate e ugualmente spaziate sono **una piega sola, quella di mezzo**;
2. la fasciatura e' **simmetrica rispetto alla mezzeria del nastro**, quindi le
   pieghe stanno a coppie speculari: la coppia esterna separa retro e fianco,
   quella interna fianco e fronte;
3. le pinne di testa si misurano dal **margine non stampato**, non dalle linee
   di quota.

Verifica: perimetro + 2 falde deve dare la larghezza del nastro.

| | nastro | fronte | fianco | falda | somma |
|---|---|---|---|---|---|
| Milch-Schnitte T1 | 144,0 | 43,0 | 15,0 | 14,0 | 144,0 |
| FULFIL | 141,0 | 36,0 | 19,5 | 15,0 | 141,0 |
| Kinder Bueno Dark | 415,0 | 150,5 | 41,0 | 16,0 | 415,0 |

Regole di forma, da applicare senza chiedere:

- denti **equilateri**, contati sul **bordo della pinna** e non sul perimetro
  della sezione: base = bordo / numero denti, altezza = base x V3/2. Il taglio
  agisce solo sul bordo esterno, l'interno resta piano con le nervature delle
  ganasce;
- la **pinna longitudinale segue la forma del pack**, costruita come superficie
  offset della sezione; se troppo complessa va eliminata;
- **pinne laterali verso l'alto**;
- morbidezza e fedelta' della grafica tirano in direzioni opposte: la sezione a
  superellisse piena comprime il fronte del 17%. Serve **curvatura continua
  agli spigoli con centro piano**;
- l'apertura della pinna va concentrata vicino alla saldatura (rampa di quinto
  grado): con una rampa corta il gonfiore invade il corpo e deforma i bollini.

## Coppe e contenitori conici

Lo steso e' un **settore anulare**. Il contorno va letto appiattendo le bezier
dal content stream (`cup.py`): ne' la silhouette rasterizzata ne' i punti che
pdfplumber espone per le curve vanno bene, i secondi includono i punti di
controllo.

```
r_bocca = R2 * alpha / 2pi     r_fondo = R1 * alpha / 2pi
apotema = R2 - R1              altezza = radice(apotema^2 - (r_bocca - r_fondo)^2)
```

- **Il fronte si ancora al baricentro angolare della grafica**, non alla
  mezzeria geometrica del settore. Sulla coppa Nutella il baricentro dei pixel
  rossi cade a +8,86 gradi.
- **Con un render disponibile il fondo si allinea alla silhouette**: l'arco
  interno puo' non essere concentrico con l'esterno. Nutella POT: 72,0 mm da
  silhouette, poi confermati dal DT a 72,32, contro i 69,3 dell'artwork.
- Su `fit_sector` guardare **due numeri**, non uno. Residuo basso non basta se
  lo scarto fra gli angoli dei due archi e' alto: 0,001 mm con 14,5 gradi di
  scarto significa cerchio adattato al pezzo sbagliato di contorno.
- Il **fondo ha una cordonatura con rientranza**, leggibile dai cerchi
  concentrici del DT.

## Casi calibrati

Gli artwork il cui impaginato non rientra nei solutori automatici stanno nel
registro `CASI` in `server.py`, riconosciuti dalla firma della pagina. Oggi
contiene FULFIL Chocolate Hazelnut Whip.

## Assunzioni non verificate

- Il livello **Medio** di gonfiore e' interpolato fra Rigido e Morbido: manca un
  caso reale.
- Il **raggio di raccordo** e' trattato come proprieta' del film, quindi
  assoluto e non proporzionale allo spessore.
- L'**apertura della pinna** e' fissata al 94,8% di meta' perimetro, misurato su
  un solo render.
- Il **profilo del tappo** della coppa (cordonatura, arrotolatura, rientranza)
  e' stimato dal render: nessun documento lo riporta.
- Un'eventuale **sovrapposizione incollata** dello sleeve non e' misurabile dal
  PDF: se c'e', tutti i diametri calano.
