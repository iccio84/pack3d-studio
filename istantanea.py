"""
Il progetto in un file solo, da dare in pasto alla chat.

La chat non vede GitHub: ragiona sulla copia che le hai dato tu. Se quella
copia e' vecchia, il pacchetto che ti restituisce cancella tutto il lavoro
fatto nel frattempo — ed e' esattamente cosi' che lo stesso model id e' stato
riscritto a mano quattro volte di fila.

Questo script impacchetta i file veri, quelli che git ha adesso, in un unico
markdown da caricare nella conoscenza del progetto della chat.

    python istantanea.py                        # tutto
    python istantanea.py pack3d/flowpack.py server.py   # solo questi
    python istantanea.py --out /tmp/x.md
"""
from __future__ import annotations

import os
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))

LINGUA = {".py": "python", ".html": "html", ".ts": "ts", ".tsx": "tsx",
          ".md": "markdown", ".json": "json", ".txt": "text", ".css": "css",
          ".js": "js", ".yml": "yaml", ".yaml": "yaml"}
PER_NOME = {"Dockerfile": "dockerfile", ".gitignore": "text",
            ".dockerignore": "text"}

# la rete di sicurezza per quando non c'e' git: senza .gitignore a guidare
# la passeggiata ci finirebbero dentro i .pyc e i GLB di prova
SALTA_CARTELLE = {".git", "__pycache__", "node_modules", ".venv", "venv",
                  "out", "dist", "build", ".pytest_cache"}
SALTA_ESTENSIONI = {".pyc", ".pyo", ".glb", ".obj", ".mtl", ".pdf", ".png",
                    ".jpg", ".jpeg", ".zip", ".so", ".dylib", ".ico"}

INTESTAZIONE = """\
# Istantanea di pack3d-studio

%(firma)s

Questo e' lo stato **vero** del progetto, piu' recente della copia che hai in
memoria. I file qui sotto sostituiscono qualsiasi versione precedente: se
ricordi un file diverso da questo, quello che ricordi e' stato superato.

Quando proponi una modifica dammi **solo i file che cambiano**, interi, con il
percorso in testa. Non rigenerare il progetto e non allegare uno zip: l'ho gia'
tutto, e un pacchetto completo riporta indietro le parti che non hai toccato.

## Indice

%(indice)s
"""


def _git(*args):
    return subprocess.run(("git",) + args, cwd=QUI, capture_output=True,
                          text=True, check=True).stdout


def _elenco_git():
    # --others --exclude-standard perche' un modulo appena scritto e non ancora
    # committato fa parte del progetto: senza, l'istantanea lo nasconde e la
    # chat ragiona su un progetto che non esiste piu'
    fuori = _git("ls-files", "--cached", "--others", "--exclude-standard")
    return sorted(f for f in fuori.splitlines() if f.strip())


def _elenco_a_mano():
    trovati = []
    for radice, cartelle, file in os.walk(QUI):
        cartelle[:] = [c for c in cartelle if c not in SALTA_CARTELLE]
        for f in file:
            p = os.path.relpath(os.path.join(radice, f), QUI)
            if os.path.splitext(f)[1].lower() not in SALTA_ESTENSIONI:
                trovati.append(p)
    return sorted(trovati)


def _firma():
    try:
        h = _git("log", "-1", "--format=%h %ad %s", "--date=short").strip()
        sporco = bool(_git("status", "--porcelain").strip())
        return "commit `%s`%s" % (h, "  — **con modifiche non committate**"
                                  if sporco else "")
    except Exception:
        return "copia locale, senza git: la provenienza non e' verificabile"


def _lingua(rel):
    base = os.path.basename(rel)
    if base in PER_NOME:
        return PER_NOME[base]
    return LINGUA.get(os.path.splitext(rel)[1].lower(), "")


def _recinto(testo):
    """Un recinto piu' lungo della piu' lunga fila di apici che sta dentro.

    REGOLE.md e LEGGIMI.md contengono blocchi ``` : con il recinto fisso a tre
    il file si spezzerebbe a meta' e la chat leggerebbe il resto come prosa.
    """
    massimo = corrente = 0
    for c in testo:
        corrente = corrente + 1 if c == "`" else 0
        massimo = max(massimo, corrente)
    return "`" * max(3, massimo + 1)


def istantanea(soltanto=None):
    try:
        elenco = _elenco_git()
    except Exception:
        elenco = _elenco_a_mano()
    if soltanto:
        voluti = {os.path.normpath(s) for s in soltanto}
        elenco = [f for f in elenco if os.path.normpath(f) in voluti]
        mancanti = voluti - {os.path.normpath(f) for f in elenco}
        if mancanti:
            raise SystemExit("non trovati: %s" % ", ".join(sorted(mancanti)))

    corpi, indice, saltati = [], [], []
    for rel in elenco:
        percorso = os.path.join(QUI, rel)
        if not os.path.isfile(percorso):
            continue
        try:
            testo = open(percorso, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            saltati.append(rel)
            continue
        righe = testo.count("\n") + (0 if testo.endswith("\n") else 1)
        indice.append("- `%s` — %d righe" % (rel, righe))
        r = _recinto(testo)
        corpi.append("## `%s`\n\n%s%s\n%s\n%s\n" %
                     (rel, r, _lingua(rel), testo.rstrip("\n"), r))

    fuori = [INTESTAZIONE % dict(firma=_firma(), indice="\n".join(indice))]
    fuori.extend(corpi)
    if saltati:
        fuori.append("## File binari, non inclusi\n\n%s\n" %
                     "\n".join("- `%s`" % s for s in saltati))
    return "\n".join(fuori), len(indice), saltati


def main(argv):
    argv = list(argv)
    out = os.path.join(QUI, "istantanea_pack3d.md")
    if "--out" in argv:
        i = argv.index("--out")
        out = argv[i + 1]
        del argv[i:i + 2]

    testo, quanti, saltati = istantanea(argv or None)
    open(out, "w", encoding="utf-8").write(testo)
    print("%s — %d file, %d KB, ~%d mila token" %
          (out, quanti, len(testo) // 1024, len(testo) // 4000))
    if saltati:
        print("binari elencati ma non inclusi: %d" % len(saltati))


if __name__ == "__main__":
    main(sys.argv[1:])
