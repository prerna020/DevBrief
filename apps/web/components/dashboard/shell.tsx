"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/theme-toggle";
import { Logo } from "@/components/brand/logo";
import { DashboardNav } from "@/components/dashboard/nav";
import { UserMenu } from "@/components/dashboard/user-menu";

export function DashboardShell({
  user,
  onSignOut,
  children,
}: {
  user: { name?: string | null; email?: string | null; image?: string | null };
  onSignOut: () => void | Promise<void>;
  children: React.ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 flex-col border-r-2 border-foreground bg-sidebar text-sidebar-foreground md:flex">
        <div className="flex h-16 items-center px-5">
          <Link href="/" aria-label="DevBrief home">
            <Logo textClassName="text-sidebar-foreground" />
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto px-3">
          <DashboardNav />
        </div>
        <div className="border-t border-sidebar-border p-3">
          <UserMenu {...user} onSignOut={onSignOut} />
        </div>
      </aside>

      {/* Main column */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b-2 border-border px-4 md:px-6">
          <div className="flex items-center gap-2 md:hidden">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger
                render={<Button variant="ghost" size="icon" aria-label="Open menu" />}
              >
                <Menu className="size-5" />
              </SheetTrigger>
              <SheetContent side="left" className="w-64 bg-sidebar p-0">
                <SheetHeader className="h-16 justify-center border-b border-sidebar-border px-4">
                  <SheetTitle className="text-sidebar-foreground">
                    <Logo textClassName="text-sidebar-foreground" />
                  </SheetTitle>
                </SheetHeader>
                <div className="flex h-[calc(100%-4rem)] flex-col justify-between px-3 py-3">
                  <DashboardNav onNavigate={() => setMobileOpen(false)} />
                  <div className="border-t border-sidebar-border pt-3">
                    <UserMenu {...user} onSignOut={onSignOut} />
                  </div>
                </div>
              </SheetContent>
            </Sheet>
            <Logo />
          </div>

          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>

        <main className="bg-grid flex-1 px-4 py-8 md:px-10">{children}</main>
      </div>
    </div>
  );
}
