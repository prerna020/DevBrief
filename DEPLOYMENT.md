# DevBrief Deployment Guide

This guide covers how to deploy the DevBrief backend (API + Worker) and frontend dashboard to production environments.

## Architecture

DevBrief runs as three components in production:
1. **API**: A FastAPI web server that receives GitHub webhook events, verifies signatures, and enqueues background jobs.
2. **Worker**: A background polling process that picks up pending jobs from the queue (`SELECT ... FOR UPDATE SKIP LOCKED`), performs the LLM PR review, and posts comments back to GitHub.
3. **Dashboard (Frontend)**: A web dashboard to view usage statistics and configure team rules.

## Deploying the Backend (API + Worker)

The backend is fully dockerized via a multi-stage `Dockerfile`. You can deploy it to managed container platforms like **Render**, **Fly.io**, or **AWS ECS**.

### Option A: Render
1. Create a new **PostgreSQL** database on Render. Note the internal connection string.
2. Create a **Web Service** for the API:
   - Connect your GitHub repository.
   - Environment: `Docker`
   - Start Command: Automatically uses the `CMD` from `Dockerfile` (`uvicorn app.webhook.server:app ...`)
3. Create a **Background Worker**:
   - Connect the same repository.
   - Environment: `Docker`
   - Start Command: Override to `python -m app.worker`
4. Configure the following environment variables (Platform Secrets) on both services:
   - `DATABASE_URL`: Your PostgreSQL connection string.
   - `GROQ_API_KEY`: Your Groq API key for LLM inference (from console.groq.com).
   - `GROQ_MODEL`: Model name (default: `llama-3.3-70b-versatile`).
   - `GITHUB_APP_ID`: Your GitHub App ID.
   - `GITHUB_APP_PRIVATE_KEY`: Your GitHub App private key.
   - `GITHUB_WEBHOOK_SECRET`: The secret for verifying webhooks.
   - `GITHUB_OAUTH_CLIENT_ID`: The client ID for GitHub OAuth login.
   - `GITHUB_OAUTH_CLIENT_SECRET`: The secret for GitHub OAuth.
   - `JWT_SECRET`: A secure random string for signing session tokens.
   - `AGENTIC_REVIEW_ENABLED`: `true`

### Option B: Fly.io
Use the included `docker-compose.prod.yml` as a reference, or generate a `fly.toml` for the API and another for the worker.
1. Run `fly launch` to setup the API app.
2. Run `fly postgres create` and attach it to your app.
3. Set secrets: `fly secrets set GROQ_API_KEY=... GITHUB_APP_ID=...`
4. Scale the worker process by defining a `[processes]` block in `fly.toml`:
   ```toml
   [processes]
   api = "uvicorn app.webhook.server:app --host 0.0.0.0 --port 8000"
   worker = "python -m app.worker"
   ```

## Deploying the Dashboard (Frontend)

The frontend dashboard (e.g., built with Next.js or React) should be deployed to **Vercel** or **Netlify**.
1. Import your frontend repository into Vercel.
2. Set the `NEXT_PUBLIC_API_URL` environment variable to point to your live backend API URL (e.g., `https://devbrief-api.onrender.com`).
3. Set the GitHub OAuth Redirect URI to point to your live Vercel domain.

## Post-Deployment Checklist

After the API is live, you must update your GitHub App configuration:
1. Go to your **GitHub App Settings** -> **General**.
2. Scroll to the **Webhook** section.
3. Update the **Webhook URL** to your new production API endpoint: `https://your-api-domain.com/webhook`
4. Ensure the Webhook Secret matches the `GITHUB_WEBHOOK_SECRET` environment variable you set in production.
