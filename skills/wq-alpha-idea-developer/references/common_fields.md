# 常用BRAIN字段参考

## 价格与回报
| 字段名 | 说明 |
|-------|------|
| `close` | 调整后收盘价 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `volume` | 成交量 |
| `returns` | 日收益率 |
| `vwap` | 成交量加权平均价 |

## 成交量与流动性
| 字段名 | 说明 |
|-------|------|
| `adv20` | 20日平均成交额 |
| `adv90` | 90日平均成交额 |
| `turnover` | 换手率 |
| `dollar_volume` | 成交金额 |

## 估值
| 字段名 | 说明 |
|-------|------|
| `bm` | 账面市值比 |
| `pb` | 市净率 |
| `pe_ratio` | 市盈率 |
| `earnings_yield` | 盈利收益率（EPS/Price） |
| `dividend_yield` | 股息率 |
| `mkt_cap` | 市值 |
| `capital` | 总市值 |

## 财务指标
| 字段名 | 说明 |
|-------|------|
| `gpoa` | 毛利率/总资产（Novy-Marx） |
| `roe` | 净资产收益率 |
| `roa` | 总资产收益率 |
| `accruals` | 应计项目 |
| `inv_1y` | 1年投资增长率 |
| `asset_growth` | 资产增长率 |
| `lev` | 杠杆率 |

## 技术/情绪
| 字段名 | 说明 |
|-------|------|
| `ivol_252d` | 252日特质波动率 |
| `beta_252d` | 252日Beta |
| `max_ret_252d` | 252日最大日收益 |
| `min_ret_252d` | 252日最小日收益 |
| `short_interest_ratio` | 空头比例 |
| `short_interest_change` | 空头变化 |
| `snt_buzz` | 社交媒体热度 |
| `snt_sentiment` | 情绪分数 |

## 行业/板块
| 字段名 | 说明 |
|-------|------|
| `sector` | 行业分类 |
| `subindustry` | 子行业分类 |
| `group` | 分组标签 |

## 特殊数据集
| 字段名前缀 | 数据集说明 |
|-----------|-----------|
| `options_*` | 期权指标 |
| `credit_*` | 信用指标 |
| `insider_*` | 内部交易 |
| `analyst_*` | 分析师预期 |
| `esg_*` | ESG评分 |
| `fund_*` | 基金持仓 |
| `fiscal_*` | 财务指标 |
| `macro_*` | 宏观指标 |
