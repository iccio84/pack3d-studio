#!/usr/bin/env python3
"""
Backend locale di pack3d studio.

    python server.py            # poi apri http://localhost:8000

Solo libreria standard: serve l'interfaccia e due endpoint che girano la
pipeline `pack3d`. Il PDF arriva come corpo binario grezzo, non come
multipart: dentro un iframe la fetch viene inoltrata con postMessage e una
FormData non e' clonabile, mentre un ArrayBuffer lo e'.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from urllib.parse import quote
import tempfile
import time
import traceback
import threading
from collections import OrderedDict
from dataclasses import replace
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)      # il pacchetto pack3d/ sta accanto a questo file

try:
    import numpy as np
    from PIL import Image
except ImportError as e:                       # messaggio utile, non uno stack trace
    sys.exit("Manca una libreria (%s).\n"
             "Installa con:  pip install -r requirements.txt" % e.name)

from pack3d import (artwork, dieline as dl, folding, exporters, nero,
                    plancia, vassoio, verifica)
# le quote scritte sul file; `quote` qui e' gia' quella di urllib
from pack3d import quote as quotature
from pack3d import flowpack as fpk
from pack3d.dieline import Panel, PT2MM
from pack3d.flowpack import Flowpack, fin_on_surface
# La risoluzione della texture per qualita' - HD di serie, per tutte le
# famiglie - sta in `pack3d.artwork`, perche' la applichi anche la riga di
# comando: finche' stava qui, gli astucci fatti da li' uscivano a 2048 px.
from pack3d.artwork import qualita, risoluzione
from pack3d.exporters import _normals

# gonfiore: raccordo, esponente spigolo, grinza, pancia, rastremazione
# Il rigonfiamento e' una scala continua 1-10: rigido 1-3, medio 4-6,
# morbido 7-10. Le tre fasce restano come etichette per l'utente, ma i
# parametri si interpolano sul livello, cosi' "medio 4" e "medio 6" non sono
# la stessa cosa.
FASCE = {"rigido": 2, "medio": 5, "morbido": 8}
ANCORE = {   # livello -> raccordo, esponente, grinza, pancia, rastremazione
    1:  dict(soft_r=4.5, soft_n=2.0, wrinkle_mm=0.00, bulge=0.008, taper=6.0),
    5:  dict(soft_r=7.5, soft_n=2.4, wrinkle_mm=0.35, bulge=0.030, taper=16.0),
    10: dict(soft_r=11.0, soft_n=2.8, wrinkle_mm=0.75, bulge=0.060, taper=30.0),
}


def gonfiore(valore):
    """Parametri di forma per un livello 1-10, o per un'etichetta."""
    if isinstance(valore, str):
        v = FASCE.get(valore.strip().lower())
        if v is None:
            try:
                v = float(valore)
            except ValueError:
                v = 5
    else:
        v = float(valore)
    v = max(1.0, min(10.0, v))
    lo, hi = (1, 5) if v <= 5 else (5, 10)
    t = (v - lo) / (hi - lo)
    a, b = ANCORE[lo], ANCORE[hi]
    return {k: a[k] + (b[k] - a[k]) * t for k in a}


GONFIORE = {k: gonfiore(k) for k in FASCE}

# casi gia' calibrati: l'analizzatore automatico non copre ogni impaginato,
# quindi i flowpack risolti a mano restano disponibili tramite la firma della
# pagina (larghezza x altezza in punti, arrotondate).
CASI = {
    (1672, 737): dict(
        name="FULFIL Chocolate Hazelnut Whip",
        sheet=(481.78, 120.34, 481.78 + 142 / PT2MM, 120.34 + 141 / PT2MM),
        girth_span=(120.34 + 15 / PT2MM, 120.34 + 126 / PT2MM),
        W=36.0, T=19.5, L=116.0, end_fin=13.0, side_fin=15.0,
        back_a=18.0, back_b=18.0, web=141.0, step=142.0,
        fin_open=52.6, teeth=20, soft="morbido",
        drop_seps=["Coldseal", "White", "Stand Blau", "All",
                   "Label_ferrero", "Label_linked"],
    ),
}


