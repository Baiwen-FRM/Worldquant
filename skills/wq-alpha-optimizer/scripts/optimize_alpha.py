#!/usr/bin/env python3
"""
 WQ Alpha Optimizer -- Helper script for the wq-alpha-optimizer skill.

Usage:
  python3 optimize_alpha.py <alpha_id>                    # Fetch and analyze alpha
  python3 optimize_alpha.py <alpha_id> --simulate         # Simulate with current expression
  python3 optimize_alpha.py <alpha_id> --simulate --language PYTHON  # Simulate as Python Alpha
  python3 optimize_alpha.py <alpha_id> --simulate --code "new_expr"  # Simulate with custom code
  python3 optimize_alpha.py <alpha_id> --compare <new_id> # Compare two alphas

Supports both Fast Expression and Python Alpha. Detects language automatically
from the alpha code. Use --language to override.
"""

import argparse
import asyncio
import sys
from typing import Any, Optional

import cnhkmcp
from cnhkmcp.untracked.platform_functions import SimulationData, SimulationSettings


def detect_language(code: str) -> str:
    """Detect if code is Python Alpha or Fast Expression."""
    python_indicators = ["@alpha", "from brain.alphas", "import numpy",
                         "def alpha", "def my_alpha", "astype"]
    for indicator in python_indicators:
        if indicator in code:
            return "PYTHON"
    return "FASTEXPR"


def trim_settings_for_python(settings: dict) -> dict:
    """Remove settings not supported by Python Alpha."""
    disallowed = ["nanHandling", "unitHandling"]
    return {k: v for k, v in settings.items() if k not in disallowed}


async def authenticate():
    """Ensure we have a valid session."""
    await cnhkmcp.authenticate()


async def fetch_alpha(alpha_id: str) -> dict:
    """Fetch alpha details including expression, settings, and metrics."""
    await authenticate()
    return await cnhkmcp.get_alpha_details(alpha_id)


async def analyze_alpha(alpha_id: str):
    """Fetch and display alpha details in a structured format."""
    alpha = await fetch_alpha(alpha_id)

    print(f"Alpha ID: {alpha['id']}")
    print()

    expr = alpha.get("regular", {}).get("code", "N/A")
    lang = detect_language(expr)
    print(f"=== Expression (detected: {lang}) ===")
    print(expr)
    print()

    print("=== Settings ===")
    settings = alpha.get("settings", {})
    for key in ["instrumentType", "region", "universe", "delay", "decay",
                "neutralization", "truncation", "pasteurization"]:
        val = settings.get(key, "N/A")
        print(f"  {key}: {val}")
    print()

    print("=== Metrics ===")
    metrics = alpha.get("is", {})
    for key in ["sharpe", "fitness", "turnover", "margin", "returns",
                "drawdown", "std", "days"]:
        val = metrics.get(key, "N/A")
        if isinstance(val, float):
            print(f"  {key}: {val:.4f}")
        else:
            print(f"  {key}: {val}")
    print()

    print("=== Submission Check ===")
    try:
        check = await cnhkmcp.get_submission_check(alpha_id)
        corr = check.get("correlation_checks", {})
        print(f"  All passed: {check.get('all_passed', 'N/A')}")
        for check_type in ["production", "self"]:
            c = corr.get("checks", {}).get(check_type, {})
            max_corr = c.get("max_correlation", "N/A")
            passes = c.get("passes_check", "N/A")
            print(f"  {check_type} max correlation: {max_corr}")
            print(f"  {check_type} passes: {passes}")
    except Exception as e:
        print(f"  Error: {e}")

    return alpha


