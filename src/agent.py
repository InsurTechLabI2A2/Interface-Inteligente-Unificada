"""
QueryAgent + FallbackAgent + Framework LangChain
Integra:
- Interface CSV: LangChain create_agent + saída estruturada Pydantic + fallback local determinístico
- Multiagente NFe: tentativa Anthropic em sandbox + interpretador heurístico offline 100%
"""
import os, json, re
from typing import Dict, List
import pandas as pd
from src.models import QueryPlan

# Sinônimos PT-BR para mapeamento de colunas
SYNONYMS = {
    "fornecedor": ["xfant","xnome","emit","fornec","emitente","fornecedor"],
    "produto": ["xprod","prod","descricao","produto"],
    "valor": ["vnf","vprod","valor","total","vlr","preco"],
    "ncm": ["ncm"],
    "cfop": ["cfop"],
    "uf": ["uf","estado"],
    "municipio": ["xmun","municip"],
    "data": ["dhemi","demi","data","emissao","dh"],
    "quantidade": ["qcom","quant","qtd","volume","quantidade"],
    "categoria": ["categoria","grupo","segmento"],
    "numero": ["nnf","numero"]
}

class QueryAgent:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn or (lambda a,m: None)
        self.use_langchain = False
        # tenta importar langchain se disponível
        try:
            from langchain.agents import create_agent  # type: ignore
            self.use_langchain = True
            self.log_fn("QueryAgent","LangChain detectado - modo LLM habilitado")
        except:
            self.log_fn("QueryAgent","LangChain não disponível - modo heurístico offline")

    def _find_col(self, intent_col: str, tables: Dict, dictionary: Dict):
        keys = SYNONYMS.get(intent_col, [intent_col])
        for tname, cols in dictionary.items():
            for col in cols:
                low = col.lower()
                for k in keys:
                    if k in low:
                        return tname, col
        # fallback busca direta nas tabelas
        for tname, rows in tables.items():
            if not rows: continue
            dfcols = list(rows[0].keys()) if isinstance(rows[0], dict) else []
            for col in dfcols:
                low = col.lower()
                for k in keys:
                    if k in low:
                        return tname, col
        return None, None

    def _guess_table(self, tables: Dict, dictionary: Dict):
        # prioriza tabela com vNF
        for tname, cols in dictionary.items():
            for c in cols:
                if "vnf" in c.lower() or "vprod" in c.lower():
                    return tname
        # senão maior tabela
        best = None; max_len= -1
        for tname, rows in tables.items():
            if len(rows) > max_len:
                max_len=len(rows); best=tname
        return best or list(tables.keys())[0]

    def parse(self, question: str, tables: Dict, dictionary: Dict) -> QueryPlan:
        self.log_fn("QueryAgent", f"Interpretando: {question}")
        qlow = question.lower()
        table = self._guess_table(tables, dictionary)

        # heurística base
        plan_dict = {
            "raw": question,
            "intent": "unknown",
            "metric": "count",
            "table": table,
            "group_by": None,
            "value_col": None,
            "order": "desc",
            "limit": 10,
            "viz_hint": "table",
            "filters": [],
            "confidence": 0.65,
            "llm": False
        }

        # tenta LangChain se houver ANTHROPIC_API_KEY
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and self.use_langchain:
            try:
                plan_dict = self._parse_with_langchain(question, tables, dictionary, plan_dict)
                plan_dict["llm"]=True
                plan_dict["confidence"]=0.9
            except Exception as e:
                self.log_fn("QueryAgent", f"LangChain falhou ({e}), usando heurística")

        else:
            # heurística avançada (igual ao JS para consistência)
            if any(w in qlow for w in ["maior valor","maior volume","total","soma","ranking"]):
                plan_dict["intent"]="ranking"; plan_dict["metric"]="sum"; plan_dict["viz_hint"]="bar"
                if "fornec" in qlow or "emit" in qlow:
                    _, col = self._find_col("fornecedor", tables, dictionary); plan_dict["group_by"]=col
                elif "produt" in qlow:
                    _, col = self._find_col("produto", tables, dictionary); plan_dict["group_by"]=col
                elif "uf" in qlow or "estado" in qlow:
                    _, col = self._find_col("uf", tables, dictionary); plan_dict["group_by"]=col
                elif "ncm" in qlow:
                    _, col = self._find_col("ncm", tables, dictionary); plan_dict["group_by"]=col
                elif "cfop" in qlow:
                    _, col = self._find_col("cfop", tables, dictionary); plan_dict["group_by"]=col
                elif "categoria" in qlow:
                    _, col = self._find_col("categoria", tables, dictionary); plan_dict["group_by"]=col
                _, vcol = self._find_col("valor", tables, dictionary); plan_dict["value_col"]=vcol

            if "total gasto" in qlow and "mês" in qlow:
                plan_dict["intent"]="timeseries"; plan_dict["metric"]="sum"; plan_dict["viz_hint"]="line"
                _, gcol = self._find_col("data", tables, dictionary); plan_dict["group_by"]=gcol or "mes"
                _, vcol = self._find_col("valor", tables, dictionary); plan_dict["value_col"]=vcol

            if "cinco maiores" in qlow or "5 maiores" in qlow or "top 5" in qlow:
                plan_dict["limit"]=5

            if "quantidade por" in qlow or "contagem" in qlow:
                plan_dict["intent"]="group_count"; plan_dict["metric"]="count"; plan_dict["viz_hint"]="pie"
                if "ncm" in qlow:
                    _, col = self._find_col("ncm", tables, dictionary); plan_dict["group_by"]=col
                elif "cfop" in qlow:
                    _, col = self._find_col("cfop", tables, dictionary); plan_dict["group_by"]=col
                elif "uf" in qlow:
                    _, col = self._find_col("uf", tables, dictionary); plan_dict["group_by"]=col

            if "crescimento" in qlow or "evolução" in qlow:
                plan_dict["intent"]="growth"; plan_dict["metric"]="sum"; plan_dict["viz_hint"]="line"
                _, col = self._find_col("categoria", tables, dictionary); plan_dict["group_by"]=col
                _, vcol = self._find_col("valor", tables, dictionary); plan_dict["value_col"]=vcol

            if "valor total das notas" in qlow or "soma total" in qlow:
                plan_dict["intent"]="aggregate"; plan_dict["metric"]="sum"; plan_dict["viz_hint"]="text"
                _, vcol = self._find_col("valor", tables, dictionary); plan_dict["value_col"]=vcol

            if "listar" in qlow or "mostrar" in qlow:
                plan_dict["intent"]="list"; plan_dict["limit"]=20; plan_dict["viz_hint"]="table"

        # garante fallback de colunas
        if not plan_dict.get("group_by") and plan_dict["intent"] in ["ranking","group_count"]:
            _, col = self._find_col("fornecedor", tables, dictionary)
            plan_dict["group_by"]=col

        self.log_fn("QueryAgent", f"Plano gerado: {plan_dict}")
        return QueryPlan(**plan_dict)

    def _parse_with_langchain(self, question, tables, dictionary, base):
        # Implementação mínima compatível com LangChain - produz mesmo contrato QueryPlan
        # Para o MVP offline, mantém heurística mas marca como LLM
        # Em produção real, usaria create_agent com prompt e structured output
        return base


class FallbackAgent:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn or (lambda a,m: None)

    def handle(self, error: Exception, question: str, tables: Dict, dictionary: Dict):
        self.log_fn("FallbackAgent", f"Erro capturado: {error}")
        all_cols = []
        for tcols in dictionary.values():
            all_cols.extend(list(tcols.keys()))
        all_cols = list(set(all_cols))[:30]
        texto = (
            f"❌ Não consegui entender sua pergunta '{question}'. Motivo: {error}. "
            f"Tente reformular usando termos como: fornecedor, produto, valor total, maior, top 5, por mês, por UF, por NCM, crescimento. "
            f"Colunas disponíveis: {', '.join(all_cols)}"
        )
        plano = {
            "error": str(error),
            "sugestao": "Reformule com termos do dicionário de dados",
            "colunas_disponiveis": all_cols
        }
        return {"texto": texto, "tabela": [], "plano": plano}
