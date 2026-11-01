"""
La busta stand-up col soffietto: analisi e costruzione.
"""
from __future__ import annotations


from .. import artwork
from .. import exporters
from .. import folding
from .. import lettura as lettura_pdf
from .. import nero
from .. import pouch
from ..artwork import risoluzione
from ..dieline import Panel
from .comune import avviso_pagine, avviso_quadricromia, scrivi_lettura
from .flowpack import analisi_flowpack


def analisi_pouch(pdf):
    """Il pouch dallo steso: nastro, passo e saldature laterali le legge il
    lettore del flowpack, che ha lo stesso nastro; la struttura attraverso il
    nastro - piega in cima, pannelli, soffietto - `pack3d.pouch`."""
    try:
        _box, fp, _rip = analisi_flowpack(pdf)
    except Exception as e:
        raise ValueError("pouch: il nastro non si legge (%s)" % str(e)[:120])
    return pouch.leggi(pdf, fp)


def build_pouch(pdf, out_glb, quality="hd", lastre_extra=(),
                colata_riquadro=None):
    """La busta stand-up col soffietto: vedi `pack3d.pouch`.

    La texture e' lo steso intero, pulito come quello di un flowpack, e la
    maglia ne prende le posizioni: fronte e retro dalla piega in giu', la base
    dal corpo del soffietto. Il fronte lo decide la grafica.
    """
    dpi, tmax = risoluzione(quality)
    pdf, n_pagine = artwork.pagina_unica(pdf)
    pu = analisi_pouch(pdf)
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, pu.foglio, "Pouch letto cosi'", pouch.dichiara(pu)))
    conti = {}
    clean, lastre = artwork.senza_coperture(pdf, extra=lastre_extra,
                                            regione=pu.foglio, conti=conti)
    deciso_nero = nero.spia(clean, 0, dpi / 72.0)
    avvisi = list(pu.avvisi)
    pagine = avviso_pagine(n_pagine)
    if pagine:
        avvisi.append(pagine)
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi.append(fuori)
    avvisi.extend(artwork.avvisi_gda(conti))
    rgb = avviso_quadricromia(clean, regione=pu.foglio)
    if rgb:
        avvisi.append(rgb)
    if lastre:
        avvisi.append("lastre tecniche e coperture tolte per nome: %s"
                      % ", ".join(lastre))
    sh = pu.foglio
    lato_pt = max(sh[2] - sh[0], sh[3] - sh[1])
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"film": Panel(sh[0], sh[1], sh[2], sh[3], "film")},
        dpi=dpi_tex, inset_px=0, clean=True, note=avvisi,
        nero_deciso=deciso_nero, colata_riquadro=colata_riquadro)["film"]
    fronte_b, perche = pouch.quale_fronte(pu, tex)
    avvisi.append(perche)
    V, UV, T = pouch.maglia(pu, fronte_b)
    exporters.write_glb_mesh(V, UV, T, tex, out_glb, tex_max=tmax)
    return pouch.dichiara(pu) + avvisi
