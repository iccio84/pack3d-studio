"""
Il secondo tentativo prima della coda (regole/decisioni.md, *Un
deterministico che fallisce il meno possibile*, punto 3).

Il proprietario, il 20 novembre 2026: «preferisco che il deterministico
fallisca il meno possibile a discapito del tempo». Se la lettura si ferma, o
il controllo dell'AI dice sbagliato o dubbio, il codice riprova da solo con
le letture successive e le soglie piu' larghe, ricostruisce e fa
ricontrollare; il caso va alla routine solo quando sono finite.

Questo modulo tiene due cose.

- **Il tentativo in corso** (`Tentativo`, in una ContextVar: vale per il
  thread che costruisce, e un altro thread non lo vede). Le letture lo
  consultano in pochi punti - `strade.scegli` salta gli astucci gia'
  scartati (`escluso`), `artwork.astuccio_sulla_grafica` legge il foglio nel
  verso che il tentativo impone (`giro_forzato`), il registro salta la prova
  scartata (`prove_scartate`), le soglie si allargano (`larghe`) - e ci
  scrivono cosa hanno visto (`osserva`): la prova che ha detto «e' mio»,
  l'astuccio scelto, se c'erano altre letture plausibili, se la grafica
  diceva il verso. Fuori da un tentativo, o nel primo, tutto e' com'era: le
  funzioni tornano i valori di sempre.
- **Il giro** (`Giro`): la memoria dei tentativi di una costruzione - le
  letture scartate, i versi provati, le prove scartate -, il piano del
  prossimo (`prossimo`) e il tetto di tempo (`TETTO_S`, tre minuti in tutto,
  la prima lettura compresa).

Il giro parte solo col controllo dell'AI acceso, o con l'oracolo delle prove
(`oracolo`): una lettura piu' larga che nessuno conferma sarebbe un modello
sbagliato in silenzio. Senza, tutto resta come prima, e il parco - che gira
col controllo spento - non cambia per costruzione.

L'ordine dei tentativi (`Giro.prossimo`), ognuno solo se puo' dare un
modello diverso da quelli gia' provati:

1. **seconda lettura**: sugli astucci, la plausibile successiva del
   punteggio (`pack3d.strade`), un astuccio diverso, nello stesso verso;
2. **altro verso**: gli altri versi del foglio, quando niente dice il verso
   (nessuna faccia con testo vivo, o la grafica non d'accordo in nessuno);
3. **soglie larghe**: tutte le strade della fustella anche se quella per
   colore e' forte, e le letture plausibili fino a `COSTO_MAX_LARGO`; da li'
   in poi restano larghe;
4. **altra forma**: la prova successiva del registro che dice «e' mio»,
   saltando quella scartata (`famiglie.registro.prove_dopo`): dichiarato
   cartotecnico, la punta, la coppa, il tubo dopo l'astuccio; dentro la
   tipologia dichiarata, mai fuori.

Quando la prima lettura si ferma non c'e' una seconda plausibile: si
comincia dalle soglie larghe.

L'oracolo (`PACK3D_ORACOLO`), per provare il giro senza spendere: un giudice
finto al posto dell'AI, che confronta il modello col modello approvato del
parco (`prove/parco.py --oracolo`). Mai sullo Space.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace

# Tre minuti in tutto, dalla lettura al verdetto dell'ultimo tentativo: un
# tentativo nuovo non parte se, durando quanto il precedente, sforerebbe.
TETTO_S = float(os.environ.get("PACK3D_TENTATIVI_S", "180"))
# Quanti tentativi al massimo, la prima lettura compresa: il tetto di tempo
# di solito si ferma prima.
TENTATIVI_MAX = 6
# Le soglie larghe degli astucci (`dieline.plausibili`): una lettura vale
# fino a questo costo geometrico, invece di `dieline.COSTO_MAX`.
COSTO_MAX_LARGO = 3.0

# cosa fa ogni tentativo, come lo dicono la pagina e le statistiche
PRIMA = "prima lettura"
SECONDA = "seconda lettura"
VERSO = "altro verso"
LARGHE = "soglie larghe"
FORMA = "altra forma"
MONTAGGIO = "altro montaggio"
VERSO_PACK = "altro verso del pack"
COME = {SECONDA: "la seconda lettura del punteggio",
        VERSO: "un altro verso del foglio",
        LARGHE: "le soglie piu' larghe",
        FORMA: "un'altra forma della famiglia",
        MONTAGGIO: "il vassoio montato come coperchio",
        VERSO_PACK: "il pack girato attorno al fronte"}

# l'inizio delle righe che il giro aggiunge agli avvisi: non entrano
# nell'impronta della lettura (`firma`)
RIGA = "TENTATIVO"
GIRI = (0, 90, 180, 270)


class Uguale(Exception):
    """Il tentativo ha dato una lettura o un modello che un tentativo prima
    ha gia' dato: non si guarda due volte."""


