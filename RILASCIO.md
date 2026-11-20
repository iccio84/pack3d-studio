# Il rilascio: subito, ogni volta che il codice cambia

Le istruzioni per portare sullo Space quello che e' stato unito in
`coda-settimana`. Valgono le stesse regole per risparmiare (CODA.md, *Prima
di tutto: risparmiare*): log su file e a video il riassunto, le immagini
solo dei casi cambiati, una per volta.

**Non si aspetta la settimana.** Fino al 2 novembre 2026 le correzioni
restavano in `coda-settimana` fino al rilascio della domenica: chi aveva
caricato un PDF poteva aspettare sette giorni un codice gia' pronto. Adesso
il rilascio si fa **subito dopo ogni unione** in `coda-settimana`, da chi
l'ha unita:

- la routine, dopo la `consegna` di un caso corretto (CODA.md, *Il giro*);
- una sessione che lavora sul codice, dopo l'unione della sua PR.

Costa tre quarti d'ora: il parco intero in locale, nella sessione, una
quarantina di minuti (punto 3; nelle Actions di `pack3d-casi` solo di
riserva, perche' costano minuti), poi lo Space che riparte e la prova del
caso. Nelle Actions il parco costruisce solo il codice nuovo: `main` la trova in cassa, perche' la cassa
ha la chiave sull'albero del codice e `main` ha lo stesso albero che il
rilascio prima ha appena provato; e dentro la cassa ogni caso ha la sua
impronta, cosi' il caso appena consegnato, nuovo nel parco, si costruisce
da solo (`prove/parco.py costruisci --riusa`). La chiave tiene anche la
macchina (l'impronta del processore): le macchine di GitHub non sono tutte
uguali e lo stesso codice da' GLB diversi al byte da un processore all'altro,
quindi una costruzione in cassa vale solo contro una della stessa macchina.
Su un processore che la cassa non ha ancora visto, `main` si ricostruisce
intera: il giro dura una ventina di minuti in piu'.

**POP e pack, nel parco.** Una PR del POP non cambia nessun caso dei pack, e
una dei pack nessun caso POP (regole/pop.md, *Il confine*): nel confronto del
parco ogni `CAMBIA` deve essere della parte della PR che si rilascia. Un caso
dell'altra parte che cambia ferma il rilascio, come una misura approvata. Senza correzioni non si rilascia niente:
il giro della routine che non trova casi non pubblica.

Resta una **rete di sicurezza**: il giro programmato della routine (quello
senza `routine-fire-payload`), prima di guardare la coda, rilascia quello
che fosse rimasto indietro - `coda-settimana` avanti a `main`, o casi
approvati da chiudere (punto 1).

1. **C'e' qualcosa da rilasciare?** Aggiorna i due repository. Se
   `git diff --quiet origin/main origin/coda-settimana` non trova differenze
   e non ci sono issue aperte con `da-rilasciare`, non c'e' niente: torna al
   giro. Se il codice e' uguale ma ci sono issue `da-rilasciare`, salta al
   punto 6: il codice e' gia' sullo Space, quei casi si provano e si
   chiudono.
2. **Fissa il ramo.** Annota lo SHA di `origin/coda-settimana`: provi e
   pubblichi quello, non quello che un'altra sessione unisce nel frattempo.
3. **Il parco serve?** Solo se cambia il codice che costruisce i modelli:

       python3 prove/parco.py serve origin/main <SHA> --casi ../pack3d-casi

   Esce con 1 se cambiano solo la pagina, le prove o i documenti: i modelli
   non possono cambiare, basta il controllo `prove` della PR, e si salta al
   punto 5. Con 0 dice quali file dei modelli cambiano, e il parco si fa:
   **intero** se cambia il nucleo dei pack o il comune (il server, il
   registro), che usano tutte le famiglie; **solo i casi delle famiglie
   toccate** se cambiano solo file propri di famiglie (`prove/confini.py`,
   regole/casi.md, *Una famiglia per PR*), e allora stampa la riga
   `--solo ...` da passare a `costruisci` e a `misure`. Il riempimento conta
   anche per la famiglia del pack che contiene, il flowpack e gli incarti
   vanno insieme; il giro del sabato rifa' comunque il parco intero.

   **Un parco per rilascio.** Lo SHA fissato al punto 2 porta tutte le PR
   gia' unite: un parco solo le prova tutte. Un'unione che arriva mentre il
   parco gira non ne fa partire un secondo: va nel rilascio dopo.

   **Il parco intero, prima e dopo, in locale, nella sessione.** Dal 19
   novembre 2026 e' la strada di serie: le Actions di `pack3d-casi`, privato,
   costano minuti (a novembre circa 3.000 in 19 giorni, contro i 2.000 del
   mese, e il 19 si sono fermate), il parco nella sessione no. La sessione ha
   i PDF (`../pack3d-casi`); le due costruzioni in parallelo, in background,
   una quarantina di minuti:

       git worktree add --detach <scratch>/prima origin/main
       git worktree add --detach <scratch>/dopo <SHA>
       (TMPDIR=<scratch>/tmp PACK3D_CACHE=<scratch>/tmp/c_prima python3 prove/parco.py costruisci ../pack3d-casi <scratch>/parco_prima --codice <scratch>/prima [--solo ...] > <scratch>/prima.log 2>&1 &
        TMPDIR=<scratch>/tmp PACK3D_CACHE=<scratch>/tmp/c_dopo python3 prove/parco.py costruisci ../pack3d-casi <scratch>/parco_dopo --codice <scratch>/dopo [--solo ...] > <scratch>/dopo.log 2>&1 & wait)
       python3 prove/parco.py esito <scratch>/parco_prima <scratch>/parco_dopo
       python3 prove/parco.py confronta <scratch>/parco_prima <scratch>/parco_dopo --immagini <scratch>/confronto
       python3 prove/parco.py misure ../pack3d-casi <scratch>/parco_dopo [--solo ...]
       python3 prove/parco.py stesi ../pack3d-casi <scratch>/parco_dopo [--solo ...]

   `[--solo ...]` e' la riga che ha stampato `serve`, se l'ha stampata;
   senza, il parco e' intero.

   `esito` e' il verdetto del parco delle Actions: rosso se un caso che con
   `main` si costruiva non si costruisce piu', o se una misura approvata
   cambia. `confronta` dice i modelli solo cambiati, coi nomi, e le viste
   affiancate stanno nella cartella `--immagini`: si guardano da li', una
   per volta. Nella PR verso `main` si scrive che il parco e' stato fatto
   in locale, coi numeri del riassunto.

   **Le Actions solo di riserva**: se la sessione non arriva ai PDF o non ha
   lo spazio per le due costruzioni. Il giro:

       gh api -X POST repos/iccio84/pack3d-casi/actions/workflows/parco.yml/dispatches -f ref=main -f "inputs[codice]=<SHA>"
       gh api "repos/iccio84/pack3d-casi/actions/workflows/parco.yml/runs?event=workflow_dispatch&per_page=1" --jq '.workflow_runs[0] | [.id, .status, .conclusion, .created_at] | @tsv'

   Aspetta che il giro finisca (controlla ogni cinque minuti; un altro parco
   in corso lo mette in fila): una ventina di minuti, quaranta se `main`
   manca in cassa. `conclusion` e' `success` se il verdetto e' verde; i
   modelli solo cambiati li dice il log del giro, nel passo «Le viste
   affiancate». Se il giro si chiude in pochi secondi senza log, i minuti
   del mese sono finiti: si torna al parco in locale.

4. **Si pubblica solo se sono vere tutte**:
   - il parco e' verde: nessun caso che prima si costruiva si e' rotto,
     nessuna misura approvata cambiata, oppure ognuna voluta e spiegata
     nella PR coi suoi numeri;
   - i modelli cambiati sono solo quelli dei casi corretti in questo
     rilascio - nel parco col loro `codice` - oppure ogni altro cambio e' un
     **miglioramento evidente**, guardato sulle viste affiancate (la
     cartella di `confronta`, o l'artefatto delle Actions) e spiegato caso
     per caso nella PR;
   - il controllo `prove` della PR verso `main` e' verde.

   Se un caso si e' rotto, trova quale correzione l'ha rotto e sistemala con
   una regola generale, con una PR verso `coda-settimana`; poi riparti dal
   punto 2. Se non ci riesci, non si pubblica: PR «Rilascio» verso `main` in
   bozza con la diagnosi, e scrivilo sulla issue del caso e nel riassunto.
   Il codice resta in `coda-settimana`, e la rete di sicurezza del giorno
   dopo lo ritrova.
5. **Pubblica**. Le statistiche dello Space non servono a mano: lo Space
   le salva da solo nel registro dei casi quando si spegne per ripartire
   col codice nuovo (`pack3d.statistiche`, `statistiche/spazio/`). PR da
   `coda-settimana` verso `main`,
   titolo «Rilascio <data>: <cosa>», con la regola nuova, i casi per codice
   (mai i nomi dei file: il repository e' pubblico) e cosa cambia sul parco,
   e unione con merge commit **allo SHA del punto 2** (se il ramo e' andato
   avanti l'unione si rifiuta: riparti dal punto 2). Gli stessi comandi
   delle PR dei casi (CODA.md, *Quando si unisce*), con `base=main` e
   `head=coda-settimana`. Controlla che il workflow "Sync to Hugging Face
   Spaces" sul commit di unione finisca con **success**.
6. **Lo Space**: da un clone di `main` aggiornato, `prove/parco.py spazio`
   aspetta che lo Space riparta col codice nuovo e costruisce i casi come un
   utente. Quanti, e con o senza il controllo dell'AI, lo dice il parco:

   - **I casi di questo rilascio e ogni issue `da-rilasciare`**, tutti in un
     comando solo (l'attesa dello Space la paga il primo), **col controllo
     dell'AI**: il verdetto serve alla issue e a Glam (`glam` manda solo un
     modello che il controllo ha detto "ok").

         python3 prove/parco.py spazio https://iccio-maurizio.hf.space ../pack3d-casi <nome>...

   - **Il parco ha cambiato dei modelli**: anche **un caso per famiglia** -
     flowpack, astuccio, ballotin, coppa, incarto, pouch, scatola a punta,
     riempimento, tubo, vassoio, ognuna col PDF piu' leggero
     (`_una_per_famiglia`) - **senza il controllo dell'AI**: dice se lo Space
     costruisce ogni famiglia, e le verifiche restano.

         python3 prove/parco.py spazio https://iccio-maurizio.hf.space ../pack3d-casi

   - **Il parco non ha cambiato niente** (0 cambiati) e il rilascio non ha
     casi: **una costruzione sola**, la piu' leggera, senza il controllo:
     basta a dire che lo Space e' ripartito col codice nuovo e costruisce.

         python3 prove/parco.py spazio https://iccio-maurizio.hf.space ../pack3d-casi --uno

   **Perche' cosi'.** Il controllo dell'AI e' una chiamata a Claude con le
   immagini, sulla chiave della console Anthropic. La prova per famiglia a
   ogni rilascio, col controllo acceso, ne faceva dieci: dal 9 al 12 novembre
   2026 le prove hanno fatto circa 137 controlli, gli utenti veri 3, e quasi
   tutti su modelli che il parco aveva appena trovato uguali al byte. Dal
   proprietario, il 12 novembre 2026: la prova per famiglia solo quando il
   parco cambia dei modelli, e le prove senza il controllo dell'AI tranne il
   caso che si rilascia. Lo Space lo salta solo per le prove che lo chiedono
   (`"prova": true` e `"controllo": false`, `server.senza_controllo`): un
   utente il controllo lo ha sempre. `--controllo si|no` lo decide a mano.

   Esce col codice peggiore. Sono prove: le richieste del parco portano
   `"prova": true` e non contano nelle statistiche dello Space
   (`pack3d.statistiche.in_prova`), che devono contare i PDF veri.
   - **"ok"** (uscita 0): se la issue e' `da-rilasciare` - chi l'ha
     caricato ha approvato - commenta col verdetto e il link al rilascio,
     togli `da-rilasciare` e chiudila come risolta. Se e' ancora
     `da-approvare`, commenta che la correzione e' sullo Space: la chiude il
     rilascio dopo l'approvazione (la rete di sicurezza, punto 1).
   - **"dubbio" o "sbagliato"** (uscita 1 o 2): commenta col verdetto e i
     difetti, metti `da-guardare` e lasciala aperta: il controllo non e'
     d'accordo, lo guarda chi gestisce il servizio.
   - **Lo Space non riparte** in 25 minuti (uscita 4), o un caso col
     controllo non l'ha avuto o non si e' costruito (uscita 3): scrivilo
     sulla issue; la riprova il giro dopo. Senza il controllo, una
     costruzione riuscita esce con 0 ("costruito").
   - **I lavoratori**: `curl -s https://iccio-maurizio.hf.space/api/lavori`
     dice quanti sono e la macchina che hanno visto (`macchina`). Devono
     essere tanti quante le vCPU dello Space; se no vedi DEPLOY.md, *Piu'
     vCPU: cosa comprano*, e scrivilo nel riassunto.
   - **La risorsa della colata**: `curl -s https://iccio-maurizio.hf.space/api/ping`
     deve dire `"colata": true`. Se dice `false` manca il secret `CASI_TOKEN`
     (DEPLOY.md, *La risorsa della colata*): scrivilo nel riassunto.
   - **Le statistiche della vita finita**: aggiorna il registro e guarda
     l'ultimo salvataggio,

         git -C ../pack3d-casi log -1 --format='%cr: %s' -- statistiche/spazio

     Se lo Space prima del rilascio aveva lavorato (gli eventi di
     `/api/statistiche` prima di pubblicare) e l'ultimo salvataggio e' di
     prima del rilascio, la chiusura non le ha salvate: scrivilo nel
     riassunto. Si perde al piu' un giorno, quello dopo il salvataggio
     quotidiano.

   Poi in `pack3d-casi` aggiorna `parco/riferimento/` con le viste nuove dei
   casi cambiati, e le loro misure approvate se la misura cambiata e'
   voluta (`prove/parco.py misure ... --solo <casi> --approva`), commit e
   push.
7. **Riallinea il ramo**: porta `main` dentro `coda-settimana` con una PR,
   come una correzione:

       gh api -X POST repos/iccio84/pack3d-studio/pulls -f base=coda-settimana -f head=main -f title="Riallinea coda-settimana a main" -f body="..." --jq .number
       gh api -X PUT repos/iccio84/pack3d-studio/pulls/<numero>/merge -f merge_method=merge -f sha=<sha di origin/main>

   Se `coda-settimana` contiene gia' `main` (`git merge-base --is-ancestor
   origin/main origin/coda-settimana`) non serve niente. Mai forzare.
   L'aggiornamento diretto del riferimento del ramo e l'API "merges" di
   GitHub, da una sessione cloud, il proxy non li permette.

Il parco del sabato notte, le varianti del 1 e del 15 del mese e le soglie
del venerdi' (Actions di `pack3d-casi`) restano: sono la rete che vede
quello che un rilascio non ha guardato. Dal 19 novembre 2026 girano meno
spesso - il parco era ogni notte, le varianti tre volte a settimana - per
stare nei minuti del mese.
