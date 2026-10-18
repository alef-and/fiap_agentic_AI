import pytest

from assistente.agent import InvestmentAgent
from assistente.chat import answer
from assistente.data import get_price_data
from assistente.recommendation import decide, generate_recommendation
from assistente.tools import Tool, ToolResult
from conftest import make_prices

BASE = {"date": "2026-10-16", "close": 10.0, "RSI": 25.0, "MACD": 0.2, "MACD_signal": 0.1,
        "MACD_prev": 0.05, "MACD_signal_prev": 0.1, "SMA_short": 9.8, "SMA_long": 9.5,
        "BB_upper": 11.0, "BB_lower": 9.0, "Volume_ratio": 1.0, "Return_1d": 0.01}
NO_NEWS = ToolResult(True, {"items": [], "sentiment": None, "summary": "Nenhuma notícia",
                            "sources_ok": ["M"], "sources_failed": {}})


def _agent(price_fn, news_fn):
    return InvestmentAgent(tools={"get_price_data": Tool("get_price_data", "", price_fn),
                                  "search_news": Tool("search_news", "", news_fn)})


def _ok_prices(n=200):
    p = make_prices(n)
    return lambda t, per: ToolResult(True, p, meta={"source": "mock", "rows": n})


def test_decide_thresholds():
    assert decide(2.0) == "COMPRAR" and decide(-2.0) == "VENDER" and decide(1.99) == "AGUARDAR"


def test_bullish_snapshot_buys():
    r = generate_recommendation({"indicators": BASE, "news": None})
    assert r["recommendation"] == "COMPRAR" and r["score"] >= 2
    assert any("sobrevendido" in s["descricao"] for s in r["signals"])
    assert any("apenas técnica" in x for x in r["limitations"])


def test_bearish_snapshot_sells():
    bear = {**BASE, "RSI": 80.0, "MACD": -0.2, "MACD_prev": 0.2, "MACD_signal_prev": 0.1,
            "SMA_short": 9.0, "SMA_long": 10.5}
    assert generate_recommendation({"indicators": bear})["recommendation"] == "VENDER"


def test_news_weight_applies_only_with_enough_items():
    neutral = {**BASE, "RSI": 50.0}
    s0 = generate_recommendation({"indicators": neutral})["score"]
    s1 = generate_recommendation({"indicators": neutral, "news": {
        "sentiment": 0.9, "items": [{}], "label": "positivo"}})["score"]
    s3 = generate_recommendation({"indicators": neutral, "news": {
        "sentiment": -0.9, "items": [{}] * 3, "label": "negativo", "impact": 0.3}})["score"]
    assert s1 == s0 and s3 == pytest.approx(s0 - 0.9)


def test_missing_indicators_waits():
    r = generate_recommendation({"indicators": None})
    assert r["recommendation"] == "AGUARDAR" and r["signals"] == []


def test_agent_full_flow_offline():
    recs = _agent(_ok_prices(), lambda t: NO_NEWS).run_all()
    assert set(recs) == {"VALE3", "PETR4", "BBAS3", "ITUB4"}
    r = recs["PETR4"]
    assert [s["ferramenta"] for s in r["trace"]] == ["get_price_data", "calculate_indicators",
                                                     "search_news", "generate_recommendation"]
    for k in ("ticker", "date", "close", "rsi", "macd_signal", "news_sentiment", "recommendation",
              "justification", "limitations", "data_used"):
        assert k in r
    assert r["recommendation"] in {"COMPRAR", "VENDER", "AGUARDAR"}


def test_agent_handles_price_and_news_failures(tmp_path):
    a = _agent(lambda t, p: ToolResult(False, error="sem rede"), lambda t: ToolResult(False, error="feeds fora"))
    r = a.run("VALE3")
    assert r["recommendation"] == "AGUARDAR" and r["close"] is None
    assert any("sem rede" in x for x in r["limitations"])
    assert InvestmentAgent.load(a.save(tmp_path / "r.json"))["VALE3"]["recommendation"] == "AGUARDAR"


def test_agent_tool_exception_does_not_crash():
    def boom(t):
        raise RuntimeError("falhou")
    r = _agent(_ok_prices(), boom).run("ITUB4")
    assert r["trace"][2]["resultado"].startswith("RuntimeError")
    assert r["recommendation"] in {"COMPRAR", "VENDER", "AGUARDAR"}


def test_short_history_waits():
    r = _agent(_ok_prices(30), lambda t: NO_NEWS).run("BBAS3")
    assert r["recommendation"] == "AGUARDAR" and "aquecimento" in r["trace"][1]["resultado"]


def test_chat_answers_from_records():
    a = _agent(_ok_prices(), lambda t: NO_NEWS)
    a.run("PETR4")
    assert "PETR4" in answer("Por que você recomendou comprar PETR4 hoje?", a.records)
    assert "RSI=" in answer("Como está o RSI da Petrobras?", a.records)
    assert "Nenhuma notícia" in answer("Quais notícias de PETR4?", a.records)
    assert "Ainda não há" in answer("E a VALE3?", a.records)
    assert "Não identifiquei" in answer("E a bolsa?", a.records)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        InvestmentAgent(period="7d")
    with pytest.raises(ValueError):
        InvestmentAgent().run("XPTO3")
    assert not get_price_data("PETR4", "3d").ok and not get_price_data("ABC").ok
