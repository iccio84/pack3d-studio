"""
Preparare l'artwork prima di ritagliarne la texture.

Tre passaggi, e sono tre REGOLE, non tre comodita':

1. **le coperture si tolgono per nome.** Vernici, bianchi coprenti e cold seal
   sono pieni grandi quanto la grafica: nessuna euristica sul tratto li vede, e
   pdfium li rende opachi. Il nome invece lo dice senza ambiguita'.
2. **il modello segue la grafica, non il disegno tecnico.** Il DT dice come e'
   impaginato il foglio, la grafica dice come si legge il pack in mano.
3. **la grafica non si distorce mai**, che e' il limite della seconda: dove
   girare stirerebbe il pannello non si gira, e lo si dichiara.

E due regole che valgono per tutte le famiglie - flowpack, astucci, vassoi:
la grafica si prende dal suo livello, col disegno tecnico spento oggetto per
oggetto (`folding.rasterize_panels` con `clean`, vedi `strati.py`), e la
texture e' HD (`risoluzione`).

Stanno qui, e non nel server, perche' non sono questioni di HTTP: sono
dell'artwork. Finche' stavano nel server le applicava solo lui, e la riga di
comando consegnava astucci diversi da quelli del prodotto - sul Nutella Donut
una scatola rosa piena, con la vernice ancora sopra.
"""
from __future__ import annotations

import os
import tempfile

from PIL import Image

from .dieline import PT2MM


# La risoluzione della texture, (dpi, lato massimo in px), per qualita'.
#
# Di serie e' HD, per tutte le famiglie. Sul piano Free di Render la texture
# di un flowpack stava in 1700 px, e un foglio come Colazione - 460 mm di
# nastro - usciva a 3,7 px/mm, meno di 100 dpi: sgranato appena ci si
# avvicinava. Il limite era la memoria, e sugli Spaces non c'e' piu' (vedi
# DEPLOY.md). A 300 dpi quel foglio fa 5433 px di lato; il tetto a 8192 e'
# quello che le schede video da scrivania reggono tutte, e sotto il quale
# three.js non deve ridimensionare niente.
#
# "web" resta per chi vuole un GLB leggero, e sono i numeri di prima.
TEXTURE = {"web": (200, 1700), "hd": (300, 8192)}


def qualita(q):
    """"web", "hd" o "alta" - che e' HD con la maglia piu' fitta."""
    q = str(q or "").strip().lower()
    return q if q in ("web", "hd", "alta") else "hd"


def risoluzione(quality):
    """(dpi, lato massimo) della texture per quella qualita'."""
    return TEXTURE["web" if qualita(quality) == "web" else "hd"]


