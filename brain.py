#!/usr/bin/env python3
"""
BRAIN 工具集 — 统一入口

用法:
    python3 brain.py simulation single fe <表达式> [选项]
    python3 brain.py simulation single py <文件> [选项]
    python3 brain.py simulation multi <e1> <e2>... [选项]
    python3 brain.py simulation mass <配置文件> [选项]
    python3 brain.py compare <结果文件>... [选项]

示例:
    python3 brain.py simulation single fe "ts_rank(rank(returns),5)"
    python3 brain.py simulation single py alpha.py --output r.json
    python3 brain.py simulation multi "e1" "e2"
    python3 brain.py simulation mass config.json
    python3 brain.py compare results.json --min-sharpe 1.0
"""

import subprocess, sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"
SCRIPTS = {
    # (命令, 子命令) -> (脚本名, 额外参数)
    ("simulation", "single", "fe"):  ("simulation.py", ["single", "fe"]),
    ("simulation", "single", "py"):  ("simulation.py", ["single", "py"]),
    ("simulation", "multi"):        ("simulation.py", ["multi"]),
    ("simulation", "mass"):         ("simulation.py", ["mass"]),
    ("compare",):                    ("compare_results.py", []),
}


def dispatch(cmd_key, extra_args):
    key = cmd_key if isinstance(cmd_key, tuple) else (cmd_key,)
    info = SCRIPTS.get(key)
    if not info:
        return False
    script, base_args = info
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + base_args + extra_args
    sys.exit(subprocess.run(cmd).returncode)
    return True


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print_help()
        return

    # simulation single fe <expr> [...]
    if len(args) >= 4 and args[0] == "simulation" and args[1] == "single" and args[2] in ("fe", "py"):
        dispatch(("simulation", "single", args[2]), args[3:])

    # simulation multi <e1> <e2> [...]
    elif len(args) >= 3 and args[0] == "simulation" and args[1] == "multi":
        dispatch(("simulation", "multi"), args[2:])

    # simulation mass <config> [...]
    elif len(args) >= 3 and args[0] == "simulation" and args[1] == "mass":
        dispatch(("simulation", "mass"), args[2:])

    # compare <files> [...]
    elif args[0] == "compare":
        dispatch(("compare",), args[1:])

    else:
        print(f"未知命令或参数不足: {' '.join(args)}")
        print_help()


def print_help():
    print("BRAIN 工具集")
    print()
    print("  simulation single fe <表达式> [选项]   — FE 单条回测")
    print("  simulation single py <文件> [选项]     — Python Alpha 回测")
    print("  simulation multi <e1> <e2>... [选项]   — FE Multi 并行回测")
    print("  simulation mass <配置.json> [选项]      — 暴力扫荡（传 .json 走配置文件扫荡）")
    print("  compare <结果文件>... [选项]            — 结果对比")
    print()
    print("查看详细选项:  python3 brain.py <子命令> --help")


if __name__ == "__main__":
    main()
