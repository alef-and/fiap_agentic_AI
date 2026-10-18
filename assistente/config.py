"""Configuração central: ações monitoradas, fontes RSS, parâmetros e limiares.

Todos os limiares são heurísticos (não otimizados) e ficam aqui para que
qualquer ajuste seja explícito e auditável.
"""

DISCLAIMER = (
    "AVISO: Recomendações experimentais e educacionais. Não constituem "
    "aconselhamento financeiro e não garantem resultados. Desempenho passado "
    "não indica desempenho futuro."
)

# Ticker B3 -> metadados. O Yahoo Finance usa o sufixo ".SA" para a B3.
# Os aliases servem para relacionar notícias à ação (busca por nome/ticker).
STOCKS = {
    "VALE3": {
        "yahoo": "VALE3.SA",
        "empresa": "Vale",
        "setor": "Mineração",
        # "Vale" sozinho é tratado à parte em news.py (case-sensitive), pois é palavra comum.
        "aliases": ["VALE3", "Vale S.A", "Vale SA", "mineradora Vale"],
        "news_query": 'VALE3 OR "mineradora Vale" OR "Vale S.A."',
    },
    "PETR4": {
        "yahoo": "PETR4.SA",
        "empresa": "Petrobras",
        "setor": "Energia",
        "aliases": ["PETR4", "PETR3", "Petrobras", "Petrobrás"],
    },
    "BBAS3": {
        "yahoo": "BBAS3.SA",
        "empresa": "Banco do Brasil",
        "setor": "Financeiro",
        "aliases": ["BBAS3", "Banco do Brasil"],
    },
    "ITUB4": {
        "yahoo": "ITUB4.SA",
        "empresa": "Itaú Unibanco",
        "setor": "Financeiro",
        "aliases": ["ITUB4", "ITUB3", "Itaú", "Itau Unibanco", "Itaú Unibanco"],
    },
}

# Feeds gerais (filtrados por menção à ação) + Google News por ticker.
# Reuters encerrou seus feeds RSS públicos; a cobertura vem via Google News.
RSS_FEEDS = {
    "InfoMoney": "https://www.infomoney.com.br/feed/",
    "InfoMoney Mercados": "https://www.infomoney.com.br/mercados/feed/",
    "Money Times": "https://www.moneytimes.com.br/feed/",
}
GOOGLE_NEWS_URL = (
    "https://news.google.com/rss/search?q={query}+when:7d"
    "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)

HTTP_TIMEOUT = 10  # segundos por requisição
USER_AGENT = "Mozilla/5.0 (assistente-investimentos educacional)"
MAX_NEWS_PER_TICKER = 15

# Períodos aceitos pelo yfinance.
VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"}
DEFAULT_PERIOD = "2y"

# Indicadores técnicos
RSI_WINDOW = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
SMA_SHORT, SMA_LONG = 20, 50
EMA_FAST, EMA_SLOW, MACD_SIGNAL = 12, 26, 9
BB_WINDOW, BB_STD = 20, 2.0
VOLUME_WINDOW = 20
VOLUME_SPIKE = 1.5  # volume/média acima disto confirma o movimento do dia
MIN_ROWS = SMA_LONG + 10  # mínimo de pregões para indicadores confiáveis

# Regras de decisão: soma dos pesos -> recomendação
BUY_THRESHOLD = 2.0
SELL_THRESHOLD = -2.0
NEWS_WEIGHT = 1.0          # peso máximo do sentimento (score em [-1, 1])
NEWS_MIN_ITEMS = 2         # mínimo de notícias relacionadas para o sentimento contar

# Avaliação histórica
EVAL_HORIZON = 5           # pregões à frente para medir a tendência
HOLD_BAND = 0.02           # |retorno| abaixo disto = AGUARDAR acertou
TRANSACTION_COST = 0.001   # 0,1% por operação (entrada ou saída)

SEED = 42
