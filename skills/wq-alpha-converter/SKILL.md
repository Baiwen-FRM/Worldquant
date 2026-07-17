---
name: wq-alpha-converter
description: Convert WorldQuant BRAIN Fast Expression Alpha into Python Alpha code. Use when the user provides a Fast Expression like 'ts_rank(rank(returns))' or an Alpha ID like 'aoK8Pm2' and wants it translated to a proper Python Alpha with the @alpha decorator. Also use when the user needs help understanding how to structure a Python Alpha, applying operators like ts_rank/rank/ts_sum in Python.
metadata:
  short-description: Convert BRAIN Fast Expression Alpha to Python Alpha code
---

# BRAIN Alpha Converter

## Overview

Convert a WorldQuant BRAIN Fast Expression Alpha into a fully functional Python Alpha. The conversion follows the BRAIN documentation's 5-part structure:

1. Parse the original Fast Expression (from the user or from `cnhkmcp.get_alpha_details()`)
2. Look up operator definitions from `references/operators.md`
3. Extract data field names from the expression (no API calls needed)
4. Apply Python Alpha syntax rules
5. Generate complete, runnable code

## Optimized Conversion Flow (~5 seconds total)

When the user provides an **Alpha ID**, do this in ONE `python3` call:

### Step 1: Authenticate + fetch Alpha (1 API call)

```python
import asyncio, cnhkmcp
await cnhkmcp.authenticate()
alpha = await cnhkmcp.get_alpha_details(alpha_id)
expr = alpha["regular"]["code"]   # e.g. "trade_when(rank(x)>0.8, -group_rank(returns, group), -1)"
settings = alpha["settings"]
```

### Step 2: Parse expression (instant, no API)

Use regex to find all function-call patterns. Cross-reference against `references/operators.md`:
- **Operators**: words that match known operator names → look up in reference
- **Data fields**: words that DON'T match operators → put directly in `data=[]`
- **Variables**: words before `=` assignment operator → exclude

### Step 3: Look up operators (instant, from reference)

All 107 operators are in `references/operators.md` with Python implementations. No API call needed.

### Step 4: Verify field types via API

Extract field names from the expression. Query ONLY those exact field IDs:

```python
# Query each field to confirm type=MATRIX
for fname in field_names:
    result = await cnhkmcp.get_datafields(data_type="MATRIX", search=fname)
    for f in result.get("results", []):
        if f["id"] == fname:
            print(f"{f['id']}: type={f['type']}")
            if f["type"] != "MATRIX":
                warn(f"{fname} is {f['type']}, not supported in Python Alpha")
```

Each query takes ~5s due to server latency. For a typical Alpha with 2-4 fields, this step takes ~10-20s. This is unavoidable — the time comes from the BRAIN API, not from Codex.

### Step 5: Write file

Save to `alpha_<id>.py` in the workspace.

**Result**: ~5 seconds total (1 auth call, 1 alpha details call, 0 data field calls).

## Workflow Details

### A. When User Gives an Alpha ID

1. `cnhkmcp.get_alpha_details(id)` → get expression + settings
2. Parse operators and field names from expression
3. Look up operators in `references/operators.md`
4. Generate code with field names directly in `data=[]`
5. Write `alpha_<id>.py`

### B. When User Gives a Raw Expression

Same as above but skip the API step — parse the expression directly.

 
## Backtesting Verification

After converting, verify the Python Alpha against the original FastExpr by running a simulation.
The converter supports optional backtesting via `cnhkmcp`:

```bash
# Convert and submit for backtesting
python3 scripts/wq_converter.py <alpha_id> --backtest

# Convert and compare with original FastExpr
python3 scripts/wq_converter.py <alpha_id> --compare
```

### Before Submission

1. **Trim settings** — Remove Regular-only fields (`startDate`, `endDate`, `nanHandling`, etc.)
   See [references/settings-trimming.md](references/settings-trimming.md) for the whitelist.
2. **Check gotchas** — Review [references/platform-gotchas.md](references/platform-gotchas.md)
   for known pitfalls (store warm-up, submission_unknown, settings rejection).
3. **Run tests** — `python3 scripts/test_conversion.py` validates parser accuracy.

### Interpreting Results

| Delta | Assessment | Action |
|-------|-----------|--------|
| Sharpe within ±0.05 | **Match** | Submit as-is |
| Sharpe within ±0.2 | **Acceptable** | Check warm-up period; disclose in Notes |
| Sharpe > ±0.3 | **Mismatch** | Compare PnL curve; check operator semantics |

## Python Alpha Syntax Rules

