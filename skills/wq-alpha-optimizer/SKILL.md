---
name: wq-alpha-optimizer
description: 'Optimize WorldQuant BRAIN alphas via iterative simulation using strategies from official BRAIN documentation and community forum. Supports both Fast Expression and Python Alpha. Use when: (1) user provides an Alpha ID and asks to improve/submit/optimize it, (2) an alpha failed submission and needs fixes, (3) user wants to maximize Sharpe/Fitness/Margin while reducing correlation/turnover.'
metadata:
  short-description: Optimize BRAIN alphas via simulation until submission-ready
---

 # WQ Alpha Optimizer

## Overview

Given a BRAIN Alpha ID, this skill fetches the alpha's expression and metrics, identifies what failed against actual platform thresholds, applies targeted optimization strategies, runs simulations to verify improvements, and iterates until the alpha is submission-ready.

**Supports both Fast Expression and Python Alpha.** For Python Alphas, the workflow
adapts: code modifications use Python patterns (numpy, store) instead of FastExpr
strings, and settings are trimmed for Python compatibility.

## Quick Reference: Key Platform Insights

From BRAIN documentation and community forum analysis:

1. **Fitness formula:** `Fitness = Sharpe * sqrt(abs(Returns) / max(Turnover, 0.125))`
2. **Decay reduces turnover** (explicitly stated in BRAIN docs)
3. **Submission thresholds** (actual):
   - D1: Sharpe >= 1.5, Fitness >= 1.0
   - D0: Sharpe >= 2.0, Fitness >= 1.3
   - Consultant: D1 Sharpe >= 1.58, D0 Sharpe >= 2.69
6. **LOW_2Y_SHARPE (2-Year Rolling Sharpe)**:
   - Tests alpha performance over rolling 2-year windows within the simulation period
   - Fail means the alpha's recent 2-year performance is below threshold
   - Cutoff = pyramid-adjusted threshold (e.g., D1 + multiplier 1.5 → cutoff ~2.07)
   - Fix: add decay, smooth the signal, or reduce recent-period volatility
   - A gap of 0.01 (e.g., 2.06 vs 2.07) can be closed by decay or smoothing adjustments
4. **Sharpe improves in two ways:** Increase return (better signal) + Reduce volatility (neutralization)
5. **Overfitting check:** 80-20 train-test split. If Sharpe drops >50% → overfit.

---

## Workflow: Fast Expression Alpha

### Step 1: Fetch Alpha

```python
import asyncio, cnhkmcp
async def fetch(alpha_id):
    await cnhkmcp.authenticate()
    return await cnhkmcp.get_alpha_details(alpha_id)
```

Key fields: `alpha["regular"]["code"]` (expression), `alpha["settings"]`, `alpha["is"]` (metrics).

### Step 2: Analyze Against Platform Thresholds

```python
check = await cnhkmcp.get_submission_check(alpha_id)
```

Check Sharpe, Fitness, Turnover, Margin, Correlation against thresholds in
`references/submission-thresholds.md`.

### Step 3: Diagnose and Optimize

Use `references/optimization-strategies.md`. One change per iteration.

**Quick guide:**
- **Low Sharpe**: Smooth, combine signals, better neutralization, improve signal quality
- **Low Fitness**: Apply decay, smooth, or use trade_when/hump operators
- **High Turnover**: Decay, ts_mean, trade_when, hump, increase delay
- **High Correlation**: Swap data fields, change operators, diversify datasets
- **Weight/Margin issues**: Add truncation, avoid size factors
- **Overfitting risk**: Use 80-20 test split, run rank/sign robustness checks

### Step 3b: Multi-Simulation (FastExpr Only) — Parallel Variant Testing

When you have multiple plausible tweaks to test at once, use **multi-simulation** to run them in parallel rather than sequentially. This saves time when exploring several optimization directions at once.

**Key facts (confirmed from the BRAIN API):**
- Accepts **2–8 expressions** in a single request
- Language defaults to `FASTEXPR` (FastExpr only — Python alpha multi-simulation is not supported by the platform)
- All expressions share the **same simulation settings** (region, universe, delay, decay, neutralization, truncation, etc.)
- The call can take **8+ minutes** — `create_multi_simulation` waits for all to finish and returns comprehensive results for each alpha

**When to use multi-simulation:**
- Testing variations of the same core signal with different operators or parameters
- Exploring multiple decay/truncation/neutralization combinations
- Comparing different datasets for the same signal idea
- Screening several candidate expressions before diving deeper

