"use client";

import { useEffect, useState } from "react";
import { Plus, ArrowDownLeft, ArrowUpRight, Wallet as WalletIcon } from "lucide-react";
import { api } from "@/lib/api";
import { bdt, timeAgo } from "@/lib/format";
import type { WalletStatement } from "@/lib/types";
import { Card, Skeleton, Spinner } from "@/components/ui";

const ACCOUNT_LABEL: Record<string, string> = {
  rider_wallet: "Ride / top-up", driver_wallet: "Earnings",
  platform_revenue: "Platform", cash_clearing: "Top-up", promo_expense: "Promo",
};

export default function WalletPage() {
  const [data, setData] = useState<WalletStatement | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.wallet().then(setData).catch(() => {});
  useEffect(() => { load(); }, []);

  async function topup(amount: number) {
    setBusy(true);
    try { await api.topup(amount); await load(); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-8">
      <h1 className="mb-6 font-display text-2xl font-bold tracking-tight text-ink">Wallet</h1>

      {/* Balance card */}
      <div className="overflow-hidden rounded-3xl bg-ink shadow-console">
        <div className="relative p-6">
          <div className="console-grid absolute inset-0 opacity-70" />
          <div className="relative">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-white/50">
              <WalletIcon size={14} /> Available balance
            </div>
            <div className="mt-2 font-mono text-5xl font-bold text-white tnum">
              {data ? bdt(data.wallet.balance_poisha) : "৳—"}
            </div>
            <div className="mt-1 font-mono text-[11px] uppercase tracking-wider text-teal">Shohojatri Wallet</div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-white/10 bg-white/[0.03] p-4">
          <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-white/50">Top up</span>
          {[200, 500, 1000].map((amt) => (
            <button key={amt} disabled={busy} onClick={() => topup(amt)}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white/10 disabled:opacity-50 active:scale-95">
              <Plus size={14} /> ৳{amt}
            </button>
          ))}
          {busy && <span className="self-center text-white"><Spinner /></span>}
        </div>
      </div>

      <h2 className="mb-3 mt-8 text-xs font-semibold uppercase tracking-wide text-slate2">Activity</h2>
      <Card>
        {!data ? (
          <ul className="divide-y divide-line">
            {[0, 1, 2].map((i) => (
              <li key={i} className="flex items-center gap-3 px-5 py-3.5">
                <Skeleton className="h-9 w-9 rounded-full" />
                <div className="flex-1 space-y-1.5"><Skeleton className="h-3.5 w-28" /><Skeleton className="h-2.5 w-16" /></div>
                <Skeleton className="h-4 w-16" />
              </li>
            ))}
          </ul>
        ) : data.entries.length === 0 ? (
          <p className="px-5 py-12 text-center text-sm text-slate2">No activity yet. Top up to get started.</p>
        ) : (
          <ul className="divide-y divide-line">
            {data.entries.map((e) => {
              const credit = e.amount_poisha >= 0;
              return (
                <li key={e.id} className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-paper/50">
                  <span className={`grid h-10 w-10 place-items-center rounded-full ${credit ? "bg-jade/10 text-jade" : "bg-slate2/10 text-slate2"}`}>
                    {credit ? <ArrowDownLeft size={17} /> : <ArrowUpRight size={17} />}
                  </span>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-ink">{ACCOUNT_LABEL[e.account] ?? e.account}</div>
                    <div className="font-mono text-[11px] text-slate2">{timeAgo(e.created_at)}</div>
                  </div>
                  <span className={`font-mono text-sm font-bold tnum ${credit ? "text-jade" : "text-ink"}`}>
                    {credit ? "+" : "−"}{bdt(Math.abs(e.amount_poisha))}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
