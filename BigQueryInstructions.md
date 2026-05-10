# Digital Footprints of the Unobserved Economy

Working thesis title: "Digital Footprints of the Unobserved Economy: A Recalibration of the MIMIC Model by Integrating News Activity Indicators"

This file defines the extraction plan for a GDELT/BigQuery news-sentiment dataset that can be used as an auxiliary digital-footprint layer in a MIMIC-style shadow economy analysis.

## 1. Research Objective

Build a reproducible, cost-controlled pipeline that extracts GDELT article-level records from 2016 to the latest available complete GDELT day for:

- Romania, Italy, Spain, Portugal, Belgium, and Germany.
- Articles where the target country appears in `V2Locations` (FIPS code match).
- Web-content articles only (`SourceCollectionIdentifier = 1`).
- Economic, fiscal, labor-market, cost-of-living, institutional, corruption, and shadow-economy-adjacent topics.
- Selected GCAM dictionaries:
  - Loughran-McDonald Financial Sentiment Dictionary.
  - ML-Senticon.
  - WordNet-Affect.
  - Hedometer.

The pipeline should produce:

1. Article-level Parquet, preserving enough raw GDELT fields to reprocess later.
2. Daily, monthly, quarterly, and yearly aggregate Parquet panels.

Romania is the main research target, but all six countries should be processed consistently to allow comparative analysis.

## 2. Core Data Source

Use the partitioned GDELT GKG table:

```sql
`gdelt-bq.gdeltv2.gkg_partitioned`
```

Always filter using the partition pseudocolumn:

```sql
_PARTITIONTIME >= TIMESTAMP(@start_date)
AND _PARTITIONTIME < TIMESTAMP(@end_date)
```

Do not query `gdelt-bq.gdeltv2.gkg` for the main extraction. Do not rely on `LIMIT` to control cost.

Use BigQuery dry runs before every execution and enforce `maximum_bytes_billed`.

## 3. Date Range

Default extraction range:

```text
start_date = 2016-01-01
end_date = latest complete GDELT partition, exclusive
```

As of the planning date, use:

```text
2016-01-01 <= date < 2026-05-05
```

At implementation time, detect the latest available complete GDELT day and write the exact `end_date` to the run manifest.

## 4. Country Scope

Target countries:

| Country | ISO3 | GDELT/FIPS-style source country code to validate |
|---|---:|---:|
| Romania | ROU | RO |
| Italy | ITA | IT |
| Spain | ESP | SP |
| Portugal | PRT | PO |
| Belgium | BEL | BE |
| Germany | DEU | GM |

Important: GDELT uses FIPS-style country codes in many places, not ISO alpha-2. Validate these codes against the actual source-country table before the full run.

## 5. Country Filtering Strategy

Filter articles by the presence of a target-country FIPS code in `V2Locations`. This captures articles where the target country is a geographically identified location in the article, regardless of where the source is published.

```sql
REGEXP_EXTRACT(V2Locations, r'#(RO|IT|SP|PO|BE|GM)#') AS fips_country
```

Apply in the `WHERE` clause:

```sql
AND REGEXP_CONTAINS(V2Locations, r'#(RO|IT|SP|PO|BE|GM)#')
```

Then map FIPS to country name in a downstream CTE:

```sql
CASE fips_country
  WHEN 'RO' THEN 'Romania'
  WHEN 'IT' THEN 'Italy'
  WHEN 'SP' THEN 'Spain'
  WHEN 'PO' THEN 'Portugal'
  WHEN 'BE' THEN 'Belgium'
  WHEN 'GM' THEN 'Germany'
END AS country_name
```

Additional base filters:

- `SourceCollectionIdentifier = 1` — web content only (exclude broadcast and print transcripts).
- `V2Tone IS NOT NULL` — exclude rows with no tone vector.

## 6. Topic Filtering Strategy

The article should pass based on topic only. Do not require country mentions.

Use `V2Themes`, not full-text search, for the baseline extraction. Parse it by stripping the character offsets:

