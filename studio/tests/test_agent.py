"""
Prove sul ciclo di tool use, con un client Anthropic finto.

Nessuna chiamata di rete e nessuna spesa: il client finto risponde con blocchi
costruiti a mano, come il vero SDK. Serve a fissare la forma delle richieste
(strumenti esposti, schema di chiusura, uso di extra_system) e il
comportamento nei casi limite, che sono quelli che in produzione sono costati
i commit 12f6fcb, 3828d57 e 82ebd6b.
"""
import io
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


class Troncamento(unittest.TestCase):
    """Su Render un'analisi e' morta con stop_reason "max_tokens", nessun
    testo e tre strumenti gia' chiamati: le misure c'erano, la conclusione no,
    e l'intera chiamata da 20-60 secondi e' finita in un 500. Un troncamento
    deve costare un giro, non l'analisi."""

    def ruoli(self, richiesta):
        return [m["role"] for m in richiesta["messages"]]

    def test_riprova_e_conclude(self):
        c = ClienteFinto(Risposta([], "max_tokens"),
                         Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        par, _ = agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(par, CONCLUSIONE)
        self.assertEqual(len(c.richieste), 2)

    def test_il_turno_troncato_non_torna_al_modello(self):
        # un tool_use senza il suo tool_result fa fallire la richiesta dopo:
        # il turno troncato va buttato, non rimandato indietro
        c = ClienteFinto(
            Risposta([chiamata("list_paths", {"limit": 4}, id="mozzo")],
                     "max_tokens"),
            Risposta([chiamata("presenta_risultato", CONCLUSIONE, id="b")]))
        with senza_strumenti_veri():
            par, tr = agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(par, CONCLUSIONE)
        inviati = c.richieste[1]["messages"]
        self.assertNotIn("assistant", self.ruoli(c.richieste[1]))
        self.assertNotIn("mozzo", repr(inviati))
        # e la misura mozzata non entra nella traccia: non e' mai stata fatta
        self.assertNotIn("list_paths", [t["tool"] for t in tr])

    def test_le_misure_gia_fatte_restano(self):
        c = ClienteFinto(
            Risposta([chiamata("list_paths", {"limit": 4}, id="a")]),
            Risposta([], "max_tokens"),
            Risposta([chiamata("presenta_risultato", CONCLUSIONE, id="b")]))
        with senza_strumenti_veri():
            par, tr = agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(par, CONCLUSIONE)
        inviati = c.richieste[2]["messages"]
        # 415.0 e' la misura finta: se sparisse, il modello ricomincerebbe
        self.assertIn("415.0", repr(inviati))
        # i ruoli devono alternarsi: la richiesta di concludere si attacca al
        # turno utente che c'e' gia', non ne apre un secondo di fila
        self.assertEqual(self.ruoli(c.richieste[2]),
                         ["user", "assistant", "user"])
        coda = inviati[-1]["content"]
        self.assertEqual(coda[0]["type"], "tool_result")
        self.assertEqual(coda[-1]["text"], agent.RIPRESA)

    def test_troncamento_al_primo_giro_non_rompe_i_ruoli(self):
        # qui il turno utente in coda e' il primo, che ha contenuto testuale
        # invece di una lista di blocchi
        c = ClienteFinto(Risposta([], "max_tokens"),
                         Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(self.ruoli(c.richieste[1]), ["user"])
        self.assertIn(agent.RIPRESA, c.richieste[1]["messages"][0]["content"])

    def test_se_si_tronca_sempre_si_arrende(self):
        vero = agent.MAX_TRONCAMENTI
        agent.MAX_TRONCAMENTI = 2
        try:
            c = ClienteFinto(*[Risposta([], "max_tokens") for _ in range(4)])
            par, _ = agent.analyse("finto.pdf", "flowpack", client=c)
            self.assertIn("troncata", par["errore"])
            self.assertEqual(par["stop_reason"], "max_tokens")
            # tre chiamate: l'originale piu' i due tentativi, non MAX_STEPS
            self.assertEqual(len(c.richieste), 3)
        finally:
            agent.MAX_TRONCAMENTI = vero

    def test_il_log_dice_cosa_c_era_nel_turno_perduto(self):
        # con testo_grezzo vuoto i log di Render non dicevano niente: i tipi
        # di blocco e i token spesi distinguono la prosa dal giro a vuoto
        r = Risposta([chiamata("list_paths", {}, id="a")], "max_tokens")
        r.usage = types.SimpleNamespace(input_tokens=12000, output_tokens=8000)
        with mock.patch.object(agent.sys, "stderr", io.StringIO()) as err:
            agent._log_troncamento(r, [{"tool": "analyze_flowpack"}])
        riga = err.getvalue()
        self.assertIn("tool_use", riga)
        self.assertIn("8000", riga)
        self.assertIn("analyze_flowpack", riga)

    def test_il_log_regge_una_risposta_senza_blocchi(self):
        with mock.patch.object(agent.sys, "stderr", io.StringIO()) as err:
            agent._log_troncamento(Risposta([], "max_tokens"), [])
        self.assertIn("nessuno", err.getvalue())


class FormaDellaRichiesta(unittest.TestCase):
    def test_il_budget_copre_ragionamento_e_risposta(self):
        """Il ragionamento e la risposta pescano dallo stesso max_tokens.

        Sul primo collaudo vero il log ha detto blocchi ['thinking'] con
        8000/8000: tutto il budget speso a ragionare, niente per concludere.
        Il tetto deve restare sopra a quello che il ragionamento chiede da
        solo, altrimenti il ripiego si tronca ogni volta e il recupero
        diventa la regola invece dell'eccezione."""
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(c.richieste[0]["max_tokens"], agent.MAX_TOKENS)
        self.assertGreater(agent.MAX_TOKENS, 8000)

    def test_timeout_esplicito(self):
        """Con un tetto alto l'SDK rifiuta da solo la richiesta
        non-streaming che stima possa sforare i dieci minuti. Passare un
        timeout disattiva quella stima: senza, alzare MAX_TOKENS non
        allunga l'analisi, la fa fallire prima di partire."""
        c = ClienteFinto(Risposta([chiamata("presenta_risultato", CONCLUSIONE)]))
        agent.analyse("finto.pdf", "flowpack", client=c)
        self.assertEqual(c.richieste[0]["timeout"], agent.TIMEOUT)

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
