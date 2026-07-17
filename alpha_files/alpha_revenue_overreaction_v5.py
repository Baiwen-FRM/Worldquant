# Alpha ID: alpha_revenue_overreaction_v5
# 策略说明: 在分析师营收预期排名前50%的股票中，做空近期涨幅最大的（均值回归）
# 改动: 字段从 sales_estimate_median_value 换成 anl4_..._sales_mean（均值预测）
# BRAIN表达式: trade_when(rank(anl4_..._sales_mean) > 0.5, -rank(ts_mean(returns, 5)), 0)
# Settings: region=USA, universe=TOP3000, delay=1, decay=5, neutralization=INDUSTRY, truncation=0.08, pasteurization=ON

from brain.alphas import alpha
import numpy as np

def field_to_float(x):
    if np.issubdtype(x.dtype, np.integer):
        missing = np.iinfo(x.dtype).min
        out = x.astype(np.float64)
        out[x == missing] = np.nan
        return out
    return x.astype(np.float64)

def cross_sectional_rank(x):
    invalid = np.isnan(x)
    n = np.sum(~invalid)
    if n == 0:
        return np.full_like(x, np.nan)
    x_filled = np.where(invalid, -np.inf, x)
    order = np.argsort(x_filled)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(x))
    return np.where(invalid, np.nan, (ranks + 1) / n)

def pasteurize(a, u):
    a = a.copy()
    a[~u.astype(bool)] = np.nan
    return a

def scale(a):
    a0 = np.nan_to_num(a, nan=0, posinf=0, neginf=0)
    norm = np.linalg.norm(a0, ord=1)
    return a / norm if norm > 0 else a

@alpha(
    data=["anl4_fs_detail_estimates_basic_af_v4_nd_sales_mean", "returns"],
    store=["prev_signal"],
)
def alpha_fn(data, store):
    u = data.universe[-1].astype(bool)
    n = u.shape[0]

    # 营收均值预测 → 截面排名 → 前50%
    rev_est = field_to_float(data.anl4_fs_detail_estimates_basic_af_v4_nd_sales_mean[-1])
    high_rev = cross_sectional_rank(rev_est) > 0.5

    # 过去5天平均收益率 → 做空涨幅最高的
    ret_5d = field_to_float(data.returns[-5:].mean(axis=0))
    short_signal = -cross_sectional_rank(ret_5d)

    # trade_when(high_rev, short_signal, 0)
    if store.prev_signal is None:
        store.prev_signal = np.zeros(n, dtype=np.float64)

    result = np.where(high_rev, short_signal, store.prev_signal)
    result[~high_rev & (np.abs(store.prev_signal) < 1e-10)] = np.nan
    store.prev_signal = short_signal.copy()

    result = pasteurize(result, u)
    result = scale(result)
    return result.astype(np.float32)