```sql
ARRAY(
  SELECT DISTINCT REGEXP_REPLACE(theme_part, r',.*$', '')
  FROM UNNEST(SPLIT(IFNULL(V2Themes, ''), ';')) AS theme_part
  WHERE theme_part IS NOT NULL AND theme_part != ''
) AS themes
```

### Critical Caveat About `TAX_`

Do not use a blanket `theme LIKE 'TAX_%'` filter as a taxation proxy. In GDELT, many `TAX_` themes are taxonomy labels unrelated to tax burden, such as function, ethnicity, language, or occupation tags.

Instead:

1. Build a topic whitelist from actual observed themes.
2. Include `TAX_` themes only if manual inspection shows they are substantively fiscal/tax-related.
3. Prefer exact or carefully reviewed economic/fiscal themes, such as taxation, fiscal policy, cost of living, banking, inflation, unemployment, poverty, recession, austerity, corruption, bribery, informality, cash, and crime-related themes.

## 7. Topic Discovery Step

Before the full extraction, run a bounded theme-discovery query over representative periods:

- 2016 Q1.
- 2019 Q4.
- 2020 Q2.
- 2022 Q2.
- 2024 Q1.
- Latest complete quarter.

For target source countries only, count themes matching these stems:

```text
TAX
FISCAL
INFLATION
UNEMPLOYMENT
POVERTY
RECESSION
AUSTERITY
BANK
COSTLIVING
COST_OF_LIVING
CORRUPT
BRIBE
BRIBERY
EVASION
INFORMAL
UNDERGROUND
BLACK_MARKET
ILLICIT
SMUGGL
CASH
PAYMENT
CRIME
FRAUD
REGULATION
BUREAUCRACY
RULE_OF_LAW
```

Save results to:

```text
config/gdelt_topic_candidates.csv
```

Required columns:

```text
theme
sample_article_count
sample_countries_seen
matched_keyword
review_status
topic_group
include
notes
```

Only use themes with `include = true` in the main extraction.

## 8. Initial Topic Groups

Start with these conceptual groups. The exact GDELT theme whitelist must come from the topic-discovery step.

| Topic group | MIMIC rationale | Candidate theme stems |
|---|---|---|
| tax_burden | Classical shadow-economy cause: tax and social contribution pressure | TAXATION, FISCAL, TAX, PUBLIC_REVENUE |
| inflation_cost_living | Macroeconomic pressure, purchasing-power stress, informality incentives | INFLATION, COSTLIVING, COST_OF_LIVING, ECON_PRICE |
| unemployment_labor | Classical shadow-economy cause: unemployment and labor-market exclusion | UNEMPLOYMENT, LABOR, JOBS, WAGES, STRIKE |
| poverty_social_stress | Informality and subsistence-pressure channel | POVERTY, INEQUALITY, SOCIAL_PROTECTION |
| recession_growth | Formal-sector weakness and cyclical pressure | RECESSION, GDP, GROWTH, DOWNTURN |
| austerity_fiscal_adjustment | Fiscal consolidation and public-service pressure | AUSTERITY, FISCAL, PUBLIC_SPENDING, BUDGET |
| banking_finance_cash | Cash usage, financial exclusion, payment traceability | BANKING, CASH, PAYMENTS, CREDIT, DEBT |
| regulation_bureaucracy | Regulatory burden, business freedom, compliance costs | REGULATION, BUREAUCRACY, BUSINESS_FREEDOM |
| institutions_rule_law | Rule of law, institutional quality, tax morale | RULE_OF_LAW, INSTITUTION, JUSTICE, GOVERNANCE |
| corruption_bribery | Shadow-economy-adjacent institutional channel | CORRUPTION, BRIBERY, FRAUD |
| illicit_informal_activity | Direct shadow-economy narrative channel | INFORMAL, UNDERGROUND, BLACK_MARKET, ILLICIT, SMUGGLING |
| crime_enforcement | Enforcement, deterrence, illegality proxy | CRIME, POLICE, PROSECUTION, COURT |

