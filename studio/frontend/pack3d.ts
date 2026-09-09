// Client del backend pack3d. Il PDF viaggia come corpo binario grezzo:
// con FormData la fetch dentro un iframe fallisce perche' non e' clonabile.
const API = (import.meta.env.VITE_PACK3D_API as string || "").replace(/\/$/, "");

export type Kind = "carton" | "flowpack" | "cup";
export type Soft = "rigido" | "medio" | "morbido";

export interface Analisi {
  famiglia?: string;
  quote?: Record<string, number>;
  pulizia?: { livello: number; metodo: string };
  avvisi?: string[];
  provenienza?: Record<string, string>;
}

async function post(path: string, pdf: ArrayBuffer, params: object) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    body: pdf,
    headers: {
      "Content-Type": "application/pdf",
      "X-Pack3d": JSON.stringify(params),
    },
  });
  if (!r.ok) throw new Error((await r.text()).slice(0, 300));
  return r;
}

/** Analisi guidata da Claude: restituisce quote, avvisi e provenienza. */
export async function analyseAI(pdf: ArrayBuffer, kind: Kind, answers: object = {}) {
  return (await post("/api/analyze-ai", pdf, { kind, ...answers })).json() as Promise<Analisi>;
}

/** Costruzione della mesh: restituisce un object URL del GLB. */
export async function build(
  pdf: ArrayBuffer,
  opts: { kind: Kind; teeth?: number; soft?: Soft; params?: object }
) {
  const blob = await (await post("/api/build", pdf, opts)).blob();
  return URL.createObjectURL(blob);
}

export async function ping() {
  try { return (await fetch(`${API}/api/ping`, { cache: "no-store" })).ok; }
  catch { return false; }
}
