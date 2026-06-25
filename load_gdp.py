"""
load_gdp.py

Downloads GDP per capita data (World Bank via Our World in Data)
and loads it into the country_year table as a new column.

This script:
  1. Adds gdp_per_capita column to country_year if not present
  2. Downloads the CSV directly
  3. Updates matching (code, year) rows with GDP values
  4. Reports what matched, what didn't

Usage:
    python3 load_gdp.py <db_file>
"""

import csv
import io
import sqlite3
import sys
import urllib.request
from pathlib import Path

GDP_URL = (
    "https://ourworldindata.org/grapher/gdp-per-capita-worldbank.csv"
    "?v=1&csvType=full&useColumnShortNames=false"
)


def add_column(conn: sqlite3.Connection) -> None:
    """Add gdp_per_capita column if it doesn't exist yet."""
    existing = [
        row[1] for row in conn.execute("PRAGMA table_info(country_year)")
    ]
    if "gdp_per_capita" not in existing:
        conn.execute("ALTER TABLE country_year ADD COLUMN gdp_per_capita REAL")
        print("  Added column: gdp_per_capita")
    else:
        print("  Column gdp_per_capita already exists -- skipping ALTER")


def download_csv(url: str) -> list[dict]:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Our World In Data data fetch/1.0"}
    )
    with urllib.request.urlopen(req) as r:
        content = r.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def load_gdp(conn: sqlite3.Connection, rows: list[dict]) -> dict:
    counts = {"matched": 0, "no_suicide_row": 0, "skipped_aggregate": 0}

    # Find the GDP value column dynamically
    sample = rows[0]
    gdp_col = next(
        k for k in sample.keys() if k not in ("Entity", "Code", "Year", "owid_region")
    )
    print(f"  GDP column detected: '{gdp_col}'")

    for row in rows:
        code = row["Code"]
        year = int(row["Year"])
        gdp_raw = row[gdp_col]

        # Skip aggregate regions (no ISO3 code or known non-country codes)
        if not code or len(code) != 3:
            counts["skipped_aggregate"] += 1
            continue

        gdp_value = float(gdp_raw) if gdp_raw != "" else None

        cur = conn.execute(
            """
            UPDATE country_year
            SET gdp_per_capita = ?
            WHERE code = ? AND year = ?
            """,
            (gdp_value, code, year),
        )

        if cur.rowcount == 0:
            counts["no_suicide_row"] += 1
        else:
            counts["matched"] += 1

    conn.commit()
    return counts


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 load_gdp.py <db_file>")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    conn = sqlite3.connect(db_path)

    print("[1/3] Adding GDP column to country_year...")
    add_column(conn)

    print("[2/3] Downloading GDP data...")
    rows = download_csv(GDP_URL)
    print(f"  Downloaded: {len(rows)} rows")

    print("[3/3] Loading into database...")
    counts = load_gdp(conn, rows)

    # Summary
    total_cy = conn.execute("SELECT COUNT(*) FROM country_year").fetchone()[0]
    has_gdp = conn.execute(
        "SELECT COUNT(*) FROM country_year WHERE gdp_per_capita IS NOT NULL"
    ).fetchone()[0]
    missing_gdp = total_cy - has_gdp

    print(f"\n  Matched and updated:    {counts['matched']}")
    print(f"  No matching suicide row: {counts['no_suicide_row']}")
    print(f"  Skipped aggregates:     {counts['skipped_aggregate']}")
    print(f"\n  country_year rows with GDP:    {has_gdp}")
    print(f"  country_year rows missing GDP: {missing_gdp}")

    # Show sample of rows missing GDP -- worth knowing why
    missing = conn.execute("""
        SELECT DISTINCT cy.entity, cy.code,
               MIN(cy.year) as from_year, MAX(cy.year) as to_year
        FROM country_year cy
        WHERE cy.gdp_per_capita IS NULL
        GROUP BY cy.code
        ORDER BY cy.entity
        LIMIT 15
    """).fetchall()

    if missing:
        print(f"\n  Sample rows missing GDP (first 15 countries):")
        print(f"  {'entity':<30} {'code':<5} {'years'}")
        for r in missing:
            print(f"  {r[0]:<30} {r[1]:<5} {r[2]}-{r[3]}")

    conn.close()


if __name__ == "__main__":
    main()
