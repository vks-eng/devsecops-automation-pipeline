"""Start a throw-away embedded PostgreSQL (via the `pgserver` dev dependency) and print its URL.

For local development without Docker only. Usage:

    python scripts/dev_postgres.py [data_dir]

Keeps running until Ctrl+C. Export the printed DATABASE_URL in another shell.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pgserver
import psycopg2


def main() -> None:
    data_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".pgdata").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    server = pgserver.get_server(str(data_dir), cleanup_mode="stop")
    conn = psycopg2.connect(server.get_uri())
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'devsecops'")
        if cur.fetchone() is None:
            cur.execute("CREATE DATABASE devsecops")
    conn.close()
    uri = server.get_uri("devsecops").replace("postgresql://", "postgresql+psycopg2://", 1)
    print(f"DATABASE_URL={uri}", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
