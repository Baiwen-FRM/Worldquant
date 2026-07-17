#!/usr/bin/env python3
"""
BRAIN 回测引擎 — Single / Multi / Mass 统一入口

用 brain.py 调用:
    python3 brain.py simulation single fe <表达式> [选项]
    python3 brain.py simulation single py <文件> [选项]
    python3 brain.py simulation multi <e1..e8> [选项]
    python3 brain.py simulation mass <表达式> [选项]  （传 .json 走配置文件扫荡）

直接调用:
    python3 scripts/simulation.py single fe "ts_rank(rank(returns),5)"
    python3 scripts/simulation.py single py alpha.py
    python3 scripts/simulation.py multi "e1" "e2"
    python3 scripts/simulation.py mass config.json
"""

import argparse
import time
import json
import os
import sys


# ============================================================
# Unicode 表格符号
# ============================================================
BOX_H = "\u2500"
BOX_T = "\u251c"
BOX_RL = "\u2524"
BOX_BL = "\u2514"
BOX_BR = "\u2518"


# ============================================================
# 指标分组（三种模式共用）
# ============================================================
METRICS_CORE = [
    ("夏普比率", "sharpe", ".4f"),
    ("Fitness", "fitness", ".4f"),
    ("年化收益率", "returns", ".4f"),
    ("边际收益率", "margin", ".4f"),
    ("换手率", "turnover", ".4f"),
]
METRICS_RISK = [
    ("最大回撤", "drawdown", ".4f"),
    ("年化波动率", "standardDeviation", ".4f"),
    ("残差波动率", "stdResidual", ".4f"),
    ("回撤占比", "drawdownPct", ".4f"),
]
METRICS_INFOCoeff = [
    ("信息系数 (IC)", "ic", ".4f"),
    ("IC 均值", "icMean", ".4f"),
    ("IC 标准差", "icStd", ".4f"),
    ("IC 夏普", "icSharpe", ".4f"),
]
METRICS_SUBSET = [
    ("子集夏普", "subUniverseSharpe", ".4f"),
    ("低流动性2年夏普", "low2ySharpe", ".4f"),
]
METRICS_POSITIONS = [
    ("多头持仓数", "longCount", ".0f"),
    ("空头持仓数", "shortCount", ".0f"),
    ("个股集中度", "concentration", ".4f"),
]
ALL_METRIC_KEYS = [
    k for _, k, _ in (
        METRICS_CORE + METRICS_RISK + METRICS_INFOCoeff
        + METRICS_SUBSET + METRICS_POSITIONS
    )
]


# ============================================================
# 共享工具函数
# ============================================================

def print_metric_group(title, metrics, metric_defs):
    print(f"   [{title}]")
    for label, key, fmt in metric_defs:
        val = metrics.get(key)
        if val is None:
            print(f"     {label:16s}: N/A")
        elif isinstance(val, float):
            print(f"     {label:16s}: {val:{fmt}}")
        elif isinstance(val, int):
            print(f"     {label:16s}: {val}")
        else:
            print(f"     {label:16s}: {val}")


def print_results(alpha_id, metrics, label="", checks=None):
    prefix = f" [{label}] " if label else " "
    print(f"\n{prefix}\u7ed3\u679c (Alpha ID: {alpha_id})")
    print_metric_group("核心指标", metrics, METRICS_CORE)
    print_metric_group("风险指标", metrics, METRICS_RISK)
    print_metric_group("信息系数", metrics, METRICS_INFOCoeff)
    print_metric_group("子集回测", metrics, METRICS_SUBSET)
    print_metric_group("持仓信息", metrics, METRICS_POSITIONS)
    if checks:
        for c in checks:
            name = c.get("name", "?")
            result = c.get("result", "?")
            icon = "V" if result == "PASS" else "W" if result == "WARNING" else "X"
            detail = ""
            if "limit" in c and "value" in c:
                detail = f" (标准={c['limit']}, 实际={c['value']})"
            print(f"     {icon} {name}: {result}{detail}")
        for c in checks:
            if c.get("name") == "MATCHES_PYRAMID" and "pyramids" in c:
                mults = [f"{p['name']}: {p['multiplier']}x" for p in c["pyramids"]]
                print(f"\n   \u5d11\u5854\u500d\u6570: {', '.join(mults)}")



