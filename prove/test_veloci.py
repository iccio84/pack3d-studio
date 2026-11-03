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
import json
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


def _pdf(cartella, tratti=(), larghezza=600.0, altezza=600.0, altro=b""):
    """Un PDF di una pagina con questi tratti a penna: [(x0, y0, x1, y1)] in
    punti, con la y dal basso come nel contenuto del PDF, e `altro` in coda
    al contenuto."""
    import pypdf
    from pypdf.generic import NameObject, StreamObject
    w = pypdf.PdfWriter()
    pagina = w.add_blank_page(larghezza, altezza)
    contenuto = b"0.5 w 0 0 0 RG\n" + b"".join(
        b"%.2f %.2f m %.2f %.2f l S\n" % t for t in tratti) + altro
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

    def test_la_cornice_girata_non_entra_nella_fustella(self):
        # una cornice dell'artwork - contorno e riempimento sullo stesso
        # riquadro - disegnata sotto una matrice capovolta, coi suoi decimi
        # di miliardesimo: pdfminer vuole i lati uguali al bit, la da' come
        # curva, e non deve diventare quattro tratti
        cornice = (b"q -1 0.00000000000001 -0.00000000000001 -1 600 600 cm "
                   b"1 w 0 0 0 1 K 1 0 0 0 k "
                   b"120 120 80 40 re f 120 120 80 40 re S Q\n")
        import pdfplumber
        with pdfplumber.open(_pdf(self.cartella, GRIGLIA, altro=cornice)) as doc:
            pagina = doc.pages[0]
            self.assertTrue(pagina.curves, "pdfminer ha cambiato idea: la "
                            "cornice girata non e' piu' una curva")
            stili = {s[4] for s in dl._segments(pagina)}
        self.assertEqual(stili, {(0.5, "(0.0, 0.0, 0.0)")})

    def test_la_pagina_col_disegno_dopo_una_copertina(self):
        import pypdf
        from pack3d import artwork
        disegno = _pdf(self.cartella, GRIGLIA)
        w = pypdf.PdfWriter(clone_from=disegno)
        w.insert_blank_page(600.0, 600.0, index=0)      # la copertina, vuota
        f = os.path.join(self.cartella, "con_copertina.pdf")
        with open(f, "wb") as fh:
            w.write(fh)
        self.assertEqual(artwork._pagina_col_dt(f, 2), 1)
        # la prima pagina col disegno resta la prima
        w = pypdf.PdfWriter(clone_from=disegno)
        w.add_blank_page(600.0, 600.0)
        g = os.path.join(self.cartella, "con_retro.pdf")
        with open(g, "wb") as fh:
            w.write(fh)
        self.assertEqual(artwork._pagina_col_dt(g, 2), 0)

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


