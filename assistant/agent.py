"""Agente de investimentos: orquestra as ferramentas em um ciclo ação -> observação.

O ciclo segue o padrão ReAct (agir com uma ferramenta, observar o resultado,
decidir o próximo passo), mas o registro guarda apenas passos executados,
entradas, resultados observáveis e regras acionadas — não um "raciocínio
interno" simulado.
"""

import json
from datetime import datetime
from pathlib import Path

from . import config
from .data import get_price_data
from .indicators import calculate_indicators, snapshot
from .news import search_news
from .recommendation import generate_recommendation
from .tools import Tool, normalize_ticker

TOOLS = {
    "search_news": Tool("search_news", "search_news(ticker): notícias RSS relacionadas à ação, "
                        "com sentimento por notícia e score agregado.", search_news),
    "get_price_data": Tool("get_price_data", "get_price_data(ticker, period): OHLCV diário ajustado "
                           "via yfinance (ticker B3, ex.: PETR4; period ex.: '1y', '2y').", get_price_data),
    "calculate_indicators": Tool("calculate_indicators", "calculate_indicators(data): RSI, MACD/sinal, "
                                 "SMA/EMA, Bandas de Bollinger e volume.", calculate_indicators),
    "generate_recommendation": Tool("generate_recommendation", "generate_recommendation(analysis): "
                                    "COMPRAR/VENDER/AGUARDAR com sinais, justificativa e limitações.",
                                    generate_recommendation),
}


class InvestmentAgent:
    """Executa o fluxo completo por ação e mantém os registros consultáveis."""

    def __init__(self, period: str = config.DEFAULT_PERIOD, use_news: bool = True, tools: dict | None = None):
        if period not in config.VALID_PERIODS:
            raise ValueError(f"Período inválido: {period}")
        self.period = period
        self.use_news = use_news
        self.tools = {**TOOLS, **(tools or {})}
        self.records: dict[str, dict] = {}

    def _call(self, trace, name, entrada, *args, **kwargs):
        """Chama a ferramenta, captura exceções e registra o passo."""
        try:
            out = self.tools[name](*args, **kwargs)
            err = getattr(out, "error", None) if hasattr(out, "ok") and not out.ok else None
        except Exception as e:
            out, err = None, f"{type(e).__name__}: {e}"
        trace.append({"passo": len(trace) + 1, "ferramenta": name, "entrada": entrada,
                      "resultado": err or "ok"})
        return out, err

    def run(self, ticker: str) -> dict:
        t = normalize_ticker(ticker)
        trace, extra_lim, snap, news_data, data_used = [], [], None, None, {"periodo": self.period}

        prices, err = self._call(trace, "get_price_data", f"{t}, {self.period}", t, self.period)
        if err:
            extra_lim.append(f"Preços indisponíveis: {err}")
        else:
            data_used.update({"fonte_precos": prices.meta.get("source"), "pregoes": prices.meta.get("rows"),
                              "inicio": prices.meta.get("start"), "fim": prices.meta.get("end")})
            ind, err = self._call(trace, "calculate_indicators", f"DataFrame({len(prices.data)} pregões)",
                                  prices.data)
            if not err:
                snap = snapshot(ind)
                if snap is None:
                    trace[-1]["resultado"] = "indicadores em aquecimento (dados insuficientes)"
                    extra_lim.append(f"Histórico curto: são necessários ~{config.MIN_ROWS} pregões.")
                else:
                    trace[-1]["resultado"] = (f"RSI={snap['RSI']:.1f}, MACD={snap['MACD']:.3f}, "
                                              f"sinal={snap['MACD_signal']:.3f}")

        if self.use_news:
            news, err = self._call(trace, "search_news", t, t)
            if news is not None and news.data:
                news_data = news.data
                data_used["fontes_noticias_ok"] = news_data["sources_ok"]
                data_used["fontes_noticias_falha"] = list(news_data["sources_failed"])
                trace[-1]["resultado"] = (err + "; " if err else "") + (
                    f"{len(news_data['items'])} notícias, sentimento={news_data['sentiment']}")
            if err:
                extra_lim.append(f"Notícias: {err}")
        else:
            extra_lim.append("Busca de notícias desativada nesta execução.")

        analysis = {"ticker": t, "indicators": snap, "news": news_data, "extra_limitations": extra_lim}
        rec, err = self._call(trace, "generate_recommendation", "analysis(indicadores + notícias)", analysis)
        if err:  # não deveria ocorrer; mantém o fluxo com resultado conservador
            rec = {"recommendation": "AGUARDAR", "score": 0.0, "signals": [],
                   "justification": f"Falha ao gerar recomendação ({err}).", "limitations": extra_lim}
        else:
            trace[-1]["resultado"] = f"{rec['recommendation']} (score {rec['score']:+.2f})"

        record = {
            "ticker": t,
            "empresa": config.STOCKS[t]["empresa"],
            "date": snap["date"] if snap else data_used.get("fim"),
            "close": round(snap["close"], 2) if snap else None,
            "rsi": round(snap["RSI"], 1) if snap else None,
            "macd_signal": (("bullish" if snap["MACD"] > snap["MACD_signal"] else "bearish") if snap else None),
            "news_sentiment": news_data["sentiment"] if news_data else None,
            "recommendation": rec["recommendation"],
            "score": rec["score"],
            "signals": rec["signals"],
            "indicators": ({k: (round(v, 4) if isinstance(v, float) else v) for k, v in snap.items()}
                           if snap else None),
            "news_summary": news_data["summary"] if news_data else "Notícias não consultadas/indisponíveis.",
            "news_items": [{k: it[k] for k in ("source", "title", "link", "published", "label", "score", "terms")}
                           for it in (news_data or {}).get("items", [])],
            "justification": rec["justification"],
            "limitations": rec["limitations"],
            "data_used": data_used,
            "trace": trace,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": config.DISCLAIMER,
        }
        self.records[t] = record
        return record

    def run_all(self, tickers=None) -> dict[str, dict]:
        for t in tickers or config.STOCKS:
            self.run(t)
        return self.records

    def save(self, path="recomendacoes.json") -> str:
        p = Path(path)
        p.write_text(json.dumps(self.records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return str(p.resolve())

    @staticmethod
    def load(path="recomendacoes.json") -> dict[str, dict]:
        return json.loads(Path(path).read_text(encoding="utf-8"))
