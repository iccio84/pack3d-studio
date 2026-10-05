"""L'impronta del codice: la stessa sullo Space e in un clone di main.

Serve a sapere quando lo Space ha finito di ripartire dopo una pubblicazione.
`/api/ping` la restituisce, e `prove/parco.py spazio` aspetta che sia uguale a
quella del codice appena unito prima di provarci sopra un caso: senza, la
prova girava sul codice vecchio e diceva il falso.

Non dipende da git, perche' nell'immagine dello Space la cartella .git non
c'e' (.dockerignore): e' l'impronta dei file che fanno il modello, che il
Dockerfile copia cosi' come sono.
"""
import hashlib
import os

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = ("server.py", "agent.py", "pack3d_studio.html", "REGOLE.md",
        "requirements.txt")
CARTELLE = ("pack3d", "risorse")


def impronta(radice=RADICE):
    """Dodici cifre esadecimali: cambiano se cambia uno dei file del modello."""
    nomi = [f for f in FILE if os.path.isfile(os.path.join(radice, f))]
    for cartella in CARTELLE:
        for base, dirs, files in os.walk(os.path.join(radice, cartella)):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for f in files:
                if not f.endswith(".pyc"):
                    nomi.append(os.path.relpath(os.path.join(base, f), radice))
    h = hashlib.sha256()
    for nome in sorted(n.replace(os.sep, "/") for n in nomi):
        h.update(nome.encode("utf-8") + b"\0")
        with open(os.path.join(radice, nome), "rb") as fh:
            h.update(fh.read())
        h.update(b"\0")
    return h.hexdigest()[:12]
