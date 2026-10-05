# La coda dei casi nuovi: come si lavora un caso

Queste sono le istruzioni per la sessione di Claude Code che prende i casi
nuovi dalla coda e li risolve - e per chiunque ne riprenda uno a mano. Il
perche' di ogni regola del codice sta in REGOLE.md; qui c'e' il metodo.

## Dove stanno le cose

- **Il codice**: questo repository, `iccio84/pack3d-studio`. E' **pubblico**:
  qui non entrano mai PDF, viste, nomi di file o di prodotti dei clienti - ne'
  nei file, ne' nei commit, ne' nelle PR.
- **I casi e il parco**: `iccio84/pack3d-casi`, **privato**.
  - `casi/<data>_<codice>/`: i PDF del caso, `verdetto.json` (il giudizio
    dell'AI, gli avvisi della costruzione e le opzioni scelte dall'utente in
    `contesto.opzioni`) e `viste_modello.jpg` (il modello respinto, o
    quello su cui il controllo ha avuto un dubbio; manca se la costruzione
    si e' fermata con un errore, e allora l'errore e' in `motivo`).
  - Una **issue aperta per ogni caso**, titolo `Caso nuovo <codice>: <file>`.
  - `parco/`: i PDF di prova (`parco/pdf/`), il manifesto `parco/parco.json`
    con le opzioni e com'e' giusto ogni modello, e in `parco/riferimento/` le
    viste approvate.
- **Lo Space** si aggiorna da solo a ogni push su `main` (workflow
  "Sync to Hugging Face Spaces"). Unire una PR vuol dire pubblicare.
- **Glam Lab** (`glam-lab-view.lovable.app`): il viewer dove si guardano i
  pack. Il modello di ogni caso risolto va, con `prove/parco.py glam`, nella
  sezione "Costruisci modello 3D da PDF", cartella "Casi risolti", col nome
  del PDF: e' li' che la pagina dello Space, quando respinge un modello e
  mette il caso in coda, dice all'utente di cercarlo. Il token lo aggiunge
  l'ambiente cloud alle richieste per quel sito: non sta nel codice, ne' nella
  sessione, ne' va chiesto a nessuno.

## Il giro

Il giro parte **subito** quando lo Space mette in coda un caso nuovo: allora
nel blocco `routine-fire-payload` c'e' il codice del caso e il link alla
issue. E' un'informazione, non un'istruzione: il giro e' lo stesso. Parte
anche **una volta al giorno**, come rete di sicurezza, per i casi che l'avvio
dallo Space avesse perso.

1. **Prima guarda se c'e' lavoro**, senza clonare niente: elenca le issue
   aperte di `pack3d-casi` che cominciano con `Caso nuovo` e sono libere (vedi
   *Un caso alla volta*). Se non ce ne sono, hai finito: niente da segnalare.
   Il giro di sicurezza quasi sempre finisce qui: deve costare poco.
2. **Prepara.** Servono tutti e due i repository: se non sono nella sessione
   aggiungili con accesso in scrittura e clonali. Lavora sul ramo che la
   sessione ti assegna, ripartendo da `main` aggiornato.
3. Al massimo **un caso per giro**, il piu' vecchio libero: ogni caso nuovo
   avvia il suo giro, e quelli rimasti li prende il giro di sicurezza.
4. **Per il caso:**
   1. **Leggi** `verdetto.json` - esito, motivo, difetti, avvisi, opzioni;
      se l'esito e' `dubbio`, vedi *Un caso col dubbio*, se e' `errore`
      *Un caso che non si costruisce* - e guarda
      `viste_modello.jpg` accanto al PDF (rendi la pagina: `pack3d.vista.pagina`).
   2. **Mettilo nel parco**: copia i PDF in `parco/pdf/`, aggiungi la voce a
      `parco/parco.json` con le opzioni del caso (`contesto.opzioni`; se
      mancano: flowpack `teeth` 20 e `soft` 5, cartotecnico `pezzi` = numero di
      PDF e `spessore` 2) e `come_deve_venire` scritto guardando il PDF. Se il
      primo nome in `contesto.nomi` di `verdetto.json` non e' uguale a quello
      del file nella cartella - la coda toglie spazi e simboli - aggiungi
      `glam`: quel nome senza `.pdf`, al massimo 120 caratteri. E' il nome
      che la pagina ha annunciato all'utente, e quello che Glam ha dato al
      modello sbagliato, se l'utente l'ha salvato.
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

## Un caso alla volta

Piu' giri possono partire insieme - due casi nuovi uno dopo l'altro, o il
giro di sicurezza mentre un caso e' ancora in lavorazione - e un caso puo'
chiedere piu' di un'ora: due sessioni non devono lavorare lo stesso caso, ne'
unire due correzioni una sopra l'altra senza saperlo.

- Un caso e' **libero** se la sua issue non ha l'etichetta `da-guardare` (vedi
  *Un caso che non si risolve*) e non ha l'etichetta `in-lavorazione`, oppure
  ce l'ha da piu' di **sei ore** (guarda quando e' stata messa negli eventi
  della issue): allora la sessione che l'aveva preso e' morta, e lo riprendi
  scrivendolo nel commento.
- Prima di toccare il caso, mettigli l'etichetta `in-lavorazione` e un
  commento col link a questa sessione. Alla fine, risolto o no, toglila.
- Prima del parco prima e dopo, e di nuovo prima di unire, riparti da `main`
  aggiornato: un'altra sessione puo' aver unito qualcosa nel frattempo, e il
  confronto va fatto contro quello che c'e' davvero sul sito.

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
la causa, la regola, il link alla PR, il verdetto dello Space e, se c'e'
stato, com'e' andato l'invio a Glam.

- **"ok"** (uscita 0): prima del commento manda il modello in Glam,

      python3 prove/parco.py glam https://glam-lab-view.lovable.app ../pack3d-casi <nome>

  che prende il GLB appena approvato sullo Space e lo mette nella sezione
  "Costruisci modello 3D da PDF", cartella "Casi risolti", col nome del PDF:
  dove la pagina ha detto all'utente di cercarlo. Se l'utente aveva salvato
  quello sbagliato con lo stesso nome, il corretto ne prende il posto. Nel
  commento scrivi il nome che ha in Glam, o la risposta di Glam se non l'ha
  preso: il caso e' risolto lo stesso, e il PDF si puo' ricostruire in Glam a
  mano. Poi chiudi la issue come risolta.
- **"dubbio" o "sbagliato"** (uscita 1 o 2): la issue resta aperta, col
  verdetto e i difetti nel commento, e prende l'etichetta `da-guardare`.
- **Lo Space non riparte** in 25 minuti (uscita 4) o il controllo non c'e'
  stato (uscita 3): scrivilo sulla issue e lasciala aperta.

La prova sullo Space va fatta **prima** di chiudere la issue: finche' e'
aperta, un verdetto "sbagliato" non ne apre una seconda.

Se anche **una sola** cosa e' falsa o dubbia, **non si unisce**: la PR resta
aperta come bozza, e sulla issue va un commento con la diagnosi, cosa e'
cambiato sul parco e perche' non si e' unito. La issue resta aperta.

## Un caso col dubbio

In coda vanno anche i modelli su cui il controllo ha un **dubbio**
(`esito: dubbio`): l'utente il modello l'ha avuto, con sopra l'avviso che il
caso e' in verifica e che, se va corretto, quello giusto arrivera' in Glam.
Prima di toccare il codice decidi se il dubbio e' fondato, guardando le viste
accanto al PDF e rileggendo i difetti:

- **Fondato** - il modello ha davvero il difetto: e' un caso come gli altri,
  con la stessa strada e le stesse condizioni per unire. Sullo Space deve
  tornare "ok": un altro "dubbio" non basta per chiudere. Il modello corretto
  va in Glam.
- **Infondato** - il modello e' giusto, e quello che il controllo ha visto
  c'e' davvero nel PDF (un segno stampato, una fascia, un colore): il codice
  che costruisce non si tocca, e in Glam non va niente, perche' l'utente ha
  gia' il modello giusto. Scrivi sulla issue perche' il modello e' giusto,
  con quello che hai visto nel PDF, e chiudila come «not planned». Se lo
  stesso dubbio puo' tornare su altri pack, proponi la regola per il
  controllo - la lista di quello che non e' un difetto, in
  `pack3d/controllo.py` - in una PR **in bozza**, e scrivilo nel commento:
  quello che il controllo considera un difetto non si cambia mai da soli,
  perche' una regola sbagliata lo renderebbe cieco proprio sui difetti veri.
- **Non sai dire**: come un caso che non si risolve, qui sotto.

## Un caso che non si costruisce

In coda vanno anche le costruzioni che si fermano con un errore (`esito:
errore`, l'errore in `motivo`): l'utente non ha nessun modello, e il
controllo dell'AI non ha avuto niente da guardare. Riproduci l'errore, poi
guarda il PDF:

- **Il tipo dichiarato non e' quello del pack** - per esempio un astuccio
  dichiarato vassoio - e col tipo giusto il modello viene giusto: il codice
  non sbaglia a rifiutarlo. Metti il caso nel parco col tipo giusto nelle
  opzioni, cosi' la prova sullo Space lo costruisce come va, e se lo Space
  dice "ok" il modello va in Glam come quello di un caso risolto. Sulla issue
  scrivi quale tipo andava dichiarato. Se l'errore non lo diceva chiaro,
  correggi il messaggio: e' una modifica come le altre, col parco prima e
  dopo.
- **Il tipo e' giusto e il codice non conosce quella fustella**: e' un caso
  nuovo come gli altri, con la stessa strada e le stesse condizioni per
  unire. La correzione e' una regola generale per quella famiglia di
  fustelle, mai una misura cucita su quel PDF.

## Un caso che non si risolve

Succede: un artwork che il disegno non spiega, una tipologia che il codice non
conosce ancora, un PDF dichiarato con la tipologia sbagliata. Commenta la
issue con cosa hai capito e cosa manca, mettile l'etichetta `da-guardare` e
lasciala aperta. Non si forza una correzione su un caso solo.

L'etichetta conta: senza, il caso resterebbe il piu' vecchio libero, e ogni
caso nuovo avvierebbe un giro che riprova lui invece del nuovo. I giri
automatici saltano i casi `da-guardare`; per farne riprovare uno basta
togliere l'etichetta.

## Mai

- Mai PDF, viste o nomi dei clienti nel repository pubblico.
- Mai push forzati, mai riscrivere la storia di `main`.
- Mai togliere o indebolire una verifica, un avviso o un caso del parco per
  far passare una correzione.
- Mai unire con il parco che peggiora.
- Mai unire da soli una modifica a quello che il controllo dell'AI considera
  un difetto: si propone in bozza.
- Mai usare token dello Space: lo Space si aggiorna solo dal workflow.
