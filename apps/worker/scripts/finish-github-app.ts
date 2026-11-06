// Run by scripts\setup-github-app.ps1 after Probot's setup wizard has created
// the GitHub App and written its credentials to apps/github-app/.env.
//
// This copies those credentials to the places that need them:
//   - root .env           -> worker (APP_ID, PRIVATE_KEY, REDIS_URL, ...)
//   - apps/web/.env.local -> dashboard sign-in + "Install on GitHub" button
// The same GitHub App signs users in to the dashboard, so there is no
// separate OAuth App to create.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { parseEnv } from "node:util";
import { Octokit } from "octokit";
import { createAppAuth } from "@octokit/auth-app";

const root = path.resolve(import.meta.dir, "../../..");
const appEnvPath = path.join(root, "apps", "github-app", ".env");
const rootEnvPath = path.join(root, ".env");
const webEnvPath = path.join(root, "apps", "web", ".env.local");

function readEnv(file: string): Record<string, string> {
  return existsSync(file) ? parseEnv(readFileSync(file, "utf8")) : {};
}

function upsertEnv(file: string, values: Record<string, string>): void {
  let text = existsSync(file) ? readFileSync(file, "utf8") : "";
  for (const [key, value] of Object.entries(values)) {
    const line = `${key}=${value}`;
    const pattern = new RegExp(`^${key}=.*$`, "m");
    if (pattern.test(text)) {
      // Function replacer so "$" in a value is never treated as a back-reference.
      text = text.replace(pattern, () => line);
    } else {
      text = text.replace(/\s*$/, "") + (text.trim() ? "\n" : "") + line + "\n";
    }
  }
  writeFileSync(file, text);
}

const app = readEnv(appEnvPath);
const missing = ["APP_ID", "PRIVATE_KEY", "WEBHOOK_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"].filter(
  (k) => !app[k],
);
if (missing.length > 0) {
  console.error(
    `apps/github-app/.env is missing ${missing.join(", ")}. ` +
      "The GitHub App was not created yet; run scripts\\setup-github-app.ps1 again.",
  );
  process.exit(1);
}

const privateKey = app.PRIVATE_KEY!.replace(/\\n/g, "\n");

// Ask GitHub for the app's slug (the name used in github.com/apps/<slug>).
const octokit = new Octokit({
  authStrategy: createAppAuth,
  auth: { appId: app.APP_ID, privateKey },
});
const { data: appInfo } = await octokit.request("GET /app");
if (!appInfo?.slug) {
  console.error("GitHub did not return the app slug. Check APP_ID and PRIVATE_KEY.");
  process.exit(1);
}

const rootEnv = readEnv(rootEnvPath);
upsertEnv(rootEnvPath, {
  APP_ID: app.APP_ID!,
  // One line with escaped newlines: works for dotenv and for the worker's own un-escaping.
  PRIVATE_KEY: `"${privateKey.trim().replace(/\n/g, "\\n")}"`,
  WEBHOOK_SECRET: app.WEBHOOK_SECRET!,
  REDIS_URL: rootEnv.REDIS_URL || "redis://localhost:6379",
  AI_ENGINE_URL: "http://localhost:8000",
  // The sandbox clones repos with git+chmod and lints Python. It is optional
  // and needs Linux tools, so it stays off for local use.
  SANDBOX_ENABLED: "false",
});

upsertEnv(webEnvPath, {
  AUTH_GITHUB_ID: app.GITHUB_CLIENT_ID!,
  AUTH_GITHUB_SECRET: app.GITHUB_CLIENT_SECRET!,
  GITHUB_APP_SLUG: appInfo.slug,
});

console.log(`GitHub App "${appInfo.name}" is ready (slug: ${appInfo.slug}).`);
console.log(`Install it on a repo at: https://github.com/apps/${appInfo.slug}/installations/new`);
