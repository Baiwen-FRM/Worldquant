---
name: wq-alpha-idea-developer
description: 从多种渠道提取Alpha灵感并转化为可执行的BRAIN Alpha表达式（Fast Expression或Python）。优化：字段选择走平台真实数据（get_datafields），产出格式让用户选，FE走批量回测、Python走逐条回测。
---

# Alpha Idea Developer

## 概述

将Alpha灵感/想法转化为可执行的BRAIN Alpha表达式，并附带合理的settings。支持两种输出格式：Fast Expression 和 Python Alpha。

## 入口流程：询问Alpha来源

当用户调用此技能时，首先让用户选择Alpha灵感的来源：

> 请选择Alpha灵感的来源：
>
> **1. BRAIN平台文章** — 从BRAIN平台的Alpha灵感栏目或顾问中文论坛精品文章中提取思路
> **2. 手动提供** — 你提供网页链接、文件、或文字描述的Alpha想法
> **3. 平台已有Alpha** — 基于BRAIN平台上已有的Alpha进行衍生
> **4. 随机探索** — 选择特殊数据集/字段，组合运算符和settings，观察信号是否明显

用户选择后，按照对应的工作流执行。

### 通用小贴士

- **用平台真实字段，别靠静态表**：从想法落到字段时，先用 `get_datafields(search=...)` 去 BRAIN 平台搜真实字段名，查看 `id`（字段名）、`description`（含义）、`dataset`（所属数据集）。平台字段名通常带前缀（如 `fnd44_cashflow_accruals`、`earnings_yield_close`），跟静态参考资料里的缩写不一样。
- **变体数量规则**：同一个经济含义的信号，搜索出来的字段可能很多。按以下规则选变体：
  * 字段数 > 20：取 20%（向上取整），最多不超过 20 个变体
  * 字段数 ≤ 20：全部选用
  * 每个变体用不同的字段 + 相同的核心运算，批量回测对比哪个字段信号最强
- **回测前问用户要格式**：表达式设计好之后，问用户要 Fast Expression 还是 Python Alpha。
  * Fast Expression → `create_multi_simulation` 批量跑（一次 2-8 个，分多批跑完）
  * Python Alpha → 逐个 `create_simulation` 单跑
- **从想法到表达式的关键**：想法的核心是"用什么样的数据，做什么样的运算，预测什么方向的收益"。抓住这三个要素即可。
- **先写Fast Expression原型**：Fast Expression语法简洁，能快速验证思路。验证有效后再转Python Alpha。
- **Settings的起点**：region=USA, universe=TOP3000, delay=1, decay=5, neutralization=INDUSTRY, truncation=0.08 是常见的起点。根据信号性质调整（高换手信号加decay，截面信号加neutralization）。
- **关联技能**：转换Python Alpha用 `wq-alpha-converter`；优化迭代用 `wq-alpha-optimizer`。

---

## 来源1：BRAIN平台文章

从BRAIN平台获取Alpha灵感文章或顾问论坛精品帖，提取其中的交易思路。

### 获取文章内容

使用 `cnhkmcp` 工具：

```python
import asyncio, cnhkmcp
async def fetch_articles():
    await cnhkmcp.authenticate()
    inspiration = await cnhkmcp.get_documentation_page("alpha-inspiration")
    return inspiration
```

### 提取信号思路

阅读文章内容，提取：

1. **核心逻辑** — 文章在说什么样的交易信号？
2. **数据需求** — 需要哪些字段？
3. **运算方式** — 是截面比较还是时间序列？
4. **持有期** — 信号多久更新一次？

### 搜索真实字段

根据数据需求，用 `get_datafields(search=...)` 在平台搜真实字段：

```python
async def search_fields(keyword):
    await cnhkmcp.authenticate()
    result = await cnhkmcp.get_datafields(search=keyword)
    return result["results"]  # 每个元素含 id, description, dataset
```

取出所有相关字段后，按**变体数量规则**决定用哪些：
- 字段 > 20 → 取 20%（向上取整），最多 20 个
- 字段 ≤ 20 → 全部用

### 设计变体 & 问输出格式

基于筛选出的字段 + 核心运算（同一运算逻辑），生成变体列表。然后问用户：

> 表达式设计好了，共 N 个变体。你选 Fast Expression 还是 Python Alpha？

#### 选 Fast Expression：批量回测（推荐）

如果变体 ≤ 8 个，一次跑完。如果 > 8 个，分批跑（每批 8 个）：

```python
async def batch_test(all_exprs):
    await cnhkmcp.authenticate()
    all_results = []
    # 分批，每批最多 8 个
    for i in range(0, len(all_exprs), 8):
        batch = all_exprs[i:i+8]
        result = await cnhkmcp.create_multi_simulation(
            alpha_expressions=batch,
            instrument_type="EQUITY", region="USA", universe="TOP3000",
            delay=1, decay=5.0, neutralization="INDUSTRY", truncation=0.08,
            pasteurization="ON", language="FASTEXPR",
        )
        all_results.append(result)
    return all_results
```

