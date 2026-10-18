# Prompt para desenvolvimento do projeto

Atue como engenheiro(a) de software e especialista em AI Agents, Python e análise de dados financeiros. Desenvolva neste workspace o projeto descrito em `enunciado.md`, respeitando os requisitos abaixo e aproveitando os arquivos e dependências que já existirem.

## Antes de implementar

1. Inspecione a estrutura do workspace, o conteúdo de `enunciado.md`, o notebook `trab_final.ipynb` e os arquivos de dependências disponíveis.
2. Identifique o que já está implementado e preserve o trabalho existente sempre que possível.
3. Verifique as dependências e o ambiente Python configurado. Não substitua nem recrie a venv.
4. Se houver decisões importantes que não possam ser deduzidas do projeto, registre as premissas adotadas e escolha alternativas gratuitas ou open source sempre que viável.

## Objetivo

Construir um AI Agent funcional, em Python, para analisar as ações brasileiras VALE3, PETR4, BBAS3 e ITUB4 e produzir recomendações diárias explicáveis: **COMPRAR**, **VENDER** ou **AGUARDAR**.

O agente deve combinar dados históricos de mercado, indicadores técnicos e notícias financeiras. A solução deve ser executável e adequada à entrega em Jupyter Notebook ou repositório GitHub.

## Requisitos funcionais

- Coletar preços e volumes históricos com `yfinance`, usando os tickers apropriados para ações brasileiras.
- Coletar notícias financeiras por RSS com `feedparser`, quando as fontes estiverem disponíveis.
- Tratar falhas de rede, fontes indisponíveis, dados vazios e limites das bibliotecas sem interromper inesperadamente o fluxo. Não invente dados ou notícias.
- Calcular, no mínimo:
  - RSI;
  - MACD e sinal;
  - SMA e EMA;
  - Bandas de Bollinger;
  - volume.
- Classificar o sentimento das notícias como positivo, negativo ou neutro. Preferir uma abordagem gratuita e explicar suas limitações; não exigir chaves pagas para executar o fluxo principal.
- Relacionar notícias às ações monitoradas, produzir um score de sentimento/impacto e resumir os eventos relevantes sem atribuir às notícias informações que não estejam presentes nas fontes.
- Implementar um agente com pelo menos três ferramentas claramente definidas, incluindo ferramentas equivalentes a:
  - `search_news(ticker)`;
  - `get_price_data(ticker, period)`;
  - `calculate_indicators(data)`;
  - `generate_recommendation(analysis)`.
- Integrar as ferramentas em um fluxo de agente, usando LangChain, LangGraph ou uma alternativa simples e funcional. Se uma dependência de agente exigir configuração externa, oferecer uma alternativa executável sem credenciais pagas.
- Gerar, para cada ação analisada, recomendação, data, dados utilizados, principais sinais técnicos, resumo do sentimento das notícias, justificativa e limitações relevantes.
- Responder perguntas sobre uma recomendação com base nos dados e resultados registrados pelo sistema.

## Explicabilidade e segurança

Forneça justificativas concisas, auditáveis e baseadas em evidências observáveis — por exemplo, valores dos indicadores, notícias consideradas e regras que contribuíram para a decisão. **Não exponha nem simule raciocínio interno privado (Chain-of-Thought)**; registre apenas resumos da decisão, evidências e critérios utilizados.

Deixe claro que as recomendações são experimentais, não constituem aconselhamento financeiro e não garantem resultados. Não apresente projeções como certezas.

## Avaliação

Implemente uma avaliação histórica quando houver dados suficientes:

- Defina de forma explícita o que significa “acerto de tendência” e como cada recomendação é avaliada.
- Evite vazamento de dados futuros: cada decisão deve usar somente dados disponíveis até a data da decisão.
- Apresente métricas compreensíveis, como acurácia das recomendações e, se implementar backtest, retorno acumulado e comparação com Buy-and-Hold.
- Documente custos, premissas, limitações e os riscos de interpretar resultados históricos como garantia de desempenho futuro.
- Trate corretamente recomendações AGUARDAR e períodos sem dados suficientes.

## Qualidade e organização

- Organize o código em etapas ou módulos coerentes, evitando duplicação e células monolíticas.
- Inclua tratamento de erros, validações de entrada e comentários/docstrings onde agreguem clareza.
- Torne os resultados reproduzíveis sempre que possível.
- Inclua visualizações úteis para preços, indicadores e resultados, se as dependências disponíveis permitirem.
- Inclua instruções de execução e dependências necessárias, atualizando arquivos existentes em vez de criar duplicatas.
- Não inclua segredos, tokens ou chaves de API no código ou nos notebooks.
- Não descarte nem sobrescreva dados ou arquivos existentes sem necessidade.

## Critérios de conclusão

Considere o trabalho concluído quando:

1. O notebook ou ponto de entrada principal puder ser executado na ordem indicada.
2. O fluxo cobrir coleta, processamento, indicadores, sentimento, uso das ferramentas e geração de recomendações.
3. O projeto funcionar sem chave paga, ou explicar claramente e isolar qualquer integração opcional que a exija.
4. Houver uma demonstração para as quatro ações monitoradas, com tratamento explícito para indisponibilidade de dados.
5. A avaliação não utilizar informação futura e as limitações estiverem documentadas.
6. As dependências e instruções de execução estiverem atualizadas.
7. Os testes ou verificações disponíveis forem executados; informe objetivamente quais passaram e quais não puderam ser executados.

Ao final, apresente um resumo das alterações realizadas, como executar o projeto, as premissas adotadas e quaisquer limitações que permaneçam.