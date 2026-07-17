# BRAIN Data Fields Reference

Common MATRIX data fields. Use this reference FIRST before hitting the live API.

## Price & Returns (dataset: pv1)

| Field ID | Description | Notes |
|----------|-------------|-------|
| `returns` | Daily returns | Most commonly used |
| `close` | Daily close price | Corporate actions need adjfactor |
| `open` | Daily open price | |
| `high` | Daily high price | |
| `low` | Daily low price | |
| `volume` | Daily trading volume | Shares |
| `vwap` | Volume-weighted average price | |
| `cap` | Daily market capitalization | Millions USD |
| `adjfactor` | Cumulative adjustment factor | For split-adjusted prices |
| `close_unadj` | Unadjusted close price | |
| `volume_unadj` | Unadjusted volume | |

## Fundamentals

| Field ID | Dataset | Description |
|----------|---------|-------------|
| `market_capitalization_usd_3_fast_d1` | forward_beta_risk | Market cap in USD |
| `market_cap_logarithm` | risk62 | Log market cap |
| `return_assets` | fundamental6 | Return on Assets (ROA) |
| `pe_ratio` | fundamental6 | Price-to-Earnings ratio |
| `pb_ratio` | fundamental6 | Price-to-Book ratio |
| `ps_ratio` | fundamental6 | Price-to-Sales ratio |
| `dividend_yield` | fundamental6 | Dividend yield |
| `earnings_yield` | fundamental6 | Earnings yield (E/P) |
| `book_value` | fundamental6 | Book value per share |
| `enterprise_value` | fundamental6 | Enterprise value |
| `debt_to_equity` | fundamental6 | Debt-to-Equity ratio |
| `roe` | fundamental6 | Return on Equity |
| `roa` | fundamental6 | Return on Assets |
| `gross_margin` | fundamental6 | Gross profit margin |
| `operating_margin` | fundamental6 | Operating profit margin |
| `net_margin` | fundamental6 | Net profit margin |
| `revenue_growth` | fundamental6 | Revenue growth YoY |
| `earnings_growth` | fundamental6 | Earnings growth YoY |

## Analyst Estimates (dataset: analyst15)

| Field ID | Description |
|----------|-------------|
| `anl15_sal_s_cal_fy0_total` | Total revenue estimate, current fiscal year |
| `anl15_eps_s_cal_fy0_mean` | EPS estimate, current fiscal year |
| `anl15_sal_s_cal_fy1_total` | Total revenue estimate, next fiscal year |
| `anl15_eps_s_cal_fy1_mean` | EPS estimate, next fiscal year |
| `anl15_rec_mean` | Mean analyst recommendation |
| `anl15_pt_mean` | Mean price target |

## Volatility & Risk

| Field ID | Dataset | Description |
|----------|---------|-------------|
| `volatility_90d` | risk | 90-day annualized volatility |
| `beta_90d` | risk | 90-day beta vs market |
| `close_to_close_volatility_180d_medium_term` | option_horizon_decomp | Historical volatility 180d, medium term |
| `short_interest` | pv1 | Short interest ratio |
| `short_interest_pct` | pv1 | Short interest % of float |

## Classification (Grouping Fields)

| Field ID | Dataset | Description | Type |
|----------|---------|-------------|------|
| `sector` | classification | Sector classification | int32 (categorical) |
| `industry` | classification | Industry classification | int32 (categorical) |
| `subindustry` | classification | Sub-industry classification | int32 (categorical) |
| `country` | classification | Country of listing | int32 (categorical) |

## Technical Indicators

| Field ID | Dataset | Description |
|----------|---------|-------------|
| `volume_fluctuation_score` | pv_tech_indicators | Volume fluctuation score |
| `volume_change_indicator` | pv_tech_indicators | Volume change indicator |
| `sector_12mo_marketcap_percent` | analyst15 | Sector market cap percentage |

## Key Notes

- MATRIX fields arrive as 2-D ndarray `[lookback+1, n_instruments]`, dtype float32, read-only
- VECTOR fields, GLB region, and multi-sim are NOT supported in Python Alphas
- **int32 fields**: Missing values use `np.iinfo(np.int32).min` (-2147483648) as sentinel
  - Use `from brain import get_missing_value; missing = get_missing_value(arr.dtype)` 
  - Then cast: `arr_float[arr == missing] = np.nan`
- `data.universe[-1]` for today's in-universe mask (int 1/0)
- Set simulation lookback >= largest ts_* window
- For unknown fields, query: `cnhkmcp.get_datafields(data_type='MATRIX', search=<field_id>)`
