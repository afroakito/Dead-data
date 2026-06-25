"""
build_country_reference.py

Creates and populates a `country` reference table -- the single source
of truth for country identities across all datasets.

Design:
- Based on ISO 3166-1 alpha-3 codes (pycountry)
- Flags known problem cases explicitly (contested sovereignty,
  non-standard codes, territories)
- Sovereign countries loaded first; non-sovereign flagged but included
  with notes so gaps are visible, not silent

Usage:
    python build_country_reference.py <db_file>
"""

import sqlite3
import sys
from pathlib import Path
import pycountry

# -------------------------------------------------------------------
# Known problem cases -- explicit, visible, not hidden
# Each entry: iso3_code -> (is_sovereign, note)
# is_sovereign: 1 = treat as sovereign for now, 0 = exclude from
#               primary analysis
# -------------------------------------------------------------------
PROBLEM_CASES = {
    "XKX": (0, "Kosovo: non-standard code XKX, not in ISO 3166-1, "
               "recognized by ~100 countries, excluded from primary joins. "
               "NOTE: World Bank/OWID GDP data uses a DIFFERENT code "
               "(OWID_KOS) for Kosovo -- the two codes don't match, "
               "so Kosovo's GDP data silently fails to join even though "
               "it exists. Same country, incompatible codes across sources."),
    "ESH": (0, "Western Sahara: disputed territory, "
               "no functioning government, unreliable data"),
    "TWN": (1, "Taiwan: ISO recognizes as 'Taiwan, Province of China', "
               "WHO/World Bank data inconsistent -- include with caution"),
    "GRL": (0, "Greenland: autonomous territory of Denmark, "
               "not sovereign, separate ISO code"),
    "HKG": (0, "Hong Kong: Special Administrative Region of China, "
               "not sovereign"),
    "MAC": (0, "Macao: Special Administrative Region of China, "
               "not sovereign"),
    "PRI": (0, "Puerto Rico: US territory, not sovereign"),
    "PSE": (1, "Palestine: partial ISO recognition, "
               "WHO includes but World Bank inconsistent"),
}

# Countries where name in WHO/OWID data differs from ISO standard name
# iso3 -> preferred display name
NAME_OVERRIDES = {
    "RUS": "Russia",
    "IRN": "Iran",
    "KOR": "South Korea",
    "PRK": "North Korea",
    "BOL": "Bolivia",
    "VEN": "Venezuela",
    "MDA": "Moldova",
    "SYR": "Syria",
    "TZA": "Tanzania",
    "COD": "DR Congo",
    "COG": "Congo",
    "LAO": "Laos",
    "VNM": "Vietnam",
    "USA": "United States",
    "GBR": "United Kingdom",
}


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS country (
            code_iso3       TEXT PRIMARY KEY,
            name_standard   TEXT NOT NULL,
            name_iso        TEXT NOT NULL,   -- original ISO name, preserved
            is_sovereign    INTEGER NOT NULL DEFAULT 1,  -- 1=yes, 0=no/disputed
            notes           TEXT             -- explicit flags for problem cases
        )
    """)


def populate(conn: sqlite3.Connection) -> dict:
    counts = {"sovereign": 0, "non_sovereign": 0, "problem_flagged": 0}

    # Add Kosovo manually -- not in ISO 3166-1 at all
    conn.execute("""
        INSERT OR IGNORE INTO country
            (code_iso3, name_standard, name_iso, is_sovereign, notes)
        VALUES (?, ?, ?, ?, ?)
    """, ("XKX", "Kosovo", "Kosovo",
          0, PROBLEM_CASES["XKX"][1]))
    counts["non_sovereign"] += 1
    counts["problem_flagged"] += 1

    for country in pycountry.countries:
        code = country.alpha_3
        iso_name = country.name
        display_name = NAME_OVERRIDES.get(code, iso_name)

        if code in PROBLEM_CASES:
            is_sovereign, note = PROBLEM_CASES[code]
            counts["problem_flagged"] += 1
        else:
            is_sovereign = 1
            note = None

        if is_sovereign:
            counts["sovereign"] += 1
        else:
            counts["non_sovereign"] += 1

        conn.execute("""
            INSERT OR IGNORE INTO country
                (code_iso3, name_standard, name_iso, is_sovereign, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (code, display_name, iso_name, is_sovereign, note))

    conn.commit()
    return counts


def main():
    if len(sys.argv) != 2:
        print("Usage: python build_country_reference.py <db_file>")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    conn = sqlite3.connect(db_path)

    create_table(conn)
    counts = populate(conn)

    total = conn.execute("SELECT COUNT(*) FROM country").fetchone()[0]
    sovereign = conn.execute(
        "SELECT COUNT(*) FROM country WHERE is_sovereign = 1"
    ).fetchone()[0]
    flagged = conn.execute(
        "SELECT COUNT(*) FROM country WHERE notes IS NOT NULL"
    ).fetchone()[0]

    print(f"Total entries in country table: {total}")
    print(f"Marked sovereign:               {sovereign}")
    print(f"Explicitly flagged with notes:  {flagged}")

    print("\n=== PROBLEM CASES ===")
    rows = conn.execute("""
        SELECT code_iso3, name_standard, is_sovereign, notes
        FROM country WHERE notes IS NOT NULL
        ORDER BY name_standard
    """).fetchall()
    for r in rows:
        status = "sovereign" if r[2] else "non-sovereign"
        print(f"  {r[0]} | {r[1]:<20} | {status:<14} | {r[3][:60]}...")

    print("\n=== OUR CURRENT DATA vs REFERENCE TABLE ===")
    check = conn.execute("""
        SELECT cy.entity, cy.code,
               c.is_sovereign,
               c.notes
        FROM country_year cy
        LEFT JOIN country c ON cy.code = c.code_iso3
        GROUP BY cy.code
        ORDER BY cy.entity
    """).fetchall()
    print(f"{'entity':<22} {'code':<5} {'sovereign':>9} {'note'}")
    for r in check:
        sovereign_str = str(r[2]) if r[2] is not None else "NOT IN REF"
        note_str = r[3][:40] + "..." if r[3] else ""
        print(f"{r[0]:<22} {r[1]:<5} {sovereign_str:>9}  {note_str}")

    conn.close()


if __name__ == "__main__":
    main()