class Statistiche(unittest.TestCase):
    """`statistiche`: una riga per evento, sommate, senza numeri nei motivi."""

    def setUp(self):
        from pack3d import statistiche
        self.st = statistiche
        cartella = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(cartella, True))
        self._f = mock.patch.object(statistiche, "FILE", os.path.join(cartella, "s.jsonl"))
        self._f.start()
        self.addCleanup(self._f.stop)

    def test_il_motivo_perde_numeri_e_misure(self):
        e = ValueError("astuccio: i fianchi (3.4 e 5.0 mm) non tornano con 45,3 mm. "
                       "Fasce (mm): [45.3, 131.5]")
        self.assertEqual(self.st.motivo(e),
                         "ValueError: astuccio: i fianchi non tornano con # mm")

    def test_una_prova_non_conta(self):
        import threading
        self.st.in_prova(True)
        self.addCleanup(self.st.in_prova, False)
        self.st.conta("costruzione", dichiarato="flowpack", letto="flowpack")
        # un'altra richiesta, nel suo thread, conta
        t = threading.Thread(target=self.st.conta, args=("lettura",),
                             kwargs=dict(dichiarato="carton", letto="carton"))
        t.start()
        t.join()
        self.st.in_prova(False)
        self.st.conta("verdetto", letto="flowpack", esito="ok")
        r = self.st.riassunto()
        self.assertEqual(r["eventi"], 2)
        self.assertNotIn("costruzione", r["conti"])

    def test_le_righe_si_sommano(self):
        for _ in range(2):
            self.st.conta("fermata", fase="lettura", dichiarato="carton",
                          motivo="ValueError: astuccio: x")
        self.st.conta("lettura", dichiarato="flowpack", letto="flowpack")
        r = self.st.riassunto()
        self.assertEqual(r["eventi"], 3)
        self.assertEqual(r["conti"]["fermata"],
                         [dict(cosa="carton | lettura | ValueError: astuccio: x", quante=2)])
        self.assertEqual(r["conti"]["lettura"][0]["quante"], 1)

    def _registro(self, risposte):
        """Il registro dei casi finto: le richieste che riceve, e per ognuna
        la risposta (un dict) o l'errore da sollevare."""
        import urllib.error
        from pack3d import coda
        chieste = []

        def richiesta(metodo, percorso, corpo=None, timeout=60):
            chieste.append((metodo, percorso, dict(corpo) if corpo else None))
            r = risposte.pop(0)
            if isinstance(r, int):
                raise urllib.error.HTTPError(percorso, r, "no", {}, None)
            return r
        for p in (mock.patch.object(coda, "_richiesta", richiesta),
                  mock.patch.dict(os.environ, PACK3D_CODA_REPO="io/casi",
                                  PACK3D_CODA_TOKEN="t"),
                  mock.patch.dict(self.st._VITA, t=1000, nome="2026-11-02_100000",
                                  parte=1, righe=0, sha=None)):
            p.start()
            self.addCleanup(p.stop)
        return chieste

    def test_il_registro_ha_gli_eventi_di_questa_vita(self):
        import base64
        import json
        chieste = self._registro([{"content": {"sha": "s1"}}, {"content": {"sha": "s2"}}])
        with open(self.st.FILE, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(t=999, e="lettura")) + "\n")   # la vita di prima
        with mock.patch("time.time", return_value=1001):
            self.st.conta("lettura", dichiarato="flowpack")
            self.st.conta("fermata", motivo="x")
        self.assertTrue(self.st.salva_nel_registro())
        metodo, percorso, corpo = chieste[0]
        self.assertEqual((metodo, percorso),
                         ("PUT", "/repos/io/casi/contents/statistiche/spazio/2026-11-02_100000.jsonl"))
        righe = base64.b64decode(corpo["content"]).decode().splitlines()
        self.assertEqual([json.loads(r)["e"] for r in righe], ["lettura", "fermata"])
        self.assertNotIn("sha", corpo)
        # niente di nuovo, niente commit
        self.assertFalse(self.st.salva_nel_registro())
        self.assertEqual(len(chieste), 1)
        with mock.patch("time.time", return_value=1002):
            self.st.conta("verdetto", esito="ok")
        self.assertTrue(self.st.salva_nel_registro())
        self.assertEqual(chieste[1][2]["sha"], "s1")

    def test_il_registro_con_l_impronta_sbagliata_si_riprova(self):
        chieste = self._registro([422, {"sha": "s9"}, {"content": {"sha": "s10"}}])
        with mock.patch("time.time", return_value=1001):
            self.st.conta("lettura")
        self.assertTrue(self.st.salva_nel_registro())
        self.assertEqual([c[0] for c in chieste], ["PUT", "GET", "PUT"])
        self.assertEqual(chieste[2][2]["sha"], "s9")
        self.assertEqual(self.st._VITA["sha"], "s10")

    def test_senza_la_coda_non_si_salva(self):
        chieste = self._registro([])
        with mock.patch.dict(os.environ, PACK3D_CODA_TOKEN=""), \
                mock.patch("time.time", return_value=1001):
            self.st.conta("lettura")
            self.assertFalse(self.st.salva_nel_registro())
        self.assertEqual(chieste, [])


