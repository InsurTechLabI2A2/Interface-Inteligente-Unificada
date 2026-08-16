import unittest
import pandas as pd
import sys
sys.path.append('..')
from src.data_engine import ExecutorAgent
from src.models import QueryPlan

class TestDataEngine(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"xFant":"A","vNF":"1000","NCM":"8471","UF":"SP","xProd":"Notebook","qCom":"10"},
            {"xFant":"B","vNF":"2000","NCM":"8471","UF":"RJ","xProd":"Smartphone","qCom":"20"},
            {"xFant":"A","vNF":"1500","NCM":"9403","UF":"SP","xProd":"Notebook","qCom":"5"},
        ]
        self.tables = {"202401_nfs": self.rows}
        self.executor = ExecutorAgent()

    def test_sum_total(self):
        plan = QueryPlan(raw="total", intent="aggregate", metric="sum", table="202401_nfs", value_col="vNF", viz_hint="text")
        df = self.executor.execute(plan, self.tables)
        self.assertAlmostEqual(df.iloc[0]["valor"], 4500, delta=0.1)

    def test_ranking_fornecedor(self):
        plan = QueryPlan(raw="maior fornecedor", intent="ranking", metric="sum", table="202401_nfs", group_by="xFant", value_col="vNF", limit=2, viz_hint="bar")
        df = self.executor.execute(plan, self.tables)
        self.assertEqual(df.iloc[0]["xFant"], "A") # A tem 2500, B 2000 -> A maior
        # na verdade A=2500, B=2000, então A primeiro
        self.assertEqual(len(df), 2)

    def test_group_count_ncm(self):
        plan = QueryPlan(raw="quantidade por NCM", intent="group_count", metric="count", table="202401_nfs", group_by="NCM", viz_hint="pie")
        df = self.executor.execute(plan, self.tables)
        self.assertEqual(len(df), 2) # 8471 e 9403

    def test_list(self):
        plan = QueryPlan(raw="listar", intent="list", metric="count", table="202401_nfs", limit=2, viz_hint="table")
        df = self.executor.execute(plan, self.tables)
        self.assertEqual(len(df), 2)

if __name__ == '__main__':
    unittest.main()
