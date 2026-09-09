"""
pack3d — da artwork PDF (disegno tecnico + grafica) a modello 3D mappato.

    python -m pack3d build ARTWORK.pdf --out DIR [--kind carton]
                            [--reference RENDER.png] [--dpi 300]

Se viene passato un render di riferimento, la camera viene ricavata da quello
e il risultato e' direttamente confrontabile con il mockup esistente.
"""
from __future__ import annotations

import argparse
import json
import os

from . import dieline as dl
from . import folding, exporters, studio, knowledge
from .camera import preset_camera


def build(args):
    os.makedirs(args.out, exist_ok=True)
    base = args.name or os.path.splitext(os.path.basename(args.pdf))[0]

    d = dl.analyze(args.pdf, kind=args.kind)
    if not d.panels:
        raise SystemExit(f"tipologia '{d.kind}' non ancora supportata dal solutore")
    print(f"tipologia   : {d.kind} ({d.layout})")
    print(f"quote L/H/P : {d.dims_mm[0]} x {d.dims_mm[1]} x {d.dims_mm[2]} mm")
    for k, p in sorted(d.panels.items()):
        print(f"  {k:7s} {p.w_mm:7.1f} x {p.h_mm:6.1f} mm")

    for m in dl.check(d):
        print("  avviso   :", m)
    tex = folding.rasterize_panels(args.pdf, d.panels, dpi=args.dpi)
    faces = folding.build_faces(d.dims_mm, tex, layout=d.layout)

    err = None
    if args.reference:
        from .reference import learn_camera
        cam, err, assign, refsize = learn_camera(args.reference, d.dims_mm)
        print(f"camera dal riferimento: errore max {err:.2f} px su {refsize}")
        cam.f *= args.size / refsize
        cam.cx = cam.cy = args.size / 2
    else:
        from .camera import frame
        cam = frame(preset_camera(args.preset, size=args.size), d.dims_mm, args.size)

    img, alpha = studio.studio_render(faces, cam, size=args.size,
                                      shadow=True, dims_mm=d.dims_mm)
    png = os.path.join(args.out, f"{base}_3d.png")
    img.convert("RGBA").putalpha(alpha) or None
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)
    rgba.save(png)
    print("render      :", png)

    objdir = os.path.join(args.out, "obj")
    obj = exporters.write_obj(faces, objdir, basename=base)
    glb = exporters.write_glb(faces, os.path.join(args.out, f"{base}.glb"))
    print("obj         :", obj)
    print("glb         :", glb)

    report = {
        "source": os.path.basename(args.pdf),
        "kind": d.kind,
        "dims_mm": {"L": d.dims_mm[0], "H": d.dims_mm[1], "P": d.dims_mm[2]},
        "sheet_mm": [round((d.bbox[2] - d.bbox[0]) * dl.PT2MM, 1),
                     round((d.bbox[3] - d.bbox[1]) * dl.PT2MM, 1)],
        "panels": {k: {"w_mm": round(p.w_mm, 1), "h_mm": round(p.h_mm, 1),
                       "bbox_pt": [round(v, 2) for v in p.bbox()]}
                   for k, p in sorted(d.panels.items())},
        "layout": d.layout,
        "warnings": dl.check(d),
        "camera_fit_error_px": err,
    }
    with open(os.path.join(args.out, f"{base}_report.json"), "w") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    if args.learn:
        knowledge.remember(d, base, report)
        print("appreso     : struttura salvata nella knowledge base")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pack3d")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("pdf")
    b.add_argument("--out", default="out")
    b.add_argument("--name", default=None)
    b.add_argument("--kind", default=None,
                   choices=[None, "carton", "flowpack", "tray"])
    b.add_argument("--reference", default=None)
    b.add_argument("--preset", default="hero-left")
    b.add_argument("--dpi", type=int, default=300)
    b.add_argument("--size", type=int, default=2000)
    b.add_argument("--learn", action="store_true")
    b.set_defaults(func=build)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
