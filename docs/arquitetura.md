# Arquitetura Multiagente Unificada v2

## Diagrama de Fluxo

```
┌─────────────┐
│  Usuário    │  upload ZIPs (202401_NFs.zip + 202505_NFe.zip)
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ LoaderAgent     │  JSZip / zipfile
│ - Valida ZIP    │  - Detecta encoding
│ - Extrai CSVs   │  - PapaParse / pandas
└──────┬──────────┘
       │ tabelas brutas
       ▼
┌─────────────────┐
│ SchemaAgent     │  Inferência de tipos
│ - Tipos         │  - Sinônimos PT-BR
│ - Dicionário    │  - Stats, únicos
└──────┬──────────┘
       │ dicionário + tabelas
       ▼
┌─────────────────┐      ┌──────────────────────┐
│ QueryAgent      │─────▶│ LangChain (opcional) │
│ - NLU híbrido   │      │ create_agent         │
│ - Intent/Metric │      │ + Pydantic QueryPlan │
│ - Heurística    │◀─────│ Fallback 100% offline│
└──────┬──────────┘      └──────────────────────┘
       │ QueryPlan validado
       ▼
┌─────────────────┐
│ ExecutorAgent   │  Whitelist ops:
│ - Filtros       │  sum, avg, count, max, min
│ - Agregações    │  Sem eval
└──────┬──────────┘
       │ DataFrame resultado
       ▼
┌─────────────────┐      ┌─────────────────┐
│ VizAgent        │─────▶│ FallbackAgent   │
│ - Decide viz    │      │ - Mensagens     │
│ - Chart.js      │      │ - Sugestões     │
└──────┬──────────┘      └─────────────────┘
       │ texto/tabela/gráfico
       ▼
┌─────────────────┐
│ Interface B     │  Texto + Tabela + Gráfico + Plano JSON + Logs
└─────────────────┘
```

## Decisão de Cada Agente

**LoaderAgent**: decide se arquivo é ZIP válido contendo CSV; rejeita sem quebrar; loga cada CSV encontrado. Em Python, tenta utf-8 → latin1.

**SchemaAgent**: amostra 100 linhas para inferir tipo; se >80% números → numérico, >70% datas → data, senão categórico. Mapeia sinônimos: fornecedor (xFant, xNome, emitente), valor (vNF, vProd), produto (xProd). Gera descrição humana.

**QueryAgent**: 
- Se ANTHROPIC_API_KEY existe e LangChain instalado, monta prompt com schema + pergunta e pede JSON estruturado. Valida com Pydantic.
- Senão, aplica regex de palavras-chave: "maior valor" → ranking+sum, "por mês" → timeseries+line, "top 5" → limit 5, "quantidade por NCM" → group_count+pie.
- Confidence: 0.9 se LLM, 0.65 se heurística.

**ExecutorAgent**:
- Whitelist: só permite groupby + agg predefinidas. Nunca executa código gerado.
- Conversão BR: regex remove R$, pontos de milhar, troca vírgula por ponto.
- Se coluna não encontrada, busca coluna numérica similar.
- Growth: calcula pct_change.

**VizAgent**:
- Regra: 1 linha → text, timeseries/growth → line, group_count ≤8 → pie, ranking → bar, list → table.
- No client usa Chart.js, no Python st.bar_chart / plotly.

**FallbackAgent**:
- Captura exceção, classifica: ColumnNotFound, AmbiguousQuestion, EmptyTable.
- Retorna texto em PT-BR com sugestão e lista colunas disponíveis (top 30).

## Framework Escolhido

- **LangChain**: obrigatório pelo desafio, usado para orquestração opcional com `create_agent` e structured output.
- **Pydantic**: valida QueryPlan, garante contrato entre agentes.
- **Client-side**: JSZip + PapaParse + Chart.js via CDN, sem backend, 100% offline, atende requisito GitHub Pages.
- **Streamlit**: interface Python avançada para testes locais.

## Separação de Componentes

- `index.html`: Interface A + B + 6 agentes JS (tudo em um arquivo para Pages)
- `app.py`: Streamlit orquestrador
- `src/csv_loader.py`: Loader + Schema
- `src/models.py`: QueryPlan
- `src/agent.py`: Query + Fallback
- `src/data_engine.py`: Executor + Viz

Organização em módulos, código documentado, logs por agente.
