# Projeto Integrado — AI Agents

> Fonte: [avaliacao_enunciado.pdf](avaliacao_enunciado.pdf), 12 páginas.
> Transcrição estruturada em Markdown para facilitar a leitura por IA. A organização visual e as quebras de linha foram adaptadas; os requisitos e o conteúdo do enunciado foram preservados. As referências de página correspondem ao PDF original.

## 1. O desafio

### Contexto e objetivo (página 2)

A QuantumFinance está expandindo sua atuação para o mercado de renda variável e deseja oferecer aos seus clientes um **Assistente de Investimentos baseado em AI Agents**, capaz de recomendar operações de compra e venda de ações de forma autônoma e explicável.

Para isso, a empresa identificou a necessidade de um agente inteligente que combine:

- Análise de notícias e sentimentos do mercado financeiro em tempo real.
- Indicadores técnicos de análise gráfica (RSI, MACD, Médias Móveis, Bandas de Bollinger).
- Raciocínio e tomada de decisão autônoma com justificativa para o usuário.
- Interface conversacional para consulta e explicação das recomendações.

### Ações monitoradas (página 3)

As seguintes ações foram selecionadas para a primeira versão do agente:

| Ação | Empresa | Setor |
| --- | --- | --- |
| VALE3 | Vale do Rio Doce | Mineração |
| PETR4 | Petrobras | Energia |
| BBAS3 | Banco do Brasil | Financeiro |
| ITUB4 | Itaú Unibanco | Financeiro |

O agente deverá monitorar continuamente essas ações, coletar dados de mercado e notícias, e emitir recomendações diárias fundamentadas.

### Capacidades do AI Agent (página 4)

O Assistente de Investimentos deve ser construído como um AI Agent com as seguintes capacidades:

#### Percepção

- Leitura de feeds de notícias financeiras.
- Coleta de preços e volumes via API.
- Extração de indicadores técnicos.

#### Raciocínio

- Análise de sentimento das notícias (NLP).
- Interpretação dos indicadores técnicos.
- Geração de hipóteses de compra/venda.

#### Ação

- Emissão de recomendação com justificativa.
- Resposta a perguntas em linguagem natural.
- Registro do raciocínio (Chain-of-Thought).

## 2. Como resolver o problema

### Fontes principais de análise (página 5)

O agente deverá integrar duas fontes principais de dados para emitir suas recomendações:

#### Análise de notícias

- Fontes: RSS feeds (InfoMoney, B3, Reuters) via `feedparser` (open source).
- Processamento com LLM para classificar sentimento: **Positivo / Negativo / Neutro**.
- Score de impacto por ação monitorada.
- Sumarização automática dos principais eventos.

#### Indicadores técnicos

- **RSI** — Índice de Força Relativa (sobrecomprado/sobrevendido).
- **MACD** — Convergência/Divergência de Médias Móveis.
- **Médias Móveis Simples e Exponenciais (SMA/EMA)**.
- **Bandas de Bollinger e Volume**.

### Fluxo de execução do AI Agent (página 6)

1. **Coleta de Dados:** APIs de mercado + feeds de notícias.
2. **Processamento:** NLP + indicadores técnicos calculados.
3. **Análise pelo LLM Agent:** ReAct / Chain-of-Thought reasoning.
4. **Recomendação:** **COMPRAR / VENDER / AGUARDAR** + justificativa.

O agente utiliza a estratégia **ReAct (Reasoning + Acting)** — raciocina passo a passo antes de emitir cada recomendação, registrando o raciocínio de forma transparente para o usuário.

**Ferramentas (Tools) do Agente:**

- `search_news(ticker)`
- `get_price_data(ticker, period)`
- `calculate_indicators(data)`
- `generate_recommendation(analysis)`

Dados via `yfinance` + `feedparser` (ambos open source).

### Fontes de dados sugeridas (página 7)

| Tipo de dado | Fonte sugerida | Formato |
| --- | --- | --- |
| Preços históricos de ações | `yfinance` (open source, Yahoo Finance) | DataFrame (OHLCV) |
| Notícias financeiras | `feedparser` — RSS feeds InfoMoney, B3, Reuters | JSON / RSS Feed |
| Indicadores técnicos | `pandas-ta` ou TA-Lib (open source) | DataFrame |
| Dados fundamentalistas | `fundamentus` (open source, scraping B3) | DataFrame |

