"""
I materiali POP, i materiali per il punto vendita: totem, e poi dondolini,
strip, vele, angolari, portaprezzi, sticker.

Si caricano da un'altra finestra di Glam Lab, «Crea materiali POP 3D da
PDF»: la stessa pagina dello Space con pop=1 nell'indirizzo, e le voci dei
materiali al posto di quelle dei pack (GLAM.md, sezione 10).

**Il POP sta qui, e solo qui** (regole/pop.md, *Il confine*). Le famiglie dei
pack - flowpack, astucci, vassoi... - non si toccano per un materiale POP, e
il POP non si tocca per un pack: una PR verso coda-settimana o e' POP o e' dei
pack, e `prove/confini.py` lo controlla. Le parti comuni leggono il POP da
questo pacchetto e non lo nominano: il registro delle famiglie
(`MATERIALI_POP`, `analisi`, `COSTRUZIONI`), i tipi dichiarati
(`NOMI_POP`), la coda e la routine (`sezione_glam`). Un materiale nuovo
entra qui, nella pagina (la sua voce) e in regole/pop.md.

Ci sono il totem e l'espositore, e lo Space li costruisce: `analisi` legge
il PDF (o i due PDF del totem, fronte e retro; o i PDF dei pezzi
dell'espositore, uno per pezzo) e `COSTRUZIONI` porta le loro costruzioni,
`espositore.monta`, `ripiani.monta` e `totem.monta`, nel registro delle
famiglie. Un PDF che non si legge si ferma col motivo, e il caso va in coda
col PDF (`server.caso_fermo`, CODA.md).
"""

# I materiali che la finestra POP dichiara, col loro nome a parole per la
# coda e per il controllo dell'AI (`famiglie.comune.NOMI_KIND` li prende da
# qui, e cosi' `KIND_NOTI` e i sinonimi).
# Il nome di un materiale non puo' essere un tipo o un sinonimo dei pack:
# «espositore», per i pack, vuol dire vassoio (`comune.SINONIMI_KIND`), e
# dichiararlo POP avrebbe cambiato strada ai pack. Per questo `espositore_pop`.
NOMI_POP = {
    "totem": "totem (materiale POP: espositore da terra, un pannello piatto o "
             "curvato in piedi sulla sua base, anche con i popup)",
    "espositore_pop": "espositore (materiale POP: una struttura da banco o da "
                      "terra coi ripiani o i vani dove stanno i prodotti)",
}
MATERIALI_POP = tuple(NOMI_POP)

def e_pop(kind):
    """Il tipo dichiarato e' un materiale POP."""
    return kind in NOMI_POP


def _analisi_espositore(pdfs):
    from . import espositore as E, fustella as F
    if len(pdfs) > 1:
        # un PDF per pezzo: l'espositore a ripiani (`ripiani`)
        from . import ripiani
        letti = ripiani.leggi(pdfs)
        return dict(kind="espositore_pop", title="Espositore POP",
                    meta=["espositore POP a ripiani da %d PDF: %s"
                          % (len(pdfs), ", ".join(sorted(letti)))])
    pdf = pdfs[0]
    tagli, pieghe = F.tratti(pdf, [])
    pezzi = F.pezzi(tagli, pieghe)
    ruoli = E.riconosci(pezzi, E.inchiostro(pdf, pezzi))
    mancano = [r for r in ("fianco_sx", "fianco_dx", "schiena") if r not in ruoli]
    if mancano:
        raise ValueError("espositore: nella fustella non trovo %s - il caso va "
                         "a chi corregge il codice, che parte dal tuo PDF"
                         % ", ".join(r.replace("_", " ") for r in mancano))
    m = E.misure(ruoli, E.SPESSORE)
    return dict(kind="espositore_pop", title="Espositore POP",
                meta=["espositore POP: %s" % ", ".join(
                          sorted(r.replace("_", " ") for r in ruoli)),
                      "corpo %.0f x %.0f mm, alto %.0f mm"
                      % (m["Wi"], m["D"], m["H"])])


