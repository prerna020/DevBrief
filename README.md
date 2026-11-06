# DevBrief

**DevBrief** is an AI code reviewer for pull requests. When a PR is opened or updated, it
comments on the exact lines where it finds bugs or security problems, and an optional
pass/fail check can block merging on critical findings. A command-line tool reviews local
changes before you push.

DevBrief is **BYOK** (bring your own key): you connect your own Gemini, Groq or OpenRouter
key in the dashboard, so there is no shared LLM bill. Free tiers work.

## Run it

Follow [LOCAL_SETUP.md](LOCAL_SETUP.md). In short:

```powershell
.\setup.ps1              # database + secret keys (once)
.\setup-github-app.ps1   # Redis + GitHub App (once)
.\start.ps1              # start everything
```

## Features

- **GitHub App**: reviews every opened or updated PR with inline comments and an optional
  `DevBrief` check run (`require_check` in `.devbrief.yml`).
- **Dashboard**: reviews, findings by severity (click through to each finding), connected
  repos, API keys, and your AI provider settings.
- **CLI**: `devbrief review --staged` reviews local changes from the terminal.
- **Per-repo config**: a `.devbrief.yml` at the repo root controls ignored paths, minimum
  severity, comment limit and the check run.
- **Optional extras**: repo-wide context through Pinecone, and Python linting through the
  sandbox runner. Reviews work without both.

## How it works

```
GitHub PR event ──► smee.io relay ──► GitHub receiver (apps/github-app)
                                            │
                                            ▼
                                   Redis queue (BullMQ)
                                            │
                                            ▼
                         Review worker (apps/worker): fetches the diff
                                            │
                                            ▼
              AI engine (services/ai-engine): ingest → enrich → review → verify
                                            │
                                            ▼
                   Gemini / Groq / OpenRouter (your key) returns findings
                                            │
                                            ▼
            Worker posts PR comments and saves the review in Postgres (Neon)
                                            │
                                            ▼
                                   Dashboard (apps/web)
```

The review pipeline in the AI engine:

| Step     | Does                                                                          |
| -------- | ----------------------------------------------------------------------------- |
| `ingest` | Parses the diff, applies `.devbrief.yml`, enforces the `MAX_DIFF_CHARS` cap.  |
| `enrich` | Adds repo context from Pinecone when it is configured; otherwise skipped.     |
| `review` | The LLM returns structured findings (severity, file, line, rationale).        |
| `verify` | Drops findings that are not on changed lines or are not backed up by linting. |

## Repository layout

Two workspaces that only talk over HTTP: Bun (TypeScript) and uv (Python).

```
apps/
  web/            Next.js dashboard and sign-in
  github-app/     Probot receiver: verifies webhooks, queues review jobs
  worker/         BullMQ worker: fetches the diff, calls the AI engine, posts comments
  cli/            `devbrief` command-line tool (Python)
services/
  ai-engine/      FastAPI + LangGraph review engine
  sandbox-runner/ Optional Python linter used to back up findings
packages/
  db/             Drizzle schema and migrations (Postgres)
  devbrief-core/  Shared diff parsing and review models (Python)
  shared-types/   Queue job types (TypeScript)
  config/         Shared tsconfig
docker-compose.yml   Redis (and an optional local Postgres)
setup.ps1, setup-github-app.ps1, start.ps1   Local setup and start scripts
render.yaml          Optional config for hosting the backend on Render
```

## Tech stack

Next.js, Probot, BullMQ, Drizzle, FastAPI, LangGraph, Typer, Postgres (Neon), Redis, and
optionally Pinecone.

## Development

```powershell
bun run check-types   # type-check the TypeScript workspaces
bun run lint
bun run test          # TypeScript tests
uv run pytest         # run inside a Python package folder
```

`.\start.ps1 -Dev` runs the dashboard with live reload instead of a production build.
