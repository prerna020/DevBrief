CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE repos (
    id SERIAL PRIMARY KEY,
    team_id INT REFERENCES teams(id),
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(owner, name)
);

CREATE TABLE rules (
    id SERIAL PRIMARY KEY,
    team_id INT REFERENCES teams(id),
    rule_text TEXT NOT NULL,
    category TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);
