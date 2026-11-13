"""
Le prove veloci dei materiali POP (`pack3d/pop/`), a parte da quelle dei
pack: una PR del POP non tocca prove/test_veloci.py, e una dei pack non tocca
questo file (regole/pop.md, *Il confine*; `prove/confini.py`).

    python3 -m unittest prove.test_pop
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, QUI)
os.environ.setdefault("PACK3D_LAVORATORI", "0")


class FinestraPop(unittest.TestCase):
    """La finestra «Crea materiali POP 3D da PDF»: la pagina con pop=1, il
    totem dichiarato che va in coda, e il modello che torna in quella
    finestra di Glam."""

    def test_il_totem_e_un_tipo_noto(self):
        from pack3d.famiglie import comune
        self.assertIn("totem", comune.KIND_NOTI)
        self.assertEqual(comune.normalizza_kind("Totem"), "totem")
        self.assertIn("materiale POP", comune.dichiarazione("totem", 1))

    def test_la_lettura_si_ferma_e_il_caso_va_in_coda(self):
        from pack3d import pop
        from pack3d.famiglie import registro
        with self.assertRaises(ValueError) as e:
            pop.analisi(["totem.pdf"], "totem")
        self.assertIn("totem: il codice non sa ancora costruirlo", str(e.exception))
        # la riga del registro passa da li', e nessuna famiglia dei pack
        # vale per un materiale POP
        righe = [f for f in registro.RICONOSCIMENTO if "totem" in f.dichiarate]
        self.assertEqual([f.nome for f in righe], ["materiale POP"])

    def test_il_modello_torna_nella_finestra_pop(self):
        from pack3d import pop
        self.assertEqual(pop.sezione_glam("totem"), "pop")
        self.assertIsNone(pop.sezione_glam("carton"))
        self.assertIsNone(pop.sezione_glam(None))
        self.assertEqual(pop.SEZIONI_GLAM["pop"], "Crea materiali POP 3D da PDF")
        sys.path.insert(0, os.path.join(QUI, "prove"))
        import parco
        self.assertEqual(parco.sezione_glam({"opzioni": {"kind": "totem"}}), "pop")
        self.assertIsNone(parco.sezione_glam({"opzioni": {"kind": "flowpack"}}))
        self.assertEqual(parco._nome_sezione({}), "Costruisci modello 3D da PDF")

    def test_la_coda_legge_la_finestra_dal_caso(self):
        from pack3d import coda
        verdetto = {"contesto": {"opzioni": {"kind": "totem"}}}
        with mock.patch.object(coda, "_leggi_json", return_value=(verdetto, "sha")):
            self.assertEqual(coda._sezione("casi/x"), "pop")
        with mock.patch.object(coda, "_leggi_json", return_value=({}, "sha")):
            self.assertIsNone(coda._sezione("casi/x"))
        with mock.patch.object(coda, "_leggi_json", side_effect=OSError("rete")):
            self.assertIsNone(coda._sezione("casi/x"))
        self.assertEqual(coda._con_sezione({}, "pop"), {"X-Model-Section": "pop"})
        self.assertEqual(coda._con_sezione({}, None), {})

    def test_l_espositore(self):
        from pack3d import pop
        from pack3d.famiglie import comune
        self.assertIn("espositore_pop", comune.KIND_NOTI)
        self.assertEqual(comune.normalizza_kind("espositore_pop"), "espositore_pop")
        self.assertIn("espositore (materiale POP", comune.dichiarazione("espositore_pop", 1))
        with self.assertRaises(ValueError) as e:
            pop.analisi(["espositore.pdf"], "espositore_pop")
        self.assertTrue(str(e.exception).startswith("espositore: il codice non sa"))
        self.assertEqual(pop.sezione_glam("espositore_pop"), "pop")
        # per i pack «espositore» resta il vassoio
        self.assertEqual(comune.normalizza_kind("espositore"), "vassoio")

    def test_nessun_materiale_ha_il_nome_di_un_pack(self):
        # un nome dei pack dichiarato POP cambierebbe strada ai pack
        # (`famiglie.comune` non si importa, se succede)
        from pack3d import pop
        from pack3d.famiglie import comune
        pack = set(comune.SINONIMI_PACK) | set(comune.SINONIMI_PACK.values())
        self.assertFalse(set(pop.MATERIALI_POP) & pack)
        self.assertIn("espositore", pack)

    def test_la_pagina_ha_la_voce_espositore(self):
        with open(os.path.join(QUI, "pack3d_studio.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('data-f="espositore_pop"><b>Espositore</b>', html)
        self.assertIn("espositore_pop: {nome: 'Espositore'", html)

    def test_la_pagina_ha_la_voce_totem(self):
        with open(os.path.join(QUI, "pack3d_studio.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('<div class="carte" id="carte-pop"', html)
        self.assertIn('data-f="totem"', html)
        self.assertIn("totem: {nome: 'Totem'", html)
        self.assertIn("'Crea materiali POP 3D da PDF'", html)


if __name__ == "__main__":
    unittest.main()


class FustellaPop(unittest.TestCase):
    """La fustella e il montaggio dell'espositore (`pop.fustella`,
    `pop.espositore`) su pezzi finti: niente PDF dei clienti."""

    def test_i_contorni_hanno_il_cartone_a_destra(self):
        import numpy as np
        from pack3d.pop import fustella as F
        m = np.zeros((8, 10), bool)
        m[1:7, 1:9] = True
        m[3:5, 4:6] = False                         # un foro
        anelli = F.contorni(m)
        self.assertEqual(len(anelli), 2)
        for an in anelli:
            a, b = an[0], an[1]
            e = b - a
            p = (a + b) / 2 + np.array([-e[1], e[0]]) * 0.5
            self.assertTrue(m[int(np.floor(p[1])), int(np.floor(p[0]))])

    def test_le_curve_restano_curve_e_i_gradini_spariscono(self):
        import numpy as np
        from pack3d.pop import fustella as F
        # un cerchio di raggio 50 campionato fitto: semplificato resta un
        # cerchio entro 0,05 mm, con abbastanza punti da sembrare tondo
        t = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
        cerchio = np.stack([50 * np.cos(t), 50 * np.sin(t)], 1)
        s = F.semplifica(cerchio, 0.05)
        self.assertGreater(len(s), 40)
        self.assertLess(np.abs(np.hypot(*s.T) - 50).max(), 0.06)
        # i gradini di un bordo di pixel finiscono sulla linea vera
        gradini = np.array([[x, 10.0 + (x % 2) * 0.8] for x in range(20)], float)
        su = F.aggancia(gradini, [[(0.0, 10.4), (30.0, 10.4)]], toll=2.0)
        self.assertEqual(len(su), len(gradini))
        self.assertLess(np.abs(su[:, 1] - 10.4).max(), 1e-9)

    def test_due_parti_che_si_incrociano_si_intagliano(self):
        import numpy as np
        from PIL import Image
        from pack3d.pop import espositore as E, fustella as F
        G = F.Griglia((0.0, 0.0, 100.0, 100.0), 1.0)
        mo = E.Montaggio(G, 6.0)
        mo.texture(Image.new("RGB", (G.W, G.H), "orange"))
        masc = np.ones((60, 60), bool)
        a = F.Pezzo((0.0, 0.0, 60.0, 60.0), nome="a")
        b = F.Pezzo((0.0, 0.0, 60.0, 60.0), nome="b")
        # un ripiano a y = 50 e una parete che lo attraversa a x = 30
        mo.pannello(a, masc, (0, 0), lambda lx, ly: (lx, 50.0, ly), (0, 1, 0), "ripiano")
        mo.pannello(b, masc, (0, 0), lambda lx, ly: (30.0, 20.0 + ly, lx), (1, 0, 0), "parete")
        V, UV, T, parti = mo.array(lambda p: 0 if p["nome"] == "ripiano" else 1)
        self.assertEqual(E.intersezioni(mo), [])
        self.assertTrue(any(n == "parete" and contro == "ripiano"
                            for n, contro, _ in mo.intagli))
        # la parete e' in due pezzi, sopra e sotto il ripiano
        Vp = V[np.unique(T[parti[1][1]:parti[1][2]])]
        self.assertFalse(np.any((Vp[:, 1] > 50.5) & (Vp[:, 1] < 55.5)))
        # senza l'ordine resta la compenetrazione, e il controllo la trova
        mo2 = E.Montaggio(G, 6.0)
        mo2.texture(Image.new("RGB", (G.W, G.H), "orange"))
        mo2.pannello(a, masc, (0, 0), lambda lx, ly: (lx, 50.0, ly), (0, 1, 0), "ripiano")
        mo2.pannello(b, masc, (0, 0), lambda lx, ly: (30.0, 20.0 + ly, lx), (1, 0, 0), "parete")
        mo2.array()
        self.assertEqual(len(E.intersezioni(mo2)), 1)

    def test_un_pannello_storto_si_ferma(self):
        import numpy as np
        from pack3d.pop import espositore as E, fustella as F
        G = F.Griglia((0.0, 0.0, 100.0, 100.0), 1.0)
        mo = E.Montaggio(G, 6.0)
        p = F.Pezzo((0.0, 0.0, 60.0, 60.0))
        with self.assertRaises(ValueError) as e:
            mo.pannello(p, np.ones((60, 60), bool), (0, 0),
                        lambda lx, ly: (lx, 0.0, min(lx, 30.0)), (0, 1, 0), "storto")
        self.assertIn("non e' piatto", str(e.exception))


class PiegheEIncisioniPop(unittest.TestCase):
    """Le pieghe tonde, lo spessore dalle pieghe doppie e la prefustella
    incisa dell'espositore."""

    def test_la_piega_tonda_unisce_i_due_pannelli(self):
        import numpy as np
        from pack3d.pop import espositore as E
        t = 4.0
        # il bordo davanti di un fianco: dal pannello esterno (x = -2t,
        # cartone verso +x) alla parete interna (x = 0, cartone verso -x)
        punto, curva = E.piega_tonda((-t, 0.0, 300.0), (-1, 0, 0), (0, 0, 1), t, np.pi,
                                     lambda lx, ly: lx / 8.0, lambda lx, ly: (0.0, ly, 0.0), 0)
        self.assertIsInstance(curva, E.Curva)
        np.testing.assert_allclose(punto(0.0, 5.0), (-2 * t, 5.0, 300.0), atol=1e-9)
        np.testing.assert_allclose(punto(8.0, 5.0), (0.0, 5.0, 300.0), atol=1e-9)
        np.testing.assert_allclose(punto(4.0, 5.0), (-t, 5.0, 300.0 + t), atol=1e-9)
        np.testing.assert_allclose(curva.dentro(0.0, 0.0), (1, 0, 0), atol=1e-9)
        np.testing.assert_allclose(curva.dentro(8.0, 0.0), (-1, 0, 0), atol=1e-9)

    def test_lo_spessore_dalle_pieghe_doppie(self):
        from pack3d.pop import espositore as E
        m = {"fsx_piega": (313, 321), "fsx_cima": (75, 83), "fdx_piega": (244, 252),
             "fdx_cima": (75, 83), "ripiano_sup": {"pieghe_v": [40, 415, 421]},
             "ripiano_inf": {"pieghe_v": [383, 389, 764]}, "div_v": [77.5, 82.5]}
        self.assertEqual(E.spessore(m), 4.0)

    def test_la_prefustella_e_un_taglio_dentro(self):
        from pack3d.pop import fustella as F
        bordo = [[(0, 0), (100, 0), (100, 60), (0, 60), (0, 0)]]
        arco = [[(30, 20), (40, 15), (50, 20)]]
        p = F.Pezzo((0.0, 0.0, 100.0, 60.0), tagli=bordo + arco)
        interni = F.tagli_interni(p)
        self.assertEqual(len(interni), 1)
        self.assertIs(interni[0], arco[0])

    def test_il_solco_scende_sulla_linea(self):
        import numpy as np
        from pack3d.pop import fustella as F
        linea = [np.array([[0.0, 0.0], [10.0, 0.0]])]
        pr = F.profondita_solco(np.array([[5.0, 0.0], [5.0, 0.25], [5.0, 2.0]]),
                                linea, 1.0, 0.9)
        self.assertAlmostEqual(pr[0], 0.9, places=3)
        self.assertAlmostEqual(pr[1], 0.45, places=2)
        self.assertEqual(pr[2], 0.0)
        # i campioni del solco: la linea e i due bordi, piu' fitti della larghezza
        s = F.solchi(linea, 1.0, 0.35)
        self.assertTrue(np.any(np.isclose(s[:, 1], 0.5)) and np.any(np.isclose(s[:, 1], -0.5)))

    def test_un_taglio_dentro_non_fa_esplodere_i_triangoli(self):
        import numpy as np
        from pack3d.pop import fustella as F
        # un pannello con una fessura larga zero: i due bordi sulla stessa
        # linea non si spezzano all'infinito
        anello = np.array([[0, 0], [100, 0], [100, 50], [60, 50], [60, 20],
                           [60, 50], [0, 50]], float)
        pts, tri = F.triangola([anello])
        self.assertLess(len(tri), 2000)
        self.assertGreater(len(tri), 0)


