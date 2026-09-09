#!/usr/bin/env python3
"""
Backend locale di pack3d studio.

    python server.py            # poi apri http://localhost:8000

Solo libreria standard: serve l'interfaccia e due endpoint che girano la
pipeline `pack3d`. Il PDF arriva come corpo binario grezzo, non come
multipart: dentro un iframe la fetch viene inoltrata con postMessage e una
FormData non e' clonabile, mentre un ArrayBuffer lo e'.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import tempfile
import traceback
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pack3d"))
sys.path.insert(0, os.path.join(HERE, "pack3d"))

try:
    import numpy as np
    from PIL import Image
except ImportError as e:                       # messaggio utile, non uno stack trace
    sys.exit("Manca una libreria (%s).\n"
             "Installa con:  pip install -r requirements.txt" % e.name)

from pack3d import dieline as dl, folding, exporters
from pack3d import flowpack as fpk
from pack3d.dieline import Panel, PT2MM
from pack3d.flowpack import Flowpack, soft_section_fit, fin_on_surface
from pack3d.exporters import _normals

# gonfiore: raccordo, esponente spigolo, grinza, pancia, rastremazione
GONFIORE = {
    "rigido":  dict(soft_r=5.2, soft_n=2.0, wrinkle_mm=0.0,  bulge=0.015, taper=8.0),
    "medio":   dict(soft_r=7.5, soft_n=2.4, wrinkle_mm=0.35, bulge=0.030, taper=16.0),
    "morbido": dict(soft_r=9.5, soft_n=2.6, wrinkle_mm=0.60, bulge=0.045, taper=26.0),
}

# casi gia' calibrati: l'analizzatore automatico non copre ogni impaginato,
# quindi i flowpack risolti a mano restano disponibili tramite la firma della
# pagina (larghezza x altezza in punti, arrotondate).
CASI = {
    (1672, 737): dict(
        name="FULFIL Chocolate Hazelnut Whip",
        sheet=(481.78, 120.34, 481.78 + 142 / PT2MM, 120.34 + 141 / PT2MM),
        girth_span=(120.34 + 15 / PT2MM, 120.34 + 126 / PT2MM),
        W=36.0, T=19.5, L=116.0, end_fin=13.0, side_fin=15.0,
        back_a=18.0, back_b=18.0, web=141.0, step=142.0,
        fin_open=52.6, teeth=20, soft="morbido",
        drop_seps=["Coldseal", "White", "Stand Blau", "All",
                   "Label_ferrero", "Label_linked"],
    ),
}


def _sig(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        p = pdf.pages[0]
        return (int(p.width), int(p.height))


# --------------------------------------------------------------------------- #
# pulizia dell'artwork
# --------------------------------------------------------------------------- #
def strip_separations(src, dst, drop):
    """Toglie le lastre tecniche eliminando le operazioni di disegno.

    Colorarle di bianco non basta: un tratto tecnico sopra la grafica
    lascerebbe una riga bianca. Il filtro scende anche dentro i Form XObject,
    dove spesso stanno cold seal e bianco coprente.
    """
    import pypdf
    from pypdf.generic import ContentStream

    r = pypdf.PdfReader(src)
    w = pypdf.PdfWriter()
    w.append(r)
    drop = {d.lower() for d in drop}

    def names(res):
        out = set()
        cs = res.get("/ColorSpace")
        if not cs:
            return out
        for k, v in cs.get_object().items():
            try:
                o = v.get_object()
                if o[0] == "/Separation":
                    if str(o[1]).lstrip("/").replace("#20", " ").lower() in drop:
                        out.add(str(k))
                elif o[0] == "/DeviceN":
                    nm = [str(x).lstrip("/").replace("#20", " ").lower() for x in o[1]]
                    if nm and all(n in drop for n in nm):
                        out.add(str(k))
            except Exception:
                pass
        return out

    FILL, STROKE = {b"f", b"F", b"f*"}, {b"S", b"s"}
    BOTH = {b"B", b"B*", b"b", b"b*"}

    def filt(obj, res):
        bad = names(res)
        cs = ContentStream(obj, w)
        ncs = scs = None
        out = []
        for ops, op in cs.operations:
            if op == b"cs":
                ncs = str(ops[0])
            elif op == b"CS":
                scs = str(ops[0])
            if op in FILL and ncs in bad:
                out.append(([], b"n")); continue
            if op in STROKE and scs in bad:
                out.append(([], b"n")); continue
            if op in BOTH:
                fd, sd = ncs in bad, scs in bad
                if fd and sd:
                    out.append(([], b"n")); continue
                if fd:
                    out.append((ops, b"S")); continue
                if sd:
                    out.append((ops, b"f")); continue
            if op == b"sh" and ncs in bad:
                continue
            out.append((ops, op))
        cs.operations = out
        return cs

    def walk(res, seen):
        xo = res.get("/XObject")
        if not xo:
            return
        for _, v in xo.get_object().items():
            o = v.get_object()
            if o.get("/Subtype") != "/Form" or id(o) in seen:
                continue
            seen.add(id(o))
            sub = o.get("/Resources")
            if sub is None:
                continue
            o.set_data(filt(o, sub.get_object()).get_data())
            walk(sub.get_object(), seen)

    page = w.pages[0]
    res = page["/Resources"]
    page.replace_contents(filt(page.get_contents(), res))
    walk(res, set())
    with open(dst, "wb") as fh:
        w.write(fh)
    return dst


# --------------------------------------------------------------------------- #
# costruzione
# --------------------------------------------------------------------------- #
def build_carton(pdf, out_glb, quality="web"):
    dpi = 300 if quality == "alta" else 200
    d = dl.analyze(pdf)
    if not d.panels:
        raise ValueError("astuccio riconosciuto ma i pannelli non sono risolvibili")
    tex = folding.rasterize_panels(pdf, d.panels, dpi=dpi)
    faces = folding.build_faces(d.dims_mm, tex, layout=d.layout)
    exporters.write_glb_mesh  # noqa: B018  (import usato sotto per i flowpack)
    exporters.write_glb(faces, out_glb)
    meta = ["astuccio %s" % d.layout,
            "%.1f x %.1f x %.1f mm" % d.dims_mm]
    return meta + [w for w in dl.check(d)]


def _flowpack_from_case(case):
    return Flowpack(W=case["W"], T=case["T"], L=case["L"], end_fin=case["end_fin"],
                    side_fin=case["side_fin"], back_a=case["back_a"],
                    back_b=case["back_b"], web_mm=case["web"], step_mm=case["step"],
                    sheet=case["sheet"], girth_span=case["girth_span"])


def build_flowpack(pdf, out_glb, teeth, soft, case=None, quality="web"):
    par = GONFIORE.get(soft, GONFIORE["medio"])
    nu, nv, dpi, tmax = (320, 420, 300, 2600) if quality == "alta" else (150, 260, 200, 1700)
    if case:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        clean = strip_separations(pdf, tmp.name, case["drop_seps"])
        fp = _flowpack_from_case(case)
        fin_open = case["fin_open"]
    else:
        clean = pdf
        try:
            fp = fpk.analyze_auto(pdf)
        except Exception:
            fp = fpk.analyze(pdf)          # solutore storico come ripiego
        fin_open = 0.948 * fp.girth / 2.0

    _, dsec, SW = soft_section_fit(fp, par["soft_r"], par["soft_n"])
    V, UV, T = fpk.build_mesh(
        fp, nu=nu, nv=nv, soft_r=par["soft_r"], soft_n=par["soft_n"],
        width_end=fin_open / SW, taper=par["taper"], flare_pow=5.0, soft=True,
        serration=teeth > 0, serr_teeth=teeth,
        fin_stations=60 if quality == "alta" else 26,
        bulge=par["bulge"], crimp_period=1.25, crimp_mm=0.32,
        wrinkle_mm=par["wrinkle_mm"])
    UV = fpk.remap_to_sheet(UV, fp)
    grid = V.reshape(-1, nv + 1, 3)
    V2, UV2, T2 = fin_on_surface(grid, fp, dsec[-1], nv, gap=0.55, fade=12.0)
    Vm = np.vstack([V, V2]); UVm = np.vstack([UV, UV2]); Tm = np.vstack([T, T2 + len(V)])

    sh = fp.sheet
    tex = folding.rasterize_panels(
        clean, {"film": Panel(sh[0], sh[1], sh[2], sh[3], "film")},
        dpi=dpi, inset_px=0, clean=(case is None))["film"]
    exporters.write_glb_mesh(Vm, UVm, Tm, tex, out_glb, tex_max=tmax)

    n = _normals(Vm, Tm)
    i = np.argsort(-Vm[:, 2])[:300]
    base = fin_open / max(teeth, 1)
    return ["flowpack %s" % soft,
            "corpo %.1f mm, sezione %.1f x %.1f" % (fp.L, SW, fp.T),
            ("pinne lisce" if teeth == 0 else
             "%d denti equilateri (base %.2f, altezza %.2f mm)"
             % (teeth, base, base * math.sqrt(3) / 2)),
            "normale fronte %s" % np.round(n[i].mean(0), 2).tolist()]


def analyze_pdf(pdf, kind=None):
    """`kind` arriva dall'utente: la tipologia si dichiara, non si indovina.
    Il riconoscimento automatico sbaglia (il solutore astuccio risolve anche
    certi flowpack) e sbagliare qui compromette tutto il resto."""
    case = CASI.get(_sig(pdf))
    if case and kind in (None, "flowpack"):
        return dict(kind="flowpack", title=case["name"],
                    teeth_default=case["teeth"], soft_default=case["soft"],
                    meta=["caso calibrato: " + case["name"],
                          "nastro %.0f x passo %.0f mm" % (case["web"], case["step"])])
    if kind in (None, "carton"):
        try:
            d = dl.analyze(pdf)
            if d.panels:
                return dict(kind="carton", title="Astuccio %s" % d.layout,
                            meta=["astuccio %s" % d.layout,
                                  "%.1f x %.1f x %.1f mm" % d.dims_mm])
        except Exception:
            if kind == "carton":
                raise
    try:
        fp = fpk.analyze_auto(pdf)
    except Exception:
        fp = fpk.analyze(pdf)      # se fallisce anche questo, l'errore va al client
    return dict(kind="flowpack", title="Flowpack",
                teeth_default=20, soft_default="medio",
                meta=["flowpack", "nastro %.0f x passo %.0f mm" % (fp.web_mm, fp.step_mm),
                      "corpo %.1f mm" % fp.L,
                      "sezione %.1f x %.1f mm" % (fp.W, fp.T)])


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("  %s\n" % (fmt % a))

    def _cors(self):
        # l'interfaccia puo' stare su un dominio diverso dal backend
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
            self.send_header("Content-Disposition",
                             'attachment; filename="%s"' % filename)
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self._send(200, json.dumps({"ok": True}))
        path = os.path.join(HERE, "pack3d_studio.html")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), "text/html; charset=utf-8")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return self._send(400, "Nessun file ricevuto")
            if n > MAX_UPLOAD:
                return self._send(413, "PDF troppo grande (limite %d MB)"
                                  % (MAX_UPLOAD // (1024 * 1024)))
            data = self.rfile.read(n)
            if not data.startswith(b"%PDF"):
                return self._send(400, "Il file caricato non e' un PDF")
            opts = json.loads(self.headers.get("X-Pack3d") or "{}")
            with tempfile.TemporaryDirectory() as td:
                pdf = os.path.join(td, "in.pdf")
                with open(pdf, "wb") as fh:
                    fh.write(data)
                kind = opts.get("kind") or None
                if kind == "altro":
                    return self._send(400, "Tipologia non ancora supportata")
                if self.path.startswith("/api/analyze-ai"):
                    import agent
                    par, tr = agent.analyse(pdf, kind, opts)
                    par["_chiamate"] = [t["tool"] for t in tr]
                    return self._send(200, json.dumps(par, ensure_ascii=False))
                if self.path.startswith("/api/analyze"):
                    return self._send(200, json.dumps(analyze_pdf(pdf, kind)))
                if self.path.startswith("/api/build"):
                    if not _slots.acquire(blocking=False):
                        return self._send(503, "Server occupato: riprova fra qualche "
                                               "secondo")
                    out = os.path.join(td, "out.glb")
                    case = CASI.get(_sig(pdf))
                    info = analyze_pdf(pdf, kind)
                    q = "alta" if str(opts.get("quality")) == "alta" else "web"
                    try:
                        if info["kind"] == "carton":
                            build_carton(pdf, out, q)
                        else:
                            build_flowpack(pdf, out, int(opts.get("teeth", 20)),
                                           str(opts.get("soft", "medio")), case, q)
                    except Exception:
                        _slots.release()
                        raise
                    try:
                        q = q
                        with open(out, "rb") as fh:
                            return self._send(200, fh.read(), "model/gltf-binary",
                                              filename="modello.glb")
                    finally:
                        _slots.release()
            return self._send(404, "endpoint sconosciuto")
        except Exception as e:
            traceback.print_exc()
            return self._send(500, "%s: %s" % (type(e).__name__, e))


MAX_UPLOAD = 60 * 1024 * 1024
MAX_JOBS = int(os.environ.get("PACK3D_MAX_JOBS", "2"))
_slots = threading.Semaphore(MAX_JOBS)

if __name__ == "__main__":
    # PORT e HOST arrivano dall'ambiente sui servizi di hosting; in locale
    # bastano gli argomenti. 0.0.0.0 serve per essere raggiungibili da fuori.
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("pack3d studio in ascolto su %s:%d" % (host, port))
    if host in ("0.0.0.0", "::"):
        print("  in locale:  http://localhost:%d" % port)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
