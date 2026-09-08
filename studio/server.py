#!/usr/bin/env python3
"""
Backend di pack3d studio collegato all'API di Anthropic Claude (Vision via Image Conversion).
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

# Importazione di PyMuPDF per convertire PDF in Immagini
try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("Manca la libreria 'PyMuPDF'. Installa con: pip install PyMuPDF")

HERE = os.path.dirname(os.path.abspath(__file__))

# Inizializzazione controllata del client Anthropic
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ATTENZIONE: La variabile d'ambiente ANTHROPIC_API_KEY non e' stata trovata!")

anthropic_client = anthropic.Anthropic(api_key=api_key) if api_key else None

def load_project_rules():
    regole_path = os.path.join(HERE, "REGOLE.md")
    if os.path.exists(regole_path):
        with open(regole_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Sei un esperto di modellazione 3D da PDF di packaging."

def convert_pdf_to_png_base64(pdf_bytes: bytes) -> str:
    """Apre il PDF dal buffer di memoria e converte la prima pagina in PNG Base64."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        raise ValueError("Il PDF caricato non contiene pagine.")
    
    page = doc[0]
    # Rendering ad alta risoluzione (2x per mantenere nitide le quote e le linee di fustella)
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")


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
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self._send(200, json.dumps({"ok": True}))
        
        path = os.path.join(HERE, "pack3d_studio.html")
        if os.path.exists(path):
            with open(path, "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        return self._send(404, "File non trovato")

    def do_POST(self):
        try:
            if not anthropic_client:
                return self._send(500, json.dumps({
                    "error": "ANTHROPIC_API_KEY non configurata nelle variabili d'ambiente su Render."
                }))

            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, "Nessun file ricevuto")
            if n > MAX_UPLOAD:
                return self._send(413, "PDF troppo grande (limite %d MB)" % (MAX_UPLOAD // (1024 * 1024)))
            
            pdf_data = self.rfile.read(n)
            if not pdf_data.startswith(b"%PDF"):
                return self._send(400, "Il file caricato non e' un PDF valido")
            
            # Converte il PDF in un'immagine PNG codificata in Base64
            png_b64 = convert_pdf_to_png_base64(pdf_data)

            if self.path.startswith("/api/build") or self.path.startswith("/api/analyze"):
                if not _slots.acquire(blocking=False):
                    return self._send(503, "Server occupato: riprova fra qualche secondo")
                
                try:
                    system_prompt = load_project_rules()

                    # Chiamata API Vision standard accettata da TUTTI i modelli Claude 3
                    response = anthropic_client.messages.create(
                        model="claude-3-5-sonnet-20240620",
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
                                        "text": "Analizza l'immagine di questa fustella/packaging e genera la struttura del modello 3D seguendo rigorosamente le regole fornite."
                                    }
                                ]
                            }
                        ]
                    )

                    result_3d = response.content[0].text
                    return self._send(200, json.dumps({"success": True, "model3d": result_3d}))

                finally:
                    _slots.release()

            return self._send(404, "Endpoint sconosciuto")

        except Exception as e:
            traceback.print_exc()
            return self._send(500, json.dumps({"error": "%s: %s" % (type(e).__name__, e)}))


MAX_UPLOAD = 60 * 1024 * 1024
MAX_JOBS = int(os.environ.get("PACK3D_MAX_JOBS", "2"))
_slots = threading.Semaphore(MAX_JOBS)

if __name__ == "__main__":
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("pack3d studio AI in ascolto su %s:%d" % (host, port))
    ThreadingHTTPServer((host, port), Handler).serve_forever()
