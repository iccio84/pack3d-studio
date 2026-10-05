"""Il parco: tutti i casi di prova ricostruiti come li costruisce il sito.

I PDF stanno nel repository PRIVATO dei casi (cartella `parco/` di
iccio84/pack3d-casi), mai qui: sono artwork dei clienti, e questo repository
e' pubblico. Qui c'e' solo lo strumento.

    python3 prove/parco.py costruisci CASI USCITA [--codice DIR] [--solo a,b]
    python3 prove/parco.py confronta PRIMA DOPO [--immagini DIR]

`costruisci` avvia un server col codice di DIR (di serie quello di questo
repository), con il controllo dell'AI e la coda spenti, e per ogni caso di
CASI/parco/parco.json manda i PDF a /api/build con le opzioni del caso, come
fa la pagina. In USCITA salva per ogni caso il GLB, gli avvisi della
costruzione e le quattro viste (`pack3d.vista`).

`confronta` dice quali modelli sono cambiati fra due costruzioni, con gli
avvisi che cambiano, e per ognuno affianca le viste: PRIMA sopra, DOPO sotto.
Le immagini finiscono in DIR, di serie DOPO/confronto.

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
    """(stato, glb o None, avvisi, secondi) di un caso, come lo chiede la pagina."""
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
            return r.status, glb, avvisi, time.time() - t
    except urllib.error.HTTPError as e:
        testo = e.read().decode("utf-8", "replace")
        return e.code, None, [testo[:1000]], time.time() - t


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
                stato, glb, avvisi, sec = _costruisci_caso(url, args.casi, caso)
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
    uguali, cambiati = [], []
    for nome in sorted(set(a) | set(b)):
        ea, eb = a.get(nome), b.get(nome)
        if ea is None or eb is None:
            print("SOLO IN %s  %s" % ("DOPO" if ea is None else "PRIMA", nome))
            cambiati.append(nome)
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
    print("\n%d uguali al byte, %d cambiati%s" % (
        len(uguali), len(cambiati),
        (": le viste affiancate sono in %s" % uscita) if cambiati else ""))


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
    args = ap.parse_args()
    args.fai(args)


if __name__ == "__main__":
    main()