@dataclass
class Tentativo:
    """Un tentativo: il numero (1 e' la prima lettura), cosa fa, e cosa la
    lettura deve fare diversamente. `osservato` lo riempie la lettura."""
    n: int = 1
    cosa: str = PRIMA
    larghe: bool = False
    giro: int | None = None
    escludi: tuple = ()
    prove_scartate: frozenset = frozenset()
    # il vassoio montato come coperchio, quando nessuna scritta lo dice
    # (`vassoio.montaggio`)
    montaggio: str | None = None
    # nel riempimento, il pack girato di tanti gradi attorno al fronte,
    # quando il suo verso non si legge (`riempimento.gira_il_pack`)
    gira_pack: int | None = None
    osservato: dict = field(default_factory=dict)

    @property
    def neutro(self):
        """Se legge come la lettura di sempre: allora valgono anche le
        memorie delle letture (`artwork._SULLA_GRAFICA`)."""
        return (not self.larghe and self.giro is None and not self.escludi
                and not self.prove_scartate and self.montaggio is None
                and self.gira_pack is None)

    def descrivi(self):
        return COME.get(self.cosa, self.cosa)


_ORA = contextvars.ContextVar("pack3d_tentativo", default=None)


@contextmanager
def dentro(t):
    """Le letture di questo blocco fanno il tentativo `t`."""
    tok = _ORA.set(t)
    try:
        yield t
    finally:
        _ORA.reset(tok)


def ora():
    return _ORA.get()


# --- quello che le letture chiedono e dicono ------------------------------

def larghe():
    t = _ORA.get()
    return bool(t and t.larghe)


def costo_max(di_serie):
    """Il costo geometrico oltre cui una lettura dell'astuccio non vale."""
    return max(di_serie, COSTO_MAX_LARGO) if larghe() else di_serie


def giro_forzato():
    t = _ORA.get()
    return t.giro if t else None


def prove_scartate():
    t = _ORA.get()
    return t.prove_scartate if t else frozenset()


def neutro():
    t = _ORA.get()
    return t is None or t.neutro


def montaggio():
    t = _ORA.get()
    return t.montaggio if t else None


def gira_pack():
    t = _ORA.get()
    return t.gira_pack if t else None


def escluso(lettura):
    """Se la lettura dell'astuccio da' un astuccio gia' scartato da un
    tentativo prima (stesso modello, stesso verso: `dieline.stesso_modello`)."""
    t = _ORA.get()
    if not t or not t.escludi or getattr(lettura, "d", None) is None:
        return False
    from . import dieline as dl
    return any(dl.stesso_modello(lettura, s) for s in t.escludi
               if getattr(s, "tipo", None) is None)


def escluso_display(impronta):
    """Se la lettura della Trade Unit (`vassoio.LetturaTU.impronta`) da' un
    display gia' scartato da un tentativo prima (`vassoio.stesso_display`)."""
    t = _ORA.get()
    if not t or not t.escludi:
        return False
    from . import vassoio
    return any(vassoio.stesso_display(impronta, s) for s in t.escludi
               if getattr(s, "tipo", None) == "vassoio")


