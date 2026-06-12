"""
Extractor: reads billing CSV files and normalizes column names into a
consistent internal schema regardless of source format.
"""

import pandas as pd
from pathlib import Path


COLUMN_MAP = {
    # AWS-style aliases
    "UsageStartDate": "date",
    "ProductName": "service",
    "UsageRegion": "region",
    "ResourceId": "resource_id",
    "UsageType": "usage_type",
    "UsageQuantity": "usage_amount",
    "UnblendedCost": "cost",
    "Currency": "currency",
    # Generic / simulated
    "date": "date",
    "service": "service",
    "region": "region",
    "resource_id": "resource_id",
    "usage_type": "usage_type",
    "usage_amount": "usage_amount",
    "cost": "cost",
    "currency": "currency",
    "tag_env": "tag_env",
    "tag_team": "tag_team",
}

REQUIRED_COLUMNS = {"date", "service", "region", "cost"}


def extract(path: str | Path) -> pd.DataFrame:
    """Read a billing CSV and return a normalized DataFrame."""
    df = pd.read_csv(path)
    df = df.rename(columns={c: COLUMN_MAP.get(c, c) for c in df.columns})

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").fillna(0.0)
    df["currency"] = df.get("currency", pd.Series(["USD"] * len(df)))
    df["tag_env"] = df.get("tag_env", pd.Series(["unknown"] * len(df)))
    df["tag_team"] = df.get("tag_team", pd.Series(["unknown"] * len(df)))

    return df
