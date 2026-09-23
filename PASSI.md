# L'agente: come Claude misura un artwork

Questo documento copre la parte dell'agente - le regole, gli strumenti di
misura, il ciclo di tool use. La costruzione del modello dal PDF sta in
`server.py` e non ha bisogno di niente di tutto questo: l'agente serve quando
le quote non si ricavano dai tracciati e vanno **guardate**.

Per mettere in piedi il servizio vedi `DEPLOY.md`.

---

## La chiave API su Render

Dashboard Render → il tuo servizio → **Environment** → aggiungi:

```
ANTHROPIC_API_KEY  = sk-ant-...
OPENAI_API_KEY     = sk-...        (solo per il piano B di ricostruzione)
PACK3D_MODEL      = claude-sonnet-5        (opzionale)
PACK3D_MAX_STEPS  = 16                     (opzionale)
```

La chiave sta **solo** sul backend. Se finisce nel frontend e' pubblica.

---

## I file dell'agente

Nel repository che Render sta usando:

| file | dove |
|---|---|
| `pack3d/tools.py` | strumenti di misura esposti a Claude |
| `agent.py` | ciclo di tool use |
| `REGOLE.md` | system prompt: le regole del progetto |
| `server.py` | contiene gia' `/api/analyze-ai` |
| `requirements.txt` | aggiunto `anthropic` |

Commit e push: Render ricostruisce da solo.

Prova dal terminale:

```bash
curl -X POST https://TUO-SERVIZIO.onrender.com/api/analyze-ai \
  -H "Content-Type: application/pdf" \
  -H 'X-Pack3d: {"kind":"cup"}' \
  --data-binary @NU_POT_Sleeve.pdf
```

Deve tornare un JSON con quote, avvisi e `_chiamate`, cioe' l'elenco degli
strumenti che Claude ha usato.

---

## Come funziona il ciclo

Claude non produce geometria: orchestra. Riceve le regole, chiama gli
strumenti, controlla che i conti chiudano e restituisce un JSON di venti righe.

| strumento | a cosa serve |
|---|---|
| `classify_technical` | livello di pulizia: ISO 19593, livelli OCG, separazioni, euristica |
| `list_paths` | tracciati con ingombro, **inclusi i DT in miniatura** |
| `fit_sector` | archi concentrici, apertura, **residuo** e scarto fra archi |
| `analyze_carton` | griglia fustella, verso di fasciatura, quote |
| `analyze_flowpack` | fasce, perimetro, saldature |
| `measure_region` | croma, margini non stampati, conteggio righe |
| `clean_artwork` | maschera DT, grafica salvata prima, riverniciatura a tinta piatta |
| `visual_check` | **guarda** il confronto prima/dopo: l'unico modo di accorgersi che manca un logo |
| `reconstruct_area` | piano B: GPT-Image-2.5 Sunburst dove il DT cade su foto |

Il **residuo** e' il numero che permette a Claude di scegliere fra due contorni
senza vederli. Sulla coppa Nutella, il DT in miniatura da' 0,000 mm contro
0,564 del contorno sotto la grafica.

Attenzione: residuo basso da solo non basta. Provando gli strumenti sul PDF
della coppa, un tracciato da' residuo 0,001 mm ma 14,5 gradi di scarto fra i
due archi: significa cerchio adattato al pezzo sbagliato di contorno. Per
questo `fit_sector` restituisce entrambi i numeri e le istruzioni dicono di
guardarli tutti e due.

## Cosa aspettarsi

- **Latenza** 20-60 secondi di analisi piu' 10-20 di costruzione su una
  macchina da 0,1 CPU. Serve uno stato visibile.
- **Costo** qualche centesimo a modello con un modello Sonnet.
- **L'analisi si fa una volta sola** per file, con memoria sull'impronta
  sha256: `/api/analyze` la calcola e `/api/build` la riusa invece di rifarla.
  Sul K Brioss sono sei secondi e mezzo di CPU e trecento MB risparmiati a
  ogni costruzione.

## Cosa e' stato verificato e cosa no

Provato eseguendolo: i sei strumenti sul PDF vero della coppa, la
serializzazione dei risultati, il ciclo dell'agente con un cliente finto, gli
schemi dei tool.

**Non** provato: la chiamata all'API vera, perche' da qui non ho rete. Il
primo `curl` del passo 4 e' il collaudo da fare.
