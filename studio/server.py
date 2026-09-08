#!/usr/bin/env python3
"""
Backend per pack3d studio.
Genera e restituisce il file GLB binario sfruttando le funzioni di exporters.py.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import traceback
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))

# Configurazione importazioni per pack3d
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pack3d"))

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
        print(f"⚠️ Errore importazione moduli pack3d: {e}")
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
    Invocazione della pipeline deterministica per la generazione e lettura del file GLB binario.
    """
    kind = kind.lower().strip()
    
    # Regola REGOLE.md
    if kind == "altro":
        raise ValueError("La tipologia 'Altro' non e' ancora supportata.")

    if not exporters:
        raise NotImplementedError("Modulo exporters.py non caricato correttamente.")

    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
        tmp_glb_path = tmp.name

    try:
        # 1. CASO FLOWPACK (mesh triangolare)
        if kind == "flowpack":
            if flowpack:
                # Cerca il costruttore di mesh per flowpack
                if hasattr(flowpack, "build_mesh"):
                    V, UV, tris, tex = flowpack.build_mesh(pdf_bytes, teeth=teeth, swelling=gonfiore)
                    exporters.write_glb_mesh(V, UV, tris, tex, tmp_glb_path)
                elif hasattr(flowpack, "process_pdf"):
                    V, UV, tris, tex = flowpack.process_pdf(pdf_bytes, teeth=teeth, swelling=gonfiore)
                    exporters.write_glb_mesh(V, UV, tris, tex, tmp_glb_path)
                else:
                    raise NotImplementedError("Funzione di generazione mesh per flowpack non trovata in flowpack.py")
            else:
                raise NotImplementedError("Modulo flowpack.py non disponibile.")

        # 2. CASO CARTOTECNICO / ASTUCCI (facce)
        else:
            if dieline:
                if hasattr(dieline, "build_box"):
                    faces = dieline.build_box(pdf_bytes)
                    exporters.write_glb(faces, tmp_glb_path)
                elif hasattr(dieline, "process_pdf"):
                    faces = dieline.process_pdf(pdf_bytes)
                    exporters.write_glb(faces, tmp_glb_path)
                elif hasattr(dieline, "analyze_pdf"):
                    faces = dieline.analyze_pdf(pdf_bytes)
                    exporters.write_glb(faces, tmp_glb_path)
                else:
                    raise NotImplementedError("Funzione di analisi fustella non trovata in dieline.py")
            else:
                raise NotImplementedError("Modulo dieline.py non disponibile.")

        # Legge il file GLB appena generato sul percorso temporaneo
        with open(tmp_glb_path, "rb") as fh:
            glb_data = fh.read()

        return glb_data

    finally:
        # Pulisce il file temporaneo
        if os.path.exists(tmp_glb_path):
            try:
                os.remove(tmp_glb_path)
            except OSError:
                pass


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

                    # Generazione del file GLB binario reale tramite exporters.write_glb
                    glb_bytes = process_pdf_to_glb(pdf_data, kind=kind, teeth=teeth, gonfiore=gonfiore)

                    # Restituisce direttamente la sequenza di byte del file .glb
                    return self._send(200, glb_bytes, ctype="model/gltf-binary", filename="pack3d_model.glb")

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
    print(f"🚀 pack3d studio server attivo su {host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
