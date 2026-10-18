"""Modo opcional: agente LangChain com LLM (OpenAI ou Google Gemini).

Isolado do fluxo principal. Requer `pip install -r requirements-llm.txt` e
OPENAI_API_KEY ou GOOGLE_API_KEY no ambiente (nunca no código). O LLM usa as
MESMAS ferramentas do agente determinístico; a recomendação continua vindo
das regras auditáveis — o LLM apenas escolhe ferramentas e redige a resposta
com base no que elas retornam. Qualquer falha devolve uma mensagem, sem
interromper o restante do notebook.
"""

import json
import os

from . import config
from .agent import InvestmentAgent
from .data import get_price_data as _get_price_data
from .indicators import calculate_indicators as _calc, snapshot
from .news import search_news as _search_news

PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "langchain_openai", "ChatOpenAI", "gpt-4o-mini"),
    "google": ("GOOGLE_API_KEY", "langchain_google_genai", "ChatGoogleGenerativeAI", "gemini-2.5-flash"),
}

SYSTEM_PROMPT = (
    "Você é um assistente de investimentos educacional para as ações VALE3, PETR4, BBAS3 e ITUB4. "
    "Use as ferramentas para obter dados; responda em português, de forma concisa, citando apenas "
    "valores, notícias e regras retornados pelas ferramentas. Nunca invente dados ou notícias. "
    "A recomendação oficial é a de generate_recommendation; não a altere. Apresente evidências e "
    "critérios, não um raciocínio interno passo a passo. Termine lembrando que não é aconselhamento "
    "financeiro e não há garantia de resultados."
)


class LLMUnavailable(RuntimeError):
    pass


def available_providers() -> list[str]:
    return [p for p, (env, *_rest) in PROVIDERS.items() if os.environ.get(env)]


def _make_model(provider: str):
    env, module, cls, default_model = PROVIDERS[provider]
    if not os.environ.get(env):
        raise LLMUnavailable(f"{env} não definida no ambiente deste processo.")
    try:
        mod = __import__(module, fromlist=[cls])
    except ImportError as e:
        raise LLMUnavailable(f"Pacote '{module}' não instalado (pip install -r requirements-llm.txt).") from e
    model_name = os.environ.get("LLM_MODEL", default_model)
    return getattr(mod, cls)(model=model_name, temperature=0)


def build_langchain_agent(records: dict | None = None, provider: str | None = None, period: str = "1y"):
    """Cria o agente LangChain com as ferramentas do projeto como StructuredTools."""
    try:
        from langchain.agents import create_agent
        from langchain_core.tools import tool
    except ImportError as e:
        raise LLMUnavailable("LangChain não instalado (pip install -r requirements-llm.txt).") from e

    provider = provider or next(iter(available_providers()), None)
    if provider not in PROVIDERS:
        raise LLMUnavailable("Nenhuma chave OPENAI_API_KEY/GOOGLE_API_KEY disponível neste processo.")
    model = _make_model(provider)
    records = records if records is not None else {}
    det_agent = InvestmentAgent(period=period)

    @tool
    def get_price_data(ticker: str, period: str = "1y") -> str:
        """Resumo dos preços diários (OHLCV) da ação B3 no período (ex.: '6mo', '1y', '2y')."""
        r = _get_price_data(ticker, period)
        if not r.ok:
            return f"ERRO: {r.error}"
        tail = r.data.tail(5).round(2).reset_index()
        tail["Date"] = tail["Date"].dt.date.astype(str)
        return json.dumps({"meta": r.meta, "ultimos_pregoes": tail.to_dict("records")}, ensure_ascii=False)

    @tool
    def calculate_indicators(ticker: str, period: str = "1y") -> str:
        """Indicadores técnicos do último pregão (RSI, MACD, SMA/EMA, Bollinger, volume)."""
        r = _get_price_data(ticker, period)
        if not r.ok:
            return f"ERRO: {r.error}"
        snap = snapshot(_calc(r.data))
        return json.dumps(snap, ensure_ascii=False) if snap else "Dados insuficientes para os indicadores."

    @tool
    def search_news(ticker: str) -> str:
        """Notícias RSS relacionadas à ação, com sentimento por notícia e score agregado."""
        r = _search_news(ticker)
        if r.data is None:
            return f"ERRO: {r.error}"
        items = [{k: it[k] for k in ("title", "source", "published", "label", "score")} for it in r.data["items"]]
        return json.dumps({"resumo": r.data["summary"], "sentimento": r.data["sentiment"], "itens": items,
                           "fontes_com_falha": r.data["sources_failed"]}, ensure_ascii=False)

    @tool
    def generate_recommendation(ticker: str) -> str:
        """Recomendação oficial (COMPRAR/VENDER/AGUARDAR) com sinais, justificativa e limitações."""
        t = ticker.strip().upper().removesuffix(".SA")
        rec = records.get(t) or det_agent.run(t)
        keys = ("ticker", "date", "recommendation", "score", "signals", "justification",
                "news_summary", "limitations", "data_used")
        return json.dumps({k: rec[k] for k in keys}, ensure_ascii=False, default=str)

    tools = [get_price_data, calculate_indicators, search_news, generate_recommendation]
    return create_agent(model, tools, system_prompt=SYSTEM_PROMPT), provider


def _text(content) -> str:
    if isinstance(content, list):  # Gemini pode devolver blocos
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


def ask_llm(question: str, records: dict | None = None, provider: str | None = None) -> str:
    """Pergunta ao agente LLM. Nunca lança exceção: devolve a resposta ou o motivo da falha."""
    try:
        agent, used = build_langchain_agent(records, provider)
        out = agent.invoke({"messages": [{"role": "user", "content": question}]})
        msgs = out["messages"]
        calls = [tc["name"] for m in msgs for tc in (getattr(m, "tool_calls", None) or [])]
        return (f"[{used}] ferramentas usadas: {', '.join(calls) or 'nenhuma'}\n"
                f"{_text(msgs[-1].content)}")
    except LLMUnavailable as e:
        return f"Modo LLM indisponível: {e} O fluxo principal (sem chaves) não é afetado."
    except Exception as e:
        return f"Falha na chamada ao LLM ({type(e).__name__}: {str(e)[:200]}). {config.DISCLAIMER}"