# ============================================================
# 暴力模式参数组合
# ============================================================
MASS_CONFIG = {
    "USA": {
        "universe":       ["TOP3000", "TOP1000", "TOP500", "TOP200", "ILLIQUID_MINVOL1M"],
        "decay":          [1, 3, 5, 10, 15, 20],
        "truncation":     [0.02, 0.04, 0.06, 0.08, 0.1],
        "neutralization": ["MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"],
    },
    "CHN": {
        "universe":       ["TOP3000", "TOP2000"],
        "decay":          [1, 3, 5, 10, 15, 20],
        "truncation":     [0.02, 0.04, 0.06, 0.08, 0.1],
        "neutralization": ["MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"],
    },
    "GLB": {
        "universe":       ["TOP3000", "MINVOL1M"],
        "decay":          [1, 3, 5, 10, 15, 20],
        "truncation":     [0.02, 0.04, 0.06, 0.08, 0.1],
        "neutralization": ["MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"],
    },
    "EUR": {
        "universe":       ["TOP1200", "TOP800", "TOP400", "ILLIQUID_MINVOL1M"],
        "decay":          [1, 3, 5, 10, 15, 20],
        "truncation":     [0.02, 0.04, 0.06, 0.08, 0.1],
        "neutralization": ["MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"],
    },
    "ASI": {
        "universe":       ["MINVOL1M", "ILLIQUID_MINVOL1M"],
        "decay":          [1, 3, 5, 10, 15, 20],
        "truncation":     [0.02, 0.04, 0.06, 0.08, 0.1],
        "neutralization": ["MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"],
    },
    "HKG": {
        "universe":       ["TOP800", "TOP500"],
        "decay":          [1, 3, 5, 10, 15, 20],
        "truncation":     [0.02, 0.04, 0.06, 0.08, 0.1],
        "neutralization": ["MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"],
    },
}

def build_result_dict(alpha_name, alpha_id, metrics):
    r = {"alpha_name": alpha_name, "alpha_id": alpha_id}
    for key in ALL_METRIC_KEYS:
        val = metrics.get(key)
        if val is not None:
            r[key] = val
    checks = metrics.get("checks", [])
    if checks:
        r["checks"] = [{"name": c["name"], "result": c["result"]} for c in checks]
        for c in checks:
            if c.get("name") == "MATCHES_PYRAMID" and "pyramids" in c:
                r["pyramids"] = [p for p in c["pyramids"]]
    return r


def print_comparison_table(results, title="\u5bf9\u6bd4\u8868"):
    if len(results) < 2:
        return
    keys = [
        ("名称", "alpha_name", None),
        ("夏普", "sharpe", ".4f"),
        ("Fitness", "fitness", ".4f"),
        ("年化收益", "returns", ".4f"),
        ("边际", "margin", ".4f"),
        ("换手率", "turnover", ".4f"),
        ("最大回撤", "drawdown", ".4f"),
        ("IC", "ic", ".4f"),
        ("子集夏普", "subUniverseSharpe", ".4f"),
    ]
    headers = [h for h, _, _ in keys]
    rows = []
    for r in results:
        row = []
        for h, key, fmt in keys:
            if key is None:
                val = r.get("alpha_name", "?")
                if len(val) > 24:
                    val = val[:21] + "..."
                row.append(val)
            else:
                v = r.get(key)
                if v is None:
                    row.append("N/A")
                elif isinstance(v, float):
                    row.append(f"{v:{fmt}}")
                else:
                    row.append(str(v))
        rows.append(row)
    col_widths = []
    for ci, h in enumerate(headers):
        cw = max(len(h), max((len(row[ci]) for row in rows), default=0)) + 2
        col_widths.append(cw)
    total_width = sum(col_widths) + len(col_widths) + 1

    def fmt_row(cells):
        return "\u2502 " + " \u2502 ".join(c.rjust(w) for c, w in zip(cells, col_widths)) + " \u2502"

    print(f"\n {'=' * total_width}")
    print(f" {title}")
    print(f" {'=' * total_width}")
    print(fmt_row(headers))
    print(BOX_T + BOX_H * (total_width - 2) + BOX_RL)
    for row in rows:
        print(fmt_row(row))
    print(BOX_BL + BOX_H * (total_width - 2) + BOX_BR)
    ranked = sorted(results, key=lambda r: r.get("sharpe", -999) or -999, reverse=True)
    print(f"\n \u590f\u666e\u6bd4\u7387\u6392\u540d")
    for i, r in enumerate(ranked, 1):
        s = r.get("sharpe", "N/A")
        s_str = f"{s:.4f}" if isinstance(s, float) else str(s)
        print(f"   {i}. {r['alpha_name']:30s} Sharpe = {s_str}")
    print()


def load_settings_overrides(raw_args):
    overrides = {}
    for item in raw_args:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        try:
            v = float(v) if "." in v else int(v)
        except ValueError:
            pass
        overrides[k] = v
    return overrides


