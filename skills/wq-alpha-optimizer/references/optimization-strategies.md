---
name: optimization-strategies
description: Optimization strategies from BRAIN platform documentation, community forum posts, and consultant experience. Covers all failure types with actionable modifications.
---

# Optimization Strategies

**Sources:** BRAIN official tutorials, community forum ("Stop Memorizing Operators",
"How to Improve Sharpe", "How to reduce turnover", "Avoiding Overfitting",
"How to reduce prod correlation"), consultant experience posts (Chinese forum), and
platform documentation.

## Core Principle (from community)

> "Sharpe improves in only two ways: Increase return → better predictive signal.
> Reduce volatility → cleaner, more stable signal.
> Most people focus on making signals more complex, but real gains often come
> from reducing noise through better design and neutralization.
> Better prediction + less noise = higher Sharpe."

---

## Low Sharpe (< 1.58 for D1, < 2.69 for D0)

### S1: Add smoothing to reduce noise (from docs + community)
The community consensus: reducing noise is often more effective than adding complexity.
```
rank(returns) -> ts_mean(rank(returns), 5)
```
Start with d=5, then try d=3 or d=10 based on turnover impact.

### S2: Better neutralization (from docs + community)
Community insight: "real gains often come from reducing noise through better neutralization."
```
NONE -> MARKET -> SECTOR -> SUBINDUSTRY
```
Consultant experience: In TOP3000 universes, sector neutralization preserves more
cross-industry alpha than sub-industry. Sub-industry can over-clean in large universes
where industries have many stocks.

### S3: Use ts_rank (from docs)
```
rank(returns) -> ts_rank(returns, 21)
```

### S4: Improve signal quality (from community)
Use more predictive data sources or combine complementary factors.
Signals based on strong economic intuition, earnings revisions, analyst expectations,
or quality metrics often generate higher returns than noisy indicators.

### S5: Enhance signal timing (from community)
Apply ts_arg_max, ts_rank, ts_delta, or momentum transformations to capture
inflection points:
```
ts_delta(rank(x), 5)  # captures recent change
```

### S6: Combine with a complementary signal
```
0.7 * rank(returns) + 0.3 * rank(ts_mean(adv, 20))
```

### S7: Tune decay
```
decay=0 -> decay=3, 5, 7
```
From BRAIN docs: "Decay can be used to reduce turnover."

### S8: Flip negative Sharpe
Wrap entire expression in `-(...)`.

---

## Low Fitness (< 1.0 for D1, < 1.5 for D0)

```
Fitness = Sharpe * sqrt(abs(Returns) / max(Turnover, 0.125))
```

### F1: Apply decay (from BRAIN docs - explicitly recommended)
```
decay=0 -> decay=3, 5, 10
```
"Decay can be used to reduce turnover" - this is the most effective single lever.

### F2: ts_mean wrapping
```
group_rank(returns, group) -> ts_mean(group_rank(returns, group), 10)
```

### F3: trade_when for turnover control (from forum)
The `trade_when` operator specifically helps reduce unnecessary trading:
```
trade_when(condition, signal, exit_value)
```

### F4: Hump operator (from forum - community recommended)
The `hump` operator and `ts_target_tvr_decay` are specifically designed for
turnover control. From community: "Understanding the hump Operator in Alpha
Creation" - these are underused but effective.

### F5: Use test period to evaluate (from "Avoiding Overfitting")
Split IS into training + test (80-20). If Sharpe drops >50% training→test,
the alpha is overfit and won't hold OS.

---

## High Turnover

### T1: Apply decay (from BRAIN docs - first recommendation)
```
decay=0 -> decay=3, 5, 10, 15
```
BRAIN documentation explicitly states: "Decay can be used to reduce turnover."

### T2: Smooth with ts_mean
```
rank(returns) -> ts_mean(rank(returns), 10)
```

### T3: Use trade_when for selective trading (from forum)
trade_when only changes positions when conditions are met, naturally reducing turnover.

### T4: Use hump / ts_target_tvr_decay (from forum)
These operators are specifically designed for turnover control.
From the community: "Understanding the hump Operator in Alpha Creation"

### T5: Increase delay
```
delay=1 -> delay=2
```

### T6: Consultant insight - short decay (6 days)
From Chinese forum: short decay (6 days) improves IS Sharpe but incurs high
transaction costs. Stacking cross-sectional momentum control at the sub-factor
level can reduce unnecessary rebalancing.

### T7: Six techniques from the community (post: "How to reduce turnover"):
1. Increase Decay to Smooth Signals
2. Utilize the trade_when Operator
3. Implement Truncation to Limit Position Sizes
4. Neutralize Across Groups
5. Adjust Signal Thresholds
6. Optimize Universe Selection

---

## High Correlation (> 0.7 to production or self)

### C1: Swap data fields within same dataset (from docs + forum)
```
rank(returns) -> rank(adv20)       # price -> volume
rank(bm) -> rank(earnings_yield)   # book-to-market -> earnings yield
```
From forum: "Use multiple datasets - fundamental, alternative, and technical indicators."

### C2: Change operator family (from docs + forum)
```
rank -> group_rank or vice versa
rank -> zscore -> ts_rank
```

### C3: Diversify input data (from community)
From forum post "How to reduce prod correlation":
- Mix short-term and long-term signals
- Use different datasets (fundamental, alternative, technical)
- Combine different modeling approaches

### C4: Orthogonalize (from community)
Feature engineering and residualization to remove common factor exposure.

### C5: Consultant insight - correlation < 0.6 hard cutoff
From Chinese forum: Using correlation < 0.6 as cutoff passes PROD correlation
easily but filters out high-Sharpe signals. Balance by testing correlation
with the specific pool, not just generic benchmarks.

### C6: Local correlation pre-check (from Chinese forum consultant)
If user has 100+ OS submissions: build a local correlation matrix by periodically
downloading the personal alpha history. Pre-filter new candidates against this
matrix before using platform quota. Filters 70%+ of correlated alphas in the
first round.

### C7: Use less common operators for differentiation
Community insight: "Hidden gems" operators that are underused:
- regression_neut, ts_quantile, ts_decay_exp_window
- group_cartesian_product, inst_tvr
- vec_range, last_diff_value, days_from_last_change

### C7a (Python Alpha): Custom operator via wq-alpha-converter
In Python Alpha, C7 moves up significantly in priority. The `wq-alpha-converter` skill
supports defining custom operators — reusable signal-processing units that wrap arbitrary
numpy/brain logic. This creates **structural** differentiation, not just surface-level
operator swaps:

```python
# Instead of a plain expression that 30 other people may have written similarly,
# wrap into a custom operator with unique structure:
@alpha(data=[...])
@custom_operator
def my_two_layer_neut(rets, volume):
    layer1 = cross_sectional_rank(rets) - cross_sectional_mean(cross_sectional_rank(rets))
    layer2 = ts_mean(layer1, 5) * cross_sectional_rank(volume)
    return group_neutralize(layer2, subindustry).astype(np.float32)
```

A custom operator is effectively a new signal "component" — if two alphas don't share
any custom operator lineage, they are structurally different in a way that raw field
and operator swaps cannot achieve. This makes C7 especially valuable for users who
already have many alphas in the pool and need fresh, orthogonal signals.

**Fast Expression vs Python Alpha priority:**

```
Fast Expression correlation priority:
  1. C1 换字段            ← 改动最小，值得先做
  2. C2 换算子族
  3. C7 冷门算子           ← 原生算子里选冷门，边际差异有限
  4. C3 分散输入数据
  5. C4-C6 更重的方案

Python Alpha correlation priority:
  1. C1 换字段            ← 改动最小，依然值得先做
  2. C7a Custom Operator ← 结构化差异，命中率高，Python 下零成本
  3. C7 冷门算子           ← 如果不想走 custom operator
  4. C3 分散输入数据
  5. C2 换算子族           ← 如果以上都做了还不够
  6. C4-C6 更重的方案
```

In Python Alpha, C7a consistently sits at position 2 — it costs nothing extra in
Python (no new imports, no new datasets), creates structural signal uniqueness,
and has the highest correlation-reduction leverage per unit of effort.

---

## Low Margin / Concentration / Weight Test

### Low Margin

#### M1: Increase truncation
```
truncation=0.01 -> 0.03 -> 0.05
```
Note: truncation=0.05 is aggressive. If simulation fails, back off to 0.03 or combine with other operators rather than going higher.

#### M2: Avoid size factors (from BRAIN sub-universe test docs)
- Avoid: rank(-assets), 1 - rank(cap)
- Avoid: factor-momentum interaction (e.g. ts_rank(rank(accruals), 21))

#### M3: Diversify signals
More diversification helps sub-universe performance.

---

### Concentration (持仓集中度)

Single-stock weight > 10% triggers concentration failure, even if overall margin is fine.

#### CO1: Truncation with nuance
```
truncation=0.01 -> 0.03
```
truncation=0.05 can sometimes fail simulation due to excessive clipping. Start at 0.01, move to 0.03, and if 0.05 fails, combine with other operators instead of forcing higher.

#### CO2: maxPosition=ON (simulation setting)
Enable `maxPosition` in simulation settings to cap single-stock max weight directly. This is a platform-level constraint separate from truncation — truncation clips outliers in expression space, maxPosition caps them in portfolio-weight space.

#### CO3: winsorize operator
```python
# Fast Expression / Python: compress extreme values without hard cutoff
winsorize(signal, min=0.01, max=0.99)
```
Unlike truncation which discards values outside a range, winsorize pulls extreme values to the boundary. Softer on the distribution, and often passes simulation weight checks that truncation fails.

#### CO4: scale operator
```python
# Normalize positions so no single stock dominates
scale(signal, target=1.0)
scale(winsorized_signal, target=0.95)
```
Ensures total position size is bounded. Combine with winsorize for two-layer weight control: compress extremes first, then normalize to target scale.

#### CO5: hump operator
```
hump(signal, hump=0.1)  # mild clipping
```
Softer alternative to truncation. Limits extreme weights without a hard cutoff.

#### CO6: Remove size-based multipliers
`rank(-assets)`, `1 - rank(cap)` naturally concentrate weights. Remove or replace with non-size-based alternatives.

---

### Weight Test (权重分布)

Weight test is about the **overall weight distribution** (skew, dispersion, asymmetry) — not just single-stock limits. An alpha can pass concentration but fail weight test.

#### W1: All concentration solutions
truncation, maxPosition, winsorize, scale, hump — everything above applies here too.

#### W2: Avoid manual weight skew
Check if component signal coefficients are so unbalanced that they produce systematic overweight on one side (e.g., 0.9 × signalA + 0.1 × signalB creates near-monolithic long positions).

#### W3: Ensure normalization operators are paired
rank/zscore/scale should be paired in the expression: if you rank at step 1, you should scale or normalize later. An un-normalized rank output can produce extreme weight dispersion.

#### W4: Test with different truncation levels
Weight test responds differently to truncation than concentration does. Run weight test separately:
```
# weight test passes at truncation=0.03 but fails at 0.01
# increase truncation incrementally
```

---

## Overfitting Prevention (from community post)

From "Avoiding Overfitting in Alpha Research" (38319194429847):

### O1: Always use a Test Period
Split IS into training (80%) + test (20%). Develop alpha only on training.
If Sharpe drops >50% training→test → overfit.

### O2: Robustness checks
- Rank test: wrap signal with rank()
- Binary test: wrap signal with sign()
If performance drops >70% after these → fitting noise, not signal.

### O3: Simple first (from "Curiosity Before Complexity")
Ask: "Why should this signal exist? Under what conditions would it stop working?"
Don't start with complex stacking - build a simple alpha first.

---

## Operator Role Framework (from community post)

From "Stop Memorizing Operators. Learn Their Jobs." (41820050908823):

| Role | Examples | Purpose |
|------|----------|---------|
| Foundation | abs, add, multiply, divide, log | Build relationships, transform raw signals |
| Cross-Sectional | rank, zscore, scale, normalize | Compare stocks, remove market effects |
| Time-Series | ts_rank, ts_delta, ts_mean, ts_corr | Learn from history, trend, momentum |
| Signal Cleaning | winsorize, truncate, ts_backfill | Handle outliers, improve coverage |
| Turnover Control | trade_when, hump, ts_target_tvr_decay | Reduce turnover, stabilize positions |
| Group Intelligence | group_rank, group_neutralize, bucket | Industry-aware signals, neutralization |
| Vector | vec_avg, vec_count, vec_range | Convert vector datasets to scalars |
| Logical | if_else, and, or, is_nan | Conditional logic, event handling |
| Distribution | densify, bucket, left_tail | Regime detection, extreme-value analysis |
| Hidden Gems | regression_neut, ts_quantile, inst_tvr | Underused but powerful |

