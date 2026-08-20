import sqlite3
import aiosqlite
import os
import asyncio
from contextlib import asynccontextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "bluebyte.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_db_sync()
        return cls._instance

    def _init_db_sync(self):
        """Initialize the database synchronously if it doesn't exist."""
        if not os.path.exists(DB_PATH):
            with sqlite3.connect(DB_PATH) as conn:
                if os.path.exists(SCHEMA_PATH):
                    with open(SCHEMA_PATH, 'r') as f:
                        schema = f.read()
                        conn.executescript(schema)
                conn.commit()

    @asynccontextmanager
    async def get_connection(self):
        """Async context manager for db connection."""
        conn = await aiosqlite.connect(DB_PATH)
        try:
            conn.row_factory = aiosqlite.Row
            yield conn
        finally:
            await conn.close()

db_manager = DatabaseManager()

@asynccontextmanager
async def get_db():
    async with db_manager.get_connection() as conn:
        yield conn

async def init_db():
    """Initialize the database — creates tables from schema.sql if DB doesn't exist."""
    # Force singleton creation which triggers schema init
    _ = DatabaseManager()
    # Also ensure tables exist via async connection
    async with get_db() as conn:
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, 'r') as f:
                schema = f.read()
            await conn.executescript(schema)
            await conn.commit()
