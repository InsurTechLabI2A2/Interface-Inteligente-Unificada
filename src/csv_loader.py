"""
LoaderAgent + SchemaAgent - Interface CSV + NFe Unificada
Validação de ZIP, leitura de CSV, inferência de schema, dicionário automático
"""
import zipfile, io, chardet if False else None
import pandas as pd
from typing import Dict, Tuple, List

class LoaderAgent:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn or (lambda a,m: None)
    
    def process(self, uploaded_files) -> Tuple[Dict[str, List[dict]], Dict]:
        """Processa lista de UploadedFile do Streamlit"""
        tables = {}
        for uf in uploaded_files:
            self.log_fn("LoaderAgent", f"Lendo ZIP {uf.name} ({uf.size} bytes)")
            with zipfile.ZipFile(io.BytesIO(uf.read())) as z:
                for name in z.namelist():
                    if not name.lower().endswith('.csv'):
                        continue
                    self.log_fn("LoaderAgent", f"CSV encontrado: {name}")
                    with z.open(name) as f:
                        raw = f.read()
                        # tenta utf-8, senão latin1
                        try:
                            text = raw.decode('utf-8')
                        except:
                            text = raw.decode('latin1')
                        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
                        # limpeza
                        df = df.loc[~(df== '').all(axis=1)]
                        tname = name.split('/')[-1].replace('.csv','').lower()
                        tables[tname] = df.to_dict(orient='records')
                        self.log_fn("LoaderAgent", f"{tname}: {len(df)} linhas, {len(df.columns)} colunas")
        if not tables:
            raise ValueError("Nenhum CSV encontrado nos ZIPs")
        
        # SchemaAgent
        dictionary = {}
        for tname, rows in tables.items():
            if not rows: continue
            df = pd.DataFrame(rows)
            cols = {}
            for col in df.columns:
                samples = df[col].dropna().astype(str).head(20).tolist()
                tipo = self._infer_type(samples)
                cols[col] = {
                    "tipo": tipo,
                    "descricao": self._describe(col),
                    "exemplo": samples[0] if samples else "",
                    "unicos": df[col].nunique()
                }
            dictionary[tname] = cols
        
        self.log_fn("SchemaAgent", f"Dicionário gerado para {len(dictionary)} tabelas")
        return tables, dictionary
    
    def _infer_type(self, samples):
        if not samples: return "texto"
        num = sum(1 for s in samples if self._is_number(s))
        if num/len(samples) > 0.7: return "numérico"
        date = sum(1 for s in samples if self._is_date(s))
        if date/len(samples) > 0.6: return "data"
        return "categórico"
    
    def _is_number(self, s):
        try:
            float(str(s).replace(',','.').replace('R$','').strip())
            return True
        except: return False
    def _is_date(self, s):
        try:
            pd.to_datetime(s, errors='raise')
            return True
        except: return False
    def _describe(self, col):
        m = {
            'xFant':'Nome fantasia do fornecedor/emitente',
            'xNome':'Razão social do emitente',
            'vNF':'Valor total da NF',
            'vProd':'Valor dos produtos',
            'nNF':'Número da NF',
            'dhEmi':'Data e hora de emissão',
            'UF':'Unidade Federativa',
            'NCM':'Nomenclatura Comum do Mercosul',
            'CFOP':'Código Fiscal de Operações',
            'xProd':'Descrição do produto',
            'qCom':'Quantidade comercializada',
            'categoria':'Categoria do produto'
        }
        low = col.lower()
        for k,v in m.items():
            if k.lower() in low: return v
        return "Coluna original do CSV"