def _sig(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        p = pdf.pages[0]
        return (int(p.width), int(p.height))


# Analisi gia' fatte: impronta del file -> (bbox, Flowpack, motivo del ripiego).
# Sono tre oggetti piccoli, non le rasterizzazioni: la memoria qui non pesa.
_ANALISI = OrderedDict()
_ANALISI_MAX = 8
_ANALISI_CHIAVE = threading.Lock()


def _impronta(pdf):
    """sha256 del file.

    Non `_sig`: quella e' la misura della pagina, e due artwork diversi dello
    stesso formato hanno la stessa firma. Per il registro dei casi calibrati,
    scritto a mano, puo' bastare; per una memoria automatica sarebbe il modo
    di costruire il pack sbagliato con le quote di un altro.
    """
    h = hashlib.sha256()
    with open(pdf, "rb") as fh:
        for blocco in iter(lambda: fh.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def analisi_flowpack(pdf):
    """Analisi automatica del flowpack, fatta una volta sola per file.

    L'interfaccia chiama /api/analyze per i cartellini e subito dopo
    /api/build: senza memoria la stessa analisi si rifaceva da capo, e non e'
    poco - sette secondi e mezzo di CPU e trecento MB, due volte. Su
    un'istanza piccola e' la differenza fra farcela e non farcela.
    """
    imp = _impronta(pdf)
    with _ANALISI_CHIAVE:
        if imp in _ANALISI:
            _ANALISI.move_to_end(imp)
            return _ANALISI[imp]
    # Si rasterizza QUI, una volta, alla risoluzione piu' alta che serva: da
    # qui in avanti find_blocks (100 dpi) e la texture riscalano quella invece
    # di rifarla. Senza, il primo che chiede e' find_blocks a 100 e l'analisi
    # deve comunque rifarla piu' grande.
    dl.render_page(pdf, 0, fpk.SCALA_ANALISI)

    box, _dt = printed_bbox(pdf)
    ripiego = None
    try:
        fp = fpk.analyze_auto(pdf, bbox=box)
    except Exception as e:
        # Secondo tentativo, sul RIQUADRO DELLA FUSTELLA invece che
        # sull'ingombro stampato. Non sono la stessa cosa: sul Kinder Choco
        # Fresh T1 la grafica scende sotto il tracciato - c'e' una striscia di
        # fondo bianco che il disegno non comprende - e misurando lo stampato
        # il nastro veniva 121 mm invece di 115. Con quel numero le fasce non
        # chiudono e il file non si costruisce; con la fustella si risolve.
        #
        # Si paga solo qui, cioe' solo sui file che altrimenti non uscirebbero
        # affatto: rileggere i tracciati sono otto secondi, e chi si risolve al
        # primo colpo non li paga. Vedi `fpk.riquadro_fustella`.
        primo = str(e)
        fp = ripiego = None
        try:
            riq = fpk.riquadro_fustella(pdf, stampato=box)
            if riq and riq != box:
                fp = fpk.analyze_auto(pdf, bbox=riq)
                fp.warnings.append(
                    "riquadro preso dalla fustella e non dallo stampato: "
                    "la grafica esce dal tracciato, e misurando lo stampato "
                    "le fasce non chiudevano")
        except Exception:
            fp = None
        if fp is None:
            # Terzo tentativo, sulle COPIE del DT: le copie tecniche e la
            # miniatura sono lo stesso disegno in scala, senza grafica sopra.
            # E' la regola "se non capisci le dimensioni prendi come
            # riferimento la miniatura". Vedi `tools.quote_dalla_copia`.
            try:
                from pack3d.tools import quote_dalla_copia
                fp = quote_dalla_copia(pdf)
            except Exception:
                fp = None
        if fp is None:
            # Il ripiego era muto, e un modello costruito da un'analisi
            # peggiore non esce sbagliato: esce plausibile, che e' peggio. E
            # guarda solo il DT con la grafica: sulla pagina intera misurava
            # anche quote, copie tecniche e cartiglio.
            fp = fpk.analyze(pdf, bbox=box)
            ripiego = primo
    with _ANALISI_CHIAVE:
        _ANALISI[imp] = (box, fp, ripiego)
        while len(_ANALISI) > _ANALISI_MAX:
            _ANALISI.popitem(last=False)
        return _ANALISI[imp]


# I versi gia' decisi: impronta del file -> (giro, avviso). Come _ANALISI:
# /api/analyze e /api/build chiedono lo stesso file, e la prova costa
# un'analisi.
_VERSO_FP = OrderedDict()


def flowpack_sulla_grafica(pdf):
    """`(pdf, giro, avviso, verso)`: lo steso di un flowpack nel verso della
    grafica, e i gradi orari di cui sul foglio tornato e' girato il testo del
    fronte - zero se si legge dritto o se il testo vivo non c'e'.

    E' `artwork.astuccio_sulla_grafica` per il flowpack, e per la stessa
    ragione: uno steso non deve dare un pack diverso secondo come sta sulla
    tavola. Il solutore gli 90 gradi li regge gia' - traspone i suoi ingressi
    e ritrova le pinne - ma la texture seguiva il FOGLIO: girato lo steso di
    mezzo giro, il Milch-Schnitte usciva a testa in giu', e sul KP T1
    Mandarino girato di un quarto la colata, che si allinea su un'onda
    orizzontale, si incollava storta e la fascia rossa spariva.

    Il verso lo da' il testo vivo del FRONTE (`fpk.fronte_in_pagina`): se e'
    girato, si gira la pagina (`artwork.pagina_girata`) e si rifa' l'analisi,
    e il giro vale solo se sul foglio girato lo steso si risolve senza ripiego
    e il fronte si legge dritto. Da li' in avanti tutto - colata, nero,
    testate, texture - lavora sullo steso com'e' negli originali del parco,
    che si leggono tutti col fronte dritto. Senza testo vivo sul fronte il
    verso non si conosce e il foglio resta com'e'.

    Un caso calibrato non passa di qui: le sue quote sono scritte a mano sul
    foglio com'e'.
    """
    from pack3d import tracciati
    imp = _impronta(pdf)
    with _ANALISI_CHIAVE:
        noto = _VERSO_FP.get(imp)
    if noto is None:
        giro, avviso, resta = 0, None, 0

        def verso(p):
            _box, fp, ripiego = analisi_flowpack(p)
            if ripiego is not None:
                return None
            return tracciati.verso_grafica(
                p, {"front": fpk.fronte_in_pagina(fp)}).get("front", -1)

        try:
            g = verso(pdf)
        except Exception:
            g = None
        if g == -1:
            # Detto, non taciuto: e' l'unico caso in cui il pack puo' ancora
            # dipendere da come lo steso sta sulla tavola.
            avviso = ("verso della grafica non letto: sul fronte non c'e' "
                      "testo vivo (scritte vettorializzate), e lo steso resta "
                      "com'e' sulla tavola - il verso va controllato sul "
                      "modello")
        elif g:
            girato = artwork.pagina_girata(pdf, (360 - g) % 360)
            try:
                dritto = girato != pdf and verso(girato) == 0
            except Exception:
                dritto = False
            if dritto:
                giro = (360 - g) % 360
                avviso = ("steso girato di %d gradi prima di risolvere: sulla "
                          "tavola la grafica del fronte era girata, e pinne, "
                          "retro e colata si leggono nel suo verso" % giro)
            else:
                resta = g
                avviso = ("la grafica del fronte e' girata di %d gradi sullo "
                          "steso, ma girato il foglio non si risolve col "
                          "fronte dritto: resta letto com'e' sulla tavola" % g)
        noto = (giro, avviso, resta)
        with _ANALISI_CHIAVE:
            _VERSO_FP[imp] = noto
            while len(_VERSO_FP) > _ANALISI_MAX:
                _VERSO_FP.popitem(last=False)
    giro, avviso, resta = noto
    return ((artwork.pagina_girata(pdf, giro) if giro else pdf), giro, avviso,
            resta)


# --------------------------------------------------------------------------- #
# costruzione
# --------------------------------------------------------------------------- #
def avviso_quadricromia(pdf, page_no=0, regione=None):
    """La riga sulla quadricromia, se il file ne ha bisogno.

    Costa una lettura di pypdf e una passeggiata nei dizionari delle risorse:
    centesimi di secondo e niente in memoria, misurati su tutto il parco.

    Con `regione` - il riquadro del DT - contano solo le immagini disegnate
    sul DT: fuori ci sono le note, e il logo RGB dello studio nel cartiglio
    non e' grafica del pack.
    """
    from pack3d import techink, tracciati
    try:
        import pypdf
        dentro = (None if regione is None else
                  tracciati.immagini_nel_riquadro(pdf, regione, page_no))
        return techink.avviso_rgb(pypdf.PdfReader(pdf).pages[page_no], dentro)
    except Exception:
        return None


def avviso_pagine(pdf):
    """La riga sulle pagine, se il file ne ha piu' di una.

    Si lavora sempre e solo sulla PRIMA pagina: un artwork su piu' pagine e'
    quasi sempre lo stesso pack ripetuto per lingua - sul Kinder Cards T2
    "64-GERMANY" e "01-ITALY", identici tranne il piede - e mescolarle vuol
    dire misurare un pack su una pagina e stamparne un altro. Lo si dice,
    perche' chi ha caricato il file sappia quale pagina e' diventata il
    modello. Le altre la costruzione non le vede proprio: vedi
    `artwork.pagina_unica`, che torna anche quante erano - ed e' quel numero
    che si passa qui, perche' la copia di pagine ne ha una.
    """
    if isinstance(pdf, int):
        n = pdf
    else:
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(pdf)
            try:
                n = len(doc)
            finally:
                doc.close()
        except Exception:
            return None
    if n <= 1:
        return None
    return ("il PDF ha %d pagine: si usa solo la prima, le altre di solito "
            "sono lo stesso pack in altre lingue" % n)


def build_carton(pdf, out_glb, quality="hd", lastre_extra=(),
                 colata_riquadro=None, carta=None):
    """L'astuccio. `carta` e' lo spessore del cartoncino in mm se l'utente
    l'ha dichiarato (`SPESSORI_CARTA`); senza, `folding.SPESSORE_CRT`."""
    dpi, tmax = risoluzione(quality)
    # L'ordine e' quello delle regole: una pagina sola, poi le quote lette
    # sul file intero - note e miniature comprese - poi via tutto quello che
    # sta fuori dal DT, e solo allora la costruzione. Il nero si decide sul
    # file pulito, dentro `texture_astuccio`: sugli Spaces la memoria per il
    # fork di Ghostscript c'e' (16 GB), e le scritte nere della legenda non
    # devono pesare sulla quota della `k`.
    pdf, n_pagine = artwork.pagina_unica(pdf)
    # sull'originale - il DT e' quello che misura - ma nel verso della
    # grafica: se il foglio sta girato sulla tavola, da qui in avanti si
    # lavora sulla copia girata. Vedi `artwork.astuccio_sulla_grafica`.
    sorgente = pdf
    pdf, d, gradi, giro = artwork.astuccio_sulla_grafica(pdf)
    colata_riquadro = artwork.riquadro_girato(sorgente, colata_riquadro, gradi)
    if not d.panels:
        raise ValueError("astuccio riconosciuto ma i pannelli non sono risolvibili")
    # Coperture via per nome e texture girate sul verso della grafica: sono
    # regole dell'artwork, e stanno in `pack3d.artwork` perche' le applichi
    # anche la riga di comando.
    esito = {}
    tex, avvisi_tex = artwork.texture_astuccio(pdf, d.panels, dpi,
                                              lastre_extra=lastre_extra,
                                              colata_riquadro=colata_riquadro,
                                              regione=d.bbox, esito=esito,
                                              dieline=d)
    faces = folding.build_faces(d.dims_mm, tex, layout=d.layout,
                                panels=d.panels, chiuso=d.chiuso,
                                spessore=(folding.SPESSORE_CRT if carta is None
                                          else carta),
                                fianchi_sul_fronte=d.fianchi_su == "front")
    # ogni faccia coi lati del suo pannello del DT, nessuna specchiata, il
    # fronte davanti: vedi `verifica.facce_astuccio`
    _ok, verifiche = verifica.facce_astuccio(faces, d.panels)
    # e le misure del disegno contro le quote che il file scrive, come per le
    # testate del flowpack: le quote non costruiscono, confermano
    riscontro = quotature.riscontro_astuccio(pdf, d)
    # il marchio orizzontale e dritto: se il fronte e' rimasto girato - la
    # texture non si poteva girare senza stirarla - si gira la scatola
    marchio = esito.get("marchio", 0)
    if marchio:
        folding.gira_facce(faces, marchio)
    exporters.write_glb(faces, out_glb, tex_max=tmax)
    meta = ["astuccio %s%s" % (d.layout, "" if d.chiuso else " aperto"),
            "%.1f x %.1f x %.1f mm" % d.dims_mm] + ([giro] if giro else [])
    if carta is not None:
        meta.append("cartoncino: %.2f mm - dichiarato" % carta)
    if marchio:
        meta.append("modello girato di %d gradi attorno al fronte perche' il "
                    "marchio si legga orizzontale e dritto: la sua grafica "
                    "sul foglio e' girata e il pannello non e' quadrato"
                    % marchio)
    rgb = avviso_quadricromia(esito.get("pdf", pdf), regione=d.bbox)
    if rgb:
        meta.insert(0, rgb)
    pagine = avviso_pagine(n_pagine)
    if pagine:
        meta.insert(0, pagine)
    return (meta + avvisi_tex + verifiche + ([riscontro] if riscontro else [])
            + [w for w in dl.check(d)])


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
        raise ValueError("non e' un vassoio: la griglia della fustella non ha "
                         "cinque colonne e tre fasce, e non e' un display con "
                         "plancia")
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
                                                    note=avvisi_sagoma)
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
    # un blocco unico: un nodo solo, col suo nome
    exporters.write_glb_mesh(V, UV, T, steso, out_glb, tex_max=tmax,
                             parti=[("vassoio", 0, len(T))])
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
                  lastre_extra=(), colata_riquadro=None, n_pagine=1):
    """Il display con plancia APERTO a espositore: vedi `pack3d.plancia`.

    `pdf`, `d` e `p` sono gia' quelli di `plancia.riconosci_sulla_tavola`,
    nel verso in cui la griglia si legge; `sorgente` il file a pagina unica,
    per riportare la colata sul foglio girato.

    Come il vassoio: una texture sola - lo steso - e le UV sono la posizione
    sul foglio. Ma lo steso si rende sul solo riquadro della fustella, non
    sulla pagina intera: sul Tronky la pagina e' 940 x 800 mm e la fustella
    515 x 486, e con lo stesso lato massimo la texture tiene quasi il doppio
    dei punti per millimetro.
    """
    dpi, tmax = risoluzione(quality)
    colata_riquadro = artwork.riquadro_girato(sorgente, colata_riquadro, gradi)
    px_mm = 4.0
    pz = plancia.pezzi(pdf, p, d, px_mm)
    rx0, ry0, rx1, ry1 = pz.riquadro()
    lato = max(rx1 - rx0, ry1 - ry0)
    dpi_tex = min(dpi, tmax * 72.0 / lato) if lato > 0 else dpi
    tex, avvisi_tex = artwork.texture_astuccio(
        pdf, {"steso": Panel(rx0, ry0, rx1, ry1, "steso")}, dpi_tex,
        lastre_extra=lastre_extra, colata_riquadro=colata_riquadro,
        regione=d.bbox)
    # la coda prima della maglia, come nel vassoio: le UV dell'interno e del
    # taglio si misurano sull'altezza che la texture ha davvero
    steso = vassoio.con_coda(tex["steso"])
    parti = {}
    V, UV, T = plancia.mesh(p, pz, px_mm, alt_texture=steso.height,
                            parti=parti)
    _ok, verifiche = verifica.plancia(V, UV, T, parti, p, pz, steso.size,
                                      dpi_tex / 25.4, vassoio.CODA)
    verifiche += verifica.blocco(V, UV, T, parti, steso.size, vassoio.CODA)[1]
    # e le misure del disegno contro le quote scritte: confermano, non
    # costruiscono
    riscontro = quotature.riscontro_plancia(pdf, p, d)
    # Il display e' un blocco unico e la plancia un elemento a se': due nodi
    # nel GLB, sugli stessi vertici e la stessa texture. La plancia e' stesa
    # per ultima, quindi i suoi triangoli stanno in fondo.
    inizio = min(a for k, (a, _b) in parti.items() if k.startswith("plancia"))
    exporters.write_glb_mesh(V, UV, T, steso, out_glb, tex_max=tmax,
                             parti=[("display", 0, inizio),
                                    ("plancia", inizio, len(T))])
    meta = plancia.dichiara(p) + [
        "%d vertici sui tratti della fustella, cartoncino %.1f mm"
        % (len(V), vassoio.SPESSORE)]
    if giro:
        meta.append(giro)
    pagine = avviso_pagine(n_pagine)
    if pagine:
        meta.insert(0, pagine)
    return (meta + avvisi_tex + verifiche
            + ([riscontro] if riscontro else []))


def _pezzi_tondi(pdfs, dichiarato="coppa"):
    """`{cosa: pdf}`: quale dei PDF e' quale pezzo, ognuno a pagina unica.

    I pack tondi arrivano in piu' file - la coppa con lo sleeve e il tappo, il
    cono con lo steso e il lid - e l'ordine in cui l'utente li carica non
    dice niente: lo dice la pagina. Lo sleeve della coppa ha lo steso a
    settore anulare, il tappo il corpo tondo disegnato in grande e in
    miniatura, il cono lo steso a settore pieno con l'apice sul foglio, il
    lid un disco. Il lid si cerca solo fra piu' PDF: un disco da solo non
    dice di essere un lid (`coppa.orienta`). Un pezzo puo' mancare; uno che
    non e' nessuno di questi e' un errore, e l'errore dice a chi ha
    dichiarato un cartotecnico in piu' pezzi che cosa il risolutore sa
    montare.
    """
    from pack3d import coppa as cp
    trovati = {}
    for k, pdf in enumerate(pdfs):
        pdf, _n = artwork.pagina_unica(pdf)
        # girato sulla tavola si legge girato: vedi `coppa.orienta`
        pdf, cosa, _gradi = cp.orienta(pdf, dischi=len(pdfs) > 1)
        if cosa is None:
            if dichiarato == "carton":
                raise ValueError(
                    "cartotecnico in %d pezzi: per ora so montare insieme lo "
                    "sleeve e il tappo di una coppa, o il cono col suo lid, e "
                    "il PDF %d non e' nessuno di questi" % (len(pdfs), k + 1))
            raise ValueError("coppa: un PDF non e' ne' lo sleeve (lo steso a "
                             "settore anulare) ne' il tappo (corpo tondo e "
                             "anello) di una coppa, ne' lo steso o il lid di "
                             "un cono")
        if cosa in trovati:
            raise ValueError("%s: due PDF dello stesso pezzo (%s) - servono %s"
                             % ("cartotecnico" if dichiarato == "carton"
                                else "coppa", cosa,
                                "lo sleeve e il tappo"
                                if cosa in ("coppa", "tappo")
                                else "il cono e il lid"))
        trovati[cosa] = pdf
    if {"coppa", "tappo"} & set(trovati) and {"cono", "lid"} & set(trovati):
        raise ValueError("i PDF sono pezzi di due pack diversi: %s"
                         % ", ".join(sorted(trovati)))
    return trovati


def _cono(pezzi):
    return "cono" in pezzi or "lid" in pezzi


def _in_pezzi(dichiarato, pdfs, cosa):
    """La riga d'apertura del cartotecnico dichiarato in pezzi."""
    return ("cartotecnico in %d %s: %s"
            % (len(pdfs), "pezzo" if len(pdfs) == 1 else "pezzi", cosa))