class BatchProgress:
    """批量回测进度跟踪器"""
    def __init__(self, total):
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self.rows = []

    def start_item(self, name, idx):
        self.current_name = name
        self.current_idx = idx
        self.item_start = time.time()
        self.rows.append([name, "polling", "", 0.0])

    def update_polling(self, pct):
        if pct <= 0:
            return
        bar_width = 16
        filled = int(min(pct, 99) / 100 * bar_width)
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
        elapsed = int(time.time() - self.item_start)
        self.rows[-1][2] = f"{bar} {pct:3.0f}%  ({elapsed // 60}:{elapsed % 60:02d})"
        self.rows[-1][3] = pct
        self._render()

    def complete_item(self, name, sharpe=None):
        self.current += 1
        elapsed = int(time.time() - self.start_time)
        s = f"Sharpe={sharpe:.4f}" if sharpe is not None else "done"
        for row in self.rows:
            if row[0] == name and row[1] != "done":
                row[1] = "done"
                row[2] = f"{s}  ({elapsed // 60}:{elapsed % 60:02d})"
                break
        self._render()

    def fail_item(self, name, reason):
        for row in self.rows:
            if row[0] == name and row[1] != "done":
                row[1] = "fail"
                row[2] = f"X {reason}"
                break
        self._render()

    def _render(self):
        for row in self.rows:
            name, status, detail = row[0], row[1], row[2]
            idx = self.rows.index(row) + 1
            icon = "V" if status == "done" else ""
            print(f"  [{idx}/{self.total}] {name[:28]:28s} {icon} {detail}")


# ============================================================
# 认证（所有模式共用）
# ============================================================

def authenticate():
    """认证并返回 brain_client"""
    import asyncio
    import cnhkmcp
    loop = asyncio.new_event_loop()
    loop.run_until_complete(cnhkmcp.authenticate())
    from cnhkmcp.untracked.platform_functions import brain_client
    return brain_client, loop



# ============================================================
# 模式 1：Single FE（支持单发和并发）
# ============================================================

def run_single_fe(argv):
    """FE 单条/批量回测（支持 --concurrent 并发）"""
    parser = argparse.ArgumentParser(prog="brain.py simulation single fe")
    parser.add_argument("expressions", nargs="+")
    parser.add_argument("--region", default="USA")
    parser.add_argument("--universe", default="TOP3000")
    parser.add_argument("--neutralization", default="INDUSTRY")
    parser.add_argument("--decay", type=float, default=5.0)
    parser.add_argument("--truncation", type=float, default=0.08)
    parser.add_argument("--delay", type=int, default=1)
    parser.add_argument("--label", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--from-file", action="store_true")
    parser.add_argument("--concurrent", type=int, default=1, help="并发数（默认 1 单发，最大 6）")
    args = parser.parse_args(argv)

    # 提取表达式
    expr_list = []
    if args.from_file:
        for fpath in args.expressions:
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        expr_list.append(line)
    else:
        expr_list = args.expressions

    if not expr_list:
        print("X 未提供表达式")
        sys.exit(1)

    brain_client, loop = authenticate()
    settings = {
        "instrumentType": "EQUITY", "region": args.region,
        "universe": args.universe, "delay": args.delay,
        "decay": args.decay, "neutralization": args.neutralization,
        "truncation": args.truncation, "pasteurization": "ON",
        "unitHandling": "VERIFY", "nanHandling": "OFF",
        "testPeriod": "P0Y0M", "language": "FASTEXPR",
        "visualization": False, "maxTrade": "OFF",
    }

    results = []
    total = len(expr_list)

    if args.concurrent < 1 or args.concurrent > 6:
        args.concurrent = 6
    if args.concurrent > 1:
        # 并发模式：用 ThreadPoolExecutor 同时发 N 个 FE 单条回测
        # 每个 _poll_fe 独立 POST + 轮询，不互相等待
        from concurrent.futures import ThreadPoolExecutor, as_completed
        labels = []
        for expr in expr_list:
            lbl = args.label if args.label else expr[:57] + ("..." if len(expr) > 60 else "")
            labels.append(lbl)

        print(f"  共 {total} 条，并发 {args.concurrent} 个")
        with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
            futures = {}
            for i, expr in enumerate(expr_list):
                label = labels[i]
                futures[executor.submit(_poll_fe, brain_client, expr, label, settings)] = (i, label, expr)

            for future in as_completed(futures):
                i, label, expr = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"  X [{label}] 异常: {e}")
                print(f"  进度: {len(results)}/{total}")
    else:
        # 单发模式（原逻辑）
        progress = BatchProgress(total) if total > 1 else None
        for i, expr in enumerate(expr_list, 1):
            label = args.label if args.label else expr[:57] + ("..." if len(expr) > 60 else "")
            print(f"\n  [{i}/{total}] {label}", file=__import__('sys').stderr)
            result = _poll_fe(brain_client, expr, label, settings, progress=progress, idx=i)
            if result:
                results.append(result)

    if len(results) > 1:
        print_comparison_table(results)
    if args.output and results:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    loop.close()
    if not results:
        sys.exit(1)
    if not results:
        sys.exit(1)


