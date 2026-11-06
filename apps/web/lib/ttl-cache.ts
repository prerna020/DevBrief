/**
 * Tiny in-memory cache for dashboard data. Every database query costs a
 * network round trip (~300 ms to the hosted database), so repeat visits and
 * back-and-forth navigation reuse a result for a few seconds instead of
 * re-querying. Entries live in this server process only.
 */
type Entry = { expires: number; value: Promise<unknown> };

const store = (globalThis as unknown as { __devbriefTtl?: Map<string, Entry> }).__devbriefTtl ?? new Map<string, Entry>();
(globalThis as unknown as { __devbriefTtl?: Map<string, Entry> }).__devbriefTtl = store;

export function cached<T>(key: string, ttlMs: number, load: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const hit = store.get(key);
  if (hit && hit.expires > now) return hit.value as Promise<T>;

  const value = load();
  store.set(key, { expires: now + ttlMs, value });
  // Do not keep failures: the next call should try again.
  value.catch(() => {
    if (store.get(key)?.value === value) store.delete(key);
  });
  return value;
}

/** Drops every cached entry whose key starts with `prefix` (e.g. after a write). */
export function invalidate(prefix: string): void {
  for (const key of store.keys()) {
    if (key.startsWith(prefix)) store.delete(key);
  }
}
