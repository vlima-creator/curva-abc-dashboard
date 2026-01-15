import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Curva ABC, Dashboard e Relatório", layout="wide")
st.title("Curva ABC de Vendas, Dashboard e Relatório Estratégico")

# =========================
# Helpers
# =========================
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

def to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    csv = dataframe.to_csv(index=False, sep=";", encoding="utf-8-sig")
    return csv.encode("utf-8-sig")

rank = {"-": 0, "C": 1, "B": 2, "A": 3}

periods = [
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
# Uploads
# =========================
uploaded = st.file_uploader("Envie o arquivo Excel da Curva ABC", type=["xlsx"])
if not uploaded:
    st.info("Envie o arquivo para carregar o dashboard e o relatório.")
    st.stop()

enrich_upload = st.file_uploader(
    "Opcional: envie um arquivo Excel/CSV com custo/margem e investimento em ads por MLB (jeito 1)",
    type=["xlsx", "csv"],
    key="enrich",
)

df = load_main(uploaded)
edf = load_enrich(enrich_upload)

# =========================
# Sidebar filters
# =========================
st.sidebar.header("Filtros")
curva_filtro = st.sidebar.multiselect(
    "Curvas para incluir",
    options=["A", "B", "C", "-"],
    default=["A", "B", "C", "-"]
)

mask_any = (
    df["Curva 0-30"].isin(curva_filtro) |
    df["Curva 31-60"].isin(curva_filtro) |
    df["Curva 61-90"].isin(curva_filtro) |
    df["Curva 91-120"].isin(curva_filtro)
)
df_f = df[mask_any].copy()

# =========================
# Merge opcional (não interfere se não enviar)
# =========================
if not edf.empty:
    df_f = df_f.merge(edf, on="MLB", how="left")

# =========================
# Base metrics
# =========================
df_f["Qtd total"] = df_f[QTY_COLS].sum(axis=1)
df_f["Fat total"] = df_f[FAT_COLS].sum(axis=1)
df_f["TM total"] = np.where(df_f["Qtd total"] > 0, df_f["Fat total"] / df_f["Qtd total"], np.nan)

for p in ["0-30", "31-60", "61-90", "91-120"]:
    df_f[f"rank_{p}"] = df_f[f"Curva {p}"].map(rank).fillna(0).astype(int)

df_f["queda_recente"] = df_f["rank_0-30"] < df_f["rank_31-60"]
df_f["queda_forte"] = (df_f["rank_31-60"] - df_f["rank_0-30"]) >= 2

# Ticket médio por janela (ponderado)
kpi_rows = []
for p, cc, qq, ff in periods:
    qty = int(df_f[qq].sum())
    fat = float(df_f[ff].sum())
    tm = safe_div(fat, qty)
    kpi_rows.append({"Período": p, "Qtd": qty, "Faturamento": fat, "Ticket médio": tm})
kpi_df = pd.DataFrame(kpi_rows)

# =========================
# Métricas avançadas (se tiver enriquecimento)
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
    # só faz sentido se tiver pelo menos um dos campos preenchidos
    has_any = False
    for c in ["custo_unitario", "margem_percentual", "investimento_ads"]:
        if c in row.index and pd.notna(row.get(c)):
            has_any = True
            break
    if not has_any:
        return "Sem dados (opcional)"

    # prejuízo pós ads
    if pd.notna(row.get("lucro_pos_ads_0_30")) and row["lucro_pos_ads_0_30"] < 0:
        return "Risco alto, prejuízo"

    # tacos alto
    if pd.notna(row.get("tacos_0_30")) and row["tacos_0_30"] > 0.20:
        return "Risco médio, tacos alto"

    # margem pós ads boa
    if pd.notna(row.get("margem_pos_ads_%_0_30")) and row["margem_pos_ads_%_0_30"] >= 0.10:
        return "Oportunidade, margem boa"

    return "Ok, monitorar"

df_f["risco_lucro"] = df_f.apply(classifica_risco, axis=1)

# =========================
# Segmentações do projeto
# =========================

# Produtos Âncora: A em todos os períodos
anchors = df_f[
    (df_f["Curva 0-30"] == "A") &
    (df_f["Curva 31-60"] == "A") &
    (df_f["Curva 61-90"] == "A") &
    (df_f["Curva 91-120"] == "A")
].copy().sort_values("Fat total", ascending=False)

# Fuga de receita: era A ou B em 31-60 ou 61-90 e agora virou C ou -
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

# Ascensão: era B/C/- e virou A no 0-30
rise_to_A = df_f[
    (df_f["Curva 0-30"] == "A") &
    (
        df_f["Curva 31-60"].isin(["B", "C", "-"]) |
        df_f["Curva 61-90"].isin(["B", "C", "-"]) |
        df_f["Curva 91-120"].isin(["B", "C", "-"])
    )
].copy().sort_values("Fat. 0-30", ascending=False)

# Estoque morto e combos: sem venda 0-30, com histórico, TM histórico < 35
hist_qty = df_f["Qntd 31-60"] + df_f["Qntd 61-90"] + df_f["Qntd 91-120"]
hist_fat = df_f["Fat. 31-60"] + df_f["Fat. 61-90"] + df_f["Fat. 91-120"]
df_f["TM histórico"] = np.where(hist_qty > 0, hist_fat / hist_qty, np.nan)

dead_stock = df_f[(df_f["Fat. 0-30"] == 0) & (hist_fat > 0)].copy()
dead_stock_combo = dead_stock[dead_stock["TM histórico"] < 35].copy().sort_values("TM histórico", ascending=True)

# C recorrente
tmp = df_f.copy()
tmp["c_count"] = (tmp[CURVE_COLS] == "C").sum(axis=1)
c_rec = tmp[tmp["c_count"] >= 3].copy()

# Sem vendas (proxy)
no_sales_90 = df_f[(df_f["Qntd 0-30"] == 0) & (df_f["Qntd 31-60"] == 0) & (df_f["Qntd 61-90"] == 0)].copy()
no_sales_60 = df_f[(df_f["Qntd 0-30"] == 0) & (df_f["Qntd 31-60"] == 0)].copy()

# Revitalizar cirúrgico
revitalize = df_f[
    df_f["queda_recente"] &
    (
        ((df_f["Qntd 0-30"] >= 30) & (df_f["Qntd 0-30"] <= 40)) |
        (((df_f["Qntd 31-60"] >= 30) & (df_f["Qntd 31-60"] <= 40)) & (df_f["Qntd 0-30"] <= 10)) |
        (df_f["queda_forte"] & (df_f["Qntd 0-30"] >= 1) & (df_f["Qntd 0-30"] <= 25))
    )
].copy()

# Inativar cirúrgico
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

# Oportunidade 50 a 60
opp_50_60 = df_f[
    ((df_f["Qntd 0-30"] >= 50) & (df_f["Qntd 0-30"] <= 60)) |
    ((df_f["Qntd 31-60"] >= 50) & (df_f["Qntd 31-60"] <= 60))
].copy()

# =========================
# Ação sugerida + Plano 15 e 30 (com lucro/risco quando existir)
# =========================
def action_bundle(row):
    idx = row.name

    is_anchor = idx in anchors.index
    is_inactivate = idx in inactivate.index
    is_revitalize = idx in revitalize.index
    is_opp = idx in opp_50_60.index
    is_drop = idx in drop_alert.index
    is_rise = idx in rise_to_A.index
    is_combo = idx in dead_stock_combo.index

    risco = row.get("risco_lucro", "Sem dados (opcional)")
    tacos = row.get("tacos_0_30", np.nan)
    lucro_pos = row.get("lucro_pos_ads_0_30", np.nan)

    # Regras de ajuste de texto quando tiver risco
    detalhe_risco = ""
    if risco != "Sem dados (opcional)":
        detalhe_risco = f" Risco: {risco}."
        if pd.notna(tacos):
            detalhe_risco += f" TACOS 0-30: {round(float(tacos) * 100, 2)}%."
        if pd.notna(lucro_pos):
            detalhe_risco += f" Lucro pós ads 0-30: {br_money(float(lucro_pos))}."

    if is_inactivate:
        return (
            f"Inativar ou pausar.{detalhe_risco}",
            "Dia 1 a 3: confirmar anúncio ativo, estoque e preço. Se estiver tudo certo e não vende, pausar.\n"
            "Dia 4 a 10: realocar foco para itens com giro.\n"
            "Dia 11 a 15: manter pausado se não houver sinal de recuperação.",
            "Semana 1: decidir manter no catálogo ou retirar.\n"
            "Semana 2: se mantiver, reativar com meta mínima de venda e ajuste simples.\n"
            "Semana 3 e 4: se não reagir, inativar definitivo."
        )

    if is_combo:
        return (
            f"Liquidação ou combos.{detalhe_risco}",
            "Dia 1 a 5: montar combo com âncoras ou itens B. Objetivo é giro, não margem máxima.\n"
            "Dia 6 a 15: ajustar preço do combo e melhorar a oferta do anúncio.",
            "Semana 1: criar kits e variações para aumentar saída.\n"
            "Semana 2 a 4: se girar, manter como estratégia. Se não, caminhar para inativação."
        )

    if is_drop:
        return (
            f"Correção imediata de fuga de receita.{detalhe_risco}",
            "Dia 1 a 2: checar ruptura, prazo, reputação e concorrência direta.\n"
            "Dia 3 a 7: ajustar preço e frete para faixa competitiva.\n"
            "Dia 8 a 15: mídia leve com termos exatos, cortar desperdício.",
            "Semana 1: ajustar título e atributos para recuperar relevância.\n"
            "Semana 2: otimizar página do anúncio para conversão.\n"
            "Semana 3 e 4: manter investimento só onde há venda e recuperar curva."
        )

    if is_anchor:
        return (
            f"Defesa e escala controlada.{detalhe_risco}",
            "Dia 1 a 3: garantir estoque e evitar ruptura.\n"
            "Dia 4 a 10: melhorar conversão (título, fotos, variações).\n"
            "Dia 11 a 15: aumentar orçamento em passos pequenos, controlar desperdício.",
            "Semana 1: separar campanhas por intenção.\n"
            "Semana 2: teste pequeno de preço se fizer sentido.\n"
            "Semana 3 e 4: escalar mantendo ticket e margem sob controle."
        )

    if is_rise:
        return (
            f"Ataque para consolidar crescimento.{detalhe_risco}",
            "Dia 1 a 5: identificar gatilho de crescimento e replicar.\n"
            "Dia 6 a 10: ampliar exposição em termos rentáveis.\n"
            "Dia 11 a 15: reforçar página para segurar conversão.",
            "Semana 1: campanhas separadas por termos fortes e long tail.\n"
            "Semana 2: proteger ticket médio.\n"
            "Semana 3 e 4: escalar sem travar estoque."
        )

    if is_opp:
        return (
            f"Oportunidade 50 a 60, alavancar ou escoar.{detalhe_risco}",
            "Dia 1 a 3: validar margem e competitividade.\n"
            "Dia 4 a 10: aumentar exposição em termos que vendem.\n"
            "Dia 11 a 15: ajustar lances só nos termos vencedores.",
            "Semana 1: otimizar página para conversão.\n"
            "Semana 2: testar kit ou variação para subir ticket.\n"
            "Semana 3 e 4: consolidar como projeto de escala ou escoar com meta clara."
        )

    if is_revitalize:
        return (
            f"Revitalizar com ajuste rápido.{detalhe_risco}",
            "Dia 1 a 4: auditoria do anúncio, preço, frete, título, fotos e estoque.\n"
            "Dia 5 a 10: campanha leve, termos específicos.\n"
            "Dia 11 a 15: aumentar só onde tiver venda.",
            "Semana 1: reorganizar variações e atributos.\n"
            "Semana 2: testar kit ou condição comercial.\n"
            "Semana 3 e 4: se não reagir, reduzir prioridade."
        )

    curva0 = row["Curva 0-30"]
    if curva0 == "A":
        return (
            f"Manter e otimizar.{detalhe_risco}",
            "Dia 1 a 7: cortar desperdício e melhorar conversão.\nDia 8 a 15: ajustar lances e termos.",
            "Semana 1: melhorias na página.\nSemana 2 a 4: escalar apenas se mantiver ticket e giro."
        )
    if curva0 in ["B", "C"]:
        return (
            f"Otimizar e definir foco.{detalhe_risco}",
            "Dia 1 a 5: checar competitividade e termos.\nDia 6 a 15: decidir se vira crescimento ou mix.",
            "Semana 1: estratégia por margem e giro.\nSemana 2 a 4: executar e medir."
        )
    return (
        f"Sem venda recente, avaliar continuidade.{detalhe_risco}",
        "Dia 1 a 7: confirmar anúncio ativo e estoque.\nDia 8 a 15: se não houver sinal, pausar.",
        "Semana 1: testar ajustes mínimos.\nSemana 2 a 4: se não reagir, inativar."
    )

plan = df_f.copy()
actions = plan.apply(action_bundle, axis=1, result_type="expand")
plan["Ação sugerida"] = actions[0]
plan["Plano 15 dias"] = actions[1]
plan["Plano 30 dias"] = actions[2]

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

plan["Frente"] = [frente_bucket(i) for i in plan.index]

# =========================
# Diagnóstico macro
# =========================
dist_0_30 = df_f["Curva 0-30"].value_counts().reindex(["A", "B", "C", "-"]).fillna(0).astype(int)
dist_0_30_df = pd.DataFrame({"Curva": dist_0_30.index, "Anúncios": dist_0_30.values})

fat_0_30_total = float(df_f["Fat. 0-30"].sum())
fat_0_30_A = float(df_f.loc[df_f["Curva 0-30"] == "A", "Fat. 0-30"].sum())
conc_A_0_30 = safe_div(fat_0_30_A, fat_0_30_total)

tm_0_30 = float(kpi_df.loc[kpi_df["Período"] == "0-30", "Ticket médio"].iloc[0])
tm_31_60 = float(kpi_df.loc[kpi_df["Período"] == "31-60", "Ticket médio"].iloc[0])
tm_61_90 = float(kpi_df.loc[kpi_df["Período"] == "61-90", "Ticket médio"].iloc[0])

def tm_direction(a, b, c):
    if np.isnan(a) or np.isnan(b) or np.isnan(c):
        return "Sem dados suficientes para leitura do ticket médio."
    if a < b < c:
        return "O ticket médio está subindo de forma consistente. Isso tende a ajudar margem, mas pode reduzir volume se o preço estiver esticando."
    if a > b > c:
        return "O ticket médio está caindo de forma consistente. Isso pode indicar promoções ou mix mais barato, e normalmente pressiona margem."
    if b < a and c > b:
        return "O ticket caiu e depois recuperou. Normalmente é efeito de promoções seguidas de retorno do mix ou ajuste de preço."
    if b > a and c < b:
        return "O ticket subiu e depois caiu. Pode ser ruptura de itens de maior valor ou mudança no mix."
    return "O ticket médio está oscilando. Vale cruzar mix e concorrência para entender impacto na margem."

tm_reading = tm_direction(tm_0_30, tm_31_60, tm_61_90)

# =========================
# KPIs topo
# =========================
total_ads = len(df_f)
tt_fat = float(df_f[FAT_COLS].sum().sum())
tt_qty = int(df_f[QTY_COLS].sum().sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total de anúncios", br_int(total_ads))
k2.metric("Faturamento total (4 janelas)", br_money(tt_fat))
k3.metric("Quantidade total (4 janelas)", br_int(tt_qty))
k4.metric("Ticket médio total", br_money(safe_div(tt_fat, tt_qty) if tt_qty else 0.0))

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Dashboard", "Listas e Exportação", "Plano tático por produto", "Relatório Estratégico"]
)

# =========================
# TAB 1: Dashboard
# =========================
with tab1:
    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("Resumo por período")
        show = kpi_df.copy()
        show["Qtd"] = show["Qtd"].map(br_int)
        show["Faturamento"] = show["Faturamento"].map(br_money)
        show["Ticket médio"] = show["Ticket médio"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Distribuição de curvas no período 0-30")
        fig = px.bar(dist_0_30_df, x="Curva", y="Anúncios")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Faturamento por curva e período")
    rev_rows = []
    for p, cc, qq, ff in periods:
        grp = df_f.groupby(cc)[ff].sum()
        for curva in ["A", "B", "C", "-"]:
            rev_rows.append({"Período": p, "Curva": curva, "Faturamento": float(grp.get(curva, 0.0))})
    rev_df = pd.DataFrame(rev_rows)
    fig2 = px.bar(rev_df, x="Período", y="Faturamento", color="Curva", barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Ticket médio (ponderado) por período")
    tm_df = kpi_df.copy()
    tm_df["Ticket médio"] = tm_df["Ticket médio"].fillna(0.0)
    fig3 = px.line(tm_df, x="Período", y="Ticket médio", markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    st.subheader("Top 40 por faturamento com ação sugerida")
    sample_cols = ["MLB", "Título", "Curva 0-30", "Qntd 0-30", "Fat. 0-30", "Frente", "Ação sugerida"]
    if "tacos_0_30" in df_f.columns:
        sample_cols += ["tacos_0_30", "roas_0_30", "lucro_pos_ads_0_30", "risco_lucro"]

    sample = plan.sort_values("Fat total", ascending=False)[sample_cols].head(40).copy()

    sample["Fat. 0-30"] = sample["Fat. 0-30"].map(br_money)
    if "tacos_0_30" in sample.columns:
        sample["tacos_0_30"] = sample["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
    if "roas_0_30" in sample.columns:
        sample["roas_0_30"] = sample["roas_0_30"].apply(lambda x: round(float(x), 2) if pd.notna(x) else "-")
    if "lucro_pos_ads_0_30" in sample.columns:
        sample["lucro_pos_ads_0_30"] = sample["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")

    st.dataframe(sample, use_container_width=True, hide_index=True)

# =========================
# TAB 2: Listas e Exportação
# =========================
with tab2:
    st.subheader("Exportação rápida em CSV")
    st.caption("Jeito 1: baixe a lista, preencha custo/margem/ads nela, junte tudo num único arquivo de enriquecimento e suba no upload opcional.")

    extra_cols = []
    for c in [
        "custo_unitario", "margem_percentual", "investimento_ads",
        "tacos_0_30", "roas_0_30",
        "lucro_bruto_estimado_0_30", "lucro_pos_ads_0_30", "margem_pos_ads_%_0_30",
        "risco_lucro"
    ]:
        if c in df_f.columns:
            extra_cols.append(c)

    def enrich_df(base_df: pd.DataFrame) -> pd.DataFrame:
        if not extra_cols:
            return base_df.copy()
        return base_df.merge(
            df_f[["MLB"] + extra_cols].drop_duplicates("MLB"),
            on="MLB",
            how="left"
        )

    anchors_export = enrich_df(anchors.copy())
    inactivate_export = enrich_df(inactivate.copy())
    revitalize_export = enrich_df(revitalize.copy())
    opp_export = enrich_df(opp_50_60.copy())
    drop_export = enrich_df(drop_alert.copy())
    combo_export = enrich_df(dead_stock_combo.copy())

    # Seleção de colunas para export
    anchors_export = anchors_export[["MLB","Título","Fat total","Qtd total","TM total","Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"] + extra_cols].copy()

    inactivate_export = inactivate_export[["MLB","Título","Fat total","Qtd total","Curva 0-30","Qntd 0-30","Qntd 31-60","Qntd 61-90"] + extra_cols].copy()

    revitalize_export = revitalize_export[["MLB","Título","Fat total","Qtd total","Curva 31-60","Curva 0-30","Qntd 31-60","Qntd 0-30"] + extra_cols].copy()

    opp_export = opp_export[["MLB","Título","Fat total","Curva 0-30","Qntd 0-30","Curva 31-60","Qntd 31-60"] + extra_cols].copy()

    drop_export_cols = ["MLB","Título","Curva 31-60","Curva 61-90","Curva 0-30","Fat anterior ref","Fat. 0-30","Perda estimada"]
    for c in drop_export_cols:
        if c not in drop_export.columns:
            drop_export[c] = np.nan
    drop_export = drop_export[drop_export_cols + extra_cols].copy()

    combo_export_cols = ["MLB","Título","TM histórico","Fat. 31-60","Fat. 61-90","Fat. 91-120","Fat. 0-30"]
    for c in combo_export_cols:
        if c not in combo_export.columns:
            combo_export[c] = np.nan
    combo_export = combo_export[combo_export_cols + extra_cols].copy()

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(f"**Âncoras:** {len(anchors_export)}")
        st.download_button("Baixar CSV Âncoras", data=to_csv_bytes(anchors_export), file_name="ancoras.csv", mime="text/csv")
    with r2:
        st.markdown(f"**Inativar:** {len(inactivate_export)}")
        st.download_button("Baixar CSV Inativar", data=to_csv_bytes(inactivate_export), file_name="inativar.csv", mime="text/csv")
    with r3:
        st.markdown(f"**Revitalizar:** {len(revitalize_export)}")
        st.download_button("Baixar CSV Revitalizar", data=to_csv_bytes(revitalize_export), file_name="revitalizar.csv", mime="text/csv")

    r4, r5, r6 = st.columns(3)
    with r4:
        st.markdown(f"**Oportunidade 50 a 60:** {len(opp_export)}")
        st.download_button("Baixar CSV Oportunidade 50 a 60", data=to_csv_bytes(opp_export), file_name="oportunidade_50_60.csv", mime="text/csv")
    with r5:
        st.markdown(f"**Fuga de receita:** {len(drop_export)}")
        st.download_button("Baixar CSV Fuga de receita", data=to_csv_bytes(drop_export), file_name="fuga_receita.csv", mime="text/csv")
    with r6:
        st.markdown(f"**Combos e liquidação:** {len(combo_export)}")
        st.download_button("Baixar CSV Combos", data=to_csv_bytes(combo_export), file_name="combos_liquidacao.csv", mime="text/csv")

    st.divider()

    with st.expander("Prévia: Fuga de receita (top 20 por perda)"):
        show = drop_export.head(20).copy()
        if "Fat anterior ref" in show.columns:
            show["Fat anterior ref"] = show["Fat anterior ref"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        if "Fat. 0-30" in show.columns:
            show["Fat. 0-30"] = show["Fat. 0-30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        if "Perda estimada" in show.columns:
            show["Perda estimada"] = show["Perda estimada"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        if "tacos_0_30" in show.columns:
            show["tacos_0_30"] = show["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
        if "lucro_pos_ads_0_30" in show.columns:
            show["lucro_pos_ads_0_30"] = show["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True)

# =========================
# TAB 3: Plano tático por produto
# =========================
with tab3:
    st.subheader("Plano tático 15 e 30 dias por produto")

    fronts = sorted(plan["Frente"].unique().tolist())
    front_filter = st.multiselect("Filtrar por Frente", options=fronts, default=fronts)

    min_fat = st.number_input("Faturamento total mínimo", min_value=0.0, value=0.0, step=100.0)
    text_search = st.text_input("Buscar por MLB ou Título", value="").strip().lower()

    view = plan[plan["Frente"].isin(front_filter)].copy()
    view = view[view["Fat total"] >= float(min_fat)].copy()

    if text_search:
        view = view[
            view["MLB"].astype(str).str.lower().str.contains(text_search) |
            view["Título"].astype(str).str.lower().str.contains(text_search)
        ].copy()

    cols = [
        "MLB", "Título", "Frente",
        "Curva 31-60", "Curva 0-30",
        "Qntd 31-60", "Qntd 0-30",
        "Fat. 0-30", "Fat total", "TM total",
        "Ação sugerida", "Plano 15 dias", "Plano 30 dias"
    ]
    # Colunas financeiras extras
    for c in ["tacos_0_30", "roas_0_30", "lucro_pos_ads_0_30", "risco_lucro"]:
        if c in plan.columns:
            cols.append(c)

    view_show = view[cols].sort_values("Fat total", ascending=False).copy()

    st.download_button(
        "Baixar CSV do plano filtrado",
        data=to_csv_bytes(view_show),
        file_name="plano_tatico.csv",
        mime="text/csv"
    )

    show = view_show.copy()
    show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
    show["Fat total"] = show["Fat total"].map(br_money)
    show["TM total"] = show["TM total"].apply(lambda x: br_money(x) if pd.notna(x) else "-")

    if "tacos_0_30" in show.columns:
        show["tacos_0_30"] = show["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
    if "roas_0_30" in show.columns:
        show["roas_0_30"] = show["roas_0_30"].apply(lambda x: round(float(x), 2) if pd.notna(x) else "-")
    if "lucro_pos_ads_0_30" in show.columns:
        show["lucro_pos_ads_0_30"] = show["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")

    st.dataframe(show, use_container_width=True, hide_index=True)

# =========================
# TAB 4: Relatório Estratégico
# =========================
with tab4:
    st.subheader("Relatório Estratégico com Plano de Ação")

    st.markdown("## 1. Diagnóstico Macro")

    st.markdown("### 1.1 Cenário do período atual (0-30)")
    st.write(f"Total de anúncios no arquivo: {br_int(total_ads)}")
    st.dataframe(dist_0_30_df, use_container_width=True, hide_index=True)

    st.markdown("### 1.2 Volume vs Faturamento vs Ticket médio")
    show_kpi = kpi_df.copy()
    show_kpi["Qtd"] = show_kpi["Qtd"].map(br_int)
    show_kpi["Faturamento"] = show_kpi["Faturamento"].map(br_money)
    show_kpi["Ticket médio"] = show_kpi["Ticket médio"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
    st.dataframe(show_kpi, use_container_width=True, hide_index=True)

    st.markdown("Leitura do ticket médio e impacto em margem")
    st.write(tm_reading)

    st.markdown("### 1.3 Concentração de faturamento na Curva A no 0-30")
    st.write(f"Faturamento 0-30 total: {br_money(fat_0_30_total)}")
    st.write(f"Faturamento 0-30 Curva A: {br_money(fat_0_30_A)}")
    st.write(f"Concentração na Curva A: {round(float(conc_A_0_30 or 0.0) * 100, 2)}%")

    if conc_A_0_30 and conc_A_0_30 >= 0.65:
        st.write("Interpretação: dependência alta da Curva A. Ruptura ou concorrência em poucos itens bate direto no mês.")
    elif conc_A_0_30 and conc_A_0_30 >= 0.50:
        st.write("Interpretação: dependência moderada. Vale promover B fortes para reduzir risco.")
    else:
        st.write("Interpretação: dependência baixa. Menos risco, mas exige atenção para eficiência de catálogo.")

    # Se houver dados de ads e margem, traz leitura extra
    if not edf.empty and ("investimento_ads" in df_f.columns):
        st.divider()
        st.markdown("### 1.4 Leitura de lucro e risco (quando enviado o arquivo opcional)")
        ok_rows = df_f["risco_lucro"].value_counts()
        rr = pd.DataFrame({"Classificação": ok_rows.index, "Itens": ok_rows.values})
        st.dataframe(rr, use_container_width=True, hide_index=True)

        # top prejuízo
        if "lucro_pos_ads_0_30" in df_f.columns:
            neg = df_f[pd.notna(df_f["lucro_pos_ads_0_30"]) & (df_f["lucro_pos_ads_0_30"] < 0)].copy()
            neg = neg.sort_values("lucro_pos_ads_0_30", ascending=True).head(15)
            if len(neg):
                st.markdown("Top 15 itens com prejuízo pós ads no 0-30")
                show = neg[["MLB","Título","Fat. 0-30","investimento_ads","tacos_0_30","lucro_pos_ads_0_30","risco_lucro"]].copy()
                show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
                show["investimento_ads"] = show["investimento_ads"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
                show["tacos_0_30"] = show["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
                show["lucro_pos_ads_0_30"] = show["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
                st.dataframe(show, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("## 2. Segmentação de Produtos")

    st.markdown("### 2.1 Produtos Âncora")
    top5_anchors = anchors.head(5).copy()
    fat_sum_top5 = float(top5_anchors["Fat total"].sum()) if len(top5_anchors) else 0.0
    st.write(f"Quantidade de âncoras: {br_int(len(anchors))}")
    st.write(f"Top 5 âncoras, faturamento somado: {br_money(fat_sum_top5)}")

    if len(top5_anchors):
        cols = ["MLB","Título","Fat total","Qtd total","TM total"]
        for c in ["tacos_0_30","lucro_pos_ads_0_30","risco_lucro"]:
            if c in top5_anchors.columns:
                cols.append(c)
        show = top5_anchors[cols].copy()
        show["Fat total"] = show["Fat total"].map(br_money)
        show["Qtd total"] = show["Qtd total"].map(br_int)
        show["TM total"] = show["TM total"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        if "tacos_0_30" in show.columns:
            show["tacos_0_30"] = show["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
        if "lucro_pos_ads_0_30" in show.columns:
            show["lucro_pos_ads_0_30"] = show["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("Padrão observado")
    st.write("Âncoras sustentam previsibilidade. Queda nelas costuma ser ruptura, perda de ranking, piora de frete ou concorrência.")
    st.markdown("Ação recomendada")
    st.write("Defesa primeiro, depois escala. Escale somente onde TACOS e lucro pós ads estiverem saudáveis, quando o arquivo opcional existir.")

    st.markdown("### 2.2 Alerta de Queda, fuga de receita")
    loss_total = float(drop_alert["Perda estimada"].sum()) if len(drop_alert) else 0.0
    st.write(f"Produtos em fuga: {br_int(len(drop_alert))}")
    st.write(f"Perda financeira estimada somada: {br_money(loss_total)}")

    if len(drop_alert):
        cols = ["MLB","Título","Curva 31-60","Curva 61-90","Curva 0-30","Fat anterior ref","Fat. 0-30","Perda estimada"]
        for c in ["tacos_0_30","lucro_pos_ads_0_30","risco_lucro"]:
            if c in drop_alert.columns:
                cols.append(c)
        show = drop_alert[cols].head(20).copy()
        show["Fat anterior ref"] = show["Fat anterior ref"].map(br_money)
        show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
        show["Perda estimada"] = show["Perda estimada"].map(br_money)
        if "tacos_0_30" in show.columns:
            show["tacos_0_30"] = show["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
        if "lucro_pos_ads_0_30" in show.columns:
            show["lucro_pos_ads_0_30"] = show["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("Padrão observado")
    st.write("Queda de A ou B para C ou sem venda costuma vir de ruptura, aumento de concorrência, alteração de preço ou perda de posicionamento.")
    st.markdown("Ação recomendada")
    st.write("Correção imediata com checklist. Se tiver lucro pós ads bom, a prioridade sobe, porque recuperar esse item devolve dinheiro rápido.")

    st.markdown("### 2.3 Produtos em Ascensão")
    st.write(f"Produtos em ascensão: {br_int(len(rise_to_A))}")
    if len(rise_to_A):
        cols = ["MLB","Título","Curva 0-30","Curva 31-60","Curva 61-90","Fat. 0-30","Qntd 0-30"]
        for c in ["tacos_0_30","lucro_pos_ads_0_30","risco_lucro"]:
            if c in rise_to_A.columns:
                cols.append(c)
        show = rise_to_A[cols].head(20).copy()
        show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
        show["Qntd 0-30"] = show["Qntd 0-30"].map(br_int)
        if "tacos_0_30" in show.columns:
            show["tacos_0_30"] = show["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
        if "lucro_pos_ads_0_30" in show.columns:
            show["lucro_pos_ads_0_30"] = show["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("Ação recomendada")
    st.write("Ataque com controle. Se margem pós ads estiver boa, vale escalar. Se TACOS estiver alto, ajuste campanha antes de colocar mais verba.")

    st.markdown("### 2.4 Estoque morto e combos ou liquidação")
    st.write(f"Sem venda no 0-30, com histórico: {br_int(len(dead_stock))}")
    st.write(f"Candidatos a combo (TM histórico < R$ 35): {br_int(len(dead_stock_combo))}")

    if len(dead_stock_combo):
        cols = ["MLB","Título","TM histórico","Fat. 31-60","Fat. 61-90","Fat. 91-120"]
        for c in ["custo_unitario","margem_percentual","investimento_ads","risco_lucro"]:
            if c in dead_stock_combo.columns:
                cols.append(c)
        show = dead_stock_combo[cols].head(20).copy()
        show["TM histórico"] = show["TM histórico"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        show["Fat. 31-60"] = show["Fat. 31-60"].map(br_money)
        show["Fat. 61-90"] = show["Fat. 61-90"].map(br_money)
        show["Fat. 91-120"] = show["Fat. 91-120"].map(br_money)
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("## 4. Plano Tático Operacional (15 e 30 Dias)")
    front_order = ["LIMPEZA, Parado", "CORREÇÃO, Fuga de receita", "CORREÇÃO, Revitalizar", "ATAQUE, Crescimento", "DEFESA, Âncora", "Otimização"]
    front_counts = plan["Frente"].value_counts()
    front_df = pd.DataFrame({"Frente": front_order, "Itens": [int(front_counts.get(f, 0)) for f in front_order]})
    st.dataframe(front_df, use_container_width=True, hide_index=True)

    st.markdown("### Tabela operacional por frente")
    op_cols = ["Frente","MLB","Título","Curva 0-30","Fat. 0-30","Ação sugerida","Plano 15 dias","Plano 30 dias"]
    for c in ["tacos_0_30","roas_0_30","lucro_pos_ads_0_30","risco_lucro"]:
        if c in plan.columns:
            op_cols.append(c)

    op = plan[op_cols].copy().sort_values(["Frente", "Fat. 0-30"], ascending=[True, False])

    st.download_button(
        "Baixar CSV do plano operacional completo",
        data=to_csv_bytes(op),
        file_name="plano_operacional_completo.csv",
        mime="text/csv"
    )

    for fr in front_order:
        subset = op[op["Frente"] == fr].head(20).copy()
        if len(subset) == 0:
            continue
        subset["Fat. 0-30"] = subset["Fat. 0-30"].map(br_money)
        if "tacos_0_30" in subset.columns:
            subset["tacos_0_30"] = subset["tacos_0_30"].apply(lambda x: f"{round(float(x)*100,2)}%" if pd.notna(x) else "-")
        if "roas_0_30" in subset.columns:
            subset["roas_0_30"] = subset["roas_0_30"].apply(lambda x: round(float(x), 2) if pd.notna(x) else "-")
        if "lucro_pos_ads_0_30" in subset.columns:
            subset["lucro_pos_ads_0_30"] = subset["lucro_pos_ads_0_30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        st.markdown(f"#### {fr} (top 20 por faturamento 0-30)")
        st.dataframe(subset, use_container_width=True, hide_index=True)
