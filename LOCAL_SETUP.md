# Running DevBrief on your computer (free)

## What you get

You open a pull request on GitHub. A minute later DevBrief comments on it:

> **[critical]** `user_id` is put straight into the SQL query.
>
> This allows SQL injection. Use a parameterized query instead.

The comment sits on the exact line of the pull request. The dashboard also lists every review.

## How it works

```
You open a PR on GitHub
        |
        v
GitHub sends a message ("webhook") --> smee.io (free relay, so GitHub can reach your laptop)
        |
        v
GitHub receiver (port 3002) puts a job in Redis (the queue)
        |
        v
Review worker takes the job, downloads the PR diff
        |
        v
AI engine (port 8000) sends the diff to Gemini/Groq with YOUR free key
        |
        v
Worker posts the comments on the PR and saves the review in the database
        |
        v
Dashboard (port 3000) shows it
```

Your computer must be on, with DevBrief running, for reviews to happen. Nothing is hosted for you.

One GitHub App does two jobs: it is the bot that comments on PRs, and it is also the
"Sign in with GitHub" button on the dashboard. You do not need a separate OAuth App.

## What you need (all free)

| What | Why | Where |
| --- | --- | --- |
| Neon account | the database | https://neon.tech |
| Docker Desktop | runs Redis (the queue) | already installed on this PC |
| Gemini or Groq key | the AI that reviews | step 4 |
| GitHub account | owns the app, has a repo to test | github.com |

No Pinecone key is needed. Pinecone is an optional extra that lets reviews also look at other
files of the repo. Without it, reviews still work.

All commands run in PowerShell from the repo folder (the one containing `setup.ps1`).

## Step 1: Database and keys (once)

1. Sign up at https://neon.tech and create a project.
2. Click **Connect** and copy the connection string (starts with `postgresql://`).
3. Run:

```powershell
bun install
uv sync --all-packages
.\setup.ps1
```

Paste the Neon string when asked. The script generates the secret keys, writes `.env` and
`apps\web\.env.local`, and creates the database tables.

## Step 2: Redis and the GitHub App (once)

```powershell
.\setup-github-app.ps1
```

It starts Docker Desktop and Redis if needed (this can take a minute or two the first time).
Then your browser opens a page. Do this:

1. Click **Register GitHub App**.
2. On GitHub, click **Create GitHub App**. (If the name is taken, type a different one.)
3. GitHub then shows an **Install** page. **Close that tab** without installing.
   You will install from the DevBrief dashboard in step 5, which links the install to your account.

The script waits, then saves the app's credentials into `.env` and `apps\web\.env.local`.

## Step 3: Start DevBrief (every time you want reviews)

```powershell
.\start.ps1
```

Four windows open: AI engine, dashboard, GitHub receiver, review worker. Keep them open.
The first start (and any start after the code changed) builds the dashboard first, which takes about a minute.
Wait until the dashboard window says `Ready`. To work on the dashboard code with live reload, use `.\start.ps1 -Dev` instead.

To stop, close the four windows. Redis keeps running in Docker; stop it with `docker compose stop redis`.

## Step 4: Add your free AI key (once)

1. Open http://localhost:3000 and click **Start reviewing**. Sign in with GitHub (approve the app).
2. Go to **Settings > LLM Provider** and get a key:
   - **Google Gemini**: https://aistudio.google.com/apikey (free, no card). Default model `gemini-flash-lite-latest`.
   - **Groq**: https://console.groq.com/keys (free tier). Default model `openai/gpt-oss-20b`.
3. Paste it and click **Connect provider**. DevBrief sends one test request, so a wrong key or model shows an error immediately.

## Step 5: Install the app on a repo (once per repo)

1. In the dashboard, click **Install DevBrief on GitHub**.
2. Choose **Only select repositories**, pick a test repo, click **Install**.
3. You land back on the dashboard with "GitHub App connected". (Keep `.\start.ps1` running while you do this. If GitHub shows "refused to connect", see Troubleshooting.)

## Step 6: Try it

1. In that repo, make a branch and add code with an obvious bug, for example in a Python file:
   ```python
   def get_user(db, user_id):
       return db.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()
   ```
2. Push the branch and open a pull request.
3. Within a minute or two DevBrief comments on the PR. The review window of the worker shows progress.
4. Refresh the dashboard: the review appears under **Recent activity**.

Optional: add a `.devbrief.yml` file at the repo root to tune reviews (see http://localhost:3000/docs#devbrief-yml).

## Optional: the terminal command

Without GitHub, you can review local changes from a terminal:

```powershell
uv tool install --editable ./apps/cli
```

Create an API key in the dashboard (**API Keys**), then in any git repo:

```powershell
devbrief auth
git add .
devbrief review --staged
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `running scripts is disabled` | Run `powershell -ExecutionPolicy Bypass -File .\setup.ps1` (same for the other scripts). |
| Docker or Redis will not start | Open Docker Desktop yourself and wait until it says it is running, then rerun. Or make a free database at https://upstash.com and put its `rediss://...` URL in `REDIS_URL` in `.env`. |
| Sign-in returns to the login page | The GitHub App's callback URL must be `http://localhost:3000/api/auth/callback/github`. Check it at https://github.com/settings/apps. |
| "localhost refused to connect" after clicking Install on GitHub | DevBrief is not running. Run `.\start.ps1`, wait for the dashboard window to say `Ready`, then open http://localhost:3000/dashboard. It finds the install by itself. |
| Dashboard says `install_error=not_found` | Open the dashboard again; it asks GitHub which installs you have and records them. |
| PR gets no comment | Check the windows. The receiver window should log `POST /api/github/webhooks 200`. If not, the smee relay is down: open the smee URL in `apps\github-app\.env` (`WEBHOOK_PROXY_URL`) in a browser to see the deliveries. |
| PR gets a comment "DevBrief review failed: No LLM provider configured" | Do step 4 while signed in with the same GitHub account that did step 5. |
| PR gets a comment about a rate limit or bad model | Free AI tiers have per-minute and per-day limits. Wait and push another commit, or change the model in Settings. |
| PR gets no inline comments | DevBrief only comments when it finds a real problem on a changed line. Try the bug example above. |
| Port already in use | Close old DevBrief windows. Ports used: 3000, 3002, 8000, 6379. |

## Review metrics and reliability

Every review records how long the model call took, the tokens used, an estimated cost (at list
price), how many attempts it needed, and whether it succeeded. Print the summary any time:

```powershell
.\.venv\Scripts\python.exe services\ai-engine\scripts\metrics_report.py
.\.venv\Scripts\python.exe services\ai-engine\scripts\metrics_report.py --days 7
```

Prices live in `services/ai-engine/app/metrics.py`; a model that is not listed shows no cost.

When the AI provider has a hiccup, DevBrief retries instead of failing: up to 3 retries (waiting
1, 2, then 4 seconds) for timeouts, rate limits (429), server errors (5xx) and network errors, and
one retry when the model returns a malformed review. If it still fails, the PR gets a short
"DevBrief review failed" comment with the reason, and the worker keeps running. Retries show up in
the AI engine window as `model call failed (...); retry 1/3`.
