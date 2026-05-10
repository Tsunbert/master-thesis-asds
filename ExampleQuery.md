WITH 
-- ─── CTE 1: Extract and Filter GKG (Target Countries & Fiscal Themes) ────
gkg_fiscal AS (
  SELECT
    CAST(FLOOR(DATE / 1000000) AS INT64) AS date_int,
    SourceCommonName AS source_name,
    DocumentIdentifier AS article_url,
    V2Themes AS matched_themes,
    GCAM,
    REGEXP_EXTRACT(
      COALESCE(V2Themes, '') || ';' || COALESCE(Themes, ''),
      r'(?i)(ECON_TAXATION|ECON_NATIONALDEBT|ECON_DEBT|FISCAL|AUSTERITY|GOV_SPENDING|DEFICIT|BUDGET|SOVEREIGN_DEBT|CREDIT_RATING|WB_\d+_FISCAL|WB_\d+_PUBLIC_DEBT|EPU_POLICY|EPU_ECONOMY|ECON_SOCIAL_WELFARE|ECON_PENSION|ECON_BENEFITS|WB_\d+_SOCIAL_PROTECTION|ECON_SUBSIDIES|ECON_UNEMPLOYMENT|ECON_WAGES|ECON_LABOR|ECON_WORKFORCE|WB_\d+_LABOR_MARKET|WB_\d+_EMPLOYMENT|WB_\d+_GOVERNANCE|ECON_RECESSION|ECON_RECOVERY|ECON_GROWTH|ECON_INFLATION|MONETARY_POLICY|CENTRAL_BANK|ECON_INTEREST_RATE|CORRUPTION|ECON_REMITTANCE|WB_\d+_INFORMAL|ECON_TRADE|ECON_FOREIGNINVESTMENT|ECON_STOCKMARKET|ECON_MANUFACTURING|ECON_INDUSTRY|ECON_RETAIL|ECON_HOUSING|ECON_CONSTRUCTION|WB_\d+_PRIVATE_SECTOR|ECON_ENERGY|ENERGY_PRICES|ENERGY_CRISIS|WB_\d+_ENERGY|ECON_BANKING|BANK_CRISIS|FINANCIAL_CRISIS|ECON_CREDIT|ECON_LENDING|WB_\d+_FINANCIAL_SECTOR|ECON_BANKRUPTCY|ECON_COST_OF_LIVING|ECON_EARNINGSREPORT|EU_FUND|COHESION_FUND|STRUCTURAL_FUND)'
    ) AS primary_theme,
    REGEXP_EXTRACT_ALL(
      COALESCE(V2Themes, '') || ';' || COALESCE(Themes, ''),
      r'(?i)(ECON_TAXATION|ECON_NATIONALDEBT|ECON_DEBT|FISCAL|AUSTERITY|GOV_SPENDING|DEFICIT|BUDGET|SOVEREIGN_DEBT|CREDIT_RATING|WB_\d+_FISCAL|WB_\d+_PUBLIC_DEBT|EPU_POLICY|EPU_ECONOMY|ECON_SOCIAL_WELFARE|ECON_PENSION|ECON_BENEFITS|WB_\d+_SOCIAL_PROTECTION|ECON_SUBSIDIES|ECON_UNEMPLOYMENT|ECON_WAGES|ECON_LABOR|ECON_WORKFORCE|WB_\d+_LABOR_MARKET|WB_\d+_EMPLOYMENT|WB_\d+_GOVERNANCE|ECON_RECESSION|ECON_RECOVERY|ECON_GROWTH|ECON_INFLATION|MONETARY_POLICY|CENTRAL_BANK|ECON_INTEREST_RATE|CORRUPTION|ECON_REMITTANCE|WB_\d+_INFORMAL|ECON_TRADE|ECON_FOREIGNINVESTMENT|ECON_STOCKMARKET|ECON_MANUFACTURING|ECON_INDUSTRY|ECON_RETAIL|ECON_HOUSING|ECON_CONSTRUCTION|WB_\d+_PRIVATE_SECTOR|ECON_ENERGY|ENERGY_PRICES|ENERGY_CRISIS|WB_\d+_ENERGY|ECON_BANKING|BANK_CRISIS|FINANCIAL_CRISIS|ECON_CREDIT|ECON_LENDING|WB_\d+_FINANCIAL_SECTOR|ECON_BANKRUPTCY|ECON_COST_OF_LIVING|ECON_EARNINGSREPORT|EU_FUND|COHESION_FUND|STRUCTURAL_FUND)'
    ) AS all_matched_themes,
    -- Strict extraction of the requested 6 reference countries only
    REGEXP_EXTRACT(V2Locations, r'#(RO|IT|SP|PO|BE|GM)#') AS fips_country,

    -- Vector parsing for V2Tone
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(1)] AS FLOAT64) AS positive_score,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(2)] AS FLOAT64) AS negative_score,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(3)] AS FLOAT64) AS polarity,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(4)] AS FLOAT64) AS activity_ref_density,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(5)] AS FLOAT64) AS self_group_ref_density,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(6)] AS INT64) AS word_count

  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE
    _PARTITIONTIME >= TIMESTAMP('2016-01-01')
    --AND _PARTITIONTIME < TIMESTAMP('2026-04-01')
    AND _PARTITIONTIME < TIMESTAMP('2016-02-01')
    AND SourceCollectionIdentifier = 1
    AND V2Tone IS NOT NULL
    AND REGEXP_CONTAINS(
      COALESCE(V2Themes, '') || ';' || COALESCE(Themes, ''),
      r'(?i)(ECON_TAXATION|ECON_NATIONALDEBT|ECON_DEBT|FISCAL|AUSTERITY|GOV_SPENDING|DEFICIT|BUDGET|SOVEREIGN_DEBT|CREDIT_RATING|WB_\d+_FISCAL|WB_\d+_PUBLIC_DEBT|EPU_POLICY|EPU_ECONOMY|ECON_SOCIAL_WELFARE|ECON_PENSION|ECON_BENEFITS|WB_\d+_SOCIAL_PROTECTION|ECON_SUBSIDIES|ECON_UNEMPLOYMENT|ECON_WAGES|ECON_LABOR|ECON_WORKFORCE|WB_\d+_LABOR_MARKET|WB_\d+_EMPLOYMENT|WB_\d+_GOVERNANCE|ECON_RECESSION|ECON_RECOVERY|ECON_GROWTH|ECON_INFLATION|MONETARY_POLICY|CENTRAL_BANK|ECON_INTEREST_RATE|CORRUPTION|ECON_REMITTANCE|WB_\d+_INFORMAL|ECON_TRADE|ECON_FOREIGNINVESTMENT|ECON_STOCKMARKET|ECON_MANUFACTURING|ECON_INDUSTRY|ECON_RETAIL|ECON_HOUSING|ECON_CONSTRUCTION|WB_\d+_PRIVATE_SECTOR|ECON_ENERGY|ENERGY_PRICES|ENERGY_CRISIS|WB_\d+_ENERGY|ECON_BANKING|BANK_CRISIS|FINANCIAL_CRISIS|ECON_CREDIT|ECON_LENDING|WB_\d+_FINANCIAL_SECTOR|ECON_BANKRUPTCY|ECON_COST_OF_LIVING|ECON_EARNINGSREPORT|EU_FUND|COHESION_FUND|STRUCTURAL_FUND)'
    )
),