def analisi_coppa(pdfs, dichiarato="coppa"):
    """L'analisi della coppa o del cono: le misure, senza texture. Vedi
    `pack3d.coppa`."""
    from pack3d import coppa as cp
    pezzi = _pezzi_tondi(pdfs, dichiarato)
    if _cono(pezzi):
        return _analisi_cono(pezzi, pdfs, dichiarato)
    sleeve, tappo = pezzi.get("coppa"), pezzi.get("tappo")
    meta = []
    if sleeve:
        c = cp.leggi_coppa(sleeve)
        m = c.montata
        meta.append("coppa: alta %.1f mm, bocca %.1f, fondo %.1f, bordo "
                    "arrotolato %.1f, fondo rientrato %.1f"
                    % (m.altezza, 2 * m.r_bordo, 2 * m.r_fondo, m.ricciolo,
                       m.rientro))
        meta += cp.riscontri(c, cp.tracce(sleeve))
    if tappo:
        p = cp.leggi_tappo(tappo)
        meta.append("tappo: gonna di %.1f mm dentro, alta %.1f, piano "
                    "incassato di %.1f" % (2 * p.r_interno, p.altezza,
                                           p.z_piano))
    if sleeve and not tappo:
        meta.append("SENZA TAPPO: la coppa esce aperta - per chiuderla carica "
                    "insieme il PDF dello sleeve e quello del tappo")
    if tappo and not sleeve:
        meta.append("SOLO IL TAPPO: per la coppa intera carica insieme il PDF "
                    "dello sleeve e quello del tappo")
    titolo = ("Coppa col tappo" if sleeve and tappo
              else "Coppa senza tappo" if sleeve else "Tappo della coppa")
    if dichiarato == "carton":
        meta.insert(0, _in_pezzi(dichiarato, pdfs,
                                 "lo sleeve e il tappo di una coppa"
                                 if sleeve and tappo
                                 else "lo sleeve di una coppa" if sleeve
                                 else "il tappo di una coppa"))
    return dict(kind="coppa", title=titolo, meta=meta)


def _analisi_cono(pezzi, pdfs, dichiarato):
    from pack3d import coppa as cp
    cono, lid = pezzi.get("cono"), pezzi.get("lid")
    meta = []
    if cono:
        k = cp.leggi_cono(cp.tracce(cono))
        meta.append("cono: alto %.1f mm, bocca %.1f, punta %.1f, apre %.1f "
                    "gradi" % (k.altezza, 2 * k.r_bocca, 2 * k.r_punta,
                               2 * math.degrees(k.beta)))
        meta += k.note + cp.riscontri_cono(k)
    if lid:
        d = cp.leggi_disco(cp.tracce(lid))
        meta.append("lid: disco di %.1f mm al taglio" % (2 * d.r_taglio))
    if cono and not lid:
        meta.append("SENZA LID: il cono esce aperto - per chiuderlo carica "
                    "insieme il PDF del cono e quello del lid")
    if lid and not cono:
        meta.append("SOLO IL LID: per il cono intero carica insieme il PDF "
                    "del cono e quello del lid")
    titolo = ("Cono col lid" if cono and lid
              else "Cono senza lid" if cono else "Lid del cono")
    if dichiarato == "carton":
        meta.insert(0, _in_pezzi(dichiarato, pdfs,
                                 "il cono e il suo lid" if cono and lid
                                 else "il cono" if cono else "il lid di un "
                                                             "cono"))
    return dict(kind="coppa", title=titolo, meta=meta)


def in_piu_pezzi(kind, pdfs):
    """Vero se la richiesta va al risolutore dei pack in piu' PDF.

    La coppa lo e' sempre - lo sleeve e il tappo - e il cartotecnico quando
    l'utente ha dichiarato piu' di un pezzo: un PDF per pezzo. Oggi i pack
    in piu' pezzi che il risolutore sa montare sono la coppa col tappo e il
    cono col lid.
    """
    return kind == "coppa" or (kind == "carton" and len(pdfs) > 1)


def build_coppa(pdfs, out_glb, quality="hd", lastre_extra=(),
                dichiarato="coppa", carta=None):
    """La coppa di carta col tappo, o il cono col lid, da uno o due PDF: vedi
    `pack3d.coppa`.

    Una texture sola, un atlante con i ritagli dei due fogli; due nodi nel
    GLB, il contenitore e la chiusura, perche' la chiusura si toglie.
    """
    from pack3d import coppa as cp
    dpi, tmax = risoluzione(quality)
    pezzi = _pezzi_tondi(pdfs, dichiarato)
    if _cono(pezzi):
        cono, lid = pezzi.get("cono"), pezzi.get("lid")
        V, UV, T, A, parti, meta = cp.costruisci_cono(
            cono, lid, dpi=dpi, lastre_extra=lastre_extra, tex_max=tmax,
            carta=carta)
        titolo = ("cono col lid" if cono and lid
                  else "cono senza lid: carica anche il PDF del lid per "
                       "chiuderlo" if cono
                  else "solo il lid: carica anche il PDF del cono")
        nodi = "il cono e il lid sono due nodi del GLB"
    else:
        sleeve, tappo = pezzi.get("coppa"), pezzi.get("tappo")
        V, UV, T, A, parti, meta = cp.costruisci(sleeve, tappo, dpi=dpi,
                                                 lastre_extra=lastre_extra,
                                                 tex_max=tmax, carta=carta)
        titolo = ("coppa col tappo" if sleeve and tappo
                  else "coppa senza tappo: carica anche il PDF del tappo per "
                       "chiuderla" if sleeve
                  else "solo il tappo: carica anche il PDF dello sleeve")
        nodi = "la coppa e il tappo sono due nodi del GLB"
    exporters.write_glb_mesh(V, UV, T, A, out_glb, tex_max=tmax, parti=parti)
    if dichiarato == "carton":
        titolo = _in_pezzi(dichiarato, pdfs, titolo)
    return [titolo] + meta + ["%d vertici, %d triangoli; %s"
                              % (len(V), len(T), nodi)]


def _flowpack_from_case(case):
    return Flowpack(W=case["W"], T=case["T"], L=case["L"], end_fin=case["end_fin"],
                    side_fin=case["side_fin"], back_a=case["back_a"],
                    back_b=case["back_b"], web_mm=case["web"], step_mm=case["step"],
                    sheet=case["sheet"], girth_span=case["girth_span"])


def sezione_da_agente(params):
    """Larghezza e spessore del pack CHIUSO, se l'agente li ha misurati.

    Le cordonature dicono dove il film e' cordonato, non che forma prende una
    volta riempito: su Kinder Bueno T2 i pannelli danno 50 x 11, ma il pack in
    mano e' 41 x 20. Hanno lo stesso perimetro, quindi dalla fustella non si
    distinguono: il rapporto puo' arrivare solo da chi guarda il prodotto.
    """
    if not isinstance(params, dict):
        return None
    q = params.get("quote")
    if not isinstance(q, dict):
        return None
    try:
        w, t = float(q.get("larghezza")), float(q.get("spessore"))
    except (TypeError, ValueError):
        return None
    return (w, t) if w > 0 and t > 0 else None


def livello_da_agente(params):
    """Il livello 1-10 scelto dall'agente con "Scegli tu", se l'ha riportato."""
    if not isinstance(params, dict):
        return None
    pc = params.get("parametri_costruzione")
    try:
        return max(1.0, min(10.0, float(pc.get("rigonfiamento"))))
    except (AttributeError, TypeError, ValueError):
        return None


def pinne_da_agente(params):
    """Apertura delle pinne 1-3, se l'agente l'ha decisa."""
    if not isinstance(params, dict):
        return None
    pc = params.get("parametri_costruzione")
    try:
        return max(1.0, min(3.0, float(pc.get("apertura_pinne"))))
    except (AttributeError, TypeError, ValueError):
        return None


def _rss():
    """La memoria che il processo sta usando adesso, in MB. 0 se non si sa."""
    try:
        with open("/proc/self/statm") as fh:
            return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576.0
    except (OSError, IndexError, ValueError):
        return 0.0


def traccia(fase, da=None, dettaglio=""):
    """Una riga sul log: quanto e' durata la fase e a che memoria siamo.

    Serve quando la costruzione NON arriva in fondo. Se il processo muore -
    ucciso per memoria, o tagliato dalla piattaforma perche' ci mette troppo -
    la risposta non arriva e chi guarda vede un 502 senza niente dentro: non
    si sa nemmeno in quale pezzo e' morto. Le righe gia' stampate invece
    restano nel log del servizio, e dicono l'ultimo passo cominciato.

    E' la differenza che conta su un piano da 0,1 CPU, dove un file che qui
    costa 9 secondi di CPU la' ne prende 94 di orologio: senza traccia,
    memoria e tempo si distinguono solo a indovinare.

    Scrive su stderr perche' e' li' che finisce gia' `log_message`, e torna il
    tempo di adesso cosi' le fasi si incatenano senza contarlo due volte.
    """
    import resource
    ora = time.time()
    if da is not None:
        # DUE numeri, e servono tutti e due. `ru_maxrss` e' il massimo del
        # processo da quando e' partito e non scende mai: dopo tre costruzioni
        # dice 681 MB anche se nessuna singola ci e' arrivata vicino, quindi
        # da solo inganna. Quello che si sta usando ADESSO lo dice /proc, e in
        # coppia i due raccontano la cosa giusta: quanto pesa questa fase, e
        # quanto ha pesato il peggio fin qui.
        sys.stderr.write(
            "  [pack3d] %-22s %6.1f s  %5.0f MB ora, %5.0f max%s\n"
            % (fase, ora - da, _rss(),
               resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
               ("  " + dettaglio) if dettaglio else ""))
        sys.stderr.flush()
    return ora


def aree_da_agente(params):
    """Le lastre delle aree riservate che l'agente ha riconosciuto guardando.

    E' il caso dei file che l'area riservata non la dichiarano da nessuna
    parte - niente livello, niente nome di lastra, niente scritta sopra il
    riquadro - dove la lettura automatica non ha niente da leggere e l'unica
    cosa che resta e' guardare. L'agente indica il riquadro, `area_riservata`
    trova la lastra e gliela MOSTRA, e quello che passa di qui e' gia' stato
    confermato a occhio.

    Vuoto se non c'e' analisi allegata: allora il file resta come prima, che
    e' il comportamento di sempre, e il build lo dichiara.
    """
    if not isinstance(params, dict):
        return []
    pc = params.get("parametri_costruzione")
    voci = pc.get("aree_riservate") if isinstance(pc, dict) else None
    if not isinstance(voci, (list, tuple)):
        return []
    return [str(v).strip() for v in voci if str(v).strip()]


def colata_da_agente(params):
    """Il riquadro della colata che l'agente ha indicato guardando.

    Serve ai file che la colata non la mettono su un livello suo - sul parco
    di prova otto su nove - dove il codice non ha niente da misurare e
    l'ombra resta azzurra. L'agente indica la banda, `colata_a_occhio` gliela
    MOSTRA prima e dopo, e quello che passa di qui e' gia' stato confermato a
    occhio. Il livello, quando c'e', viene comunque prima.

    `None` se non c'e' analisi allegata, o se il riquadro non e' quattro
    numeri: un riquadro mezzo scritto e' peggio di nessun riquadro.
    """
    if not isinstance(params, dict):
        return None
    pc = params.get("parametri_costruzione")
    r = pc.get("colata") if isinstance(pc, dict) else None
    if not isinstance(r, dict):
        return None
    try:
        v = tuple(float(r[k]) for k in ("x_mm", "y_mm", "w_mm", "h_mm"))
    except (KeyError, TypeError, ValueError):
        return None
    return v if v[2] > 0 and v[3] > 0 else None


def scatola_da_agente(params):
    """Se il film avvolge un corpo rigido che arriva fino alla saldatura.

    Non e' la stessa cosa del rigonfiamento: un pack puo' essere teso sul
    prodotto senza contenere una scatola. Quello che cambia e' la pinna, e
    cambia per un motivo meccanico: le ganasce appiattiscono un tubo solo se
    dentro c'e' aria. Con una scatola dentro non c'e' niente da appiattire.
    """
    if not isinstance(params, dict):
        return False
    pc = params.get("parametri_costruzione")
    if not isinstance(pc, dict):
        return False
    return bool(pc.get("avvolge_scatola"))


