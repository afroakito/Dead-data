-- Dead Data: Supabase schema
-- Run this in Supabase SQL Editor before syncing.

-- Core data table
CREATE TABLE IF NOT EXISTS country_year_data (
    code                TEXT    NOT NULL,
    entity              TEXT    NOT NULL,
    year                INTEGER NOT NULL,
    suicide_rate        FLOAT,
    suicide_rate_flag   TEXT,
    population          BIGINT,
    gdp_per_capita      FLOAT,
    PRIMARY KEY (code, year)
);

-- Coverage gaps table
CREATE TABLE IF NOT EXISTS data_gaps (
    code        TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    has_suicide BOOLEAN NOT NULL,
    row_count   INTEGER,
    year_min    INTEGER,
    year_max    INTEGER,
    gap_reason  TEXT
);

-- Correlation results table
CREATE TABLE IF NOT EXISTS pair_results (
    pair_id         TEXT    PRIMARY KEY,
    variable_a      TEXT    NOT NULL,
    variable_b      TEXT    NOT NULL,
    r_value         FLOAT,
    n_observations  INTEGER,
    scope           TEXT,
    method          TEXT,
    status          TEXT,
    null_reason     TEXT,
    notes           TEXT,
    tested_on       DATE
);
