import { Fragment } from "react";

// Clean readout strip for light surfaces. Values are mono; labels small caps.
export function Telemetry({ items }: { items: { label: string; value: string; accent?: "jade" | "amber" | "teal" }[] }) {
  const accentColor = { jade: "text-jade", amber: "text-amber", teal: "text-teal-deep" } as const;
  return (
    <div className="flex flex-wrap items-stretch overflow-hidden rounded-2xl border border-line bg-paper/60">
      {items.map((it, i) => (
        <Fragment key={it.label}>
          <div className="min-w-[84px] flex-1 px-4 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate2">{it.label}</div>
            <div className={`mt-0.5 font-mono text-base font-bold tnum ${it.accent ? accentColor[it.accent] : "text-ink"}`}>
              {it.value}
            </div>
          </div>
          {i < items.length - 1 && <div className="w-px bg-line" />}
        </Fragment>
      ))}
    </div>
  );
}