```python
from cnhkmcp import create_multi_simulation

variants = [
    "rank(ts_mean(adv90, 20))",                          # variant 1
    "rank(ts_mean(adv90, 20)) * rank(ts_mean(returns, 20))",  # variant 2
    "ts_mean(rank(adv90), 20)",                           # variant 3
    "rank(adv90) + rank(ts_mean(returns, 40))",          # variant 4
]

result = await create_multi_simulation(
    alpha_expressions=variants,
    instrument_type="EQUITY",
    region="USA",
    universe="TOP3000",
    delay=1,
    decay=5.0,
    neutralization="INDUSTRY",
    truncation=0.5,
    pasteurization="ON",
    max_trade="OFF",
    language="FASTEXPR",
    test_period="P0Y0M",
    visualization=True,
)
```

**Response structure:**
```python
{
    "status": "completed",
    "total_alphas": 4,
    "results": [
        {
            "alpha_id": "abc123",
            "expression": "rank(ts_mean(adv90, 20))",
            "metrics": {"sharpe": 1.82, "fitness": 1.45, "turnover": 15.3, ...}
        },
        # ... one entry per variant
    ]
}
```

**Limits:**
- At least **2** expressions required; at most **8** per call
- All variants share the **same settings** — if you need different settings per variant, run separate single simulations
- Do not use for unrelated alphas; keep each batch focused on one optimization question
- **Python alphas** should use regular `create_simulation` per variant

### Step 4: Run Simulation (FastExpr)

```python
from cnhkmcp.untracked.platform_functions import SimulationData, SimulationSettings
settings = SimulationSettings(
    instrumentType=alpha["settings"]["instrumentType"],
    region=alpha["settings"]["region"],
    universe=alpha["settings"]["universe"],
    delay=alpha["settings"]["delay"],
    decay=float(alpha["settings"].get("decay", 0)),
    neutralization=alpha["settings"].get("neutralization", "NONE"),
    truncation=float(alpha["settings"].get("truncation", 0)),
    pasteurization=alpha["settings"].get("pasteurization", "ON"),
    language="FASTEXPR",
    testPeriod="P0Y0M",
)
sim_data = SimulationData(type="REGULAR", settings=settings, regular=new_expr)
result = await cnhkmcp.create_simulation(sim_data)
```

### Step 5: Evaluate and Iterate

Max 5 iterations. Present comparison table to user. Do NOT auto-submit.

---

## Workflow: Python Alpha

When the user provides a Python Alpha ID, the workflow adapts:

### Step 1: Detect Python Alpha

Check the alpha language. Python Alphas have:
- Code with `@alpha` decorator, `import numpy`, `from brain.alphas`
- Settings with `language="PYTHON"` or similar
- `alpha["regular"]["code"]` contains Python code, not FastExpr

```python
alpha = await cnhkmcp.get_alpha_details(alpha_id)
code = alpha["regular"]["code"]
is_python = "@alpha" in code and "from brain.alphas" in code
```

### Step 2: Modify Python Code

Instead of modifying a FastExpr string, modify the Python code directly.
Key modification targets:

**Parameter tuning:** Change values inside the code (lookback, window sizes, thresholds).

**Adding/removing data fields:** Edit the `@alpha(data=[...])` decorator.

**Modifying operators:** Replace numpy operations (e.g., add ts_mean via rolling window).

**Adjusting neutralization:** Change the neutralization function call or settings.

**Store-based modifications:** If alpha uses store, adjust store parameters.

### Step 3: Run Simulation (Python)

Set `language="PYTHON"` and trim settings for Python compatibility:

```python
settings = SimulationSettings(
    instrumentType=alpha["settings"]["instrumentType"],
    region=alpha["settings"]["region"],
    universe=alpha["settings"]["universe"],
    delay=alpha["settings"]["delay"],
    decay=float(alpha["settings"].get("decay", 0)),
    neutralization=alpha["settings"].get("neutralization", "NONE"),
    truncation=float(alpha["settings"].get("truncation", 0)),
    pasteurization=alpha["settings"].get("pasteurization", "ON"),
    language="PYTHON",  # <-- Important: set to PYTHON
    testPeriod="P0Y0M",
    # Do NOT include: nanHandling, unitHandling (Python doesn't support these)
)
sim_data = SimulationData(type="REGULAR", settings=settings, regular=code)
result = await cnhkmcp.create_simulation(sim_data)
```


**Helper script:** Use `scripts/optimize_alpha.py --simulate --language PYTHON --code "your_code"` to simulate Python Alphas from the command line. The script auto-detects the alpha language.
**Settings trimming for Python Alpha:**
- Remove: `nanHandling`, `unitHandling` (not supported in Python)
- Remove: `startDate`, `endDate`, `testPeriod` (metadata only)
- Keep: all other standard settings