class GiudiceDelloSteso(unittest.TestCase):
    """`flowpack._riquadro_coerente`: lati che non sono tagli, uno steso
    disegnato dalla prova (nessun file dei clienti)."""

    def _steso(self, cornice=False, pinna_bianca=False, legenda=False, pinna_aperta=False):
        from pack3d import flowpack as fpk
        mm = 1.0 / fpk.PT2MM
        y0, y1, x0, x1 = 50.0, 50.0 + 100 * mm, 50.0, 50.0 + 150 * mm
        st = (0.5, "(0, 0, 0)")
        inizio = y0 + (15 * mm if pinna_bianca else 8 * mm if pinna_aperta else 0.0)
        S = [("H", y, x0, x1, st) for y in (y0 + 20 * mm, y0 + 50 * mm, y0 + 80 * mm, y1)]
        if pinna_aperta:
            # la pinna bianca come fascia a se', fino alla sua piega: i
            # tagli del passo non la attraversano, il suo bordo esce di 3,5
            # mm per parte (il T2 al cioccolato fondente)
            S += [("H", y0, x0 - 3.5 * mm, x1 + 3.5 * mm, st), ("H", inizio, x0, x1, st),
                  ("V", x0, inizio, y1, st), ("V", x1, inizio, y1, st)]
        else:
            S += [("H", y0, x0, x1, st), ("V", x0, y0, y1, st), ("V", x1, y0, y1, st)]
        S += [("V", x, inizio, y1, st) for x in (x0 + 10 * mm, x1 - 10 * mm)]
        hs = [y0, y0 + 20 * mm, y0 + 50 * mm, y0 + 80 * mm, y1]
        if pinna_aperta:
            hs = [y0, inizio] + hs[1:]
        vs = [x0, x0 + 10 * mm, x1 - 10 * mm, x1]
        if cornice:
            d = 10 * mm
            S += [("H", y0 - d, x0 - d, x1 + d, st), ("H", y1 + d, x0 - d, x1 + d, st),
                  ("V", x0 - d, y0 - d, y1 + d, st), ("V", x1 + d, y0 - d, y1 + d, st)]
            hs, vs = [y0 - d] + hs + [y1 + d], [x0 - d] + vs + [x1 + d]
        if legenda:
            # un riquadro attaccato sotto lo steso, largo meta'
            xl, yl = x0 + 75 * mm, y1 + 22 * mm
            S += [("H", yl, x0, xl, st), ("V", x0, y1, yl, st), ("V", xl, y1, yl, st)]
            hs = hs + [yl]
        raster = np.full((int(y1 + 40 * mm), int(x1 + 40 * mm), 3), 255, np.int16)
        raster[int(inizio):int(y1), int(x0):int(x1)] = 120
        return fpk, S, hs, vs, raster

    def test_la_cornice_non_e_lo_steso(self):
        fpk, S, hs, vs, raster = self._steso(cornice=True)
        h, v, avviso = fpk._riquadro_coerente(S, hs, vs, raster, 1.0)
        self.assertEqual((h, v), (hs[1:-1], vs[1:-1]))
        self.assertIn("steso per coerenza", avviso)

    def test_la_legenda_attaccata_non_e_lo_steso(self):
        fpk, S, hs, vs, raster = self._steso(legenda=True)
        h, v, avviso = fpk._riquadro_coerente(S, hs, vs, raster, 1.0)
        self.assertEqual((h, v), (hs[:-1], vs))

    def test_una_pinna_bianca_resta_dello_steso(self):
        fpk, S, hs, vs, raster = self._steso(pinna_bianca=True)
        self.assertEqual(fpk._riquadro_coerente(S, hs, vs, raster, 1.0), (hs, vs, None))

    def test_la_pinna_bianca_dentro_la_cornice_resta_dello_steso(self):
        # la pinna bianca e il margine della cornice sono tutti e due vuoti:
        # la pinna pero' la attraversano i tagli del passo, fino al bordo
        fpk, S, hs, vs, raster = self._steso(cornice=True, pinna_bianca=True)
        h, v, avviso = fpk._riquadro_coerente(S, hs, vs, raster, 1.0)
        self.assertEqual((h, v), (hs[1:-1], vs[1:-1]))

    def test_la_pinna_disegnata_come_fascia_resta_dello_steso(self):
        fpk, S, hs, vs, raster = self._steso(cornice=True, pinna_aperta=True)
        h, v, avviso = fpk._riquadro_coerente(S, hs, vs, raster, 1.0)
        self.assertEqual((h, v), (hs[1:-1], vs[1:-1]))

    def test_la_linea_della_cornice_non_e_grafica(self):
        # oltre il capo sinistro, fra 6 e 12 mm, la stampa e' poca (il 18%
        # della striscia) e la linea della cornice, a 10 mm, la porterebbe
        # oltre TAGLIA_GRAFICA: una linea del disegno non e' grafica, e il
        # capo sinistro resta un taglio (il pane ripieno T1 del display da 15)
        fpk, S, hs, vs, raster = self._steso(cornice=True)
        mm = 1.0 / fpk.PT2MM
        for k, c, a, b, st in S:
            if k == "H":
                raster[int(c), int(a):int(b) + 1] = 0
            else:
                raster[int(a):int(b) + 1, int(c)] = 0
        x0 = vs[1]
        raster[int(hs[1]):int(hs[-2]), int(x0 - 9 * mm):int(x0 - 8 * mm)] = 0
        h, v, avviso = fpk._riquadro_coerente(S, hs, vs, raster, 1.0)
        self.assertEqual((h, v), (hs[1:-1], vs[1:-1]))

    def test_una_quota_d_insieme_dice_dove_stanno_i_capi(self):
        # la quota dei 101 sotto lo steso, dal capo sinistro al taglio: il
        # riquadro che arriva al filo dell'abbondanza (113) e' smentito, come
        # quello che comincia alla pinna (13); una quota di catena (20) o piu'
        # lunga del lato (206,5 su 184) non smentisce niente
        from pack3d import flowpack as fpk
        mm = 1.0 / fpk.PT2MM
        x0, y0, y1 = 50.0, 50.0, 50.0 + 115 * mm
        quota = {("H", y1 + 8 * mm): (101.0, x0, x0 + 101 * mm)}
        self.assertFalse(fpk._smentito(quota, y0, y1, x0, x0 + 101 * mm))
        self.assertTrue(fpk._smentito(quota, y0, y1, x0, x0 + 113 * mm))
        self.assertTrue(fpk._smentito(quota, y0, y1, x0 + 13 * mm, x0 + 113 * mm))
        catena = {("H", y1 + 8 * mm): (20.0, x0, x0 + 20 * mm)}
        self.assertFalse(fpk._smentito(catena, y0, y1, x0, x0 + 113 * mm))
        lunga = {("H", y1 + 8 * mm): (206.5, x0 - 10 * mm, x0 + 196.5 * mm)}
        self.assertFalse(fpk._smentito(lunga, y0, y1, x0, x0 + 184 * mm))
        # le quote delle miniature, lontane, non sono di questo riquadro
        lontana = {("H", y1 + 60 * mm): (101.0, x0, x0 + 101 * mm)}
        self.assertFalse(fpk._smentito(lontana, y0, y1, x0, x0 + 113 * mm))

    def test_il_ritaglio_tiene_le_linee_dello_steso(self):
        # dentro il riquadro scelto: il capo sinistro, che prosegue nella
        # legenda attaccata, si taglia al riquadro; la linea di una miniatura
        # sotto lo steso resta fuori
        from pack3d import flowpack as fpk
        st = (0.5, "(0, 0, 0)")
        S = [("V", 100.0, 100.0, 400.0, st), ("H", 300.0, 100.0, 300.0, st),
             ("V", 150.0, 360.0, 500.0, st)]
        self.assertEqual(fpk._ritaglia(S, 100.0, 300.0, 100.0, 300.0),
                         [("V", 100.0, 100.0, 303.0, st), ("H", 300.0, 100.0, 300.0, st)])