---

## Post-Optimization Checklist

---

## Sub-Universe Sharpe (from Chinese forum)

From community posts (35062818902423, 37378958993303, 37759477785239):

### SU1: signed_power signal transformation (most effective)
When Sub-universe Sharpe fails, wrapping with `signed_power` can transform the signal distribution:
```
signed_power(original_expr, y)
```
- **y > 1** (e.g. y=2): Amplifies extreme values, compresses middle values → stronger signal differentiation. Proven to turn Sub-universe fail into Spectacular pass.
- **0 < y < 1** (e.g. y=0.5): Compresses extremes, pulls distribution toward Gaussian → smoother signal, less outlier sensitivity, better robustness.
- Try y in range [0.25, 2.0]; most effective case: y=2 turned Sub-universe 0.51→Spectacular.

### SU2: Liquidity-weighted decay separation
Separate signal into liquid and illiquid components with different decay windows:
```
ts_decay_linear(signal, short_window) * rank(volume*close)
+ ts_decay_linear(signal, long_window) * (1 - rank(volume*close))
```
Use `volume*close` or `cap` as liquidity proxy. Short window (e.g. 5 days) for liquid portion,
long window (e.g. 10 days) for illiquid portion. If initial attempt fails, try adjusting
window parameters rather than giving up.

### SU3: Strengthen neutralization
- Add `group_neutralize(signal, sector)` or `group_neutralize(signal, subindustry)`
- Switch neutralization from NONE → SECTOR → SUBINDUSTRY
- From forum: SUBINDUSTRY neutralization is more effective for Sub-universe issues in EUR/USA

### SU4: Avoid size-related multipliers
- Avoid: `rank(-assets)`, `1 - rank(cap)`, or similar size-factor multipliers
- Size multipliers concentrate weight in low/high liquidity stocks → Sub-universe failure
- If using cap filtering, keep filter very loose (e.g. `rank(cap) > 0.01`)

### SU5: Strategic fallback
If all above fail, the signal may lack inherent robustness — "Some signals are intrinsically
not robust." Consider changing the core logic rather than continuing to patch.

---

## IS Ladder Sharpe (from Chinese forum)

From community post (39050410166807 "关于IS ladder sharpe优化的一点实践经验"):

### IL1: ts_rank wrapper
Wrap the expression with `ts_rank` to stabilize the time-series behavior:
```
ts_rank(original_expr, d)
```
Start with d=120, then try d=60, 90, 180. From a JPN case study,
d=180 gave IS Ladder = 1.24 (improved but still below threshold).

### IL2: power(ts_rank(...)) for final push
Apply `signed_power` or `power` on top of ts_rank to push IS Ladder over the threshold:
```
power(ts_rank(original_expr, 120), 2)
```
From forum case: ts_delta(ts_product(...), 352) → ts_rank(..., 120) → power(ts_rank(...), 2)
successfully lifted IS Ladder from fail to > 1.58 without degrading overall performance.

### IL3: Check margin first
Low-margin alphas tend to have worse IS Ladder due to turnover costs eating into
historical returns. If margin is very low (< 0.001), IS Ladder issues may be
secondary to the turnover/margin problem.

---

## Regional Optimization (from Chinese forum)

### Japan (ASI) Robustness (post 40531412200471)
JPN Sharpe >= 1.0 is a common stumbling block for ASI region alphas.

**Key insights from a successful case (JPN Sharpe 0.88 → 1.00):**
- **Optimization priority**: signal weights > grouping dimension > window params > field choice
- **sector grouping is unreliable in Japan**: switch to `market` grouping for cross-sectional ops
- **Fundamental data (fnd28) is weak in Japan**: its coverage is low; dont try to fix it, compensate with price-based signals instead
- **When a component signal underperforms in a sub-region**: reduce its weight rather than trying to fix it
- **signed_power must match dominant signal type**: 0.75 (compress) for fundamental-heavy, 1.1 (stretch) for price-reversal-heavy

```
alpha1 = trade_when(group_rank(...region_filter), fundamental_signal, cap_filter);
alpha = alpha1 + 2.5 * group_rank(-ts_mean(returns, 20), market);
signed_power(alpha, 1.1)
```

**Key parameter changes from the case:**
- Reversal weight: 0.5 → 2.5 (5x)
- Reversal grouping: sector → market
- Reversal window: 10 → 20 days
- signed_power: 0.75 → 1.1

**If 3+ attempts don't improve a sub-region:** the signal component is fundamentally
unreliable in that region. Stop trying to fix it. Reduce its weight or replace it.

### IND Robust Universe (post 37759477785239)
IND region frequently fails Robust Universe Sharpe due to sparse datasets.

**Methods:**
- Adjust `ts_backfill` window: try 60 → 90 → 120 for better coverage
- Use `group_backfill` with well-chosen groups (sector/industry) instead of ts_backfill
- Apply `group_zscore` / `group_neutralize` — both tend to work similarly; if one works, both work
- Use smaller window sizes (15, 22, 66) — IND datasets often signal better on shorter windows
- Warning: smaller windows may increase prod correlation

### ASI General (from forum posts)
- ASI regions require `max_trade=ON` in settings
- Sector grouping in ASI may be inconsistent across sub-regions; prefer MARKET grouping for cross-sectional operators in multi-country ASI alphas
- Japan is the most common sub-region failure point; always check JPN Sharpe when optimizing ASI

---

## Detailed Turnover Reduction with Decay Windows (from forum)

From community post (34949059814679 "turnover优化，论坛精华版"):

### T8: ts_decay_linear with window economics
Window size economic interpretation:
| Window | Calendar | Best For |
|--------|----------|----------|
| 5 | 1 trading week | Short-term signal smoothing |
| 22 | 1 trading month | Monthly trend capture |
| 44 | 2 trading months | Medium-term signal stabilization |
| 63 | 1 quarter (earnings cycle) | Fundamental signals |

Expect 30-50% turnover reduction with acceptable Sharpe loss (< 15%).

### T9: hump operator
```
hump(original_expr, hump=0.1)  # mild clipping
hump(original_expr, hump=0.2)  # moderate
hump(original_expr, hump=0.3)  # aggressive
```
Especially effective when Sub-universe Sharpe is also an issue.

