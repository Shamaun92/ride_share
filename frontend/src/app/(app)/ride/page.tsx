"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Car, Bike, Loader2, MapPin, Navigation, ShieldCheck, Star, Users, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useRideSocket } from "@/lib/ws";
import { distanceKm, estimatePoisha } from "@/lib/fare";
import { bdt, bdtFromTaka, coord, STATUS_LABEL, surgeX, VEHICLE_LABEL } from "@/lib/format";
import type { PaymentMethod, Ride, RideReceipt, RideStatus, VehicleType } from "@/lib/types";
import { Badge, Button, Card, Field, Select, Spinner } from "@/components/ui";
import { DispatchMap } from "@/components/Map";
import { Telemetry } from "@/components/Telemetry";
import { RideTimeline } from "@/components/RideTimeline";

interface Place { id: string; name: string; lat: number; lng: number; }
const PLACES: Place[] = [
  { id: "gulshan", name: "Gulshan 1", lat: 23.7806, lng: 90.4074 },
  { id: "banani", name: "Banani", lat: 23.7937, lng: 90.4066 },
  { id: "dhanmondi", name: "Dhanmondi 27", lat: 23.7461, lng: 90.3742 },
  { id: "motijheel", name: "Motijheel", lat: 23.7330, lng: 90.4172 },
  { id: "mohakhali", name: "Mohakhali", lat: 23.7783, lng: 90.4055 },
  { id: "mirpur", name: "Mirpur 10", lat: 23.8069, lng: 90.3686 },
  { id: "uttara", name: "Uttara", lat: 23.8759, lng: 90.3795 },
  { id: "airport", name: "Airport (HSIA)", lat: 23.8431, lng: 90.3978 },
];
const ACTIVE: RideStatus[] = ["scheduled", "requested", "accepted", "arrived", "in_progress"];

export default function RidePage() {
  const [ride, setRide] = useState<Ride | null>(null);
  const [resuming, setResuming] = useState(true);

  // On load, resume any in-flight ride.
  useEffect(() => {
    (async () => {
      try {
        const rides = await api.listRides();
        const live = rides.find((r) => ACTIVE.includes(r.status));
        if (live) setRide(live);
      } catch { /* not signed in yet / empty */ }
      finally { setResuming(false); }
    })();
  }, []);

  if (resuming) {
    return <div className="grid h-[60vh] place-items-center"><Spinner className="text-teal" /></div>;
  }
  return ride ? (
    <LiveConsole ride={ride} onReset={() => setRide(null)} onUpdate={setRide} />
  ) : (
    <RequestForm onRequested={setRide} />
  );
}

