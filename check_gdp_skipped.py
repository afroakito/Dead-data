"""
check_gdp_skipped.py
Verifies that codes skipped during GDP load were actually aggregates
(regions, income groups) and not real countries with malformed codes.

Usage: python3 check_gdp_skipped.py
"""
import csv
import io
import urllib.request

GDP_URL = (
    "https://ourworldindata.org/grapher/gdp-per-capita-worldbank.csv"
    "?v=1&csvType=full&useColumnShortNames=false"
)

req = urllib.request.Request(GDP_URL, headers={"User-Agent": "Our World In Data data fetch/1.0"})
with urllib.request.urlopen(req) as r:
    content = r.read().decode("utf-8")

reader = csv.DictReader(io.StringIO(content))
skipped_entities = set()
for row in reader:
    code = row["Code"]
    if not code or len(code) != 3:
        skipped_entities.add((row["Entity"], code))

print(f"Total distinct skipped entities: {len(skipped_entities)}")
print("\nSample (first 30):")
for entity, code in sorted(skipped_entities)[:30]:
    print(f"  {entity:<40} code='{code}'")
