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
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-card px-4 py-6 md:flex">
        <div className="px-2"><Logo /></div>
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {links.map((l) => {
            const active = pathname === l.href;
            const Icon = l.icon;
            return (
              <Link key={l.href} href={l.href}
                className={`flex items-center gap-3 rounded-xl2 px-3 py-2.5 text-sm font-medium transition-colors ${
                  active ? "bg-teal/10 text-teal-deep" : "text-slate2 hover:bg-ink/5 hover:text-ink"}`}>
                <Icon size={18} strokeWidth={2} />
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-line pt-4">
          <div className="px-3 pb-2">
            <div className="truncate text-sm font-medium text-ink">{user?.full_name}</div>
            <div className="truncate font-mono text-[11px] text-slate2">{user?.email}</div>
          </div>
          <button onClick={onLogout} className="flex w-full items-center gap-3 rounded-xl2 px-3 py-2.5 text-sm font-medium text-slate2 hover:bg-danger/5 hover:text-danger">
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-line bg-card/95 backdrop-blur md:hidden">
        {links.map((l) => {
          const active = pathname === l.href;
          const Icon = l.icon;
          return (
            <Link key={l.href} href={l.href} className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium ${active ? "text-teal-deep" : "text-slate2"}`}>
              <Icon size={20} /> {l.label}
            </Link>
          );
        })}
        <button onClick={onLogout} className="flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium text-slate2">
          <LogOut size={20} /> Out
        </button>
      </nav>
    </>
  );
}