class DtFusoConLeNote(unittest.TestCase):
    """`tools._fuso`: un gruppo di linee tecniche in cui nessuna penna da
    sola copre meta' del gruppo e' piu' disegni uniti da un'altra penna."""

    def _griglia(self, x0, y0, lato, st):
        passi = [x0 + lato * f for f in (0.0, 0.3, 0.7, 1.0)]
        return ([("H", y0 + (v - x0), x0, x0 + lato, st) for v in passi]
                + [("V", v, y0, y0 + lato, st) for v in passi])

    def test_due_viste_unite_dai_richiami(self):
        from pack3d import tools
        verde, nero = (0.5, "(43, 80, 53)"), (0.5, "(35, 31, 32)")
        G = self._griglia(0.0, 0.0, 300.0, verde) + self._griglia(800.0, 0.0, 300.0, verde)
        # i richiami neri: una catena di tratti che va da una vista all'altra
        G += [("H", 150.0, 300.0 + 20.0 * i, 320.0 + 20.0 * i, nero) for i in range(25)]
        self.assertTrue(tools._fuso(G, (0.0, 0.0, 1100.0, 300.0)))

    def test_un_dt_a_due_penne_resta_uno(self):
        # il contorno in una penna, le pieghe in un'altra (il wafer T1)
        from pack3d import tools
        nero, blu = (0.5, "(0, 0, 0)"), (0.3, "(0, 0, 255)")
        G = [("H", 0.0, 0.0, 400.0, nero), ("H", 300.0, 0.0, 400.0, nero),
             ("V", 0.0, 0.0, 300.0, nero), ("V", 400.0, 0.0, 300.0, nero)]
        G += [("V", x, 0.0, 300.0, blu) for x in (100.0, 200.0, 300.0)]
        self.assertFalse(tools._fuso(G, (0.0, 0.0, 400.0, 300.0)))


class QuoteFuoriDallaFustella(unittest.TestCase):
    """`dieline._largest_cluster` coi numeri: una quota non e' fustella, e
    non deve portarsi via le alette."""

    def test_una_quota_non_tira_fuori_le_alette(self):
        from pack3d import dieline as dl
        st = (0.5, "(0, 0, 0)")
        corpo = ([("H", y, 0.0, 300.0, st) for y in (0.0, 100.0, 200.0)]
                 + [("V", x, 0.0, 200.0, st) for x in (0.0, 150.0, 300.0)])
        # un'aletta a fianchi obliqui: nessun tratto H/V la attacca al corpo
        aletta = ("H", -40.0, 20.0, 280.0, st)
        # la quota a destra, 240 punti, coi richiami: quello in alto tocca
        # l'aletta, quello in basso sta lontano dal corpo
        quota = [("V", 360.0, -40.0, 200.0, st), ("H", -40.0, 283.0, 365.0, st),
                 ("H", 200.0, 335.0, 365.0, st)]
        tutti = corpo + [aletta] + quota
        self.assertNotIn(aletta, dl._largest_cluster(tutti))
        numeri = [(363.0, 80.0, round(240 * dl.PT2MM, 1))]
        con = dl._largest_cluster(tutti, numeri=numeri)
        self.assertIn(aletta, con)
        self.assertFalse(any(s in con for s in quota))

    def test_una_quota_attaccata_al_corpo_non_e_una_piega(self):
        """`dieline._quote_fuori`: la quota del passo sotto lo steso, coi
        richiami a tre punti dagli angoli, sta nel gruppo della fustella; si
        toglie lei, coi richiami. Una piega con la sua misura accanto resta."""
        from pack3d import dieline as dl
        st = (0.5, "(0, 0, 0)")
        corpo = ([("H", y, 0.0, 300.0, st) for y in (0.0, 100.0, 200.0)]
                 + [("V", x, 0.0, 200.0, st) for x in (0.0, 150.0, 300.0)])
        # sotto lo steso, a 23 punti: la linea spezzata dal numero
        quota = [("H", 223.0, 0.0, 140.0, st), ("H", 223.0, 160.0, 300.0, st),
                 ("V", 0.0, 203.0, 229.0, st), ("V", 300.0, 203.0, 229.0, st)]
        lato = round(300 * dl.PT2MM, 1)
        numeri = [(150.0, 226.0, lato),
                  # la piega di mezzo con la sua misura scritta accanto
                  (75.0, 104.0, lato)]
        con = dl._largest_cluster(corpo + quota, numeri=numeri)
        self.assertEqual(sorted(con), sorted(corpo))
        # senza numeri resta tutto: la quota senza il suo numero non si sa
        self.assertEqual(len(dl._largest_cluster(corpo + quota)), len(corpo + quota))


