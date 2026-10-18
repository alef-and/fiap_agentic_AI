import numpy as np
import pandas as pd
import pytest

from assistant.indicators import calculate_indicators, rsi, snapshot
from conftest import make_prices


def test_columns_and_ranges(prices):
    ind = calculate_indicators(prices)
    for c in ["RSI", "MACD", "MACD_signal", "SMA_short", "SMA_long", "EMA_fast", "BB_upper", "BB_lower",
              "Volume_ratio"]:
        assert c in ind
    assert ind["RSI"].dropna().between(0, 100).all()
    valid = ind.dropna(subset=["BB_upper"])
    assert (valid["BB_upper"] >= valid["BB_mid"]).all() and (valid["BB_mid"] >= valid["BB_lower"]).all()


def test_sma_matches_manual(prices):
    ind = calculate_indicators(prices)
    assert ind["SMA_short"].iloc[-1] == pytest.approx(prices["Close"].iloc[-20:].mean())


def test_rsi_extremes():
    up = pd.Series(np.arange(1, 40, dtype=float))
    assert rsi(up).iloc[-1] == 100
    assert rsi(up[::-1].reset_index(drop=True)).iloc[-1] == 0


def test_no_lookahead():
    """Truncar a série no dia D não altera nenhum indicador até D."""
    p = make_prices(300, seed=3)
    full = calculate_indicators(p)
    for cut in (80, 150, 299):
        pd.testing.assert_frame_equal(full.iloc[:cut], calculate_indicators(p.iloc[:cut]))


def test_snapshot_warmup_and_validation():
    assert snapshot(calculate_indicators(make_prices(30))) is None
    with pytest.raises(ValueError):
        calculate_indicators(pd.DataFrame())
    with pytest.raises(ValueError):
        calculate_indicators(pd.DataFrame({"Close": [1.0]}))
