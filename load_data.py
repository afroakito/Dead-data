"""
load_data.py

Loads suicide rate data (WHO Mortality Database via Our World in Data)
into a SQLite database following schema.sql.

Usage:
    python load_data.py <csv_file> <db_file>

Example:
    python load_data.py sample_suicide_rates.csv mental_health.db
"""

import csv
import sqlite3
import sys
from pathlib import Path


def create_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    with open(schema_path, "r") as f:
        conn.executescript(f.read())


def load_csv(conn: sqlite3.Connection, csv_path: Path) -> tuple[int, int]:
    """Load rows from csv_path into country_year. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["Code"]
            entity = row["Entity"]
            year = int(row["Year"])
            # The real OWID CSV has a long column name -- find it dynamically
            # rather than hardcoding, so this survives future column renames.
            rate_col = next(k for k in row.keys() if k not in ("Entity", "Code", "Year"))
            rate_raw = row[rate_col]

            # Some sources leave this blank for missing rows -- handle that.
            suicide_rate = float(rate_raw) if rate_raw != "" else None

            try:
                conn.execute(
                    """
                    INSERT INTO country_year (code, entity, year, suicide_rate)
                    VALUES (?, ?, ?, ?)
                    """,
                    (code, entity, year, suicide_rate),
                )
                inserted += 1
            except sqlite3.IntegrityError as e:
                # Primary key collision -- same (code, year) appeared twice.
                print(f"  SKIPPED duplicate: {entity} ({code}) {year} -- {e}")
                skipped += 1

    conn.commit()
    return inserted, skipped


def main():
    if len(sys.argv) != 3:
        print("Usage: python load_data.py <csv_file> <db_file>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    db_path = Path(sys.argv[2])
    schema_path = Path(__file__).parent / "schema.sql"

    conn = sqlite3.connect(db_path)
    create_schema(conn, schema_path)

    inserted, skipped = load_csv(conn, csv_path)

    total = conn.execute("SELECT COUNT(*) FROM country_year").fetchone()[0]

    print(f"Inserted: {inserted}")
    print(f"Skipped (duplicates): {skipped}")
    print(f"Total rows now in country_year: {total}")

    conn.close()


if __name__ == "__main__":
    main()
