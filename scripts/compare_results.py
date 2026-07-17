#!/usr/bin/env python3
"""
Alpha 回测结果对比工具

功能：
- 加载一个或多个 JSON 结果文件（支持 Python Alpha 和 FE 回测结果）
- 合并展示综合对比表
- 按夏普/Fitness/年化收益等指标排名
- 按阈值过滤
- 按设置分组对比
- 导出对比报告

用法：
    # 查看单个结果文件
    python3 scripts/compare_results.py results.json

    # 对比多个结果文件
    python3 scripts/compare_results.py batch1.json batch2.json

    # 按夏普过滤（只显示夏普 >= 1.0 的）
    python3 scripts/compare_results.py results.json --min-sharpe 1.0

    # 按 Fitness 排名（默认按夏普）
    python3 scripts/compare_results.py results.json --rank-by fitness

    # 导出对比报告为 JSON
    python3 scripts/compare_results.py results.json --export report.json

    # 按设置分组展示
    python3 scripts/compare_results.py results.json --group-by neutralization
"""

import argparse
import json
import sys
# Unicode 表格符号常量
BOX_H = "\u2500"
BOX_T = "\u251c"
BOX_RL = "\u2524"
BOX_BL = "\u2514"
BOX_BR = "\u2518"



def load_results(file_paths):
    """加载一个或多个 JSON 结果文件，合并为统一列表"""
    all_results = []
    loaded_from = []
    for fpath in file_paths:
        try:
            with open(fpath) as f:
                data = json.load(f)
        except Exception as e:
            print(f"\u26a0\ufe0f  无法读取 {fpath}: {e}", file=sys.stderr)
            continue

        if isinstance(data, list):
            all_results.extend(data)
        elif isinstance(data, dict):
            all_results.append(data)
        else:
            print(f"\u26a0\ufe0f  未知格式: {fpath} (期望 list 或 dict)", file=sys.stderr)
            continue
        loaded_from.append(fpath)

    return all_results, loaded_from


def filter_results(results, min_sharpe=None, max_turnover=None, min_fitness=None):
    """按条件过滤结果"""
    filtered = results
    if min_sharpe is not None:
        filtered = [r for r in filtered
                    if isinstance(r.get("sharpe"), (int, float))
                    and (r["sharpe"] or 0) >= min_sharpe]
    if max_turnover is not None:
        filtered = [r for r in filtered
                    if isinstance(r.get("turnover"), (int, float))
                    and (r["turnover"] or 999) <= max_turnover]
    if min_fitness is not None:
        filtered = [r for r in filtered
                    if isinstance(r.get("fitness"), (int, float))
                    and (r["fitness"] or 0) >= min_fitness]
    return filtered


def get_safe(r, key):
    """安全取值，None 时返回默认值"""
    v = r.get(key)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    return None


# 对比指标定义
COMPARE_METRICS = [
    ("夏普比率", "sharpe"),
    ("Fitness", "fitness"),
    ("年化收益", "returns"),
    ("边际收益", "margin"),
    ("换手率", "turnover"),
    ("最大回撤", "drawdown"),
    ("IC", "ic"),
    ("子集夏普", "subUniverseSharpe"),
]

# 用于排名的指标（必须都是数值）
RANK_METRICS = {
    "sharpe": ("夏普比率", False),     # (显示名, 是否越低越好)
    "fitness": ("Fitness", False),
    "returns": ("年化收益率", False),
    "margin": ("边际收益率", False),
    "turnover": ("换手率", True),      # 越低越好
    "drawdown": ("最大回撤", True),    # 越低越好（负数越浅越好）
    "ic": ("IC", False),
}


def print_comparison_table(results, title="Alpha 回测结果对比"):
    """打印美观的对比表"""
    if not results:
        print("\u274c 没有数据可展示")
        return

    # 表头：名称 + 各指标
    headers = ["名称"] + [m[0] for m in COMPARE_METRICS]
    rows = []
    for r in results:
        name = r.get("alpha_name") or r.get("alpha_id", "?")
        if len(name) > 20:
            name = name[:17] + "..."
        row = [name]
        for label, key in COMPARE_METRICS:
            v = get_safe(r, key)
            if v is None:
                row.append("N/A")
            else:
                # 特殊处理：drawdown 是负数
                row.append(f"{v:.4f}")
        rows.append(row)

    # 计算列宽
    col_widths = []
    for ci, h in enumerate(headers):
        cw = max(len(h), max((len(row[ci]) for row in rows), default=0)) + 2
        col_widths.append(cw)

    total_width = sum(col_widths) + len(col_widths) + 1

    def fmt_row(cells, sep="\u2502"):
        return f"{sep} " + f" {sep} ".join(c.ljust(w) for c, w in zip(cells, col_widths)) + f" {sep}"

    # 打印
    print(f"\n{'=' * total_width}")
    print(f"{title}")
    print(f"{'=' * total_width}")
    print(fmt_row(headers))
    print(BOX_T + BOX_H * (total_width - 2) + BOX_RL)
    for row in rows:
        print(fmt_row(row))
    print(BOX_BL + BOX_H * (total_width - 2) + BOX_BR)