### T10: TVR control operators
```
ts_target_tvr_delta_limit(original_expr, volume, target_tvr=0.1)
ts_target_tvr_delta_limit(original_expr, volume, target_tvr=0.15)
```
These directly target a specific turnover level. Forum recommendation: prefer
ts_decay_linear over TVR operators when overfitting risk is a concern.

### T11: Combined smoothing
```
ts_decay_linear(ts_mean(original_expr, 5), 22)  # weekly mean + monthly decay
hump(ts_decay_linear(original_expr, 5), hump=0.2)  # weekly decay + clipping
```

### T12: Window size generalization
- Smaller windows → higher turnover, lower prod correlation risk
- Larger windows → lower turnover, potentially higher prod correlation
- Balance: match window size to the data's natural signal frequency

---

## Deep Optimization Principles (from Chinese forum)

From the Japan Robustness optimization case (40531412200471):

### P1: Optimization priority order
1. **Signal weights** (most impactful) — 0.5 → 2.5 (5x change, not 1.2x)
2. **Grouping dimension** — sector vs market vs subindustry vs country
3. **Window parameters** — decay length, lookback period
4. **Field selection** (least impactful) — only change if combining with weight/grouping changes

### P2: Dont try to fix what is broken
If a signal component is fundamentally weak in a sub-region (3+ failed attempts),
stop trying to fix it. Instead:
- Reduce its weight
- Compensate with a different signal that works in that sub-region
- Accept the component's limitations and optimize around them

### P3: Parameter search: wide first, then narrow
Wrong approach: change fields → change windows → change weights (from micro to macro)
Right approach: change weights (0.1→5.0) → change grouping → change windows → change fields (from macro to micro)

### P4: signed_power must match signal type
- Fundamental-heavy signals: use 0.75 (compress extremes, handle outliers)
- Price/reversal-heavy signals: use 1.1-2.0 (stretch distribution, enhance differentiation)
- Defaulting to one value for all signal types misses optimization opportunities

### P5: When micro-adjustments fail, go structural
If 3 rounds of micro-tuning (window sizes, thresholds, decay) don't fix a Sharpe gap of 0.12,
the solution is not finer tuning but structural change — typically weight redistribution or
grouping dimension change.

Before presenting to user:
1. All metrics pass platform thresholds
2. Check correlation: `cnhkmcp.check_correlation(new_id, "both")`
3. If GLB region: check sub-geography Sharpe (AMER>=1, APAC>=1, EMEA>=1)
4. Rank test the new alpha as a robustness sanity check
5. Sub-universe test passed (check formula if user can see it)

## Python Alpha: Strategy Equivalents

This section provides the Python Alpha equivalent for every Fast Expression strategy in this reference. Use it when optimizing a Python Alpha — you don't need to mentally translate from FastExpr syntax.

### Python Alpha 基础模式

A Python Alpha follows this structure:

```python
from brain.alphas import *  # cs_rank, cs_zscore, ts_mean, group_neutralize, etc.
import numpy as np

@alpha(data=[returns, adv20])
def my_alpha(data):
    # data is a named tuple: data.returns, data.adv20, etc.
    # data.returns shape: (T, N) where T = time, N = stocks
    # data.returns[-1] extracts the most recent cross-section
    signal = cs_rank(data.returns[-1].copy())
    signal = ts_mean(signal, 5)
    return signal.astype(np.float32)
```

**关键注意事项：**
1. `cs_` 前缀：FastExpr 的 `rank(x)` → Python 中是 `cs_rank(x)`（同理 `zscore` → `cs_zscore`, `scale` → `cs_scale`, `normalize` → `cs_normalize`, `group_rank` → `cs_group_rank`）
2. `.copy()`：时间序列切片后建议 `.copy()`，避免 numpy 视图引起的踩内存问题
3. `.astype(np.float32)`：返回值必须是 float32，否则平台会报错
4. `data.*` 访问：数据集字段需通过 `data.字段名` 访问，如 `data.returns`、`data.adv20`
5. numpy 自由：对于 `brain.alphas` 未覆盖的操作，可以直接用 numpy（如 `np.mean`, `np.where`, `np.corrcoef`）
6. `store` 接口：需要跨变量引用时用 `with store(data):` 上下文

```python
# store 接口示例 — 跨行变量引用
with store(data):
    store['r'] = cs_rank(data.returns[-1].copy())
    store['v'] = cs_rank(data.adv20[-1].copy())
    signal = 0.7 * store['r'] + 0.3 * store['v']
```

---

### 快速查询表：FastExpr → Python Alpha

| FastExpr | Python Alpha (`brain.alphas`) |
|---|---|
| `rank(x)` | `cs_rank(x)` |
| `zscore(x)` | `cs_zscore(x)` |
| `scale(x)` | `cs_scale(x)` |
| `normalize(x)` | `cs_normalize(x)` |
| `group_rank(x, g)` | `cs_group_rank(x, g)` |
| `group_neutralize(x, g)` | `group_neutralize(x, g)` |
| `group_mean(x, g)` | `cs_group_mean(x, g)` |
| `group_std(x, g)` | `cs_group_std(x, g)` |
| `group_zscore(x, g)` | `cs_group_zscore(x, g)` |
| `group_sum(x, g)` | `cs_group_sum(x, g)` |
| `ts_mean(x, n)` | `ts_mean(x, n)` |
| `ts_rank(x, n)` | `ts_rank(x, n)` |
| `ts_delta(x, n)` | `ts_delta(x, n)` |
| `ts_sum(x, n)` | `ts_sum(x, n)` |
| `ts_std_dev(x, n)` | `ts_std_dev(x, n)` |
| `ts_corr(x, y, n)` | `ts_corr(x, y, n)` |
| `ts_arg_max(x, n)` | `ts_arg_max(x, n)` |
| `ts_arg_min(x, n)` | `ts_arg_min(x, n)` |
| `ts_decay_linear(x, n)` | `ts_decay_linear(x, n)` |
| `ts_decay_exp_window(x, n)` | `ts_decay_exp_window(x, n)` |
| `ts_backfill(x, n)` | `ts_backfill(x, n)` |
| `ts_product(x, n)` | `ts_product(x, n)` |
| `ts_min(x, n)` / `ts_max(x, n)` | `ts_min(x, n)` / `ts_max(x, n)` |
| `ts_quantile(x, n, q)` | `ts_quantile(x, n, q)` |
| `winsorize(x, min, max)` | `winsorize(x, min, max)` |
| `truncate(x, min, max)` | `truncate(x, min, max)` |
| `trade_when(cond, signal, exit)` | `trade_when(cond, signal, exit)` |
| `hump(x, hump=v)` | `hump(x, hump=v)` |
| `signed_power(x, y)` | `signed_power(x, y)` |
| `densify(x)` | `densify(x)` |
| `if_else(cond, t, f)` | `if_else(cond, t, f)` |
| `abs(x)` | `np.abs(x)` 或 `abs(x)` |
| `log(x)` | `np.log(x)` |
| `sqrt(x)` | `np.sqrt(x)` |
| `sign(x)` | `np.sign(x)` |
| `x + y`, `x - y`, `x * y`, `x / y` | 同左 |
| `power(x, y)` | `np.power(x, y)` 或 `signed_power(x, y)` |
| `fill(x, v)` | `np.nan_to_num(x, nan=v)` |
| `not_nan(x)` | `~np.isnan(x)` |

