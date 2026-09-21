"""
I livelli dell'artwork: il modo giusto di separare il disegno tecnico.

Il disegno tecnico non si indovina dal colore. E' la lezione piu' cara di
questo progetto, e adesso e' misurata: la maschera sceglieva pieni e scritte
in base alla tinta - "cromatica e non di una tinta piatta, quindi tecnica" - e
su tutto il parco quella regola non ha mai tolto un solo pixel di disegno
tecnico che i tratti non togliessero gia'. Su sei file su nove non cambia
niente; sugli altri tre cancella **grafica**:

    K Brioss STD   il logo `Brioss`, la tabella nutrizionale, "CON LATTE",
                   il testo legale - il 4,4% del foglio
    K Pingui T6    il bollino "x6" e l'icona del pack
    K Brioss       lo 0,75% del foglio, tutto grafica

Il motivo non e' una soglia sbagliata: e' che **una lastra tecnica usa colori
che usa anche la grafica**. Il ciano di processo che traccia una quota e' lo
stesso ciano del logo Brioss; la Pantone di servizio e' la stessa del marchio;
il registro `All` e' nero come il testo. Nessuna soglia separa due cose che
hanno lo stesso colore.

Quello che invece lo dice senza ambiguita' e' il **livello**. Su K Brioss STD
il file ha otto OCG, e due si chiamano `Cutter` e `Legend`: spegnendo quelli si
toglie l'1,61% - la fustella e il cartiglio, esattamente - e il logo resta
intero. E' la stessa scala di certezza che REGOLE.md descrive da sempre, solo
usata anche per la maschera e non piu' solo per la diagnosi.

Restano i **tratti**: un filo di capello e' tecnico per geometria, non per
colore, e quello continua a valere anche senza livelli.
"""
from __future__ import annotations

import os
import tempfile


def livelli(pdf):
    """{nome minuscolo: riferimento} degli OCG della pagina."""
    import pypdf
    try:
        r = pypdf.PdfReader(pdf)
        oc = r.trailer["/Root"].get("/OCProperties")
        if not oc:
            return {}
        return {str(g.get_object().get("/Name", "")).strip().lower(): g
                for g in oc.get("/OCGs", [])}
    except Exception:
        return {}


def spegni(src, dst, nomi):
    """Scrive `dst` con quei livelli spenti. Restituisce i nomi spenti.

    E' una modifica di DIZIONARIO - l'OCG finisce in `/OCProperties/D/OFF` -
    e non costa la passata di pypdf sul flusso di contenuto, che su Colazione
    vale 7 secondi e 100 MB.

    `PdfWriter().append()` PERDE `/OCProperties`, e senza quello non c'e'
    niente da spegnere: si clona.
    """
    import pypdf
    from pypdf.generic import ArrayObject, NameObject
    nomi = {n.strip().lower() for n in nomi}
    w = pypdf.PdfWriter(clone_from=src)
    oc = w._root_object.get("/OCProperties")
    if oc is None:
        return []
    via = [g for g in oc.get("/OCGs", [])
           if str(g.get_object().get("/Name", "")).strip().lower() in nomi]
    if not via:
        return []
    d = oc.get("/D")
    d = d.get_object() if hasattr(d, "get_object") else d
    off = ArrayObject(list(d.get("/OFF") or []))
    off.extend(via)
    d[NameObject("/OFF")] = off
    with open(dst, "wb") as fh:
        w.write(fh)
    return [str(g.get_object().get("/Name")) for g in via]


def tecnici(pdf, page_no=0):
    """I nomi dei livelli che NON vanno stampati sul modello.

    Tre criteri, tutti per nome e nessuno per colore: i Processing Steps
    ISO 19593-1, i nomi di livello dichiaratamente tecnici
    (`techink.OCG_TECH`) e i nomi che collocano una separazione fra le lastre
    tecniche (`techink.tecnica`) - `Cutter` passa di li'.
    """
    from . import techink
    nomi = set(livelli(pdf))
    if not nomi:
        return set()
    fuori = set()
    try:
        import pypdf
        r = pypdf.PdfReader(pdf)
        for v in techink.processing_steps(r, r.pages[page_no]).values():
            n = (v.get("name") or "").strip().lower()
            if n in nomi:
                fuori.add(n)
    except Exception:
        pass
    for n in nomi:
        if n in techink.OCG_TECH or techink.tecnica(n):
            fuori.add(n)
    return fuori


def senza_tecnici(pdf, page_no=0):
    """`(pdf da cui ritagliare la texture, nomi dei livelli spenti)`.

    Se il file i livelli non ce li ha, o nessuno e' tecnico, torna il file
    com'e': chi non ha livelli non paga niente.
    """
    nomi = tecnici(pdf, page_no)
    if not nomi:
        return pdf, []
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    try:
        spenti = spegni(pdf, tmp.name, nomi)
        if not spenti:
            os.unlink(tmp.name)
            return pdf, []
        return tmp.name, spenti
    except Exception:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        return pdf, []
