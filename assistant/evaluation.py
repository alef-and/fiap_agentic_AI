"""Avaliação histórica (walk-forward) e backtest das regras técnicas.

Definições:
- Decisão em D: usa só indicadores com dados até o fechamento de D. Os
  indicadores são causais (janelas para trás), então calculá-los uma vez na
  série inteira dá o mesmo valor que recalcular truncando em D (testado).
- Notícias não entram: os feeds RSS não oferecem histórico confiável, logo a
  avaliação mede apenas o componente técnico do agente.
- Acerto de tendência (horizonte H = config.EVAL_HORIZON pregões), com
  r = Close[D+H] / Close[D] - 1:
    COMPRAR acerta se r > 0; VENDER acerta se r < 0;
    AGUARDAR acerta se |r| < config.HOLD_BAND.
  Decisões sem D+H disponível não são avaliadas (contadas à parte);
  pregões em aquecimento dos indicadores não geram decisão.
- Backtest long-only: COMPRAR -> comprado; VENDER -> zerado; AGUARDAR mantém
  a posição anterior. A posição decidida em D rende a partir do retorno de
  D+1 (executa no fechamento de D, sem usar o futuro). Custo
  config.TRANSACTION_COST por mudança de posição. Comparado ao Buy-and-Hold
  no mesmo intervalo (com custo de entrada).
"""

import numpy as np
import pandas as pd

from . import config
from .indicators import calculate_indicators, snapshot
from .recommendation import decide, technical_signals

LABELS = ("COMPRAR", "VENDER", "AGUARDAR")


def walk_forward_decisions(prices: pd.DataFrame) -> pd.DataFrame:
    """Uma decisão técnica por pregão, usando apenas dados até aquele pregão."""
    ind = calculate_indicators(prices)
    rows = []
    for i in range(1, len(ind)):
        snap = snapshot(ind, i)
        if snap is None:
            continue
        score = sum(s["contribuicao"] for s in technical_signals(snap))
        rows.append({"date": ind.index[i], "close": snap["close"], "score": round(score, 2),
                     "recommendation": decide(score)})
    if not rows:
        return pd.DataFrame(columns=["close", "score", "recommendation"])
    return pd.DataFrame(rows).set_index("date")


def trend_hit(rec: str, fwd_return: float) -> bool | None:
    if fwd_return is None or np.isnan(fwd_return):
        return None
    if rec == "COMPRAR":
        return fwd_return > 0
    if rec == "VENDER":
        return fwd_return < 0
    return abs(fwd_return) < config.HOLD_BAND


def accuracy_metrics(decisions: pd.DataFrame, close: pd.Series, horizon: int = config.EVAL_HORIZON) -> tuple:
    d = decisions.copy()
    fwd = close.shift(-horizon) / close - 1  # só usado para AVALIAR, nunca para decidir
    d["fwd_return"] = fwd.reindex(d.index)
    d["hit"] = [trend_hit(r, x) for r, x in zip(d["recommendation"], d["fwd_return"])]
    ev = d[d["hit"].notna()]
    per = {}
    for lab in LABELS:
        sub = ev[ev["recommendation"] == lab]
        per[lab] = {"n": int(len(sub)), "acuracia": float(sub["hit"].mean()) if len(sub) else None}
    directional = ev[ev["recommendation"] != "AGUARDAR"]
    up_rate = float((ev["fwd_return"] > 0).mean()) if len(ev) else None
    metrics = {
        "horizonte_pregoes": horizon,
        "decisoes_totais": int(len(d)),
        "decisoes_avaliadas": int(len(ev)),
        "sem_horizonte_futuro": int(d["hit"].isna().sum()),
        "acuracia_geral": float(ev["hit"].mean()) if len(ev) else None,
        "acuracia_direcional_sem_aguardar": float(directional["hit"].mean()) if len(directional) else None,
        "taxa_base_alta": up_rate,  # referência: % de janelas com retorno > 0
        "por_recomendacao": per,
    }
    return metrics, d


def backtest(decisions: pd.DataFrame, close: pd.Series, cost: float = config.TRANSACTION_COST) -> tuple:
    """Curva de patrimônio da estratégia long-only vs Buy-and-Hold."""
    if decisions.empty:
        raise ValueError("Sem decisões para o backtest.")
    c = close.loc[decisions.index[0]:]
    pos, cur = [], 0
    recs = decisions["recommendation"].reindex(c.index)
    for r in recs:
        if r == "COMPRAR":
            cur = 1
        elif r == "VENDER":
            cur = 0
        pos.append(cur)  # AGUARDAR (ou sem decisão) mantém
    pos = pd.Series(pos, index=c.index, dtype=float)
    held = pos.shift(1).fillna(0)  # posição decidida em D vale para o retorno de D+1
    ret = c.pct_change().fillna(0)
    trades = held.diff().abs().fillna(held.iloc[0])
    strat = (1 + held * ret - trades * cost).cumprod()
    bh = (1 + ret).cumprod() * (1 - cost)
    curve = pd.DataFrame({"estrategia": strat, "buy_and_hold": bh, "posicao": held})

    def mdd(s):
        return float((s / s.cummax() - 1).min())

    stats = {"inicio": c.index[0].date().isoformat(), "fim": c.index[-1].date().isoformat(),
             "retorno_estrategia": float(strat.iloc[-1] - 1), "retorno_buy_and_hold": float(bh.iloc[-1] - 1),
             "max_drawdown_estrategia": mdd(strat), "max_drawdown_buy_and_hold": mdd(bh),
             "operacoes": int((trades > 0).sum()), "exposicao_media": float(held.mean()),
             "custo_por_operacao": cost}
    return stats, curve


def evaluate_ticker(prices: pd.DataFrame, horizon: int = config.EVAL_HORIZON) -> dict:
    """Executa decisões walk-forward, métricas de acerto e backtest para uma ação."""
    if prices is None or len(prices) < config.MIN_ROWS + horizon:
        n = 0 if prices is None else len(prices)
        return {"erro": f"Dados insuficientes para avaliação ({n} pregões; mínimo {config.MIN_ROWS + horizon})."}
    decisions = walk_forward_decisions(prices)
    if decisions.empty:
        return {"erro": "Nenhuma decisão gerada (indicadores em aquecimento)."}
    metrics, detail = accuracy_metrics(decisions, prices["Close"], horizon)
    bt, curve = backtest(decisions, prices["Close"])
    return {"metrics": metrics, "backtest": bt, "decisions": detail, "curve": curve}
