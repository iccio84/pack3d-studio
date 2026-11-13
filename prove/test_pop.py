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