def print_rankings(results, rank_by="sharpe", top_n=10):
    """按指定指标打印排名"""
    if rank_by not in RANK_METRICS:
        print(f"\u26a0\ufe0f  未知的排名指标: {rank_by}")
        print(f"   可选: {', '.join(RANK_METRICS.keys())}")
        return

    label, lower_is_better = RANK_METRICS[rank_by]

    # 过滤掉无该指标值的
    valid = [r for r in results if get_safe(r, rank_by) is not None]
    if not valid:
        print(f"\u274c 没有包含 '{label}' 指标的 Alpha")
        return

    sorted_results = sorted(
        valid,
        key=lambda r: (get_safe(r, rank_by) or 0),
        reverse=not lower_is_better,
    )

    print(f"\n\U0001f3c6 {label} 排名 {'(越低越好)' if lower_is_better else '(越高越好)'}")
    print(f"{'=' * 60}")
    for i, r in enumerate(sorted_results[:top_n], 1):
        name = r.get("alpha_name") or r.get("alpha_id", "?")
        val = get_safe(r, rank_by)
        aid = r.get("alpha_id", "")
        print(f"  {i:2d}. {name:30s}  {label} = {val:.4f}  (ID: {aid})")

    if len(sorted_results) > top_n:
        print(f"  ... 共 {len(sorted_results)} 个 Alpha (显示前 {top_n} 个)")


def print_grouped_comparison(results, group_by_key="neutralization"):
    """按设置分组展示对比"""
    groups = {}
    for r in results:
        settings = r.get("settings", {})
        group_val = settings.get(group_by_key, "其他")
        if group_val not in groups:
            groups[group_val] = []
        groups[group_val].append(r)

    if len(groups) <= 1:
        print(f"\n\U0001f4ca 同一设置 (无分组对比)")
        return

    print(f"\n\U0001f4ca 按 {group_by_key} 分组对比")
    for gval, grp in sorted(groups.items()):
        avg_sharpe = sum(get_safe(r, "sharpe") or 0 for r in grp) / len(grp)
        best = max(grp, key=lambda r: get_safe(r, "sharpe") or 0)
        print(f"\n  [{gval}] 数量={len(grp)}, 平均夏普={avg_sharpe:.4f}")
        print(f"         最优: {best.get('alpha_name', '?')} (Sharpe={get_safe(best, 'sharpe'):.4f})")
        for r in sorted(grp, key=lambda x: get_safe(x, "sharpe") or 0, reverse=True)[:3]:
            s = get_safe(r, "sharpe")
            print(f"         \u2502 {r.get('alpha_name', '?'):25s} Sharpe={s:.4f}" if s else f"         \u2502 {r.get('alpha_name', '?'):25s} Sharpe=N/A")


def export_report(results, output_path, rank_by="sharpe"):
    """导出对比报告"""
    if not results:
        print("\u274c 无结果可导出")
        return

    # 按指定指标排序
    sorted_results = sorted(
        results,
        key=lambda r: get_safe(r, rank_by) or 0,
        reverse=True,
    )

    report = {
        "report_generated": True,
        "total_alphas": len(results),
        "ranked_by": rank_by,
        "alphas": sorted_results,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\U0001f4be 对比报告已导出到: {output_path}")


def run():
    parser = argparse.ArgumentParser(
        description="Alpha 回测结果对比工具"
    )
    parser.add_argument(
        "files", nargs="+",
        help="JSON 结果文件路径（支持多个，会自动合并对比）"
    )
    parser.add_argument(
        "--min-sharpe", type=float, default=None,
        help="最低夏普比率过滤"
    )
    parser.add_argument(
        "--max-turnover", type=float, default=None,
        help="最高换手率过滤"
    )
    parser.add_argument(
        "--min-fitness", type=float, default=None,
        help="最低 Fitness 过滤"
    )
    parser.add_argument(
        "--rank-by", default="sharpe",
        help="排名指标: sharpe/fitness/returns/margin/turnover/ic (默认: sharpe)"
    )
    parser.add_argument(
        "--top", type=int, default=15,
        help="排名显示前 N 个 (默认: 15)"
    )
    parser.add_argument(
        "--group-by", default="",
        help="按设置分组对比: neutralization/region/universe/decay"
    )
    parser.add_argument(
        "--export", default="",
        help="导出对比报告为 JSON 文件路径"
    )
    args = parser.parse_args()

    # 加载结果
    results, loaded = load_results(args.files)
    if not results:
        print("\u274c 未能加载任何结果")
        sys.exit(1)

    print(f"\U0001f4cb 加载 {len(loaded)} 个文件，共 {len(results)} 个 Alpha 结果")

    # 过滤
    filtered = filter_results(results, args.min_sharpe, args.max_turnover, args.min_fitness)
    if len(filtered) < len(results):
        print(f"\U0001f50d 过滤后: {len(filtered)} 个 Alpha (原始: {len(results)})")

    if not filtered:
        print("\u274c 过滤后没有满足条件的结果")
        sys.exit(1)

    # 展示对比表
    print_comparison_table(filtered)

    # 排名
    print_rankings(filtered, args.rank_by, args.top)

    # 分组对比
    if args.group_by:
        print_grouped_comparison(filtered, args.group_by)

    # 导出
    if args.export:
        export_report(filtered, args.export, args.rank_by)

    print()


if __name__ == "__main__":
    run()