## 9. GCAM Dictionary Scope

Use the `GCAM` field from GKG. Preserve the parsed GCAM features as an array of `{dict_key, dict_value}` structs in the article-level Parquet.

Extract only the following key prefixes, validated against the Tilly et al. (2020) codebook:

| Dictionary | Key prefix | Value type | Notes |
|---|---|---|---|
| Loughran-McDonald Financial Sentiment | `c6.*` | word count | Litigious, modal-strong, modal-weak, negative, positive, uncertainty dimensions. |
| ML-Senticon | `c14.*` | word count | Validated against Tilly et al. |
| WordNet-Affect | `c20.*` | word count | Validated against Tilly et al. |
| WordNet-Affect valence | `v20.*` | scored value | Extension beyond Tilly et al. |
| Hedometer | `c21.*` | word count | Validated against Tilly et al. |
| Hedometer valence | `v21.*` | scored value | Extension beyond Tilly et al. |

GCAM extraction SQL:

```sql
(
  SELECT ARRAY_AGG(STRUCT(
    SPLIT(kv, ':')[SAFE_OFFSET(0)] AS dict_key,
    SAFE_CAST(SPLIT(kv, ':')[SAFE_OFFSET(1)] AS FLOAT64) AS dict_value
  ))
  FROM UNNEST(SPLIT(GCAM, ',')) kv
  WHERE REGEXP_CONTAINS(
    SPLIT(kv, ':')[SAFE_OFFSET(0)],
    r'^(c6|c14|c20|v20|c21|v21)\.'
  )
) AS gcam_features
```

Rules:

1. Store missing GCAM keys as null, not zero.
2. For `c*` word-count fields, create density features at the aggregation stage: `count / word_count`.
3. For `v*` scored-value fields, do not divide by word count.
4. Record coverage separately at aggregation: `share_articles_with_<key>`.

## 10. Article-Level Parquet

Output path:

```text
data/gdelt/article_level/
```

Partitioning:

```text
source_country_iso3=<ISO3>/year=<YYYY>/month=<MM>/
```

Output columns (matching the validated example query output):

```text
country_name              STRING    — full country name (e.g. Romania)
fips_country              STRING    — GDELT/FIPS-style code (RO, IT, SP, PO, BE, GM)
article_date              DATE      — parsed from GDELT integer date field
yr                        INT64     — EXTRACT(YEAR FROM article_date)
mo                        INT64     — EXTRACT(MONTH FROM article_date)
dy                        INT64     — EXTRACT(DAY FROM article_date)
primary_theme             STRING    — first matched theme from regex extraction
all_matched_themes        ARRAY<STRING>  — all matched themes from regex extraction
confidence_score          INT64     — MAX(Confidence) from eventmentions_partitioned; 0 if unmatched
sentiment_score           FLOAT64   — V2Tone[0]: average tone
positive_score            FLOAT64   — V2Tone[1]: positive score
negative_score            FLOAT64   — V2Tone[2]: negative score
polarity                  FLOAT64   — V2Tone[3]: polarity
word_count                INT64     — V2Tone[6]: article word count
activity_ref_density      FLOAT64   — V2Tone[4]: activity reference density
self_group_ref_density    FLOAT64   — V2Tone[5]: self/group reference density
source_name               STRING    — SourceCommonName
article_url               STRING    — DocumentIdentifier
gcam_features             ARRAY<STRUCT<dict_key STRING, dict_value FLOAT64>>
                                    — parsed GCAM keys c6.*, c14.*, c20.*, v20.*, c21.*, v21.*
```

Notes:

- `article_date` is derived from GDELT's `DATE` integer field: `PARSE_DATE('%Y%m%d', CAST(FLOOR(DATE / 1000000) AS STRING))`.
- `confidence_score` is joined from `gdelt-bq.gdeltv2.eventmentions_partitioned` on `MentionIdentifier = DocumentIdentifier`, `MAX(Confidence)` per URL, defaulting to 0 when no match.
- `gcam_features` is a struct array, not individual columns, to keep schema stable across GCAM key additions.

