# Conversion Accuracy Tests

**Test suite for FastExpr → Python Alpha conversion quality.**
Use `scripts/test_conversion.py` to run these tests automatically.

---

## Core Operator Tests

These verify that the converter correctly parses and generates code for each operator family.

| ID | Category | FastExpr | Expected Behavior | Priority |
|----|----------|----------|-------------------|----------|
| 01 | Arithmetic | `-returns` | Negation: `-data.returns[-1]` | critical |
| 02 | Arithmetic | `abs(returns)` | Absolute value: `np.abs(data.returns[-1])` | critical |
| 03 | Arithmetic | `log(cap)` | Natural log with `x>0` guard | critical |
| 04 | Arithmetic | `sqrt(cap)` | Square root with `max(x,0)` clamp | critical |
| 05 | Arithmetic | `signed_power(x, 3)` | `np.sign(x) * np.abs(x)**3` | normal |
| 06 | Cross-sectional | `rank(returns)` | `cross_sectional_rank()` via argsort; NaN → NaN out | critical |
| 07 | Cross-sectional | `zscore(returns)` | `(x - nanmean) / nanstd` | critical |
| 08 | Cross-sectional | `winsorize(returns, 4)` | Clip at `mean ± 4*std` | critical |
| 09 | Cross-sectional | `scale(returns)` | L1 normalize: `x * scale / norm` | normal |
| 10 | Cross-sectional | `normalize(returns)` | Market neutral: `x - nanmean(x)` | normal |
| 11 | Group | `group_neutralize(x, sector)` | Per-group mean subtract; NaN/valid group filtering | **critical** |
| 12 | Group | `group_rank(x, industry)` | Rank within each group; excludes missing group IDs | critical |
| 13 | Group | `group_zscore(x, subindustry)` | Z-score within groups; NaN if group has <2 valid | critical |
| 14 | Group | `group_mean(x, weight, group)` | Harmonic mean per group | normal |
| 15 | Group | `group_scale(x, group)` | 0-1 normalize per group | normal |
| 16 | Time-series | `ts_mean(returns, 20)` | `np.nanmean(x[-20:], axis=0)` | critical |
| 17 | Time-series | `ts_sum(returns, 20)` | `np.nansum(x[-20:], axis=0)` | critical |
| 18 | Time-series | `ts_std_dev(returns, 20)` | `np.nanstd(x[-20:], ddof=0)` — **population std** | critical |
| 19 | Time-series | `ts_zscore(returns, 20)` | `(current - ts_mean) / ts_std_dev` — strict/FastExpr test | **critical** |
| 20 | Time-series | `ts_backfill(cap, 120)` | Bounded search within last 120 rows; int32→float conversion | **critical** |
| 21 | Time-series | `ts_rank(returns, 20)` | Rolling rank: `mean(window <= current)` | critical |
| 22 | Time-series | `ts_arg_max(returns, 20)` | Days since max via argmax on reversed window | normal |
| 23 | Time-series | `ts_delay(returns, 3)` | `x[-1-3]` with shape guard | normal |
| 24 | Time-series | `ts_delta(returns, 3)` | `x[-1] - x[-1-3]` with shape guard | normal |
| 25 | Time-series | `ts_corr(returns, volume, 20)` | Per-instrument corr on overlapping-valid slice (>=3 pairs) | normal |
| 26 | Special | `universe_size` | `np.sum(data.universe[-1].astype(bool))` | normal |
| 27 | Transform | `bucket(rank(cap), range)` | `np.digitize(rank_result, bins)`; NaN stays NaN | normal |
| 28 | Transform | `trade_when(x, y, z)` | Store-based prev signal; NaN on exit | normal |
| 29 | Logical | `if_else(cond, a, b)` | `np.where(cond.astype(bool), a, b)` | normal |
| 30 | Logical | `is_nan(x)` | `np.isnan(x).astype(np.float32)` | normal |

## Complex Expression Tests

| ID | Expression | Check Points |
|----|-----------|--------------|
| 31 | `-ts_mean(returns, 20)` | Negation after time-series; both ops parsed |
| 32 | `rank(ts_mean(returns, 20))` | Nested: ts inside cross-sectional |
| 33 | `group_neutralize(returns, sector)` | Group op with integer group field (sentinel handling) |
| 34 | `ts_zscore(ts_mean(returns, 5), 20)` | Time-series over computed intermediate (store caching needed) |
| 35 | `signed_power(group_neutralize(ts_backfill(cap, 120), country), 3)` | 4-layer nesting with group, fill, power |
| 36 | `group_zscore(winsorize(ts_backfill(cap, 120), 4), sector)` | Fill → winsorize → group zscore |
| 37 | `-group_rank(returns, industry)` | Negation after group rank |
| 38 | `trade_when(rank(x)>0.8, -group_rank(returns, group), -1)` | Original trade_when template from BRAIN |
| 39 | `ts_corr(returns, volume, 20)` | Two-field time-series |
| 40 | `bucket(rank(ts_mean(volume, 20)), 0, 1, 0.1)` | 3-level: ts → rank → bucket |

## Code Template Checks

On every generated output, verify:

| Check | Detail |
|-------|--------|
| T01 | `@alpha` decorator present |
| T02 | `data=` list contains all needed fields |
| T03 | `store=` declared when ts_* operators are present |
| T04 | `field_to_float()` or sentinel conversion for int32 fields |
| T05 | `return .astype(np.float32)` present |
| T06 | `pasteurize(signal, u)` called before return |
| T07 | Name mangling avoided (no `__` internal names) |
| T08 | `data.universe[-1]` used correctly as bool mask |

## Semantic Equivalence Checks

These require actual platform backtesting to validate:

| Check | Operator | Risk |
|-------|----------|------|
| S01 | `ts_zscore` strict vs lenient window coverage | Window coverage mismatch can change alpha by >0.5 Sharpe |
| S02 | `ts_std_dev` ddof=0 vs ddof=1 | Systematic bias in all std-based metrics |
| S03 | `ts_backfill` bounded vs infinite | Infinite fill overestimates data availability |
| S04 | `group_neutralize` NaN group exclusion | Missing groups treated as group 0 → wrong neutralization |
| S05 | `rank` NaN handling | NaN values getting rank 0 instead of NaN |
| S06 | Store warm-up period | First 20-60 days of Python Alpha may differ from FastExpr |
| S07 | `trade_when` signal filtering vs `z` parameter | Filtering signal values that equal `z` (e.g. `np.isclose(signal, -1)` when `z=-1`) deletes legitimate strong short signals from `-group_rank`, inflating turnover by ~22% and lowering Sharpe. The `z` parameter is a control-flow instruction, not a sentinel value to strip. |

## Running Tests

```bash
# Run all tests
python3 scripts/test_conversion.py

# Run a specific category
python3 scripts/test_conversion.py --category group

# Run a specific test by ID
python3 scripts/test_conversion.py --id 33

# Show verbose output
python3 scripts/test_conversion.py --verbose
```

---

*Maintain this file as new operators are added and conversion edge cases are discovered.*

## Running Tests

```bash
# Run all tests
python3 scripts/test_conversion.py

# Run a specific category
python3 scripts/test_conversion.py --category group

# Run a specific test by ID
python3 scripts/test_conversion.py --id 33

# Show verbose output
python3 scripts/test_conversion.py --verbose
```

---

*Maintain this file as new operators are added and conversion edge cases are discovered.*
