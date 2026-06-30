"use client";

import { useEffect, useState } from "react";
import { Activity, BadgeDollarSign, Car, Users } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { bdt } from "@/lib/format";
import type { AdminMetrics } from "@/lib/types";
import { Card, Spinner } from "@/components/ui";

const STATUS_TONE: Record<string, string> = {
  completed: "bg-jade", in_progress: "bg-teal", requested: "bg-amber",
  cancelled: "bg-danger", scheduled: "bg-slate2", accepted: "bg-teal-deep",
  arrived: "bg-teal", expired: "bg-line",
};

export default function AdminPage() {
  const [m, setM] = useState<AdminMetrics | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setM).catch((e) => setErr(e instanceof ApiError ? e.detail : "Failed to load"));
  }, []);

  if (err) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16 text-center">
        <p className="text-sm text-danger">{err}</p>
        <p className="mt-1 text-xs text-slate2">This console requires an admin account.</p>
      </div>
    );
  }
  if (!m) return <div className="grid h-[60vh] place-items-center"><Spinner className="text-teal" /></div>;

  const total = m.total_rides || 1;
  const statuses = Object.entries(m.rides_by_status).sort((a, b) => b[1] - a[1]);

  return (
    <div className="mx-auto max-w-5xl px-5 py-8">
      <h1 className="mb-1 font-display text-2xl font-bold tracking-tight text-ink">Operations console</h1>
      <p className="mb-6 font-mono text-xs text-slate2">Live platform metrics from the ledger</p>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tile icon={<BadgeDollarSign size={18} />} label="Platform revenue" value={bdt(m.platform_revenue_poisha)} accent />
        <Tile icon={<Activity size={18} />} label="Total rides" value={String(m.total_rides)} />
        <Tile icon={<Car size={18} />} label="Active drivers" value={String(m.active_drivers)} />
        <Tile icon={<Users size={18} />} label="Total users" value={String(m.total_users)} />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-slate2">Rides by status</h2>
          <div className="space-y-3">
            {statuses.length === 0 && <p className="text-sm text-slate2">No rides yet.</p>}
            {statuses.map(([s, n]) => (
              <div key={s}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize text-ink">{s.replace("_", " ")}</span>
                  <span className="font-mono font-bold tnum text-slate2">{n}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-line/60">
                  <div className={`h-full rounded-full ${STATUS_TONE[s] ?? "bg-slate2"}`} style={{ width: `${(n / total) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-slate2">Ledger</h2>
          <dl className="space-y-3 font-mono text-sm">
            <Line k="Platform revenue" v={bdt(m.platform_revenue_poisha)} tone="text-jade" />
            <Line k="Promo expense" v={`− ${bdt(Math.abs(m.promo_expense_poisha))}`} tone="text-amber" />
            <div className="border-t border-line pt-3">
              <Line k="Net" v={bdt(m.platform_revenue_poisha + m.promo_expense_poisha)} tone="text-ink" bold />
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}

function Tile({ icon, label, value, accent }: { icon: React.ReactNode; label: string; value: string; accent?: boolean }) {
  return (
    <Card className={`p-4 ${accent ? "bg-ink" : ""}`}>
      <span className={accent ? "text-jade" : "text-teal"}>{icon}</span>
      <div className={`mt-3 font-mono text-xl font-bold tnum ${accent ? "text-white" : "text-ink"}`}>{value}</div>
      <div className={`text-[11px] uppercase tracking-wider ${accent ? "text-white/50" : "text-slate2"}`}>{label}</div>
    </Card>
  );
}

function Line({ k, v, tone, bold }: { k: string; v: string; tone: string; bold?: boolean }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate2">{k}</dt>
      <dd className={`${tone} ${bold ? "font-bold" : ""}`}>{v}</dd>
    </div>
  );
}
