# Custom Operators Reference

> **Not Official BRAIN Operators** — These are custom extensions implementable in Python inside `@alpha` function
> bodies. They use `numpy`/`scipy` and follow `store` patterns for caching expensive computations. See
> `references/store_patterns.md` for store usage and `custom_operators.md` for future updates to this set.

---

 
> **Common pattern**: All window-based operators (ts_*, ewm_*) return NaN when fewer than `d` rows are available.
> NaN inputs propagate through — an instrument with all-NaN in the window gets NaN output.
> Cross-sectional operators (cs_*) return NaN when fewer than 3 valid values exist.
 
---
 
## Clustering-based Groupers
 
*Window-dependent: `x.shape[0]` must be ≥5 for meaningful distance computation.*
 
---
 
## Decomposition / Factor Models
 
*Input-validity: all operators require at least `n_components + 2` instruments with finite data.*
 
---
 
## Regime Detection
 
*Sufficient data: `returns.shape[0]` must be ≥ `d_long` for meaningful results. Returns NaN for all instruments when below threshold.*
 
---
 
## Signal Processing
 
*Warm-up: `ts_kalman_filter` and `ts_hodrick_prescott` return NaN when window < 3 or < 5 rows respectively.
 `ts_robust_zscore` returns NaN when window < 3 valid values.*
 
---
 
## Advanced Time Series Statistics
 
*Common: all operators return NaN per-instrument when window has <3 valid values (or <5 for
 `ts_autocorr`, `ts_half_life`, `ts_beta`). `ts_hurst_exponent` requires ≥30.*
 
---
 
## Advanced Cross-sectional Statistics
 
*Common: all operators return NaN when input has <3 valid instruments (cs_spearman requires ≥10,
 cs_trimmed_mean requires ≥5).*
 
---
 
## Alpha Combination & Utility
 
*`ewm_*` operators: require at least `span/2` valid values per instrument.
 `pairwise_ic`/`pairwise_angular_distance`: return NaN when <5 valid pairs.
 `combo_ic_weighted`: returns equal-weight fallback when no signal has positive IC.*

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `hierarchical_correlation_clusters` | (x, n_clusters=10) | Ward's hierarchical clustering on correlation distance `sqrt(0.5*(1-corr))`. Groups instruments by return co-movement | `scipy.cluster.hierarchy.linkage(squareform(dist), method='ward')` + `fcluster(Z, t=n_clusters, criterion='maxclust')` |
| `kmeans_clusters` | (x, n_clusters=10, n_init=10) | K-means clustering on feature vectors. Faster than hierarchical for large universes | `scipy.cluster.vq.kmeans2(fv, n_clusters, minit='points', iter=n_init)` |
| `volatility_clusters` | (x, d=60, n_clusters=5) | Cluster instruments by rolling realized volatility curves over d days | Rolling `np.nanstd(window, axis=0)` per step → `kmeans_clusters(vol_curves, n_clusters)` |
| `pairwise_corr_cluster_zscore` | (signal, returns, n_clusters=10, recluster_every=20, store=None) | Z-score within dynamic correlation clusters with store-based periodic reclustering | `hierarchical_correlation_clusters(returns, n_clusters)` → `group_zscore(x, labels)` with store caching |

**Store pattern**: Use `{"name": "clusters", "dims": "i", "extend": np.float64(np.nan)}` + `"day_count"` for periodic recomputation.

---

## Decomposition / Factor Models

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `pca_decomposition` | (x, n_components=5) | Extract top principal components from N×F instrument-feature matrix via SVD | Mean-impute NaNs → standardize → `np.linalg.svd(x_std, full_matrices=False)` → `U[:, :n] * s[:n]` |
| `pca_residual` | (x, n_components=5) | Remove top PCs from signal, return residual (factor removal) | Build nonlinear feature expansion → SVD → regress x on PCs → `x - PC_scores @ coeffs` |
| `factor_risk_adjust` | (signal, factor_loadings, n_factors=5) | Remove known factor exposure via cross-sectional OLS regression | `np.linalg.lstsq(X, y, rcond=None)` → `y - X @ beta` with intercept |
| `pca_outlier_detection` | (x, n_components=3, n_std=3) | Flag outliers via PCA reconstruction error (large error = anomalous) | SVD → reconstruct → `error > mean(error) + n_std * std(error)` |

---

