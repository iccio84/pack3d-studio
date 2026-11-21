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

Dentro i pack, dal 20 novembre 2026, **una famiglia per PR** (regole/casi.md):
i file propri di una famiglia (`FAMIGLIE`) con il nucleo comune dei pack, o
la Trade Unit con la famiglia del pack che contiene. Un lavoro che deve
toccarne di piu' - una regola per tutte le famiglie, uno spostamento - si
dichiara col titolo della PR che comincia con «Trasversale:» (la variabile
PR_TITOLO); il confine fra POP e pack vale lo stesso.

    python3 prove/confini.py BASE [TESTA]

guarda i file che cambiano fra BASE e TESTA (di serie HEAD) ed esce con 1 se
passano un confine. Nelle Actions gira su ogni PR verso coda-settimana
(`.github/workflows/prove.yml`), contro il ramo di base.
"""
from __future__ import annotations

import os
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


# Dentro i pack, i file propri di ogni famiglia (MAPPA.md, *Dove sta cosa*):
# una PR ne tocca al massimo una. Tutto il resto dei pack e' il **nucleo** -
# la lettura del DT, la grafica, la piegatura, la texture, le verifiche - che
# tutte le famiglie usano, e si tocca con una famiglia qualsiasi.
FAMIGLIE = {
    "flowpack": ("pack3d/flowpack.py", "pack3d/famiglie/flowpack.py",
                 "regole/flowpack.md"),
    "pouch": ("pack3d/pouch.py", "pack3d/famiglie/pouch.py", "regole/pouch.md"),
    "cartotecnico": ("pack3d/incisioni.py", "pack3d/apertura.py", "pack3d/rilievo.py",
                     "pack3d/lamina.py", "pack3d/punta.py", "pack3d/prisma.py",
                     "pack3d/coppa.py", "pack3d/cup.py", "pack3d/ballotin.py",
                     "pack3d/tubo.py", "pack3d/gelato.py",
                     "pack3d/famiglie/astuccio.py", "pack3d/famiglie/ballotin.py",
                     "pack3d/famiglie/coppa.py", "pack3d/famiglie/punta.py",
                     "pack3d/famiglie/tubo.py",
                     "regole/astucci.md", "regole/ballotin.md", "regole/coppe.md",
                     "regole/prisma.md", "regole/punta.md", "regole/tubo.md"),
    "incarti": ("pack3d/incarto.py", "pack3d/uovo.py", "pack3d/pralina.py",
                "pack3d/famiglie/incarto.py",
                "regole/incarti.md"),
    "trade unit": ("pack3d/vassoio.py", "pack3d/plancia.py", "pack3d/scatola_plancia.py",
                   "pack3d/sportello.py", "pack3d/riempimento.py",
                   "pack3d/famiglie/vassoio.py", "pack3d/famiglie/riempimento.py",
                   "regole/vassoi.md", "regole/riempimenti.md"),
}


def famiglia(f):
    """La famiglia dei pack di questo file, "nucleo" se e' dei pack ma di
    nessuna famiglia, o la sua parte ("pop", "comune") se non e' dei pack."""
    p = parte(f)
    if p != "pack":
        return p
    for nome, voci in FAMIGLIE.items():
        if _dentro(f, voci):
            return nome
    return "nucleo"


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


def controlla(file, trasversale=False):
    """(va bene, righe da dire) per la lista dei file cambiati. Con
    `trasversale` la PR puo' toccare piu' famiglie dei pack, mai il POP e i
    pack insieme."""
    parti = {"pop": [], "comune": [], "pack": []}
    for f in file:
        parti[parte(f)].append(f)
    righe = ["%s: %d file" % (p, len(parti[p])) for p in ("pop", "pack", "comune")]
    fam = {}
    for f in parti["pack"]:
        g = famiglia(f)
        if g != "nucleo":
            fam.setdefault(g, []).append(f)
    if fam:
        righe.append("famiglie dei pack: " + ", ".join(sorted(fam)))
    # la Trade Unit porta dentro le CU: un caso di riempimento puo' toccare
    # anche la famiglia del pack che contiene (il flowpack del display, la
    # posa dell'astuccio aperto), mai due famiglie oltre a lei
    altre = [g for g in fam if g != "trade unit"]
    if len(altre) > 1 and trasversale:
        righe.append("PR trasversale: piu' famiglie dei pack, come dice il titolo")
    elif len(altre) > 1:
        righe += ["", "La PR tocca piu' famiglie dei pack insieme: una PR per "
                      "famiglia, col nucleo comune dove serve; la Trade Unit "
                      "puo' andare con la famiglia del pack che contiene "
                      "(regole/casi.md, *Una famiglia per PR*).", ""]
        for g in sorted(fam):
            righe += [g + ":"] + ["  " + f for f in fam[g]]
        return False, righe
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
    titolo = os.environ.get("PR_TITOLO", "").strip()
    va, righe = controlla(cambiati(*argv),
                          trasversale=titolo.lower().startswith("trasversale"))
    print("\n".join(righe))
    return 0 if va else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
