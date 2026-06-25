# Dead Data — Question Log

## Q1: Does GDP per capita correlate with suicide rate globally?

**Status:** Closed — null result

**Question stated precisely:**
Is there a linear correlation between GDP per capita and suicide rate
across sovereign countries, pooled globally, post-1990?

**Method:**
- Source: WHO Mortality Database (suicide rate) + World Bank via OWID (GDP)
- Scope: sovereign countries only, 1990–2023, rows with both metrics present
- Excluded: suspect_zero flagged rows
- Metric: Pearson r (pooled, cross-country and cross-year)
- n = 2,806 country-year observations, 107 countries

**Result:**
r = 0.004 — near zero. No linear relationship.

**What this means:**
Wealthier countries do not systematically have higher or lower suicide rates
when data is pooled globally across all years. The relationship, if one exists,
is not simple or linear at this level of aggregation.

**Why this is a real finding, not a failure:**
- Strong prior assumption exists (wealth should correlate with mental health outcomes)
- The data directly contradicts the naive assumption
- Known examples confirm heterogeneity: Japan and South Korea (high GDP, high rate),
  Italy and Spain (high GDP, low rate), Guyana (low GDP, highest rate in dataset)

**Known limitations:**
- Pooled correlation masks within-country trends over time
- Post-1990 only (World Bank GDP data constraint)
- 53% of sovereign countries absent from WHO data (mostly Global South)
  — systematic bias toward wealthier, institutionally stable countries
- Linear correlation cannot detect non-linear relationships
- No controls for confounders (inequality, alcohol, cultural factors, age structure)

**Next questions this opens (parked until Q2 is closed):**
- Q2: Within-country correlation — does GDP change within a country over time
  predict suicide rate change in the same country? (fixed-effects style)
- Q3: Does the relationship differ by region or income group?

**Logged:** 2026-06-26

---

## Q1 vs Q2 — Key Distinction (worth remembering)

**Q1 is dominated by data coverage.**
Countries with long data histories (Japan 73 years, USA 73 years, France 73 years)
pull the pooled correlation heavily. All are wealthy, institutionally stable countries.
Q1's r = 0.004 is really a statement about wealthy countries with good data systems
— not a truly global statement.

**Q2 corrects for this partially.**
Each country gets one r value regardless of how many years of data it has.
A country with 10 years counts the same as one with 70 years.
Every country gets one vote.

**The difference in weighting:**
- Q1: equal weight per observation (row) → long-history countries dominate
- Q2: equal weight per country → every country counts once

This is the same data coverage problem that `data_coverage` table was built to flag —
not just which countries are missing entirely, but which countries dominate
the calculation through sheer data volume.

---

## Q2: Within-country correlation between GDP and suicide rate over time

**Status:** Open

**Question stated precisely:**
For each sovereign country individually, does GDP per capita change over time
correlate with suicide rate change in the same country?
Compute one Pearson r per country, then examine the distribution of those r values.

**Pre-defined success criteria:**
- A distribution of per-country r values (one per country)
- Summary: % of countries negative, % positive, % near zero
- Minimum 10 years of overlapping GDP + suicide data required per country

**Pre-defined next actions:**
- Signal found (clear directional trend) → record in pair_results + country_pair_results,
  investigate which regions drive it
- Null again (scattered around zero) → record, park GDP entirely, move to next variable

**Known methodological limitations (flagged before running):**
- Maximum ~30 year window per country (GDP data starts 1990)
- Within-country trends confounded by time itself (global trends affect all countries)
- Minimum 10-year threshold means some countries excluded

**Logged:** 2026-06-26

**Result:**
Median r = -0.4925 across 95 countries. Not null — real signal found.

54% of countries (51/95): negative r < -0.3 — GDP up, suicide down
24% of countries (23/95): neutral — no clear relationship
22% of countries (21/95): positive r > +0.3 — GDP up, suicide up

**Top negative (GDP up, suicide down):**
Austria -0.971, Slovakia -0.967, Latvia -0.964, Serbia -0.954, Switzerland -0.952
Mostly European, post-Soviet countries.

**Top positive (GDP up, suicide up):**
Turkey +0.911, Paraguay +0.852, Suriname +0.849, Dominican Republic +0.831
Mostly rapidly developing economies — Latin America, Southeast Asia.

**What this means:**
The same variable — GDP growth — predicts opposite outcomes depending on country.
European/post-Soviet: economic growth accompanied falling suicide rates.
Developing economies: rapid economic growth accompanied rising suicide rates.
Possible explanation: urbanization, social disruption, breakdown of traditional
community structures accompanying rapid growth in developing contexts.

**Why Q1 showed null but Q2 shows signal:**
Q1 pooled all country-years together — heterogeneous signals canceled out to ~zero.
Q2 revealed that the cancellation was real: two opposing patterns exist simultaneously.
The global null was hiding two real regional signals pointing in opposite directions.

**Status: Closed — signal found, heterogeneous**
**Logged:** 2026-06-26