对于快速查询，可以直接搜索对应 FastExpr 策略 ID（如 `S1`, `F1`, `T1`, `C1` 等）来找到 Python 实现。

---

### 低 Sharpe —— Python 实现

#### S1（平滑降噪）

```python
# FastExpr: rank(returns) -> ts_mean(rank(returns), 5)
r = cs_rank(data.returns[-1].copy())
signal = ts_mean(r, 5)
```
Python 特有：可以在 `ts_mean` 前做 `.copy()` 避免原地修改：
```python
r = cs_rank(data.returns[-1].copy())
# 如果要做多窗口对比，用不同变量保存不同窗口的平滑结果
signal_smooth = ts_mean(r.copy(), 5)   # 短平滑
signal_slower = ts_mean(r.copy(), 10)  # 长平滑
```

#### S2（更好的中性化）

Python Alpha 中，中性化通过 `group_neutralize` 实现：
```python
# NONE -> MARKET -> SECTOR -> SUBINDUSTRY
signal = cs_rank(data.returns[-1].copy())

# 行业中性化
from brain.alphas import subindustry
neutralized = group_neutralize(signal, subindustry)
```

多国家区域双重中性化：
```python
from brain.alphas import industry, country, group_cartesian_product
group = densify(group_cartesian_product(industry, country))
signal = group_neutralize(signal, group)
```

#### S3（ts_rank）

```python
# FastExpr: rank(returns) -> ts_rank(returns, 21)
signal = ts_rank(data.returns, 21)
```
注意：`ts_rank` 和 `ts_mean` 的输入是完整时间序列 `data.returns`（不是 `data.returns[-1]`），由库内部处理窗口切片。

#### S4（提升信号质量）

Python 中可以直接用 numpy 构造更复杂的信号：
```python
ret = data.returns
# 最近 5 天收益的加权平均，最近权重更高
weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])
weighted_ret = np.average(ret[-5:], axis=0, weights=weights)
signal = cs_rank(weighted_ret)
```

#### S5（增强信号时机：ts_delta）

```python
# FastExpr: ts_delta(rank(x), 5)
signal = ts_delta(cs_rank(data.returns), 5)
```

#### S6（补充信号组合）

```python
# FastExpr: 0.7 * rank(returns) + 0.3 * rank(ts_mean(adv, 20))
sig1 = cs_rank(data.returns[-1].copy())
sig2 = cs_rank(ts_mean(data.adv20, 20).copy().astype(np.float32))
signal = 0.7 * sig1 + 0.3 * sig2
return signal.astype(np.float32)
```

#### S7（衰减 tuning） 和 S8（负 Sharpe 取反）

```python
# S7: 通过 settings 调整 decay，和 FastExpr 一样
# SimulationSettings(decay=3, ...)

# S8: 负 Sharpe 取反
return -signal.astype(np.float32)
```

---

### 低 Fitness —— Python 实现

#### F1（decay 降低换手）

同 S7，通过 `SimulationSettings(decay=n, ...)` 调整，Python 和 FastExpr 完全一致。

#### F2（ts_mean 包裹）

```python
# FastExpr: group_rank(returns, group) -> ts_mean(group_rank(returns, group), 10)
r = cs_group_rank(cs_rank(data.returns[-1].copy()), group)
signal = ts_mean(r, 10)
return signal.astype(np.float32)
```

#### F3（trade_when）

```python
# FastExpr: trade_when(condition, signal, exit_value)
signal = cs_rank(data.returns[-1].copy())
# 仅在流动性足够时交易
liquidity = cs_rank(data.adv20[-1].copy())
condition = liquidity > 0.1
result = trade_when(condition, signal, -1)
return result.astype(np.float32)
```

#### F4（hump 算子）

```python
result = hump(signal, hump=0.1)
return result.astype(np.float32)
```

#### F5（测试集验证）

同 FastExpr，与语言无关的策略原则。

---

### 高 Turnover —— Python 实现

#### T1（decay）

Python 和 FastExpr 一样，`SimulationSettings(decay=3, ...)`。

#### T2（ts_mean 平滑）

```python
r = cs_rank(data.returns[-1].copy())
signal = ts_mean(r, 10)
```

#### T3（trade_when 选择性交易）

```python
# 仅在强信号时交易
signal = cs_rank(data.returns[-1].copy())
cond = np.abs(signal) > 0.3
result = trade_when(cond, signal, 0)
return result.astype(np.float32)
```

#### T4（hump / ts_target_tvr_decay）

```python
# hump 算子
result = hump(signal, hump=0.2)

# TVR 目标限制
result = ts_target_tvr_delta_limit(signal, data.adv20, target_tvr=0.1)
```

#### T5-T7

T5（delay 增加）：settings 里设置 `delay=2`，和 FastExpr 相同。
T6-T7：Python 实现和上述模式相同，无需额外说明。

#### T8-T12（decay window 更详细）

```python
# ts_decay_linear 在 Python 中的使用
signal = cs_rank(data.returns[-1].copy())
smoothed = ts_decay_linear(signal, 22)  # 1 month

# 组合平滑
smoothed = ts_decay_linear(ts_mean(signal, 5), 22)
result = hump(smoothed, hump=0.2)
return result.astype(np.float32)
```

---

### 高 Correlation —— Python 实现

#### C1（换字段）

Python Alpha 中换字段通过修改 `@alpha(data=[...])` 装饰器的数据集列表实现：