/* --------------------------------- Request -------------------------------- */
function RequestForm({ onRequested }: { onRequested: (r: Ride) => void }) {
  const [pickup, setPickup] = useState<Place>(PLACES[0]);
  const [dropoff, setDropoff] = useState<Place>(PLACES[2]);
  const [vehicle, setVehicle] = useState<VehicleType>("car");
  const [payment, setPayment] = useState<PaymentMethod>("wallet");
  const [shared, setShared] = useState(false);
  const [promo, setPromo] = useState("");
  const [surgeBps, setSurgeBps] = useState(10000);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const dist = useMemo(() => distanceKm(pickup.lat, pickup.lng, dropoff.lat, dropoff.lng), [pickup, dropoff]);
  const estimate = useMemo(() => estimatePoisha(dist, vehicle, surgeBps, shared), [dist, vehicle, surgeBps, shared]);

  useEffect(() => {
    let on = true;
    api.surge(pickup.lat, pickup.lng).then((s) => on && setSurgeBps(s.surge_bps)).catch(() => {});
    return () => { on = false; };
  }, [pickup]);

  async function submit() {
    setErr(null); setBusy(true);
    try {
      const res = await api.requestRide({
        pickup_lat: pickup.lat, pickup_lng: pickup.lng, pickup_address: pickup.name,
        dropoff_lat: dropoff.lat, dropoff_lng: dropoff.lng, dropoff_address: dropoff.name,
        vehicle_type: vehicle, payment_method: payment, shared,
        promo_code: promo.trim() || null,
      });
      onRequested(res.ride);
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : "Could not request ride");
    } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Where to?</h1>
        <p className="text-sm text-slate2">Pick your route and we’ll dispatch the nearest driver.</p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        {/* Map preview */}
        <Card className="overflow-hidden">
          <div className="aspect-[16/10] w-full bg-ink">
            <DispatchMap pickup={pickup} dropoff={dropoff} driver={null} active={false} />
          </div>
          <div className="grid grid-cols-3 divide-x divide-line border-t border-line">
            <Readout label="Distance" value={`${dist.toFixed(1)} km`} />
            <Readout label="Surge" value={surgeX(surgeBps)} accent={surgeBps > 10000 ? "amber" : undefined} />
            <Readout label="Est. fare" value={bdt(estimate)} accent="teal" />
          </div>
        </Card>

        {/* Controls */}
        <Card className="p-5">
          <div className="space-y-4">
            <Field label="Pickup">
              <PlaceSelect value={pickup} onChange={setPickup} />
            </Field>
            <Field label="Drop-off">
              <PlaceSelect value={dropoff} onChange={setDropoff} />
            </Field>

            <Field label="Vehicle">
              <div className="grid grid-cols-3 gap-2">
                {(["car", "cng", "bike"] as VehicleType[]).map((v) => (
                  <button key={v} onClick={() => setVehicle(v)} type="button"
                    className={`flex flex-col items-center gap-1 rounded-xl2 border px-2 py-2.5 text-xs font-medium transition-colors ${
                      vehicle === v ? "border-teal bg-teal/8 text-teal-deep" : "border-line text-slate2 hover:border-slate2/40"}`}>
                    {v === "bike" ? <Bike size={18} /> : <Car size={18} />}
                    {VEHICLE_LABEL[v]}
                  </button>
                ))}
              </div>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Pay with">
                <Select value={payment} onChange={(e) => setPayment(e.target.value as PaymentMethod)}>
                  <option value="wallet">Wallet</option>
                  <option value="cash">Cash</option>
                </Select>
              </Field>
              <Field label="Promo">
                <input value={promo} onChange={(e) => setPromo(e.target.value.toUpperCase())} placeholder="CODE"
                  className="w-full rounded-xl2 border border-line bg-card px-3.5 py-2.5 font-mono text-sm uppercase tracking-wider text-ink placeholder:text-slate2/50 focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/20" />
              </Field>
            </div>

            <button type="button" onClick={() => setShared(!shared)}
              className={`flex w-full items-center justify-between rounded-xl2 border px-3.5 py-3 text-left transition-colors ${
                shared ? "border-jade bg-jade/8" : "border-line"}`}>
              <span className="flex items-center gap-2.5">
                <Users size={18} className={shared ? "text-jade" : "text-slate2"} />
                <span>
                  <span className="block text-sm font-medium text-ink">Share & save</span>
                  <span className="block text-xs text-slate2">Pool with a co-rider · 25% off</span>
                </span>
              </span>
              <span className={`h-5 w-9 rounded-full p-0.5 transition-colors ${shared ? "bg-jade" : "bg-line"}`}>
                <span className={`block h-4 w-4 rounded-full bg-white transition-transform ${shared ? "translate-x-4" : ""}`} />
              </span>
            </button>

            {err && <p className="rounded-xl2 bg-danger/8 px-3 py-2 text-sm text-danger">{err}</p>}
            <Button onClick={submit} disabled={busy || pickup.id === dropoff.id} className="w-full">
              {busy ? <Spinner /> : <>Request {VEHICLE_LABEL[vehicle]} · {bdt(estimate)}</>}
            </Button>
            {pickup.id === dropoff.id && <p className="text-center text-xs text-slate2">Pick two different locations.</p>}
          </div>
        </Card>
      </div>
    </div>
  );
}

