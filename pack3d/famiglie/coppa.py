"""
La coppa e il cono gelato, coi loro pezzi tondi, e i pezzi a prisma.
"""
from __future__ import annotations

import math

import numpy as np

from .. import artwork
from .. import atlante
from .. import ballotin
from .. import exporters
from .. import folding
from .. import lettura as lettura_pdf
from .. import nero
from .. import prisma
from .. import steso as lo_steso
from ..artwork import risoluzione
from ..dieline import PT2MM
from ..dieline import Panel
from .comune import (TINTE_BALLOTIN,
    avviso_pagine,
    avviso_quadricromia,
    lamina_della_tela,
    scrivi_lettura)


def lettura_tondi(pezzi, giri):
    """La lettura dei pezzi tondi (`pack3d.lettura`): lo steso a settore
    dello sleeve o del cono, il tappo o il lid, riletti sulle loro pagine gia'
    orientate - la costruzione li legge dentro `pack3d.coppa` e restituisce
    solo la maglia. Uno sotto l'altro."""
    from pack3d import coppa as cp
    letture = []
    for nome, pdf in pezzi.items():
        if pdf is None:
            continue
        T = cp.tracce(pdf)
        gradi = giri.get(nome, 0) if giri else 0
        if nome == "coppa":
            c = cp.leggi_coppa(pdf, T)
            s = c.steso
            letture.append(lettura_pdf.steso_tondo(
                pdf, s, "Sleeve della coppa letto cosi'",
                ["carta fra i raggi %s e %s mm" % (_mm(s.R1), _mm(s.R2)),
                 "parete dalla piega del fondo alla bocca: %s mm" % _mm(c.parete),
                 "coppa alta %s mm, bocca %s mm" % (_mm(c.montata.altezza),
                                                     _mm(2 * c.montata.r_bordo))],
                parete=(s.piega, s.piega + c.parete), gradi=gradi))
        elif nome == "cono":
            k = cp.leggi_cono(T)
            if k is not None:
                letture.append(lettura_pdf.cono(
                    pdf, k, "Cono letto cosi'",
                    ["steso a settore pieno, raggio %s mm" % _mm(k.steso.R2),
                     "cono alto %s mm, bocca %s mm" % (_mm(k.altezza), _mm(2 * k.r_bocca)),
                     "lembo di colla %s mm" % _mm(k.lembo)], gradi=gradi))
        elif nome == "tappo":
            t = cp.leggi_tappo(pdf, T)
            letture.append(lettura_pdf.disco(
                pdf, t.centro, t.r_taglio, "Tappo letto cosi'",
                ["taglio %s mm, alto %s mm" % (_mm(2 * t.r_taglio), _mm(t.altezza))],
                gradi=gradi))
        elif nome == "lid":
            d = cp.leggi_disco(T)
            if d is not None:
                letture.append(lettura_pdf.disco(
                    pdf, d.centro, d.r_taglio, "Lid letto cosi'",
                    ["taglio %s mm" % _mm(2 * d.r_taglio)], gradi=gradi))
    return lettura_pdf.accosta(*letture)


def _mm(x):
    return ("%.1f" % x).replace(".", ",")


