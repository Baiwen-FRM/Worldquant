---
name: submission-thresholds
description: Platform submission thresholds for users and consultants, sourced from BRAIN documentation and community forum.
---

# Submission Thresholds

**Sources:** BRAIN tutorials ("Clear these tests", "Parameters in Simulation Results",
"How to choose Simulation Settings"), "Consultant Submission Tests" page, and
community forum discussions.

## Threshold Comparison: User vs Consultant

| Test | D1 (User) | D0 (User) | D1 (Consultant) | D0 (Consultant) |
|------|-----------|-----------|-----------------|-----------------|
| Sharpe | >= 1.5 | >= 2.0 | >= 1.58 | >= 2.69 |
| Fitness | >= 1.0 | >= 1.3 | >= 1.0 | >= 1.5 |
| Turnover | N/A | N/A | 1% - 70% | 1% - 70% |
| Weight | Max < 10% | Same | Max < 10% | Same |
| Sub-universe | Yes | Yes | Yes | Yes |
| Self-corr | < 0.7 | Same | < 0.7 | Same |
| Prod-corr | < 0.7 | Same | < 0.7 | Same |
| IS-Ladder | Yes | Yes | Yes | Yes |
| Bias test | No | No | Yes | Yes |

**Note:** CHN region has higher thresholds: D1 Sharpe >= 2.08, D0 Sharpe >= 3.5.

## Fitness Labels

| Label | D1 | D0 |
|-------|-----|-----|
| Spectacular | > 2.5 | > 3.25 |
| Excellent | > 2.0 | > 2.6 |
| Good | > 1.5 | > 1.95 |
| Average | > 1.0 | > 1.3 |
| Needs Improvement | <= 1.0 | <= 1.3 |

## Fitness Formula

```
Fitness = Sharpe * sqrt(abs(Returns) / max(Turnover, 0.125))
```

## Sub-Universe Test

For TOPXXX universes:
```
cutoff = 0.75 * sqrt(sub_size / alpha_size) * alpha_sharpe
```

For non-TOPXXX universes:
```
cutoff = subuniverse_ratio * alpha_sharpe
```
- ASI MINVOL1M: 0.295
- USA ILLIQUID_MINVOL1M: 0.41
- EUR ILLIQUID_MINVOL1M: 0.355

**Tips (from docs + community):**
- Avoid size-related multipliers
- Avoid factor-momentum interaction
- More diversification helps
- Test proactively on TOP1000/TOP500/TOP200

## IS-Ladder Test

Consultants must pass the Check-IS-Sharpe test: In-Sample Sharpe for recent
2, 3, 4...10 years must stay above thresholds. If the alpha only works in a
narrow time window, it fails.

**Single Dataset Alphas** have relaxed criteria: only Last 2Y IS Sharpe must
clear: D1 >= 2.38, D0 >= 3.96 (multiplied by 0.85 if turnover < 30%).

## Regional Specifics

| Region | Special Tests |
|--------|---------------|
| GLB | AMER >= 1, APAC >= 1, EMEA >= 1 |
| ASI | Japan Robustness Sharpe >= 1 |
| CHN | Returns >= 8% (D1), >= 12% (D0); Robust universe test >= 40% retention |
| ILLIQUID_MV | After-cost Sharpe: bottom 50% >= 52.5% of top 50% |

## Common Failure Messages

| Test Failed | Message | Action |
|------------|---------|--------|
| Weight | "Max weight > 10%" | Add truncation, diversify |
| Sharpe | "Below cutoff" | Improve signal or flip negative |
| Fitness | "Below cutoff" | Increase Sharpe and/or reduce turnover |
| Sub-universe | "Fails on sub-universe" | Avoid size factors, diversify |
| Self/Prod Correlation | "Above threshold" | Change fields/operators |
| IS-Ladder | "Performance unstable" | Check for time-period fitting |

## Community-Discovered Optimization Rules

## Detailed IS-Ladder Thresholds (D1 Consultant)

From forum post (36772838378647) and consultant submissions page:

| Year | Min Sharpe |
|------|-----------|
| Fail | 1.59 |
| 2Y | >= 2.38 |
| 3Y | >= 2.38 |
| 4Y | >= 2.38 |
| 5Y | >= 2.38 |
| 6Y | >= 2.22 |
| 7Y | >= 2.06 |
| 8Y | >= 1.90 |
| 9Y | >= 1.74 |
| 10Y | >= 1.59 |

**Note:** The 2-5 year threshold is >= 2.38 (same as Single Dataset). IS Ladder
gradually relaxes after year 5. For D0, multiply thresholds accordingly.

