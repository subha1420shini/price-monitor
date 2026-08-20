"""
database.py
------------
Sets up the SQLAlchemy engine and session.

DATABASE_URL environment variable controls where data is stored.
- Not set -> falls back to a local SQLite file (fine for local dev).
- Set to a Postgres connection string -> data survives redeploys. On Render,
  create a free PostgreSQL instance and set DATABASE_URL to its
  "Internal Database URL".
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./price_monitor.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()