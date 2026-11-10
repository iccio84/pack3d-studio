"""Ogni primitiva coi suoi vertici: il GLB che esce si apre uguale ovunque.

Le costruzioni scrivono una mesh con piu' primitive - la stampa, il
rovescio, il taglio (`steso.Tinte`), i pezzi di un display - che usano gli
stessi vertici: una POSITION, una NORMAL e una TEXCOORD_0 in comune, e per
ogni primitiva solo i suoi indici. E' glTF valido, e Glam, lo Space e il
validatore lo leggono, ma KeyShot no: un modello cosi' vi entra bianco, senza
la texture, mentre un flowpack, che ha una primitiva sola, entra col suo
colore. Con i vertici separati - la stessa forma, le stesse UV, ogni
primitiva coi suoi - KeyShot mostra la texture (provato sul T6 a punta).

`per_tutti` fa questo sul GLB finito, alla fine di ogni costruzione
(`famiglie.registro`), e lascia stare il resto del codice, che legge e
compone i GLB intermedi come sempre. In piu':

- ogni primitiva prende solo i vertici che usa, e le UV solo se il suo
  materiale ha una texture (il rovescio e il taglio, di colore pieno, no);
- le normali restano quelle di prima, fatte sui vertici in comune: lungo il
  confine fra due primitive l'ombreggiatura non cambia; quelle nulle si
  rifanno e quelle lunghe piu' o meno di 1 si riportano a 1, come vuole
  glTF (`_senza_nulle`);
- due materiali con lo stesso nome (il "film" del vassoio e quello del
  flowpack, in un riempimento) prendono nomi diversi, dalla mesh che li
  usa; un nome che c'e' una volta sola resta com'e' (le facce di un
  astuccio, che il template scrive sul PSD);
- una texture per immagine e campionatore: due texture uguali diventano
  una;
- le primitive della stessa mesh con lo stesso materiale, a meno del nome,
  diventano una (`unisci`): l'astuccio ne aveva una per faccia, sulla stessa
  texture, e in KeyShot erano tanti elementi. Il T10 passa da 12 a 2: la
  stampa con la texture e il rovescio. I nomi delle facce restano negli
  extras della primitiva (`pack3d_facce`), per il template.

Le immagini, le zone di un atlante e i nodi restano com'erano.
"""
from __future__ import annotations

import json

import numpy as np

from .atlante import _ricompatta
from .riempimento import _dati, leggi, scrivi

VERTICI = 34962
INDICI = 34963