出错时用 `get_simulation_status(sim_id)` 查错误信息。

#### 选 Python Alpha：逐条回测

```python
async def single_test():
    await cnhkmcp.authenticate()
    for code in python_codes:
        result = await cnhkmcp.create_simulation(
            type="REGULAR",
            instrument_type="EQUITY", region="USA", universe="TOP3000",
            delay=1, decay=5.0, neutralization="INDUSTRY", truncation=0.08,
            pasteurization="ON", language="PYTHON",
            regular=code,
        )
        # 逐个查看结果
```

注意 `language="PYTHON"`，`regular` 传 Python 代码。

### 结果解读：输出结果表格

回测完成后，先列出每个变体的 **Alpha Idea → 策略说明**，再展示结果表格：

```
`2rLV2pLN` — Alpha Idea: 经营现金流/总资产越高，越能预测正收益 → 策略: 做多 operating_cashflow_to_assets_4
`gJMN089K` — Alpha Idea: 现金流和盈利收益率都是定价信号 → 策略: 逆现金流应计 + rank(盈利收益率)
`88QWJYzz` — Alpha Idea: CFO/总资产是论文最核心指标 → 策略: 做多 operating_cash_flow_to_assets_2
`JjOaz1pe` — Alpha Idea: 用应计项调整盈利收益率 ≈ 现金流收益率 → 策略: rank(ey) - rank(cf_accruals)
`QPVRoGVp` — Alpha Idea: FCF越高的公司价值越大 → 策略: 做多 free_cash_flow_to_equity
`LL1ozrpe` — Alpha Idea: 现金流强于利润，低应计=好公司 → 策略: 做空 fnd44_cashflow_accruals
`d50JPZxY` — Alpha Idea: 应计占总资产百分比越低越好 → 策略: 做空 fnd44_perc_accruals
`0mEZapEv` — Alpha Idea: 营运资本应计越低现金流越好 → 策略: 做空 fnd44_working_capital_accruals
```

然后 **展示全部变体的对比表格**，按 Pass 数从多到少排序（Pass 越多越接近提交）：

| Alpha ID | Pass/n | Sharpe | Fitness | SubUniv | 2Y_Sharpe | Turnover | ConcWt | 倍数 |
|----------|-------|-------|--------|---------|----------|---------|------|-----|
| `2rLV2pLN` | **3/7**✅ | 1.58/0.51❌ | 1.0/0.34❌ | 0.22/0.26✅ | 1.58/0.77❌ | ✅5.9% | ❌ | 1.4× |
| `gJMN089K` | 3/6⚠️ | 1.58/-0.09❌ | 1.0/-0.02❌ | -0.04/-0.04✅ | -/- | ✅5.1% | ❌ | 1.1× |
| `88QWJYzz` | 2/7⚠️ | 1.58/-0.10❌ | 1.0/-0.03❌ | -0.04/-0.13❌ | 1.58/-0.48❌ | ✅12.8% | ❌ | 1.4× |
| `JjOaz1pe` | 2/6⚠️ | 1.58/-0.12❌ | 1.0/-0.03❌ | -0.05/-0.10❌ | -/- | ✅5.2% | ❌ | 1.1× |
| `QPVRoGVp` | 2/7⚠️ | 1.58/-0.20❌ | 1.0/-0.07❌ | -0.09/-0.33❌ | 1.58/0.41❌ | ✅16.7% | ❌ | 1.4× |
| `LL1ozrpe` | 2/7⚠️ | 1.58/-0.26❌ | 1.0/-0.06❌ | -0.11/-0.46❌ | 1.58/-0.96❌ | ✅5.0% | ❌ | 1.1× |
| `d50JPZxY` | 2/7⚠️ | 1.58/-0.30❌ | 1.0/-0.07❌ | -0.13/-0.55❌ | 1.58/-0.94❌ | ✅5.0% | ❌ | 1.1× |
| `0mEZapEv` | 2/7⚠️ | 1.58/-0.56❌ | 1.0/-0.19❌ | -0.24/-0.36❌ | 1.58/-1.06❌ | ✅5.2% | ❌ | 1.1× |

*每格格式：`标准/实际`，✅=通过/❌=未达标。按 Pass数降序 → Sharpe降序排序*

各列含义（对照 7 项关键提交检查）：
- **Pass/n** — 通过数/总分（满分 7 项：Sharpe、Fitness、SubUniv、2Y_Sharpe、LowTurnover、HiTurnover、ConcWt）
- **Sharpe** — LOW_SHARPE 检查：标准 / 实际 Sharpe
- **Fitness** — LOW_FITNESS 检查：标准 / 实际 Fitness
- **SubUniv** — LOW_SUB_UNIVERSE_SHARPE：标准 / 实际子行情 Sharpe
- **2Y_Sharpe** — LOW_2Y_SHARPE：2 年滚动 Sharpe（标准 1.58）
- **Turnover** — LOW/HIGH_TURNOVER：需在 1%~70%
- **ConcWt** — CONCENTRATED_WEIGHT：持仓集中度检查
- **倍数** — pyramid multiplier（越高越好）

