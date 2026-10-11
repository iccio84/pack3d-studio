"""Il parco: tutti i casi di prova ricostruiti come li costruisce il sito.

I PDF stanno nel repository PRIVATO dei casi (cartella `parco/` di
iccio84/pack3d-casi), mai qui: sono artwork dei clienti, e questo repository
e' pubblico. Qui c'e' solo lo strumento.

    python3 prove/parco.py costruisci CASI USCITA [--codice DIR] [--solo a,b]
    python3 prove/parco.py confronta PRIMA DOPO [--immagini DIR]
    python3 prove/parco.py spazio URL CASI NOME [--uscita DIR] [--attendi MIN]
    python3 prove/parco.py glam URL CASI NOME [--uscita DIR] [--categoria TESTO]
    python3 prove/parco.py caso URL CASI CODICE --stato STATO [--messaggio TESTO]
                                [--domanda TESTO --opzione TESTO ...]
    python3 prove/parco.py versione [--codice DIR]

`costruisci` avvia un server col codice di DIR (di serie quello di questo
repository), con il controllo dell'AI e la coda spenti, e per ogni caso di
CASI/parco/parco.json manda i PDF a /api/build con le opzioni del caso, come
fa la pagina. In USCITA salva per ogni caso il GLB, gli avvisi della
costruzione e le quattro viste (`pack3d.vista`).

`confronta` dice quali modelli sono cambiati fra due costruzioni, con gli
avvisi che cambiano, e per ognuno affianca le viste: PRIMA sopra, DOPO sotto.
Le immagini finiscono in DIR, di serie DOPO/confronto.

`spazio` prova un caso sullo Space vero, dopo una pubblicazione: aspetta che
/api/ping dica la versione di questo clone (`pack3d/versione.py`), cioe' che
lo Space sia ripartito col codice nuovo, poi costruisce il caso come la pagina
e stampa il verdetto del controllo dell'AI. Esce con 0 se e' "ok", 1 se e'
"dubbio", 2 se e' "sbagliato", 3 se il controllo non c'e' stato, 4 se lo
Space non e' ripartito in tempo. Attenzione: sullo Space il controllo e la
coda sono accesi, e un caso "sbagliato" va in coda come quelli degli utenti.

`glam` manda a Glam Lab, il viewer dove si guardano i pack, il modello che
`spazio` ha appena costruito sullo Space - solo se il controllo ha detto "ok",
e proprio quel GLB, non una costruzione nuova. Glam lo mette nella sezione
"Costruisci modello 3D da PDF", cartella "Casi risolti", col nome del PDF:
quello che Glam da' a un modello costruito da li', e quello che la pagina
annuncia a chi ha caricato il caso respinto. Il token non sta qui: lo
aggiunge l'ambiente cloud alle richieste per quel sito (API credentials,
vedi DEPLOY.md).

Con `codice` nel manifesto - il caso arrivato dalla coda - `glam` lo dice a
Glam (X-Pack3d-Codice), che mette il modello a chi ha caricato quel caso.

`caso` dice a Glam Lab a che punto e' un caso della coda, per chi l'ha
caricato: in lavorazione, una domanda (con le risposte fra cui scegliere),
risolto, non risolto. Il caso e' quello di CASI/casi/<data>_<CODICE>, e il
nome quello che la pagina gli ha annunciato. La risposta a una domanda torna
dallo Space, sulla issue del caso (`coda.aggiungi`).

`versione` stampa l'impronta del codice di DIR, quella che /api/ping
restituisce.

Il flusso per ogni correzione - vedi CODA.md:

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


def _avvia(codice, log):
    """Un server col codice di `codice`, solo in locale. (processo, url)

    Senza chiave e con il controllo spento: il parco misura il codice, non
    l'AI, e un caso del parco non deve finire nella coda dei casi nuovi.
    """
    porta = _porta_libera()
    env = dict(os.environ, PORT=str(porta), HOST="127.0.0.1",
               PACK3D_CONTROLLO="0")
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


def _costruisci_caso(url, cartella, caso):
    """(stato, glb o None, avvisi, secondi, controllo) di un caso, come lo chiede
    la pagina. `controllo` e' il verdetto dell'AI, o None se e' spento."""
    files = [os.path.join(cartella, "parco", "pdf", f) for f in caso["file"]]
    blocchi = []
    for f in files:
        with open(f, "rb") as fh:
            blocchi.append(fh.read())
    opts = dict(caso.get("opzioni") or {})
    opts["nomi"] = [quote(os.path.basename(f)) for f in files]
    if len(blocchi) > 1:
        opts["parti"] = [len(b) for b in blocchi]
    req = urllib.request.Request(
        url + "/api/build", data=b"".join(blocchi), method="POST",
        headers={"Content-Type": "application/pdf",
                 "X-Pack3d": json.dumps(opts)})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=ATTESA_COSTRUZIONE) as r:
            glb = r.read()
            avvisi = json.loads(unquote(r.headers.get("X-Pack3d-Meta") or "[]"))
            controllo = r.headers.get("X-Pack3d-Controllo")
            controllo = json.loads(unquote(controllo)) if controllo else None
            return r.status, glb, avvisi, time.time() - t, controllo
    except urllib.error.HTTPError as e:
        testo = e.read().decode("utf-8", "replace")
        return e.code, None, [testo[:1000]], time.time() - t, None


