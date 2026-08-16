# Interface Inteligente Unificada v2 — Consulta CSV/NFe
### Desafio 4: Interface Inteligente para Consulta de Arquivos CSV

Versão final integrada que une os pontos fortes dos dois projetos de aprendizagem do grupo InsurTechLab:

- **01 Interface-Inteligente-para-Consulta-de-Arquivos-CSV**: documentação robusta, 6 agentes bem definidos, LangChain + Pydantic, testes automatizados, Streamlit, exportação de logs e plano JSON. Em https://github.com/InsurTechLabI2A2/Interface-Inteligente-para-Consulta-de-Arquivos-CSV
- **02 Multiagente-de-Consulta-de-Nfe-v1**: acessibilidade prática via GitHub Pages, 100% client-side (JSZip, PapaParse, Chart.js), dicionário automático, perguntas de teste, sem instalação. Em https://github.com/InsurTechLabI2A2/Multiagente-de-Consulta-de-Nfe-v1

> **Objetivo**: demonstrar como agentes inteligentes + LLMs + tools transformam dados estruturados em informação automática, permitindo que qualquer usuário consulte CSVs de NFe em linguagem natural.

Link original dos dados: https://drive.google.com/drive/folders/19InGHYOQnTou_N0_KAXZ6tK9WB6rD6HS

---

## 🌐 Como usar (GitHub Pages - recomendado)

1. Acesse: **https://insurtechlabi2a2.github.io/Interface-Inteligente-Unificada/** 
   Ou abra localmente `index.html` — não precisa de backend.

2. Arraste os ZIPs `202401_NFs.zip` e `202505_NFe.zip` (ou clique em "Carregar dados de exemplo" para teste rápido).

3. Veja o **Dicionário de Dados** gerado automaticamente pelo SchemaAgent.

4. Digite perguntas em PT-BR ou clique nas perguntas de teste:

**10 perguntas exigidas pelo desafio (com respostas em texto, tabela e gráfico):**

1. Qual fornecedor recebeu o maior valor no período? → **bar**
2. Qual produto apresentou o maior volume comprado? → **bar**
3. Qual foi o total gasto em cada mês? → **line**
4. Quais foram os cinco maiores fornecedores? → **bar**
5. Qual categoria apresentou maior crescimento nas compras? → **line**
6. Qual o valor total das notas fiscais emitidas? → **text**
7. Quais os 5 emitentes com maior valor total de notas? → **bar**
8. Qual UF do destinatário recebeu mais notas fiscais? → **pie/bar**
9. Qual a quantidade total por NCM? → **pie**
10. Qual CFOP mais utilizado? → **bar**
11. Liste as notas fiscais com maior valor → **table**

5. Exporte **Dicionário (JSON/CSV)** e **Logs Técnicos** 

---

## 🧩 Arquitetura Multiagente (6 agentes especializados)

```
[ZIP] → LoaderAgent → SchemaAgent → QueryAgent → ExecutorAgent → VizAgent → FallbackAgent
           ↓              ↓              ↓               ↓             ↓
        JSZip/Pandas  Inferência      LangChain      Pandas/JS     Chart.js
                      + Sinônimos PT  + Pydantic     Whitelist
```

### 1. LoaderAgent
- Valida ZIP, extrai CSVs via JSZip (client) / zipfile (Python)
- Detecta encoding utf-8/latin1
- Usa PapaParse / pandas com `dtype=str` para segurança
- **Decisão**: ignora arquivos não-CSV, remove linhas vazias, normaliza nomes de tabelas.

### 2. SchemaAgent
- Infere tipo (numérico, data, categórico) por amostragem
- Gera dicionário automático: coluna, tipo, descrição, exemplo, únicos
- Mapeia sinônimos PT-BR: `fornecedor→xFant/xNome/emitente`, `valor→vNF/vProd`, `produto→xProd` etc.
- **Decisão**: cria stats e expõe colunas para QueryAgent, permite validação sem precisar de dicionário externo.

