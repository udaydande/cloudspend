"""
Loader: writes normalized billing data to SQLite via SQLAlchemy.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


DEFAULT_DB = Path(__file__).parents[2] / "data" / "cloudspend.db"


def get_engine(db_path: str | Path = DEFAULT_DB):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def init_schema(engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS billing_records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        DATE NOT NULL,
                service     TEXT NOT NULL,
                region      TEXT,
                resource_id TEXT,
                usage_type  TEXT,
                usage_amount REAL,
                cost        REAL NOT NULL,
                currency    TEXT DEFAULT 'USD',
                tag_env     TEXT,
                tag_team    TEXT,
                loaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_billing_date_service
            ON billing_records(date, service)
        """))
        conn.commit()


def load(df: pd.DataFrame, engine, if_exists: str = "append") -> int:
    """Write records to the billing_records table. Returns rows written."""
    cols = [
        "date", "service", "region", "resource_id",
        "usage_type", "usage_amount", "cost", "currency",
        "tag_env", "tag_team",
    ]
    subset = df[[c for c in cols if c in df.columns]]
    subset.to_sql("billing_records", engine, if_exists=if_exists, index=False)
    return len(subset)
