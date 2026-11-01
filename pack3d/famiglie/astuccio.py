"""
L'astuccio (il cartotecnico): l'apertura, le incisioni, la finestra, la
pellicola, lo spessore della carta e la costruzione (`build_carton`).
"""
from __future__ import annotations

import traceback

from .. import artwork
from .. import dieline as dl
from .. import exporters
from .. import folding
from .. import lettura as lettura_pdf
from .. import quote as quotature
from .. import rilievo
from .. import sormonto as lo_sormonto
from .. import steso as lo_steso
from .. import verifica
from ..artwork import risoluzione
from ..dieline import PT2MM
from .comune import (RUVIDITA_CARTA,
    SENZA_PELLICOLA,
    avviso_pagine,
    avviso_quadricromia,
    lamina_della_tela,
    pellicola_sicura,
    riga_pellicola,
    rilievo_sicuro,
    scrivi_lettura)


# Il controllo dell'AI vede i solchi dell'apertura come righe sottili: senza
# saperlo, una riga che segue la fustella sembra disegno tecnico rimasto. Non
# cambia cosa e' un difetto: gli dice cosa sono quelle righe.
INCISA = "apertura a strappo incisa nel modello"
# Lo stesso per la linguetta di chiusura sul bordo libero di una faccia
# (`incisioni.chiusura`).
CHIUSURA = "linguetta di chiusura incisa nel modello"


# La riga che dice il fronte curvo, anche al controllo dell'AI: il cielo a D
# che sporge in mezzo e' la scatola, non un difetto.
FRONTE_CURVO = ("fronte curvo: le alette di cielo e fondo sono piu' lunghe "
                "della profondita' e il fronte piu' largo del retro, quindi il "
                "fronte si incurva verso fuori di %.1f mm in mezzo e cielo e "
                "fondo sono a D")


def incidi_apertura(pdf, d, faces, girate, spessore, sagomate=()):
    """I tagli dell'apertura a strappo incisi nelle facce. La riga per chi
    guarda il modello, o None se l'astuccio non ha un'apertura.

    Un guasto qui non ferma la costruzione: l'astuccio esce come sempre,
    senza solchi, e la riga lo dice.
    """
    from pack3d import incisioni
    try:
        nomi = [f["name"] for f in faces if f["name"] in d.panels]
        tg = incisioni.tagli(pdf, d.panels, nomi)
        # la linguetta di chiusura sul bordo libero di una faccia
        ch = incisioni.chiusura(pdf, d.panels, nomi)
        # ... se la faccia non e' ritagliata sul suo contorno (`pack3d.sormonto`):
        # li' la linguetta e' tagliata, non incisa
        ch = {k: v for k, v in ch.items() if k not in sagomate}
        if not tg and not ch:
            return None
        tutti = {n: tg.get(n, []) + ch.get(n, []) for n in set(tg) | set(ch)}
        n = incisioni.incidi(faces, tutti, d.panels, girate, spessore)
    except Exception as e:                        # noqa: BLE001
        traceback.print_exc()
        for f in faces:
            f.pop("maglia", None)
        return ("tagli della fustella riconosciuti ma non incisi (%s): "
                "l'astuccio esce chiuso e liscio" % type(e).__name__)
    righe = []
    if tg:
        righe.append("%s: %d tagli su %s, solchi di %.2f mm come sul cartone - "
                     "la grafica resta intera, il taglio dal rovescio non si "
                     "vede da fuori" % (INCISA, sum(map(len, tg.values())),
                                        ", ".join(sorted(tg)),
                                        incisioni.LARGHEZZA))
    if ch:
        righe.append("%s: %d tagli su %s, solchi di %.2f mm come sul cartone - "
                     "la grafica resta intera" % (
                         CHIUSURA, sum(map(len, ch.values())),
                         ", ".join(sorted(ch)), incisioni.LARGHEZZA))
    return "; ".join(righe)


# L'astuccio con l'apertura a strappo APERTA: vedi `pack3d.apertura`. I nomi
# delle facce in italiano, per la riga che lo dice.
APERTA = "astuccio aperto"
# Di quanti gradi la pagina propone di aprirla, quando chiede: la finestra
# sollevata quanto basta a guardarci dentro, ma ancora sopra il buco.
GRADI_PROPOSTI = 60
NOMI_FACCE = {"front": "fronte", "back": "retro", "top": "cielo",
              "bottom": "fondo", "left": "fianco sinistro",
              "right": "fianco destro"}


def apertura_gradi(valore):
    """I gradi di cui aprire l'apertura a strappo, None se resta chiusa.
    ValueError se non e' un angolo da 0 a `apertura.GRADI_MAX`."""
    from pack3d import apertura
    if valore in (None, "", False):
        return None
    try:
        g = float(valore)
    except (TypeError, ValueError):
        g = float("nan")
    if g != g or not 0 <= g <= apertura.GRADI_MAX:
        raise ValueError("L'apertura a strappo si dice in gradi, da 0 (chiusa) "
                         "a %d" % apertura.GRADI_MAX)
    return g or None


