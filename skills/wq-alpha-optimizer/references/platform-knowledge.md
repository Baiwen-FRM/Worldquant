# BRAIN Platform Knowledge Base

来源：WorldQuant BRAIN 官方文档（通过 `cnhkmcp.get_documentation_page()` 获取）
及官方社群精华文章。此文件由 `wq-alpha-optimizer` 维护，为相关 skill 提供共享的平台知识。

---

## Fast Expression 语言定义

根据官方文档："Fast expression" 是一种专有编程语言，设计为一种伪代码形式，使用自然语言和简单的编程结构来表达算法的逻辑。一个 Fast Expression 由 data fields（如 close, returns）、operators（如 ts_rank, rank）和 constants（数值）组成。

---

## Alpha 执行模型（七步流程）

BRAIN 平台在执行 Alpha 表达式时，后台经历七个步骤：
1. 获取表达式 → 2. 获取数据集 → 3. 计算 Alpha 值 → 4. 中性化（设置中的 Neutralization） → 5. 归一化（缩放至 [0,1]） → 6. 缩放至账面规模 → 7. 组合权重

**关键观察**：步骤4 "中性化" 是设置的最后一环。如果表达式中末尾使用了 `group_neutralize(x, group)`，则设置中应设 Neutralization=None、Decay=0、Truncation=0。

如果 Fitness 低，问题可能在步骤3（信号质量）或步骤4（中性化选择）。如果 Turnover 高，问题在步骤3 的信号更新频率。

---

## 中性化规则

官方文档明确指出："Neutralization in Simulation Settings" 和 `group_neutralize(x, group)` 使用相同的操作。

当在表达式中使用 `group_neutralize(x, group)` 作为最后一个算子时，设置中应该：
- Neutralization = None（因为 group_neutralize 已经执行了中性化）
- Decay = 0（可以手动在表达式内插入 decay 算子）
- Truncation = 0（可以手动在表达式内插入 truncation 算子）

深入理解：
- 市场中性化 = Alpha - mean(Alpha)，确保多空等额
- 行业/子行业中性化在各自组内减均值
- `group_neutralize` 与设置中的 Neutralization 可互换：效果相同
- 可以在表达式内手动插入 decay/truncation 算子
- **关键观察**：在使用 TOP3000 作为 universe 时，Sector 中性化比 Sub-Industry 保留更多跨行业 alpha；Sub-Industry 在大型 universe 中可能会过度清洗

### 风险中性化类型 (Risk Neutralization)

官方 "Advanced Topics" 文档列出四种风险中性化：
1. Default（常规中性化）
2. Crowding Risk-Neutralized：控制拥挤风险
3. RAM Risk-Neutralized：基于 RAM 模型
4. Statistical Risk-Neutralized：统计方法

每种类型有不同的 Sharpe 和容量特征，对于已有 Alpha 池中添加新 Alpha 时有不同的相关度特征。

### 自定义中性化（使用 bucket + rank）

官方 Silver 示例提示可以用 `floor`/`bucket` 算子结合 `rank` 实现自定义分组中性化。
例如按历史波动率创建自定义组：
- FastExpr: `group_neutralize(alpha, floor(rank(ts_stddev(returns, 60)), 10))`

---

## 双重中性化 (Double Neutralization)

官方 "Double Neutralization" 文档关键发现：
- 适用于多国家区域（EUR, ASI, GLB）：同时按行业和国家中性化
- **顺序 group_neutralize 会部分抵消**：`group_neutralize(group_neutralize(Alpha, industry), country)` 中第二次中性化会部分抵消第一次
- **正确做法**：使用 `group_cartesian_product(industry, country)` 将两组合并，再对合成组做一次 group_neutralize
- **ASI 区域示例**：`alpha = ts_rank(eps, 252); group = densify(group_cartesian_product(industry, country)); group_neutralize(alpha, group)`
- **USA 区域示例**：`group = group_cartesian_product(sector, sta1_top1000c50); alpha = group_rank(ts_rank(eps, 252), group); group_neutralize(alpha, group)`

---

## D0 vs D1 vs Fast D1

### D0 Alpha
- 使用当天的数据（delay=0），在收盘前一定时间执行交易，捕获隔夜回报
- D0 收益分解为：交易PnL（短期）+ 持仓PnL（较长持有期）
- 隔夜回报（Overnight Returns）：公司在收盘后发布新闻/财报导致的价格变动，D1 无法捕获
- D0 预期表现更高（由于信息优势）

### Fast D1 框架
- 使用 D0 收盘到 D1 开盘之间的数据（隔夜信息）
- 数据字段带 `_fast_d1` 后缀（如 `snt_buzz_fast_d1` vs `snt_buzz`）
- 捕获：隔夜新闻、盈利公告、分析师更新、盘前交易
- 比 D1 更有信息优势，同时比 D0 更容易执行

