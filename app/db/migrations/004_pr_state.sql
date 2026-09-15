CREATE TABLE pr_state (
    repo_id INT REFERENCES repos(id),
    pull_number INT,
    last_reviewed_sha TEXT NOT NULL,
    PRIMARY KEY (repo_id, pull_number)
);