## Regime Detection

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `volatility_regime` | (returns, d_short=20, d_long=60) | Log-ratio of short/long realized vol. Positive = rising vol, negative = falling vol | `log(nanstd(ret[-d_short:]) / nanstd(ret[-d_long:]))` |
| `corr_regime_shift` | (returns, d=60, threshold=0.15) | Flag instruments whose correlation to equal-weighted market changed significantly between two adjacent d-day windows | Per-instrument: `np.corrcoef(half1, mkt1)[0,1] - np.corrcoef(half2, mkt2)[0,1]` |
| `ts_hmm_regime` | (returns, n_states=2, d=252) | Gaussian HMM via EM clustering of market returns. Assigns each instrument to most likely state | `scipy.stats.norm.logpdf` → responsibility weighting → state assignment. Store cache recommended |

---

## Signal Processing

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `ts_kalman_filter` | (x, obs_var=0.1, proc_var=0.01) | 1-D Kalman filter: predict → Kalman gain → update. Smooths noisy series with controlled responsiveness | Per instrument: `state += kg * (obs - state); cov = (1-kg) * cov + proc_var` |
| `ts_hodrick_prescott` | (x, lambda_param=1600) | HP filter: decompose into trend + cycle. Returns current cyclical (detrended) component | Solve `(I + λ*D'D)*trend = series` via `np.linalg.solve`, return `val - trend[-1]` |
| `ts_robust_zscore` | (x, d=60) | Robust z-score: `(x[-1] - median) / (MAD * 1.4826)`. Resistant to outliers versus standard z-score | `med = nanmedian(window); mad = nanmedian(abs(w-med)); (x[-1]-med) / max(mad*1.4826, 1e-10)` |
| `robust_normalize` | (x, method='mad') | Cross-sectional robust normalization. Methods: mad, iqr, percentile | mad: `(x-med)/(MAD*1.4826)`. iqr: `(x-med)/(IQR*0.7413)`. percentile: rank-based ECDF |
| `orthogonalize` | (x, y) | Gram-Schmidt: remove y-component from x. `x - (x·y / y·y) * y` | Center both → `beta = dot(x,y)/max(dot(y,y),1e-10)` → `x - beta*y` |
| `ewm_corr_rank` | (x, y, span=60) | Exponentially-weighted moving correlation per instrument, then cross-sectional rank-normalized | EW recursion on cov/var → `corr = cov/sqrt(var_x*var_y)` → `scipy.stats.rankdata(corr)/n` |

---

## Advanced Time Series Statistics

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `ts_kurtosis` | (x, d) | Rolling excess kurtosis. Positive = fat tails (more extremes than normal) | `scipy.stats.kurtosis(window, axis=0, nan_policy='omit')` |
| `ts_autocorr` | (x, d, lag=1) | Rolling autocorrelation at given lag. Positive = momentum, negative = mean-reversion | Per instrument: `np.corrcoef(s[:-lag], s[lag:])[0,1]` |
| `ts_half_life` | (x, d) | AR(1) half-life of mean reversion: `ln(0.5)/ln(β)`. Short = fast reversion | `beta = lstsq(ones+s[:-1], s[1:])[1]` → `log(0.5)/log(abs(beta))` if 0<β<1 |
| `ts_hurst_exponent` | (x, d) | Hurst exponent via R/S analysis. <0.5 = mean-reverting, ≈0.5 = random, >0.5 = trending | For multiple lag lengths: `mean(R/S)` per lag → `polyfit(log(lag), log(R/S))` slope |
| `ts_beta` | (x, y, d) | Rolling OLS beta of x against y (with intercept). Convenience wrapper for CAPM beta | Per instrument: `lstsq([ones, y], x)[0][1]`. 1-D y is broadcast to N |
| `ts_drawdown` | (x, d) | Current drawdown from rolling peak: `current/peak - 1`. ≤ 0, 0 at peak | `peak = nanmax(window, axis=0); window[-1] / max(peak, 1e-10) - 1` |
| `ts_var` | (x, d, p=0.05) | Historical Value at Risk at level p (e.g., 5th percentile for p=0.05) | `np.nanpercentile(window, p*100, axis=0)` |
| `ts_cvar` | (x, d, p=0.05) | Conditional VaR / Expected Shortfall: mean of all values below VaR threshold | `threshold = nanpercentile(window, p*100); nanmean(window[window < threshold])` |
| `ts_sharpe_ratio` | (x, d) | Rolling annualized Sharpe ratio: `mean/std * sqrt(252)` | `nanmean(window) / max(nanstd(window, ddof=1), 1e-10) * sqrt(252)` |
| `ts_semi_variance` | (x, d) | Downside semi-variance: variance of negative deviations from the mean | `downside = min(window - mean, 0); nansum(downside^2) / count` |
| `ts_omega_ratio` | (x, d, threshold=0) | Probability-weighted gain/loss ratio (captures all moments, not just mean/variance) | `sum(gains) / sum(|losses|)` relative to threshold |
| `ts_bollinger_position` | (x, d, n_std=2) | Standard deviations from rolling mean. Extreme values (>+2 or <-2) suggest reversion | `(x[-1] - nanmean(window)) / max(nanstd(window), 1e-10)` |
| `ts_rsi` | (x, d=14) | RSI: `100 - 100/(1 + avg_gain/avg_loss)`. 0-100, >70 overbought, <30 oversold | Wilder's smoothed avg gain/loss → `100 - 100/(1 + rs)` |

