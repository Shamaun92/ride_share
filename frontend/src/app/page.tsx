import Link from "next/link";
import { Logo } from "@/components/Logo";
import { ArrowRight, Radio, Route, Wallet } from "lucide-react";

export default function Landing() {
  return (
    <main className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo />
        <div className="flex items-center gap-2">
          <Link href="/login" className="rounded-xl2 px-4 py-2 text-sm font-medium text-ink hover:bg-ink/5">Sign in</Link>
          <Link href="/register" className="rounded-xl2 bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-ink2">Get started</Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-10 px-6 pb-8 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
        <div className="flex flex-col justify-center">
          <span className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-slate2">
            <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-jade opacity-60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-jade" /></span>
            Live dispatch · Dhaka
          </span>
          <h1 className="font-display text-5xl font-bold leading-[1.05] tracking-tight text-ink sm:text-6xl">
            Request a ride.<br />Watch it <span className="text-teal">move.</span>
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-slate2">
            A real-time ride-hailing console — surge-aware pricing, a wallet ledger,
            pooled rides, and a live trip you can follow second by second.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/register" className="inline-flex items-center gap-2 rounded-xl2 bg-teal px-5 py-3 text-sm font-medium text-white hover:bg-teal-deep">
              Book your first ride <ArrowRight size={16} />
            </Link>
            <Link href="/login" className="inline-flex items-center gap-2 rounded-xl2 border border-line bg-card px-5 py-3 text-sm font-medium text-ink hover:bg-ink/5">
              I have an account
            </Link>
          </div>
          <div className="mt-10 grid max-w-md grid-cols-3 gap-4">
            {[
              { icon: Radio, label: "Live tracking", sub: "WebSocket" },
              { icon: Route, label: "Surge + pooling", sub: "supply-aware" },
              { icon: Wallet, label: "Wallet ledger", sub: "double-entry" },
            ].map((f) => (
              <div key={f.label}>
                <f.icon size={18} className="text-teal" />
                <div className="mt-2 text-sm font-medium text-ink">{f.label}</div>
                <div className="font-mono text-[11px] text-slate2">{f.sub}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Console preview */}
        <div className="relative">
          <div className="overflow-hidden rounded-xl2 bg-ink shadow-console">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-3.5">
              <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-white/50">
                <span className="h-2 w-2 rounded-full bg-jade" /> Trip · live
              </div>
              <div className="font-mono text-[11px] text-white/40">SHJ-4827</div>
            </div>
            <div className="console-grid relative aspect-[4/3] w-full">
              <svg viewBox="0 0 460 345" className="h-full w-full">
                <line x1="70" y1="250" x2="380" y2="90" stroke="#0FA3A3" strokeWidth="2.5" strokeDasharray="2 7" strokeLinecap="round" opacity="0.75" />
                <circle cx="70" cy="250" r="6" fill="#16C172" />
                <text x="82" y="254" fill="#9FB0C8" fontSize="10" fontFamily="var(--font-mono)">PICKUP</text>
                <rect x="375" y="85" width="10" height="10" rx="2" fill="#F6A623" />
                <text x="392" y="94" fill="#9FB0C8" fontSize="10" fontFamily="var(--font-mono)">DROPOFF</text>
                <g transform="translate(230 170)">
                  <circle r="9" fill="#16C172" className="animate-ping2" style={{ transformBox: "fill-box", transformOrigin: "center" }} />
                  <circle r="6.5" fill="#fff" /><circle r="4" fill="#16C172" />
                </g>
              </svg>
            </div>
            <div className="grid grid-cols-4 gap-px border-t border-white/10 bg-white/5">
              {[["ETA", "6 min"], ["DIST", "4.2 km"], ["SURGE", "1.3×"], ["FARE", "৳248"]].map(([l, v], i) => (
                <div key={l} className="bg-ink px-3 py-3">
                  <div className="text-[10px] uppercase tracking-wider text-white/45">{l}</div>
                  <div className={`mt-0.5 font-mono text-sm font-bold ${i === 2 ? "text-amber" : i === 3 ? "text-jade" : "text-white"}`}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-6 py-10 font-mono text-[11px] text-slate2">
        Shohojatri — a portfolio build · FastAPI · PostgreSQL · Redis · WebSockets · Next.js
      </footer>
    </main>
  );
}