如果全部变体 Sharpe 都负 → 尝试翻转表达式（加 `-`）。

---

## 来源2：手动提供

用户提供了文字描述、网页链接、或文件中的Alpha想法。

### 处理流程

1. **理解描述** — 仔细阅读，提炼核心信号逻辑
2. **结构化提问** — 如果不清晰，追问数据、运算、方向、持有期
3. **对照BRAIN字段** — 用 `get_datafields(search=...)` 搜索平台真实字段（看 `id` 和 `description`）
4. **按变体数量规则筛选字段** — 字段数 > 20 取 20%（最多 20 个），≤ 20 全选
5. **生成表达式变体** — 用同一运算 + 不同字段
6. **问输出格式** — 选 Fast Expression 还是 Python Alpha
7. **回测验证** — FE 走批量，Python 走逐条

### 映射示例

| 用户描述 | BRAIN平台实际字段 |
|---------|-----------------|
| "过去5天平均成交量" | `ts_mean(adv20, 5)`（`adv20` 是真实字段） |
| "市盈率的倒数" | `earnings_yield_close`（model227） |
| "市值排序" | `rank(mkt_cap)` |
| "现金流应计" | `fnd44_cashflow_accruals`（fundamental44） |
| "现金流收益率近似" | `rank(earnings_yield_close) - rank(fnd44_cashflow_accruals)` |
| "CFO/总资产" | `operating_cash_flow_to_assets_2`（model219） |
| "连涨3天后的回调" | `trade_when(ts_sum(returns > 0, 3) == 3, -rank(returns), 0)` |

**关键**：每次先 `get_datafields(search=...)` 确认字段名，不要硬编码。

---

## 来源3：平台已有Alpha

基于已有的Alpha进行衍生和改造。

### 获取Alpha

```python
async def fetch_alpha(alpha_id):
    await cnhkmcp.authenticate()
    alpha = await cnhkmcp.get_alpha_details(alpha_id)
    return alpha
```

### 衍生思路 & 字段确认

| 策略 | 做法 | 示例 |
|------|------|------|
| 换数据 | 先 `get_datafields(search=...)` 找替代字段，按变体数量规则筛选 | `fnd44_cashflow_accruals` → 同数据集其他字段 |
| 变窗口 | 改变周期 | `ts_mean(x, 20)` → `ts_mean(x, 60)` |
| 加条件 | 加trade_when过滤 | 增加条件过滤极端值 |
| 换组合 | 改变组合方式 | `+` 变 `*`，调整权重 |
| 翻转 | 做反向信号 | `rank(x)` → `-rank(x)` |

衍生出变体后，**问用户输出格式**，然后按格式走回测。

---

## 来源4：随机探索

组合特殊数据集/字段和运算符，生成 Alpha 变体并观察信号。

### 获取字段和运算符

```python
async def fetch_fields_and_ops():
    await cnhkmcp.authenticate()
    fields = await cnhkmcp.get_datafields(data_type="VECTOR")
    operators = await cnhkmcp.get_operators()
    return fields, operators
```

### 组合策略

**A. 数据集聚焦法** — 选一个特殊数据集，取全部或 20% 字段组合表达式
**B. 运算符组合法** — 选1个字段+2-3个运算符，组合变体
**C. 批量测试** — 8个一组用 `create_multi_simulation` 测试
**D. 信号筛选** — Sharpe > 0.5, Fitness > 0.3, Turnover < 200%

### 推荐探索的数据集

- `short_interest`（空头兴趣）
- `options_metrics`（期权指标）
- `credit_metrics`（信用指标）
- `insider_trading`（内部交易）
- `analyst_estimates`（分析师预期）
- `sentiment`（情绪数据）
- `esg_scores`（ESG评分）
- `fund_holdings`（基金持仓）
- `fiscal_metrics`（财务指标）
- `macro_indicators`（宏观指标）

同前：设计好变体后（按变体数量规则），**问输出格式**，再走回测。

---

## 输出与交付

最终交付用户的内容包括：

1. **表达式** — Fast Expression 或 Python Alpha 代码
2. **Settings** — 推荐的settings及理由
3. **模拟结果表格** — 按 Pass 数从高到低排序的表格，包含 Alpha ID、Pass/n、Sharpe、Fitness、SubUniv、2Y_Sharpe、Turnover、ConcWt、倍数，每格格式为`标准值/实际值`
4. **优化建议** — 后续优化方向（关联 `wq-alpha-optimizer`）

---

## 动态字段搜索（替代静态参考）

每次设计 Alpha 时，**不要**依赖静态表格中的字段缩写名。用 `get_datafields(search=...)` 去平台搜，以平台返回的 `id` 为准。

## 关联技能

- `wq-alpha-converter` — Fast Expression 转 Python Alpha
- `wq-alpha-optimizer` — Alpha 优化迭代与提交流程
- `cnhkmcp` — BRAIN平台API工具
