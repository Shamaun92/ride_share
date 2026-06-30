import type { RideStatus } from "@/lib/types";

const FLOW: { key: RideStatus; label: string }[] = [
  { key: "requested", label: "Finding a driver" },
  { key: "accepted", label: "Driver assigned" },
  { key: "arrived", label: "Driver arrived" },
  { key: "in_progress", label: "On the way" },
  { key: "completed", label: "Completed" },
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
                  "grid h-5 w-5 place-items-center rounded-full border transition-colors",
                  done ? "border-jade bg-jade text-white" :
                  current ? "border-jade bg-jade/15 text-jade" :
                  "border-white/20 bg-transparent text-white/30",
                ].join(" ")}
              >
                {done ? (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none"><path d="M5 12.5 10 17l9-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                ) : current ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-jade" />
                ) : null}
              </span>
              {i < FLOW.length - 1 && <span className={`my-0.5 w-px flex-1 ${done ? "bg-jade/50" : "bg-white/10"}`} style={{ minHeight: 18 }} />}
            </div>
            <span className={`pb-4 text-sm ${current ? "font-medium text-white" : done ? "text-white/70" : "text-white/35"}`}>
              {step.label}
            </span>
          </li>
        );
      })}
      {terminal && (
        <li className="flex gap-3">
          <div className="grid h-5 w-5 place-items-center rounded-full border border-danger bg-danger/15 text-danger">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="3" strokeLinecap="round" /></svg>
          </div>
          <span className="text-sm font-medium text-danger">{status === "expired" ? "Expired" : "Cancelled"}</span>
        </li>
      )}
    </ol>
  );
}
