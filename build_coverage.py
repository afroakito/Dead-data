"""
build_coverage.py

Creates a data_coverage table recording which sovereign countries
have no suicide rate data in the WHO MDB, and flags the likely reason.

This makes the gap visible inside the database itself -- not just
in someone's head or a README nobody reads.

Coverage categories:
  'full'          -- has suicide rate data
  'no_who_data'   -- sovereign, in reference table, but absent from WHO MDB
                     likely reason: death registration below 65% threshold

Usage:
    python3 build_coverage.py <db_file>
"""

import sqlite3
import sys
from pathlib import Path


# Countries known to have data quality issues beyond simple absence
# These are worth flagging explicitly with a more specific note.
# Source: WHO MDB documentation + known reporting gaps
KNOWN_GAPS = {
    "AFG": "active conflict, minimal civil registration",
    "AGO": "civil registration system developing",
    "BGD": "low death registration completeness",
    "BEN": "low death registration completeness",
    "BTN": "limited vital statistics system",
    "BOL": "partial registration coverage",
    "BWA": "incomplete death registration",
    "BFA": "low death registration completeness",
    "BDI": "conflict-affected, minimal registration",
    "KHM": "death registration system developing",
    "CMR": "low death registration completeness",
    "CAF": "conflict-affected, minimal registration",
    "TCD": "minimal civil registration",
    "COD": "conflict-affected, minimal registration",
    "ETH": "low death registration completeness",
    "GHA": "partial registration coverage",
    "GIN": "low death registration completeness",
    "HTI": "conflict-affected, low registration",
    "IND": "partial registration, large population gaps",
    "IDN": "partial registration coverage",
    "IRQ": "conflict-affected registration gaps",
    "CIV": "low death registration completeness",
    "KEN": "partial registration coverage",
    "LAO": "limited vital statistics",
    "LBR": "conflict-affected, minimal registration",
    "MDG": "low death registration completeness",
    "MWI": "low death registration completeness",
    "MLI": "low death registration completeness",
    "MRT": "low death registration completeness",
    "MOZ": "low death registration completeness",
    "MMR": "limited vital statistics",
    "NER": "low death registration completeness",
    "NGA": "partial registration, large population",
    "PAK": "partial registration coverage",
    "PNG": "limited vital statistics",
    "SEN": "low death registration completeness",
    "SLE": "conflict-affected, low registration",
    "SOM": "conflict-affected, minimal registration",
    "SSD": "conflict-affected, minimal registration",
    "SDN": "conflict-affected registration gaps",
    "SYR": "conflict-affected registration gaps",
    "TZA": "partial registration coverage",
    "TGO": "low death registration completeness",
    "UGA": "low death registration completeness",
    "YEM": "conflict-affected, minimal registration",
    "ZMB": "low death registration completeness",
    "ZWE": "economic collapse affected registration",
}


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_coverage (
            code_iso3       TEXT PRIMARY KEY,
            name_standard   TEXT NOT NULL,
            has_suicide_data INTEGER NOT NULL,  -- 1=yes, 0=no
            suicide_row_count INTEGER,          -- NULL if no data
            suicide_year_min INTEGER,
            suicide_year_max INTEGER,
            gap_reason      TEXT                -- why data is absent, if known
        )
    """)


def populate(conn: sqlite3.Connection) -> dict:
    counts = {"with_data": 0, "without_data": 0}

    # Get all sovereign countries from reference table
    sovereign = conn.execute("""
        SELECT code_iso3, name_standard FROM country
        WHERE is_sovereign = 1
        ORDER BY name_standard
    """).fetchall()

    for code, name in sovereign:
        # Check if this country has suicide data
        stats = conn.execute("""
            SELECT COUNT(*), MIN(year), MAX(year)
            FROM country_year WHERE code = ?
        """, (code,)).fetchone()

        row_count, year_min, year_max = stats

        if row_count > 0:
            conn.execute("""
                INSERT OR REPLACE INTO data_coverage
                (code_iso3, name_standard, has_suicide_data,
                 suicide_row_count, suicide_year_min, suicide_year_max,
                 gap_reason)
                VALUES (?, ?, 1, ?, ?, ?, NULL)
            """, (code, name, row_count, year_min, year_max))
            counts["with_data"] += 1
        else:
            gap_reason = KNOWN_GAPS.get(
                code,
                "absent from WHO MDB -- likely below 65% death registration threshold"
            )
            conn.execute("""
                INSERT OR REPLACE INTO data_coverage
                (code_iso3, name_standard, has_suicide_data,
                 suicide_row_count, suicide_year_min, suicide_year_max,
                 gap_reason)
                VALUES (?, ?, 0, NULL, NULL, NULL, ?)
            """, (code, name, gap_reason))
            counts["without_data"] += 1

    conn.commit()
    return counts


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 build_coverage.py <db_file>")
        sys.exit(1)

    conn = sqlite3.connect(sys.argv[1])
    create_table(conn)
    counts = populate(conn)

    total = counts["with_data"] + counts["without_data"]
    pct = round(counts["with_data"] / total * 100)

    print(f"Sovereign countries total:    {total}")
    print(f"With suicide data:            {counts['with_data']} ({pct}%)")
    print(f"Without suicide data:         {counts['without_data']} ({100-pct}%)")

    print("\n=== SAMPLE: COUNTRIES WITHOUT DATA ===")
    rows = conn.execute("""
        SELECT code_iso3, name_standard, gap_reason
        FROM data_coverage
        WHERE has_suicide_data = 0
        ORDER BY name_standard
        LIMIT 15
    """).fetchall()
    for r in rows:
        print(f"  {r[0]} | {r[1]:<30} | {r[2][:50]}")

    print("\n=== COVERAGE BY LIKELY REGION (rough) ===")
    # Show which well-known countries DO have data
    check = ["JPN", "USA", "DEU", "IND", "NGA", "BRA", "ZAF", "IDN", "PAK", "BGD"]
    print(f"  {'code':<5} {'country':<25} {'has_data':>9} {'rows':>6} {'years'}")
    for code in check:
        r = conn.execute("""
            SELECT name_standard, has_suicide_data,
                   suicide_row_count, suicide_year_min, suicide_year_max
            FROM data_coverage WHERE code_iso3 = ?
        """, (code,)).fetchone()
        if r:
            year_range = f"{r[3]}-{r[4]}" if r[1] else "none"
            print(f"  {code:<5} {r[0]:<25} {str(bool(r[1])):>9} {str(r[2] or ''):>6}  {year_range}")

    conn.close()


if __name__ == "__main__":
    main()