def osserva(**cosa):
    """La lettura dice cosa ha visto: `famiglia` (la prova del registro),
    `astuccio` (`impronta` della lettura scelta), `altre` (quante altre
    letture plausibili danno un astuccio diverso), `giro`, `muto` (niente
    dice il verso); sulla Trade Unit `vassoio` (`vassoio.LetturaTU.impronta`)
    e `muto_montaggio` (niente dice se il vassoio e' un coperchio); nel
    riempimento `muto_pack` (il pack non sa il suo verso)."""
    t = _ORA.get()
    if t is not None:
        t.osservato.update(cosa)


def impronta(lettura):
    """Quello che serve a `dieline.stesso_modello` di una lettura, senza
    tenersi dietro la fustella."""
    d = lettura.d
    return SimpleNamespace(giro=lettura.giro, d=SimpleNamespace(
        layout=d.layout, chiuso=d.chiuso, panels=frozenset(d.panels),
        dims_mm=tuple(d.dims_mm), finestra_mm=d.finestra_mm))


def firma(info):
    """L'impronta di una lettura del registro: due tentativi con la stessa
    non si costruiscono due volte."""
    meta = [str(m) for m in info.get("meta") or [] if not str(m).startswith("TENTATIV")]
    return hashlib.sha256(json.dumps([info.get("kind"), info.get("title"), meta],
                                     ensure_ascii=False).encode()).hexdigest()


# --- il giro --------------------------------------------------------------

