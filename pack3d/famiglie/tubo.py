"""
Il tubo, col gelato se l'utente lo chiede.
"""
from __future__ import annotations


from .. import artwork
from .. import exporters
from .. import folding
from .. import gelato
from .. import lettura as lettura_pdf
from .. import nero
from .. import steso as lo_steso
from .. import tubo
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import TINTE_TUBO, avviso_pagine, avviso_quadricromia, scrivi_lettura


# l'inizio della riga che dice il gelato (`gelato.aggiungi`), anche al controllo
GELATO = "con il gelato ("


def build_tubo(pdf, out_glb, quality="hd", lastre_extra=(),
               colata_riquadro=None, carta=None, gelato_gusto=None):
    """Il tubo a cono: lo steso a settore di corona arrotolato, aperto in
    cima, col fondo saldato piatto. Vedi `pack3d.tubo`. Con `gelato_gusto`,
    il ghiacciolo che esce dalla bocca (`pack3d.gelato`).

    Come la scatola a punta: la texture e' il DT intero, pulito, e ogni punto
    della maglia prende la grafica dal suo posto sul foglio; sotto, le
    strisce del rovescio."""
    dpi, tmax = risoluzione(quality)
    pdf, n_pagine = artwork.pagina_unica(pdf)
    p = tubo.riconosci(pdf)
    if p is None:
        raise ValueError("tubo a cono: la fustella non si legge come un "
                         "settore di corona (due archi e due lati verso il "
                         "loro centro)")
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, p.regione, "Tubo a cono letto cosi'", tubo.dichiara(p)))
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
    tela = tubo.tela(tex)
    V, UV, T = tubo.maglia(p, origine, scala / PT2MM, tela.size,
                           spessore=carta)
    tela, UV, tinte = lo_steso.senza_strisce(tex.height, tela, UV, T,
                                             TINTE_TUBO)
    exporters.write_glb_mesh(V, UV, T, tela, out_glb, tex_max=tmax, tinte=tinte)
    righe = tubo.dichiara(p)
    if gelato_gusto:
        sp = folding.SPESSORE_CRT if carta is None else carta
        righe.append(gelato.aggiungi(out_glb, p, sp, gelato_gusto))
    return righe + avvisi
