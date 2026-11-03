"""
Quanto manca alle soglie: per ogni caso del parco, a quale costante del
codice la sua lettura e' vicina, e di quanto.

Il pane ripieno T1 del riempimento col display da 15 aveva il 15,6% di stampa
oltre il lato, con la soglia di `tagliati` al 20%: e' bastata la linea di una
cornice per farlo cadere. Il parco lo diceva giusto, e nessuno sapeva che
stava a quattro punti dal cadere. Questo strumento lo dice prima.

Come: si sposta una soglia e si guarda chi cambia. Spostare la soglia del 10%
equivale a spostare del 10% il valore misurato sul caso: se la lettura cambia,
il caso stava a meno del 10% dalla soglia.

1. **La mappa.** Ogni caso si legge una volta (`/api/analyze`, come la
   pagina, chiamato nel processo con `server.esegui_lavoro`), tracciando le
   funzioni del codice che passano: dei loro nomi globali si tengono le
   costanti numeriche dei moduli di pack3d (`NOME = numero`), anche quelle
   che arrivano come valore di serie di un argomento. Cosi' ogni soglia si
   riprova solo sui casi che passano da lei. La lettura di questo giro e' il
   riferimento.
2. **La spinta.** Per ogni soglia, in un processo nuovo, la costante si porta
   al 25% in piu' e in meno (`PASSI`), dappertutto dove il codice la vede, e
   si rileggono i suoi casi. Dove una lettura cambia si riprova al 10% e al
   5%, solo su quei casi.
3. **L'esito.** Per ogni caso le soglie a cui e' vicino, col passo piu'
   piccolo che lo fa cambiare e cosa cambia; per ogni soglia i casi.

    python3 prove/soglie.py CASI USCITA [--solo a,b] [--soglie pack3d.flowpack.TAGLIA_GRAFICA]

Sul parco intero sono due ore e piu'. I giri restano in USCITA/giri: rilanciato
con lo stesso codice, riprende da dove era.

Le casse su disco (`PACK3D_CACHE=0`), i lavoratori, il controllo dell'AI e le
statistiche sono spenti: la lettura deve rifarsi, nel processo che ha la
soglia spostata. Una costante usata solo per calcolarne un'altra quando il
modulo si carica non si sposta con lei: si sposta l'altra.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# i passi, in frazione del valore: il primo su tutti i casi della soglia, gli
# altri solo su quelli che al passo prima sono cambiati
PASSI = (0.25, 0.10, 0.05)
# Le costanti che non sono soglie di una decisione: unita' di misura e
# risoluzioni (quanti punti per una curva, la scala del raster). Spostarle
# cambia la precisione di una misura, non la strada presa. Quelle col
# trattino basso davanti (`_BEZIER`, `_ANALISI_MAX`) sono codici e tetti di
# memoria, e restano fuori anche loro.
NON_SOGLIE = {"PT2MM", "MM2PT", "MM", "CAMPIONI", "SCALA_ANALISI"}
# moduli che non leggono il PDF: il servizio, la coda, le casse
MODULI_FUORI = {"server", "pack3d.lavoratori", "pack3d.coda", "pack3d.statistiche",
                "pack3d.stato", "pack3d.rese", "pack3d.versione"}
# quanto puo' durare un giro di letture con una soglia spostata
ATTESA = 1800


def _ambiente(casi):
    env = dict(os.environ, PACK3D_CACHE="0", PACK3D_LAVORATORI="0",
               PACK3D_CONTROLLO="0", PACK3D_STATISTICHE="0")
    if os.path.isdir(os.path.join(casi, "risorse")):
        env["PACK3D_RISORSE"] = os.path.abspath(os.path.join(casi, "risorse"))
    for k in ("ANTHROPIC_API_KEY", "PACK3D_CODA_REPO", "PACK3D_CODA_TOKEN"):
        env.pop(k, None)
    return env


def _casi(cartella, solo=None):
    sys.path.insert(0, os.path.join(QUI, "prove"))
    import parco
    return parco._casi(cartella, solo)


# --------------------------------------------------------------------------- #
# nel processo che legge
# --------------------------------------------------------------------------- #
def _leggi(server, cartella, caso):
    """La lettura di un caso come /api/analyze: il dict, o il testo
    dell'errore (come `parco._leggi_caso`)."""
    files = [os.path.join(cartella, "parco", "pdf", f) for f in caso["file"]]
    blocchi = []
    for f in files:
        with open(f, "rb") as fh:
            blocchi.append(fh.read())
    opts = dict(caso.get("opzioni") or {})
    opts["nomi"] = [quote(os.path.basename(f)) for f in files]
    if len(blocchi) > 1:
        opts["parti"] = [len(b) for b in blocchi]
    corpo = b"".join(blocchi)
    esito = server.esegui_lavoro({"path": "/api/analyze", "corpo": corpo,
                                  "intestazioni": {"Content-Length": str(len(corpo)),
                                                   "X-Pack3d": json.dumps(opts)}})
    r = esito.get("risposta") or {}
    body = r.get("body") or b""
    if isinstance(body, str):
        body = body.encode()
    if r.get("code") != 200:
        return "errore %s: %s" % (r.get("code"), body.decode("utf-8", "replace")[:500])
    return json.loads(body.decode("utf-8"))


