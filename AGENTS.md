# 交流习惯
- 始终用中文跟我交流，包括解释、说明和提问。

# 欢迎菜单
每次启动新对话时，先展示以下选项让用户选择：

请选择你要做的事：

1. 💡 Alpha 灵感发现 → 用 wq-alpha-idea-developer 生成 Alpha 灵感，可回测
2. 🔄 Alpha 转换 → 用 wq-alpha-converter 将 FE 转成 Python Alpha
3. 🚀 Alpha 回测/优化 → 用 brain.py 跑回测，或用 wq-alpha-optimizer 优化已有 Alpha
4. 🔌 CNHK MCP 工具 → 使用 CNHK 相关 MCP 工具查数据/操作
5. ❓ 其他需求 → 自由对话，不做预设

根据用户选择，激活对应的 skill 或 toolset。

# 干活习惯
- 每次改完代码，用一两句中文告诉我你改了什么、为什么这么改。
- 创建 WorldQuant 相关的 skill 时，确保 agents/openai.yaml 里的 display_name 以 "Wq" 开头（如 "Wq Alpha Idea Developer"），使其在技能列表中显示为 Wq 开头。
- 改工具链结构、新增脚本、重命名文件、删文件时，**同步更新本文档**（AGENTS.md），确保欢迎菜单、工具链说明与实际情况一致。

# 代码习惯
- 代码里的注释用中文写。

# 回测工具链（自定义脚本）
项目里有自己写的回测工具，位于 `scripts/` 目录，通过 `brain.py` 统一调用：

```
# Single FE：单条 FE 回测，--from-file 批量 + --concurrent N 并发（最大 6）
回测:       python3 brain.py simulation single fe <表达式>
            python3 brain.py simulation single fe --from-file <文件> --concurrent 4

# Single PY：Python Alpha 回测，支持多个文件 + --concurrent N 并发（最大 3）
            python3 brain.py simulation single py <alpha文件>
            python3 brain.py simulation single py a1.py a2.py --concurrent 3

# Multi：多条 FE 并行（同 region + 同 delay），一次 2-8 个
            python3 brain.py simulation multi <e1> <e2>...

# Mass：暴力扫荡（从 MASS_CONFIG 常量展开 600+ 参数组合，每批 8 个，6 批并发）
            python3 brain.py simulation mass <表达式> --region USA

# Mass JSON：读 JSON 配置展开 field × parameter 组合（每批 8 个，6 批并发）
            python3 brain.py simulation mass <配置.json>

结果对比:   python3 brain.py compare <结果.json>
参考手册:   references/backtest-reference.md（所有坑点、设置速查）
```

当用户要求回测某个 alpha 时，优先用 `python3 brain.py simulation single py <文件>` 来跑。
批量扫荡参数组合用 `python3 brain.py simulation mass <表达式> --region USA`。
 
 # 平台 Multi-Sim 已知事实（待优化参考）

> "Consultants can execute up to **8 simultaneous** Multi-Simulations. Each Multi-Simulation can contain up to **10 Alphas** that run sequentially, each with distinct operators, data fields, and settings. However, all must share the same **Region and Delay** setting."
中文翻译：

> 顾问最多可以同时执行 **8 个** Multi-Simulation。每个 Multi-Simulation 最多可以包含 **10 个** 按顺序运行的 Alpha，每个 Alpha 可以使用不同的 operator、数据字段和 settings。但同一 Multi-Simulation 内的所有 Alpha 必须共享相同的 **Region** 和 **Delay** 设置。

 已实现的优化：
- `mass` 和 `mass json` 采用 ThreadPoolExecutor(max_workers=6)，每批 8 个并发提交
- `single fe --concurrent`：最大并发 6 个
- `single py --concurrent`：最大并发 3 个（Python 编译更耗资源）

# 文件存放规范
- 新创建或转换的 Python Alpha 文件统一放到 `alpha_files/` 目录下，不要放在项目根目录
- 回测时用 `python3 brain.py simulation single py alpha_files/<文件>` 来跑
