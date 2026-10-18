import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assistant import data, news  # noqa: E402


def make_prices(n=300, seed=0, drift=0.0005):
    """Série OHLCV sintética e reprodutível (passeio aleatório geométrico)."""
    rng = np.random.default_rng(seed)
    close = 30 * np.exp(np.cumsum(rng.normal(drift, 0.015, n)))
    idx = pd.bdate_range("2023-01-02", periods=n, name="Date")
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                         "Volume": rng.integers(1_000_000, 3_000_000, n).astype(float)}, index=idx)


@pytest.fixture
def prices():
    return make_prices()


@pytest.fixture(autouse=True)
def _clear_caches():
    data.clear_cache()
    news.clear_cache()
    yield
