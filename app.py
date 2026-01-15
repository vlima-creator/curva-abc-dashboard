import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Curva ABC, Dashboard e Relatório", layout="wide")
st.title("Curva ABC de Vendas, Dashboard e Relatório Estratégico")

@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_excel(file, sheet_name="Export")

    # Tipos numéricos
    qty_cols = ["Qntd 0-30", "Qntd 31-60", "Qntd 61-90", "Qntd 91-120"]
    fat_cols = ["Fat. 0-30", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120"]
    curve_cols = ["Curva 0-30", "Curva 31-60", "Curva 61-90", "Curva 91-120"]

    for col in qty_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    for col in fat_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    for col in curve_cols:
        if col in df.columns:
            df[col] = df[col].fillna("-").astype(str).str.strip()
        else:
            df[col] = "-"

    # Campos principais
    for col in ["MLB", "Título"]:
        if col not in df.columns:
            df[col] = ""

    return df

def br_money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_int(x: float) -> str:
    return f"{int(x):,}".replace(",", ".")

def safe_div(a, b):
    return a / b if b and b != 0 else np.nan

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

uploaded = st.file_uploader("Envie o arquivo Excel da Curva ABC", type=["xlsx"])
if not uploaded:
    st.info("Envie o arquivo para carregar o dashboard e o relatório.")
    st.stop()

df = load_data(uploaded)

# =========================
# Sidebar
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
# Métricas base
# =========================
qty_cols = ["Qntd 0-30", "Qntd 31-60", "Qntd 61-90", "Qntd 91-120"]
fat_cols = ["Fat. 0-30", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120"]
curve_cols = ["Curva 0-30", "Curva 31-60", "Curva 61-90", "Curva 91-120"]

df_f["Qtd total"] = df_f[qty_cols].sum(axis=1)
df_f["Fat total"] = df_f[fat_cols].sum(axis=1)
df_f["TM total"] = np.where(df_f["Qtd total"] > 0, df_f["Fat total"] / df_f["Qtd total"], np.nan)

for p in ["0-30", "31-60", "61-90", "91-120"]:
    df_f[f"rank_{p}"] = df_f[f"Curva {p}"].map(rank).fillna(0).astype(int)

df_f["queda_recente"] = df_f["rank_0-30"] < df_f["rank_31-60"]
df_f["queda_forte"] = (df_f["rank_31-60"] - df_f["rank_0-30"]) >= 2

total_ads = len(df_f)

# KPIs por período
kpi_rows = []
for p, cc, qq, ff in periods:
    qty = df_f[qq].sum()
    fat = df_f[ff].sum()
    tm = safe_div(fat, qty)
    kpi_rows.append({"Período": p, "Qtd": qty, "Faturamento": fat, "Ticket médio": tm})
kpi_df = pd.DataFrame(kpi_rows)

# =========================
# Segmentações principais
# =========================

# 1) Produtos Âncora: A em todos os períodos disponíveis
anchors = df_f[
    (df_f["Curva 0-30"] == "A") &
    (df_f["Curva 31-60"] == "A") &
    (df_f["Curva 61-90"] == "A") &
    (df_f["Curva 91-120"] == "A")
].copy()

anchors["Fat total"] = anchors[fat_cols].sum(axis=1)
anchors = anchors.sort_values("Fat total", ascending=False)

# 2) Alerta de queda (fuga de receita):
# eram A ou B em 31-60 ou 61-90 e caíram para C ou - agora (0-30)
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

# 3) Produtos em ascensão:
# eram C/B/- e viraram A no 0-30
rise_to_A = df_f[
    (df_f["Curva 0-30"] == "A") &
    (df_f["Curva 31-60"].isin(["B", "C", "-"]) | df_f["Curva 61-90"].isin(["B", "C", "-"]) | df_f["Curva 91-120"].isin(["B", "C", "-"]))
].copy()
rise_to_A = rise_to_A.sort_values("Fat. 0-30", ascending=False)

# 4) Estoque morto e candidatos a combo:
# sem vendas em 0-30, mas com histórico anterior, e ticket médio histórico < 35
hist_qty = df_f["Qntd 31-60"] + df_f["Qntd 61-90"] + df_f["Qntd 91-120"]
hist_fat = df_f["Fat. 31-60"] + df_f["Fat. 61-90"] + df_f["Fat. 91-120"]
df_f["TM histórico"] = np.where(hist_qty > 0, hist_fat / hist_qty, np.nan)

dead_stock = df_f[(df_f["Fat. 0-30"] == 0) & (hist_fat > 0)].copy()
dead_stock_combo = dead_stock[dead_stock["TM histórico"] < 35].copy()
dead_stock_combo = dead_stock_combo.sort_values("TM histórico", ascending=True)

# 5) Inativar e Revitalizar, mantendo suas regras cirúrgicas
tmp = df_f.copy()
tmp["c_count"] = (tmp[curve_cols] == "C").sum(axis=1)
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
# Ação sugerida com Plano 15 e 30 dias
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

    # Prioridades primeiro
    if is_inactivate:
        return (
            "Inativar ou pausar",
            "Dia 1 a 3: validar se existe estoque e se o anúncio está ativo. Se estiver tudo ok e mesmo assim não vende, pausar.\n"
            "Dia 4 a 10: realocar foco para itens com giro. Se for item estratégico, fazer 1 ajuste simples de preço ou frete.\n"
            "Dia 11 a 15: se não houver sinal, manter pausado.",
            "Semana 1: decidir manter no catálogo ou retirar.\n"
            "Semana 2: se mantiver, reativar com meta mínima de venda e teste de página.\n"
            "Semana 3 e 4: se não reagir, inativar definitivo."
        )

    if is_combo:
        return (
            "Liquidação ou combos",
            "Dia 1 a 5: montar combo com âncoras ou itens B. Objetivo é girar estoque, não margem máxima.\n"
            "Dia 6 a 15: ajustar preço do combo e colocar destaque no anúncio, focar em ganho de conversão.",
            "Semana 1: criar variações e kits para aumentar saída.\n"
            "Semana 2 a 4: se girar, manter como estratégia de cauda. Se não girar, caminhar para inativação."
        )

    if is_drop:
        return (
            "Correção imediata de fuga de receita",
            "Dia 1 a 2: checar ruptura, prazo, reputação e concorrência direta.\n"
            "Dia 3 a 7: ajustar preço e frete para faixa competitiva.\n"
            "Dia 8 a 15: reativar mídia leve com termos exatos e cortar termos ruins.",
            "Semana 1: ajustar título e atributos para recuperar relevância.\n"
            "Semana 2: otimizar página do anúncio para conversão.\n"
            "Semana 3 e 4: manter investimento só onde há venda e recuperar curva."
        )

    if is_anchor:
        return (
            "Defesa e escala controlada",
            "Dia 1 a 3: garantir estoque e evitar ruptura.\n"
            "Dia 4 a 10: melhorar conversão do anúncio com ajustes objetivos.\n"
            "Dia 11 a 15: aumentar orçamento em passos pequenos, manter controle de desperdício.",
            "Semana 1: separar campanhas por intenção de busca.\n"
            "Semana 2: testar ajuste pequeno de preço.\n"
            "Semana 3 e 4: escalar mantendo ticket e margem sob controle."
        )

    if is_rise:
        return (
            "Ataque para consolidar crescimento",
            "Dia 1 a 5: identificar gatilho de crescimento e replicar.\n"
            "Dia 6 a 10: ampliar exposição em termos rentáveis.\n"
            "Dia 11 a 15: reforçar página do anúncio para segurar conversão.",
            "Semana 1: estruturar campanhas separadas por termos fortes e long tail.\n"
            "Semana 2: proteger ticket médio.\n"
            "Semana 3 e 4: escalar se não travar estoque."
        )

    if is_opp:
        return (
            "Oportunidade 50 a 60, alavancar ou escoar",
            "Dia 1 a 3: validar margem e competitividade.\n"
            "Dia 4 a 10: aumentar exposição em termos que vendem.\n"
            "Dia 11 a 15: ajustar lances só nos termos vencedores.",
            "Semana 1: otimizar página para conversão.\n"
            "Semana 2: testar kit ou variação para subir ticket.\n"
            "Semana 3 e 4: consolidar como projeto de escala ou escoar com meta clara."
        )

    if is_revitalize:
        return (
            "Revitalizar com ajuste rápido",
            "Dia 1 a 4: auditoria do anúncio, preço, frete, título, fotos e estoque.\n"
            "Dia 5 a 10: campanha leve, termos específicos.\n"
            "Dia 11 a 15: aumentar só onde tiver venda.",
            "Semana 1: reorganizar variações e atributos.\n"
            "Semana 2: testar kit ou condição comercial.\n"
            "Semana 3 e 4: se não reagir, reduzir prioridade."
        )

    # Default
    curva0 = row["Curva 0-30"]
    if curva0 == "A":
        return (
            "Manter e otimizar",
            "Dia 1 a 7: cortar desperdício e melhorar conversão.\nDia 8 a 15: ajustar lances e termos.",
            "Semana 1: melhorias na página.\nSemana 2 a 4: escalar apenas se mantiver ticket e giro."
        )
    if curva0 in ["B", "C"]:
        return (
            "Otimizar e definir foco",
            "Dia 1 a 5: checar competitividade.\nDia 6 a 15: decidir se vira crescimento ou mix.",
            "Semana 1: estratégia por margem e giro.\nSemana 2 a 4: executar e medir."
        )
    return (
        "Sem venda recente, avaliar continuidade",
        "Dia 1 a 7: confirmar anúncio ativo e estoque.\nDia 8 a 15: se não houver sinal, pausar.",
        "Semana 1: testar ajustes mínimos.\nSemana 2 a 4: se não reagir, inativar."
    )

plan = df_f.copy()
actions = plan.apply(action_bundle, axis=1, result_type="expand")
plan["Ação sugerida"] = actions[0]
plan["Plano 15 dias"] = actions[1]
plan["Plano 30 dias"] = actions[2]

def status_bucket(idx):
    if idx in anchors.index:
        return "DEFESA, Âncora"
    if idx in drop_alert.index:
        return "CORREÇÃO, Fuga de receita"
    if idx in rise_to_A.index or idx in opp_50_60.index:
        return "ATAQUE, Crescimento"
    if idx in dead_stock_combo.index or idx in inactivate.index:
        return "LIMPEZA, Parado"
    if idx in revitalize.index:
        return "CORREÇÃO, Revitalizar"
    return "Otimização"

plan["Frente"] = [status_bucket(i) for i in plan.index]

# =========================
# Diagnóstico macro calculado
# =========================

# Distribuição 0-30
dist_0_30 = df_f["Curva 0-30"].value_counts().reindex(["A", "B", "C", "-"]).fillna(0).astype(int)
dist_0_30_df = pd.DataFrame({
    "Curva": dist_0_30.index,
    "Anúncios": dist_0_30.values
})

# Concentração de faturamento na curva A (0-30)
fat_0_30_total = float(df_f["Fat. 0-30"].sum())
fat_0_30_A = float(df_f.loc[df_f["Curva 0-30"] == "A", "Fat. 0-30"].sum())
conc_A_0_30 = safe_div(fat_0_30_A, fat_0_30_total)

# Ticket médio trend (0-30 vs 31-60 vs 61-90)
tm_0_30 = float(kpi_df.loc[kpi_df["Período"] == "0-30", "Ticket médio"].iloc[0])
tm_31_60 = float(kpi_df.loc[kpi_df["Período"] == "31-60", "Ticket médio"].iloc[0])
tm_61_90 = float(kpi_df.loc[kpi_df["Período"] == "61-90", "Ticket médio"].iloc[0])

def tm_direction(a, b, c):
    if np.isnan(a) or np.isnan(b) or np.isnan(c):
        return "Sem dados suficientes para leitura do ticket médio."
    # Lógica simples de direção
    if a < b < c:
        return "O ticket médio está subindo de forma consistente. Isso tende a ajudar margem, mas pode reduzir volume se o preço estiver esticando."
    if a > b > c:
        return "O ticket médio está caindo de forma consistente. Isso pode indicar promoções fortes ou mix mais barato, e normalmente pressiona margem."
    if b < a and c > b:
        return "O ticket caiu e depois recuperou. Isso costuma indicar período de promoções, seguido de retorno do mix ou ajuste de preço."
    if b > a and c < b:
        return "O ticket subiu e depois caiu. Pode ser efeito de ruptura dos itens de maior valor, ou mudança no mix."
    return "O ticket médio está oscilando. Vale cruzar com mix e concorrência para entender o impacto na margem."

tm_reading = tm_direction(tm_0_30, tm_31_60, tm_61_90)

# =========================
# KPIs topo
# =========================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de anúncios", br_int(total_ads))
c2.metric("Faturamento total (4 janelas)", br_money(float(df_f[fat_cols].sum().sum())))
c3.metric("Quantidade total (4 janelas)", br_int(int(df_f[qty_cols].sum().sum())))
tt_fat = float(df_f[fat_cols].sum().sum())
tt_qty = int(df_f[qty_cols].sum().sum())
c4.metric("Ticket médio total", br_money(safe_div(tt_fat, tt_qty) if tt_qty else 0.0))

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Listas e Exportação", "Plano tático por produto", "Relatório Estratégico"])

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
    sample = plan.sort_values("Fat total", ascending=False)[sample_cols].head(40).copy()
    sample["Fat. 0-30"] = sample["Fat. 0-30"].map(br_money)
    st.dataframe(sample, use_container_width=True, hide_index=True)

# =========================
# TAB 2: Listas e Exportação
# =========================
with tab2:
    st.subheader("Exportação rápida em CSV")

    anchors_export = anchors.copy()
    anchors_export = anchors_export[["MLB", "Título", "Fat total", "Qtd total", "TM total", "Curva 0-30", "Curva 31-60", "Curva 61-90", "Curva 91-120"]]

    inactivate_export = inactivate.copy()
    inactivate_export = inactivate_export[["MLB", "Título", "Fat total", "Qtd total", "Curva 0-30", "Qntd 0-30", "Qntd 31-60", "Qntd 61-90"]]

    revitalize_export = revitalize.copy()
    revitalize_export = revitalize_export[["MLB", "Título", "Fat total", "Qtd total", "Curva 31-60", "Curva 0-30", "Qntd 31-60", "Qntd 0-30"]]

    opp_export = opp_50_60.copy()
    opp_export = opp_export[["MLB", "Título", "Fat total", "Curva 0-30", "Qntd 0-30", "Curva 31-60", "Qntd 31-60"]]

    drop_export = drop_alert.copy()
    drop_export = drop_export[["MLB", "Título", "Curva 31-60", "Curva 61-90", "Curva 0-30", "Fat anterior ref", "Fat. 0-30", "Perda estimada"]]

    combo_export = dead_stock_combo.copy()
    combo_export = combo_export[["MLB", "Título", "TM histórico", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120", "Fat. 0-30"]]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Âncoras:** {len(anchors_export)}")
        st.download_button("Baixar CSV Âncoras", data=to_csv_bytes(anchors_export), file_name="ancoras.csv", mime="text/csv")
    with c2:
        st.markdown(f"**Inativar:** {len(inactivate_export)}")
        st.download_button("Baixar CSV Inativar", data=to_csv_bytes(inactivate_export), file_name="inativar.csv", mime="text/csv")
    with c3:
        st.markdown(f"**Revitalizar:** {len(revitalize_export)}")
        st.download_button("Baixar CSV Revitalizar", data=to_csv_bytes(revitalize_export), file_name="revitalizar.csv", mime="text/csv")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(f"**Oportunidade 50 a 60:** {len(opp_export)}")
        st.download_button("Baixar CSV Oportunidade 50 a 60", data=to_csv_bytes(opp_export), file_name="oportunidade_50_60.csv", mime="text/csv")
    with c5:
        st.markdown(f"**Fuga de receita:** {len(drop_export)}")
        st.download_button("Baixar CSV Fuga de receita", data=to_csv_bytes(drop_export), file_name="fuga_receita.csv", mime="text/csv")
    with c6:
        st.markdown(f"**Combos e liquidação:** {len(combo_export)}")
        st.download_button("Baixar CSV Combos", data=to_csv_bytes(combo_export), file_name="combos_liquidacao.csv", mime="text/csv")

    st.divider()
    st.subheader("Prévia das listas")
    with st.expander("Ver Fuga de receita"):
        show = drop_export.copy()
        show["Fat anterior ref"] = show["Fat anterior ref"].map(br_money)
        show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
        show["Perda estimada"] = show["Perda estimada"].map(br_money)
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
    st.dataframe(show, use_container_width=True, hide_index=True)

# =========================
# TAB 4: Relatório Estratégico (o seu prompt incorporado)
# =========================
with tab4:
    st.subheader("Relatório Estratégico com Plano de Ação")

    # 1) Diagnóstico Macro
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
        st.write("Interpretação: dependência alta da Curva A. Se 1 ou 2 âncoras quebrarem por ruptura ou concorrência, o faturamento do mês sente na hora.")
    elif conc_A_0_30 and conc_A_0_30 >= 0.50:
        st.write("Interpretação: dependência moderada. Está ok, mas vale ter um plano para promover itens B fortes para reduzir risco.")
    else:
        st.write("Interpretação: dependência baixa. Isso reduz risco, mas exige atenção para não perder eficiência em anúncios que realmente sustentam volume.")

    st.divider()

    # 2) Segmentação de Produtos
    st.markdown("## 2. Segmentação de Produtos")

    st.markdown("### 2.1 Produtos Âncora (A em todos os períodos)")
    top5_anchors = anchors.head(5).copy()
    fat_sum_top5 = float(top5_anchors["Fat total"].sum()) if len(top5_anchors) else 0.0
    st.write(f"Quantidade de âncoras: {br_int(len(anchors))}")
    st.write(f"Top 5 âncoras, faturamento somado: {br_money(fat_sum_top5)}")

    if len(top5_anchors):
        show = top5_anchors[["MLB", "Título", "Fat total", "Qtd total", "TM total"]].copy()
        show["Fat total"] = show["Fat total"].map(br_money)
        show["Qtd total"] = show["Qtd total"].map(br_int)
        show["TM total"] = show["TM total"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.write("Não há produtos que ficaram em A em todos os períodos do arquivo.")

    st.markdown("Padrão observado e causa provável")
    st.write("Âncoras sustentam previsibilidade. A causa mais comum de queda nelas é ruptura, perda de ranking por concorrência ou piora de frete e prazo.")
    st.markdown("Ação recomendada")
    st.write("Defesa primeiro, depois escala. Garanta estoque, ajuste conversão e aumente mídia em passos pequenos para não estourar custo e nem canibalizar.")

    st.markdown("### 2.2 Alerta de Queda, fuga de receita")
    loss_total = float(drop_alert["Perda estimada"].sum()) if len(drop_alert) else 0.0
    st.write(f"Produtos em fuga: {br_int(len(drop_alert))}")
    st.write(f"Perda financeira estimada somada: {br_money(loss_total)}")

    if len(drop_alert):
        show = drop_alert[["MLB", "Título", "Curva 31-60", "Curva 61-90", "Curva 0-30", "Fat anterior ref", "Fat. 0-30", "Perda estimada"]].head(20).copy()
        show["Fat anterior ref"] = show["Fat anterior ref"].map(br_money)
        show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
        show["Perda estimada"] = show["Perda estimada"].map(br_money)
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("Padrão observado e causa provável")
    st.write("Queda de A ou B para C ou sem venda costuma vir de ruptura, aumento de concorrência, alteração de preço, perda de posicionamento ou piora de frete.")
    st.markdown("Ação recomendada")
    st.write("Correção imediata com checklist objetivo: estoque, preço, frete, prazo, reputação, termos de busca e reinserção com mídia leve e bem controlada.")

    st.markdown("### 2.3 Produtos em Ascensão (subiram para A no 0-30)")
    st.write(f"Produtos em ascensão: {br_int(len(rise_to_A))}")
    if len(rise_to_A):
        show = rise_to_A[["MLB", "Título", "Curva 0-30", "Curva 31-60", "Curva 61-90", "Fat. 0-30", "Qntd 0-30"]].head(20).copy()
        show["Fat. 0-30"] = show["Fat. 0-30"].map(br_money)
        show["Qntd 0-30"] = show["Qntd 0-30"].map(br_int)
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("O que eles têm em comum")
    st.write("Geralmente é efeito de ganho de ranking, melhoria de conversão e ajuste de oferta. Também pode ser sazonalidade. O app não tem categoria, então o padrão comum real precisa ser confirmado olhando títulos e histórico de preço.")
    st.markdown("Ação recomendada")
    st.write("Ataque com controle. Separar campanhas por intenção de busca e escalar mantendo ticket médio e estoque estável.")

    st.markdown("### 2.4 Estoque morto e candidatos a combo ou liquidação")
    st.write(f"Sem venda no 0-30, com histórico: {br_int(len(dead_stock))}")
    st.write(f"Candidatos a combo (TM histórico < R$ 35): {br_int(len(dead_stock_combo))}")

    if len(dead_stock_combo):
        show = dead_stock_combo[["MLB", "Título", "TM histórico", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120"]].head(20).copy()
        show["TM histórico"] = show["TM histórico"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        show["Fat. 31-60"] = show["Fat. 31-60"].map(br_money)
        show["Fat. 61-90"] = show["Fat. 61-90"].map(br_money)
        show["Fat. 91-120"] = show["Fat. 91-120"].map(br_money)
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("Padrão observado e causa provável")
    st.write("Itens parados com ticket baixo tendem a ficar invisíveis sem incentivo. Muitas vezes são ótimos para kits com âncoras ou para liquidação rápida.")
    st.markdown("Ação recomendada")
    st.write("Combos com itens A, bundles por necessidade e liquidação controlada. O foco é giro e liberar caixa.")

    st.divider()

    # 3) Leitura estratégica e ações por segmento, já embutido nas seções acima

    # 4) Plano tático operacional em quatro frentes
    st.markdown("## 4. Plano Tático Operacional (15 e 30 Dias)")

    front_order = ["LIMPEZA, Parado", "CORREÇÃO, Fuga de receita", "CORREÇÃO, Revitalizar", "ATAQUE, Crescimento", "DEFESA, Âncora", "Otimização"]
    front_counts = plan["Frente"].value_counts()
    front_df = pd.DataFrame({
        "Frente": front_order,
        "Itens": [int(front_counts.get(f, 0)) for f in front_order]
    })
    st.dataframe(front_df, use_container_width=True, hide_index=True)

    st.markdown("### Tabela operacional por frente")
    op_cols = ["Frente", "MLB", "Título", "Curva 0-30", "Fat. 0-30", "Ação sugerida", "Plano 15 dias", "Plano 30 dias"]
    op = plan[op_cols].copy()
    op = op.sort_values(["Frente", "Fat. 0-30"], ascending=[True, False])

    # export do relatório operacional
    st.download_button(
        "Baixar CSV do plano operacional completo",
        data=to_csv_bytes(op),
        file_name="plano_operacional_completo.csv",
        mime="text/csv"
    )

    # exibir por frente, top 20 por frente
    for fr in front_order:
        subset = op[op["Frente"] == fr].head(20).copy()
        if len(subset) == 0:
            continue
        subset["Fat. 0-30"] = subset["Fat. 0-30"].map(br_money)
        st.markdown(f"#### {fr} (top 20 por faturamento 0-30)")
        st.dataframe(subset, use_container_width=True, hide_index=True)
