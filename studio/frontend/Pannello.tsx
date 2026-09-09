import { useState } from "react";
import { analyseAI, build, Kind, Soft, Analisi } from "./pack3d";

export function Pannello({ onModel }: { onModel: (url: string) => void }) {
  const [pdf, setPdf] = useState<ArrayBuffer | null>(null);
  const [kind, setKind] = useState<Kind | null>(null);
  const [teeth, setTeeth] = useState("");
  const [soft, setSoft] = useState<Soft>("medio");
  const [stato, setStato] = useState("");
  const [info, setInfo] = useState<Analisi | null>(null);

  async function scegli(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setPdf(await f.arrayBuffer());
    setKind(null); setInfo(null);
    setStato("Indica il tipo di pack");        // prima domanda su ogni PDF
  }

  async function vai(k: Kind) {
    setKind(k);
    if (k === "flowpack") { setStato("Digita i dentini e scegli il gonfiore"); return; }
    esegui({ kind: k });
  }

  async function esegui(opts: { kind: Kind; teeth?: number; soft?: Soft }) {
    if (!pdf) return;
    try {
      setStato("Analisi in corso, 20-60 secondi…");
      const a = await analyseAI(pdf, opts.kind, opts);
      setInfo(a);
      setStato("Costruzione del modello…");
      onModel(await build(pdf, { ...opts, params: a as object }));
      setStato("Modello pronto");
    } catch (err: any) {
      setStato(String(err.message ?? err).slice(0, 200));
    }
  }

  return (
    <div className="space-y-3">
      <input type="file" accept="application/pdf,.pdf" onChange={scegli} />

      {pdf && !kind && (
        <div className="flex gap-2">
          <button onClick={() => vai("carton")}>Cartotecnico</button>
          <button onClick={() => vai("flowpack")}>Flowpack</button>
          <button onClick={() => vai("cup")}>Coppa conica</button>
        </div>
      )}

      {kind === "flowpack" && (
        <div className="flex gap-2 items-end">
          <input type="number" min={0} value={teeth}
                 placeholder="dentini per lato"
                 onChange={(e) => setTeeth(e.target.value)} />
          <select value={soft} onChange={(e) => setSoft(e.target.value as Soft)}>
            <option value="rigido">Rigido</option>
            <option value="medio">Medio</option>
            <option value="morbido">Morbido</option>
          </select>
          <button disabled={teeth === ""}
                  onClick={() => esegui({ kind: "flowpack", teeth: Number(teeth), soft })}>
            Costruisci
          </button>
        </div>
      )}

      <p className="text-sm opacity-70">{stato}</p>

      {info && (
        <div className="text-sm space-y-1">
          {info.quote && (
            <ul>{Object.entries(info.quote).map(([k, v]) =>
              <li key={k}>{k}: <b>{v}</b> mm</li>)}</ul>
          )}
          {info.pulizia && <p>Pulizia: livello {info.pulizia.livello} — {info.pulizia.metodo}</p>}
          {info.avvisi?.map((a, i) => <p key={i} className="text-amber-700">{a}</p>)}
        </div>
      )}
    </div>
  );
}
