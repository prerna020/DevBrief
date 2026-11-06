import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';

if (!process.env.DATABASE_URL) {
    throw new Error('DATABASE_URL is not set');
}

// In development, Next.js's hot-module-reloading re-executes this module on
// every file change, which would otherwise create a brand new `postgres()`
// client (and a brand new connection pool) on every reload — old clients'
// connections are never explicitly closed, so they pile up over a long dev
// session. Caching the client on `globalThis` across reloads avoids this.
// This is the standard fix for this class of bug (same pattern Prisma/Drizzle
// docs recommend) and is a likely contributor to the intermittent
// "password authentication failed" errors seen after long-running dev
// sessions — stale/orphaned connections racing against Neon's pooler.
const globalForDb = globalThis as unknown as { __devbriefDbClient?: ReturnType<typeof postgres> };

// In local development use Neon's direct endpoint. The app owns one cached
// client, so it does not need PgBouncer; bypassing it avoids the connection
// resets observed during the OAuth callback. Deployments retain the pooled
// endpoint, where many short-lived application instances need pooling.
// DEVBRIEF_LOCAL=1 (set by start.ps1) applies the same rule when the dashboard
// runs as a production build on your own computer.
const useDirectEndpoint =
    process.env.NODE_ENV === "development" || process.env.DEVBRIEF_LOCAL === "1";
const databaseUrl = useDirectEndpoint
    ? process.env.DATABASE_URL!.replace(/-pooler(?=\.)/, "")
    : process.env.DATABASE_URL!;

const client = globalForDb.__devbriefDbClient ?? postgres(databaseUrl, {
    ssl: "require",
    // Neon can suspend an idle compute (five minutes by default). Keeping an
    // application-side socket open across that period means its first reuse
    // can fail with ECONNRESET before postgres.js has a chance to reconnect.
    // Close idle client sockets well before then; the pooler will cheaply open
    // a new one for the next request.
    // Opening a new connection to Neon costs ~2.5 s (TLS + auth), while a
    // query on an open one costs one network round trip. Keep sockets open
    // for 4 minutes, still under Neon's 5-minute suspend, so pages do not pay
    // the connect cost on every visit. `warmDbPool` keeps them warm.
    idle_timeout: 240,
    // Keep postgres.js's default prepared statements: a repeated query then
    // costs one network round trip. (`prepare: false` makes every query with
    // parameters cost two, which was measured at 600 ms instead of 300 ms.)
    // Belt-and-suspenders against the recurring intermittent
    // "password authentication failed" (28P01) errors seen against Neon's
    // pooler after long dev sessions. Neon's own docs list postgres.js as
    // needing this explicit `ssl` option (not just `sslmode=require` in the
    // URL) for reliable Server Name Indication (SNI) support, which Neon's
    // proxy relies on to route connections to the correct compute — see
    // https://neon.tech/docs/connect/connection-errors#password-authentication-failed-for-user
    max_lifetime: 60 * 10, // force reconnect every 10 min rather than postgres.js's default 30-60min window, so a stale/misrouted connection self-heals faster
});

// Drizzle sends every query through `client.unsafe(...)`, which postgres.js
// never prepares by default, so each query paid two network round trips
// (describe, then run: ~600 ms to the hosted database). Preparing them lets a
// repeated query run in one round trip (~300 ms). Only done on the direct
// endpoint: Neon's pooled endpoint is the one used when deployed.
if (useDirectEndpoint) {
    const unsafe = client.unsafe.bind(client);
    client.unsafe = ((query: string, args?: unknown[], options?: Record<string, unknown>) =>
        unsafe(query, args as never, { prepare: true, ...options })) as typeof client.unsafe;
}

// Share one client (and its warm connections) across every bundle in the
// process. In a production build, the server start-up hook and each page are
// separate module instances; without this each would open its own pool.
globalForDb.__devbriefDbClient = client;

export const db = drizzle(client);

/**
 * Opens `connections` database connections in parallel, so the first page
 * load does not pay ~2.5 s per new connection, and so several queries can run
 * at the same time. Never throws: warming is only an optimization.
 */
export async function warmDbPool(connections = 4): Promise<void> {
    try {
        await Promise.all(
            Array.from({ length: connections }, () => client`select 1`),
        );
    } catch {
        // The first real query will report any actual connection problem.
    }
}