def _moduli():
    return [m for n, m in sorted(sys.modules.items())
            if m is not None and (n == "pack3d" or n.startswith("pack3d."))
            and n not in MODULI_FUORI and getattr(m, "__file__", None)]


def _numeriche(g):
    return {k for k, v in g.items()
            if k.isupper() and not k.startswith("_") and type(v) in (int, float)
            and k not in NON_SOGLIE}


def _definita(mod, nome):
    """Se il sorgente del modulo assegna `nome` al primo livello."""
    try:
        with open(mod.__file__, encoding="utf-8") as fh:
            testo = fh.read()
    except OSError:
        return False
    return re.search(r"^%s\s*(:[^=\n]*)?=" % re.escape(nome), testo, re.M) is not None


def _origine(modname, nome):
    """`modulo.NOME` dove la costante e' scritta, anche se chi la usa l'ha
    importata (`from .dieline import PT2MM`)."""
    mod = sys.modules.get(modname)
    if mod is not None and _definita(mod, nome):
        return "%s.%s" % (modname, nome)
    valore = getattr(mod, nome, None) if mod is not None else None
    for m in _moduli():
        if getattr(m, nome, object()) is valore and _definita(m, nome):
            return "%s.%s" % (m.__name__, nome)
    return "%s.%s" % (modname, nome)


def _firma(fn):
    """Il testo della firma di una funzione, fino ai due punti."""
    try:
        righe, _ = inspect.getsourcelines(fn)
    except (OSError, TypeError):
        return ""
    out = []
    for r in righe:
        out.append(r)
        if r.rstrip().endswith(":"):
            break
    return "".join(out)


def _funzioni(mod):
    """Le funzioni del modulo, anche i metodi delle sue classi."""
    for v in vars(mod).values():
        if inspect.isfunction(v) and v.__module__ == mod.__name__:
            yield v
        elif inspect.isclass(v) and v.__module__ == mod.__name__:
            for w in vars(v).values():
                f = getattr(w, "__func__", w)
                if inspect.isfunction(f):
                    yield f


def _di_serie(fn):
    """{nome: indice} delle costanti di modulo che `fn` prende come valore di
    serie di un argomento (`def f(x, stacco=STACCO)`)."""
    g = fn.__globals__
    numeriche = _numeriche(g)
    out = {}
    vals = list(fn.__defaults__ or ()) + list((fn.__kwdefaults__ or {}).values())
    if not vals:
        return out
    firma = None
    for nome in numeriche:
        if any(v is g[nome] for v in vals):
            firma = _firma(fn) if firma is None else firma
            if re.search(r"=\s*%s\b" % re.escape(nome), firma):
                out[nome] = True
    return out


