"""
compute_flags.py

Computes suicide_rate_flag for rows where suicide_rate == 0.

Heuristic:
  1. For each country, compute a "typical rate" = median of that
     country's non-zero suicide_rate values (across all years available).
  2. For a zero-rate row, expected deaths = population * typical_rate / 100,000.
  3. Under a Poisson assumption, P(0 deaths) = e^(-expected_deaths).
  4. If that probability is below ZERO_PROBABILITY_THRESHOLD, a true zero
     would be very unlikely -> flag as 'suspect_zero'.
     Otherwise -> 'plausible_zero'.

This is an approximation, not a verified classification. The threshold
is a deliberate, visible parameter -- not a hidden assumption.

Rows with no non-zero history for that country get 'no_baseline'
(can't evaluate). Rows with no population stay NULL (can't evaluate).
Non-zero rows are left untouched (flag stays NULL -- the question
doesn't apply to them).

Usage:
    python compute_flags.py <db_file>
"""

import math
import sqlite3
import statistics
import sys
from pathlib import Path

ZERO_PROBABILITY_THRESHOLD = 0.05  # e^-3 ~= 0.05 -> ~3 expected deaths is the cutoff


def main():
    if len(sys.argv) != 2:
        print("Usage: python compute_flags.py <db_file>")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    conn = sqlite3.connect(db_path)

    codes = [r[0] for r in conn.execute("SELECT DISTINCT code FROM country_year").fetchall()]

    counts = {"plausible_zero": 0, "suspect_zero": 0, "no_baseline": 0, "no_population": 0}

    for code in codes:
        non_zero_rates = [
            r[0] for r in conn.execute(
                "SELECT suicide_rate FROM country_year WHERE code = ? AND suicide_rate > 0",
                (code,),
            ).fetchall()
        ]

        zero_rows = conn.execute(
            "SELECT year, population FROM country_year WHERE code = ? AND suicide_rate = 0",
            (code,),
        ).fetchall()

        if not zero_rows:
            continue

        if not non_zero_rates:
            conn.execute(
                "UPDATE country_year SET suicide_rate_flag = 'no_baseline' "
                "WHERE code = ? AND suicide_rate = 0",
                (code,),
            )
            counts["no_baseline"] += len(zero_rows)
            continue

        typical_rate = statistics.median(non_zero_rates)

        for year, population in zero_rows:
            if population is None:
                counts["no_population"] += 1
                continue

            expected_deaths = population * typical_rate / 100_000
            p_zero = math.exp(-expected_deaths)

            flag = "plausible_zero" if p_zero >= ZERO_PROBABILITY_THRESHOLD else "suspect_zero"
            counts[flag] += 1

            conn.execute(
                "UPDATE country_year SET suicide_rate_flag = ? WHERE code = ? AND year = ?",
                (flag, code, year),
            )

    conn.commit()

    print(f"Threshold: P(0 deaths) < {ZERO_PROBABILITY_THRESHOLD} -> suspect_zero")
    print(f"plausible_zero: {counts['plausible_zero']}")
    print(f"suspect_zero:   {counts['suspect_zero']}")
    print(f"no_baseline:    {counts['no_baseline']}")
    print(f"no_population:  {counts['no_population']}")

    conn.close()


if __name__ == "__main__":
    main()
