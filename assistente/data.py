"""Ferramenta get_price_data: preços e volumes diários via yfinance."""

import logging
import time

import pandas as pd

from . import config
from .tools import ToolResult, normalize_ticker

log = logging.getLogger(__name__)
_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
REQUIRED = ["Open", "High", "Low", "Close", "Volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Achata MultiIndex do yfinance, remove timezone e linhas sem fechamento."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"colunas ausentes: {missing}")
    df = df[REQUIRED].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["Close"])


def _download(symbol: str, period: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True,
                                     timeout=config.HTTP_TIMEOUT)


def get_price_data(ticker: str, period: str = config.DEFAULT_PERIOD,
                   retries: int = 2, use_cache: bool = True) -> ToolResult:
    """Baixa OHLCV diário ajustado da ação na B3.

    Retorna ToolResult(ok=False, error=...) em caso de ticker inválido, falha
    de rede ou resposta vazia; nunca fabrica dados.
    """
    try:
        t = normalize_ticker(ticker)
    except ValueError as e:
        return ToolResult(False, error=str(e))
    if period not in config.VALID_PERIODS:
        return ToolResult(False, error=f"Período '{period}' inválido. Use: {sorted(config.VALID_PERIODS)}.")

    key = (t, period)
    if use_cache and key in _CACHE:
        df = _CACHE[key]
        return ToolResult(True, df.copy(), meta=_meta(t, period, df, cached=True))

    symbol = config.STOCKS[t]["yahoo"]
    last_error = "resposta vazia"
    for attempt in range(retries + 1):
        try:
            raw = _download(symbol, period)
            if raw is None or raw.empty:
                last_error = "yfinance retornou dados vazios"
            else:
                df = _normalize(raw)
                if df.empty:
                    last_error = "sem fechamentos válidos"
                else:
                    _CACHE[key] = df
                    return ToolResult(True, df.copy(), meta=_meta(t, period, df))
        except Exception as e:  # rede, limite de requisições, formato inesperado
            last_error = f"{type(e).__name__}: {e}"
            log.warning("get_price_data(%s) tentativa %d falhou: %s", t, attempt + 1, last_error)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return ToolResult(False, error=f"Preços de {t} indisponíveis ({last_error}).",
                      meta={"ticker": t, "symbol": symbol, "period": period})


def _meta(t, period, df, cached=False):
    return {"ticker": t, "symbol": config.STOCKS[t]["yahoo"], "period": period,
            "rows": len(df), "start": df.index[0].date().isoformat(),
            "end": df.index[-1].date().isoformat(), "source": "Yahoo Finance (yfinance)",
            "cached": cached}


def clear_cache():
    _CACHE.clear()
