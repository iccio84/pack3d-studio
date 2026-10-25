---
title: pack3d studio
emoji: 📦
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# pack3d studio

Da artwork PDF a modello 3D mappato: la pipeline legge le quote dalla fustella,
ripulisce la grafica dal disegno tecnico e costruisce un GLB con la grafica
mappata sulle facce giuste.

## Struttura

| | |
|---|---|
| `pack3d/` | la pipeline: fustelle, flowpack, coppe coniche, pulizia, export |
| `server.py` | backend HTTP: `/api/analyze`, `/api/build`, `/api/analyze-ai`; `/api/nota` e `/api/risposta`, le parole di chi ha caricato un caso in coda |
| `agent.py` | ciclo di tool use: Claude orchestra, il codice misura |
| `pack3d/tools.py` | strumenti esposti all'agente, controllo visivo compreso |
| `pack3d/controllo.py` | il controllo dell'AI: il modello accanto all'artwork prima della consegna |
| `pack3d/vista.py` | il modello visto da quattro lati, dal GLB e senza GPU |
| `pack3d/incisioni.py` | l'apertura a strappo di un astuccio: i suoi tagli incisi come solchi nel modello chiuso |
| `pack3d/apertura.py` | la stessa apertura aperta di tot gradi sulla sua cerniera, con la scatola appoggiata sul retro |
| `pack3d/ballotin.py` | il ballotin, la scatola a tronco di piramide con gli spigoli a lente: la fustella letta faccia per faccia |
| `pack3d/materiali.py` | il materiale del film dai DT secondari: alluminio, white plate e vernice opaca diventano metallo e ruvidita' nel GLB |
| `pack3d/riempimento.py` | il riempimento: il vassoio espositore pieno dei suoi flowpack, un GLB solo con il flowpack una volta e un nodo per pezzo |
| `pack3d/steso.py` | la texture di ogni modello e' lo steso del PDF, pulito, nel verso del foglio e inquadrato sul DT: ci si sovrappone il nuovo artwork di una variante |
| `pack3d/texture.py` | la texture a parte: l'immagine del colore del GLB, da scaricare dalla pagina e per la sezione texture di Glam Lab |
| `pack3d/atlante.py` | i modelli di piu' fogli (coppa, cono, riempimento) con gli stesi dei loro PDF in un'immagine sola, una zona per pezzo: Glam e il template vogliono una texture |
| `pack3d/template.py` | il template PSD del modello per «Scarica Template» di Glam Lab: la texture e le guide UV (contorni, pieghe, area non modificabile, nomi delle facce) a livelli |
| `pack3d/rilievo.py` | l'embossing (o il debossing) dalla sua lastra: una mappa delle normali che mette in rilievo marchi e disegni sul modello |
| `pack3d/coda.py` | i casi nuovi respinti dal controllo, in un repository privato, con le note e le risposte di chi li ha caricati |
| `GLAM.md` | come chi ha caricato il PDF segue il suo caso da Glam Lab: stato, domande, risposte, modello corretto; il testo per Lovable |
| `prove/parco.py` | il parco: tutti i casi di prova ricostruiti come dal sito, prima e dopo una modifica (il rilascio della settimana); il giro di un caso in tre comandi (`prepara`, `consegna`, `approvato`), la prova sullo Space, l'invio a Glam Lab e lo stato dei casi per chi li ha caricati |
| `CODA.md`, `RILASCIO.md`, `MAPPA.md`, `FORME.md` | come si lavora un caso della coda, il rilascio della settimana, dove sta cosa nel codice, la ricetta per una forma nuova |
| `REGOLE.md` | le regole del progetto, usate come system prompt |
| `pack3d_studio.html` | l'interfaccia: viewer 3D, caricamento PDF, parametri |
| `PASSI.md` | l'agente: chiave API, strumenti, ciclo di tool use |
| `DEPLOY.md` | pubblicazione su Hugging Face Spaces o Render |

## Avvio rapido

```bash
pip install -r requirements.txt
python server.py          # http://localhost:8000
```

Per l'analisi guidata da Claude serve `ANTHROPIC_API_KEY` fra le variabili
d'ambiente del backend.


Da artwork PDF a modello 3D mappato. La pagina chiede prima la famiglia -
Flowpack, Pouch, Cartotecnico, Vassoio, Riempimenti, Incarti - poi i PDF che
servono a quella famiglia, uno per posto (agli incarti anche l'immagine del
prodotto da incartare), e le sue domande; il sistema ricostruisce la
geometria dalla fustella e restituisce un GLB scaricabile.

Tipologie coperte: astuccio a fasciatura verticale, astuccio a fasciatura
orizzontale, ballotin - la scatola a tronco di piramide coi coperchi in cima -,
flowpack, vassoio espositore e display con plancia - la scatola chiusa che si
apre in espositore, costruita aperta - e pouch, la busta stand-up col
soffietto sul fondo. Di un astuccio con l'apertura a strappo la pagina
chiede se lo si vuole chiuso - con la fustella dell'apertura incisa nel
cartone come sulla scatola vera, o liscio - o aperto di tot gradi: il
coperchio sollevato sulla sua cerniera e la scatola appoggiata sul retro. Un pack con
le finestre - il ballotin, l'astuccio col retro aperto fra due falde - fa
chiedere se ci va la pellicola trasparente, che di solito c'e' ma non
sempre. Se il DT ha la lastra dell'embossing, marchi e disegni escono in
rilievo. Per i flowpack vengono chieste zigrinatura, tipo di gonfiore,
apertura e saldatura delle pinne prima di costruire.

Il **riempimento** mette insieme due PDF, il pack (CU: un flowpack o un astuccio)
e il vassoio o il display: costruisce i due modelli, chiede quanti pack
mettere (vuoto vuol dire pieno) e li dispone frontali - la faccia stampata
verso il davanti, in file dal davanti al fondo - in un GLB solo.
