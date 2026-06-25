"""
summary.py
Run this to see the full picture of what's in the database.
Usage: python3 summary.py mental_health.db
"""
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])

print("=== DATABASE SUMMARY ===\n")

r = conn.execute("""
    SELECT COUNT(DISTINCT code), COUNT(*), MIN(year), MAX(year)
    FROM country_year
""").fetchone()
print(f"Total rows:      {r[1]}")
print(f"Countries:       {r[0]}")
print(f"Year range:      {r[2]} - {r[3]}")

sovereign = conn.execute("""
    SELECT COUNT(DISTINCT cy.code) FROM country_year cy
    JOIN country c ON cy.code = c.code_iso3 WHERE c.is_sovereign = 1
""").fetchone()[0]

non_sovereign = conn.execute("""
    SELECT COUNT(DISTINCT cy.code) FROM country_year cy
    JOIN country c ON cy.code = c.code_iso3 WHERE c.is_sovereign = 0
""").fetchone()[0]

unmatched = conn.execute("""
    SELECT COUNT(DISTINCT cy.code) FROM country_year cy
    LEFT JOIN country c ON cy.code = c.code_iso3
    WHERE c.code_iso3 IS NULL
""").fetchone()[0]

missing_pop = conn.execute(
    "SELECT COUNT(*) FROM country_year WHERE population IS NULL"
).fetchone()[0]

print(f"Sovereign:       {sovereign}")
print(f"Non-sovereign:   {non_sovereign}")
print(f"Unmatched codes: {unmatched}  <- not in reference table")
print(f"Missing pop:     {missing_pop}")

print("\n=== ZERO RATE FLAGS ===")
for flag, count in conn.execute("""
    SELECT suicide_rate_flag, COUNT(*)
    FROM country_year WHERE suicide_rate = 0
    GROUP BY suicide_rate_flag ORDER BY COUNT(*) DESC
""").fetchall():
    print(f"  {str(flag):<20} {count}")

print("\n=== UNMATCHED CODES (not in reference table) ===")
rows = conn.execute("""
    SELECT DISTINCT cy.entity, cy.code
    FROM country_year cy
    LEFT JOIN country c ON cy.code = c.code_iso3
    WHERE c.code_iso3 IS NULL
    ORDER BY cy.entity
""").fetchall()
if rows:
    for r in rows:
        print(f"  {r[1]} | {r[0]}")
else:
    print("  None -- all codes matched.")

print("\n=== POPULATION ROWS WITH NO SUICIDE DATA (sample) ===")
rows = conn.execute("""
    SELECT entity, code, COUNT(*) as pop_rows
    FROM (
        SELECT DISTINCT c.name_standard as entity, c.code_iso3 as code
        FROM country c
        WHERE c.is_sovereign = 1
        AND c.code_iso3 NOT IN (SELECT DISTINCT code FROM country_year)
    )
    GROUP BY entity, code
    ORDER BY entity
    LIMIT 20
""").fetchall()
if rows:
    for r in rows:
        print(f"  {r[1]} | {r[0]}")
else:
    print("  None.")

conn.close()
