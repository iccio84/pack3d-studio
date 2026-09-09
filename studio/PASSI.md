# Da pack3d studio a Glam Viewer con Claude: passi in ordine

Cinque passi. Il primo e' indipendente e risolve il JPG; dal terzo in poi si
porta dentro l'app il ragionamento della chat.

---

## Passo 1 — Il JPG nel viewport (5 minuti, indipendente)

Il backend restituisce gia' un GLB. Se vedi un'immagine statica, l'app sta
chiamando l'endpoint sbagliato.

Apri la scheda **Network** del browser e carica un PDF:

- `POST /api/build` deve tornare `Content-Type: model/gltf-binary` e qualche MB;
- se torna `image/png`, l'app chiama un endpoint di render: correggi l'URL.

---

## Passo 2 — Viewport interattivo

```bash
npm i three @react-three/fiber @react-three/drei
```

Copia in `src/`:

- `frontend/Viewport.tsx` — canvas, OrbitControls, caricamento GLB
- `frontend/pack3d.ts` — client del backend

```tsx
const [url, setUrl] = useState<string | null>(null);
<Viewport url={url} />
```

`url` e' l'object URL restituito da `build()`. Il materiale viene forzato a
`FrontSide`: un modello con le normali girate deve vedersi subito.

Variabile d'ambiente su Lovable: `VITE_PACK3D_API` con l'indirizzo Render.

---

## Passo 3 — La chiave API su Render

Dashboard Render → il tuo servizio → **Environment** → aggiungi:

```
ANTHROPIC_API_KEY = sk-ant-...
PACK3D_MODEL      = claude-sonnet-4-6      (opzionale)
PACK3D_MAX_STEPS  = 16                     (opzionale)
```

La chiave sta **solo** sul backend. Se finisce nel frontend e' pubblica.

---

## Passo 4 — Carica i file nuovi

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

## Passo 5 — Il pannello nel frontend

Copia `frontend/Pannello.tsx`. Il flusso rispetta le regole:

1. si carica un PDF, solo PDF;
2. **prima domanda su ogni file**: Cartotecnico, Flowpack o Coppa conica;
3. se flowpack, due domande in piu': dentini in **campo numerico libero senza
   valori suggeriti**, e gonfiore;
4. `analyze-ai` porta le quote, `build` porta il GLB;
5. sotto al modello compaiono quote, livello di pulizia e avvisi.

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

Il **residuo** e' il numero che permette a Claude di scegliere fra due contorni
senza vederli. Sulla coppa Nutella, il DT in miniatura da' 0,000 mm contro
0,564 del contorno sotto la grafica.

Attenzione: residuo basso da solo non basta. Provando gli strumenti sul PDF
della coppa, un tracciato da' residuo 0,001 mm ma 14,5 gradi di scarto fra i
due archi: significa cerchio adattato al pezzo sbagliato di contorno. Per
questo `fit_sector` restituisce entrambi i numeri e le istruzioni dicono di
guardarli tutti e due.

## Cosa aspettarsi

- **Latenza** 20-60 secondi di analisi piu' 3-15 di costruzione. Serve uno
  stato visibile.
- **Costo** qualche centesimo a modello con un modello Sonnet.
- **Cache**: conviene memorizzare il JSON per firma del PDF, cosi' un file gia'
  visto salta direttamente alla costruzione.

## Cosa e' stato verificato e cosa no

Provato eseguendolo: i sei strumenti sul PDF vero della coppa, la
serializzazione dei risultati, il ciclo dell'agente con un cliente finto, gli
schemi dei tool.

**Non** provato: la chiamata all'API vera, perche' da qui non ho rete. Il
primo `curl` del passo 4 e' il collaudo da fare.
