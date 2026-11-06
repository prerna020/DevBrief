import Link from "next/link";
import { GitFork, Terminal } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function InstallPage() {
  return (
    <section className="bg-grid">
      <div className="mx-auto max-w-5xl px-6 py-20 sm:px-10">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          Install
        </p>
        <h1 className="mt-3 text-4xl font-extrabold tracking-tighter sm:text-6xl">
          Get started with <span className="mark-lime">DevBrief</span>
        </h1>
        <p className="mt-4 max-w-xl text-lg text-muted-foreground">
          DevBrief reviews code in two places. Both use the same account.
        </p>

        <div className="mt-14 grid gap-8 md:grid-cols-2">
          <div className="flex flex-col rounded-xl border-2 border-foreground bg-card p-7 shadow-hard">
            <div className="flex items-center justify-between">
              <span className="flex size-12 items-center justify-center rounded-md bg-lime text-lime-foreground">
                <GitFork className="size-6" />
              </span>
              <span className="rounded-sm border border-foreground px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider">
                Most teams
              </span>
            </div>
            <h2 className="mt-6 text-2xl font-bold tracking-tight">GitHub App</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Every pull request is reviewed automatically, with inline
              comments, a summary, and a pass/fail check.
            </p>
            <Button
              size="lg"
              variant="lime"
              className="mt-8 w-full"
              render={<Link href="/dashboard" />}
            >
              Install on GitHub
            </Button>
          </div>

          <div className="flex flex-col rounded-xl border-2 border-foreground bg-card p-7 shadow-hard">
            <span className="flex size-12 items-center justify-center rounded-md bg-ink text-lime">
              <Terminal className="size-6" />
            </span>
            <h2 className="mt-6 text-2xl font-bold tracking-tight">Command line</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Review staged, uncommitted, or committed changes locally. No
              GitHub connection required.
            </p>
            <p className="mt-8 rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
              The CLI is not published as a public package yet. Setup steps
              are in <code className="font-mono">LOCAL_SETUP.md</code> in the
              repository.
            </p>
          </div>
        </div>

        <p className="mt-12 text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-foreground underline decoration-lime decoration-2 underline-offset-4 hover:bg-lime hover:text-lime-foreground"
          >
            Sign in
          </Link>
        </p>
      </div>
    </section>
  );
}