def costruisci(args):
    from pack3d import vista
    casi = _casi(args.casi, args.solo)
    os.makedirs(args.uscita, exist_ok=True)
    codice = os.path.abspath(args.codice or QUI)
    with open(os.path.join(args.uscita, "server.log"), "w") as log:
        p, url = _avvia(codice, log)
        try:
            riassunto = {}
            for caso in casi:
                nome = caso["nome"]
                stato, glb, avvisi, sec, _ = _costruisci_caso(url, args.casi, caso)
                esito = dict(nome=nome, stato=stato, secondi=round(sec, 1),
                             file=caso["file"], opzioni=caso.get("opzioni"),
                             avvisi=avvisi, md5=None)
                if glb is not None:
                    with open(os.path.join(args.uscita, nome + ".glb"), "wb") as fh:
                        fh.write(glb)
                    esito["md5"] = hashlib.md5(glb).hexdigest()
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
                sys.stdout.flush()
        finally:
            p.terminate()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
    with open(os.path.join(args.uscita, "riassunto.json"), "w") as fh:
        json.dump(dict(codice=codice, casi=riassunto), fh, indent=1)


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


def spazio(args):
    """Un caso del parco sullo Space vero, appena ripartito col codice di qui."""
    from pack3d import versione, vista
    caso = _casi(args.casi, [args.nome])[0]
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
    print("lo Space e' alla versione %s: costruisco %s" % (attesa, args.nome))
    sys.stdout.flush()
    stato, glb, avvisi, sec, controllo = _costruisci_caso(url, args.casi, caso)
    os.makedirs(args.uscita, exist_ok=True)
    esito = dict(nome=args.nome, url=url, versione=attesa, stato=stato,
                 secondi=round(sec, 1), avvisi=avvisi, controllo=controllo)
    if glb is not None:
        f = os.path.join(args.uscita, args.nome + "_spazio.glb")
        with open(f, "wb") as fh:
            fh.write(glb)
        esito["md5"] = hashlib.md5(glb).hexdigest()
        im, _ingombro = vista.viste(f, 512)
        im.save(os.path.join(args.uscita, args.nome + "_spazio_viste.png"))
    with open(os.path.join(args.uscita, args.nome + "_spazio.json"), "w",
              encoding="utf-8") as fh:
        json.dump(esito, fh, indent=1, ensure_ascii=False)
    if stato != 200:
        print("costruzione fallita sullo Space (%d): %s" % (stato, avvisi[0][:300]))
        raise SystemExit(3)
    if not controllo:
        print("costruito in %.0f s, ma il controllo dell'AI non c'e' stato" % sec)
        raise SystemExit(3)
    print("costruito in %.0f s - controllo dell'AI: %s" % (sec, controllo.get("esito")))
    print("  %s" % controllo.get("motivo", ""))
    for d in controllo.get("difetti") or []:
        print("  - %s" % d)
    raise SystemExit(ESITI.get(controllo.get("esito"), 3))


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


def glam(args):
    """Il modello che lo Space ha appena approvato, nel viewer Glam Lab."""
    caso = _casi(args.casi, [args.nome])[0]
    base = os.path.join(args.uscita, args.nome + "_spazio")
    try:
        with open(base + ".json", encoding="utf-8") as fh:
            esito = json.load(fh)
        with open(base + ".glb", "rb") as fh:
            glb = fh.read()
    except (OSError, ValueError):
        raise SystemExit("manca la prova sullo Space di %s in %s: prima `spazio`"
                         % (args.nome, args.uscita))
    verdetto = (esito.get("controllo") or {}).get("esito")
    if verdetto != "ok":
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


# Gli stati di un caso della coda, come li mostra Glam a chi l'ha caricato.
# "in-coda" non c'e': lo dice la pagina, quando il caso entra.
STATI = ("in-lavorazione", "domanda", "risolto", "non-risolto")


