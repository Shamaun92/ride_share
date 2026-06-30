"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { bdtFromTaka, STATUS_LABEL, timeAgo, VEHICLE_LABEL } from "@/lib/format";
import type { Ride, RideStatus } from "@/lib/types";
import { Badge, Card, Spinner } from "@/components/ui";

const TONE: Partial<Record<RideStatus, "jade" | "amber" | "slate" | "danger" | "teal">> = {
  completed: "jade", cancelled: "danger", expired: "slate", in_progress: "teal", requested: "amber",
};

export default function HistoryPage() {
  const [rides, setRides] = useState<Ride[] | null>(null);
  useEffect(() => { api.listRides().then(setRides).catch(() => setRides([])); }, []);

  return (
    <div className="mx-auto max-w-3xl px-5 py-8">
      <h1 className="mb-6 font-display text-2xl font-bold tracking-tight text-ink">Your rides</h1>

      {!rides ? (
        <div className="grid place-items-center py-16"><Spinner className="text-teal" /></div>
      ) : rides.length === 0 ? (
        <Card className="px-5 py-16 text-center">
          <Clock className="mx-auto text-line" size={28} />
          <p className="mt-3 text-sm text-slate2">No rides yet. Your trips will show up here.</p>
        </Card>
      ) : (
        <ul className="space-y-3">
          {rides.map((r) => (
            <Card key={r.id} className="p-4">
              <div className="flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 text-sm font-medium text-ink">
                    <span className="truncate">{r.pickup_address}</span>
                    <ArrowRight size={14} className="shrink-0 text-slate2" />
                    <span className="truncate">{r.dropoff_address}</span>
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-slate2">
                    {VEHICLE_LABEL[r.vehicle_type]} · {r.distance_km.toFixed(1)} km · {timeAgo(r.created_at)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-sm font-bold text-ink tnum">
                    {bdtFromTaka(r.final_fare ?? r.estimated_fare)}
                  </div>
                  <Badge tone={TONE[r.status] ?? "slate"}>{STATUS_LABEL[r.status]}</Badge>
                </div>
              </div>
            </Card>
          ))}
        </ul>
      )}
    </div>
  );
}