- `@alpha(data=[...], store=[...])` from `brain.alphas`
- Each `data.<field>`: 2-D `[lookback+1, n_instruments]`, float32, read-only → `.copy()` before mutation
- `data.universe[-1]`: int mask (1=in, 0=out). NEVER list `"universe"` in `data=[]`
- Return: 1-D float32 `(n_instruments,)` → always `.astype(np.float32)`
- Warm-up: fewer rows at start; reductions over `[-d:]` safe, explicit back-index needs `x.shape[0]` guard
- `store`: for stateful ops; see `references/store_patterns.md`
- Imports: `from brain.alphas import alpha`, `import numpy as np`, all helpers self-contained

## Code Template

```python
# Alpha ID: aoK8Pm2
# Original Expression: trade_when(rank(x)>0.8, -group_rank(returns, group), -1)
# Settings: region=USA, universe=TOP3000, delay=1, decay=5, neutralization=SUBINDUSTRY, truncation=0.08, pasteurization=ON

from brain.alphas import alpha
import numpy as np
import numpy.typing as npt

def field_to_float(x):
    """Convert BRAIN int32/float32 field to float64, replacing sentinel missings with NaN."""
    if np.issubdtype(x.dtype, np.integer):
        missing = np.iinfo(x.dtype).min
        out = x.astype(np.float64)
        out[x == missing] = np.nan
        return out
    return x.astype(np.float64)

def pasteurize(a, u):
    a = a.copy()
    a[~u.astype(bool)] = np.nan
    return a

def neutralize(a):
    a0 = np.nan_to_num(a, nan=0, posinf=0, neginf=0)
    return a - np.mean(a0)

def scale(a):
    a0 = np.nan_to_num(a, nan=0, posinf=0, neginf=0)
    norm = np.linalg.norm(a0, ord=1)
    return a / norm if norm > 0 else a

def cross_sectional_rank(x):
    invalid = np.isnan(x)
    n = np.sum(~invalid)
    if n == 0: return np.full_like(x, np.nan)
    x_filled = np.where(invalid, -np.inf, x)
    order = np.argsort(x_filled)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(x))
    return np.where(invalid, np.nan, (ranks + 1) / n)

def group_neutralize(a, group_labels):
    """
    Subtract group mean. Missing group IDs (NaN/int sentinel) excluded.
    Groups with all-NaN signal stay NaN. Never init result with zeros.
    """
    a = a.astype(np.float64)
    result = a.copy()
    
    # Identify valid group labels
    if np.issubdtype(group_labels.dtype, np.integer):
        sentinel = np.iinfo(group_labels.dtype).min
        is_valid_group = (group_labels != sentinel)
    else:
        is_valid_group = np.isfinite(group_labels)
    
    # Process each group with valid members
    for g in np.unique(group_labels[is_valid_group]):
        in_group = (group_labels == g) & is_valid_group
        group_vals = a[in_group]
        valid_vals = group_vals[np.isfinite(group_vals)]
        if len(valid_vals) > 0:
            result[in_group] = a[in_group] - np.mean(valid_vals)
    return result

@alpha(data=["<field1>", "<field2>"], store=[])
def alpha_fn(data, store):
    u = data.universe[-1].astype(bool)
    # ... operator implementations ...
    signal = pasteurize(signal, u)
    signal = scale(group_neutralize(signal, subind))  # if SUBINDUSTRY
    return signal.astype(np.float32)
```

## Operator Levels

**genius** (Expert/Master/Grandmaster): `sigmoid`, `tanh`, `hump_decay`, `ts_decay_exp_window`, `ts_entropy`, `ts_min_diff`, `ts_min_max_cps`, `ts_min_max_diff`, `ts_skewness`, `ts_target_tvr_decay`, `ts_target_tvr_delta_limit`, `ts_target_tvr_hump`, `regression_proj`, `vector_proj`, `vec_count`, `vec_max`, `vec_min`, `vec_range`, `vec_stddev`, `group_cartesian_product`, `group_extra`, `inst_pnl`

All others are base level.

## Key Operators Quick Reference

### ts_rank(x, d)
Time-series rank vs past d values per instrument. Python: rolling buffer in store (dims="xi"), rank within window.

### rank(x)
Cross-sectional rank, 0-1. Python: argsort-twice / `scipy.stats.rankdata`.

### group_rank(x, group)
Rank within groups. Python: for each group, local rank.

### bucket(rank(x), range)
Create buckets from ranked values. Python: rank + floor division.

### trade_when(x, y, z)
Change signal only when x is true; keep previous otherwise; close when signal == z. Python: store persists prev signal, update on trigger, NaN on exit.

