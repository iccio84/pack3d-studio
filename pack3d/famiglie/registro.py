"""
Il registro delle famiglie: come si riconosce ognuna (`RICONOSCIMENTO`)
e come si costruisce (`COSTRUZIONI`).
"""
from __future__ import annotations

import traceback

from .. import artwork
from .. import ballotin
from .. import dieline as dl
from .. import gelato
from .. import plancia
from .. import pouch
from .. import punta
from .. import scatola_plancia
from .. import sportello
from .. import tubo
from .. import vassoio
from .astuccio import (build_carton,
    finestra_astuccio,
    finestre_da_chiedere,
    strappo_astuccio)
from .ballotin import build_ballotin
from .comune import KIND_NOTI, avviso_pagine, avviso_quadricromia, normalizza_kind
from .coppa import analisi_coppa, build_coppa
from .flowpack import (CASI,
    _analisi_flowpack_dichiarata,
    _dice_film,
    _sig,
    build_flowpack,
    nello_spessore_scelto,
    saldatura_scelta,
    sezione_da_agente)
from .incarto import _analisi_incarto, analisi_incarto_dichiarato, build_incarto
from .pouch import analisi_pouch, build_pouch
from .punta import build_punta
from .riempimento import build_riempimento
from .tubo import build_tubo
from .vassoio import build_vassoio


def analyze_pdf(pdf, kind=None, domande=False):
    """`kind` arriva dall'utente: la tipologia si dichiara, non si indovina.
    Il riconoscimento automatico sbaglia (il solutore astuccio risolve anche
    certi flowpack) e sbagliare qui compromette tutto il resto.

    Tutte le famiglie si misurano sulla prima pagina sola: se ce ne sono
    altre, il primo cartellino lo dice. Vedi `avviso_pagine`."""
    pdf, n_pagine = artwork.pagina_unica(pdf)
    info = _analyze_pdf(pdf, kind, domande)
    pagine = avviso_pagine(n_pagine)
    if pagine and isinstance(info.get("meta"), list):
        info["meta"].insert(0, pagine)
    return info


# ---------------------------------------------------------------------------
# Le famiglie: chi riconosce un PDF, e in che ordine.
#
# Era una catena di `if` in `_analyze_pdf`, trecento righe, con la tipologia
# dichiarata intrecciata dentro ogni ramo: per sapere chi si prova prima di
# chi bisognava leggerla tutta, e una forma nuova si infilava a meta'. Adesso
# e' una tabella, `RICONOSCIMENTO`: una riga per prova, nell'ordine in cui si
# fanno, con le tipologie dichiarate per cui valgono. La prima prova che dice
# «e' mio» da' la lettura; una prova che dice «e' mio ma non si legge» ferma
# tutto con un errore che lo dice. L'ordine e' quello di prima, prova per
# prova: i casi del parco non cambiano strada.
#
# Una forma nuova: il suo modulo, una funzione `_prova_<forma>` qui sotto e
# una riga nella tabella, DOPO quelle che ci sono (FORME.md, *Dove entra*);
# e la sua costruzione in `COSTRUZIONI`.

class _Lettura:
    """Quello che le prove di una lettura si passano.

    `pdf` puo' cambiare strada facendo: la prova dell'astuccio lo gira nel
    verso della grafica, e le prove dopo leggono il foglio girato, come
    prima. `errore_astuccio` e' il motivo per cui il solutore astuccio ha
    rifiutato un cartotecnico dichiarato: le forme che vengono dopo si
    provano solo allora, e se nessuna e' sua l'errore resta quello."""

    def __init__(self, pdf, kind, domande):
        self.pdf, self.kind, self.domande = pdf, kind, domande
        self.errore_astuccio = None


class Famiglia:
    """Una prova del riconoscimento: `prova(lettura)` torna la lettura se il
    PDF e' suo, None se no; un errore se e' suo e non si legge. Si fa solo
    per le tipologie `dichiarate` (None: senza dichiarazione)."""

    def __init__(self, nome, dichiarate, prova):
        self.nome, self.dichiarate, self.prova = nome, tuple(dichiarate), prova

    def __repr__(self):
        return "Famiglia(%r)" % self.nome