## 11. Aggregate Parquet

Output path:

```text
data/gdelt/aggregates/
```

Partitioning:

```text
frequency=<daily|monthly|quarterly|yearly>/source_country_iso3=<ISO3>/
```

Produce four frequencies:

- Daily: useful for checking dynamics and later re-aggregation.
- Monthly: closest to the macro-forecasting paper.
- Quarterly: likely main MIMIC frequency.
- Yearly: robustness and thesis presentation layer.

Aggregate keys:

```text
period_start
period_end
frequency
source_country_iso3
source_country_name
topic_group
```

Core aggregate variables:

```text
article_count
source_count
mean_articles_per_source
median_articles_per_source
tone_mean
tone_std
tone_positive_mean
tone_negative_mean
tone_polarity_mean
gcam_<dimension>_mean
gcam_<dimension>_std
gcam_<dimension>_coverage_share
gcam_<dimension>_sum_count
```

For word-count GCAM dimensions:

- Use density means as the main sentiment/emotion level.
- Keep count sums as intensity/volume proxies.
- Keep coverage shares to avoid interpreting sparse dictionaries as strong signals.

For scored-value GCAM dimensions:

- Use article-level means and standard deviations.
- Consider weighted means using matched word counts only as a robustness variant.

## 12. Cost-Controlled BigQuery Workflow

Use modes:

```text
dry_run
execute
```

Dry run:

- Builds the query plan.
- Runs BigQuery dry-run jobs only.
- Prints estimated bytes per chunk and total.
- Does not download rows.

Execute:

- Requires explicit confirmation.
- Enforces `maximum_bytes_billed`.
- Logs job ID, bytes processed, bytes billed, duration, and row count.
- Writes Parquet and manifest files.

Chunking:

- Do not run one query per date.
- Do not run one query per country.
- Prefer yearly chunks for the 2016-present article-level backfill.
- Use quarterly chunks only if yearly result sets are too large to download/write safely.
- Hard cap: `MAX_CHUNKS = 44`, which allows quarterly chunks from 2016 through 2026.

Recommended initial run sequence:

1. `dry_run` one month, all countries.
2. `execute` one month, all countries.
3. Validate country coverage, topic matches, GCAM parsing, output row counts.
4. `dry_run` one full year.
5. If acceptable, execute yearly chunks for the full history.

## 13. BigQuery SQL Structure

The query is structured as four CTEs. This is the validated pattern from the one-month example run.

