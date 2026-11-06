import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  // Queue of results returned by db.select()...limit(1) in call order.
  selectResults: [] as unknown[],
  insertCalls: [] as { table: unknown; values: unknown }[],
}));

vi.mock("@devbrief/db", () => ({
  db: {
    select: () => ({
      from: () => ({
        where: () => ({
          limit: () => {
            const next = mocks.selectResults.shift();
            return Promise.resolve(next ?? []);
          },
        }),
      }),
    }),
    insert: (table: unknown) => ({
      values: (values: unknown) => {
        mocks.insertCalls.push({ table, values });
        return { onConflictDoNothing: () => Promise.resolve() };
      },
    }),
  },
  accounts: { provider: "github", userId: "user_id" },
  installations: { id: "id", githubInstallationId: "github_installation_id" },
  repos: { githubRepoId: "github_repo_id" },
  userInstallations: { userId: "user_id", installationId: "installation_id" },
}));

import { reconcileUserInstallations } from "@/lib/github-reconciliation";

describe("reconcileUserInstallations", () => {
  beforeEach(() => {
    mocks.selectResults = [];
    mocks.insertCalls = [];
    vi.unstubAllGlobals();
  });

  it("does nothing when the user has no linked github account", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    // First select (account lookup) returns no row.
    mocks.selectResults.push([]);

    await reconcileUserInstallations("u-1");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("backfills user_installations for known installations", async () => {
    // account row: valid, unexpired token
    mocks.selectResults.push([
      { accessToken: "tok", refreshToken: null, expiresAt: Math.floor(Date.now() / 1000) + 3600 },
    ]);
    // github API returns two installations; only one is known to us.
    mocks.selectResults.push([{ id: "inst-1" }]); // first gh id 100 exists
    mocks.selectResults.push([]); // second gh id 200 unknown

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        installations: [
          { id: 100, account: { login: "org-a" } },
          { id: 200, account: { login: "org-b" } },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchSpy);

    await reconcileUserInstallations("u-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://api.github.com/user/installations",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer tok" }) }),
    );
    // The known installation gets a link row.
    expect(mocks.insertCalls[0]!.values).toEqual({ userId: "u-1", installationId: "inst-1" });
    // The unknown one is recorded (its webhook never arrived), but with no
    // row to re-read in this mock it is not linked.
    expect(mocks.insertCalls).toHaveLength(2);
    expect(mocks.insertCalls[1]!.values).toEqual({ githubInstallationId: 200, accountLogin: "org-b" });
  });

  it("records a missed installation with its repos, then links it", async () => {
    mocks.selectResults.push([
      { accessToken: "tok", refreshToken: null, expiresAt: Math.floor(Date.now() / 1000) + 3600 },
    ]);
    mocks.selectResults.push([]); // installation 300 not known yet
    mocks.selectResults.push([{ id: "inst-3" }]); // found after being recorded

    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ installations: [{ id: 300, account: { login: "me" } }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ repositories: [{ id: 7, full_name: "me/demo" }] }),
      });
    vi.stubGlobal("fetch", fetchSpy);

    await reconcileUserInstallations("u-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://api.github.com/user/installations/300/repositories?per_page=100",
      expect.anything(),
    );
    expect(mocks.insertCalls.map((c) => c.values)).toEqual([
      { githubInstallationId: 300, accountLogin: "me" },
      { installationId: "inst-3", githubRepoId: 7, fullName: "me/demo" },
      { userId: "u-1", installationId: "inst-3" },
    ]);
  });

  it("skips the github call when the refresh fails", async () => {
    // account row: expired token + refresh token
    mocks.selectResults.push([
      { accessToken: "old", refreshToken: "rt", expiresAt: Math.floor(Date.now() / 1000) - 100 },
    ]);
    const fetchSpy = vi.fn().mockResolvedValue({ ok: false });
    vi.stubGlobal("fetch", fetchSpy);

    await reconcileUserInstallations("u-1");
    // Only the token refresh call is attempted; no installations call.
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(mocks.insertCalls).toHaveLength(0);
  });
});