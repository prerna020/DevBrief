import React from "react";
import Link from "next/link";

import { Logo } from "@/components/brand/logo";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[1.1fr_1fr]">
      {/* Left: brand panel (hidden on mobile) */}
      <div className="bg-grid-light relative hidden flex-col justify-between overflow-hidden bg-ink p-12 text-ink-foreground lg:flex">
        <Link href="/" aria-label="DevBrief home">
          <Logo textClassName="text-ink-foreground" />
        </Link>

        <div>
          <div className="rounded-xl border border-white/15 bg-black/30 p-5 font-mono text-[13px] leading-7">
            <p>
              <span className="text-lime">$</span> git push origin feature/login
            </p>
            <p className="text-white/50">PR #482 opened</p>
            <p>
              <span className="text-lime">devbrief</span>{" "}
              <span className="text-white/70">reviewing 6 files...</span>
            </p>
            <p className="text-red-400">critical: unparameterized query</p>
            <p className="caret text-amber-300">warning: unchecked None</p>
          </div>
          <p className="mt-8 max-w-sm font-heading text-3xl font-extrabold leading-tight tracking-tight">
            Ship the change. <span className="text-lime">We read the diff.</span>
          </p>
        </div>

        <p className="font-mono text-xs text-white/40">
          © {new Date().getFullYear()} DevBrief
        </p>
      </div>

      {/* Right: login content */}
      <div className="flex items-center justify-center px-4 py-16">
        {children}
      </div>
    </div>
  );
}
