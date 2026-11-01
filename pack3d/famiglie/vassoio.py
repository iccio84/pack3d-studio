"""
Il vassoio espositore, la plancia e la scatola con la plancia.
"""
from __future__ import annotations


from .. import artwork
from .. import ballotin
from .. import exporters
from .. import folding
from .. import lettura as lettura_pdf
from .. import nero
from .. import plancia
from .. import quote as quotature
from .. import scatola_plancia
from .. import sportello
from .. import steso as lo_steso
from .. import vassoio
from .. import verifica
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import (TINTE_BALLOTIN,
    TINTE_VASSOIO,
    avviso_pagine,
    avviso_quadricromia,
    scrivi_lettura)


def build_vassoio(pdf, out_glb, quality="hd", lastre_extra=(),
                  colata_riquadro=None):
    """Costruisce un vassoio espositore: fondo e quattro pareti alzate.

    Un blocco unico, senza feritoie: le alette angolari stanno dentro lo
    spessore di fronte e retro, dove da fuori non si vedono, e le pareti
    arrivano agli spigoli (`vassoio.corpo`, e `verifica.blocco` lo controlla).
    """
    dpi, tmax = risoluzione(quality)
    # una pagina sola, e il nero sul file pulito: vedi `build_carton`
    pdf, n_pagine = artwork.pagina_unica(pdf)
    sorgente = pdf
    pdf, d, v, gradi, giro = vassoio.riconosci_sulla_tavola(pdf)
    if v is None:
        # Non e' un vassoio aperto, ma puo' essere la scatola chiusa che si
        # apre in espositore: stesso fondo, stesse pareti e un coperchio che
        # diventa la plancia. Vedi `pack3d.plancia`.
        pdf, d, p, gradi, giro = plancia.riconosci_sulla_tavola(sorgente)
        if p is not None:
            return build_plancia(sorgente, pdf, d, p, gradi, giro, out_glb,
                                 quality, lastre_extra, colata_riquadro,
                                 n_pagine)
        # o la scatola con la plancia ricavata DENTRO il coperchio, lo
        # sportello perforato che si alza sul retro: `pack3d.sportello`
        pdf, d, p, gradi, giro = sportello.riconosci_sulla_tavola(sorgente)
        if p is not None:
            return build_plancia(sorgente, pdf, d, p, gradi, giro, out_glb,
                                 quality, lastre_extra, colata_riquadro,
                                 n_pagine, forma=sportello)
        # lo sportello disegnato come fustella in CAD, a fessure e cerniera
        # tratteggiata, che `pack3d.sportello` sulla griglia non vede: vedi
        # `pack3d.scatola_plancia`
        sp = scatola_plancia.riconosci(sorgente)
        if sp is not None:
            return build_scatola_plancia(sorgente, sp, out_glb, quality,
                                         lastre_extra, colata_riquadro,
                                         n_pagine)
        # per ultimo il vassoio sagomato, le pareti con gli obliqui e gli
        # incavi: vedi `vassoio.riconosci_sagomato`
        pdf, d, v, gradi, giro = vassoio.riconosci_sulla_tavola(sorgente,
                                                                sagomato=True)
        if v is None:
            raise ValueError("non e' un vassoio: la griglia della fustella "
                             "non ha cinque colonne e tre fasce, e non e' un "
                             "display con plancia")
    # la lettura del PDF accanto al GLB (`pack3d.lettura`): mai un errore
    scrivi_lettura(out_glb, lambda: lettura_pdf.vassoio(pdf, v, gradi))
    colata_riquadro = artwork.riquadro_girato(sorgente, colata_riquadro, gradi)
    # La texture e' lo STESO INTERO, una sola, e le UV sono la posizione nel
    # piano: la piega sposta i vertici e la grafica se li porta dietro,
    # quindi non c'e' nessun ritaglio da ruotare. Il pannello unico serve
    # solo a far passare lo steso dalla pulizia di `texture_astuccio`.
    # La sagoma si prende a BASSA risoluzione e la texture alla sua: le UV
    # sono normalizzate, quindi le due cose non si parlano. Prendendo la
    # sagoma a 200 dpi il picco andava a 736 MB, cioe' fuori dal tetto, per
    # un contorno che a 4 px/mm e' gia' preciso al quarto di millimetro.
    px_mm = 4.0
    avvisi_sagoma = []
    sagoma, creste, _resa = vassoio.sagoma_e_creste(pdf, d, px_mm,
                                                    note=avvisi_sagoma, v=v)
    if sagoma is None:
        raise ValueError("vassoio: non si riconosce l'impronta della "
                         "cartotecnica sul foglio")
    pagina = Panel(0.0, 0.0, d.page_w, d.page_h, "steso")
    # Il dpi si abbassa fino a quello che la texture terra' davvero, come fa
    # il flowpack: rendere un foglio da 500 x 700 mm a 200 dpi sono 21
    # megapixel prodotti per buttarne i tre quarti nel ridimensionamento, e
    # il picco andava a 682 MB.
    lato = max(d.page_w, d.page_h)
    dpi_tex = min(dpi, tmax * 72.0 / lato) if lato > 0 else dpi
    # Le quote sono lette e la sagoma presa: fuori dalla fustella va via
    # tutto prima di rendere, e lo steso resta intero perche' le UV sono la
    # posizione nel piano.
    tex, avvisi_tex = artwork.texture_astuccio(pdf, {"steso": pagina}, dpi_tex,
                                               lastre_extra=lastre_extra,
                                               colata_riquadro=colata_riquadro,
                                               regione=d.bbox)
    # la coda va attaccata PRIMA della maglia: le UV dell'interno e del taglio
    # si misurano sull'altezza che la texture ha davvero, non su quella della
    # sagoma, che e' un'altra griglia
    steso = vassoio.con_coda(tex["steso"])
    parti = {}
    V, UV, T = vassoio.mesh(v, sagoma, px_mm, creste, alt_texture=steso.height,
                            parti=parti)
    avvisi_fronte = []
    if vassoio.testata_davanti(v) == "sud":
        # il davanti e' la testata bassa, e la maglia mette davanti la nord
        V = vassoio.gira(V)
        avvisi_fronte.append("il fronte e' la testata sud, piu' bassa della "
                             "nord (%.1f contro %.1f mm): vassoio girato perche' "
                             "guardi davanti" % (v.pareti["sud"], v.pareti["nord"]))
    # le due verifiche di sempre: le pareti sulle loro fasce del DT, con la
    # scala vera della texture, e il fronte sul fronte
    _ok, verifiche = verifica.vassoio(V, UV, T, parti, v, d, steso.size,
                                      dpi_tex / 25.4, vassoio.CODA)
    # e un blocco unico, senza feritoie fra le pareti e sul fondo
    verifiche += verifica.blocco(V, UV, T, parti, steso.size, vassoio.CODA)[1]
    riscontro = quotature.riscontro_vassoio(pdf, v, d)
    # La texture e' lo steso del PDF (`pack3d.steso`): senza la coda delle
    # tinte, che diventano colori pieni, sul riquadro del DT con un
    # millimetro attorno invece che sulla pagina, nel verso del PDF
    tela, UV, tinte = lo_steso.senza_strisce(tex["steso"].height, steso, UV, T,
                                             TINTE_VASSOIO)
    s_px, m_dt = dpi_tex / 72.0, 1.0 / PT2MM
    tela, UV = lo_steso.ritaglia(
        ((d.bbox[0] - m_dt) * s_px, (d.bbox[1] - m_dt) * s_px,
         (d.bbox[2] + m_dt) * s_px, (d.bbox[3] + m_dt) * s_px), tela, UV)
    tela, UV = lo_steso.nel_verso_del_pdf(gradi, tela, UV)
    # un blocco unico: un nodo solo, col suo nome
    exporters.write_glb_mesh(V, UV, T, tela, out_glb, tex_max=tmax,
                             parti=[("vassoio", 0, len(T))], tinte=tinte)
    meta = ["vassoio espositore",
            "base %.1f x %.1f mm, pareti %s mm"
            % (v.fondo_w, v.fondo_h,
               " / ".join("%s %.1f" % (k, a) for k, a in v.pareti.items())),
            "%d vertici sul profilo della fustella, cartoncino %.1f mm"
            % (len(V), vassoio.SPESSORE)]
    if giro:
        meta.append(giro)
    pagine = avviso_pagine(n_pagine)
    if pagine:
        meta.insert(0, pagine)
    return (meta + avvisi_sagoma + avvisi_tex + list(v.warnings) + avvisi_fronte
            + verifiche + ([riscontro] if riscontro else []))