class GrigliaRicucita(unittest.TestCase):
    """`tools._griglia_ricucita`: una piega disegnata a pezzi resta una
    linea sola."""

    def test_i_lati_spezzati_a_ogni_piega_fanno_griglia(self):
        from pack3d import tools
        st = (0.5, "(0, 0, 0)")
        ys = (0.0, 100.0, 130.0, 230.0, 260.0)
        # le righe attraversano tutto, le colonne si spezzano a ogni riga
        G = [("H", y, 0.0, 200.0, st) for y in ys]
        G += [("V", x, a, b, st) for x in (0.0, 200.0) for a, b in zip(ys, ys[1:])]
        self.assertIsNone(tools._griglia(G))
        t = tools._griglia_ricucita(G)
        self.assertIsNotNone(t)
        self.assertEqual(t[:4], (0.0, 0.0, 200.0, 260.0))


class CorniceAttornoAllaTavola(unittest.TestCase):
    """Una cornice attorno alla tavola, nella penna della fustella, non e'
    fustella: ne' fra i tratti (`ballotin.tratti_fustella`, che leggono anche
    il display a scatola, il prisma e la scatola a punta) ne' nell'impronta
    di stampa del vassoio (`vassoio.sagoma_e_creste`)."""

    @staticmethod
    def _l(*punti):
        return np.array(punti, dtype=float)

    def test_i_tratti_della_cornice_vanno_via(self):
        from pack3d import ballotin
        l = self._l
        corpo = [l((0, 0), (100, 0)), l((100, 0), (100, 80)), l((100, 80), (0, 80)),
                 l((0, 80), (0, 0)), l((50, 0), (50, 80))]
        # il tratteggio di una patella, oltre l'ultima riga ma attaccato
        tratteggio = [l((20 + 5 * k, 80), (30 + 5 * k, 100)) for k in range(5)]
        finestra = [l((60, 30), (80, 30), (80, 50), (60, 50), (60, 30))]
        # una quota staccata dal disegno, da un lato solo
        quota = [l((0, -20), (100, -20))]
        cornice = [l((-10, -40), (110, -40)), l((110, -40), (110, 110)),
                   l((110, 110), (-10, 110)), l((-10, 110), (-10, -40))]
        tenuti = corpo + tratteggio + finestra + quota
        resto = {id(p) for p in ballotin._senza_cornici(tenuti + cornice)}
        self.assertTrue(all(id(p) in resto for p in tenuti))
        self.assertFalse(any(id(p) in resto for p in cornice))
        # senza cornice non cambia niente
        self.assertEqual(ballotin._senza_cornici(tenuti), tenuti)

    def test_la_cornice_non_chiude_il_foglio_del_vassoio(self):
        from types import SimpleNamespace

        from PIL import Image

        from pack3d import vassoio
        px_mm = 4.0
        scala = px_mm * 25.4 / 72.0
        a = np.full((400, 400, 3), 255, np.uint8)
        # la stampa a croce: il riquadro della fustella ha quattro angoli di foglio
        a[100:300, 170:230] = (200, 30, 30)
        a[170:230, 100:300] = (200, 30, 30)
        # la cornice a dieci millimetri, e una quota che la attacca alla stampa
        a[60, 60:341] = a[340, 60:341] = 0
        a[60:341, 60] = a[60:341, 340] = 0
        a[200, 300:341] = 0
        d = SimpleNamespace(bbox=tuple(v / scala for v in (100, 100, 300, 300)),
                            xs=[v / scala for v in (100, 150, 190, 210, 250, 300)],
                            ys=[v / scala for v in (100, 170, 230, 300)])
        with mock.patch("pack3d.dieline.render_page", return_value=Image.fromarray(a)):
            sagoma, _creste, _resa = vassoio.sagoma_e_creste("finto.pdf", d, px_mm)
        croce = np.zeros((400, 400), bool)
        croce[100:300, 170:230] = croce[170:230, 100:300] = True
        self.assertTrue(np.all(sagoma[croce]))
        # gli angoli del riquadro restano foglio: la sagoma non e' il riquadro
        self.assertFalse(sagoma[110, 110] or sagoma[290, 290])
        self.assertLessEqual(int(sagoma.sum()) - int(croce.sum()), 4)


