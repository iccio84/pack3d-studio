"""
Le misure di un modello finito, per confrontarlo con quello approvato.

Il parco diceva se un modello era cambiato - l'impronta del GLB - e non se era
peggiorato: un cambio si guardava a occhio sulle viste affiancate, caso per
caso. Il 26 ottobre il rigonfiamento nello spessore e' uscito col rilascio e
il T1 del vassoio da 36 (caso 838cbae0ac) e' passato da 40,1 a 37,1 mm di
faccia, la grafica del fronte dal 6,6 al 2,6% di stiro: a occhio il cambio non
si vedeva, e l'ha visto chi l'aveva caricato, accanto al T1 approvato: una
lettera del marchio schiacciata. Con le misure approvate nel parco il
confronto lo dice da solo: «flowpack largo: 40,1 -> 37,1 mm (-7,5%)».

Le misure sono quelle che chi guarda un pack controlla, lette dal GLB e non
dagli avvisi, che cambiano parola per parola:

- `ingombro`: la scatola che contiene il modello, in mm lungo x, y, z;
- `pezzi`: quanti pezzi ha un riempimento;
- `flowpack`: lungo, largo e spesso il primo flowpack del modello - nel suo
  riferimento, a meta' del corpo (per un riempimento, il pezzo come sta nel
  vassoio, schiacciato) - e `stiro_fronte`, quanto e' stirata la grafica sul
  fronte del corpo, in percento (`verifica.stiri_flowpack`).

Un confronto (`confronta`) dice le misure approvate che cambiano oltre la
tolleranza: in mm `TOLLERANZA_MM` o `TOLLERANZA_FRAZIONE` della misura, il
piu' largo dei due; lo stiro di `TOLLERANZA_STIRO` punti; i pezzi esatti.
"""
from __future__ import annotations

import numpy as np

TOLLERANZA_MM = 0.3
TOLLERANZA_FRAZIONE = 0.005
TOLLERANZA_STIRO = 1.0
# la fetta a meta' corpo dove si misurano larghezza e spessore, in frazione
# della lunghezza
FETTA = 0.02


def misura(glb):
    """Le misure del GLB finito: un dict, vedi in testa al modulo."""
    from .riempimento import _dati, leggi, vertici
    from .verifica import stiri_flowpack
    J, B = leggi(glb)
    V = vertici(J, B)
    out = {"ingombro": [round(float(v), 1) for v in V.max(0) - V.min(0)]}
    pezzi = sum(1 for n in J.get("nodes", [])
                if str(n.get("name", "")).startswith("pezzo "))
    if pezzi:
        out["pezzi"] = pezzi
    for me in J.get("meshes", []):
        if me.get("name") != "flowpack":
            continue
        P = np.vstack([_dati(J, B, p["attributes"]["POSITION"]).astype(float)
                       for p in me["primitives"]]) * 1000.0
        ampi = P.max(0) - P.min(0)
        # l'asse lungo e' x o y: il modello puo' essere girato attorno al fronte
        lungo = 0 if ampi[0] > ampi[1] else 1
        mezzo = 0.5 * (P[:, lungo].min() + P[:, lungo].max())
        fetta = P[np.abs(P[:, lungo] - mezzo) < FETTA * ampi[lungo]]
        fp = {"lungo": round(float(ampi[lungo]), 1)}
        if len(fetta):
            fp["largo"] = round(float(np.ptp(fetta[:, 1 - lungo])), 1)
            fp["spesso"] = round(float(np.ptp(fetta[:, 2])), 1)
        stiri = stiri_flowpack(glb)
        if stiri:
            fp["stiro_fronte"] = round(100.0 * stiri[0][0], 1)
        out["flowpack"] = fp
        break
    return out


def _piatte(m, prima=""):
    """Le misure come coppie (nome, valore): "flowpack largo", "ingombro y"."""
    for k, v in m.items():
        nome = (prima + " " + k).strip()
        if isinstance(v, dict):
            yield from _piatte(v, nome)
        elif isinstance(v, list):
            for asse, x in zip("xyz", v):
                yield "%s %s" % (nome, asse), x
        else:
            yield nome, v


def confronta(attese, misurate):
    """Le misure approvate che cambiano oltre la tolleranza: righe come
    «flowpack largo: 40,1 -> 37,1 mm (-7,5%)». Vuota se nessuna. Una misura
    approvata che il modello non ha piu' (un flowpack sparito) e' un cambio;
    una nuova no."""
    nuove = dict(_piatte(misurate or {}))
    righe = []
    for nome, a in _piatte(attese or {}):
        b = nuove.get(nome)
        if b is None:
            righe.append("%s: %s -> manca" % (nome, _num(a)))
            continue
        if nome == "pezzi":
            if a != b:
                righe.append("pezzi: %d -> %d" % (a, b))
            continue
        if nome.endswith("stiro_fronte"):
            if abs(b - a) > TOLLERANZA_STIRO:
                righe.append("%s: %s%% -> %s%%" % (nome, _num(a), _num(b)))
            continue
        if abs(b - a) > max(TOLLERANZA_MM, TOLLERANZA_FRAZIONE * abs(a)):
            righe.append("%s: %s -> %s mm (%s%%)"
                         % (nome, _num(a), _num(b),
                            ("%+.1f" % (100.0 * (b - a) / a if a else 0.0)).replace(".", ",")))
    return righe


def _num(x):
    return ("%.1f" % x).replace(".", ",") if isinstance(x, float) else str(x)
