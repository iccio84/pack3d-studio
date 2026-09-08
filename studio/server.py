#!/usr/bin/env python3
"""
Backend per pack3d studio.
Genera e restituisce direttamente il file GLB binario atteso dal viewer HTML.
"""
from __future__ import annotations

import io
import json
import os
import sys
import traceback
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))

# Aggiunge la root e la sottocartella pack3d al PYTHONPATH
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pack3d"))

# Importazione dei moduli matematici della pipeline 3D
try:
    import pack3d.dieline as dieline
    import pack3d.flowpack as flowpack
    import pack3d.exporters as exporters
except ImportError:
    try:
        import dieline
        import flowpack
        import exporters
    except ImportError as e:
        print(f"⚠️ Nota importazione moduli 3D: {e}")
        dieline = flowpack = exporters = None


def load_project_rules():
    """Carica la documentazione delle regole da REGOLE.md."""
    regole_path = os.path.join(HERE, "REGOLE.md")
    if os.path.exists(regole_path):
        with open(regole_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def process_pdf_to_glb(pdf_bytes: bytes, kind: str = "cartotecnico", teeth: int = 0, gonfiore: str = "medio") -> bytes:
    """
    Invocazione della pipeline deterministica per produrre il file .glb binario.
    """
    kind = kind.lower().strip()
    
    # Regola da REGOLE.md: "Altro" non e' ancora supportato
    if kind == "altro":
        raise ValueError("La tipologia 'Altro' non e' ancora supportata.")

    # 1. Gestione FLOWPACK
    if kind == "flowpack":
        if flowpack and hasattr(flowpack, "build_mesh"):
            mesh = flowpack.build_mesh(pdf_bytes, teeth=teeth, swelling=gonfiore)
            if exporters and hasattr(exporters, "export_glb"):
                return exporters.export_glb(mesh)
            return mesh # Se build_mesh restituisce gia' il GLB
        elif flowpack and hasattr(flowpack, "process"):
            return flowpack.process(pdf_bytes, teeth=teeth, swelling=gonfiore)

    # 2. Gestione ASTUCCI / CARTOTECNICO (Default)
    if dieline:
        if hasattr(dieline, "build_box_glb"):
            return dieline.build_box_glb(pdf_bytes)
        elif hasattr(dieline, "build_box") and exporters:
            box = dieline.build_box(pdf_bytes)
            return exporters.export_glb(box)
        elif hasattr(dieline, "process"):
            return dieline.process(pdf_bytes)

    # 3. Fallback ricerca dinamica su exporters
    if exporters:
        for fn in ["build_glb", "process_pdf", "pdf_to_glb"]:
            if hasattr(exporters, fn):
                return getattr(exporters, fn)(pdf_bytes)

    raise NotImplementedError("Impossibile trovare la funzione di esportazione GLB in dieline.py/flowpack.py/exporters.py")


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
            return self._send(200, json.dumps({"ok": True}))
        
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
                    kind = self.headers.get("X-Kind", "cartotecnico")
                    teeth = int(self.headers.get("X-Teeth", "0"))
                    gonfiore = self.headers.get("X-Gonfiore", "medio")

                    # Generazione del file GLB binario
                    glb_bytes = process_pdf_to_glb(pdf_data, kind=kind, teeth=teeth, gonfiore=gonfiore)

                    # Restituzione del file GLB binario con l'MIME type corretto
                    return self._send(200, glb_bytes, ctype="model/gltf-binary", filename="model3d.glb")

                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                except NotImplementedError as nie:
                    return self._send(500, json.dumps({"error": str(nie)}))
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
    print(f"🚀 pack3d studio avviato su {host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
