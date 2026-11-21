"""I punteggi delle letture degli astucci del parco.

Per ogni caso cartotecnico del parco: la lettura che vince, nel verso che
sceglie la costruzione (`artwork.astuccio_sulla_grafica`), e su quel foglio
tutte le strade e tutte le letture (`pack3d.strade`, anche quando la lettura
per colore e' forte e la costruzione non le prova): la seconda lettura
plausibile che da' un astuccio diverso e il margine fra le due. Dice quanto
e' sicura la lettura giusta, e dove un cambio del punteggio la sposterebbe
(regole/astucci.md, *Le letture a punteggio*).

    python3 prove/punteggi.py CASI [--solo a,b] [--scrivi]

Con `--scrivi` li salva in CASI/parco/punteggi.json, nel repository privato
dei casi: commit e push li'. Esce con 1 se un caso ha un dubbio dichiarato.
"""
import argparse
import json
import os
import sys

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, QUI)

PUNTEGGI = os.path.join("parco", "punteggi.json")


def punteggio_del_caso(pdf):
    """Il punteggio di un PDF: un dict da salvare."""
    from pack3d import artwork, dieline as dl, strade
    pdf, _n = artwork.pagina_unica(pdf)
    try:
        scelto, d, giro, _avviso = artwork.astuccio_sulla_grafica(pdf, cartotecnico=True)
    except Exception as e:                          # noqa: BLE001
        return {"errore": str(e)[:300]}
    if not d.panels:
        return {"errore": "nessun pannello"}
    es = strade.letture(scelto, 0, giro, True, tutte=True)
    valide = dl.plausibili(es.letture)
    vince = next((l for l in valide if dl.stesso_modello(l, es.migliore)
                  and l.strada == d.strada and l.correzioni == d.correzioni),
                 es.migliore)
    out = {"lettura": vince.descrivi() if vince else None,
           "strada": d.strada, "forma": d.forma, "correzioni": list(d.correzioni),
           "giro": giro, "costo": vince.costo if vince else None,
           "voci": dict(vince.voci) if vince else {},
           "letture": len(es.letture), "plausibili": len(valide),
           "dubbio": d.dubbio}
    if es.migliore is not None and vince is not None and not dl.stesso_modello(es.migliore, vince):
        # con tutte le strade vincerebbe un altro astuccio: la lettura per
        # colore e' forte e la costruzione non le prova, ma va saputo
        out["con_tutte"] = es.migliore.descrivi()
    altre = [l for l in valide if vince is not None and not dl.stesso_modello(l, vince)]
    if altre:
        seconda = min(altre, key=lambda l: l.costo)
        out.update(seconda=seconda.descrivi(), costo_seconda=seconda.costo,
                   margine=round(seconda.costo - vince.costo, 3))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("casi")
    ap.add_argument("--solo", type=lambda s: [x for x in s.split(",") if x])
    ap.add_argument("--scrivi", action="store_true")
    a = ap.parse_args(argv)
    with open(os.path.join(a.casi, "parco", "parco.json"), encoding="utf-8") as fh:
        manifesto = json.load(fh)
    tutti, dubbi = {}, 0
    for caso in manifesto["casi"]:
        if (caso.get("opzioni") or {}).get("kind") != "carton":
            continue
        if a.solo and caso["nome"] not in a.solo:
            continue
        pdf = os.path.join(a.casi, "parco", "pdf", caso["file"][0])
        p = punteggio_del_caso(pdf)
        tutti[caso["nome"]] = p
        dubbi += bool(p.get("dubbio"))
        if "errore" in p:
            riga = "non e' un astuccio: %s" % p["errore"][:90]
        else:
            riga = "%s costo %.2f%s%s" % (
                p["lettura"][:70], p["costo"],
                (", margine %.2f su %s" % (p["margine"], p["seconda"][:40]))
                if "margine" in p else ", nessuna seconda",
                ("  " + p["dubbio"][:80]) if p["dubbio"] else "")
            if p.get("con_tutte"):
                riga += "  CON TUTTE LE STRADE: %s" % p["con_tutte"][:80]
        print("%-34s %s" % (caso["nome"][:34], riga))
    if a.scrivi:
        f = os.path.join(a.casi, PUNTEGGI)
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(tutti, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        print("punteggi scritti per %d casi in %s: commit e push nel registro"
              % (len(tutti), PUNTEGGI))
    return 1 if dubbi else 0


if __name__ == "__main__":
    sys.exit(main())
