"""Funções auxiliares de formatação e manipulação de dados."""
import pandas as pd
import numpy as np
import io

def br_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_int(x) -> str:
    try:
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return "-"

def safe_div(a, b):
    try:
        if b and b != 0:
            return a / b
    except Exception:
        pass
    return np.nan

def pct(x, decimals=1) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{round(float(x) * 100, decimals)}%"
    except Exception:
        return "-"

def to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    csv = dataframe.to_csv(index=False, sep=";", encoding="utf-8-sig")
    return csv.encode("utf-8-sig")

def to_xlsx_bytes(dataframe: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    # Usando xlsxwriter como engine para formatações avançadas
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Dados')
        workbook = writer.book
        worksheet = writer.sheets['Dados']
        
        # --- DEFINIÇÃO DE FORMATOS ---
        
        # Formato para o Cabeçalho (Azul escuro com texto branco, negrito)
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#1F4E78',
            'font_color': 'white',
            'border': 1
        })
        
        # Formato para Moeda (R$)
        money_format = workbook.add_format({
            'num_format': 'R$ #,##0.00',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Formato para Porcentagem (%)
        pct_format = workbook.add_format({
            'num_format': '0.0%',
            'valign': 'vcenter',
            'align': 'center',
            'border': 1
        })
        
        # Formato para Números Inteiros
        int_format = workbook.add_format({
            'num_format': '#,##0',
            'valign': 'vcenter',
            'align': 'center',
            'border': 1
        })
        
        # Formato Padrão (Texto)
        text_format = workbook.add_format({
            'valign': 'vcenter',
            'border': 1
        })

        # --- APLICAÇÃO DE FORMATOS E AJUSTE DE COLUNAS ---
        
        for i, col in enumerate(dataframe.columns):
            # Calcular largura ideal da coluna
            max_len = max(
                dataframe[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            column_width = min(max(max_len, 12), 60) # Mínimo 12, Máximo 60
            
            col_lower = col.lower()
            
            # Aplicar formato baseado no nome da coluna
            if any(kw in col_lower for kw in ['fat', 'faturamento', 'venda', 'preço', 'tm', 'valor', 'receita', 'custo', 'lucro', 'ticket']):
                worksheet.set_column(i, i, column_width, money_format)
            elif any(kw in col_lower for kw in ['%', 'taxa', 'conversão', 'rejeição', 'pct', 'margem', 'roas', 'ads']):
                worksheet.set_column(i, i, column_width, pct_format)
            elif any(kw in col_lower for kw in ['qtd', 'quantidade', 'unidades', 'pedidos', 'visitantes', 'visualizações', 'estoque', 'rank', 'posição']):
                worksheet.set_column(i, i, column_width, int_format)
            else:
                worksheet.set_column(i, i, column_width, text_format)
                
        # Aplicar o formato de cabeçalho explicitamente (sobrescrevendo o padrão do pandas)
        for col_num, value in enumerate(dataframe.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Congelar a primeira linha (cabeçalho)
        worksheet.freeze_panes(1, 0)
        
        # Ativar filtro automático em todas as colunas
        worksheet.autofilter(0, 0, len(dataframe), len(dataframe.columns) - 1)

    return output.getvalue()

def ensure_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Garante que todas as colunas existam antes do recorte (evita KeyError)."""
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols].copy()

rank = {"-": 0, "C": 1, "B": 2, "A": 3}

periods = [
    ("0-30", "Curva 0-30", "Qntd 0-30", "Fat. 0-30"),
    ("31-60", "Curva 31-60", "Qntd 31-60", "Fat. 31-60"),
    ("61-90", "Curva 61-90", "Qntd 61-90", "Fat. 61-90"),
    ("91-120", "Curva 91-120", "Qntd 91-120", "Fat. 91-120"),
]

QTY_COLS = ["Qntd 0-30", "Qntd 31-60", "Qntd 61-90", "Qntd 91-120"]