def apri_apertura(pdf, d, faces, girate, spessore, gradi):
    """L'astuccio con l'apertura a strappo aperta di `gradi`: (fatto, riga).

    `fatto` e' falso se l'astuccio resta chiuso - il disegno non ha
    un'apertura con la sua cerniera, o un guasto - e la riga dice perche'.
    Un guasto non ferma la costruzione: le facce tornano come erano.
    """
    from pack3d import apertura
    nomi = [f["name"] for f in faces if f["name"] in d.panels]
    prima = [dict(f) for f in faces]
    try:
        info = apertura.apri(pdf, d.panels, nomi, faces, gradi, girate, spessore)
    except Exception as e:                        # noqa: BLE001
        traceback.print_exc()
        faces[:] = prima
        return False, ("apertura a strappo non aperta (%s): l'astuccio esce "
                       "chiuso" % type(e).__name__)
    if info is None:
        return False, ("aperto di %g gradi chiesto, ma il disegno non ha "
                       "un'apertura a strappo con la sua cerniera: l'astuccio "
                       "esce chiuso" % gradi)

    def nome(n):
        return NOMI_FACCE.get(n, n or "?")
    altre = [nome(n) for n in info["facce"] if n != info["cerniera"]]
    riga = ("%s di %g gradi: la finestra a strappo del %s ruota sulla piega col "
            "%s (cerniera di %.0f mm)%s, e la scatola appoggia sul %s"
            % (APERTA, info["gradi"], nome(info["cerniera"]),
               nome(info["piega_con"]), info["cerniera_mm"],
               ", con la linguetta che gira sul %s" % " e sul ".join(altre)
               if altre else "", nome(info["appoggia"])))
    if info["sfogliatura_mm"]:
        riga += ("; attorno al buco e sotto la finestra %.1f mm di cartoncino "
                 "sfogliato, fra il taglio davanti e quello dal rovescio"
                 % info["sfogliatura_mm"])
    if info["lunette"]:
        riga += ("; la lunetta per il dito spinta dentro" if info["lunette"] == 1
                 else "; %d lunette per il dito spinte dentro" % info["lunette"])
    if info["tagli_liberi"]:
        riga += ("; %d tagli vicini all'apertura non disegnati"
                 % info["tagli_liberi"])
    return True, riga


def facce_astuccio(d):
    """I pannelli che sul solido sono facce, nell'ordine in cui le fa
    `folding.build_faces`: senza alette ne' lembi incollati."""
    from pack3d import folding
    return ([n for n in folding.FOLDS.get(d.layout, {}) if n in d.panels]
            + [n for n in folding.FASCE_RETRO if n in d.panels])


def strappo_astuccio(pdf, d):
    """Se l'astuccio ha un'apertura a strappo che si sa aprire: la domanda
    per l'utente, chiusa coi tagli modellati o aperta di quanti gradi. None
    se non ce l'ha, o se leggerla non riesce: la domanda allora non si fa, e
    l'astuccio esce chiuso come sempre.

    {"dove": la frase che dice dov'e', "faccia", "piega_con", "altre",
    "gradi": quelli proposti, "gradi_max"}.
    """
    from pack3d import apertura
    try:
        t = apertura.trova(pdf, d.panels, facce_astuccio(d))
    except Exception:                             # noqa: BLE001
        traceback.print_exc()
        return None
    if t is None:
        return None

    def nome(n):
        return NOMI_FACCE.get(n, n or "?")
    dove = ("la finestra sta sul %s e resta attaccata alla piega col %s"
            % (nome(t["faccia"]), nome(t["piega_con"])))
    if t["altre"]:
        dove += ", la linguetta gira sul %s" % " e sul ".join(
            nome(n) for n in t["altre"])
    return dict(t, dove=dove, gradi=GRADI_PROPOSTI,
                gradi_max=apertura.GRADI_MAX)