def _prova_coppa_dichiarata(l):
    return analisi_coppa([l.pdf])


def _prova_riempimento(l):
    # due PDF, non uno: vedi `analisi_riempimento`. Qui non deve mai
    # arrivare, e se arriva non deve cadere nel ramo del flowpack.
    raise ValueError("riempimento: carica due PDF, il vassoio e il pack (CU)")


def _prova_incarto_dichiarato(l):
    # dichiarato senza dire come si chiude: a pieghe, vedi
    # `analisi_incarto_dichiarato` (la pagina passa da li')
    return analisi_incarto_dichiarato(l.pdf, "pieghe")


def _prova_pouch(l):
    pu = analisi_pouch(l.pdf)
    return dict(kind="pouch", title="Pouch",
                meta=pouch.dichiara(pu) + list(pu.avvisi))


def _prova_caso_calibrato(l):
    # la firma si legge per tutte le tipologie che arrivano qui, come prima;
    # il caso vale solo per il flowpack
    case = CASI.get(_sig(l.pdf))
    if case and l.kind in (None, "flowpack"):
        return dict(kind="flowpack", title=case["name"],
                    teeth_default=case["teeth"], soft_default=case["soft"],
                    meta=["caso calibrato: " + case["name"],
                          "nastro %.0f x passo %.0f mm" % (case["web"], case["step"])])
    return None


def _prova_vassoio(l):
    """Il vassoio espositore e i display: con plancia, con lo sportello,
    a scatola, sagomato. Dichiarato vassoio, se nessuno e' suo si ferma: la
    dichiarazione vale anche quando dice di no."""
    pdf, kind = l.pdf, l.kind
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
        # niente. E' qui che il display T1x48 smette di uscire flowpack.
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
        if kind == "vassoio":
            # la plancia ricavata dentro il coperchio (`pack3d.sportello`):
            # solo dichiarato, la prova gira il foglio e costa
            try:
                _p, _g, sp, _gr, giro_s = sportello.riconosci_sulla_tavola(pdf)
            except Exception:
                sp = None
            finally:
                dl.scarta_resa()
            if sp is not None:
                return dict(kind="vassoio", title="Display con plancia",
                            meta=sportello.dichiara(sp)
                            + ([giro_s] if giro_s else []))
    if v is None and kind == "vassoio":
        # la scatola che resta chiusa, con la plancia ricavata dal
        # coperchio (`pack3d.scatola_plancia`): si prova solo dichiarata
        try:
            sp = scatola_plancia.riconosci(pdf)
        except Exception:
            sp = None
        if sp is not None:
            return dict(kind="vassoio", title="Display a scatola",
                        meta=scatola_plancia.dichiara(sp))
    sagomato = False
    if v is None and kind == "vassoio":
        # per ultimo il vassoio sagomato, come in `build_vassoio`
        try:
            _p, _g, v, _gr, giro_v = vassoio.riconosci_sulla_tavola(
                pdf, sagomato=True)
        except Exception:
            v = None
        finally:
            dl.scarta_resa()
        sagomato = v is not None
    if v is None and kind == "vassoio":
        # La dichiarazione deve valere anche quando dice di NO. Senza
        # questo ramo "vassoio" scivolava fino in fondo e usciva un
        # FLOWPACK: un modello plausibile della famiglia sbagliata, cioe' il
        # difetto peggiore che questo progetto possa avere. Chi ha
        # dichiarato la tipologia merita di sapere che la fustella non gli
        # da' ragione, non un altro pack.
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
            "display con plancia un coperchio sul fianco o sul retro; "
            "questa fustella "
            "%s. Se e' un astuccio dichiara 'cartotecnico'." % letto)
    if v is not None:
        return dict(kind="vassoio", title="Vassoio espositore", sagomato=sagomato,
                    meta=["vassoio espositore",
                          "fondo %.1f x %.1f mm, pareti %s mm"
                          % (v.fondo_w, v.fondo_h,
                             " / ".join("%s %.1f" % (k, a)
                                        for k, a in v.pareti.items()))]
                         + ([giro_v] if giro_v else [])
                         + list(v.warnings))
    return None


