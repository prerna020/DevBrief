import { Card, CardContent } from "@/components/ui/card";

/** Shown instantly while a dashboard page loads its data (the sidebar stays in place). */
export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-6" role="status" aria-live="polite" aria-label="Loading">
      <div className="space-y-2">
        <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
        <div className="h-4 w-72 animate-pulse rounded-md bg-muted" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="flex items-center gap-3 pt-6">
              <div className="size-9 animate-pulse rounded-md bg-muted" />
              <div className="space-y-2">
                <div className="h-6 w-10 animate-pulse rounded-md bg-muted" />
                <div className="h-3 w-24 animate-pulse rounded-md bg-muted" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="space-y-3 pt-6">
          <div className="h-5 w-40 animate-pulse rounded-md bg-muted" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 animate-pulse rounded-md bg-muted" />
          ))}
        </CardContent>
      </Card>

      <span className="sr-only">Loading…</span>
    </div>
  );
}
