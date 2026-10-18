"""Ferramenta search_news: notícias RSS relacionadas à ação, com sentimento.

Somente títulos, resumos, fontes, links e datas presentes nos feeds são
usados; o resumo é extrativo (lista as manchetes reais), sem texto gerado.
"""

import html
import logging
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import config
from .sentiment import _norm, classify
from .tools import ToolResult, normalize_ticker

log = logging.getLogger(__name__)
_FEED_CACHE: dict[str, tuple[float, list]] = {}
FEED_TTL = 15 * 60  # segundos


def _fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
        return resp.read()


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _published(entry) -> datetime | None:
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if not st:
        return None
    try:
        return datetime(*st[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def fetch_feed(name: str, url: str, fetch=_fetch_url) -> list[dict]:
    """Lê um feed RSS e devolve as entradas normalizadas. Lança exceção se falhar."""
    import feedparser

    cached = _FEED_CACHE.get(url)
    if cached and time.time() - cached[0] < FEED_TTL:
        return cached[1]
    parsed = feedparser.parse(fetch(url))
    if parsed.get("bozo") and not parsed.entries:
        raise ValueError(f"feed inválido: {parsed.get('bozo_exception')}")
    items = []
    for e in parsed.entries:
        title = _clean(e.get("title", ""))
        if not title:
            continue
        source = name
        src = e.get("source")
        if isinstance(src, dict) and src.get("title"):
            source = f"{name} / {src['title']}"
        pub = _published(e)
        items.append({"source": source, "title": title, "summary": _clean(e.get("summary", ""))[:400],
                      "link": e.get("link", ""), "published": pub.isoformat() if pub else None})
    _FEED_CACHE[url] = (time.time(), items)
    return items


def _alias_patterns(ticker: str) -> list[re.Pattern]:
    info = config.STOCKS[ticker]
    pats = [re.compile(r"\b" + re.escape(_norm(a).strip()) + r"\b") for a in info["aliases"]]
    return pats


# "Vale" também é palavra comum ("vale a pena") e nome de regiões ("Vale do Paraíba",
# "no Vale"); exige maiúscula e exclui esses usos. "Vale do Rio Doce" é aceito.
_VALE_STRICT = re.compile(r"(?<!\bno )(?<!\bdo )(?<!\bao )(?<!\bpelo )(?<!\bo )\bVale\b"
                          r"(?! a pena| ressaltar| lembrar| destacar| e regi|-| d[oa]s? (?!Rio Doce))")


def mentions(ticker: str, item: dict) -> bool:
    """True se o título/resumo cita a ação (ticker, nome ou alias)."""
    text = f"{item['title']} {item['summary']}"
    if ticker == "VALE3" and _VALE_STRICT.search(text):
        return True
    norm = _norm(text)
    return any(p.search(norm) for p in _alias_patterns(ticker))


def _recency_weight(published: str | None, now: datetime) -> float:
    if not published:
        return 0.5
    age_days = max(0.0, (now - datetime.fromisoformat(published)).total_seconds() / 86400)
    return 0.5 ** (age_days / 3)  # meia-vida de 3 dias


def search_news(ticker: str, feeds: dict | None = None, fetch=_fetch_url,
                max_items: int = config.MAX_NEWS_PER_TICKER) -> ToolResult:
    """Busca notícias relacionadas a `ticker` nos feeds RSS e pontua o sentimento.

    data = {items, sentiment (média ponderada por recência ou None), impact,
            label, counts, summary, sources_ok, sources_failed}
    """
    try:
        t = normalize_ticker(ticker)
    except ValueError as e:
        return ToolResult(False, error=str(e))

    if feeds is None:
        info = config.STOCKS[t]
        query = urllib.parse.quote(info.get("news_query", f'{t} OR "{info["empresa"]}"'))
        feeds = {**config.RSS_FEEDS, f"Google News ({t})": config.GOOGLE_NEWS_URL.format(query=query)}

    ok, failed, seen, items = [], {}, set(), []
    for name, url in feeds.items():
        try:
            entries = fetch_feed(name, url, fetch)
            ok.append(name)
        except Exception as e:  # rede, timeout, HTML no lugar de RSS...
            failed[name] = f"{type(e).__name__}: {str(e)[:120]}"
            log.warning("Feed %s indisponível: %s", name, failed[name])
            continue
        for it in entries:
            key = _norm(re.sub(r"\s+-\s+[^-]+$", "", it["title"]))  # ignora " - Fonte" do Google News
            if key in seen or not mentions(t, it):
                continue
            seen.add(key)
            items.append({**it, **classify(f"{it['title']}. {it['summary']}")})

    items.sort(key=lambda x: x["published"] or "", reverse=True)
    items = items[:max_items]
    now = datetime.now(timezone.utc)
    data = {"ticker": t, "items": items, "sources_ok": ok, "sources_failed": failed}
    data.update(aggregate(items, now))
    if not ok:
        return ToolResult(False, data, error="Nenhuma fonte RSS disponível.")
    return ToolResult(True, data, meta={"n_items": len(items)})


def aggregate(items: list[dict], now: datetime | None = None) -> dict:
    """Score agregado (média ponderada por recência), impacto e resumo extrativo."""
    now = now or datetime.now(timezone.utc)
    counts = {"positivo": 0, "negativo": 0, "neutro": 0}
    for it in items:
        counts[it["label"]] += 1
    if not items:
        return {"sentiment": None, "impact": 0.0, "label": "sem notícias", "counts": counts,
                "summary": "Nenhuma notícia relacionada encontrada nas fontes disponíveis."}
    weights = [_recency_weight(it["published"], now) for it in items]
    sentiment = sum(w * it["score"] for w, it in zip(weights, items)) / sum(weights)
    # Impacto em [0,1]: intensidade do sentimento x cobertura (satura em 10 notícias).
    impact = abs(sentiment) * min(len(items), 10) / 10
    label = "positivo" if sentiment > 0.15 else "negativo" if sentiment < -0.15 else "neutro"
    top = sorted(items, key=lambda x: abs(x["score"]), reverse=True)[:3]
    lines = [f"{len(items)} notícia(s): {counts['positivo']} positiva(s), {counts['negativo']} "
             f"negativa(s), {counts['neutro']} neutra(s). Sentimento agregado {sentiment:+.2f} ({label})."]
    for it in top:
        when = (it["published"] or "")[:10] or "s/ data"
        lines.append(f"- [{it['label']}] {it['title']} ({it['source']}, {when})")
    return {"sentiment": round(sentiment, 3), "impact": round(impact, 3), "label": label,
            "counts": counts, "summary": "\n".join(lines)}


def clear_cache():
    _FEED_CACHE.clear()
