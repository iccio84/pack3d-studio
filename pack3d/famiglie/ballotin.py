"""
Il ballotin.
"""
from __future__ import annotations


from .. import artwork
from .. import ballotin
from .. import exporters
from .. import folding
from .. import lettura as lettura_pdf
from .. import nero
from .. import rilievo
from .. import steso as lo_steso
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import (SENZA_PELLICOLA,
    TINTE_BALLOTIN,
    avviso_pagine,
    avviso_quadricromia,
    pellicola_sicura,
    riga_pellicola,
    rilievo_sicuro,
    scrivi_lettura)


def build_ballotin(pdf, out_glb, quality="hd", lastre_extra=(),
                   colata_riquadro=None, carta=None, pellicola=None):
    """Il ballotin, la scatola a tronco di piramide: vedi `pack3d.ballotin`.

    La texture e' il DT intero, pulito come quello di un pouch, e ogni faccia
    della maglia prende la grafica dal suo posto sul DT: niente ritagli per
    pannello, perche' le lenti stanno a cavallo di due facce. Sotto la
    texture una striscia della tinta dell'interno, per il rovescio del
    cartoncino.

    Il rilievo dell'embossing, se il DT ne ha la lastra, sta in una mappa
    delle normali sulla stessa texture (`pack3d.rilievo`). Con `pellicola`
    le finestre hanno la loro pellicola trasparente: lo dice chi carica il
    PDF, vedi `pellicola_scelta`.
    """
    dpi, tmax = risoluzione(quality)
    pdf, n_pagine = artwork.pagina_unica(pdf)
    b = ballotin.riconosci(pdf)
    if b is None:
        raise ValueError("ballotin: la fustella non si legge come un ballotin "
                         "(fondo quadrato con quattro lenti agli spigoli)")
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, b.regione, "Ballotin letto cosi'", ballotin.dichiara(b)))
    conti = {}
    clean, lastre = artwork.senza_coperture(pdf, extra=lastre_extra,
                                            regione=b.regione, conti=conti)
    deciso_nero = nero.spia(clean, 0, dpi / 72.0)
    avvisi = []
    pagine = avviso_pagine(n_pagine)
    if pagine:
        avvisi.append(pagine)
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi.append(fuori)
    avvisi.extend(artwork.avvisi_gda(conti))
    rgb = avviso_quadricromia(clean, regione=b.regione)
    if rgb:
        avvisi.append(rgb)
    if lastre:
        avvisi.append("lastre tecniche e coperture tolte per nome: %s"
                      % ", ".join(lastre))
    # un millimetro di margine: i punti sul bordo del DT non leggono fuori
    m = 1.0 / PT2MM
    x0, y0, x1, y1 = b.regione
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    lato_pt = max(x1 - x0, y1 - y0)
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"dt": Panel(x0, y0, x1, y1, "dt")}, dpi=dpi_tex, inset_px=0,
        clean=True, note=avvisi, nero_deciso=deciso_nero,
        colata_riquadro=colata_riquadro)["dt"]
    # il ritaglio parte dal pixel arrotondato: l'origine si conta da li'
    scala = dpi_tex / 72.0
    origine = (round(x0 * scala) / scala * PT2MM, round(y0 * scala) / scala * PT2MM)
    tela = ballotin.con_interno(tex)
    V, UV, T = ballotin.maglia(b, origine, scala / PT2MM, tela.size,
                               spessore=carta)
    # il rilievo sulla stessa texture: il riquadro e' quello del ritaglio,
    # dal pixel arrotondato
    ox, oy = round(x0 * scala) / scala, round(y0 * scala) / scala
    normale, riga = rilievo_sicuro(
        rilievo.mappa_del_dt, pdf,
        (ox, oy, ox + tex.width / scala, oy + tex.height / scala),
        tela.size, tex.height, scala / PT2MM, coppia=True)
    if riga:
        avvisi.append(riga)
    film = None
    if pellicola and b.finestre:
        film = pellicola_sicura(ballotin.pellicola, b, spessore=carta)
        avvisi.append(riga_pellicola(len(b.finestre), film is not None,
                                     ballotin.PELLICOLA_MARGINE))
    elif pellicola is False and b.finestre:
        avvisi.append(SENZA_PELLICOLA)
    # la texture e' lo steso del PDF (`pack3d.steso`): le strisce del
    # rovescio e del taglio diventano colori pieni
    tela, UV, tinte, normale = lo_steso.senza_strisce(
        tex.height, tela, UV, T, TINTE_BALLOTIN, normale)
    exporters.write_glb_mesh(V, UV, T, tela, out_glb, tex_max=tmax,
                             normale=normale, pellicola=film, tinte=tinte)
    return ballotin.dichiara(b) + avvisi