```python
# 从价格换到成交量
@alpha(data=[adv20])
def alpha_volume(data):
    signal = cs_rank(data.adv20[-1].copy())
    return signal.astype(np.float32)

# 从估值换到盈利
@alpha(data=[earnings_yield])
def alpha_earnings(data):
    signal = cs_rank(data.earnings_yield[-1].copy())
    return signal.astype(np.float32)
```

#### C2（换算子族）

在 Python 中，换算子族意味着改变 `brain.alphas` 的函数调用：

```python
# rank -> group_rank
signal = cs_group_rank(cs_rank(data.returns[-1].copy()), sector)

# rank -> ts_rank
signal = ts_rank(data.returns, 21)

# rank -> zscore -> ts_rank
z = cs_zscore(data.returns[-1].copy())
signal = ts_rank(data.returns, 21)
```

#### C3（分散输入数据）

```python
# 混合短期和长期信号
short_signal = cs_rank(ts_delta(data.returns, 1))
long_signal = cs_rank(ts_mean(data.returns, 60))
combined = 0.5 * short_signal + 0.5 * long_signal
return combined.astype(np.float32)
```

#### C4（正交化）

Python 中可以用 numpy 做残差回归：

```python
import numpy as np

# 从信号中去除已知风险因子的暴露
signal = cs_rank(data.returns[-1].copy())
factor = cs_rank(data.adv20[-1].copy())

# 线性回归残差
A = np.column_stack([np.ones(len(factor)), factor])
coeff, residuals, _, _ = np.linalg.lstsq(A, signal, rcond=None)
orthogonal_signal = signal - A @ coeff
return orthogonal_signal.astype(np.float32)
```

#### C7a（Custom Operator —— Python 独有）

这部分已在原文档 C7a 中完整覆盖。Python Alpha 的 custom operator 是 FastExpr 无法实现的结构化差异手段。

---

### Margin / Concentration / Weight —— Python 实现

#### M1（truncation）

Python 和 FastExpr 一样，`SimulationSettings(truncation=0.03, ...)`。

#### M2（避免 size 因子）

在 Python 中，避免在 `@alpha(data=[...])` 中使用 `assets`、`cap` 等规模相关字段：
```python
# 避免
@alpha(data=[assets])
def bad_alpha(data):
    signal = -cs_rank(data.assets[-1].copy())  # 不推荐

# 推荐：使用非规模字段
@alpha(data=[returns, adv20])
def good_alpha(data):
    signal = cs_rank(data.returns[-1].copy())
    return signal.astype(np.float32)
```

#### CO1-CO6（集中度控制）

```python
# CO3: winsorize
with store(data):
    store['r'] = cs_rank(data.returns[-1].copy())
    signal = winsorize(store['r'], min=0.01, max=0.99)

# CO4: scale
signal = cs_scale(winsorized_signal, target=1.0)

# CO5: hump
signal = hump(signal, hump=0.1)
return signal.astype(np.float32)
```

---

### Sub-Universe —— Python 实现

#### SU1（signed_power）

```python
# FastExpr: signed_power(original_expr, y)
signal = cs_rank(data.returns[-1].copy())
transformed = signed_power(signal, 2.0)   # y > 1: 放大极端值
return transformed.astype(np.float32)
```

#### SU2（流动性加权的 decay 分离）

```python
# FastExpr 在 Python 中的等价实现
signal = cs_rank(data.returns[-1].copy())
liquidity = cs_rank(data.adv20[-1].copy() * data.close[-1].copy())

short_window = ts_decay_linear(signal, 5)
long_window = ts_decay_linear(signal, 10)

result = short_window * liquidity + long_window * (1 - liquidity)
return result.astype(np.float32)
```

#### SU3（加强中性化）

```python
from brain.alphas import subindustry
signal = cs_rank(data.returns[-1].copy())
result = group_neutralize(signal, subindustry)
return result.astype(np.float32)
```

#### SU4（避免 size 乘数）

Python 中检查 `@alpha(data=[...])` 是否包含 `assets` / `cap`，如果有则移除或用非 size 的流动性代理（如 `adv20`）替代。

#### SU5（回退）

与策略语言无关，属于优化决策原则。

---

### IS Ladder —— Python 实现

#### IL1（ts_rank 包裹）

```python
# FastExpr: ts_rank(original_expr, d)
signal = ts_rank(data.returns, 120)
return signal.astype(np.float32)
```

#### IL2（power(ts_rank(...))）

```python
signal = ts_rank(data.returns, 120)
result = signed_power(signal, 2.0)
return result.astype(np.float32)
```

或者使用 numpy：
```python
signal = ts_rank(data.returns, 120).astype(np.float32)
# power 会保留符号
np_result = np.sign(signal) * np.power(np.abs(signal), 2.0)
return np_result.astype(np.float32)
```

#### IL3（检查 margin）

和 FastExpr 一样，是通用的低 margin 检查原则。

---

### Regional Optimization —— Python 实现

#### Japan（ASI）优化

```python
# FastExpr 在 Python 中的等价
from brain.alphas import market

alpha1 = trade_when(
    cs_group_rank(cs_rank(data.returns[-1].copy()), market) > 0,
    data.fundamental_signal[-1].copy(),
    cs_rank(data.adv20[-1].copy())
)

alpha2 = cs_group_rank(
    -ts_mean(data.returns, 20),
    market
)

signal = alpha1 + 2.5 * alpha2
result = signed_power(signal, 1.1)
return result.astype(np.float32)
```

注意：Japan 优化中提到的 sector → market 分组切换，在 Python 中：
```python
# sector 分组（不推荐在 Japan）
from brain.alphas import sector
signal = cs_group_rank(data.returns[-1].copy(), sector)

# market 分组（推荐在 Japan）
from brain.alphas import market
signal = cs_group_rank(data.returns[-1].copy(), market)
```

---

### Python Alpha 特有优化手段

FastExpr 无法实现，但 Python Alpha 可以直接使用的技术：

#### NP1: 任意 numpy 运算

```python
def my_alpha(data):
    # 非线性组合
    r = data.returns[-1].copy()
    v = data.adv20[-1].copy()
    
    # 自定义加权：使用数据驱动的权重
    weights = np.where(r > 0, 0.7, 0.3)
    result = weights * cs_rank(r) + (1 - weights) * cs_rank(v)
    return result.astype(np.float32)
```

#### NP2: 条件逻辑 + 多列操作

