"""
Le prove veloci: secondi, non i venti o quaranta minuti del parco.

Il parco dice CHE cosa si e' rotto - un caso, un modello cambiato - ma ci
mette da venti a quaranta minuti, e non dice dove. Queste dicono dove, e in
qualche secondo: la lettura della fustella, le misure del modello, il
registro delle famiglie, lo stato di un lavoro, i lavoratori, i file di un
caso nel registro, la cassa delle rese. Non usano
nessun file dei clienti - i PDF e i GLB li costruiscono loro - e girano anche
nelle Actions di questo repository, su ogni PR (`.github/workflows/prove.yml`).

    python3 -m unittest discover -s prove -p "test_*.py"

Le letture vere, sui PDF del parco, le dice in qualche minuto
`prove/parco.py letture` (vedi la), senza costruire.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, QUI)
os.environ.setdefault("PACK3D_LAVORATORI", "0")

from pack3d import dieline as dl, lavoratori, misure, stato  # noqa: E402


def _pdf(cartella, tratti=(), larghezza=600.0, altezza=600.0):
    """Un PDF di una pagina con questi tratti a penna: [(x0, y0, x1, y1)] in
    punti, con la y dal basso come nel contenuto del PDF."""
    import pypdf
    from pypdf.generic import NameObject, StreamObject
    w = pypdf.PdfWriter()
    pagina = w.add_blank_page(larghezza, altezza)
    contenuto = b"0.5 w 0 0 0 RG\n" + b"".join(
        b"%.2f %.2f m %.2f %.2f l S\n" % t for t in tratti)
    flusso = StreamObject()
    flusso.set_data(contenuto)
    pagina[NameObject("/Contents")] = w._add_object(flusso)
    f = os.path.join(cartella, "prova.pdf")
    with open(f, "wb") as fh:
        w.write(fh)
    return f


# Una fustella a griglia: cinque colonne di cordonature e quattro righe, come
# lo steso di un astuccio. In punti, y dal basso.
XS = (50.0, 150.0, 250.0, 350.0, 450.0)
YS = (100.0, 200.0, 400.0, 500.0)
GRIGLIA = ([(x, YS[0], x, YS[-1]) for x in XS]
           + [(XS[0], y, XS[-1], y) for y in YS])


class LetturaDellaFustella(unittest.TestCase):
    """`dieline`: i tratti della pagina, e la griglia che se ne legge."""

    def setUp(self):
        self.cartella = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.cartella, True))
        # la cassa dei tratti in una cartella sua, vuota
        self._cache = mock.patch.object(dl, "CACHE", os.path.join(self.cartella, "cache"))
        self._cache.start()
        self.addCleanup(self._cache.stop)
        dl._TRATTI.clear()

    def test_la_griglia_si_legge_dove_e_disegnata(self):
        d = dl.extract(_pdf(self.cartella, GRIGLIA))
        alto = 600.0
        self.assertEqual([round(x, 1) for x in d.xs], list(XS))
        self.assertEqual([round(y, 1) for y in d.ys],
                         sorted(round(alto - y, 1) for y in YS))
        self.assertEqual(tuple(round(v, 1) for v in d.bbox), (50.0, 100.0, 450.0, 500.0))

    def test_i_tratti_si_leggono_una_volta_e_tornano_uguali_dal_disco(self):
        pdf = _pdf(self.cartella, GRIGLIA)
        import pdfplumber
        with pdfplumber.open(pdf) as doc:
            diretti = dl._segments(doc.pages[0])
        primi = dl.segmenti(pdf)
        dl._TRATTI.clear()          # un altro processo: li trova sul disco
        dal_disco = dl.segmenti(pdf)
        self.assertEqual(primi, diretti)
        self.assertEqual(dal_disco, diretti)
        self.assertTrue(all(isinstance(s[4], tuple) for s in dal_disco))

    def test_la_chiave_e_il_contenuto_non_il_nome(self):
        pdf = _pdf(self.cartella, GRIGLIA)
        n = len(dl.segmenti(pdf))
        # lo stesso nome, un altro foglio: non deve tornare la griglia di prima
        pdf = _pdf(self.cartella, GRIGLIA[:3])
        self.assertNotEqual(len(dl.segmenti(pdf)), n)


def _glb(cartella, lati_mm):
    """Il GLB di una scatola di questi lati, in mm."""
    from pack3d import exporters
    x, y, z = (v / 1000.0 for v in lati_mm)
    V = np.array([[a, b, c] for a in (0, x) for b in (0, y) for c in (0, z)], float) * 1000.0
    T = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    UV = np.zeros((len(V), 2))
    from PIL import Image
    f = os.path.join(cartella, "prova.glb")
    exporters.write_glb_mesh(V, UV, T, Image.new("RGB", (8, 8), "white"), f)
    with open(f, "rb") as fh:
        return fh.read()


class Misure(unittest.TestCase):
    """`misure`: quanto misura il modello, e quando una misura e' cambiata."""

    def test_l_ingombro_di_una_scatola(self):
        with tempfile.TemporaryDirectory() as c:
            m = misure.misura(_glb(c, (40.0, 120.0, 20.0)))
        self.assertEqual(sorted(m["ingombro"]), [20.0, 40.0, 120.0])

    def test_dentro_la_tolleranza_non_e_un_cambio(self):
        a = {"ingombro": [116.0, 40.0, 20.0]}
        self.assertEqual(misure.confronta(a, {"ingombro": [116.2, 40.0, 20.0]}), [])

    def test_fuori_dalla_tolleranza_si_dice(self):
        righe = misure.confronta({"flowpack": {"largo": 40.1}},
                                 {"flowpack": {"largo": 37.1}})
        self.assertEqual(len(righe), 1)
        self.assertIn("flowpack largo", righe[0])

    def test_un_pezzo_in_meno_e_una_misura_sparita(self):
        self.assertEqual(misure.confronta({"pezzi": 3}, {"pezzi": 2}), ["pezzi: 3 -> 2"])
        self.assertEqual(misure.confronta({"flowpack": {"lungo": 116.0}}, {}),
                         ["flowpack lungo: 116,0 -> manca"])


