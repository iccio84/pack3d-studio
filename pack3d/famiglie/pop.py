"""
I materiali POP, i materiali per il punto vendita: totem, e poi dondolini,
strip, vele, angolari, portaprezzi, sticker.

Si caricano da un'altra finestra di Glam Lab, «Crea materiali POP 3D da
PDF»: la stessa pagina dello Space con pop=1 nell'indirizzo, e le voci dei
materiali al posto di quelle dei pack (GLAM.md, sezione 10). Per ora c'e' il
totem. Il codice non lo sa ancora costruire: la sua riga del registro
(`registro.RICONOSCIMENTO`, «materiale POP») ferma la lettura col motivo, e
il caso va in coda col PDF (`server.caso_fermo`, CODA.md), da dove parte la
famiglia, come per l'incarto avvolto.
"""

# i materiali che la finestra POP dichiara; il loro nome a parole, per la
# coda e per il controllo dell'AI, sta in `comune.NOMI_KIND`
MATERIALI_POP = ("totem",)


def e_pop(kind):
    """Il tipo dichiarato e' un materiale POP."""
    return kind in MATERIALI_POP


# le finestre di Glam Lab dove arrivano i modelli: quella dei pack, e quella
# dei materiali POP (intestazione `X-Model-Section: pop`, GLAM.md, sezione 10)
SEZIONI_GLAM = {None: "Costruisci modello 3D da PDF",
                "pop": "Crea materiali POP 3D da PDF"}


def sezione_glam(kind):
    """La finestra di Glam del modello di questo tipo dichiarato: "pop" per
    un materiale POP, None per un pack."""
    return "pop" if e_pop(kind) else None


def analisi_pop(pdfs, kind):
    """La lettura di un materiale POP. Nessuno si sa ancora costruire: si
    ferma col motivo, e il caso va in coda col PDF."""
    raise ValueError("%s: il codice non sa ancora costruirlo. Il caso va a chi "
                     "corregge il codice, che parte dal tuo PDF" % kind)
