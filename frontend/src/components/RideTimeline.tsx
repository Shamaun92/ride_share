import type { RideStatus } from "@/lib/types";

const FLOW: { key: RideStatus; label: string; sub: string }[] = [
  { key: "requested", label: "Finding a driver", sub: "Matching you with the nearest driver" },
  { key: "accepted", label: "Driver assigned", sub: "On the way to your pickup" },
  { key: "arrived", label: "Driver arrived", sub: "Your driver is at the pickup point" },
  { key: "in_progress", label: "On the way", sub: "Heading to your destination" },
  { key: "completed", label: "Completed", sub: "You've arrived" },
];
const ORDER: RideStatus[] = ["requested", "accepted", "arrived", "in_progress", "completed"];

export function RideTimeline({ status }: { status: RideStatus | null }) {
  const terminal = status === "cancelled" || status === "expired";
  const idx = status ? ORDER.indexOf(status) : -1;
  return (
    <ol className="space-y-0">
      {FLOW.map((step, i) => {
        const done = idx >= 0 && i < idx;
        const current = idx === i;
        return (
          <li key={step.key} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={[
                  "grid h-6 w-6 place-items-center rounded-full border-2 transition-colors",
                  done ? "border-jade bg-jade text-white" :
                  current ? "border-jade bg-jade/15 text-jade" :
                  "border-line bg-card text-slate2/40",
                ].join(" ")}
              >
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M5 12.5 10 17l9-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                ) : current ? (
                  <span className="h-2 w-2 animate-pulse rounded-full bg-jade" />
                ) : null}
              </span>
              {i < FLOW.length - 1 && <span className={`my-1 w-0.5 flex-1 rounded-full ${done ? "bg-jade/45" : "bg-line"}`} style={{ minHeight: 20 }} />}
            </div>
            <div className="pb-5">
              <div className={`text-sm ${current ? "font-semibold text-ink" : done ? "font-medium text-ink/70" : "text-slate2/60"}`}>
                {step.label}
              </div>
              {current && <div className="mt-0.5 text-xs text-slate2">{step.sub}</div>}
            </div>
          </li>
        );
      })}
      {terminal && (
        <li className="flex gap-3">
          <div className="grid h-6 w-6 place-items-center rounded-full border-2 border-danger bg-danger/15 text-danger">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="3" strokeLinecap="round" /></svg>
          </div>
          <span className="text-sm font-semibold text-danger">{status === "expired" ? "Expired — no driver found" : "Ride cancelled"}</span>
        </li>
      )}
    </ol>
  );
}
