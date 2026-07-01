"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/Logo";
import { Button, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      await register(form);
      router.push("/ride");
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : "Could not create account");
    } finally { setBusy(false); }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto w-full max-w-sm">
          <Link href="/"><Logo /></Link>
          <h1 className="mt-10 font-display text-3xl font-bold tracking-tight text-ink">Create your account</h1>
          <p className="mt-2 text-sm text-slate2">Riders only — book a ride in under a minute.</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <Field label="Full name">
              <Input value={form.full_name} onChange={set("full_name")} placeholder="Rafi Ahmed" required minLength={2} />
            </Field>
            <Field label="Email">
              <Input type="email" value={form.email} onChange={set("email")} placeholder="you@example.com" required />
            </Field>
            <Field label="Phone">
              <Input value={form.phone} onChange={set("phone")} placeholder="+8801XXXXXXXXX" required minLength={6} />
            </Field>
            <Field label="Password" hint="min 8 chars">
              <Input type="password" value={form.password} onChange={set("password")} placeholder="••••••••" required minLength={8} />
            </Field>
            {err && <p className="rounded-2xl bg-danger/8 px-3 py-2.5 text-sm text-danger">{err}</p>}
            <Button size="lg" type="submit" disabled={busy} className="w-full">{busy ? <Spinner /> : "Create account"}</Button>
          </form>

          <p className="mt-6 text-sm text-slate2">
            Already have one? <Link href="/login" className="font-semibold text-teal-deep hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
      <div className="relative hidden overflow-hidden bg-ink lg:block">
        <div className="console-grid absolute inset-0 opacity-90" />
        <div className="relative flex h-full flex-col justify-end p-12">
          <div className="grid max-w-md grid-cols-3 gap-px overflow-hidden rounded-2xl border border-white/10">
            {[["RIDES", "live"], ["PRICING", "surge"], ["WALLET", "ledger"]].map(([l, v]) => (
              <div key={l} className="bg-white/[0.04] px-4 py-5">
                <div className="text-[10px] uppercase tracking-wider text-white/45">{l}</div>
                <div className="mt-1 font-mono text-sm font-bold text-white">{v}</div>
              </div>
            ))}
          </div>
          <p className="mt-6 max-w-md font-display text-xl font-medium leading-snug text-white">
            Surge-aware fares, pooled rides, and a receipt for every trip.
          </p>
        </div>
      </div>
    </main>
  );
}
