#!/usr/bin/env python3
"""
BRAIN Fast Expression to Python Alpha Converter with optional backtesting.

Usage:
    python3 wq_converter.py <alpha_id>
    python3 wq_converter.py --expression "ts_rank(rank(returns))"
    python3 wq_converter.py <alpha_id> --backtest
    python3 wq_converter.py <alpha_id> --compare

Requires: cnhkmcp package (authenticated credentials in config)
"""

import argparse
import asyncio
import re
import sys
from typing import Optional

try:
    import cnhkmcp
    import numpy as np
except ImportError:
    print("Error: cnhkmcp package required. Install with: pip install cnhkmcp", file=sys.stderr)
    sys.exit(1)


INDENT = "    "


# ── Settings Trimming ──

def trim_settings(raw_settings: dict) -> dict:
    """Strip Regular-only fields, return Python-compatible simulation params."""
    param_map = {
        'instrumentType': 'instrumentType', 'region': 'region', 'universe': 'universe',
        'delay': 'delay', 'decay': 'decay', 'neutralization': 'neutralization',
        'truncation': 'truncation', 'pasteurization': 'pasteurization',
    }
    trimmed = {}
    for reg_key, param_key in param_map.items():
        if reg_key in raw_settings:
            val = raw_settings[reg_key]
            if reg_key == 'pasteurization' and isinstance(val, bool):
                val = 'ON' if val else 'OFF'
            trimmed[param_key] = val
    trimmed.setdefault('instrumentType', 'EQUITY')
    trimmed.setdefault('region', 'USA')
    trimmed.setdefault('universe', 'TOP3000')
    trimmed.setdefault('delay', 1)
    trimmed.setdefault('neutralization', 'NONE')
    trimmed.setdefault('truncation', 0.0)
    trimmed.setdefault('pasteurization', 'ON')
    trimmed.setdefault('visualization', False)
    return trimmed


# ── Backtesting ──

async def run_backtest(code: str, settings: dict) -> dict:
    """Submit Python Alpha simulation and return metrics."""
    sim_settings = trim_settings(settings)
    print(f"# Submitting Python simulation ({sim_settings.get('region', 'USA')}, "
          f"{sim_settings.get('universe', 'TOP3000')})...")

    result = await cnhkmcp.create_simulation(
        type='REGULAR', language='PYTHON', regular=code, **sim_settings
    )
    sim_id = result.get('simulationId') or result.get('id', '')
    print(f"# Simulation ID: {sim_id}")

    final = await cnhkmcp.wait_for_simulation(sim_id, timeout=600)
    metrics = {}
    if isinstance(final, dict):
        for key in ('sharpe', 'fitness', 'turnover', 'return', 'std', 'max_drawdown'):
            if key in final:
                metrics[key] = final[key]
        metrics['simulationId'] = sim_id
    return metrics


# ── Conversion Core ──

async def convert_alpha(alpha_id: Optional[str] = None, expression: Optional[str] = None):
    """Main conversion entry point."""
    await cnhkmcp.authenticate()

    if alpha_id:
        alpha = await cnhkmcp.get_alpha_details(alpha_id)
        expr = alpha["regular"]["code"]
        settings = alpha.get("settings", {})
        meta = {
            "id": alpha["id"],
            "category": alpha.get("category", ""),
            "tags": alpha.get("tags", []),
            "stage": alpha.get("stage", ""),
        }
        is_data = alpha.get("is", {})
        if is_data:
            meta["sharpe"] = is_data.get("sharpe")
            meta["fitness"] = is_data.get("fitness")
            meta["turnover"] = is_data.get("turnover")
    elif expression:
        expr = expression
        settings = {}
        meta = {"id": None}
    else:
        print("Error: Provide either --alpha-id or --expression", file=sys.stderr)
        sys.exit(1)

    parsed = parse_expression(expr)

    # Look up operators
    ops_data = await cnhkmcp.get_operators()
    all_ops = {o["name"]: o for o in ops_data["operators"]}
    for op_name in parsed["operators"]:
        op = all_ops.get(op_name)
        if op:
            print(f"# Operator: {op_name} — {op.get('description', '')[:100]}")

    # Look up data fields
    for field in parsed["data_fields"]:
        fields = await cnhkmcp.get_datafields(data_type="MATRIX", search=field)
        for f in fields.get("results", []):
            if f["id"] == field:
                print(f"# Field: {f['id']} ({f['dataset']['id']}) — {f['description'][:80]}")
                break

    code = generate_python_alpha(parsed, settings, meta)
    print(code)
    return code, parsed, settings, meta


