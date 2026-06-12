"""
Generates 6 months of realistic-looking cloud billing data for demos.
"""

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SERVICES = [
    ("Compute", 0.35),
    ("Storage", 0.15),
    ("Database", 0.20),
    ("Networking", 0.10),
    ("ML/AI", 0.08),
    ("Monitoring", 0.05),
    ("CDN", 0.04),
    ("Serverless", 0.03),
]

REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
ENVS = ["prod", "staging", "dev"]
TEAMS = ["platform", "data", "backend", "frontend"]


def generate(months: int = 6, base_monthly: float = 45_000) -> pd.DataFrame:
    random.seed(42)
    start = date.today().replace(day=1) - timedelta(days=months * 30)
    records = []

    current = start
    while current < date.today():
        month_factor = 1.0 + 0.03 * (current.month - start.month)  # gentle growth
        for service, weight in SERVICES:
            for region in REGIONS:
                daily_base = base_monthly * weight * month_factor / 30 / len(REGIONS)
                noise = random.gauss(1.0, 0.12)
                # occasional spike
                if random.random() < 0.02:
                    noise *= random.uniform(2.5, 4.0)
                cost = round(max(0, daily_base * noise), 4)
                records.append({
                    "date": current.isoformat(),
                    "service": service,
                    "region": region,
                    "resource_id": f"res-{service[:3].lower()}-{region[:3]}-{random.randint(1000,9999)}",
                    "usage_type": f"{service.replace('/', '')}:standard",
                    "usage_amount": round(cost / 0.08, 2),
                    "cost": cost,
                    "currency": "USD",
                    "tag_env": random.choice(ENVS),
                    "tag_team": random.choice(TEAMS),
                })
        current += timedelta(days=1)

    return pd.DataFrame(records)


def write_seed_csv(output_path: str | Path = "data/seed_billing.csv") -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(output_path, index=False)
    print(f"Wrote {len(df):,} records to {output_path}")
    return output_path
