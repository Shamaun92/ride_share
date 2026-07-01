"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { api } from "@/lib/api";
import { bdtFromTaka, STATUS_LABEL, timeAgo, VEHICLE_LABEL } from "@/lib/format";
import type { Ride, RideStatus } from "@/lib/types";
import { Badge, Card, Skeleton } from "@/components/ui";

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
        <ul className="space-y-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-[74px] w-full rounded-3xl" />)}
        </ul>
      ) : rides.length === 0 ? (
        <Card className="px-5 py-16 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-paper"><Clock className="text-slate2" size={24} /></div>
          <p className="mt-3 text-sm text-slate2">No rides yet. Your trips will show up here.</p>
        </Card>
      ) : (
        <ul className="space-y-3">
          {rides.map((r) => (
            <Card key={r.id} className="p-4 transition-shadow hover:shadow-float">
              <div className="flex items-center gap-4">
                {/* route markers */}
                <div className="flex flex-col items-center pt-1">
                  <span className="h-2.5 w-2.5 rounded-full border-2 border-teal bg-card" />
                  <span className="my-0.5 h-6 w-0.5 rounded-full bg-line" />
                  <span className="h-2.5 w-2.5 rounded-sm bg-amber" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold text-ink">{r.pickup_address}</div>
                  <div className="truncate text-sm font-semibold text-ink">{r.dropoff_address}</div>
                  <div className="mt-1.5 font-mono text-[11px] text-slate2">
                    {VEHICLE_LABEL[r.vehicle_type]} · {r.distance_km.toFixed(1)} km · {timeAgo(r.created_at)}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1.5">
                  <div className="font-mono text-base font-bold text-ink tnum">
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
