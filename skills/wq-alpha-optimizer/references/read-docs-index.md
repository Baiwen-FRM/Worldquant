# Documentation Read Index

追踪已阅读的 BRAIN 官方文档文章，避免重复抓取和保持知识同步。此为共享的唯一 truth，两个 skill（wq-alpha-converter, wq-alpha-optimizer）共用。

## 格式

每条记录包含：文档 ID、标题、阅读日期、提取的关键知识点、对应 platform-knowledge.md 章节。

---

## 已读文档

### 2026-07-15

doc_id | title | 提取内容 | 对应文件章节
about-brain-platform | Introduction to Alphas | Alpha 定义、生命周期 | platform-knowledge.md > 官方文档核心知识
introduction-brain-expression-language | Introduction to BRAIN Expression Language | Fast Expression 语言定义 | platform-knowledge.md > 官方文档核心知识
how-brain-platform-works | How BRAIN works | 后台七步流程、持仓构建细节 | platform-knowledge.md > Alpha 七步执行流程
19-alpha-examples | Alpha Examples for Beginners | 入门示例 | 参考基础
sample-alpha-concepts | Alpha Examples for Bronze Users | 青铜示例 | 参考基础
example-expression-alphas | Alpha Examples for Silver Users | 白银示例 | 参考基础
simulation-settings | How to choose Simulation Settings | 设置选择 | submission-thresholds.md
alpha-submission | Clear these tests before submitting | 提交门槛：D1 Sharpe>=1.25, D0>=2.0, Turnover 1%-70%, Self-Corr<0.7 | submission-thresholds.md > 官方文档确认的门槛
parameters-simulation-results | Parameters in Simulation Results | Fitness 标签表、Sharpe 公式 | platform-knowledge.md > 重要修正
understanding-pnl-realization-horizon | Understanding PnL Realization Horizon | PnL 实现周期、HTVR 门槛 | platform-knowledge.md > PnL 新指标 + optimization-strategies.md > HTVR/PH
neut-cons | Neutralization | 市场/行业/子行业中性化规则、group_neutralize 与设置等价 | platform-knowledge.md > 中性化深入指南
neut-users | Double Neutralization | 双重中性化 ASI/USA 示例 | platform-knowledge.md > 双重中性化 + optimization-strategies.md > DN
getting-started-d0 | D0 | D0 定义、隔夜回报、交易PnL vs 持仓PnL | platform-knowledge.md > D0 对比 + optimization-strategies.md > D0
getting-started-investability-constrained-metrics | Investability Constrained Metrics | 流动性约束 | platform-knowledge.md > Investability
fast-d1-documentation | Fast D1 | Fast D1 框架、_fast_d1 字段 | platform-knowledge.md > Fast D1 + optimization-strategies.md > FD1
getting-started-high-turnover-alphas | Getting Started with High Turnover Alphas | HTVR 定义、优化工作流、质量检查 | platform-knowledge.md > HTVR + optimization-strategies.md > HTVR
list-must-read-posts-how-improve-your-alphas-are-submitted | Must-read posts: How to improve | 7 篇社群精华文章 | platform-knowledge.md > 社群推荐阅读
intermediate-pack-part-1 | Intermediate Pack - Understand Results [1/2] | 结果解释、公式 | 公式参考
intermediate-pack-part-2 | Intermediate Pack - Improve your Alpha [2/2] | 算子用法 | 算子参考
running-your-first-alpha | Simulate your first Alpha | 首个 Alpha 创建、好 Alpha 特征 | platform-knowledge.md > 优质 Alpha 特征
read-first-starter-pack | *Read this First* - Starter Pack | 入门基础 | 基础参考

## 维护规则

1. 新增阅读：每次通过 cnhkmcp.get_documentation_page(id) 阅读新文档后，在此追加记录
2. 重复检查：阅读前先查此表，如果 doc_id 已存在且内容未过期，跳过
3. 内容过期：如果文档 lastModified 日期晚于本表的阅读日期，需要重新阅读
4. 关联更新：如果阅读后更新了 platform-knowledge.md 或 references 文件，记录更新文件路径
