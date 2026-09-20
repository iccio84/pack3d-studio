import { useCallback, useEffect, useRef, useState } from "react";
import { ExternalLink, FileText, Upload } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

const STUDIO_URL =
  (import.meta.env['VITE_PACK3D_API'] as string | undefined) ?? "https://pack3d-studio.onrender.com";

/** Origine esatta dello studio: le postMessage si mandano e si accettano solo da qui. */
const STUDIO_ORIGIN = new URL(STUDIO_URL).origin;

const MAX_GLB_BYTES = 50 * 1024 * 1024;

type MessaggioStudio = {
  tipo?: string;
  nome?: string;
  glb?: Blob;
  avvisi?: string[];
};

/**
 * Apre pack3d studio dentro l'app, in un pannello grande come la viewport
 * e con lo stesso stile del viewer.
 *
 * Quando lo studio finisce di costruire il modello lo passa di qua da solo:
 * il pannello si chiude e il pack e' gia' in viewport, nella sezione PDFto3D.
 * Il pulsante di importazione a mano resta per i GLB che arrivano da altrove.
 */
export function Pack3dStudioDialog({
  onBuilt,
}: {
  onBuilt: (blob: Blob, name: string) => void | Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const frameRef = useRef<HTMLIFrameElement>(null);
  /** una presentazione basta: rispondere a ogni "pronto" fa rimpallare i due lati */
  const presentato = useRef(false);

  /** Un GLB entra in viewport solo se e' davvero un GLB e sta nel limite. */
  const accetta = useCallback(
    async (buf: ArrayBuffer, nome: string) => {
      if (buf.byteLength === 0 || buf.byteLength > MAX_GLB_BYTES) {
        toast.error("File non valido: massimo 50 MB");
        return false;
      }
      if (new TextDecoder().decode(new Uint8Array(buf, 0, 4)) !== "glTF") {
        toast.error("Il file non è un modello 3D valido");
        return false;
      }
      setOpen(false);
      await onBuilt(new Blob([buf], { type: "model/gltf-binary" }), nome);
      return true;
    },
    [onBuilt],
  );

  /**
   * Si presenta allo studio. Da qui in poi lo studio sa a quale finestra e a
   * quale origine mandare il modello, e non deve mai spedire un file a "*".
   */
  const presentati = useCallback(() => {
    if (presentato.current) return;
    presentato.current = true;
    frameRef.current?.contentWindow?.postMessage({ tipo: "pack3d:ospite" }, STUDIO_ORIGIN);
  }, []);

  useEffect(() => {
    if (!open) {
      presentato.current = false; // l'iframe riparte da zero alla prossima apertura
      return;
    }

    const ascolta = async (e: MessageEvent) => {
      // due filtri, non uno: l'origine giusta E il nostro iframe, non un'altra
      // finestra che si e' messa in mezzo
      if (e.origin !== STUDIO_ORIGIN) return;
      if (e.source !== frameRef.current?.contentWindow) return;

      const m = e.data as MessaggioStudio | null;
      if (m?.tipo === "pack3d:pronto") {
        presentati();
        return;
      }
      if (m?.tipo !== "pack3d:modello" || !(m.glb instanceof Blob)) return;

      // gli avvisi della costruzione (grafica ruotata, analisi in ripiego...)
      // sparirebbero con il pannello: qui restano sotto gli occhi
      for (const a of m.avvisi ?? []) toast.warning(a);

      const nome = (m.nome ?? "Pack").replace(/\.glb$/i, "").trim() || "Pack";
      await accetta(await m.glb.arrayBuffer(), nome);
    };

    window.addEventListener("message", ascolta);
    presentati(); // se lo studio e' gia' in piedi, questa basta
    return () => window.removeEventListener("message", ascolta);
  }, [open, presentati, accetta]);

  const importGlb = async (file: File) => {
    if (!/\.glb$/i.test(file.name)) {
      toast.error("Seleziona un file .glb");
      return;
    }
    await accetta(await file.arrayBuffer(), file.name.replace(/\.glb$/i, ""));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/60 bg-primary/10 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary transition-colors hover:bg-primary/20"
        aria-label="Costruisci modello da PDF"
      >
        <FileText className="h-4 w-4 shrink-0" strokeWidth={1.6} />
        <span className="min-w-0 break-words">Costruisci modello da PDF</span>
      </button>

      <DialogContent
        className="glass-panel flex h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] max-w-[1400px] flex-col gap-0 overflow-hidden rounded-3xl border border-border p-0 sm:max-w-[1400px] lg:h-[min(88dvh,900px)]"
      >
        <div className="grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2 border-b border-border px-3 py-2.5 sm:px-4">
          <DialogTitle className="min-w-0 truncate text-sm font-bold uppercase tracking-[0.2em] text-primary">
            Costruisci modello da PDF
          </DialogTitle>
          <div className="flex shrink-0 items-center gap-1.5 pr-6">
            <input
              ref={inputRef}
              type="file"
              accept=".glb,model/gltf-binary"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (inputRef.current) inputRef.current.value = "";
                if (f) void importGlb(f);
              }}
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex items-center gap-2 rounded-lg border border-primary/60 bg-primary/10 px-2.5 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-primary transition-colors hover:bg-primary/20"
            >
              <Upload className="h-4 w-4" strokeWidth={1.6} />
              <span className="hidden sm:inline">Importa GLB in viewport</span>
            </button>
            <a
              href={STUDIO_URL}
              target="_blank"
              rel="noreferrer"
              aria-label="Apri in una nuova scheda"
              className="rounded-lg border border-border p-2 text-muted-foreground transition-colors hover:text-primary"
            >
              <ExternalLink className="h-4 w-4" strokeWidth={1.6} />
            </a>
          </div>
        </div>

        <iframe
          ref={frameRef}
          src={STUDIO_URL}
          title="pack3d studio"
          onLoad={presentati}
          className="min-h-0 w-full flex-1 border-0 bg-background"
          allow="clipboard-read; clipboard-write; fullscreen"
        />
      </DialogContent>
    </Dialog>
  );
}