def build_carton(pdf, out_glb, quality="hd", lastre_extra=(),
                 colata_riquadro=None, carta=None, apertura=None,
                 pellicola=None, incisioni=True):
    """L'astuccio. `carta` e' lo spessore del cartoncino in mm se l'utente
    l'ha dichiarato (`SPESSORI_CARTA`); senza, `folding.SPESSORE_CRT`. Con
    `apertura`, in gradi, l'apertura a strappo esce aperta: vedi
    `apri_apertura`; chiusa, i suoi tagli si incidono come solchi, se non
    e' `incisioni=False`. Con `pellicola` la finestra del retro di un astuccio
    aperto - fra le due falde - ha la sua pellicola trasparente."""
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
    # la lettura del PDF accanto al GLB (`pack3d.lettura`): mai un errore
    scrivi_lettura(out_glb, lambda: lettura_pdf.astuccio(pdf, d, gradi))
    # Coperture via per nome e texture girate sul verso della grafica: sono
    # regole dell'artwork, e stanno in `pack3d.artwork` perche' le applichi
    # anche la riga di comando.
    esito = {}
    # lo steso, la texture del modello: il DT con un millimetro attorno,
    # dallo stesso foglio delle facce (`pack3d.steso`)
    m_dt = 1.0 / PT2MM
    tex, avvisi_tex = artwork.texture_astuccio(pdf, d.panels, dpi,
                                              lastre_extra=lastre_extra,
                                              colata_riquadro=colata_riquadro,
                                              regione=d.bbox, esito=esito,
                                              dieline=d,
                                              steso=(d.bbox[0] - m_dt,
                                                     d.bbox[1] - m_dt,
                                                     d.bbox[2] + m_dt,
                                                     d.bbox[3] + m_dt))
    faces = folding.build_faces(d.dims_mm, tex, layout=d.layout,
                                panels=d.panels, chiuso=d.chiuso,
                                spessore=(folding.SPESSORE_CRT if carta is None
                                          else carta),
                                fianchi_sul_fronte=d.fianchi_su == "front")
    # ogni faccia coi lati del suo pannello del DT, nessuna specchiata, il
    # fronte davanti: vedi `verifica.facce_astuccio`
    _ok, verifiche = verifica.facce_astuccio(faces, d.panels, d.curva_mm)
    # il fondo col bordo sagomato che chiude sopra la falda del retro: la
    # falda sotto di lui, il fondo ritagliato piu' avanti, sulle facce finite
    # (`pack3d.sormonto`). Non sul fronte curvo, come i tagli.
    sormonto, pannelli = None, dict(d.panels)
    if not d.curva_mm:
        try:
            sormonto = lo_sormonto.trova(pdf, d)
            if sormonto:
                tela0, box0 = esito["steso"]
                pf = lo_sormonto.falda(faces, sormonto,
                                       folding.SPESSORE_CRT if carta is None else carta,
                                       tela0, box0, esito["scala"],
                                       esito.get("girate"))
                if pf is None:
                    sormonto = None
                else:
                    pannelli["falda"] = pf
        except Exception:                         # noqa: BLE001
            traceback.print_exc()
            sormonto = None
            faces = [f for f in faces if f["name"] not in ("falda", "falda interno")]
    # il fronte curvo, se la fustella lo dice: vedi `dieline._fronte_curvo`
    if d.curva_mm:
        folding.curva_fronte(faces, d.dims_mm, d.curva_mm,
                             {k: d.panels[k].h_mm for k in ("top", "bottom")
                              if k in d.panels})
    # e le misure del disegno contro le quote che il file scrive, come per le
    # testate del flowpack: le quote non costruiscono, confermano
    riscontro = quotature.riscontro_astuccio(pdf, d)
    # il marchio orizzontale e dritto: se il fronte e' rimasto girato - la
    # texture non si poteva girare senza stirarla - si gira la scatola
    marchio = esito.get("marchio", 0)
    if marchio:
        folding.gira_facce(faces, marchio)
    # l'apertura a strappo aperta, se l'ha chiesto chi carica (`apertura`),
    # oppure incisa nelle facce, come sul cartone chiuso: vedi
    # `pack3d.apertura` e `pack3d.incisioni`. Sulle facce finite, dopo il
    # giro del marchio.
    spessore = folding.SPESSORE_CRT if carta is None else carta
    # sul fronte curvo l'apertura a strappo non si apre ne' si incide: le
    # facce sono gia' maglie, e i tagli andrebbero piegati con loro
    aperta, riga_aperta = (apri_apertura(pdf, d, faces, esito.get("girate"),
                                         spessore, apertura)
                           if apertura and not d.curva_mm else (False, None))
    incisa = (None if aperta or d.curva_mm or not incisioni else
              incidi_apertura(pdf, d, faces, esito.get("girate"), spessore,
                              sagomate=("bottom",) if sormonto else ()))
    riga_sormonto = None
    if sormonto:
        try:
            if lo_sormonto.ritaglia(faces, sormonto, d.panels,
                                    esito.get("girate"), spessore):
                riga_sormonto = (
                    "chiusura a sormonto: il fondo e' ritagliato sul contorno "
                    "della fustella (linguetta e smussi del bordo libero, che "
                    "entra %.1f mm) e chiude sopra la falda del retro, che si "
                    "vede dalle tacche" % sormonto["entra_mm"])
        except Exception:                         # noqa: BLE001
            traceback.print_exc()
    # la pellicola sulla finestra del retro, se chi carica l'ha voluta: sulle
    # facce finite, girate e curvate come escono
    film, riga_film = None, None
    if finestra_astuccio(d):
        if pellicola:
            film = pellicola_sicura(folding.pellicola_retro, faces, spessore)
            riga_film = riga_pellicola(1, film is not None,
                                       folding.PELLICOLA_FALDA)
        elif pellicola is False:
            riga_film = SENZA_PELLICOLA
    # La texture e' lo steso del PDF (`pack3d.steso`): ogni faccia stampata
    # ci arriva dal suo pannello, girato come la sua immagine, e lo steso
    # torna nel verso del PDF. Il rilievo dell'embossing, se il DT ne ha la
    # lastra, e' una mappa delle normali sullo steso.
    tela, box = esito["steso"]
    scala = esito["scala"]
    girate_steso = dict(esito.get("girate") or {})
    if "falda" in pannelli and "bottom" in girate_steso:
        girate_steso["falda"] = girate_steso["bottom"]
    op = lo_steso.facce_sullo_steso(faces, pannelli, girate_steso, scala,
                                 box, gradi)
    normale, riga_rilievo = rilievo_sicuro(
        rilievo.mappa_dello_steso, pdf, tuple(c / scala for c in box),
        tela.size, scala / PT2MM, op, coppia=True)
    # la lamina, se il DT ne ha la lastra - o la legenda la dice su una
    # tinta piatta: metallo dove c'e', cartoncino attorno (`pack3d.lamina`)
    righe_lamina = []
    mr = lamina_della_tela(pdf, tuple(c / scala for c in box), tela.size,
                           tela.size, scala / PT2MM, "astuccio", righe_lamina,
                           carta=RUVIDITA_CARTA, legenda=sorgente)
    if mr is not None:
        mr = lo_steso.gira(mr, op)
    tela = lo_steso.gira(tela, op)
    storte = lo_steso.riscontro(faces, tela)
    exporters.write_glb(faces, out_glb, tex_max=tmax, pellicola=film,
                        steso=(tela, normale, mr))
    meta = ["astuccio %s%s" % (d.layout, "" if d.chiuso else " aperto"),
            "%.1f x %.1f x %.1f mm" % d.dims_mm] + ([giro] if giro else [])
    meta += righe_lamina
    if storte:
        meta.append("STESO: la grafica di %s non torna con lo steso (%s): la "
                    "texture non e' quella delle facce" % (
                        ", ".join(n for n, _q in storte),
                        ", ".join("%.0f%%" % (100 * q) for _n, q in storte)))
    if riga_film:
        meta.append(riga_film)
    if riga_rilievo:
        meta.append(riga_rilievo)
    if d.curva_mm:
        meta.append(FRONTE_CURVO % d.curva_mm)
    if riga_aperta:
        meta.append(riga_aperta)
    if incisa:
        meta.append(incisa)
    if riga_sormonto:
        meta.append(riga_sormonto)
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

