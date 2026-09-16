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
| `server.py` | backend HTTP: `/api/analyze`, `/api/build`, `/api/analyze-ai` |
| `agent.py` | ciclo di tool use: Claude orchestra, il codice misura |
| `pack3d/tools.py` | strumenti esposti all'agente, controllo visivo compreso |
| `REGOLE.md` | le regole del progetto, usate come system prompt |
| `frontend/` | componenti React per il viewer |
| `PASSI.md` | messa in opera, passo per passo |
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
orizzontale, flowpack. Per i flowpack vengono chieste zigrinatura e tipo di
gonfiore prima di costruire.