def parse_expression(expr: str) -> dict:
    """Parse Fast Expression into structured data."""
    operators = set()
    data_fields = set()
    variables = {}

    # Common BRAIN operators
    op_patterns = [
        r'\b(ts_rank|ts_sum|ts_mean|ts_std_dev|ts_zscore|ts_corr|ts_covariance|'
        r'ts_arg_max|ts_arg_min|ts_delay|ts_delta|ts_decay_linear|ts_decay_exp_window|'
        r'ts_av_diff|ts_backfill|ts_count_nans|ts_entropy|ts_min_diff|ts_min_max_cps|'
        r'ts_min_max_diff|ts_product|ts_quantile|ts_regression|ts_scale|ts_skewness|'
        r'ts_step|ts_target_tvr_decay|ts_target_tvr_delta_limit|ts_target_tvr_hump|'
        r'rank|group_rank|group_mean|group_neutralize|group_scale|group_zscore|'
        r'group_backfill|group_extra|group_cartesian_product|combo_a|'
        r'bucket|trade_when|generate_stats|'
        r'scale|neutralize|normalize|quantile|winsorize|zscore|regression_proj|vector_proj|'
        r'abs|add|multiply|subtract|divide|inverse|log|power|signed_power|sqrt|reverse|'
        r'densify|sigmoid|sign|tanh|'
        r'if_else|is_nan|'
        r'and|or|not|'
        r'vec_avg|vec_count|vec_max|vec_min|vec_range|vec_stddev|vec_sum|'
        r'hump|hump_decay|days_from_last_change|kth_element|last_diff_value|'
        r'self_corr|inst_pnl|in|universe_size|'
        r'reduce_avg|reduce_choose|reduce_count|reduce_ir|reduce_kurtosis|reduce_max|'
        r'reduce_min|reduce_norm|reduce_percentage|reduce_powersum|reduce_range|'
        r'reduce_skewness|reduce_stddev|reduce_sum'
        r')\s*\('
    ]

    # Identify operators from expression
    for match in re.finditer(op_patterns[0], expr, re.IGNORECASE):
        operators.add(match.group(1))

    # Extract ALL word-like tokens from expression
    all_tokens = set(re.findall(r'\b([a-z]\w*)\b', expr.lower()))
    known_ops = {
        'ts_rank','ts_sum','ts_mean','ts_std_dev','ts_zscore','ts_corr','ts_covariance',
        'ts_arg_max','ts_arg_min','ts_delay','ts_delta','ts_decay_linear','ts_decay_exp_window',
        'ts_av_diff','ts_backfill','ts_count_nans','ts_entropy','ts_min_diff','ts_min_max_cps',
        'ts_min_max_diff','ts_product','ts_quantile','ts_regression','ts_scale','ts_skewness',
        'ts_step','ts_target_tvr_decay','ts_target_tvr_delta_limit','ts_target_tvr_hump',
        'rank','group_rank','group_mean','group_neutralize','group_scale','group_zscore',
        'group_backfill','group_extra','group_cartesian_product','combo_a',
        'bucket','trade_when','generate_stats',
        'scale','neutralize','normalize','quantile','winsorize','zscore','regression_proj','vector_proj',
        'abs','add','multiply','subtract','divide','inverse','log','power','signed_power','sqrt','reverse',
        'densify','sigmoid','sign','tanh',
        'if_else','is_nan','and','or','not',
        'vec_avg','vec_count','vec_max','vec_min','vec_range','vec_stddev','vec_sum',
        'hump','hump_decay','days_from_last_change','kth_element','last_diff_value',
        'self_corr','inst_pnl','universe_size',
        'reduce_avg','reduce_choose','reduce_count','reduce_ir','reduce_kurtosis','reduce_max',
        'reduce_min','reduce_norm','reduce_percentage','reduce_powersum','reduce_range',
        'reduce_skewness','reduce_stddev','reduce_sum',
    }
    param_names = {
        'd', 'k', 'lag', 'rate', 'std', 'limit', 'usestd', 'nlength', 'sigma',
        'driver', 'scale', 'longscale', 'shortscale', 'hump', 'p', 'f', 'c',
        'dense', 'rettype', 'range', 'filter', 'condition', 'nan', 'group',
        'input', 'alpha', 'threshold', 'span', 'n_init', 'maxlag',
    }
    var_assignments = set(re.findall(r'(\w+)\s*=', expr))
    data_fields = all_tokens - known_ops - param_names - var_assignments

    # Detect prefix operators that don't use function-call syntax
    if re.search(r'(?<![\w)])-(?![0-9.\s])', expr):
        operators.add('reverse')
    if 'universe_size' in re.findall(r'\buniverse_size\b', expr.lower()):
        operators.add('universe_size')

    return {
        "original": expr,
        "operators": sorted(operators),
        "data_fields": sorted(data_fields),
        "variables": variables,
    }


