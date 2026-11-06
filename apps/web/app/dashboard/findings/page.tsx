import Link from "next/link";
import { redirect } from "next/navigation";
import { AlertTriangle, ArrowLeft, ExternalLink, Info, ShieldAlert } from "lucide-react";
import { getUserFindings, type UserFinding } from "@devbrief/db";

import { auth } from "@/auth";
import { Card, CardContent } from "@/components/ui/card";
import { cached } from "@/lib/ttl-cache";
import { cn } from "@/lib/utils";

type Severity = UserFinding["severity"];

const SEVERITIES: Severity[] = ["critical", "warning", "info"];
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const SEVERITY_STYLE: Record<
  Severity,
  { label: string; badge: string; icon: React.ComponentType<{ className?: string }> }
> = {
  critical: {
    label: "Critical",
    badge: "bg-destructive/10 text-destructive",
    icon: ShieldAlert,
  },
  warning: {
    label: "Warning",
    badge: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    icon: AlertTriangle,
  },
  info: {
    label: "Info",
    badge: "bg-muted text-muted-foreground",
    icon: Info,
  },
};

function isSeverity(value: string | undefined): value is Severity {
  return !!value && (SEVERITIES as string[]).includes(value);
}

function tabHref(severity: Severity | undefined, reviewId: string | undefined) {
  const params = new URLSearchParams();
  if (severity) params.set("severity", severity);
  if (reviewId) params.set("review", reviewId);
  const qs = params.toString();
  return qs ? `/dashboard/findings?${qs}` : "/dashboard/findings";
}

export default async function FindingsPage({
  searchParams,
}: {
  searchParams: Promise<{ severity?: string; review?: string }>;
}) {
  const session = await auth();
  if (!session?.user?.id) redirect("/login?callbackUrl=/dashboard/findings");

  const params = await searchParams;
  const severity = isSeverity(params.severity) ? params.severity : undefined;
  const reviewId = params.review && UUID.test(params.review) ? params.review : undefined;

  const userId = session.user.id;
  const list = await cached(`findings:${userId}:${severity ?? ""}:${reviewId ?? ""}`, 15_000, () =>
    getUserFindings(userId, { severity, reviewId }),
  );
  const first = list[0];

  return (
    <div className="flex flex-col gap-6">
      <div>
        {reviewId && (
          <Link
            href={tabHref(severity, undefined)}
            className="mb-3 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            All findings
          </Link>
        )}
        <h1 className="text-3xl font-extrabold tracking-tighter">
          {reviewId && first ? `${first.repoFullName} #${first.prNumber}` : "Findings"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {reviewId
            ? "Everything DevBrief flagged in this review."
            : "Every unresolved issue DevBrief has flagged on your pull requests."}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {[undefined, ...SEVERITIES].map((s) => {
          const active = s === severity;
          return (
            <Link
              key={s ?? "all"}
              href={tabHref(s, reviewId)}
              className={cn(
                "rounded-md border-2 px-3 py-1.5 font-mono text-xs font-semibold transition-colors",
                active
                  ? "border-foreground bg-lime text-lime-foreground"
                  : "border-border text-muted-foreground hover:border-foreground hover:text-foreground",
              )}
            >
              {s ? SEVERITY_STYLE[s].label : "All"}
            </Link>
          );
        })}
      </div>

      {list.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No findings here. Open a pull request with a bug in it on a connected repo and DevBrief
            will list what it finds.
          </CardContent>
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {list.map((f) => {
            const style = SEVERITY_STYLE[f.severity];
            const Icon = style.icon;
            const repoUrl = `https://github.com/${f.repoFullName}`;
            return (
              <li key={f.id}>
                <Card>
                  <CardContent className="flex flex-col gap-3 pt-5">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold",
                          style.badge,
                        )}
                      >
                        <Icon className="size-3" />
                        {style.label}
                      </span>
                      <Link
                        href={`/dashboard/findings?review=${f.reviewId}`}
                        className="font-medium text-foreground hover:underline"
                      >
                        {f.repoFullName} #{f.prNumber}
                      </Link>
                      <span className="text-muted-foreground">
                        {f.createdAt.toLocaleDateString()}
                      </span>
                      <a
                        href={`${repoUrl}/pull/${f.prNumber}/files`}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-auto inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
                      >
                        Open PR <ExternalLink className="size-3" />
                      </a>
                    </div>

                    <a
                      href={`${repoUrl}/blob/${f.headSha}/${f.file}#L${f.line}`}
                      target="_blank"
                      rel="noreferrer"
                      className="w-fit break-all rounded-sm bg-muted px-2 py-1 font-mono text-xs hover:bg-lime hover:text-lime-foreground"
                    >
                      {f.file}:{f.line}
                    </a>

                    <div>
                      <p className="text-sm font-semibold">{f.message}</p>
                      <p className="mt-1.5 whitespace-pre-wrap text-sm text-muted-foreground">
                        {f.rationale}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
