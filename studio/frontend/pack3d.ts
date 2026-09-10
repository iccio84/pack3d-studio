// Client del backend pack3d. Il PDF viaggia come corpo binario grezzo:
// con FormData la fetch dentro un iframe fallisce perche' non e' clonabile.
const API = (import.meta.env.VITE_PACK3D_API as string || "").replace(/\/$/, "");

export type Kind = "carton" | "flowpack" | "cup";
export type Soft = "rigido" | "medio" | "morbido";

/** Geometria del flowpack in mm. Il backend la rivalida sulle stesse coerenze
 *  fisiche prima di costruire: qui e' un dato di passaggio, non una garanzia. */
export interface FlowpackGeom {
  W: number; T: number; L: number;
  end_fin: number; side_fin: number;
  back_a: number; back_b: number;
  web_mm: number; step_mm: number;
  sheet_x0_mm: number; sheet_y0_mm: number;
}

export interface Analisi {
  famiglia?: string;
  quote?: Record<string, number>;
  pulizia?: { livello: number; metodo: string };
  avvisi?: string[];
  provenienza?: Record<string, string>;
  flowpack?: FlowpackGeom;
  /** gli strumenti di misura che il modello ha chiamato, in ordine */
  _chiamate?: string[];
}

/** Esito della costruzione: il modello piu' il resoconto del backend. */
export interface Modello {
  url: string;
  /** quote, avvisi di coerenza e — quando c'e' — l'avvertenza che la
   *  geometria e' stimata dall'AI e non misurata */
  meta: string[];
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

/** Costruzione della mesh: object URL del GLB piu' il resoconto del backend.
 *
 *  `params` e' l'esito di `analyseAI`: passandolo, il backend riusa la
 *  geometria gia' misurata invece di rifare l'analisi da zero — che sui
 *  flowpack non riconosciuti significherebbe una seconda chiamata a pagamento
 *  di 20-60 secondi. */
export async function build(
  pdf: ArrayBuffer,
  opts: { kind: Kind; teeth?: number; soft?: Soft; params?: Analisi }
): Promise<Modello> {
  const r = await post("/api/build", pdf, opts);
  // il corpo e' il GLB, quindi il resoconto viaggia in un header
  let meta: string[] = [];
  try {
    const raw = JSON.parse(r.headers.get("X-Pack3d-Meta") || "null");
    if (Array.isArray(raw)) meta = raw;
  } catch {
    /* header assente o illeggibile: il modello resta valido */
  }
  return { url: URL.createObjectURL(await r.blob()), meta };
}

/** L'avvertenza sulla geometria stimata, se il backend l'ha segnalata. */
export function avvisoAI(meta: string[]): string | undefined {
  return meta.find((t) => /^geometria .*\bAI\b/.test(t));
}

export async function ping() {
  try { return (await fetch(`${API}/api/ping`, { cache: "no-store" })).ok; }
  catch { return false; }
}