def traccia(server, cartella, caso):
    """(lettura, [soglie usate]) di un caso: le costanti numeriche dei moduli
    di pack3d che le funzioni passate nominano, o prendono di serie."""
    viste = set()

    def profilo(frame, evento, _arg):
        if evento == "call":
            viste.add(frame.f_code)

    import threading
    sys.setprofile(profilo)
    threading.setprofile(profilo)
    try:
        lettura = _leggi(server, cartella, caso)
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
    usate = set()
    numeriche = {}
    for m in _moduli():
        numeriche[m.__name__] = _numeriche(vars(m))
    per_codice = {}
    for m in _moduli():
        for fn in _funzioni(m):
            per_codice[fn.__code__] = (m.__name__, fn)
    for code in viste:
        mod_fn = per_codice.get(code)
        modname = mod_fn[0] if mod_fn else None
        if modname is None:
            # una funzione annidata o una comprensione: il modulo dal file
            for m in _moduli():
                if m.__file__ == code.co_filename:
                    modname = m.__name__
                    break
        if modname is None:
            continue
        for n in code.co_names:
            if n in numeriche.get(modname, ()):
                usate.add(_origine(modname, n))
        if mod_fn:
            for n in _di_serie(mod_fn[1]):
                usate.add(_origine(modname, n))
    return lettura, sorted(usate)


def sposta(nome, valore):
    """Porta la costante `modulo.NOME` a `valore` dappertutto dove il codice
    la vede: nei moduli che la tengono (anche importata) e nei valori di
    serie degli argomenti che la nominano. Torna una funzione che rimette
    tutto com'era."""
    modname, n = nome.rsplit(".", 1)
    __import__(modname)
    vecchio = getattr(sys.modules[modname], n)
    rimetti = []
    for m in _moduli():
        if vars(m).get(n, object()) is vecchio:
            setattr(m, n, valore)
            rimetti.append(lambda m=m: setattr(m, n, vecchio))
        for fn in _funzioni(m):
            d = fn.__defaults__
            if d and any(v is vecchio for v in d) and re.search(
                    r"=\s*%s\b" % re.escape(n), _firma(fn)):
                fn.__defaults__ = tuple(valore if v is vecchio else v for v in d)
                rimetti.append(lambda fn=fn, d=d: setattr(fn, "__defaults__", d))
            k = fn.__kwdefaults__
            if k and any(v is vecchio for v in k.values()) and re.search(
                    r"=\s*%s\b" % re.escape(n), _firma(fn)):
                fn.__kwdefaults__ = {a: (valore if v is vecchio else v) for a, v in k.items()}
                rimetti.append(lambda fn=fn, k=k: setattr(fn, "__kwdefaults__", k))

    def indietro():
        for r in reversed(rimetti):
            r()
    return indietro


def _importa_server():
    sys.path.insert(0, QUI)
    os.chdir(QUI)
    import server
    return server


def _lavora(args):
    """Il processo che legge: la mappa di un caso, o i casi con una soglia
    spostata. Scrive il JSON in `args.scrivi`."""
    server = _importa_server()
    casi = _casi(args.casi, args.solo)
    if args.mappa:
        out = {}
        for c in casi:
            lettura, usate = traccia(server, args.casi, c)
            out[c["nome"]] = {"lettura": lettura, "soglie": usate}
    else:
        _carica_tutto()
        sposta(args.soglia, json.loads(args.valore))
        out = {c["nome"]: _leggi(server, args.casi, c) for c in casi}
    with open(args.scrivi, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)


def _carica_tutto():
    """Tutti i moduli di pack3d, prima di spostare una soglia: un modulo
    caricato dopo prenderebbe la costante gia' spostata solo da chi la
    definisce, e con lei i suoi valori di serie."""
    import pkgutil
    import pack3d
    import pack3d.famiglie
    for pkg in (pack3d, pack3d.famiglie):
        for info in pkgutil.iter_modules(pkg.__path__):
            nome = "%s.%s" % (pkg.__name__, info.name)
            if nome in MODULI_FUORI:
                continue
            try:
                __import__(nome)
            except Exception:  # noqa: BLE001 - un modulo che non si carica non legge
                pass


