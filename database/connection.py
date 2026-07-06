"""
database/connection.py

Purpose: build the actual connection to Postgres, and provide a
reusable way to get a "session" (a working conversation with the
database) for other scripts to use.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base  # our table definitions from Step 2

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "investigation_platform")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# This connection string format is standard across almost every
# Postgres tool: dialect+driver://user:password@host:port/database
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# The "engine" is SQLAlchemy's core connection object -- it manages a
# pool of actual network connections to Postgres, opening/closing them
# as needed. You typically create ONE engine per application and reuse it.
engine = create_engine(DATABASE_URL)

# sessionmaker() gives us a factory for creating "sessions" -- a session
# is like a workspace/transaction: you make changes (add, update, delete),
# then commit() to save them for real, or rollback() to undo them.
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """Returns a new database session for a script to use."""
    return SessionLocal()


def create_all_tables():
    """
    Looks at every class that inherits from Base (currently just
    Document) and creates the matching table in Postgres, IF it doesn't
    already exist. Safe to run repeatedly -- it won't recreate or wipe
    existing tables.
    """
    Base.metadata.create_all(bind=engine)
    print("Tables created (or already existed).")


if __name__ == "__main__":
    create_all_tables()