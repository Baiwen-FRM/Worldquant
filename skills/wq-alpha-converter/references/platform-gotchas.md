# Python Alpha Platform Gotchas

Platform-specific pitfalls discovered during FastExpr → Python Alpha conversion.

---

## Settings & Submission

| Issue | Detail | Mitigation |
|-------|--------|------------|
| `startDate` / `endDate` rejection | `get_alpha_details()` returns these in settings, but `create_simulation()` rejects them | Always remove these fields before submit. See `settings-trimming.md` |
| `nanHandling` / `unitHandling` | Regular-only settings; **PYTHON language rejects** them with 400 error. `unitHandling=VERIFY` and `nanHandling=OFF` are not valid choices for `language=PYTHON` | Always remove `unitHandling` and `nanHandling` from the settings payload when `language=PYTHON`. Handle NaN behavior explicitly in code instead |
| `universe` | Region-specific availability. `TOP3000` only works for USA; CHN rejects it with 400 error. `get_alpha_details()` returns TOP3000 even for CHN alphas, but `create_simulation()` validates region-universe compatibility | For CHN, the only available universe is `TOP2000U`. Always check `get_platform_setting_options()` before submitting for non-USA regions |
| `visualization` | Required by BRAIN API for PYTHON language. Missing field causes 400 error even though `create_simulation()` MCP tool has a default `True` | Always include `"visualization": False` in the settings payload |
| `lookback` | **Required** for PYTHON language, but the `create_simulation()` MCP tool wrapper's `SimulationSettings` model **does not include a `lookback` field**. Using the MCP tool always fails for PYTHON | Submit directly via `brain_client.session.post()` with `"lookback": N` inside the settings dict. Set `N = max(largest_ts_window, default_252)` |
| `submission_unknown` | Network timeout / 5xx after `POST /simulations`, client can't tell if platform created the task | Check platform UI manually; don't blindly resubmit. Log the simulation name for manual lookup |
| Settings mismatch | Regular Alpha detail settings may contain fields not accepted by Python submit | Use `get_platform_setting_options()` to validate; trim non-Python fields |
| lookback off-by-one | Python Alpha receives `lookback + 1` rows. A ts_* with `d=252` needs `lookback >= 252` | If code needs 317 rows including today, set `lookback = 316` |

## Execution Model

| Issue | Detail | Mitigation |
|-------|--------|------------|
| Computed intermediate too expensive | Rebuilding a long computed history every day (e.g. ts_zscore over ts_mean of 252 returns) will timeout | Use typed `store` to cache intermediate values per day; see `store_patterns.md` |
| Store warm-up period | Store starts empty at first call; takes `d` days before time-series over store is fully populated | Disclose warm-up days in Notes. Compare post-warm-up Sharpe vs FastExpr |
| Warm-up ≠ pre-start history | FastExpr may have pre-start data for operators like `ts_sum`; Python Alpha store has none | Accept that first `d` days will have degraded quality; note in submission |
| `vec_*` operators unsupported | Python Alpha doesn't support BRAIN vector data types. `vec_avg` / `vec_max` etc. can't convert | Stop conversion if expression depends on vector fields. Keep as Regular |
| MultiSim unsupported | Multi-simulation (multiple scenarios) not available for Python Alpha | Submit single simulations only |
| GLB region | GLB (Global) region temporarily doesn't support Python Alpha | Use USA, CHN, or other supported regions |

## Data Handling

| Issue | Detail | Mitigation |
|-------|--------|------------|
| int32 sentinel values | Integer fields (sector, industry, subindustry) use `np.iinfo(np.int32).min` as NaN sentinel | Always use `field_to_float()` helper before computation; see `SKILL.md` template |
| data.field read-only | `data.field` is a read-only ndarray. Mutation crashes silently | Always `.copy()` before modification |
| Universe mask | `data.universe[-1]` is int 1/0, not bool | Convert: `data.universe[-1].astype(bool)` |
| np.nanmean / np.nanstd warnings | These emit RuntimeWarning on all-NaN slices; platform may fail without surfacing the warning | Pre-filter with `np.isfinite()` or use `np.warnings.filterwarnings('ignore')` in alpha code |
| dtypes | `data.field` arrives as float32; arithmetic promotes to float64 implicitly | Be explicit about dtype. Return `np.float32` |

