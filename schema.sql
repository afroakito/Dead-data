-- country_year: one row per (country code, year)
-- Wide format: each new metric becomes a new column over time.
--
-- Design principles:
--   1. Raw values are never overwritten. suicide_rate stores exactly
--      what the source (WHO Mortality Database via Our World in Data) reports.
--   2. suicide_rate_flag is a DERIVED interpretation, computed separately,
--      and can be recomputed later without touching the raw value.
--   3. population starts NULL and gets filled from a separate source later.

CREATE TABLE IF NOT EXISTS country_year (
    code              TEXT    NOT NULL,   -- ISO3 country/territory code, e.g. "ALB"
    entity            TEXT    NOT NULL,   -- display name, e.g. "Albania"
    year              INTEGER NOT NULL,

    suicide_rate      REAL,               -- raw value, deaths per 100,000, age-standardized
    suicide_rate_flag TEXT,               -- 'plausible_zero' | 'suspect_zero' | NULL

    population        INTEGER,            -- nullable until populated from another source

    PRIMARY KEY (code, year)
);
