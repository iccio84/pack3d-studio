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
