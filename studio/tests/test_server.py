"""
Prove sul livello di trasporto e sul gate di validazione della geometria.

Solo libreria standard, come il server: `python -m unittest discover -s tests`
gira anche dentro il container, senza aggiungere una dipendenza di sviluppo.

Qui **non** si verifica geometria: per quella servono i PDF di riferimento in
`tests/fixtures/` e le quote attese prese dalle tabelle di REGOLE.md. Un PDF
finto serve solo a far passare il controllo `%PDF` e ad arrivare al punto che
si vuole provare.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import server

# abbastanza per superare il controllo della firma: i test che lo usano si
# fermano prima che un parser PDF lo veda davvero
FAKE_PDF = b"%PDF-1.4 non e' un PDF vero, serve solo a passare la firma"

# geometria coerente: sono le quote del caso FULFIL gia' calibrato.
# 2*(36+19.5) + 2*15 = 141 = nastro; 18+18 = 36 = fronte; 116 + 2*13 = 142 = passo
GEOM_OK = dict(W=36.0, T=19.5, L=116.0, end_fin=13.0, side_fin=15.0,
               back_a=18.0, back_b=18.0, web_mm=141.0, step_mm=142.0,
               sheet_x0_mm=170.0, sheet_y0_mm=42.5)


class QuietHandler(server.Handler):
    def log_message(self, fmt, *a):
        pass


def post(port, path, body=FAKE_PDF, opts=None, raw_header=None):
    """(codice, testo, header) senza far esplodere le risposte non 2xx."""
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path), data=body, method="POST",
        headers={"Content-Type": "application/pdf",
                 "X-Pack3d": raw_header if raw_header is not None
                 else json.dumps(opts or {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e.headers


class ValidazioneGeometria(unittest.TestCase):
    """_flowpack_from_ai_json e' il gate che rifiuta una geometria non
    misurata. Da quando /api/build accetta la geometria dal client e' anche il
    filtro sull'input non fidato, quindi conta che rifiuti per davvero."""

    def test_geometria_coerente_passa(self):
        fp = server._flowpack_from_ai_json(GEOM_OK)
        self.assertAlmostEqual(fp.W, 36.0)
        self.assertAlmostEqual(fp.girth, 111.0)
        # lo steso e' in punti PDF, non in millimetri
        self.assertAlmostEqual(fp.sheet[0], 170.0 / server.PT2MM, places=6)
        self.assertAlmostEqual(fp.sheet[2] - fp.sheet[0],
                               142.0 / server.PT2MM, places=6)
        self.assertLess(fp.girth_span[0], fp.girth_span[1])

    def test_perimetro_piu_falde_diverso_dal_nastro(self):
        g = dict(GEOM_OK, web_mm=160.0)
        with self.assertRaises(ValueError) as ctx:
            server._flowpack_from_ai_json(g)
        self.assertIn("nastro", str(ctx.exception))

    def test_retro_diverso_dal_fronte(self):
        g = dict(GEOM_OK, back_a=10.0, back_b=10.0)
        with self.assertRaises(ValueError) as ctx:
            server._flowpack_from_ai_json(g)
        self.assertIn("retro", str(ctx.exception))

    def test_corpo_piu_pinne_diverso_dal_passo(self):
        g = dict(GEOM_OK, L=90.0)
        with self.assertRaises(ValueError) as ctx:
            server._flowpack_from_ai_json(g)
        self.assertIn("passo", str(ctx.exception))

    def test_campo_mancante(self):
        g = dict(GEOM_OK)
        del g["step_mm"]
        with self.assertRaises(ValueError):
            server._flowpack_from_ai_json(g)

    def test_valore_non_numerico(self):
        with self.assertRaises(ValueError):
            server._flowpack_from_ai_json(dict(GEOM_OK, W="trentasei"))

    def test_quota_non_positiva(self):
        with self.assertRaises(ValueError) as ctx:
            server._flowpack_from_ai_json(dict(GEOM_OK, T=0.0))
        self.assertIn("positive", str(ctx.exception))

    def test_tolleranza_del_tre_percento(self):
        # 141 -> 4,23 mm di tolleranza: 143 dentro, 148 fuori
        server._flowpack_from_ai_json(dict(GEOM_OK, web_mm=143.0))
        with self.assertRaises(ValueError):
            server._flowpack_from_ai_json(dict(GEOM_OK, web_mm=148.0))