## Signal & Control Flow

| Issue | Detail | Mitigation |
|-------|--------|------------|
| `np.isclose(signal, z)` filtering when `trade_when(..., z)` uses z as default | `-group_rank(returns, group)` produces signals in [-1, 0). If `z=-1`, filtering out all values `isclose` to -1 deletes the strongest short signals — the stocks with the highest returns in their group. This inflates turnover (~+22%) and degrades Sharpe. The `z` parameter is a control-flow instruction to the runtime ("hold prev signal when condition is false"), not a sentinel value to be stripped. | Never add post-processing like `np.where(np.isclose(signal, -1), np.nan, signal)` in a `trade_when` alpha. The legal signal range may overlap with `z`. The runtime handles the `z` case internally; the Python implementation uses `store.prev_signal` for that. |


## Store & State

| Issue | Detail | Mitigation |
|-------|--------|------------|
| `extend: np.nan` is wrong | `extend` must match the container dtype exactly. `np.nan` is Python float = float64, may mismatch | Use `{"extend": np.float64(np.nan)}` for float64, `{"extend": np.float32(np.nan)}` for float32 |
| Store `is None` check | `store.field is None` is true only on the very first call. After that, the array exists (even if all-NaN) | Only use `is None` for initialization. Don't use `hasattr()` |
| Store persistence | Store persists between time steps but is re-created each simulation run | No special action needed; just be aware for warm-up calculations |
| Store dims must match | `dims="xi"` expects 2-D; assigning 1-D will crash | Match your assignment shape to `dims` declaration |

## Error Diagnosis

Use `cnhkmcp.lookINTO_SimError_message(locations=[sim_id])` to decode simulation failure reasons.
Common errors include:

| Error Pattern | Likely Cause |
|--------------|-------------|
| `timeout` during simulation | Computed intermediate too expensive; add store caching |
| `NaN` in output or `pasteurization` failures | Integer sentinel not converted, or divide-by-zero not guarded |
| Settings rejection | `startDate`, `nanHandling`, or other Regular-only fields in settings |
| `MemoryError` | Data too large; reduce window size or cache in store |
| `KeyError` on data field | Field name typo or field not available as MATRIX type |

---

*Maintained alongside `operators.md` and `custom_operators.md`. Update when new platform behaviors are discovered.*

## Forum-Discovered Gotchas (顾问中文论坛)

From community posts (40734489248151 "Python alpha 提交经验分享" and comments):

| Issue | Detail | Mitigation |
|-------|--------|------------|
| Python Alpha quota impact | Does NOT affect Operators per Alpha/Operators used; DOES affect Fields per Alpha/Fields used | Document that conversion saves operator quota but still consumes field quota |
| Python Alpha cannot be PPA | Platform cannot count operators used in Python Alpha (no FastExpr), so cannot determine PPA eligibility (<=8 operators) | Only submit Python Alpha as RA (Regular Alpha), never expect PPA status |
| Python Alpha cannot be SA-selected | SuperAlpha Selection cannot currently select Python Alphas | If user needs SA combination, keep as FastExpr |
| Python Alpha instability | Sometimes a failing Python Alpha passes when re-simulated with identical code | Build retry mechanism: if first attempt fails with no clear error, retry once |
| Nested lookback estimation | ts_mean(ts_decay_linear(x,5),5) needs lookback >= 10, not just max(5,5)=5 | Estimate cumulative: outer window + inner window for nested time-series |
| FastExpr IS Ladder pre-check | If FastExpr version already fails IS Ladder, Python version will not fix it — IS Ladder is data quality, not language-dependent | Always pre-check FastExpr IS Ladder before converting; skip conversion if it fails |
| Python Alpha intermittent web errors | Web UI crashes during Python sim; opening new sim bar + re-pasting code occasionally works | Try re-simulation before debugging code logic |
| scipy/scikit-learn support | Training sessions mention support; actual behavior may vary | Import at your own risk; test thoroughly before relying on external packages |
| Vector fields unsupported | Python Alpha does NOT support Vector-type data fields at all | If FastExpr uses vec_* on vector fields, keep as Regular — conversion impossible |
