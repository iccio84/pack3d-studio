"""
La scatola a punta.
"""
from __future__ import annotations


from .. import artwork
from .. import ballotin
from .. import exporters
from .. import folding
from .. import lettura as lettura_pdf
from .. import nero
from .. import punta
from .. import steso as lo_steso
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import TINTE_BALLOTIN, avviso_pagine, avviso_quadricromia, scrivi_lettura


def build_punta(pdf, out_glb, quality="hd", lastre_extra=(),
                colata_riquadro=None, carta=None):
    """La scatola a punta: fronte e retro chiusi in cima, fianchi a soffietto,
    l'aletta incollata sul retro. Vedi `pack3d.punta`.

    Come il ballotin: la texture e' il DT intero, pulito, e ogni pezzo della
    maglia prende la grafica dal suo posto sul foglio; sotto, le strisce del
    rovescio."""
    dpi, tmax = risoluzione(quality)
    pdf, n_pagine = artwork.pagina_unica(pdf)
    p = punta.riconosci(pdf)
    if p is None:
        raise ValueError("scatola a punta: la fustella non si legge come una "
                         "scatola a punta (fronte e retro chiusi in cima, "
                         "fianchi a soffietto)")
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, p.regione, "Scatola a punta letta cosi'", punta.dichiara(p)))
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
    tela = ballotin.con_interno(tex)
    V, UV, T = punta.maglia(p, origine, scala / PT2MM, tela.size,
                            spessore=carta)
    tela, UV, tinte = lo_steso.senza_strisce(tex.height, tela, UV, T,
                                             TINTE_BALLOTIN)
    exporters.write_glb_mesh(V, UV, T, tela, out_glb, tex_max=tmax, tinte=tinte)
    return punta.dichiara(p) + avvisi
