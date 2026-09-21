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


def strip_separations(src, dst, drop):
    """Toglie le lastre tecniche eliminando le operazioni di disegno.

    Colorarle di bianco non basta: un tratto tecnico sopra la grafica
    lascerebbe una riga bianca. Il filtro scende anche dentro i Form XObject,
    dove spesso stanno cold seal e bianco coprente.
    """
    import pypdf
    from pypdf.generic import ContentStream

    # `clone_from` e non `append`: append PERDE /OCProperties, e con quello
    # perde i livelli. Un astuccio che ha insieme una vernice e la colata su un
    # livello suo usciva dallo strappo senza livelli, e la sostituzione della
    # colata non partiva - in silenzio, perche' a quel punto il livello non
    # c'era piu' davvero.
    w = pypdf.PdfWriter(clone_from=src)
    drop = {d.lower() for d in drop}

    def names(res):
        out = set()
        cs = res.get("/ColorSpace")
        if not cs:
            return out
        for k, v in cs.get_object().items():
            try:
                o = v.get_object()
                if o[0] == "/Separation":
                    if str(o[1]).lstrip("/").replace("#20", " ").lower() in drop:
                        out.add(str(k))
                elif o[0] == "/DeviceN":
                    nm = [str(x).lstrip("/").replace("#20", " ").lower() for x in o[1]]
                    if nm and all(n in drop for n in nm):
                        out.add(str(k))
            except Exception:
                pass
        return out

    FILL, STROKE = {b"f", b"F", b"f*"}, {b"S", b"s"}
    BOTH = {b"B", b"B*", b"b", b"b*"}

    def filt(obj, res):
        bad = names(res)
        cs = ContentStream(obj, w)
        ncs = scs = None
        out = []
        for ops, op in cs.operations:
            if op == b"cs":
                ncs = str(ops[0])
            elif op == b"CS":
                scs = str(ops[0])
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
            o.set_data(filt(o, sub.get_object()).get_data())
            walk(sub.get_object(), seen)

    page = w.pages[0]
    res = page["/Resources"]
    page.replace_contents(filt(page.get_contents(), res))
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


def senza_coperture(pdf, page_no=0):
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
    """
    from . import techink
    try:
        import pypdf
        pagina = pypdf.PdfReader(pdf).pages[page_no]
        lastre = sorted(set(techink.technical_separations(
            pagina, prova=techink.copertura).values()))
    except Exception:
        return pdf, []
    if not lastre:
        return pdf, []
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        return strip_separations(pdf, tmp.name, lastre), lastre
    except Exception:
        # meglio una texture con un residuo tecnico che nessun modello
        return pdf, []


def texture_astuccio(pdf, panels, dpi, page_no=0, clean=True):
    """Le texture di un astuccio, pulite e girate sul verso della grafica.

    L'unico punto in cui i tre passaggi si applicano, cosi' non possono piu'
    divergere fra il server e la riga di comando.

    Restituisce `(texture, avvisi)`, con gli avvisi gia' scritti come vanno
    mostrati a chi guarda il modello.
    """
    from . import folding
    pulito, lastre = senza_coperture(pdf, page_no)
    avvisi = []
    tex = folding.rasterize_panels(pulito, panels, dpi=dpi, page_no=page_no,
                                   clean=clean, note=avvisi)
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
