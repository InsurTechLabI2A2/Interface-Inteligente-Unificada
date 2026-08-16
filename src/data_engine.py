"""
ExecutorAgent + VizAgent - execução determinística + visualização
Sem eval, apenas operações whitelist (segurança do Interface CSV)
"""
import pandas as pd
import numpy as np
from typing import Dict
from src.models import QueryPlan
import re

class ExecutorAgent:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn or (lambda a,m: None)

    def _to_num(self, v):
        if v is None or v == '': return 0.0
        s = str(v).strip()
        # remove moeda, espaços
        s = re.sub(r'[^0-9,\.\-]', '', s)
        # trata 12.500,50 -> 12500.50
        if ',' in s and '.' in s:
            s = s.replace('.','').replace(',','.')
        elif ',' in s:
            s = s.replace(',','.')
        try:
            return float(s)
        except:
            try:
                return float(v)
            except:
                return 0.0

    def _find_numeric_col(self, df: pd.DataFrame):
        for c in df.columns:
            low=c.lower()
            if any(k in low for k in ['vnf','vprod','valor','total','vlr']):
                return c
        # senão primeira numérica
        for c in df.columns:
            try:
                pd.to_numeric(df[c].astype(str).str.replace(',','.'))
                return c
            except: pass
        return df.columns[0]

    def execute(self, plan: QueryPlan, tables: Dict):
        self.log_fn("ExecutorAgent", f"Executando intent={plan.intent} metric={plan.metric} table={plan.table}")
        raw_rows = tables.get(plan.table)
        if raw_rows is None:
            raise ValueError(f"Tabela {plan.table} não encontrada")
        df = pd.DataFrame(raw_rows)
        if df.empty:
            return pd.DataFrame()

        # conversão de valor para numérico auxiliar
        if plan.value_col and plan.value_col in df.columns:
            df['_valor_num'] = df[plan.value_col].apply(self._to_num)
        else:
            num_col = self._find_numeric_col(df)
            df['_valor_num'] = df[num_col].apply(self._to_num)
            if not plan.value_col:
                plan.value_col = num_col

        # Execução por intent (whitelist)
        if plan.intent == "aggregate" and plan.metric == "sum":
            total = df['_valor_num'].sum()
            return pd.DataFrame([{"metrica": f"Soma de {plan.value_col}", "valor": total, "tabela": plan.table, "linhas": len(df)}])

        elif plan.intent in ["ranking","group_count","timeseries","growth"]:
            group_col = plan.group_by
            if not group_col or group_col not in df.columns:
                group_col = df.columns[0]
            
            # tratamento especial para timeseries por data
            if plan.intent == "timeseries" and group_col:
                try:
                    df['_data_parsed'] = pd.to_datetime(df[group_col], errors='coerce')
                    df['_mes'] = df['_data_parsed'].dt.to_period('M').astype(str)
                    if df['_mes'].notna().sum() > 0:
                        group_col = '_mes'
                except:
                    pass

            grouped = df.groupby(group_col).agg(total_valor=('_valor_num','sum'), quantidade=('_valor_num','count')).reset_index()
            if plan.metric == "count":
                grouped = grouped.sort_values('quantidade', ascending=(plan.order=='asc'))
            else:
                grouped = grouped.sort_values('total_valor', ascending=(plan.order=='asc'))
            
            grouped = grouped.head(plan.limit)

            if plan.intent == "growth" and len(grouped)>1:
                grouped = grouped.sort_values(group_col)
                grouped['crescimento'] = grouped['total_valor'].pct_change()*100
                grouped['crescimento'] = grouped['crescimento'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")

            return grouped

        elif plan.intent == "list":
            return df.head(plan.limit)

        else:
            # default
            return pd.DataFrame([{"total_linhas": len(df), "tabela": plan.table}])


class VizAgent:
    def decide(self, plan: QueryPlan, result_df: pd.DataFrame) -> str:
        if plan.viz_hint in ["text","table","bar","line","pie"]:
            return plan.viz_hint
        if len(result_df) <= 1:
            return "text"
        if plan.intent in ["timeseries","growth"]:
            return "line"
        if plan.intent == "group_count" and len(result_df) <= 8:
            return "pie"
        if len(result_df) > 1:
            return "bar"
        return "table"

    def render_streamlit(self, df: pd.DataFrame, viz_type: str, plan: QueryPlan):
        import streamlit as st
        if df.empty:
            return
        # identifica colunas
        label_col = df.columns[0]
        value_col = 'total_valor' if 'total_valor' in df.columns else 'quantidade' if 'quantidade' in df.columns else df.columns[1] if len(df.columns)>1 else df.columns[0]
        
        chart_df = df.head(15)
        
        if viz_type == "bar":
            st.bar_chart(chart_df.set_index(label_col)[value_col])
        elif viz_type == "line":
            st.line_chart(chart_df.set_index(label_col)[value_col])
        elif viz_type == "pie":
            # pie via plotly se disponível, senão bar
            try:
                import plotly.express as px
                fig = px.pie(chart_df, names=label_col, values=value_col, title=f"{plan.raw}")
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.bar_chart(chart_df.set_index(label_col)[value_col])