class RegistroDelleFamiglie(unittest.TestCase):
    """`famiglie.registro.RICONOSCIMENTO` e `famiglie.registro.COSTRUZIONI`."""

    def setUp(self):
        from pack3d.famiglie import registro
        self.s = registro
        self.nomi = [f.nome for f in self.s.RICONOSCIMENTO]

    def test_ogni_tipologia_dichiarata_ha_una_prova(self):
        for kind in self.s.KIND_NOTI:
            self.assertTrue(any(kind in f.dichiarate for f in self.s.RICONOSCIMENTO), kind)

    def test_il_flowpack_per_ultimo_e_solo_se_non_si_e_dichiarato_altro(self):
        ultimo = self.s.RICONOSCIMENTO[-1]
        self.assertEqual(ultimo.nome, "flowpack")
        self.assertEqual(set(ultimo.dichiarate), {None, "flowpack"})

    def test_le_forme_che_l_astuccio_rifiuta_vengono_dopo_di_lui(self):
        astuccio = self.nomi.index("astuccio")
        for nome in ("scatola a punta", "pezzo di coppa", "tubo a cono",
                     "cartotecnico che non si legge"):
            self.assertGreater(self.nomi.index(nome), astuccio, nome)
        for nome in ("vassoio e display", "cono", "ballotin", "film che lo dice"):
            self.assertLess(self.nomi.index(nome), astuccio, nome)

    def test_ogni_famiglia_letta_ha_la_sua_costruzione(self):
        for kind in ("coppa", "vassoio", "pouch", "ballotin", "punta", "incarto",
                     "tubo", "carton", "riempimento", "flowpack"):
            self.assertIn(kind, self.s.COSTRUZIONI)

    def _leggi(self, kind):
        """Un foglio vuoto che il solutore astuccio accetta senza pannelli e
        che nessun'altra forma prende."""
        s = self.s
        from pack3d import coppa, punta, tubo, artwork
        vuoto = mock.Mock(panels=[])
        with tempfile.TemporaryDirectory() as c, \
                mock.patch.object(artwork, "astuccio_sulla_grafica",
                                  side_effect=lambda p: (p, vuoto, 0, None)), \
                mock.patch.object(coppa, "e_un_cono", return_value=False), \
                mock.patch.object(coppa, "riconosci", return_value=None), \
                mock.patch.object(coppa, "leggi_disco", return_value=None), \
                mock.patch.object(punta, "riconosci", return_value=None), \
                mock.patch.object(tubo, "riconosci", return_value=None), \
                mock.patch.object(s, "_dice_film", return_value=False), \
                mock.patch.object(s, "_analisi_incarto", return_value=None), \
                mock.patch.object(s, "_analisi_flowpack_dichiarata",
                                  return_value={"kind": "flowpack"}), \
                contextlib.redirect_stderr(io.StringIO()):
            return s._analyze_pdf(_pdf(c), kind)

    def test_un_cartotecnico_dichiarato_senza_pannelli_si_ferma(self):
        with self.assertRaises(ValueError) as e:
            self._leggi("carton")
        self.assertEqual(str(e.exception), self.s.CARTOTECNICO_SENZA_PANNELLI)
        self.assertLessEqual(len(str(e.exception)), 200)

    def test_senza_dichiarazione_lo_stesso_foglio_va_al_flowpack(self):
        self.assertEqual(self._leggi(None), {"kind": "flowpack"})


