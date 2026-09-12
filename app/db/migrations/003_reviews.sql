CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    team_id INT REFERENCES teams(id),
    repo_id INT REFERENCES repos(id),
    pull_number INT,
    developer_login TEXT,
    head_sha TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE review_issues (
    id SERIAL PRIMARY KEY,
    review_id INT REFERENCES reviews(id),
    file TEXT,
    category TEXT,
    severity TEXT,
    is_custom_rule_violation BOOLEAN,
    matched_rule TEXT,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
