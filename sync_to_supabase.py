"""
sync_to_supabase.py

Mirrors local SQLite data to Supabase.
SQLite is the working database. Supabase is the remote mirror.

Creates three tables in Supabase if they don't exist, then upserts:
  - country_year_data  (core data)
  - data_gaps          (coverage information)
  - pair_results       (correlation results)

Usage:
    python3 sync_to_supabase.py <db_file>

Requires .env file with:
    SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
    SUPABASE_KEY=your_anon_key_here
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    sys.exit(1)

# Batch size for upserts -- Supabase has request size limits
BATCH_SIZE = 500


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def batch_upsert(client: Client, table: str, rows: list[dict]) -> int:
    """Upsert rows in batches. Returns total rows upserted."""
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        client.table(table).upsert(batch).execute()
        total += len(batch)
        print(f"  {table}: upserted {total}/{len(rows)} rows...", end="\r")
    print()
    return total


def sync_country_year(conn: sqlite3.Connection, client: Client) -> None:
    print("[1/3] Syncing country_year_data...")
    rows = conn.execute("""
        SELECT cy.code, cy.entity, cy.year,
               cy.suicide_rate, cy.suicide_rate_flag,
               cy.population, cy.gdp_per_capita
        FROM country_year cy
        JOIN country c ON cy.code = c.code_iso3
        WHERE c.is_sovereign = 1
    """).fetchall()

    records = [
        {
            "code":             r[0],
            "entity":           r[1],
            "year":             r[2],
            "suicide_rate":     r[3],
            "suicide_rate_flag": r[4],
            "population":       r[5],
            "gdp_per_capita":   r[6],
        }
        for r in rows
    ]
    batch_upsert(client, "country_year_data", records)
    print(f"  Done: {len(records)} rows")


def sync_data_gaps(conn: sqlite3.Connection, client: Client) -> None:
    print("[2/3] Syncing data_gaps...")
    rows = conn.execute("""
        SELECT code_iso3, name_standard, has_suicide_data,
               suicide_row_count, suicide_year_min, suicide_year_max,
               gap_reason
        FROM data_coverage
    """).fetchall()

    records = [
        {
            "code":             r[0],
            "name":             r[1],
            "has_suicide":      bool(r[2]),
            "row_count":        r[3],
            "year_min":         r[4],
            "year_max":         r[5],
            "gap_reason":       r[6],
        }
        for r in rows
    ]
    batch_upsert(client, "data_gaps", records)
    print(f"  Done: {len(records)} rows")


def sync_pair_results(client: Client) -> None:
    """
    Reads pair results from question_log.md is manual.
    Instead we hardcode Q1 result here -- the first closed question.
    Future results get added as they close.
    """
    print("[3/3] Syncing pair_results...")
    records = [
        {
            "pair_id":       "gdp_x_suicide",
            "variable_a":    "gdp_per_capita",
            "variable_b":    "suicide_rate",
            "r_value":       0.004,
            "n_observations": 2806,
            "scope":         "sovereign countries, 1990-2023, pooled global",
            "method":        "pearson",
            "status":        "closed",
            "null_reason":   "true_null",
            "notes":         (
                "Near-zero pooled global correlation. Wealthier countries do not "
                "systematically have higher or lower suicide rates. Known heterogeneity: "
                "Japan/South Korea (high GDP, high rate), Italy/Spain (high GDP, low rate), "
                "Guyana (low GDP, highest rate). Likely masks within-country trends. "
                "See Q2 for fixed-effects style analysis."
            ),
            "tested_on":     "2026-06-26",
        }
    ]
    batch_upsert(client, "pair_results", records)
    print(f"  Done: {len(records)} rows")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 sync_to_supabase.py <db_file>")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    print(f"Connecting to Supabase: {SUPABASE_URL[:40]}...")
    client = get_client()

    conn = sqlite3.connect(db_path)

    sync_country_year(conn, client)
    sync_data_gaps(conn, client)
    sync_pair_results(client)

    conn.close()
    print("\n=== Sync complete ===")


if __name__ == "__main__":
    main()