def build_plancia(sorgente, pdf, d, p, gradi, giro, out_glb, quality="hd",
                  lastre_extra=(), colata_riquadro=None, n_pagine=1,
                  forma=plancia):
    """Il display con plancia APERTO a espositore: vedi `pack3d.plancia`.

    `forma` e' il modulo che legge i pezzi e li piega: `pack3d.plancia`, o
    `pack3d.sportello` per la plancia ricavata dentro il coperchio. La
    texture, i nodi e il GLB sono gli stessi.

    `pdf`, `d` e `p` sono gia' quelli di `plancia.riconosci_sulla_tavola`,
    nel verso in cui la griglia si legge; `sorgente` il file a pagina unica,
    per riportare la colata sul foglio girato.

    Come il vassoio: una texture sola - lo steso - e le UV sono la posizione
    sul foglio. Ma lo steso si rende sul solo riquadro della fustella, non
    sulla pagina intera: sul wafer T1 la pagina e' 940 x 800 mm e la fustella
    515 x 486, e con lo stesso lato massimo la texture tiene quasi il doppio
    dei punti per millimetro.
    """
    dpi, tmax = risoluzione(quality)
    # la lettura del PDF accanto al GLB (`pack3d.lettura`): mai un errore
    scrivi_lettura(out_glb, lambda: lettura_pdf.plancia(pdf, p, gradi))
    colata_riquadro = artwork.riquadro_girato(sorgente, colata_riquadro, gradi)
    px_mm = 4.0
    pz = forma.pezzi(pdf, p, d, px_mm)
    rx0, ry0, rx1, ry1 = pz.riquadro()
    # lo steso, la texture del GLB, e' il DT con un millimetro attorno: lo
    # stesso foglio, oltre i pezzi della maglia (`pack3d.steso`)
    m_dt = 1.0 / PT2MM
    dt = (min(rx0, d.bbox[0] - m_dt), min(ry0, d.bbox[1] - m_dt),
          max(rx1, d.bbox[2] + m_dt), max(ry1, d.bbox[3] + m_dt))
    lato = max(dt[2] - dt[0], dt[3] - dt[1])
    dpi_tex = min(dpi, tmax * 72.0 / lato) if lato > 0 else dpi
    esito = {}
    tex, avvisi_tex = artwork.texture_astuccio(
        pdf, {"steso": Panel(rx0, ry0, rx1, ry1, "steso")}, dpi_tex,
        lastre_extra=lastre_extra, colata_riquadro=colata_riquadro,
        regione=d.bbox, esito=esito, steso=dt)
    # la coda prima della maglia, come nel vassoio: le UV dell'interno e del
    # taglio si misurano sull'altezza che la texture ha davvero
    steso = vassoio.con_coda(tex["steso"])
    parti = {}
    V, UV, T = forma.mesh(p, pz, px_mm, alt_texture=steso.height,
                          parti=parti)
    verifiche, riscontro = [], None
    if forma is plancia:
        _ok, verifiche = verifica.plancia(V, UV, T, parti, p, pz, steso.size,
                                          dpi_tex / 25.4, vassoio.CODA)
        verifiche += verifica.blocco(V, UV, T, parti, steso.size,
                                     vassoio.CODA)[1]
        # e le misure del disegno contro le quote scritte: confermano, non
        # costruiscono
        riscontro = quotature.riscontro_plancia(pdf, p, d)
    # Il display e' un blocco unico e la plancia un elemento a se': due nodi
    # nel GLB, sugli stessi vertici e la stessa texture. La plancia e' stesa
    # per ultima, quindi i suoi triangoli stanno in fondo.
    inizio = min(a for k, (a, _b) in parti.items() if k.startswith("plancia"))
    # la texture e' lo steso del PDF, come nel vassoio: senza la coda, sul DT
    # intero e nel verso del PDF
    _tela, UV, tinte = lo_steso.senza_strisce(tex["steso"].height, steso, UV, T,
                                              TINTE_VASSOIO)
    tela, box = esito["steso"]
    sc = esito["scala"]
    UV = lo_steso.allarga(UV, tuple(round(c * sc) for c in (rx0, ry0, rx1, ry1)),
                          box)
    tela, UV = lo_steso.nel_verso_del_pdf(gradi, tela, UV)
    exporters.write_glb_mesh(V, UV, T, tela, out_glb, tex_max=tmax,
                             parti=[("display", 0, inizio),
                                    ("plancia", inizio, len(T))], tinte=tinte)
    meta = forma.dichiara(p) + [
        "%d vertici sui tratti della fustella, cartoncino %.1f mm"
        % (len(V), vassoio.SPESSORE)]
    if giro:
        meta.append(giro)
    pagine = avviso_pagine(n_pagine)
    if pagine:
        meta.insert(0, pagine)
    return (meta + avvisi_tex + verifiche
            + ([riscontro] if riscontro else []))


