"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Car, Wallet, Clock, LayoutDashboard, LogOut } from "lucide-react";
import { Logo } from "./Logo";
import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/ride", label: "Ride", icon: Car },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/history", label: "History", icon: Clock },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const links = user?.role === "admin" ? [...LINKS, { href: "/admin", label: "Console", icon: LayoutDashboard }] : LINKS;

  const onLogout = () => { logout(); router.push("/login"); };

  return (
    <>
      {/* Desktop rail */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-card px-4 py-6 md:flex">
        <div className="px-2"><Logo /></div>
        <nav className="mt-8 flex flex-1 flex-col gap-1.5">
          {links.map((l) => {
            const active = pathname === l.href;
            const Icon = l.icon;
            return (
              <Link key={l.href} href={l.href}
                className={`group flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm font-semibold transition-all ${
                  active ? "bg-teal-soft text-teal-deep shadow-sm" : "text-slate2 hover:bg-paper hover:text-ink"}`}>
                <Icon size={19} strokeWidth={2.2} className={active ? "text-teal" : ""} />
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-line pt-4">
          <div className="flex items-center gap-3 rounded-2xl px-2 pb-2">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-teal-soft font-display text-sm font-bold text-teal-deep">
              {user?.full_name?.charAt(0) ?? "?"}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-ink">{user?.full_name}</div>
              <div className="truncate font-mono text-[11px] text-slate2">{user?.email}</div>
            </div>
          </div>
          <button onClick={onLogout} className="mt-1 flex w-full items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-semibold text-slate2 transition-colors hover:bg-danger/5 hover:text-danger">
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-line bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
        {links.map((l) => {
          const active = pathname === l.href;
          const Icon = l.icon;
          return (
            <Link key={l.href} href={l.href} className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-semibold transition-colors ${active ? "text-teal-deep" : "text-slate2"}`}>
              <span className={`grid h-8 w-12 place-items-center rounded-full transition-colors ${active ? "bg-teal-soft" : ""}`}><Icon size={19} /></span>
              {l.label}
            </Link>
          );
        })}
        <button onClick={onLogout} className="flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-semibold text-slate2">
          <span className="grid h-8 w-12 place-items-center"><LogOut size={19} /></span> Out
        </button>
      </nav>
    </>
  );
}