def _poll_fe(brain_client, expr, label, settings, progress=None, idx=0, max_wait=600):
    payload = {"type": "REGULAR", "settings": settings, "regular": expr}
    if progress:
        progress.start_item(label, idx)
    try:
        resp = brain_client.session.post(
            f"{brain_client.base_url}/simulations", json=payload, timeout=60)
    except Exception as e:
        print(f"X [{label}] 网络失败: {e}")
        if progress: progress.fail_item(label, "网络失败")
        return None
    if resp.status_code != 201:
        print(f"X [{label}] 创建失败 (HTTP {resp.status_code})")
        if progress: progress.fail_item(label, f"HTTP {resp.status_code}")
        return None

    loc = resp.headers.get("Location", "")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            sim = brain_client.session.get(loc, timeout=60).json()
        except Exception as e:
            time.sleep(5)
            continue
        if sim.get("alpha"):
            aid = sim["alpha"]
            alpha = brain_client.session.get(
                f"{brain_client.base_url}/alphas/{aid}", timeout=60).json()
            metrics = alpha.get("is", {})
            r = build_result_dict(label, aid, metrics)
            print_results(aid, metrics, label)
            if progress: progress.complete_item(label, r.get("sharpe"))
            return r
        if progress:
            progress.update_polling(sim.get("progress", 0))
        retry = resp.headers.get("Retry-After", "5")
        time.sleep(int(float(retry)) if retry and retry != "0" else 5)

    print(f"X [{label}] 超时")
    if progress: progress.fail_item(label, "超时")
    return None


# ============================================================
# 模式 2：Single Python（支持单发和并发）
# ============================================================

def run_single_py(argv):
    """Python Alpha 回测（支持多个文件批量跑）"""
    parser = argparse.ArgumentParser(prog="brain.py simulation single py")
    parser.add_argument("alpha_files", nargs="+")
    parser.add_argument("--settings", nargs="*", default=[])
    parser.add_argument("--max-retries", type=int, default=120)
    parser.add_argument("--output", default="")
    parser.add_argument("--concurrent", type=int, default=1, help="并发数（默认 1 单发，最大 3）")
    args = parser.parse_args(argv)

    brain_client, loop = authenticate()
    settings = {
        "instrumentType": "EQUITY", "region": "USA", "universe": "TOP3000",
        "delay": 1, "decay": 5.0, "neutralization": "INDUSTRY",
        "truncation": 0.08, "pasteurization": "ON", "maxTrade": "OFF",
        "language": "PYTHON", "visualization": True, "lookback": 252,
    }
    overrides = load_settings_overrides(args.settings)
    if overrides:
        print(f"  \u8986\u76d6\u8bbe\u7f6e: {overrides}")
        settings.update(overrides)

    # 获取已有 Alpha 列表
    existing_ids = set()
    try:
        resp = brain_client.session.get(
            f"{brain_client.base_url}/users/self/alphas",
            params={"limit": 10, "order": "-dateCreated"}, timeout=30).json()
        for a in resp.get("results", []):
            existing_ids.add(a["id"])
    except Exception:
        pass

    total = len(args.alpha_files)
    results = []

    if args.concurrent < 1 or args.concurrent > 3:
        args.concurrent = 3
    if args.concurrent > 1:
        # 并发模式：用 ThreadPoolExecutor 同时发 N 个 Python Alpha 回测
        # 每个 _poll_py 独立 POST + 轮询
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print(f"  共 {total} 个文件，并发 {args.concurrent} 个")

        # 包装函数：每个线程独立读文件 + 调 _poll_py 回测
        # existing_ids 多个线程共用，用来check Alpha，线程不安全但不影响结果
        def _run_one_py(alpha_file):
            if not os.path.isfile(alpha_file):
                return None, f"文件不存在: {alpha_file}"
            with open(alpha_file) as f:
                code = f.read()
            name = os.path.splitext(os.path.basename(alpha_file))[0]
            result, err = _poll_py(brain_client, code, name, settings, existing_ids,
                                    args.max_retries)
            return result, err

        with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
            futures = {executor.submit(_run_one_py, f): f for f in args.alpha_files}
            for future in as_completed(futures):
                fname = futures[future]
                try:
                    result, err = future.result()
                    if err:
                        print(f"  X [{fname}] 失败: {err}")
                    elif result:
                        results.append(result)
                        s = result.get("sharpe", "?")
                        s_str = f"{s:.4f}" if isinstance(s, float) else str(s)
                        print(f"  V [{result.get('alpha_name','?')}] Sharpe={s_str}")
                except Exception as e:
                    print(f"  X [{fname}] 异常: {e}")
                print(f"  进度: {len(results)}/{total}")
    else:
        # 单发模式
        progress = BatchProgress(total) if total > 1 else None
        for alpha_file in args.alpha_files:
            if not os.path.isfile(alpha_file):
                print(f"W  文件不存在，跳过: {alpha_file}")
                continue
            with open(alpha_file) as f:
                code = f.read()
            name = os.path.splitext(os.path.basename(alpha_file))[0]
            print(f"\n  \u8bfb\u53d6: {alpha_file}")

            result, err = _poll_py(brain_client, code, name, settings, existing_ids,
                                    args.max_retries, progress=progress)
            if err:
                print(f"X [{name}] 失败: {err}")
                if progress: progress.fail_item(name, str(err)[:30])
                continue
            if result:
                results.append(result)


    if len(results) > 1:
        print_comparison_table(results)
    if args.output and results:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    loop.close()
    if not results:
        sys.exit(1)


