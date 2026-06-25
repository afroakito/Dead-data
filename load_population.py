"""
load_population.py

Updates the population column in country_year using a population CSV
(UN WPP via Our World in Data, same Entity/Code/Year format).

This is a JOIN operation expressed as an UPDATE: for each (code, year)
in the population file, find the matching row in country_year and fill
in population. Rows that don't match in either direction are reported,
not silently dropped.

Usage:
    python load_population.py <population_csv> <db_file>
"""

import csv
import sqlite3
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("Usage: python load_population.py <population_csv> <db_file>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    db_path = Path(sys.argv[2])

    conn = sqlite3.connect(db_path)

    matched = 0
    unmatched_population_rows = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["Code"]
            year = int(row["Year"])
            pop_col = next(k for k in row.keys() if k not in ("Entity", "Code", "Year"))
            population = int(float(row[pop_col]))

            cur = conn.execute(
                """
                UPDATE country_year
                SET population = ?
                WHERE code = ? AND year = ?
                """,
                (population, code, year),
            )

            if cur.rowcount == 0:
                # No (code, year) row exists in country_year for this
                # population record -- the suicide_rate dataset didn't
                # cover this country-year.
                unmatched_population_rows.append((row["Entity"], code, year))
            else:
                matched += 1

    conn.commit()

    # Now check the other direction: rows in country_year that still
    # have no population after this update.
    still_missing = conn.execute(
        "SELECT entity, code, year FROM country_year WHERE population IS NULL"
    ).fetchall()

    print(f"Matched and updated: {matched}")
    print(f"Population rows with no matching country_year row: {len(unmatched_population_rows)}")
    for entity, code, year in unmatched_population_rows:
        print(f"  no suicide_rate row for: {entity} ({code}) {year}")

    print(f"country_year rows still missing population: {len(still_missing)}")
    for entity, code, year in still_missing:
        print(f"  no population for: {entity} ({code}) {year}")

    conn.close()


if __name__ == "__main__":
    main()
