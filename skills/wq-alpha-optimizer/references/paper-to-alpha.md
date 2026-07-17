---
name: paper-to-alpha
description: Reference table mapping academic quantitative finance papers to implementable BRAIN alpha expressions.
---

# Paper-to-Alpha Reference

## Quick Translation Table

| Year | Paper / Authors | Core Idea | BRAIN Expression | Settings | Ease |
|------|----------------|-----------|-----------------|----------|------|
| 1993 | Jegadeesh & Titman | 12-month momentum | `rank(ts_mean(returns, 252) - ts_mean(returns, 21))` | decay=5, neut=SECTOR | Easy |
| 2006 | Ang, Hodrick, Xing & Zhang | Idiosyncratic volatility | `rank(-ivol_252d)` | neut=SUBINDUSTRY | Easy |
| 2008 | Heston & Sadka | Seasonality | `rank(ts_mean(returns, 21) - ts_mean(returns[-252], 21))` | decay=3 | Medium |
| 2011 | Bali, Cakici & Whitelaw | Max daily return | `rank(-ts_max(returns, 252))` | decay=5, neut=SECTOR | Medium |
| 2013 | Novy-Marx | Gross profitability | `rank(gpoa)` | neut=INDUSTRY | Easy |
| 2015 | Fama-French (5-factor) | Profitability + Investment | `0.5 * rank(gpoa) + 0.3 * rank(-inv_1y) + 0.2 * rank(bm)` | neut=SECTOR | Easy |
| 2021 | Pedersen, Fitzgibbons, Pomorski | ESG-adjusted momentum | `rank(gpoa) + rank(esg_score)` | neut=INDUSTRY | Medium |
| 2014 | Lou | Flow-induced trading | `rank(ts_mean(returns, 252) * ts_mean(adv90, 252))` | decay=10 | Complex |
| 2005 | Jiang, Lee & Zhang | Information uncertainty | `rank(-ivol_252d) * rank(1 - analyst_coverage)` | neut=INDUSTRY | Medium |
| 2020 | Gu, Kelly & Xiu | ML cross-section | Python Alpha: rank-based ML factor output | Python | Complex |

## Implementation Notes

**Momentum (Jegadeesh & Titman 1993):** Core effect is strong, but the BRAIN
universe is TOP3000 liquid stocks. Use ts_mean(returns, 126) for 6-month or
(returns, 252) for 12-month. Add -ts_mean(returns, 21) to control 1-month
reversal if Sharpe is negative.

**Idiosyncratic Vol (Ang et al. 2006):** `ivol_252d` is available directly.
Low vol stocks outperform consistently across regions. Try both `-ivol_252d`
(low vol premium) and `ivol_252d` (lottery demand) — which one works depends
on the region.

**Gross Profitability (Novy-Marx 2013):** Simple, robust, low turnover. Best
neutralization is INDIUSTRY or SECTOR. Add decay=3 to bring Fitness up if
needed.

**Max Daily Return (Bali et al. 2011):** Best as reversal-like signal:
stocks with extreme positive days underperform. Use -ts_max(returns, 252).
Works better with some decay.

## Translation Principle

For any paper, the rule of thumb is: extract the signal intuition, not the
methodology. A typical academic paper will use Fama-MacBeth regressions with
10+ control variables, industry fixed effects, and standard error corrections.
None of that translates. What matters is:

1. What is the raw data input? (price, volume, fundamentals, alternatives)
2. What is the transformation? (rank, z-score, long-short, ratio)
3. What is the predicted holding period? (1 day, 1 month, 12 months)

Everything else is academic infrastructure that does not help on BRAIN.
