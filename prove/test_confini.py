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


if __name__ == "__main__":
    unittest.main()
