import Link from "next/link";
import { Logo } from "@/components/Logo";
import { DispatchMap } from "@/components/Map";
import { ArrowRight, Radio, Route, ShieldCheck, Star, Wallet } from "lucide-react";

const HERO_PICKUP = { lat: 23.7806, lng: 90.4074 };
const HERO_DROPOFF = { lat: 23.7461, lng: 90.3742 };
const HERO_DRIVER = { lat: 23.7702, lng: 90.3999 };

export default function Landing() {
  return (
    <main className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo />
        <div className="flex items-center gap-2">
          <Link href="/login" className="rounded-full px-4 py-2 text-sm font-semibold text-ink hover:bg-ink/5">Sign in</Link>
          <Link href="/register" className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white shadow-float hover:bg-ink2">Get started</Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-10 pt-8 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
        <div className="flex flex-col justify-center">
          <span className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-slate2 shadow-sm">
            <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-jade opacity-60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-jade" /></span>
            Live dispatch · Dhaka
          </span>
          <h1 className="font-display text-5xl font-bold leading-[1.03] tracking-tight text-ink sm:text-6xl">
            Your ride,<br />tracked <span className="text-teal">in real time.</span>
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-slate2">
            Book a car, CNG, or bike in seconds. Watch your driver approach live,
            pay from your wallet, and get a receipt for every trip.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/register" className="inline-flex items-center gap-2 rounded-full bg-teal px-6 py-3.5 text-[15px] font-semibold text-white shadow-float transition-colors hover:bg-teal-deep">
              Book your first ride <ArrowRight size={16} />
            </Link>
            <Link href="/login" className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-6 py-3.5 text-[15px] font-semibold text-ink hover:bg-ink/5">
              I have an account
            </Link>
          </div>
          <div className="mt-10 grid max-w-md grid-cols-3 gap-4">
            {[
              { icon: Radio, label: "Live tracking", sub: "WebSocket" },
              { icon: Route, label: "Surge + pooling", sub: "supply-aware" },
              { icon: Wallet, label: "Wallet ledger", sub: "double-entry" },
            ].map((f) => (
              <div key={f.label} className="rounded-2xl border border-line bg-card p-3.5 shadow-sm">
                <f.icon size={18} className="text-teal" />
                <div className="mt-2 text-sm font-semibold text-ink">{f.label}</div>
                <div className="font-mono text-[11px] text-slate2">{f.sub}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Phone preview */}
        <div className="flex justify-center lg:justify-end">
          <PhonePreview />
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-6 py-10 font-mono text-[11px] text-slate2">
        Shohojatri — a portfolio build · FastAPI · PostgreSQL · Redis · WebSockets · Next.js
      </footer>
    </main>
  );
}

function PhonePreview() {
  return (
    <div className="relative w-[300px]">
      <div className="absolute -inset-6 -z-10 rounded-[3.5rem] bg-teal/10 blur-2xl" />
      <div className="rounded-[2.75rem] border-[10px] border-ink bg-ink shadow-console">
        <div className="relative h-[560px] overflow-hidden rounded-[2.1rem] bg-map-bg">
          {/* notch */}
          <div className="absolute left-1/2 top-0 z-20 h-6 w-32 -translate-x-1/2 rounded-b-2xl bg-ink" />
          {/* map */}
          <div className="absolute inset-0">
            <DispatchMap pickup={HERO_PICKUP} dropoff={HERO_DROPOFF} driver={HERO_DRIVER} active />
          </div>
          {/* status pill */}
          <div className="absolute left-4 right-4 top-9 flex items-center gap-2 rounded-2xl bg-card/95 px-3.5 py-2.5 shadow-float backdrop-blur">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-jade/12"><Radio size={16} className="text-jade" /></span>
            <div>
              <div className="text-sm font-bold text-ink">Driver 3 min away</div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-slate2">Rafi · Toyota Axio</div>
            </div>
          </div>
          {/* bottom card */}
          <div className="absolute inset-x-3 bottom-3 rounded-3xl bg-card p-4 shadow-float">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-full bg-teal-soft font-display font-bold text-teal-deep">R</div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-ink">Rafi Ahmed</div>
                <div className="flex items-center gap-1 font-mono text-[11px] text-slate2">
                  <Star size={11} className="fill-amber text-amber" /> 4.9 · DHA-GA-2213
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono text-lg font-bold tnum text-ink">৳248</div>
                <div className="flex items-center justify-end gap-1 text-[10px] font-semibold uppercase tracking-wide text-jade"><ShieldCheck size={11} /> wallet</div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 overflow-hidden rounded-2xl border border-line">
              {[["ETA", "6 min"], ["DIST", "4.2 km"], ["SURGE", "1.3×"]].map(([l, v], i) => (
                <div key={l} className={`px-3 py-2 ${i < 2 ? "border-r border-line" : ""}`}>
                  <div className="text-[9px] font-semibold uppercase tracking-wider text-slate2">{l}</div>
                  <div className={`font-mono text-sm font-bold ${i === 2 ? "text-amber" : "text-ink"}`}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
