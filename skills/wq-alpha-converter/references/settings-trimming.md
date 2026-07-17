# Python Alpha Settings Trimming Guide

Not all settings from a Regular Alpha's `get_alpha_details()` can be passed to
`cnhkmcp.create_simulation(language='PYTHON', ...)`. This reference lists which fields
to keep, which to remove, and how to map between formats.

---

## Whitelist: Safe for Python Alpha Submit

| create_simulation Parameter | Default | Source in get_alpha_details | Notes |
|----------------------------|---------|----------------------------|-------|
| `instrumentType` | `EQUITY` | `settings.instrumentType` | |
| `region` | `USA` | `settings.region` | GLB not supported |
| `universe` | `TOP3000` | `settings.universe` | USA only; CHN must use `TOP2000U`. Check `get_platform_setting_options()` for other regions |
| `delay` | `1` | `settings.delay` | |
| `decay` | `0` | `settings.decay` | Keep as float |
| `neutralization` | `NONE` | `settings.neutralization` | Keep uppercase |
| `truncation` | `0.0` | `settings.truncation` | |
| `pasteurization` | `ON` | `settings.pasteurization` | Convert bool to `ON`/`OFF` |
| `visualization` | `True` | — | **Required for PYTHON.** The BRAIN API rejects PYTHON submissions without this field. Set to `False` for headless runs |
| `lookback` | (derived from expression) | `settings.lookback` | **Required for PYTHON.** The `create_simulation()` MCP tool **cannot** pass lookback; submit directly via `brain_client.session.post()`. Set to `max(largest_ts_window, 252)` |

## Blacklist: Always Remove Before Submit

| get_alpha_details Field | Reason |
|-------------------------|--------|
| `startDate` | Python submit rejects date-range fields |
| `endDate` | Same as above |
| `testPeriod` | Regular-only; Python submit uses `lookback` instead |
| `nanHandling` | Regular-only; **PYTHON rejects** with 400 error |
| `unitHandling` | Regular-only; **PYTHON rejects** with 400 error |
| `id` | Metadata, not a setting |
| `category` / `tags` / `stage` | Metadata only |
| Any `is` sub-object (sharpe, fitness, turnover) | Read-only metrics, not submit parameters |

## Trimming Rules: Step by Step

```
1. Start with settings from get_alpha_details()
2. Remove: startDate, endDate, nanHandling, unitHandling, testPeriod
3. Remove: id, category, tags, stage, is, isData
4. Map remaining fields to create_simulation parameter names
5. Set visualization=false for automated runs
6. Set lookback = max(largest_ts_window, default_252)
```

## Quick Function

```python
# ⚠️ Direct submission note:
# The create_simulation() MCP tool wraps SimulationSettings which lacks 'lookback'.
# PYTHON simulations MUST include lookback in settings.
# Use brain_client.session.post() directly instead of the MCP tool:
#
#   payload = {
#       "type": "REGULAR",
#       "settings": {**trimmed_settings, "lookback": 252, "visualization": False},
#       "regular": code,
#   }
#   resp = brain_client.session.post(f"{base_url}/simulations", json=payload)
#   # Then poll Location header for result

def trim_python_settings(raw_settings: dict) -> dict:
    """Strip Regular-only fields and return Python-compatible simulation params."""
    BLACKLIST = {
        'startDate', 'endDate', 'testPeriod', 'nanHandling', 'unitHandling',
        'id', 'category', 'tags', 'stage', 'is', 'isData',
    }
    PARAM_MAP = {
        'instrumentType': 'instrumentType',
        'region': 'region',
        'universe': 'universe',
        'delay': 'delay',
        'decay': 'decay',
        'neutralization': 'neutralization',
        'truncation': 'truncation',
        'pasteurization': 'pasteurization',
    }
    trimmed = {}
    for reg_key, param_key in PARAM_MAP.items():
        if reg_key in raw_settings:
            val = raw_settings[reg_key]
            # Convert pasteurization bool → string
            if reg_key == 'pasteurization' and isinstance(val, bool):
                val = 'ON' if val else 'OFF'
            trimmed[param_key] = val
    # Add defaults for fields not in raw settings
    trimmed.setdefault('instrumentType', 'EQUITY')
    trimmed.setdefault('region', 'USA')
    trimmed.setdefault('universe', 'TOP3000')
    trimmed.setdefault('delay', 1)
    trimmed.setdefault('neutralization', 'NONE')
    trimmed.setdefault('truncation', 0.0)
    trimmed.setdefault('pasteurization', 'ON')
    trimmed.setdefault('visualization', False)
    return trimmed
```

## Verification

Before submitting, run:
```python
options = await cnhkmcp.get_platform_setting_options()
# Cross-reference your trimmed settings against accepted values
```
If submission fails, check the error message against `platform-gotchas.md`.

---

*Use with `platform-gotchas.md` for full submission workflow.*
