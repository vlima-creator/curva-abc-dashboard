"""
Fábrica de processadores de canal.
Detecta automaticamente o canal e retorna o processador apropriado.
"""
from typing import List, Tuple, Optional
import pandas as pd
from .mercado_livre_processor import MercadoLivreProcessor
from .shopee_processor import ShopeeProcessor


def detect_channel(files: list) -> str:
    """
    Detecta o canal (Mercado Livre ou Shopee) baseado nos arquivos.
    Retorna: nome do canal
    """
    if not files:
        raise ValueError("Nenhum arquivo fornecido")
    
    # Tenta detectar Shopee primeiro (múltiplos arquivos ou colunas específicas)
    shopee_proc = ShopeeProcessor()
    if shopee_proc.detect(files[0]):
        return "Shopee"
    
    # Caso contrário, assume Mercado Livre
    return "Mercado Livre"


def detect_and_process(files: list) -> Tuple[str, pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Detecta o canal dos arquivos e processa os dados.
    
    Args:
        files: Lista de arquivos uploaded pelo usuário
        
    Returns:
        Tuple contendo:
        - canal_name: Nome do canal detectado
        - df_export: DataFrame principal com análise ABC
        - df_logistics: DataFrame com métricas logísticas (ou None)
        - df_ads: DataFrame com métricas de publicidade (ou None)
        
    Raises:
        ValueError: Se o canal não puder ser detectado ou se houver erro no processamento
    """
    if not files or len(files) == 0:
        raise ValueError("Nenhum arquivo fornecido")
    
    # Lista de processadores disponíveis
    processors = [
        MercadoLivreProcessor(),
        ShopeeProcessor()
    ]
    
    # Tenta detectar o canal do primeiro arquivo
    detected_processor = None
    for processor in processors:
        if processor.detect(files[0]):
            detected_processor = processor
            break
    
    if detected_processor is None:
        raise ValueError(
            "Não foi possível detectar o canal do arquivo. "
            "Certifique-se de que está usando um relatório válido do Mercado Livre ou Shopee."
        )
    
    # Processa os arquivos
    try:
        df_export, df_logistics, df_ads = detected_processor.process(files)
        
        # Adiciona coluna de canal
        df_export['_canal'] = detected_processor.canal_name
        
        return detected_processor.canal_name, df_export, df_logistics, df_ads
        
    except Exception as e:
        raise ValueError(f"Erro ao processar arquivos do canal {detected_processor.canal_name}: {str(e)}")


def get_available_channels() -> List[str]:
    """
    Retorna lista de canais disponíveis no sistema.
    """
    return ["Mercado Livre", "Shopee"]