class PiegheSempliciPop(unittest.TestCase):
    """Le pieghe semplici tonde (`Montaggio.arrotonda`) e le note tolte."""

    def _due_pannelli(self, convessa):
        import numpy as np
        from PIL import Image
        from pack3d.pop import espositore as E, fustella as F
        G = F.Griglia((0.0, 0.0, 100.0, 100.0), 1.0)
        mo = E.Montaggio(G, 4.0)
        mo.texture(Image.new("RGB", (G.W, G.H), "orange"))
        pz = F.Pezzo((0.0, 0.0, 60.0, 80.0), tagli=[[(0, 0), (60, 0), (60, 80), (0, 80), (0, 0)]])
        pz.linee_piega = [[(0.0, 40.0), (60.0, 40.0)]]
        a = np.zeros((80, 60), bool)
        a[:42] = True                       # sopra la piega (con la sua banda)
        b = np.zeros((80, 60), bool)
        b[38:] = True
        # A: un davanti in piedi a z = 0 (stampa verso +z); B: il fondo, che
        # va indietro (convessa: stampa sotto) o avanti (stampa sopra, dentro)
        mo.pannello(pz, a, (0, 0), lambda lx, ly: (lx, 40.0 - ly, 0.0), (0, 0, -1), "f")
        if convessa:
            mo.pannello(pz, b, (0, 0), lambda lx, ly: (lx, 0.0, -(ly - 40.0)), (0, 1, 0), "f")
        else:
            mo.pannello(pz, b, (0, 0), lambda lx, ly: (lx, 0.0, ly - 40.0), (0, -1, 0), "f")
        return mo

    def test_la_piega_con_la_stampa_fuori_si_arrotonda(self):
        import numpy as np
        mo = self._due_pannelli(True)
        V, UV, T, parti = mo.array()
        self.assertEqual(len(mo.tonde), 1)
        self.assertAlmostEqual(mo.tonde[0][1], 90.0, places=0)
        self.assertEqual(sum(1 for p in mo.grezzi if p.get("curva") is not None), 1)
        # nessun vertice della faccia stampata sullo spigolo vivo
        vicini = np.hypot(V[:, 1], V[:, 2]) < 0.5
        self.assertFalse(vicini.any())

    def test_la_piega_con_la_stampa_dentro_resta_viva(self):
        mo = self._due_pannelli(False)
        mo.array()
        self.assertEqual(mo.tonde, [])

    def test_le_note_si_tolgono(self):
        from pack3d.pop import fustella as F
        for nome in ("notes", "Note tecniche", "COLLA", "legenda"):
            self.assertTrue(F.NOTE.search(nome), nome)
        for nome in ("technical-drawing", "0101-italy.ITAL", "shared", "grafica"):
            self.assertFalse(F.NOTE.search(nome), nome)


