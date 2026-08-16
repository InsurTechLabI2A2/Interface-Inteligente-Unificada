"""
Modelos Pydantic - QueryPlan
Contrato entre QueryAgent e ExecutorAgent
Baseado no Interface CSV (LangChain + Pydantic) e Multiagente NFe
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class QueryPlan(BaseModel):
    """Plano estruturado validado que o QueryAgent produz e o ExecutorAgent executa"""
    raw: str = Field(description="Pergunta original em linguagem natural")
    intent: Literal["ranking","aggregate","group_count","timeseries","growth","list","unknown"] = Field(default="unknown")
    metric: Literal["sum","avg","count","count_distinct","max","min"] = Field(default="count")
    table: str = Field(description="Tabela alvo escolhida pelo SchemaAgent")
    group_by: Optional[str] = Field(default=None, description="Coluna de agrupamento")
    value_col: Optional[str] = Field(default=None, description="Coluna de valor para agregação")
    order: Literal["asc","desc"] = Field(default="desc")
    limit: int = Field(default=10, ge=1, le=1000)
    viz_hint: Literal["text","table","bar","line","pie"] = Field(default="table")
    filters: List[dict] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0, le=1)
    llm: bool = Field(default=False, description="Se foi enriquecido por LLM")

    class Config:
        json_schema_extra = {
            "example": {
                "raw": "Qual fornecedor recebeu o maior valor no período?",
                "intent": "ranking",
                "metric": "sum",
                "table": "202401_nfs",
                "group_by": "xFant",
                "value_col": "vNF",
                "order": "desc",
                "limit": 5,
                "viz_hint": "bar"
            }
        }
