CREATE TABLE IF NOT EXISTS review_jobs (
    id SERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'pending',
    attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_teams (
    user_id TEXT NOT NULL,
    team_id INT REFERENCES teams(id),
    PRIMARY KEY (user_id, team_id)
);

ALTER TABLE reviews 
ADD COLUMN IF NOT EXISTS prompt_tokens INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS completion_tokens INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC DEFAULT 0;
