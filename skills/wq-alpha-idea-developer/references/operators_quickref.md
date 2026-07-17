# 常用运算符快速参考

## 截面运算符

| 运算符 | 说明 | 示例 |
|-------|------|------|
| `rank(x)` | 截面排名，归一化到0-1 | `rank(returns)` |
| `group_rank(x, group)` | 组内排名 | `group_rank(returns, sector)` |
| `group_neutralize(x, group)` | 减去组均值 | `group_neutralize(returns, industry)` |
| `zscore(x)` | 截面标准化 | `zscore(returns)` |
| `winsorize(x, min, max)` | 缩尾处理 | `winsorize(returns, 0.01, 0.99)` |
| `scale(x)` | L1归一化 | `scale(rank(returns))` |
| `bucket(x, range)` | 分桶 | `bucket(rank(returns), 5)` |

## 时间序列运算符

| 运算符 | 说明 | 示例 |
|-------|------|------|
| `ts_mean(x, d)` | d日移动平均 | `ts_mean(returns, 20)` |
| `ts_sum(x, d)` | d日求和 | `ts_sum(returns > 0, 5)` |
| `ts_std(x, d)` | d日标准差 | `ts_std(returns, 20)` |
| `ts_rank(x, d)` | d日时间序列排名 | `ts_rank(returns, 20)` |
| `ts_min(x, d)` | d日内最小值 | `ts_min(low, 20)` |
| `ts_max(x, d)` | d日内最大值 | `ts_max(high, 20)` |
| `ts_argmin(x, d)` | 最小值位置 | `ts_argmin(low, 20)` |
| `ts_argmax(x, d)` | 最大值位置 | `ts_argmax(high, 20)` |
| `ts_delta(x, d)` | 当前-d日的差值 | `ts_delta(close, 1)` |
| `ts_percentile(x, d, p)` | d日p分位数 | `ts_percentile(returns, 20, 0.5)` |
| `ts_corr(x, y, d)` | d日相关系数 | `ts_corr(returns, adv20, 20)` |
| `ts_covariance(x, y, d)` | d日协方差 | `ts_covariance(returns, adv20, 20)` |
| `ts_regression(x, y, d)` | 线性回归斜率 | `ts_regression(returns, adv20, 20)` |
| `ts_entropy(x, d)` | d日信息熵 | `ts_entropy(returns, 20)` |

## 复杂运算符

| 运算符 | 说明 | 示例 |
|-------|------|------|
| `trade_when(c, s, e)` | 条件触发交易 | `trade_when(rank(x)>0.8, y, -1)` |
| `hump_decay(x, r)` | 驼峰衰减 | `hump_decay(rank(returns), 5)` |
| `ts_decay_exp_window(x, d, factor)` | 指数衰减窗口 | `ts_decay_exp_window(rank(returns), 20, 0.5)` |
| `ts_min_diff(x, d)` | 最小值到当前位置的差值 | `ts_min_diff(close, 20)` |
| `ts_min_max_cps(x, d)` | 当前位置在min-max区间的位置 | `ts_min_max_cps(high, 20)` |
| `ts_min_max_diff(x, d)` | (max-min) 占当前位置比例 | `ts_min_max_diff(close, 20)` |
| `ts_skewness(x, d)` | d日偏度 | `ts_skewness(returns, 20)` |

## 逻辑/条件运算符

| 运算符 | 说明 | 示例 |
|-------|------|------|
| `if_else(c, t, f)` | 条件判断 | `if_else(rank(x)>0.5, x, 0)` |
| `>`, `<`, `==`, `>=`, `<=` | 比较运算符 | `returns > 0` |
| `+`, `-`, `*`, `/` | 四则运算 | `rank(x) + rank(y)` |
| `max(x, y)` | 取大值 | `max(rank(x), rank(y))` |
| `min(x, y)` | 取小值 | `min(rank(x), rank(y))` |
| `abs(x)` | 绝对值 | `abs(returns)` |
| `log(x)` | 自然对数 | `log(adv20)` |
| `sign(x)` | 符号函数 | `sign(returns)` |
| `sigmoid(x)` | Sigmoid函数 | `sigmoid(rank(returns))` |
| `tanh(x)` | Tanh函数 | `tanh(zscore(returns))` |