def printed_bbox(pdf):
    """Riquadro del blocco stampato, in punti PDF.

    Senza questo si misura l'intera tavola, che contiene anche le viste
    tecniche e i cartigli: da li' escono pack larghi quanto il foglio.
    """
    try:
        from pack3d.tools import find_blocks
        b = [x for x in find_blocks(pdf)["blocchi"] if x["tipo"] == "stampato"]
        if not b:
            return None, None
        b = b[0]
        mm = 1.0 / PT2MM
        box = (b["x_mm"] * mm, b["y_mm"] * mm,
               (b["x_mm"] + b["w_mm"]) * mm, (b["y_mm"] + b["h_mm"]) * mm)
        return box, b.get("maschera_dt_x_mm")
    except Exception:
        return None, None


# Falde misurate sui pack che conosciamo, dal piu' piccolo al piu' grande:
#
#   Milch-Schnitte T1  nastro 144   falda 14,0
#   Kinder Country     nastro 122   falda 16,0
#   Kinder Paradiso    nastro 165   falda 12,5
#   K Brioss T10 Promo nastro 420   falda  4,1
#   FULFIL             nastro 141   falda 15,0
#
# Fra 4 e 16 mm, su nastri che vanno da 122 a 420. E' fisica, non statistica:
# la falda e' il lembo che schiacciano le ganasce, e le ganasce non diventano
# piu' grandi perche' il sacchetto lo e'. Il solutore invece accetta una falda
# fino al 25% del nastro, che su 420 mm vuol dire 105: un valore che non e'
# una falda, e' un quarto del film.
FALDA_VISTA_MAX = 16.0


def falda_sospetta(fp):
    """Avviso se la falda risolta non somiglia a nessuna falda mai misurata.

    Non rifiuta niente: una quota fuori scala puo' essere giusta su un pack
    che non abbiamo mai visto. Ma un modello costruito su una falda sbagliata
    esce plausibile invece che evidentemente rotto - il difetto che questo
    progetto ha gia' pagato tre volte - e allora almeno lo dice.
    """
    if fp.side_fin <= FALDA_VISTA_MAX * 1.5:
        return None
    return ("FALDA FUORI SCALA: %.1f mm, contro i %.0f mm della piu' grande "
            "mai misurata e %.1f di spessore del pack. Se il pack sembra "
            "troppo sottile e' questo: il solutore ha scelto le pieghe "
            "sbagliate, e nastro e passo restano giusti lo stesso."
            % (fp.side_fin, FALDA_VISTA_MAX, fp.T))


