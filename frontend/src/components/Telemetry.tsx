import { Fragment } from "react";

// Console-style readout strip. Values are mono; labels small caps.
export function Telemetry({ items }: { items: { label: string; value: string; accent?: "jade" | "amber" | "teal" }[] }) {
  const accentColor = { jade: "text-jade", amber: "text-amber", teal: "text-teal" } as const;
  return (
    <div className="flex flex-wrap items-stretch gap-px overflow-hidden rounded-xl2 border border-white/10 bg-white/[0.03]">
      {items.map((it, i) => (
        <Fragment key={it.label}>
          <div className="min-w-[88px] flex-1 px-3.5 py-2.5">
            <div className="text-[10px] font-medium uppercase tracking-wider text-white/45">{it.label}</div>
            <div className={`mt-0.5 font-mono text-sm font-bold tnum ${it.accent ? accentColor[it.accent] : "text-white"}`}>
              {it.value}
            </div>
          </div>
          {i < items.length - 1 && <div className="w-px bg-white/10" />}
        </Fragment>
      ))}
    </div>
  );
}
