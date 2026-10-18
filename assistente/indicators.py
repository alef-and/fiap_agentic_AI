"""Ferramenta calculate_indicators: indicadores técnicos em pandas puro.

Todas as janelas olham apenas para trás: o valor em D depende só de dados
até D (sem lookahead), o que permite reutilizá-los no backtest.
"""

import pandas as pd

from . import config


def rsi(close: pd.Series, window: int = config.RSI_WINDOW) -> pd.Series:
    """RSI de Wilder (média móvel exponencial com alpha = 1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = gain / loss
    out = 100 - 100 / (1 + rs)
    # Sem perdas no período -> RSI 100; sem ganhos -> 0.
    out = out.where(loss != 0, 100.0).where(gain != 0, 0.0)
    return out.where(gain.notna())


def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Adiciona RSI, MACD, SMA/EMA, Bandas de Bollinger e métricas de volume.

    Espera colunas 'Close' e 'Volume'. Linhas iniciais ficam NaN até as
    janelas terem dados suficientes (período de aquecimento).
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("DataFrame de preços vazio.")
    missing = {"Close", "Volume"} - set(data.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")

    df = data.copy()
    close = df["Close"].astype(float)

    df["RSI"] = rsi(close)

    df["EMA_fast"] = close.ewm(span=config.EMA_FAST, adjust=False, min_periods=config.EMA_FAST).mean()
    df["EMA_slow"] = close.ewm(span=config.EMA_SLOW, adjust=False, min_periods=config.EMA_SLOW).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["MACD_signal"] = df["MACD"].ewm(span=config.MACD_SIGNAL, adjust=False,
                                       min_periods=config.MACD_SIGNAL).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    df["SMA_short"] = close.rolling(config.SMA_SHORT).mean()
    df["SMA_long"] = close.rolling(config.SMA_LONG).mean()

    mid = close.rolling(config.BB_WINDOW).mean()
    std = close.rolling(config.BB_WINDOW).std(ddof=0)
    df["BB_mid"] = mid
    df["BB_upper"] = mid + config.BB_STD * std
    df["BB_lower"] = mid - config.BB_STD * std
    df["BB_pctB"] = (close - df["BB_lower"]) / (df["BB_upper"] - df["BB_lower"])

    vol = df["Volume"].astype(float)
    df["Volume_avg"] = vol.rolling(config.VOLUME_WINDOW).mean()
    df["Volume_ratio"] = vol / df["Volume_avg"]
    df["Return_1d"] = close.pct_change()
    return df


INDICATOR_COLUMNS = ["RSI", "MACD", "MACD_signal", "MACD_hist", "SMA_short", "SMA_long",
                     "EMA_fast", "EMA_slow", "BB_upper", "BB_mid", "BB_lower", "BB_pctB",
                     "Volume_avg", "Volume_ratio"]


def snapshot(ind: pd.DataFrame, pos: int = -1) -> dict | None:
    """Extrai os valores do pregão `pos` (e do anterior, para cruzamentos).

    Retorna None se algum indicador essencial ainda estiver em aquecimento.
    """
    if len(ind) < 2:
        return None
    row, prev = ind.iloc[pos], ind.iloc[pos - 1]
    needed = ["Close", "RSI", "MACD", "MACD_signal", "SMA_short", "SMA_long", "BB_upper", "BB_lower"]
    if row[needed].isna().any() or pd.isna(prev["MACD"]) or pd.isna(prev["MACD_signal"]):
        return None
    snap = {"date": ind.index[pos].date().isoformat(), "close": float(row["Close"])}
    for c in INDICATOR_COLUMNS + ["Volume", "Return_1d"]:
        v = row.get(c)
        snap[c] = None if pd.isna(v) else float(v)
    snap["MACD_prev"] = float(prev["MACD"])
    snap["MACD_signal_prev"] = float(prev["MACD_signal"])
    return snap
