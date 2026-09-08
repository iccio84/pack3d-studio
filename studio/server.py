#!/usr/bin/env python3
"""
Backend di pack3d studio collegato all'API di Anthropic Claude (Vision via pypdfium2).
"""
from __future__ import annotations

import io
import json
import os
import sys
import traceback
import threading
import base64
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Importazione dell'SDK di Anthropic
try:
    import anthropic
except ImportError:
    sys.exit("Manca la libreria 'anthropic'. Installa con: pip install anthropic")

# Importazione di pypdfium2 per il rendering del PDF
try:
    import pypdfium2 as pdfium
except ImportError:
    sys.exit("Manca la libreria 'pypdfium2'. Installa con: pip install pypdfium2")

HERE = os.path.dirname(os.path.abspath(__file__))

# Inizializzazione controllata del client Anthropic
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("⚠️ CRITICO: La variabile d'ambiente ANTHROPIC_API_KEY non e' stata trovata!")
else:
    print(f"ℹ️ ANTHROPIC_API_KEY rilevata: {api_key[:8]}...{api_key[-4:]}")

anthropic_client = anthropic.Anthropic(api_key=api_key) if api_key else None


def load_project_rules():
    """Carica le regole del progetto da REGOLE.md se presente."""
    regole_path = os.path.join(HERE, "REGOLE.md")
    if os.path.exists(regole_path):
        with open(regole_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Sei un esperto di modellazione 3D da PDF di packaging."


def convert_pdf_to_png_base64(pdf_bytes: bytes) -> str:
    """Apre il PDF dal buffer e converte la prima pagina in PNG Base64 (DPI 144 / scale 2)."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    if len(pdf) == 0:
        raise ValueError("Il PDF caricato non contiene pagine.")
    
    page = pdf[0]
    image = page.render(scale=2).to_pil()
    
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("  %s\n" % (fmt % a))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Pack3d")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code, body, ctype="application/json", filename=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % filename)
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        """Risponde alle verifiche di stato (health check) di Render e del browser."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self._send(200, json.dumps({
                "ok": True,
                "api_key_configured": bool(api_key)
            }))
        
        path = os.path.join(HERE, "pack3d_studio.html")
        if os.path.exists(path):
            with open(path, "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        return self._send(404, "File non trovato")

    def do_POST(self):
        try:
            if not anthropic_client:
                return self._send(500, json.dumps({
                    "error": "ANTHROPIC_API_KEY non configurata su Render."
                }))

            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, json.dumps({"error": "Nessun file ricevuto"}))
            if n > MAX_UPLOAD:
                return self._send(413, json.dumps({"error": f"PDF troppo grande (limite {MAX_UPLOAD // (1024 * 1024)} MB)"}))
            
            pdf_data = self.rfile.read(n)
            if not pdf_data.startswith(b"%PDF"):
                return self._send(400, json.dumps({"error": "Il file caricato non e' un PDF valido"}))
            
            png_b64 = convert_pdf_to_png_base64(pdf_data)

            if self.path.startswith("/api/build") or self.path.startswith("/api/analyze"):
                if not _slots.acquire(blocking=False):
                    return self._send(503, json.dumps({"error": "Server occupato: riprova fra qualche secondo"}))
                
                try:
                    system_prompt = load_project_rules()

                    # Lista completa degli identificatori di modelli supportati dalla piattaforma
                    models_to_try = [
                        "claude-3-5-sonnet-latest",
                        "claude-3-5-sonnet-20241022",
                        "claude-3-5-sonnet-20240620",
                        "claude-3-5-haiku-latest",
                        "claude-3-haiku-20240307",
                        "sonnet-5",
                        "haiku-4.5"
                    ]

                    response = None
                    errors_log = []

                    for model_name in models_to_try:
                        try:
                            print(f"[API] Chiamata in corso con modello: {model_name}")
                            response = anthropic_client.messages.create(
                                model=model_name,
                                max_tokens=4096,
                                system=system_prompt,
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "image",
                                                "source": {
                                                    "type": "base64",
                                                    "media_type": "image/png",
                                                    "data": png_b64
                                                }
                                            },
                                            {
                                                "type": "text",
                                                "text": "Analizza l'immagine di questa fustella/packaging e genera la struttura del modello 3D seguendo le regole."
                                            }
                                        ]
                                    }
                                ]
                            )
                            print(f"✅ Successo con il modello: {model_name}")
                            break
                        except Exception as err:
                            msg = f"{model_name} -> {type(err).__name__}: {err}"
                            print(f"⚠️ {msg}")
                            errors_log.append(msg)

                    if not response:
                        return self._send(400, json.dumps({
                            "error": "Tutti gli identificatori di modello hanno restituito errore. Genera una nuova chiave dalla sezione 'Chiavi API' della console e aggiornala su Render.",
                            "details": errors_log
                        }))

                    result_3d = response.content[0].text
                    return self._send(200, json.dumps({"success": True, "model3d": result_3d}))

                finally:
                    _slots.release()

            return self._send(404, json.dumps({"error": "Endpoint sconosciuto"}))

        except Exception as e:
            traceback.print_exc()
            return self._send(500, json.dumps({"error": f"{type(e).__name__}: {e}"}))


MAX_UPLOAD = 60 * 1024 * 1024
MAX_JOBS = int(os.environ.get("PACK3D_MAX_JOBS", "2"))
_slots = threading.Semaphore(MAX_JOBS)

if __name__ == "__main__":
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"🚀 pack3d studio AI in ascolto su {host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
