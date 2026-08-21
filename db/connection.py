"""
connection.py — Postgres/asyncpg replacement for the aiosqlite version.

Keeps the same public interface the rest of the app already imports
(`get_db`, `db_manager`, `init_db`) so server/api routes and
websocket_manager.py don't need to change their import lines — only
how each connection behaves under the hood changes (pooled, dict-like
Record rows via asyncpg instead of aiosqlite.Row).
"""

import os
import asyncpg
from contextlib import asynccontextmanager

# Set BLUEBYTE_DATABASE_URL in your environment / .env file. Matches the
# credentials in docker-compose.db.yml by default for local dev.
DATABASE_URL = os.environ.get(
    "BLUEBYTE_DATABASE_URL",
    "postgresql://bluebyte:bluebyte_dev@localhost:5432/bluebyte",
)


class DatabaseManager:
    """Holds a single asyncpg connection pool for the app's lifetime.
    Call `await db_manager.connect()` once at startup (e.g. FastAPI
    lifespan/startup event) before any route uses get_db()."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.pool: asyncpg.Pool | None = None
        return cls._instance

    async def connect(self, dsn: str = DATABASE_URL, min_size: int = 2, max_size: int = 10):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size)
        return self.pool

    async def disconnect(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def get_connection(self):
        if self.pool is None:
            await self.connect()
        async with self.pool.acquire() as conn:
            yield conn


db_manager = DatabaseManager()


@asynccontextmanager
async def get_db():
    """Usage unchanged from the SQLite version:

        async with get_db() as conn:
            rows = await conn.fetch("SELECT * FROM buoy_readings WHERE sensor_id = $1", sid)
    """
    async with db_manager.get_connection() as conn:
        yield conn


async def init_db():
    """Call once at app startup. Establishes the pool; schema itself is
    applied via schema_postgis.sql + schema_postgis_addendum.sql at
    container init (see docker-compose.db.yml), not from here — running
    DDL from app startup code is avoided so migrations stay explicit and
    reviewable rather than implicit side effects of booting the API."""
    await db_manager.connect()