def _prova_cono(l):
    # Lo steso di un cono si riconosce dai soli tratti in due decimi di
    # secondo, e va provato PRIMA dell'astuccio: sul cono T1 macaron il
    # solutore astuccio trovava fra le icone un "astuccio vwrap" di 18,7 x
    # 5,9 x 2,5 mm, e il cono non veniva mai provato. La coppa invece
    # l'astuccio la rifiuta da se', e resta in fondo.
    from pack3d import coppa as cp
    if cp.e_un_cono(l.pdf):
        return analisi_coppa([l.pdf], l.kind or "coppa")
    return None


def _prova_ballotin(l):
    # Il ballotin anche, e per la stessa ragione: il solutore astuccio lo
    # risolve, e male - sul ballotin al frutto della passione una torre da
    # 465 x 120,7 x 90 mm. Su un astuccio la prova si ferma al prefiltro
    # delle lenti: sugli astucci del parco da 0,15 a 0,7 s, quasi tutti per
    # leggere le penne del DT.
    try:
        b = ballotin.riconosci(l.pdf)
    except Exception:
        traceback.print_exc()
        b = None
    if b is None:
        return None
    meta = ballotin.dichiara(b)
    rgb = avviso_quadricromia(l.pdf, regione=b.regione)
    if rgb:
        meta.insert(0, rgb)
    letto = dict(kind="ballotin", title="Ballotin", meta=meta)
    if l.domande and b.finestre:
        letto["finestre"] = finestre_da_chiedere(
            len(b.finestre), ballotin.dove_finestre(b))
    return letto


def _prova_film(l):
    # Il file dice di essere un film: il flowpack si prova PRIMA
    # dell'astuccio. Il solutore astuccio risolve anche certi film - sul T1
    # cold seal, 1 | 15 | 83 | 15 | 1 per 15 | 85 | 15, trovava un astuccio
    # vwrap 52,5 x 51,2 x 9,7 - e il flowpack non veniva mai provato. Se il
    # flowpack non si risolve si va avanti come sempre.
    if not _dice_film(l.pdf):
        return None
    letto = _analisi_incarto(l.pdf)
    if letto is not None:
        return letto
    try:
        return _analisi_flowpack_dichiarata(l.pdf, esigente=True)
    except Exception:
        return None


# Il messaggio sta dentro i 200 caratteri che l'interfaccia mostra, col
# consiglio in fondo: e' quello che dice cosa fare.
CARTOTECNICO_SENZA_PANNELLI = (
    "cartotecnico: la fustella non si divide in pannelli, e non e' una "
    "scatola a punta, una coppa o un tubo. Se e' un film, dichiara 'flowpack'.")


def _prova_astuccio(l):
    """L'astuccio. Se il solutore lo rifiuta e il pack e' dichiarato
    cartotecnico, il motivo resta in `errore_astuccio` per le forme dopo."""
    try:
        # nel verso della grafica, come la costruzione: i cartellini
        # devono dire le falde nell'ordine in cui le vedra' il modello
        l.pdf, d, _gradi, giro = artwork.astuccio_sulla_grafica(l.pdf)
        if not d.panels:
            if l.kind == "carton":
                # Dichiarato cartotecnico, e il solutore astuccio non trova
                # pannelli senza fermarsi: e' un rifiuto come gli altri.
                # Prima si scivolava fino al flowpack, cioe' la famiglia
                # sbagliata senza dirlo (REGOLE.md, *La dichiarazione vale
                # anche quando dice di no*).
                l.errore_astuccio = ValueError(CARTOTECNICO_SENZA_PANNELLI)
            return None
        meta = ["astuccio %s%s" % (d.layout, "" if d.chiuso else " aperto"),
                "%.1f x %.1f x %.1f mm" % d.dims_mm]
        if giro:
            meta.append(giro)
        apertura = dl.dichiara_apertura(d)
        if apertura:
            meta.append(apertura)
        rgb = avviso_quadricromia(l.pdf, regione=d.bbox)
        if rgb:
            meta.insert(0, rgb)
        letto = dict(kind="carton", title="Astuccio %s" % d.layout, meta=meta)
        s = strappo_astuccio(l.pdf, d) if l.domande else None
        if s:
            meta.append("apertura a strappo: %s - si puo' avere chiusa, "
                        "coi tagli modellati, o aperta" % s["dove"])
            letto["strappo"] = s
        if l.domande and finestra_astuccio(d):
            letto["finestre"] = finestre_da_chiedere(
                1, "sul retro, fra le due falde: alta %.1f mm" % d.finestra_mm)
        return letto
    except Exception as e:
        if l.kind == "carton":
            l.errore_astuccio = e
        return None