```sql
WITH
-- CTE 1: Extract and filter GKG (target countries & fiscal themes)
gkg_fiscal AS (
  SELECT
    CAST(FLOOR(DATE / 1000000) AS INT64) AS date_int,
    SourceCommonName AS source_name,
    DocumentIdentifier AS article_url,
    V2Themes AS matched_themes,
    GCAM,
    REGEXP_EXTRACT(
      COALESCE(V2Themes, '') || ';' || COALESCE(Themes, ''),
      r'(?i)(<THEME_REGEX>)'
    ) AS primary_theme,
    REGEXP_EXTRACT_ALL(
      COALESCE(V2Themes, '') || ';' || COALESCE(Themes, ''),
      r'(?i)(<THEME_REGEX>)'
    ) AS all_matched_themes,
    REGEXP_EXTRACT(V2Locations, r'#(RO|IT|SP|PO|BE|GM)#') AS fips_country,
    -- V2Tone vector parsing
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(1)] AS FLOAT64) AS positive_score,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(2)] AS FLOAT64) AS negative_score,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(3)] AS FLOAT64) AS polarity,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(4)] AS FLOAT64) AS activity_ref_density,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(5)] AS FLOAT64) AS self_group_ref_density,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(6)] AS INT64)   AS word_count
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE
    _PARTITIONTIME >= TIMESTAMP(@start_date)
    AND _PARTITIONTIME < TIMESTAMP(@end_date)
    AND SourceCollectionIdentifier = 1
    AND V2Tone IS NOT NULL
    AND REGEXP_CONTAINS(
      COALESCE(V2Themes, '') || ';' || COALESCE(Themes, ''),
      r'(?i)(<THEME_REGEX>)'
    )
),

-- CTE 2: Data formatting & country name mapping
gkg_filtered AS (
  SELECT
    *,
    PARSE_DATE('%Y%m%d', CAST(date_int AS STRING)) AS article_date,
    CASE fips_country
      WHEN 'RO' THEN 'Romania'
      WHEN 'IT' THEN 'Italy'
      WHEN 'SP' THEN 'Spain'
      WHEN 'PO' THEN 'Portugal'
      WHEN 'BE' THEN 'Belgium'
      WHEN 'GM' THEN 'Germany'
    END AS country_name
  FROM gkg_fiscal
  WHERE fips_country IS NOT NULL
),

-- CTE 3: Confidence scores from EventMentions
confidence_scores AS (
  SELECT
    MentionIdentifier AS article_url,
    MAX(Confidence) AS gdelt_confidence
  FROM `gdelt-bq.gdeltv2.eventmentions_partitioned`
  WHERE
    _PARTITIONTIME >= TIMESTAMP(@start_date)
    AND _PARTITIONTIME < TIMESTAMP(@end_date)
    AND Confidence IS NOT NULL
  GROUP BY MentionIdentifier
),

-- CTE 4: Join & GCAM array extraction
joined_data AS (
  SELECT
    g.country_name,
    g.fips_country,
    g.article_date,
    EXTRACT(YEAR  FROM g.article_date) AS yr,
    EXTRACT(MONTH FROM g.article_date) AS mo,
    EXTRACT(DAY   FROM g.article_date) AS dy,
    g.primary_theme,
    g.all_matched_themes,
    COALESCE(c.gdelt_confidence, 0) AS confidence_score,
    g.tone                AS sentiment_score,
    g.positive_score,
    g.negative_score,
    g.polarity,
    g.word_count,
    g.activity_ref_density,
    g.self_group_ref_density,
    g.source_name,
    g.article_url,
    (
      SELECT ARRAY_AGG(STRUCT(
        SPLIT(kv, ':')[SAFE_OFFSET(0)] AS dict_key,
        SAFE_CAST(SPLIT(kv, ':')[SAFE_OFFSET(1)] AS FLOAT64) AS dict_value
      ))
      FROM UNNEST(SPLIT(g.GCAM, ',')) kv
      WHERE REGEXP_CONTAINS(
        SPLIT(kv, ':')[SAFE_OFFSET(0)],
        r'^(c6|c14|c20|v20|c21|v21)\.'
      )
    ) AS gcam_features
  FROM gkg_filtered g
  LEFT JOIN confidence_scores c ON g.article_url = c.article_url
)

-- c6  → Loughran-McDonald Financial Sentiment
-- c14 → ML-Senticon
-- c20 → WordNet-Affect (word count)
-- v20 → WordNet-Affect valence (scored)
-- c21 → Hedometer (word count)
-- v21 → Hedometer valence (scored)

SELECT * FROM joined_data
ORDER BY country_name, article_date;
```

`<THEME_REGEX>` must be replaced with the validated theme regex from the topic whitelist (see section 8). For the current extraction the regex covers:

```text
ECON_TAXATION|ECON_NATIONALDEBT|ECON_DEBT|FISCAL|AUSTERITY|GOV_SPENDING|DEFICIT|BUDGET|
SOVEREIGN_DEBT|CREDIT_RATING|WB_\d+_FISCAL|WB_\d+_PUBLIC_DEBT|EPU_POLICY|EPU_ECONOMY|
ECON_SOCIAL_WELFARE|ECON_PENSION|ECON_BENEFITS|WB_\d+_SOCIAL_PROTECTION|ECON_SUBSIDIES|
ECON_UNEMPLOYMENT|ECON_WAGES|ECON_LABOR|ECON_WORKFORCE|WB_\d+_LABOR_MARKET|WB_\d+_EMPLOYMENT|
WB_\d+_GOVERNANCE|ECON_RECESSION|ECON_RECOVERY|ECON_GROWTH|ECON_INFLATION|MONETARY_POLICY|
CENTRAL_BANK|ECON_INTEREST_RATE|CORRUPTION|ECON_REMITTANCE|WB_\d+_INFORMAL|ECON_TRADE|
ECON_FOREIGNINVESTMENT|ECON_STOCKMARKET|ECON_MANUFACTURING|ECON_INDUSTRY|ECON_RETAIL|
ECON_HOUSING|ECON_CONSTRUCTION|WB_\d+_PRIVATE_SECTOR|ECON_ENERGY|ENERGY_PRICES|ENERGY_CRISIS|
WB_\d+_ENERGY|ECON_BANKING|BANK_CRISIS|FINANCIAL_CRISIS|ECON_CREDIT|ECON_LENDING|
WB_\d+_FINANCIAL_SECTOR|ECON_BANKRUPTCY|ECON_COST_OF_LIVING|ECON_EARNINGSREPORT|
EU_FUND|COHESION_FUND|STRUCTURAL_FUND
```

## 14. Parquet and Manifest Rules

Every pipeline run writes a manifest:

```text
metadata/runs/<run_id>.json
```

Required fields:

```text
run_id
mode
started_at_utc
finished_at_utc
git_commit
query_hash
start_date
end_date
chunks
countries
total_bigquery_jobs
total_bytes_processed
total_bytes_billed
total_rows_written
output_paths
```

Idempotency:

- Output paths should include deterministic country/year/month partitions.
- Re-running the same extraction should replace the same partition, not append duplicates.
- Store `extraction_run_id` as metadata, not as part of the article uniqueness key.

Article uniqueness key:

```text
source_name + article_url + article_date
```

## 15. Quality Checks

Run these checks after each extraction chunk:

1. No null `fips_country` or `country_name`.
2. No null `article_url`.
3. No duplicate `article_url` within the same `article_date` and `country_name`.
4. All rows have at least one entry in `all_matched_themes`.
5. `word_count` is positive.
6. Top source names per country look plausible.
7. Topic distribution by country is not dominated by accidental taxonomy tags.
8. Daily article counts do not have unexplained large gaps.
9. GCAM key coverage is recorded and reviewed.

Generate reports:

```text
reports/topic_distribution.parquet
reports/gcam_coverage.parquet
reports/daily_article_counts.parquet
```

## 16. Implementation Order

1. Create config files:
   - `config/countries.csv`.
   - `config/gdelt_topic_whitelist.csv`.
2. Implement BigQuery dry-run planner.
3. Implement topic-discovery query (section 7).
4. Review and freeze the topic regex whitelist.
5. Implement article-level extraction (one-month chunk).
6. Validate output against `data/Example_Query_Output.csv` schema.
7. Run yearly or quarterly backfill from 2016 to present.
8. Implement aggregate panel builder.

## 17. References Consulted

- GDELT partitioned BigQuery tables: https://blog.gdeltproject.org/announcing-partitioned-gdelt-bigquery-tables/
- BigQuery partitioned tables and pruning: https://cloud.google.com/bigquery/docs/partitioned-tables
- BigQuery dry runs and maximum bytes billed: https://cloud.google.com/bigquery/docs/running-queries
- GDELT GCAM introduction: https://blog.gdeltproject.org/introducing-the-global-content-analysis-measures-gcam/
- Tilly, Ebner, Livan. "Macroeconomic forecasting through news, emotions and narrative": https://arxiv.org/abs/2009.14281
- Zhang. "Interpretable Machine Learning for Macro Alpha: A News Sentiment Case Study": https://arxiv.org/abs/2505.16136
- Dybka et al. "Currency demand and MIMIC models": https://link.springer.com/article/10.1007/s10797-018-9504-5
- Hassan and Schneider. "Size and Development of the Shadow Economies of 157 Countries Worldwide": https://www.iza.org/publications/dp/10281