# --------------------------------------------------------------------------- #
# il processo che guida
# --------------------------------------------------------------------------- #
def _giro(casi_dir, uscita, nomi, soglia=None, valore=None, mappa=False):
    """Un processo che legge `nomi`: con la soglia spostata, o la mappa."""
    os.makedirs(os.path.join(uscita, "giri"), exist_ok=True)
    chiave = "mappa_%s" % nomi[0] if mappa else "%s_%s_%d" % (
        soglia, repr(valore).replace(".", "p").replace("-", "m"), len(nomi))
    scrivi = os.path.join(uscita, "giri", re.sub(r"[^\w.]+", "_", chiave)[:150] + ".json")
    if os.path.exists(scrivi):
        # un giro gia' fatto con questo codice (`_stesso_codice`): si riprende
        with open(scrivi, encoding="utf-8") as fh:
            return json.load(fh), 0.0
    cmd = [sys.executable, os.path.abspath(__file__), "_lavora", casi_dir,
           "--scrivi", scrivi, "--solo", ",".join(nomi)]
    if mappa:
        cmd.append("--mappa")
    else:
        cmd += ["--soglia", soglia, "--valore", json.dumps(valore)]
    t = time.time()
    try:
        r = subprocess.run(cmd, env=_ambiente(casi_dir), capture_output=True,
                           text=True, timeout=ATTESA)
    except subprocess.TimeoutExpired:
        return {n: "tempo scaduto (%d s)" % ATTESA for n in nomi}, time.time() - t
    if r.returncode != 0 or not os.path.exists(scrivi):
        if os.path.exists(scrivi):
            os.remove(scrivi)
        coda = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or ["?"]
        return {n: "il giro non finisce: %s" % coda[0][:200] for n in nomi}, time.time() - t
    with open(scrivi, encoding="utf-8") as fh:
        return json.load(fh), time.time() - t


def _spinto(v, passo, segno, nome=""):
    """Il valore spostato di `passo` (frazione) verso `segno`; un intero di
    almeno uno; None se non si sposta (lo zero).

    Una frazione oltre la meta' (fra 0,5 e 1, senza unita' nel nome) si
    sposta nella parte che MANCA: `COPRE` = 0,9 vuol dire che puo' mancare
    il 10% della linea, e spostarla del 10% vuol dire che ne puo' mancare il
    9 o l'11 - non portarla a 0,99, che ne lascia mancare un decimo. Col
    valore spostato i display con plancia, che coprono il 98%, sembravano a
    un passo dal cadere, e ci stavano a 17 mm di linea. Sotto la meta' (una
    stampa del 20%) si sposta il valore."""
    if v == 0:
        return None
    if type(v) is int:
        d = max(1, int(round(abs(v) * passo)))
        return v + segno * d
    frazione = 0 < v < 1 and not re.search(r"_(MM|PT|PX|GRADI)$", nome)
    if frazione and v > 0.5:
        return 1.0 - (1.0 - v) * (1.0 - segno * passo)
    w = v * (1.0 + segno * passo)
    if frazione and w >= 1.0:
        return None
    return w


def _primo(v, segno, nome, da=0, prima=None):
    """(indice, valore) del primo passo di `PASSI`, da `da` in giu', che sposta
    davvero la soglia (diverso da `prima`), o None."""
    for i in range(da, len(PASSI)):
        w = _spinto(v, PASSI[i], segno, nome)
        if w is not None and w != prima:
            return i, w
    return None


def _cosa_cambia(a, b):
    if isinstance(b, str) and not isinstance(a, str):
        return ["la lettura diventa un errore: %s" % b[:160]]
    if isinstance(a, str) and not isinstance(b, str):
        return ["l'errore diventa una lettura (%s)" % b.get("title", "?")]
    sys.path.insert(0, os.path.join(QUI, "prove"))
    import parco
    righe = parco._differenze(a, b)
    return righe[:3]