# Lo spessore della carta che l'utente dichiara per un cartotecnico, da 1 a 3:
# 1 la carta dei coni gelato, poco piu' di un foglio; 2 il cartoncino degli
# astucci e delle coppe; 3 un cartoncino spesso. Senza dichiarazione ogni
# famiglia tiene il suo: 0,45 mm l'astuccio (`folding.SPESSORE_CRT`), 0,35 la
# coppa (dal cartiglio della coppa da 500), 0,10 il cono.
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


def finestra_astuccio(d):
    """Vero se l'astuccio ha la finestra sul retro: aperto, con le due falde
    che lasciano in mezzo un'apertura (il T6 aperto). Un astuccio
    senza retro, tipo vassoio, non ha una finestra: e' aperto."""
    return bool(not d.chiuso and d.finestra_mm > 0
                and all(k in d.panels for k in folding.FASCE_RETRO))


def finestre_da_chiedere(quante, dove):
    """La domanda della pellicola, per la pagina: va fatta ogni volta che il
    pack ha una finestra."""
    return dict(quante=quante, dove=dove)


def incisioni_scelte(valore):
    """Se l'astuccio chiuso porta la fustella dell'apertura a strappo
    modellata come solchi: si', di serie; no se chi carica la vuole liscia.
    ValueError se non e' un si' o un no."""
    if valore in (None, ""):
        return True
    try:
        return bool(pellicola_scelta(valore))
    except ValueError:
        raise ValueError("La fustella dell'apertura modellata si dice con si' o no")


def pellicola_scelta(valore):
    """True, False, o None se non e' dichiarata. ValueError se non e' un si'
    o un no."""
    if valore in (None, ""):
        return None
    if isinstance(valore, bool):
        return valore
    v = str(valore).strip().lower()
    if v in ("1", "si", "si'", "s\u00ec", "true", "yes"):
        return True
    if v in ("0", "no", "false"):
        return False
    raise ValueError("La pellicola delle finestre si dice con si' o no")
