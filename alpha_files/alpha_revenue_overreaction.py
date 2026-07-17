# Alpha ID: alpha_revenue_overreaction
# 策略说明: 在分析师营收预期排名前20%的股票中，做空近期涨幅最大的（均值回归）
# 原始思路: 分析师高营收预期的股票如果最近涨多了，可能过度乐观 → 均值回归
# BRAIN表达式: trade_when(rank(sales_estimate_median_value) > 0.8, -rank(ts_mean(returns, 5)), 0)
# Settings: region=USA, universe=TOP3000, delay=1, decay=5, neutralization=INDUSTRY, truncation=0.08, pasteurization=ON

from brain.alphas import alpha
import numpy as np


def field_to_float(x):
    """将BRAIN int32/float32字段转为float64，把标记缺失值替换为NaN。"""
    if np.issubdtype(x.dtype, np.integer):
        missing = np.iinfo(x.dtype).min
        out = x.astype(np.float64)
        out[x == missing] = np.nan
        return out
    return x.astype(np.float64)


def cross_sectional_rank(x):
    """截面排序，返回0-1归一化排名。"""
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
    """将不在universe中的股票信号置为NaN。"""
    a = a.copy()
    a[~u.astype(bool)] = np.nan
    return a


def scale(a):
    """L1归一化。"""
    a0 = np.nan_to_num(a, nan=0, posinf=0, neginf=0)
    norm = np.linalg.norm(a0, ord=1)
    return a / norm if norm > 0 else a


@alpha(
    data=["sales_estimate_median_value", "returns"],
    store=["prev_signal"],
)
def alpha_fn(data, store):
    """
    策略流程:
    1. 计算营收预期的截面排名，筛选前20%的股票
    2. 在这些股票中，做空过去5天涨幅最大的（-rank(returns)）
    3. 其他股票保持原来的仓位（trade_when逻辑）
    """
    u = data.universe[-1].astype(bool)
    n = u.shape[0]

    # 营收预期的截面排名，筛选高营收预期股票
    rev_est = field_to_float(data.sales_estimate_median_value[-1])
    high_rev = cross_sectional_rank(rev_est) > 0.8

    # 过去5天平均收益率的截面排名 → 做空涨幅最高的
    ret_5d = field_to_float(data.returns[-5:].mean(axis=0))
    short_signal = -cross_sectional_rank(ret_5d)

    # trade_when(high_rev, short_signal, 0) 实现:
    # - 条件为真 → 输出做空信号
    # - 条件为假 & 上一期信号不为0 → 保持仓位
    # - 条件为假 & 上一期信号为0 → 关闭仓位（NaN）
    if store.prev_signal is None:
        store.prev_signal = np.zeros(n, dtype=np.float64)

    result = np.where(high_rev, short_signal, store.prev_signal)
    result[~high_rev & (np.abs(store.prev_signal) < 1e-10)] = np.nan

    # 保存本期未做条件筛选的原始信号，供下期trade_when使用
    store.prev_signal = short_signal.copy()

    result = pasteurize(result, u)
    result = scale(result)

    return result.astype(np.float32)