class SoglieSpostate(unittest.TestCase):
    """`prove/soglie.py`: una soglia si sposta dappertutto dove il codice la
    vede - nel modulo che la scrive, in quelli che la importano, nei valori
    di serie degli argomenti - e torna com'era."""

    @staticmethod
    def _soglie():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "soglie_prova", os.path.join(QUI, "prove", "soglie.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_si_sposta_di_serie_e_importata_e_torna(self):
        from pack3d import ballotin
        from pack3d.famiglie import astuccio, comune
        soglie = self._soglie()
        stacco, ruvida = ballotin.STACCO, comune.RUVIDITA_CARTA
        indietro = soglie.sposta("pack3d.ballotin.STACCO", 99.0)
        try:
            self.assertEqual(ballotin.STACCO, 99.0)
            self.assertEqual(ballotin._senza_cornici.__defaults__, (99.0,))
        finally:
            indietro()
        self.assertIs(ballotin.STACCO, stacco)
        self.assertIs(ballotin._senza_cornici.__defaults__[0], stacco)
        indietro = soglie.sposta("pack3d.famiglie.comune.RUVIDITA_CARTA", 0.5)
        try:
            self.assertEqual((comune.RUVIDITA_CARTA, astuccio.RUVIDITA_CARTA), (0.5, 0.5))
        finally:
            indietro()
        self.assertIs(astuccio.RUVIDITA_CARTA, ruvida)

    def test_il_passo(self):
        soglie = self._soglie()
        self.assertAlmostEqual(soglie._spinto(0.2, 0.25, +1), 0.25)
        self.assertAlmostEqual(soglie._spinto(0.2, 0.25, -1), 0.15)
        # un intero si sposta almeno di uno; lo zero non si sposta
        self.assertEqual((soglie._spinto(4, 0.1, +1), soglie._spinto(4, 0.1, -1)), (5, 3))
        self.assertIsNone(soglie._spinto(0, 0.25, +1))
        # una frazione oltre la meta' si sposta nella parte che manca; una
        # misura in mm si sposta nel valore
        self.assertAlmostEqual(soglie._spinto(0.9, 0.25, +1, "pack3d.plancia.COPRE"), 0.925)
        self.assertAlmostEqual(soglie._spinto(0.9, 0.25, -1, "pack3d.plancia.COPRE"), 0.875)
        self.assertAlmostEqual(soglie._spinto(0.9, 0.25, +1, "pack3d.x.LARGO_MM"), 1.125)
        i, v = soglie._primo(0.9, +1, "pack3d.plancia.COPRE")
        self.assertEqual(i, 0)
        self.assertAlmostEqual(v, 0.925)
        # un intero che al passo dopo resta uguale non si riprova
        self.assertIsNone(soglie._primo(4, +1, "pack3d.ballotin.LENTI", 1, 5))

    def test_i_vicini_entro_il_rosso(self):
        soglie = self._soglie()
        esiti = {"m.A": {"valore": 0.2, "casi": ["x", "y"], "cambia": {
                     "x": {"+1": {"passo": 0.05}},
                     "y": {"-1": {"passo": 0.25}}}},
                 # un valore che entra nella lettura: cambia nei due versi
                 "m.B": {"valore": 8, "casi": ["x"], "cambia": {
                     "x": {"+1": {"passo": 0.05}, "-1": {"passo": 0.05}}}}}
        self.assertEqual(soglie.vicini_entro(esiti, 0.10),
                         [{"caso": "x", "soglia": "m.A", "verso": "+1"}])

    def test_le_costanti_che_non_sono_soglie(self):
        soglie = self._soglie()
        g = {"TAGLIA": 0.2, "PT2MM": 0.35, "_BEZIER": 3, "ATTIVO": True, "NOME": "x",
             "minuscola": 1.0}
        self.assertEqual(soglie._numeriche(g), {"TAGLIA"})


class BallotinTolleranzaCercata(unittest.TestCase):
    """`ballotin.riconosci`: se con NODO il ballotin non torna, si riprova
    con le tolleranze vicine (NODO_PROVE), e vale la prima che lo da'."""

    def _prova(self, torna_alla):
        from pack3d import ballotin as B
        provate = []

        def grafo(restano, tol=B.NODO):
            provate.append(round(tol, 3))
            return np.zeros((0, 2)), []

        def classifica(ff, archi, page_no=0):
            return "ballotin" if len(provate) == torna_alla else None
        with mock.patch.object(B, "tratti_fustella", return_value=[np.zeros((2, 2))]), \
                mock.patch.object(B, "ha_lenti", return_value=True), \
                mock.patch.object(B, "tratteggi", return_value=set()), \
                mock.patch.object(B, "grafo", side_effect=grafo), \
                mock.patch.object(B, "ripara", side_effect=lambda n, a: a), \
                mock.patch.object(B, "pota", side_effect=lambda a: a), \
                mock.patch.object(B, "facce", return_value=[]), \
                mock.patch.object(B, "principale", return_value=None), \
                mock.patch.object(B, "componi", return_value=[]), \
                mock.patch.object(B, "_classifica", side_effect=classifica):
            return B.riconosci("finto.pdf"), provate

    def test_al_primo_colpo_non_si_riprova(self):
        self.assertEqual(self._prova(1), ("ballotin", [0.3]))

    def test_si_riprova_con_le_vicine(self):
        self.assertEqual(self._prova(3), ("ballotin", [0.3, 0.36, 0.24]))

    def test_se_nessuna_torna_non_e_un_ballotin(self):
        b, provate = self._prova(99)
        self.assertIsNone(b)
        self.assertEqual(provate, [0.3, 0.36, 0.24, 0.42, 0.18])


class ProvaDelloSpazio(unittest.TestCase):
    """`prove/parco.py spazio`: un caso per famiglia, il piu' leggero, e le
    richieste del parco segnate come prove."""

    def setUp(self):
        sys.path.insert(0, os.path.join(QUI, "prove"))
        import parco
        self.parco = parco
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.dir, True))
        os.makedirs(os.path.join(self.dir, "parco", "pdf"))
        casi = []
        letture = {}
        for nome, kind, peso in (("a", "flowpack", 300), ("b", "flowpack", 100),
                                 ("c", "vassoio", 200), ("d", None, 50)):
            with open(os.path.join(self.dir, "parco", "pdf", nome + ".pdf"), "wb") as fh:
                fh.write(b"%PDF" + b"x" * peso)
            casi.append({"nome": nome, "file": [nome + ".pdf"], "opzioni": {"kind": "x"}})
            # "d" non ha una lettura approvata: non si prova
            if kind:
                letture[nome] = {"kind": kind, "title": kind}
        with open(os.path.join(self.dir, "parco", "parco.json"), "w") as fh:
            json.dump({"casi": casi}, fh)
        with open(os.path.join(self.dir, "parco", "letture.json"), "w") as fh:
            json.dump(letture, fh)

    def test_uno_per_famiglia_il_piu_leggero(self):
        scelti = [(k, c["nome"]) for k, c in self.parco._una_per_famiglia(self.dir)]
        self.assertEqual(scelti, [("flowpack", "b"), ("vassoio", "c")])

    def test_la_richiesta_del_parco_e_una_prova(self):
        caso = {"nome": "a", "file": ["a.pdf"], "opzioni": {"kind": "flowpack"}}
        req = self.parco._richiesta("http://x", "/api/build", self.dir, caso)
        opts = json.loads(req.get_header("X-pack3d"))
        self.assertIs(opts["prova"], True)
        self.assertEqual(opts["kind"], "flowpack")