### Step 4: Python-Specific Optimization Patterns

**Replace a FastExpr-like operation in Python:**
```python
# Original: ts_mean(rank(returns), 5)
# Python equivalent: rolling mean on ranked data
ranked = cross_sectional_rank(data.returns[-1].copy())
window = 5
if data.returns.shape[0] >= window:
    smoothed = np.mean([cross_sectional_rank(data.returns[-i].copy()) 
                        for i in range(1, window+1)], axis=0)
```

**Add complementary signal:**
```python
# Original: 0.7 * rank(returns) + 0.3 * rank(ts_mean(adv, 20))
signal1 = cross_sectional_rank(data.returns[-1].copy())
adv_mean = np.mean(data.adv[-20:], axis=0)
signal2 = cross_sectional_rank(adv_mean)
combined = 0.7 * signal1 + 0.3 * signal2
```

**Adjust decay via settings:**
Change `decay` parameter in settings -- same effect as FastExpr.


**完整 Python Alpha 策略参考：** 见 `references/optimization-strategies.md` 中新增的 `## Python Alpha: Strategy Equivalents` 章节。该章节提供了所有 FastExpr 优化策略对应的 Python 实现代码，包含运算符快速查询表、各策略组的 Python 等价模式（低 Sharpe、低 Fitness、高 Turnover、高 Correlation、Sub-Universe、IS Ladder 等），以及 Python 独有优化手段（numpy 自由运算、regime switch、循环复合信号等）。
**Flip negative Sharpe:**
Add `-` before the return statement: `return -signal.astype(np.float32)`

### Step 5: Evaluate

Same criteria as Fast Expression. The result metrics are identical.

### Conversion Path

If a Fast Expression alpha needs Python optimization:
 1. First convert: use `wq-alpha-converter` skill
2. Then optimize the Python version using the Python workflow above

---

## API Quick Reference

| Method | Purpose |
|--------|---------|
| `cnhkmcp.authenticate()` | Login |
| `cnhkmcp.get_alpha_details(id)` | Expression + settings + metrics |
| `cnhkmcp.create_simulation(SimulationData)` | Single alpha simulation |
| `cnhkmcp.create_multi_simulation(expressions, ...)` | Multi-simulation (2–8 FastExpr alphas in parallel) |
| `cnhkmcp.get_submission_check(id)` | Full submission check |
| `cnhkmcp.check_correlation(id, "both")` | Production + self correlation |
| `cnhkmcp.get_alpha_pnl(id)` | Historical PnL |
| `cnhkmcp.get_platform_setting_options()` | Valid settings values |
| `cnhkmcp.get_datafields(data_type="MATRIX", ...)` | Find alternative data fields |
| `cnhkmcp.get_operators()` | All operators with descriptions |
| `cnhkmcp.get_documentation_page(id)` | Fetch BRAIN docs |
| `cnhkmcp.submit_alpha(id)` | Submit (only if user asks) |


## Key Constraints

1. **One change per iteration** -- Isolate cause and effect.
2. **Preserve core logic** -- Tune, do not rewrite from scratch.
3. **5-iteration limit** -- Stop after 5 attempts if no clear improvement.
4. **Negative Sharpe** -- Wrap in `-(...)` (FastExpr) or `return -signal` (Python).
5. **Check correlation at the end** -- Always `check_correlation(new_id, "both")`.
6. **Python Alpha settings** -- Remove nanHandling, unitHandling from settings.
7. **Test Period** -- Only for FastExpr. Python uses lookback instead.
8. **Overfitting check** -- Run rank/sign robustness checks on the final result.
9. **Paper-to-alpha: extract signal intuition, not methodology** -- Academic regressions with 20 control variables don't translate; the core effect is what drives the signal.
10. **Batch checkpoint: always use manifest when more than 8 variants** -- Prevents wasted platform quota and lost progress. Save after each batch.
11. **Resume is automatic** -- The manifest pattern makes resume free; reload and re-run.



## Academic Paper-Driven Alpha Ideas

Beyond tuning existing alphas, this section provides a structured workflow for translating findings from quantitative finance papers into testable BRAIN expressions.

### Workflow: Paper to Alpha

#### Step 1: Identify a Paper

When tuning has plateaued or the user needs orthogonal signals, the first step is to find a relevant paper. Use web search or the user's own sources. Productive categories include:

