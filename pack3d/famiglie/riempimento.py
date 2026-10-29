"""
Il riempimento: un contenitore coi suoi pack dentro.
"""
from __future__ import annotations

import os
import tempfile

from .. import atlante
from .. import lettura as lettura_pdf
from .. import stato
from .astuccio import build_carton
from .comune import normalizza_kind, scrivi_lettura
from .flowpack import build_flowpack
from .vassoio import build_vassoio


# Che cosa va nel vassoio: il flowpack, o l'astuccio - un cartotecnico di un
# pezzo solo. Lo dichiara chi carica, come la famiglia.
CU_RIEMPIMENTO = ("flowpack", "carton")


def cu_riempimento(valore):
    """Il pack (CU) del riempimento: 'flowpack' di serie, o 'carton'."""
    v = normalizza_kind(valore or "flowpack")
    if v not in CU_RIEMPIMENTO:
        raise ValueError("Riempimento: il pack (CU) e' un flowpack o un astuccio")
    return v


def analisi_riempimento(pdfs, cu="flowpack"):
    """Il riempimento: un vassoio espositore - o un display - e il pack che ci
    va dentro, in due PDF in qualsiasi ordine. Il vassoio e' quello dei due
    che si legge come vassoio; l'altro si legge come `cu`, flowpack o
    astuccio. Vedi `pack3d.riempimento`."""
    # il registro usa il riempimento: analyze_pdf si importa qui, non in testa
    from .registro import analyze_pdf
    if len(pdfs) != 2:
        raise ValueError("riempimento: carica due PDF, il vassoio e il pack (CU)")
    letti = []
    for p in pdfs:
        try:
            letti.append(analyze_pdf(p, "vassoio"))
        except Exception:
            letti.append(None)
    vassoi = [k for k, l in enumerate(letti) if l is not None]
    if len(vassoi) == 2:
        # Il vassoio sagomato si prova per ultimo, quando gli altri hanno
        # rifiutato (`vassoio.riconosci_sagomato`): se l'altro PDF si legge
        # come vassoio prima di lui, il vassoio e' quello, e il sagomato e' il
        # pack. Il film del flowpack del display da 26 ha un fondo chiuso da
        # quattro coppie di righe e si leggeva come vassoio sagomato: il
        # riempimento, che si costruiva, si fermava su «tutti e due».
        forti = [k for k in vassoi if not letti[k].get("sagomato")]
        if len(forti) == 1:
            vassoi = forti
    if len(vassoi) != 1:
        raise ValueError("riempimento: dei due PDF %s" % (
            "nessuno si legge come vassoio espositore" if not vassoi else
            "tutti e due si leggono come vassoi: l'altro deve essere il pack (CU)"))
    iv = vassoi[0]
    ifp = 1 - iv
    nome_cu = "astuccio" if cu == "carton" else "flowpack"
    # l'astuccio con le sue domande: l'apertura a strappo, se c'e'
    fp = analyze_pdf(pdfs[ifp], cu, domande=(cu == "carton"))
    meta = (["riempimento: il vassoio e' il PDF %d, %s il PDF %d"
             % (iv + 1, "l'astuccio" if cu == "carton" else "il flowpack", ifp + 1)]
            + ["vassoio: %s" % m for m in letti[iv].get("meta", [])[:3]]
            + ["%s: %s" % (nome_cu, m) for m in fp.get("meta", [])[:3]])
    out = dict(kind="riempimento", cu=cu,
               title="Riempimento: %s coi suoi %s"
               % (letti[iv].get("title") or "vassoio",
                  "astucci" if cu == "carton" else "flowpack"),
               meta=meta, vassoio=iv, flowpack=ifp,
               teeth_default=fp.get("teeth_default", 20),
               soft_default=fp.get("soft_default", "medio"))
    if cu == "carton" and fp.get("strappo"):
        out["strappo"] = fp["strappo"]
    return out


def quanti_pezzi(valore):
    """Quanti pezzi nel vassoio: un intero da 1, o None per pieno."""
    if valore in (None, "", 0, "0", "pieno"):
        return None
    try:
        n = int(valore)
    except (TypeError, ValueError):
        raise ValueError("Quanti flowpack nel vassoio va digitato come numero intero")
    if n < 1 or n > 2000:
        raise ValueError("Quanti flowpack nel vassoio: da 1 a 2000")
    return n


def per_fila_scelti(valore):
    """Quanti pezzi affiancati per fila nel largo del vassoio, se chi l'ha
    caricato lo dice, o None: allora quanti ce ne stanno. Il pack non si
    allarga per riempire il posto (`riempimento._per_fila`)."""
    if valore in (None, "", 0, "0"):
        return None
    try:
        n = int(valore)
    except (TypeError, ValueError):
        raise ValueError("Pezzi per fila va digitato come numero intero")
    if n < 1 or n > 200:
        raise ValueError("Pezzi per fila: da 1 a 200")
    return n


def build_riempimento(pdfs, info, out_glb, quanti, flowpack=None, quality="hd",
                      carta=None, incisioni=True, per_fila=None):
    """Il vassoio pieno: il vassoio e il pack costruiti ognuno dalla sua
    famiglia, poi `quanti` pezzi messi nel vano (None: pieno). Il flowpack
    con `flowpack`, gli argomenti di `build_flowpack` dopo il PDF e il file
    d'uscita; l'astuccio (`info["cu"] == "carton"`) chiuso, con lo spessore
    `carta` e la fustella dell'apertura a strappo se `incisioni`."""
    from pack3d import riempimento
    astuccio = info.get("cu") == "carton"
    with tempfile.TemporaryDirectory(dir=stato.cartella()) as td:
        gv = os.path.join(td, "vassoio.glb")
        gf = os.path.join(td, "pack.glb")
        av_v = build_vassoio(pdfs[info["vassoio"]], gv, quality)
        if astuccio:
            av_f = build_carton(pdfs[info["flowpack"]], gf, quality, carta=carta,
                                incisioni=incisioni)
        else:
            # al rigonfiamento scelto, come da solo: piu' gonfio la sezione si
            # allarga a perimetro costante e la grafica del fronte si stira
            # (il T15 al livello 8: «il T1 non corrisponde al DT»)
            av_f = build_flowpack(pdfs[info["flowpack"]], gf, *flowpack)
        # la lettura del vassoio e quella del CU, una sotto l'altra, accanto
        # al GLB del riempimento

        def due_letture():
            letture = []
            for g in (gv, gf):
                if os.path.exists(g + lettura_pdf.ACCANTO):
                    with open(g + lettura_pdf.ACCANTO, "rb") as fh:
                        letture.append(fh.read())
            return lettura_pdf.accosta(*letture)
        scrivi_lettura(out_glb, due_letture)
        with open(gv, "rb") as fh:
            glb_v = fh.read()
        with open(gf, "rb") as fh:
            glb_f = fh.read()
    glb, righe = riempimento.componi(glb_v, glb_f, quanti, rigido=astuccio,
                                     per_fila=per_fila)
    # il vassoio e il pack in un'immagine sola: Glam ne mette una su tutto
    # il modello, e il template e' la sua tela (`pack3d.atlante`)
    glb, _zone = atlante.unisci(glb)
    with open(out_glb, "wb") as fh:
        fh.write(glb)
    return (righe + ["vassoio: %s" % a for a in av_v]
            + ["%s: %s" % ("astuccio" if astuccio else "flowpack", a) for a in av_f])
