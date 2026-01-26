"""
Classe base abstrata para processadores de dados de canais de venda.
Todos os processadores específicos de canal devem herdar desta classe.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Tuple, Optional


class BaseProcessor(ABC):
    """Classe base para processadores de canal."""
    
    def __init__(self):
        self.canal_name = "Base"
    
    @abstractmethod
    def detect(self, file) -> bool:
        """
        Detecta se o arquivo pertence a este canal.
        
        Args:
            file: Arquivo uploaded pelo usuário
            
        Returns:
            bool: True se o arquivo pertence a este canal
        """
        pass
    
    @abstractmethod
    def process(self, files: list) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Processa os arquivos do canal e retorna DataFrames padronizados.
        
        Args:
            files: Lista de arquivos do canal
            
        Returns:
            Tuple contendo:
            - df_export: DataFrame principal com análise ABC
            - df_logistics: DataFrame com métricas logísticas (ou None)
            - df_ads: DataFrame com métricas de publicidade (ou None)
        """
        pass
    
    def calculate_abc_curve(self, df: pd.DataFrame, revenue_col: str, group_col: str = None) -> pd.DataFrame:
        """
        Calcula a curva ABC baseada no faturamento.
        
        Args:
            df: DataFrame com os dados
            revenue_col: Nome da coluna de faturamento
            group_col: Coluna opcional para agrupar antes do cálculo
            
        Returns:
            DataFrame com coluna 'curva_abc' adicionada
        """
        result = df.copy()
        
        if group_col and group_col in result.columns:
            # Agrupa por produto antes de calcular
            agg_df = result.groupby(group_col)[revenue_col].sum().reset_index()
        else:
            agg_df = result[[revenue_col]].copy()
            agg_df['_id'] = range(len(agg_df))
            group_col = '_id'
        
        # Ordena por faturamento decrescente
        agg_df = agg_df.sort_values(revenue_col, ascending=False)
        
        # Calcula percentual acumulado
        total_revenue = agg_df[revenue_col].sum()
        if total_revenue > 0:
            agg_df['_pct_acum'] = (agg_df[revenue_col].cumsum() / total_revenue) * 100
        else:
            agg_df['_pct_acum'] = 0
        
        # Classifica em curvas
        def classify_curve(pct):
            if pct <= 80:
                return 'A'
            elif pct <= 95:
                return 'B'
            else:
                return 'C'
        
        agg_df['curva_abc'] = agg_df['_pct_acum'].apply(classify_curve)
        
        # Merge de volta ao DataFrame original
        if '_id' in agg_df.columns:
            result['curva_abc'] = agg_df['curva_abc'].values
        else:
            result = result.merge(agg_df[[group_col, 'curva_abc']], on=group_col, how='left')
        
        # Produtos sem vendas ficam como "-"
        result['curva_abc'] = result['curva_abc'].fillna('-')
        result.loc[result[revenue_col] == 0, 'curva_abc'] = '-'
        
        return result
