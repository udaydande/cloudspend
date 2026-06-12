"""
CLI entrypoint for the cloudspend ETL pipeline.

Usage:
    python -m cloudspend.pipeline --seed
    python -m cloudspend.pipeline --input path/to/billing.csv
"""

import argparse
import sys
from pathlib import Path

from cloudspend.extractors.csv_extractor import extract
from cloudspend.extractors.seeder import write_seed_csv
from cloudspend.loaders.sqlite_loader import get_engine, init_schema, load


def main():
    parser = argparse.ArgumentParser(description="cloudspend ETL pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", action="store_true", help="Generate and load demo data")
    group.add_argument("--input", type=str, help="Path to billing CSV file")
    parser.add_argument("--db", type=str, default=None, help="SQLite DB path (default: data/cloudspend.db)")

    args = parser.parse_args()

    engine = get_engine(args.db) if args.db else get_engine()
    init_schema(engine)

    if args.seed:
        print("Generating seed data...")
        csv_path = write_seed_csv()
        df = extract(csv_path)
    else:
        csv_path = Path(args.input)
        if not csv_path.exists():
            print(f"Error: file not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Loading {csv_path}...")
        df = extract(csv_path)

    print(f"Extracted {len(df):,} records. Loading into DB...")
    rows = load(df, engine)
    print(f"Done. {rows:,} rows written.")


if __name__ == "__main__":
    main()
