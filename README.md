# Assistente de Investimentos com AI Agent — VALE3, PETR4, BBAS3, ITUB4

Projeto Integrado de AI Agents (FIAP). O enunciado está em [docs/enunciado.md](docs/enunciado.md).

> **Aviso:** projeto experimental e educacional. As recomendações **não constituem aconselhamento
> financeiro** e **não garantem resultados**. Desempenho passado não indica desempenho futuro.

O agente coleta preços (`yfinance`) e notícias RSS (`feedparser`) e calcula indicadores técnicos. Também classifica o sentimento das notícias com um léxico em português. Com isso, emite uma recomendação diária **COMPRAR / VENDER / AGUARDAR** por ação, com justificativa baseada em evidências observáveis.

O fluxo principal **não exige nenhuma chave de API**.

## Como executar

Pré-requisito: Python 3.12 com a venv do projeto (`.venv/`).

```powershell
# 1. Instalar as dependências na venv existente
.venv\Scripts\python -m pip install -r requirements.txt

# 2. (opcional) Modo LLM: LangChain + OpenAI/Gemini
.venv\Scripts\python -m pip install -r requirements_llm.txt

# 3. Testes automatizados (offline, sem rede)
.venv\Scripts\python -m pytest
```

Depois, abra `trab_final.ipynb` no VS Code ou no Jupyter, selecione o kernel da `.venv` e execute as células em ordem (*Restart & Run All*). Também é possível executar sem interface:

```powershell
$env:PYTHONUTF8 = "1"   # obrigatório no Windows: sem isso o arquivo é lido como cp1252 e os acentos se corrompem
.venv\Scripts\jupyter execute --inplace trab_final.ipynb   # via nbclient (já em requirements.txt)
```

O notebook salva os registros em `recomendacoes.json`. Esse arquivo é ignorado pelo git.

### Modo LLM (opcional)

1. Defina `OPENAI_API_KEY` ou `GOOGLE_API_KEY` no terminal **antes** de iniciar o VS Code ou o Jupyter. O kernel herda o ambiente desse processo.
2. Opcionalmente, defina `LLM_MODEL` para escolher outro modelo. O padrão é `gpt-4o-mini` na OpenAI e `gemini-2.5-flash` no Google.

Nunca grave chaves no código ou no notebook. Chamadas a APIs pagas podem gerar custo. Sem chave ou sem os pacotes, a seção 5.1 apenas informa a indisponibilidade.

## Estrutura

```
assistente/
  config.py          ações, feeds RSS, parâmetros e limiares
  tools.py           Tool / ToolResult e validação de ticker
  data.py            get_price_data(ticker, period)       -> yfinance (.SA), retry, cache
  indicators.py      calculate_indicators(data)            -> RSI, MACD, SMA/EMA, Bollinger, volume
  sentiment.py       léxico financeiro PT (positivo/negativo/neutro + termos)
  news.py            search_news(ticker)                   -> feedparser, relação notícia-ação, score/impacto
  recommendation.py  generate_recommendation(analysis)     -> regras pontuadas e auditáveis
  agent.py           InvestmentAgent: orquestra as ferramentas e registra o trace
  chat.py            perguntas e respostas sobre os registros
  evaluation.py      avaliação walk-forward e backtest vs Buy-and-Hold
  plots.py           gráficos (matplotlib)
  llm_agent.py       modo opcional LangChain (OpenAI/Gemini) com as mesmas ferramentas
tests/               testes pytest com dados sintéticos e feeds simulados
trab_final.ipynb     notebook de entrega (ponto de entrada)
```

## Como o agente decide

Para cada ação, o agente executa quatro ferramentas em sequência:

1. `get_price_data`
2. `calculate_indicators`
3. `search_news`
4. `generate_recommendation`

Cada passo fica registrado no `trace` com a ferramenta, a entrada e o resultado. Se uma etapa falha, o agente registra a falha e continua. Sem preços, por exemplo, a recomendação é AGUARDAR com o motivo.

### Regras de pontuação

| Sinal | Condição | Contribuição |
| --- | --- | --- |
| RSI | < 30 / > 70 | +1 / −1 |
| MACD vs sinal | cruzamento de alta / de baixa | +1,5 / −1,5 |
| MACD vs sinal | só acima / só abaixo da linha de sinal | +0,5 / −0,5 |
| Fechamento vs SMA50 | acima / abaixo | +0,5 / −0,5 |
| SMA20 vs SMA50 | acima / abaixo | +1 / −1 |
| Bandas de Bollinger | fechamento fora das bandas | ±0,5 |
| Volume | ≥ 1,5× a média de 20 dias, confirmando o retorno do dia | ±0,5 |
| Notícias | sentimento agregado, se houver ≥ 2 notícias | score × 1 |

A soma das contribuições define a recomendação: score ≥ +2 → COMPRAR, score ≤ −2 → VENDER e, entre esses limiares, AGUARDAR.

O registro guarda as evidências (valores, notícias e regras acionadas), não um raciocínio interno do modelo.

O sentimento das notícias funciona assim:

- Cada notícia recebe um score de −1 a +1 e a lista dos termos que pontuaram.
- O score da ação é a média ponderada por recência (meia-vida de 3 dias).
- O impacto vai de 0 a 1 e é calculado como |sentimento| × cobertura.
- O resumo é extrativo: lista as manchetes reais com fonte e data.

## Avaliação histórica

- **Sem vazamento de dados futuros.** A decisão em D usa apenas dados até o fechamento de D. Os testes comprovam que truncar a série em D não altera nenhuma decisão até D.
- **Apenas regras técnicas.** Os feeds RSS não têm histórico confiável, então as notícias ficam fora da avaliação.
- **Acerto de tendência** em 5 pregões, com r = Close[D+5]/Close[D] − 1:
  - COMPRAR acerta se r > 0;
  - VENDER acerta se r < 0;
  - AGUARDAR acerta se |r| < 2%.
- **Decisões fora da métrica.** Decisões sem D+5 disponível e o período de aquecimento dos indicadores são contados à parte.
- **Métricas:**
  - acurácia geral;
  - acurácia direcional (sem AGUARDAR);
  - acurácia por classe;
  - taxa base de alta, como referência.
- **Backtest long-only:**
  - COMPRAR entra, VENDER sai e AGUARDAR mantém a posição;
  - a decisão de D rende a partir de D+1;
  - custo de 0,1% por operação;
  - comparado ao Buy-and-Hold com retorno acumulado e drawdown máximo.

## Premissas e limitações

- **Preços.** Os tickers são os da B3 no Yahoo Finance, com sufixo `.SA`, e os preços são ajustados. Os dados podem ter atraso ou falhas.
- **Notícias.** As fontes são InfoMoney, Money Times e Google News, que agrega Valor, Reuters e outros veículos. A Reuters não mantém mais RSS público próprio. Os feeds podem mudar ou ficar indisponíveis.
- **Relação notícia-ação.** A notícia é associada à ação por ticker ou nome no título e no resumo. "Vale" tem um filtro específico porque também é palavra comum e nome de regiões.
- **Sentimento.** O léxico não capta ironia, contexto nem quem é afetado pela notícia.
- **Regras.** As regras e os limiares são heurísticos e não foram otimizados.
- **Backtest.** Não considera impostos, slippage nem liquidez. Usa uma única janela de cerca de 2 anos.
- **Fora do escopo.** Dados fundamentalistas, alertas automáticos e arquitetura multiagente não foram implementados.