⚠️ **Common bug: don't filter out signal values that equal the `z` parameter** (e.g. `-1` in `trade_when(x, y, -1)`). The `z` parameter is a **control-flow instruction** to the runtime ("hold previous signal when condition is false"), not a signal value. When `y` legitimately produces values equal to `z` (e.g. `-group_rank(returns, group)` ranges [-1, 0), and `z=-1`), converting those values to NaN deletes the strongest short signals. Never add code like `np.where(np.isclose(signal, -1), np.nan, signal)` — it breaks the alpha's turnover and Sharpe.

### scale(x)
L1 normalize. Python: `x / np.linalg.norm(x, ord=1)`.

## Scripts

- [scripts/wq_converter.py](scripts/wq_converter.py) — Automated skeleton generator. Runs everything in one process.
- [scripts/lookup_operator.py](scripts/lookup_operator.py) — Operator lookup utility.

 
## Casebook Methodology

Conversion quality improves with each iteration. Follow this workflow when a conversion
produces unexpected results:

```
FastExpr → Convert → Backtest → Match? → Done
                                 ↓ No
                     Classify failure:
                     ┌─────────────┬──────────────┐
                     │ Syntax      │ Settings      │
                     │ Operator    │ Store/State   │
                     │ NaN/Window  │ Platform      │
                     └─────────────┴──────────────┘
                                  ↓
                     Can reproduce? → No → Move on
                                  ↓ Yes
                     Write rule into operators.md
                     Update platform-gotchas.md
                     Add test case to conversion-evals.md
```

**Principles:**
- Only promote stable, reproduced findings into reference files
- Keep single-case thresholds in casebook, not as global defaults
- Remove all private IDs, task UUIDs, and account info from public references
- Run `python3 scripts/test_conversion.py` after each reference update

## References

- [references/operators.md](references/operators.md) — 107 operators with Python implementations
- [references/data_fields.md](references/data_fields.md) — Common MATRIX field reference
- [references/store_patterns.md](references/store_patterns.md) — Store usage patterns
### Conversion Kit

For production-grade conversion workflows, these references extend the basic flow:

| File | Purpose |
|------|---------|
| [references/platform-gotchas.md](references/platform-gotchas.md) | 19+ platform-specific pitfalls and how to avoid them |
| [references/settings-trimming.md](references/settings-trimming.md) | Python Alpha settings whitelist + trimming rules |
| [references/conversion-evals.md](references/conversion-evals.md) | 35 accuracy test cases covering all operator families |
| [scripts/test_conversion.py](scripts/test_conversion.py) | Run `python3 scripts/test_conversion.py` to validate conversion quality |

## Custom Operators
 
 For custom operators that go beyond the official BRAIN set, see
 [references/custom_operators.md](references/custom_operators.md).
 These operators follow the same table format as the official reference and are
 maintained separately for easy updates.
 
 ### Custom Operator Quick Reference
 
 | Category | Operators | Reference |
 |----------|-----------|-----------|
 | Clustering Groupers | `hierarchical_correlation_clusters`, `kmeans_clusters`, `volatility_clusters`, `pairwise_corr_cluster_zscore` | [custom_operators.md](references/custom_operators.md) |
 | Decomposition / Factors | `pca_decomposition`, `pca_residual`, `factor_risk_adjust`, `pca_outlier_detection` | [custom_operators.md](references/custom_operators.md) |
 | Regime Detection | `volatility_regime`, `corr_regime_shift`, `ts_hmm_regime` | [custom_operators.md](references/custom_operators.md) |
 | Signal Processing | `ts_kalman_filter`, `ts_hodrick_prescott`, `ts_robust_zscore`, `robust_normalize`, `orthogonalize`, `ewm_corr_rank` | [custom_operators.md](references/custom_operators.md) |


## Adjacent Skills

For alpha optimization (submission thresholds, backtesting verification, iterative improvement), use `wq-alpha-optimizer`. Platform documentation knowledge (neutralization, thresholds, formulas, FAST D1, HTVR, etc.) is maintained in `wq-alpha-optimizer/references/platform-knowledge.md`.

## References

- [references/operators.md](references/operators.md) -- 107 operators with Python implementations
- [references/data_fields.md](references/data_fields.md) -- Common MATRIX field reference
- [references/store_patterns.md](references/store_patterns.md) -- Store usage patterns
- [references/custom_operators.md](references/custom_operators.md) -- Custom operator implementations
- [references/platform-gotchas.md](references/platform-gotchas.md) -- 19+ platform-specific pitfalls
- [references/settings-trimming.md](references/settings-trimming.md) -- Python Alpha settings whitelist
- [references/conversion-evals.md](references/conversion-evals.md) -- 35 accuracy test cases
- [scripts/test_conversion.py](scripts/test_conversion.py) -- Conversion quality tests
