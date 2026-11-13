"""
I materiali POP, i materiali per il punto vendita: totem, e poi dondolini,
strip, vele, angolari, portaprezzi, sticker.

Si caricano da un'altra finestra di Glam Lab, «Crea materiali POP 3D da
PDF»: la stessa pagina dello Space con pop=1 nell'indirizzo, e le voci dei
materiali al posto di quelle dei pack (GLAM.md, sezione 10).

**Il POP sta qui, e solo qui** (regole/pop.md, *Il confine*). Le famiglie dei
pack - flowpack, astucci, vassoi... - non si toccano per un materiale POP, e
il POP non si tocca per un pack: una PR verso coda-settimana o e' POP o e' dei
pack, e `prove/confini.py` lo controlla. Le parti comuni leggono il POP da
questo pacchetto e non lo nominano: il registro delle famiglie
(`MATERIALI_POP`, `analisi`, `COSTRUZIONI`), i tipi dichiarati
(`NOMI_POP`), la coda e la routine (`sezione_glam`). Un materiale nuovo
entra qui, nella pagina (la sua voce) e in regole/pop.md.

Per ora ci sono il totem e l'espositore. Lo Space non li costruisce ancora:
la loro lettura si ferma col motivo, e il caso va in coda col PDF
(`server.caso_fermo`, CODA.md), da dove parte la famiglia. Le costruzioni
in prova, dai PDF dei casi: `espositore.monta` e `totem.monta`.
"""

# I materiali che la finestra POP dichiara, col loro nome a parole per la
# coda e per il controllo dell'AI (`famiglie.comune.NOMI_KIND` li prende da
# qui, e cosi' `KIND_NOTI` e i sinonimi).
# Il nome di un materiale non puo' essere un tipo o un sinonimo dei pack:
# «espositore», per i pack, vuol dire vassoio (`comune.SINONIMI_KIND`), e
# dichiararlo POP avrebbe cambiato strada ai pack. Per questo `espositore_pop`.
NOMI_POP = {
    "totem": "totem (materiale POP: espositore da terra, un pannello piatto o "
             "curvato in piedi sulla sua base, anche con i popup)",
    "espositore_pop": "espositore (materiale POP: una struttura da banco o da "
                      "terra coi ripiani o i vani dove stanno i prodotti)",
}
MATERIALI_POP = tuple(NOMI_POP)

# Le costruzioni dei materiali POP, come `famiglie.registro.COSTRUZIONI`: per
# il materiale letto (`info["kind"]`) la funzione che prepara la costruzione.
# Il registro le aggiunge alle sue. Ancora nessuna.
COSTRUZIONI = {}


def e_pop(kind):
    """Il tipo dichiarato e' un materiale POP."""
    return kind in NOMI_POP


def analisi(pdfs, kind):
    """La lettura di un materiale POP: la riga «materiale POP» del registro
    passa da qui. Nessuno si sa ancora costruire: si ferma col motivo, e il
    caso va in coda col PDF."""
    nome = NOMI_POP[kind].split(" (")[0]
    raise ValueError("%s: il codice non sa ancora costruirlo. Il caso va a chi "
                     "corregge il codice, che parte dal tuo PDF" % nome)


# Le finestre di Glam Lab dove arrivano i modelli: quella dei pack, e quella
# dei materiali POP (intestazione `X-Model-Section: pop`, GLAM.md, sezione 10)
SEZIONI_GLAM = {None: "Costruisci modello 3D da PDF",
                "pop": "Crea materiali POP 3D da PDF"}


def sezione_glam(kind):
    """La finestra di Glam del modello di questo tipo dichiarato: "pop" per
    un materiale POP, None per un pack."""
    return "pop" if e_pop(kind) else None