```python
def my_alpha(data):
    # 不同市场环境用不同信号
    vol = ts_std_dev(data.returns, 20)
    regime = cs_zscore(vol[-1].copy())
    
    signal_low_vol = cs_rank(data.returns[-1].copy())
    signal_high_vol = -cs_rank(ts_mean(data.returns, 5))
    
    # Python 独有：numpy where 做 regime switch
    result = np.where(regime < 0, signal_low_vol, signal_high_vol)
    return result.astype(np.float32)
```

#### NP3: 循环构造复合信号

```python
def my_alpha(data):
    signals = []
    # 多窗口复合
    for w in [5, 10, 21]:
        s = cs_rank(ts_mean(data.returns, w)[-1].copy())
        signals.append(s)
    
    # 等权组合
    result = np.mean(signals, axis=0)
    return result.astype(np.float32)
```

#### NP4: store 跨越复杂计算

```python
from brain.alphas import store

def my_alpha(data):
    with store(data):
        store['r'] = cs_rank(data.returns[-1].copy())
        store['v'] = cs_rank(data.adv20[-1].copy())
        store['interaction'] = store['r'] * store['v']
        store['smoothed'] = ts_mean(store['interaction'], 5)
        # 在 store 内，time-series 算子可以引用已命名的变量
        return store['smoothed'].astype(np.float32)
```

---

### 快速决策表：给定优化目标，Python Alpha 应该用什么

| 目标 | Python 手段 | 参考策略 |
|------|-----------|---------|
| 提 Sharpe | `cs_rank` → `ts_mean(cs_rank, d)` 平滑 | S1 |
| 提 Sharpe | `ts_rank(data.field, d)` 代替 `cs_rank` | S3 |
| 提 Sharpe | `group_neutralize(sig, sector/subindustry)` | S2 |
| 提 Fitness | 设置 `decay=3/5/10` | F1 |
| 提 Fitness | `hump(signal, 0.1)` 或 `trade_when(cond, sig, 0)` | F3, F4 |
| 降 Turnover | `ts_mean(signal, d)` 平滑 | T2 |
| 降 Turnover | `hump(signal, 0.2)` 或 `ts_decay_linear(sig, 22)` | T4, T8 |
| 降 Correlation | 换 `@alpha(data=[新字段])` | C1 |
| 降 Correlation | `cs_group_rank` 代替 `cs_rank` | C2 |
| 降 Correlation | custom operator + `wq-alpha-converter` | C7a |
| 降 Concentration | `winsorize(signal, 0.01, 0.99)` + `cs_scale(sig, 1.0)` | CO3, CO4 |
| 提 Sub-universe | `signed_power(signal, 2.0)` | SU1 |
| 提 IS Ladder | `ts_rank(signal, 120)` → `signed_power(ts_rank(signal, 120), 2)` | IL1, IL2 |
| 复用现有 FastExpr | 先 `wq-alpha-converter` 转换 → 再用 Python 策略优化 | 转换路径 |

---

## 官方文档补充优化策略（2026年更新）

以下策略来源于 BRAIN 官方文档（通过 cnhkmcp.get_documentation_page() 获取）。

### HTVR：高点换手 Alpha 优化（来自官方 "High Turnover Alphas" + "PnL Realization Horizon" 文档）

HTVR 目标：Turnover > 20%，PnL Realization Horizon < 20天

#### HTVR1：高换手的正确出发点
常见错误：直接追求高换手，而不是追求短生命周期信息源。
高换手应该是想法的结果，而不是想法本身。

正确工作流：
1. 从快速变化效应的直觉开始（如新闻情绪、收益惊喜、短期反转）
2. 选择更新频率合适且有足够广度的字段（如价格变化、情绪指标）
3. 建立清晰表达该效应的简单 alpha
4. 检查 alpha 是否自然落入高换手区间
5. 在真实市场条件、不同 universe 和成本意识变体下测试

#### HTVR2：使用变化量而非水平量
优先使用：delta, surprises, accelerations, revisions
避免使用：静态水平值（如 raw close, raw volume）
```
# 推荐：delta/surprise 类
ts_delta(rank(returns), 1)  # 短期变化
rank(ts_delta(adv20, 5))     # 成交量变化

# 不推荐：静态水平
rank(returns)  # 水平量
```

#### HTVR3：条件逻辑做事件门控
用流动性、关注度或事件状态做门控，帮助信号在正确时机行动：
```
trade_when(liquidity > 0.1, signal, -1)  # 仅在流动性足够时交易
```

#### HTVR4：PnL Realization Horizon 验证
提交前检查 PnL Realization Horizon 是否与 Alpha 想法匹配：
- 动量/新闻 Alpha：期望 Horizon < 10天
- 基本面 Alpha：期望 Horizon 20-40天
- 高换手 Alpha (HTVR)：期望 Horizon < 20天

如果 Horizon 与想法类型不匹配，说明信号时间特征不符合预期。

#### HTVR5：分散化价值
短 Horizon 的 Alpha 天然与长 Horizon Alpha 池低相关：
- 与已有 daily 池更低相关
- 对 book 影响更小
- 更好的分散化收益

#### HTVR6：质量检查清单
好的高换手研究特征：
- 信号更新速度足以证明频繁换仓的合理性
- 表现不集中在少数日期或工具上
- 在现实约束或 investable 设置下仍有意义
- 能用"信息为何应快速到达并衰减"来解释想法

### D0 优化策略（来自官方 "D0" 文档）

#### D0-1：识别适合 D0 的想法
D0 适合的信号特征：
- 高度依赖当日信息（收益公告、新闻情绪、盘前数据）
- 利用隔夜回报（Overnight Returns）
- 短持仓周期，快速信息衰减

#### D0-2：D0 的收益来源理解
D0 收益分为两个部分：
- 交易PnL（短期）：快速反转、微观结构
- 持仓PnL（较长持有期）：隔夜到次日的趋势延续

优化时可分别关注哪个部分贡献更大。

#### D0-3：D0 与 D1 的切换测试
如果 D1 Alpha 的信号可能受益于当日信息：
1. 先在 D1 下优化到最佳
2. 改为 delay=0 测试 D0 版本
3. 预期 Sharpe 提升（但门槛也提高到 2.0）

D0 比 D1 更早进入交易，所以预期表现更高。

### Fast D1 优化策略（来自官方 "Fast D1 Documentation" 文档）

#### FD1-1：识别 Fast D1 机会
Fast D1 适合的信号特征：
- 使用隔夜信息（新闻、财报、分析师更新、盘前交易）
- 传统 D1 数据时间戳为昨日收盘，信息已经过时

