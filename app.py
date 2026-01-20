import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
import io

# =========================
# Helpers (definidos cedo para evitar NameError em reruns)
# =========================

def br_money(x) -> str:
    """Formata valor em R$ de forma segura."""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"


def bm(x) -> str:
    """Wrapper simples e seguro para moeda."""
    return br_money(x)


def br_int(x) -> str:
    try:
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return "-"


def pct(x, decimals=2):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{round(float(x) * 100, decimals)}%"
    except Exception:
        return "-"


def safe_div(a, b):
    try:
        if b and b != 0:
            return a / b
    except Exception:
        pass
    return np.nan


st.set_page_config(
    page_title="Curva ABC, Diagnóstico e Ações",
    layout="wide"
)

# =========================
# Estilo premium (dark)
# =========================
st.markdown(
    """
<style>
.block-container {padding-top: 1.35rem; padding-bottom: 2.5rem;}
h1, h2, h3 {letter-spacing: -0.3px;}
hr {opacity: 0.25;}

.premium-card {
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.03);
  border-radius: 16px;
  padding: 16px;
  margin: 10px 0 14px 0;
}

.premium-title {
  font-size: 0.92rem;
  opacity: 0.85;
  margin-bottom: 6px;
}

.premium-value {
  font-size: 1.35rem;
  font-weight: 700;
  margin-top: 2px;
}

.premium-sub {
  opacity: 0.75;
  font-size: 0.85rem;
  margin-top: 6px;
}

div.stDownloadButton button,
div.stButton button {
  border-radius: 12px !important;
  padding: 0.55rem 0.85rem !important;
}

div[data-testid="stDataFrame"] {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  overflow: hidden;
}

header[data-testid="stHeader"] {
  background: rgba(0,0,0,0);
}

header[data-testid="stHeader"] * {
  color: rgba(255,255,255,0.85);
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Header + período do dashboard
# =========================
_period_options = ["0-30", "31-60", "61-90", "91-120"]
if "period_sel" not in st.session_state:
    st.session_state["period_sel"] = "0-30"

# Selectbox do período no topo, com cara de badge
col_h1, col_h2 = st.columns([3.2, 1.0])
with col_h1:
    st.markdown(
        """
<div style="padding:10px 4px 6px 4px;margin-bottom:2px;">
  <div style="font-size:32px;font-weight:800;line-height:1.12;letter-spacing:-0.4px;">
    Curva ABC, Diagnóstico e Ações
  </div>
  <div style="opacity:0.75;margin-top:4px;font-size:14px;line-height:1.25;">
    Decisão rápida por frente e prioridade.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with col_h2:
    # o widget é o "badge clicável"
    st.selectbox(
        "Período do dashboard",
        options=_period_options,
        key="period_sel",
        label_visibility="collapsed",
    )
    st.markdown(
        f"""
<div style="margin-top:6px;display:flex;justify-content:flex-end;">
  <div style="padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,0.14);background:rgba(255,255,255,0.06);font-size:12px;opacity:0.9;white-space:nowrap;">
    Período: {st.session_state['period_sel']}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin:10px 0 14px 0;opacity:0.15;'>", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def br_money(x) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"

def bm(x) -> str:
    """Wrapper simples e seguro para moeda."""
    return br_money(x)


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

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    csv = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    return csv.encode("utf-8-sig")


def to_excel_bytes(sheets: dict, filename_hint: str = "relatorio") -> bytes:
    """Gera um XLSX em memória com múltiplas abas."""
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, sdf in sheets.items():
            safe_name = str(name)[:31] if name else "Sheet1"
            sdf.to_excel(writer, index=False, sheet_name=safe_name)
    bio.seek(0)
    return bio.getvalue()

def ensure_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols].copy()

def pct(x, decimals=2):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{round(float(x) * 100, decimals)}%"
    except Exception:
        return "-"

rank = {"-": 0, "C": 1, "B": 2, "A": 3}

PERIODS = [
    ("0-30", "Curva 0-30", "Qntd 0-30", "Fat. 0-30"),
    ("31-60", "Curva 31-60", "Qntd 31-60", "Fat. 31-60"),
    ("61-90", "Curva 61-90", "Qntd 61-90", "Fat. 61-90"),
    ("91-120", "Curva 91-120", "Qntd 91-120", "Fat. 91-120"),
]

QTY_COLS = ["Qntd 0-30", "Qntd 31-60", "Qntd 61-90", "Qntd 91-120"]
FAT_COLS = ["Fat. 0-30", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120"]
CURVE_COLS = ["Curva 0-30", "Curva 31-60", "Curva 61-90", "Curva 91-120"]

# =========================
# Loaders
# =========================
@st.cache_data
def load_main(file) -> pd.DataFrame:
    df = pd.read_excel(file, sheet_name="Export")

    for col in QTY_COLS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in FAT_COLS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in CURVE_COLS:
        if col not in df.columns:
            df[col] = "-"
        df[col] = df[col].fillna("-").astype(str).str.strip()

    if "MLB" not in df.columns:
        df["MLB"] = ""
    if "Título" not in df.columns:
        if "Titulo" in df.columns:
            df["Título"] = df["Titulo"]
        else:
            df["Título"] = ""

    df["MLB"] = df["MLB"].astype(str).str.strip()
    df["Título"] = df["Título"].astype(str).str.strip()

    return df

@st.cache_data
def load_enrich(file) -> pd.DataFrame:
    if file is None:
        return pd.DataFrame()

    name = getattr(file, "name", "").lower()
    if name.endswith(".csv"):
        edf = pd.read_csv(file, sep=None, engine="python")
    else:
        edf = pd.read_excel(file)

    edf.columns = [c.strip() for c in edf.columns]

    if "MLB" not in edf.columns:
        for alt in ["mlb", "Mlb", "sku", "SKU", "id", "ID"]:
            if alt in edf.columns:
                edf = edf.rename(columns={alt: "MLB"})
                break

    if "MLB" not in edf.columns:
        return pd.DataFrame()

    edf["MLB"] = edf["MLB"].astype(str).str.strip()

    for col in ["custo_unitario", "margem_percentual", "investimento_ads"]:
        if col in edf.columns:
            edf[col] = pd.to_numeric(edf[col], errors="coerce")

    if "margem_percentual" in edf.columns:
        m = edf["margem_percentual"]
        edf["margem_percentual"] = np.where(m > 1, m / 100.0, m)

    keep = [c for c in ["MLB", "custo_unitario", "margem_percentual", "investimento_ads"] if c in edf.columns]
    edf = edf[keep].drop_duplicates(subset=["MLB"], keep="last")

    return edf


# =========================
# Status (ação em andamento)
# Persistência: enquanto o app estiver rodando.
# =========================
if "mlb_status" not in st.session_state:
    st.session_state["mlb_status"] = {}  # {mlb: status}

STATUS_OPTIONS = ["Novo", "Em andamento", "Concluído", "Pausado"]

def get_status(mlb: str) -> str:
    mlb = str(mlb).strip()
    return st.session_state["mlb_status"].get(mlb, "Novo")

def set_status(mlb: str, status: str):
    mlb = str(mlb).strip()
    if status not in STATUS_OPTIONS:
        status = "Novo"
    st.session_state["mlb_status"][mlb] = status
# =========================
# Uploads
# =========================
with st.container(border=True):
    st.subheader("Arquivos")
    col_u1, col_u2 = st.columns([1.2, 1.0])
    with col_u1:
        main_file = st.file_uploader("Arquivo Curva ABC (Excel)", type=["xlsx"])
        st.session_state["_main_file"] = main_file
    with col_u2:
        enrich_file = st.file_uploader(
            "Opcional: arquivo com custo, margem e investimento em ads por MLB",
            type=["xlsx", "csv"],
            key="enrich",
        )

if not main_file:
    st.info("Envie o arquivo da Curva ABC para carregar o dashboard.")
    st.stop()

df = load_main(main_file)
edf = load_enrich(enrich_file)

# =========================
# Sidebar, painel de comando
# =========================
st.sidebar.header("Painel de comando")

page = st.sidebar.radio(
    "Navegação",
    options=["Visão geral", "Diagnóstico e riscos", "Plano tático e exportação"],
    index=0,
)

st.sidebar.subheader("Filtros")
curva_filtro = st.sidebar.multiselect(
    "Curvas para incluir",
    options=["A", "B", "C", "-"],
    default=["A", "B", "C", "-"]
)

st.sidebar.subheader("Parâmetros estratégicos")
tacos_limite = st.sidebar.number_input("TACOS máximo aceitável", min_value=0.0, max_value=1.0, value=0.15, step=0.01)
margem_pos_ads_min = st.sidebar.number_input("Margem pós ads mínima", min_value=-1.0, max_value=1.0, value=0.08, step=0.01)
ticket_min_escala = st.sidebar.number_input("Ticket mínimo para escalar", min_value=0.0, value=50.0, step=5.0)
modo_conservador = st.sidebar.checkbox("Modo conservador", value=False)

if modo_conservador:
    tacos_limite = min(tacos_limite, 0.12)
    margem_pos_ads_min = max(margem_pos_ads_min, 0.10)

st.sidebar.subheader("Busca")
search_text = st.sidebar.text_input("Buscar por MLB ou Título", value="").strip().lower()

# =========================
# Base dataframe + merge opcional
# =========================
mask_any = (
    df["Curva 0-30"].isin(curva_filtro) |
    df["Curva 31-60"].isin(curva_filtro) |
    df["Curva 61-90"].isin(curva_filtro) |
    df["Curva 91-120"].isin(curva_filtro)
)
df_f = df[mask_any].copy()

if not edf.empty:
    df_f = df_f.merge(edf, on="MLB", how="left")

if search_text:
    df_f = df_f[
        df_f["MLB"].astype(str).str.lower().str.contains(search_text) |
        df_f["Título"].astype(str).str.lower().str.contains(search_text)
    ].copy()

# =========================
# Métricas base
# =========================
df_f["Qtd total"] = df_f[QTY_COLS].sum(axis=1)
df_f["Fat total"] = df_f[FAT_COLS].sum(axis=1)
df_f["TM total"] = np.where(df_f["Qtd total"] > 0, df_f["Fat total"] / df_f["Qtd total"], np.nan)

for p in ["0-30", "31-60", "61-90", "91-120"]:
    df_f[f"rank_{p}"] = df_f[f"Curva {p}"].map(rank).fillna(0).astype(int)

df_f["queda_recente"] = df_f["rank_0-30"] < df_f["rank_31-60"]
df_f["queda_forte"] = (df_f["rank_31-60"] - df_f["rank_0-30"]) >= 2

# KPIs por período (ponderados)
kpi_rows = []
for p, cc, qq, ff in PERIODS:
    qty = int(df_f[qq].sum())
    fat = float(df_f[ff].sum())
    tm = safe_div(fat, qty)
    kpi_rows.append({"Período": p, "Qtd": qty, "Faturamento": fat, "Ticket médio": tm})
kpi_df = pd.DataFrame(kpi_rows)

# =========================
# Métricas financeiras (opcionais)
# =========================
df_f["preco_medio_0_30"] = np.where(df_f["Qntd 0-30"] > 0, df_f["Fat. 0-30"] / df_f["Qntd 0-30"], np.nan)

df_f["lucro_bruto_estimado_0_30"] = np.nan
if "custo_unitario" in df_f.columns:
    df_f["lucro_bruto_estimado_0_30"] = (df_f["preco_medio_0_30"] - df_f["custo_unitario"]) * df_f["Qntd 0-30"]

if "margem_percentual" in df_f.columns:
    fill_mask = df_f["lucro_bruto_estimado_0_30"].isna()
    df_f.loc[fill_mask, "lucro_bruto_estimado_0_30"] = df_f.loc[fill_mask, "Fat. 0-30"] * df_f.loc[fill_mask, "margem_percentual"]

if "investimento_ads" in df_f.columns:
    df_f["tacos_0_30"] = np.where(df_f["Fat. 0-30"] > 0, df_f["investimento_ads"] / df_f["Fat. 0-30"], np.nan)
    df_f["roas_0_30"] = np.where(df_f["investimento_ads"] > 0, df_f["Fat. 0-30"] / df_f["investimento_ads"], np.nan)
    df_f["lucro_pos_ads_0_30"] = df_f["lucro_bruto_estimado_0_30"] - df_f["investimento_ads"]
    df_f["margem_pos_ads_%_0_30"] = np.where(df_f["Fat. 0-30"] > 0, df_f["lucro_pos_ads_0_30"] / df_f["Fat. 0-30"], np.nan)
else:
    df_f["tacos_0_30"] = np.nan
    df_f["roas_0_30"] = np.nan
    df_f["lucro_pos_ads_0_30"] = np.nan
    df_f["margem_pos_ads_%_0_30"] = np.nan

def classifica_risco(row):
    has_any = False
    for c in ["custo_unitario", "margem_percentual", "investimento_ads"]:
        if c in row.index and pd.notna(row.get(c)):
            has_any = True
            break
    if not has_any:
        return "Sem dados (opcional)"

    if pd.notna(row.get("lucro_pos_ads_0_30")) and row["lucro_pos_ads_0_30"] < 0:
        return "Risco alto, prejuízo"

    if pd.notna(row.get("tacos_0_30")) and row["tacos_0_30"] > tacos_limite:
        return "Risco médio, tacos alto"

    if pd.notna(row.get("margem_pos_ads_%_0_30")) and row["margem_pos_ads_%_0_30"] >= margem_pos_ads_min:
        return "Oportunidade, margem boa"

    return "Ok, monitorar"

df_f["risco_lucro"] = df_f.apply(classifica_risco, axis=1)

# =========================
# Segmentações atuais (regras mantidas)
# =========================
anchors = df_f[
    (df_f["Curva 0-30"] == "A") &
    (df_f["Curva 31-60"] == "A") &
    (df_f["Curva 61-90"] == "A") &
    (df_f["Curva 91-120"] == "A")
].copy().sort_values("Fat total", ascending=False)

prev_good_31 = df_f["Curva 31-60"].isin(["A", "B"])
prev_good_61 = df_f["Curva 61-90"].isin(["A", "B"])
now_bad = df_f["Curva 0-30"].isin(["C", "-"])

drop_alert = df_f[now_bad & (prev_good_31 | prev_good_61)].copy()
drop_alert["Fat anterior ref"] = np.where(
    prev_good_31.loc[drop_alert.index],
    drop_alert["Fat. 31-60"],
    drop_alert["Fat. 61-90"]
)
drop_alert["Perda estimada"] = (drop_alert["Fat anterior ref"] - drop_alert["Fat. 0-30"]).clip(lower=0.0)
drop_alert = drop_alert.sort_values("Perda estimada", ascending=False)

perda_total = float(drop_alert["Perda estimada"].fillna(0).sum())

rise_to_A = df_f[
    (df_f["Curva 0-30"] == "A") &
    (
        df_f["Curva 31-60"].isin(["B", "C", "-"]) |
        df_f["Curva 61-90"].isin(["B", "C", "-"]) |
        df_f["Curva 91-120"].isin(["B", "C", "-"])
    )
].copy().sort_values("Fat. 0-30", ascending=False)

hist_qty = df_f["Qntd 31-60"] + df_f["Qntd 61-90"] + df_f["Qntd 91-120"]
hist_fat = df_f["Fat. 31-60"] + df_f["Fat. 61-90"] + df_f["Fat. 91-120"]
df_f["TM histórico"] = np.where(hist_qty > 0, hist_fat / hist_qty, np.nan)

dead_stock = df_f[(df_f["Fat. 0-30"] == 0) & (hist_fat > 0)].copy()
dead_stock_combo = dead_stock[dead_stock["TM histórico"] < 35].copy().sort_values("TM histórico", ascending=True)

tmp = df_f.copy()
tmp["c_count"] = (tmp[CURVE_COLS] == "C").sum(axis=1)
c_rec = tmp[tmp["c_count"] >= 3].copy()

no_sales_90 = df_f[(df_f["Qntd 0-30"] == 0) & (df_f["Qntd 31-60"] == 0) & (df_f["Qntd 61-90"] == 0)].copy()
no_sales_60 = df_f[(df_f["Qntd 0-30"] == 0) & (df_f["Qntd 31-60"] == 0)].copy()

revitalize = df_f[
    df_f["queda_recente"] &
    (
        ((df_f["Qntd 0-30"] >= 30) & (df_f["Qntd 0-30"] <= 40)) |
        (((df_f["Qntd 31-60"] >= 30) & (df_f["Qntd 31-60"] <= 40)) & (df_f["Qntd 0-30"] <= 10)) |
        (df_f["queda_forte"] & (df_f["Qntd 0-30"] >= 1) & (df_f["Qntd 0-30"] <= 25))
    )
].copy()

inactivate = df_f[
    (df_f.index.isin(no_sales_90.index)) |
    (
        (df_f.index.isin(no_sales_60.index)) &
        (df_f["Curva 0-30"].isin(["-", "C"])) &
        (df_f["queda_recente"])
    ) |
    (
        (df_f.index.isin(c_rec.index)) &
        (df_f["Qntd 0-30"] == 0) &
        (df_f["Qntd 31-60"] == 0)
    )
].copy()

opp_50_60 = df_f[
    ((df_f["Qntd 0-30"] >= 50) & (df_f["Qntd 0-30"] <= 60)) |
    ((df_f["Qntd 31-60"] >= 50) & (df_f["Qntd 31-60"] <= 60))
].copy()

# =========================
# Ação curta + Plano 15 e 30
# =========================
def action_short(row, group_label: str) -> str:
    curva0 = row.get("Curva 0-30", "-")
    risk = row.get("risco_lucro", "Sem dados (opcional)")
    tm = row.get("TM total", np.nan)

    if group_label == "LIMPEZA, Parado":
        if row.name in dead_stock_combo.index:
            return "Combo ou liquidação"
        return "Pausar e limpar catálogo"

    if group_label == "CORREÇÃO, Fuga de receita":
        return "Corrigir oferta e recuperar"

    if group_label == "CORREÇÃO, Revitalizar":
        return "Revitalizar com ajustes"

    if group_label == "ATAQUE, Crescimento":
        if pd.notna(tm) and float(tm) >= ticket_min_escala:
            return "Escalar com controle"
        return "Escalar com cautela"

    if group_label == "DEFESA, Âncora":
        if risk in ["Risco alto, prejuízo", "Risco médio, tacos alto"]:
            return "Defender sem escalar"
        return "Defender e escalar"

    if curva0 == "A":
        return "Otimizar e manter"
    if curva0 in ["B", "C"]:
        return "Otimizar e decidir foco"
    return "Reavaliar continuidade"

def action_bundle(row, group_label: str):
    risco = row.get("risco_lucro", "Sem dados (opcional)")
    tacos = row.get("tacos_0_30", np.nan)
    lucro_pos = row.get("lucro_pos_ads_0_30", np.nan)

    detalhe_risco = ""
    if risco != "Sem dados (opcional)":
        detalhe_risco = f" Risco: {risco}."
        if pd.notna(tacos):
            detalhe_risco += f" TACOS 0-30: {pct(tacos)}."
        if pd.notna(lucro_pos):
            detalhe_risco += f" Lucro pós ads 0-30: {bm(lucro_pos)}."

    if group_label == "LIMPEZA, Parado":
        if row.name in dead_stock_combo.index:
            return (
                f"Liquidação ou combos.{detalhe_risco}",
                "Dia 1 a 5: montar combo com âncoras ou itens B. Objetivo é giro.\nDia 6 a 15: ajustar preço e oferta do anúncio.",
                "Semana 1: criar kits e variações.\nSemana 2 a 4: manter o que girar. Se não girar, caminhar para inativação."
            )
        return (
            f"Inativar ou pausar.{detalhe_risco}",
            "Dia 1 a 3: confirmar anúncio ativo, estoque e preço. Se estiver tudo certo e não vende, pausar.\nDia 4 a 15: realocar foco para itens com giro.",
            "Semana 1: decidir manter no catálogo ou retirar.\nSemana 2 a 4: se não reagir, inativar definitivo."
        )

    if group_label == "CORREÇÃO, Fuga de receita":
        return (
            f"Correção imediata de fuga de receita.{detalhe_risco}",
            "Dia 1 a 2: checar ruptura, prazo, reputação e concorrência.\nDia 3 a 7: ajustar preço e frete.\nDia 8 a 15: mídia leve com termos exatos, cortar desperdício.",
            "Semana 1: ajustar título e atributos.\nSemana 2: otimizar página para conversão.\nSemana 3 a 4: manter só o que dá venda."
        )

    if group_label == "CORREÇÃO, Revitalizar":
        return (
            f"Revitalizar com ajuste rápido.{detalhe_risco}",
            "Dia 1 a 4: auditoria do anúncio, preço, frete, título, fotos e estoque.\nDia 5 a 10: campanha leve.\nDia 11 a 15: aumentar só onde tiver venda.",
            "Semana 1: reorganizar variações.\nSemana 2: testar kit ou condição.\nSemana 3 a 4: se não reagir, reduzir prioridade."
        )

    if group_label == "DEFESA, Âncora":
        return (
            f"Defesa e escala controlada.{detalhe_risco}",
            "Dia 1 a 3: garantir estoque.\nDia 4 a 10: melhorar conversão.\nDia 11 a 15: aumentar orçamento em passos pequenos.",
            "Semana 1: separar campanhas por intenção.\nSemana 2: teste pequeno de preço.\nSemana 3 a 4: escalar com controle de custo."
        )

    if group_label == "ATAQUE, Crescimento":
        return (
            f"Ataque para consolidar crescimento.{detalhe_risco}",
            "Dia 1 a 5: identificar gatilho e replicar.\nDia 6 a 10: ampliar exposição em termos rentáveis.\nDia 11 a 15: reforçar página do anúncio.",
            "Semana 1: campanhas separadas.\nSemana 2: proteger ticket.\nSemana 3 a 4: escalar sem travar estoque."
        )

    return (
        f"Otimizar e monitorar.{detalhe_risco}",
        "Dia 1 a 15: melhorar conversão e cortar desperdício.",
        "Semana 1 a 4: manter o que performa e ajustar o que cai."
    )

def frente_bucket(idx):
    if idx in anchors.index:
        return "DEFESA, Âncora"
    if idx in drop_alert.index:
        return "CORREÇÃO, Fuga de receita"
    if idx in revitalize.index:
        return "CORREÇÃO, Revitalizar"
    if idx in rise_to_A.index or idx in opp_50_60.index:
        return "ATAQUE, Crescimento"
    if idx in dead_stock_combo.index or idx in inactivate.index:
        return "LIMPEZA, Parado"
    return "Otimização"

plan = df_f.copy()
plan["Frente"] = [frente_bucket(i) for i in plan.index]
plan["Ação curta"] = plan.apply(lambda r: action_short(r, r["Frente"]), axis=1)

bundles = plan.apply(lambda r: action_bundle(r, r["Frente"]), axis=1, result_type="expand")
plan["Ação sugerida"] = bundles[0]
plan["Plano 15 dias"] = bundles[1]
plan["Plano 30 dias"] = bundles[2]

# =========================
# Score de prioridade (ranking)
# =========================
def normalize_series(s: pd.Series) -> pd.Series:
    s2 = pd.to_numeric(s, errors="coerce")
    if s2.notna().sum() == 0:
        return pd.Series(np.zeros(len(s2)), index=s2.index)
    mn = float(s2.min())
    mx = float(s2.max())
    if mx - mn == 0:
        return pd.Series(np.zeros(len(s2)), index=s2.index)
    return (s2 - mn) / (mx - mn)

plan["impacto_queda"] = plan.get("Perda estimada", pd.Series(np.zeros(len(plan)), index=plan.index)).fillna(0.0)
plan["impacto_fat0"] = plan["Fat. 0-30"].fillna(0.0)
plan["impacto_lucro"] = plan.get("lucro_pos_ads_0_30", pd.Series(np.zeros(len(plan)), index=plan.index)).fillna(0.0)

n_queda = normalize_series(plan["impacto_queda"])
n_fat0 = normalize_series(plan["impacto_fat0"])
n_lucro = normalize_series(plan["impacto_lucro"])

score = (0.40 * n_queda) + (0.30 * n_lucro) + (0.20 * n_fat0)

bonus = np.zeros(len(plan))
bonus += np.where(plan["Frente"] == "CORREÇÃO, Fuga de receita", 0.20, 0.0)
bonus += np.where(plan["Frente"] == "ATAQUE, Crescimento", 0.10, 0.0)
bonus += np.where(plan["Frente"] == "DEFESA, Âncora", 0.05, 0.0)
bonus -= np.where(plan["Frente"] == "LIMPEZA, Parado", 0.05, 0.0)

bonus += np.where(plan["risco_lucro"] == "Oportunidade, margem boa", 0.10, 0.0)
bonus -= np.where(plan["risco_lucro"] == "Risco alto, prejuízo", 0.20, 0.0)

plan["Score prioridade"] = (score + bonus).clip(lower=0.0)

def prioridade_label(x):
    try:
        if x >= 0.75:
            return "P1, agora"
        if x >= 0.50:
            return "P2, esta semana"
        if x >= 0.30:
            return "P3, este mês"
        return "P4, monitorar"
    except Exception:
        return "P4, monitorar"

plan["Prioridade"] = plan["Score prioridade"].apply(prioridade_label)

# =========================
# Cards executivos topo (período selecionado)
# =========================
period_sel = st.session_state.get("period_sel", "0-30")
curve_col_sel = f"Curva {period_sel}"
qty_col_sel = f"Qntd {period_sel}"
fat_col_sel = f"Fat. {period_sel}"

# defensivo, se alguma coluna não existir
for _c in [curve_col_sel, qty_col_sel, fat_col_sel]:
    if _c not in df_f.columns:
        # cai para 0-30 como fallback
        period_sel = "0-30"
        curve_col_sel = "Curva 0-30"
        qty_col_sel = "Qntd 0-30"
        fat_col_sel = "Fat. 0-30"
        break

total_ads = len(df_f)
fat_sel_total = float(df_f[fat_col_sel].sum())
qty_sel_total = int(df_f[qty_col_sel].sum())
tm_sel_total = safe_div(fat_sel_total, qty_sel_total)

# Concentração Curva A no período selecionado
fat_sel_A = float(df_f.loc[df_f[curve_col_sel] == "A", fat_col_sel].sum())
conc_A_sel = safe_div(fat_sel_A, fat_sel_total)

# Distribuição de curvas no período selecionado
dist_sel = df_f[curve_col_sel].value_counts().reindex(["A","B","C","-"]).fillna(0).astype(int)

# Itens em risco continua baseado em lucro/tacos do 0-30 (regras atuais)
itens_risco = int((df_f["risco_lucro"].isin(["Risco alto, prejuízo", "Risco médio, tacos alto"])).sum())

def premium_metric(title, value, subtitle=None):
    sub_html = f'<div class="premium-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
<div class="premium-card">
  <div class="premium-title">{title}</div>
  <div class="premium-value">{value}</div>
  {sub_html}
</div>
""",
        unsafe_allow_html=True,
    )

with st.container():
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        premium_metric("Anúncios", br_int(total_ads))
    with c2:
        premium_metric(f"Faturamento {period_sel}", bm(fat_sel_total))
    with c3:
        premium_metric(f"Quantidade {period_sel}", br_int(qty_sel_total))
    with c4:
        premium_metric(f"Ticket médio {period_sel}", bm(tm_sel_total))
    with c5:
        premium_metric("Concentração Curva A", pct(conc_A_sel), "Dependência do topo")
    with c6:
        premium_metric("Itens em risco", br_int(itens_risco), "TACOS alto ou prejuízo")

st.caption(
    f"Parâmetros. TACOS limite {pct(tacos_limite)}. Margem pós ads mínima {pct(margem_pos_ads_min)}. Ticket mínimo para escalar {bm(ticket_min_escala)}."
)

# =========================
# UI Components
# =========================
def segment_card(title, emoji, df_seg, subtitle, filename):
    # status por produto
    df_seg = df_seg.copy()
    if "MLB" in df_seg.columns:
        df_seg["Status"] = df_seg["MLB"].astype(str).map(get_status)
    else:
        df_seg["Status"] = "Novo"

    inprog = int((df_seg["Status"] == "Em andamento").sum()) if "Status" in df_seg.columns else 0

    with st.container(border=True):
        colA, colB, colC, colD, colE = st.columns([2.2, 0.85, 0.95, 1.15, 1.35])

        with colA:
            st.markdown(f"### {emoji} {title}")
            st.caption(subtitle)

        with colB:
            st.metric("Itens", br_int(len(df_seg)))

        with colC:
            st.metric("Em andamento", br_int(inprog))

        with colD:
            if "Perda estimada" in df_seg.columns and df_seg["Perda estimada"].notna().any():
                st.metric("Impacto", bm(float(df_seg["Perda estimada"].fillna(0).sum())))
            elif "lucro_pos_ads_0_30" in df_seg.columns and df_seg["lucro_pos_ads_0_30"].notna().any():
                st.metric("Lucro pós ads", bm(float(df_seg["lucro_pos_ads_0_30"].fillna(0).sum())))
            else:
                base = float(df_seg["Fat. 0-30"].fillna(0).sum()) if "Fat. 0-30" in df_seg.columns else 0.0
                st.metric("Faturamento", bm(base))

        with colE:
            export_cols = [
                "MLB","Título","Frente","Prioridade","Score prioridade","Status","Ação curta",
                "Curva 31-60","Curva 0-30","Qntd 31-60","Qntd 0-30",
                "Fat. 0-30","Fat total","TM total",
                "investimento_ads","tacos_0_30","roas_0_30",
                "lucro_bruto_estimado_0_30","lucro_pos_ads_0_30","margem_pos_ads_%_0_30",
                "risco_lucro",
                "Plano 15 dias","Plano 30 dias"
            ]
            export_df = ensure_cols(df_seg, export_cols)

            st.download_button(
                "Baixar CSV",
                data=to_csv_bytes(export_df),
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )


# =========================
# Page: Visão geral
# =========================
if page == "Visão geral":
    col_left, col_right = st.columns([1.45, 1.0])

    with col_left:
        with st.container(border=True):
            st.subheader(f"Distribuição de curvas no {period_sel}")
            dist_df = pd.DataFrame({"Curva": dist_sel.index, "Anúncios": dist_sel.values})
            fig = px.bar(dist_df, x="Curva", y="Anúncios")
            st.plotly_chart(fig, use_container_width=True)

        with st.container(border=True):
            st.subheader("Faturamento por curva e período")
            rev_rows = []
            for p, cc, qq, ff in PERIODS:
                grp = df_f.groupby(cc)[ff].sum()
                for curva in ["A", "B", "C", "-"]:
                    rev_rows.append({"Período": p, "Curva": curva, "Faturamento": float(grp.get(curva, 0.0))})
            rev_df = pd.DataFrame(rev_rows)
            fig2 = px.bar(rev_df, x="Período", y="Faturamento", color="Curva", barmode="group")
            st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.subheader("Resumo por período")
            show = kpi_df.copy()
            show["Qtd"] = show["Qtd"].map(br_int)
            show["Faturamento"] = show["Faturamento"].map(br_money)
            show["Ticket médio"] = show["Ticket médio"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            st.dataframe(show, use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.subheader("Top prioridades agora")
            cols = [
                "Prioridade", "Score prioridade", "MLB", "Título", "Frente", "Ação curta",
                "Curva 0-30", "Fat. 0-30", "tacos_0_30", "lucro_pos_ads_0_30", "risco_lucro"
            ]
            top = ensure_cols(plan.sort_values(["Score prioridade"], ascending=[False]).head(15), cols)
            top["Fat. 0-30"] = top["Fat. 0-30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            top["tacos_0_30"] = top["tacos_0_30"].apply(lambda x: pct(x))
            top["lucro_pos_ads_0_30"] = top["lucro_pos_ads_0_30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            top["Score prioridade"] = top["Score prioridade"].apply(lambda x: round(float(x), 3) if pd.notna(x) else "-")
            st.dataframe(top, use_container_width=True, hide_index=True)

    st.subheader("Ações por frente")
    seg_defesa = plan[plan["Frente"] == "DEFESA, Âncora"].copy().sort_values("Fat. 0-30", ascending=False)
    seg_correcao_queda = plan[plan["Frente"] == "CORREÇÃO, Fuga de receita"].copy().sort_values("impacto_queda", ascending=False)
    seg_ataque = plan[plan["Frente"] == "ATAQUE, Crescimento"].copy().sort_values("Fat. 0-30", ascending=False)
    seg_limpeza = plan[plan["Frente"] == "LIMPEZA, Parado"].copy().sort_values("Fat. 0-30", ascending=False)

    segment_card(
        title="Defesa, Âncoras",
        emoji="🛡",
        df_seg=seg_defesa,
        subtitle="Produtos âncora. Proteja estoque e conversão, depois escale com controle.",
        filename="defesa_ancoras.csv"
    )
    segment_card(
        title="Correção, Fuga de receita",
        emoji="🧰",
        df_seg=seg_correcao_queda,
        subtitle=f"Produtos que caíram. Perda estimada total {bm(perda_total)}.",
        filename="correcao_fuga_receita.csv"
    )
    segment_card(
        title="Ataque, Crescimento",
        emoji="🔥",
        df_seg=seg_ataque,
        subtitle="Produtos em ascensão e oportunidades. Escale o que dá lucro e mantém ticket.",
        filename="ataque_crescimento.csv"
    )
    segment_card(
        title="Limpeza, Parados",
        emoji="🧹",
        df_seg=seg_limpeza,
        subtitle="Produtos parados, combos e inativação. Libere caixa e foco do catálogo.",
        filename="limpeza_parados.csv"
    )

# =========================
# Page: Diagnóstico e riscos
# =========================
if page == "Diagnóstico e riscos":
    with st.container(border=True):
        st.subheader("Diagnóstico macro")
        cA, cB, cC, cD = st.columns(4)
        cA.metric("Curva A", br_int(int(dist_sel.get("A", 0))))
        cB.metric("Curva B", br_int(int(dist_sel.get("B", 0))))
        cC.metric("Curva C", br_int(int(dist_sel.get("C", 0))))
        cD.metric("Sem venda", br_int(int(dist_sel.get("-", 0))))

        st.caption(
            "Concentração alta em Curva A aumenta dependência do topo. "
            "Concentração baixa reduz risco, mas pode indicar falta de foco nos melhores itens."
        )

    with st.container(border=True):
        st.subheader("Ticket médio por período")
        tm_df = kpi_df.copy()
        tm_df["Ticket médio"] = tm_df["Ticket médio"].fillna(0.0)
        fig = px.line(tm_df, x="Período", y="Ticket médio", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    has_any_enrich = (not edf.empty) and (
        ("investimento_ads" in df_f.columns) or ("custo_unitario" in df_f.columns) or ("margem_percentual" in df_f.columns)
    )

    with st.container(border=True):
        st.subheader("Lucro e risco")
        if not has_any_enrich:
            st.info("Envie o arquivo opcional para ver lucro e risco por produto.")
        else:
            rcount = df_f["risco_lucro"].value_counts()
            rr = pd.DataFrame({"Classificação": rcount.index, "Itens": rcount.values})

            col_l, col_r = st.columns([1.0, 1.4])
            with col_l:
                fig2 = px.bar(rr, x="Classificação", y="Itens")
                st.plotly_chart(fig2, use_container_width=True)

            with col_r:
                st.markdown("### Alertas principais")
                neg_count = int((pd.notna(df_f["lucro_pos_ads_0_30"]) & (df_f["lucro_pos_ads_0_30"] < 0)).sum())
                high_tacos_count = int((pd.notna(df_f["tacos_0_30"]) & (df_f["tacos_0_30"] > tacos_limite)).sum())
                st.write(f"- Itens com prejuízo pós ads: {br_int(neg_count)}")
                st.write(f"- Itens com TACOS acima do limite: {br_int(high_tacos_count)}")
                st.write("- Use o ranking para atacar o que tem dinheiro na mesa e cortar desperdício.")

    if has_any_enrich:
        with st.container(border=True):
            st.subheader("Top prejuízo pós ads")
            cols = ["MLB", "Título", "Curva 0-30", "Fat. 0-30", "investimento_ads", "tacos_0_30", "lucro_pos_ads_0_30", "margem_pos_ads_%_0_30", "risco_lucro"]
            neg = df_f[pd.notna(df_f["lucro_pos_ads_0_30"]) & (df_f["lucro_pos_ads_0_30"] < 0)].copy()
            neg = neg.sort_values("lucro_pos_ads_0_30", ascending=True).head(15)
            neg = ensure_cols(neg, cols)
            neg["Fat. 0-30"] = neg["Fat. 0-30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            neg["investimento_ads"] = neg["investimento_ads"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            neg["tacos_0_30"] = neg["tacos_0_30"].apply(lambda x: pct(x))
            neg["lucro_pos_ads_0_30"] = neg["lucro_pos_ads_0_30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            neg["margem_pos_ads_%_0_30"] = neg["margem_pos_ads_%_0_30"].apply(lambda x: pct(x))
            st.dataframe(neg, use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.subheader("Top melhor lucro pós ads")
            cols = ["MLB", "Título", "Curva 0-30", "Fat. 0-30", "investimento_ads", "tacos_0_30", "lucro_pos_ads_0_30", "margem_pos_ads_%_0_30", "risco_lucro"]
            pos = df_f[pd.notna(df_f["lucro_pos_ads_0_30"]) & (df_f["lucro_pos_ads_0_30"] > 0)].copy()
            pos = pos.sort_values("lucro_pos_ads_0_30", ascending=False).head(15)
            pos = ensure_cols(pos, cols)
            pos["Fat. 0-30"] = pos["Fat. 0-30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            pos["investimento_ads"] = pos["investimento_ads"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            pos["tacos_0_30"] = pos["tacos_0_30"].apply(lambda x: pct(x))
            pos["lucro_pos_ads_0_30"] = pos["lucro_pos_ads_0_30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
            pos["margem_pos_ads_%_0_30"] = pos["margem_pos_ads_%_0_30"].apply(lambda x: pct(x))
            st.dataframe(pos, use_container_width=True, hide_index=True)

    with st.container(border=True):
        st.subheader("Fuga de receita, foco cirúrgico")
        st.caption(f"Perda estimada total {bm(perda_total)}")
        cols = ["MLB", "Título", "Curva 31-60", "Curva 61-90", "Curva 0-30", "Fat anterior ref", "Fat. 0-30", "Perda estimada", "tacos_0_30", "lucro_pos_ads_0_30", "risco_lucro"]
        fuga = ensure_cols(drop_alert.head(30), cols)
        fuga["Fat anterior ref"] = fuga["Fat anterior ref"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        fuga["Fat. 0-30"] = fuga["Fat. 0-30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        fuga["Perda estimada"] = fuga["Perda estimada"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        fuga["tacos_0_30"] = fuga["tacos_0_30"].apply(lambda x: pct(x))
        fuga["lucro_pos_ads_0_30"] = fuga["lucro_pos_ads_0_30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        st.dataframe(fuga, use_container_width=True, hide_index=True)

# =========================
# Page: Plano tático e exportação
# =========================
if page == "Plano tático e exportação":

    with st.container(border=True):
        st.subheader("Status, ação em andamento")
        st.caption("Marque o status por produto. Isso fica salvo enquanto o app estiver rodando.")

        editor_base = plan.sort_values(["Score prioridade"], ascending=False).head(60).copy()
        editor_base["Status"] = editor_base["MLB"].astype(str).map(get_status)
        editor_view = editor_base[["MLB", "Título", "Frente", "Prioridade", "Status"]].copy()

        edited = st.data_editor(
            editor_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=STATUS_OPTIONS,
                    required=True,
                )
            },
            key="status_editor",
        )

        for _, r in edited.iterrows():
            set_status(r["MLB"], r["Status"])

        # Export em Excel do status (para enviar ao cliente)
        status_cols = [
            "Prioridade", "Score prioridade", "MLB", "Título", "Frente", "Status", "Ação curta",
            "Curva 0-30", "Curva 31-60", "Curva 61-90", "Curva 91-120",
            "Fat. 0-30", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120",
            "Perda estimada", "risco_lucro",
            "Plano 15 dias", "Plano 30 dias",
        ]
        status_df = plan.copy()
        status_df["Status"] = status_df["MLB"].astype(str).map(get_status)
        status_df = ensure_cols(status_df.sort_values(["Score prioridade"], ascending=False), status_cols)

        xlsx_bytes = to_excel_bytes({"Status": status_df}, filename_hint="status")
        st.download_button(
            "Baixar Excel de Status (cliente)",
            data=xlsx_bytes,
            file_name="status_acao_em_andamento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with st.container(border=True):
        st.subheader("Ranking de prioridades")
        top_k = st.slider("Mostrar top prioridades", min_value=20, max_value=200, value=80, step=10)

        plan_view = plan.sort_values(["Score prioridade", "Fat. 0-30"], ascending=[False, False]).head(int(top_k))

        cols = [
            "Prioridade", "Score prioridade",
            "MLB", "Título",
            "Frente", "Ação curta",
            "Curva 31-60", "Curva 0-30",
            "Qntd 31-60", "Qntd 0-30",
            "Fat. 0-30", "Fat total", "TM total",
            "investimento_ads", "tacos_0_30", "roas_0_30",
            "lucro_bruto_estimado_0_30", "lucro_pos_ads_0_30", "margem_pos_ads_%_0_30",
            "risco_lucro",
            "Plano 15 dias", "Plano 30 dias"
        ]
        plan_show = ensure_cols(plan_view, cols)

        st.download_button(
            "Baixar CSV do ranking",
            data=to_csv_bytes(plan_show),
            file_name="ranking_prioridades.csv",
            mime="text/csv",
            use_container_width=True
        )

        disp = plan_show.copy()
        disp["Score prioridade"] = disp["Score prioridade"].apply(lambda x: round(float(x), 3) if pd.notna(x) else "-")
        disp["Fat. 0-30"] = disp["Fat. 0-30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        disp["Fat total"] = disp["Fat total"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        disp["TM total"] = disp["TM total"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        disp["investimento_ads"] = disp["investimento_ads"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        disp["tacos_0_30"] = disp["tacos_0_30"].apply(lambda x: pct(x))
        disp["roas_0_30"] = disp["roas_0_30"].apply(lambda x: round(float(x), 2) if pd.notna(x) else "-")
        disp["lucro_bruto_estimado_0_30"] = disp["lucro_bruto_estimado_0_30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        disp["lucro_pos_ads_0_30"] = disp["lucro_pos_ads_0_30"].apply(lambda x: bm(x) if pd.notna(x) else "-")
        disp["margem_pos_ads_%_0_30"] = disp["margem_pos_ads_%_0_30"].apply(lambda x: pct(x))

        st.dataframe(disp, use_container_width=True, hide_index=True)

    with st.container(border=True):
        st.subheader("Exportações")
        export_exec_cols = [
            "Prioridade", "MLB", "Título", "Frente", "Ação curta",
            "Curva 0-30", "Fat. 0-30",
            "Perda estimada", "tacos_0_30", "lucro_pos_ads_0_30", "risco_lucro"
        ]
        export_time_cols = [
            "Prioridade", "Score prioridade", "MLB", "Título", "Frente", "Ação curta",
            "Curva 31-60", "Curva 0-30",
            "Qntd 31-60", "Qntd 0-30",
            "Fat. 0-30", "investimento_ads", "tacos_0_30",
            "lucro_pos_ads_0_30", "margem_pos_ads_%_0_30", "risco_lucro",
            "Plano 15 dias", "Plano 30 dias"
        ]
        exec_df = ensure_cols(plan.sort_values(["Score prioridade"], ascending=False), export_exec_cols)
        time_df = ensure_cols(plan.sort_values(["Score prioridade"], ascending=False), export_time_cols)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Baixar CSV executivo",
                data=to_csv_bytes(exec_df),
                file_name="export_executivo.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "Baixar CSV do time",
                data=to_csv_bytes(time_df),
                file_name="export_time_planos.csv",
                mime="text/csv",
                use_container_width=True
            )

        
        # Export executivo mais enxuto
        plan_all = plan.copy()
        plan_all["Status"] = plan_all["MLB"].astype(str).map(get_status)
        exec_cols = [
            "Prioridade","MLB","Título","Frente","Status","Ação curta",
            "Fat. 0-30","Perda estimada","risco_lucro",
            "Plano 15 dias","Plano 30 dias"
        ]
        exec_df = ensure_cols(plan_all.sort_values(["Score prioridade"], ascending=False), exec_cols)

        st.download_button(
            "Baixar CSV executivo (enxuto)",
            data=to_csv_bytes(exec_df),
            file_name="export_executivo_enxuto.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.subheader("Listas rápidas")
    st.caption("Baixe as listas, complete custo, margem e ads no seu arquivo de apoio e envie no upload opcional.")

    seg_defesa = plan[plan["Frente"] == "DEFESA, Âncora"].copy().sort_values("Fat. 0-30", ascending=False)
    seg_correcao_queda = plan[plan["Frente"] == "CORREÇÃO, Fuga de receita"].copy().sort_values("impacto_queda", ascending=False)
    seg_correcao_rev = plan[plan["Frente"] == "CORREÇÃO, Revitalizar"].copy().sort_values("Fat. 0-30", ascending=False)
    seg_ataque = plan[plan["Frente"] == "ATAQUE, Crescimento"].copy().sort_values("Fat. 0-30", ascending=False)
    seg_limpeza = plan[plan["Frente"] == "LIMPEZA, Parado"].copy().sort_values("Fat. 0-30", ascending=False)

    segment_card("Defesa, Âncoras", "🛡", seg_defesa, "Proteja e escale com controle.", "defesa_ancoras.csv")
    segment_card("Correção, Fuga de receita", "🧰", seg_correcao_queda, "Recuperar o que caiu e devolve dinheiro.", "correcao_fuga_receita.csv")
    segment_card("Correção, Revitalizar", "🧰", seg_correcao_rev, "Ajuste rápido para recuperar itens com potencial.", "correcao_revitalizar.csv")
    segment_card("Ataque, Crescimento", "🔥", seg_ataque, "Escalar o que subiu e dá lucro.", "ataque_crescimento.csv")
    segment_card("Limpeza, Parados", "🧹", seg_limpeza, "Cortar, pausar, combos e liquidação.", "limpeza_parados.csv")

    with st.container(border=True):
        st.subheader("Detalhe por produto")
        st.caption("Use a busca na sidebar para achar um MLB e ver o plano completo.")

        detail_cols = [
            "MLB", "Título", "Frente", "Prioridade", "Score prioridade", "Ação curta",
            "Curva 91-120", "Curva 61-90", "Curva 31-60", "Curva 0-30",
            "Qntd 91-120", "Qntd 61-90", "Qntd 31-60", "Qntd 0-30",
            "Fat. 91-120", "Fat. 61-90", "Fat. 31-60", "Fat. 0-30",
            "investimento_ads", "tacos_0_30", "roas_0_30",
            "lucro_pos_ads_0_30", "margem_pos_ads_%_0_30", "risco_lucro",
            "Ação sugerida", "Plano 15 dias", "Plano 30 dias"
        ]
        detail = ensure_cols(plan.sort_values(["Score prioridade"], ascending=False).head(50), detail_cols)
        detail["Score prioridade"] = detail["Score prioridade"].apply(lambda x: round(float(x), 3) if pd.notna(x) else "-")
        st.dataframe(detail, use_container_width=True, hide_index=True)
