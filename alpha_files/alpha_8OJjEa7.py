# Alpha ID: 8OJjEa7
# Original Expression:
# turn = volume/sharesout;
# turn20=rank(regression_neut(-ts_mean(turn,20),densify(cap)));
# STR = regression_neut(-ts_std_dev(turn,20),densify(cap));
# UTR = STR+turn20+(STR/(1+abs(STR)));
# regression_neut(regression_neut(regression_neut(sign(UTR)*power(abs(UTR),0.5),turn20),vwap),ts_delta(mdl175_retainedearnings/sharesout,120))
#
# Settings: region=CHN, universe=TOP3000, delay=0, decay=0,
#           neutralization=INDUSTRY, truncation=0.05, pasteurization=ON

from brain.alphas import alpha
import numpy as np
import numpy.typing as npt

WINDOW_TURN = 20
WINDOW_TS_DELTA = 121  # ts_delta(x, 120) needs x[-1] - x[-1-120]


def field_to_float(x):
    """Convert BRAIN int32/float32 field to float64, replacing sentinel missings with NaN."""
    if np.issubdtype(x.dtype, np.integer):
        missing = np.iinfo(x.dtype).min
        out = x.astype(np.float64)
        out[x == missing] = np.nan
        return out
    return x.astype(np.float64)


def pasteurize(a, u):
    a = a.copy()
    a[~u.astype(bool)] = np.nan
    return a


def cross_sectional_rank(x):
    """Rank across instruments, 0.0–1.0. NaN inputs -> NaN in output."""
    invalid = np.isnan(x)
    n = np.sum(~invalid)
    if n == 0:
        return np.full_like(x, np.nan)
    x_filled = np.where(invalid, -np.inf, x)
    order = np.argsort(x_filled)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(x))
    return np.where(invalid, np.nan, (ranks + 1) / n)


def densify(x, n_buckets=20):
    """Convert continuous values to compact buckets (densify)."""
    valid = np.isfinite(x)
    if np.sum(valid) == 0:
        return np.full_like(x, np.nan)
    x_valid = x[valid]
    ranks = np.argsort(np.argsort(x_valid))
    buckets = np.floor(ranks / max(1, len(x_valid) / n_buckets)).astype(np.float64)
    result = np.full_like(x, np.nan)
    result[valid] = buckets
    return result


def regression_proj(y, x):
    """
    Cross-sectional regression projection: ŷ = α + βx
    Regress y on x with intercept, return predicted values.
    regression_neut(y, x) = y - regression_proj(y, x)
    Handles NaN by only using finite pairs.
    """
    valid = np.isfinite(x) & np.isfinite(y)
    n_valid = np.sum(valid)
    if n_valid < 2:
        return np.full_like(y, np.nan)
    xv = x[valid]
    yv = y[valid]
    x_mean = np.mean(xv)
    y_mean = np.mean(yv)
    # beta with intercept: cov(x,y) / var(x)
    beta = np.nansum((xv - x_mean) * (yv - y_mean)) / max(np.nansum((xv - x_mean) ** 2), 1e-30)
    projection = y_mean + beta * (x - x_mean)
    projection[~valid] = np.nan
    return projection


def regression_neut(y, x):
    """
    Cross-sectional regression residual: ε = y - regression_proj(y, x)
    Equivalent to sub(y, regression_proj(y, x)).
    Handles NaN by only using finite pairs.
    """
    return y - regression_proj(y, x)


def ts_delta_from_buffer(buf):
    """
    ts_delta(x, d): current value minus value d days ago.
    buf is a rolling buffer where buf[-1] is current and buf[0] is oldest.
    """
    if buf.shape[0] < 2:
        return np.full(buf.shape[1], np.nan)
    return buf[-1] - buf[0]


@alpha(
    data=["volume", "sharesout", "cap", "vwap", "mdl175_retainedearnings"],
    store=[
        {"name": "turn_buffer", "dims": "xi", "extend": np.float64(np.nan)},
        {"name": "md_earnings_buffer", "dims": "xi", "extend": np.float64(np.nan)},
    ],
)
def alpha_fn(data, store) -> npt.NDArray[np.float32]:
    n = data.volume.shape[1]

    volume_f = field_to_float(data.volume[-1])
    sharesout_f = field_to_float(data.sharesout[-1])
    cap_f = field_to_float(data.cap[-1])
    vwap_f = field_to_float(data.vwap[-1])
    re_f = field_to_float(data.mdl175_retainedearnings[-1])

    # Step 1: turn = volume / sharesout
    with np.errstate(invalid="ignore", divide="ignore"):
        turn = np.divide(volume_f, sharesout_f, out=np.full(n, np.nan), where=sharesout_f != 0)

    # Step 2: Update rolling buffers
    if store.turn_buffer is None:
        store.turn_buffer = turn[np.newaxis, :]
    else:
        store.turn_buffer = np.vstack([store.turn_buffer, turn[np.newaxis, :]])[-WINDOW_TURN:]

    with np.errstate(invalid="ignore", divide="ignore"):
        re_ratio = np.divide(re_f, sharesout_f, out=np.full(n, np.nan), where=sharesout_f != 0)
    if store.md_earnings_buffer is None:
        store.md_earnings_buffer = re_ratio[np.newaxis, :]
    else:
        store.md_earnings_buffer = np.vstack([store.md_earnings_buffer, re_ratio[np.newaxis, :]])[-WINDOW_TS_DELTA:]

    # Step 3: turn20 = rank(regression_neut(-ts_mean(turn,20), densify(cap)))
    ts_mean_turn = np.nanmean(store.turn_buffer, axis=0)
    cap_dense = densify(cap_f)
    turn20 = cross_sectional_rank(regression_neut(-ts_mean_turn, cap_dense))

    # Step 4: STR = regression_neut(-ts_std_dev(turn,20), densify(cap))
    ts_std_turn = np.nanstd(store.turn_buffer, axis=0, ddof=0)
    STR = regression_neut(-ts_std_turn, cap_dense)

    # Step 5: UTR = STR + turn20 + STR/(1+abs(STR))
    with np.errstate(invalid="ignore", divide="ignore"):
        str_term = np.divide(STR, 1.0 + np.abs(STR), out=np.full(n, np.nan), where=(1.0 + np.abs(STR)) != 0)
    UTR = STR + turn20 + str_term

    # Step 6: Nested regression_neut chain:
    #   sign(UTR) * power(abs(UTR), 0.5)
    #   ~> regression_neut(_, turn20)
    #   ~> regression_neut(_, vwap)
    #   ~> regression_neut(_, ts_delta(mdl175_retainedearnings/sharesout, 120))
    signal = np.sign(UTR) * np.power(np.abs(UTR), 0.5)
    signal = regression_neut(signal, turn20)
    signal = regression_neut(signal, vwap_f)
    signal = regression_neut(signal, ts_delta_from_buffer(store.md_earnings_buffer))

    # Step 7: Pasteurize (platform handles neutralization=INDUSTRY, truncation, scale) (platform handles neutralization=INDUSTRY, truncation, scale)
    u = data.universe[-1].astype(bool)
    signal = pasteurize(signal, u)

    return signal.astype(np.float32)