def _analisi_totem(pdfs):
    import numpy as np
    from . import totem as T
    if len(pdfs) != 2:
        raise ValueError("totem: carica due PDF, il pannello del fronte e "
                         "quello del retro")
    meta = ["totem POP: due pannelli curvi, il retro girato di 180 gradi, "
            "sulla base ovale"]
    for nome, pdf in zip(("fronte", "retro"), pdfs):
        pann, popup = T.leggi(pdf)
        w, h = np.ptp(pann, axis=0)
        meta.append("%s: pannello %.0f x %.0f mm, %s" % (
            nome, w, h, "%d popup" % len(popup) if popup else "senza popup"))
    return dict(kind="totem", title="Totem POP", meta=meta)


def analisi(pdfs, kind):
    """La lettura di un materiale POP, dai suoi PDF: `{kind, title, meta}`
    come le famiglie dei pack. Un PDF che non si legge si ferma col motivo,
    e il caso va in coda col PDF."""
    if kind == "totem":
        return _analisi_totem(list(pdfs))
    if kind == "espositore_pop":
        return _analisi_espositore(list(pdfs))
    nome = NOMI_POP[kind].split(" (")[0]
    raise ValueError("%s: il codice non sa ancora costruirlo. Il caso va a chi "
                     "corregge il codice, che parte dal tuo PDF" % nome)


def _rifinito(prepara):
    """La costruzione di `prepara` col GLB rifatto da `primitive.rifinisci`,
    come quelle dei pack (`registro._vertici_separati`, che il POP non
    importa: il registro importa il POP): ogni primitiva coi suoi vertici,
    perche' KeyShot mostri la texture. Mai un errore."""
    import functools

    @functools.wraps(prepara)
    def prepara_e_rifinisci(r, info):
        costruisci = prepara(r, info)

        def costruisci_e_rifinisci(lastre, uscita):
            import os
            import traceback
            avvisi = costruisci(lastre, uscita)
            if os.path.exists(uscita):
                try:
                    from .. import primitive
                    primitive.rifinisci(uscita)
                except Exception:                   # noqa: BLE001
                    traceback.print_exc()
            return avvisi
        return costruisci_e_rifinisci
    return prepara_e_rifinisci


@_rifinito
def _costruisci_espositore(r, info):
    from . import espositore

    def costruisci(lastre, uscita):
        if len(r.pdfs) > 1:
            from . import ripiani
            avvisi, _m = ripiani.monta(r.pdfs, uscita)
        else:
            avvisi, _m = espositore.monta(r.pdfs[0], uscita)
        return list(avvisi)
    return costruisci


@_rifinito
def _costruisci_totem(r, info):
    from . import totem

    def costruisci(lastre, uscita):
        avvisi, _m = totem.monta(r.pdfs[0], r.pdfs[1], uscita)
        return list(avvisi)
    return costruisci


# Le costruzioni dei materiali POP, come `famiglie.registro.COSTRUZIONI`: per
# il materiale letto (`info["kind"]`) la funzione che prepara la costruzione,
# `costruisci(lastre, uscita)` che torna gli avvisi. Il registro le aggiunge
# alle sue.
COSTRUZIONI = {"espositore_pop": _costruisci_espositore,
               "totem": _costruisci_totem}


# Le finestre di Glam Lab dove arrivano i modelli: quella dei pack, e quella
# dei materiali POP (intestazione `X-Model-Section: pop`, GLAM.md, sezione 10)
SEZIONI_GLAM = {None: "Costruisci modello 3D da PDF",
                "pop": "Crea materiali POP 3D da PDF"}


def sezione_glam(kind):
    """La finestra di Glam del modello di questo tipo dichiarato: "pop" per
    un materiale POP, None per un pack."""
    return "pop" if e_pop(kind) else None
