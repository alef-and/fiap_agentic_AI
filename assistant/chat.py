"""Interface conversacional baseada apenas nos registros do agente.

Identifica a ação e a intenção da pergunta por palavras-chave e responde com
os campos registrados (sinais, notícias, justificativa, limitações). Não
consulta dados novos nem inventa informações.
"""

from . import config
from .sentiment import _norm

INTENTS = {
    "noticias": ["noticia", "sentimento", "manchete", "news"],
    "indicadores": ["rsi", "macd", "indicador", "media", "sma", "ema", "bollinger", "volume", "tecnic"],
    "limitacoes": ["limitac", "risco", "confiavel", "confianca", "garant"],
    "dados": ["dado", "fonte", "periodo", "pregao"],
    "porque": ["por que", "porque", "motivo", "justific", "explica", "razao"],
}


def find_ticker(question: str) -> str | None:
    q = _norm(question)
    for t, info in config.STOCKS.items():
        names = [t, info["empresa"]] + info["aliases"] + (["vale"] if t == "VALE3" else [])
        if any(_norm(n).strip() in q for n in names):
            return t
    return None


def detect_intent(question: str) -> str:
    q = _norm(question)
    for intent, keys in INTENTS.items():
        if any(k in q for k in keys):
            return intent
    return "resumo"


def _signals_text(r):
    return "\n".join(f"  - {s['descricao']} (contribuição {s['contribuicao']:+.2f})" for s in r["signals"]) \
        or "  - nenhum sinal registrado"


def answer(question: str, records: dict) -> str:
    """Responde a uma pergunta sobre as recomendações registradas."""
    if not question or not question.strip():
        return "Faça uma pergunta citando uma das ações: " + ", ".join(config.STOCKS) + "."
    t = find_ticker(question)
    if t is None:
        return "Não identifiquei a ação. Ações monitoradas: " + ", ".join(config.STOCKS) + "."
    r = records.get(t)
    if not r:
        return f"Ainda não há recomendação registrada para {t}. Execute o agente primeiro."

    head = f"{t} ({r['date']}): recomendação {r['recommendation']} (score {r['score']:+.2f})."
    intent = detect_intent(question)
    if intent == "noticias":
        body = "Notícias consideradas:\n" + r["news_summary"]
    elif intent == "indicadores":
        ind = r.get("indicators") or {}
        if not ind:
            body = "Indicadores indisponíveis para esta data."
        else:
            body = (f"RSI={ind['RSI']:.1f}; MACD={ind['MACD']:.3f} vs sinal={ind['MACD_signal']:.3f} "
                    f"({r['macd_signal']}); SMA{config.SMA_SHORT}={ind['SMA_short']:.2f}, "
                    f"SMA{config.SMA_LONG}={ind['SMA_long']:.2f}; Bollinger [{ind['BB_lower']:.2f}, "
                    f"{ind['BB_upper']:.2f}]; fechamento {ind['close']:.2f}.\nSinais:\n" + _signals_text(r))
    elif intent == "limitacoes":
        body = "Limitações:\n" + "\n".join(f"  - {x}" for x in r["limitations"])
    elif intent == "dados":
        body = "Dados utilizados: " + ", ".join(f"{k}={v}" for k, v in r["data_used"].items())
    elif intent == "porque":
        body = r["justification"] + "\nSinais que contribuíram:\n" + _signals_text(r)
    else:
        body = r["justification"]
    return f"{head}\n{body}\n({config.DISCLAIMER})"