async def simulate_expression(alpha_id: str, language: str = "auto",
                              custom_code: Optional[str] = None):
    """Re-simulate the expression and return the new alpha.

    Args:
        alpha_id: Source alpha ID for settings reference.
        language: "auto" (detect from code), "FASTEXPR", or "PYTHON".
        custom_code: If provided, use this instead of the alpha's saved code.
    """
    alpha = await fetch_alpha(alpha_id)
    expr = custom_code or alpha.get("regular", {}).get("code", "")
    settings = alpha.get("settings", {})

    if not expr:
        print("Error: No expression found in alpha")
        return None

    if language == "auto":
        language = detect_language(expr)

    print(f"Simulating expression (language: {language}): {expr[:80]}...")

    sim_kwargs: dict[str, Any] = {
        "instrumentType": settings.get("instrumentType", "EQUITY"),
        "region": settings.get("region", "USA"),
        "universe": settings.get("universe", "TOP3000"),
        "delay": settings.get("delay", 1),
        "decay": float(settings.get("decay", 0)),
        "neutralization": settings.get("neutralization", "NONE"),
        "truncation": float(settings.get("truncation", 0)),
        "pasteurization": settings.get("pasteurization", "ON"),
        "language": language,
    }

    if language == "FASTEXPR":
        sim_kwargs["testPeriod"] = "P0Y0M"
    elif language == "PYTHON":
        trimmed = trim_settings_for_python(settings)
        for key in trimmed:
            if key in sim_kwargs:
                sim_kwargs[key] = trimmed[key]

    sim_settings = SimulationSettings(**sim_kwargs)
    sim_data = SimulationData(type="REGULAR", settings=sim_settings, regular=expr)

    result = await cnhkmcp.create_simulation(sim_data)
    return result


async def compare_alphas(alpha1_id: str, alpha2_id: str):
    """Compare metrics between two alphas."""
    a1 = await fetch_alpha(alpha1_id)
    a2 = await fetch_alpha(alpha2_id)

    m1 = a1.get("is", {})
    m2 = a2.get("is", {})

    print(f"{'Metric':<20} {'Original':<15} {'New':<15} {'Delta':<15}")
    print("-" * 65)
    for key in ["sharpe", "fitness", "turnover", "margin", "returns", "std", "drawdown"]:
        v1 = m1.get(key)
        v2 = m2.get(key)
        v1_str = f"{v1:.4f}" if isinstance(v1, (int, float)) else str(v1) if v1 else "N/A"
        v2_str = f"{v2:.4f}" if isinstance(v2, (int, float)) else str(v2) if v2 else "N/A"
        delta_str = f"{v2 - v1:+.4f}" if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else "N/A"
        print(f"{key:<20} {v1_str:<15} {v2_str:<15} {delta_str:<15}")


async def main():
    parser = argparse.ArgumentParser(description="WQ Alpha Optimizer")
    parser.add_argument("alpha_id", help="Alpha ID to analyze or optimize")
    parser.add_argument("--simulate", action="store_true", help="Simulate the expression")
    parser.add_argument("--compare", metavar="NEW_ID", help="Compare two alpha IDs")
    parser.add_argument("--language", choices=["auto", "FASTEXPR", "PYTHON"],
                        default="auto",
                        help="Alpha language (auto=detect from code)")
    parser.add_argument("--code", metavar="TEXT", default=None,
                        help="Custom expression/code to simulate (overrides saved code)")
    args = parser.parse_args()

    if args.compare:
        await compare_alphas(args.alpha_id, args.compare)
    elif args.simulate:
        result = await simulate_expression(args.alpha_id, args.language, args.code)
        if result:
            lang = args.language if args.language != "auto" else detect_language(
                args.code or "")
            print(f"\nNew Alpha ID: {result.get('id', 'N/A')}")
            m = result.get("is", {})
            for key in ["sharpe", "fitness", "turnover", "margin"]:
                val = m.get(key)
                if isinstance(val, (int, float)):
                    fmt = ".6f" if key == "margin" else ".4f"
                    print(f"{key.capitalize()}: {val:{fmt}}")
                else:
                    print(f"{key.capitalize()}: {val or 'N/A'}")
    else:
        await analyze_alpha(args.alpha_id)


if __name__ == "__main__":
    asyncio.run(main())