三种 delay 对比：
- Delay 1（snt_buzz）：昨日收盘数据，仅捕获昨日收盘数据
- Fast D1（snt_buzz_fast_d1）：今日开盘数据，捕获隔夜新闻、事件、盘前交易
- Delay 0（snt_buzz）：今日收盘前30分钟数据，捕获收盘到今日结束——更难执行

优化建议：如果 Alpha 的信号高度依赖当日信息（如收益公告、新闻情绪），考虑转为 D0。但 D0 门槛更高（Sharpe >= 2.0 vs D1 的 1.25）。

---

## 提交门槛与检查项

官方 "Clear these tests before submitting an Alpha" 文档确认：

| 检查项 | D1 门槛 | D0 门槛 |
|--------|---------|---------|
| Sharpe | >= 1.25 | >= 2.0 |
| Fitness | >= 1.0 | >= 1.3 |
| Turnover | 1% < T < 70% | 1% < T < 70% |
| Weight test | 单只股票最大持仓 < 10% | 同左 |
| Self-Correlation | < 0.7 PnL correlation | 同左 |
| Sub-universe | 通过 | 通过 |
| IS-Ladder | 通过 | 通过 |

Self-correlation 基于四年滚动窗口计算。如果 Sharpe 比已有的相关 Alpha 高 10% 以上，Self-Correlation 检查也可以通过。

**CHN 区域门槛更高**：D1 Sharpe >= 2.08, D0 Sharpe >= 3.5。

### LOW_2Y_SHARPE（2年滚动Sharpe）
名称：`IS_LADDER_SHARPE`（在IS指标中）或 `LOW_2Y_SHARPE`（在检测列表中）
- 含义：衡量 alpha 在模拟期内**最近2年**的滚动 Sharpe 比率
- 门槛：与 D1/D0 门槛挂钩，受金字塔乘数影响
- 例如 D1 + 金字塔乘数 1.5 → LOW_2Y_SHARPE 门槛 ≈ 2.07
- 失败原因：信号在最近2年表现下滑（可能是过拟合或市况变化）
- 优化方法：加 decay、信号平滑（ts_mean）、或加 hump 降低近期信号噪声

### 官方公式
```
Sharpe = sqrt(252) * Mean(PnL) / Stdev(PnL)
Return = 年化PnL / (账面规模的一半)
Turnover = 美元交易金额 / 账面规模
Fitness = Sharpe * sqrt(abs(Returns) / max(Turnover, 0.125))
```

### Fitness 标签

| Label | D1 Fitness | D0 Fitness |
|-------|------------|------------|
| Spectacular | > 2.5 | > 3.25 |
| Excellent | > 2.0 | > 2.6 |
| Good | > 1.5 | > 1.95 |
| Average | > 1.0 | > 1.3 |
| Needs Improvement | <= 1.0 | <= 1.3 |

---

## PnL Realization Horizon（新指标，2026年推出）

官方 "Understanding PnL Realization Horizon" 文档定义：
- 定义：衡量 Alpha 持仓转化为已实现 PnL 的速度
- 短期成分：1-5天内实现回报，适合动量/新闻 Alpha
- 长期成分：10-20+天积累回报，适合基本面 Alpha
- HTVR 门槛：Turnover > 20% 且 PnL Realization Horizon < 20天（或 High TVR Returns > 总回报的 75%）

优化应用：
- 动量/新闻 Alpha：期望 Horizon < 10天，信号更新快，信息衰减快
- 基本面 Alpha：期望 Horizon 20-40天，价值需要时间实现
- 高换手 Alpha (HTVR)：期望 Horizon < 20天，换手成本需要快速实现来抵消
- 检查方法：提交前用 PnL Realization Horizon 验证 alpha 想法是否与 horizon 匹配
- 短 horizon 的 Alpha 天然与已有长 horizon Alpha 池低相关，提供更好的分散化

---

## Investability Constrained Metrics（流动性约束）

官方文档：
- 约束确保 Alpha 持仓在工具的流动性限制内
- 避免重大市场冲击影响盈利
- 高 Investability Constrained 表现的 Alpha 具有更高容量和流动性
- IS Summary 现在包含流动性约束后的聚合表现数据

---

## 高点换手 (HTVR) Alpha 指南

HTVR 定义：Turnover > 20%，信号在短持仓周期内仍然经济有效。

HTVR 的重要性：
- 分散化：与传统低换手信号低相关
- 信号新鲜度：更短持仓周期意味着更快信息消化
- 补充性：为已有组合提供正交回报来源

常见错误：直接追求高换手，而不是追求短生命周期信息源。高换手应该是想法的结果，而不是想法本身。

更好的 HTVR 工作流：
1. 从快速变化效应的直觉开始
2. 选择更新频率合适且有足够广度的字段
3. 建立清晰表达该效应的简单 alpha
4. 检查 alpha 是否自然落入高换手区间
5. 在真实市场条件、不同 universe 和成本意识变体下测试

