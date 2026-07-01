"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Banknote, Bike, Car, ChevronRight, MapPin, Navigation, ArrowUpDown,
  ShieldCheck, Star, Tag, Users, Wallet as WalletIcon, X,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useRideSocket } from "@/lib/ws";
import { distanceKm, estimatePoisha } from "@/lib/fare";
import { bdt, bdtFromTaka, coord, STATUS_LABEL, surgeX, VEHICLE_LABEL } from "@/lib/format";
import type { PaymentMethod, Ride, RideReceipt, RideStatus, VehicleType } from "@/lib/types";
import { Badge, Button, Card, Skeleton, Spinner } from "@/components/ui";
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

const VEHICLES: { type: VehicleType; label: string; blurb: string; eta: number }[] = [
  { type: "car", label: "Car", blurb: "Comfortable · AC", eta: 3 },
  { type: "cng", label: "CNG", blurb: "Auto-rickshaw", eta: 5 },
  { type: "bike", label: "Bike", blurb: "Fastest & cheapest", eta: 2 },
];

function VehicleGlyph({ type, size = 20 }: { type: VehicleType; size?: number }) {
  if (type === "bike") return <Bike size={size} />;
  if (type === "car") return <Car size={size} />;
  // CNG three-wheeler
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 15 L5 8.5 C5.2 7 6 6 7.5 6 L13 6 C14 6 14.6 6.5 15 7.5 L17.5 13.5 L19 14 C19.6 14.2 20 14.8 20 15.5 L20 17 L4 17 Z"
            stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <circle cx="7" cy="18" r="2" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="17" cy="18" r="2" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export default function RidePage() {
  const [ride, setRide] = useState<Ride | null>(null);
  const [resuming, setResuming] = useState(true);

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
    return (
      <div className="mx-auto max-w-6xl lg:px-5 lg:py-8">
        <div className="grid lg:grid-cols-[1fr_420px] lg:gap-6">
          <Skeleton className="h-[38vh] w-full lg:h-[560px] lg:rounded-3xl" />
          <div className="-mt-6 space-y-3 rounded-t-3xl bg-card p-5 lg:mt-0 lg:rounded-3xl">
            <Skeleton className="h-24 w-full rounded-2xl" />
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-12 w-full rounded-2xl" />
          </div>
        </div>
      </div>
    );
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
  const prices = useMemo(() => Object.fromEntries(
    VEHICLES.map((v) => [v.type, estimatePoisha(dist, v.type, surgeBps, shared)]),
  ) as Record<VehicleType, number>, [dist, surgeBps, shared]);
  const estimate = prices[vehicle];
  const sameSpot = pickup.id === dropoff.id;

  useEffect(() => {
    let on = true;
    api.surge(pickup.lat, pickup.lng).then((s) => on && setSurgeBps(s.surge_bps)).catch(() => {});
    return () => { on = false; };
  }, [pickup]);

  function swap() { setPickup(dropoff); setDropoff(pickup); }

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
    <div className="mx-auto max-w-6xl lg:px-5 lg:py-8">
      <div className="grid lg:grid-cols-[1fr_420px] lg:gap-6">
        {/* Map */}
        <div className="relative h-[38vh] w-full overflow-hidden lg:h-full lg:min-h-[560px] lg:rounded-3xl lg:border lg:border-line lg:shadow-card">
          <DispatchMap pickup={pickup} dropoff={dropoff} driver={null} active={false} />
          <div className="pointer-events-none absolute left-4 top-4 flex items-center gap-2 rounded-full bg-card/95 px-3 py-1.5 text-xs font-semibold text-ink shadow-float backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-jade" /> {dist.toFixed(1)} km · {surgeBps > 10000 ? "surge" : "standard"} fare
          </div>
        </div>

        {/* Sheet */}
        <div className="relative -mt-6 animate-sheet rounded-t-3xl bg-card px-5 pb-8 pt-4 shadow-sheet lg:mt-0 lg:rounded-3xl lg:border lg:border-line lg:p-6 lg:shadow-card">
          <div className="mx-auto mb-3 h-1.5 w-10 rounded-full bg-line lg:hidden" />
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Where to?</h1>
          <p className="mb-4 text-sm text-slate2">Pick your route and we’ll dispatch the nearest driver.</p>

          {/* Route selector */}
          <div className="relative rounded-2xl border border-line bg-paper/50 p-2">
            <RouteRow marker={<span className="h-3 w-3 rounded-full border-2 border-teal bg-card" />} value={pickup} onChange={setPickup} label="Pickup" />
            <div className="ml-[26px] h-4 border-l-2 border-dotted border-line" />
            <RouteRow marker={<MapPin size={16} className="text-amber" />} value={dropoff} onChange={setDropoff} label="Drop-off" />
            <button type="button" onClick={swap} aria-label="Swap pickup and drop-off"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 grid h-9 w-9 place-items-center rounded-full border border-line bg-card text-slate2 shadow-sm transition-colors hover:text-ink active:scale-95">
              <ArrowUpDown size={15} />
            </button>
          </div>

          {/* Vehicle cards */}
          <div className="mt-5 space-y-2">
            {VEHICLES.map((v) => {
              const on = vehicle === v.type;
              return (
                <button key={v.type} type="button" onClick={() => setVehicle(v.type)}
                  className={`flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition-all active:scale-[0.99] ${
                    on ? "border-teal bg-teal-soft/60 ring-1 ring-teal" : "border-line hover:border-slate2/30 hover:bg-paper/50"}`}>
                  <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl2 ${on ? "bg-teal text-white" : "bg-paper text-ink"}`}>
                    <VehicleGlyph type={v.type} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                      {v.label}
                      <span className="font-mono text-[11px] font-medium text-slate2">{v.eta} min away</span>
                    </span>
                    <span className="block text-xs text-slate2">{v.blurb}</span>
                  </span>
                  <span className="text-right">
                    <span className="block font-mono text-base font-bold tnum text-ink">{bdt(prices[v.type])}</span>
                    {shared && <span className="block text-[10px] font-semibold uppercase tracking-wide text-jade">pooled</span>}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Options */}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setPayment(payment === "wallet" ? "cash" : "wallet")}
              className="flex items-center gap-2.5 rounded-2xl border border-line px-3.5 py-3 text-left transition-colors hover:bg-paper/50">
              {payment === "wallet" ? <WalletIcon size={18} className="text-teal-deep" /> : <Banknote size={18} className="text-jade" />}
              <span>
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-slate2">Pay with</span>
                <span className="block text-sm font-semibold text-ink">{payment === "wallet" ? "Wallet" : "Cash"}</span>
              </span>
            </button>
            <label className="flex items-center gap-2.5 rounded-2xl border border-line px-3.5 py-3">
              <Tag size={18} className="shrink-0 text-slate2" />
              <span className="min-w-0 flex-1">
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-slate2">Promo</span>
                <input value={promo} onChange={(e) => setPromo(e.target.value.toUpperCase())} placeholder="Add code"
                  className="w-full bg-transparent font-mono text-sm uppercase tracking-wider text-ink placeholder:font-sans placeholder:normal-case placeholder:tracking-normal placeholder:text-slate2/60 focus:outline-none" />
              </span>
            </label>
          </div>

          <button type="button" onClick={() => setShared(!shared)}
            className={`mt-2 flex w-full items-center justify-between rounded-2xl border px-3.5 py-3 text-left transition-colors ${
              shared ? "border-jade bg-jade/8" : "border-line"}`}>
            <span className="flex items-center gap-2.5">
              <Users size={18} className={shared ? "text-jade" : "text-slate2"} />
              <span>
                <span className="block text-sm font-semibold text-ink">Share & save</span>
                <span className="block text-xs text-slate2">Pool with a co-rider · 25% off</span>
              </span>
            </span>
            <span className={`h-6 w-11 rounded-full p-0.5 transition-colors ${shared ? "bg-jade" : "bg-line"}`}>
              <span className={`block h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${shared ? "translate-x-5" : ""}`} />
            </span>
          </button>

          {err && <p className="mt-3 rounded-2xl bg-danger/8 px-3 py-2.5 text-sm text-danger">{err}</p>}
          {sameSpot && <p className="mt-3 text-center text-xs text-slate2">Pick two different locations to continue.</p>}

          <Button size="lg" onClick={submit} disabled={busy || sameSpot} className="mt-4 w-full">
            {busy ? <Spinner /> : <>Request {VEHICLE_LABEL[vehicle]} · {bdt(estimate)}</>}
          </Button>
        </div>
      </div>
    </div>
  );
}

function RouteRow({ marker, value, onChange, label }: {
  marker: React.ReactNode; value: Place; onChange: (p: Place) => void; label: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl2 px-2.5 py-2">
      <span className="grid w-4 place-items-center">{marker}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[10px] font-semibold uppercase tracking-wide text-slate2">{label}</span>
        <select value={value.id} onChange={(e) => onChange(PLACES.find((p) => p.id === e.target.value)!)}
          className="-ml-0.5 w-full cursor-pointer appearance-none bg-transparent pr-6 text-sm font-semibold text-ink focus:outline-none">
          {PLACES.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </span>
      <ChevronRight size={16} className="shrink-0 text-slate2/50" />
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

  useEffect(() => {
    if (terminal) return;
    const t = setInterval(async () => {
      try { onUpdate(await api.getRide(ride.id)); } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(t);
  }, [ride.id, terminal, onUpdate]);

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
    <div className="mx-auto max-w-6xl lg:px-5 lg:py-8">
      <div className="grid lg:grid-cols-[1fr_400px] lg:gap-6">
        {/* Map */}
        <div className="relative h-[42vh] w-full overflow-hidden lg:h-full lg:min-h-[600px] lg:rounded-3xl lg:border lg:border-line lg:shadow-card">
          <DispatchMap
            pickup={{ lat: ride.pickup_lat, lng: ride.pickup_lng }}
            dropoff={{ lat: ride.dropoff_lat, lng: ride.dropoff_lng }}
            driver={driverPt} active={!terminal && !!driverPt}
          />
          <div className="absolute left-4 top-4 rounded-2xl bg-card/95 px-3.5 py-2 shadow-float backdrop-blur">
            <div className="font-display text-sm font-bold text-ink">{STATUS_LABEL[status]}</div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-slate2">Ride {ride.id.slice(0, 8)}</div>
          </div>
          <div className="absolute right-4 top-4">
            <Badge tone={live.connected ? "jade" : "slate"}>
              <span className={`h-1.5 w-1.5 rounded-full ${live.connected ? "animate-pulse bg-jade" : "bg-slate2"}`} />
              {live.connected ? "Live" : "Connecting"}
            </Badge>
          </div>
        </div>

        {/* Sheet */}
        <div className="relative -mt-6 animate-sheet space-y-4 rounded-t-3xl bg-card px-5 pb-8 pt-4 shadow-sheet lg:mt-0 lg:rounded-none lg:bg-transparent lg:px-0 lg:pb-0 lg:pt-0 lg:shadow-none">
          <div className="mx-auto h-1.5 w-10 rounded-full bg-line lg:hidden" />

          <Telemetry items={[
            { label: "ETA", value: terminal ? "—" : eta, accent: "jade" },
            { label: "Distance", value: `${ride.distance_km.toFixed(1)} km` },
            { label: "Surge", value: surgeX(ride.surge_bps), accent: ride.surge_bps > 10000 ? "amber" : undefined },
            { label: finished ? "Fare" : "Est.", value: finished ? bdtFromTaka(ride.final_fare) : bdtFromTaka(ride.estimated_fare), accent: "teal" },
          ]} />

          {ride.driver && !terminal && (
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-full bg-teal-soft font-display text-lg font-bold text-teal-deep">
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

          <Card className="p-5"><RideTimeline status={status} /></Card>

          <Card className="p-4">
            <div className="space-y-3 text-sm">
              <Leg marker={<span className="mt-1 h-3 w-3 rounded-full border-2 border-teal bg-card" />} label={ride.pickup_address} sub={coord(ride.pickup_lat, ride.pickup_lng)} />
              <div className="ml-[5px] h-3 border-l-2 border-dotted border-line" />
              <Leg marker={<Navigation size={15} className="mt-0.5 text-amber" />} label={ride.dropoff_address} sub={coord(ride.dropoff_lat, ride.dropoff_lng)} />
            </div>
          </Card>

          {!terminal && (status === "requested" || status === "accepted" || status === "scheduled") && (
            <Button variant="danger" onClick={cancel} className="w-full"><X size={16} /> Cancel ride</Button>
          )}

          {finished && <CompletionCard ride={ride} receipt={receipt} onReset={onReset} />}
          {(status === "cancelled" || status === "expired") && (
            <Button size="lg" onClick={onReset} className="w-full">Book another ride</Button>
          )}
        </div>
      </div>
    </div>
  );
}

function Leg({ marker, label, sub }: { marker: React.ReactNode; label: string; sub: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="grid w-4 place-items-center">{marker}</span>
      <span className="min-w-0">
        <span className="block truncate font-semibold text-ink">{label}</span>
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
    try { await api.rate(ride.id, n); setRated(true); } catch { setRated(true); }
    finally { setBusy(false); }
  }

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-jade/12"><ShieldCheck size={18} className="text-jade" /></span>
        <span className="font-display text-lg font-bold text-ink">Trip complete</span>
      </div>
      <div className="mt-3 flex items-end justify-between border-b border-line pb-3">
        <span className="text-sm text-slate2">Total fare</span>
        <span className="font-mono text-2xl font-bold text-ink tnum">{bdtFromTaka(ride.final_fare)}</span>
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
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate2">{rated ? "Thanks for rating" : "Rate your driver"}</div>
        <div className="flex gap-1.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} disabled={busy || rated} onClick={() => rate(n)} aria-label={`${n} stars`} className="transition-transform active:scale-90">
              <Star size={28} className={n <= score ? "fill-amber text-amber" : "text-line hover:text-amber/50"} />
            </button>
          ))}
        </div>
      </div>
      <Button size="lg" onClick={onReset} className="mt-5 w-full">Book another ride</Button>
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between"><dt>{k}</dt><dd className="text-ink">{v}</dd></div>;
}
