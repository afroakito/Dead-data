"""
export_gdp_suicide.py

Exports a clean CSV: one row per country-year, with suicide rate,
GDP per capita, population, and flags side by side.
Only sovereign countries, only rows with both suicide_rate and gdp data.

Usage:
    python3 export_gdp_suicide.py <db_file> <output_csv>
"""

import csv
import sqlite3
import sys

db_path = sys.argv[1]
out_path = sys.argv[2]

conn = sqlite3.connect(db_path)

rows = conn.execute("""
    SELECT cy.entity,
           cy.code,
           cy.year,
           cy.suicide_rate,
           cy.suicide_rate_flag,
           cy.population,
           cy.gdp_per_capita
    FROM country_year cy
    JOIN country c ON cy.code = c.code_iso3
    WHERE c.is_sovereign = 1
      AND cy.suicide_rate IS NOT NULL
      AND cy.gdp_per_capita IS NOT NULL
    ORDER BY cy.entity, cy.year
""").fetchall()

with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "country", "code", "year",
        "suicide_rate", "suicide_rate_flag",
        "population", "gdp_per_capita"
    ])
    writer.writerows(rows)

print(f"Exported {len(rows)} rows to {out_path}")
print(f"Countries included: {len(set(r[1] for r in rows))}")

conn.close()