| Source Category | Examples | Typical Signal Type |
|----------------|----------|-------------------|
| Factor/Anomaly | Jegadeesh & Titman (1993), Novy-Marx (2013) | Cross-sectional momentum, profitability |
| Market Microstructure | Avramov et al. (2006), Hendershott et al. (2011) | Liquidity, order imbalance, bid-ask |
| Sentiment/NLP | Tetlock (2007), Loughran & McDonald (2011) | Text-based sentiment, tone |
| ML/AI | Gu, Kelly & Xiu (2020), Moritz & Zimmermann (2016) | Tree-based factors, neural net portfolios |
| Options/Vol | Ang et al. (2006), Bali et al. (2011) | Vol-of-vol, IV skew, max daily return |
| ESG | Pedersen et al. (2021), Pastor et al. (2021) | ESG momentum, green innovation |

#### Step 2: Extract the Core Signal Logic

For any paper, extract these three elements:

**1. Data inputs needed** -- Map paper data to BRAIN fields: `returns`, `adv20`, `bm`, `earnings_yield`, `gpoa`, `accruals`, `ivol`, `snt_buzz`, etc.

**2. Signal construction** -- Map transformations to BRAIN operators: `rank(x)`, `ts_mean(x, d)`, `group_neutralize(x, g)`, `zscore(x)`, `winsorize(x, min, max)`, `trade_when(c, s, e)`

**3. Holding period** -- Estimate signal decay: Short (1-5d) translates to high turnover; Medium (5-20d) is standard; Long (20-60d) needs IS Ladder check

#### Step 3: Express as BRAIN Formula

Map each paper step to BRAIN operators:

```
Paper: "Sort stocks by past 12-month return" (Jegadeesh & Titman 1993)
BRAIN: rank(ts_mean(returns, 252))

Paper: "Sort by gross profitability / total assets" (Novy-Marx 2013)
BRAIN: rank(gpoa)

Paper: "Rank by 1-day reversal controlling for size" (Heston et al.)
BRAIN: group_neutralize(-rank(ts_delta(close, 1)), sector)
```

**Do not replicate exact methodology -- extract the core signal intuition.** Academic regressions with 20 control variables do not translate; the main effect is what matters.

#### Step 4: Screen with Single Simulation

```python
result = await create_simulation(
    type="REGULAR", instrument_type="EQUITY", region="USA",
    universe="TOP3000", delay=1, decay=0,
    neutralization="NONE", truncation=0,
    language="FASTEXPR",
    regular="rank(ts_mean(returns, 252))",
    test_period="P0Y0M",
)
```

**Expected outcomes:**
- Sharpe 0.3-0.6: Raw signal noisy. Needs smoothing (S1), neutralization (S2), or complementary signal (S6)
- Sharpe 0.6-1.0: Core signal valid. Apply standard optimization strategies from `references/optimization-strategies.md`
- Sharpe greater than 1.0: Strong signal. Proceed immediately
- Negative: Region applies opposite effect. Flip with `-(...)`

#### Step 5: Multi-Simulation Screening

Test 3-8 variants in parallel:

```python
base = "rank(ts_mean(returns, 252))"
variants = [
    base,
    f"ts_mean({base}, 20)",
    f"group_neutralize({base}, sector)",
    f"group_neutralize({base}, subindustry)",
    f"{base} * rank(ts_mean(adv90, 20))",
    f"trade_when(rank(adv20) > 0.1, {base}, 0)",
]
result = await create_multi_simulation(
    alpha_expressions=variants,
    instrument_type="EQUITY", region="USA", universe="TOP3000",
    delay=1, decay=5, neutralization="INDUSTRY", truncation=0.5,
    language="FASTEXPR", test_period="P0Y0M", visualization=True,
)
```

#### Step 6: Compare Against Correlation Baseline

If the best variant shows Sharpe greater than 1.0 and Fitness greater than 0.8, proceed to full optimization using the standard workflow.

### Curated Paper Collection (BRAIN-Implementable)

| Paper / Author | Core Idea | BRAIN Expression Sketch | Ease |
|---------------|-----------|------------------------|------|
| Jegadeesh and Titman (1993) | 12-month momentum | `rank(ts_mean(returns, 252) - ts_mean(returns, 21))` | Easy |
| Novy-Marx (2013) | Gross profitability | `rank(gpoa)` | Easy |
| Ang, Hodrick, Xing and Zhang (2006) | Idiosyncratic volatility | `rank(-ivol_252d)` | Easy |
| Bali, Cakici and Whitelaw (2011) | Max daily return | `rank(-ts_max(returns, 252))` | Medium |
| Fama-French (2015) | Profitability + Investment | `rank(gpoa) + rank(-inv_1y) + rank(bm)` | Easy |
| Pedersen, Fitzgibbons, Pomorski (2021) | ESG-adjusted ranking | `rank(gpoa) + rank(esg_score)` | Medium |
| Heston and Sadka (2008) | Seasonality | `rank(ts_mean(returns,21)-ts_mean(returns[-252],21))` | Medium |
| Gu, Kelly and Xiu (2020) | ML cross-section | `rank(ml_factor)` via Python Alpha | Complex |

