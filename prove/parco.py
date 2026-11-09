"""Il parco: tutti i casi di prova ricostruiti come li costruisce il sito.

I PDF stanno nel repository PRIVATO dei casi (cartella `parco/` di
iccio84/pack3d-casi), mai qui: sono artwork dei clienti, e questo repository
e' pubblico. Qui c'e' solo lo strumento.

    python3 prove/parco.py costruisci CASI USCITA [--codice DIR] [--solo a,b] [--riusa]
    python3 prove/parco.py confronta PRIMA DOPO [--immagini DIR]
    python3 prove/parco.py esito PRIMA DOPO [--ieri DIR] [--titolo TESTO] [--riassunto FILE]
    python3 prove/parco.py stesi CASI USCITA [--solo a,b]
    python3 prove/parco.py misure CASI USCITA [--solo a,b] [--approva]
    python3 prove/parco.py letture CASI [--codice DIR] [--solo a,b] [--approva]
    python3 prove/parco.py spazio URL CASI NOME [--uscita DIR] [--attendi MIN]
    python3 prove/parco.py glam URL CASI NOME [--uscita DIR] [--categoria TESTO]
    python3 prove/parco.py caso URL CASI CODICE --stato STATO [--messaggio TESTO]
                                [--domanda TESTO --opzione TESTO ... [--anteprima NOME]]
    python3 prove/parco.py prepara CASI CODICE [--riprendi]
    python3 prove/parco.py verifica CASI CODICE
    python3 prove/parco.py varianti CASI USCITA [--famiglia KIND] [--varianti giro90,scala1.03]
    python3 prove/parco.py consegna CASI CODICE --messaggio TESTO --commento TESTO
                                    [--senza-verifica MOTIVO]
    python3 prove/parco.py approvato CASI CODICE
    python3 prove/parco.py prossimo CASI CODICE
    python3 prove/parco.py versione [--codice DIR]

`costruisci` avvia un server col codice di DIR (di serie quello di questo
repository), con il controllo dell'AI e la coda spenti, e per ogni caso di
CASI/parco/parco.json manda i PDF a /api/build con le opzioni del caso, come
fa la pagina. In USCITA salva per ogni caso il GLB, gli avvisi della
costruzione e le quattro viste (`pack3d.vista`), e la lettura del PDF
che la pagina mette accanto al modello (`pack3d.lettura`), se c'e'.

`confronta` dice quali modelli sono cambiati fra due costruzioni, con gli
avvisi che cambiano, e per ognuno affianca le viste: PRIMA sopra, DOPO sotto.
Le immagini finiscono in DIR, di serie DOPO/confronto.

`costruisci` misura anche ogni modello (`pack3d.misure`: l'ingombro, i
pezzi, il flowpack lungo, largo e spesso, lo stiro della grafica del fronte)
e lo confronta con le misure approvate del caso, `misure` nel manifesto: una
misura approvata che cambia oltre la tolleranza la dice sotto il caso e in
`misure_cambiate`. `confronta` le riassume tutte. Un modello cambiato a
misure approvate ferme e' un cambio che non si vede; una misura cambiata va
spiegata, o e' un difetto.

`misure` rifa' il confronto su una costruzione gia' fatta, dal GLB; con
`--approva` scrive le misure di quei modelli nel manifesto come approvate:
dopo un rilascio, per i casi cambiati, o quando un cambio e' voluto. Il giro
di un caso le scrive con `consegna`, insieme a `come_deve_venire`.

`stesi` controlla che la texture di ogni modello sia lo steso del suo PDF
(REGOLE.md, *La texture e' lo steso*): cerca ogni texture - e ogni zona di
un atlante, quello dei modelli di piu' fogli - sulla prima pagina del PDF
senza i livelli tecnici e senza le lastre che coprono la grafica,
girata di 0, 90, 180 o 270 gradi e a scale
diverse, e dice dove combacia meglio. Deve combaciare dritta, a scala
uniforme. Esce con 1 se una texture combacia nettamente meglio girata; una
"incerta" (un pack quasi simmetrico pareggia dritto e capovolto) o una che non
si ritrova sulla pagina va guardata a occhio, ma non conta come errore.

`spazio` prova un caso sullo Space vero, dopo una pubblicazione: aspetta che
/api/ping dica la versione di questo clone (`pack3d/versione.py`), cioe' che
lo Space sia ripartito col codice nuovo, poi costruisce il caso come la pagina
e stampa il verdetto del controllo dell'AI. Esce con 0 se e' "ok", 1 se e'
"dubbio", 2 se e' "sbagliato", 3 se il controllo non c'e' stato, 4 se lo
Space non e' ripartito in tempo. Attenzione: sullo Space il controllo e la
coda sono accesi, e un caso "sbagliato" va in coda come quelli degli utenti.

`glam` manda a Glam Lab, il viewer dove si guardano i pack, il modello che
`spazio` ha appena costruito sullo Space - solo se il controllo ha detto "ok",
e proprio quel GLB, non una costruzione nuova. Per un caso della coda manda
il modello che chi l'ha caricato ha approvato (`modello.glb` nella cartella
del caso), e solo dopo l'approvazione. Glam lo mette nella sezione
"Costruisci modello 3D da PDF", cartella "Casi risolti", col nome del PDF:
quello che Glam da' a un modello costruito da li', e quello che la pagina
annuncia a chi ha caricato il caso respinto. Il token non sta qui: lo
aggiunge l'ambiente cloud alle richieste per quel sito (API credentials,
vedi DEPLOY.md).

Con `codice` nel manifesto - il caso arrivato dalla coda - `glam` lo dice a
Glam (X-Pack3d-Codice), che mette il modello a chi ha caricato quel caso.

`caso` dice a Glam Lab a che punto e' un caso della coda, per chi l'ha
caricato: in lavorazione, una domanda (con le risposte fra cui scegliere),
da approvare, risolto, non risolto. Con `--stato da-approvare --modello NOME`
mette nella cartella del caso il modello da approvare: quello che
`costruisci --solo NOME` ha costruito col codice della settimana (il giro di
un caso, CODA.md), o quello provato sullo Space con `spazio`. Il caso e'
quello di CASI/casi/<data>_<CODICE>, e il nome quello che la pagina gli ha
annunciato. Con `--stato domanda --anteprima NOME` la domanda porta con se'
le viste del modello di adesso e la lettura del PDF con le misure lette di
quel caso del parco, che la finestra dei casi mostra sopra la domanda. La
risposta a una domanda torna dallo Space, sulla issue del caso
(`coda.aggiungi`).

`versione` stampa l'impronta del codice di DIR, quella che /api/ping
restituisce.

Il giro di un caso (CODA.md) usa `prepara`, `verifica`, `consegna` e
`approvato`, qui
sotto, e costruisce solo quel caso, col codice della settimana. Alla fine
`prossimo` chiede allo Space di avviare una sessione nuova se in coda c'e'
un altro caso libero (`consegna` lo chiede da sola):

    python3 prove/parco.py costruisci ../pack3d-casi /tmp/caso --solo <nome>

Il parco intero, prima e dopo, lo fa il rilascio (vedi
RILASCIO.md), da un clone del ramo `coda-settimana`:

    git -C . worktree add /tmp/prima origin/main
    python3 prove/parco.py costruisci ../pack3d-casi /tmp/parco_prima --codice /tmp/prima
    python3 prove/parco.py costruisci ../pack3d-casi /tmp/parco_dopo
    python3 prove/parco.py confronta /tmp/parco_prima /tmp/parco_dopo

Le viste si fanno sempre col `vista` di questo repository, anche quando il
codice che costruisce e' un altro: cosi' fra PRIMA e DOPO cambia solo il
modello, non il modo di guardarlo.
"""
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote, unquote

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, QUI)

# una costruzione HD di un foglio grande sta sotto i due minuti; il margine
# serve a una macchina lenta, non a un caso bloccato
ATTESA_COSTRUZIONE = 1800


def _casi(cartella, solo=None):
    """I casi del manifesto, nell'ordine in cui sono scritti."""
    with open(os.path.join(cartella, "parco", "parco.json"), encoding="utf-8") as fh:
        casi = json.load(fh)["casi"]
    if solo:
        voluti = set(solo)
        mancano = voluti - {c["nome"] for c in casi}
        if mancano:
            raise SystemExit("casi che il manifesto non ha: %s"
                             % ", ".join(sorted(mancano)))
        casi = [c for c in casi if c["nome"] in voluti]
    return casi


def _porta_libera():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


def _avvia(codice, log, casi=None):
    """Un server col codice di `codice`, solo in locale. (processo, url)

    Senza chiave e con il controllo spento: il parco misura il codice, non
    l'AI, e un caso del parco non deve finire nella coda dei casi nuovi. Con
    `casi`, il clone del repository privato, le risorse che stanno li' (la
    colata: e' grafica del cliente, vedi `pack3d.colata`).
    """
    porta = _porta_libera()
    env = dict(os.environ, PORT=str(porta), HOST="127.0.0.1",
               PACK3D_CONTROLLO="0", PACK3D_STATISTICHE="0")
    if casi and os.path.isdir(os.path.join(casi, "risorse")):
        env["PACK3D_RISORSE"] = os.path.abspath(os.path.join(casi, "risorse"))
    for k in ("ANTHROPIC_API_KEY", "PACK3D_CODA_REPO", "PACK3D_CODA_TOKEN"):
        env.pop(k, None)
    p = subprocess.Popen([sys.executable, "server.py"], cwd=codice, env=env,
                         stdout=log, stderr=subprocess.STDOUT)
    url = "http://127.0.0.1:%d" % porta
    for _ in range(240):
        if p.poll() is not None:
            raise SystemExit("il server non parte: vedi %s" % log.name)
        try:
            with urllib.request.urlopen(url + "/api/ping", timeout=2) as r:
                if r.status == 200:
                    return p, url
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    p.kill()
    raise SystemExit("il server non risponde: vedi %s" % log.name)


def _richiesta(url, percorso, cartella, caso):
    """La richiesta di un caso del parco, come la manda la pagina: i suoi PDF
    in un corpo solo e le sue opzioni."""
    files = [os.path.join(cartella, "parco", "pdf", f) for f in caso["file"]]
    blocchi = []
    for f in files:
        with open(f, "rb") as fh:
            blocchi.append(fh.read())
    opts = dict(caso.get("opzioni") or {})
    opts["nomi"] = [quote(os.path.basename(f)) for f in files]
    if len(blocchi) > 1:
        opts["parti"] = [len(b) for b in blocchi]
    # un caso del parco e' una prova, non un lavoro: sullo Space non conta
    # nelle statistiche (`pack3d.statistiche.in_prova`)
    opts["prova"] = True
    return urllib.request.Request(
        url + percorso, data=b"".join(blocchi), method="POST",
        headers={"Content-Type": "application/pdf",
                 "X-Pack3d": json.dumps(opts)})


def _costruisci_caso(url, cartella, caso, lettura=None):
    """(stato, glb o None, avvisi, secondi, controllo) di un caso, come lo chiede
    la pagina. `controllo` e' il verdetto dell'AI, o None se e' spento. Con
    `lettura`, un percorso, ci salva la lettura del PDF che la pagina mette
    accanto al modello (`pack3d.lettura`), se il server l'ha fatta."""
    req = _richiesta(url, "/api/build", cartella, caso)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=ATTESA_COSTRUZIONE) as r:
            glb = r.read()
            avvisi = json.loads(unquote(r.headers.get("X-Pack3d-Meta") or "[]"))
            controllo = r.headers.get("X-Pack3d-Controllo")
            controllo = json.loads(unquote(controllo)) if controllo else None
            gettone = r.headers.get("X-Pack3d-Lettura")
            attesa = r.headers.get("X-Pack3d-Verdetto")
            secondi = time.time() - t
        if attesa:
            # il modello e' arrivato prima del verdetto del controllo: si
            # aspetta lui, e il modello corretto se la correzione l'ha rifatto
            v = _verdetto(url, attesa)
            if v is not None:
                controllo, avvisi = v["verdetto"], v["meta"] or avvisi
                if v["glb"]:
                    with urllib.request.urlopen(url + "/api/verdetto/glb?id=" + attesa,
                                                timeout=120) as rg:
                        glb = rg.read()
        if lettura and gettone:
            try:
                with urllib.request.urlopen(url + "/api/lettura/" + gettone,
                                            timeout=60) as rl, open(lettura, "wb") as fh:
                    fh.write(rl.read())
            except (urllib.error.URLError, OSError) as e:
                print("lettura del PDF non salvata: %s" % e)
        return r.status, glb, avvisi, secondi, controllo
    except urllib.error.HTTPError as e:
        testo = e.read().decode("utf-8", "replace")
        return e.code, None, [testo[:1000]], time.time() - t, None
    except urllib.error.URLError as e:
        # il server ha chiuso la connessione (un 413 a corpo non letto): e'
        # l'esito di questo caso, non la fine del parco
        return 0, None, ["connessione caduta: %s" % e.reason], time.time() - t, None


def _verdetto(url, gettone):
    """Il verdetto del controllo che arriva dopo il modello (/api/verdetto),
    quando c'e'; None se non arriva in tempo."""
    fine = time.time() + ATTESA_COSTRUZIONE
    while time.time() < fine:
        try:
            with urllib.request.urlopen(url + "/api/verdetto?id=" + gettone,
                                        timeout=60) as r:
                v = json.loads(r.read().decode("utf-8"))
            if v.get("pronto"):
                return v
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(3)
    print("il verdetto del controllo non e' arrivato in %d s" % ATTESA_COSTRUZIONE)
    return None


def _misura(glb, caso):
    """(misure del modello, misure approvate cambiate). Mai un errore: un
    GLB che non si misura lo dice nelle misure."""
    from pack3d import misure
    try:
        m = misure.misura(glb)
    except Exception as e:                  # noqa: BLE001
        return {"errore": "%s: %s" % (type(e).__name__, e)}, []
    return m, misure.confronta(caso.get("misure"), m)


def _impronta_risorse(cartella):
    """Le risorse del registro (la colata): entrano in ogni costruzione."""
    h = hashlib.sha256()
    radice = os.path.join(cartella, "risorse")
    for base, dirs, files in os.walk(radice):
        dirs.sort()
        for f in sorted(files):
            percorso = os.path.join(base, f)
            h.update(os.path.relpath(percorso, radice).encode("utf-8") + b"\0")
            with open(percorso, "rb") as fh:
                h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()[:16]


