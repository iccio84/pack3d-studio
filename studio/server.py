#!/usr/bin/env python3
"""
Backend di pack3d studio.
Gestisce la conversione di PDF in modelli 3D (GLB) applicando le regole di REGOLE.md,
utilizzando pypdfium2 e la pipeline interna di rendering/esportazione.
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

# Importazione di pypdfium2 per il rendering e la manipolazione dei PDF
try:
    import pypdfium2 as pdfium
except ImportError:
    sys.exit("Manca la libreria 'pypdfium2'. Installa con: pip install pypdfium2")

# SDK Anthropic (opzionale se usato per estrazione dati)
try:
    import anthropic
except ImportError:
    anthropic = None

HERE = os.path.dirname(os.path.abspath(__file__))

# Configurazione API Key Anthropic
api_key = os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=api_key) if (api_key and anthropic) else None


def load_project_rules():
    """Carica la documentazione delle regole da REGOLE.md."""
    regole_path = os.path.join(HERE, "REGOLE.md")
    if os.path.exists(regole_path):
        with open(regole_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def process_pdf_to_glb(pdf_bytes: bytes, kind: str = "cartotecnico", teeth: int = 0, gonfiore: str = "medio") -> bytes:
    """
    Simulazione/Interfaccia della pipeline interna di generazione GLB.
    Qui vanno inglobate le chiamate ai moduli di progetto (dieline.py, flowpack.py, exporters.py).
    Se la tipologia è 'altro', solleva un ValueError (400) come specificato in REGOLE.md.
    """
    kind = kind.lower().strip()
    if kind == "altro":
        raise ValueError("'Altro' non e' ancora supportato.")

    # NOTA PER LO SVILUPPATORE:
    # Collega qui la chiamata ai tuoi moduli interni:
    # es. if kind == "flowpack": return flowpack.build_mesh(pdf_bytes, teeth=teeth, swelling=gonfiore)
    # es. else: return dieline.build_box_glb(pdf_bytes)
    
    # Se la pipeline interna restituisce un buffer GLB, ritornalo direttamente.
    # In assenza dei moduli locali integrati nel file singolo, solleviamo l'istruzione di integrazione:
    raise NotImplementedError("Agganciare la chiamata a dieline.py / flowpack.py per produrre il file .glb binario.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("  %s\n" % (fmt % a))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Pack3d, X-Kind, X-Teeth, X-Gonfiore")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code, body, ctype="application/json", filename=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
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
            return self._send(200, json.dumps({"ok": True, "api_key_configured": bool(api_key)}))
        
        path = os.path.join(HERE, "pack3d_studio.html")
        if os.path.exists(path):
            with open(path, "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        return self._send(404, "File non trovato")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, json.dumps({"error": "Nessun file ricevuto"}))
            if n > MAX_UPLOAD:
                return self._send(413, json.dumps({"error": f"PDF troppo grande (limite {MAX_UPLOAD // (1024 * 1024)} MB)"}))
            
            pdf_data = self.rfile.read(n)
            if not pdf_data.startswith(b"%PDF"):
                return self._send(400, json.dumps({"error": "Il file caricato non e' un PDF valido"}))

            if self.path.startswith("/api/build") or self.path.startswith("/api/analyze"):
                if not _slots.acquire(blocking=False):
                    return self._send(503, json.dumps({"error": "Server occupato: riprova fra qualche secondo"}))
                
                try:
                    # Legge le opzioni passate negli header dal frontend
                    kind = self.headers.get("X-Kind", "cartotecnico")
                    teeth = int(self.headers.get("X-Teeth", "0"))
                    gonfiore = self.headers.get("X-Gonfiore", "medio")

                    # Esecuzione delle regole definite in REGOLE.md
                    if kind.lower() == "altro":
                        return self._send(400, json.dumps({"error": "La tipologia 'Altro' non e' ancora supportata."}))

                    # Generazione del binario GLB tramite la pipeline Python
                    glb_bytes = process_pdf_to_glb(pdf_data, kind=kind, teeth=teeth, gonfiore=gonfiore)

                    # Restituisce direttamente il file GLB con il Content-Type corretto
                    return self._send(200, glb_bytes, ctype="model/gltf-binary", filename="model3d.glb")

                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                except NotImplementedError:
                    # Fallback temporaneo: Se la pipeline 3D locale non è ancora collegata,
                    # notifica la configurazione invece di inviare testo incompatibile al viewer
                    return self._send(500, json.dumps({
                        "error": "Pipeline 3D locale non agganciata. Il viewer si aspetta un file .glb binario, non una risposta testuale dall'LLM."
                    }))
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
    print(f"🚀 pack3d studio attivo su {host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
