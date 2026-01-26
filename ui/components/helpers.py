"""Funções auxiliares de formatação e manipulação de dados."""
import pandas as pd
import numpy as np

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
