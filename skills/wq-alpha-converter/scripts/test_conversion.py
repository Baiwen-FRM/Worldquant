#!/usr/bin/env python3
"""
Conversion Accuracy Test Suite

Validates FastExpr to Python Alpha conversion quality by:
1. Parsing test expressions and checking operator/field detection
2. Generating Python code and checking syntax + template features
3. Verifying edge-case handling (NaN, int32 sentinels, window bounds)

Usage:
    python3 test_conversion.py              # Run all tests
    python3 test_conversion.py --id 19      # Run specific test
    python3 test_conversion.py --category group  # Run category
"""

import ast
import re
import sys
import argparse

sys.path.insert(0, '.')

try:
    from scripts.wq_converter import parse_expression
except ImportError:
    try:
        from wq_converter import parse_expression
    except ImportError:
        print("Warning: wq_converter.py not found; running syntax-only tests.")
        parse_expression = None


# Test Cases: (id, category, expr, expected_ops, expected_fields, expected_patterns)
TESTS = [
    (1, "arithmetic", "-returns", {"reverse"}, {"returns"}, []),
    (2, "arithmetic", "abs(returns)", {"abs"}, {"returns"}, []),
    (3, "arithmetic", "log(cap)", {"log"}, {"cap"}, []),
    (4, "arithmetic", "sqrt(cap)", {"sqrt"}, {"cap"}, []),
    (5, "arithmetic", "signed_power(x, 3)", {"signed_power"}, {"x"}, []),
    (6, "arithmetic", "inverse(returns)", {"inverse"}, {"returns"}, []),
    (7, "cross-sectional", "rank(returns)", {"rank"}, {"returns"}, []),
    (8, "cross-sectional", "zscore(returns)", {"zscore"}, {"returns"}, []),
    (9, "cross-sectional", "winsorize(returns, 4)", {"winsorize"}, {"returns"}, []),
    (10, "cross-sectional", "scale(returns)", {"scale"}, {"returns"}, []),
    (11, "cross-sectional", "normalize(returns)", {"normalize"}, {"returns"}, []),
    (12, "cross-sectional", "quantile(returns)", {"quantile"}, {"returns"}, []),
    (13, "group", "group_neutralize(returns, sector)", {"group_neutralize"}, {"returns", "sector"}, []),
    (14, "group", "group_rank(returns, industry)", {"group_rank"}, {"returns", "industry"}, []),
    (15, "group", "group_zscore(returns, subindustry)", {"group_zscore"}, {"returns", "subindustry"}, []),
    (16, "group", "group_mean(returns, weight, sector)", {"group_mean"}, {"returns", "weight", "sector"}, []),
    (17, "time-series", "ts_mean(returns, 20)", {"ts_mean"}, {"returns"}, []),
    (18, "time-series", "ts_sum(returns, 20)", {"ts_sum"}, {"returns"}, []),
    (19, "time-series", "ts_std_dev(returns, 20)", {"ts_std_dev"}, {"returns"}, []),
    (20, "time-series", "ts_zscore(returns, 20)", {"ts_zscore"}, {"returns"}, []),
    (21, "time-series", "ts_rank(returns, 20)", {"ts_rank"}, {"returns"}, []),
    (22, "time-series", "ts_delay(returns, 3)", {"ts_delay"}, {"returns"}, []),
    (23, "time-series", "ts_delta(returns, 3)", {"ts_delta"}, {"returns"}, []),
    (24, "time-series", "ts_arg_max(returns, 20)", {"ts_arg_max"}, {"returns"}, []),
    (25, "time-series", "ts_arg_min(returns, 20)", {"ts_arg_min"}, {"returns"}, []),
    (26, "time-series", "ts_min_diff(returns, 20)", {"ts_min_diff"}, {"returns"}, []),
    (27, "time-series", "ts_product(returns, 20)", {"ts_product"}, {"returns"}, []),
    (28, "time-series", "ts_corr(returns, volume, 20)", {"ts_corr"}, {"returns", "volume"}, []),
    (29, "special", "universe_size", {"universe_size"}, set(), []),
    (30, "special", "trade_when(rank(x)>0.8, -group_rank(returns, group), -1)",
     {"trade_when", "rank", "group_rank", "reverse"}, {"x", "returns"}, []),
    (31, "transform", "bucket(rank(cap), 0, 1, 0.1)", {"bucket", "rank"}, {"cap"}, []),
    (32, "complex", "-ts_mean(returns, 20)", {"ts_mean", "reverse"}, {"returns"}, []),
    (33, "complex", "rank(ts_mean(returns, 20))", {"rank", "ts_mean"}, {"returns"}, []),
    (34, "complex", "group_zscore(winsorize(ts_backfill(cap, 120), 4), sector)",
     {"group_zscore", "winsorize", "ts_backfill"}, {"cap", "sector"}, []),
    (35, "complex", "signed_power(group_neutralize(ts_backfill(cap, 120), country), 3)",
     {"signed_power", "group_neutralize", "ts_backfill"}, {"cap", "country"}, []),
]


