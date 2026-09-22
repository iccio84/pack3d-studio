"""
Il vassoio espositore: un fondo e quattro pareti che si alzano.

Non e' un astuccio e non e' un flowpack, ed e' la terza famiglia. Il display
del Milch-Schnitte Raspberry cadeva nel ramo flowpack e usciva "saldature di
testa non riconosciute": un messaggio che non dice niente a chi ha in mano un
vassoio.

La forma e' la piu' semplice di tutte: un rettangolo centrale - il **fondo** -
con una parete attaccata a ciascuno dei suoi quattro lati, e le alette agli
angoli che tengono su le pareti. Le quattro pareti NON sono alte uguali: su un
display da scaffale i fianchi lunghi sono alti perche' reggono la pila, e la
parete davanti e' bassa perche' il prodotto si deve vedere. Sul Milch-Schnitte
sono 98,6 e 98,5 contro 40,0 e 40,5.

Quello che lo distingue si legge nella griglia della fustella, e non e'
un'euristica: **cinque colonne e tre fasce**, con la colonna e la fascia di
mezzo che coincidono sul fondo. Le due colonne sottili fra fondo e pareti sono
la cordonatura, due millimetri di spessore del cartoncino.

    colonne (mm)   98,6 | 2,0 | 145,5 | 2,0 | 98,5
    fasce   (mm)   40,0 | 385,9 | 40,5

Le alette angolari non vengono costruite: da fuori non si vedono, perche' le
copre la parete che tengono. Il modello e' fondo piu' quattro pareti, con lo
spessore del cartoncino che ci mette `folding.guscio`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dieline import PT2MM

# la cordonatura fra fondo e parete: due tratti vicini, non un pannello
CORDONATURA_MAX = 6.0
# una parete sotto questa altezza non e' una parete, e' un'aletta
PARETE_MINIMA = 8.0


@dataclass
class Vassoio:
    """Un vassoio, in millimetri. Le pareti girano da nord in senso orario."""
    fondo_w: float
    fondo_h: float
    pareti: dict          # {"nord": alt, "est": alt, "sud": alt, "ovest": alt}
    riquadri: dict        # {nome: (x0, y0, x1, y1) in punti PDF}
    warnings: list = field(default_factory=list)

    @property
    def dims_mm(self):
        """Ingombro del vassoio montato: larghezza, profondita', altezza."""
        return (self.fondo_w, self.fondo_h, max(self.pareti.values()))


def _fasce(valori):
    """Da una lista di coordinate alle luci fra l'una e l'altra, in mm."""
    return [(b - a) * PT2MM for a, b in zip(valori, valori[1:])]


def riconosci(d):
    """`Vassoio` dalla griglia della fustella, o `None` se non lo e'.

    `d` e' quello che restituisce `dieline.extract`. Si guarda la griglia e
    basta: cinque colonne con la seconda e la quarta sottili (cordonature),
    tre fasce, e la colonna di mezzo larga quanto il fondo. Niente di
    stimato - o la griglia ha questa forma o non ce l'ha.
    """
    xs = sorted({round(v, 2) for v in getattr(d, "xs", [])})
    ys = sorted({round(v, 2) for v in getattr(d, "ys", [])})
    if len(xs) != 6 or len(ys) != 4:
        return None
    col = _fasce(xs)
    ban = _fasce(ys)
    # [ovest | cordone | fondo | cordone | est]
    if not (col[1] <= CORDONATURA_MAX and col[3] <= CORDONATURA_MAX):
        return None
    ovest, fondo_w, est = col[0], col[2], col[4]
    nord, fondo_h, sud = ban[0], ban[1], ban[2]
    if min(ovest, est, nord, sud) < PARETE_MINIMA:
        return None
    if fondo_w <= max(ovest, est) * 0.5 or fondo_h <= max(nord, sud) * 0.5:
        return None

    riquadri = {
        "fondo": (xs[2], ys[1], xs[3], ys[2]),
        "ovest": (xs[0], ys[1], xs[1], ys[2]),
        "est":   (xs[4], ys[1], xs[5], ys[2]),
        "nord":  (xs[2], ys[0], xs[3], ys[1]),
        "sud":   (xs[2], ys[2], xs[3], ys[3]),
    }
    v = Vassoio(fondo_w=round(fondo_w, 1), fondo_h=round(fondo_h, 1),
                pareti={"nord": round(nord, 1), "est": round(est, 1),
                        "sud": round(sud, 1), "ovest": round(ovest, 1)},
                riquadri=riquadri)
    lunghe = sorted(v.pareti.values())
    if lunghe[-1] - lunghe[0] > 1.0:
        v.warnings.append(
            "pareti di altezze diverse (%s mm): normale su un display, dove i "
            "fianchi reggono la pila e il davanti lascia vedere il prodotto"
            % ", ".join("%.1f" % a for a in lunghe))
    return v


def facce(v: Vassoio, textures: dict):
    """Fondo e quattro pareti come quad 3D, pronti per `folding.guscio`.

    Stessa convenzione degli astucci - **y in alto**, vedi `folding.corners` -
    cosi' rasterizzatore, guscio ed export non vedono differenza fra un
    vassoio e un astuccio. Il fondo sta a y=0 e le pareti salgono.

    **La piega gira il ritaglio, e la texture va girata con lei.** Il bordo
    del ritaglio attaccato al fondo finisce sempre in BASSO sulla parete
    alzata: per la parete a nord quel bordo e' gia' quello di sotto e non
    serve niente, per quella a sud e' quello di sopra e il ritaglio va
    ribaltato di 180 gradi, per le due laterali e' un fianco e il ritaglio
    ruota di 90. Non e' una correzione a occhio: e' la stessa rotazione che fa
    il cartoncino quando lo pieghi.
    """
    W, P = v.fondo_w, v.fondo_h
    hx, hz = W / 2.0, P / 2.0
    UV = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    a = v.pareti
    out = []

    def aggiungi(nome, quad, giro=None):
        t = textures.get(nome)
        if t is None:
            return
        if giro is not None:
            t = t.transpose(giro)
        out.append({"name": nome, "quad": quad, "uv": list(UV), "tex": t})

    from PIL import Image as _I

    # Fondo: visto da sopra, la riga alta del ritaglio confina con NORD.
    aggiungi("fondo", [(-hx, 0.0, -hz), (+hx, 0.0, -hz),
                       (+hx, 0.0, +hz), (-hx, 0.0, +hz)])
    # Nord, sul retro: il ritaglio e' gia' nel verso giusto.
    aggiungi("nord", [(+hx, a["nord"], -hz), (-hx, a["nord"], -hz),
                      (-hx, 0.0, -hz), (+hx, 0.0, -hz)])
    # Sud, davanti: il bordo attaccato al fondo e' quello alto, quindi 180.
    aggiungi("sud", [(-hx, a["sud"], +hz), (+hx, a["sud"], +hz),
                     (+hx, 0.0, +hz), (-hx, 0.0, +hz)], _I.ROTATE_180)
    # Est e ovest: il bordo attaccato al fondo e' un fianco, quindi 90.
    aggiungi("est", [(+hx, a["est"], +hz), (+hx, a["est"], -hz),
                     (+hx, 0.0, -hz), (+hx, 0.0, +hz)], _I.ROTATE_90)
    aggiungi("ovest", [(-hx, a["ovest"], -hz), (-hx, a["ovest"], +hz),
                       (-hx, 0.0, +hz), (-hx, 0.0, -hz)], _I.ROTATE_270)
    return out
