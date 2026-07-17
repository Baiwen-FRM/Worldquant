# BRAIN 回测完全参考手册

> 唯一参考文档。新增发现随时补充。

---

## 一、三种回测模式

| 模式 | 定义 | 命令 |
|------|------|------|
| **Single** | 1 个表达式 + 1 组 settings | `brain.py simulation single fe "expr"`<br>`brain.py simulation single py alpha.py` |
| **Multi** | N 个表达式（2-8）+ 同 1 组 settings<br>走 `create_multi_simulation` API，并行快 | `brain.py simulation multi "e1" "e2"` |
| **Mass** | N 个表达式 × M 组 settings<br>自动拆分组 → 并行 Multi-Sim → 总对比表 | `brain.py simulation mass config.json` |

> Python Alpha **不支持** Multi/Mass（BRAIN 限制），只能走 Single。

---

## 二、Settings 速查

### 全部字段

| 字段 | Python | FE | 说明 |
|------|:---:|:---:|------|
| `instrumentType` | ✅ | ✅ | 默认 `EQUITY` |
| `region` | ✅ | ✅ | 市场区域 |
| `universe` | ✅ | ✅ | 股票池 |
| `delay` | ✅ | ✅ | 信号延迟，默认 1 |
| `decay` | ✅ | ✅ | 衰减系数 |
| `neutralization` | ✅ | ✅ | 中性化方式 |
| `truncation` | ✅ | ✅ | 截断比例 |
| `pasteurization` | ✅ | ✅ | `ON` / `OFF` |
| `maxTrade` | ✅ | ✅ | **刚补上的遗漏字段**，默认 `OFF` |
| `lookback` | ✅必填 | ❌ | Python Alpha 必需，推荐 `252` |
| `unitHandling` | ❌ | ✅ | FE 可用 |
| `nanHandling` | ❌ | ✅ | FE 可用 |
| `testPeriod` | ❌ | ✅ | FE 可用 |

### 默认设置

```python
# Python Alpha（绝对不能加 unitHandling/nanHandling/testPeriod，送了就 400）
settings = {
    "instrumentType": "EQUITY", "region": "USA", "universe": "TOP3000",
    "delay": 1, "decay": 5.0, "neutralization": "INDUSTRY",
    "truncation": 0.08, "pasteurization": "ON", "maxTrade": "OFF",
    "language": "PYTHON", "visualization": True,
    "lookback": 252,
}

# FE
fe_settings = {
    "instrumentType": "EQUITY", "region": "USA", "universe": "TOP3000",
    "delay": 1, "decay": 5.0, "neutralization": "INDUSTRY",
    "truncation": 0.08, "pasteurization": "ON", "maxTrade": "OFF",
    "unitHandling": "VERIFY", "nanHandling": "OFF", "testPeriod": "P0Y0M",
    "language": "FASTEXPR", "visualization": False,
}
```

> `visualization=True` 会生成图表，批量回测时建议关了加速。

### Region × Universe

| Region | Universe |
|--------|---------|
| USA | TOP3000, TOP2000, TOP1000, TOP500, TOP200, ILLIQUID_MINVOL1M, TOPSP500 |
| EUR | TOP2500, TOP1200, TOP800, TOP400, ILLIQUID_MINVOL1M, TOPCS1600 |
| GLB | TOP3000, MINVOL1M, MINVOL10M, TOPDIV3000 |
| ASI | MINVOL1M, MINVOL10M, ILLIQUID_MINVOL1M, TOP500 |
| CHN | TOP2000U |
| JPN | TOP1600, TOP1200 |
| IND | TOP500 |
| MEA | TOP400, TOP300 |

---

