"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/Logo";
import { DispatchMap } from "@/components/Map";
import { Button, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      await login(identifier, password);
      router.push("/ride");
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : "Could not sign in");
    } finally { setBusy(false); }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto w-full max-w-sm">
          <Link href="/"><Logo /></Link>
          <h1 className="mt-10 font-display text-3xl font-bold tracking-tight text-ink">Welcome back</h1>
          <p className="mt-2 text-sm text-slate2">Sign in to request a ride and track it live.</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <Field label="Email or phone">
              <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="you@example.com" autoComplete="username" required />
            </Field>
            <Field label="Password">
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password" required />
            </Field>
            {err && <p className="rounded-2xl bg-danger/8 px-3 py-2.5 text-sm text-danger">{err}</p>}
            <Button size="lg" type="submit" disabled={busy} className="w-full">
              {busy ? <Spinner /> : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-slate2">
            New here? <Link href="/register" className="font-semibold text-teal-deep hover:underline">Create an account</Link>
          </p>
        </div>
      </div>
      <AuthAside />
    </main>
  );
}

function AuthAside() {
  return (
    <div className="relative hidden overflow-hidden bg-ink lg:block">
      <div className="console-grid absolute inset-0 opacity-90" />
      <div className="relative flex h-full flex-col justify-between p-12">
        <div className="max-w-md rounded-3xl border border-white/10 bg-white/[0.04] p-2 shadow-console">
          <div className="h-56 overflow-hidden rounded-2xl">
            <DispatchMap pickup={{ lat: 23.7806, lng: 90.4074 }} dropoff={{ lat: 23.7461, lng: 90.3742 }} driver={{ lat: 23.7702, lng: 90.3999 }} active />
          </div>
          <div className="flex items-center justify-between px-3 py-2.5 font-mono text-[11px] uppercase tracking-wider text-white/50">
            <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jade" /> Driver en route</span>
            <span>ETA 6 min</span>
          </div>
        </div>
        <blockquote className="max-w-md">
          <p className="font-display text-2xl font-medium leading-snug text-white">
            “Every trip is a live channel — the moment a driver moves, you see it.”
          </p>
          <footer className="mt-4 font-mono text-[11px] uppercase tracking-wider text-white/45">
            Real-time dispatch · Redis Pub/Sub · WebSockets
          </footer>
        </blockquote>
      </div>
    </div>
  );
}
