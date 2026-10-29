"""
Le rese di pdfium tenute su disco, da una costruzione all'altra.

Su un artwork pesante la resa di pdfium e' quasi tutto il tempo di una
costruzione, e non dipende dalla risoluzione: sull'astuccio T10 al lampone
ogni resa costa dieci secondi fissi, anche a un decimo di scala, e una
costruzione ne fa nove - 74 secondi su 93. Ricostruire lo stesso PDF con
un'altra opzione - l'apertura, la saldatura, il rigonfiamento - le rifaceva
tutte e nove, perche' le casse di prima tengono una pagina sola, per nome di
file e per la sola costruzione in corso. Sul wafer da colazione erano 32
secondi su 48.

Qui le rese restano su disco, e la chiave e' il CONTENUTO del file, non il
nome: i file temporanei che la costruzione si fa strada facendo - la pagina
unica, la copia coi livelli spenti, quella senza le coperture - cambiano
nome a ogni costruzione ma hanno sempre gli stessi byte. Nella chiave c'e'
anche tutto il resto che decide i pixel: la pagina, i parametri della resa,
lo stato che chi rende ci mette intorno (vedi chi chiama `chiave`) e la
versione - il codice di `pack3d`, pypdfium2 e pdfium, Pillow, numpy,
Ghostscript. Una resa presa dalla cassa e' identica al byte a una rifatta:
il parco lo prova, e un codice cambiato non trova le rese del codice di
prima.

Si tengono solo le rese costate almeno `SOGLIA_S`: le altre si rifanno in
meno di quanto si scrivano. La cartella sta sotto quella dei tratti
(`dieline.CACHE`, `PACK3D_CACHE`; `0` spegne tutte e due), e quando passa
`RESE_MB` se ne vanno le meno usate. Un disco che non si legge o non si
scrive non ferma niente: la resa si rifa'.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

from . import dieline

CARTELLA = (os.path.join(dieline.CACHE, "rese")
            if dieline.CACHE and dieline.CACHE != "0" else None)
RESE_MB = float(os.environ.get("PACK3D_RESE_MB", "2048"))
SOGLIA_S = 1.0
# l'inizio di ogni file: una cassa di un'altra versione del formato non si legge
MAGIA = b"P3DRESA1"

_VERSIONE = []


def _ghostscript():
    gs = shutil.which("gs")
    if not gs:
        return None
    try:
        return subprocess.run([gs, "--version"], capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "?"


def versione():
    """L'impronta di quello che decide i pixel oltre al file: il codice di
    `pack3d` e le librerie. Fatta una volta per processo."""
    if not _VERSIONE:
        import importlib.metadata as metadati
        import pypdfium2
        h = hashlib.sha256()
        qui = os.path.dirname(os.path.abspath(__file__))
        for nome in sorted(os.listdir(qui)):
            if nome.endswith(".py"):
                with open(os.path.join(qui, nome), "rb") as fh:
                    h.update(nome.encode() + b"\0" + fh.read())
        librerie = []
        for p in ("pypdfium2", "pillow", "numpy"):
            try:
                librerie.append((p, metadati.version(p)))
            except metadati.PackageNotFoundError:
                librerie.append((p, None))
        h.update(repr((librerie, str(getattr(pypdfium2, "PDFIUM_INFO", "")),
                       _ghostscript())).encode())
        _VERSIONE.append(h.hexdigest()[:16])
    return _VERSIONE[0]


def chiave(tipo, pdf, *parti):
    """La chiave di una resa di `pdf`, o None se la cassa e' spenta o il file
    non si legge. `parti` e' tutto quello che, oltre al contenuto del file,
    cambia i pixel: deve avere un `repr` stabile."""
    if not CARTELLA:
        return None
    try:
        imp = dieline.impronta_file(pdf)
    except OSError:
        return None
    testo = repr((versione(), tipo, imp) + tuple(parti))
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()[:40]


def _file(k):
    return os.path.join(CARTELLA, k + ".resa")


def leggi(k):
    """`(array o None, dati)` dalla cassa, o None."""
    if k is None:
        return None
    f = _file(k)
    try:
        with open(f, "rb") as fh:
            if fh.read(len(MAGIA)) != MAGIA:
                raise ValueError("formato")
            testa = json.loads(fh.read(int.from_bytes(fh.read(4), "little")))
            a = None
            if "forma" in testa:
                forma = tuple(testa["forma"])
                n = math.prod(forma)
                a = np.fromfile(fh, dtype=np.dtype(testa["tipo"]), count=n)
                if a.size != n:
                    raise ValueError("corta")
                a = a.reshape(forma)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("cassa delle rese: %s non si legge (%s), la tolgo" % (k, e), file=sys.stderr)
        try:
            os.remove(f)
        except OSError:
            pass
        return None
    try:
        os.utime(f)         # le piu' usate restano quando la cartella si sfoltisce
    except OSError:
        pass
    return a, testa.get("dati")


def scrivi(k, a, dati=None):
    """Mette in cassa `a` (array numpy o None) e `dati` (JSON). Poi, se la
    cartella passa `RESE_MB`, butta le meno usate."""
    if k is None:
        return
    try:
        os.makedirs(CARTELLA, mode=0o700, exist_ok=True)
        testa = {"dati": dati}
        if a is not None:
            a = np.ascontiguousarray(a)
            testa.update(forma=list(a.shape), tipo=a.dtype.str)
        testa = json.dumps(testa, separators=(",", ":")).encode("utf-8")
        fd, tmp = tempfile.mkstemp(dir=CARTELLA, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(MAGIA + len(testa).to_bytes(4, "little") + testa)
                if a is not None:
                    fh.write(a.data)
            # chi legge trova la resa intera o niente, mai una a meta'
            os.replace(tmp, _file(k))
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        _sfoltisci()
    except OSError as e:
        print("cassa delle rese non scritta: %s" % e, file=sys.stderr)


def _sfoltisci():
    voci = []
    for nome in os.listdir(CARTELLA):
        try:
            s = os.stat(os.path.join(CARTELLA, nome))
        except OSError:
            continue
        voci.append((s.st_mtime, s.st_size, nome))
    tot = sum(v[1] for v in voci)
    for _t, n, nome in sorted(voci):
        if tot <= RESE_MB * 1024 * 1024:
            break
        try:
            os.remove(os.path.join(CARTELLA, nome))
            tot -= n
        except OSError:
            pass


def tieni(k, fai):
    """`(array o None, dati)`: dalla cassa se c'e'; se no da `fai()`, che va
    in cassa se e' costata almeno `SOGLIA_S`."""
    v = leggi(k)
    if v is not None:
        return v
    t = time.time()
    a, dati = fai()
    if k is not None and time.time() - t >= SOGLIA_S:
        scrivi(k, a, dati)
    return a, dati
