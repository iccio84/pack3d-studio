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
ANTHROPIC_API_KEY  = sk-ant-...
OPENAI_API_KEY     = sk-...        (solo per il piano B di ricostruzione)
PACK3D_MODEL      = claude-sonnet-5        (opzionale)
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

---

## Il GLB va da solo in viewport, nella sezione PDFto3D

Oggi il giro e' lungo: costruisci nel pannello, scarichi il GLB sul disco, lo
ritrovi, premi "Importa GLB in viewport". Tre passaggi a mano e un giro dal
filesystem per un file che sta gia' nella memoria del browser.

Con questa modifica, appena la costruzione finisce lo studio passa il modello
alla pagina che lo ospita: il pannello si chiude e il pack e' in viewport.

### Come si parlano le due parti

Lo studio sta in un iframe, quindi il passaggio e' una `postMessage`. La
stretta di mano serve a non spedire **mai** un file a `"*"`:

1. lo studio, se e' incorniciato, annuncia `pack3d:pronto` al genitore;
2. il viewer risponde `pack3d:ospite` all'origine dello studio;
3. lo studio si segna origine e finestra, e da li' in poi parla solo con
   quelle;
4. a costruzione finita manda `pack3d:modello` con `{nome, glb, avvisi}`.

L'annuncio va in tutte e due le direzioni, cosi' non conta chi dei due e'
pronto prima. Ma ognuno risponde **una volta sola**: rispondere a ogni
messaggio manda i due lati in rimpallo infinito, ed e' successo davvero
mettendolo in prova la prima volta.

Gli avvisi viaggiano con il modello di proposito. Chiudendosi il pannello, i
cartellini dello studio sparirebbero, e un `GRAFICA RUOTATA` o un
`ANALISI AUTOMATICA FALLITA` non e' una cosa che si possa lasciare indietro:
nel viewer diventano dei toast.

### Da copiare in Lovable

- `frontend/Pack3dStudioDialog.tsx` — sostituisce quello attuale: fa la
  stretta di mano, valida il GLB che arriva (magic `glTF`, limite 50 MB),
  chiude il pannello e chiama `onBuilt`.

### La sezione PDFto3D

In `src/routes/viewer.tsx`, `handlePdfBuilt` usa gia' una categoria, che e'
la macro-categoria dell'accordion nella sidebar. Basta cambiarne il nome nei
due punti:

```diff
-        category: "Pack 3D",
+        category: "PDFto3D",
...
-      const row = await uploadUserModel({ file, name, category: "Pack 3D" });
+      const row = await uploadUserModel({ file, name, category: "PDFto3D" });
```

La sezione compare da sola: `categories` e' costruita da `CATEGORIES` piu' le
categorie dei modelli utente, e `modelsByCategory` raggruppa nell'ordine di
dichiarazione.

Un'avvertenza: la sezione appare nella sidebar solo quando il modello viene
**salvato** (ramo admin). Per chi non e' admin il pack si vede in viewport ma
resta un `tempModel`, che non entra in `allModels`. Per mostrarlo comunque
serve includerlo:

```diff
-  const allModels = useMemo<ModelSpec[]>(
-    () => [...MODELS, ...userModels].filter((m) => !(hidden.models ?? []).includes(m.id)),
-    [userModels, hidden.models],
-  );
+  const allModels = useMemo<ModelSpec[]>(
+    () => [...MODELS, ...userModels, ...(tempModel ? [tempModel] : [])]
+      .filter((m) => !(hidden.models ?? []).includes(m.id)),
+    [userModels, hidden.models, tempModel],
+  );
```

Attenzione all'ordine: `tempModel` oggi e' dichiarato **dopo** `allModels`, e
una `const` letta prima della sua riga lancia. Va spostato sopra.

### Cosa e' stato verificato e cosa no

Provato eseguendolo, con un ospite finto su un'altra origine (porta diversa =
origine diversa, come fra Lovable e Render): stretta di mano chiusa in due
messaggi, costruzione vera di `KMS_T1.pdf`, GLB da 4.212.072 byte arrivato
all'ospite con i sei avvisi e la firma `glTF`, e l'origine registrata esatta.
Provato anche con un ospite ingenuo che si ripresenta a ogni messaggio: il
rimpallo si chiude lo stesso, perche' il freno sta dalla parte dello studio.

**Non** provato: il componente React dentro Lovable, che da qui non posso
montare. Le mie prove riproducono il suo protocollo, non il suo codice.