def strip_separations(src, dst, drop, riquadri=None, variabili=None):
    """Toglie le lastre tecniche eliminando le operazioni di disegno.

    Colorarle di bianco non basta: un tratto tecnico sopra la grafica
    lascerebbe una riga bianca. Il filtro scende anche dentro i Form XObject,
    dove spesso stanno cold seal e bianco coprente.

    Se `riquadri` e' una lista, ci finiscono i riquadri delle aree riservate
    ai dati variabili che si sono tolte - le lastre `variabili`, o se non
    vengono date quelle il cui nome lo dice (`techink.DATI_VARIABILI`) - nel
    telaio di misura (punti, MediaBox, y in giu'): sono i posti dove la loro
    didascalia sta, e chi rende la texture la spegne. Vedi
    `strati.segna_riservate`.
    """
    import pypdf
    from pypdf.generic import ContentStream
    from .techink import DATI_VARIABILI

    # `clone_from` e non `append`: append PERDE /OCProperties, e con quello
    # perde i livelli. Un astuccio che ha insieme una vernice e la colata su un
    # livello suo usciva dallo strappo senza livelli, e la sostituzione della
    # colata non partiva - in silenzio, perche' a quel punto il livello non
    # c'era piu' davvero.
    w = pypdf.PdfWriter(clone_from=src)
    drop = {d.lower() for d in drop}
    if riquadri is None:
        variabili = set()
    elif variabili is None:
        variabili = {d for d in drop if DATI_VARIABILI.search(d)}
    else:
        variabili = {v.lower() for v in variabili} & drop

    def names(res, quali=drop):
        out = set()
        cs = res.get("/ColorSpace")
        if not cs:
            return out
        for k, v in cs.get_object().items():
            try:
                o = v.get_object()
                if o[0] == "/Separation":
                    if str(o[1]).lstrip("/").replace("#20", " ").lower() in quali:
                        out.add(str(k))
                elif o[0] == "/DeviceN":
                    nm = [str(x).lstrip("/").replace("#20", " ").lower() for x in o[1]]
                    if nm and all(n in quali for n in nm):
                        out.add(str(k))
            except Exception:
                pass
        return out

    FILL, STROKE = {b"f", b"F", b"f*"}, {b"S", b"s"}
    BOTH = {b"B", b"B*", b"b", b"b*"}
    # Lo spazio colore e' STATO GRAFICO, come la matrice: lo cambiano anche
    # g, rg e k - che dipingono in grigio, RGB e quadricromia - e Q lo
    # riporta a com'era al q. Seguendo solo `cs`, dopo il riempimento di
    # un'area riservata tutto quello che veniva in quadricromia con `k` era
    # ancora "di quella lastra" e veniva tolto: sul Kinder Cards T2 106
    # riempimenti su 112, per fortuna tutti fuori dal DT - il fondo del
    # cartiglio, le pastiglie della legenda - ma sulla grafica sarebbe stato
    # lo stesso.
    DISPOSITIVO = {b"g": "/DeviceGray", b"rg": "/DeviceRGB",
                   b"k": "/DeviceCMYK"}
    DISPOSITIVO_TRATTO = {b"G": "/DeviceGray", b"RG": "/DeviceRGB",
                          b"K": "/DeviceCMYK"}
    PERCORSO = {b"m", b"l", b"c", b"v", b"y", b"re"}
    # dove i form sono disegnati: matrice al momento del Do, per i riquadri
    matrici = {}

    def per(m, n):
        """m e poi n, come compone il PDF."""
        a1, b1, c1, d1, e1, f1 = m
        a2, b2, c2, d2, e2, f2 = n
        return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
                c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
                e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)

    def punti(ops, op, m):
        v = [float(x) for x in ops]
        if op == b"re":
            x, y, a, b = v
            v = [x, y, x + a, y, x, y + b, x + a, y + b]
        return [(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])
                for x, y in zip(v[0::2], v[1::2])]

    def filt(obj, res, base=None):
        bad = names(res)
        var = names(res, variabili) if base is not None and variabili else set()
        cs = ContentStream(obj, w)
        ncs = scs = None
        pila = []
        ctm, tracciato = base, []
        out = []
        for ops, op in cs.operations:
            if op == b"cs":
                ncs = str(ops[0])
            elif op == b"CS":
                scs = str(ops[0])
            elif op in DISPOSITIVO:
                ncs = DISPOSITIVO[op]
            elif op in DISPOSITIVO_TRATTO:
                scs = DISPOSITIVO_TRATTO[op]
            elif op == b"q":
                pila.append((ncs, scs, ctm))
            elif op == b"Q":
                if pila:
                    ncs, scs, ctm = pila.pop()
            elif ctm is not None:
                if op == b"cm":
                    ctm = per(tuple(float(x) for x in ops), ctm)
                elif op in PERCORSO and var:
                    try:
                        tracciato.extend(punti(ops, op, ctm))
                    except (TypeError, ValueError):
                        pass
                elif op == b"Do":
                    try:
                        o = res["/XObject"].get_object()[str(ops[0])].get_object()
                        mat = tuple(float(x) for x in
                                    o.get("/Matrix", (1, 0, 0, 1, 0, 0)))
                        matrici.setdefault(id(o), per(mat, ctm))
                    except Exception:
                        pass
            if op in FILL or op in BOTH or op in STROKE or op == b"n":
                if ncs in var and op not in STROKE and op != b"n" and tracciato:
                    xs = [p[0] for p in tracciato]
                    ys = [p[1] for p in tracciato]
                    riquadri.append((min(xs) - mx0, my1 - max(ys),
                                     max(xs) - mx0, my1 - min(ys)))
                tracciato = []
            if op in FILL and ncs in bad:
                out.append(([], b"n")); continue
            if op in STROKE and scs in bad:
                out.append(([], b"n")); continue
            if op in BOTH:
                fd, sd = ncs in bad, scs in bad
                if fd and sd:
                    out.append(([], b"n")); continue
                if fd:
                    out.append((ops, b"S")); continue
                if sd:
                    out.append((ops, b"f")); continue
            if op == b"sh" and ncs in bad:
                continue
            out.append((ops, op))
        cs.operations = out
        return cs

    def walk(res, seen):
        xo = res.get("/XObject")
        if not xo:
            return
        for _, v in xo.get_object().items():
            o = v.get_object()
            if o.get("/Subtype") != "/Form" or id(o) in seen:
                continue
            seen.add(id(o))
            sub = o.get("/Resources")
            if sub is None:
                continue
            o.set_data(filt(o, sub.get_object(), matrici.get(id(o))).get_data())
            walk(sub.get_object(), seen)

    page = w.pages[0]
    mb = page.mediabox
    mx0, my1 = float(mb.left), float(mb.top)
    res = page["/Resources"]
    # la matrice si segue solo se c'e' un'area riservata da cercare: su un
    # foglio come Colazione il flusso sono centinaia di migliaia di operazioni
    page.replace_contents(filt(page.get_contents(), res,
                               (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                               if variabili else None))
    walk(res, set())
    with open(dst, "wb") as fh:
        w.write(fh)
    return dst


# Come si rimette dritta una grafica girata. Il verso e' lo STESSO
# dell'angolo, non l'opposto: pdfium misura l'angolo nello spazio del PDF, con
# la y in su, mentre la texture ha la y in giu', quindi il senso e' gia'
# rovesciato una volta. Verificato guardando le due direzioni affiancate.
GIRO_TEXTURE = {90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}

# Quanto puo' essere lontano da quadrato un pannello perche' girarlo di 90
# gradi non lo stiri. Vedi gira_sulla_grafica.
QUADRATO = float(os.environ.get("PACK3D_QUADRATO", "0.9"))


def verso_della_grafica(pdf, panels, page_no=0):
    """Di quanto e' girata la grafica in ogni pannello. {} se non lo dice."""
    from . import tracciati
    try:
        return tracciati.verso_grafica(
            pdf, {n: (p.x0, p.y0, p.x1, p.y1) for n, p in panels.items()}, page_no)
    except Exception:
        return {}


def gira_sulla_grafica(tex, panels, verso):
    """Rimette dritte le texture seguendo la grafica. (fatte, non fatte).

    La regola e' che il modello segue la GRAFICA e non il disegno tecnico: il
    DT dice come e' impaginato il foglio, la grafica dice come si legge il
    pack in mano.

    Un solo limite, e non e' un compromesso: e' l'altra regola, quella che dice
    di non distorcere mai la grafica. Il pannello sul foglio e la faccia sul
    solido hanno le stesse proporzioni - vengono dalla stessa fustella - quindi
    girare la texture di 90 gradi la mappa su una faccia con le proporzioni
    scambiate. Su un pannello quasi quadrato non si vede; su un fianco stretto
    si', ed e' anche il caso in cui girare sarebbe sbagliato: su un fianco da
    38 x 191 il testo verticale E' il progetto, non un errore di impaginato,
    mentre su un pannello da 188 x 191 vuol dire che il foglio e' girato.
    Il rapporto di forma distingue i due casi.

    Dove non si puo' girare senza stirare, non si gira e lo si dichiara: la
    regola dice di seguire la grafica, non di consegnare grafica deformata.
    """
    fatte, no = [], []
    for nome, gradi in sorted(verso.items()):
        if not gradi or nome not in tex:
            continue
        p = panels[nome]
        lati = abs(p.x1 - p.x0), abs(p.y1 - p.y0)
        quadrato = min(lati) / max(max(lati), 1e-9) >= QUADRATO
        if gradi == 180 or quadrato:
            tex[nome] = tex[nome].transpose(GIRO_TEXTURE[gradi])
            fatte.append("%s di %d" % (nome, gradi))
        else:
            no.append("%s (%d gradi, %.0f x %.0f)"
                      % (nome, gradi, lati[0] * PT2MM, lati[1] * PT2MM))
    return fatte, no


def senza_coperture(pdf, page_no=0, extra=()):
    """(pdf da cui ritagliare la texture, nomi delle coperture togliute).

    Le lastre tecniche dichiarate per nome sono l'informazione piu' attendibile
    che un file possa dare, dopo i Processing Steps: `REGOLE.md` le mette al
    livello 3-4 dei cinque, sopra l'euristica su spessore e colore. Finora
    pero' le leggeva solo `tools.classify_technical`, che e' uno strumento per
    l'agente: la costruzione deterministica non le guardava, e strappava le
    separazioni solo se un caso calibrato le elencava a mano.

    Il caso che l'ha fatto vedere: su un astuccio Nutella Donut la vernice si
    chiama `Water Based Gloss Varnish` e copre tutto il pannello. pdfium la
    rende opaca, quindi la texture uscirebbe rosa piena. Nessuna euristica su
    spessore e colore la puo' prendere - non e' un tratto sottile, e' un pieno
    grande quanto la grafica - mentre il nome lo dice senza ambiguita'.

    Si strappano solo le COPERTURE - vernice, bianco coprente, cold seal - e
    non tutte le lastre tecniche: vedi techink.COPERTURE_FRASI per il perche',
    che e' misurato in secondi e in MB.

    E si toglie SOLO per la texture, mai per l'analisi: il disegno tecnico e'
    quello che fa misurare il pack, e togliendolo prima non si misura piu'
    niente.

    Alle coperture dichiarate per nome si aggiungono le **aree riservate che
    il file scrive ma non nomina** - vedi `techink.aree_riservate`. Si cercano
    solo quando il file non ha livelli tecnici: se i livelli ci sono la
    pulizia e' gia' esatta, e quella ricerca costa una passata di testo che
    sul K Brioss STD sono 2,9 secondi buttati.

    `extra` sono le lastre che l'agente ha riconosciuto GUARDANDO, per i file
    che l'area riservata non la scrivono da nessuna parte - vedi
    `tools.area_riservata`. Arrivano gia' confermate a occhio, e qui si
    strappano insieme alle altre: una passata sola invece di due.
    """
    from . import strati, techink
    try:
        import pypdf
        pagina = pypdf.PdfReader(pdf).pages[page_no]
        lastre = set(techink.technical_separations(
            pagina, prova=techink.copertura).values())
    except Exception:
        return pdf, []
    # {lastra: didascalia} delle aree riservate trovate leggendo la scritta:
    # si chiamano con un numero di Pantone, e se servono i dati variabili lo
    # dice solo la didascalia
    etichettate = {}
    try:
        if not strati.tecnici(pdf, page_no):
            etichettate = techink.aree_riservate(pdf, page_no)
            lastre |= set(etichettate)
    except Exception:
        pass
    lastre |= {techink._norm(n) for n in (extra or ()) if str(n).strip()}
    lastre = sorted(lastre)
    if not lastre:
        return pdf, []
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        # Tolta l'area riservata resta la sua ETICHETTA, se non e' scritta in
        # bianco: sul Kinder Cards T2 "Best Before Area" e "POSITIONING AREA
        # FOR EAN CODE (if requested)", marrone scuro, restavano stampate sui
        # fianchi del pack. I riquadri delle aree tolte vanno a chi rende la
        # texture, che dentro spegne le scritte: vedi `strati.dividi`.
        riquadri = []
        variabili = {n for n in lastre
                     if techink.DATI_VARIABILI.search(n)
                     or techink.DATI_VARIABILI.search(etichettate.get(n, ""))}
        pulito = strip_separations(pdf, tmp.name, lastre, riquadri=riquadri,
                                   variabili=variabili)
        if riquadri:
            strati.segna_riservate(pulito, riquadri)
        return pulito, lastre
    except Exception:
        # meglio una texture con un residuo tecnico che nessun modello
        return pdf, []


def texture_astuccio(pdf, panels, dpi, page_no=0, clean=True, lastre_extra=(),
                     nero_deciso=None, colata_riquadro=None):
    """Le texture di un astuccio, pulite e girate sul verso della grafica.

    L'unico punto in cui i tre passaggi si applicano, cosi' non possono piu'
    divergere fra il server e la riga di comando.

    Restituisce `(texture, avvisi)`, con gli avvisi gia' scritti come vanno
    mostrati a chi guarda il modello.
    """
    from . import folding
    pulito, lastre = senza_coperture(pdf, page_no, lastre_extra)
    avvisi = []
    tex = folding.rasterize_panels(pulito, panels, dpi=dpi, page_no=page_no,
                                   clean=clean, note=avvisi,
                                   nero_deciso=nero_deciso,
                                   colata_riquadro=colata_riquadro)
    giri, storti = gira_sulla_grafica(
        tex, panels, verso_della_grafica(pulito, panels, page_no))
    if lastre:
        avvisi.append("coperture togliute per nome: %s" % ", ".join(lastre))
    if giri:
        avvisi.append("girato sul verso della grafica: %s" % ", ".join(giri))
    if storti:
        avvisi.append("GRAFICA GIRATA ma il pannello non e' quadrato, lasciato "
                      "com'e' per non stirarla: %s" % ", ".join(storti))
    return tex, avvisi
