"""
Le email a chi ha caricato un caso nuovo, quando la routine gli fa una domanda.

Chi ha in mano il pack spesso non ha Glam aperto, e magari entra con un
account condiviso: la domanda la vedrebbe solo tornando a guardare. Quando il
caso entra in coda, la pagina gli chiede un'email (si puo' saltare); quando la
routine chiede qualcosa (`prove/parco.py caso --stato domanda`), lo Space gli
scrive, con la domanda e il link per rispondere dalla pagina.

Le email partono da Resend (https://resend.com), con due valori dello Space:

    RESEND_API_KEY      la chiave dell'account (fra i Secrets)
    PACK3D_EMAIL_DA     il mittente, su un dominio verificato in Resend, per
                        esempio "ICCIO PDFto3D <casi@tuodominio.it>"

Senza tutti e due non parte niente, e il log dice perche': l'email resta nel
caso, pronta per quando l'invio c'e'.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = os.environ.get("PACK3D_EMAIL_API", "https://api.resend.com").rstrip("/")

# Abbastanza per scartare quello che non e' un indirizzo, senza pretendere di
# validarlo: se non esiste, lo dice Resend.
EMAIL_RE = re.compile(r"^[^@\s<>\"',;]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")


def email_valida(testo):
    """L'indirizzo ripulito, o None se non e' un indirizzo."""
    e = str(testo or "").strip()
    return e if len(e) <= 254 and EMAIL_RE.match(e) else None


def configurato():
    return bool(os.environ.get("RESEND_API_KEY", "").strip()
                and os.environ.get("PACK3D_EMAIL_DA", "").strip())


def testo_domanda(nome, cod, domanda, opzioni, link):
    """(oggetto, testo, html) dell'email con la domanda della routine."""
    oggetto = "Una domanda sul tuo pack «%s»" % nome
    righe = ["Ciao,", "",
             "stiamo correggendo il modello 3D del tuo pack «%s» e ci serve "
             "un'informazione:" % nome, "", domanda, ""]
    if opzioni:
        righe += ["Puoi scegliere fra:"] + ["- %s" % o for o in opzioni] + [""]
    righe += ["Rispondi da qui, anche con una foto del pack: %s" % link, "",
              "Codice del caso: %s" % cod, "",
              "Se non hai caricato tu questo PDF, ignora questa email."]
    testo = "\n".join(righe)
    e = html.escape
    corpo = ["<p>Ciao,</p>",
             "<p>stiamo correggendo il modello 3D del tuo pack <b>%s</b> e ci serve "
             "un'informazione:</p>" % e(nome),
             "<p style=\"font-size:16px\"><b>%s</b></p>" % e(domanda)]
    if opzioni:
        corpo.append("<p>Puoi scegliere fra:</p><ul>%s</ul>"
                     % "".join("<li>%s</li>" % e(o) for o in opzioni))
    corpo += ["<p><a href=\"%s\">Rispondi alla domanda</a>, anche con una foto del "
              "pack.</p>" % e(link, quote=True),
              "<p style=\"color:#777\">Codice del caso: %s<br>Se non hai caricato tu "
              "questo PDF, ignora questa email.</p>" % e(cod)]
    return oggetto, testo, "\n".join(corpo)


def manda(a, oggetto, testo, corpo_html):
    """Manda un'email. True se Resend l'ha presa; mai un'eccezione."""
    if not configurato():
        print("avvisi: email a un caso non mandata: mancano RESEND_API_KEY o "
              "PACK3D_EMAIL_DA fra i Secrets dello Space", file=sys.stderr)
        return False
    req = urllib.request.Request(
        API + "/emails", method="POST",
        data=json.dumps({"from": os.environ["PACK3D_EMAIL_DA"].strip(), "to": [a],
                         "subject": oggetto, "text": testo,
                         "html": corpo_html}).encode("utf-8"),
        headers={"Authorization": "Bearer " + os.environ["RESEND_API_KEY"].strip(),
                 "Content-Type": "application/json",
                 "User-Agent": "pack3d-studio"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        return True
    except urllib.error.HTTPError as e:
        # l'indirizzo nel log no: e' un dato di chi ha caricato il PDF
        print("avvisi: Resend rifiuta l'email (HTTP %s: %s)"
              % (e.code, e.read()[:300].decode("utf-8", "replace")), file=sys.stderr)
    except (OSError, ValueError) as e:
        print("avvisi: Resend non risponde (%s)" % e, file=sys.stderr)
    return False
