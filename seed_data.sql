-- Seed data for DevBrief dashboard demo
-- Creates team, repo, reviews, and review_issues so the dashboard has data to display

-- Team and repo
INSERT INTO teams (id, name) VALUES (1, 'DevBrief Team') ON CONFLICT DO NOTHING;
SELECT setval('teams_id_seq', 1, true);

INSERT INTO repos (id, team_id, owner, name) VALUES (1, 1, 'prerna020', 'DevBrief') ON CONFLICT DO NOTHING;
SELECT setval('repos_id_seq', 1, true);

-- Reviews spread over the last 14 days with realistic data
INSERT INTO reviews (team_id, repo_id, pull_number, developer_login, head_sha, prompt_tokens, completion_tokens, estimated_cost_usd, created_at) VALUES
  (1, 1, 10, 'prerna020',   'aaa1111', 1200, 450, 0.00045, now() - interval '13 days'),
  (1, 1, 11, 'alex-dev',    'bbb2222', 2100, 800, 0.00080, now() - interval '12 days'),
  (1, 1, 12, 'prerna020',   'ccc3333', 1800, 600, 0.00063, now() - interval '11 days'),
  (1, 1, 14, 'sam-coder',   'ddd4444', 3200, 1100, 0.00113, now() - interval '10 days'),
  (1, 1, 15, 'alex-dev',    'eee5555', 900,  350, 0.00035, now() - interval '9 days'),
  (1, 1, 16, 'prerna020',   'fff6666', 2500, 900, 0.00090, now() - interval '8 days'),
  (1, 1, 17, 'jordan-code', 'ggg7777', 1600, 500, 0.00052, now() - interval '7 days'),
  (1, 1, 18, 'sam-coder',   'hhh8888', 2800, 950, 0.00098, now() - interval '6 days'),
  (1, 1, 19, 'prerna020',   'iii9999', 1400, 420, 0.00046, now() - interval '5 days'),
  (1, 1, 20, 'alex-dev',    'jjjaaaa', 3100, 1050, 0.00110, now() - interval '4 days'),
  (1, 1, 21, 'jordan-code', 'kkkbbbb', 2200, 750, 0.00078, now() - interval '3 days'),
  (1, 1, 22, 'prerna020',   'lllcccc', 1900, 680, 0.00071, now() - interval '2 days'),
  (1, 1, 23, 'sam-coder',   'mmmdddd', 2600, 870, 0.00092, now() - interval '1 day'),
  (1, 1, 24, 'alex-dev',    'nnneeee', 1500, 520, 0.00053, now() - interval '6 hours');

