"""
Memoria delle strutture apprese.

Ogni artwork gia' risolto viene archiviato con una *firma strutturale*: le
proporzioni relative della griglia di cordonature, indipendenti dalla scala.
Un nuovo PDF con firma simile eredita direttamente ruoli e quote, senza dover
ripassare dalle euristiche.
"""
from __future__ import annotations

import json
import os

STORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "knowledge", "templates.json")


def signature(d):
    """Firma invariante di scala: passi normalizzati di righe e colonne."""
    def norm(vals):
        span = vals[-1] - vals[0] or 1.0
        return [round((vals[i + 1] - vals[i]) / span, 4) for i in range(len(vals) - 1)]
    return {"kind": d.kind, "cols": norm(d.xs), "rows": norm(d.ys)}


def _load():
    if not os.path.exists(STORE):
        return []
    with open(STORE) as fh:
        return json.load(fh)


def _save(items):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    with open(STORE, "w") as fh:
        json.dump(items, fh, indent=2, ensure_ascii=False)


def remember(d, name, report):
    items = _load()
    items = [i for i in items if i["name"] != name]
    items.append({"name": name, "signature": signature(d), "report": report})
    _save(items)
    return len(items)


def _distance(a, b):
    if a["kind"] != b["kind"]:
        return 1e9
    if len(a["cols"]) != len(b["cols"]) or len(a["rows"]) != len(b["rows"]):
        return 1e9
    return (sum(abs(x - y) for x, y in zip(a["cols"], b["cols"])) +
            sum(abs(x - y) for x, y in zip(a["rows"], b["rows"])))


def recall(d, tol=0.06):
    """Il template noto piu' vicino, se abbastanza simile."""
    sig = signature(d)
    best, bd = None, 1e9
    for item in _load():
        dist = _distance(sig, item["signature"])
        if dist < bd:
            bd, best = dist, item
    return (best, bd) if best and bd <= tol else (None, bd)