def _prova_punta(l):
    # Dichiarato cartotecnico e non e' un astuccio: puo' essere la scatola
    # a punta, che il solutore astuccio rifiuta perche' non ha cielo. Solo
    # qui, dopo l'astuccio: gli astucci non la pagano e non ne possono
    # essere scambiati.
    if l.errore_astuccio is None:
        return None
    try:
        pu = punta.riconosci(l.pdf)
    except Exception:
        traceback.print_exc()
        pu = None
    if pu is None:
        return None
    meta = punta.dichiara(pu)
    rgb = avviso_quadricromia(l.pdf, regione=pu.regione)
    if rgb:
        meta.insert(0, rgb)
    return dict(kind="punta", title="Scatola a punta", meta=meta)


def _prova_pezzo_di_coppa(l):
    # Non e' nemmeno quella: puo' essere un pezzo di una coppa, che e'
    # cartotecnica anche lei.
    if l.errore_astuccio is None:
        return None
    from pack3d import coppa as cp
    if cp.riconosci(l.pdf) is not None:
        return analisi_coppa([l.pdf], "carton")
    return None


def _prova_tubo(l):
    # Un tubo a cono, lo sleeve lungo e stretto col fondo saldato piatto: un
    # settore di corona che la coppa non prende (non ha fondo ne' vista
    # montata). Vedi `pack3d.tubo`.
    if l.errore_astuccio is None:
        return None
    try:
        tb = tubo.riconosci(l.pdf)
    except Exception:
        traceback.print_exc()
        tb = None
    if tb is None:
        return None
    meta = tubo.dichiara(tb)
    rgb = avviso_quadricromia(l.pdf, regione=tb.regione)
    if rgb:
        meta.insert(0, rgb)
    return dict(kind="tubo", title="Tubo a cono", meta=meta,
                gusti=list(gelato.GUSTI))


def _ferma_cartotecnico(l):
    # Dichiarato cartotecnico e nessuna forma l'ha preso: l'errore resta
    # quello dell'astuccio. Un disco da solo non dice di essere un lid
    # (`coppa.orienta`): se c'e', prima viene il consiglio, che
    # l'interfaccia mostra solo i primi 200 caratteri.
    e = l.errore_astuccio
    if e is None:
        return None
    from pack3d import coppa as cp
    disco = cp.leggi_disco(cp.tracce(l.pdf))
    if disco is not None:
        raise ValueError("Non si risolve come astuccio, e ha un disco "
                         "di %.0f mm: se e' il lid di un cono, "
                         "dichiara 2 pezzi e carica anche il PDF del "
                         "cono. (astuccio: %s)"
                         % (2 * disco.r_taglio, e)) from e
    raise e


def _prova_incarto(l):
    return _analisi_incarto(l.pdf)


def _prova_flowpack(l):
    # nel verso della grafica, come la costruzione; e se fallisce anche il
    # ripiego, l'errore va al client
    try:
        return _analisi_flowpack_dichiarata(l.pdf)
    except Exception:
        if l.kind is None:
            # Senza dichiarazione, l'ultima possibilita' e' una coppa: lo
            # sleeve o il tappo. Si prova per ULTIMA, quando tutto il resto ha
            # fallito, cosi' gli altri pack non la pagano e non ne possono
            # essere scambiati; sulla coppa da 500 il ripiego flowpack falliva
            # con "saldature di testa non riconosciute".
            from pack3d import coppa as cp
            if cp.riconosci(l.pdf) is not None:
                return analisi_coppa([l.pdf])
        raise