HTVR 优化技巧（来自官方文档）：
- 优先使用变化量（delta）而非水平量（level）：deltas, surprises, accelerations
- 条件逻辑要谨慎：用流动性、关注度或事件状态做门控
- 信号更新速度必须证明频繁换仓的合理性
- 表现不应集中在少数日期或少数工具上

---

## 官方推荐算子分类框架

来自官方社群 "Stop Memorizing Operators. Learn Their Jobs." 文章，算子可按功能角色分类：

| 角色 | 示例算子 | 用途 |
|------|----------|------|
| Foundation | abs, add, multiply, divide, log | 基础运算，构建关系 |
| Cross-Sectional | rank, zscore, scale, normalize | 跨截面比较，消除市场效应 |
| Time-Series | ts_rank, ts_delta, ts_mean, ts_corr | 历史学习，趋势动量 |
| Signal Cleaning | winsorize, truncate, ts_backfill | 异常值处理，覆盖度提升 |
| Turnover Control | trade_when, hump, ts_target_tvr_decay | 降低换手，稳定持仓 |
| Group Intelligence | group_rank, group_neutralize, bucket | 行业内信号，中性化 |
| Vector | vec_avg, vec_count, vec_range | 向量数据集转标量 |
| Logical | if_else, and, or, is_nan | 条件逻辑，事件处理 |
| Distribution | densify, bucket, left_tail | 状态检测，极值分析 |
| Hidden Gems | regression_neut, ts_quantile, inst_tvr | 使用率低但强大的算子 |

---

## 优质 Alpha 的特征

官方 "Simulate your first Alpha" 总结：
- 一致增长的累积 PnL
- 高年化回报、Sharpe Ratio、% Profitable Days、Profit per Dollar Traded
- 低 Drawdown 和 Turnover
- 累计 PnL 图没有大的波动/回撤
- Turnover 低（但不低于 1%）、% Drawdown < 10%、Sharpe > 2.0（D0）/ > 1.25（D1）

---

## 官方参考文档列表

通过 `cnhkmcp.get_documentation_page(id)` 可获取以下完整官方教程：

| doc_id | 标题 | 内容 |
|--------|------|------|
| about-brain-platform | Introduction to Alphas | 基础概念 |
| introduction-brain-expression-language | Introduction to BRAIN Expression Language | 表达式语法理解 |
| how-brain-platform-works | How BRAIN works | 后台执行流程 |
| 19-alpha-examples | Alpha Examples for Beginners | 入门示例参考 |
| sample-alpha-concepts | Alpha Examples for Bronze Users | 青铜示例 |
| example-expression-alphas | Alpha Examples for Silver Users | 白银示例 |
| simulation-settings | How to choose Simulation Settings | 设置选择 |
| alpha-submission | Clear these tests before submitting | 提交门槛 |
| parameters-simulation-results | Parameters in Simulation Results | 指标解释 |
| understanding-pnl-realization-horizon | PnL Realization Horizon | HTVR 新指标 |
| neut-cons | Neutralization | 中性化详解 |
| neut-users | Double Neutralization | 双重中性化 |
| getting-started-d0 | D0 | D0 Alpha 详解 |
| getting-started-investability-constrained-metrics | Investability Constrained Metrics | 流动性约束 |
| fast-d1-documentation | Fast D1 | Fast D1 框架 |
| getting-started-high-turnover-alphas | High Turnover Alphas | HTVR 指南 |
| list-must-read-posts-how-improve-your-alphas-are-submitted | Must-read posts | 社群精华 |
| intermediate-pack-part-1 | Understand Results [1/2] | 结果解释 |
| intermediate-pack-part-2 | Improve your Alpha [2/2] | 改进技巧 |
| running-your-first-alpha | Simulate your first Alpha | 创建 Alpha |
| read-first-starter-pack | *Read this First* - Starter Pack | 入门基础 |

---

## 社群推荐阅读

官方 "Must-read posts: How to improve your Alphas" 汇总的 7 篇关键社群文章：
1. How to get a higher Sharpe
2. 5 ways to potentially increase returns
3. How to reduce correlation
4. Using trade_when for Event Alphas
5. How to smooth PnL curve
6. Neutralization intuition
7. How to avoid overfitting

---

## 文档阅读与维护规则

每次通过 `cnhkmcp.get_documentation_page(id)` 阅读官方文档前：
1. 先检查 `references/read-docs-index.md` 是否已阅读过该文档
2. 如果 doc_id 已存在且 lastModified 未更新，跳过
3. 如果文档 lastModified 日期晚于记录，需要重新阅读
4. 阅读后同步更新此文件 (`platform-knowledge.md`) 和 `read-docs-index.md`

如果阅读后产生了新的知识点，追加对应主题段落；如果现有知识有修正，更新对应段落并注明原因。