---

## Batch Alpha Simulation with Checkpoint Resume

When screening many expressions or running large-scale variant tests (10+ candidates), individual runs are slow and interruptions waste completed work. This section documents a checkpoint-based batch workflow that tracks progress and supports automatic resume.

### Why Checkpoint Matters

`create_multi_simulation` accepts at most 8 expressions per call. If you have 20 variants to test, that is at least 3 batches. If batch 2 fails (network error, timeout), you need to know which succeeded and which still need running.

### Checkpoint Workflow

#### Step 1: Prepare a Variant Manifest

A manifest is a local JSON file tracking each variant and its status:

```json
{
  "run_id": "sweep-20260716",
  "created": "2026-07-16T10:00:00Z",
  "settings": { "region": "USA", "universe": "TOP3000", "delay": 1, "decay": 3, "neutralization": "INDUSTRY" },
  "variants": [
    {"id": "v01", "source": "baseline",  "expr": "rank(ts_mean(returns, 20))",                    "status": "pending"},
    {"id": "v02", "source": "smoothing", "expr": "ts_mean(rank(returns), 20)",                    "status": "pending"},
    {"id": "v03", "source": "liquidity", "expr": "rank(ts_mean(returns,20))*rank(ts_mean(adv90,20))", "status": "pending"}
  ],
  "results": {}
}
```

#### Step 2: Batch Dispatch

Group pending variants into batches of up to 8, dispatch each, update manifest:

```python
def get_pending_batches(m, size=8):
    pending = [v for v in m["variants"] if v["status"] == "pending"]
    return [pending[i:i+size] for i in range(0, len(pending), size)]

async def dispatch_batch(batch, settings):
    exprs = [v["expr"] for v in batch]
    result = await create_multi_simulation(alpha_expressions=exprs, **settings)
    return result["results"]
```

#### Step 3: Resume After Interruption

If a batch fails, reload the manifest and re-run -- pending variants are automatically dispatched, completed ones are skipped:

```python
manifest = json.load(open("wq_manifest.json"))
completed = [v for v in manifest["variants"] if v["status"] == "completed"]
pending = [v for v in manifest["variants"] if v["status"] == "pending"]
print(f"Resume: {len(completed)} done, {len(pending)} remaining")
```

#### Step 4: Compare Results

After all batches complete, produce a ranked comparison:

```python
ranked = sorted(manifest["results"].values(), key=lambda r: r["metrics"]["sharpe"], reverse=True)
for r in ranked:
    print(f"{r['alpha_id']:10s} Sharpe={r['metrics']['sharpe']:.2f}  Fitness={r['metrics']['fitness']:.2f}")
```

### When to Use Batch + Checkpoint

| Scenario | Suggestion |
|----------|-----------|
| Tuning plateaued, need new signal directions | Use paper-driven ideas above, then batch-screen top 10-20 variants |
| Settings sweep (decay x neut x truncation) | Create manifest with permutations, batch 8 per run |
| Correlation reduction (need orthogonal signals) | Batch 8-16 candidates, sort by Sharpe + 1-corr for Pareto frontier |
| Python Alpha variants (no multi-sim support) | Manifest still works; dispatch one-at-a-time sequentially |

### Rule of Thumb

If your variant count exceeds 8, use a checkpoint manifest. It costs almost nothing to set up and saves hours of re-runs after a platform timeout.



## References

- [references/optimization-strategies.md](references/optimization-strategies.md) -- Strategies by failure type
- [references/submission-thresholds.md](references/submission-thresholds.md) -- Platform thresholds from docs and forum
- [scripts/optimize_alpha.py](scripts/optimize_alpha.py) -- Helper script

## Adjacent Skills

 For FastExpr to Python Alpha conversion, use `wq-alpha-converter`.

## Platform Knowledge

Shared BRAIN platform documentation knowledge is maintained in:

- **`references/platform-knowledge.md`** -- All extracted official docs insights (neutralization, thresholds, formulas, FAST D1, HTVR, PnL Horizon, etc.)
- **`references/read-docs-index.md`** -- Single source of truth for tracked document reading; shared with `wq-alpha-converter`

When `cnhkmcp.get_documentation_page(id)` discovers new or updated documentation:
1. Update `references/platform-knowledge.md` (add/revise topic section)
2. Update `references/read-docs-index.md` (mark as read)
