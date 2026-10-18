"""Tipos básicos das ferramentas do agente."""

from dataclasses import dataclass, field
from typing import Any, Callable

from . import config


@dataclass
class ToolResult:
    """Resultado padronizado: nenhuma ferramenta lança exceção para o agente."""

    ok: bool
    data: Any = None
    error: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def normalize_ticker(ticker: str) -> str:
    """Valida e normaliza o ticker (aceita 'petr4', 'PETR4.SA')."""
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker vazio ou inválido.")
    t = ticker.strip().upper().removesuffix(".SA")
    if t not in config.STOCKS:
        raise ValueError(f"Ticker '{ticker}' não monitorado. Use um de: {', '.join(config.STOCKS)}.")
    return t
