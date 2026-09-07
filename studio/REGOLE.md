# Regole applicate dalla pipeline

Elenco delle regole accumulate finora, con il punto del codice che le applica.
Serve sia come documentazione sia come traccia per chi mette mano al progetto.

## Domande all'utente

| regola | dove |
|---|---|
| Su ogni PDF chiedere prima la tipologia: Cartotecnico, Flowpack, Altro. La tipologia si dichiara, non si indovina. | `pack3d_studio.html` (pannello tipo) + `server.analyze_pdf(pdf, kind)` |
| Solo per flowpack: chiedere il numero esatto di dentini, digitato dall'utente. Nessuna alternativa proposta, 0 = pinne lisce. | campo numerico senza valore predefinito |
| Solo per flowpack: chiedere il gonfiore fra Rigido, Medio, Morbido. | `server.GONFIORE` |
| "Altro" non e' ancora supportato. | risposta 400 |

Nessun'altra domanda va posta durante la costruzione.

## Regole applicate senza chiedere

**Comuni a tutte le tipologie**

- Confrontare sempre il modello finito con lo steso: la grafica sul 3D deve
  avere lo stesso orientamento del PDF, mai specchiata o capovolta.
- Non distorcere mai la grafica. I bollini circolari devono restare cerchi.
  Ogni pannello va sulla faccia corrispondente e centrato.
- Verificare il verso delle normali. L'attributo NORMAL non basta: conta
  l'avvolgimento dei triangoli, ed e' quello che i viewer usano per il culling.
  `exporters` scrive gli indici in senso antiorario visto da fuori.
- Eliminare il disegno tecnico dall'artwork usando i livelli o le separazioni
  del PDF quando ci sono. **Non colorare di bianco**: un tratto tecnico sopra
  la grafica lascerebbe una riga bianca. Vanno eliminate le operazioni di
  disegno, anche dentro i Form XObject (`server.strip_separations`).
  Quando le separazioni non esistono si usa la regola del tratto a filo di
  capello, spessore <= 0,8 pt (`folding._technical_mask`).

**Solo flowpack**

- I denti sono triangoli equilateri contati sul **bordo della pinna**, non sul
  perimetro della sezione: base = bordo / numero denti, altezza = base x V3/2.
  Il taglio agisce solo sul bordo esterno, l'interno resta piano con le sole
  nervature delle ganasce (`flowpack.build_mesh`, `serr_teeth`).
- Il numero di denti non e' deducibile dalla dimensione. Controesempio:
  Milch-Schnitte 30 denti su bordo 55 mm = passo 1,83; Kinder Bueno Dark 30
  denti su bordo 181,5 mm = passo 6,05. Fattore 3,3 a parita' di conteggio.
- La pinna longitudinale deve seguire la forma del pack, non essere un
  rettangolo piatto sospeso; se troppo complessa va eliminata
  (`flowpack.fin_on_surface`, superficie offset della sezione).
- Le pinne laterali vanno rivolte verso l'alto.

## Come vengono lette le quote

**Astucci** — `dieline.py` isola il tratto della fustella scegliendo la penna
che accumula piu' lunghezza *e* piu' cordonature distinte, scarta i riquadri
dell'artwork riconoscendoli dalla coppia contorno+riempimento, isola il gruppo
connesso piu' esteso per escludere cartigli, e valida le cordonature fascia per
fascia. Il verso di fasciatura, verticale o orizzontale, viene dedotto dalla
struttura.

**Flowpack** — `flowpack.analyze_auto`:

1. le cordonature sono spesso tracciate con due guide equidistanti: tre linee
   ravvicinate e ugualmente spaziate sono una piega sola, quella di mezzo
   (`_collapse_guides`);
2. la fasciatura e' simmetrica rispetto alla mezzeria del nastro, quindi le
   pieghe stanno a coppie speculari: la coppia esterna separa retro e fianco,
   quella interna fianco e fronte (`solve_bands`);
3. le pinne di testa si misurano dal margine non stampato, non dalle linee di
   quota.

Verificato esatto su Milch-Schnitte T1 e Kinder Bueno Dark:

| | nastro | fronte | fianco | falda | perimetro + 2 falde |
|---|---|---|---|---|---|
| Milch-Schnitte T1 | 144,0 | 43,0 | 15,0 | 14,0 | 144,0 |
| Kinder Bueno Dark | 415,0 | 150,5 | 41,0 | 16,0 | 415,0 |

## Casi calibrati

Gli artwork il cui impaginato non rientra nel solutore automatico stanno nel
registro `CASI` in `server.py`, riconosciuti dalla firma della pagina. Oggi
contiene FULFIL Chocolate Hazelnut Whip.

## Assunzioni non ancora verificate

- Il livello **Medio** di gonfiore e' interpolato fra Rigido e Morbido: manca
  un caso reale su cui tararlo.
- Il raggio di raccordo e' trattato come proprieta' del film, quindi assoluto e
  non proporzionale allo spessore. Su Kinder Bueno Dark, spesso 41 mm contro i
  15 del Milch-Schnitte, questo produce uno spigolo proporzionalmente molto
  piu' vivo. Da verificare su una foto.
- L'apertura della pinna e' fissata al 94,8% di meta' perimetro, valore
  misurato su un solo render.
