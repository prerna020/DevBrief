// Runs once when the Next.js server starts.
// Opens database connections up front and keeps them warm: a new connection
// to the remote database takes ~2.5 s, which made the first click on every
// page feel broken.
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  if (!process.env.DATABASE_URL) return;

  const { warmDbPool } = await import("@devbrief/db");
  void warmDbPool();

  // The database suspends itself after ~5 idle minutes and drops idle
  // connections (idle_timeout is 4 min). A ping every 3 min keeps both the
  // connections and the database awake while DevBrief is running.
  const timer = setInterval(() => void warmDbPool(), 3 * 60 * 1000);
  timer.unref();
}