def _pezzi_tondi(pdfs, dichiarato="coppa", giri=None):
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

    In `giri`, se c'e', finiscono i gradi di cui ogni pezzo e' stato girato
    sul verso della grafica: lo steso ci torna alla fine (`pack3d.steso`).
    """
    from pack3d import coppa as cp
    trovati = {}
    for k, pdf in enumerate(pdfs):
        pdf, _n = artwork.pagina_unica(pdf)
        # girato sulla tavola si legge girato: vedi `coppa.orienta`
        pdf, cosa, gradi = cp.orienta(pdf, dischi=len(pdfs) > 1)
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
        if giri is not None:
            giri[cosa] = int(gradi or 0)
    if {"coppa", "tappo"} & set(trovati) and {"cono", "lid"} & set(trovati):
        raise ValueError("i PDF sono pezzi di due pack diversi: %s"
                         % ", ".join(sorted(trovati)))
    return trovati


def _pezzi_prisma(pdfs, dichiarato):
    """`(fondo, coperchio)` della scatola a prisma, o None: si prova quando i
    pezzi tondi hanno rifiutato i PDF, e solo sul cartotecnico dichiarato in
    pezzi. Ogni PDF dice da se' che pezzo e' (`prisma.pezzi`): l'ordine in
    cui arrivano non conta."""
    if dichiarato != "carton":
        return None
    letti = []
    for pdf in pdfs:
        p = prisma.riconosci(artwork.pagina_unica(pdf)[0])
        if p is None:
            return None
        letti.append(p)
    return prisma.pezzi(letti)


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
    try:
        pezzi = _pezzi_tondi(pdfs, dichiarato)
    except ValueError:
        pr = _pezzi_prisma(pdfs, dichiarato)
        if pr is None:
            raise
        meta = prisma.dichiara(*pr)
        meta.insert(0, _in_pezzi(dichiarato, pdfs, "il fondo e il coperchio "
                                 "di una scatola a prisma" if pr[1] is not None
                                 else "il fondo di una scatola a prisma"))
        return dict(kind="coppa", title="Scatola a prisma", meta=meta)
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

    La texture di ogni pezzo e' lo steso del suo foglio (`pack3d.steso`),
    e il rovescio bianco un colore pieno; due nodi nel GLB, il contenitore e
    la chiusura, perche' la chiusura si toglie. I due stesi vanno in
    un'immagine sola, l'atlante (`pack3d.atlante`).
    """
    from pack3d import coppa as cp
    dpi, tmax = risoluzione(quality)
    giri = {}
    try:
        pezzi = _pezzi_tondi(pdfs, dichiarato, giri)
    except ValueError:
        pr = _pezzi_prisma(pdfs, dichiarato)
        if pr is None:
            raise
        return build_prisma(pdfs, pr, out_glb, quality, lastre_extra,
                            dichiarato, carta)
    scrivi_lettura(out_glb, lambda: lettura_tondi(pezzi, giri))
    if _cono(pezzi):
        cono, lid = pezzi.get("cono"), pezzi.get("lid")
        V, UV, T, A, parti, meta, bianchi = cp.costruisci_cono(
            cono, lid, dpi=dpi, lastre_extra=lastre_extra, tex_max=tmax,
            carta=carta)
        titolo = ("cono col lid" if cono and lid
                  else "cono senza lid: carica anche il PDF del lid per "
                       "chiuderlo" if cono
                  else "solo il lid: carica anche il PDF del cono")
        nodi = "il cono e il lid sono due nodi del GLB"
    else:
        sleeve, tappo = pezzi.get("coppa"), pezzi.get("tappo")
        V, UV, T, A, parti, meta, bianchi = cp.costruisci(sleeve, tappo, dpi=dpi,
                                                 lastre_extra=lastre_extra,
                                                 tex_max=tmax, carta=carta)
        titolo = ("coppa col tappo" if sleeve and tappo
                  else "coppa senza tappo: carica anche il PDF del tappo per "
                       "chiuderla" if sleeve
                  else "solo il tappo: carica anche il PDF dello sleeve")
        nodi = "la coppa e il tappo sono due nodi del GLB"
    # lo steso di ogni pezzo torna nel verso del suo PDF, se `orienta` aveva
    # girato il foglio; le parti hanno vertici loro
    for k, (nome, a, b) in enumerate(parti):
        op = lo_steso.INDIETRO[giri.get(nome, 0) % 360]
        if op is not None:
            usati = np.unique(np.asarray(T)[a:b].ravel())
            UV[usati] = lo_steso.applica(lo_steso.matrice(op), UV[usati])
            A[k] = A[k].transpose(op)
    tinte = lo_steso.Tinte(np.where(bianchi, 0, -1).astype(np.int32),
                           [("rovescio", cp.BIANCO)])
    exporters.write_glb_mesh(V, UV, T, A, out_glb, tex_max=tmax, parti=parti,
                             tinte=tinte)
    atlante.unisci_file(out_glb)
    if dichiarato == "carton":
        titolo = _in_pezzi(dichiarato, pdfs, titolo)
    return [titolo] + meta + ["%d vertici, %d triangoli; %s"
                              % (len(V), len(T), nodi)]


