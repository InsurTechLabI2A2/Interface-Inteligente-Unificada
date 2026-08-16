"""
Interface Inteligente Unificada v2 - Desafio 4
Versão Python Streamlit com 6 agentes especializados + LangChain opcional
Integra pontos fortes de:
- Interface-Inteligente-para-Consulta-de-Arquivos-CSV (LangChain, Pydantic, testes)
- Multiagente-de-Consulta-de-Nfe-v1 (GitHub Pages, Chart.js, dicionário automático)

Execução: streamlit run app.py
"""
import streamlit as st
import zipfile, io, json
import pandas as pd
from pathlib import Path
from src.csv_loader import LoaderAgent
from src.agent import QueryAgent, FallbackAgent
from src.data_engine import ExecutorAgent, VizAgent
from src.models import QueryPlan

st.set_page_config(page_title="Interface Unificada v2 - I2A2", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# --- Estilo ---
st.markdown("""
<style>
.stApp {background: #0b1020;}
div[data-testid="stMetric"]{background:#121a32;border:1px solid #22306a;border-radius:12px;padding:12px}
</style>
""", unsafe_allow_html=True)

st.title("🧠 Interface Inteligente Unificada v2 — Desafio 4")
st.caption("LoaderAgent • SchemaAgent • QueryAgent • ExecutorAgent • VizAgent • FallbackAgent | Client-side + Python + LangChain-ready | I2A2 InsurTechLab")

# Estado
if 'tables' not in st.session_state: st.session_state.tables={}
if 'dictionary' not in st.session_state: st.session_state.dictionary={}
if 'logs' not in st.session_state: st.session_state.logs=[]
if 'history' not in st.session_state: st.session_state.history=[]

def log(agent, msg):
    st.session_state.logs.append({"agent":agent, "msg":msg})
    
loader = LoaderAgent(log_fn=log)
query_agent = QueryAgent(log_fn=log)
executor = ExecutorAgent(log_fn=log)
viz = VizAgent()
fallback = FallbackAgent()

# Sidebar - Arquitetura
with st.sidebar:
    st.header("🧩 Arquitetura Multiagente")
    st.markdown("""
    **LoaderAgent**: valida ZIP, extrai CSVs, detecta encoding (utf-8/latin1).  
    **SchemaAgent**: infere tipos, gera dicionário automático, mapeia sinônimos PT-BR.  
    **QueryAgent**: LangChain (create_agent) + plano Pydantic QueryPlan. Fallback heurístico 100% offline.  
    **ExecutorAgent**: execução determinística whitelist (sem eval).  
    **VizAgent**: decide text/table/bar/line/pie e renderiza Chart.js / Streamlit.  
    **FallbackAgent**: mensagens claras + sugestão de reformulação.
    """)
    st.divider()
    st.header("📦 Interface A - Carga")
    uploaded = st.file_uploader("Envie ZIPs 202401_NFs e 202505_NFe", type=["zip"], accept_multiple_files=True)
    if st.button("⚡ Usar dados de exemplo"):
        # cria zip exemplo em memória
        import zipfile, io
        sample = """xFant,xNome,vNF,vProd,nNF,dhEmi,UF,NCM,CFOP,xProd,qCom,categoria
Fornecedor A LTDA,Fornecedor A LTDA,12500.50,12000,1001,2024-01-15,SP,8471,5102,Notebook Dell,10,Informática
Fornecedor B SA,Fornecedor B SA,8900.00,8900,1002,2024-02-10,RJ,8517,5102,Smartphone Samsung,20,Telefonia
Fornecedor A LTDA,Fornecedor A LTDA,15200.75,15000,1003,2024-03-05,SP,8471,6102,Notebook Dell,12,Informática
Fornecedor C ME,Fornecedor C ME,5400.20,5000,1004,2025-05-02,MG,9403,5102,Cadeira Escritório,15,Móveis
Fornecedor B SA,Fornecedor B SA,21000.00,20000,1005,2025-05-10,RJ,8471,5102,Servidor HP,2,Informática
Fornecedor D LTDA,Fornecedor D LTDA,3200.00,3000,1006,2025-05-12,SP,9403,5102,Mesa Reunião,5,Móveis
"""
        st.session_state.tables = {
            "202401_NFs": pd.DataFrame([l.split(",") for l in sample.splitlines()[1:3]], columns=sample.splitlines()[0].split(",")),
            "202505_NFe": pd.DataFrame([l.split(",") for l in sample.splitlines()[4:]], columns=sample.splitlines()[0].split(","))
        }
        # converte para formato esperado
        for k in st.session_state.tables:
            st.session_state.tables[k] = st.session_state.tables[k].to_dict(orient='records')
        st.success("Dados de exemplo carregados")
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📤 Carregar Dados", "💬 Consultar", "📊 Evidências & Relatório"])

with tab1:
    st.subheader("Interface A — Carga dos dados")
    if uploaded:
        if st.button("Processar arquivos", type="primary"):
            try:
                tables_dict, dict_data = loader.process(uploaded)
                st.session_state.tables = tables_dict
                st.session_state.dictionary = dict_data
                st.success(f"✓ {len(tables_dict)} tabelas processadas")
            except Exception as e:
                st.error(f"Erro no LoaderAgent: {e}")
                st.session_state.logs.append({"agent":"FallbackAgent","msg":str(e)})

    if st.session_state.tables:
        cols = st.columns(3)
        total_rows = sum(len(v) if isinstance(v,list) else len(v) for v in st.session_state.tables.values())
        cols[0].metric("Tabelas", len(st.session_state.tables))
        cols[1].metric("Linhas totais", total_rows)
        cols[2].metric("Dicionário", "Gerado" if st.session_state.dictionary else "Pendente")

        st.subheader("📘 Dicionário de Dados (SchemaAgent)")
        for tname, d in st.session_state.dictionary.items():
            with st.expander(f"📁 {tname} — {len(d)} colunas"):
                st.dataframe(pd.DataFrame.from_dict(d, orient='index'), use_container_width=True)

        # export
        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Exportar dicionário JSON", json.dumps(st.session_state.dictionary, indent=2, ensure_ascii=False), "dicionario_dados.json", "application/json")
        with c2:
            if st.session_state.logs:
                st.download_button("⬇️ Exportar logs técnicos", json.dumps(st.session_state.logs, indent=2, ensure_ascii=False), "logs_tecnicos.json", "application/json")

with tab2:
    st.subheader("Interface B — Consulta em linguagem natural")
    perguntas_exemplo = [
        "Qual fornecedor recebeu o maior valor no período?",
        "Qual produto apresentou o maior volume comprado?",
        "Qual foi o total gasto em cada mês?",
        "Quais foram os cinco maiores fornecedores?",
        "Qual categoria apresentou maior crescimento nas compras?",
        "Qual o valor total das notas fiscais emitidas?",
        "Quais os 5 emitentes com maior valor total de notas?",
        "Qual UF do destinatário recebeu mais notas fiscais?",
        "Qual a quantidade total por NCM?",
        "Qual CFOP mais utilizado?",
        "Liste as notas fiscais com maior valor"
    ]
    st.write("**Perguntas de teste (clique para usar):**")
    cols = st.columns(3)
    for i,q in enumerate(perguntas_exemplo):
        if cols[i%3].button(q, key=f"q{i}"):
            st.session_state.last_q = q

    query = st.text_input("Digite sua pergunta:", value=st.session_state.get("last_q",""))
    show_plan = st.checkbox("Mostrar Plano JSON antes da execução (recurso avançado Interface CSV)", value=True)
    
    if st.button("🔍 Consultar", type="primary") and query:
        if not st.session_state.tables:
            st.warning("Carregue os dados na aba Carregar Dados primeiro.")
        else:
            try:
                # QueryAgent
                plan: QueryPlan = query_agent.parse(query, st.session_state.tables, st.session_state.dictionary)
                st.session_state.history.append({"pergunta":query, "plano":plan.model_dump()})
                
                if show_plan:
                    with st.expander("🧾 Plano JSON (QueryPlan Pydantic validado)", expanded=True):
                        st.json(plan.model_dump())
                
                # Executor
                result_df = executor.execute(plan, st.session_state.tables)
                
                # VizAgent decide visualização
                viz_type = viz.decide(plan, result_df)
                st.markdown(f"**VizAgent decidiu:** `{viz_type}` | **Intent:** `{plan.intent}` | **Metric:** `{plan.metric}` | **Tabela:** `{plan.table}`")
                
                if viz_type == "text":
                    st.success(f"💰 {plan.raw} → {result_df.iloc[0].to_dict() if not result_df.empty else 'sem dados'}")
                if not result_df.empty:
                    st.dataframe(result_df.head(100), use_container_width=True)
                    if viz_type in ["bar","line","pie"]:
                        viz.render_streamlit(result_df, viz_type, plan)
                else:
                    st.info("Nenhum resultado encontrado.")
                    
            except Exception as e:
                fb = fallback.handle(e, query, st.session_state.tables, st.session_state.dictionary)
                st.error(fb["texto"])
                st.json(fb["plano"])
                if show_plan:
                    st.code(str(e))

with tab3:
    st.subheader("📄 Evidências, Logs e Relatório Técnico")
    if st.session_state.logs:
        st.write("**Logs técnicos por agente:**")
        for entry in st.session_state.logs[-20:]:
            st.text(f"[{entry['agent']}] {entry['msg']}")
    else:
        st.info("Nenhum log ainda.")
    
    if st.session_state.history:
        st.write("**Histórico de consultas:**")
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
    
    st.markdown("""
    ### Relatório Técnico Completo
    O relatório unificado está em `docs/relatorio_tecnico.md` e `docs/relatorio_tecnico.pdf`.
    Inclui:
    - Framework escolhido (LangChain + fallback heurístico)
    - Arquitetura dos 6 agentes especializados
    - Fluxo de funcionamento (diagrama)
    - Decisão de cada agente (como toma decisões)
    - 10+ perguntas com respostas em texto, tabela e gráfico
    - Limitações e próximos passos
    """)
    if Path("docs/relatorio_tecnico.md").exists():
        st.download_button("⬇️ Baixar relatório MD", Path("docs/relatorio_tecnico.md").read_text(encoding="utf-8"), "relatorio_tecnico.md")