# L'ordine e' la regola. Le dichiarate solo: si fanno subito, e non cadono
# mai in un'altra famiglia. Poi, senza dichiarazione o dichiarate, le forme
# che il solutore astuccio risolverebbe male - vassoio e display, cono,
# ballotin, il film che lo dice - PRIMA dell'astuccio; quelle che il solutore
# astuccio rifiuta DOPO, e solo se e' stato lui a rifiutarle; il flowpack per
# ultimo.
RICONOSCIMENTO = (
    Famiglia("coppa", ["coppa"], _prova_coppa_dichiarata),
    Famiglia("riempimento", ["riempimento"], _prova_riempimento),
    Famiglia("incarto dichiarato", ["incarto"], _prova_incarto_dichiarato),
    Famiglia("pouch", ["pouch"], _prova_pouch),
    Famiglia("caso calibrato", [None, "flowpack", "carton", "vassoio"],
             _prova_caso_calibrato),
    Famiglia("vassoio e display", [None, "carton", "vassoio"], _prova_vassoio),
    Famiglia("cono", [None, "carton"], _prova_cono),
    Famiglia("ballotin", [None, "carton"], _prova_ballotin),
    Famiglia("film che lo dice", [None], _prova_film),
    Famiglia("astuccio", [None, "carton"], _prova_astuccio),
    Famiglia("scatola a punta", ["carton"], _prova_punta),
    Famiglia("pezzo di coppa", ["carton"], _prova_pezzo_di_coppa),
    Famiglia("tubo a cono", ["carton"], _prova_tubo),
    Famiglia("cartotecnico che non si legge", ["carton"], _ferma_cartotecnico),
    Famiglia("incarto", [None, "flowpack"], _prova_incarto),
    Famiglia("flowpack", [None, "flowpack"], _prova_flowpack),
)


def _analyze_pdf(pdf, kind=None, domande=False):
    """La lettura del PDF: la prima famiglia di `RICONOSCIMENTO` che dice
    che e' suo.

    `domande`: preparare le domande che la pagina fa prima di costruire -
    sull'astuccio, se ha un'apertura a strappo la vuole chiusa o aperta
    (`strappo_astuccio`); su un pack con le finestre, se le vuole con la
    pellicola trasparente o senza (`finestre_da_chiedere`). Solo
    dall'analisi che la pagina chiede prima di costruire: la costruzione non
    la ripete."""
    kind = normalizza_kind(kind)
    if kind is not None and kind not in KIND_NOTI:
        # Cadere nel ramo flowpack e' peggio che fermarsi: e' lo stesso difetto
        # del sinonimo mancante, solo sull'altro capo. Su questo file -
        # l'astuccio della ciambella - passando "auto" invece di niente il
        # solutore astuccio veniva saltato e usciva un flowpack.
        raise ValueError("tipologia '%s' non riconosciuta: dichiara %s"
                         % (kind, " o ".join("'%s'" % k for k in KIND_NOTI)))
    lettura = _Lettura(pdf, kind, domande)
    for famiglia in RICONOSCIMENTO:
        if kind in famiglia.dichiarate:
            letto = famiglia.prova(lettura)
            if letto is not None:
                return letto
    # il flowpack, per ultimo, o risponde o si ferma: qui non si arriva
    raise ValueError("nessuna famiglia riconosce questo PDF")


# Le costruzioni: per ogni famiglia letta (`info["kind"]`) la funzione che
# prepara `costruisci(lastre, uscita)`, la costruzione che la correzione
# dell'AI rifa' con le lastre tecniche che ha riconosciuto. `r` e' la
# richiesta: i PDF, le scelte della pagina, la qualita' (vedi `_col_pdf`).
# Una famiglia che qui non c'e' si costruisce come flowpack, come prima.

