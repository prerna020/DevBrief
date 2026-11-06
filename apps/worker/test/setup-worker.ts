// The worker module throws at import time unless these are set (it builds a
// real BullMQ worker + Redis connection), so they are provided here. The
// actual connections/network calls are all mocked in the tests.
process.env.INTERNAL_SERVICE_TOKEN = "test-internal-token";
process.env.REDIS_URL = "redis://localhost:6379";
process.env.APP_ID = "12345";
process.env.PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nMIIEvoA\n-----END PRIVATE KEY-----";
// Tests exercise the sandbox path. A developer's real .env (written by setup-github-app.ps1)
// sets SANDBOX_ENABLED=false, which must not change test behavior.
process.env.SANDBOX_ENABLED = "true";
process.env.AI_ENGINE_URL = "http://localhost:8000";