#### FD1-2：字段选择
使用带 _fast_d1 后缀的字段：
- snt_buzz_fast_d1（今日开盘情绪，vs snt_buzz 昨日收盘）
- 其他 Fast D1 系列字段

对比三种 delay 的信息优势：
- Delay 1（snt_buzz）：仅昨日收盘数据
- Fast D1（snt_buzz_fast_d1）：今日开盘数据，捕获隔夜信息
- Delay 0（snt_buzz）：今日收盘前数据，信息最新但更难执行

#### FD1-3：快速 D1 的特殊优化
- 数据更新更快，换手通常更高
- 需要结合 HTVR 策略控制换手
- 通过 ts_mean 或 decay 平滑信号

### 双重中性化策略（来自官方 "Double Neutralization" 文档）

#### DN-1：适用区域
- EUR, ASI, GLB（多国家区域）：行业 + 国家双重中性化
- USA：行业/子行业 + 统计分组（如 sta1_top1000c50）

#### DN-2：正确实现方式
不要顺序使用两次 group_neutralize：
```
# 错误：第二次会部分抵消第一次
group_neutralize(group_neutralize(Alpha, industry), country)

# 正确：使用 group_cartesian_product 合并分组
group = densify(group_cartesian_product(industry, country))
group_neutralize(Alpha, group)
```

#### DN-3：ASI 区域示例
```
alpha = ts_rank(eps, 252)
group = densify(group_cartesian_product(industry, country))
group_neutralize(alpha, group)
```
设置 Neutralization=None, Decay=0, Truncation=0。

#### DN-4：USA 区域示例
```
group = group_cartesian_product(sector, sta1_top1000c50)
alpha = group_rank(ts_rank(eps, 252), group)
group_neutralize(alpha, group)
```

#### DN-5：优化建议
- 双重中性化对多国家区域的 alpha 有显著提升
- 使用基本的行业/国家分组效果最好
- 尝试不同的分组组合（industry+country, sector+sta_group等）
- 如果一种组合失效，尝试更换分组维度

### 风险中性化四种类型（来自官方 "Advanced Topics" 文档）

#### RN-1：四种类型对比
| 类型 | 特点 | 适合场景 |
|------|------|---------|
| Default | 常规中性化 | 大多数情况 |
| Crowding Risk | 控制拥挤风险 | 已有大量 ALPHA 提交后 |
| RAM Risk | 基于 RAM 模型 | 需要模型驱动的风险控制 |
| Statistical Risk | 统计方法 | 无先验风险因子时 |

#### RN-2：选择建议
- 初期使用 Default
- 当已有 alpha 池变大时，考虑 Crowding Risk 降低拥挤暴露
- RAM 和 Statistical 在更复杂的 alpha 管理场景使用

### PnL Realization Horizon 深度应用（来自官方文档）

#### PH-1：验证 Alpha 想法匹配度
提交前检查 PnL Realization Horizon 是否与 Alpha 的 thesis 匹配：
- 动量/新闻 Alpha：应有短 horizon（< 10天）——信息衰减快
- 基本面 Alpha：可能有较长的 horizon（20-40天）——价值需要时间实现
- 高换手 Alpha：必须短 horizon（< 20天）——换仓成本需要快速实现来抵消

#### PH-2：识别正交信号
短 horizon 的 Alpha 天然与每日 Alpha 池正交：
- 与现有持仓更低相关
- 对 book 影响更小
- 更好的分散化收益

#### PH-3：理解信号成分
Alpha 的 PnL 实现有两个成分：
- 短期成分：1-5天内实现，信号在5天后几乎没有预测性
- 长期成分：10-20+天累积，信号需要更长时间实现价值

优化时可针对性地增强主要成分。
大多数已提交的 Alpha 有 20+ 天的 horizon（低换手成分可达 40+ 天）。
短期实现的 Alpha 提供自然正交性。

### Investability Constrained Metrics 优化（来自官方文档）

#### IC-1：理解流动性约束
Investability Constraints 确保 Alpha 持仓在工具的流动性限内：
- 避免重大市场冲击影响盈利
- 高 Investability 表现的 Alpha 有更高容量和流动性
- 可在新模拟结果页面查看

#### IC-2：优化建议
- 添加 truncation 减少极端持仓
- 避免在小盘股上过度集中
- 检查 IS Summary 中的流动性约束后表现
- 不同 universe（TOP3000 vs TOP1000）的流动性特征不同

### 官方公式汇总

```
Sharpe = sqrt(252) * Mean(PnL) / Stdev(PnL)
Return = 年化PnL / (账面规模的一半)
Turnover = 美元交易金额 / 账面规模
Fitness = Sharpe * sqrt(abs(Returns) / max(Turnover, 0.125))
```

公式来自官方 "Parameters in Simulation Results" 文档和 "Fitness" 文档。

### 官方社群精华文章（改善 Alpha 的 7 篇必读）
来自官方 "Must-read posts: How to improve your Alphas"：
1. How to get a higher Sharpe
2. 5 ways to potentially increase returns
3. How to reduce correlation
4. Using trade_when for Event Alphas（降低换手）
5. How to smooth PnL curve（减少波动）
6. Neutralization intuition（中性化直觉）
7. How to avoid overfitting（避免过拟合）

可通过 cnhkmcp.get_documentation_page 获取这些文章的完整链接。

### 官方文档参考表
通过 `cnhkmcp.get_documentation_page(id)` 获取完整官方教程：
+ about-brain-platform - Introduction to Alphas（基础概念）
+ introduction-brain-expression-language - BRAIN 表达式语言
+ how-brain-platform-works - BRAIN 后台执行流程
+ 19-alpha-examples - 初级 Alpha 示例
+ sample-alpha-concepts - 青铜 Alpha 示例
+ example-expression-alphas - 白银 Alpha 示例
+ simulation-settings - 设置选择指南
+ alpha-submission - 提交门槛详解
+ parameters-simulation-results - 模拟结果参数说明
+ understanding-pnl-realization-horizon - PnL 实现周期
+ neut-cons - 中性化详解
+ neut-users - 双重中性化
+ getting-started-d0 - D0 Alpha
+ getting-started-investability-constrained-metrics - 流动性约束指标
+ fast-d1-documentation - Fast D1 框架
+ getting-started-high-turnover-alphas - 高换手 Alpha 指南
+ list-must-read-posts-how-improve-your-alphas-are-submitted - 社群精华文章