def build_flowpack(pdf, out_glb, teeth, soft, case=None, quality="hd",
                   sezione=None, scatola=False, pinne=None, lastre_extra=(),
                   colata_riquadro=None):
    """Costruisce il flowpack con le tecniche messe a punto sul campo.

    Quattro cose che la versione base non faceva, e che senza si vedono subito:

    1. Gonfiando, la sezione si arrotonda **a perimetro costante**: lo spessore
       cresce e la larghezza cala. Alzare solo lo spessore inventa film.
    2. La grafica si mappa **per pannello**, usando gli spigoli della sezione
       come nodi: con l'arco uniforme ogni fascia scivola.
    3. Le pinne portano la **zigrinatura** a triangoli equilateri, contata sul
       bordo della pinna.
    4. Le pinne non restano **mai a filo**: si aprono a farfalla verso la punta.
    """
    import math
    par = gonfiore(soft)
    nu, nv = (320, 420) if quality == "alta" else (190, 260)
    dpi, tmax = risoluzione(quality)
    # Una pagina sola: le altre sono lo stesso pack in altre lingue, e da qui
    # in avanti non le vede nessuno. Vedi `artwork.pagina_unica`.
    pdf, n_pagine = artwork.pagina_unica(pdf)
    conti = {}
    giro = None
    verso_fronte = 0
    if case:
        # anche qui le lastre dell'agente: un caso calibrato elenca a mano
        # quello che sapeva allora, non quello che si vede oggi guardando. E
        # anche qui i box area, che si tolgono su tutti i modelli: vedi
        # `artwork.senza_coperture`.
        fp0 = _flowpack_from_case(case)
        clean, lastre = artwork.senza_coperture(
            pdf, extra=lastre_extra, regione=fpk.foglio_in_pagina(fp0),
            conti=conti, fisse=case["drop_seps"])
        box = None
        ripiego = None
    else:
        # Nel verso della grafica: da qui in avanti `pdf` e' lo steso girato,
        # se sulla tavola stava girato, e con lui il riquadro della colata
        # che l'agente ha indicato guardando il foglio com'era. Vedi
        # `flowpack_sulla_grafica`.
        sorgente = pdf
        pdf, gradi, giro, verso_fronte = flowpack_sulla_grafica(pdf)
        colata_riquadro = artwork.riquadro_girato(sorgente, colata_riquadro,
                                                  gradi)
        # Stessa analisi di /api/analyze, non una seconda uguale: il ripiego
        # muto (che su Milch-Schnitte T1 dava corpo e pinne 136,5 e 8,0 invece
        # di 138,7 e 6,9, con la grafica che scivolava sul fronte) resta
        # dichiarato, perche' il motivo viaggia insieme alle quote.
        box, fp0, ripiego = analisi_flowpack(pdf)
        # L'analisi e' fatta, e con lei le quote: ora, e non prima, si tolgono
        # le lastre tecniche dichiarate per nome e TUTTO quello che sta fuori
        # dallo steso - quote, copie tecniche, legenda, cartiglio, miniature.
        # Servivano a leggere le misure; alla costruzione darebbero solo
        # penne tecniche contate male, un nero deciso sulle scritte della
        # legenda, una colata misurata sulla pastiglia del cartiglio.
        clean, lastre = artwork.senza_coperture(
            pdf, extra=lastre_extra, regione=fpk.foglio_in_pagina(fp0),
            conti=conti)
    # Il nero sul file pulito, prima di rendere: vedi `nero.spia`. Sugli
    # Spaces la memoria per il fork di Ghostscript c'e'.
    deciso_nero = nero.spia(clean, 0, dpi / 72.0)

    # NB: l'UnboundLocalError su 'avvisi' non nasceva qui. Nasceva in
    # do_POST, che quel nome lo assegnava solo sul ramo flowpack e lo
    # leggeva su tutti e due. Legare 'avvisi' dentro questa funzione non
    # tocca l'altra: sono due scope diversi, e qui il nome non si rilegge
    # mai. La correzione vera sta nel chiamante.
    avvisi_sez = []
    # l'analisi com'e' uscita dal DT, prima che la sezione dell'agente la
    # cambi: e' su questa che si controlla il fronte
    analisi = fp0 if case is None else None
    pagine = avviso_pagine(n_pagine)
    if pagine:
        avvisi_sez.append(pagine)
    if giro:
        avvisi_sez.append(giro)
    fuori = artwork.avviso_fuori_dt(conti)
    if fuori:
        avvisi_sez.append(fuori)
    avvisi_sez.extend(artwork.avvisi_gda(conti))
    rgb = avviso_quadricromia(clean, regione=fpk.foglio_in_pagina(fp0))
    if rgb:
        avvisi_sez.append(rgb)
    # Quello che l'analisi ha da dire - testate dal DT, steso ruotato,
    # rientri diversi - finiva nel Flowpack e da li' da nessuna parte.
    avvisi_sez.extend(fp0.warnings)
    if lastre:
        avvisi_sez.append("lastre tecniche e coperture tolte per nome: %s"
                          % ", ".join(lastre))
    sospetto = falda_sospetta(fp0)
    if sospetto:
        avvisi_sez.append(sospetto)
    if ripiego is not None:
        avvisi_sez.append("ANALISI AUTOMATICA FALLITA (%s): ripiego sul "
                          "solutore vecchio, quote e grafica da verificare"
                          % ripiego[:70])
    if sezione:
        # Dall'agente il RAPPORTO, dal film il PERIMETRO. Il perimetro la
        # fustella lo misura bene e non si tocca; e' il rapporto che non sa
        # dare, perche' 50 x 11 e 41 x 20 hanno lo stesso perimetro e la
        # differenza sta nel prodotto dentro, non nel disegno.
        w_a, t_a = sezione
        t_n = fp0.girth / (2.0 * (1.0 + w_a / t_a))
        w_n = fp0.girth / 2.0 - t_n
        avvisi_sez.append("sezione dall'analisi AI: %.1f x %.1f, riportata sul "
                          "perimetro del film come %.1f x %.1f"
                          % (w_a, t_a, w_n, t_n))
        # E la cucitura si sposta di meta' della differenza. Il film non si
        # allunga: dal centro del fronte alla cucitura ci sono gli stessi
        # millimetri di film comunque si riempia il pack, quindi se il fronte
        # chiuso e' piu' stretto della fascia del DT la cucitura sul retro si
        # avvicina allo spigolo di (W - W')/2 - 4,5 mm sul Bueno T2, 50 x 11
        # sulla fustella e 41 x 20 in mano. Tenendo fermo `back_a` i nodi del
        # giro sommavano a W + W' + 2T' invece che al perimetro, e il riscalo
        # che li riporta sul giro stirava la grafica fra un nodo e l'altro. Il
        # centro del fronte no: li' il riscalo compensa, e la verifica del
        # fronte lo dava gia' a posto anche prima.
        #
        # Su un tubo piatto a pinna la sezione il DT non la dice proprio: se
        # l'agente la da', il pack ha i suoi fianchi, e non e' piu' piatto.
        sposta = (fp0.W - w_n) / 2.0
        fp0 = replace(fp0, W=round(w_n, 2), T=round(t_n, 2),
                      back_a=round(max(fp0.back_a - sposta, 0.5), 2),
                      back_b=round(max(fp0.back_b - sposta, 0.5), 2),
                      piatto=False)

    # (1) la sezione si arrotonda a perimetro costante
    liv = FASCE.get(str(soft).strip().lower(), None)
    if liv is None:
        try:
            liv = float(soft)
        except (TypeError, ValueError):
            # "auto" o valore non riconosciuto: se l'agente ha gia' deciso usa
            # la sua scelta, altrimenti il centro scala
            liv = 5.0
    # Il rigonfiamento cambia la FORMA, non la taglia: il film che c'e' nello
    # steso e' quello, e gonfiare non ne aggiunge. Le due chiusure pero'
    # partono da forme diverse, e la scala vuol dire cose diverse: qui sotto
    # la pinna, in fondo la sovrapposizione.
    liv = max(1.0, min(10.0, liv))
    fp = fp0
    if fp0.tubo_piatto:
        # Un tubo piatto non ha un rapporto larghezza/spessore da tenere fermo:
        # gonfiandosi passa dalla lente al cerchio, e il cerchio e' il massimo
        # fisico - con quel film non si puo' essere piu' tondi. Il livello dice
        # quanto ci si avvicina, in frazione del diametro del cerchio.
        #
        # La scala e' tarata sul GLB di riferimento del K Tronky T1, che e'
        # l'unica misura che abbiamo per questa famiglia: sezione a ellisse di
        # rapporto 1,466 e bbox 26,7 x 18,2 su un giro di 71, cioe' 0,806 del
        # diametro del cerchio. Il livello 5 ci cade sopra.
        #
        # La scala e' volutamente STRETTA - da 1,85 di rapporto a 1,00 - e non
        # copre i wrap davvero piatti: allargarla vorrebbe dire inventare
        # numeri che nessun pack misurato conferma, e spostare il centro della
        # scala via dall'unico riferimento che c'e'. Il giorno che arriva un
        # pack piatto a sovrapposizione, si allarga con quello in mano.
        n_sez = SEZ_ELLISSE
        scala = 1.0
        pienezza = PILLOW_LENTE + (PILLOW_CERCHIO - PILLOW_LENTE) * (liv - 1) / 9.0
        # Lo spessore va messo DENTRO il Flowpack, non passato a parte: a
        # valle fp.T lo usano le nervature delle ganasce, l'apertura delle
        # pinne e i cartellini. Con T a zero la nervatura divide per la
        # protezione da zero e la mesh esplode - misurato: vertici a
        # cinque milioni di millimetri. La proprieta' `girth` non ne soffre,
        # perche' su un tubo piatto il giro lo da' il nastro, meno il lembo a
        # sovrapposizione o le due fasce della pinna.
        fp = replace(fp, T=round(pienezza * fp0.girth / math.pi, 2))
        avvisi_sez.append("tubo piatto gonfiato al %.0f%% del cerchio "
                          "(livello %g)" % (100.0 * pienezza, liv))
    else:
        # A pinna la sezione va dal rettangolo teso sul prodotto all'ellisse
        # piena d'aria, tenendo fermi il rapporto larghezza/spessore MISURATO
        # nello steso e il perimetro del film. La scala che serve a tornare sul
        # perimetro gonfia il pack in entrambe le direzioni.
        n_sez = SEZ_RETTANGOLO + (SEZ_ELLISSE - SEZ_RETTANGOLO) * (liv - 1) / 9.0
        scala = fpk.sezione_rigonfiata(fp, n_sez)
    if scatola:
        # Il riscalo a perimetro costante dice che una forma piu' tonda, con lo
        # stesso film, e' piu' grande: vale quando dentro c'e' aria. Con una
        # scatola la sezione la detta la scatola, e i pochi millimetri che la
        # superellisse taglia agli spigoli se li prende la piega, non il pack.
        # Senza questo il Brioss usciva 155,9 x 59,7 invece di 148,9 x 57,0.
        scala = 1.0
    # superellipse_section torna il SEMIASSE, non la larghezza come faceva
    # soft_section_fit: senza il raddoppio width_end esce doppio e le pinne si
    # aprono fino al perimetro intero invece che a meta'
    # Quanto misura la fustella oltre il corpo — 37,5 mm sul Brioss — non e'
    # tutto pinna. Prima il tubo deve collassare, e la gola piegata sullo
    # spigolo costa mezzo spessore; quello che avanza e' la pinna vera. Con una
    # scatola dentro il collasso non puo' mangiare il corpo, perche' la scatola
    # tiene la sezione fino alla sua faccia: la gola sta tutta oltre. Sul
    # Brioss: 37,6 = 22,8 di gola piu' 14,8 di pinna, vedi GOLA_SU_SPESSORE.
    # La somma L/2 + end_fin non cambia, quindi le UV restano quelle e la
    # grafica non si sposta di un pixel.
    #
    # Ma solo se la gola non la dice gia' il DT. Quando disegna la saldatura
    # E dove finisce il prodotto, la testata e' gia' divisa: la pinna finisce
    # alla saldatura, la gola sta fra lei e il prodotto, e il corpo la
    # comprende. Su K Colazione Piu' T10 le quote del file sono 20 | 37,5 |
    # 215 | 37,5 | 20: corpo 290 con la gola, pinna 20. Dividendo la pinna
    # un'altra volta ne restavano 2 mm, e il pack usciva una scatola senza
    # pinne con la grafica delle testate stirata di 2,07 volte.
    gola = 0.0
    if scatola and fp0.gola > 0:
        gola = fp0.gola
        avvisi_sez.append("oltre la scatola %.1f mm: %.1f di gola piu' %.1f di "
                          "pinna, come li disegna il DT"
                          % (fp0.gola + fp0.end_fin, gola, fp.end_fin))
    elif scatola:
        gola = min(GOLA_SU_SPESSORE * fp0.T, max(fp0.end_fin - 2.0, 0.0))
        fp = replace(fp, L=round(fp0.L + 2.0 * gola, 2),
                     end_fin=round(fp0.end_fin - gola, 2))
        avvisi_sez.append("oltre la scatola %.1f mm: %.1f di gola piu' %.1f di "
                          "pinna" % (fp0.end_fin, gola, fp.end_fin))

    Ps, d, semiasse = fpk.superellipse_section(fp, n_sez, thickness=scala * fp.T)
    sw = 2.0 * semiasse
    G = d[-1]
    # Quanto si apre la pinna, su una scala di tre.
    #
    # Un tubo si appiattisce perche' dentro c'e' aria, e appiattito misura meta'
    # perimetro: quello e' il massimo geometrico, oltre il quale il film
    # dovrebbe allungarsi. E' il caso di Milch-Schnitte, pinne aperte e piu'
    # alte del pack, ed e' il 3. All'altro capo, quando il film avvolge una
    # scatola che arriva fino alla saldatura, non c'e' niente da appiattire: la
    # pellicola si ripiega sugli spigoli e la pinna esce larga esattamente
    # quanto la faccia. E' Kinder Brioss, ed e' l'1. Il 2 sta in mezzo.
    #
    # Non e' deducibile dal rigonfiamento: dice come si comporta il film alle
    # ganasce, non che forma prende il corpo.
    ap = pinne if pinne is not None else (1.0 if scatola else 3.0)
    ap = max(1.0, min(3.0, float(ap)))
    fin_open = sw + (FIN_OPEN_RATIO * G / 2.0 - sw) * (ap - 1.0) / 2.0
    if ap < 3.0:
        avvisi_sez.append("apertura pinne %g/3: bordo %.1f mm contro i %.1f di "
                          "meta' perimetro" % (ap, fin_open, G / 2.0))
    if scatola and liv > 3:
        avvisi_sez.append("rigonfiamento %g su un pack che avvolge una "
                          "scatola: di norma e' 1" % liv)

    # Dove il tubo comincia a schiacciarsi. Con una scatola dentro lo decide
    # la gola; se no, prima il DT - la zona fra la saldatura e la fine del
    # prodotto, quando la segna uguale dai due lati - e solo dove tace la
    # regola di sempre, mai piu' corta della pinna.
    rastremo = gola if scatola else (fp0.gola or max(fp0.end_fin, 6.0))
    # E la spalla deve starci col film. Dalla sezione piena alla saldatura il
    # tubo cala di mezzo spessore, e il film, che non si allunga, quel calo lo
    # copre solo se la spalla e' abbastanza lunga: sul Paradiso la gola del
    # DT e' 10 mm e il calo 14,1, e dieci millimetri di film su una discesa
    # di quattordici sono una grafica stirata fino a 3,7 volte - la scritta
    # LATTE del bollino. Allora la spalla comincia prima, dentro il prodotto,
    # come fa un prodotto morbido che il film tira giu' sugli spigoli: la
    # saldatura resta dov'e' e con lei tutte le linee del DT. Con una scatola
    # no: li' la sezione la tiene la scatola fino alla sua faccia.
    calo = 0.5 * scala * fp.T * (1.0 - FLAT_END)
    spalla = rastremo
    # mai oltre meta' del mezzo corpo: una sezione piena deve restare
    voluta = min(SPALLA_SU_CALO * calo, fp.L / 4.0)
    if not scatola and voluta > rastremo + 0.5:
        spalla = round(voluta, 1)
        avvisi_sez.append("spalla di %.1f mm invece di %.1f: il tubo cala di "
                          "%.1f mm fino alla saldatura e il film, che non si "
                          "allunga, lo copre solo cosi'; la spalla comincia "
                          "%.1f mm dentro il prodotto"
                          % (spalla, rastremo, calo, spalla - rastremo))
    # (2) mappatura per pannello: gli spigoli della sezione fanno da nodi. Si
    # calcolano prima della mesh perche' servono anche a lei: nella gola e
    # nella pinna il giro si rimisura sul film, e il film lo dicono i nodi.
    knots = _panel_knots(Ps, d, G, fp0)
    V, UV, T = fpk.build_mesh(
        fp, nu=nu, nv=nv, sec_exp=n_sez, sec_thickness=scala * fp.T,
        width_end=fin_open / sw,
        taper=spalla, flat_end=FLAT_END, flare_pow=3.0, soft=True,
        serration=teeth > 0, serr_teeth=max(int(teeth), 1),
        fin_stations=36 if quality == "alta" else 26,
        bulge=par["bulge"], crimp_period=1.4, crimp_mm=0.32,
        wrinkle_mm=par["wrinkle_mm"], giro=_giro_film(knots, G, fp0),
        spalla_sul_film=True)

    if knots:
        ks, kf = knots
        # La regola dice di verificare il modello mappato contro l'AW con una
        # misura, fascia per fascia, prima di finalizzare. Qui si puo' fare da
        # soli: lo scarto fra dove cade lo spigolo sulla sezione e dove lo
        # vuole la fasciatura dello steso. Simmetrico e piccolo e' la
        # superellisse che taglia lo spigolo, ed e' fisiologico; sbilanciato o
        # grande vuol dire grafica che scivola attorno al tubo.
        # Due cose diverse dentro gli stessi numeri. Gli scarti a segni
        # alterni sono la superellisse che taglia gli spigoli: il film sopra
        # l'arrotondamento appartiene un po' al fianco e un po' al retro, e
        # l'interpolazione qui sotto lo sistema. Uno scarto tutto dallo stesso
        # lato invece e' una ROTAZIONE dell'origine, cioe' grafica che scivola
        # attorno al tubo, e l'interpolazione non la puo' correggere perche'
        # le sposta anche i riferimenti. La media distingue i due casi.
        scarti = [a - b for a, b in zip(ks, kf)]
        rotazione = abs(sum(scarti) / len(scarti))
        peggio = max(abs(s) for s in scarti)
        if rotazione > 0.01 * G:
            avvisi_sez.append("GRAFICA RUOTATA di %.1f mm sul giro di %.1f: "
                              "controlla la cucitura" % (rotazione, G))
        else:
            avvisi_sez.append("mappatura verificata: rotazione %.1f mm, spigoli "
                              "entro %.1f mm su un giro di %.1f"
                              % (rotazione, peggio, G))
        UV[:, 1] = np.interp(UV[:, 1] * G, ks, kf) / G
    UV = fpk.remap_to_sheet(UV, fp)
    # il film sulle testate: pinne e spalle non sono un piano, e la grafica ci
    # deve cadere come ci cade il film. Dopo i nodi e il riporto sullo steso,
    # perche' e' il film vero che si misura.
    dente = (fin_open / max(int(teeth), 1)) * math.sqrt(3.0) / 2.0 if teeth > 0 else 0.0
    avvisi_sez.append(verifica.testate_flowpack(V, UV, T, fp, spalla, dente,
                                                ap >= 3.0)[1])
    # PRIMA della mappatura: le UV sono il DT steso, e se le testate non
    # cadono sulle sue linee la grafica andra' fuori posto comunque la si
    # mappi. E le misure del disegno contro le quote che il file scrive.
    #
    # Anche per un caso tarato a mano: le sue misure sono state prese una
    # volta, su quel file, e il DT e' ancora li' per confermarle. Le linee
    # vengono dall'analisi del disegno; se il disegno non si legge - ed e'
    # spesso il motivo per cui un caso e' stato tarato - lo si dice.
    linee = fp0
    if case is not None:
        try:
            _box, linee, _rip = analisi_flowpack(pdf)
        except Exception:
            linee = None
    if linee is not None:
        avvisi_sez.append(verifica.uvw_flowpack(linee, fp, rastremo, scatola,
                                                spalla)[1])
    else:
        avvisi_sez.append("UVW contro il DT: il disegno di questo file non si "
                          "legge in automatico, le testate sono quelle del "
                          "caso tarato: da controllare sulla miniatura")
    riscontro = quotature.riscontro_testate(pdf, fp0.step_mm,
                                            fp0.end_fin, fp0.gola)
    if riscontro:
        avvisi_sez.append(riscontro)
    # e la miniatura, che e' il riscontro quando le quote sono in curve: sul
    # DT come l'ha letto l'analisi, non sulla sezione ritoccata dall'agente
    letto = analisi if case is None else linee
    miniatura = (quotature.riscontro_miniature(pdf, letto)
                 if letto is not None else None)
    if miniatura:
        avvisi_sez.append(miniatura)

    grid = V.reshape(-1, nv + 1, 3)
    # (4) le pinne restano saldate e piatte: nessuna manipolazione dei lembi.
    # Quello che le rende "aperte" e' che il loro bordo e' PIU' ALTO della
    # sezione del pack, e a questo pensa width_end.
    V = grid.reshape(-1, 3)

    if fp.pillow:
        # a sovrapposizione non c'e' niente da appoggiare sul retro: il lembo
        # sta SOTTO l'altro bordo, quindi non si vede e non si modella. Una
        # falda a spessore zero uscirebbe come una lamina degenere.
        Vm, UVm, Tm = V, UV, T
    else:
        V2, UV2, T2 = fin_on_surface(grid, fp, G, nv, gap=0.5, fade=10.0,
                                     u_tubo=UV.reshape(-1, nv + 1, 2)[:, :, 0])
        Vm = np.vstack([V, V2])
        UVm = np.vstack([UV, UV2])
        Tm = np.vstack([T, T2 + len(V)])
    if _normals(Vm, Tm)[int(np.argmax(Vm[:, 2]))][2] < 0:
        Tm = Tm[:, [0, 2, 1]]

    # lo steso analizzato trasposto si ritaglia dal rettangolo vero della
    # pagina, e la texture va poi rimessa nello stesso telaio della UV, con il
    # perimetro sulle righe
    sh = fpk.foglio_in_pagina(fp)
    # Rasterizzare piu' fine di quanto write_glb_mesh poi terra' vuol dire
    # produrre pixel per buttarli. Il dpi si abbassa fino a quello che serve
    # davvero, mai piu' in su di quello chiesto - quindi sui fogli che stanno
    # sotto il lato massimo, cioe' quasi tutti in HD, non cambia niente.
    lato_pt = max(sh[2] - sh[0], sh[3] - sh[1])
    dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
    tex = folding.rasterize_panels(
        clean, {"film": Panel(sh[0], sh[1], sh[2], sh[3], "film")},
        dpi=dpi_tex, inset_px=0, clean=True,
        note=avvisi_sez, nero_deciso=deciso_nero,
        colata_riquadro=colata_riquadro)["film"]
    foglio = tex
    if fp.ruotato:
        # rotazione, non trasposizione: trasporre e' una riflessione e
        # specchierebbe la grafica. Di 270 perche' e' il verso che lascia il
        # perimetro crescente come lo intende girth_span.
        tex = tex.transpose(Image.ROTATE_270)
    # DOPO la mappatura: il fronte dell'AW sul fronte del modello. Il fronte
    # e' quello del DT, cioe' dell'analisi: se l'agente ha cambiato la sezione
    # e' proprio lo spostamento che si vuole vedere.
    avvisi_sez.append(verifica.fronte_flowpack(
        V, UV, nv, analisi if analisi is not None else fp0,
        tex, foglio, dpi_tex / 72.0)[1])
    # Il modello finito si gira attorno alla normale del fronte perche' il
    # marchio si legga orizzontale e dritto: il tubo si costruisce coricato,
    # e su uno steso col testo attraverso il passo il pack sta in piedi.
    # Dopo le verifiche, che il giro attorno al fronte non tocca: il centro
    # del fronte resta al centro e la sua normale davanti.
    marchio = verifica.giro_del_marchio(
        V, UV, nv, analisi if analisi is not None else fp0, verso_fronte)
    if marchio:
        Vm = verifica.gira_attorno_al_fronte(Vm, marchio)
        avvisi_sez.append(
            "modello girato di %d gradi attorno al fronte perche' il marchio "
            "si legga orizzontale e dritto%s" % (
                marchio, ": il pack sta in piedi, con le pinne in alto e in "
                "basso" if marchio in (90, 270) else ""))
    exporters.write_glb_mesh(Vm, UVm, Tm, tex, out_glb, tex_max=tmax)

    base = fin_open / max(int(teeth), 1)
    if fp.pillow:
        sez = ("sezione a ellisse %.1f x %.1f (giro %.1f invariato, lembo "
               "coperto %.1f)" % (2.0 * semiasse, fp.T, G,
                                  fp.sovrapposizione))
    elif fp.piatto:
        sez = ("sezione a ellisse %.1f x %.1f (giro %.1f invariato, pinna "
               "%.1f sul retro)" % (2.0 * semiasse, fp.T, G, fp.side_fin))
    else:
        sez = ("sezione %.1f x %.1f (perimetro %.1f invariato)"
               % (scala * fp.W, scala * fp.T, G))
    return ["flowpack%s, rigonfiamento %s"
            % (" a sovrapposizione" if fp.pillow else
               " a tubo piatto" if fp.piatto else "", soft), sez,
            "corpo %.1f mm, pinne %.1f" % (fp0.L, fp.end_fin),
            ("pinne lisce" if teeth == 0 else
             "%d denti equilateri, base %.2f altezza %.2f mm"
             % (teeth, base, base * math.sqrt(3) / 2)),
            "mappatura per pannello" if knots else "mappatura per arco"] + avvisi_sez


