"""
Prove sul ciclo di tool use, con un client Anthropic finto.

Nessuna chiamata di rete e nessuna spesa: il client finto risponde con blocchi
costruiti a mano, come il vero SDK. Serve a fissare la forma delle richieste
(strumenti esposti, schema di chiusura, uso di extra_system) e il
comportamento nei casi limite, che sono quelli che in produzione sono costati
i commit 12f6fcb, 3828d57 e 82ebd6b.
"""
import types
import unittest
from unittest import mock

import agent

# `agent` importa `anthropic` solo dentro analyse(), e solo se il client non
# arriva dal chiamante: passando un client finto non serve ne' la libreria ne'
# una chiave.
#
# Gli strumenti di misura veri leggono il PDF, quindi qui vanno sostituiti: un
# PDF finto li farebbe fallire e la prova misurerebbe le librerie installate
# invece del ciclo.
MISURA_FINTA = {"list_paths": lambda pdf, **kw: [{"index": 0, "larghezza_mm": 415.0}]}


def senza_strumenti_veri():
    return mock.patch.dict(agent.RUN, MISURA_FINTA, clear=True)


class Blocco:
    """Un blocco di contenuto come lo espone il vero SDK."""

    def __init__(self, type, **kw):
        self.type = type
        for k, v in kw.items():
            setattr(self, k, v)


def testo(t):
    return Blocco("text", text=t)


def chiamata(name, input=None, id="tu_1"):
    return Blocco("tool_use", name=name, input=input or {}, id=id)


class Risposta:
    def __init__(self, content, stop_reason="tool_use"):
        self.content = content
        self.stop_reason = stop_reason


class ClienteFinto:
    """Restituisce le risposte in coda e registra le richieste ricevute."""

    def __init__(self, *risposte):
        self.coda = list(risposte)
        self.richieste = []
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kw):
        # `analyse` accoda ai messaggi in place, quindi va registrata una
        # copia: tenendo il riferimento si rileggerebbe lo stato finale della
        # conversazione invece di quello spedito in questa richiesta
        kw = dict(kw, messages=list(kw["messages"]))
        self.richieste.append(kw)
        return self.coda.pop(0) if self.coda else Risposta([testo("finito")],
                                                           "end_turn")


CONCLUSIONE = {"famiglia": "flowpack", "quote": {"W": 36.0}, "avvisi": []}


class CicloDiChiusura(unittest.TestCase):
    def test_conclude_con_lo_strumento(self):
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        par, tr = agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(par, CONCLUSIONE)
        self.assertEqual([t["tool"] for t in tr], ["presenta_risultato"])

    def test_misura_poi_conclude(self):
        c = ClienteFinto(
            Risposta([chiamata("list_paths", {"limit": 4}, id="a")]),
            Risposta([chiamata("presenta_risultato", CONCLUSIONE, id="b")]))
        with senza_strumenti_veri():
            par, tr = agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(par, CONCLUSIONE)
        self.assertEqual([t["tool"] for t in tr],
                         ["list_paths", "presenta_risultato"])
        # il risultato dello strumento deve tornare al modello come tool_result
        ultimi = c.richieste[-1]["messages"][-1]["content"]
        self.assertEqual(ultimi[0]["type"], "tool_result")
        self.assertEqual(ultimi[0]["tool_use_id"], "a")

    def test_strumento_sconosciuto_non_interrompe(self):
        c = ClienteFinto(
            Risposta([chiamata("misura_inventata", {}, id="a")]),
            Risposta([chiamata("presenta_risultato", CONCLUSIONE, id="b")]))
        par, tr = agent.analyse("finto.pdf", "carton", client=c)
        self.assertEqual(par, CONCLUSIONE)
        self.assertIn("errore", tr[0]["output"])


class ReteDiSicurezza(unittest.TestCase):
    """Il modello dovrebbe sempre chiudere con presenta_risultato. Quando non
    lo fa, il motivo va distinguibile nei log: e' il commit 82ebd6b."""

    def test_prosa_con_json_recuperato(self):
        c = ClienteFinto(Risposta(
            [testo('Ecco:\n```json\n{"famiglia":"carton"}\n```')], "end_turn"))
        par, _ = agent.analyse("finto.pdf", "carton", client=c)
        self.assertEqual(par["famiglia"], "carton")

    def test_troncamento_riporta_stop_reason(self):
        c = ClienteFinto(Risposta([testo("stavo misurando quando")], "max_tokens"))
        par, _ = agent.analyse("finto.pdf", "carton", client=c)
        self.assertIn("errore", par)
        self.assertEqual(par["stop_reason"], "max_tokens")

    def test_giro_a_vuoto_si_ferma(self):
        vero = agent.MAX_STEPS
        agent.MAX_STEPS = 3
        try:
            c = ClienteFinto(*[Risposta([chiamata("list_paths", {}, id="a")])
                               for _ in range(3)])
            with senza_strumenti_veri():
                par, tr = agent.analyse("finto.pdf", "carton", client=c)
            self.assertIn("troppi passi", par["errore"])
            self.assertEqual(len(c.richieste), 3)
        finally:
            agent.MAX_STEPS = vero


class FormaDellaRichiesta(unittest.TestCase):
    def test_regole_nel_system_prompt(self):
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", client=c)
        system = c.richieste[0]["system"]
        # REGOLE.md e' un artefatto di prompt, non solo documentazione
        self.assertIn("Regole del progetto", system)
        self.assertIn("presenta_risultato", system)

    def test_extra_system_in_coda(self):
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", client=c,
                      extra_system="ISTRUZIONE-IN-CODA")
        self.assertTrue(c.richieste[0]["system"].rstrip()
                        .endswith("ISTRUZIONE-IN-CODA"))

    def test_schema_flowpack_solo_se_richiesto(self):
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", client=c, require_flowpack=True)
        chiusura = next(t for t in c.richieste[0]["tools"]
                        if t["name"] == "presenta_risultato")
        self.assertIn("flowpack", chiusura["input_schema"]["required"])
        campi = chiusura["input_schema"]["properties"]["flowpack"]["required"]
        for k in ("W", "T", "L", "web_mm", "step_mm", "sheet_x0_mm"):
            self.assertIn(k, campi)

        c2 = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "carton", client=c2)
        chiusura2 = next(t for t in c2.richieste[0]["tools"]
                         if t["name"] == "presenta_risultato")
        self.assertNotIn("flowpack", chiusura2["input_schema"]["properties"])

    def test_schema_di_base_non_mutato_fra_chiamate(self):
        # _conclude_tool fa una copia profonda: senza, require_flowpack=True
        # inquinerebbe ogni analisi successiva del processo
        prima = agent._CONCLUDE_BASE["input_schema"]["required"][:]
        agent._conclude_tool(True)
        self.assertEqual(agent._CONCLUDE_BASE["input_schema"]["required"], prima)
        self.assertNotIn("flowpack",
                         agent._CONCLUDE_BASE["input_schema"]["properties"])

    def test_risposte_dell_utente_nel_primo_messaggio(self):
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", {"teeth": 30, "soft": "morbido"},
                      client=c)
        primo = c.richieste[0]["messages"][0]["content"]
        self.assertIn("flowpack", primo)
        self.assertIn("30", primo)
        self.assertIn("morbido", primo)


if __name__ == "__main__":
    unittest.main()
