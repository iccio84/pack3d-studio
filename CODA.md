# La coda dei casi nuovi: come si lavora un caso

Queste sono le istruzioni per la sessione di Claude Code che ogni giorno
prende i casi nuovi dalla coda e li risolve - e per chiunque ne riprenda uno a
mano. Il perche' di ogni regola del codice sta in REGOLE.md; qui c'e' il
metodo.

## Dove stanno le cose

- **Il codice**: questo repository, `iccio84/pack3d-studio`. E' **pubblico**:
  qui non entrano mai PDF, viste, nomi di file o di prodotti dei clienti - ne'
  nei file, ne' nei commit, ne' nelle PR.
- **I casi e il parco**: `iccio84/pack3d-casi`, **privato**.
  - `casi/<data>_<codice>/`: i PDF del caso, `verdetto.json` (il giudizio
    dell'AI, gli avvisi della costruzione e le opzioni scelte dall'utente in
    `contesto.opzioni`) e `viste_modello.jpg` (il modello respinto).
  - Una **issue aperta per ogni caso**, titolo `Caso nuovo <codice>: <file>`.
  - `parco/`: i PDF di prova (`parco/pdf/`), il manifesto `parco/parco.json`
    con le opzioni e com'e' giusto ogni modello, e in `parco/riferimento/` le
    viste approvate.
- **Lo Space** si aggiorna da solo a ogni push su `main` (workflow
  "Sync to Hugging Face Spaces"). Unire una PR vuol dire pubblicare.

## Il giro di ogni giorno

1. **Prepara.** Servono tutti e due i repository: se `pack3d-casi` non e' nella
   sessione aggiungilo con accesso in scrittura. Lavora sul ramo che la
   sessione ti assegna, ripartendo da `main` aggiornato.
2. **Elenca** le issue aperte di `pack3d-casi` che cominciano con
   `Caso nuovo`. Se non ce ne sono, hai finito: niente da segnalare.
   Al massimo **tre casi per giro**, dal piu' vecchio: gli altri al giro dopo.
3. **Per ogni caso:**
   1. **Leggi** `verdetto.json` - motivo, difetti, avvisi, opzioni - e guarda
      `viste_modello.jpg` accanto al PDF (rendi la pagina: `pack3d.vista.pagina`).
   2. **Mettilo nel parco**: copia i PDF in `parco/pdf/`, aggiungi la voce a
      `parco/parco.json` con le opzioni del caso (`contesto.opzioni`; se
      mancano: flowpack `teeth` 20 e `soft` 5, cartotecnico `pezzi` = numero di
      PDF e `spessore` 2) e `come_deve_venire` scritto guardando il PDF.
   3. **Riproduci** col codice di oggi:
      `python3 prove/parco.py costruisci ../pack3d-casi /tmp/caso --solo <nome>`.
   4. **Trova la causa** nel codice. La correzione e' una **regola generale**:
      mai il nome del file, il codice del cliente, o misure cucite su quel
      PDF. Se l'errore non si spiega con una regola, il caso non si risolve
      oggi (vedi sotto).
   5. **Parco prima e dopo**, sempre per intero:

          git worktree add /tmp/prima origin/main
          python3 prove/parco.py costruisci ../pack3d-casi /tmp/parco_prima --codice /tmp/prima
          python3 prove/parco.py costruisci ../pack3d-casi /tmp/parco_dopo
          python3 prove/parco.py confronta /tmp/parco_prima /tmp/parco_dopo

      e guarda **tutte** le immagini affiancate dei casi cambiati, una per una,
      leggendo il `come_deve_venire` di ognuno.
   6. **Scrivi la regola** in REGOLE.md: il caso, la causa, la regola, cosa
      cambia sul parco. Come le altre: con i numeri.

## Quando si unisce da soli

La PR si unisce senza chiedere **solo se sono vere tutte**:

- il caso nuovo adesso e' giusto: guardando le viste accanto al PDF, con
  l'occhio del controllo AI - forma, verso, fronte sul fronte, retro, nessun
  segno tecnico;
- ogni caso del parco e' **identico al byte**, oppure cambia e il cambio e'
  un **miglioramento evidente**, spiegato caso per caso nella PR;
- nessun caso del parco che prima si costruiva adesso fallisce;
- `python3 -m py_compile` passa su ogni file Python toccato.

Allora: commit, push, PR verso `main`, unione con merge commit, e controlla
che il workflow "Sync to Hugging Face Spaces" sul commit di unione finisca con
**success**. Poi, da un clone di `main` aggiornato, la **prova sullo Space
vero**:

    python3 prove/parco.py spazio https://iccio-maurizio.hf.space ../pack3d-casi <nome>

Aspetta che lo Space riparta col codice nuovo - `/api/ping` dice l'impronta
del codice in esecuzione - e costruisce il caso come un utente, col controllo
dell'AI acceso. Poi, in `pack3d-casi`: aggiorna `parco/riferimento/` con le
viste nuove del caso e dei casi cambiati, commit e push; commenta la issue con
la causa, la regola, il link alla PR e il verdetto dello Space.

- **"ok"** (uscita 0): chiudi la issue come risolta.
- **"dubbio" o "sbagliato"** (uscita 1 o 2): la issue resta aperta, col
  verdetto e i difetti nel commento. Il caso torna il giorno dopo.
- **Lo Space non riparte** in 25 minuti (uscita 4) o il controllo non c'e'
  stato (uscita 3): scrivilo sulla issue e lasciala aperta.

La prova sullo Space va fatta **prima** di chiudere la issue: finche' e'
aperta, un verdetto "sbagliato" non ne apre una seconda.

Se anche **una sola** cosa e' falsa o dubbia, **non si unisce**: la PR resta
aperta come bozza, e sulla issue va un commento con la diagnosi, cosa e'
cambiato sul parco e perche' non si e' unito. La issue resta aperta.

## Un caso che non si risolve

Succede: un artwork che il disegno non spiega, una tipologia che il codice non
conosce ancora. Commenta la issue con cosa hai capito e cosa manca, e lasciala
aperta. Non si forza una correzione su un caso solo.

## Mai

- Mai PDF, viste o nomi dei clienti nel repository pubblico.
- Mai push forzati, mai riscrivere la storia di `main`.
- Mai togliere o indebolire una verifica, un avviso o un caso del parco per
  far passare una correzione.
- Mai unire con il parco che peggiora.
- Mai usare token dello Space: lo Space si aggiorna solo dal workflow.