def _pdf_totem(percorso, colore, specchio=False):
    """Un PDF finto di totem: una pagina 200 x 300 mm col pannello pieno di
    `colore`, il suo contorno di taglio (con una punta in Bezier sopra, come
    l'aletta) e un popup tondo, in magenta, solo contorno. Il retro ha il
    contorno specchiato."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as R
    PT = 72 / 25.4
    W, H = 200.0, 300.0
    doc = pdfium.PdfDocument.new()
    pg = doc.new_page(W * PT, H * PT)

    def X(x):
        return (W - x if specchio else x) * PT

    def Y(y):
        return (H - y) * PT

    def tracciato(punti, curve=(), riempi=None, chiudi=True):
        h = R.FPDFPageObj_CreateNewPath(X(punti[0][0]), Y(punti[0][1]))
        for p in punti[1:]:
            if p in curve:
                (a, b, c) = curve[p]
                R.FPDFPath_BezierTo(h, X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), X(c[0]), Y(c[1]))
            else:
                R.FPDFPath_LineTo(h, X(p[0]), Y(p[1]))
        if chiudi:
            R.FPDFPath_Close(h)
        if riempi:
            R.FPDFPageObj_SetFillColor(h, *riempi, 255)
            R.FPDFPath_SetDrawMode(h, R.FPDF_FILLMODE_ALTERNATE, False)
        else:
            R.FPDFPageObj_SetStrokeColor(h, 237, 2, 140, 255)
            R.FPDFPageObj_SetStrokeWidth(h, 1.0)
            R.FPDFPath_SetDrawMode(h, 0, True)
        R.FPDFPage_InsertObject(pg.raw, h)
    # il pannello: da (50, 60) a (150, 260), con la punta sopra fra x 80 e 100
    bordo = [(50, 60), (80, 60), "punta", (150, 60), (150, 260), (50, 260)]
    pts = [(50, 60), (80, 60), (100, 60), (150, 60), (150, 260), (50, 260)]
    curve = {(100, 60): ((85, 30), (95, 30), (100, 60))}
    tracciato(pts, riempi=colore)
    tracciato(pts, curve=curve)
    del bordo
    # il popup: un quadrato smussato dentro
    tracciato([(80, 120), (120, 120), (120, 160), (80, 160)], riempi=(255, 255, 255))
    tracciato([(80, 120), (120, 120), (120, 160), (80, 160)])
    R.FPDFPage_GenerateContent(pg.raw)
    doc.save(percorso)


class TotemPop(unittest.TestCase):
    """Il totem lenticolare (`pop.totem`) su PDF finti."""

    def test_il_raggio_dalla_freccia(self):
        import numpy as np
        from pack3d.pop import totem
        R = totem.raggio(580.0, 100.0)
        self.assertAlmostEqual(R * (1 - np.cos(580.0 / (2 * R))), 100.0, places=3)

    def test_il_contorno_tiene_le_curve(self):
        import tempfile
        from pack3d.pop import fustella as F, totem
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, "fronte.pdf")
            _pdf_totem(pdf, (200, 30, 60))
            tagli = F.contorni_di_taglio(pdf)
            pannello, popup = totem.leggi(pdf)
        # la punta in Bezier sale sopra il bordo: la curva, non la corda
        self.assertLess(pannello[:, 1].min(), 50.0)
        self.assertGreater(pannello[:, 1].min(), 35.0)
        self.assertEqual(len(tagli), 2)
        self.assertEqual(len(popup), 1)

    def test_il_taglio_curvo_esce_dalla_grafica(self):
        import tempfile
        import numpy as np
        from scipy.spatial import cKDTree
        from pack3d.pop import fustella as F, totem
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, "fronte.pdf")
            _pdf_totem(pdf, (200, 30, 60))
            pannello, popup = totem.leggi(pdf)
            linee = [np.vstack([a, a[:1]]) for a in [pannello] + popup]
            _, sul_dt = F._oggetti(pdf, cKDTree(F._campiona(linee, 0.5)))
        self.assertEqual(len(sul_dt), 2)            # il contorno con la punta e il popup

    def test_un_totem_curvo_con_la_piattina(self):
        import tempfile
        import numpy as np
        from pack3d import vista
        from pack3d.pop import totem
        with tempfile.TemporaryDirectory() as d:
            f, r = os.path.join(d, "fronte.pdf"), os.path.join(d, "retro.pdf")
            _pdf_totem(f, (200, 30, 60))
            _pdf_totem(r, (30, 60, 200), specchio=True)
            glb = os.path.join(d, "totem.glb")
            avvisi, m = totem.monta(f, r, glb, freccia=20.0)
            parti = {p["nome"]: p for p in vista.leggi_glb(glb)}
        self.assertIn("totem: pannello 100 x", avvisi[0])
        for nome in ("pannello_fronte", "pannello_retro", "popup_fronte_1", "popup_retro_1",
                     "piattina", "distanziali"):
            self.assertIn(nome, parti)
        def verts(nome):                                     # mm, solo quelli della parte
            q = parti[nome]
            return q["verts"][np.unique(q["tris"])] * 1000.0
        V = verts("pannello_fronte")
        # curvo: il centro davanti, i lati indietro della freccia
        self.assertAlmostEqual(V[:, 2].max(), 0.0, delta=0.5)
        self.assertAlmostEqual(-V[:, 2].min(), 20.0 + 1.5, delta=2.0)
        # liscio: tanti vertici lungo l'arco, non due spigoli
        self.assertGreater(len(np.unique(np.round(V[:, 0], 0))), 15)
        # in piedi sulla piattina
        P = verts("piattina")
        self.assertAlmostEqual(P[:, 1].max(), totem.PIATTINA_SPESSORE, delta=0.01)
        self.assertAlmostEqual(V[:, 1].min(), totem.PIATTINA_SPESSORE, delta=0.5)
