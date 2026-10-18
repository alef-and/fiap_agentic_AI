import pandas as pd
import pytest

from assistant import config
from assistant.evaluation import backtest, evaluate_ticker, trend_hit, walk_forward_decisions
from conftest import make_prices


def test_trend_hit_definitions():
    assert trend_hit("COMPRAR", 0.01) and not trend_hit("COMPRAR", -0.01)
    assert trend_hit("VENDER", -0.01) and not trend_hit("VENDER", 0.01)
    assert trend_hit("AGUARDAR", 0.01) and not trend_hit("AGUARDAR", 0.05)
    assert trend_hit("COMPRAR", float("nan")) is None


def test_decisions_do_not_use_future():
    """Decisões até D são idênticas com ou sem os dados posteriores a D."""
    p = make_prices(300, seed=5)
    full = walk_forward_decisions(p)
    part = walk_forward_decisions(p.iloc[:200])
    pd.testing.assert_frame_equal(full.loc[:part.index[-1]], part)


def test_metrics_exclude_last_horizon_days():
    m = evaluate_ticker(make_prices(300, seed=1))["metrics"]
    assert m["sem_horizonte_futuro"] == config.EVAL_HORIZON
    assert m["decisoes_avaliadas"] + m["sem_horizonte_futuro"] == m["decisoes_totais"]
    assert sum(v["n"] for v in m["por_recomendacao"].values()) == m["decisoes_avaliadas"]


def test_backtest_hand_example():
    idx = pd.bdate_range("2024-01-01", periods=4)
    close = pd.Series([10.0, 11.0, 12.1, 10.89], index=idx)
    dec = pd.DataFrame({"recommendation": ["COMPRAR", "AGUARDAR", "VENDER", "AGUARDAR"]}, index=idx)
    stats, curve = backtest(dec, close, cost=0.0)
    # comprado no fechamento de D0 -> ganha D1 (+10%) e D2 (+10%); vende em D2 -> fora em D3
    assert stats["retorno_estrategia"] == pytest.approx(0.21)
    assert stats["retorno_buy_and_hold"] == pytest.approx(0.089)
    assert list(curve["posicao"]) == [0, 1, 1, 0]
    stats_c, _ = backtest(dec, close, cost=0.01)
    assert stats_c["retorno_estrategia"] < stats["retorno_estrategia"] and stats_c["operacoes"] == 2


def test_insufficient_data():
    assert "erro" in evaluate_ticker(make_prices(40))
    assert "erro" in evaluate_ticker(None)