def generate_python_alpha(parsed: dict, settings: dict, meta: dict) -> str:
    """Generate Python Alpha code from parsed expression."""
    alpha_id = meta.get("id")
    original_expr = parsed.get("original", "")

    header_lines = []
    if alpha_id:
        header_lines.append(f'# Alpha ID: {alpha_id}')
    header_lines.append(f'# Original Expression: {original_expr}')
    if settings:
        setting_parts = []
        order = ['region', 'universe', 'delay', 'decay', 'neutralization', 'truncation', 'pasteurization']
        for key in order:
            if key not in settings:
                continue
            val = settings[key]
            if key == 'neutralization':
                val = str(val).upper()
            elif key == 'pasteurization':
                val = 'ON' if val else 'OFF'
            setting_parts.append(f'{key}={val}')
        for key, val in settings.items():
            if key not in order:
                setting_parts.append(f'{key}={val}')
        header_lines.append(f'# Settings: {", ".join(setting_parts)}')
    header_lines.append('')

    fields = parsed["data_fields"]
    has_ts_ops = any(o.startswith("ts_") for o in parsed["operators"])
    needs_store = "trade_when" in parsed["operators"] or has_ts_ops

    lines = []
    lines.append('from brain.alphas import alpha')
    lines.append('import numpy as np')
    lines.append('import numpy.typing as npt')
    for h in reversed(header_lines):
        lines.insert(0, h)
    lines.append('')

    lines.append('')
    lines.append('def field_to_float(x):')
    lines.append(f'{INDENT}"""Convert BRAIN int32/float32 field to float64, replacing sentinel missings."""')
    lines.append(f'{INDENT}if np.issubdtype(x.dtype, np.integer):')
    lines.append(f'{INDENT}{INDENT}missing = np.iinfo(x.dtype).min')
    lines.append(f'{INDENT}{INDENT}out = x.astype(np.float64)')
    lines.append(f'{INDENT}{INDENT}out[x == missing] = np.nan')
    lines.append(f'{INDENT}{INDENT}return out')
    lines.append(f'{INDENT}return x.astype(np.float64)')
    lines.append('')

    lines.append('def pasteurize(a, u):')
    lines.append(f'{INDENT}a = a.copy()')
    lines.append(f'{INDENT}a[~u.astype(bool)] = np.nan')
    lines.append(f'{INDENT}return a')
    lines.append('')

    lines.append('def neutralize(a):')
    lines.append(f'{INDENT}a0 = np.nan_to_num(a, nan=0, posinf=0, neginf=0)')
    lines.append(f'{INDENT}return a - np.mean(a0)')
    lines.append('')

    lines.append('def scale(a):')
    lines.append(f'{INDENT}a0 = np.nan_to_num(a, nan=0, posinf=0, neginf=0)')
    lines.append(f'{INDENT}norm = np.linalg.norm(a0, ord=1)')
    lines.append(f'{INDENT}return a / norm if norm > 0 else a')
    lines.append('')

    lines.append('def cross_sectional_rank(x):')
    lines.append(f'{INDENT}"""Rank across instruments, returns 0.0 to 1.0. NaN in -> NaN out."""')
    lines.append(f'{INDENT}n = np.sum(~np.isnan(x))')
    lines.append(f'{INDENT}if n == 0:')
    lines.append(f'{INDENT}{INDENT}return np.full_like(x, np.nan)')
    lines.append(f'{INDENT}invalid = np.isnan(x)')
    lines.append(f'{INDENT}x_filled = np.where(invalid, -np.inf, x)')
    lines.append(f'{INDENT}order = np.argsort(x_filled)')
    lines.append(f'{INDENT}ranks = np.empty_like(order)')
    lines.append(f'{INDENT}ranks[order] = np.arange(len(x))')
    lines.append(f'{INDENT}result = np.where(invalid, np.nan, (ranks + 1) / n)')
    lines.append(f'{INDENT}return result')
    lines.append('')

    lines.append('def group_neutralize(a, group_labels):')
    lines.append(f'{INDENT}"""')
    lines.append(f'{INDENT}Subtract group mean. NaN/int sentinel group labels excluded.')
    lines.append(f'{INDENT}Groups with all-NaN signal stay NaN.')
    lines.append(f'{INDENT}"""')
    lines.append(f'{INDENT}a = a.astype(np.float64)')
    lines.append(f'{INDENT}result = a.copy()')
    lines.append(f'{INDENT}if np.issubdtype(group_labels.dtype, np.integer):')
    lines.append(f'{INDENT}{INDENT}sentinel = np.iinfo(group_labels.dtype).min')
    lines.append(f'{INDENT}{INDENT}is_valid = (group_labels != sentinel)')
    lines.append(f'{INDENT}else:')
    lines.append(f'{INDENT}{INDENT}is_valid = np.isfinite(group_labels)')
    lines.append(f'{INDENT}for g in np.unique(group_labels[is_valid]):')
    lines.append(f'{INDENT}{INDENT}mask = (group_labels == g) & is_valid')
    lines.append(f'{INDENT}{INDENT}valid_vals = a[mask][np.isfinite(a[mask])]')
    lines.append(f'{INDENT}{INDENT}if len(valid_vals) > 0:')
    lines.append(f'{INDENT}{INDENT}{INDENT}result[mask] = a[mask] - np.mean(valid_vals)')
    lines.append(f'{INDENT}return result')
    lines.append('')

    fields_list = ', '.join(f'"{f}"' for f in fields)
    if needs_store:
        store_decl = '[{"name": "prev", "dims": "i", "extend": np.float64(np.nan)}]'
    else:
        store_decl = '[]'

    lines.append('')
    lines.append('@alpha(')
    lines.append(f'{INDENT}data=[{fields_list}],')
    lines.append(f'{INDENT}store={store_decl},')
    lines.append(')')
    lines.append(f'def alpha_fn(data, store) -> npt.NDArray[np.float32]:')

    indent = INDENT
    lines.append(f'{indent}u = data.universe[-1].astype(bool)')
    lines.append(f'{indent}n = len(u)')
    for f in fields:
        lines.append(f'{indent}{f} = data.{f}[-1].copy()')
    lines.append(f'{indent}# TODO: Implement expression logic here')
    lines.append(f'{indent}signal = np.zeros(n, dtype=np.float32)')
    lines.append(f'{indent}')
    lines.append(f'{indent}# Post-processing')
    lines.append(f'{indent}signal = pasteurize(signal, u)')
    lines.append(f'{indent}signal = scale(neutralize(signal))')
    lines.append(f'{indent}return signal.astype(np.float32)')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Convert BRAIN Fast Expression Alpha to Python Alpha"
    )
    parser.add_argument("alpha_id", nargs="?", help="BRAIN Alpha ID to convert")
    parser.add_argument("--expression", "-e", help="Fast Expression string (if no Alpha ID)")
    parser.add_argument("--backtest", "-b", action="store_true",
                        help="Submit Python Alpha for backtesting after conversion")
    parser.add_argument("--compare", "-c", action="store_true",
                        help="Compare Python Alpha with original FastExpr metrics")
    args = parser.parse_args()

    if not args.alpha_id and not args.expression:
        parser.print_help()
        sys.exit(1)

    async def run():
        code, parsed, settings, meta = await convert_alpha(args.alpha_id, args.expression)

        # Show original metrics when comparing
        if args.compare and args.alpha_id:
            print("\n# === FastExpr Metrics (original) ===")
            alpha = await cnhkmcp.get_alpha_details(args.alpha_id)
            is_data = alpha.get("is", {})
            if is_data:
                print(f"  sharpe:   {is_data.get('sharpe', 'N/A')}")
                print(f"  fitness:  {is_data.get('fitness', 'N/A')}")
                print(f"  turnover: {is_data.get('turnover', 'N/A')}")
                print(f"  returns:  {is_data.get('returns', 'N/A')}")

        # Backtesting
        if args.backtest and args.alpha_id:
            print("\n# === Python Alpha Backtest ===")
            metrics = await run_backtest(code, settings)
            if metrics:
                for k, v in metrics.items():
                    if k != 'simulationId':
                        print(f"  {k}: {v}")
                print(f"  simulationId: {metrics.get('simulationId', 'N/A')}")

                # Compare if both available
                if args.compare:
                    alpha = await cnhkmcp.get_alpha_details(args.alpha_id)
                    orig = alpha.get("is", {})
                    if orig and 'sharpe' in metrics and orig.get('sharpe'):
                        delta = float(metrics['sharpe']) - float(orig['sharpe'])
                        print(f"\n# Sharpe delta: {delta:+.3f}"
                              f" ({'within tolerance' if abs(delta) < 0.2 else 'CHECK MISMATCH'})")
            else:
                print("  No metrics returned. Check platform UI for task status.")

    asyncio.run(run())


if __name__ == "__main__":
    main()
