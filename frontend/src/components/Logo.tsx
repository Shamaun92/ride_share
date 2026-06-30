export function Logo({ className = "", mark = false }: { className?: string; mark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className="relative grid h-7 w-7 place-items-center rounded-lg bg-teal text-white">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M4 16.5 12 4l8 12.5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="12" cy="18.5" r="2" fill="currentColor" />
        </svg>
      </span>
      {!mark && <span className="font-display text-lg font-bold tracking-tight text-ink">Shohojatri</span>}
    </span>
  );
}
