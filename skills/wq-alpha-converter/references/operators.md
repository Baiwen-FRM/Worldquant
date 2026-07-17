# BRAIN Operators Reference (Full)

Complete operator reference from platform.worldquantbrain.com/learn/operators.
Level: **base** = available to all, **genius** = Expert/Master/Grandmaster.

---

## Arithmetic

| Operator | Level | Description | Python |
|----------|-------|-------------|--------|
| `abs(x)` | base | Absolute value | `np.abs(x)` |
| `add(x, y, ...)` / `x + y` | base | Element-wise addition; `filter=true` treats NaN as 0 | `np.nansum(np.stack([x,y], axis=0), axis=0)` + nan handling |
| `densify(x)` | base | Converts grouping field to fewer compact buckets | Use `pandas.factorize()` or manual re-mapping |
| `divide(x, y)` / `x / y` | base | Element-wise division | `np.divide(x, y)` |
| `inverse(x)` | base | 1 / x | `np.divide(1, x, out=np.zeros_like(x), where=x!=0)` |
| `log(x)` | base | Natural logarithm | `np.log(x)` — guard `x > 0` |
| `max(x, y, ..)` | base | Element-wise maximum (≥2 inputs) | `np.maximum(x, y)` |
| `min(x, y, ..)` | base | Element-wise minimum (≥2 inputs) | `np.minimum(x, y)` |
| `multiply(x, y, ..)` / `x * y` | base | Element-wise multiplication; `filter=true` treats NaN as 0 | `np.nanprod(np.stack([x,y], axis=0), axis=0)` |
| `power(x, y)` | base | x ^ y | `np.power(x, y)` |
| `reverse(x)` | base | -x | `-x` |
| `sigmoid(x)` | genius | 1 / (1 + exp(-x)) | `1 / (1 + np.exp(-x))` |
| `sign(x)` | base | +1, -1, 0 (NaN → NaN) | `np.sign(x)` |
| `signed_power(x, y)` | base | x^y with sign preserved | `np.sign(x) * np.abs(x)**y` |
| `sqrt(x)` | base | Non-negative square root | `np.sqrt(np.maximum(x, 0))` |
| `subtract(x, y, ...)` / `x - y` | base | Left-to-right subtraction; `filter=true` treats NaN as 0 | `x - y` with nan handling |
| `tanh(x)` | genius | Hyperbolic tangent | `np.tanh(x)` |

## Logical

| Operator | Description | Python |
|----------|-------------|--------|
| `and(x, y)` | 1 if both true | `np.logical_and(x, y).astype(np.float32)` |
| `if_else(cond, a, b)` | cond ? a : b | `np.where(cond.astype(bool), a, b)` |
| `x < y` | 1 if x < y | `(x < y).astype(np.float32)` |
| `x <= y` | 1 if x ≤ y | `(x <= y).astype(np.float32)` |
| `x == y` | 1 if equal | `np.isclose(x, y).astype(np.float32)` or `(x == y).astype(np.float32)` |
| `x > y` | 1 if x > y | `(x > y).astype(np.float32)` |
| `x >= y` | 1 if x ≥ y | `(x >= y).astype(np.float32)` |
| `x != y` | 1 if not equal | `(~np.isclose(x, y)).astype(np.float32)` |
| `is_nan(x)` | 1 if NaN | `np.isnan(x).astype(np.float32)` |
| `not(x)` | Logical negation | `np.logical_not(x).astype(np.float32)` |
| `or(x, y)` | 1 if either true | `np.logical_or(x, y).astype(np.float32)` |

## Time Series

