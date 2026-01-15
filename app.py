import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard Curva ABC", layout="wide")

st.title("Dashboard Curva ABC e Movimento por Períodos")

@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_excel(file, sheet_name="Export")
    # padroniza tipos
    for col in ["Qntd 0-30","Qntd 31-60","Qntd 61-90","Qntd 91-120"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    # garante curvas como string
    for col in ["Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]:
        df[col] = df[col].fillna("-").astype(str)
    return df

def br_money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_int(x: float) -> str:
    return f"{int(x):,}".replace(",", ".")

periods = [
    ("0-30", "Curva 0-30", "Qntd 0-30", "Fat. 0-30"),
    ("31-60", "Curva 31-60", "Qntd 31-60", "Fat. 31-60"),
    ("61-90", "Curva 61-90", "Qntd 61-90", "Fat. 61-90"),
    ("91-120", "Curva 91-120", "Qntd 91-120", "Fat. 91-120"),
]

rank = {"-": 0, "C": 1, "B": 2, "A": 3}

uploaded = st.file_uploader("Envie o arquivo Excel da Curva ABC", type=["xlsx"])

if not uploaded:
    st.info("Envie o arquivo para carregar o dashboard.")
    st.stop()

df = load_data(uploaded)

# filtros
st.sidebar.header("Filtros")
curva_filtro = st.sidebar.multiselect(
    "Curvas para incluir",
    options=["A","B","C","-"],
    default=["A","B","C","-"]
)

# aplica filtro se o usuário quiser excluir alguma curva em alguma visão
# aqui, como cada período tem uma curva diferente, o filtro vai ser aplicado em qualquer período
mask_any = (
    df["Curva 0-30"].isin(curva_filtro) |
    df["Curva 31-60"].isin(curva_filtro) |
    df["Curva 61-90"].isin(curva_filtro) |
    df["Curva 91-120"].isin(curva_filtro)
)
df_f = df[mask_any].copy()

total_ads = len(df_f)

# KPIs por período
kpi_rows = []
for p, cc, qq, ff in periods:
    qty = df_f[qq].sum()
    fat = df_f[ff].sum()
    tm = fat / qty if qty > 0 else np.nan
    kpi_rows.append({"Período": p, "Qtd": qty, "Faturamento": fat, "Ticket médio": tm})

kpi_df = pd.DataFrame(kpi_rows)

# KPIs topo
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de anúncios", br_int(total_ads))
c2.metric("Faturamento total (4 janelas)", br_money(df_f[[p[3] for p in periods]].sum().sum()))
c3.metric("Qtd total (4 janelas)", br_int(df_f[[p[2] for p in periods]].sum().sum()))
tt_fat = df_f[[p[3] for p in periods]].sum().sum()
tt_qty = df_f[[p[2] for p in periods]].sum().sum()
c4.metric("Ticket médio total", br_money(tt_fat / tt_qty if tt_qty > 0 else 0.0))

st.divider()

# Tabelas resumo
left, right = st.columns([1.2, 1])

with left:
    st.subheader("Resumo por período")
    show = kpi_df.copy()
    show["Qtd"] = show["Qtd"].map(br_int)
    show["Faturamento"] = show["Faturamento"].map(br_money)
    show["Ticket médio"] = show["Ticket médio"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
    st.dataframe(show, use_container_width=True, hide_index=True)

with right:
    st.subheader("Distribuição de curvas por período")
    dist_rows = []
    for p, cc, qq, ff in periods:
        vc = df_f[cc].value_counts()
        for curva in ["A","B","C","-"]:
            dist_rows.append({"Período": p, "Curva": curva, "Anúncios": int(vc.get(curva, 0))})
    dist_df = pd.DataFrame(dist_rows)
    fig = px.bar(dist_df, x="Período", y="Anúncios", color="Curva", barmode="stack")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Faturamento por curva por período
st.subheader("Faturamento por curva e período")
rev_rows = []
for p, cc, qq, ff in periods:
    grp = df_f.groupby(cc)[ff].sum()
    for curva in ["A","B","C","-"]:
        rev_rows.append({"Período": p, "Curva": curva, "Faturamento": float(grp.get(curva, 0.0))})
rev_df = pd.DataFrame(rev_rows)
fig2 = px.bar(rev_df, x="Período", y="Faturamento", color="Curva", barmode="group")
st.plotly_chart(fig2, use_container_width=True)

# Ticket médio por período
st.subheader("Ticket médio (ponderado) por período")
tm_df = kpi_df.copy()
tm_df["Ticket médio"] = tm_df["Ticket médio"].fillna(0.0)
fig3 = px.line(tm_df, x="Período", y="Ticket médio", markers=True)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# Perda acumulada: A que deixou de ser A
st.subheader("Perda acumulada: itens que eram A e deixaram de ser A")
def cohort_loss(prev_curve_col, prev_fat_col, next_curve_col, next_fat_col, curve="A"):
    cohort = df_f[df_f[prev_curve_col] == curve]
    left = cohort[cohort[next_curve_col] != curve]
    stayed = cohort[cohort[next_curve_col] == curve]
    return {
        "cohort_n": len(cohort),
        "left_n": len(left),
        "stayed_n": len(stayed),
        "prev_fat_left": float(left[prev_fat_col].sum()),
        "next_fat_left": float(left[next_fat_col].sum()),
        "fat_drop_left": float((left[prev_fat_col] - left[next_fat_col]).sum()),
    }

t1 = cohort_loss("Curva 0-30", "Fat. 0-30", "Curva 31-60", "Fat. 31-60")
t2 = cohort_loss("Curva 31-60", "Fat. 31-60", "Curva 61-90", "Fat. 61-90")
t3 = cohort_loss("Curva 61-90", "Fat. 61-90", "Curva 91-120", "Fat. 91-120")

loss_table = pd.DataFrame([
    {"Transição": "0-30 -> 31-60", "A no período anterior": t1["cohort_n"], "Saiu de A": t1["left_n"], "Perda acumulada": t1["fat_drop_left"]},
    {"Transição": "31-60 -> 61-90", "A no período anterior": t2["cohort_n"], "Saiu de A": t2["left_n"], "Perda acumulada": t2["fat_drop_left"]},
    {"Transição": "61-90 -> 91-120", "A no período anterior": t3["cohort_n"], "Saiu de A": t3["left_n"], "Perda acumulada": t3["fat_drop_left"]},
])
show_loss = loss_table.copy()
show_loss["Perda acumulada"] = show_loss["Perda acumulada"].map(br_money)
st.dataframe(show_loss, use_container_width=True, hide_index=True)

st.divider()

# Tabelas de ação
st.subheader("Tabelas de ação")

# Âncoras: A em todos os períodos
anchors = df_f[
    (df_f["Curva 0-30"]=="A") &
    (df_f["Curva 31-60"]=="A") &
    (df_f["Curva 61-90"]=="A") &
    (df_f["Curva 91-120"]=="A")
].copy()

anchors["Qtd total"] = df_f[["Qntd 0-30","Qntd 31-60","Qntd 61-90","Qntd 91-120"]].sum(axis=1)
anchors["Fat total"] = df_f[["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]].sum(axis=1)
anchors = anchors.sort_values("Fat total", ascending=False)

with st.expander(f"Produtos âncora (A em todos os períodos): {len(anchors)}"):
    show = anchors[["MLB","Título","Qtd total","Fat total"]].copy()
    show["Qtd total"] = show["Qtd total"].map(br_int)
    show["Fat total"] = show["Fat total"].map(br_money)
    st.dataframe(show, use_container_width=True, hide_index=True)

# A que caiu no 61-90
a_drop = df_f[(df_f["Curva 0-30"]=="A") & (df_f["Curva 61-90"]!="A")].copy()
a_drop["Fat 0-30"] = a_drop["Fat. 0-30"]
a_drop = a_drop.sort_values("Fat 0-30", ascending=False)

with st.expander(f"A no 0-30 que caiu no 61-90 (virou B/C/sem venda): {len(a_drop)}"):
    show = a_drop[["MLB","Título","Curva 0-30","Qntd 0-30","Fat. 0-30","Curva 61-90","Qntd 61-90","Fat. 61-90","Curva 91-120","Qntd 91-120","Fat. 91-120"]].copy()
    for col in ["Fat. 0-30","Fat. 61-90","Fat. 91-120"]:
        show[col] = show[col].map(br_money)
    st.dataframe(show, use_container_width=True, hide_index=True)

# Subiu para A depois
rise_to_A = df_f[
    df_f["Curva 0-30"].isin(["B","C","-"]) &
    ((df_f["Curva 31-60"]=="A") | (df_f["Curva 61-90"]=="A") | (df_f["Curva 91-120"]=="A"))
].copy()
rise_to_A["Fat total"] = rise_to_A[["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]].sum(axis=1)
rise_to_A = rise_to_A.sort_values("Fat total", ascending=False)

with st.expander(f"Produtos que eram B/C/sem venda no 0-30 e viraram A depois: {len(rise_to_A)}"):
    show = rise_to_A[["MLB","Título","Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120","Fat total"]].copy()
    show["Fat total"] = show["Fat total"].map(br_money)
    st.dataframe(show, use_container_width=True, hide_index=True)

# C recorrente (3 ou 4 períodos como C)
tmp = df_f.copy()
tmp["c_count"] = (tmp[["Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]]=="C").sum(axis=1)
c_rec = tmp[tmp["c_count"]>=3].copy()
c_rec["Fat total"] = c_rec[["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]].sum(axis=1)
c_rec = c_rec.sort_values("Fat total", ascending=False)

with st.expander(f"Curva C recorrente (3 ou 4 períodos em C): {len(c_rec)}"):
    show = c_rec[["MLB","Título","c_count","Fat total","Qntd 0-30","Qntd 31-60","Qntd 61-90"]].copy()
    show["Fat total"] = show["Fat total"].map(br_money)
    st.dataframe(show, use_container_width=True, hide_index=True)

# Sem vendas últimos 90 dias (proxy)
no_sales_90 = df_f[(df_f["Qntd 0-30"]==0) & (df_f["Qntd 31-60"]==0) & (df_f["Qntd 61-90"]==0)].copy()
no_sales_90["Fat histórico (91-120)"] = no_sales_90["Fat. 91-120"]
no_sales_90 = no_sales_90.sort_values("Fat histórico (91-120)", ascending=False)

with st.expander(f"Sem vendas nos últimos 90 dias (0-30, 31-60, 61-90): {len(no_sales_90)}"):
    show = no_sales_90[["MLB","Título","Curva 0-30","Curva 31-60","Curva 61-90","Fat histórico (91-120)"]].copy()
    show["Fat histórico (91-120)"] = show["Fat histórico (91-120)"].map(br_money)
    st.dataframe(show, use_container_width=True, hide_index=True)

