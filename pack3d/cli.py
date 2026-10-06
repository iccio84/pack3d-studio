"""
pack3d — da artwork PDF (disegno tecnico + grafica) a modello 3D mappato.

    python -m pack3d build ARTWORK.pdf --out DIR [--kind carton]
                            [--reference RENDER.png] [--quality hd|web]

Se viene passato un render di riferimento, la camera viene ricavata da quello
e il risultato e' direttamente confrontabile con il mockup esistente.

Le regole sono quelle del server, non una versione ridotta: grafica dal suo
livello e in HD, misure dal disegno tecnico, e le stesse verifiche - le facce
sui pannelli del DT, il fronte sul fronte, le quote del file.
"""
from __future__ import annotations

import argparse
import json
import os

from . import dieline as dl
from . import artwork, folding, exporters, studio, knowledge, quote, verifica
from .camera import preset_camera


def build(args):
    os.makedirs(args.out, exist_ok=True)
    base = args.name or os.path.splitext(os.path.basename(args.pdf))[0]

    giro = None
    if args.kind in (None, "carton"):
        # nel verso della grafica, come il server: vedi
        # `artwork.astuccio_sulla_grafica`. Da qui in avanti `pdf` e' la
        # copia girata, se il foglio andava girato.
        pdf, d, _gradi, giro = artwork.astuccio_sulla_grafica(args.pdf)
    else:
        pdf = args.pdf
        d = dl.analyze(pdf, kind=args.kind)
    if not d.panels:
        raise SystemExit(f"tipologia '{d.kind}' non ancora supportata dal solutore")
    print(f"tipologia   : {d.kind} ({d.layout})")
    if giro:
        print("  avviso   :", giro)
    print(f"quote L/H/P : {d.dims_mm[0]} x {d.dims_mm[1]} x {d.dims_mm[2]} mm")
    for k, p in sorted(d.panels.items()):
        print(f"  {k:7s} {p.w_mm:7.1f} x {p.h_mm:6.1f} mm")

    for m in dl.check(d):
        print("  avviso   :", m)
    dpi, tmax = artwork.risoluzione(args.quality)
    if args.dpi:
        dpi = args.dpi
    esito = {}
    tex, avvisi_tex = artwork.texture_astuccio(pdf, d.panels, dpi,
                                              dieline=d, esito=esito)
    for m in avvisi_tex:
        print("  avviso   :", m)
    faces = folding.build_faces(d.dims_mm, tex, layout=d.layout,
                                panels=d.panels, chiuso=d.chiuso,
                                fianchi_sul_fronte=d.fianchi_su == "front")
    # il fronte curvo, come il server: vedi `dieline._fronte_curvo`
    if d.curva_mm:
        folding.curva_fronte(faces, d.dims_mm, d.curva_mm,
                             {k: d.panels[k].h_mm for k in ("top", "bottom")
                              if k in d.panels})
        print("  avviso   : fronte curvo, freccia %.1f mm" % d.curva_mm)
    # il marchio orizzontale e dritto, come il server: vedi `folding.gira_facce`
    if esito.get("marchio"):
        folding.gira_facce(faces, esito["marchio"])
        print("  avviso   : modello girato di %d gradi attorno al fronte "
              "perche' il marchio si legga orizzontale e dritto"
              % esito["marchio"])
    _ok, verifiche = verifica.facce_astuccio(faces, d.panels, d.curva_mm)
    # l'apertura a strappo aperta (`--apertura`) o incisa nelle facce, come
    # il server: vedi `pack3d.apertura` e `pack3d.incisioni`. Solo nel GLB:
    # il render e l'OBJ restano dell'astuccio chiuso e liscio.
    from . import apertura, incisioni
    nomi = [f["name"] for f in faces if f["name"] in d.panels]
    aperta = None
    if args.apertura and not d.curva_mm:
        liscio = [dict(f) for f in faces]
        aperta = apertura.apri(pdf, d.panels, nomi, faces, args.apertura,
                               esito.get("girate"), folding.SPESSORE_CRT)
        if aperta:
            print("  avviso   : apertura a strappo aperta nel GLB di %g gradi, "
                  "cerniera sul %s, appoggiato sul %s"
                  % (aperta["gradi"], aperta["cerniera"], aperta["appoggia"]))
        else:
            print("  avviso   : nessuna apertura a strappo con la sua "
                  "cerniera: l'astuccio esce chiuso")
    tagli = {} if aperta or d.curva_mm else incisioni.tagli(pdf, d.panels, nomi)
    if tagli:
        n = incisioni.incidi(faces, tagli, d.panels, esito.get("girate"),
                             folding.SPESSORE_CRT)
        print("  avviso   : apertura a strappo incisa nel GLB: %d tagli su %s"
              % (n, ", ".join(sorted(tagli))))
    riscontro = quote.riscontro_astuccio(pdf, d)
    verifiche = verifiche + ([riscontro] if riscontro else [])
    for m in verifiche:
        print("  verifica :", m)

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

    # il render e l'OBJ sono dei quad: dell'astuccio chiuso, nel suo verso
    piane = liscio if aperta else faces
    img, alpha = studio.studio_render(piane, cam, size=args.size,
                                      shadow=True, dims_mm=d.dims_mm)
    png = os.path.join(args.out, f"{base}_3d.png")
    img.convert("RGBA").putalpha(alpha) or None
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)
    rgba.save(png)
    print("render      :", png)

    objdir = os.path.join(args.out, "obj")
    obj = exporters.write_obj(piane, objdir, basename=base)
    glb = exporters.write_glb(faces, os.path.join(args.out, f"{base}.glb"),
                              tex_max=tmax)
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
        "warnings": ([giro] if giro else []) + dl.check(d) + avvisi_tex + verifiche,
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
    b.add_argument("--quality", default="hd", choices=["hd", "web"])
    b.add_argument("--dpi", type=int, default=None,
                   help="forza i dpi della texture; di serie quelli della qualita'")
    b.add_argument("--size", type=int, default=2000)
    b.add_argument("--learn", action="store_true")
    b.add_argument("--apertura", type=float, default=None,
                   help="gradi di cui aprire l'apertura a strappo di un "
                        "astuccio (solo nel GLB)")
    b.set_defaults(func=build)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