class NumeriDelleQuote(unittest.TestCase):
    """`quote.numeri`: il numero sta dove e' scritto, anche dopo un carattere
    che `get_text_range` perde (un glifo sul codice 3, come in certi font)."""

    def test_il_numero_resta_al_suo_posto(self):
        import pypdf
        import pypdfium2 as pdfium
        from pypdf.generic import DictionaryObject, NameObject, StreamObject
        from pack3d import quote
        from pack3d.dieline import PT2MM
        w = pypdf.PdfWriter()
        pagina = w.add_blank_page(300, 200)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        flusso = StreamObject()
        flusso.set_data(b"BT /F1 10 Tf 1 0 0 1 20 150 Tm (ab\\003cd) Tj ET\n"
                        b"BT /F1 10 Tf 1 0 0 1 200 40 Tm (148) Tj ET\n")
        pagina[NameObject("/Contents")] = w._add_object(flusso)
        pagina[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject(
            {NameObject("/F1"): w._add_object(font)})})
        with tempfile.TemporaryDirectory() as c:
            f = os.path.join(c, "quote.pdf")
            with open(f, "wb") as fh:
                w.write(fh)
            doc = pdfium.PdfDocument(f)
            try:
                tp = doc[0].get_textpage()
                self.assertEqual(len(quote.testo_per_indice(tp)), tp.count_chars())
                tp.close()
            finally:
                doc.close()
            (valore, x, y, asse), = quote.numeri(f)
        self.assertEqual((valore, asse), (148.0, 0))
        # scritto a x 200 punti, con la base a 40 dal basso di una pagina alta 200
        self.assertAlmostEqual(x, 200 * PT2MM, delta=1.0)
        self.assertAlmostEqual(y, (200 - 47) * PT2MM, delta=1.5)


