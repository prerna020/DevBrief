import { AlertTriangle, GitPullRequest, ShieldAlert } from "lucide-react";

import { cn } from "@/lib/utils";

type DiffLine = { n: number; kind: "add" | "del" | "ctx"; text: string };

const DIFF: DiffLine[] = [
  { n: 41, kind: "ctx", text: "def get_user(request, user_id):" },
  { n: 42, kind: "del", text: '    row = db.get("users", id=user_id)' },
  { n: 42, kind: "add", text: '    q = f"SELECT * FROM users WHERE id = {user_id}"' },
  { n: 43, kind: "add", text: "    row = db.execute(q).fetchone()" },
  { n: 44, kind: "ctx", text: "    return jsonify(row)" },
];

/** A fake pull request review: diff lines plus an inline finding. */
export function ReviewMock({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border-2 border-foreground bg-card shadow-hard",
        className
      )}
    >
      <div className="flex items-center gap-3 border-b-2 border-foreground bg-lime px-4 py-3 text-lime-foreground">
        <GitPullRequest className="size-4 shrink-0" />
        <span className="truncate font-mono text-xs font-semibold">
          acme/api #482 · Add user lookup endpoint
        </span>
        <span className="ml-auto shrink-0 rounded-sm bg-lime-foreground px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase text-lime">
          2 findings
        </span>
      </div>

      <div className="font-mono text-[12.5px] leading-6">
        {DIFF.map((line, i) => (
          <div
            key={i}
            className={cn(
              "flex gap-3 px-4",
              line.kind === "add" && "bg-emerald-500/10",
              line.kind === "del" && "bg-red-500/10"
            )}
          >
            <span className="w-6 shrink-0 select-none text-right text-muted-foreground">
              {line.kind === "del" ? "" : line.n}
            </span>
            <span
              className={cn(
                "w-3 shrink-0 select-none",
                line.kind === "add" && "text-emerald-600 dark:text-emerald-400",
                line.kind === "del" && "text-red-600 dark:text-red-400"
              )}
            >
              {line.kind === "add" ? "+" : line.kind === "del" ? "-" : " "}
            </span>
            <span className="whitespace-pre text-foreground/90">{line.text}</span>
          </div>
        ))}
      </div>

      <div className="m-3 rounded-md border-2 border-destructive/60 bg-destructive/5 p-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-destructive" />
          <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-destructive">
            Critical · SQL injection
          </span>
        </div>
        <p className="mt-2 text-sm text-foreground/80">
          <code className="font-mono text-xs">user_id</code> is interpolated
          straight into the query. Use a parameterized statement:
          <code className="mt-1.5 block rounded-sm bg-ink px-2 py-1 font-mono text-xs text-ink-foreground">
            db.execute(&quot;... WHERE id = ?&quot;, (user_id,))
          </code>
        </p>
      </div>

      <div className="mx-3 mb-3 flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
        <AlertTriangle className="size-3.5 text-amber-500" />
        Warning · line 43 · <span className="font-mono">fetchone()</span> may
        return <span className="font-mono">None</span>
      </div>
    </div>
  );
}

/** A fake terminal session for the CLI. */
export function TerminalMock({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border-2 border-foreground bg-ink text-ink-foreground",
        className
      )}
    >
      <div className="flex items-center gap-1.5 border-b border-white/10 px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="ml-3 font-mono text-[11px] text-white/40">~/projects/api</span>
      </div>
      <div className="space-y-1 p-4 font-mono text-[12.5px] leading-6">
        <p>
          <span className="text-lime">$</span> devbrief review --staged
        </p>
        <p className="text-white/50">Reading staged diff (3 files, +74 -12)...</p>
        <p className="text-white/50">Reviewing...</p>
        <p className="pt-2">
          <span className="text-red-400">critical</span>{" "}
          <span className="text-white/70">api/users.py:42</span>
        </p>
        <p className="pl-4 text-white/80">Unparameterized SQL query.</p>
        <p>
          <span className="text-amber-300">warning </span>{" "}
          <span className="text-white/70">api/users.py:43</span>
        </p>
        <p className="pl-4 text-white/80">fetchone() can return None.</p>
        <p className="caret pt-2 text-lime">2 findings</p>
      </div>
    </div>
  );
}