def _giro_film(knots, G, fp):
    """Nodi e larghezze di fronte e retro, sul film, per `build_mesh`.

    Le larghezze vengono dai nodi stessi, che sono gia' riportati sul giro
    della sezione: prese dal Flowpack sarebbero in un'altra scala appena il
    perimetro della fasciatura non torna al decimo con quello della sezione.
    """
    if not knots:
        tot = fp.W + 2.0 * fp.T + fp.back_a + fp.back_b
        s = G / tot if tot > 0 else 1.0
        return None, None, fp.W * s, (fp.back_a + fp.back_b) * s
    ks, kf = knots
    if len(kf) == 4:        # tubo piatto: cucitura, piega, piega, cucitura
        return ks, kf, kf[2] - kf[1], kf[1] + (G - kf[2])
    return ks, kf, kf[3] - kf[2], kf[1] + (G - kf[4])


def _panel_knots(Ps, d, G, fp):
    """Spigoli della sezione, per far cadere ogni fascia sul suo pannello."""
    if fp.tubo_piatto:
        # Un'ellisse non ha spigoli, quindi la ricerca per curvatura qui sotto
        # non trova niente e la verifica non scattava: la grafica poteva
        # ruotare attorno al tubo senza che nessuno se ne accorgesse. I nodi
        # di un tubo piatto sono le due PIEGHE, cioe' gli estremi dell'asse
        # maggiore, e lo steso dice dove devono cadere: a back_a dalla
        # cucitura e a back_a + fronte.
        #
        # Nell'ordine in cui le incontra il film: prima la piega a +y, a
        # back_a dalla cucitura, poi l'altra mezzo giro dopo. Ordinarle per
        # valore sbagliava quando il retro sta tutto da un lato - Kinder Choco
        # Fresh - e la cucitura cade sulla seconda piega: quella veniva a
        # zero, prima dell'altra, e il fronte finiva sul retro.
        try:
            ia = int(np.argmax(Ps[:-1, 0]))
            ib = int(np.argmin(Ps[:-1, 0]))
            da, db = float(d[ia]), float(d[ib])
            if db <= da:
                db += G
            ks = [0.0, da, min(db, G), G]
            kf = [0.0, fp.back_a, fp.back_a + fp.W, fp.back_a + fp.W + fp.back_b]
            if kf[-1] <= 0:
                return None
            return ks, [x * G / kf[-1] for x in kf]
        except Exception:
            return None
    try:
        t = np.gradient(Ps, axis=0)
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        cr = np.abs(np.arctan2(t[:-1, 0] * t[1:, 1] - t[:-1, 1] * t[1:, 0],
                               (t[:-1] * t[1:]).sum(1))) / np.maximum(np.diff(d), 1e-9)
        hot = cr > cr.max() * 0.25
        groups, cur = [], []
        for i, h in enumerate(hot):
            if h:
                cur.append(i)
            elif cur:
                groups.append(cur); cur = []
        if cur:
            groups.append(cur)
        if len(groups) != 4:
            return None
        mid = sorted(float(np.average(d[g], weights=cr[g])) for g in groups)
        ks = [0.0] + mid + [G]
        kf = [0.0, fp.back_a, fp.back_a + fp.T, fp.back_a + fp.T + fp.W,
              fp.back_a + 2 * fp.T + fp.W, fp.back_a + 2 * fp.T + fp.W + fp.back_b]
        if kf[-1] <= 0:
            return None
        kf = [x * G / kf[-1] for x in kf]
        return ks, kf
    except Exception:
        return None


# Il viewer glamlab chiama questa API con le sue etichette: il suo
# BuildFromPdfPanel manda kind "cartotecnico", non "carton". Senza sinonimo
# quel valore non entrava in nessun ramo e ogni astuccio finiva dal solutore
# flowpack, che e' esattamente l'errore contro cui le regole mettono in
# guardia: la tipologia si dichiara, e se la dichiarazione non viene
# riconosciuta e' come non averla.
SINONIMI_KIND = {"cartotecnico": "carton", "astuccio": "carton",
                 "carton": "carton", "flowpack": "flowpack",
                 "vassoio": "vassoio", "espositore": "vassoio",
                 "display": "vassoio", "tray": "vassoio",
                 "coppa": "coppa", "coppa conica": "coppa", "cup": "coppa",
                 "bicchiere": "coppa", "sleeve": "coppa", "tappo": "coppa",
                 # il cono gelato col lid e' della stessa famiglia: pezzi
                 # tondi, uno steso a settore e una chiusura
                 "cono": "coppa", "cono gelato": "coppa", "cone": "coppa",
                 "lid": "coppa"}


def normalizza_kind(kind):
    if kind is None:
        return None
    return SINONIMI_KIND.get(str(kind).strip().lower(), kind)


KIND_NOTI = ("carton", "flowpack", "vassoio", "coppa")

# Lo spessore della carta che l'utente dichiara per un cartotecnico, da 1 a 3:
# 1 la carta dei coni gelato, poco piu' di un foglio; 2 il cartoncino degli
# astucci e delle coppe; 3 un cartoncino spesso. Senza dichiarazione ogni
# famiglia tiene il suo: 0,45 mm l'astuccio (`folding.SPESSORE_CRT`), 0,35 la
# coppa (dal cartiglio del Nutella POT), 0,10 il cono.
SPESSORI_CARTA = {1: 0.10, 2: 0.40, 3: 0.70}


def spessore_carta(valore):
    """Il livello dichiarato (1-3) in mm, None se non e' dichiarato.
    ValueError se non e' un livello."""
    if valore in (None, ""):
        return None
    try:
        return SPESSORI_CARTA[int(valore)]
    except (TypeError, ValueError, KeyError):
        raise ValueError("Lo spessore della carta va da 1 a 3: 1 carta (coni "
                         "gelato), 2 cartoncino (astucci e coppe), 3 "
                         "cartoncino spesso")


def analyze_pdf(pdf, kind=None):
    """`kind` arriva dall'utente: la tipologia si dichiara, non si indovina.
    Il riconoscimento automatico sbaglia (il solutore astuccio risolve anche
    certi flowpack) e sbagliare qui compromette tutto il resto.

    Tutte le famiglie si misurano sulla prima pagina sola: se ce ne sono
    altre, il primo cartellino lo dice. Vedi `avviso_pagine`."""
    pdf, n_pagine = artwork.pagina_unica(pdf)
    info = _analyze_pdf(pdf, kind)
    pagine = avviso_pagine(n_pagine)
    if pagine and isinstance(info.get("meta"), list):
        info["meta"].insert(0, pagine)
    return info