class Giro:
    """I tentativi di una costruzione: la memoria, il piano e il tetto.

    `attivo` falso (controllo dell'AI spento): un tentativo solo, il primo,
    come prima. `kind` e' la tipologia dichiarata."""

    def __init__(self, attivo, kind=None, tetto=TETTO_S, orologio=time.time):
        self.attivo = bool(attivo)
        self.kind = kind
        self.tetto = tetto
        self.orologio = orologio
        self.inizio = orologio()
        self.fatti = []             # dict(n, cosa, esito, motivo, secondi)
        self.escludi = []
        self.giri = set()
        self.prove = set()
        self.larghe = False
        self.firme = set()
        self.glb = set()
        self.ultimo = None
        self.astuccio = None        # l'ultimo osservato con un astuccio
        self.montaggi = set()       # i montaggi del vassoio gia' provati
        self.giri_pack = set()      # i versi del pack del riempimento provati
        self.perche_finiti = ""
        self._dal = None
        self._scartata = None

    # chi costruisce dice quando comincia e com'e' andato ogni tentativo
    def primo(self):
        return self._comincia(Tentativo())

    def _comincia(self, t):
        self.ultimo = t
        self._dal = self.orologio()
        return t

    def gia_letto(self, info):
        """Se un tentativo prima ha gia' dato questa lettura (`firma`)."""
        f = firma(info)
        if f in self.firme:
            return True
        self.firme.add(f)
        return False

    def gia_costruito(self, glb):
        h = hashlib.md5(glb).hexdigest()
        if h in self.glb:
            return True
        self.glb.add(h)
        return False

    def esito(self, t, esito, motivo=""):
        """Com'e' andato il tentativo `t`: ok, dubbio, sbagliato, fermata,
        uguale (la stessa lettura o lo stesso modello di uno prima)."""
        secondi = round(self.orologio() - (self._dal or self.inizio), 1)
        self.fatti.append(dict(n=t.n, cosa=t.cosa, esito=esito,
                               motivo=str(motivo or "")[:200], secondi=secondi))
        oss = t.osservato
        if t.giro is not None:
            # il verso imposto e' provato, anche se la lettura si e' fermata
            self.giri.add(t.giro)
        if oss.get("astuccio") is not None:
            self.astuccio = dict(oss)
        if t.montaggio is not None:
            self.montaggi.add(t.montaggio)
        if t.gira_pack is not None:
            self.giri_pack.add(t.gira_pack)
        if esito == "ok":
            return
        if oss.get("astuccio") is not None:
            self.escludi.append(oss["astuccio"])
        if (oss.get("vassoio") is not None and self.kind == "vassoio"
                and not (t.montaggio or oss.get("muto_montaggio"))):
            # il display scartato non vince piu'; se e' muto si prova prima
            # montato come coperchio, sulla stessa lettura. Solo dichiarato
            # vassoio: nel riempimento lo scarto puo' essere del pack, e
            # senza il contenitore il tentativo del verso del pack si
            # fermava su «nessuno si legge come vassoio» (i display a scatola
            # T1x10 e T15, che non passano per il montaggio)
            self.escludi.append(oss["vassoio"])
        if oss.get("giro") is not None:
            self.giri.add(oss["giro"])
        if esito != "fermata" and oss.get("famiglia"):
            self._scartata = oss["famiglia"]

    def resta(self):
        return self.tetto - (self.orologio() - self.inizio)

    def _stima(self):
        """Quanto durera' il prossimo: quanto e' durato il piu' lungo dei
        tentativi che hanno costruito (una fermata costa poco)."""
        durate = [f["secondi"] for f in self.fatti if f["esito"] != "fermata"]
        return max(durate) if durate else 0.0

    def prossimo(self):
        """Il prossimo tentativo, o None se sono finiti (`perche_finiti`)."""
        if not self.attivo:
            return None
        if len(self.fatti) >= TENTATIVI_MAX:
            self.perche_finiti = "fatti %d tentativi" % len(self.fatti)
            return None
        if self._stima() > self.resta():
            self.perche_finiti = "finito il tempo (%d s)" % self.tetto
            return None
        t = self._piano()
        if t is None:
            self.perche_finiti = "nessun'altra lettura da provare"
            return None
        return self._comincia(t)

    def _nuovo(self, cosa, **k):
        k.setdefault("larghe", self.larghe)
        k.setdefault("escludi", tuple(self.escludi))
        k.setdefault("prove_scartate", frozenset(self.prove))
        return Tentativo(n=len(self.fatti) + 1, cosa=cosa, **k)

    def _piano(self):
        from .famiglie import registro
        ultimo = self.fatti[-1] if self.fatti else None
        oss = self.ultimo.osservato if self.ultimo else {}
        scartato = ultimo is not None and ultimo["esito"] not in ("ok", "fermata")
        ast = self.astuccio
        # 1. la plausibile successiva, nello stesso verso
        if (scartato and oss.get("famiglia") == "astuccio"
                and oss.get("astuccio") is not None and oss.get("altre")):
            return self._nuovo(SECONDA, giro=self.ultimo.giro)
        # sulla Trade Unit, il vassoio che nessuna scritta dice come si monta:
        # montato come coperchio, poi la plausibile successiva
        if (scartato and oss.get("famiglia") == "vassoio e display"
                and oss.get("vassoio") is not None):
            if oss.get("muto_montaggio") and "coperchio" not in self.montaggi:
                return self._nuovo(MONTAGGIO, montaggio="coperchio")
            if oss.get("altre"):
                if oss["vassoio"] not in self.escludi:
                    self.escludi.append(oss["vassoio"])
                return self._nuovo(SECONDA)
        # nel riempimento, il pack che non sa il suo verso: girato attorno al
        # fronte, un quarto, tre quarti, mezzo giro
        if scartato and oss.get("muto_pack"):
            # prima si disfa il giro che il flowpack ha dato al modello per
            # il marchio (`giro_pack`), poi gli altri
            fatto = int(oss.get("giro_pack") or 0)
            ordine = ([(360 - fatto) % 360] if fatto else []) + [90, 270, 180]
            for g in ordine:
                if g and g not in self.giri_pack:
                    return self._nuovo(VERSO_PACK, gira_pack=g)
        # 2. gli altri versi, quando niente dice il verso
        if ast is not None and ast.get("muto"):
            for g in GIRI:
                if g not in self.giri:
                    return self._nuovo(VERSO, giro=g)
        # 3. le soglie larghe: gli astucci e la Trade Unit
        if not self.larghe and self.kind in (None, "carton", "vassoio", "riempimento"):
            self.larghe = True
            return self._nuovo(LARGHE)
        # 4. la prova dopo nel registro
        nome = self._scartata
        if nome and nome not in self.prove and registro.prove_dopo(nome, self.kind):
            self.prove.add(nome)
            self._scartata = None
            return self._nuovo(FORMA)
        return None

    # per la pagina, gli avvisi, la coda e il controllo
    def riga(self):
        """La riga dei tentativi per gli avvisi e per la coda."""
        return "TENTATIVI: %s" % ("; ".join(
            "%d %s - %s%s" % (f["n"], f["cosa"], f["esito"],
                              ": " + f["motivo"][:120] if f["motivo"] else "")
            for f in self.fatti)) if self.fatti else ""

    def nota(self, t):
        """Per il controllo dell'AI: questo e' un tentativo dopo altri."""
        prima = [f for f in self.fatti if f["n"] < t.n]
        if not prima:
            return ""
        return ("questo modello e' il tentativo %d, con %s: i tentativi prima "
                "sono stati scartati (%s). Giudicalo da solo, sul PDF."
                % (t.n, t.descrivi(), "; ".join(
                    "%d %s: %s%s" % (f["n"], f["cosa"], f["esito"],
                                     " - " + f["motivo"][:100] if f["motivo"] else "")
                    for f in prima)))