### 3. QueryAgent
- **Modo LLM (Interface CSV)**: tenta `langchain.create_agent` com `ANTHROPIC_API_KEY`, saída estruturada `QueryPlan` Pydantic validado. Nunca executa código gerado, só produz plano.
- **Modo Local (Multiagente NFe)**: heurística de keywords + detecção de intent (ranking, aggregate, group_count, timeseries, growth, list), metric (sum, count), group_by, value_col, viz_hint.
- **Decisão**: se LLM disponível, enriquece plano; senão, fallback 100% offline garante funcionamento. Confidence score indica origem.

### 4. ExecutorAgent
- Executa apenas operações whitelist: `sum, avg, count, count_distinct, max, min, group_sum, growth`
- Conversão robusta de moeda BR: `12.500,50 → 12500.50`
- Sem `eval`, sem execução de código arbitrário
- **Decisão**: escolhe coluna numérica se `value_col` não encontrado, limita resultados, ordena.

### 5. VizAgent
- Decide visualização com base em intent + cardinalidade:
  - `aggregate → text`
  - `timeseries/growth → line`
  - `group_count com ≤8 grupos → pie`
  - `ranking → bar`
  - `list → table`
- Renderiza Chart.js (client) / st.bar_chart + Plotly pie (Python)
- **Decisão**: prioriza clareza sobre estética; exportável.

### 6. FallbackAgent
- Captura erros de todos os agentes
- Devolve mensagem clara em PT-BR + sugestão de reformulação + lista colunas relevantes
- Nunca quebra a UI
- **Decisão**: classifica erro como "coluna não encontrada", "pergunta ambígua", "tabela vazia" e sugere perguntas válidas.

**Fluxo completo está documentado em `docs/arquitetura.md` e `docs/relatorio_tecnico.md`.**

---

## 💻 Interface Python (Streamlit)

Para quem prefere backend local com LangChain:

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\Activate.ps1 no Windows
pip install -r requirements.txt
# opcional: crie .env com ANTHROPIC_API_KEY=...
streamlit run app.py
```

Abas:
- **Carregar Dados**: upload ZIP, dicionário, export JSON/CSV
- **Consultar**: input natural, plano JSON antes da execução, texto+tabela+gráfico
- **Evidências**: logs por agente, histórico, relatório

---

## 📊 Visualizações

Consolida Chart.js do projeto 01 para enriquecer respostas:
- Barras: ranking de fornecedores, produtos, UF, CFOP
- Linha: total gasto por mês, crescimento por categoria
- Pizza: distribuição por NCM, UF
- Texto: agregações simples
- Tabela: listagens

Todos os gráficos são responsivos e exportáveis.

---

## 🛡️ Tratamento de erros (FallbackAgent)

- Upload sem CSV → mensagem + exemplo de ZIP válido
- Pergunta sem colunas reconhecidas → lista colunas + perguntas sugeridas
- Tabela vazia → aviso
- Falha LLM → fallback automático para heurística local
- Conversão numérica falha → conta como 0 e loga warning

---

## 📄 Relatório Técnico e Entregáveis

- `docs/relatorio_tecnico.md` + `docs/relatorio_tecnico.pdf` (gerado)
- Descreve: framework (LangChain), arquitetura, fluxo, decisão de cada agente, 11 perguntas testadas em 3 formatos, limitações
- `index.html`: GitHub Pages 100% client-side
- `app.py`: Streamlit + LangChain
- `src/`: módulos separados (loader, models, agent, data_engine)
- `tests/`: testes unitários (soma, média, ranking, NCM, UF)
- `sample_data/`: ZIP exemplo

---

## 🔐 Segurança

- Chaves API ocultas via `.env` (nunca commitadas)
- Execução determinística (sem eval de código LLM)
- 100% local no modo client-side: nenhum dado sai do navegador
- Logs não contêm dados sensíveis

---

## 📚 Créditos

Baseado nos projetos de aprendizagem I2A2:
- Interface CSV: relatório técnico detalhado, agentes claros, export logs, plano JSON em https://github.com/InsurTechLabI2A2/Interface-Inteligente-para-Consulta-de-Arquivos-CSV
- Multiagente NFe: acessibilidade via GitHub Pages, dicionário automático, perguntas de teste, UX amigável em https://github.com/InsurTechLabI2A2/Multiagente-de-Consulta-de-Nfe-v1

Versão unificada v2 por Grupo de Estudos I2A2 InsurTechLab 2026
Licença MIT
