import Link from "next/link";

import { Logo } from "@/components/brand/logo";

const FOOTER_COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/install", label: "Install" },
      { href: "/docs", label: "Docs" },
      { href: "/login", label: "Log in" },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="bg-ink text-ink-foreground">
      <div className="bg-grid-light">
        <div className="mx-auto max-w-6xl px-6 pt-16 sm:px-10">
          <div className="grid gap-12 md:grid-cols-[1.4fr_1fr]">
            <div>
              <Logo textClassName="text-ink-foreground" />
              <p className="mt-4 max-w-xs text-sm text-ink-foreground/60">
                Pull request reviews that read your whole diff, so your
                teammates only read what matters.
              </p>
            </div>

            {FOOTER_COLUMNS.map((column) => (
              <div key={column.title}>
                <h3 className="font-mono text-xs uppercase tracking-widest text-lime">
                  {column.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {column.links.map((link) => (
                    <li key={link.href}>
                      {"external" in link && link.external ? (
                        <a
                          href={link.href}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm text-ink-foreground/80 transition-colors hover:text-lime"
                        >
                          {link.label}
                        </a>
                      ) : (
                        <Link
                          href={link.href}
                          className="text-sm text-ink-foreground/80 transition-colors hover:text-lime"
                        >
                          {link.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <p className="mt-14 border-t border-white/10 py-6 font-mono text-xs text-ink-foreground/50">
            © {new Date().getFullYear()} DevBrief. All rights reserved.
          </p>
        </div>

        <div
          aria-hidden
          className="overflow-hidden px-6 sm:px-10"
        >
          <div className="mx-auto max-w-6xl select-none whitespace-nowrap text-center font-heading text-[22vw] font-extrabold leading-[0.8] tracking-tighter text-white/[0.06] sm:text-[15rem]">
            DevBrief
          </div>
        </div>
      </div>
    </footer>
  );
}
