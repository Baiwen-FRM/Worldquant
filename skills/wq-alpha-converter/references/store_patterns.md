# Store Usage Patterns

The `store` parameter in `@alpha` decorator persists state across days.

## Basic Syntax

```python
from brain.alphas import alpha
import numpy as np
import numpy.typing as npt

@alpha(
    data=["returns"],
    store=[{"name": "buf", "dims": "xi", "extend": np.float64(0)}],
)
def my_alpha(data, store) -> npt.NDArray[np.float32]:
    if store.buf is None:
        # First call only -- initialise
        store.buf = np.zeros((1, data.returns.shape[1]), dtype=np.float64)
    # ... use/store.buf ...
    return signal.astype(np.float32)
```

## Dims Options

| Value | Shape | Description |
|-------|-------|-------------|
| `"i"` | (n_instruments,) | 1-D vector, one value per instrument |
| `"xi"` | (any_rows, n_instruments) | 2-D buffer, rows are your window |

## Extend Value

- `extend` fills new instrument columns when the universe grows
- Must match the dtype exactly: `np.float64(0)`, `np.float32(0)`, `np.int64(0)`
- `store.buf is None` is ONLY true on the very first call
- Assign back to `store.buf` every step

## Common Patterns

### Rolling Window Buffer (dims="xi")

```python
WINDOW = 10

@alpha(
    data=["returns"],
    store=[{"name": "buf", "dims": "xi", "extend": np.float64(0)}],
)
def rolling_mean_reversion(data, store) -> npt.NDArray[np.float32]:
    raw = -np.nanmean(data.returns, axis=0).astype(np.float64)

    if store.buf is None:
        store.buf = raw[np.newaxis, :]
    else:
        store.buf = np.vstack([store.buf, raw])[-WINDOW:]

    signal = np.nanmean(store.buf, axis=0)
    return signal.astype(np.float32)
```

### State Tracking (dims="i")

```python
@alpha(
    data=["returns"],
    store=[{"name": "state", "dims": "i", "extend": np.float64(0)}],
)
def stateful_alpha(data, store) -> npt.NDArray[np.float32]:
    if store.state is None:
        store.state = np.zeros(data.returns.shape[1], dtype=np.float64)

    # Update state
    store.state = store.state * 0.9 + data.returns[-1] * 0.1

    return store.state.astype(np.float32)
```

## Key Rules

- `store` is a typed namespace object; `store.buf` acts like an attribute
- Always check `store.name is None` for first-call initialization
- The simulator persists `store` between time steps
- New instruments get `extend` value in each store column
- Use `dims="xi"` for time-series buffers, `dims="i"` for single-value-per-instrument state