---

## Advanced Cross-sectional Statistics

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `cs_trimmed_mean` | (x, pct=0.1) | Remove top/bottom pct fraction then compute mean. Robust to outliers | `sort(x)[trim:-trim].mean()` |
| `cs_mad` | (x) | Median Absolute Deviation × 1.4826. Robust dispersion, consistent with std for normal data | `median(|x - median(x)|) * 1.4826` |
| `cs_iqr` | (x) | Interquartile range: Q75 - Q25. Robust spread measure | `percentile(x, 75) - percentile(x, 25)` |
| `cs_spearman` | (x, y) | Spearman rank correlation. Captures monotonic (not necessarily linear) relationships | `scipy.stats.spearmanr(x, y)[0]` |
| `cs_skewness` | (x) | Cross-sectional skewness (third moment). Detects asymmetric factor exposures | `scipy.stats.skew(x, bias=False)` |
| `cs_kurtosis` | (x) | Cross-sectional excess kurtosis (fourth moment). Detects extreme-value concentration | `scipy.stats.kurtosis(x, bias=False)` |

---

## Alpha Combination & Utility

| Operator | Parameters | Description | Python |
|----------|-----------|-------------|--------|
| `pairwise_ic` | (x, y) | Rank Information Coefficient = Spearman correlation between signal and forward returns | `cs_spearman(x, y)` |
| `pairwise_angular_distance` | (x, y) | Cosine/angular distance: `acos(cos_sim)/pi`. 0 = same direction, 1 = opposite | `arccos(clip(dot(x,y)/(|x|*|y|), -1, 1)) / pi` |
| `ewm_var` | (x, span) | Exponentially weighted variance. Decay = 2/(span+1). More weight on recent data | EW recursion: `var = (1-decay)*var + decay*dx^2` |
| `ewm_skew` | (x, span) | Exponentially weighted skewness. Tracks asymmetry evolution over time | EW recursion on second/third moments → `m3 / (m2^1.5)` |
| `ewm_covariance` | (x, y, span) | Exponentially weighted covariance. Useful for adaptive hedging | EW recursion: `cov = (1-decay)*cov + decay*dx*dy` |
| `combo_ic_weighted` | (signals, returns, ic_span=60, store=None) | Combine multiple alphas weighted by recent Rank IC. Adaptive signal fusion | `pairwise_ic(signal_i, returns)` → softmax-weight → weighted sum |
| `ts_hmm_regime` | (returns, n_states=2, d=252) | Gaussian HMM regime detection. Assign each instrument to latent market state. Store-cache recommended | EM on market returns → state assignment per instrument |

---

*42 custom operators total. Maintained separately from official `operators.md`. Add new operators above this note.*

## Regression (Deprecated)

| Operator | Level | Description | Python |
|----------|-------|-------------|--------|
| `regression_proj(y, x)` | base | Cross-sectional regression projection with intercept: ŷ = α + βx. Regress y on x, return fitted values. Handles NaN by using only finite pairs. | `def regression_proj(y, x): valid = np.isfinite(x) & np.isfinite(y); n = np.sum(valid); if n < 2: return np.full_like(y, np.nan); xv, yv = x[valid], y[valid]; xm, ym = np.mean(xv), np.mean(yv); beta = np.nansum((xv - xm) * (yv - ym)) / max(np.nansum((xv - xm) ** 2), 1e-30); proj = ym + beta * (x - xm); proj[~valid] = np.nan; return proj` |
| `regression_neut(y, x)` | base | **Deprecated.** Cross-sectional regression residual: ε = y - regression_proj(y, x). Equivalent to `sub(y, regression_proj(y, x))`. Use `y - regression_proj(y, x)` instead. ⚠️ Must include intercept! Old implementations using `y - beta*x` (through origin) are wrong and degrade Sharpe significantly. | `y - regression_proj(y, x)` |

