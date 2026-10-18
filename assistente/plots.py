"""Visualizações em matplotlib: preço/indicadores e curvas do backtest."""

import matplotlib.pyplot as plt
import pandas as pd

from . import config

C_PRICE, C_A, C_B, C_BAND, C_UP, C_DOWN = "#1f2937", "#2563eb", "#d97706", "#94a3b8", "#16a34a", "#dc2626"


def plot_indicators(ind: pd.DataFrame, ticker: str, last_n: int = 250):
    """Painel com preço + SMA/EMA + Bollinger, volume, RSI e MACD."""
    d = ind.tail(last_n)
    fig, ax = plt.subplots(4, 1, figsize=(12, 10), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1, 1, 1]})
    ax[0].fill_between(d.index, d["BB_lower"], d["BB_upper"], color=C_BAND, alpha=0.2, label="Bollinger")
    ax[0].plot(d.index, d["Close"], color=C_PRICE, lw=1.4, label="Fechamento")
    ax[0].plot(d.index, d["SMA_short"], color=C_A, lw=1, label=f"SMA{config.SMA_SHORT}")
    ax[0].plot(d.index, d["SMA_long"], color=C_B, lw=1, label=f"SMA{config.SMA_LONG}")
    ax[0].plot(d.index, d["EMA_fast"], color=C_A, lw=0.8, ls="--", label=f"EMA{config.EMA_FAST}")
    ax[0].set_title(f"{ticker}: preço e indicadores técnicos (últimos {len(d)} pregões)")
    ax[0].legend(loc="upper left", fontsize=8, ncol=5, frameon=False)

    colors = [C_UP if r >= 0 else C_DOWN for r in d["Return_1d"].fillna(0)]
    ax[1].bar(d.index, d["Volume"], color=colors, width=1.0)
    ax[1].plot(d.index, d["Volume_avg"], color=C_PRICE, lw=1, label=f"Média {config.VOLUME_WINDOW}d")
    ax[1].set_ylabel("Volume")
    ax[1].legend(loc="upper left", fontsize=8, frameon=False)

    ax[2].plot(d.index, d["RSI"], color=C_A, lw=1)
    ax[2].axhline(config.RSI_OVERBOUGHT, color=C_DOWN, lw=0.8, ls=":")
    ax[2].axhline(config.RSI_OVERSOLD, color=C_UP, lw=0.8, ls=":")
    ax[2].set_ylim(0, 100)
    ax[2].set_ylabel("RSI")

    ax[3].bar(d.index, d["MACD_hist"], color=[C_UP if h >= 0 else C_DOWN for h in d["MACD_hist"].fillna(0)],
              width=1.0, alpha=0.6)
    ax[3].plot(d.index, d["MACD"], color=C_A, lw=1, label="MACD")
    ax[3].plot(d.index, d["MACD_signal"], color=C_B, lw=1, label="Sinal")
    ax[3].set_ylabel("MACD")
    ax[3].legend(loc="upper left", fontsize=8, frameon=False)
    for a in ax:
        a.grid(alpha=0.2)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def plot_backtest(curve: pd.DataFrame, ticker: str):
    """Curvas de patrimônio (base 1) da estratégia e do Buy-and-Hold."""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(curve.index, curve["estrategia"], color=C_A, lw=1.4, label="Estratégia do agente (técnica)")
    ax.plot(curve.index, curve["buy_and_hold"], color=C_PRICE, lw=1.2, alpha=0.7, label="Buy-and-Hold")
    ax.fill_between(curve.index, 0, 1, where=curve["posicao"] > 0, transform=ax.get_xaxis_transform(),
                    color=C_A, alpha=0.06, label="Posição comprada")
    ax.axhline(1, color=C_BAND, lw=0.8)
    ax.set_title(f"{ticker}: backtest (custo {config.TRANSACTION_COST:.1%} por operação)")
    ax.set_ylabel("Patrimônio (base 1)")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig
