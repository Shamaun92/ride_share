"use client";

import { useEffect, useState } from "react";
import { Plus, ArrowDownLeft, ArrowUpRight, Wallet as WalletIcon } from "lucide-react";
import { api } from "@/lib/api";
import { bdt, timeAgo } from "@/lib/format";
import type { WalletStatement } from "@/lib/types";
import { Button, Card, Spinner } from "@/components/ui";

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

      <Card className="overflow-hidden">
        <div className="bg-ink p-6">
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-white/50">
            <WalletIcon size={14} /> Balance
          </div>
          <div className="mt-2 font-mono text-4xl font-bold text-white tnum">
            {data ? bdt(data.wallet.balance_poisha) : "৳—"}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 border-t border-line p-4">
          {[200, 500, 1000].map((amt) => (
            <Button key={amt} variant="ghost" disabled={busy} onClick={() => topup(amt)}>
              <Plus size={14} /> ৳{amt}
            </Button>
          ))}
          {busy && <span className="self-center"><Spinner className="text-teal" /></span>}
        </div>
      </Card>

      <h2 className="mb-3 mt-8 text-xs font-medium uppercase tracking-wide text-slate2">Activity</h2>
      <Card>
        {!data ? (
          <div className="grid place-items-center py-12"><Spinner className="text-teal" /></div>
        ) : data.entries.length === 0 ? (
          <p className="px-5 py-12 text-center text-sm text-slate2">No activity yet. Top up to get started.</p>
        ) : (
          <ul className="divide-y divide-line">
            {data.entries.map((e) => {
              const credit = e.amount_poisha >= 0;
              return (
                <li key={e.id} className="flex items-center gap-3 px-5 py-3.5">
                  <span className={`grid h-9 w-9 place-items-center rounded-full ${credit ? "bg-jade/10 text-jade" : "bg-slate2/10 text-slate2"}`}>
                    {credit ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}
                  </span>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-ink">{ACCOUNT_LABEL[e.account] ?? e.account}</div>
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
