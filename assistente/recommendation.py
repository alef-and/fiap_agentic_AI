"""Ferramenta generate_recommendation: regras pontuadas e auditáveis.

Cada regra acionada vira um "sinal" com o valor observado e sua contribuição
para o score. Score >= BUY_THRESHOLD -> COMPRAR; <= SELL_THRESHOLD -> VENDER;
caso contrário AGUARDAR. Os mesmos sinais técnicos são usados no backtest.
"""

from . import config

BASE_LIMITATIONS = [
    "Regras e limiares heurísticos, não otimizados nem validados estatisticamente.",
    "Indicadores técnicos refletem apenas o histórico de preços/volume; não antecipam eventos.",
    "Sentimento por léxico: não capta ironia, contexto ou quem é afetado pela notícia.",
]


def _sig(rule, value, contrib, text):
    return {"regra": rule, "valor": value, "contribuicao": round(contrib, 2), "descricao": text}


def technical_signals(s: dict) -> list[dict]:
    """Sinais técnicos a partir de um snapshot de indicadores (ver indicators.snapshot)."""
    sigs = []
    rsi = s["RSI"]
    if rsi < config.RSI_OVERSOLD:
        sigs.append(_sig("RSI", round(rsi, 1), +1.0, f"RSI {rsi:.1f} < {config.RSI_OVERSOLD} (sobrevendido)"))
    elif rsi > config.RSI_OVERBOUGHT:
        sigs.append(_sig("RSI", round(rsi, 1), -1.0, f"RSI {rsi:.1f} > {config.RSI_OVERBOUGHT} (sobrecomprado)"))
    else:
        sigs.append(_sig("RSI", round(rsi, 1), 0.0, f"RSI {rsi:.1f} em zona neutra"))

    macd, sig, pm, ps = s["MACD"], s["MACD_signal"], s["MACD_prev"], s["MACD_signal_prev"]
    vals = {"macd": round(macd, 4), "sinal": round(sig, 4)}
    if pm <= ps and macd > sig:
        sigs.append(_sig("MACD", vals, +1.5, "MACD cruzou acima da linha de sinal (cruzamento de alta)"))
    elif pm >= ps and macd < sig:
        sigs.append(_sig("MACD", vals, -1.5, "MACD cruzou abaixo da linha de sinal (cruzamento de baixa)"))
    elif macd > sig:
        sigs.append(_sig("MACD", vals, +0.5, "MACD acima da linha de sinal"))
    else:
        sigs.append(_sig("MACD", vals, -0.5, "MACD abaixo da linha de sinal"))

    close, sl, ss = s["close"], s["SMA_long"], s["SMA_short"]
    if close > sl:
        sigs.append(_sig("Preço vs SMA_long", {"close": round(close, 2), "sma": round(sl, 2)}, +0.5,
                         f"Fechamento acima da SMA{config.SMA_LONG}"))
    else:
        sigs.append(_sig("Preço vs SMA_long", {"close": round(close, 2), "sma": round(sl, 2)}, -0.5,
                         f"Fechamento abaixo da SMA{config.SMA_LONG}"))
    if ss > sl:
        sigs.append(_sig("SMA_short vs SMA_long", {"curta": round(ss, 2), "longa": round(sl, 2)}, +1.0,
                         f"SMA{config.SMA_SHORT} acima da SMA{config.SMA_LONG} (tendência de alta)"))
    else:
        sigs.append(_sig("SMA_short vs SMA_long", {"curta": round(ss, 2), "longa": round(sl, 2)}, -1.0,
                         f"SMA{config.SMA_SHORT} abaixo da SMA{config.SMA_LONG} (tendência de baixa)"))

    bb = {"close": round(close, 2), "inferior": round(s["BB_lower"], 2), "superior": round(s["BB_upper"], 2)}
    if close < s["BB_lower"]:
        sigs.append(_sig("Bollinger", bb, +0.5, "Fechamento abaixo da banda inferior (esticado para baixo)"))
    elif close > s["BB_upper"]:
        sigs.append(_sig("Bollinger", bb, -0.5, "Fechamento acima da banda superior (esticado para cima)"))

    vr, r1 = s.get("Volume_ratio"), s.get("Return_1d")
    if vr is not None and r1 is not None and vr >= config.VOLUME_SPIKE:
        c = 0.5 if r1 > 0 else -0.5 if r1 < 0 else 0.0
        sigs.append(_sig("Volume", {"razao_media": round(vr, 2), "retorno_dia": round(r1, 4)}, c,
                         f"Volume {vr:.1f}x a média confirma movimento de {r1:+.2%} no dia"))
    return sigs


def news_signal(news: dict | None) -> dict | None:
    """Sinal de sentimento, se houver notícias relacionadas suficientes."""
    if not news or news.get("sentiment") is None:
        return None
    n = len(news.get("items", []))
    if n < config.NEWS_MIN_ITEMS:
        return _sig("Notícias", {"sentimento": news["sentiment"], "n": n}, 0.0,
                    f"Apenas {n} notícia(s) relacionada(s); sentimento não pontuado")
    c = news["sentiment"] * config.NEWS_WEIGHT
    return _sig("Notícias", {"sentimento": news["sentiment"], "impacto": news.get("impact"), "n": n}, c,
                f"Sentimento agregado {news['sentiment']:+.2f} em {n} notícias ({news.get('label')})")


def decide(score: float) -> str:
    if score >= config.BUY_THRESHOLD:
        return "COMPRAR"
    if score <= config.SELL_THRESHOLD:
        return "VENDER"
    return "AGUARDAR"


def generate_recommendation(analysis: dict) -> dict:
    """Gera a recomendação a partir de {'ticker', 'indicators': snapshot|None, 'news': dict|None}."""
    if not isinstance(analysis, dict):
        raise ValueError("analysis deve ser um dicionário.")
    snap, news = analysis.get("indicators"), analysis.get("news")
    limitations = list(BASE_LIMITATIONS) + list(analysis.get("extra_limitations", []))

    if not snap:
        return {"recommendation": "AGUARDAR", "score": 0.0, "signals": [],
                "justification": "Dados de preço/indicadores insuficientes ou indisponíveis; "
                                 "sem base para recomendar compra ou venda.",
                "limitations": limitations + ["Recomendação sem evidência técnica."]}

    signals = technical_signals(snap)
    ns = news_signal(news)
    if ns:
        signals.append(ns)
    else:
        limitations.append("Sem notícias relacionadas disponíveis: decisão apenas técnica.")
    score = round(sum(s["contribuicao"] for s in signals), 2)
    rec = decide(score)

    drivers = sorted((s for s in signals if s["contribuicao"]), key=lambda s: -abs(s["contribuicao"]))
    pro = [s["descricao"] for s in drivers if s["contribuicao"] > 0][:3]
    con = [s["descricao"] for s in drivers if s["contribuicao"] < 0][:3]
    parts = [f"{rec} com score {score:+.2f} (limiares: COMPRAR >= {config.BUY_THRESHOLD:+.1f}, "
             f"VENDER <= {config.SELL_THRESHOLD:+.1f})."]
    if pro:
        parts.append("A favor de alta: " + "; ".join(pro) + ".")
    if con:
        parts.append("A favor de baixa: " + "; ".join(con) + ".")
    return {"recommendation": rec, "score": score, "signals": signals,
            "justification": " ".join(parts), "limitations": limitations}
