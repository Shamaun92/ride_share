"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="grid min-h-screen place-items-center text-slate2">
        <Spinner className="text-teal" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Nav />
      <div className="flex-1 pb-20 md:pb-0">{children}</div>
    </div>
  );
}
