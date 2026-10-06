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
| `pack3d/coda.py` | i casi nuovi respinti dal controllo, in un repository privato, con le note e le risposte di chi li ha caricati |
| `CODA.md` | come si lavora un caso della coda, anche dalla sessione automatica |
| `GLAM.md` | come chi ha caricato il PDF segue il suo caso da Glam Lab: stato, domande, risposte, modello corretto; il testo per Lovable |
| `prove/parco.py` | il parco: tutti i casi di prova ricostruiti come dal sito, prima e dopo una modifica; la prova sullo Space, l'invio a Glam Lab e lo stato dei casi per chi li ha caricati |
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


Da artwork PDF a modello 3D mappato. Carica il PDF, il sistema riconosce la
tipologia di packaging, ricostruisce la geometria dalla fustella e restituisce
un GLB scaricabile.

Tipologie coperte: astuccio a fasciatura verticale, astuccio a fasciatura
orizzontale, flowpack, vassoio espositore e display con plancia - la scatola
chiusa che si apre in espositore, costruita aperta - e pouch, la busta
stand-up col soffietto sul fondo. Per i flowpack vengono chieste zigrinatura
e tipo di gonfiore prima di costruire.
