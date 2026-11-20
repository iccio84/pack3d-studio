"""
Le prove del confine fra POP e pack (`prove/confini.py`): una PR verso
coda-settimana non tocca insieme i materiali POP e le famiglie dei pack.

    python3 -m unittest prove.test_confini
"""
from __future__ import annotations

import os
import sys
import unittest

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(QUI, "prove"))

import confini  # noqa: E402


class ConfineFraPopEPack(unittest.TestCase):

    def test_le_parti(self):
        self.assertEqual(confini.parte("pack3d/pop/__init__.py"), "pop")
        self.assertEqual(confini.parte("pack3d/pop/totem.py"), "pop")
        self.assertEqual(confini.parte("regole/pop.md"), "pop")
        self.assertEqual(confini.parte("prove/test_pop.py"), "pop")
        self.assertEqual(confini.parte("pack3d_studio.html"), "comune")
        self.assertEqual(confini.parte("pack3d/famiglie/registro.py"), "comune")
        self.assertEqual(confini.parte("REGOLE.md"), "comune")
        self.assertEqual(confini.parte(".github/workflows/prove.yml"), "comune")
        self.assertEqual(confini.parte("pack3d/flowpack.py"), "pack")
        self.assertEqual(confini.parte("pack3d/famiglie/astuccio.py"), "pack")
        self.assertEqual(confini.parte("regole/flowpack.md"), "pack")
        # una cartella che comincia come quella del POP non e' sua
        self.assertEqual(confini.parte("pack3d/popolare.py"), "pack")
        self.assertEqual(confini.parte("regole/pop2.md"), "pack")

    def test_pop_col_comune_va_bene(self):
        va, _ = confini.controlla(["pack3d/pop/__init__.py", "pack3d_studio.html",
                                   "GLAM.md"])
        self.assertTrue(va)

    def test_pack_col_comune_va_bene(self):
        va, _ = confini.controlla(["pack3d/flowpack.py", "server.py",
                                   "prove/test_veloci.py"])
        self.assertTrue(va)

    def test_pop_e_pack_insieme_no(self):
        va, righe = confini.controlla(["pack3d/pop/__init__.py", "pack3d/flowpack.py"])
        self.assertFalse(va)
        testo = "\n".join(righe)
        self.assertIn("vanno in due PR", testo)
        self.assertIn("  pack3d/flowpack.py", testo)
        self.assertIn("  pack3d/pop/__init__.py", testo)

    def test_i_file_cambiati_da_git(self):
        # questo repository: fra un commit e se stesso non cambia niente
        if not os.path.isdir(os.path.join(QUI, ".git")):
            self.skipTest("niente git")
        prima = os.getcwd()
        os.chdir(QUI)
        try:
            self.assertEqual(confini.cambiati("HEAD", "HEAD"), [])
        finally:
            os.chdir(prima)


class UnaFamigliaPerPR(unittest.TestCase):
    """Dentro i pack, una famiglia per PR col nucleo comune; la Trade Unit
    con la famiglia del pack che contiene; «Trasversale:» per il resto."""

    def test_le_famiglie(self):
        self.assertEqual(confini.famiglia("pack3d/flowpack.py"), "flowpack")
        self.assertEqual(confini.famiglia("pack3d/famiglie/astuccio.py"), "cartotecnico")
        self.assertEqual(confini.famiglia("regole/riempimenti.md"), "trade unit")
        self.assertEqual(confini.famiglia("pack3d/uovo.py"), "incarti")
        self.assertEqual(confini.famiglia("pack3d/dieline.py"), "nucleo")
        self.assertEqual(confini.famiglia("pack3d/artwork.py"), "nucleo")
        self.assertEqual(confini.famiglia("server.py"), "comune")
        self.assertEqual(confini.famiglia("pack3d/pop/totem.py"), "pop")

    def test_una_famiglia_col_nucleo_va_bene(self):
        va, righe = confini.controlla(["pack3d/dieline.py", "pack3d/artwork.py",
                                       "pack3d/incisioni.py", "regole/astucci.md"])
        self.assertTrue(va)
        self.assertIn("famiglie dei pack: cartotecnico", righe)

    def test_trade_unit_col_suo_pack_va_bene(self):
        va, _ = confini.controlla(["pack3d/riempimento.py", "pack3d/famiglie/flowpack.py"])
        self.assertTrue(va)

    def test_due_famiglie_no(self):
        va, righe = confini.controlla(["pack3d/flowpack.py", "pack3d/incisioni.py"])
        self.assertFalse(va)
        self.assertIn("Una famiglia per PR", "\n".join(righe))
        va, _ = confini.controlla(["pack3d/riempimento.py", "pack3d/flowpack.py",
                                   "pack3d/apertura.py"])
        self.assertFalse(va)

    def test_trasversale_si_ma_non_col_pop(self):
        va, _ = confini.controlla(["pack3d/flowpack.py", "pack3d/incisioni.py"],
                                  trasversale=True)
        self.assertTrue(va)
        va, _ = confini.controlla(["pack3d/flowpack.py", "pack3d/pop/totem.py"],
                                  trasversale=True)
        self.assertFalse(va)


if __name__ == "__main__":
    unittest.main()