def _impronta_caso(cartella, caso, risorse):
    """Tutto quello che entra nella costruzione di un caso, fuori dal codice:
    la sua voce del manifesto (file, opzioni, misure approvate), i suoi PDF e
    le risorse. Uguale, col codice uguale, vuol dire lo stesso modello."""
    h = hashlib.sha256(json.dumps(caso, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for f in caso["file"]:
        with open(os.path.join(cartella, "parco", "pdf", f), "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
    h.update(risorse.encode("ascii"))
    return h.hexdigest()[:16]


def _da_riusare(uscita, casi, impronta, impronte, pulisci):
    """{nome: esito} dei casi gia' costruiti in `uscita` con questo codice e
    con gli stessi file: non si ricostruiscono. Con `pulisci`, toglie dalla
    cartella i casi che il manifesto non ha piu'."""
    gia = _esiti(uscita) if os.path.isdir(uscita) else {}
    riusati = {}
    for caso in casi:
        e = gia.get(caso["nome"])
        if (e and e.get("versione") == impronta and e.get("caso") == impronte[caso["nome"]]
                and (e.get("md5") is None or "viste" in e or os.path.exists(
                    os.path.join(uscita, caso["nome"] + "_viste.png")))):
            riusati[caso["nome"]] = e
    if pulisci:
        for nome in set(gia) - set(impronte):
            for coda in (".json", "_viste.png", ".glb", "_lettura.jpg"):
                try:
                    os.remove(os.path.join(uscita, nome + coda))
                except OSError:
                    pass
    return riusati


def costruisci(args):
    from pack3d import versione, vista
    casi = _casi(args.casi, args.solo)
    os.makedirs(args.uscita, exist_ok=True)
    codice = os.path.abspath(args.codice or QUI)
    impronta = versione.impronta(codice)
    risorse = _impronta_risorse(args.casi)
    impronte = {c["nome"]: _impronta_caso(args.casi, c, risorse) for c in casi}
    riusati = (_da_riusare(args.uscita, casi, impronta, impronte, pulisci=not args.solo)
               if getattr(args, "riusa", False) else {})
    riassunto = {n: dict(stato=e["stato"], md5=e["md5"], secondi=e["secondi"])
                 for n, e in riusati.items()}
    da_fare = [c for c in casi if c["nome"] not in riusati]
    if riusati:
        print("%d casi gia' costruiti con questo codice e gli stessi file: non li rifaccio"
              % len(riusati))
    with open(os.path.join(args.uscita, "server.log"), "w") as log:
        p, url = _avvia(codice, log, args.casi) if da_fare else (None, None)
        try:
            for caso in da_fare:
                nome = caso["nome"]
                stato, glb, avvisi, sec, _ = _costruisci_caso(
                    url, args.casi, caso, os.path.join(args.uscita, nome + "_lettura.jpg"))
                esito = dict(nome=nome, stato=stato, secondi=round(sec, 1),
                             file=caso["file"], opzioni=caso.get("opzioni"),
                             avvisi=avvisi, md5=None, versione=impronta,
                             caso=impronte[nome])
                if glb is not None:
                    with open(os.path.join(args.uscita, nome + ".glb"), "wb") as fh:
                        fh.write(glb)
                    esito["md5"] = hashlib.md5(glb).hexdigest()
                    esito["misure"], cambiate = _misura(glb, caso)
                    if cambiate:
                        esito["misure_cambiate"] = cambiate
                    try:
                        im, ingombro = vista.viste(
                            os.path.join(args.uscita, nome + ".glb"), 512)
                        im.save(os.path.join(args.uscita, nome + "_viste.png"))
                        esito["ingombro_mm"] = [round(v, 1) for v in ingombro]
                    except Exception as e:      # un GLB che non si guarda e' un esito
                        esito["viste"] = "non riuscite: %s" % e
                with open(os.path.join(args.uscita, nome + ".json"), "w",
                          encoding="utf-8") as fh:
                    json.dump(esito, fh, indent=1, ensure_ascii=False)
                riassunto[nome] = dict(stato=stato, md5=esito["md5"],
                                       secondi=esito["secondi"])
                print("%-18s %3d %6.1f s  %s" % (nome, stato, sec,
                                                 (esito["md5"] or avvisi[0][:80])[:80]))
                for r in esito.get("misure_cambiate") or []:
                    print("    MISURA APPROVATA CAMBIATA  %s" % r)
                sys.stdout.flush()
        finally:
            if p is not None:
                p.terminate()
                try:
                    p.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    p.kill()
    riassunto = {c["nome"]: riassunto[c["nome"]] for c in casi if c["nome"] in riassunto}
    with open(os.path.join(args.uscita, "riassunto.json"), "w") as fh:
        json.dump(dict(codice=codice, casi=riassunto), fh, indent=1)
    # l'ultima riga: il workflow del parco la legge per sapere se salvare la cassa
    print("parco: riusati %d, costruiti %d" % (len(riusati), len(da_fare)))


def _esiti(cartella):
    fuori = {}
    for f in sorted(os.listdir(cartella)):
        if f.endswith(".json") and f != "riassunto.json":
            with open(os.path.join(cartella, f), encoding="utf-8") as fh:
                e = json.load(fh)
            if isinstance(e, dict) and "nome" in e:
                fuori[e["nome"]] = e
    return fuori


def _affianca(a, b, nome, uscita):
    """Le viste di PRIMA sopra quelle di DOPO, in un'immagine sola."""
    from PIL import Image, ImageDraw
    ims = []
    for cartella in (a, b):
        f = os.path.join(cartella, nome + "_viste.png")
        ims.append(Image.open(f).convert("RGB") if os.path.exists(f) else None)
    if all(i is None for i in ims):
        return                      # nessuna delle due si e' costruita
    w = max(i.width for i in ims if i is not None)
    h = sum((i.height if i is not None else 60) for i in ims) + 2 * 28
    out = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(out)
    y = 0
    for titolo, im in zip(("PRIMA", "DOPO"), ims):
        d.text((8, y + 8), "%s  %s" % (titolo, nome), fill="black")
        y += 28
        if im is None:
            d.text((8, y + 20), "nessuna vista: la costruzione non e' riuscita",
                   fill="red")
            y += 60
        else:
            out.paste(im, (0, y))
            y += im.height
    out.save(os.path.join(uscita, nome + "_confronto.png"))


def confronta(args):
    a, b = _esiti(args.prima), _esiti(args.dopo)
    uscita = args.immagini or os.path.join(args.dopo, "confronto")
    os.makedirs(uscita, exist_ok=True)
    uguali, cambiati, spaiati = [], [], []
    for nome in sorted(set(a) | set(b)):
        ea, eb = a.get(nome), b.get(nome)
        if ea is None or eb is None:
            print("SOLO IN %s  %s" % ("DOPO" if ea is None else "PRIMA", nome))
            spaiati.append(nome)
            continue
        if ea["stato"] == eb["stato"] and ea["md5"] == eb["md5"]:
            uguali.append(nome)
            continue
        cambiati.append(nome)
        print("CAMBIA  %s  (stato %s -> %s)" % (nome, ea["stato"], eb["stato"]))
        tolti = [x for x in ea["avvisi"] if x not in eb["avvisi"]]
        nuovi = [x for x in eb["avvisi"] if x not in ea["avvisi"]]
        for x in tolti:
            print("    - %s" % x[:220])
        for x in nuovi:
            print("    + %s" % x[:220])
        if not tolti and not nuovi:
            print("    avvisi identici: cambia solo il modello (geometria o texture)")
        _affianca(args.prima, args.dopo, nome, uscita)
    print("\n%d uguali al byte, %d cambiati%s%s" % (
        len(uguali), len(cambiati),
        (", %d costruiti da una parte sola" % len(spaiati)) if spaiati else "",
        (": le viste affiancate sono in %s" % uscita) if cambiati else ""))
    # le misure approvate che DOPO cambia: un cambio che va spiegato
    misurati = [e for e in b.values() if e.get("misure")]
    cambiate = [(n, b[n]["misure_cambiate"]) for n in sorted(b)
                if b[n].get("misure_cambiate")]
    if cambiate:
        print("\nMISURE APPROVATE CAMBIATE in %d casi:" % len(cambiate))
        for n, righe in cambiate:
            print("  %s" % n)
            for r in righe:
                print("    %s" % r)
    elif misurati:
        print("nessuna misura approvata cambiata (%d casi misurati)" % len(misurati))


def esito(args):
    """Il verdetto di un parco fatto da solo (la notte, nelle Actions del
    repository dei casi): DOPO contro PRIMA - il codice di `main`, quello
    approvato - e, se c'e', contro IERI. Scrive il riassunto in markdown
    (`--riassunto`, di serie a video) ed esce con 1 se qualcosa si e' rotto:
    un caso che con PRIMA si costruiva e con DOPO no, un caso nuovo che non
    si costruisce, o una misura approvata cambiata. Un modello solo cambiato
    no: il ramo della settimana cambia i modelli apposta, e si guarda al
    rilascio."""
    a, b = _esiti(args.prima), _esiti(args.dopo)
    ieri = _esiti(args.ieri) if args.ieri and os.path.isdir(args.ieri) else {}
    rotti = [n for n in sorted(b) if b[n]["stato"] != 200
             and (n not in a or a[n]["stato"] == 200)]
    cambiati = [n for n in sorted(set(a) & set(b)) if n not in rotti
                and (a[n]["stato"], a[n]["md5"]) != (b[n]["stato"], b[n]["md5"])]
    misure = [(n, b[n]["misure_cambiate"]) for n in sorted(b)
              if b[n].get("misure_cambiate")]
    da_ieri = [n for n in sorted(b) if n in ieri
               and (ieri[n]["stato"], ieri[n]["md5"]) != (b[n]["stato"], b[n]["md5"])]
    righe = ["## Parco%s" % (": " + args.titolo if args.titolo else ""), "",
             "**%d casi**: %d uguali a `main` al byte, %d cambiati, **%d rotti**, "
             "**%d con misure approvate cambiate**." % (
                 len(b), len(b) - len(cambiati) - len(rotti), len(cambiati),
                 len(rotti), len(misure))]
    if ieri:
        righe.append("Rispetto alla notte prima cambiano %d casi%s." % (
            len(da_ieri), (": " + ", ".join("`%s`" % n for n in da_ieri)) if da_ieri else ""))
    if rotti:
        righe += ["", "### Rotti", ""]
        for n in rotti:
            prima = a[n]["stato"] if n in a else "caso nuovo"
            righe.append("- `%s`: %s -> %s. %s" % (n, prima, b[n]["stato"],
                                                   (b[n]["avvisi"] or [""])[0][:300]))
    if misure:
        righe += ["", "### Misure approvate cambiate", ""]
        for n, cambiate in misure:
            righe.append("- `%s`: %s" % (n, "; ".join(cambiate)))
    if cambiati:
        righe += ["", "### Cambiati rispetto a `main`", "",
                  "Le viste affiancate, PRIMA sopra e DOPO sotto, sono nell'artefatto.", ""]
        for n in cambiati:
            nuovi = [x for x in b[n]["avvisi"] if x not in a[n]["avvisi"]]
            righe.append("- `%s`%s%s" % (n, " (da stanotte)" if n in da_ieri else "",
                                          (": " + nuovi[0][:200]) if nuovi else ""))
    testo = "\n".join(righe) + "\n"
    if args.riassunto:
        with open(args.riassunto, "a", encoding="utf-8") as fh:
            fh.write(testo)
    else:
        print(testo)
    if rotti or misure:
        raise SystemExit(1)


# le letture approvate, una per caso: nel repository dei casi, accanto al
# manifesto
LETTURE = os.path.join("parco", "letture.json")
# le varianti diverse gia' note, approvate: vedi `varianti`
VARIANTI = os.path.join("parco", "varianti.json")


def _leggi_caso(url, cartella, caso):
    """La lettura di un caso come la chiede la pagina prima di costruire
    (/api/analyze): il dict, o il testo dell'errore."""
    try:
        with urllib.request.urlopen(_richiesta(url, "/api/analyze", cartella, caso),
                                    timeout=ATTESA_COSTRUZIONE) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return "errore %d: %s" % (e.code, e.read().decode("utf-8", "replace")[:500])


def _differenze(a, b):
    """Le righe che dicono come cambia una lettura: le chiavi, e le righe dei
    cartellini tolte e aggiunte."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return ["    prima: %s" % str(a)[:300], "    dopo:  %s" % str(b)[:300]]
    righe = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) == b.get(k):
            continue
        if k == "meta" and isinstance(a.get(k), list) and isinstance(b.get(k), list):
            righe += ["    - %s" % x for x in a[k] if x not in b[k]]
            righe += ["    + %s" % x for x in b[k] if x not in a[k]]
        else:
            righe.append("    %s: %s -> %s" % (k, str(a.get(k))[:200], str(b.get(k))[:200]))
    return righe


def _letture_approvate(casi):
    f = os.path.join(casi, LETTURE)
    if not os.path.exists(f):
        return {}
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)


def _leggi_tutti(cartella, casi, codice=None):
    """{nome: lettura} dei `casi`, con un server solo col codice di `codice`
    (di serie questo repository)."""
    from concurrent.futures import ThreadPoolExecutor
    with open(os.devnull, "w") as log:
        p, url = _avvia(os.path.abspath(codice or QUI), log, cartella)
        try:
            # una per lavoratore: la lettura di un caso non dipende da chi
            # e' passato prima (`pack3d.stato`)
            with ThreadPoolExecutor(2) as pool:
                return dict(zip([c["nome"] for c in casi], pool.map(
                    lambda c: _leggi_caso(url, cartella, c), casi)))
        finally:
            p.terminate()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()


def letture(args):
    """La lettura di ogni caso del parco - famiglia, misure, cartellini -
    contro quella approvata, in qualche minuto e senza costruire: dice a
    quale caso una modifica ha cambiato strada prima del parco intero. Con
    `--approva` le scrive come approvate. Esce con 1 se una e' cambiata."""
    casi = _casi(args.casi, args.solo)
    approvate = _letture_approvate(args.casi)
    f = os.path.join(args.casi, LETTURE)
    t = time.time()
    lette = _leggi_tutti(args.casi, casi, args.codice)
    cambiate = 0
    for nome, letta in lette.items():
        if nome not in approvate:
            print("%-44s nessuna lettura approvata" % nome[:44])
            continue
        if letta == approvate[nome]:
            print("%-44s uguale" % nome[:44])
            continue
        cambiate += 1
        print("%-44s CAMBIA" % nome[:44])
        for r in _differenze(approvate[nome], letta):
            print(r)
    print("\n%d letture, %d cambiate, in %.0f s" % (len(lette), cambiate, time.time() - t))
    if args.approva:
        approvate.update(lette)
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(approvate, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        print("letture approvate scritte per %d casi in %s: commit e push nel registro"
              % (len(lette), LETTURE))
    elif cambiate:
        raise SystemExit(1)


def misure_del_parco(args):
    """Le misure di una costruzione gia' fatta contro quelle approvate; con
    `--approva`, scritte nel manifesto come approvate."""
    from pack3d import misure
    manifesto = _manifesto(args.casi)
    voluti = set(args.solo or [])
    cambiati, scritti = 0, 0
    for caso in manifesto["casi"]:
        nome = caso["nome"]
        f = os.path.join(args.uscita, nome + ".glb")
        if (voluti and nome not in voluti) or not os.path.exists(f):
            continue
        with open(f, "rb") as fh:
            m = misure.misura(fh.read())
        righe = misure.confronta(caso.get("misure"), m)
        if not caso.get("misure"):
            righe = ["nessuna misura approvata"]
        print("%-44s %s" % (nome[:44], "uguale" if not righe else righe[0]))
        for r in righe[1:]:
            print("%-44s %s" % ("", r))
        cambiati += bool(righe)
        if args.approva and caso.get("misure") != m:
            caso["misure"] = m
            scritti += 1
    if args.approva:
        with open(os.path.join(args.casi, "parco", "parco.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(manifesto, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print("misure approvate scritte per %d casi in parco/parco.json: commit e push "
              "nel registro" % scritti)
    elif cambiati:
        raise SystemExit(1)


def versione_del_codice(args):
    from pack3d import versione
    print(versione.impronta(os.path.abspath(args.codice or QUI)))


def _versione_in_linea(url):
    """La versione che /api/ping dice, o perche' non la dice."""
    try:
        with urllib.request.urlopen(url + "/api/ping", timeout=30) as r:
            return json.loads(r.read().decode("utf-8")).get("versione") or "senza versione"
    except (urllib.error.URLError, OSError, ValueError) as e:
        # mentre lo Space riparte risponde con un errore o con una pagina
        return "non risponde (%s)" % str(e)[:80]


ESITI = {"ok": 0, "dubbio": 1, "sbagliato": 2}


def _una_per_famiglia(cartella):
    """Un caso per famiglia, la `kind` della lettura approvata: il piu'
    leggero, perche' la prova dello Space a ogni rilascio resti di pochi
    minuti. Cosi' un rilascio che rompe solo i vassoi, o solo gli incarti,
    lo Space lo dice; col solo T1 di riferimento no."""
    letture = _letture_approvate(cartella)
    scelti = {}
    for c in _casi(cartella):
        r = letture.get(c["nome"])
        if not isinstance(r, dict) or not r.get("kind"):
            continue
        file = [os.path.join(cartella, "parco", "pdf", f) for f in c["file"]]
        if not all(os.path.exists(f) for f in file):
            continue
        peso = sum(os.path.getsize(f) for f in file)
        if r["kind"] not in scelti or peso < scelti[r["kind"]][0]:
            scelti[r["kind"]] = (peso, c)
    return [(k, scelti[k][1]) for k in sorted(scelti)]


def spazio(args):
    """I casi del parco sullo Space vero, appena ripartito col codice di qui:
    quelli nominati, o uno per famiglia (`_una_per_famiglia`). Esce col
    codice peggiore: 0 ok, 1 dubbio, 2 sbagliato, 3 non costruito o senza
    controllo dell'AI. Sono prove: non contano nelle statistiche dello Space
    (`_richiesta`)."""
    from pack3d import versione
    if args.nomi:
        casi = [(None, c) for c in _casi(args.casi, args.nomi)]
    else:
        casi = _una_per_famiglia(args.casi)
    url = args.url.rstrip("/")
    attesa = versione.impronta(QUI)
    fine = time.time() + args.attendi * 60
    while True:
        in_linea = _versione_in_linea(url)
        if in_linea == attesa:
            break
        if time.time() > fine:
            print("lo Space non e' ripartito col codice di qui in %d minuti: "
                  "dice %s, aspettavo %s" % (args.attendi, in_linea, attesa))
            raise SystemExit(4)
        print("lo Space dice %s, aspetto %s" % (in_linea, attesa))
        sys.stdout.flush()
        time.sleep(30)
    print("lo Space e' alla versione %s: costruisco %d %s" % (
        attesa, len(casi), "caso" if len(casi) == 1 else "casi, uno per famiglia"
        if not args.nomi else "casi"))
    sys.stdout.flush()
    esiti = []
    for famiglia, caso in casi:
        esiti.append((famiglia, caso["nome"], _uno_sullo_spazio(url, args, caso, attesa)))
    if len(esiti) > 1:
        nomi = {v: k for k, v in ESITI.items()}
        print("\n%d casi: %s" % (len(esiti), ", ".join(
            "%s %s" % (f or n, nomi.get(c, "non costruito")) for f, n, c in esiti)))
    raise SystemExit(max(c for _f, _n, c in esiti))


def _uno_sullo_spazio(url, args, caso, attesa):
    """Un caso sullo Space: GLB, viste e verdetto in `args.uscita`; torna il
    codice d'uscita del caso."""
    from pack3d import vista
    nome = caso["nome"]
    print("\n%s" % nome)
    sys.stdout.flush()
    stato, glb, avvisi, sec, controllo = _costruisci_caso(url, args.casi, caso)
    os.makedirs(args.uscita, exist_ok=True)
    esito = dict(nome=nome, url=url, versione=attesa, stato=stato,
                 secondi=round(sec, 1), avvisi=avvisi, controllo=controllo)
    if glb is not None:
        f = os.path.join(args.uscita, nome + "_spazio.glb")
        with open(f, "wb") as fh:
            fh.write(glb)
        esito["md5"] = hashlib.md5(glb).hexdigest()
        im, _ingombro = vista.viste(f, 512)
        im.save(os.path.join(args.uscita, nome + "_spazio_viste.png"))
    with open(os.path.join(args.uscita, nome + "_spazio.json"), "w",
              encoding="utf-8") as fh:
        json.dump(esito, fh, indent=1, ensure_ascii=False)
    if stato != 200:
        print("costruzione fallita sullo Space (%d): %s" % (stato, avvisi[0][:300]))
        return 3
    if not controllo:
        print("costruito in %.0f s, ma il controllo dell'AI non c'e' stato" % sec)
        return 3
    print("costruito in %.0f s - controllo dell'AI: %s" % (sec, controllo.get("esito")))
    print("  %s" % controllo.get("motivo", ""))
    for d in controllo.get("difetti") or []:
        print("  - %s" % d)
    sys.stdout.flush()
    return ESITI.get(controllo.get("esito"), 3)


# come encodeURIComponent, che e' quello che Glam decodifica
_URI = "-_.!~*'()"

# L'indirizzo di Glam Lab, quello che usano i comandi di CODA.md. Se cambia,
# cambia anche fra gli Allowed websites della credenziale "Glam Lab"
# dell'ambiente cloud: e' li' che il proxy aggiunge il token, e solo i siti
# di quella lista sono raggiungibili.
GLAM = "https://iccio-3d-viewer.lovable.app"

# Lo Space, a cui `caso` chiede di avvisare per email chi ha mandato il caso
# quando la routine gli fa una domanda (/api/avviso).
SPAZIO = "https://iccio-maurizio.hf.space"


def _glam_assente(codice, testo):
    """Un 404 di Lovable con "Project not found" non viene da Glam: a
    quell'indirizzo non c'e' piu' nessun sito."""
    if codice == 404 and "project not found" in testo.lower():
        print("a questo indirizzo Glam non c'e' (404 \"Project not found\" di "
              "Lovable): l'indirizzo di Glam e' cambiato. Va aggiornato in "
              "CODA.md (GLAM in prove/parco.py) e fra gli Allowed websites "
              "della credenziale dell'ambiente cloud")
        return True
    return False


def _glam_irraggiungibile(e):
    """Il proxy dell'ambiente lascia passare solo i siti permessi: un 403
    sul tunnel vuol dire che Glam non e' fra quelli, non che e' giu'."""
    if "403" in str(e) or "tunnel" in str(e).lower():
        print("Glam non e' raggiungibile da questo ambiente (%s): il suo "
              "dominio va fra gli Allowed websites della credenziale \"Glam "
              "Lab\" dell'ambiente cloud" % e)
    else:
        print("Glam non risponde: %s" % e)


def nome_glam(caso):
    """Il nome del modello in Glam: il nome del primo PDF senza `.pdf`, come
    lo chiama Glam costruendolo dal PDF e come lo annuncia la pagina dello
    Space (`nomeInGlam`). Al massimo 120 caratteri: di piu' Glam non ne
    accetta. `glam` nel manifesto vince: la coda toglie spazi e simboli dai
    nomi dei file, e allora quello del parco non e' piu' quello caricato."""
    if caso.get("glam"):
        return caso["glam"]
    base = os.path.basename(caso["file"][0])
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    return base[:120] or "Pack"


def _approvato(cartella):
    """Chi ha caricato il caso ha approvato il modello da approvare piu'
    recente: in `stato.json` c'e' "approvato" dopo l'ultimo "da-approvare"
    (lo scrive lo Space, dalla finestra dei casi)."""
    try:
        with open(os.path.join(cartella, "stato.json"), encoding="utf-8") as fh:
            storia = json.load(fh).get("storia") or []
    except (OSError, ValueError, AttributeError):
        return False
    stati = [v.get("stato") for v in storia if isinstance(v, dict)]
    if "da-approvare" not in stati:
        return False
    ultimo = len(stati) - 1 - stati[::-1].index("da-approvare")
    return "approvato" in stati[ultimo + 1:]


def _ultimo_stato(cartella):
    try:
        with open(os.path.join(cartella, "stato.json"), encoding="utf-8") as fh:
            storia = json.load(fh).get("storia") or []
    except (OSError, ValueError, AttributeError):
        return None
    return (storia[-1] if storia and isinstance(storia[-1], dict) else {}).get("stato")


def glam(args):
    """Il modello approvato, nel viewer Glam Lab: da chi ha caricato il caso
    della coda, o dallo Space (`spazio`) per un caso del parco senza codice."""
    caso = _casi(args.casi, [args.nome])[0]
    base = os.path.join(args.uscita, args.nome + "_spazio")
    dal_registro = False
    if not os.path.exists(base + ".json") and caso.get("codice"):
        # un caso approvato da chi l'ha caricato: il modello sta nel registro,
        # dove l'ha messo `caso --stato da-approvare` (forse un'altra sessione)
        cartella, _v = _caso_in_coda(args.casi, caso["codice"])
        if os.path.exists(os.path.join(cartella, "modello.json")):
            base = os.path.join(cartella, "modello")
            dal_registro = True
            if not _approvato(cartella):
                raise SystemExit("chi ha caricato il caso %s non ha ancora approvato il "
                                 "modello: in Glam va solo dopo l'approvazione (se e' "
                                 "appena arrivata, aggiorna il clone del registro)"
                                 % caso["codice"])
    try:
        with open(base + ".json", encoding="utf-8") as fh:
            esito = json.load(fh)
        with open(base + ".glb", "rb") as fh:
            glb = fh.read()
    except (OSError, ValueError):
        raise SystemExit("manca la prova sullo Space di %s in %s: prima `spazio`"
                         % (args.nome, args.uscita))
    verdetto = (esito.get("controllo") or {}).get("esito")
    # il modello costruito col codice della settimana non e' passato dal
    # controllo dello Space: lo riprova il rilascio. Basta l'approvazione;
    # ma un verdetto che non e' "ok", se c'e', ferma tutto
    if not (verdetto == "ok" or (dal_registro and esito.get("provato") == "locale"
                                 and verdetto is None)):
        raise SystemExit("lo Space non ha approvato %s (%s): in Glam va solo un "
                         "modello approvato" % (args.nome, verdetto or "nessun controllo"))
    if hashlib.md5(glb).hexdigest() != esito.get("md5"):
        raise SystemExit("%s.glb non e' il modello provato sullo Space" % base)
    nome = nome_glam(caso)
    # Glam sta dietro Cloudflare, che respinge l'intestazione di serie di
    # urllib ("Python-urllib/3.x": errore 1010) prima che arrivi al sito
    intestazioni = {"Content-Type": "model/gltf-binary",
                    "X-Model-Name": quote(nome, safe=_URI),
                    "X-Model-Category": quote(args.categoria, safe=_URI),
                    "User-Agent": "pack3d-studio"}
    # il caso della coda: Glam mette il modello a chi l'ha caricato
    if caso.get("codice"):
        intestazioni["X-Pack3d-Codice"] = caso["codice"]
    req = urllib.request.Request(
        args.url.rstrip("/") + "/api/import-model", data=glb, method="POST",
        headers=intestazioni)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            risposta = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        testo = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            print("Glam rifiuta il token (401): la credenziale dell'ambiente "
                  "cloud per questo sito manca, o non e' uguale al secret "
                  "PACK3D_IMPORT_TOKEN di Glam")
        elif not _glam_assente(e.code, testo):
            print("Glam non ha preso il modello (HTTP %d): %s" % (e.code, testo))
        raise SystemExit(1)
    except (urllib.error.URLError, OSError, ValueError) as e:
        _glam_irraggiungibile(e)
        raise SystemExit(1)
    print("in Glam: \"%s\" fra \"%s\" (id %s)%s" % (
        risposta.get("name", nome), risposta.get("category", args.categoria),
        risposta.get("id", "?"),
        ", utenti: %s" % risposta["utenti"] if risposta.get("utenti") else ""))
    _texture_in_glam(args.url, glb, nome, args.categoria, caso.get("codice"))
    _template_in_glam(args.url, glb, nome, args.categoria, caso.get("codice"))


def _template_in_glam(url, glb, nome, categoria, codice):
    """Il template PSD del modello appena mandato, per «Scarica Template» di
    Glam (GLAM.md, sezione 9): `pack3d.template`. Come la texture: il
    modello in Glam c'e' gia', e se il template non passa lo si dice e
    basta."""
    try:
        from pack3d import template
        t = template.template(glb)
    except ImportError as e:
        print("template: manca %s (pip install -q -r requirements.txt): in Glam "
              "va senza template" % e.name)
        return
    except Exception as e:      # noqa: BLE001 - il modello e' gia' in Glam
        print("template: non si fa dal GLB (%s): in Glam va senza template" % e)
        return
    if t is None:
        print("template: il modello ha piu' texture (coppa col tappo, cono col lid, riempimento): in Glam va "
              "senza template")
        return
    file = template.nome_file(nome)
    intestazioni = {"Content-Type": template.MIME,
                    "X-Model-Name": quote(nome, safe=_URI),
                    "X-Model-Category": quote(categoria, safe=_URI),
                    "X-Template-Name": quote(file, safe=_URI),
                    "User-Agent": "pack3d-studio"}
    if codice:
        intestazioni["X-Pack3d-Codice"] = codice
    req = urllib.request.Request(
        url.rstrip("/") + "/api/import-template", data=t["dati"], method="POST",
        headers=intestazioni)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            risposta = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        testo = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            print("Glam rifiuta il token del template (401): e' lo stesso di "
                  "/api/import-model, PACK3D_IMPORT_TOKEN")
        elif not _glam_assente(e.code, testo):
            print("Glam non ha preso il template (HTTP %d): %s - il modello c'e'. "
                  "Se /api/import-template non esiste, Glam non conosce ancora i "
                  "template: GLAM.md, sezione 9" % (e.code, testo))
        return
    except (urllib.error.URLError, OSError, ValueError) as e:
        _glam_irraggiungibile(e)
        return
    print("in Glam anche il template \"%s\", %d x %d px, %.1f MB%s" % (
        file, t["lato"][0], t["lato"][1], len(t["dati"]) / 1e6,
        ", utenti: %s" % risposta["utenti"] if risposta.get("utenti") else ""))


def _texture_in_glam(url, glb, nome, categoria, codice):
    """La texture del modello appena mandato, nella sezione texture di Glam,
    legata a quel modello (GLAM.md, sezione 8): `pack3d.texture`. Il
    modello in Glam c'e' gia': se la texture non passa lo si dice, e il
    comando finisce bene lo stesso."""
    from pack3d import texture
    try:
        t = texture.per_glam(glb)
    except Exception as e:      # noqa: BLE001 - il modello e' gia' in Glam
        print("texture: non si legge dal GLB (%s): in Glam va solo il modello" % e)
        return
    if t is None:
        print("texture: il modello ne ha piu' d'una (coppa col tappo, cono col lid, riempimento), e Glam ne "
              "mette una sola su tutto il modello: in Glam va solo il modello")
        return
    file = texture.nomi_file(nome, [t])[0]
    intestazioni = {"Content-Type": t["mime"],
                    "X-Model-Name": quote(nome, safe=_URI),
                    "X-Model-Category": quote(categoria, safe=_URI),
                    "X-Texture-Name": quote(file, safe=_URI),
                    "User-Agent": "pack3d-studio"}
    if codice:
        intestazioni["X-Pack3d-Codice"] = codice
    req = urllib.request.Request(
        url.rstrip("/") + "/api/import-texture", data=t["dati"], method="POST",
        headers=intestazioni)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            risposta = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        testo = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            print("Glam rifiuta il token della texture (401): e' lo stesso di "
                  "/api/import-model, PACK3D_IMPORT_TOKEN")
        elif not _glam_assente(e.code, testo):
            print("Glam non ha preso la texture (HTTP %d): %s - il modello c'e'. "
                  "Se /api/import-texture non esiste, Glam non conosce ancora le "
                  "texture: GLAM.md, sezione 8" % (e.code, testo))
        return
    except (urllib.error.URLError, OSError, ValueError) as e:
        _glam_irraggiungibile(e)
        return
    print("in Glam anche la texture \"%s\", %d x %d px%s%s" % (
        file, t["lato"][0], t["lato"][1],
        " (ridotta a %d px, il massimo di Glam)" % texture.LATO_GLAM if t["ridotta"] else "",
        ", utenti: %s" % risposta["utenti"] if risposta.get("utenti") else ""))


# Gli stati di un caso della coda, come li mostra Glam a chi l'ha caricato.
# "in-coda" non c'e': lo dice la pagina, quando il caso entra. "da-approvare":
# il modello corretto aspetta che chi l'ha caricato lo approvi, dalla finestra
# dei casi della pagina; "approvato" e "non-approvato" li scrive lo Space.
STATI = ("in-lavorazione", "domanda", "da-approvare", "risolto", "non-risolto")

# Glam, finche' non conosce "da-approvare" (GLAM.md), lo riceve cosi'
DA_APPROVARE_IN_GLAM = ("in-lavorazione", "Il modello corretto è pronto: guardalo "
                        "e approvalo nella finestra dei casi della pagina.")


def _caso_in_coda(casi, cod):
    """(cartella del caso nel repository privato, il suo verdetto.json).

    La piu' recente: lo stesso PDF ricaricato un altro giorno apre un caso
    nuovo in una cartella nuova, `<data>_<codice>`, e lo Space legge stato e
    modello da quella della issue aperta (`coda._storia`). Lo Space non apre
    una seconda issue finche' la prima e' aperta, quindi la cartella piu'
    recente e' sempre quella del caso in corso. Prendendo la prima, la
    routine scriveva il modello da approvare nella cartella di un caso
    eliminato giorni prima, e chi l'aveva caricato non lo vedeva."""
    if not cod or len(cod) != 10 or any(c not in "0123456789abcdef" for c in cod):
        raise SystemExit("il codice di un caso e' di 10 cifre esadecimali: %r" % cod)
    radice = os.path.join(casi, "casi")
    for d in sorted(os.listdir(radice) if os.path.isdir(radice) else [], reverse=True):
        if d.endswith("_" + cod):
            try:
                with open(os.path.join(radice, d, "verdetto.json"), encoding="utf-8") as fh:
                    return os.path.join(radice, d), json.load(fh)
            except (OSError, ValueError):
                break
    raise SystemExit("il caso %s non c'e' in %s" % (cod, radice))


def nome_del_caso(verdetto):
    """Il nome che la pagina ha annunciato a chi ha caricato il caso: il primo
    PDF senza `.pdf`, al massimo 120 caratteri (`nomeInGlam`)."""
    nomi = (verdetto.get("contesto") or {}).get("nomi") or []
    base = str(nomi[0]) if nomi else ""
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    return base[:120] or "Pack"


def _git(casi, *a):
    return subprocess.run(["git", "-C", casi] + list(a), capture_output=True, text=True)


def _modello_da_approvare(args, cartella):
    """Copia nella cartella del caso il modello da approvare: `modello.glb` e
    `modello.json`, con l'impronta del codice e il verdetto dello Space, se
    c'e'. Lo legge da li' la pagina, per farlo approvare, e `glam`, quando
    arriva l'approvazione. Torna i percorsi da registrare.

    Il modello e' quello che `costruisci --solo` ha costruito in USCITA col
    codice della settimana (il giro di un caso: lo Space lo riprova al
    rilascio), o quello provato sullo Space con `spazio`, se c'e'."""
    spazio_ = os.path.join(args.uscita, args.modello + "_spazio")
    locale = os.path.join(args.uscita, args.modello)
    base = spazio_ if os.path.exists(spazio_ + ".json") else locale
    try:
        with open(base + ".json", encoding="utf-8") as fh:
            esito = json.load(fh)
        with open(base + ".glb", "rb") as fh:
            glb = fh.read()
    except (OSError, ValueError):
        raise SystemExit("manca il modello di %s in %s: prima `costruisci "
                         "--solo %s` (o `spazio`)" % (args.modello, args.uscita,
                                                      args.modello))
    if base == spazio_:
        if (esito.get("controllo") or {}).get("esito") != "ok":
            raise SystemExit("lo Space non ha approvato %s: da approvare va solo un "
                             "modello che lo Space dice ok" % args.modello)
        provato = "spazio"
    else:
        if esito.get("stato") != 200 or not esito.get("versione"):
            raise SystemExit("%s non si e' costruito (%s): da approvare va un modello"
                             % (args.modello, esito.get("stato")))
        provato = "locale"
    if hashlib.md5(glb).hexdigest() != esito.get("md5"):
        raise SystemExit("%s.glb non e' il modello costruito" % base)
    with open(os.path.join(cartella, "modello.glb"), "wb") as fh:
        fh.write(glb)
    with open(os.path.join(cartella, "modello.json"), "w", encoding="utf-8") as fh:
        json.dump(dict({k: esito.get(k) for k in ("nome", "versione", "md5", "controllo")},
                       provato=provato), fh, ensure_ascii=False, indent=1)
    return [os.path.join(cartella, "modello.glb"), os.path.join(cartella, "modello.json")]


# L'anteprima di una domanda, nella cartella del caso: il modello di adesso
# dai quattro lati e la lettura del PDF con le misure lette, uno sotto
# l'altra. La finestra dei casi della pagina la mostra sopra la domanda
# (`coda.anteprima`): chi risponde vede cosa si e' costruito e cosa si e'
# letto, non solo la domanda.
ANTEPRIMA = "domanda.jpg"
ANTEPRIMA_LATO = 1600


def _anteprima(uscita, nome, cartella):
    """Compone CARTELLA/domanda.jpg dal caso del parco NOME costruito in
    USCITA (`costruisci --solo`): le viste e la lettura del PDF. Il percorso."""
    from PIL import Image
    pezzi = [Image.open(f).convert("RGB") for f in
             (os.path.join(uscita, nome + "_viste.png"),
              os.path.join(uscita, nome + "_lettura.jpg")) if os.path.exists(f)]
    if not pezzi:
        raise SystemExit("mancano le viste di %s in %s: prima `costruisci --solo %s`"
                         % (nome, uscita, nome))
    largo = min(ANTEPRIMA_LATO, max(im.width for im in pezzi))
    pezzi = [im.resize((largo, max(1, round(im.height * largo / im.width)))) for im in pezzi]
    tela = Image.new("RGB", (largo, sum(im.height for im in pezzi) + 20 * (len(pezzi) - 1)),
                     "white")
    y = 0
    for im in pezzi:
        tela.paste(im, (0, y))
        y += im.height + 20
    dove = os.path.join(cartella, ANTEPRIMA)
    tela.save(dove, quality=80)
    return dove


def _registra_stato(casi, cartella, codice, corpo, altri=()):
    """Lo stato del caso in `stato.json`, nella sua cartella, per la pagina
    dello Space: la finestra dei casi e le notifiche di chi l'ha mandato lo
    leggono da li'. Commit e push su main del repository dei casi, come ogni
    altra cosa del registro. Mai un errore: se non va, lo dice e basta."""
    percorso = os.path.join(cartella, "stato.json")
    try:
        with open(percorso, encoding="utf-8") as fh:
            dati = json.load(fh)
    except (OSError, ValueError):
        dati = {}
    if not isinstance(dati, dict):
        dati = {}
    storia = [v for v in dati.get("storia") or [] if isinstance(v, dict)]
    voce = {k: corpo[k] for k in ("stato", "nome", "messaggio", "domanda", "opzioni",
                                  "immagine")
            if corpo.get(k) not in (None, "", [])}
    voce["quando"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    dati["storia"] = (storia + [voce])[-30:]
    with open(percorso, "w", encoding="utf-8") as fh:
        json.dump(dati, fh, ensure_ascii=False, indent=1)
    rel = [os.path.relpath(p, casi) for p in [percorso] + list(altri)]
    if _commit_registro(casi, rel, "Caso %s: stato %s" % (codice, corpo["stato"])):
        print("stato del caso registrato in %s" % ", ".join(rel))
        return True
    return False


def _commit_registro(casi, rel, messaggio):
    """Commit dei file `rel` (relativi a `casi`) e push su main del registro,
    con l'autore dell'ultimo commit. True se e' su main (anche se non c'era
    niente da registrare). Mai un errore: se non va, lo dice e basta."""
    autore = _git(casi, "log", "-1", "--format=%an%n%ae").stdout.split("\n")
    chi = ["-c", "user.name=" + autore[0], "-c", "user.email=" + autore[1]] \
        if len(autore) >= 2 and autore[0] and autore[1] else []
    _git(casi, "add", *rel)
    # niente di nuovo da registrare: si spinge lo stesso, se un push di prima
    # non era andato
    if _git(casi, "diff", "--cached", "--quiet", "--", *rel).returncode != 0:
        fatto = _git(casi, *chi, "commit", "-q", "-m", messaggio, "--", *rel)
        if fatto.returncode != 0:
            print("non registrato nel registro: %s"
                  % (fatto.stderr or fatto.stdout).strip()[:300])
            return False
    for _ in range(3):
        if _git(casi, "push", "-q", "origin", "HEAD:main").returncode == 0:
            return True
        _git(casi, "pull", "-q", "--rebase", "--autostash", "origin", "main")
    print("scritto ma non spinto su main del registro: fallo tu (git push origin HEAD:main)")
    return False


def _avvisa(spazio, codice):
    """Chiede allo Space di mandare la domanda per email a chi l'ha chiesto."""
    req = urllib.request.Request(
        spazio.rstrip("/") + "/api/avviso", method="POST",
        data=json.dumps({"codice": codice}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pack3d-studio"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            esito = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        print("email a chi ha mandato il caso non partita (HTTP %d): %s"
              % (e.code, e.read().decode("utf-8", "replace")[:200]))
        return
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("lo Space non risponde per l'email a chi ha mandato il caso: %s" % e)
        return
    if esito.get("inviate"):
        print("email mandata a chi ha mandato il caso (%d)" % esito["inviate"])
    else:
        print("email a chi ha mandato il caso: nessuna (%s)" % esito.get("perche", "-"))


def _prossimo(spazio, codice):
    """Chiede allo Space di avviare una sessione nuova della routine, se in
    coda c'e' un altro caso libero (`coda.prossimo`). Un caso per sessione:
    costa meno che lavorarne due nella stessa."""
    for prova in (1, 2):
        req = urllib.request.Request(
            spazio.rstrip("/") + "/api/prossimo", method="POST",
            data=json.dumps({"codice": codice}).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "pack3d-studio"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                esito = json.loads(r.read().decode("utf-8") or "{}")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and prova == 1:
                time.sleep(20)          # un'altra sessione ha appena guardato
                continue
            print("prossimo caso: lo Space dice HTTP %d: %s"
                  % (e.code, e.read().decode("utf-8", "replace")[:200]))
            return
        except (urllib.error.URLError, OSError, ValueError) as e:
            print("prossimo caso: lo Space non risponde (%s); lo prende il giro di "
                  "sicurezza" % e)
            return
    if esito.get("avviata"):
        print("prossimo caso: %s, in una sessione nuova" % esito.get("caso"))
    else:
        print("prossimo caso: nessuno (%s)" % (esito.get("perche") or "-"))


def prossimo(args):
    """Fine del giro, comunque sia andato: se c'e' un altro caso libero, una
    sessione nuova lo prende."""
    _prossimo(args.spazio, args.codice)


def caso(args):
    """A che punto e' un caso della coda, in Glam Lab per chi l'ha caricato,
    e nella pagina dello Space per chi l'ha mandato da li'."""
    cartella, verdetto = _caso_in_coda(args.casi, args.codice)
    corpo = {"codice": args.codice, "nome": nome_del_caso(verdetto),
             "stato": args.stato}
    if args.messaggio:
        corpo["messaggio"] = args.messaggio.strip()[:500]
    if args.stato == "domanda":
        if not (args.domanda or "").strip():
            raise SystemExit("con --stato domanda ci vuole la domanda: --domanda")
        opzioni = [o.strip()[:120] for o in args.opzione or [] if o.strip()]
        if len(opzioni) > 4:
            raise SystemExit("al massimo quattro risposte fra cui scegliere")
        corpo["domanda"] = args.domanda.strip()[:500]
        corpo["opzioni"] = opzioni
    elif args.domanda or args.opzione:
        raise SystemExit("--domanda e --opzione vanno con --stato domanda")
    altri = []
    if args.anteprima:
        if args.stato != "domanda":
            raise SystemExit("--anteprima va con --stato domanda")
        altri = [_anteprima(args.uscita, args.anteprima, cartella)]
        corpo["immagine"] = ANTEPRIMA
    if args.stato == "da-approvare":
        if not args.modello:
            raise SystemExit("con --stato da-approvare ci vuole --modello: il caso "
                             "del parco costruito con `costruisci --solo`")
        altri = _modello_da_approvare(args, cartella)
    elif args.modello:
        raise SystemExit("--modello va con --stato da-approvare")
    # Prima la pagina dello Space, che non dipende da Glam: lo stato e la
    # domanda li legge dal registro dei casi, e con una domanda o un modello
    # da approvare lo Space scrive a chi ha lasciato l'email.
    if (_registra_stato(args.casi, cartella, args.codice, corpo, altri)
            and args.stato in ("domanda", "da-approvare")):
        _avvisa(args.spazio, args.codice)
    if args.stato in ("domanda", "non-risolto"):
        _in_attesa(args.repo, args.codice)
    # l'anteprima la mostra la pagina: Glam riceve i campi che conosce (GLAM.md)
    corpo.pop("immagine", None)
    try:
        risposta = _stato_a_glam(args.url, corpo)
    except urllib.error.HTTPError as e:
        if e.code == 400 and corpo["stato"] == "da-approvare":
            # Glam non conosce ancora lo stato: lo riceve come in lavorazione,
            # col messaggio che dice dove approvarlo
            stato, msg = DA_APPROVARE_IN_GLAM
            corpo = dict(corpo, stato=stato, messaggio=msg)
            try:
                risposta = _stato_a_glam(args.url, corpo)
                print("Glam non conosce ancora \"da-approvare\": l'ha ricevuto "
                      "come \"%s\" (vedi GLAM.md)" % stato)
                e = None
            except urllib.error.HTTPError as e2:
                e = e2
            except (urllib.error.URLError, OSError, ValueError) as e2:
                _glam_irraggiungibile(e2)
                raise SystemExit(1)
        if e is not None:
            _errore_glam(e)
            raise SystemExit(1)
    except (urllib.error.URLError, OSError, ValueError) as e:
        _glam_irraggiungibile(e)
        raise SystemExit(1)
    print("in Glam: caso %s \"%s\" -> %s%s" % (
        args.codice, corpo["nome"], corpo["stato"],
        " (utenti: %s)" % risposta["utenti"] if "utenti" in risposta else ""))


def _in_attesa(repo, cod):
    """Il caso aspetta chi l'ha caricato: `da-guardare` al posto del lucchetto
    `in-lavorazione` (CODA.md). Lo faceva la sessione a mano, e il T15 a
    soffietto l'ha dimenticato: alla risposta la routine ha trovato il
    lucchetto di poche ore prima, l'ha preso per il lavoro di un'altra
    sessione e si e' fermata, e il caso e' rimasto li'. Un guasto qui non
    ferma lo stato a Glam: lo dice, e le etichette vanno messe a mano."""
    try:
        issue = _issue(repo, cod)
        if issue is None:
            print("nessuna issue aperta per il caso %s: etichette non toccate" % cod)
            return
        _metti(repo, issue["number"], "da-guardare")
        _togli(repo, issue["number"], "in-lavorazione")
        print("issue #%d: da-guardare, via in-lavorazione - la risposta riapre "
              "il caso" % issue["number"])
    except SystemExit as e:
        print("etichette del caso %s non cambiate (%s): metti da-guardare e "
              "togli in-lavorazione a mano" % (cod, e))


def _stato_a_glam(glam, corpo):
    req = urllib.request.Request(
        glam.rstrip("/") + "/api/pack3d-case", method="POST",
        data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pack3d-studio"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _errore_glam(e):
    """Dice perche' Glam non ha preso lo stato del caso."""
    testo = e.read().decode("utf-8", "replace")[:300]
    if e.code == 401:
        print("Glam rifiuta il token (401): la credenziale dell'ambiente "
              "cloud per questo sito manca, o non e' uguale al secret "
              "PACK3D_IMPORT_TOKEN di Glam")
    elif _glam_assente(e.code, testo):
        pass
    elif e.code == 404:
        print("Glam non conosce ancora i casi della coda (404 su "
              "/api/pack3d-case): vedi DEPLOY.md, Glam Lab")
    else:
        print("Glam non ha preso lo stato del caso (HTTP %d): %s" % (e.code, testo))


# ---------------------------------------------------------------------------
# Il giro di un caso in tre comandi.
#
# Ogni passo della sessione che lavora un caso rilegge tutto quello che c'e'
# prima: venti passi meccanici - etichette, commenti, stato a Glam, il caso
# nel parco, la costruzione, le viste, la consegna - costavano quanto la
# correzione. Qui diventano tre comandi che stampano poche righe:
#
#   prepara    prende il caso (lucchetto e stato), lo mette nel parco, lo
#              costruisce col codice di adesso e fa UN foglio da guardare:
#              la pagina del PDF, il modello di adesso e quello respinto;
#   consegna   dopo la correzione: il modello da approvare a chi ha caricato
#              il PDF, il commento e le etichette;
#   approvato  dopo l'approvazione, se lo Space non l'ha gia' fatto da solo:
#              il modello in Glam, lo stato risolto, l'etichetta
#              da-rilasciare.
#
# Le chiamate a GitHub passano da `gh api`, quello della sessione.

REPO_CASI = "iccio84/pack3d-casi"
FERMI = ("da-guardare", "da-approvare", "da-rilasciare")
SEGNAPOSTO = "DA SCRIVERE"
# le voci di chi ha caricato il PDF, sulla issue (pack3d/coda.py)
VOCI = ("**Nota di chi ha caricato", "**Risposta dell'utente", "**Modello NON approvato",
        "**Modello approvato")


def _gh(metodo, percorso, corpo=None, tollera=()):
    """Una chiamata all'API di GitHub con `gh api`. SystemExit se non va,
    tranne per i codici in `tollera` (None)."""
    argomenti = ["gh", "api", "-X", metodo, percorso]
    if corpo is not None:
        argomenti += ["--input", "-"]
    try:
        r = subprocess.run(argomenti, capture_output=True, text=True, timeout=120,
                           input=json.dumps(corpo) if corpo is not None else None)
    except FileNotFoundError:
        raise SystemExit("manca `gh`: etichette e commenti mettili con gli strumenti "
                         "GitHub della sessione")
    if r.returncode != 0:
        testo = (r.stderr or r.stdout).strip()
        if any(str(c) in testo for c in tollera):
            return None
        raise SystemExit("GitHub, %s %s: %s" % (metodo, percorso, testo[:300]))
    return json.loads(r.stdout) if r.stdout.strip() else None


def _issue(repo, cod):
    for i in _gh("GET", "repos/%s/issues?state=open&per_page=100" % repo) or []:
        if not i.get("pull_request") and str(i.get("title", "")).startswith(
                "Caso nuovo %s:" % cod):
            return i
    return None


def _etichette(issue):
    return [e.get("name") for e in issue.get("labels") or [] if isinstance(e, dict)]


def _metti(repo, n, *nomi):
    _gh("POST", "repos/%s/issues/%d/labels" % (repo, n), {"labels": list(nomi)})


def _togli(repo, n, *nomi):
    for nome in nomi:
        _gh("DELETE", "repos/%s/issues/%d/labels/%s" % (repo, n, quote(nome)),
            tollera=(404, "Label does not exist"))


def _commenta(repo, n, testo):
    _gh("POST", "repos/%s/issues/%d/comments" % (repo, n), {"body": testo})


def _sessione():
    s = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID", "").strip()
    return "https://claude.ai/code/" + s.replace("cse_", "session_", 1) if s else ""


def _lucchetto_mio(repo, n):
    """True se l'ultimo lucchetto messo sulla issue e' di questa sessione.

    Una sessione che rilancia `prepara` dopo un errore (un pacchetto che
    mancava, il registro da riallineare) ritrova il suo lucchetto: non e' di
    un'altra sessione ne' di una morta, e non va «ripreso» con un commento."""
    import re
    sessione = _sessione()
    if not sessione:
        return False
    for c in reversed(_gh("GET", "repos/%s/issues/%d/comments?per_page=100" % (repo, n)) or []):
        m = re.search(r"In lavorazione in questa sessione: (https://claude\.ai/code/[A-Za-z0-9_]+)",
                      str(c.get("body") or ""))
        if m:
            return m.group(1) == sessione
    return False


def _aggiorna_registro(casi):
    _git(casi, "pull", "-q", "--rebase", "--autostash", "origin", "main")


def _manifesto(casi):
    with open(os.path.join(casi, "parco", "parco.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _voce_del_caso(casi, cod):
    """La voce del parco del caso della coda, o SystemExit."""
    for c in _manifesto(casi)["casi"]:
        if c.get("codice") == cod:
            return c
    raise SystemExit("il caso %s non e' nel parco: prima `prepara`" % cod)


def _nel_parco(casi, cartella, cod, verdetto):
    """(voce del parco del caso, nuova). Se non c'e' la crea: i PDF del caso
    in parco/pdf/, le opzioni scelte dall'utente (o quelle di serie), il nome
    che la pagina ha annunciato, il codice. `come_deve_venire` resta da
    scrivere: lo scrive chi guarda il PDF."""
    import re
    import shutil
    from pack3d import coda
    manifesto = _manifesto(casi)
    for c in manifesto["casi"]:
        if c.get("codice") == cod:
            return c, False
    contesto = verdetto.get("contesto") or {}
    file = [coda._nome_file(str(n)) for n in contesto.get("nomi") or []]
    file = [f for f in file if os.path.exists(os.path.join(cartella, f))] or sorted(
        f for f in os.listdir(cartella) if f.lower().endswith(".pdf"))
    if not file:
        raise SystemExit("nella cartella del caso non ci sono PDF")
    for f in file:
        dove = os.path.join(casi, "parco", "pdf", f)
        with open(os.path.join(cartella, f), "rb") as fh:
            dati = fh.read()
        if os.path.exists(dove):
            with open(dove, "rb") as fh:
                if fh.read() != dati:
                    raise SystemExit("in parco/pdf c'e' gia' un %s diverso: rinomina "
                                     "a mano il PDF del caso" % f)
        else:
            shutil.copyfile(os.path.join(cartella, f), dove)
    opzioni = dict(contesto.get("opzioni") or {})
    if opzioni.get("kind") == "riempimento" and opzioni.get("cu") == "carton":
        opzioni.setdefault("spessore", 2)
    elif opzioni.get("kind") in ("flowpack", "riempimento"):
        opzioni.setdefault("teeth", 20)
        opzioni.setdefault("soft", 5)
    elif opzioni.get("kind") == "carton":
        opzioni.setdefault("pezzi", len(file))
        opzioni.setdefault("spessore", 2)
    annunciato = nome_del_caso(verdetto)
    base = re.sub(r"[^a-z0-9]+", "_", annunciato.lower()).strip("_")[:40] or "caso"
    presi = {c["nome"] for c in manifesto["casi"]}
    nome, k = base, 2
    while nome in presi:
        nome, k = "%s_%d" % (base, k), k + 1
    voce = {"nome": nome, "file": file, "opzioni": opzioni, "codice": cod,
            "come_deve_venire": SEGNAPOSTO + ": com'e' giusto il modello, guardando il PDF"}
    if annunciato != os.path.splitext(file[0])[0][:120]:
        voce["glam"] = annunciato
    manifesto["casi"].append(voce)
    with open(os.path.join(casi, "parco", "parco.json"), "w", encoding="utf-8") as fh:
        json.dump(manifesto, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return voce, True


def _foglio(casi, cartella, voce, uscita):
    """Un'immagine sola da guardare: la pagina del PDF, il modello costruito
    adesso e, sotto, quello respinto. Piccola: ogni immagine guardata resta
    nella sessione fino alla fine."""
    from PIL import Image, ImageDraw
    from pack3d import vista
    pezzi = []
    try:
        pezzi.append(("il PDF", vista.pagina(
            os.path.join(casi, "parco", "pdf", voce["file"][0]), lato=900)))
    except Exception as e:                      # noqa: BLE001
        print("pagina del PDF non resa: %s" % e)
    for titolo, f in (("il modello di adesso", os.path.join(uscita, voce["nome"] + "_viste.png")),
                      ("il modello respinto", os.path.join(cartella, "viste_modello.jpg"))):
        if os.path.exists(f):
            pezzi.append((titolo, Image.open(f).convert("RGB")))
    if not pezzi:
        return None
    alto = 560
    righe, riga = [], []
    for titolo, im in pezzi:
        im = im.resize((max(1, round(im.width * alto / im.height)), alto))
        riga.append((titolo, im))
        if len(riga) == 2:
            righe.append(riga)
            riga = []
    if riga:
        righe.append(riga)
    largo = max(sum(im.width for _t, im in r) + 10 * (len(r) - 1) for r in righe)
    tela = Image.new("RGB", (largo, len(righe) * (alto + 22)), "white")
    disegno = ImageDraw.Draw(tela)
    y = 0
    for r in righe:
        x = 0
        for titolo, im in r:
            disegno.text((x + 4, y + 4), titolo, fill="black")
            tela.paste(im, (x, y + 22))
            x += im.width + 10
        y += alto + 22
    if tela.width > 1600:
        tela = tela.resize((1600, round(tela.height * 1600 / tela.width)))
    dove = os.path.join(uscita, "foglio.jpg")
    tela.save(dove, quality=85)
    return dove


def _voci(repo, n, cartella, uscita):
    """Le note e le risposte di chi ha caricato il PDF, dai commenti della
    issue: tutte in USCITA/voci.md, le ultime a video, accorciate."""
    commenti = _gh("GET", "repos/%s/issues/%d/comments?per_page=100" % (repo, n)) or []
    voci = [c.get("body") or "" for c in commenti if str(c.get("body") or "").startswith(VOCI)]
    with open(os.path.join(uscita, "voci.md"), "w", encoding="utf-8") as fh:
        fh.write("\n\n---\n\n".join(voci))
    foto = sorted(f for f in os.listdir(cartella)
                  if f.split("_")[0] in ("nota", "risposta", "rifiuto", "approvazione"))
    return voci, foto


def _famiglia(lettura, voce):
    """La famiglia letta di un caso, o quella dichiarata se la lettura non c'e'."""
    if isinstance(lettura, dict) and lettura.get("kind"):
        return lettura["kind"]
    return (voce.get("opzioni") or {}).get("kind")


def _simili(casi, voce, famiglia, ingombro, quanti=3):
    """I casi del parco gia' giusti piu' vicini a questo: della stessa
    famiglia letta, prima quelli con l'ingombro piu' simile. Il loro
    `come_deve_venire` dice com'e' venuto giusto un pack come questo."""
    import math
    lette = _letture_approvate(casi)
    mio = sorted(ingombro or [])
    vicini = []
    for c in _manifesto(casi)["casi"]:
        giusto = str(c.get("come_deve_venire") or "")
        if c["nome"] == voce["nome"] or not giusto or giusto.startswith(SEGNAPOSTO):
            continue
        if _famiglia(lette.get(c["nome"]), c) != famiglia:
            continue
        suo = sorted((c.get("misure") or {}).get("ingombro") or [])
        if len(suo) == 3 and len(mio) == 3 and min(suo + mio) > 0:
            d = sum(abs(math.log(a / b)) for a, b in zip(mio, suo))
        else:
            d = float("inf")
        vicini.append((d, c["nome"], c))
    return [c for _d, _n, c in sorted(vicini, key=lambda x: x[:2])[:quanti]]


def _schede(testo, quante=3):
    """I titoli delle schede di DIFETTI.md le cui parole stanno in `testo`,
    prima quelle con piu' parole trovate."""
    try:
        with open(os.path.join(QUI, "DIFETTI.md"), encoding="utf-8") as fh:
            righe = fh.read().splitlines()
    except OSError:
        return []
    schede, titolo = [], None
    for r in righe:
        if r.startswith("## "):
            titolo = r[3:].strip()
        elif titolo and r.startswith("Parole:"):
            schede.append((titolo, [p.strip().lower() for p in r[7:].split(",") if p.strip()]))
    testo = testo.lower()
    punti = [(sum(1 for p in parole if p in testo), -i, titolo)
             for i, (titolo, parole) in enumerate(schede)]
    return [titolo for n, _i, titolo in sorted(punti, reverse=True) if n][:quante]


def prepara(args):
    """Prende un caso libero e lo prepara: vedi sopra."""
    from contextlib import redirect_stdout
    import io
    cod = args.codice
    _aggiorna_registro(args.casi)
    cartella, verdetto = _caso_in_coda(args.casi, cod)
    if _approvato(cartella) and _ultimo_stato(cartella) == "approvato":
        # approvato, e lo Space non l'ha mandato in Glam: non c'e' niente da
        # correggere, solo da consegnare
        print("il caso %s e' stato approvato: lo mando in Glam" % cod)
        return approvato(argparse.Namespace(casi=args.casi, codice=cod, repo=args.repo,
                                            glam=args.glam, spazio=args.spazio,
                                            messaggio=None, categoria="Casi risolti"))
    issue = _issue(args.repo, cod)
    if issue is None:
        raise SystemExit("nessuna issue aperta per il caso %s" % cod)
    n = issue["number"]
    etichette = _etichette(issue)
    fermi = [e for e in etichette if e in FERMI]
    if fermi:
        raise SystemExit("il caso %s non e' libero: ha %s (CODA.md)" % (cod, ", ".join(fermi)))
    mio = "in-lavorazione" in etichette and _lucchetto_mio(args.repo, n)
    if "in-lavorazione" in etichette and not (args.riprendi or mio):
        raise SystemExit("il caso %s ha gia' il lucchetto in-lavorazione. Se l'ha preso "
                         "un'altra sessione da poco, prendi il caso libero successivo "
                         "(o hai finito); se e' di una sessione morta (piu' di sei ore, "
                         "negli eventi della issue) usa --riprendi" % cod)
    if mio:
        print("il lucchetto del caso %s e' gia' di questa sessione: riparto" % cod)
    else:
        _metti(args.repo, n, "in-lavorazione")
        sessione = _sessione()
        _commenta(args.repo, n, "%s%s." % ("Ripreso: il lucchetto era di una sessione ferma "
                                           "da piu' di sei ore. In lavorazione"
                                           if args.riprendi and "in-lavorazione" in etichette
                                           else "In lavorazione",
                                           " in questa sessione: " + sessione if sessione else ""))
    uscita = args.uscita or "/tmp/caso_" + cod
    os.makedirs(uscita, exist_ok=True)
    rumore = io.StringIO()
    with redirect_stdout(rumore):
        try:
            caso(argparse.Namespace(url=args.glam, casi=args.casi, codice=cod,
                                    stato="in-lavorazione", messaggio=None, domanda=None,
                                    opzione=None, anteprima=None, modello=None, uscita=uscita,
                                    spazio=args.spazio))
            a_glam = "si'"
        except SystemExit:
            a_glam = "no: " + (rumore.getvalue().strip().splitlines() or ["?"])[-1][:200]
    voce, nuova = _nel_parco(args.casi, cartella, cod, verdetto)
    if nuova:
        _commit_registro(args.casi, ["parco/parco.json"] + ["parco/pdf/" + f for f in voce["file"]],
                         "Caso %s: nel parco come %s" % (cod, voce["nome"]))
    with redirect_stdout(rumore):
        costruisci(argparse.Namespace(casi=args.casi, uscita=uscita, codice=None,
                                      solo=[voce["nome"]]))
    with open(os.path.join(uscita, voce["nome"] + ".json"), encoding="utf-8") as fh:
        esito = json.load(fh)
    foglio = _foglio(args.casi, cartella, voce, uscita)
    voci, foto = _voci(args.repo, n, cartella, uscita)
    contesto = verdetto.get("contesto") or {}
    print("caso %s, issue #%d: in lavorazione (stato a Glam: %s)" % (cod, n, a_glam))
    print("esito della coda: %s - %s" % (verdetto.get("esito"),
                                          str(verdetto.get("motivo") or "")[:300]))
    for d in (verdetto.get("difetti") or [])[:6]:
        print("  - %s" % str(d)[:200])
    for a in (contesto.get("avvisi") or [])[:2]:
        print("  avviso: %s" % str(a)[:300])
    print("nel parco come %s%s, opzioni %s" % (voce["nome"], " (nuovo)" if nuova else "",
                                               json.dumps(voce.get("opzioni"))))
    if esito.get("stato") == 200:
        print("costruito adesso: ok in %s s, ingombro %s mm" % (esito.get("secondi"),
                                                               esito.get("ingombro_mm")))
    else:
        print("costruito adesso: %s - %s" % (esito.get("stato"),
                                             str((esito.get("avvisi") or [""])[0])[:300]))
    print("avvisi della costruzione: %d, in %s" % (len(esito.get("avvisi") or []),
                                                   os.path.join(uscita, voce["nome"] + ".json")))
    print("foglio da guardare: %s" % foglio)
    print("voci di chi l'ha caricato: %d, in %s%s" % (
        len(voci), os.path.join(uscita, "voci.md"),
        "; foto: " + ", ".join(foto) if foto else ""))
    for v in voci[-3:]:
        print("  > " + " ".join(v.split())[:600])
    no = sum(1 for v in voci if v.startswith("**Modello NON approvato"))
    if no:
        print("respinto %d %s: prima di un'altra interpretazione, la domanda con "
              "l'anteprima%s (CODA.md, *Dopo un Non approvo, prima si chiede*)"
              % (no, "volta" if no == 1 else "volte",
                 ", sempre: e' il secondo no" if no >= 2 else
                 ", se la correzione non e' una sola"))
    # da dove partire: i casi gia' giusti che gli somigliano e le schede dei
    # difetti che il verdetto e le voci nominano
    try:
        lettura = _leggi_tutti(args.casi, [voce]).get(voce["nome"])
    except SystemExit:
        lettura = None
    famiglia = _famiglia(lettura, voce)
    simili = _simili(args.casi, voce, famiglia, esito.get("ingombro_mm"))
    print("famiglia letta: %s; casi simili gia' giusti nel parco: %d" % (famiglia, len(simili)))
    for c in simili:
        print("  ~ %s, ingombro %s: %s" % (c["nome"], (c.get("misure") or {}).get("ingombro"),
                                           " ".join(c["come_deve_venire"].split())[:300]))
    schede = _schede(" ".join([str(verdetto.get("motivo") or "")]
                              + [str(d) for d in verdetto.get("difetti") or []] + voci))
    if schede:
        print("schede dei difetti da leggere (DIFETTI.md): " + "; ".join(schede))
    if nuova:
        print("da fare: scrivi `come_deve_venire` della voce %s in parco/parco.json" % voce["nome"])


def _approva_misure(casi, nome, esito):
    """Scrive nel manifesto le misure di `esito` come quelle approvate del
    caso `nome`. Niente, se l'esito non le ha."""
    if not esito.get("misure") or "errore" in esito["misure"]:
        return
    manifesto = _manifesto(casi)
    for caso in manifesto["casi"]:
        if caso["nome"] == nome:
            caso["misure"] = esito["misure"]
    with open(os.path.join(casi, "parco", "parco.json"), "w", encoding="utf-8") as fh:
        json.dump(manifesto, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def _esito_di_adesso(casi, voce, uscita):
    """L'esito della costruzione del caso col codice di adesso: quello che
    c'e' in `uscita`, o lo ricostruisce se e' di un altro codice o non si era
    costruito."""
    from contextlib import redirect_stdout
    import io
    from pack3d import versione
    f = os.path.join(uscita, voce["nome"] + ".json")
    esito = {}
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            esito = json.load(fh)
    if esito.get("versione") != versione.impronta(QUI) or esito.get("stato") != 200:
        with redirect_stdout(io.StringIO()):
            costruisci(argparse.Namespace(casi=casi, uscita=uscita, codice=None,
                                          solo=[voce["nome"]]))
        with open(f, encoding="utf-8") as fh:
            esito = json.load(fh)
    return esito


def verifica_caso(args):
    """Prima della PR, quello che il rilascio guarderebbe dopo: il caso si
    costruisce senza difetti, la texture e' lo steso dritto, le prove veloci
    passano e la lettura degli altri casi del parco non cambia. Stampa anche
    `come_deve_venire` accanto alle misure del modello, da confrontare. Esce
    con 1 se qualcosa non va; `consegna` vuole che sia passata col codice
    che consegna."""
    from contextlib import redirect_stdout
    import io
    from pack3d import verifica as controlli
    cod = args.codice
    voce = _voce_del_caso(args.casi, cod)
    nome = voce["nome"]
    uscita = args.uscita or "/tmp/caso_" + cod
    os.makedirs(uscita, exist_ok=True)
    problemi = []
    giusto = str(voce.get("come_deve_venire") or "")
    if not giusto or giusto.startswith(SEGNAPOSTO):
        problemi.append("`come_deve_venire` della voce %s non e' scritto" % nome)
    esito = _esito_di_adesso(args.casi, voce, uscita)
    if esito.get("stato") != 200:
        problemi.append("il caso non si costruisce (%s): %s" % (
            esito.get("stato"), str((esito.get("avvisi") or [""])[0])[:300]))
    for d in controlli.difetti([str(a) for a in esito.get("avvisi") or []]):
        problemi.append("difetto della costruzione: %s" % d[:300])
    rumore = io.StringIO()
    with redirect_stdout(rumore):
        try:
            stesi(argparse.Namespace(casi=args.casi, uscita=uscita, solo=[nome]))
        except SystemExit:
            problemi.append("la texture non e' lo steso dritto:\n" + rumore.getvalue()[-800:])
    prove = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "prove",
                            "-p", "test_*.py"], cwd=QUI, capture_output=True, text=True)
    if prove.returncode:
        problemi.append("le prove veloci non passano:\n" + prove.stderr[-800:])
    approvate = _letture_approvate(args.casi)
    lette = _leggi_tutti(args.casi, _casi(args.casi))
    cambiate = [n for n, l in lette.items() if n != nome and n in approvate
                and l != approvate[n]]
    for n in cambiate:
        problemi.append("la lettura di %s cambia: se e' voluto, approvala con `letture "
                        "--approva --solo %s` e scrivilo nella PR\n%s"
                        % (n, n, "\n".join(_differenze(approvate[n], lette[n])[:8])))
    if nome in approvate and lette.get(nome) != approvate[nome]:
        print("la lettura del caso cambia rispetto a quella approvata:")
        print("\n".join(_differenze(approvate[nome], lette.get(nome))[:8]))
    print("come deve venire: %s" % " ".join(giusto.split())[:500])
    print("il modello: ingombro %s mm, misure %s" % (esito.get("ingombro_mm"),
                                                     json.dumps(esito.get("misure"))[:300]))
    for r in esito.get("misure_cambiate") or []:
        print("  misura approvata cambiata: %s" % r)
    print("da guardare accanto al PDF: %s" % os.path.join(uscita, nome + "_viste.png"))
    with open(os.path.join(uscita, "verifica.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(versione=esito.get("versione"), ok=not problemi, problemi=problemi,
                       lettura=lette.get(nome)), fh, ensure_ascii=False, indent=1)
    if problemi:
        print("\nVERIFICA NON PASSATA, %d problemi:" % len(problemi))
        for p in problemi:
            print("- " + p)
        raise SystemExit(1)
    print("verifica passata: %d letture del parco uguali, prove veloci e steso a posto"
          % (len(lette) - 1))


def consegna(args):
    """Il modello corretto a chi ha caricato il caso, da approvare."""
    from contextlib import redirect_stdout
    import io
    cod = args.codice
    _aggiorna_registro(args.casi)
    cartella, _verdetto = _caso_in_coda(args.casi, cod)
    voce = _voce_del_caso(args.casi, cod)
    if not voce.get("come_deve_venire") or voce["come_deve_venire"].startswith(SEGNAPOSTO):
        raise SystemExit("scrivi prima `come_deve_venire` della voce %s in parco/parco.json"
                         % voce["nome"])
    issue = _issue(args.repo, cod)
    if issue is None:
        raise SystemExit("nessuna issue aperta per il caso %s" % cod)
    uscita = args.uscita or "/tmp/caso_" + cod
    esito = _esito_di_adesso(args.casi, voce, uscita)
    if esito.get("stato") != 200:
        raise SystemExit("il caso non si costruisce col codice di adesso (%s): %s"
                         % (esito.get("stato"), str((esito.get("avvisi") or [""])[0])[:300]))
    try:
        with open(os.path.join(uscita, "verifica.json"), encoding="utf-8") as fh:
            prova = json.load(fh)
    except (OSError, ValueError):
        prova = {}
    if args.senza_verifica:
        args.commento += "\n\nConsegnato senza `verifica`: %s" % args.senza_verifica
    elif not prova.get("ok") or prova.get("versione") != esito.get("versione"):
        raise SystemExit("prima `verifica` col codice di adesso, e che passi (CODA.md, "
                         "*Il giro*, punto 6)")
    rumore = io.StringIO()
    # le misure del modello consegnato diventano quelle approvate del caso,
    # insieme a `come_deve_venire`: il rilascio le confronta
    if "misure" not in esito:
        # costruito prima che le misure ci fossero: si misura il suo GLB
        with open(os.path.join(uscita, voce["nome"] + ".glb"), "rb") as fh:
            esito["misure"], _ = _misura(fh.read(), voce)
    _approva_misure(args.casi, voce["nome"], esito)
    registro = ["parco/parco.json"]
    if isinstance(prova.get("lettura"), dict):
        # e la lettura del PDF, che `letture` confronta coi casi di dopo
        approvate = _letture_approvate(args.casi)
        approvate[voce["nome"]] = prova["lettura"]
        with open(os.path.join(args.casi, LETTURE), "w", encoding="utf-8") as fh:
            json.dump(approvate, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        registro.append(LETTURE)
    _commit_registro(args.casi, registro, "Caso %s: com'e' giusto" % cod)
    with redirect_stdout(rumore):
        try:
            caso(argparse.Namespace(url=args.glam, casi=args.casi, codice=cod,
                                    stato="da-approvare", messaggio=args.messaggio,
                                    domanda=None, opzione=None, anteprima=None,
                                    modello=voce["nome"], uscita=uscita, spazio=args.spazio))
        except SystemExit:
            pass
    # registrato? lo stato e il modello sono nel registro prima di Glam
    try:
        with open(os.path.join(cartella, "stato.json"), encoding="utf-8") as fh:
            ultimo = (json.load(fh).get("storia") or [{}])[-1]
        with open(os.path.join(cartella, "modello.json"), encoding="utf-8") as fh:
            registrato = json.load(fh).get("md5") == esito.get("md5")
    except (OSError, ValueError):
        ultimo, registrato = {}, False
    if ultimo.get("stato") != "da-approvare" or not registrato:
        print(rumore.getvalue()[-1500:])
        raise SystemExit("il modello da approvare non e' stato registrato: vedi sopra")
    n = issue["number"]
    _commenta(args.repo, n, args.commento.strip() + "\n\nIl modello corretto (`%s`, "
              "costruito col codice della settimana) aspetta l'approvazione di chi ha "
              "caricato il PDF." % esito.get("md5"))
    _metti(args.repo, n, "da-approvare")
    _togli(args.repo, n, "in-lavorazione")
    glam_ok = "in Glam: caso" in rumore.getvalue()
    print("caso %s consegnato da approvare (issue #%d)%s" % (
        cod, n, "" if glam_ok else "; Glam non ha preso lo stato: scrivilo nel riassunto"))
    _prossimo(args.spazio, cod)


def approvato(args):
    """Dopo l'approvazione: il modello in Glam, lo stato risolto, la issue
    da-rilasciare. Lo fa lo Space da solo, se ha il token di Glam; questo e'
    per quando non l'ha fatto."""
    from contextlib import redirect_stdout
    import io
    cod = args.codice
    _aggiorna_registro(args.casi)
    cartella, _verdetto = _caso_in_coda(args.casi, cod)
    if not _approvato(cartella):
        raise SystemExit("chi ha caricato il caso %s non ha ancora approvato il modello" % cod)
    voce = _voce_del_caso(args.casi, cod)
    issue = _issue(args.repo, cod)
    if issue is None:
        raise SystemExit("nessuna issue aperta per il caso %s" % cod)
    n = issue["number"]
    if "da-rilasciare" in _etichette(issue):
        print("il caso %s e' gia' in Glam e da rilasciare (issue #%d): niente da fare" % (cod, n))
        return
    rumore = io.StringIO()
    with redirect_stdout(rumore):
        try:
            glam(argparse.Namespace(url=args.glam, casi=args.casi, nome=voce["nome"],
                                    uscita=os.path.join(cartella, "-"),
                                    categoria=args.categoria))
            in_glam = True
        except SystemExit:
            in_glam = False
    detto = rumore.getvalue().strip()
    nome = nome_glam(voce)
    messaggio = args.messaggio or ("Il modello corretto e' in Glam Lab, nella sezione "
                                   "«Costruisci modello 3D da PDF», cartella «%s», col "
                                   "nome «%s»." % (args.categoria, nome))
    with redirect_stdout(io.StringIO()):
        try:
            caso(argparse.Namespace(url=args.glam, casi=args.casi, codice=cod,
                                    stato="risolto", messaggio=messaggio, domanda=None,
                                    opzione=None, anteprima=None, modello=None, uscita="/tmp",
                                    spazio=args.spazio))
        except SystemExit:
            pass
    _commenta(args.repo, n, ("**In Glam**: «%s», cartella «%s» (%s)." % (
        nome, args.categoria, detto.splitlines()[-1][:300] if detto else "")
        if in_glam else "**Glam non ha preso il modello** (%s): il caso e' risolto lo "
        "stesso, e il PDF si puo' ricostruire in Glam a mano." % detto[-300:])
        + "\n\nResta aperta con `da-rilasciare`: la chiude il rilascio, dopo la prova sullo Space.")
    _metti(args.repo, n, "da-rilasciare")
    _togli(args.repo, n, "in-lavorazione", "da-approvare")
    print("caso %s: %s, da rilasciare (issue #%d)" % (
        cod, "in Glam" if in_glam else "Glam non l'ha preso", n))


# `stesi`: una texture si cerca sulla pagina senza i livelli tecnici
# (`strati.senza_tecnici`: il DT sopra la grafica pesava piu' della grafica) e
# senza le coperture (`artwork.senza_coperture`),
# resa perche' la texture ci stia su almeno STESI_PX pixel - fra 30 e 72 dpi -
# girata di 0, 90, 180 e 270 gradi e a scale fra 100 e 400 dpi. Il verso dritto
# vince se e' il migliore a meno di STESI_PARI; un altro vince se lo stacca di
# STESI_MARGINE; nel mezzo e' incerta, da guardare. Sotto STESI_SOGLIA la
# texture sulla pagina non si ritrova. Un pack quasi simmetrico - il film di
# un flowpack piccolo, bianco e azzurro sopra e sotto - pareggia dritto e
# capovolto: e' giusto che lo dica, e non che scelga.
STESI_PX = 300
STESI_SOGLIA = 0.3
STESI_PARI = 0.02
STESI_MARGINE = 0.1


def _correlazione(P, t):
    """La correlazione normalizzata di `t` su `P` (grigi, `t` piu' piccolo):
    `(massimo, y, x)`."""
    import numpy as np
    H, W = P.shape
    h, w = t.shape
    tz = t - t.mean()
    nt = np.sqrt((tz ** 2).sum())
    if h > H or w > W or nt < 1e-6:
        return -1.0, 0, 0
    F = (H + h, W + w)
    num = np.fft.irfft2(np.fft.rfft2(P, F) * np.fft.rfft2(tz[::-1, ::-1], F),
                        F)[h - 1:H, w - 1:W]

    def finestra(A):
        S = np.cumsum(np.cumsum(np.pad(A, ((1, 0), (1, 0))), 0), 1)
        return S[h:, w:] - S[:-h, w:] - S[h:, :-w] + S[:-h, :-w]
    s1, s2 = finestra(P), finestra(P ** 2)
    var = s2 - s1 ** 2 / (h * w)
    c = num / (np.sqrt(np.maximum(var, 1e-9)) * nt)
    c[var < 1e-3 * h * w] = -1
    k = np.unravel_index(np.argmax(c), c.shape)
    return float(c[k]), int(k[0]), int(k[1])


def _pagina_variata(sorgente, destinazione, variante, kind=None):
    """Una copia del PDF variata come la manderebbe un altro cliente. Le
    varianti si sommano con `+` (`appiattito+giro90`), nell'ordine scritto:

    - `giro90`, `giro180`, `giro270`: la pagina girata, gradi antiorari,
      cotti nel contenuto come li cuoce `artwork.pagina_girata`;
    - `rotate`: la pagina che si vede come l'originale, ma salvata girata
      con /Rotate 90 (il contenuto girato all'indietro);
    - `scala1.03`: il disegno in scala;
    - `spostato`: il disegno spostato su una tavola piu' grande;
    - `miniatura`: una copia della pagina a un quinto, accanto, come le
      miniature dei cartigli;
    - `copertina`: una pagina in piu' davanti, senza disegno;
    - `quote`, `cornice`, `legenda`: lo stesso PDF con piu' disegno nella
      penna del DT - quote lunghe quanto lo steso, una cornice, una legenda
      attaccata - come lo disegnano altri grafici (`_disegno_in_piu`);
    - `appiattito`: ripassato da Ghostscript con le scritte in tracciati,
      come un PDF di stampa appiattito - senza testo vivo e senza livelli.
      Attenzione: Ghostscript butta anche gran parte del disegno tecnico
      (sul wafer T1 le linee da 1187 a 212, le curve da 552 a 6), e il
      pack non lo risolverebbe nessuno: misura Ghostscript piu' che il
      codice, e nel giro della settimana non c'e'.

    Il documento si clona intero: i livelli che la pulizia spegne per nome
    devono restare gli stessi oggetti a cui punta il contenuto. Copiati a
    parte, il livello tecnico del T10 al lampone non si spegneva piu', e le
    sue quote entravano nella fustella."""
    import tempfile
    passi = variante.split("+")
    corrente = sorgente
    for k, passo in enumerate(passi):
        if k + 1 == len(passi):
            uscita = destinazione
        else:
            fd, uscita = tempfile.mkstemp(suffix=".pdf", dir=os.path.dirname(destinazione))
            os.close(fd)
        _un_passo(corrente, uscita, passo, kind, insieme=set(passi) - {passo})
        if corrente != sorgente:
            os.remove(corrente)
        corrente = uscita


def _riquadro_tecnico(pdf, pagina, kind=None):
    """Il riquadro del disegno tecnico nella pagina e la sua penna:
    `((x0, y0, x1, y1), (spessore, (r, g, b)))` nel telaio di misura (punti,
    y dall'alto), o None. Il riquadro e' quello delle linee lunghe della
    penna tecnica: per un flowpack, lo steso; per le altre famiglie il DT
    principale intero (`tools.dt_principale`), alette e falde comprese - le
    linee lunghe di un astuccio sono il solo corpo."""
    from pack3d.dieline import _technical_pens
    from pack3d.tracciati import segmenti, _canali
    segs, W, H = segmenti(pdf, pagina)
    penne = _technical_pens(segs, W, H)
    if not penne:
        return None
    lunghezza = {}
    for k, c, a, b, st in segs:
        if st in penne:
            lunghezza[st] = lunghezza.get(st, 0.0) + (b - a)
    penna = max(lunghezza, key=lunghezza.get)
    tec = [sg for sg in segs if sg[4] in penne]
    lh = max((b - a for k, c, a, b, st in tec if k == "H"), default=0.0)
    lv = max((b - a for k, c, a, b, st in tec if k == "V"), default=0.0)
    hs = [c for k, c, a, b, st in tec if k == "H" and b - a >= 0.6 * lh]
    vs = [c for k, c, a, b, st in tec if k == "V" and b - a >= 0.6 * lv]
    if not hs or not vs:
        return None
    riquadro = (min(vs), min(hs), max(vs), max(hs))
    if kind not in (None, "flowpack"):
        # la fustella com'e' letta: alette e linguette comprese (sul T3 di
        # biscotti escono di 11-16 mm dal riquadro del DT principale), e una
        # quota o una cornice non attraversano mai la fustella. Il DT
        # principale solo se la lettura non c'e': sul T4 di wafer e' la
        # miniatura nel cartiglio
        from pack3d import tools
        from pack3d.dieline import PT2MM
        try:
            if pagina != 0:
                raise ValueError
            from pack3d import dieline
            riquadro = tuple(dieline.analyze(pdf).bbox)
        except Exception:
            dt = tools.dt_principale(pdf, pagina)
            if dt:
                mm = 1.0 / PT2MM
                riquadro = (dt[0] * mm, dt[1] * mm, (dt[0] + dt[2]) * mm, (dt[1] + dt[3]) * mm)
    elif pagina == 0:
        # un flowpack: lo steso come lo legge il codice di adesso, che sui
        # casi del parco e' quello giusto. Le linee lunghe da sole prendono
        # anche la seconda vista della tavola, quando ce n'e' una
        try:
            from pack3d import flowpack as fpk
            from pack3d.famiglie.flowpack import analisi_flowpack
            _box, fp, ripiego = analisi_flowpack(pdf)
            if ripiego is None:
                riquadro = fpk.foglio_in_pagina(fp)
        except Exception:
            pass
    # la penna e' quella delle linee dentro il riquadro. La piu' usata della
    # pagina puo' essere un'altra: su una tavola le viste piccole in una penna
    # piu' sottile, e le quote disegnate con quella non erano del DT dello
    # steso, che le cerca nella penna sua
    x0, y0, x1, y1 = riquadro
    dentro = {}
    for k, c, a, b, st in tec:
        if k == "H":
            ok = y0 - 3 <= c <= y1 + 3 and a >= x0 - 3 and b <= x1 + 3
        else:
            ok = x0 - 3 <= c <= x1 + 3 and a >= y0 - 3 and b <= y1 + 3
        if ok:
            dentro[st] = dentro.get(st, 0.0) + (b - a)
    if dentro:
        penna = max(dentro, key=dentro.get)
    rgb = _canali(penna[1]) or [0, 0, 0]
    return riquadro, (max(penna[0], 0.1), rgb)


def _ingombro_tecnico(pdf, pagina, riquadro):
    """Il riquadro del disegno tecnico attorno allo steso: le linee lunghe
    della penna tecnica che toccano il riquadro dello steso. Il DT puo'
    andare oltre lo steso - il filo dell'abbondanza, una striscia sotto - e
    una cornice di tavola gli sta attorno, non lo attraversa."""
    from pack3d.dieline import _technical_pens
    from pack3d.tracciati import segmenti
    segs, W, H = segmenti(pdf, pagina)
    penne = _technical_pens(segs, W, H)
    tec = [sg for sg in segs if sg[4] in penne]
    x0, y0, x1, y1 = riquadro
    lh = max((b - a for k, c, a, b, st in tec if k == "H"), default=0.0)
    lv = max((b - a for k, c, a, b, st in tec if k == "V"), default=0.0)
    t = 6.0  # due millimetri
    for k, c, a, b, st in tec:
        if k == "H" and b - a >= 0.6 * lh and y0 - t <= c <= y1 + t and b >= x0 - t and a <= x1 + t:
            x0, x1, y0, y1 = min(x0, a), max(x1, b), min(y0, c), max(y1, c)
        elif k == "V" and b - a >= 0.6 * lv and x0 - t <= c <= x1 + t and b >= y0 - t and a <= y1 + t:
            x0, x1, y0, y1 = min(x0, c), max(x1, c), min(y0, a), max(y1, b)
    return x0, y0, x1, y1


def _fuori_dalla_stampa(pdf, pagina, ingombro, d):
    """L'ingombro allargato alla stampa attaccata al disegno, perche' la
    cornice a `d` non attraversi la grafica.

    Una cornice di tavola sta attorno a tutto: al disegno e alla sua grafica.
    Sul T1 a fondo argento il fondo grigio esce fino a 15 mm oltre il
    riquadro tecnico, e la cornice a dieci millimetri gli passava in mezzo:
    il giudice dello steso prendeva il riquadro chiuso dalla cornice - dalla
    saldatura alla cornice, largo uguale per caso - perche' oltre la cornice
    la stampa finiva e oltre il taglio no. Si prendono le macchie
    d'inchiostro che toccano l'ingombro, su tutta la pagina: sul cono e sulla
    scatola a punta la grafica e' molto piu' grande del riquadro della
    fustella. Una cornice che cosi' esce dalla pagina non si vede, e la
    variante e' l'originale.

    Le macchie sono quelle piene: i tratti sottili (meno di 5 pt, quasi due
    millimetri) si tolgono prima. Attaccate per i fili dei richiami, la
    stampa arrivava ai riquadri delle note e alle quote: sul pane ripieno T2
    la cornice prendeva meta' dell'altra vista, su kp_cheesecake i
    riquadri dei caratteri a destra, e il giudice dello steso leggeva il
    riquadro della cornice. Sul T1 a fondo argento resta il fondo grigio, che
    e' la stampa vera."""
    import numpy as np
    from scipy.ndimage import binary_opening, label
    from pack3d.dieline import render_page
    x0, y0, x1, y1 = ingombro
    im = np.asarray(render_page(pdf, pagina, 1.0).convert("RGB"))
    H, W = im.shape[:2]
    piene = binary_opening(im.min(axis=2) < 230, structure=np.ones((5, 5), bool))
    lab, n = label(piene)
    if n == 0:
        return ingombro
    dentro = np.unique(lab[min(max(int(y0), 0), H):min(max(int(y1) + 1, 0), H),
                           min(max(int(x0), 0), W):min(max(int(x1) + 1, 0), W)])
    dentro = dentro[dentro > 0]
    if not len(dentro):
        return ingombro
    ys, xs = np.nonzero(np.isin(lab, dentro))
    return (min(x0, float(xs.min())), min(y0, float(ys.min())),
            max(x1, float(xs.max() + 1)), max(y1, float(ys.max() + 1)))


def _fuori_dai_tratti(pdf, pagina, ingombro, d):
    """L'ingombro allargato perche' la cornice a `d` non attraversi il DT.

    `_ingombro_tecnico` conta le sole righe orizzontali e verticali. Un
    tratto obliquo della penna tecnica che parte dal disegno e va oltre la
    cornice e' disegno, e la cornice gli passa fuori: sul display a scatola
    da 15 il tratteggio sopra il coperchio, che sale 24 mm oltre l'ultima
    riga; sul ballotin i lati inclinati dei fianchi. Le righe dritte no: oltre
    il disegno sono le quote e le note, e la cornice di una tavola ci passa
    anche sopra. I tratti che restano dentro la cornice, o che non toccano il
    disegno, non la spostano."""
    import numpy as np
    from pack3d.ballotin import polilinee
    from pack3d.dieline import PT2MM, _technical_pens
    from pack3d.tracciati import segmenti
    segs, W, H = segmenti(pdf, pagina)
    penne = set(_technical_pens(segs, W, H))
    x0, y0, x1, y1 = ingombro
    t = 6.0  # due millimetri
    n0, n1, n2, n3 = ingombro
    for p, st in polilinee(pdf, pagina, lambda st: st in penne):
        q = p / PT2MM
        a0, b0 = (float(v) for v in q.min(axis=0))
        a1, b1 = (float(v) for v in q.max(axis=0))
        if not (a1 >= x0 - t and a0 <= x1 + t and b1 >= y0 - t and b0 <= y1 + t):
            continue
        dd = np.abs(np.diff(q, axis=0))
        if not np.any((dd[:, 0] > 0.05 * dd[:, 1]) & (dd[:, 1] > 0.05 * dd[:, 0])):
            continue
        if a0 <= x0 - d or b0 <= y0 - d or a1 >= x1 + d or b1 >= y1 + d:
            n0, n1 = min(n0, a0), min(n1, b0)
            n2, n3 = max(n2, a1), max(n3, b1)
    return n0, n1, n2, n3


def _penna_letta(pdf, pagina, riquadro, w, rgb):
    """`(spessore, colore)` della penna della fustella come la legge
    `dieline.segmenti` - la chiave con cui la lettura distingue le penne -,
    o None. Si prendono le linee che pdfium da' alla penna (`w`, `rgb`)
    dentro il riquadro, e si guarda con che chiave pdfplumber legge le
    stesse linee: lo spessore di pdfium e' nel telaio del tratto (sul cono,
    disegnato in scala, 0,2 invece di 1), e il colore e' convertito."""
    from collections import Counter
    from pack3d import dieline
    from pack3d.tracciati import segmenti
    x0, y0, x1, y1 = riquadro
    colore = "(%d, %d, %d)" % tuple(int(v) for v in rgb[:3])

    def dentro(k, c, a, b):
        if k == "H":
            return y0 - 3 <= c <= y1 + 3 and a >= x0 - 3 and b <= x1 + 3
        return x0 - 3 <= c <= x1 + 3 and a >= y0 - 3 and b <= y1 + 3
    segs, _W, _H = segmenti(pdf, pagina)
    nostri = [(k, c, a, b) for k, c, a, b, st in segs
              if st[1] == colore and abs(max(st[0], 0.1) - w) <= 0.02 and dentro(k, c, a, b)]
    if not nostri:
        return None
    letti = [sg for sg in dieline.segmenti(pdf, pagina) if dentro(*sg[:4])]
    conta = Counter()
    for k, c, a, b in nostri:
        for k2, c2, a2, b2, st in letti:
            if k2 == k and abs(c2 - c) <= 0.6 and min(b, b2) - max(a, a2) >= 0.5 * (b - a):
                conta[st] += b - a
                break
    if not conta:
        return None
    return max(conta, key=conta.get)


def _colore_della_penna(pagina, spessore, rgb=None, chiave=None):
    """Il colore con cui la pagina disegna i tratti di `spessore`, come lo
    scrive il PDF: `(operatore, spazio, valori)` - "K", "RG", "G" per gli
    spazi del dispositivo (spazio None), "CS" per uno spazio dalle risorse
    (la tinta piatta della fustella, spazio = l'oggetto) - o None.

    La lettura distingue le penne dal colore com'e' scritto: una tinta piatta,
    un CMYK e lo stesso colore in RGB sono tre penne. Le varianti di stile
    disegnavano in RGB, col colore che pdfium da' convertito: su 49 PDF del
    parco su 53 - 39 in tinta piatta, 10 in CMYK - le quote, la cornice e la
    legenda erano un'altra penna, e il filtro delle penne le scartava. Si
    scorre il contenuto (anche dentro i gruppi di oggetti), e vince il colore
    coi tratti piu' lunghi a quello spessore, contati in operatori di
    percorso. Con `rgb` (il colore che ne da' pdfium) un colore del
    dispositivo che, convertito alla buona, gli sta lontano non e' la
    fustella: sul display KMS T10 la grafica ha piu' tratti neri da 0,5 della
    fustella ciano. Una tinta piatta non si converte, e resta in gara.

    Con `chiave` (il colore come lo legge pdfplumber, `_penna_letta`) vince
    il colore che pdfplumber leggerebbe proprio cosi', se c'e': e' la stessa
    penna per la lettura della fustella."""
    from collections import defaultdict
    from pypdf.generic import ContentStream
    peso = defaultdict(int)
    oggetti = {}

    def numeri(ops):
        out = []
        for v in ops:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                pass
        return out

    def scorri(contenuto, risorse, prof=0, eredita=None):
        if contenuto is None or prof > 4:
            return
        try:
            ops = ContentStream(contenuto, None).operations
        except Exception:  # noqa: BLE001 - un contenuto illeggibile non ha penne
            return
        risorse = risorse or {}
        spazi = risorse.get("/ColorSpace") or {}
        xobj = risorse.get("/XObject") or {}
        # lo spessore puo' venire da uno stato grafico (`gs` con /LW): sul
        # display KMS T10 la fustella non usa mai `w`
        stati = risorse.get("/ExtGState") or {}
        # un gruppo di oggetti eredita lo stato di chi lo richiama: sul
        # display KMS T10 la fustella e' in un gruppo, col colore scelto fuori
        st = dict(eredita) if eredita else {"op": "G", "cs": None, "v": (0.0,), "w": 1.0}
        pila, tratti = [], 0
        for operandi, op in ops:
            if op == b"q":
                pila.append(dict(st))
            elif op == b"Q":
                st = pila.pop() if pila else st
            elif op == b"w" and operandi:
                st["w"] = numeri(operandi[:1])[0] if numeri(operandi[:1]) else st["w"]
            elif op == b"gs" and operandi and str(operandi[0]) in stati:
                lw = stati[str(operandi[0])].get_object().get("/LW")
                if lw is not None:
                    st["w"] = float(lw)
            elif op == b"CS" and operandi:
                nome = str(operandi[0])
                if nome in ("/DeviceGray", "/DeviceRGB", "/DeviceCMYK"):
                    st["op"] = {"/DeviceGray": "G", "/DeviceRGB": "RG",
                                "/DeviceCMYK": "K"}[nome]
                    st["cs"] = None
                elif nome in spazi:
                    st["op"], st["cs"] = "CS", nome
                    oggetti.setdefault(("CS", id(spazi), nome), spazi.raw_get(nome)
                                       if hasattr(spazi, "raw_get") else spazi[nome])
                    st["chiave"] = ("CS", id(spazi), nome)
            elif op in (b"SC", b"SCN"):
                st["v"] = tuple(numeri(operandi))
            elif op in (b"G", b"RG", b"K"):
                st["op"], st["cs"], st["v"] = op.decode(), None, tuple(numeri(operandi))
            elif op in (b"m", b"l", b"c", b"v", b"y", b"re"):
                tratti += 1
            elif op in (b"S", b"s", b"B", b"B*", b"b", b"b*"):
                if abs(st["w"] - spessore) <= max(0.05, 0.15 * spessore):
                    chiave = st.get("chiave") if st["op"] == "CS" else None
                    peso[(st["op"], chiave, st["v"])] += max(tratti, 1)
                tratti = 0
            elif op in (b"n", b"f", b"F", b"f*"):
                tratti = 0
            elif op == b"Do" and operandi and str(operandi[0]) in xobj:
                x = xobj[str(operandi[0])].get_object()
                if x.get("/Subtype") == "/Form":
                    scorri(x, x.get("/Resources") or risorse, prof + 1, st)

    scorri(pagina.get_contents(), pagina.get("/Resources"))

    def vicino(op, v, chiave=None):
        if rgb is None:
            return True
        if op == "CS":
            # uno spazio ICC si confronta coi suoi canali; una tinta piatta
            # (Separation, DeviceN) non si converte, e resta in gara. Sul
            # display KMS T10 un blu in un ICC a tre canali passava per tinta
            try:
                spazio = oggetti.get(chiave).get_object()
                if spazio[0] != "/ICCBased":
                    return True
                op = {1: "G", 3: "RG", 4: "K"}.get(int(spazio[1].get_object().get("/N")))
            except Exception:  # noqa: BLE001 - uno spazio che non si legge resta in gara
                return True
            if op is None:
                return True
        try:
            if op == "G":
                c = (v[0] * 255,) * 3
            elif op == "RG":
                c = tuple(x * 255 for x in v[:3])
            else:
                c0, m0, y0, k0 = v[:4]
                c = tuple(255 * (1 - x) * (1 - k0) for x in (c0, m0, y0))
        except (IndexError, TypeError, ValueError):
            return False
        return sum((a - b) ** 2 for a, b in zip(c, rgb)) ** 0.5 <= 120
    def come_pdfplumber(v):
        return str(float(v[0])) if len(v) == 1 else str(tuple(float(x) for x in v))
    if chiave is not None:
        uguali = {k: n for k, n in peso.items() if come_pdfplumber(k[2]) == chiave}
        if uguali:
            peso = uguali
    peso = {k: n for k, n in peso.items() if vicino(k[0], k[2], k[1])}
    if not peso:
        return None
    (op, chiave, valori), _n = max(peso.items(), key=lambda kv: kv[1])
    if op == "CS":
        return "CS", oggetti.get(chiave), valori
    return op, None, valori


def _disegno_in_piu(pdf, pagina, variante, mx0, my1, kind=None, insieme=frozenset(),
                    colore=None):
    """Il contenuto da aggiungere alla pagina per le varianti di stile del
    disegno tecnico, nella stessa penna del DT; None se il DT non si trova.

    - `quote`: la quota del passo sotto lo steso e quella del giro a destra,
      lunghe quanto lo steso, col loro numero: il T1 del biscotto argento;
    - `cornice`: un riquadro attorno al DT, a dieci millimetri, come la
      cornice di una tavola disegnata con la stessa penna;
    - `legenda`: un riquadro con le scritte della legenda attaccato sotto
      lo steso, largo meta'. Con le quote nella stessa variante (`insieme`,
      `quote+legenda`) si attacca sopra: sotto c'e' la quota del passo, e
      nessun disegnatore mette una legenda sopra una quota - disegnata li',
      il riquadro della legenda e i richiami della quota si fondevano, e il
      display del riempimento KMS T10 trovava sette colonne invece di cinque;
    - `segni`: i segni di stampa di una tavola pronta per la tipografia -
      crocini di taglio agli angoli, crocini di registro a meta' dei lati,
      la barra dei colori sotto -, fuori dal DT e dalla sua stampa."""
    from pack3d.dieline import PT2MM
    r = _riquadro_tecnico(pdf, pagina, kind)
    if r is None:
        return None
    (x0, y0, x1, y1), (w, rgb) = r
    mm = 1.0 / PT2MM
    # lo spessore come lo vede la lettura della fustella (pdfplumber), che e'
    # quello della chiave della penna: pdfium lo da' nel telaio del tratto, e
    # sul cono, disegnato in scala, 0,2 invece di 1
    letta = _penna_letta(pdf, pagina, (x0, y0, x1, y1), w, rgb)
    w_tratto = w
    if letta is not None:
        w = max(letta[0], 0.01)
    # il colore della penna com'e' scritto nel PDF (`_colore_della_penna`,
    # da chi chiama, che lo cerca coi tratti di quello spessore nel loro
    # telaio e con la chiave della lettura), o l'RGB di pdfium se non si trova
    if colore is not None:
        operatori = colore(w_tratto, rgb, letta[1] if letta else None)
    else:
        c = " ".join("%.3f" % (v / 255.0) for v in rgb)
        operatori = "%s RG %s rg" % (c, c)

    def X(x):
        return x + mx0

    def Y(y):
        return my1 - y

    righe = ["q %s %.2f w" % (operatori, w)]

    def linea(xa, ya, xb, yb):
        righe.append("%.2f %.2f m %.2f %.2f l S" % (X(xa), Y(ya), X(xb), Y(yb)))

    def testo(x, y, t, girato=False):
        m = "0 1 -1 0" if girato else "1 0 0 1"
        righe.append("BT /Fq %.1f Tf %s %.2f %.2f Tm (%s) Tj ET"
                     % (2.6 * mm, m, X(x), Y(y), t))

    if variante == "quote":
        buco = 7 * mm
        # il passo, sotto
        yq, xm = y1 + 8 * mm, (x0 + x1) / 2
        linea(x0, y1 + 1 * mm, x0, yq + 2 * mm)
        linea(x1, y1 + 1 * mm, x1, yq + 2 * mm)
        linea(x0, yq, xm - buco / 2, yq)
        linea(xm + buco / 2, yq, x1, yq)
        testo(xm - buco / 2 + 0.5 * mm, yq + 1 * mm, "%g" % round((x1 - x0) * PT2MM))
        # il giro, a destra
        xq, ym = x1 + 8 * mm, (y0 + y1) / 2
        linea(x1 + 1 * mm, y0, xq + 2 * mm, y0)
        linea(x1 + 1 * mm, y1, xq + 2 * mm, y1)
        linea(xq, y0, xq, ym - buco / 2)
        linea(xq, ym + buco / 2, xq, y1)
        testo(xq + 1 * mm, ym + buco / 2 - 0.5 * mm, "%g" % round((y1 - y0) * PT2MM),
              girato=True)
    elif variante == "cornice":
        # attorno a tutto il DT dello steso, non alla sola lettura: dove il
        # DT va oltre (il filo dell'abbondanza) la cornice lo attraversava
        d = 10 * mm
        c0, c1, c2, c3 = _ingombro_tecnico(pdf, pagina, (x0, y0, x1, y1))
        if kind not in (None, "flowpack"):
            # lo steso di un flowpack e' un rettangolo; una fustella ha
            # tratteggi e lati inclinati
            c0, c1, c2, c3 = _fuori_dai_tratti(pdf, pagina, (c0, c1, c2, c3), d)
        c0, c1, c2, c3 = _fuori_dalla_stampa(pdf, pagina, (c0, c1, c2, c3), d)
        for xa, ya, xb, yb in ((c0 - d, c1 - d, c2 + d, c1 - d), (c0 - d, c3 + d, c2 + d, c3 + d),
                               (c0 - d, c1 - d, c0 - d, c3 + d), (c2 + d, c1 - d, c2 + d, c3 + d)):
            linea(xa, ya, xb, yb)
    elif variante == "segni":
        # i segni di stampa di una tavola pronta per la tipografia, attorno
        # al DT e alla sua stampa come la cornice: i crocini di taglio sui
        # prolungamenti dei lati, fuori dall'abbondanza; i crocini di
        # registro a meta' di ogni lato; la barra dei colori sotto. Crocini
        # nella penna del DT, come li mette il CAD della fustella; la barra
        # piena, in quadricromia.
        c0, c1, c2, c3 = _ingombro_tecnico(pdf, pagina, (x0, y0, x1, y1))
        if kind not in (None, "flowpack"):
            c0, c1, c2, c3 = _fuori_dai_tratti(pdf, pagina, (c0, c1, c2, c3), 3 * mm)
        c0, c1, c2, c3 = _fuori_dalla_stampa(pdf, pagina, (c0, c1, c2, c3), 3 * mm)
        o, L = 3 * mm, 6 * mm
        for x, sx in ((c0, -1), (c2, +1)):
            for y, sy in ((c1, -1), (c3, +1)):
                linea(x + sx * o, y, x + sx * (o + L), y)
                linea(x, y + sy * o, x, y + sy * (o + L))
        r = 2.5 * mm

        def registro(xc, yc):
            k = 0.5523 * r
            righe.append("%.2f %.2f m %.2f %.2f %.2f %.2f %.2f %.2f c "
                         "%.2f %.2f %.2f %.2f %.2f %.2f c "
                         "%.2f %.2f %.2f %.2f %.2f %.2f c "
                         "%.2f %.2f %.2f %.2f %.2f %.2f c S" % (
                             X(xc + r), Y(yc),
                             X(xc + r), Y(yc + k), X(xc + k), Y(yc + r), X(xc), Y(yc + r),
                             X(xc - k), Y(yc + r), X(xc - r), Y(yc + k), X(xc - r), Y(yc),
                             X(xc - r), Y(yc - k), X(xc - k), Y(yc - r), X(xc), Y(yc - r),
                             X(xc + k), Y(yc - r), X(xc + r), Y(yc - k), X(xc + r), Y(yc)))
            linea(xc - 1.4 * r, yc, xc + 1.4 * r, yc)
            linea(xc, yc - 1.4 * r, xc, yc + 1.4 * r)
        d = o + L / 2 + r
        xm, ym = (c0 + c2) / 2, (c1 + c3) / 2
        for xc, yc in ((xm, c1 - d), (xm, c3 + d), (c0 - d, ym), (c2 + d, ym)):
            registro(xc, yc)
        lato = 5 * mm
        yb = c3 + o + L + 2 * mm
        for k, cmyk in enumerate(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1),
                                  (.5, 0, 0, 0), (0, .5, 0, 0), (0, 0, .5, 0), (0, 0, 0, .5),
                                  (1, 1, 0, 0), (0, 1, 1, 0), (1, 0, 1, 0))):
            xa = c0 + 10 * mm + k * lato
            righe.append("q %g %g %g %g k %.2f %.2f %.2f %.2f re f Q"
                         % (cmyk + (X(xa), Y(yb + lato), lato, lato)))
    elif variante == "legenda":
        xl = x0 + (x1 - x0) / 2
        # sotto lo steso, o sopra se sotto c'e' la quota del passo
        yb, verso = (y0, -1) if "quote" in insieme else (y1, +1)
        yl = yb + verso * 22 * mm
        linea(x0, yb, x0, yl)
        linea(xl, yb, xl, yl)
        linea(x0, yl, xl, yl)
        cima = min(yb, yl)
        for k, t in enumerate(("LEGENDA", "taglio", "cordonatura", "area non stampata")):
            testo(x0 + 3 * mm, cima + (5 + 4.5 * k) * mm, t)
    else:
        return None
    righe.append("Q")
    return ("\n".join(righe) + "\n").encode("ascii")


def _un_passo(sorgente, destinazione, variante, kind=None, insieme=frozenset()):
    """Una variante sola di `_pagina_variata`."""
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import (DecodedStreamObject, DictionaryObject, NameObject,
                               RectangleObject)
    if variante in ("quote", "cornice", "legenda", "segni"):
        from pypdf import PageObject
        w = PdfWriter(clone_from=sorgente)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        for i, p in enumerate(w.pages):
            mb = p.mediabox
            spazi = {}

            def colore(lw, rgb, chiave=None, p=p, spazi=spazi):
                # la penna della fustella com'e' scritta (`_colore_della_penna`):
                # una tinta piatta, un CMYK e lo stesso colore in RGB sono tre
                # penne per la lettura
                trovato = _colore_della_penna(p, lw, rgb, chiave)
                if trovato is None or (trovato[0] == "CS" and trovato[1] is None):
                    c = " ".join("%.3f" % (v / 255.0) for v in rgb)
                    return "%s RG %s rg" % (c, c)
                op, spazio, valori = trovato
                v = " ".join("%.4g" % x for x in valori) or "1"
                if op == "CS":
                    spazi["/CSfust"] = spazio
                    return "/CSfust CS %s SCN /CSfust cs %s scn" % (v, v)
                return "%s %s %s %s" % (v, op, v, op.lower())
            dati = _disegno_in_piu(sorgente, i, variante, float(mb.left), float(mb.top), kind,
                                   insieme, colore)
            if not dati:
                continue
            sopra = PageObject.create_blank_page(w, float(mb.width), float(mb.height))
            sopra.mediabox = RectangleObject([float(mb.left), float(mb.bottom),
                                              float(mb.right), float(mb.top)])
            flusso = DecodedStreamObject()
            flusso.set_data(dati)
            sopra[NameObject("/Contents")] = w._add_object(flusso)
            risorse = DictionaryObject({NameObject("/Font"): DictionaryObject(
                {NameObject("/Fq"): w._add_object(font)})})
            if spazi:
                risorse[NameObject("/ColorSpace")] = DictionaryObject(
                    {NameObject(k): v for k, v in spazi.items()})
            sopra[NameObject("/Resources")] = risorse
            p.merge_page(sopra)
        with open(destinazione, "wb") as fh:
            w.write(fh)
        return
    if variante == "appiattito":
        subprocess.run(["gs", "-q", "-o", destinazione, "-sDEVICE=pdfwrite",
                        "-dNoOutputFonts", sorgente], check=True, timeout=900,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    w = PdfWriter(clone_from=sorgente)
    if variante == "copertina":
        W, H = (float(v) for v in w.pages[0].mediabox[2:])
        p = w.insert_blank_page(W, H, index=0)
        testo = DecodedStreamObject()
        testo.set_data(b"0 0 0 RG 2 w 40 40 %.1f %.1f re S BT /F1 36 Tf 80 %.1f Td "
                       b"(SCHEDA TECNICA - copertina) Tj ET\n" % (W - 80, H - 80, H - 140))
        p[NameObject("/Contents")] = w._add_object(testo)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        p[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject(
            {NameObject("/F1"): w._add_object(font)})})
        with open(destinazione, "wb") as fh:
            w.write(fh)
        return
    for i, p in enumerate(w.pages):
        mb = p.mediabox
        x0, y0 = float(mb.left), float(mb.bottom)
        W, H = float(mb.width), float(mb.height)
        t = Transformation().translate(-x0, -y0)
        girata = None
        if variante.startswith("giro") or variante == "rotate":
            g = 90 if variante == "rotate" else int(variante[4:])
            t = t.rotate(g).translate(*{90: (H, 0), 180: (W, H), 270: (0, W)}[g])
            if g != 180:
                W, H = H, W
            if variante == "rotate":
                # chi lo apre lo vede girato indietro di un quarto: com'era
                girata = 90
        elif variante.startswith("scala"):
            s = float(variante[5:])
            t = t.scale(s, s)
            W, H = W * s, H * s
        elif variante == "spostato":
            t = t.translate(150, 80)
            W, H = W + 200, H + 120
        elif variante == "miniatura":
            # la tavola piu' larga, e a destra una copia della pagina a un
            # quinto; nel telaio della pagina, che `t` dopo porta all'origine
            p.merge_transformed_page(PdfReader(sorgente).pages[i], Transformation().translate(
                -x0, -y0).scale(0.2, 0.2).translate(W * 1.05 + x0, H * 0.05 + y0))
            W = W * 1.3
        else:
            raise SystemExit("variante sconosciuta: %s" % variante)
        p.add_transformation(t)
        for k in ("/CropBox", "/TrimBox", "/BleedBox", "/ArtBox"):
            if k in p:
                del p[k]
        p.mediabox = RectangleObject([0, 0, W, H])
        if girata:
            p.rotate(girata)
    # la miniatura ripete le immagini della pagina: una volta sola, o il file
    # raddoppia e passa il limite del server
    w.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    with open(destinazione, "wb") as fh:
        w.write(fh)


def varianti(args):
    """La tolleranza del codice, misurata: ogni caso del parco delle famiglie
    chieste (con le misure approvate) con le pagine variate - tutti i PDF del
    caso allo stesso modo; l'immagine del prodotto di un incarto resta
    com'e' - costruito, contro l'originale costruito col codice di adesso:
    misure in scala e viste. I PDF variati stanno in USCITA, mai nel
    repository. Esce con 1 se una variante da' un modello diverso e non e'
    fra quelle gia' note (`VARIANTI`, scritte con `--approva`: i limiti
    dichiarati)."""
    import shutil
    import numpy as np
    from PIL import Image
    famiglie = set(args.famiglia.split(","))
    tutte = [c for c in _casi(args.casi, args.solo) if c.get("misure") and (
        "tutte" in famiglie or ((c.get("opzioni") or {}).get("kind") or "senza") in famiglie)]
    if not tutte:
        raise SystemExit("nessun caso %s con le misure approvate" % args.famiglia)
    finto = os.path.join(args.uscita, "casi")
    os.makedirs(os.path.join(finto, "parco", "pdf"), exist_ok=True)
    risorse = os.path.join(args.casi, "risorse")
    if os.path.isdir(risorse) and not os.path.exists(os.path.join(finto, "risorse")):
        os.symlink(os.path.abspath(risorse), os.path.join(finto, "risorse"))
    nuovi = []
    for c in tutte:
        for v in args.varianti:
            file = []
            for f in c["file"]:
                sorgente = os.path.join(args.casi, "parco", "pdf", f)
                if not f.lower().endswith(".pdf"):
                    # l'immagine del prodotto: la pagina la manda per nome
                    if not os.path.exists(os.path.join(finto, "parco", "pdf", f)):
                        shutil.copyfile(sorgente, os.path.join(finto, "parco", "pdf", f))
                    file.append(f)
                    continue
                file.append("%s__%s.pdf" % (os.path.splitext(f)[0], v))
                _pagina_variata(sorgente, os.path.join(finto, "parco", "pdf", file[-1]), v,
                                kind=(c.get("opzioni") or {}).get("kind"))
            nuovi.append(dict(nome="%s__%s" % (c["nome"], v), file=file,
                              opzioni=c.get("opzioni"), originale=c, variante=v))
    with open(os.path.join(finto, "parco", "parco.json"), "w", encoding="utf-8") as fh:
        json.dump({"casi": [{k: x[k] for k in ("nome", "file", "opzioni")} for x in nuovi]},
                  fh, ensure_ascii=False, indent=1)
    originali, variate = os.path.join(args.uscita, "originali"), os.path.join(args.uscita, "varianti")
    print("%d casi (%s), %d varianti: costruisco" % (len(tutte), args.famiglia, len(nuovi)))
    sys.stdout.flush()
    from contextlib import redirect_stdout
    import io
    with redirect_stdout(io.StringIO()):
        # con --riusa un giro interrotto riprende: i PDF variati escono uguali
        # al byte, e i casi gia' costruiti col codice di adesso restano
        riusa = getattr(args, "riusa", False)
        costruisci(argparse.Namespace(casi=args.casi, uscita=originali, codice=None,
                                      solo=[c["nome"] for c in tutte], riusa=riusa))
        costruisci(argparse.Namespace(casi=finto, uscita=variate, codice=None, solo=None,
                                      riusa=riusa))
    risultati, conto = {}, {}
    for x in nuovi:
        c, v = x["originale"], x["variante"]
        s = 1.0
        for passo in v.split("+"):
            if passo.startswith("scala"):
                s *= float(passo[5:])
        with open(os.path.join(variate, x["nome"] + ".json"), encoding="utf-8") as fh:
            e = json.load(fh)
        motivo = None
        if e.get("stato") != 200:
            motivo = "non si costruisce: %s" % str((e.get("avvisi") or [""])[0])[:200]
        else:
            a, b = c["misure"]["ingombro"], (e.get("misure") or {}).get("ingombro") or [0, 0, 0]
            # nello stesso ordine: un pack girato ha le stesse misure in un altro
            if max(abs(p * s - q) for p, q in zip(a, b)) > 1.5 * s:
                motivo = "ingombro %s invece di %s" % (b, [round(p * s, 1) for p in a])
            elif s == 1.0:
                fa, fb = (os.path.join(originali, c["nome"] + "_viste.png"),
                          os.path.join(variate, x["nome"] + "_viste.png"))
                if os.path.exists(fa) and os.path.exists(fb):
                    A = np.asarray(Image.open(fa).convert("L"), float)
                    B = np.asarray(Image.open(fb).convert("L"), float)
                    d = float(np.abs(A - B).mean()) if A.shape == B.shape else 255.0
                    if d > 3:
                        motivo = "viste diverse dall'originale (%.1f livelli di grigio)" % d
        conto.setdefault(v, [0, 0])[motivo is not None] += 1
        risultati[x["nome"]] = motivo
    # le diverse gia' note - i limiti dichiarati - sono approvate in
    # VARIANTI: rosso e' solo una variante diversa che non c'era
    f = os.path.join(args.casi, VARIANTI)
    note = {}
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            note = json.load(fh)
    nuove = {n: m for n, m in risultati.items() if m and n not in note}
    guarite = [n for n, m in risultati.items() if not m and n in note]
    righe = []
    for n, m in sorted(risultati.items()):
        if m:
            righe.append("  %-44s %s%s" % (n[:44], m, "" if n in nuove else "  (nota)"))
    for n in guarite:
        righe.append("  %-44s adesso come l'originale: era nota (%s)" % (n[:44], note[n]))
    print("\n".join(righe))
    for v, (uguali, no) in sorted(conto.items()):
        print("%-10s %d su %d come l'originale" % (v, uguali, uguali + no))
    if args.riassunto:
        with open(args.riassunto, "a", encoding="utf-8") as fh:
            fh.write("## Varianti (%s)\n\n| variante | come l'originale |\n|---|---|\n" % args.famiglia)
            for v, (uguali, no) in sorted(conto.items()):
                fh.write("| %s | %d su %d |\n" % (v, uguali, uguali + no))
            fh.write("\n%s\n\n" % ("**%d diverse nuove**, non approvate:" % len(nuove)
                                     if nuove else "Nessuna diversa nuova."))
            if righe:
                fh.write("```\n%s\n```\n" % "\n".join(righe))
    if args.approva:
        note = {n: m for n, m in note.items() if n not in risultati}
        note.update({n: m for n, m in risultati.items() if m})
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(note, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        print("varianti diverse approvate: %d in %s - commit e push nel registro"
              % (len(note), VARIANTI))
    if not args.tieni:
        shutil.rmtree(finto)
    if nuove and not args.approva:
        raise SystemExit(1)


def stesi(args):
    """Ogni texture contro la pagina del suo PDF: dritta, a scala uniforme."""
    import io
    import numpy as np
    import pypdfium2 as pdfium
    from PIL import Image
    from pack3d import artwork, strati, texture
    girate = 0
    for caso in _casi(args.casi, args.solo):
        try:
            with open(os.path.join(args.uscita, caso["nome"] + ".glb"), "rb") as fh:
                glb = fh.read()
        except OSError:
            continue
        # la pagina come la vede chi apre il file - col suo /Rotate, che
        # `pagina_unica` cuoce e la copia senza livelli perderebbe - senza i
        # livelli tecnici e senza le lastre che coprono la grafica, come la
        # pulisce la costruzione (`artwork.senza_coperture`: la vernice del
        # astuccio della ciambella, resa, copre tutto il foglio), resa a una risoluzione
        # per texture
        puliti = []
        for f in caso["file"]:
            # l'immagine del prodotto di un incarto non e' un foglio
            if not f.lower().endswith(".pdf"):
                continue
            una, _n = artwork.pagina_unica(os.path.join(args.casi, "parco", "pdf", f))
            puliti.append(artwork.senza_coperture(strati.senza_tecnici(una)[0])[0])
        rese = {}

        def pagina(i, dpi):
            if (i, dpi) not in rese:
                doc = pdfium.PdfDocument(puliti[i])
                rese[(i, dpi)] = np.asarray(doc[0].render(scale=dpi / 72.0)
                                            .to_pil().convert("L"), float)
                doc.close()
            return rese[(i, dpi)]
        # un atlante (`pack3d.atlante`) si cerca zona per zona: ognuna e' lo
        # steso del suo foglio
        pezzi = []
        for t in texture.texture(glb, 100000):
            tutta = Image.open(io.BytesIO(t["dati"])).convert("L")
            for z in t["zone"] or [None]:
                if z is None:
                    pezzi.append((t["nome"], tutta))
                    continue
                W, H = tutta.size
                pezzi.append((z["nome"], tutta.crop((
                    round(z["x"] * W), round(z["y"] * H),
                    round((z["x"] + z["w"]) * W), round((z["y"] + z["h"]) * H)))))
        for nome, im in pezzi:
            if max(im.size) < 64:
                print("%-30s %-12s %5d x %-5d  troppo piccola per cercarla"
                      % (caso["nome"], nome, im.width, im.height))
                continue
            R = float(round(min(72.0, max(30.0, STESI_PX * 300.0 / max(im.size)))))
            per_giro = {}
            for k in range(4):
                g = im.rotate(90 * k, expand=True)
                for dpi in np.geomspace(100, 400, 32):
                    w = max(1, round(g.width * R / dpi))
                    h = max(1, round(g.height * R / dpi))
                    a = np.asarray(g.resize((w, h), Image.BILINEAR), float)
                    for i in range(len(puliti)):
                        c = _correlazione(pagina(i, R), a)[0]
                        if c > per_giro.get(90 * k, (-1.0,))[0]:
                            per_giro[90 * k] = (c, dpi, i)
            if 0 not in per_giro:
                # tutta di un colore: non c'e' niente da ritrovare
                print("%-30s %-12s %5d x %-5d  di un colore solo, non si cerca"
                      % (caso["nome"], nome, im.width, im.height))
                continue
            giro = max(per_giro, key=lambda k: per_giro[k][0])
            c, dpi, i = per_giro[giro]
            dritta, dpi0, i0 = per_giro[0]
            if c < STESI_SOGLIA:
                esito = "non si ritrova sulla pagina"
            elif dritta >= c - STESI_PARI:
                esito, c, dpi, i = "dritta", dritta, dpi0, i0
            elif c - dritta >= STESI_MARGINE:
                esito = "GIRATA di %d gradi" % giro
                girate += 1
            else:
                esito = ("incerta, da guardare: girata di %d gradi %.2f, dritta "
                         "%.2f" % (giro, c, dritta))
            print("%-30s %-12s %5d x %-5d  %s (pdf %d, %.0f dpi, correlazione %.2f)"
                  % (caso["nome"], nome, im.width, im.height, esito, i + 1,
                     dpi, c))
    if girate:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cosa", required=True)
    c = sub.add_parser("costruisci", help="costruisce tutti i casi del parco")
    c.add_argument("casi", help="clone del repository privato dei casi")
    c.add_argument("uscita", help="cartella dove salvare GLB, avvisi e viste")
    c.add_argument("--codice", help="cartella del codice da provare "
                                    "(di serie questo repository)")
    c.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                   help="solo questi casi, separati da virgole")
    c.add_argument("--riusa", action="store_true",
                   help="non rifare i casi gia' in USCITA con lo stesso codice e "
                        "gli stessi file (la cassa del parco nelle Actions)")
    c.set_defaults(fai=costruisci)
    k = sub.add_parser("confronta", help="confronta due costruzioni del parco")
    k.add_argument("prima")
    k.add_argument("dopo")
    k.add_argument("--immagini", help="dove salvare le viste affiancate")
    k.set_defaults(fai=confronta)
    e = sub.add_parser("esito", help="il verdetto di un parco fatto da solo: "
                                     "esce con 1 se qualcosa si e' rotto")
    e.add_argument("prima", help="la costruzione col codice di main")
    e.add_argument("dopo", help="la costruzione col codice da provare")
    e.add_argument("--ieri", help="la costruzione della notte prima, se c'e'")
    e.add_argument("--titolo", help="cosa si e' provato, per il riassunto")
    e.add_argument("--riassunto", help="il file dove aggiungere il riassunto "
                                       "in markdown (nelle Actions: $GITHUB_STEP_SUMMARY)")
    e.set_defaults(fai=esito)
    t = sub.add_parser("stesi", help="controlla che ogni texture sia lo steso "
                                     "del suo PDF, dritta")
    t.add_argument("casi", help="clone del repository privato dei casi")
    t.add_argument("uscita", help="la cartella di una costruzione del parco")
    t.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                   help="solo questi casi, separati da virgole")
    t.set_defaults(fai=stesi)
    va = sub.add_parser("varianti", help="la tolleranza del codice: i casi di una "
                                         "famiglia con la pagina girata o in scala, "
                                         "contro l'originale")
    va.add_argument("casi", help="clone del repository privato dei casi")
    va.add_argument("uscita", help="dove mettere i PDF variati e le costruzioni "
                                   "(fuori dal repository)")
    va.add_argument("--famiglia", default="flowpack",
                    help="i `kind` dei casi da variare, separati da virgole "
                         "(di serie flowpack; `senza` quelli senza kind, "
                         "`tutte` tutti)")
    va.add_argument("--varianti", default=["giro90", "giro180", "giro270", "scala1.03"],
                    type=lambda s: [x for x in s.split(",") if x],
                    help="giroN (N = 90, 180, 270), rotate, scalaS, spostato, "
                         "miniatura, copertina, appiattito, quote, cornice, segni, "
                         "legenda, separate da virgole; "
                         "si sommano con + (appiattito+giro90)")
    va.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                    help="solo questi casi, separati da virgole")
    va.add_argument("--tieni", action="store_true",
                    help="non cancellare i PDF variati alla fine")
    va.add_argument("--riusa", action="store_true",
                    help="non ricostruire i casi gia' costruiti in USCITA con "
                         "questo codice e gli stessi file (un giro interrotto)")
    va.add_argument("--approva", action="store_true",
                    help="scrive le varianti diverse di adesso come note "
                         "(limiti dichiarati), in parco/varianti.json")
    va.add_argument("--riassunto", help="il file dove aggiungere il riassunto in "
                                        "markdown (nelle Actions: $GITHUB_STEP_SUMMARY)")
    va.set_defaults(fai=varianti)
    lt = sub.add_parser("letture", help="la lettura di ogni caso contro quella "
                                        "approvata, senza costruire")
    lt.add_argument("casi", help="clone del repository privato dei casi")
    lt.add_argument("--codice", help="cartella del codice da provare "
                                     "(di serie questo repository)")
    lt.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                    help="solo questi casi, separati da virgole")
    lt.add_argument("--approva", action="store_true",
                    help="scrive le letture di questi casi come approvate")
    lt.set_defaults(fai=letture)
    m = sub.add_parser("misure", help="le misure di una costruzione contro quelle "
                                      "approvate (con --approva le scrive)")
    m.add_argument("casi", help="clone del repository privato dei casi")
    m.add_argument("uscita", help="la cartella di una costruzione del parco")
    m.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                   help="solo questi casi, separati da virgole")
    m.add_argument("--approva", action="store_true",
                   help="scrive le misure di questi modelli come approvate")
    m.set_defaults(fai=misure_del_parco)
    s = sub.add_parser("spazio", help="prova dei casi sullo Space vero, appena "
                                      "ripartito col codice di qui: uno per "
                                      "famiglia, o quelli nominati")
    s.add_argument("url", help="per esempio https://iccio-maurizio.hf.space")
    s.add_argument("casi", help="clone del repository privato dei casi")
    s.add_argument("nomi", nargs="*", help="i casi del parco da provare (di serie: "
                                           "uno per famiglia, il piu' leggero)")
    s.add_argument("--uscita", default="/tmp/parco_spazio",
                   help="dove salvare GLB, viste e verdetto")
    s.add_argument("--attendi", type=int, default=25,
                   help="minuti di attesa massima per la ripartenza dello Space")
    s.set_defaults(fai=spazio)
    g = sub.add_parser("glam", help="manda a Glam Lab il modello che lo Space "
                                    "ha appena approvato")
    g.add_argument("url", help="l'indirizzo di Glam Lab: %s" % GLAM)
    g.add_argument("casi", help="clone del repository privato dei casi")
    g.add_argument("nome", help="il caso del parco, gia' provato con `spazio`")
    g.add_argument("--uscita", default="/tmp/parco_spazio",
                   help="la cartella dove `spazio` ha salvato GLB e verdetto")
    # la stessa che annuncia la pagina dello Space (GLAM_CARTELLA)
    g.add_argument("--categoria", default="Casi risolti",
                   help="la cartella del modello in Glam")
    g.set_defaults(fai=glam)
    q = sub.add_parser("caso", help="dice a Glam Lab a che punto e' un caso "
                                    "della coda, per chi l'ha caricato")
    q.add_argument("url", help="l'indirizzo di Glam Lab: %s" % GLAM)
    q.add_argument("casi", help="clone del repository privato dei casi")
    q.add_argument("codice", help="il codice del caso, 10 cifre esadecimali")
    q.add_argument("--stato", required=True, choices=STATI)
    q.add_argument("--messaggio", help="due righe per l'utente, in parole sue")
    q.add_argument("--domanda", help="con --stato domanda: la domanda all'utente")
    q.add_argument("--opzione", action="append",
                   help="una risposta fra cui scegliere (ripetibile, al massimo 4)")
    q.add_argument("--modello", help="con --stato da-approvare: il caso del "
                                     "parco costruito con `costruisci --solo` (o "
                                     "provato con `spazio`), il cui modello va a "
                                     "chi l'ha caricato da approvare")
    q.add_argument("--anteprima", help="con --stato domanda: il caso del parco "
                                       "costruito con `costruisci --solo`, le cui "
                                       "viste e la cui lettura del PDF vanno con la "
                                       "domanda")
    q.add_argument("--uscita", default="/tmp/parco_spazio",
                   help="la cartella dove `costruisci` (o `spazio`) ha salvato il GLB")
    q.add_argument("--spazio", default=SPAZIO,
                   help="lo Space che manda l'email della domanda (di serie %s)" % SPAZIO)
    q.add_argument("--repo", default=REPO_CASI,
                   help="il registro dei casi su GitHub: con --stato domanda o "
                        "non-risolto il caso passa a da-guardare")
    q.set_defaults(fai=caso)
    for nome, fai, aiuto in (("prepara", prepara, "prende un caso libero, lo mette nel "
                              "parco, lo costruisce e fa il foglio da guardare"),
                             ("verifica", verifica_caso, "prima della PR: il caso senza "
                              "difetti, lo steso, le prove veloci, le letture del parco"),
                             ("consegna", consegna, "dopo la correzione: il modello a chi "
                              "l'ha caricato, da approvare"),
                             ("approvato", approvato, "dopo l'approvazione: in Glam, risolto, "
                              "da rilasciare"),
                             ("prossimo", prossimo, "fine del giro: se in coda c'e' un altro "
                              "caso libero, lo Space avvia una sessione nuova")):
        x = sub.add_parser(nome, help=aiuto)
        x.add_argument("casi", help="clone del repository privato dei casi")
        x.add_argument("codice", help="il codice del caso, 10 cifre esadecimali")
        x.add_argument("--uscita", help="dove costruire (di serie /tmp/caso_<codice>)")
        x.add_argument("--repo", default=REPO_CASI, help="il registro dei casi su GitHub")
        x.add_argument("--glam", default=GLAM, help="l'indirizzo di Glam Lab")
        x.add_argument("--spazio", default=SPAZIO, help="lo Space, per gli avvisi")
        if nome == "prepara":
            x.add_argument("--riprendi", action="store_true",
                           help="il lucchetto e' di una sessione morta: riprendilo")
        if nome == "consegna":
            x.add_argument("--messaggio", required=True,
                           help="due righe per chi l'ha caricato: cosa e' cambiato")
            x.add_argument("--commento", required=True,
                           help="per la issue: la causa, la regola, il link alla PR")
            x.add_argument("--senza-verifica", metavar="MOTIVO",
                           help="consegna senza `verifica` passata; il motivo va "
                                "nel commento della issue")
        if nome == "approvato":
            x.add_argument("--messaggio", help="due righe per chi l'ha caricato")
            x.add_argument("--categoria", default="Casi risolti",
                           help="la cartella del modello in Glam")
        x.set_defaults(fai=fai)
    v = sub.add_parser("versione", help="l'impronta del codice, come la dice "
                                        "/api/ping")
    v.add_argument("--codice", help="cartella del codice (di serie questo)")
    v.set_defaults(fai=versione_del_codice)
    args = ap.parse_args()
    args.fai(args)


if __name__ == "__main__":
    main()