def build_prisma(pdfs, pezzi, out_glb, quality="hd", lastre_extra=(),
                 dichiarato="carton", carta=None):
    """La scatola a prisma, il fondo poligonale con le pareti e il coperchio
    a calzare: vedi `pack3d.prisma`.

    Come la scatola a punta, pezzo per pezzo: la texture e' il DT intero,
    pulito, e ogni faccia prende la grafica dal suo posto sul foglio, con
    sotto le strisce del rovescio. Due nodi nel GLB, il fondo e il
    coperchio, e i due stesi in un'immagine sola (`pack3d.atlante`)."""
    dpi, tmax = risoluzione(quality)
    fondo, coperchio = pezzi
    M_fondo, M_cop = prisma.assetti(fondo, coperchio)
    sp = folding.SPESSORE_CRT if carta is None else carta
    per_pdf = {}
    for pdf in pdfs:
        pagina, n_pagine = artwork.pagina_unica(pdf)
        p = prisma.riconosci(pagina)
        for q in (fondo, coperchio):
            if q is not None and p is not None and np.allclose(p.piano, q.piano) \
                    and q.regione == p.regione and id(q) not in per_pdf:
                per_pdf[id(q)] = (pagina, n_pagine)
                break
    # la riga di ogni pezzo: il fondo dice anche se manca il coperchio
    righe = prisma.dichiara(fondo, coperchio)
    scrivi_lettura(out_glb, lambda: lettura_pdf.accosta(*[
        lettura_pdf.generica(per_pdf[id(pr)][0], pr.regione,
                             "Scatola a prisma, %s, letta cosi'" % nome, r)
        for nome, pr, r in (("fondo", fondo, righe if coperchio is None else righe[:1]),
                            ("coperchio", coperchio, righe[1:]))
        if pr is not None and id(pr) in per_pdf]))
    avvisi, V, UV, T, A, parti, quali = [], [], [], [], [], [], []
    colori, MR = [], []
    for nome, pr, M, quota, cop in (
            ("fondo", fondo, M_fondo, 0.0, False),
            ("coperchio", coperchio, M_cop, fondo.altezza + sp, True)):
        if pr is None:
            continue
        pdf, n_pagine = per_pdf[id(pr)]
        conti = {}
        clean, lastre = artwork.senza_coperture(pdf, extra=lastre_extra,
                                                regione=pr.regione, conti=conti)
        deciso_nero = nero.spia(clean, 0, dpi / 72.0)
        pagine = avviso_pagine(n_pagine)
        if pagine:
            avvisi.append(pagine)
        fuori = artwork.avviso_fuori_dt(conti)
        if fuori:
            avvisi.append(fuori)
        avvisi.extend(artwork.avvisi_gda(conti))
        rgb = avviso_quadricromia(clean, regione=pr.regione)
        if rgb:
            avvisi.append(rgb)
        if lastre:
            avvisi.append("%s: lastre tecniche e coperture tolte per nome: %s"
                          % (nome, ", ".join(lastre)))
        m = 1.0 / PT2MM
        x0, y0, x1, y1 = pr.regione
        x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
        lato_pt = max(x1 - x0, y1 - y0)
        dpi_tex = min(dpi, tmax * 72.0 / lato_pt) if lato_pt > 0 else dpi
        tex = folding.rasterize_panels(
            clean, {"dt": Panel(x0, y0, x1, y1, "dt")}, dpi=dpi_tex, inset_px=0,
            clean=True, note=avvisi, nero_deciso=deciso_nero)["dt"]
        scala = dpi_tex / 72.0
        origine = (round(x0 * scala) / scala * PT2MM,
                   round(y0 * scala) / scala * PT2MM)
        tela = ballotin.con_interno(tex)
        v, uv, t = prisma.maglia(pr, M, origine, scala / PT2MM, tela.size,
                                 coperchio=cop, quota=quota, spessore=carta)
        # la lamina, se il DT ne ha la lastra: metallo sulla texture, carta
        # attorno, e sotto le strisce niente metallo (`pack3d.lamina`)
        mr = lamina_della_tela(pdf, (x0, y0, x1, y1), tex.size, tela.size,
                               scala / PT2MM, nome, avvisi)
        tela, uv, tinte, mr = lo_steso.senza_strisce(tex.height, tela, uv, t,
                                                     TINTE_BALLOTIN, mr)
        MR.append(mr)
        # le tinte dei due pezzi in una lista sola
        mappa = []
        for nome_t, c in tinte.colori:
            if (nome_t, c) not in colori:
                colori.append((nome_t, c))
            mappa.append(colori.index((nome_t, c)))
        quali.append(np.array([mappa[q] if q >= 0 else -1
                               for q in tinte.quale], np.int32))
        primo = len(T)
        T.extend((np.asarray(t) + len(V)).tolist())
        V.extend(np.asarray(v).tolist())
        UV.extend(np.asarray(uv).tolist())
        A.append(tela)
        parti.append((nome, primo, len(T)))
    V = np.asarray(V, np.float32)
    UV = np.asarray(UV, np.float32)
    T = np.asarray(T, np.int64)
    tinte = lo_steso.Tinte(np.concatenate(quali), colori)
    exporters.write_glb_mesh(V, UV, T, A, out_glb, tex_max=tmax, parti=parti,
                             tinte=tinte,
                             mr=MR if any(m is not None for m in MR) else None)
    atlante.unisci_file(out_glb)
    titolo = _in_pezzi(dichiarato, pdfs, "scatola a prisma col coperchio"
                       if coperchio is not None else
                       "scatola a prisma senza coperchio")
    return ([titolo] + prisma.dichiara(fondo, coperchio) + avvisi
            + ["%d vertici, %d triangoli; il fondo e il coperchio sono due "
               "nodi del GLB" % (len(V), len(T))])
