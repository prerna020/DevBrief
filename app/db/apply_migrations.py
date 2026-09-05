from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg


async def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    connection = await asyncpg.connect(database_url)
    try:
        for migration in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
            await connection.execute(migration.read_text(encoding="utf-8"))
            print(f"Applied {migration.name}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())