-- Review issues linked to the reviews above
-- Using currval approach: we need the review IDs. Since we just inserted 14 reviews starting from id=1:
INSERT INTO review_issues (review_id, file, category, severity, is_custom_rule_violation, matched_rule, issue, why, fix, created_at) VALUES
  -- Review 1 (PR #10, 13 days ago)
  (1, 'src/auth/login.py', 'Security', 'high', false, NULL, 'SQL injection vulnerability in user query', 'User input is concatenated directly into SQL', 'Use parameterized queries', now() - interval '13 days'),
  (1, 'src/auth/login.py', 'Error Handling', 'medium', false, NULL, 'Missing exception handler for database errors', 'Unhandled exceptions crash the server', 'Wrap in try/except with proper logging', now() - interval '13 days'),
  -- Review 2 (PR #11, 12 days ago)
  (2, 'src/api/routes.py', 'Performance', 'medium', false, NULL, 'N+1 query in list endpoint', 'Each item triggers a separate DB query', 'Use eager loading or batch query', now() - interval '12 days'),
  (2, 'src/api/routes.py', 'Code Style', 'low', true, 'Use type hints', 'Missing type annotations on function parameters', 'Type hints improve readability and IDE support', 'Add type hints to all parameters', now() - interval '12 days'),
  (2, 'src/models/user.py', 'Security', 'high', false, NULL, 'Password stored in plain text', 'Plain text passwords are a critical security risk', 'Use bcrypt or argon2 for password hashing', now() - interval '12 days'),
  -- Review 3 (PR #12, 11 days ago)
  (3, 'src/utils/parser.py', 'Bug Risk', 'high', false, NULL, 'Off-by-one error in loop boundary', 'Last element is skipped during iteration', 'Use <= instead of < in loop condition', now() - interval '11 days'),
  -- Review 4 (PR #14, 10 days ago)
  (4, 'src/services/payment.py', 'Security', 'high', false, NULL, 'API key hardcoded in source', 'Secrets in code can be leaked via version control', 'Move to environment variables', now() - interval '10 days'),
  (4, 'src/services/payment.py', 'Error Handling', 'medium', false, NULL, 'No retry logic for payment API calls', 'Transient failures cause payment failures', 'Add exponential backoff retry', now() - interval '10 days'),
  (4, 'src/services/email.py', 'Performance', 'low', false, NULL, 'Synchronous email sending blocks request', 'Users wait for email to be sent', 'Use async task queue', now() - interval '10 days'),
  (4, 'src/services/email.py', 'Code Style', 'low', true, 'Max function length 50 lines', 'Function exceeds 80 lines', 'Long functions are hard to test and maintain', 'Split into smaller helper functions', now() - interval '10 days'),
  -- Review 5 (PR #15, 9 days ago)
  (5, 'src/api/middleware.py', 'Security', 'medium', false, NULL, 'CORS allows all origins in production', 'Any website can make requests to your API', 'Restrict to known frontend domains', now() - interval '9 days'),
  -- Review 6 (PR #16, 8 days ago)
  (6, 'src/db/migrations.py', 'Bug Risk', 'high', false, NULL, 'Migration not wrapped in transaction', 'Partial migration leaves DB in broken state', 'Wrap migration steps in a transaction', now() - interval '8 days'),
  (6, 'src/db/connection.py', 'Performance', 'medium', false, NULL, 'New DB connection per request', 'Connection creation is expensive', 'Use connection pooling', now() - interval '8 days'),
  -- Review 7 (PR #17, 7 days ago)
  (7, 'src/utils/cache.py', 'Bug Risk', 'medium', false, NULL, 'Cache key collision possible', 'Different inputs may produce same cache key', 'Include all relevant parameters in cache key', now() - interval '7 days'),
  (7, 'src/utils/cache.py', 'Performance', 'low', false, NULL, 'No TTL set on cache entries', 'Stale data served indefinitely', 'Add reasonable TTL based on data freshness needs', now() - interval '7 days'),
  -- Review 8 (PR #18, 6 days ago)
  (8, 'src/api/serializers.py', 'Security', 'high', false, NULL, 'Internal user IDs exposed in API response', 'Sequential IDs reveal user count and are enumerable', 'Use UUIDs or opaque identifiers', now() - interval '6 days'),
  (8, 'src/api/serializers.py', 'Code Style', 'low', true, 'Use type hints', 'Missing return type annotation', 'Return types help with documentation and IDE support', 'Add return type hints', now() - interval '6 days'),
  -- Review 9 (PR #19, 5 days ago)
  (9, 'src/config/settings.py', 'Error Handling', 'medium', false, NULL, 'Missing validation for environment variables', 'App crashes with cryptic error if env var missing', 'Validate required env vars at startup with clear messages', now() - interval '5 days'),
  -- Review 10 (PR #20, 4 days ago)
  (10, 'src/workers/processor.py', 'Bug Risk', 'high', false, NULL, 'Race condition in concurrent job processing', 'Two workers may process the same job', 'Use database-level locking (FOR UPDATE SKIP LOCKED)', now() - interval '4 days'),
  (10, 'src/workers/processor.py', 'Error Handling', 'medium', false, NULL, 'Dead letter queue not implemented', 'Failed jobs retry infinitely', 'Add max retry count and move to dead letter queue', now() - interval '4 days'),
  (10, 'src/workers/scheduler.py', 'Performance', 'low', false, NULL, 'Polling interval too aggressive', 'Unnecessary DB load when no jobs pending', 'Use exponential backoff or LISTEN/NOTIFY', now() - interval '4 days'),
  -- Review 11 (PR #21, 3 days ago)
  (11, 'src/auth/tokens.py', 'Security', 'high', false, NULL, 'JWT token never expires', 'Compromised tokens are valid forever', 'Set reasonable expiration (e.g. 24 hours)', now() - interval '3 days'),
  (11, 'src/auth/tokens.py', 'Security', 'medium', false, NULL, 'Weak JWT signing algorithm', 'HS256 with short secret is brute-forceable', 'Use RS256 or longer secret key', now() - interval '3 days'),
  -- Review 12 (PR #22, 2 days ago)
  (12, 'src/api/uploads.py', 'Security', 'high', false, NULL, 'No file type validation on uploads', 'Malicious files could be uploaded', 'Validate MIME type and file extension', now() - interval '2 days'),
  (12, 'src/api/uploads.py', 'Bug Risk', 'medium', false, NULL, 'Upload size limit not enforced', 'Large uploads can exhaust server memory', 'Add max file size check', now() - interval '2 days'),
  -- Review 13 (PR #23, 1 day ago)
  (13, 'src/services/notification.py', 'Error Handling', 'medium', false, NULL, 'Silent failure when notification service is down', 'Users miss important notifications', 'Add fallback mechanism and alerting', now() - interval '1 day'),
  (13, 'src/services/notification.py', 'Code Style', 'low', true, 'Max function length 50 lines', 'Send function is 95 lines long', 'Hard to understand and test', 'Break into setup, send, and log functions', now() - interval '1 day'),
  (13, 'src/services/webhook.py', 'Performance', 'medium', false, NULL, 'Webhook delivery is synchronous', 'Slow webhook endpoints delay the response', 'Use background task or message queue', now() - interval '1 day'),
  -- Review 14 (PR #24, 6 hours ago)
  (14, 'src/api/graphql.py', 'Security', 'medium', false, NULL, 'No query depth limit on GraphQL', 'Deeply nested queries can DoS the server', 'Add query depth and complexity limits', now() - interval '6 hours'),
  (14, 'src/api/graphql.py', 'Performance', 'low', false, NULL, 'Missing DataLoader for batching', 'N+1 queries in GraphQL resolvers', 'Implement DataLoader pattern', now() - interval '6 hours');
