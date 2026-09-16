import { useState } from "react";
import { analyseAI, build, Kind, Analisi } from "./pack3d";

const FASCIA = (v: number) =>
  v <= 3 ? "Rigido" : v <= 6 ? "Medio" : "Morbido";

export function Pannello({ onModel }: { onModel: (url: string) => void }) {
  const [pdf, setPdf] = useState<ArrayBuffer | null>(null);
  const [nome, setNome] = useState("");
  const [kind, setKind] = useState<Kind | null>(null);
  const [teeth, setTeeth] = useState("");
  const [liv, setLiv] = useState(5);          // scala 1-10, non tre gradini
  const [auto, setAuto] = useState(false);    // "Scegli tu"
  const [stato, setStato] = useState("");
  const [info, setInfo] = useState<Analisi | null>(null);

  async function scegli(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setPdf(await f.arrayBuffer());
    setNome(f.name);
    setKind(null); setInfo(null);
    setStato("Indica il tipo di pack");       // prima domanda su ogni PDF
  }

  function vai(k: Kind) {
    setKind(k);
    if (k === "flowpack") { setStato("Digita i dentini e scegli il rigonfiamento"); return; }
    esegui({ kind: k });
  }

  async function esegui(opts: { kind: Kind; teeth?: number; soft?: number | string }) {
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
          <button disabled title="Non ancora supportato">Altro</button>
        </div>
      )}

      {kind === "flowpack" && (
        <div className="space-y-3">
          <div className="flex gap-2 items-end">
            <label className="flex flex-col text-sm">
              Dentini zigrinatura per lato
              <input type="number" min={0} value={teeth}
                     placeholder="digita il numero"
                     onChange={(e) => setTeeth(e.target.value)} />
            </label>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-3 text-sm">
              <span>Rigonfiamento</span>
              <input type="range" min={1} max={10} step={1} value={liv}
                     disabled={auto}
                     onChange={(e) => setLiv(Number(e.target.value))}
                     className="flex-1" />
              <b>{auto ? "—" : `${FASCIA(liv)} ${liv}/10`}</b>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={auto}
                     onChange={(e) => setAuto(e.target.checked)} />
              Scegli tu — decide l&apos;AI in base al prodotto
            </label>
            <p className="text-xs opacity-60">
              1-3 teso e aderente · 4-6 volume standard · 7-10 volumetrico e gonfio
            </p>
          </div>

          <button disabled={teeth === ""}
                  onClick={() => esegui({ kind: "flowpack", teeth: Number(teeth),
                                          soft: auto ? "auto" : liv })}>
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