def build_scatola_plancia(pdf, p, out_glb, quality="hd", lastre_extra=(),
                          colata_riquadro=None, n_pagine=1, carta=None):
    """Il display a scatola: la scatola chiusa con la plancia alzata dal
    coperchio e la finestra da cui si vede il prodotto. Vedi
    `pack3d.scatola_plancia`.

    Come la scatola a punta: la texture e' il DT intero, pulito, e ogni pezzo
    della maglia prende la grafica dal suo posto sul foglio; sotto, le strisce
    del rovescio. Nel GLB la plancia e' un nodo a parte, come nel display con
    plancia: il riempimento misura il vano senza di lei."""
    dpi, tmax = risoluzione(quality)
    scrivi_lettura(out_glb, lambda: lettura_pdf.generica(
        pdf, p.regione, "Display a scatola letto cosi'", scatola_plancia.dichiara(p)))
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
    V, UV, T, inizio = scatola_plancia.maglia(p, origine, scala / PT2MM,
                                               tela.size, spessore=carta)
    tela, UV, tinte = lo_steso.senza_strisce(tex.height, tela, UV, T,
                                             TINTE_BALLOTIN)
    exporters.write_glb_mesh(V, UV, T, tela, out_glb, tex_max=tmax,
                             parti=[("display", 0, inizio),
                                    ("plancia", inizio, len(T))],
                             tinte=tinte)
    return scatola_plancia.dichiara(p) + avvisi