def _riferimenti_texture(x):
    """I riferimenti a una texture (`{"index": ..}` sotto una chiave che
    finisce in "Texture") dentro un materiale, anche nelle estensioni."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k.endswith("Texture") and isinstance(v, dict) and "index" in v:
                yield v
            else:
                yield from _riferimenti_texture(v)
    elif isinstance(x, list):
        for v in x:
            yield from _riferimenti_texture(v)


def nomi_unici(J):
    """Due materiali con lo stesso nome: il primo lo tiene, gli altri lo
    prendono dalla prima mesh che li usa ("film" diventa il nome della mesh,
    un altro nome gli si aggiunge dopo)."""
    materiali = J.get("materials") or []
    mesh_di = {}
    for me in J.get("meshes") or []:
        for p in me.get("primitives") or []:
            if p.get("material") is not None:
                mesh_di.setdefault(p["material"], me.get("name") or "mesh")
    usati = set()
    for i, m in enumerate(materiali):
        n = m.get("name") or ""
        if n and n not in usati:
            usati.add(n)
            continue
        me = mesh_di.get(i, "materiale")
        base = me if n in ("", "film") else "%s %s" % (me, n)
        nuovo, k = base, 2
        while nuovo in usati:
            nuovo, k = "%s %d" % (base, k), k + 1
        usati.add(nuovo)
        m["name"] = nuovo
    return J


def una_texture_per_immagine(J):
    """Campionatori uguali uniti, e una texture per (immagine,
    campionatore): i materiali puntano a quella."""
    campionatori = J.get("samplers") or []
    if campionatori:
        chiave = [json.dumps(s, sort_keys=True) for s in campionatori]
        primo = {}
        cm = {i: primo.setdefault(c, len(primo)) for i, c in enumerate(chiave)}
        J["samplers"] = [campionatori[chiave.index(c)] for c in primo]
    else:
        cm = {}
    trame, nuove, tm, per = J.get("textures") or [], [], {}, {}
    for i, t in enumerate(trame):
        t = dict(t)
        if "sampler" in t:
            t["sampler"] = cm[t["sampler"]]
        c = json.dumps(t, sort_keys=True)
        if c not in per:
            per[c] = len(nuove)
            nuove.append(t)
        tm[i] = per[c]
    if trame:
        J["textures"] = nuove
    for m in J.get("materials") or []:
        for r in _riferimenti_texture(m):
            r["index"] = tm[r["index"]]
    return J


def _senza_nulle(N, P, T):
    """Le normali `N` della primitiva lunghe 1, con quelle nulle rifatte
    sulle sue facce. Sui vertici in comune una normale si somma su tutte le facce che
    li toccano, e dove una parete ha la stampa da un lato e il rovescio
    dall'altro le due si annullano: glTF la vuole lunga 1, e il validatore
    la segna come errore. Sola, la primitiva ha le facce da un lato solo."""
    N = np.array(N, np.float32)
    lun = np.linalg.norm(N, axis=1)
    nulle = lun < 1e-6
    # una normale lunga piu' o meno di 1 (il display KMS T10 aperto le ha
    # lunghe 1,026) si riporta a 1: la direzione resta quella
    storte = ~nulle & (np.abs(lun - 1.0) > 1e-3)
    N[storte] /= lun[storte, None]
    if not nulle.any():
        return N
    P = P.astype(float)
    f = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    somma = np.zeros((len(P), 3))
    for j in range(3):
        np.add.at(somma, T[:, j], f)
    lun = np.linalg.norm(somma, axis=1)
    rifatte = np.where(lun[:, None] > 1e-12, somma / np.maximum(lun, 1e-12)[:, None],
                       [0.0, 0.0, 1.0])
    N[nulle] = rifatte[nulle]
    return N


def separa(J, B):
    """`(J, B)` nuovi: ogni primitiva coi suoi attributi, solo i vertici che
    usa e gli indici rifatti su quelli. Le UV restano solo dove il
    materiale ha una texture."""
    B = bytearray(B)
    materiali = J.get("materials") or []
    con_texture = {i for i, m in enumerate(materiali)
                   if next(_riferimenti_texture(m), None) is not None}

    def aggiungi(arr, vecchio, target):
        arr = np.ascontiguousarray(arr)
        while len(B) % 4:
            B.append(0)
        J["bufferViews"].append({"buffer": 0, "byteOffset": len(B),
                                 "byteLength": arr.nbytes, "target": target})
        B.extend(arr.tobytes())
        acc = {"bufferView": len(J["bufferViews"]) - 1,
               "componentType": vecchio["componentType"],
               "count": int(arr.shape[0]), "type": vecchio["type"]}
        if vecchio.get("normalized"):
            acc["normalized"] = True
        if "min" in vecchio or "max" in vecchio:
            acc["min"] = arr.min(0).tolist()
            acc["max"] = arr.max(0).tolist()
        J["accessors"].append(acc)
        return len(J["accessors"]) - 1

    for me in J.get("meshes") or []:
        for p in me.get("primitives") or []:
            a = p["attributes"]
            n = J["accessors"][a["POSITION"]]["count"]
            ix = (_dati(J, B, p["indices"]).astype(np.int64).ravel()
                  if "indices" in p else np.arange(n))
            usati, nuovi = np.unique(ix, return_inverse=True)
            nuovo = {}
            for k, i in a.items():
                if k.startswith("TEXCOORD_") and p.get("material") not in con_texture:
                    continue
                dati = _dati(J, B, i)[usati]
                if k == "NORMAL" and p.get("mode", 4) == 4:
                    dati = _senza_nulle(dati, _dati(J, B, a["POSITION"])[usati],
                                        nuovi.reshape(-1, 3))
                nuovo[k] = aggiungi(dati, J["accessors"][i], VERTICI)
            p["attributes"] = nuovo
            for t in p.get("targets") or []:
                for k, i in list(t.items()):
                    t[k] = aggiungi(_dati(J, B, i)[usati], J["accessors"][i], VERTICI)
            p["indices"] = aggiungi(nuovi.astype(np.uint32).ravel(),
                                    {"componentType": 5125, "type": "SCALAR"}, INDICI)
    # via gli accessori che nessuna primitiva usa piu', e le loro viste
    usati = sorted({v for me in J.get("meshes") or [] for p in me.get("primitives") or []
                    for v in list(p["attributes"].values()) + [p["indices"]]
                    + [x for t in p.get("targets") or [] for x in t.values()]})
    m = {k: n for n, k in enumerate(usati)}
    J["accessors"] = [J["accessors"][k] for k in usati]
    for me in J.get("meshes") or []:
        for p in me.get("primitives") or []:
            p["attributes"] = {k: m[v] for k, v in p["attributes"].items()}
            p["indices"] = m[p["indices"]]
            for t in p.get("targets") or []:
                for k in t:
                    t[k] = m[t[k]]
    return J, _ricompatta(J, B, [])


def _chiave(J, p):
    """Cosa deve avere uguale una primitiva per unirsi a un'altra: il
    materiale a meno del nome, gli attributi, il modo."""
    m = dict((J.get("materials") or [])[p["material"]]) if "material" in p else {}
    m.pop("name", None)
    return json.dumps([m, sorted(p["attributes"]), p.get("mode", 4)], sort_keys=True)


def _nome_comune(nomi, mesh):
    """Il nome del materiale unito: la parte finale comune ("front interno",
    "back interno" -> "interno"), o il nome della mesh."""
    parole = [n.split() for n in nomi]
    comune = []
    for gruppo in zip(*[list(reversed(w)) for w in parole]):
        if len(set(gruppo)) != 1:
            break
        comune.insert(0, gruppo[0])
    return " ".join(comune) or mesh


def unisci(J, B):
    """`(J, B)` con le primitive della stessa mesh e dello stesso materiale
    (a meno del nome) unite in una. L'astuccio scrive una primitiva per
    faccia, ognuna col suo materiale sulla stessa texture: in KeyShot e negli
    altri programmi erano tanti elementi, uno per faccia. Uniti, il pack e'
    un elemento solo: la stampa con la sua texture, e il rovescio e il
    taglio coi loro colori. I nomi delle facce restano negli `extras` della
    primitiva, `pack3d_facce`: [[nome, primo triangolo, quanti]], per il
    template (`template.triangoli`). Va dopo `separa`: ogni primitiva ha i
    suoi vertici, e unirle e' metterli in fila."""
    B = bytearray(B)
    materiali = J.get("materials") or []

    def aggiungi(arr, vecchio, target):
        arr = np.ascontiguousarray(arr)
        while len(B) % 4:
            B.append(0)
        J["bufferViews"].append({"buffer": 0, "byteOffset": len(B),
                                 "byteLength": arr.nbytes, "target": target})
        B.extend(arr.tobytes())
        acc = {"bufferView": len(J["bufferViews"]) - 1,
               "componentType": vecchio["componentType"],
               "count": int(arr.shape[0]), "type": vecchio["type"]}
        if vecchio.get("normalized"):
            acc["normalized"] = True
        if "min" in vecchio or "max" in vecchio:
            acc["min"] = arr.min(0).tolist()
            acc["max"] = arr.max(0).tolist()
        J["accessors"].append(acc)
        return len(J["accessors"]) - 1

    for me in J.get("meshes") or []:
        gruppi = {}
        for p in me.get("primitives") or []:
            if p.get("targets") or "indices" not in p:
                gruppi.setdefault(id(p), []).append(p)
                continue
            gruppi.setdefault(_chiave(J, p), []).append(p)
        nuove = []
        for gruppo in gruppi.values():
            if len(gruppo) == 1:
                nuove.append(gruppo[0])
                continue
            facce, dati, indici, n_vert, n_tri = [], {}, [], 0, 0
            for p in gruppo:
                ix = _dati(J, B, p["indices"]).astype(np.int64).ravel()
                nome = materiali[p["material"]].get("name", "") if "material" in p else ""
                for f in (p.get("extras") or {}).get("pack3d_facce") or [[nome, 0, len(ix) // 3]]:
                    facce.append([f[0], n_tri + int(f[1]), int(f[2])])
                indici.append(ix + n_vert)
                for k, i in p["attributes"].items():
                    dati.setdefault(k, []).append(_dati(J, B, i))
                n_vert += J["accessors"][p["attributes"]["POSITION"]]["count"]
                n_tri += len(ix) // 3
            primo = gruppo[0]
            nuova = {"attributes": {k: aggiungi(np.vstack(v), J["accessors"][primo["attributes"][k]],
                                                VERTICI) for k, v in dati.items()},
                     "indices": aggiungi(np.concatenate(indici).astype(np.uint32),
                                         {"componentType": 5125, "type": "SCALAR"}, INDICI),
                     "extras": dict(primo.get("extras") or {}, pack3d_facce=facce)}
            for k in ("material", "mode"):
                if k in primo:
                    nuova[k] = primo[k]
            if "material" in primo:
                materiali[primo["material"]]["name"] = _nome_comune(
                    [materiali[p["material"]].get("name", "") for p in gruppo],
                    me.get("name") or "mesh")
            nuove.append(nuova)
        me["primitives"] = nuove
    # via i materiali che nessuno usa piu'
    usati = sorted({p["material"] for me in J.get("meshes") or []
                    for p in me.get("primitives") or [] if "material" in p})
    if materiali and len(usati) < len(materiali):
        m = {k: n for n, k in enumerate(usati)}
        J["materials"] = [materiali[k] for k in usati]
        for me in J.get("meshes") or []:
            for p in me.get("primitives") or []:
                if "material" in p:
                    p["material"] = m[p["material"]]
    # e gli accessori, con le loro viste
    usati = sorted({v for me in J.get("meshes") or [] for p in me.get("primitives") or []
                    for v in list(p["attributes"].values()) + [p["indices"]]
                    + [x for t in p.get("targets") or [] for x in t.values()]})
    m = {k: n for n, k in enumerate(usati)}
    J["accessors"] = [J["accessors"][k] for k in usati]
    for me in J.get("meshes") or []:
        for p in me.get("primitives") or []:
            p["attributes"] = {k: m[v] for k, v in p["attributes"].items()}
            p["indices"] = m[p["indices"]]
            for t in p.get("targets") or []:
                for k in t:
                    t[k] = m[t[k]]
    return J, _ricompatta(J, B, [])


def per_tutti(glb):
    """Il GLB coi vertici separati per primitiva, le primitive dello stesso
    materiale unite (un elemento solo per mesh), i nomi dei materiali unici
    e una texture per immagine."""
    J, B = leggi(glb)
    nomi_unici(J)
    una_texture_per_immagine(J)
    J, B = separa(J, B)
    J, B = unisci(J, B)
    nomi_unici(J)
    return scrivi(J, B)


def rifinisci(percorso):
    """`per_tutti` sul file, al suo posto."""
    with open(percorso, "rb") as fh:
        glb = fh.read()
    with open(percorso, "wb") as fh:
        fh.write(per_tutti(glb))
