import os, json, asyncpg, asyncio
from dotenv import load_dotenv
load_dotenv()

async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Insert team and repo
    await conn.execute("INSERT INTO teams (id, name) VALUES (1, 'Acme Corp') ON CONFLICT DO NOTHING")
    repo_id = await conn.fetchval("INSERT INTO repos (name, owner) VALUES ($1, $2) RETURNING id", 'demo-repo', 'new-coder20')
    
    # Insert a fake review
    review_id = await conn.fetchval("""
        INSERT INTO reviews (team_id, repo_id, pull_number, developer_login, head_sha, prompt_tokens, completion_tokens, estimated_cost_usd)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
    """, 1, repo_id, 42, 'new-coder20', 'abc123def456', 1500, 500, 0.05)
    
    # Insert some fake issues
    issues = [
        ('main.py', 'security', 'high', False, 'sql-injection', 'SQL Injection vulnerability', 'Use parameterized queries', 'Fix it'),
        ('utils.py', 'bug', 'medium', False, 'null-pointer', 'Possible NoneType error', 'Check for None', 'Add if x is not None'),
        ('utils.py', 'style', 'low', False, 'naming', 'Bad variable name', 'Rename to x', 'Rename to x')
    ]
    for issue in issues:
        await conn.execute("""
            INSERT INTO review_issues (review_id, file, category, severity, is_custom_rule_violation, matched_rule, issue, why, fix)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, review_id, *issue)
        
    print('Mock data inserted successfully! The dashboard should now show this data.')
    await conn.close()

asyncio.run(main())