def _poll_py(brain_client, code, name, settings, existing_ids, max_retries, progress=None):
    payload = {"type": "REGULAR", "settings": settings, "regular": code}
    try:
        resp = brain_client.session.post(
            f"{brain_client.base_url}/simulations", json=payload, timeout=60)
    except Exception as e:
        return None, e

    if resp.status_code != 201:
        return None, Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

    loc = resp.headers.get("Location", "")
    if progress:
        progress.start_item(name, len(progress.rows) + 1)

    # 轮询等结果——最多三招：先正常轮询，卡住就check最新 Alpha，超时后硬拉一次
    alpha_id = None
    last_progress, stuck_count = None, 0

    for _ in range(max_retries):
        try:
            sim = brain_client.session.get(loc, timeout=60).json()
        except Exception:
            time.sleep(5)
            continue

        if sim.get("alpha"):
            alpha_id = sim["alpha"]
            break

        pct = sim.get("progress", 0)
        if progress:
            progress.update_polling(pct)
        if last_progress is not None and pct == last_progress:
            stuck_count += 1
            if stuck_count >= 12:
                new_a = _get_latest_alpha(brain_client, existing_ids)
                if new_a:
                    alpha_id = new_a
                    break
                stuck_count = 0
        else:
            stuck_count = 0
        last_progress = pct

        retry = resp.headers.get("Retry-After")
        time.sleep(int(float(retry)) if retry and retry != "0" else 5)

    # 前两招都没拿到，再check最后一次
    if not alpha_id:
        alpha_id = _get_latest_alpha(brain_client, existing_ids)
    if not alpha_id:
        if progress: progress.fail_item(name, "超时")
        return None, Exception("未找到 Alpha")

    try:
        alpha = brain_client.session.get(
            f"{brain_client.base_url}/alphas/{alpha_id}", timeout=60).json()
        metrics = alpha.get("is", {})
    except Exception as e:
        return None, e

    r = build_result_dict(name, alpha_id, metrics)
    print_results(alpha_id, metrics)
    if progress: progress.complete_item(name, r.get("sharpe"))
    existing_ids.add(alpha_id)
    return r, None


def _get_latest_alpha(brain_client, exclude_ids):
    resp = brain_client.session.get(
        f"{brain_client.base_url}/users/self/alphas",
        params={"limit": 5, "order": "-dateCreated"}, timeout=30).json()
    for a in resp.get("results", []):
        if a["id"] not in exclude_ids:
            return a["id"]
    return None


# ============================================================
# 模式 3：Multi（FE 并行 2-8 个）
# ============================================================

def run_multi(argv):
    """走 create_multi_simulation API，2-8 个表达式并行回测"""
    parser = argparse.ArgumentParser(prog="brain.py simulation multi")
    parser.add_argument("expressions", nargs="+")
    parser.add_argument("--region", default="USA")
    parser.add_argument("--universe", default="TOP3000")
    parser.add_argument("--neutralization", default="INDUSTRY")
    parser.add_argument("--decay", type=float, default=5.0)
    parser.add_argument("--truncation", type=float, default=0.08)
    parser.add_argument("--delay", type=int, default=1)
    parser.add_argument("--output", default="")
    parser.add_argument("--from-file", action="store_true")
    args = parser.parse_args(argv)

    expr_list = []
    if args.from_file:
        for fpath in args.expressions:
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        expr_list.append(line)
    else:
        expr_list = args.expressions

    if len(expr_list) < 2:
        print("X Multi 模式至少需要 2 个表达式")
        sys.exit(1)
    if len(expr_list) > 8:
        print(f"W  最多 8 个，截取前 8 个（共 {len(expr_list)}）")
        expr_list = expr_list[:8]

    import asyncio
    import cnhkmcp
    loop = asyncio.new_event_loop()
    loop.run_until_complete(cnhkmcp.authenticate())

    print(f"\n === Multi: {len(expr_list)} 个表达式并行 ===")
    result = loop.run_until_complete(cnhkmcp.create_multi_simulation(
        alpha_expressions=expr_list,
        region=args.region, universe=args.universe,
        delay=args.delay, decay=args.decay,
        neutralization=args.neutralization,
        truncation=args.truncation,
    ))

    results = []
    if isinstance(result, dict) and result.get("error"):
        print(f"X 失败: {result['error']}")
    else:
        for i, ar in enumerate(result.get("alpha_results", [])):
            aid = ar.get("alpha_id")
            if not aid:
                continue
            details = ar.get("details", {})
            metrics = details.get("is", {})
            label = expr_list[i] if i < len(expr_list) else f"expr_{i+1}"
            r = build_result_dict(label, aid, metrics)
            print_results(aid, metrics, label)
            results.append(r)

    if len(results) > 1:
        print_comparison_table(results)
    if args.output and results:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    loop.close()
    if not results:
        sys.exit(1)