def _analyze_pdf(pdf, kind=None):
    kind = normalizza_kind(kind)
    if kind is not None and kind not in KIND_NOTI:
        # Cadere nel ramo flowpack e' peggio che fermarsi: e' lo stesso difetto
        # del sinonimo mancante, solo sull'altro capo. Su questo file - un
        # astuccio Nutella Donut - passando "auto" invece di niente il solutore
        # astuccio veniva saltato e usciva un flowpack.
        raise ValueError("tipologia '%s' non riconosciuta: dichiara %s"
                         % (kind, " o ".join("'%s'" % k for k in KIND_NOTI)))
    if kind == "coppa":
        return analisi_coppa([pdf])
    case = CASI.get(_sig(pdf))
    if case and kind in (None, "flowpack"):
        return dict(kind="flowpack", title=case["name"],
                    teeth_default=case["teeth"], soft_default=case["soft"],
                    meta=["caso calibrato: " + case["name"],
                          "nastro %.0f x passo %.0f mm" % (case["web"], case["step"])])
    if kind in (None, "carton", "vassoio"):
        grezza = None
        giro_v = None
        try:
            if kind == "vassoio":
                # dichiarato: vale la pena di provarlo anche di traverso,
                # vedi `vassoio.riconosci_sulla_tavola`. Senza dichiarazione
                # no: la prova la pagherebbe ogni astuccio e ogni flowpack.
                _p, grezza, v, _g, giro_v = vassoio.riconosci_sulla_tavola(pdf)
            else:
                grezza = dl.extract(pdf)
                v = vassoio.riconosci(grezza)
        except Exception:
            v = None
        finally:
            dl.scarta_resa()
        if v is None and kind in (None, "vassoio"):
            # Non e' un vassoio aperto: puo' essere il display con plancia, la
            # scatola chiusa che si apre in espositore (`pack3d.plancia`).
            # Dichiarato si prova anche di traverso, come il vassoio; senza
            # dichiarazione si guarda la griglia gia' letta, e non costa
            # niente. E' qui che il Tronky T48 smette di uscire flowpack.
            pl, giro_p = None, None
            try:
                if kind == "vassoio":
                    _p, _g, pl, _gr, giro_p = plancia.riconosci_sulla_tavola(pdf)
                elif grezza is not None:
                    pl = plancia.riconosci(grezza)
                    if pl is None:
                        # di traverso sulla tavola: la griglia trasposta lo
                        # dice senza rileggere il file, e la costruzione poi
                        # il foglio lo gira davvero
                        pl = plancia.di_traverso(grezza)
                        if pl is not None:
                            giro_p = ("foglio di traverso sulla tavola: la "
                                      "costruzione lo gira di un quarto")
            except Exception:
                pl = None
            finally:
                dl.scarta_resa()
            if pl is not None:
                return dict(kind="vassoio", title="Display con plancia",
                            meta=plancia.dichiara(pl)
                            + ([giro_p] if giro_p else []))
        if v is None and kind == "vassoio":
            # La dichiarazione deve valere anche quando dice di NO. Senza
            # questo ramo "vassoio" scivolava fino in fondo alla funzione e
            # usciva un FLOWPACK: un modello plausibile della famiglia
            # sbagliata, cioe' il difetto peggiore che questo progetto possa
            # avere. Chi ha dichiarato la tipologia merita di sapere che la
            # fustella non gli da' ragione, non un altro pack.
            # Il messaggio sta dentro i 200 caratteri che l'interfaccia
            # mostra: piu' lungo, e il consiglio finale - quello che dice
            # cosa fare - veniva tagliato via proprio lui.
            letto = "non si legge"
            if grezza is not None:
                # stesso arrotondamento di `vassoio.riconosci`, altrimenti
                # il conto che si legge nel messaggio non e' quello su cui la
                # decisione e' stata presa
                letto = "ne ha %d e %d" % (
                    max(0, len({round(t, 2) for t in grezza.xs}) - 1),
                    max(0, len({round(t, 2) for t in grezza.ys}) - 1))
            raise ValueError(
                "vassoio: un espositore ha cinque colonne e tre fasce, un "
                "display con plancia un coperchio sul fianco; questa fustella "
                "%s. Se e' un astuccio dichiara 'cartotecnico'." % letto)
        if v is not None:
            return dict(kind="vassoio", title="Vassoio espositore",
                        meta=["vassoio espositore",
                              "fondo %.1f x %.1f mm, pareti %s mm"
                              % (v.fondo_w, v.fondo_h,
                                 " / ".join("%s %.1f" % (k, a)
                                            for k, a in v.pareti.items()))]
                             + ([giro_v] if giro_v else [])
                             + list(v.warnings))
    if kind in (None, "carton"):
        # Lo steso di un cono si riconosce dai soli tratti in due decimi di
        # secondo, e va provato PRIMA dell'astuccio: sul cono Camy Apolo il
        # solutore astuccio trovava fra le icone un "astuccio vwrap" di 18,7 x
        # 5,9 x 2,5 mm, e il cono non veniva mai provato. La coppa invece
        # l'astuccio la rifiuta da se', e resta in fondo.
        from pack3d import coppa as cp
        if cp.e_un_cono(pdf):
            return analisi_coppa([pdf], kind or "coppa")
    if kind is None and _dice_film(pdf):
        # Il file dice di essere un film: il flowpack si prova PRIMA
        # dell'astuccio. Il solutore astuccio risolve anche certi film - sul
        # Kinder Happy Hippo T1, 1 | 15 | 83 | 15 | 1 per 15 | 85 | 15, trovava
        # un astuccio vwrap 52,5 x 51,2 x 9,7 - e il flowpack non veniva mai
        # provato. Se il flowpack non si risolve si va avanti come sempre.
        try:
            return _analisi_flowpack_dichiarata(pdf, esigente=True)
        except Exception:
            pass
    if kind in (None, "carton"):
        try:
            # nel verso della grafica, come la costruzione: i cartellini
            # devono dire le falde nell'ordine in cui le vedra' il modello
            pdf, d, _gradi, giro = artwork.astuccio_sulla_grafica(pdf)
            if d.panels:
                meta = ["astuccio %s%s" % (d.layout, "" if d.chiuso
                                           else " aperto"),
                        "%.1f x %.1f x %.1f mm" % d.dims_mm]
                if giro:
                    meta.append(giro)
                apertura = dl.dichiara_apertura(d)
                if apertura:
                    meta.append(apertura)
                rgb = avviso_quadricromia(pdf, regione=d.bbox)
                if rgb:
                    meta.insert(0, rgb)
                return dict(kind="carton", title="Astuccio %s" % d.layout,
                            meta=meta)
        except Exception as e:
            if kind == "carton":
                # Dichiarato cartotecnico e non e' un astuccio: puo' essere
                # un pezzo di una coppa, che e' cartotecnica anche lei. Se
                # non e' nemmeno quello, l'errore resta quello dell'astuccio.
                from pack3d import coppa as cp
                if cp.riconosci(pdf) is not None:
                    return analisi_coppa([pdf], "carton")
                # Un disco da solo non dice di essere un lid (`coppa.orienta`):
                # se c'e', l'errore dell'astuccio resta, ma prima viene il
                # consiglio, che l'interfaccia mostra solo i primi 200 caratteri
                disco = cp.leggi_disco(cp.tracce(pdf))
                if disco is not None:
                    raise ValueError("Non si risolve come astuccio, e ha un disco "
                                     "di %.0f mm: se e' il lid di un cono, "
                                     "dichiara 2 pezzi e carica anche il PDF del "
                                     "cono. (astuccio: %s)"
                                     % (2 * disco.r_taglio, e)) from e
                raise
    # nel verso della grafica, come la costruzione; e se fallisce anche il
    # ripiego, l'errore va al client
    try:
        return _analisi_flowpack_dichiarata(pdf)
    except Exception:
        if kind is None:
            # Senza dichiarazione, l'ultima possibilita' e' una coppa: lo
            # sleeve o il tappo. Si prova per ULTIMA, quando tutto il resto ha
            # fallito, cosi' gli altri pack non la pagano e non ne possono
            # essere scambiati; sul Nutella POT il ripiego flowpack falliva
            # con "saldature di testa non riconosciute".
            from pack3d import coppa as cp
            if cp.riconosci(pdf) is not None:
                return analisi_coppa([pdf])
        raise


def _dice_film(pdf):
    """Il file dice da se' di essere un film da flowpack?

    Il cartiglio Artworkr dei Ferrero lo scrive nella descrizione - "T1 0018 |
    WRAPPING/FILM" - e il disegno tecnico di un film ha FASCIA e PASSO, cioe'
    nastro e passo. Su tutti i file che abbiamo, WRAPPING lo porta ogni
    flowpack e nessun astuccio.
    """
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        try:
            testo = doc[0].get_textpage().get_text_range().upper()
        finally:
            doc.close()
    except Exception:
        return False
    return "WRAPPING" in testo or ("FASCIA" in testo and "PASSO" in testo)


def _analisi_flowpack_dichiarata(pdf, esigente=False):
    """I cartellini del flowpack. Con `esigente` fallisce invece di ripiegare
    sul solutore vecchio: e' la prova che si fa prima dell'astuccio, e un
    ripiego li' vorrebbe dire scegliere la famiglia su una lettura muta."""
    pdf, _gradi, giro, _verso = flowpack_sulla_grafica(pdf)
    _box, fp, ripiego = analisi_flowpack(pdf)
    if esigente and ripiego is not None:
        raise ValueError("flowpack non risolto: %s" % ripiego)
    meta = ["flowpack", "nastro %.0f x passo %.0f mm" % (fp.web_mm, fp.step_mm),
            "corpo %.1f mm" % fp.L]
    if giro:
        meta.append(giro)
    if fp.pillow:
        # a sovrapposizione la sezione non c'e' nello steso: il tubo e' piatto
        # e la forma che prende gonfiandosi la decide il rigonfiamento. Quello
        # che lo steso dice davvero e' giro, fronte e lembo coperto.
        meta.append("tubo piatto: giro %.1f, fronte %.1f, lembo coperto %.1f mm"
                    % (fp.girth, fp.W, fp.sovrapposizione))
    elif fp.piatto:
        # lo stesso, chiuso a pinna: giro, fronte e le due fasce della pinna
        meta.append("tubo piatto a pinna: giro %.1f, fronte %.1f, pinna %.1f mm"
                    % (fp.girth, fp.W, fp.side_fin))
    else:
        meta.append("sezione %.1f x %.1f mm" % (fp.W, fp.T))
    sospetto = falda_sospetta(fp)
    if sospetto:
        # prima di costruire, non dopo: qui l'utente le quote le sta leggendo
        meta.insert(0, sospetto)
    rgb = avviso_quadricromia(pdf, regione=fpk.foglio_in_pagina(fp))
    if rgb:
        meta.insert(0, rgb)
    if ripiego is not None:
        # anche qui il ripiego si dichiara: questi cartellini sono la prima
        # cosa che l'utente legge, e finora tacevano
        meta.insert(0, "ANALISI AUTOMATICA FALLITA (%s): quote dal solutore "
                       "vecchio, da verificare" % ripiego[:70])
    return dict(kind="flowpack", title="Flowpack",
                teeth_default=20, soft_default="medio", meta=meta)


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #
def _dividi(data, parti):
    """I PDF di un corpo solo: `[bytes]`, o None se `parti` non torna.

    Senza `parti` il corpo e' un PDF solo, com'e' sempre stato.
    """
    if not parti:
        return [data]
    try:
        lunghe = [int(k) for k in parti]
    except (TypeError, ValueError):
        return None
    if any(k <= 0 for k in lunghe) or sum(lunghe) != len(data):
        return None
    blocchi, o = [], 0
    for k in lunghe:
        blocchi.append(data[o:o + k])
        o += k
    if not all(b.startswith(b"%PDF") for b in blocchi):
        return None
    return blocchi