-- ─── CTE 2: Data Formatting & Country Mapping ────────────────────────────
gkg_filtered AS (
  SELECT
    *,
    -- Convert Integer Date to strict Date type for daily frequency
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
  WHERE 
    fips_country IS NOT NULL
    --AND word_count >= 500
),

-- ─── CTE 3: Event Mentions Pre-Aggregation (Confidence Scoring) ──────────
confidence_scores AS (
  SELECT
    MentionIdentifier AS article_url,
    MAX(Confidence) AS gdelt_confidence
  FROM `gdelt-bq.gdeltv2.eventmentions_partitioned` 
  WHERE
    _PARTITIONTIME >= TIMESTAMP('2016-01-01')
    --AND _PARTITIONTIME < TIMESTAMP('2026-04-01')
    AND _PARTITIONTIME < TIMESTAMP('2016-02-01')
    AND Confidence IS NOT NULL
  GROUP BY MentionIdentifier
),

-- ─── CTE 4: JOIN & GCAM Array Extraction ─────────────────────────────────
joined_data AS (
  SELECT
    g.country_name,
    g.fips_country,
    g.article_date,
    EXTRACT(YEAR FROM g.article_date) AS yr,
    EXTRACT(MONTH FROM g.article_date) AS mo,
    EXTRACT(DAY FROM g.article_date) AS dy,
    g.primary_theme,
    g.all_matched_themes,
    COALESCE(c.gdelt_confidence, 0) AS confidence_score,
    g.tone AS sentiment_score,
    g.positive_score,
    g.negative_score,
    g.polarity,
    g.word_count,
    g.activity_ref_density,
    g.self_group_ref_density,
    g.source_name,
    g.article_url,
    
    -- GCAM Dictionary Extraction Logic
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
  LEFT JOIN confidence_scores c
    ON g.article_url = c.article_url
)

-- c6  → Loughran-McDonald           validat, identic Tilly et al.
-- c14 → ML-Senticon                 validat, identic Tilly et al.
-- c20 → WordNet-Affect              validat, identic Tilly et al.
-- v20 → WordNet-Affect valence      extensia ta față de Tilly et al.
-- c21 → Hedometer                   validat, identic Tilly et al.
-- v21 → Hedometer valence           extensia ta față de Tilly et al.


-- ─── Final Output ────────────────────────────────────────────────────────
SELECT * FROM joined_data
ORDER BY country_name, article_date;


-- Testare diferente semnificative in distributie [evaluam daca ponderam sau filtram confidence %]

-- SELECT 
--   country_name,
--   COUNT(*) AS n_articles,
--   COUNTIF(confidence_score = 0) AS no_confidence_match,
--   ROUND(COUNTIF(confidence_score = 0) / COUNT(*) * 100, 1) AS pct_unmatched,
--   ROUND(AVG(confidence_score), 1) AS avg_confidence,
--   ROUND(AVG(word_count), 0) AS avg_words,
--   MIN(article_date) AS date_min,
--   MAX(article_date) AS date_max
-- FROM joined_data
-- GROUP BY country_name
-- ORDER BY country_name;


-- Testam diferentele de distributie pe tematici in fiecare tara

-- SELECT
--   country_name,
--   theme,
--   COUNT(*) AS n_articles,
--   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY country_name), 2) AS pct_of_country
-- FROM joined_data,
-- UNNEST(all_matched_themes) AS theme
-- GROUP BY country_name, theme
-- ORDER BY country_name, n_articles DESC