# ============================================================
# 模式 4：Mass（暴力扫荡）
# ============================================================

def run_mass(argv):
    """暴力模式：用 MASS_CONFIG 扫荡表达式"""
    parser = argparse.ArgumentParser(prog="brain.py simulation mass")
    parser.add_argument("expression", help="Alpha 表达式")
    parser.add_argument("--region", default="USA", choices=list(MASS_CONFIG.keys()),
                        help="市场区域（默认 USA）")
    parser.add_argument("--delay", type=int, default=1, help="数据延迟（默认 1）")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    config = MASS_CONFIG[args.region]

    # 笛卡尔积展开所有参数组合
    from itertools import product
    runs = []
    for decay, truncation, universe, neutralization in product(
            config["decay"], config["truncation"],
            config["universe"], config["neutralization"]):
        runs.append({
            "settings": {
                "instrumentType": "EQUITY",
                "region": args.region,
                "universe": universe,
                "delay": args.delay,
                "decay": decay,
                "neutralization": neutralization,
                "truncation": truncation,
                "pasteurization": "ON",
                "unitHandling": "VERIFY",
                "nanHandling": "OFF",
                "language": "FASTEXPR",
                "visualization": False,
            },
            "expression": args.expression,
            "label": "decay=%d,trunc=%.2f,uni=%s,neut=%s" % (
                decay, truncation, universe, neutralization),
        })

    total = len(runs)
    print("\n  === mass (%s) ===" % args.region)
    print("  展开: %d 个组合" % total)

    # 认证
    import asyncio
    import cnhkmcp
    loop = asyncio.new_event_loop()
    loop.run_until_complete(cnhkmcp.authenticate())
    from cnhkmcp.untracked.platform_functions import brain_client

    # === 并发提交 ===
    # 1. 按 8 个一组拆成 Multi-Sim batch
    # 2. ThreadPoolExecutor(6) 同时提交 6 批
    all_results = []
    batch_size = 8
    batches = []
    for batch_start in range(0, total, batch_size):
        batch = runs[batch_start:batch_start + batch_size]
        if len(batch) < 2:
            batch.append(runs[0])
            batch[-1]["label"] = "(占位)"
        batches.append(batch)

    total_batches = len(batches)
    print("  共 %d 批，每批 %d 个，最多同时跑 6 批" % (total_batches, batch_size))

    from concurrent.futures import ThreadPoolExecutor, as_completed
    batch_done = [False] * total_batches

    def _run_batch(batch_idx):
        batch = batches[batch_idx]
        labels = [r["label"] for r in batch]

        multisim_data = [{
            "type": "REGULAR",
            "settings": r["settings"],
            "regular": r["expression"],
        } for r in batch]

        import time as _time

        try:
            resp = brain_client.session.post(
                "%s/simulations" % brain_client.base_url,
                json=multisim_data, timeout=60)
        except Exception as e:
            return {"_error": "网络失败: %s" % e, "_batch_idx": batch_idx}

        if resp.status_code != 201:
            return {"_error": "HTTP %d" % resp.status_code, "_batch_idx": batch_idx}

        loc = resp.headers.get("Location", "")

        max_wait = 600
        start_t = _time.time()
        batch_alpha_ids = [None] * len(batch)

        while _time.time() - start_t < max_wait:
            try:
                multisim = brain_client.session.get(loc, timeout=60).json()
            except Exception:
                _time.sleep(5)
                continue

            children = multisim.get("children", [])
            for ci, child_url in enumerate(children):
                if ci >= len(batch_alpha_ids):
                    break
                try:
                    child_resp = brain_client.session.get(child_url, timeout=30).json()
                except Exception:
                    continue
                if child_resp.get("alpha"):
                    batch_alpha_ids[ci] = child_resp["alpha"]

            completed = sum(1 for a in batch_alpha_ids if a is not None)
            if completed == len(batch):
                break

            retry = resp.headers.get("Retry-After", "10")
            _time.sleep(int(float(retry)) if retry and retry != "0" else 10)

        results = []
        for ci, aid in enumerate(batch_alpha_ids):
            if not aid or labels[ci] == "(占位)":
                continue
            try:
                alpha = brain_client.session.get(
                    "%s/alphas/%s" % (brain_client.base_url, aid), timeout=60).json()
                metrics = alpha.get("is", {})
            except Exception:
                continue

            r = build_result_dict(labels[ci], aid, metrics)
            r["_region"] = args.region
            r["_decay"] = batch[ci]["settings"]["decay"]
            r["_neut"] = batch[ci]["settings"]["neutralization"]
            r["_uni"] = batch[ci]["settings"]["universe"]
            r["_trunc"] = batch[ci]["settings"]["truncation"]
            results.append(r)

        return {"_results": results, "_batch_idx": batch_idx}

    # 同时最多 6 个 Multi-Sim 在跑
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_run_batch, i): i for i in range(total_batches)}
        for future in as_completed(futures):
            bidx = futures[future]
            try:
                bd = future.result()
                if "_error" in bd:
                    print("  X 批 %d 失败: %s" % (bd["_batch_idx"] + 1, bd["_error"]))
                else:
                    for r in bd["_results"]:
                        print_results(r.get("alpha_id", ""), r, r.get("alpha_name", ""))
                        all_results.append(r)
            except Exception as e:
                print("  X 批 %d 异常: %s" % (bidx + 1, e))
            finally:
                batch_done[bidx] = True
                done_count = sum(batch_done)
                print("  进度: %d/%d 批完成" % (done_count, total_batches))

    loop.close()

    # 总对比表（按夏普排序）
    if len(all_results) > 1:
        headers = ["region", "decay", "trunc", "uni", "neut", "sharpe", "fitness"]
        rows = []
        for r in all_results:
            rows.append([
                r.get("_region", "?"),
                str(r.get("_decay", "?")),
                str(r.get("_trunc", "?")),
                (r.get("_uni", "?")[:20]),
                r.get("_neut", "?")[:15],
                "%.4f" % r["sharpe"] if r.get("sharpe") else "N/A",
                "%.4f" % r["fitness"] if r.get("fitness") else "N/A",
            ])
        cw = [max(len(h), max((len(r[i]) for r in rows), default=0)) + 2 for i, h in enumerate(headers)]
        tw = sum(cw) + len(cw) + 1
        print("\n %s" % ("=" * tw))
        print(" 扫荡总对比表（按夏普排序）")
        print(" %s" % ("=" * tw))
        print("| " + " | ".join(h.rjust(cw[i]) for i, h in enumerate(headers)) + " |")
        sorted_rows = sorted(rows, key=lambda r: float(r[5]) if r[5] != "N/A" else -999, reverse=True)
        for r in sorted_rows:
            print("| " + " | ".join(r[i].rjust(cw[i]) for i in range(len(headers))) + " |")
        print("\n  TOP 3:")
        for i, r in enumerate(sorted_rows[:3], 1):
            print("   %d. decay=%s trunc=%s uni=%s neut=%s  Sharpe=%s" % (
                i, r[1], r[2], r[3], r[4], r[5]))

    if args.output and all_results:
        import json
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

    if not all_results:
        sys.exit(1)


