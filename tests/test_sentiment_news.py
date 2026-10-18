from assistant.news import mentions, search_news
from assistant.sentiment import classify

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Petrobras dispara com lucro recorde</title><description>PETR4 sobe</description>
<pubDate>Fri, 16 Oct 2026 10:00:00 GMT</pubDate><link>http://x/1</link></item>
<item><title>Vale cai com queda do minerio</title><description></description>
<pubDate>Fri, 16 Oct 2026 09:00:00 GMT</pubDate><link>http://x/2</link></item>
<item><title>Vale a pena investir em CDB?</title><description></description></item>
<item><title>Petrobras recua apos prejuizo</title><description></description>
<pubDate>Thu, 15 Oct 2026 09:00:00 GMT</pubDate><link>http://x/3</link></item>
</channel></rss>"""


def test_classify_labels():
    assert classify("Petrobras dispara após lucro recorde")["label"] == "positivo"
    assert classify("Vale despenca com prejuízo")["label"] == "negativo"
    assert classify("Assembleia de acionistas marcada para terça")["label"] == "neutro"
    assert classify("Ações da Caixa estáveis")["terms"] == []  # "cai" não casa "Caixa"
    assert classify("empresa não teve prejuízo")["score"] > 0  # negação


def test_mentions_vale_disambiguation():
    def it(t):
        return {"title": t, "summary": ""}
    assert mentions("VALE3", it("Vale cai com minério"))
    assert not mentions("VALE3", it("Vale a pena investir em CDB?"))
    assert not mentions("VALE3", it("Chuva provoca estragos no Vale e região"))
    assert not mentions("VALE3", it("Vale do Paraíba tem previsão de temporais"))
    assert mentions("VALE3", it("Vale do Rio Doce anuncia dividendos"))
    assert mentions("VALE3", it("Ações da Vale caem"))
    assert mentions("ITUB4", it("Itaú Unibanco divulga balanço"))


def test_search_news_with_mock_feed():
    r = search_news("PETR4", feeds={"Mock": "http://mock"}, fetch=lambda url: RSS)
    assert r.ok and r.data["sources_ok"] == ["Mock"]
    titles = [i["title"] for i in r.data["items"]]
    assert titles == ["Petrobras dispara com lucro recorde", "Petrobras recua apos prejuizo"]
    assert r.data["sentiment"] is not None and "Petrobras dispara" in r.data["summary"]


def test_search_news_all_sources_down():
    def boom(url):
        raise OSError("sem rede")
    r = search_news("BBAS3", feeds={"A": "http://a", "B": "http://b"}, fetch=boom)
    assert not r.ok and set(r.data["sources_failed"]) == {"A", "B"}
    assert r.data["items"] == [] and r.data["sentiment"] is None


def test_search_news_invalid_ticker():
    assert not search_news("XPTO3").ok


def test_no_related_news_gives_none():
    r = search_news("ITUB4", feeds={"Mock": "http://mock"}, fetch=lambda url: RSS)
    assert r.ok and r.data["items"] == [] and r.data["sentiment"] is None
