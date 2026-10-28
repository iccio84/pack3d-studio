# Il rilascio della settimana

Le istruzioni per il rilascio delle correzioni della settimana. Il giro di
un caso (CODA.md) non le legge: si leggono solo quando tocca al rilascio.
Valgono le stesse regole per risparmiare (CODA.md, *Prima di tutto:
risparmiare*): log su file e a video il riassunto, le immagini solo dei casi
cambiati, una per volta.

Una volta a settimana le correzioni di `coda-settimana` vanno sul sito, dopo
le prove che i giri dei casi saltano: il parco intero, prima e dopo, e i casi
della settimana sullo Space vero, col controllo dell'AI acceso. Lo fa il giro
programmato della routine (quello senza `routine-fire-payload`) quando
l'ultimo rilascio - l'ultima PR «Rilascio della settimana» unita in `main` -
ha piu' di sei giorni, o non ce n'e' ancora nessuno; si puo' fare anche a
mano. Si fa **prima** di guardare la coda.

1. **C'e' qualcosa da rilasciare?** Aggiorna i due repository. Se il ramo
   `coda-settimana` non c'e', o `git diff --quiet origin/main
   origin/coda-settimana` non trova differenze, e non ci sono issue aperte
   con `da-rilasciare`, non c'e' niente: torna al giro.
2. **Fissa il ramo.** Annota lo SHA di `origin/coda-settimana`: provi e
   pubblichi quello, non quello che un giro di un caso unisce nel frattempo.
3. **Parco prima e dopo**, per intero:

       git worktree add /tmp/prima origin/main
       git worktree add /tmp/dopo <SHA>
       python3 prove/parco.py costruisci ../pack3d-casi /tmp/parco_prima --codice /tmp/prima > /tmp/prima.log 2>&1
       python3 prove/parco.py costruisci ../pack3d-casi /tmp/parco_dopo --codice /tmp/dopo > /tmp/dopo.log 2>&1
       python3 prove/parco.py confronta /tmp/parco_prima /tmp/parco_dopo
       python3 prove/parco.py stesi ../pack3d-casi /tmp/parco_dopo

   e guarda **tutte** le immagini affiancate dei casi cambiati, una per una,
   leggendo il `come_deve_venire` di ognuno.
4. **Si pubblica solo se sono vere tutte**:
   - ogni caso della settimana (le issue `da-rilasciare`, nel parco col loro
     `codice`) e' giusto;
   - ogni altro caso del parco e' **identico al byte**, oppure cambia e il
     cambio e' un **miglioramento evidente**, spiegato caso per caso nella PR;
   - `confronta` non trova **misure approvate cambiate** (in fondo, «MISURE
     APPROVATE CAMBIATE»), oppure ognuna e' voluta e spiegata nella PR con i
     suoi numeri: una misura che cambia senza una ragione e' un caso rotto,
     anche se a occhio le viste sembrano uguali (il T1 del vassoio da 36 il
     26 ottobre: 40,1 -> 37,1 mm);
   - nessun caso del parco che prima si costruiva adesso fallisce;
   - `stesi` non trova texture girate: ognuna e' lo steso del suo PDF;
   - `python3 -m py_compile` passa sui file Python cambiati.

   Se un caso si e' rotto, trova quale correzione della settimana l'ha rotto
   e sistemala con una regola generale, con una PR verso `coda-settimana`
   come quelle dei casi; poi riparti dal punto 2. Se non ci riesci, non si
   pubblica: apri (o aggiorna) la PR «Rilascio della settimana» in bozza con
   la diagnosi, e scrivilo nel riassunto. I casi restano `da-rilasciare`: chi
   li ha caricati ha gia' il modello approvato.
5. **Pubblica**: PR da `coda-settimana` verso `main`, titolo «Rilascio della
   settimana <data>», con le regole della settimana, i casi per codice (mai i
   nomi dei file: il repository e' pubblico) e cosa cambia sul parco. Unisci
   con merge commit **allo SHA del punto 2** (l'expected head SHA: se il ramo
   e' andato avanti, l'unione si rifiuta, e riparti dal punto 2). Controlla
   che il workflow "Sync to Hugging Face Spaces" sul commit di unione finisca
   con **success**.
6. **Lo Space**: da un clone di `main` aggiornato, per ogni caso della
   settimana,

       python3 prove/parco.py spazio https://iccio-maurizio.hf.space ../pack3d-casi <nome> | tail -6

   che aspetta che lo Space riparta col codice nuovo e costruisce il caso
   come un utente, col controllo dell'AI acceso. Tutti i casi in un comando
   solo (un ciclo `for`): l'attesa dello Space la paga il primo.
   - **"ok"** (uscita 0): commenta la issue col verdetto e il link al
     rilascio, togli `da-rilasciare` e chiudila come risolta.
   - **"dubbio" o "sbagliato"** (uscita 1 o 2): commenta col verdetto e i
     difetti, metti `da-guardare` al posto di `da-rilasciare` e lasciala
     aperta. Chi l'ha caricato ha approvato il modello, ma il controllo non
     e' d'accordo: lo guarda chi gestisce il servizio.
   - **Lo Space non riparte** in 25 minuti (uscita 4) o il controllo non c'e'
     stato (uscita 3): scrivilo sulla issue e lasciala `da-rilasciare`; la
     riprova il rilascio dopo.

   Poi in `pack3d-casi` aggiorna `parco/riferimento/` con le viste nuove dei
   casi della settimana e dei casi cambiati, e le loro misure approvate:

       python3 prove/parco.py misure ../pack3d-casi /tmp/parco_dopo --solo <casi> --approva

   (solo i casi la cui misura cambiata e' voluta: le altre non si approvano),
   commit e push.
7. **Riallinea il ramo**: porta `main` dentro `coda-settimana` con una PR,
   come una correzione (CODA.md, *Quando si unisce nel ramo della
   settimana*):

       gh api -X POST repos/iccio84/pack3d-studio/pulls -f base=coda-settimana -f head=main -f title="Riallinea coda-settimana a main" -f body="..." --jq .number
       gh api -X PUT repos/iccio84/pack3d-studio/pulls/<numero>/merge -f merge_method=merge -f sha=<sha di origin/main>

   Se `coda-settimana` contiene gia' `main` (`git merge-base --is-ancestor
   origin/main origin/coda-settimana`) non serve niente. Mai forzare.
   L'aggiornamento diretto del riferimento del ramo e l'API "merges" di
   GitHub, da una sessione cloud, il proxy non li permette.

Poi torna al giro (CODA.md): se c'e' un caso libero, lavoralo.