def fase(t, perche):
    """La riga di stato della pagina mentre un tentativo lavora."""
    return ("%s: provo un'altra lettura, con %s (tentativo %d)…"
            % (perche, t.descrivi(), t.n))


# --- l'oracolo delle prove -------------------------------------------------
#
# `PACK3D_ORACOLO` e' un file JSON: per nome di caso (l'opzione `oracolo`
# che `prove/parco.py` mette in ogni richiesta), il modello approvato -
# `ingombro` in mm, `viste` (il PNG delle viste di `vista.viste`), `scala`.
# Il giudice dice ok se il modello costruito torna come lui, con la misura del
# banco delle varianti (`prove/parco.py varianti`): ingombro entro 1,5 mm,
# viste entro 3 livelli di grigio. `PACK3D_ORACOLO=pessimista` dice sempre
# sbagliato: il giro deve finire in tempo e mettere il caso in coda.

ORACOLO = os.environ.get("PACK3D_ORACOLO", "")
_ORACOLO_DATI = {}


def oracolo():
    return bool(ORACOLO)


def _dati_oracolo():
    if not _ORACOLO_DATI and ORACOLO and ORACOLO != "pessimista":
        with open(ORACOLO, encoding="utf-8") as fh:
            _ORACOLO_DATI.update(json.load(fh))
    return _ORACOLO_DATI


def giudica_oracolo(nome, glb_path):
    """Il verdetto dell'oracolo sul caso `nome`, come quello di
    `controllo.giudica`."""
    t0 = time.time()

    def v(esito, motivo):
        return dict(esito=esito, motivo="oracolo: " + motivo, difetti=[] if esito == "ok"
                    else [motivo], pack_nel_pdf="", modello="", residui_tecnici=False,
                    secondi=round(time.time() - t0, 1), oracolo=True)
    if ORACOLO == "pessimista":
        return v("sbagliato", "pessimista, dice sempre di no")
    caso = _dati_oracolo().get(str(nome or ""))
    if caso is None:
        return v("dubbio", "il caso non ha un modello approvato")
    import numpy as np
    from PIL import Image
    from . import vista
    from . import misure
    with open(glb_path, "rb") as fh:
        ingombro = misure.misura(fh.read())["ingombro"]
    s = float(caso.get("scala") or 1.0)
    atteso = [p * s for p in caso["ingombro"]]
    if max(abs(p - q) for p, q in zip(atteso, ingombro)) > 1.5 * s:
        return v("sbagliato", "ingombro %s invece di %s"
                 % ([round(x, 1) for x in ingombro], [round(x, 1) for x in atteso]))
    if s == 1.0 and caso.get("viste") and os.path.exists(caso["viste"]):
        A = np.asarray(Image.open(caso["viste"]).convert("L"), float)
        im, _ = vista.viste(glb_path, 512)
        B = np.asarray(im.convert("L"), float)
        d = float(np.abs(A - B).mean()) if A.shape == B.shape else 255.0
        if d > 3:
            return v("sbagliato", "viste diverse dall'approvato (%.1f livelli)" % d)
    return v("ok", "come il modello approvato (%s)" % caso.get("nome", "-"))