class Handler(BaseHTTPRequestHandler):
    # HEAD risponde con le stesse intestazioni di GET e senza corpo. Il flag
    # lo dice a _send, cosi' le due risposte non possono divergere.
    _senza_corpo = False

    def log_message(self, fmt, *a):
        sys.stderr.write("  %s\n" % (fmt % a))

    def _cors(self):
        # l'interfaccia puo' stare su un dominio diverso dal backend
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Pack3d")
        # senza questo il browser nasconde l'header alla pagina, su altra origine
        self.send_header("Access-Control-Expose-Headers", "X-Pack3d-Meta")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code, body, ctype="application/json", filename=None,
              meta=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if meta:
            # percent-encoded: un header HTTP e' latin-1 e non tollera accenti
            self.send_header("X-Pack3d-Meta", quote(
                json.dumps(meta, ensure_ascii=False)))
        if filename:
            self.send_header("Content-Disposition",
                             'attachment; filename="%s"' % filename)
        self._cors()
        self.end_headers()
        if not self._senza_corpo:
            self.wfile.write(body)

    def do_HEAD(self):
        # Render controlla la salute del servizio con HEAD, e
        # BaseHTTPRequestHandler senza do_HEAD risponde 501 a ogni controllo:
        # nel log di produzione si vede "Unsupported method ('HEAD')" a ogni
        # giro, dal primo istante dopo il deploy.
        self._senza_corpo = True
        try:
            self.do_GET()
        finally:
            self._senza_corpo = False

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self._send(200, json.dumps({"ok": True}))
        path = os.path.join(HERE, "pack3d_studio.html")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), "text/html; charset=utf-8")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, "Nessun file ricevuto")
            if n > MAX_UPLOAD:
                return self._send(413, "PDF troppo grande (limite %d MB)"
                                  % (MAX_UPLOAD // (1024 * 1024)))
            data = self.rfile.read(n)
            if not data.startswith(b"%PDF"):
                return self._send(400, "Il file caricato non e' un PDF")
            opts = json.loads(self.headers.get("X-Pack3d") or "{}")
            # Piu' PDF in un corpo solo, uno dopo l'altro: `parti` ne dice le
            # lunghezze. Serve alla coppa, che arriva in due file - lo sleeve
            # e il tappo - e si costruisce intera solo con tutti e due.
            blocchi = _dividi(data, opts.get("parti"))
            if blocchi is None:
                return self._send(400, "Le parti dichiarate non tornano col "
                                       "corpo, o una non e' un PDF")
            with tempfile.TemporaryDirectory() as td:
                pdfs = []
                for k, blocco in enumerate(blocchi):
                    pdfs.append(os.path.join(td, "in.pdf" if k == 0
                                             else "in%d.pdf" % k))
                    with open(pdfs[-1], "wb") as fh:
                        fh.write(blocco)
                pdf = pdfs[0]
                kind = normalizza_kind(opts.get("kind") or None)
                if kind == "altro":
                    return self._send(400, "Tipologia non ancora supportata")
                if kind is not None and kind not in KIND_NOTI:
                    return self._send(400, "Tipologia '%s' non riconosciuta: "
                                           "dichiara %s"
                                           % (kind, " o ".join("'%s'" % k
                                                               for k in KIND_NOTI)))
                # Il cartotecnico dice di quanti pezzi e' fatto, e ogni pezzo
                # e' un PDF: se i conti non tornano non si indovina quale
                # manca, si dice.
                pezzi = opts.get("pezzi")
                if pezzi not in (None, ""):
                    try:
                        pezzi = int(pezzi)
                    except (TypeError, ValueError):
                        return self._send(400, "Il numero di pezzi va digitato "
                                               "come numero intero")
                    if pezzi < 1:
                        return self._send(400, "Un pack ha almeno un pezzo")
                    if pezzi != len(pdfs):
                        return self._send(400, "Il pack e' di %d %s ma sono "
                                               "arrivati %d PDF: ne serve uno "
                                               "per pezzo"
                                          % (pezzi, "pezzo" if pezzi == 1
                                             else "pezzi", len(pdfs)))
                try:
                    carta = spessore_carta(opts.get("spessore"))
                except ValueError as e:
                    return self._send(400, str(e))
                # (`coppa` resta per chi chiama l'API: dalla pagina la coppa
                # e' un cartotecnico in due pezzi)
                if len(pdfs) > 1 and kind not in ("coppa", "carton"):
                    return self._send(400, "Piu' PDF insieme solo per un "
                                           "cartotecnico in piu' pezzi: per "
                                           "questa tipologia caricane uno")
                if (in_piu_pezzi(kind, pdfs)
                        and self.path.startswith("/api/analyze")):
                    # anche da /api/analyze-ai: i pezzi li misura il codice,
                    # l'agente non ha niente da aggiungere
                    return self._send(200, json.dumps(analisi_coppa(pdfs,
                                                                    kind)))
                if self.path.startswith("/api/analyze-ai"):
                    import agent
                    par, tr = agent.analyse(pdf, kind, opts)
                    par["_chiamate"] = [t["tool"] for t in tr]
                    return self._send(200, json.dumps(par, ensure_ascii=False))
                if self.path.startswith("/api/analyze"):
                    return self._send(200, json.dumps(analyze_pdf(pdf, kind)))
                if self.path.startswith("/api/build"):
                    if not _slots.acquire(blocking=False):
                        return self._send(503, "Server occupato: riprova fra qualche "
                                               "secondo")
                    # Da qui in giu' il posto e' preso e va restituito comunque
                    # vada. Prima analyze_pdf stava FUORI da qualsiasi
                    # protezione: su un PDF che non sa risolvere (K Tronky,
                    # "saldature di testa non riconosciute") lanciava, il posto
                    # non tornava indietro, e dopo MAX_JOBS tentativi il server
                    # rispondeva 503 a chiunque fino al riavvio.
                    try:
                        out = os.path.join(td, "out.glb")
                        t0 = traccia("inizio")
                        case = CASI.get(_sig(pdf))
                        info = (analisi_coppa(pdfs, kind)
                                if in_piu_pezzi(kind, pdfs)
                                else analyze_pdf(pdf, kind))
                        t1 = traccia("analisi", t0,
                                     "%s, %d kB" % (info["kind"], len(data) // 1024))
                        q = qualita(opts.get("quality"))
                        # Su TUTTI i rami: e' proprio sul ramo che se ne
                        # dimenticava che nasceva l'UnboundLocalError.
                        avvisi_ingresso = []
                        # Le aree riservate che l'agente ha visto: valgono su
                        # tutte e due le famiglie, quindi si leggono una volta
                        # sola prima di scegliere il ramo.
                        aree = aree_da_agente(opts.get("params"))
                        # stessa storia delle aree riservate: il file non
                        # dichiara la colata, e l'unica cosa che resta e'
                        # quello che l'agente ha guardato
                        col_riq = colata_da_agente(opts.get("params"))
                        if info["kind"] == "coppa":
                            avvisi = build_coppa(pdfs, out, q, aree,
                                                 dichiarato=kind or "coppa",
                                                 carta=carta)
                        elif info["kind"] == "vassoio":
                            avvisi = build_vassoio(pdf, out, q, aree, col_riq)
                        elif info["kind"] == "carton":
                            # build_carton i suoi avvisi li restituiva gia', ed
                            # era il chiamante a buttarli e poi a leggere una
                            # variabile che su questo ramo non esisteva.
                            avvisi = build_carton(pdf, out, q, aree, col_riq,
                                                  carta=carta)
                        else:
                            soft = opts.get("soft", "medio")
                            if str(soft).strip().lower() == "auto":
                                # "Scegli tu": il livello lo decide l'agente in
                                # /api/analyze-ai e torna qui dentro params
                                scelto = livello_da_agente(opts.get("params"))
                                if scelto is None:
                                    # Nessuna analisi allegata: gonfiore() cade
                                    # su 5 in silenzio mentre l'interfaccia ha
                                    # appena promesso che sceglieva l'AI. Un
                                    # ripiego muto che produce un modello
                                    # plausibile e' il difetto peggiore che
                                    # questo progetto possa avere.
                                    avvisi_ingresso.append(
                                        "RIGONFIAMENTO NON SCELTO DA NESSUNO: "
                                        "nessuna analisi AI allegata alla "
                                        "richiesta, uso il livello medio 5")
                                    soft = 5
                                else:
                                    soft = scelto
                            # la scatola puo' dirla l'agente o la casella
                            # dell'interfaccia: basta una delle due
                            scatola = (bool(opts.get("scatola"))
                                       or scatola_da_agente(opts.get("params")))
                            pinne = opts.get("pinne")
                            if pinne in (None, "", "auto"):
                                pinne = pinne_da_agente(opts.get("params"))
                            avvisi = build_flowpack(
                                pdf, out, int(opts.get("teeth", 20)),
                                str(soft), case, q,
                                sezione_da_agente(opts.get("params")),
                                scatola, pinne, aree, col_riq)
                        traccia("costruzione", t1,
                                "%d kB" % (os.path.getsize(out) // 1024))
                        traccia("totale", t0)
                        with open(out, "rb") as fh:
                            # gli avvisi della costruzione viaggiano in un
                            # header: il corpo e' il GLB. Finivano nel nulla,
                            # e con loro ogni diagnostica.
                            return self._send(200, fh.read(), "model/gltf-binary",
                                              filename="modello.glb",
                                              meta=avvisi_ingresso + list(avvisi))
                    finally:
                        _slots.release()
            return self._send(404, "endpoint sconosciuto")
        except Exception as e:
            traceback.print_exc()
            return self._send(500, "%s: %s" % (type(e).__name__, e))


# Tubo piatto a sovrapposizione: quanto e' spessa la sezione in frazione del
# diametro del cerchio, ai due estremi della scala di rigonfiamento. Il cerchio
# e' il massimo fisico: con quel film non si puo' essere piu' tondi. Il valore
# al livello 1 viene dalla taratura sul K Tronky T1, che al livello 5 deve
# uscire con rapporto 1,466 come il suo GLB di riferimento.
PILLOW_LENTE = float(os.environ.get("PACK3D_PILLOW_LENTE", "0.65"))
PILLOW_CERCHIO = float(os.environ.get("PACK3D_PILLOW_CERCHIO", "1.0"))

# esponente della superellisse ai due estremi della scala di rigonfiamento:
# alto = rettangolo (film teso sul prodotto), 2 = ellisse (pack pieno d'aria)
SEZ_RETTANGOLO = float(os.environ.get("PACK3D_SEZ_RIGIDO", "10"))
SEZ_ELLISSE = float(os.environ.get("PACK3D_SEZ_MORBIDO", "2"))

# quanto il bordo della pinna sfrutta meta' perimetro: 1.0 e' il massimo fisico
FIN_OPEN_RATIO = float(os.environ.get("PACK3D_FIN_OPEN", "1.0"))
# Quanto del film oltre il corpo se lo mangia la gola, in frazione di spessore.
# Il limite geometrico e' 0,5: la gola piegata a 45 gradi sullo spigolo costa
# mezzo spessore. Sul pack vero pero' una parte di quel film si ripiega di lato
# come orecchia invece di accorciare la pinna, quindi la frazione utile e' piu'
# bassa. 0,40 e' quella che riproduce le foto del Brioss: 37,6 = 22,8 di gola
# piu' 14,8 di pinna. Tarata su un pack solo.
GOLA_SU_SPESSORE = float(os.environ.get("PACK3D_GOLA", "0.40"))
# La spalla, fuori dalla scatola, lunga almeno tante volte il calo del tubo
# dalla sezione piena alla saldatura. Con la rampa morbida della mesh il punto
# piu' ripido ha pendenza 1,87 volte il calo sulla lunghezza: a 1,7 e' 1,1,
# cioe' 48 gradi, e il film ci si stende stirato di 1,2 in modo uniforme
# (misurato sul bollino del Paradiso: era 2,5 in media e 3,7 di punta).
SPALLA_SU_CALO = float(os.environ.get("PACK3D_SPALLA", "1.7"))
# Quanto resta dello spessore sulla pinna: e' il parametro di build_mesh, qui
# perche' serve anche a calcolare il calo.
FLAT_END = 0.035

MAX_UPLOAD = 60 * 1024 * 1024
# Uno, e non e' un numero da tarare sulla macchina: pdfium non e' thread-safe
# nemmeno su documenti diversi, e due costruzioni insieme fanno morire il
# processo intero con un int3 dentro libpdfium.so. Provato su 16 GB, dove la
# memoria non c'entrava niente. Alzarlo vuol dire far cadere il servizio sotto
# i piedi anche di chi non c'entrava. Vedi REGOLE.md, *pdfium non si chiama da
# due thread*, e DEPLOY.md per i numeri per fase.
MAX_JOBS = int(os.environ.get("PACK3D_MAX_JOBS", "1"))
_slots = threading.Semaphore(MAX_JOBS)

if __name__ == "__main__":
    # PORT e HOST arrivano dall'ambiente sui servizi di hosting; in locale
    # bastano gli argomenti. 0.0.0.0 serve per essere raggiungibili da fuori.
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("pack3d studio in ascolto su %s:%d" % (host, port))
    if host in ("0.0.0.0", "::"):
        print("  in locale:  http://localhost:%d" % port)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
