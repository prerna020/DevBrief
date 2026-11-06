FROM oven/bun:1.3-slim AS base
WORKDIR /repo

# Copy only manifests first for layer caching — this layer only invalidates
# when a package.json or the lockfile changes, not on every source edit.
COPY package.json bun.lock ./
COPY apps/github-app/package.json apps/github-app/package.json
COPY apps/worker/package.json apps/worker/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/db/package.json packages/db/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/config/package.json packages/config/package.json

RUN bun install --frozen-lockfile

# Now bring in the source this service actually needs at runtime.
COPY apps/github-app apps/github-app
COPY packages/db packages/db
COPY packages/shared-types packages/shared-types

WORKDIR /repo/apps/github-app
ENV NODE_ENV=production
EXPOSE 3000

CMD ["bunx", "--bun", "probot", "run", "./src/index.ts"]