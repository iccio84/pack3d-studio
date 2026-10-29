"""
L'incarto: la chiusura dichiarata, l'immagine del prodotto e la
costruzione.
"""
from __future__ import annotations

import traceback

from .. import artwork
from .. import exporters
from .. import folding
from .. import incarto
from .. import lettura as lettura_pdf
from .. import nero
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import avviso_pagine, avviso_quadricromia, scrivi_lettura


def build_incarto(pdf, out_glb, quality="hd", lastre_extra=(),
                  colata_riquadro=None):
    """L'incarto a triangolo: il film attorno alla barretta, chiuso sulle
    testate. Vedi `pack3d.incarto`. Come il tubo a cono: la texture e' il
    foglio intero, pulito, e ogni punto della barretta prende la grafica dal
    suo posto sul foglio."""
    dpi, tmax = risoluzione(quality)
    pdf, n_pagine = artwork.pagina_unica(pdf)
    p = incarto.riconosci(pdf)
    if p is None:
        raise ValueError("incarto a triangolo: il DT non si legge come il "
                         "foglio di una barretta incartata (cinque fasce fra "
                         "righe intere, testate dritte sulla faccia)")
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, p.regione, "Incarto letto cosi'", incarto.dichiara(p)))
    conti = {}
    clean, lastre = artwork.senza_coperture(pdf, extra=lastre_extra,
                                            regione=p.regione, conti=conti)
    deciso_nero = nero.spia(clean, 0, dpi / 72.0)
    avvisi = []
    pagine = avviso_pagine(n_pagine)
    if pagine:
        avvisi.append(pagine)
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi.append(fuori)
    avvisi.extend(artwork.avvisi_gda(conti))
    rgb = avviso_quadricromia(clean, regione=p.regione)
    if rgb:
        avvisi.append(rgb)
    if lastre:
        avvisi.append("lastre tecniche e coperture tolte per nome: %s"
                      % ", ".join(lastre))
    avvisi.extend(p.avvisi)
    m = 1.0 / PT2MM
    x0, y0, x1, y1 = p.regione
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    lato_pt = max(x1 - x0, y1 - y0)
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"dt": Panel(x0, y0, x1, y1, "dt")}, dpi=dpi_tex, inset_px=0,
        clean=True, note=avvisi, nero_deciso=deciso_nero,
        colata_riquadro=colata_riquadro)["dt"]
    scala = dpi_tex / 72.0
    origine = (round(x0 * scala) / scala * PT2MM, round(y0 * scala) / scala * PT2MM)
    V, UV, T = incarto.maglia(p, origine, scala / PT2MM, tex.size)
    exporters.write_glb_mesh(V, UV, T, tex.convert("RGB"), out_glb, tex_max=tmax)
    return incarto.dichiara(p) + avvisi


# Come si chiude l'incarto: "pieghe", il foglio attorno al prodotto e chiuso
# con le pieghe sulle testate (le barrette, `pack3d.incarto`); "avvolto", il
# foglio che avvolge tutto il prodotto (tipo l'ovetto), che il codice non sa
# ancora costruire. Senza dichiarazione, a pieghe: e' quello che c'e'.
CHIUSURE_INCARTO = {"pieghe": "pieghe", "a pieghe": "pieghe",
                    "piegato": "pieghe", "barretta": "pieghe",
                    "avvolto": "avvolto", "avviluppato": "avvolto",
                    "avvolgente": "avvolto", "ovetto": "avvolto"}


def chiusura_incarto(valore):
    """"pieghe" o "avvolto"; ValueError per tutto il resto."""
    if valore in (None, ""):
        return "pieghe"
    v = CHIUSURE_INCARTO.get(str(valore).strip().lower())
    if v is None:
        raise ValueError("La chiusura dell'incarto si dice con 'pieghe' (le "
                         "barrette) o 'avvolto' (tipo l'ovetto)")
    return v


def analisi_incarto_dichiarato(pdf, chiusura):
    """L'incarto dichiarato dalla pagina: a pieghe, il foglio della barretta
    (`_analisi_incarto`); avvolto, tipo l'ovetto, non ancora. Si ferma con
    l'errore che dice cosa manca, e il caso va in coda."""
    if chiusura == "avvolto":
        raise ValueError("incarto avvolto (tipo l'ovetto): il codice non sa "
                         "ancora costruirlo. Il caso va in coda col PDF e "
                         "l'immagine del prodotto")
    letto = _analisi_incarto(pdf)
    if letto is None:
        raise ValueError("incarto a pieghe: il DT non si legge come il foglio "
                         "di una barretta incartata (vuole cinque fasce fra "
                         "righe intere, la faccia in mezzo con le testate "
                         "dritte e i fianchi con le testate inclinate)")
    return letto


def _analisi_incarto(pdf):
    """I cartellini dell'incarto a triangolo, o None se non lo e': il film
    attorno a una barretta rigida, chiuso sulle testate (`pack3d.incarto`).
    Il flowpack non lo rifiuta, lo risolve male - le pinne seghettate al
    posto delle testate -: si prova prima, e su un flowpack esce subito
    (vuole cinque fasce fra righe intere e le testate dritte sulla faccia di
    mezzo)."""
    try:
        ic = incarto.riconosci(pdf)
    except Exception:
        traceback.print_exc()
        return None
    if ic is None:
        return None
    meta = incarto.dichiara(ic) + list(ic.avvisi)
    rgb = avviso_quadricromia(pdf, regione=ic.regione)
    if rgb:
        meta.insert(0, rgb)
    return dict(kind="incarto", title="Incarto a triangolo", meta=meta)
