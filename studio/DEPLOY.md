# Mettere pack3d studio online

Serve un servizio che esegua il container: la pipeline e' Python e nel browser
non gira. Sotto la strada piu' rapida e una alternativa.

## A. Hugging Face Spaces — gratis, senza git, ~10 minuti

E' la via piu' semplice perche' i file si caricano dal browser.

1. Vai su https://huggingface.co/new-space
2. **Owner** il tuo account, **Space name** `pack3d-studio`
3. **License** a piacere, **Space SDK** scegli **Docker** → *Blank*
4. **Hardware** CPU basic (gratis), visibilita' **Public**
5. Crea lo Space, poi apri la scheda **Files** → **Add file** → **Upload files**
6. Trascina dentro **tutto il contenuto** della cartella `studio`:
   `Dockerfile`, `README.md`, `requirements.txt`, `server.py`,
   `pack3d_studio.html` e la cartella `pack3d/` intera
7. Conferma con **Commit changes to main**

La build parte da sola (5-10 minuti la prima volta). Quando lo stato diventa
*Running*, il link e':

```
https://huggingface.co/spaces/TUO-UTENTE/pack3d-studio
```

Chiunque lo apre puo' caricare un PDF e scaricare il GLB. Il `README.md` ha
gia' l'intestazione che serve agli Spaces, `app_port: 7860`.

**Attenzione:** gli Spaces gratuiti vanno in pausa dopo 48 ore di inattivita' e
si risvegliano alla prima visita, con qualche secondo di attesa.

## B. Render — gratis, richiede un repository

1. Metti la cartella `studio` in un repository GitHub
2. https://dashboard.render.com → **New** → **Web Service**
3. Collega il repository, **Language: Docker**, piano **Free**
4. Crea: Render assegna `PORT` da solo, il server la legge

URL finale: `https://pack3d-studio.onrender.com`. Il piano gratuito va in
sospensione dopo 15 minuti di inattivita'.

## Aggiornare dopo una nuova regola

Quando la pipeline cambia, sostituisci i file modificati (di solito qualcosa
dentro `pack3d/`) e fai commit: la build riparte e il link resta lo stesso.

## Verifiche fatte in locale prima della consegna

| prova | esito |
|---|---|
| Porta 7860 e `PORT` da ambiente | ok |
| Astuccio KMS T10 | 200, 915 kB, 5,5 s |
| Flowpack FULFIL, 20 denti morbido | 200, 3591 kB, 3,4 s |
| Tre costruzioni insieme | 200, 200, 503 (coda piena) |
| Ripresa dopo il carico | 200 |
| Preflight CORS da altro dominio | 204 |
| File non PDF | 400 con messaggio |

## Limiti

- **Una** costruzione alla volta (`PACK3D_MAX_JOBS`), la seconda riceve 503
  con invito a riprovare. Meglio respingere che far cadere il servizio.

  Il numero viene dalla memoria, non dalla CPU. Picchi misurati su
  `/api/analyze` piu' `/api/build` nello stesso processo, qualita' web.
  Lo steso e' nastro x passo sui flowpack, ingombro della fustella sugli
  astucci:

  | pack | tipologia | steso | picco | CPU |
  |---|---|---|---|---|
  | Colazione | flowpack | 460 x 330 mm | 434 MB | 20,0 s |
  | Nutella Donut | astuccio | 452 x 265 mm | 402 MB | 6,8 s |
  | K Pingui T6 | astuccio aperto | 261 x 270 mm | 354 MB | 4,6 s |
  | K Country | flowpack | 122 x 119 mm | 274 MB | 3,2 s |
  | K Brioss | flowpack | 420 x 290 mm | 247 MB | 4,4 s |
  | K Paradiso | flowpack | 165 x 155 mm | 233 MB | 2,4 s |
  | K Brioss STD | flowpack | 420 x 290 mm | 216 MB | 4,7 s |
  | K Tronky T1 | flowpack | 83 x 144 mm | 199 MB | 1,7 s |

  Presi tutti nello stesso giro e sulla stessa macchina, perche' il picco varia
  di qualche decina di MB col carico: Colazione, misurata prima, dava 386 MB
  contro i 434 di adesso, e il codice di allora rimisurato oggi da' 442. Le
  cifre servono a dimensionare, non a confrontare due versioni: per quello si
  misurano prima e dopo di seguito.

  Sui flowpack il picco e' quasi tutto nella rasterizzazione della pagina per
  l'analisi, e la costruzione costa fra 0,5 e 2,1 s. Sugli astucci e'
  rovesciato: l'analisi e' un paio di secondi e la costruzione se ne prende
  cinque, perche' ogni pannello si ritaglia e si ripulisce a 200 dpi.

  Le istanze Free e Starter di Render hanno 512 MB. Due costruzioni insieme
  non ci stanno: il kernel uccide il processo a meta' e chi aspettava riceve
  una risposta senza corpo, che nel browser diventa un errore senza testo. Su
  una macchina con piu' RAM si alza dall'ambiente.
- PDF fino a 60 MB.
- Nessuno stato conservato: i PDF finiscono in una cartella temporanea e
  vengono cancellati.