def _costruisci_coppa(r, info):
    def costruisci(lastre, uscita):
        return build_coppa(r.pdfs, uscita, r.q, lastre,
                           dichiarato=r.kind or "coppa", carta=r.carta)
    return costruisci


def _costruisci_vassoio(r, info):
    def costruisci(lastre, uscita):
        return build_vassoio(r.pdf, uscita, r.q, lastre, r.col_riq)
    return costruisci


def _costruisci_pouch(r, info):
    def costruisci(lastre, uscita):
        return build_pouch(r.pdf, uscita, r.q, lastre, r.col_riq)
    return costruisci


def _costruisci_ballotin(r, info):
    def costruisci(lastre, uscita):
        return build_ballotin(r.pdf, uscita, r.q, lastre, r.col_riq,
                              carta=r.carta, pellicola=r.pellicola)
    return costruisci


def _costruisci_punta(r, info):
    def costruisci(lastre, uscita):
        return build_punta(r.pdf, uscita, r.q, lastre, r.col_riq, carta=r.carta)
    return costruisci


def _costruisci_incarto(r, info):
    def costruisci(lastre, uscita):
        return build_incarto(r.pdf, uscita, r.q, lastre, r.col_riq)
    return costruisci


def _costruisci_tubo(r, info):
    def costruisci(lastre, uscita):
        return build_tubo(r.pdf, uscita, r.q, lastre, r.col_riq, carta=r.carta,
                          gelato_gusto=r.gelato)
    return costruisci


def _costruisci_astuccio(r, info):
    def costruisci(lastre, uscita):
        return build_carton(r.pdf, uscita, r.q, lastre, r.col_riq, carta=r.carta,
                            apertura=r.apertura, pellicola=r.pellicola,
                            incisioni=r.incisioni)
    return costruisci


def _costruisci_riempimento(r, info):
    if info.get("cu") == "carton":
        # un vassoio coi suoi astucci, chiusi
        def costruisci(lastre, uscita):
            return build_riempimento(r.pdfs, info, uscita, r.quanti, quality=r.q,
                                     carta=r.carta, incisioni=r.incisioni,
                                     per_fila=r.per_fila)
        return costruisci
    # un vassoio coi suoi flowpack: due costruzioni e un GLB solo, vedi
    # `pack3d.riempimento`
    pdf_fp = r.pdfs[info["flowpack"]]
    soft, scatola, pinne, mat = r.parametri_flowpack(pdf_fp, r.nomi[info["flowpack"]])
    case_fp = CASI.get(_sig(pdf_fp))

    def costruisci(lastre, uscita):
        opts = r.opts
        return build_riempimento(
            r.pdfs, info, uscita, r.quanti,
            (int(opts.get("teeth", 20)), str(soft), case_fp, r.q,
             sezione_da_agente(opts.get("params")),
             scatola, pinne, lastre, r.col_riq, mat, r.mat_ai,
             saldatura_scelta(opts), nello_spessore_scelto(opts)), r.q,
            per_fila=r.per_fila)
    return costruisci


def _costruisci_flowpack(r, info):
    soft, scatola, pinne, mat = r.parametri_flowpack(r.pdf, r.nomi[0])

    def costruisci(lastre, uscita):
        opts = r.opts
        return build_flowpack(
            r.pdf, uscita, int(opts.get("teeth", 20)), str(soft), r.case, r.q,
            sezione_da_agente(opts.get("params")),
            scatola, pinne, lastre, r.col_riq, mat, r.mat_ai,
            saldatura_scelta(opts), nello_spessore_scelto(opts))
    return costruisci


COSTRUZIONI = {
    "coppa": _costruisci_coppa,
    "vassoio": _costruisci_vassoio,
    "pouch": _costruisci_pouch,
    "ballotin": _costruisci_ballotin,
    "punta": _costruisci_punta,
    "incarto": _costruisci_incarto,
    "tubo": _costruisci_tubo,
    "carton": _costruisci_astuccio,
    "riempimento": _costruisci_riempimento,
    "flowpack": _costruisci_flowpack,
}