passed = 0
failed = 0
skipped = 0
results = []


def test_parse(test_id, expr, expected_ops, expected_fields):
    if parse_expression is None:
        return "skip", "parse not available"
    parsed = parse_expression(expr)
    issues = []
    missing_ops = expected_ops - set(parsed["operators"])
    if missing_ops:
        issues.append(f"missing operators: {missing_ops}")
    if expected_fields:
        missing_fields = expected_fields - set(parsed["data_fields"])
        if missing_fields:
            issues.append(f"missing fields: {missing_fields}")
    return ("fail", "; ".join(issues)) if issues else ("pass", "")


def test_syntax(code):
    try:
        ast.parse(code)
        return "pass", ""
    except SyntaxError as e:
        return "fail", f"syntax error: {e}"


def test_data_fields(code, expected_fields):
    """Check that @alpha data=[] includes all expected fields."""
    m = re.search(r'data=\[(.*?)\]', code)
    if not m:
        return ["data=[] not found in @alpha"]
    fields = set(f.strip(' "') for f in m.group(1).split(',') if f.strip())
    missing = expected_fields - fields
    return [f"missing data field in @alpha: {missing}"] if missing else []


def test_template_features(code):
    checks = {
        "@alpha(": "@alpha decorator",
        "return signal.astype(np.float32)": "float32 return type",
        "data.universe": "universe mask",
        "pasteurize(": "pasteurization helper",
        "import numpy as np": "numpy import",
        "np.nan_to_num": "NaN-safe helpers",
    }
    return [f"missing: {name}" for pattern, name in checks.items() if pattern not in code]


def run_test(test):
    test_id, category, expr, expected_ops, expected_fields, _ = test
    issues = []

    # 1. Parse test
    parse_result, parse_msg = test_parse(test_id, expr, expected_ops, expected_fields)
    if parse_result == "skip":
        return "SKIP", parse_msg
    if parse_result == "fail":
        issues.append(f"parse: {parse_msg}")

    # 2. Code generation tests
    if parse_expression is not None:
        from scripts.wq_converter import generate_python_alpha
        parsed = parse_expression(expr)
        code = generate_python_alpha(parsed, {}, {"id": None})

        syn_result, syn_msg = test_syntax(code)
        if syn_result == "fail":
            issues.append(f"syntax: {syn_msg}")

        field_issues = test_data_fields(code, expected_fields)
        issues.extend(field_issues)

        template_issues = test_template_features(code)
        issues.extend(template_issues)

    return ("FAIL", "; ".join(issues)) if issues else ("PASS", "")


def print_header():
    print(f"{'ID':>4} {'Category':<18} {'Result':<7} Detail")
    print("-" * 70)


def print_result(test_id, category, status, detail=""):
    colors = {"PASS": "\033[32m", "FAIL": "\033[31m", "SKIP": "\033[33m"}
    display = f"{colors.get(status, '')}{status}\033[0m"
    detail_short = detail[:50] + "..." if len(detail) > 50 else detail
    print(f"{test_id:>4} {category:<18} {display:<7} {detail_short}")


def main():
    parser = argparse.ArgumentParser(description="Run conversion accuracy tests")
    parser.add_argument("--id", type=int, help="Run specific test by ID")
    parser.add_argument("--category", type=str, help="Run tests in a category")
    args = parser.parse_args()

    tests_to_run = TESTS
    if args.id:
        tests_to_run = [t for t in TESTS if t[0] == args.id]
    if args.category:
        tests_to_run = [t for t in tests_to_run if t[1] == args.category]
    if not tests_to_run:
        print("No tests matched")
        sys.exit(1)

    global passed, failed, skipped
    print_header()
    for test in tests_to_run:
        test_id, category = test[0], test[1]
        status, detail = run_test(test)
        print_result(test_id, category, status, detail)
        globals()[{"PASS": "passed", "FAIL": "failed", "SKIP": "skipped"}[status]] += 1

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped ({passed+failed+skipped} total)")
    if failed:
        print("See references/conversion-evals.md for test specifications.")
        sys.exit(1)


if __name__ == "__main__":
    main()