| Operator | Level | Description | Python Strategy |
|----------|-------|-------------|-----------------|
| `days_from_last_change(x)` | base | Days since x last changed | Store prev value in store; count steps since change |
| `hump(x, hump=0.01)` | base | Limits magnitude of day-to-day changes | Store prev value; clamp delta |
| `hump_decay(x, p=0)` | genius | Ignores values that changed too little | EWMA with threshold on change magnitude |
| `kth_element(x, d, k)` | base | K-th value from past d days | Rolling window buffer, index k |
| `last_diff_value(x, d)` | base | Most recent value different from current | Rolling window buffer, find last non-equal |
| `ts_arg_max(x, d)` | base | Days since max in past d days | Rolling window buffer: `d - np.argmax(window[::-1], axis=0) - 1` |
| `ts_arg_min(x, d)` | base | Days since min in past d days | Rolling window buffer: `d - np.argmin(window[::-1], axis=0) - 1` |
| `ts_av_diff(x, d)` | base | x - ts_mean(x, d) | `x[-1] - np.nanmean(window, axis=0)` |
| `ts_backfill(x, d, k=1)` | base | Fill NaN from most recent `d` rows (bounded). `k=1` picks nearest valid; int fields convert sentinel first | Roll window `x[-d:]` (not infinite); vectorized find_last_valid per instrument. For int32 fields: `field_to_float()` first (see data_fields.md) |
| `ts_corr(x, y, d)` | base | Pearson correlation over d days; requires ≥3 overlapping non-NaN pairs per instrument | Rolling window, `np.corrcoef` per instrument on overlapping-valid slice |
| `ts_count_nans(x, d)` | base | Count NaN in past d days | `np.sum(np.isnan(window), axis=0)` |
| `ts_covariance(y, x, d)` | base | Covariance over d days (population, ddof=0) | Rolling window, `np.cov(..., ddof=0)` per instrument on overlapping-valid slice |
| `ts_decay_exp_window(x, d, factor)` | genius | Exponential decay with factor over d days | EWMA: `result = factor * current + (1-factor) * prev` |
| `ts_decay_linear(x, d, dense=false)` | base | Linear decay over d days. `dense=false` skips NaN positions before weighting | Weights = [1,2,...,d]; weighted avg over window. dense=true: only non-NaN positions get weights |
| `ts_delay(x, d)` | base | Value from d days ago | `x[-1-d]` — guard `x.shape[0] > d` |
| `ts_delta(x, d)` | base | x - ts_delay(x, d) | `x[-1] - x[-1-d]` — guard warm-up |
| `ts_entropy(x, d)` | genius | Information entropy over d days via histogram | Histogram binning → probability → entropy |
| `ts_mean(x, d)` | base | Mean over past d days | `np.nanmean(window, axis=0)` |
| `ts_min_diff(x, d)` | genius | x - ts_min(x, d) | `x[-1] - np.nanmin(window, axis=0)` |
| `ts_min_max_cps(x, d, f=2)` | genius | (ts_min+ts_max) - f*x | `(np.nanmin(w)+np.nanmax(w)) - f*x[-1]` |
| `ts_min_max_diff(x, d, f=0.5)` | genius | x - f*(ts_min+ts_max) | `x[-1] - f*(np.nanmin(w)+np.nanmax(w))` |
| `ts_product(x, d)` | base | Product over past d days | `np.nanprod(window, axis=0)` |
| `ts_quantile(x, d)` | base | ts_rank → inverse CDF (default Gaussian). NaN in window → NaN output | `scipy.stats.norm.ppf(ts_rank_result)` — NaN in → NaN out |
| `ts_rank(x, d, c=0)` | base | Current value rank vs past d days | Rolling window, `(window <= current).mean()` |
| `ts_regression(y, x, d, lag=0, rettype=0)` | base | Regression params over d days. rettype: 0=residual, 1=slope, 2=intercept, 3=r², 4=t-stat(slope) | Rolling OLS via `np.linalg.lstsq` per instrument; shift x by lag before regress |
| `ts_scale(x, d, c=0)` | base | Scale to 0-1 over d days | `(current - ts_min) / (ts_max - ts_min)` |
| `ts_skewness(x, d)` | genius | Skewness over d days | `scipy.stats.skew(window, axis=0)` |
| `ts_std_dev(x, d)` | base | Std dev over d days (population, ddof=0) | `np.nanstd(window, axis=0, ddof=0)` — population std, not sample |
| `ts_step(1)` | base | Day counter, increments each day | Store counter in store, increment each call |
| `ts_sum(x, d)` | base | Sum over past d days | `np.nansum(window, axis=0)` |
| `ts_target_tvr_decay(x, ...)` | genius | Decay tuned to target turnover | Complex optimization; see BRAIN docs |
| `ts_target_tvr_delta_limit(x, y, ...)` | genius | Delta-limit tuned to target turnover | Complex optimization; see BRAIN docs |
| `ts_target_tvr_hump(x, ...)` | genius | Hump tuned to target turnover | Complex optimization; see BRAIN docs |
| `ts_zscore(x, d)` | base | Z-score over d days. Strict: all d values finite, else NaN. Pop std. Std=0 → NaN | `(current - nanmean) / nanstd(ddof=0)` — strict semantics; test vs FastExpr baseline for lenient alternative |