Exemplo de estrutura de dado esperada para cada ação em cada dia de análise:

```json
{
  "ticker": "VALE3",
  "date": "2024-11-15",
  "close": 61.42,
  "rsi": 45.2,
  "macd_signal": "bullish",
  "news_sentiment": 0.72,
  "recommendation": "COMPRAR"
}
```

## 3. O que é esperado como entrega?

### Solução e componentes (página 8)

A solução deve ser um **AI Agent funcional, implementado em Python**, com entrega em **Jupyter Notebook ou repositório GitHub**:

1. **Coleta e Pré-processamento**
   - Pipeline de dados: preços históricos, cálculo de indicadores técnicos e coleta de notícias.
2. **Análise de Sentimento**
   - Classificação de notícias financeiras usando LLM ou modelo de NLP treinado.
3. **AI Agent com Tools**
   - Agente implementado com LangChain, AutoGen ou similar, com **pelo menos 3 ferramentas definidas**.
4. **Recomendações e Backtest**
   - O agente deve gerar recomendações (**COMPRAR/VENDER/AGUARDAR**) e registrar o raciocínio.
   - Backtest opcional.

### Indicadores de avaliação (página 9)

Os seguintes indicadores devem ser apresentados na avaliação do agente:

#### Acurácia das recomendações

Comparação entre as recomendações do agente e o comportamento real das ações no período de teste (acerto de tendência).

#### Qualidade do raciocínio (Chain-of-Thought)

O agente deve registrar o passo a passo do raciocínio que levou à recomendação, de forma coerente e explicável.

#### Desempenho financeiro via Backtest (opcional, mas valorizado)

Simulação do retorno financeiro caso as recomendações do agente fossem seguidas no período de teste. Comparar com estratégia Buy-and-Hold.

#### Interface conversacional (opcional)

Chatbot ou interface em que o usuário pode perguntar: “Por que você recomendou comprar PETR4 hoje?”

## 4. Possibilidades adicionais (página 10)

**O problema: o que mais seria possível ser feito?**

A criatividade é totalmente permitida desde que utilize AI Agents de forma coerente e inovadora.

- **Multi-agente:** um agente de notícias + um agente técnico + um agente orquestrador tomador de decisão.
- **Agente com memória de longo prazo:** lembrar de eventos macroeconômicos passados e seu impacto nas ações.
- **Alertas automáticos:** agente que envia e-mail ou mensagem no Telegram com recomendações diárias.
- **Comparador de carteiras:** agente que monta e avalia carteiras de ações com base em perfil de risco do usuário.
- **Agente de explicabilidade:** gera relatórios em linguagem natural justificando cada recomendação para o cliente.

## 5. Tecnologias sugeridas (página 11)

| Categoria | Tecnologias sugeridas |
| --- | --- |
| Frameworks de AI Agents | LangChain, LangGraph, Google ADK |
| Modelos de Linguagem | OpenAI GPT-4o¹, Anthropic Claude¹, Llama 3 via Ollama (open source e local) |
| Dados de Mercado | `yfinance` (open source) — preços históricos via Yahoo Finance, sem necessidade de API key |
| Notícias Financeiras | `feedparser` (open source) — leitura de RSS feeds: InfoMoney, Reuters, B3, Valor Econômico |
| Análise Técnica | `pandas-ta` (open source), TA-Lib (open source), `mplfinance` (open source) |
| NLP / Sentimento (Opcional) | FinBERT via HuggingFace `transformers` (open source), VADER (open source), spaCy (open source) |
| Visualização / Interface | Plotly (open source), Matplotlib (open source) — Como Tool do Agente |

¹ Modelos proprietários — exigem chave de API paga. Alternativa gratuita: Llama 3 via Ollama (roda localmente).

## 6. Encerramento e direitos autorais (página 12)

**OBRIGADO — FIAP**

Copyright © 2026 | Professor Felipe Gustavo Silva Teodoro

Todos os direitos reservados. A reprodução ou divulgação total ou parcial deste documento é expressamente proibida sem consentimento formal, por escrito, do professor(a)/autor(a).