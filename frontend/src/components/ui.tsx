"use client";

import { forwardRef } from "react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes } from "react";

function cx(...c: (string | false | undefined)[]) { return c.filter(Boolean).join(" "); }

type BtnVariant = "primary" | "ghost" | "dark" | "danger";
export function Button({
  variant = "primary", className, ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl2 px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-teal";
  const variants: Record<BtnVariant, string> = {
    primary: "bg-teal text-white hover:bg-teal-deep",
    ghost: "bg-transparent text-ink hover:bg-ink/5 border border-line",
    dark: "bg-ink text-white hover:bg-ink2",
    danger: "bg-transparent text-danger border border-danger/30 hover:bg-danger/5",
  };
  return <button className={cx(base, variants[variant], className)} {...props} />;
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cx(
          "w-full rounded-xl2 border border-line bg-card px-3.5 py-2.5 text-sm text-ink placeholder:text-slate2/60",
          "focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/20",
          className,
        )}
        {...props}
      />
    );
  },
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select
        ref={ref}
        className={cx(
          "w-full appearance-none rounded-xl2 border border-line bg-card px-3.5 py-2.5 text-sm text-ink",
          "focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/20",
          className,
        )}
        {...props}
      >
        {children}
      </select>
    );
  },
);

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate2">{label}</span>
        {hint && <span className="font-mono text-[11px] text-slate2/70">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cx("rounded-xl2 border border-line bg-card shadow-card", className)}>{children}</div>;
}

type Tone = "teal" | "jade" | "amber" | "slate" | "danger";
export function Badge({ tone = "slate", children }: { tone?: Tone; children: React.ReactNode }) {
  const tones: Record<Tone, string> = {
    teal: "bg-teal/10 text-teal-deep", jade: "bg-jade/10 text-jade",
    amber: "bg-amber/15 text-amber", slate: "bg-slate2/10 text-slate2",
    danger: "bg-danger/10 text-danger",
  };
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cx("animate-spin", className)} width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