**Single Dataset Alphas** relaxed criteria: only Last 2Y IS Sharpe required.
D1 >= 2.38, D0 >= 3.96 (multiplied by 0.85 if turnover < 30%).

## Python Alpha Submission Notes (from Chinese forum)

From post 40734489248151 (79 votes, Python alpha 提交经验分享):

| Item | Detail |
|------|--------|
| PPA eligibility | Python Alpha cannot be PPA (platform can't count operators) |
| RA only | Python Alpha can only be submitted as Regular Alpha |
| SA Selection | Python Alpha cannot be selected by SuperAlpha Selection |
| Quota impact | Does NOT affect Operators per Alpha/Operators used; DOES affect Fields per Alpha/Fields used |
| Region restriction | GLB region does not support Python Alpha |
| D0 quota | D0 Python Alpha consumes monthly D0 quota normally |
| Pyramid | Python Alpha lights up field pyramids normally |
| MultiSim | Python Alpha does not support multi-simulation |
| Payload key | Must set `language: "PYTHON"`, `lookback >= max ts window`, and put full code in `regular` field |

## ASI/MINVOL1M Notes (from Chinese forum)

- ASI regions require `max_trade=ON` in simulation settings
- Japan Robustness (JPN Sharpe >= 1.0) is the most common ASI failure point
- For IND region: Robust Universe test uses retention rate; try ts_backfill window = 90-120, group_backfill, or smaller operator windows (15/22/66)
- IND datasets are often sparse; short-window signals work better but increase prod correlation risk
- Sector grouping may be inconsistent across ASI sub-regions; prefer MARKET grouping for cross-sectional operators

From forum posts and consultant experience:
- **Decay reduces turnover** — Explicitly stated in BRAIN docs
- **Sector > Sub-industry** in TOP3000 — Preserves more cross-industry alpha
- **Correlation < 0.6 hard cutoff** — Passes PROD easily but filters good signals
- **Local correlation pre-check** — Build matrix from personal alpha history
- **80-20 test split** — If Sharpe drops >50% → overfit
- **Rank/Sign robustness** — If Sharpe drops >70% → fitting noise
## 官方文档确认的门槛（2026年更新）

以下数据来源于 BRAIN 官方文档（通过 cnhkmcp.get_documentation_page('alpha-submission') 获取），
是平台实际使用的提交门槛值。

| 门槛 | D1 用户 | D0 用户 | 来源 |
|------|---------|---------|------|
| Sharpe | >= 1.25 | >= 2.0 | 官方 "Clear these tests" 文档 |
| Fitness | >= 1.0 | >= 1.3 | 同上 |
| Turnover | 1% < Turnover < 70% | 1% < Turnover < 70% | 同上 |
| Weight test | 最大持仓 < 10% | 最大持仓 < 10% | 同上 |
| Sub-universe test | 须通过 | 须通过 | 同上 |
| Self-Correlation | < 0.7 或 Sharpe 高 10%+ | < 0.7 或 Sharpe 高 10%+ | 同上 |

**重要提示**：此前社区流传的 D1 Sharpe >= 1.5 并非官方门槛。
官方门槛为 Sharpe >= 1.25。

### Self-Correlation 细节（来自官方文档）
- 四年滚动窗口
- 如果 Sharpe 比所有相关 Alpha（correlation > 0.7）高 10% 或更多，也可以通过
- 例如：已有 Alpha X 的 Sharpe = 3.18，新 Alpha Y 与之高相关，但 Y 的 Sharpe >= 3.5（~10% 更高）即可通过

### HTVR（High Turnover）门槛（来自官方 PnL Realization Horizon 文档）
- Turnover > 20%
- PnL Realization Horizon < 20天 或 High TVR Returns > 总回报的 75%

### Fast D1 特点（来自官方 Fast D1 文档）
- 使用带 _fast_d1 后缀的数据字段
- 捕获隔夜信息（D0收盘-D1开盘）
- 门槛同 D1（Sharpe >= 1.25, Fitness >= 1.0），但数据质量更高

### D0 特点（来自官方 D0 文档）
- 使用当天数据（delay=0）
- 捕获隔夜回报和日内信息
- 门槛高于 D1：Sharpe >= 2.0, Fitness >= 1.3
- 收益分解：交易PnL + 持仓PnL
- D0 通常有更高表现

### 参考页面
可通过 `cnhkmcp.get_documentation_page('alpha-submission')` 获取完整官方提交门槛表格。
其他相关文档：`parameters-simulation-results`、`neut-cons`、`neut-users`、`understanding-pnl-realization-horizon`、
`fast-d1-documentation`、`getting-started-d0`。
