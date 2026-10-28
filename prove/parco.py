"""Il parco: tutti i casi di prova ricostruiti come li costruisce il sito.

I PDF stanno nel repository PRIVATO dei casi (cartella `parco/` di
iccio84/pack3d-casi), mai qui: sono artwork dei clienti, e questo repository
e' pubblico. Qui c'e' solo lo strumento.

    python3 prove/parco.py costruisci CASI USCITA [--codice DIR] [--solo a,b]
    python3 prove/parco.py confronta PRIMA DOPO [--immagini DIR]
    python3 prove/parco.py stesi CASI USCITA [--solo a,b]
    python3 prove/parco.py misure CASI USCITA [--solo a,b] [--approva]
    python3 prove/parco.py spazio URL CASI NOME [--uscita DIR] [--attendi MIN]
    python3 prove/parco.py glam URL CASI NOME [--uscita DIR] [--categoria TESTO]
    python3 prove/parco.py caso URL CASI CODICE --stato STATO [--messaggio TESTO]
                                [--domanda TESTO --opzione TESTO ...]
    python3 prove/parco.py prepara CASI CODICE [--riprendi]
    python3 prove/parco.py consegna CASI CODICE --messaggio TESTO --commento TESTO
    python3 prove/parco.py approvato CASI CODICE
    python3 prove/parco.py prossimo CASI CODICE
    python3 prove/parco.py versione [--codice DIR]

`costruisci` avvia un server col codice di DIR (di serie quello di questo
repository), con il controllo dell'AI e la coda spenti, e per ogni caso di
CASI/parco/parco.json manda i PDF a /api/build con le opzioni del caso, come
fa la pagina. In USCITA salva per ogni caso il GLB, gli avvisi della
costruzione e le quattro viste (`pack3d.vista`).

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
annunciato. La risposta a una domanda torna
dallo Space, sulla issue del caso (`coda.aggiungi`).

`versione` stampa l'impronta del codice di DIR, quella che /api/ping
restituisce.

Il giro di un caso (CODA.md) usa `prepara`, `consegna` e `approvato`, qui
sotto, e costruisce solo quel caso, col codice della settimana. Alla fine
`prossimo` chiede allo Space di avviare una sessione nuova se in coda c'e'
un altro caso libero (`consegna` lo chiede da sola):

    python3 prove/parco.py costruisci ../pack3d-casi /tmp/caso --solo <nome>

Il parco intero, prima e dopo, lo fa il rilascio della settimana (vedi
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


def _misura(glb, caso):
    """(misure del modello, misure approvate cambiate). Mai un errore: un
    GLB che non si misura lo dice nelle misure."""
    from pack3d import misure
    try:
        m = misure.misura(glb)
    except Exception as e:                  # noqa: BLE001
        return {"errore": "%s: %s" % (type(e).__name__, e)}, []
    return m, misure.confronta(caso.get("misure"), m)


def costruisci(args):
    from pack3d import versione, vista
    casi = _casi(args.casi, args.solo)
    os.makedirs(args.uscita, exist_ok=True)
    codice = os.path.abspath(args.codice or QUI)
    impronta = versione.impronta(codice)
    with open(os.path.join(args.uscita, "server.log"), "w") as log:
        p, url = _avvia(codice, log)
        try:
            riassunto = {}
            for caso in casi:
                nome = caso["nome"]
                stato, glb, avvisi, sec, _ = _costruisci_caso(url, args.casi, caso)
                esito = dict(nome=nome, stato=stato, secondi=round(sec, 1),
                             file=caso["file"], opzioni=caso.get("opzioni"),
                             avvisi=avvisi, md5=None, versione=impronta)
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
    voce = {k: corpo[k] for k in ("stato", "nome", "messaggio", "domanda", "opzioni")
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
                                    opzione=None, modello=None, uscita=uscita,
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


def consegna(args):
    """Il modello corretto a chi ha caricato il caso, da approvare."""
    from contextlib import redirect_stdout
    import io
    from pack3d import versione
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
    f = os.path.join(uscita, voce["nome"] + ".json")
    esito = {}
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            esito = json.load(fh)
    rumore = io.StringIO()
    if esito.get("versione") != versione.impronta(QUI) or esito.get("stato") != 200:
        # il modello va costruito col codice che si consegna
        with redirect_stdout(rumore):
            costruisci(argparse.Namespace(casi=args.casi, uscita=uscita, codice=None,
                                          solo=[voce["nome"]]))
        with open(f, encoding="utf-8") as fh:
            esito = json.load(fh)
    if esito.get("stato") != 200:
        raise SystemExit("il caso non si costruisce col codice di adesso (%s): %s"
                         % (esito.get("stato"), str((esito.get("avvisi") or [""])[0])[:300]))
    # le misure del modello consegnato diventano quelle approvate del caso,
    # insieme a `come_deve_venire`: il rilascio le confronta
    if "misure" not in esito:
        # costruito prima che le misure ci fossero: si misura il suo GLB
        with open(os.path.join(uscita, voce["nome"] + ".glb"), "rb") as fh:
            esito["misure"], _ = _misura(fh.read(), voce)
    _approva_misure(args.casi, voce["nome"], esito)
    _commit_registro(args.casi, ["parco/parco.json"], "Caso %s: com'e' giusto" % cod)
    with redirect_stdout(rumore):
        try:
            caso(argparse.Namespace(url=args.glam, casi=args.casi, codice=cod,
                                    stato="da-approvare", messaggio=args.messaggio,
                                    domanda=None, opzione=None, modello=voce["nome"],
                                    uscita=uscita, spazio=args.spazio))
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
                                    opzione=None, modello=None, uscita="/tmp",
                                    spazio=args.spazio))
        except SystemExit:
            pass
    _commenta(args.repo, n, ("**In Glam**: «%s», cartella «%s» (%s)." % (
        nome, args.categoria, detto.splitlines()[-1][:300] if detto else "")
        if in_glam else "**Glam non ha preso il modello** (%s): il caso e' risolto lo "
        "stesso, e il PDF si puo' ricostruire in Glam a mano." % detto[-300:])
        + "\n\nResta aperta con `da-rilasciare`: la chiude il rilascio della settimana.")
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
        # Nutella Donut, resa, copre tutto il foglio), resa a una risoluzione
        # per texture
        puliti = []
        for f in caso["file"]:
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
    c.set_defaults(fai=costruisci)
    k = sub.add_parser("confronta", help="confronta due costruzioni del parco")
    k.add_argument("prima")
    k.add_argument("dopo")
    k.add_argument("--immagini", help="dove salvare le viste affiancate")
    k.set_defaults(fai=confronta)
    t = sub.add_parser("stesi", help="controlla che ogni texture sia lo steso "
                                     "del suo PDF, dritta")
    t.add_argument("casi", help="clone del repository privato dei casi")
    t.add_argument("uscita", help="la cartella di una costruzione del parco")
    t.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                   help="solo questi casi, separati da virgole")
    t.set_defaults(fai=stesi)
    m = sub.add_parser("misure", help="le misure di una costruzione contro quelle "
                                      "approvate (con --approva le scrive)")
    m.add_argument("casi", help="clone del repository privato dei casi")
    m.add_argument("uscita", help="la cartella di una costruzione del parco")
    m.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                   help="solo questi casi, separati da virgole")
    m.add_argument("--approva", action="store_true",
                   help="scrive le misure di questi modelli come approvate")
    m.set_defaults(fai=misure_del_parco)
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
    q.add_argument("--modello", help="con --stato da-approvare: il caso del "
                                     "parco costruito con `costruisci --solo` (o "
                                     "provato con `spazio`), il cui modello va a "
                                     "chi l'ha caricato da approvare")
    q.add_argument("--uscita", default="/tmp/parco_spazio",
                   help="la cartella dove `costruisci` (o `spazio`) ha salvato il GLB")
    q.add_argument("--spazio", default=SPAZIO,
                   help="lo Space che manda l'email della domanda (di serie %s)" % SPAZIO)
    q.set_defaults(fai=caso)
    for nome, fai, aiuto in (("prepara", prepara, "prende un caso libero, lo mette nel "
                              "parco, lo costruisce e fa il foglio da guardare"),
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
