"""
q2_within_country.py

Q2: Within-country correlation between GDP per capita and suicide rate over time.

For each sovereign country with sufficient data:
  - Compute Pearson r between GDP and suicide rate across available years
  - Require minimum MIN_YEARS of overlapping data
  - Exclude suspect_zero flagged rows

Outputs:
  - Terminal summary
  - q2_results.csv  (one row per country)
  - Syncs results to Supabase (pair_results + country_pair_results)

Usage:
    py q2_within_country.py mental_health.db
"""

import csv
import math
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

MIN_YEARS = 10  # minimum overlapping data points required per country


def pearson_r(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / n)
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys) / n)
    if std_x == 0 or std_y == 0:
        return None
    return cov / (std_x * std_y)


def compute_q2(conn: sqlite3.Connection) -> list[dict]:
    codes = [
        r[0] for r in conn.execute("""
            SELECT DISTINCT cy.code FROM country_year cy
            JOIN country c ON cy.code = c.code_iso3
            WHERE c.is_sovereign = 1
        """).fetchall()
    ]

    results = []

    for code in codes:
        rows = conn.execute("""
            SELECT cy.entity, cy.year, cy.suicide_rate, cy.gdp_per_capita
            FROM country_year cy
            WHERE cy.code = ?
              AND cy.suicide_rate IS NOT NULL
              AND cy.gdp_per_capita IS NOT NULL
              AND (cy.suicide_rate_flag IS NULL
                   OR cy.suicide_rate_flag != 'suspect_zero')
              AND cy.suicide_rate > 0
            ORDER BY cy.year
        """, (code,)).fetchall()

        if len(rows) < MIN_YEARS:
            continue

        entity = rows[0][0]
        gdps = [r[2] for r in rows]
        rates = [r[3] for r in rows]

        r = pearson_r(gdps, rates)
        if r is None:
            continue

        results.append({
            "code":    code,
            "entity":  entity,
            "r_value": round(r, 4),
            "n_years": len(rows),
        })

    return sorted(results, key=lambda x: x["r_value"])


def summarize(results: list[dict]) -> dict:
    r_values = [r["r_value"] for r in results]
    n = len(r_values)
    negative = sum(1 for r in r_values if r < -0.3)
    positive = sum(1 for r in r_values if r > 0.3)
    neutral  = n - negative - positive
    median_r = sorted(r_values)[n // 2]

    return {
        "n_countries": n,
        "median_r":    round(median_r, 4),
        "negative":    negative,
        "neutral":     neutral,
        "positive":    positive,
        "pct_negative": round(negative / n * 100),
        "pct_positive": round(positive / n * 100),
    }


def save_csv(results: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "entity", "r_value", "n_years"])
        writer.writeheader()
        writer.writerows(results)


def sync_supabase(results: list[dict], summary: dict) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("  No Supabase credentials -- skipping sync")
        return

    client = create_client(url, key)

    # country_pair_results -- one row per country
    rows = [
        {
            "pair_id": "gdp_x_suicide_within",
            "code":    r["code"],
            "entity":  r["entity"],
            "r_value": r["r_value"],
            "n_years": r["n_years"],
        }
        for r in results
    ]
    client.table("country_pair_results").upsert(rows).execute()
    print(f"  Synced {len(rows)} rows to country_pair_results")

    # pair_results -- one summary row for Q2
    client.table("pair_results").upsert([{
        "pair_id":        "gdp_x_suicide_within",
        "variable_a":     "gdp_per_capita",
        "variable_b":     "suicide_rate",
        "r_value":        summary["median_r"],
        "n_observations": summary["n_countries"],
        "scope":          f"within-country, sovereign, min {MIN_YEARS} years, 1990-2023",
        "method":         "pearson per country, median reported",
        "status":         "closed",
        "null_reason":    None,
        "notes": (
            f"{summary['n_countries']} countries qualified. "
            f"Median r = {summary['median_r']}. "
            f"{summary['pct_negative']}% negative (r < -0.3), "
            f"{summary['pct_positive']}% positive (r > 0.3). "
            f"See country_pair_results for per-country detail."
        ),
        "tested_on": "2026-06-26",
    }]).execute()
    print(f"  Synced Q2 summary to pair_results")


def main():
    if len(sys.argv) != 2:
        print("Usage: py q2_within_country.py <db_file>")
        sys.exit(1)

    conn = sqlite3.connect(sys.argv[1])

    print(f"Computing per-country Pearson r (min {MIN_YEARS} years required)...")
    results = compute_q2(conn)
    summary = summarize(results)

    print(f"\n=== Q2 RESULTS ===")
    print(f"Countries qualified:  {summary['n_countries']}")
    print(f"Median r:             {summary['median_r']}")
    print(f"Negative (r < -0.3): {summary['negative']} ({summary['pct_negative']}%)")
    print(f"Neutral:              {summary['neutral']}")
    print(f"Positive (r > +0.3): {summary['positive']} ({summary['pct_positive']}%)")

    print(f"\n=== TOP 10 MOST NEGATIVE (GDP up, suicide down) ===")
    print(f"  {'country':<25} {'r':>7} {'years':>6}")
    for r in results[:10]:
        print(f"  {r['entity']:<25} {r['r_value']:>7} {r['n_years']:>6}")

    print(f"\n=== TOP 10 MOST POSITIVE (GDP up, suicide up) ===")
    print(f"  {'country':<25} {'r':>7} {'years':>6}")
    for r in reversed(results[-10:]):
        print(f"  {r['entity']:<25} {r['r_value']:>7} {r['n_years']:>6}")

    out_csv = "q2_results.csv"
    save_csv(results, out_csv)
    print(f"\nSaved: {out_csv}")

    print("\nSyncing to Supabase...")
    sync_supabase(results, summary)

    conn.close()


if __name__ == "__main__":
    main()