## Cross Sectional

| Operator | Level | Description | Python |
|----------|-------|-------------|--------|
| `normalize(x, useStd=false, limit=0)` | base | Subtract market mean (NaN-safe); optionally ÷ std; clamp to ±limit. NaN inputs stay NaN | `x - np.nanmean(x); if useStd: /= np.nanstd(x); np.clip(..., -limit, limit)` — NaN propagated |
| `quantile(x, driver="gaussian", sigma=1)` | base | Rank + apply statistical distribution. NaN in → NaN out; driver options: gaussian, uniform, laplace, etc. | `rank(x)` → mask NaN → `scipy.stats.norm.ppf(rank_result)` |
| `rank(x, rate=2)` | base | Rank across instruments, 0.0–1.0. NaN inputs → NaN in output, excluded from ranking pool | `scipy.stats.rankdata(x)/n` with NaN-to-NaN mask |
| `regression_proj(y, x)` | genius | Cross-sectional regression projection | OLS: `beta = np.linalg.lstsq(X, y)[0]; y_pred = X @ beta` |
| `scale(x, scale=1, longscale=1, shortscale=1)` | base | L1 normalize with separate long/short scaling. `scale`: target norm; `longscale`/`shortscale` override for +/− positions | `norm = sum(abs(x)); x * scale / max(norm, 1e-10)` — long/short override via separate L1 norms |
| `vector_proj(x, y)` | genius | Vector projection of x onto y | `(x @ y) / (y @ y) * y` |
| `winsorize(x, std=4)` | base | Clip beyond std from mean | `mean, sd = np.nanmean(x), np.nanstd(x); np.clip(x, mean-std*sd, mean+std*sd)` |
| `zscore(x)` | base | Standardize 0-1 | `(x - np.nanmean(x)) / np.nanstd(x)` |

## Vector

| Operator | Level | Description | Python |
|----------|-------|-------------|--------|
| `vec_avg(x)` | base | Mean of vector field elements | `np.nanmean(x, axis=-1)` |
| `vec_count(x)` | genius | Number of elements in vector | `x.shape[-1]` |
| `vec_max(x)` | genius | Max of vector elements | `np.nanmax(x, axis=-1)` |
| `vec_min(x)` | genius | Min of vector elements | `np.nanmin(x, axis=-1)` |
| `vec_range(x)` | genius | Max - min of vector | `np.nanmax(x, axis=-1) - np.nanmin(x, axis=-1)` |
| `vec_stddev(x)` | genius | Std dev of vector elements | `np.nanstd(x, axis=-1)` |
| `vec_sum(x)` | base | Sum of vector elements | `np.nansum(x, axis=-1)` |

## Transformational

| Operator | Level | Description | Python |
|----------|-------|-------------|--------|
| `bucket(rank(x), range/roots)` | base | Create buckets from ranked values. `range` = `(start, end, step)`; output 0..N-1, NaN stays NaN | `np.digitize(rank_result, bins)` — bins from `np.arange(start, end+step, step)`; NaN out |
| `generate_stats(alpha)` | base | Alpha statistics per day (shape S×D×A) | Complex; see BRAIN docs |
| `trade_when(x, y, z)` | base | Change alpha only when condition met | `np.where(condition, new_val, np.where(exit_cond, np.nan, prev_val))` with store |

