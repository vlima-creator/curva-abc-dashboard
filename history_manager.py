import sqlite3
import pandas as pd
import json
from datetime import datetime
import os

# Usar caminho relativo para compatibilidade com Streamlit Cloud
DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabela para snapshots gerais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cliente TEXT,
            canal TEXT,
            total_ads INTEGER,
            total_fat REAL,
            total_qty INTEGER,
            conc_a REAL,
            tm_atual REAL,
            fuga_receita_count INTEGER,
            fuga_receita_valor REAL,
            ancoras_count INTEGER,
            ancoras_valor REAL,
            ads_pct REAL,
            ads_valor REAL,
            organic_valor REAL
        )
    ''')
    # Verificar se a coluna cliente existe (para migração de bancos existentes)
    cursor.execute("PRAGMA table_info(snapshots)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'cliente' not in columns:
        cursor.execute("ALTER TABLE snapshots ADD COLUMN cliente TEXT DEFAULT 'Geral'")
    conn.commit()
    conn.close()

def save_snapshot(metrics):
    """
    metrics: dict com as chaves correspondentes às colunas da tabela snapshots
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cols = metrics.keys()
    placeholders = ', '.join(['?'] * len(cols))
    sql = f"INSERT INTO snapshots ({', '.join(cols)}) VALUES ({placeholders})"
    conn.execute(sql, list(metrics.values()))
    conn.commit()
    conn.close()

def get_last_snapshot(cliente, canal):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM snapshots WHERE cliente = ? AND canal = ? ORDER BY timestamp DESC LIMIT 1"
    df = pd.read_sql_query(query, conn, params=(cliente, canal))
    conn.close()
    if df.empty:
        return None
    return df.iloc[0].to_dict()

def get_history(cliente, canal, limit=10):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM snapshots WHERE cliente = ? AND canal = ? ORDER BY timestamp DESC LIMIT ?"
    df = pd.read_sql_query(query, conn, params=(cliente, canal, limit))
    conn.close()
    return df
