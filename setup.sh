#!/bin/bash
# setup.sh
# Downloads all data and runs the full pipeline in order.
# Run once from the project directory:
#   bash setup.sh

set -e  # stop immediately if any command fails

echo "=== Dead Data Project Setup ==="
echo ""

# --- 1. Check Python ---
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3."
    exit 1
fi
echo "[1/6] Python found: $(python3 --version)"

# --- 2. Install dependencies ---
echo "[2/6] Installing Python dependencies..."
pip install pycountry --break-system-packages -q 2>/dev/null || \
pip install pycountry -q 2>/dev/null || true
echo "      Done."

# --- 3. Download suicide rate data ---
echo "[3/6] Downloading suicide rate data (WHO MDB via Our World in Data)..."
curl -L \
  "https://ourworldindata.org/grapher/suicide-rate-who-mdb.csv?v=1&csvType=full&useColumnShortNames=false" \
  -H "User-Agent: Our World In Data data fetch/1.0" \
  -o suicide_rates_full.csv \
  --silent --show-error
LINES=$(wc -l < suicide_rates_full.csv)
echo "      Downloaded: $LINES rows"

# --- 4. Download population data ---
echo "[4/6] Downloading population data (UN WPP via Our World in Data)..."
curl -L \
  "https://ourworldindata.org/grapher/population-unwpp.csv?v=1&csvType=full&useColumnShortNames=false" \
  -H "User-Agent: Our World In Data data fetch/1.0" \
  -o population_full.csv \
  --silent --show-error
LINES=$(wc -l < population_full.csv)
echo "      Downloaded: $LINES rows"

# --- 5. Build fresh database ---
echo "[5/6] Building database..."

# Remove old database if it exists to start clean
if [ -f mental_health.db ]; then
    echo "      Removing old database..."
    rm mental_health.db
fi

python3 build_country_reference.py mental_health.db
echo ""
python3 load_data.py suicide_rates_full.csv mental_health.db
echo ""
python3 load_population.py population_full.csv mental_health.db
echo ""
python3 compute_flags.py mental_health.db

# --- 6. Summary ---
echo ""
echo "[6/6] Summary"
python3 <<'PYEOF'
import sqlite3
conn = sqlite3.connect("mental_health.db")

countries, rows, earliest, latest = conn.execute("""
    SELECT COUNT(DISTINCT code), COUNT(*), MIN(year), MAX(year)
    FROM country_year
""").fetchone()

sovereign = conn.execute(
    "SELECT COUNT(DISTINCT cy.code) FROM country_year cy "
    "JOIN country c ON cy.code = c.code_iso3 WHERE c.is_sovereign = 1"
).fetchone()[0]

non_sovereign = conn.execute(
    "SELECT COUNT(DISTINCT cy.code) FROM country_year cy "
    "JOIN country c ON cy.code = c.code_iso3 WHERE c.is_sovereign = 0"
).fetchone()[0]

unmatched = conn.execute(
    "SELECT COUNT(DISTINCT cy.code) FROM country_year cy "
    "LEFT JOIN country c ON cy.code = c.code_iso3 WHERE c.code_iso3 IS NULL"
).fetchone()[0]

missing_pop = conn.execute(
    "SELECT COUNT(*) FROM country_year WHERE population IS NULL"
).fetchone()[0]

flags = conn.execute("""
    SELECT suicide_rate_flag, COUNT(*) 
    FROM country_year 
    WHERE suicide_rate = 0
    GROUP BY suicide_rate_flag
""").fetchall()

print(f"  Total rows:         {rows}")
print(f"  Countries:          {countries}")
print(f"  Sovereign:          {sovereign}")
print(f"  Non-sovereign:      {non_sovereign}")
print(f"  Unmatched codes:    {unmatched}  <- need attention")
print(f"  Missing population: {missing_pop}  <- need attention")
print(f"  Year range:         {earliest} - {latest}")
print(f"  Zero-rate flags:")
for flag, count in flags:
    print(f"    {str(flag):<20} {count}")

conn.close()
PYEOF

echo ""
echo "=== Done. Database is ready: mental_health.db ==="