class CassaDelParco(unittest.TestCase):
    """`parco.py costruisci --riusa`: si rifanno solo i casi cambiati."""

    def setUp(self):
        sys.path.insert(0, os.path.join(QUI, "prove"))
        import parco
        self.parco = parco
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.dir, True))
        os.makedirs(os.path.join(self.dir, "casi", "parco", "pdf"))
        os.makedirs(os.path.join(self.dir, "casi", "risorse"))
        for f, dati in (("a.pdf", b"a"), ("b.pdf", b"b")):
            with open(os.path.join(self.dir, "casi", "parco", "pdf", f), "wb") as fh:
                fh.write(dati)
        self.casi = [dict(nome="a", file=["a.pdf"]), dict(nome="b", file=["b.pdf"])]
        self.uscita = os.path.join(self.dir, "uscita")
        os.makedirs(self.uscita)

    def _impronte(self):
        r = self.parco._impronta_risorse(os.path.join(self.dir, "casi"))
        return {c["nome"]: self.parco._impronta_caso(os.path.join(self.dir, "casi"), c, r)
                for c in self.casi}

    def _costruito(self, nome, versione, caso):
        import json
        with open(os.path.join(self.uscita, nome + ".json"), "w") as fh:
            json.dump(dict(nome=nome, stato=200, md5=None, secondi=1,
                           versione=versione, caso=caso), fh)

    def test_si_riusa_solo_lo_stesso_caso_con_lo_stesso_codice(self):
        imp = self._impronte()
        self._costruito("a", "v1", imp["a"])
        self._costruito("b", "v0", imp["b"])          # codice di prima
        self._costruito("vecchio", "v1", "x")          # tolto dal manifesto
        r = self.parco._da_riusare(self.uscita, self.casi, "v1", imp, pulisci=True)
        self.assertEqual(set(r), {"a"})
        self.assertFalse(os.path.exists(os.path.join(self.uscita, "vecchio.json")))

    def test_costruisci_senza_riusa_come_lo_chiamano_prepara_e_varianti(self):
        import argparse
        import json
        with open(os.path.join(self.dir, "casi", "parco", "parco.json"), "w") as fh:
            json.dump({"casi": []}, fh)
        with contextlib.redirect_stdout(io.StringIO()):
            self.parco.costruisci(argparse.Namespace(
                casi=os.path.join(self.dir, "casi"), uscita=self.uscita, codice=None, solo=None))
        self.assertTrue(os.path.exists(os.path.join(self.uscita, "riassunto.json")))

    def test_un_pdf_o_un_opzione_cambiati_cambiano_l_impronta(self):
        prima = self._impronte()
        with open(os.path.join(self.dir, "casi", "parco", "pdf", "a.pdf"), "wb") as fh:
            fh.write(b"a2")
        self.casi[1]["opzioni"] = {"x": 1}
        dopo = self._impronte()
        self.assertNotEqual(prima["a"], dopo["a"])
        self.assertNotEqual(prima["b"], dopo["b"])
        with open(os.path.join(self.dir, "casi", "risorse", "colata.png"), "wb") as fh:
            fh.write(b"c")
        self.assertNotEqual(dopo["a"], self._impronte()["a"])


class SchedeDeiDifetti(unittest.TestCase):
    """DIFETTI.md: ogni scheda ha le sue parole, e `prepara` le trova."""

    def setUp(self):
        sys.path.insert(0, os.path.join(QUI, "prove"))
        import parco
        self.parco = parco

    def test_ogni_scheda_ha_le_parole(self):
        with open(os.path.join(QUI, "DIFETTI.md"), encoding="utf-8") as fh:
            parti = fh.read().split("\n## ")[1:]
        self.assertTrue(parti)
        for p in parti:
            self.assertIn("\nParole: ", p, p.splitlines()[0])

    def test_le_parole_trovano_la_scheda(self):
        self.assertEqual(self.parco._schede("Il pack e' costruito come flowpack mentre "
                                            "il PDF e' un astuccio")[0],
                         "La famiglia sbagliata")
        self.assertEqual(self.parco._schede("La fascia rossa del fronte e' finita "
                                            "sul retro"),
                         ["Il fronte sul retro, la grafica capovolta"])
        self.assertEqual(self.parco._schede("tutto bene"), [])


if __name__ == "__main__":
    unittest.main()