## 三、已知坑点（13 条）

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| P1 | Python 送 unitHandling 等字段 → 400 | `create_simulation()` 硬编码了 FE 才有的字段 | 手动 `brain_client.session.post()` 构造 payload |
| P2 | Python Alpha 报 "lookback required" | 少发了 `lookback` 字段 | 加 `"lookback": 252` |
| P3 | 轮询永远卡在 35%，但 Alpha 已生成 | 平台状态接口不同步 | 三路兜底：① 检查 `alpha` 字段 ② progress 卡 1 分钟查列表 ③ 10 分钟终兜底 |
| P4 | SUBINDUSTRY+decay=10 卡死在 35% | 未知（组合参数或平台偶发） | 放弃该组合，换参数再试 |
| P5 | `create_simulation()` 轮询 KeyError 崩溃 | 源码直接 `data["alpha"]`，但进度中无此键 | 不用该函数，用自定义轮询 |
| P6 | 字段跨 region 报 "unknown variable" | 字段是 region 相关的 | 换 region 前用 `get_datafields(search=..., region=XXX)` 重新搜 |
| P7 | Multi-Sim 报超出限制 | API 限制 2-8 个表达式 | 分批，每批 ≤8 个 |
| P8 | Multi-Sim settings 全部共享 | 设计如此 | 不同 settings 要分别调用 |
| P9 | Multi-Sim 返回解析总写错路径 | 指标在 `details.is` 里 | 路径: `result.alpha_results[i].details.is.sharpe` |
| P10 | FE 单条轮询没 Retry-After 时直接退出 | 早期逻辑的 bug | 没有 Retry-After 时等 5 秒继续 |
| P11 | `maxTrade` 字段遗漏 | 脚本默认设置没包含 | 已加 `"maxTrade": "OFF"` |
| P12 | Python 3.11- 的 f-string 反斜杠报错 | `f"├{'─'*10}┤"` 在 3.12 以下不合法 | Unicode 符号赋值给变量引用 |
| P13 | 批量回测时 visualization=True 拖慢 | 每次生成图表 | 批量时 `--settings visualization=False` |

---

## 四、脚本工具一览

| 命令 | 用途 | 关键特性 |
|------|------|---------|
| `brain.py simulation single fe` | FE 单条回测 | 进度条、对比表、JSON 保存 |
| `brain.py simulation single py` | Python Alpha 回测 | 批量、进度条、对比表、JSON 保存 |
| `brain.py simulation multi` | FE Multi 并行回测 | 2-8 个表达式一次提交 |
| `brain.py simulation mass` | Mass 多维扫荡 | 配置文件驱动、自动分组并行、总表 |
| `brain.py compare` | 结果对比 | 多文件、过滤、排名、分组、导出 |

```bash
# Single FE
python3 brain.py simulation single fe "ts_rank(rank(returns),5)"

# Single Python
python3 brain.py simulation single py alpha.py --output r.json

# Multi
python3 brain.py simulation multi "e1" "e2"

# Mass
python3 brain.py simulation mass config.json

# 对比
python3 brain.py compare results.json --min-sharpe 1.0
```

---

## 五、工作流

```
确认信号 → 字段扫荡 → 参数扫荡 → Region 拓展 → Python Alpha
```

**字段扫荡（Mass）：** 固定一个 region，换不同字段。Multi-Sim 一组 8 个。

**参数扫荡（Mass）：** 固定最佳字段，换 decay/窗口/中性化。

**Region 拓展（Mass）：** 换 region 时必须换字段（同经济含义但字段名不同）。
先用 `get_datafields(search="营收", region=EUR)` 搜等效字段，再配置到 `field_regions`。

**转 Python Alpha：** 最佳组合写 Python，验证提交级结果。

---

## 六、提交阈值参考

| 指标 | 阈值 | 2026-07-17 实测（alpha_revenue_overreaction） |
|------|------|:---:|
| Sharpe | ≥ 1.58 | 1.05 ❌ |
| Fitness | ≥ 1.0 | 0.55 ❌ |
| Turnover | 1%-70% | 37% ✅ |
| SubUniv Sharpe | ≥ 0.45 | 0.82 ✅ |
| IS Ladder 2Y | ≥ 1.58 | 1.21 ❌ |

**结论：** 信号方向正确但不够强，需优化。

### 字段表现排名（USA, 营收预期策略）

| 字段 | Sharpe |
|------|:------:|
| `max_estimate_revenue_longterm` | **1.33** |
| `mdl26_revenue` | 0.99 |
| `anl4_..._sales_mean` | 0.91 |
| `sales_estimate_median_value` | 0.88 |
| `pv87_qtr_matrix_revenue_estimate_mean` | 0.86 |
| `anl4_..._sales_high` | 0.87 |
| `anl4_..._sales_low` | 0.83 |

---

> 最后更新: 2026-07-17