## Group

| Operator | Level | Description | Python |
|----------|-------|-------------|--------|
| `combo_a(alpha, nlength=250)` | base | Combine multiple alpha signals | Weighted average with recent return/vol optimization |
| `group_backfill(x, group, d, std=4)` | base | Fill NaN with winsorized group mean | Group by field, compute winsorized mean per group |
| `group_cartesian_product(g1, g2)` | genius | Merge two groups into one (cartesian) | `pd.MultiIndex` or manual cross join |
| `group_extra(x, weight, group)` | genius | Replace NaN with group means | Group mean imputation |
| `group_mean(x, weight, group)` | base | Harmonic mean within groups. Invalid group IDs excluded; group with no valid data → NaN | Group by: filter valid groups + valid x → `1/nanmean(1/x_valid)` per group |
| `group_neutralize(x, group)` | base | Subtract group mean within each group. Missing group IDs (NaN/int sentinel) excluded, not treated as own group. All-NaN groups stay NaN | Filter valid groups → mean per group (only over valid x in group) → `x - group_mean`. Never init with 0 |
| `group_rank(x, group)` | base | Rank within groups, 0.0–1.0. Invalid group IDs excluded; groups with <2 valid → NaN | Group by field: per group filter valid → `scipy.stats.rankdata`/n within group |
| `group_scale(x, group)` | base | Normalize 0-1 within groups. Invalid group IDs excluded; group with NaN-only input → NaN | Per group: `(x - min) / max(1e-10, max - min)` over valid x within group |
| `group_zscore(x, group)` | base | Z-score within groups. Invalid group IDs excluded; group with <2 valid x or std=0 → NaN | Per group over valid x: `(x - nanmean) / nanstd(ddof=0)`; propagate NaN |

## Special

| Operator | Level | Description | Notes |
|----------|-------|-------------|-------|
| `in` | base | Selection operator | Used instrument selection |
| `inst_pnl(x)` | genius | PnL per instrument | Uses pv1 dataset |
| `self_corr(input)` | base | Auto-correlation across instruments | Output D×N×N; see BRAIN docs |
| `universe_size` | base | Number of instruments in universe | `np.sum(data.universe[-1].astype(bool))` |

## Reduce

All reduce operators take a 2-D (D×N) or 3-D (D×N×N) input and apply over the last dimension.

| Operator | Description | Python (axis=-1) |
|----------|-------------|-------------------|
| `reduce_avg(input, threshold=0)` | Mean with NaN threshold | `np.nanmean(x, axis=-1)` |
| `reduce_choose(input, nth)` | Choose nth element | Manual indexing |
| `reduce_count(input, threshold)` | Count > threshold | `np.sum(x > threshold, axis=-1)` |
| `reduce_ir(input)` | Information ratio | `np.nanmean(x, axis=-1) / np.nanstd(x, axis=-1)` |
| `reduce_kurtosis(input)` | Kurtosis | `scipy.stats.kurtosis(x, axis=-1)` |
| `reduce_max(input)` | Maximum | `np.nanmax(x, axis=-1)` |
| `reduce_min(input)` | Minimum | `np.nanmin(x, axis=-1)` |
| `reduce_norm(input)` | L1 norm | `np.nansum(np.abs(x), axis=-1)` |
| `reduce_percentage(input, p=0.5)` | Quantile (median at 0.5) | `np.nanpercentile(x, p*100, axis=-1)` |
| `reduce_powersum(input, c=2, precise=false)` | Sum of powers | `np.nansum(x**c, axis=-1)` |
| `reduce_range(input)` | Max - min | `np.nanmax(x, axis=-1) - np.nanmin(x, axis=-1)` |
| `reduce_skewness(input)` | Skewness | `scipy.stats.skew(x, axis=-1)` |
| `reduce_stddev(input, threshold=0)` | Std dev with NaN threshold | `np.nanstd(x, axis=-1)` |
| `reduce_sum(input)` | Sum | `np.nansum(x, axis=-1)` |