def _valori(soglie):
    """{soglia: valore} leggendo i moduli in un processo a parte: quello che
    guida non carica pack3d."""
    codice = ("import json,sys; sys.path.insert(0, %r); out={}\n"
              "for s in %r:\n"
              "    m, n = s.rsplit('.', 1)\n"
              "    __import__(m); out[s] = getattr(sys.modules[m], n)\n"
              "print(json.dumps(out))" % (QUI, list(soglie)))
    r = subprocess.run([sys.executable, "-c", codice], capture_output=True, text=True,
                       cwd=QUI, env=dict(os.environ, PACK3D_CACHE="0"))
    if r.returncode != 0:
        raise SystemExit("non leggo i valori delle soglie: %s" % r.stderr[-300:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _stesso_codice(uscita):
    """I giri in `uscita` valgono solo per il codice che li ha fatti: con un
    altro codice (`pack3d.versione.impronta`) si buttano. Cosi' un giro
    interrotto - due ore e piu' sul parco intero - riprende da dove era."""
    import shutil
    sys.path.insert(0, QUI)
    from pack3d import versione
    adesso = versione.impronta(QUI)
    f = os.path.join(uscita, "codice.txt")
    prima = open(f, encoding="utf-8").read().strip() if os.path.exists(f) else None
    if prima != adesso and os.path.isdir(os.path.join(uscita, "giri")):
        shutil.rmtree(os.path.join(uscita, "giri"))
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(adesso + "\n")
    return adesso, prima == adesso


def guida(args):
    casi = _casi(args.casi, args.solo)
    nomi = [c["nome"] for c in casi]
    os.makedirs(args.uscita, exist_ok=True)
    codice, riprende = _stesso_codice(args.uscita)
    print("codice %s%s" % (codice, ": riprendo i giri gia' fatti" if riprende else ""),
          flush=True)
    paralleli = args.paralleli or max(1, (os.cpu_count() or 2))
    t0 = time.time()

    # 1. la mappa, un processo per caso
    print("la mappa: %d casi, %d alla volta" % (len(nomi), paralleli), flush=True)
    with ThreadPoolExecutor(paralleli) as pool:
        giri = list(pool.map(lambda n: _giro(args.casi, args.uscita, [n], mappa=True), nomi))
    mappa = {}
    for (out, _s), n in zip(giri, nomi):
        r = out.get(n)
        if not isinstance(r, dict):
            print("  %-44s %s" % (n[:44], r))
            continue
        mappa[n] = r
    # la lettura nel processo e' quella della pagina: contro le approvate
    sys.path.insert(0, os.path.join(QUI, "prove"))
    import parco
    approvate = parco._letture_approvate(args.casi)
    diverse = [n for n, r in mappa.items() if n in approvate and r["lettura"] != approvate[n]]
    print("%d letture su %d uguali alle approvate%s" % (
        len(mappa) - len(diverse), len(mappa),
        (": diverse " + ", ".join(diverse)) if diverse else ""), flush=True)
    soglie = sorted({s for r in mappa.values() for s in r["soglie"]})
    if args.soglie:
        voluti = set(args.soglie)
        soglie = [s for s in soglie if s in voluti]
    valori = _valori(soglie)
    print("%d soglie usate dai casi, in %.0f s" % (len(soglie), time.time() - t0), flush=True)

    # 2. la spinta: un giro per soglia e verso, sui casi che la usano
    def chi_usa(s):
        return [n for n in nomi if n in mappa and s in mappa[n]["soglie"]]

    esiti = {s: {"valore": valori[s], "casi": chi_usa(s), "cambia": {}} for s in soglie}
    lavori = []
    for s in soglie:
        for segno in (+1, -1):
            p = _primo(valori[s], segno, s)
            if p is not None and esiti[s]["casi"]:
                lavori.append((s, segno, p[0], p[1], esiti[s]["casi"]))
    fatti = 0
    while lavori:
        with ThreadPoolExecutor(paralleli) as pool:
            risultati = list(pool.map(
                lambda l: (l, _giro(args.casi, args.uscita, l[4], soglia=l[0], valore=l[3])),
                lavori))
        nuovi = []
        for (s, segno, i, v, chi), (out, sec) in risultati:
            fatti += 1
            cambiati = [n for n in chi if out.get(n) != mappa[n]["lettura"]]
            for n in cambiati:
                # il passo piu' piccolo vince: i passi vanno dal grande al piccolo
                esiti[s]["cambia"].setdefault(n, {})["%+d" % segno] = {
                    "passo": PASSI[i], "valore": v,
                    "cosa": _cosa_cambia(mappa[n]["lettura"], out.get(n))}
            p = _primo(valori[s], segno, s, i + 1, v) if cambiati else None
            if p is not None:
                nuovi.append((s, segno, p[0], p[1], cambiati))
        print("  %d giri fatti, %d da fare (%.0f s)" % (fatti, len(nuovi), time.time() - t0),
              flush=True)
        lavori = nuovi

    # 3. l'esito
    with open(os.path.join(args.uscita, "soglie.json"), "w", encoding="utf-8") as fh:
        json.dump(esiti, fh, ensure_ascii=False, indent=1)
    testo = rapporto(esiti, len(nomi), time.time() - t0)
    with open(os.path.join(args.uscita, "soglie.md"), "w", encoding="utf-8") as fh:
        fh.write(testo)
    print(testo)
    if args.riassunto:
        with open(args.riassunto, "a", encoding="utf-8") as fh:
            fh.write(testo)


def rapporto(esiti, n_casi, secondi):
    """Il riassunto in markdown. Prima i casi vicini a una soglia - la
    lettura cambia spostandola in un verso solo: una decisione che cambia
    strada -, dal passo piu' piccolo. Poi i valori che entrano nella
    lettura: cambia in tutti e due i versi, come cambia una misura quando
    cambia un numero che la compone, e non e' una strada vicina al bivio."""
    vicini, valori = [], {}
    for s, e in esiti.items():
        for n, versi in e["cambia"].items():
            if len(versi) == 2:
                valori.setdefault(s, []).append(n)
                continue
            for verso, d in versi.items():
                vicini.append((d["passo"], n, s, verso, e["valore"], d["valore"], d["cosa"]))
    vicini.sort(key=lambda x: (x[0], x[1], x[2]))
    righe = ["## Quanto manca alle soglie",
             "",
             "%d casi, %d soglie provate (spostate del %s), in %.0f minuti."
             % (n_casi, len(esiti), ", ".join("%d%%" % round(p * 100) for p in PASSI),
                secondi / 60.0),
             ""]
    if vicini:
        righe += ["### Vicini a una soglia",
                  "",
                  "La lettura cambia spostando la soglia in un verso solo: il valore "
                  "misurato sul caso sta entro quel passo da lei.",
                  "",
                  "| entro | caso | soglia | verso | valore -> spostato | cosa cambia |",
                  "|---|---|---|---|---|---|"]
        for passo, n, s, verso, v, v2, cosa in vicini:
            righe.append("| %d%% | %s | `%s` | %s | %s -> %s | %s |" % (
                round(passo * 100), n, s, "su" if verso == "+1" else "giu'",
                _num(v), _num(v2), "<br>".join(c.strip().replace("|", "/")[:140]
                                               for c in cosa)))
        righe.append("")
    else:
        righe += ["Nessun caso e' vicino a una soglia: tutti stanno a piu' del %d%%."
                  % round(PASSI[0] * 100), ""]
    if valori:
        righe += ["### Valori che entrano nella lettura",
                  "",
                  "Cambiano la lettura in tutti e due i versi: sono numeri che la "
                  "compongono (un angolo proposto, una misura d'uso), non bivi.",
                  ""]
        for s in sorted(valori):
            righe.append("- `%s` (%s): %s" % (s, _num(esiti[s]["valore"]),
                                             ", ".join(sorted(valori[s]))))
        righe.append("")
    regge = sorted(s for s, e in esiti.items() if not e["cambia"])
    righe += ["Reggono in tutti e due i versi: %d soglie su %d." % (len(regge), len(esiti)),
              ""]
    return "\n".join(righe) + "\n"


def _num(v):
    return ("%d" % v) if isinstance(v, int) else ("%.4g" % v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    lv = sub.add_parser("_lavora")
    lv.add_argument("casi")
    lv.add_argument("--scrivi", required=True)
    lv.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x])
    lv.add_argument("--mappa", action="store_true")
    lv.add_argument("--soglia")
    lv.add_argument("--valore")
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ["_lavora"]:
        return _lavora(ap.parse_args(argv))
    g = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g.add_argument("casi", help="clone del repository privato dei casi")
    g.add_argument("uscita", help="dove scrivere i giri e l'esito (fuori dal repository)")
    g.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x],
                   help="solo questi casi, separati da virgole")
    g.add_argument("--soglie", type=lambda s: [x for x in s.split(",") if x],
                   help="solo queste soglie (modulo.NOME), separate da virgole")
    g.add_argument("--paralleli", type=int, help="quanti processi alla volta")
    g.add_argument("--riassunto", help="il file dove aggiungere il riassunto in "
                                       "markdown (nelle Actions: $GITHUB_STEP_SUMMARY)")
    return guida(g.parse_args(argv))


if __name__ == "__main__":
    main()
