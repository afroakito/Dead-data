"""
query_basics.py

Tests the foundation by querying patterns in the data we have.
Exercises: sovereignty filter, flag filter, year range, aggregation.

Usage:
    python3 query_basics.py mental_health.db
"""

import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])

print("=== TOP 10 HIGHEST SUICIDE RATES (2010-2020, sovereign, no suspect zeros) ===")
rows = conn.execute("""
    SELECT cy.entity,
           ROUND(AVG(cy.suicide_rate), 2) as avg_rate,
           COUNT(*) as years_covered
    FROM country_year cy
    JOIN country c ON cy.code = c.code_iso3
    WHERE c.is_sovereign = 1
      AND cy.year BETWEEN 2010 AND 2020
      AND (cy.suicide_rate_flag IS NULL OR cy.suicide_rate_flag != 'suspect_zero')
      AND cy.suicide_rate > 0
    GROUP BY cy.code, cy.entity
    HAVING years_covered >= 5
    ORDER BY avg_rate DESC
    LIMIT 10
""").fetchall()

print(f"  {'country':<30} {'avg_rate':>10} {'years':>6}")
for r in rows:
    print(f"  {r[0]:<30} {r[1]:>10} {r[2]:>6}")

print("\n=== BOTTOM 10 LOWEST SUICIDE RATES (2010-2020, sovereign, no suspect zeros) ===")
rows = conn.execute("""
    SELECT cy.entity,
           ROUND(AVG(cy.suicide_rate), 2) as avg_rate,
           COUNT(*) as years_covered
    FROM country_year cy
    JOIN country c ON cy.code = c.code_iso3
    WHERE c.is_sovereign = 1
      AND cy.year BETWEEN 2010 AND 2020
      AND cy.suicide_rate_flag IS NULL
      AND cy.suicide_rate > 0
    GROUP BY cy.code, cy.entity
    HAVING years_covered >= 5
    ORDER BY avg_rate ASC
    LIMIT 10
""").fetchall()

print(f"  {'country':<30} {'avg_rate':>10} {'years':>6}")
for r in rows:
    print(f"  {r[0]:<30} {r[1]:>10} {r[2]:>6}")

print("\n=== JAPAN TREND (2000-2022) ===")
rows = conn.execute("""
    SELECT year, ROUND(suicide_rate, 2) as rate, suicide_rate_flag
    FROM country_year
    WHERE code = 'JPN' AND year BETWEEN 2000 AND 2022
    ORDER BY year
""").fetchall()
print(f"  {'year':>5} {'rate':>8} {'flag'}")
for r in rows:
    print(f"  {r[0]:>5} {r[1]:>8} {str(r[2] or '')}")

print("\n=== SANITY CHECK: countries with most data points ===")
rows = conn.execute("""
    SELECT cy.entity, COUNT(*) as rows, MIN(cy.year), MAX(cy.year)
    FROM country_year cy
    JOIN country c ON cy.code = c.code_iso3
    WHERE c.is_sovereign = 1
    GROUP BY cy.code, cy.entity
    ORDER BY rows DESC
    LIMIT 10
""").fetchall()
print(f"  {'country':<30} {'rows':>6} {'from':>6} {'to':>6}")
for r in rows:
    print(f"  {r[0]:<30} {r[1]:>6} {r[2]:>6} {r[3]:>6}")

conn.close()
