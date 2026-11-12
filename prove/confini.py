"""
Il confine fra i materiali POP e i pack (regole/pop.md, *Il confine*).

Una PR verso coda-settimana o e' del POP o e' dei pack: non tocca le due cose
insieme. Un materiale POP nuovo, o una sua regola, non coinvolge le famiglie
dei pack (flowpack, astucci, vassoi...), e una correzione dei pack non tocca
il POP. Ogni file del repository sta in una di tre parti:

- **POP**: `pack3d/pop/`, `regole/pop.md`, `prove/test_pop.py`;
- **comune**: il servizio che le due parti condividono - la pagina,
  `server.py`, la coda, il registro delle famiglie e i tipi dichiarati, il
  parco, le prove comuni, il workflow, i documenti in cima al repository;
- **pack**: tutto il resto.

Una PR puo' toccare il comune con l'una o con l'altra, mai il POP e i pack
insieme. Il parco dice il resto: dopo una PR del POP nessun caso dei pack
cambia (RILASCIO.md).

    python3 prove/confini.py BASE [TESTA]

guarda i file che cambiano fra BASE e TESTA (di serie HEAD) ed esce con 1 se
toccano POP e pack insieme. Nelle Actions gira su ogni PR verso
coda-settimana (`.github/workflows/prove.yml`), contro il ramo di base.
"""
from __future__ import annotations

import subprocess
import sys

# la parte dei materiali POP; `pack3d/famiglie/pop.py` e' la casa che aveva
# prima di `pack3d/pop/`
POP = ("pack3d/pop/", "regole/pop.md", "prove/test_pop.py",
       "pack3d/famiglie/pop.py")

# il servizio comune: le due parti lo usano, e si tocca con l'una o con l'altra
COMUNI = ("server.py", "agent.py", "istantanea.py", "pack3d_studio.html",
          "pack3d/__init__.py", "pack3d/coda.py",
          "pack3d/famiglie/__init__.py", "pack3d/famiglie/comune.py",
          "pack3d/famiglie/registro.py",
          "prove/parco.py", "prove/soglie.py", "prove/confini.py",
          "prove/test_veloci.py", "prove/test_confini.py",
          "Dockerfile", "requirements.txt", ".gitignore", ".github/")


def _dentro(f, voci):
    return any(f == v or (v.endswith("/") and f.startswith(v)) for v in voci)


def parte(f):
    """"pop", "comune" o "pack": la parte del repository di questo file."""
    if _dentro(f, POP):
        return "pop"
    # i documenti in cima al repository (REGOLE.md, MAPPA.md, CODA.md...)
    if "/" not in f and f.endswith(".md"):
        return "comune"
    if _dentro(f, COMUNI):
        return "comune"
    return "pack"


def controlla(file):
    """(va bene, righe da dire) per la lista dei file cambiati."""
    parti = {"pop": [], "comune": [], "pack": []}
    for f in file:
        parti[parte(f)].append(f)
    righe = ["%s: %d file" % (p, len(parti[p])) for p in ("pop", "pack", "comune")]
    if parti["pop"] and parti["pack"]:
        righe += ["", "La PR tocca insieme il POP e i pack: vanno in due PR "
                      "(regole/pop.md, *Il confine*).", "", "POP:"]
        righe += ["  " + f for f in parti["pop"]]
        righe += ["pack:"]
        righe += ["  " + f for f in parti["pack"]]
        return False, righe
    return True, righe


def cambiati(base, testa="HEAD"):
    """I file che cambiano fra `base` e `testa`; un file spostato conta da
    tutte e due le parti, da dove esce e dove entra."""
    fuori = subprocess.run(["git", "diff", "--no-renames", "--name-only", base, testa],
                           check=True, capture_output=True, text=True).stdout
    return [r for r in fuori.splitlines() if r.strip()]


def main(argv):
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    va, righe = controlla(cambiati(*argv))
    print("\n".join(righe))
    return 0 if va else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