class LastreDiUnCasoCalibrato(unittest.TestCase):
    """`artwork.lastre_fisse`: per nome, e per prefisso col `*`."""

    def test_il_prefisso_prende_le_lastre_che_cominciano_cosi(self):
        import pypdf
        from pypdf.generic import ArrayObject, DictionaryObject, NameObject
        from pack3d import artwork
        w = pypdf.PdfWriter()
        pagina = w.add_blank_page(100, 100)
        spazi = DictionaryObject()
        for k, nome in enumerate(("/Label_uno", "/Label_due", "/Colata")):
            spazi[NameObject("/CS%d" % k)] = ArrayObject(
                [NameObject("/Separation"), NameObject(nome),
                 NameObject("/DeviceCMYK"), DictionaryObject()])
        pagina[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/ColorSpace"): spazi})
        self.assertEqual(artwork.lastre_fisse(pagina, ["White", "Label_*"]),
                         {"white", "label_uno", "label_due"})
        self.assertEqual(artwork.lastre_fisse(pagina, ["White"]), {"white"})


class StatoDiUnLavoro(unittest.TestCase):
    """`stato`: una cartella e uno stato per lavoro."""

    def test_la_cartella_si_butta_e_le_casse_si_vuotano(self):
        cassa = stato.per_lavoro({"vecchio": 1})
        self.addCleanup(stato._casse.remove, cassa)
        self.assertIsNone(stato.cartella())
        with stato.lavoro() as c:
            self.assertEqual(cassa, {})             # parte vuota
            cassa["nuovo"] = 2
            with tempfile.NamedTemporaryFile(dir=stato.cartella(), delete=False) as f:
                pass
            self.assertEqual(os.path.dirname(f.name), c)
            with stato.lavoro() as dentro:          # dentro un lavoro, lo stesso
                self.assertEqual(dentro, c)
        self.assertFalse(os.path.exists(c))
        self.assertEqual(cassa, {})
        self.assertIsNone(stato.cartella())


class Lavoratori(unittest.TestCase):
    """`lavoratori.quanti`: uno per vCPU del container, finche' stanno nella
    memoria."""

    G = 1024 ** 3

    def _quanti(self, file):
        with mock.patch.object(lavoratori, "LAVORATORI", "auto"), \
                mock.patch.object(lavoratori, "_leggi", side_effect=lambda p: file.get(p)):
            return lavoratori.quanti()[0]

    def test_uno_per_vcpu(self):
        self.assertEqual(self._quanti({"/sys/fs/cgroup/cpu.max": "200000 100000",
                                       "/sys/fs/cgroup/memory.max": str(16 * self.G)}), 2)
        self.assertEqual(self._quanti({"/sys/fs/cgroup/cpu.max": "800000 100000",
                                       "/sys/fs/cgroup/memory.max": str(32 * self.G)}), 8)

    def test_la_memoria_li_limita(self):
        self.assertEqual(self._quanti({"/sys/fs/cgroup/cpu.max": "800000 100000",
                                       "/sys/fs/cgroup/memory.max": str(4 * self.G)}), 2)

    def test_senza_tetto_due_come_prima(self):
        self.assertEqual(self._quanti({"/sys/fs/cgroup/cpu.max": "max 100000",
                                       "/proc/meminfo": "MemTotal: 16000000 kB"}), 2)


class CassaDelleRese(unittest.TestCase):
    """`rese`: le rese di pdfium su disco, con la chiave sul contenuto."""

    def setUp(self):
        from pack3d import rese
        self.rese = rese
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        p = mock.patch.object(rese, "CARTELLA", os.path.join(self.dir, "rese"))
        p.start()
        self.addCleanup(p.stop)

    def _file(self, nome, testo):
        f = os.path.join(self.dir, nome)
        with open(f, "wb") as fh:
            fh.write(testo)
        return f

    def test_andata_e_ritorno(self):
        a = np.arange(2 * 3 * 4, dtype=np.uint8).reshape(2, 3, 4)
        k = self.rese.chiave("prova", self._file("a.pdf", b"uno"), 0, 2.0)
        self.rese.scrivi(k, a, {"tinta": 2, "riquadri": [[1.5, 2.0, 3.0, 4.0]]})
        b, dati = self.rese.leggi(k)
        self.assertEqual((b.dtype, b.shape), (a.dtype, a.shape))
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(dati, {"tinta": 2, "riquadri": [[1.5, 2.0, 3.0, 4.0]]})
        self.rese.scrivi(k + "x", None, {"indici": [3, 1]})
        self.assertEqual(self.rese.leggi(k + "x"), (None, {"indici": [3, 1]}))

    def test_la_chiave_e_il_contenuto_non_il_nome(self):
        uno, copia = self._file("a.pdf", b"uno"), self._file("tmp123.pdf", b"uno")
        due = self._file("b.pdf", b"due")
        k = self.rese.chiave("prova", uno, 0, 2.0)
        self.assertEqual(k, self.rese.chiave("prova", copia, 0, 2.0))
        self.assertNotEqual(k, self.rese.chiave("prova", due, 0, 2.0))
        self.assertNotEqual(k, self.rese.chiave("prova", uno, 0, 4.0))
        self.assertNotEqual(k, self.rese.chiave("altra", uno, 0, 2.0))
        self.assertIsNone(self.rese.chiave("prova", os.path.join(self.dir, "non-c-e.pdf")))

    def test_solo_le_rese_costose(self):
        k = self.rese.chiave("prova", self._file("a.pdf", b"uno"))
        fatte = []

        def fai():
            fatte.append(1)
            return np.zeros((2, 2, 3), np.uint8), None

        with mock.patch.object(self.rese, "SOGLIA_S", 60.0):
            self.rese.tieni(k, fai)
            self.rese.tieni(k, fai)
        self.assertEqual(len(fatte), 2)             # veloce: non in cassa
        with mock.patch.object(self.rese, "SOGLIA_S", 0.0):
            self.rese.tieni(k, fai)
            self.rese.tieni(k, fai)
        self.assertEqual(len(fatte), 3)             # costosa: la seconda dalla cassa

    def test_una_resa_rovinata_si_rifa(self):
        k = self.rese.chiave("prova", self._file("a.pdf", b"uno"))
        self.rese.scrivi(k, np.zeros((4, 4), np.uint8))
        f = self.rese._file(k)
        with open(f, "r+b") as fh:
            fh.truncate(os.path.getsize(f) - 3)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(self.rese.leggi(k))
        self.assertFalse(os.path.exists(f))

    def test_il_tetto_butta_le_meno_usate(self):
        f = self._file("a.pdf", b"uno")
        chiavi = [self.rese.chiave("prova", f, i) for i in range(3)]
        with mock.patch.object(self.rese, "RESE_MB", 2.5 / 1024):    # 2,5 kB
            for i, k in enumerate(chiavi):
                self.rese.scrivi(k, np.zeros(1000, np.uint8))
                os.utime(self.rese._file(k), (1000 + i, 1000 + i))
            self.rese.scrivi(chiavi[0], np.zeros(1000, np.uint8))
        rimaste = [k for k in chiavi if os.path.exists(self.rese._file(k))]
        self.assertEqual(rimaste, [chiavi[0], chiavi[2]])


class ControlloSuiRiempimenti(unittest.TestCase):
    """Il controllo dell'AI guarda anche i riempimenti: sa che lo sono, e
    quale PDF e' il contenitore e quale il pack. Claude e' finto."""

    def test_la_nota_dice_chi_e_chi(self):
        import server
        nota = server.nota_riempimento({"vassoio": 0, "flowpack": 1},
                                       ["display.pdf", "barretta.pdf"])
        self.assertIn('il PDF "display.pdf" e\' il contenitore', nota)
        self.assertIn('il PDF "barretta.pdf" e\' il pack, un flowpack', nota)
        nota = server.nota_riempimento({"vassoio": 1, "flowpack": 0, "cu": "carton"},
                                       ["astuccio.pdf"])
        self.assertEqual(nota, "e' un RIEMPIMENTO: un contenitore pieno di astucci.")

    def test_claude_lo_sa(self):
        from pack3d import controllo
        chiesto = {}

        class Risposta:
            stop_reason = "end_turn"
            content = [mock.Mock(type="text", text='{"esito": "ok", "pack_nel_pdf": "p", '
                                 '"modello": "m", "motivo": "x", "difetti": [], '
                                 '"residui_tecnici": false}')]

        class Messaggi:
            def create(self, **k):
                chiesto.update(k)
                return Risposta()

        cliente = mock.Mock(messages=Messaggi())
        quadro = {"pagine": [b"a", b"b"], "viste": b"v", "ingombro": (100, 50, 200),
                  "fogli": [(300, 200), (150, 120)]}
        v = controllo.giudica(quadro, {"dichiarato": "riempimento", "nomi": ["d.pdf", "p.pdf"],
                                       "nota": "e' un RIEMPIMENTO: il PDF \"d.pdf\" ..."},
                              modello="prova", client=cliente)
        self.assertEqual(v["esito"], "ok")
        self.assertIn("Se il riassunto dice che e' un RIEMPIMENTO", chiesto["system"])
        testo = chiesto["messages"][0]["content"][-1]["text"]
        self.assertIn("Da sapere: e' un RIEMPIMENTO", testo)


class FileDelCasoNelRegistro(unittest.TestCase):
    """`coda._metti_file` riprova, la issue dice i file che non sono arrivati,
    e il caso rimandato li completa. GitHub e' finto: `_richiesta` risponde
    dalla lista `risposte` (un'eccezione si solleva), e segna le chiamate."""

    def setUp(self):
        from pack3d import coda
        self.coda = coda
        self.chiamate, self.risposte = [], {}
        for nome, valore in (("RIPROVE_S", (0, 0)), ("privato", lambda: True),
                             ("_richiesta", self._richiesta),
                             ("avvia_routine", mock.Mock(return_value=None)),
                             ("_salva_email", mock.Mock())):
            p = mock.patch.object(coda, nome, valore)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {"PACK3D_CODA_REPO": "io/casi",
                                         "PACK3D_CODA_TOKEN": "x"})
        p.start()
        self.addCleanup(p.stop)

    def _richiesta(self, metodo, percorso, corpo=None, timeout=60):
        self.chiamate.append((metodo, percorso, corpo))
        for chiave, coda_risposte in self.risposte.items():
            if (metodo + " " + percorso).startswith(chiave) and coda_risposte:
                r = coda_risposte.pop(0)
                if isinstance(r, Exception):
                    raise r
                return r
        return {}

    @staticmethod
    def _http(codice):
        import urllib.error
        return urllib.error.HTTPError("https://api.github.com", codice, "x", {}, None)

    def _metti(self, *risposte):
        self.risposte["PUT"] = list(risposte)
        with contextlib.redirect_stderr(io.StringIO()):
            esito = self.coda._metti_file("io/casi", "casi/x/a.pdf", "m", b"pdf")
        return esito, sum(1 for c in self.chiamate if c[0] == "PUT")

    def test_riprova_sul_409_sui_5xx_e_sulla_rete(self):
        self.assertEqual(self._metti(self._http(409), {}), (True, 2))
        self.chiamate.clear()
        self.assertEqual(self._metti(self._http(502), OSError("giu'"), {}), (True, 3))
        self.chiamate.clear()
        self.assertEqual(self._metti(*[OSError("giu'")] * 3), (False, 3))

    def test_il_422_e_gia_li_e_il_413_non_si_riprova(self):
        self.assertEqual(self._metti(self._http(422)), (True, 1))
        self.chiamate.clear()
        self.assertEqual(self._metti(self._http(413), {}), (False, 1))

    def test_la_issue_dice_i_file_che_mancano(self):
        self.risposte["GET /repos/io/casi/issues"] = [[]]
        self.risposte["PUT /repos/io/casi/contents/casi/"] = [
            {}, self._http(413), {}]
        self.risposte["POST /repos/io/casi/issues"] = [{"number": 7, "html_url": "u"}]
        with contextlib.redirect_stderr(io.StringIO()):
            self.coda._carica_davvero("abc", [b"1", b"2"], ["a.pdf", "b.pdf"],
                                      {"esito": "respinto"}, None, {})
        corpo = [c[2]["body"] for c in self.chiamate if c[0] == "POST"][0]
        self.assertIn("**File non arrivati nel registro:** b.pdf.", corpo)

    def test_il_caso_rimandato_porta_i_file_che_mancavano(self):
        issue = {"number": 7, "title": "Caso nuovo abc: a.pdf, b.pdf", "html_url": "u",
                 "body": "File: [`casi/2026-10-29_abc`](../tree/HEAD/casi/2026-10-29_abc)",
                 "labels": [{"name": "da-guardare"}]}
        self.risposte["GET /repos/io/casi/issues"] = [[issue]]
        self.risposte["GET /repos/io/casi/contents/casi/2026-10-29_abc"] = [
            [{"name": "a.pdf"}, {"name": "verdetto.json"}]]
        with contextlib.redirect_stderr(io.StringIO()):
            self.coda._carica_davvero("abc", [b"1", b"2"], ["a.pdf", "b.pdf"],
                                      {"esito": "respinto"}, None, {})
        messi = [c[1] for c in self.chiamate if c[0] == "PUT"]
        self.assertEqual(messi, ["/repos/io/casi/contents/casi/2026-10-29_abc/b.pdf"])
        commento = [c[2]["body"] for c in self.chiamate if c[0] == "POST"]
        self.assertEqual(commento, ["**File arrivati col nuovo invio:** b.pdf."])
        self.assertIn(("DELETE", "/repos/io/casi/issues/7/labels/da-guardare", None),
                      self.chiamate)
        self.coda.avvia_routine.assert_called_once()

    def test_senza_cartella_arrivano_tutti(self):
        issue = {"number": 7, "title": "Caso nuovo abc: a.pdf", "html_url": "u",
                 "body": "File: [`casi/2026-10-29_abc`](../tree/HEAD/casi/2026-10-29_abc)",
                 "labels": []}
        self.risposte["GET /repos/io/casi/issues"] = [[issue]]
        self.risposte["GET /repos/io/casi/contents/"] = [self._http(404)]
        with contextlib.redirect_stderr(io.StringIO()):
            self.coda._carica_davvero("abc", [b"1"], ["a.pdf"],
                                      {"esito": "respinto"}, None, {})
        self.assertEqual([c[1] for c in self.chiamate if c[0] == "PUT"],
                         ["/repos/io/casi/contents/casi/2026-10-29_abc/a.pdf"])
        # senza `da-guardare` la routine non riparte: il caso e' gia' libero
        self.coda.avvia_routine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