# ============================================================
# 模式 4a：Mass JSON（配置文件扫荡）
# ============================================================
def run_mass_json(argv):
    """多维扫荡：JSON 配置驱动，多组 settings 分批 Multi-Sim"""
    parser = argparse.ArgumentParser(prog="brain.py simulation mass")
    parser.add_argument("config", help="JSON 配置文件")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    template = config.get("template", "")
    if not template:
        print("X 配置文件中缺少 template")
        sys.exit(1)

    field_regions = config.get("field_regions", {})
    settings_list = config.get("settings_list", [])
    parameters = config.get("parameters", {})

    # 展开：生成 (settings, expression, field, params) 列表
    runs = []
    for s in settings_list:
        region = s.get("region", "USA")
        fields = field_regions.get(region, field_regions.get("_default", []))
        if not fields:
            continue
        # 参数组合
        combos = [{}]
        for pn, pv in parameters.items():
            combos = [dict(c, **{pn: v}) for c in combos for v in pv]
        for field in fields:
            for params in combos:
                expr = template.replace("FIELD", field)
                for pn, pv in params.items():
                    expr = expr.replace(pn, str(pv))
                runs.append((dict(s), expr, field, params))

    if not runs:
        print("X 配置展开后无有效组合（检查 field_regions 是否定义了字段）")
        sys.exit(1)

    # 按 settings 分组
    groups = {}
    for s, expr, field, params in runs:
        key = json.dumps(s, sort_keys=True)
        groups.setdefault(key, {"settings": s, "expressions": [], "fields": []})
        groups[key]["expressions"].append(expr)
        groups[key]["fields"].append(field)

    print(f"\n  展开: {len(runs)} 个组合, {len(groups)} 个 settings 分组")

    import asyncio
    import cnhkmcp
    loop = asyncio.new_event_loop()
    loop.run_until_complete(cnhkmcp.authenticate())

    all_results = []
    for gi, (gkey, gdata) in enumerate(groups.items(), 1):
        s = gdata["settings"]
        batch = list(gdata["expressions"])
        fields = list(gdata["fields"])
        if len(batch) < 2:
            batch.append("rank(returns)")
            fields.append("(占位)")

        print(f"\n  组{gi}/{len(groups)}: region={s.get('region','?')} "
              f"universe={s.get('universe','?')} "
              f"neut={s.get('neutralization','?')} decay={s.get('decay','?')}")

        result = loop.run_until_complete(cnhkmcp.create_multi_simulation(
            alpha_expressions=batch,
            region=s.get("region", "USA"),
            universe=s.get("universe", "TOP3000"),
            delay=s.get("delay", 1),
            decay=float(s.get("decay", 5.0)),
            neutralization=s.get("neutralization", "INDUSTRY"),
            truncation=float(s.get("truncation", 0.08)),
        ))

        if isinstance(result, dict) and result.get("error"):
            print(f"  X 组{gi} 失败: {result['error']}")
            continue
        for i, ar in enumerate(result.get("alpha_results", [])):
            if i >= len(fields):
                break
            aid = ar.get("alpha_id")
            if not aid:
                continue
            metrics = ar.get("details", {}).get("is", {})
            label = fields[i]
            if label == "(占位)":
                continue
            r = build_result_dict(label, aid, metrics)
            r["_region"] = str(s.get("region", "?"))
            r["_field"] = label
            r["_neut"] = str(s.get("neutralization", "?"))
            r["_decay"] = s.get("decay", "?")
            print_results(aid, metrics, label)
            all_results.append(r)

    loop.close()
    if not results:
        sys.exit(1)
    # 总对比表
    if len(all_results) > 1:
        headers = ["region", "field", "neut", "decay", "sharpe", "fitness"]
        rows = []
        for r in all_results:
            rows.append([
                r.get("_region", "?"),
                (r.get("_field", "?")[:20]),
                r.get("_neut", "?"),
                str(r.get("_decay", "?")),
                f"{r.get('sharpe', 0):.4f}" if r.get("sharpe") else "N/A",
                f"{r.get('fitness', 0):.4f}" if r.get("fitness") else "N/A",
            ])
        cw = [max(len(h), max((len(r[i]) for r in rows), default=0)) + 2 for i, h in enumerate(headers)]
        tw = sum(cw) + len(cw) + 1
        print(f"\n {'=' * tw}")
        print(f" \u626b\u8361\u603b\u5bf9\u6bd4\u8868 (\u6309\u590f\u666e\u6392\u5e8f)")
        print(f" {'=' * tw}")
        print("\u2502 " + " \u2502 ".join(h.rjust(cw[i]) for i, h in enumerate(headers)) + " \u2502")
        sorted_rows = sorted(rows, key=lambda r: float(r[4]) if r[4] != "N/A" else -999, reverse=True)
        for r in sorted_rows:
            print("\u2502 " + " \u2502 ".join(r[i].rjust(cw[i]) for i in range(len(headers))) + " \u2502")
        print(f"\n  TOP 3:")
        for i, r in enumerate(sorted_rows[:3], 1):
            print(f"   {i}. [{r[0]}] {r[1]:22s} neut={r[2]:12s} decay={r[3]:4s}  Sharpe={r[4]}")

    if args.output and all_results:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

    if not all_results:
        sys.exit(1)


# ============================================================
# 入口
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法: simulation.py <single|multi|mass> [...]")
        print("  simulation.py single fe <expr> [选项]")
        print("  simulation.py single py <file> [选项]")
        print("  simulation.py mass <expr> --region USA [选项] — 暴力模式")
        print("  simulation.py multi <e1> <e2>... [选项]")
        return

    mode = sys.argv[1]
    if mode in ("-h", "--help"):
        main()
        return
    if mode == "single":
        if len(sys.argv) < 3:
            print("需要指定 fe 或 py")
            return
        sub = sys.argv[2]
        if sub == "fe":
            run_single_fe(sys.argv[3:])
        elif sub == "py":
            run_single_py(sys.argv[3:])
        else:
            print(f"未知类型: {sub}，可用: fe, py")
    elif mode == "multi":
        run_multi(sys.argv[2:])
    elif mode == "mass":
        if len(sys.argv) >= 3 and sys.argv[2].endswith(".json"):
            run_mass_json(sys.argv[2:])
        else:
            run_mass(sys.argv[2:])
    else:
        print(f"未知模式: {mode}，可用: single, multi, mass")


if __name__ == "__main__":
    main()