def _caso_in_coda(casi, cod):
    """(cartella del caso nel repository privato, il suo verdetto.json)."""
    if not cod or len(cod) != 10 or any(c not in "0123456789abcdef" for c in cod):
        raise SystemExit("il codice di un caso e' di 10 cifre esadecimali: %r" % cod)
    radice = os.path.join(casi, "casi")
    for d in sorted(os.listdir(radice) if os.path.isdir(radice) else []):
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


def _registra_stato(casi, cartella, codice, corpo):
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
    voce = {k: corpo[k] for k in ("stato", "nome", "messaggio", "domanda", "opzioni")
            if corpo.get(k) not in (None, "", [])}
    voce["quando"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    dati["storia"] = (storia + [voce])[-30:]
    with open(percorso, "w", encoding="utf-8") as fh:
        json.dump(dati, fh, ensure_ascii=False, indent=1)
    rel = os.path.relpath(percorso, casi)
    # l'autore dei commit del registro: lo stesso dell'ultimo
    autore = _git(casi, "log", "-1", "--format=%an%n%ae").stdout.split("\n")
    chi = ["-c", "user.name=" + autore[0], "-c", "user.email=" + autore[1]] \
        if len(autore) >= 2 and autore[0] and autore[1] else []
    _git(casi, "add", rel)
    fatto = _git(casi, *chi, "commit", "-m", "Caso %s: stato %s" % (codice, corpo["stato"]),
                 "--", rel)
    if fatto.returncode != 0 and "nothing to commit" not in fatto.stdout + fatto.stderr:
        print("stato.json non registrato: %s" % (fatto.stderr or fatto.stdout).strip()[:300])
        return False
    for _ in range(3):
        if _git(casi, "push", "origin", "HEAD:main").returncode == 0:
            print("stato del caso registrato in %s" % rel)
            return True
        _git(casi, "pull", "--rebase", "--autostash", "origin", "main")
    print("stato.json scritto ma non spinto su main: fallo tu (git push origin HEAD:main)")
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
        print("email della domanda non mandata (HTTP %d): %s"
              % (e.code, e.read().decode("utf-8", "replace")[:200]))
        return
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("lo Space non risponde per l'email della domanda: %s" % e)
        return
    if esito.get("inviate"):
        print("email della domanda mandata a chi l'ha chiesta (%d)" % esito["inviate"])
    else:
        print("email della domanda: nessuna (%s)" % esito.get("perche", "-"))


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
    # Prima la pagina dello Space, che non dipende da Glam: lo stato e la
    # domanda li legge dal registro dei casi, e con una domanda lo Space
    # scrive a chi ha lasciato l'email.
    if _registra_stato(args.casi, cartella, args.codice, corpo) and args.stato == "domanda":
        _avvisa(args.spazio, args.codice)
    req = urllib.request.Request(
        args.url.rstrip("/") + "/api/pack3d-case", method="POST",
        data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pack3d-studio"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            risposta = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
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
        raise SystemExit(1)
    except (urllib.error.URLError, OSError, ValueError) as e:
        _glam_irraggiungibile(e)
        raise SystemExit(1)
    print("in Glam: caso %s \"%s\" -> %s%s" % (
        args.codice, corpo["nome"], args.stato,
        " (utenti: %s)" % risposta["utenti"] if "utenti" in risposta else ""))


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
    c.set_defaults(fai=costruisci)
    k = sub.add_parser("confronta", help="confronta due costruzioni del parco")
    k.add_argument("prima")
    k.add_argument("dopo")
    k.add_argument("--immagini", help="dove salvare le viste affiancate")
    k.set_defaults(fai=confronta)
    s = sub.add_parser("spazio", help="prova un caso sullo Space vero, "
                                      "appena ripartito col codice di qui")
    s.add_argument("url", help="per esempio https://iccio-maurizio.hf.space")
    s.add_argument("casi", help="clone del repository privato dei casi")
    s.add_argument("nome", help="il caso del parco da provare")
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
    q.add_argument("--spazio", default=SPAZIO,
                   help="lo Space che manda l'email della domanda (di serie %s)" % SPAZIO)
    q.set_defaults(fai=caso)
    v = sub.add_parser("versione", help="l'impronta del codice, come la dice "
                                        "/api/ping")
    v.add_argument("--codice", help="cartella del codice (di serie questo)")
    v.set_defaults(fai=versione_del_codice)
    args = ap.parse_args()
    args.fai(args)


if __name__ == "__main__":
    main()