function PlaceSelect({ value, onChange }: { value: Place; onChange: (p: Place) => void }) {
  return (
    <Select value={value.id} onChange={(e) => onChange(PLACES.find((p) => p.id === e.target.value)!)}>
      {PLACES.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
    </Select>
  );
}

function Readout({ label, value, accent }: { label: string; value: string; accent?: "teal" | "amber" }) {
  const c = accent === "teal" ? "text-teal-deep" : accent === "amber" ? "text-amber" : "text-ink";
  return (
    <div className="px-4 py-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-slate2">{label}</div>
      <div className={`mt-0.5 font-mono text-sm font-bold tnum ${c}`}>{value}</div>
    </div>
  );
}

/* ------------------------------- Live console ------------------------------ */
function LiveConsole({ ride, onReset, onUpdate }: { ride: Ride; onReset: () => void; onUpdate: (r: Ride) => void }) {
  const live = useRideSocket(ride.id);
  const [receipt, setReceipt] = useState<RideReceipt | null>(null);
  const status: RideStatus = live.status ?? ride.status;
  const finished = status === "completed";
  const terminal = finished || status === "cancelled" || status === "expired";

  // Poll ride detail for driver info + status reconciliation while active.
  useEffect(() => {
    if (terminal) return;
    const t = setInterval(async () => {
      try { onUpdate(await api.getRide(ride.id)); } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(t);
  }, [ride.id, terminal, onUpdate]);

  // On completion, load the receipt.
  useEffect(() => {
    if (finished && !receipt) api.receipt(ride.id).then(setReceipt).catch(() => {});
  }, [finished, receipt, ride.id]);

  const driverPt = live.driverLocation
    ?? (ride.driver?.current_lat != null ? { lat: ride.driver.current_lat, lng: ride.driver.current_lng! } : null);

  const eta = useMemo(() => {
    if (!driverPt) return "—";
    const target = status === "in_progress"
      ? { lat: ride.dropoff_lat, lng: ride.dropoff_lng }
      : { lat: ride.pickup_lat, lng: ride.pickup_lng };
    const d = distanceKm(driverPt.lat, driverPt.lng, target.lat, target.lng);
    const min = Math.max(1, Math.round((d / 20) * 60));
    return `${min} min`;
  }, [driverPt, status, ride]);

  async function cancel() {
    try { const r = await api.cancelRide(ride.id, "Changed plans"); onUpdate(r); } catch { /* ignore */ }
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-8">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink">{STATUS_LABEL[status]}</h1>
          <p className="font-mono text-xs text-slate2">RIDE {ride.id.slice(0, 8).toUpperCase()}</p>
        </div>
        <Badge tone={live.connected ? "jade" : "slate"}>
          <span className={`h-1.5 w-1.5 rounded-full ${live.connected ? "bg-jade" : "bg-slate2"}`} />
          {live.connected ? "Live" : "Connecting"}
        </Badge>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        {/* Console */}
        <div className="overflow-hidden rounded-xl2 bg-ink shadow-console">
          <div className="aspect-[16/10] w-full">
            <DispatchMap
              pickup={{ lat: ride.pickup_lat, lng: ride.pickup_lng }}
              dropoff={{ lat: ride.dropoff_lat, lng: ride.dropoff_lng }}
              driver={driverPt} active={!terminal && !!driverPt}
            />
          </div>
          <div className="p-3">
            <Telemetry items={[
              { label: "ETA", value: terminal ? "—" : eta, accent: "jade" },
              { label: "Distance", value: `${ride.distance_km.toFixed(1)} km` },
              { label: "Surge", value: surgeX(ride.surge_bps), accent: ride.surge_bps > 10000 ? "amber" : undefined },
              { label: finished ? "Fare" : "Est.", value: finished ? bdtFromTaka(ride.final_fare) : bdtFromTaka(ride.estimated_fare), accent: "jade" },
            ]} />
          </div>
        </div>

        {/* Side panel */}
        <div className="space-y-4">
          <Card className="p-5">
            <RideTimeline status={status} />
          </Card>

          {ride.driver && !terminal && (
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-full bg-teal/10 font-display font-bold text-teal-deep">
                  {ride.driver.full_name.charAt(0)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold text-ink">{ride.driver.full_name}</div>
                  <div className="flex items-center gap-1 font-mono text-xs text-slate2">
                    <Star size={12} className="fill-amber text-amber" /> {ride.driver.rating_avg.toFixed(1)}
                    {ride.driver.vehicle && <> · {ride.driver.vehicle.license_plate}</>}
                  </div>
                </div>
                {ride.driver.vehicle && <Badge tone="teal">{VEHICLE_LABEL[ride.driver.vehicle.vehicle_type]}</Badge>}
              </div>
            </Card>
          )}

          <Card className="p-4">
            <div className="space-y-2.5 text-sm">
              <Leg icon={<MapPin size={15} className="text-jade" />} label={ride.pickup_address} sub={coord(ride.pickup_lat, ride.pickup_lng)} />
              <Leg icon={<Navigation size={15} className="text-amber" />} label={ride.dropoff_address} sub={coord(ride.dropoff_lat, ride.dropoff_lng)} />
            </div>
          </Card>

          {!terminal && (status === "requested" || status === "accepted" || status === "scheduled") && (
            <Button variant="danger" onClick={cancel} className="w-full"><X size={16} /> Cancel ride</Button>
          )}

          {finished && <CompletionCard ride={ride} receipt={receipt} onReset={onReset} />}
          {(status === "cancelled" || status === "expired") && (
            <Button onClick={onReset} className="w-full">Book another ride</Button>
          )}
        </div>
      </div>
    </div>
  );
}

function Leg({ icon, label, sub }: { icon: React.ReactNode; label: string; sub: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5">{icon}</span>
      <span className="min-w-0">
        <span className="block truncate font-medium text-ink">{label}</span>
        <span className="block font-mono text-[11px] text-slate2">{sub}</span>
      </span>
    </div>
  );
}

function CompletionCard({ ride, receipt, onReset }: { ride: Ride; receipt: RideReceipt | null; onReset: () => void }) {
  const [score, setScore] = useState(0);
  const [rated, setRated] = useState(false);
  const [busy, setBusy] = useState(false);

  async function rate(n: number) {
    setScore(n); setBusy(true);
    try { await api.rate(ride.id, n); setRated(true); } catch { /* maybe already rated */ setRated(true); }
    finally { setBusy(false); }
  }

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <ShieldCheck size={18} className="text-jade" />
        <span className="font-display text-lg font-bold text-ink">Trip complete</span>
      </div>
      <div className="mt-3 flex items-end justify-between border-b border-line pb-3">
        <span className="text-sm text-slate2">Total fare</span>
        <span className="font-mono text-2xl font-bold text-ink">{bdtFromTaka(ride.final_fare)}</span>
      </div>
      {receipt?.payment && (
        <dl className="mt-3 space-y-1.5 font-mono text-xs text-slate2">
          <Row k="Method" v={receipt.payment.method} />
          {receipt.payment.breakdown?.promo_discount ? (
            <Row k="Promo" v={`− ${bdt(Number(receipt.payment.breakdown.promo_discount))}`} />
          ) : null}
          <Row k="Commission" v={bdt(receipt.payment.commission_poisha)} />
        </dl>
      )}
      <div className="mt-4">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate2">{rated ? "Thanks for rating" : "Rate your driver"}</div>
        <div className="flex gap-1.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} disabled={busy || rated} onClick={() => rate(n)} aria-label={`${n} stars`}>
              <Star size={26} className={n <= score ? "fill-amber text-amber" : "text-line hover:text-amber/50"} />
            </button>
          ))}
        </div>
      </div>
      <Button onClick={onReset} className="mt-5 w-full">Book another ride</Button>
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between"><dt>{k}</dt><dd className="text-ink">{v}</dd></div>;
}