class ResocontoNegliHeader(unittest.TestCase):
    """Il corpo di /api/build e' il GLB, quindi il resoconto va in un header:
    se non ci arriva, una geometria stimata dall'AI e una misurata sono
    indistinguibili per l'utente."""

    def _headers_di(self, meta):
        raccolti = []
        h = server.Handler.__new__(server.Handler)
        h.send_response = lambda *a, **k: None
        h.send_header = lambda k, v: raccolti.append((k, v))
        h.end_headers = lambda: None
        h.wfile = type("W", (), {"write": staticmethod(lambda b: None)})()
        server.Handler._send(h, 200, b"GLB", "model/gltf-binary", meta=meta)
        return dict(raccolti)

    def test_meta_presente_e_rileggibile(self):
        meta = ["flowpack morbido", "corpo 116.0 mm", "20 denti equilateri"]
        h = self._headers_di(meta)
        self.assertEqual(json.loads(h["X-Pack3d-Meta"]), meta)

    def test_meta_sempre_ascii(self):
        # http.server codifica gli header in latin-1: un trattino lungo o un
        # apostrofo tipografico farebbero fallire la risposta
        h = self._headers_di(["qualità alta — pinne lisce"])
        h["X-Pack3d-Meta"].encode("ascii")   # non deve alzare

    def test_nessun_header_senza_meta(self):
        h = self._headers_di(None)
        self.assertNotIn("X-Pack3d-Meta", h)


class LivelloHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.port = cls.srv.server_address[1]
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.th.join(timeout=5)

    def test_ping(self):
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/api/ping" % self.port) as r:
            self.assertEqual(r.status, 200)
            self.assertTrue(json.loads(r.read())["ok"])

    def test_interfaccia_servita(self):
        with urllib.request.urlopen("http://127.0.0.1:%d/" % self.port) as r:
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers["Content-Type"])

    def test_preflight_expone_il_meta(self):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/build" % self.port, method="OPTIONS")
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 204)
            self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
            # senza questo il browser non legge X-Pack3d-Meta cross-origin
            self.assertIn("X-Pack3d-Meta",
                          r.headers["Access-Control-Expose-Headers"])

    def test_corpo_vuoto(self):
        code, body, _ = post(self.port, "/api/build", body=b"")
        self.assertEqual(code, 400)
        self.assertIn("Nessun file", body)

    def test_non_e_un_pdf(self):
        code, body, _ = post(self.port, "/api/build", body=b"PK\x03\x04zip")
        self.assertEqual(code, 400)
        self.assertIn("non e' un PDF", body)

    def test_troppo_grande(self):
        vero = server.MAX_UPLOAD
        server.MAX_UPLOAD = 16
        try:
            code, body, _ = post(self.port, "/api/build")
            self.assertEqual(code, 413)
            self.assertIn("troppo grande", body)
        finally:
            server.MAX_UPLOAD = vero

    def test_header_json_malformato(self):
        code, body, _ = post(self.port, "/api/build", raw_header="{kind:")
        self.assertEqual(code, 400)
        self.assertIn("X-Pack3d", body)

    def test_header_non_oggetto(self):
        code, body, _ = post(self.port, "/api/build", raw_header="[1, 2]")
        self.assertEqual(code, 400)
        self.assertIn("oggetto JSON", body)

    def test_tipologia_altro(self):
        code, body, _ = post(self.port, "/api/build", opts={"kind": "altro"})
        self.assertEqual(code, 400)
        self.assertIn("non ancora supportata", body)

    def test_coppa_conica_dichiarata_non_costruibile(self):
        # la misura del settore c'e', il generatore di mesh no: meglio un 400
        # che un modello di un'altra famiglia consegnato come buono
        code, body, _ = post(self.port, "/api/analyze", opts={"kind": "cup"})
        self.assertEqual(code, 400)
        self.assertIn("Coppa conica", body)

    def test_dentini_non_numerici(self):
        code, body, _ = post(self.port, "/api/build",
                             opts={"kind": "flowpack", "teeth": "venti"})
        self.assertEqual(code, 400)
        self.assertIn("teeth", body)

    def test_geometria_dal_client_incoerente_rifiutata(self):
        # arriva dal browser: e' input non fidato e non viene creduta
        opts = {"kind": "flowpack", "teeth": 20,
                "params": {"flowpack": dict(GEOM_OK, web_mm=160.0)}}
        code, body, _ = post(self.port, "/api/build", opts=opts)
        self.assertEqual(code, 400)
        self.assertIn("params.flowpack", body)

    def test_endpoint_sconosciuto(self):
        code, _, _ = post(self.port, "/api/qualcosa")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
