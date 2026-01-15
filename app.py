import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import StringIO

st.set_page_config(page_title="Dashboard Curva ABC", layout="wide")
st.title("Dashboard Curva ABC e Movimento por Períodos")

@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_excel(file, sheet_name="Export")

    for col in ["Qntd 0-30","Qntd 31-60","Qntd 61-90","Qntd 91-120"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in ["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]:
        df[col] = df[col].fillna("-").astype(str).str.strip()

    for col in ["MLB", "Título"]:
        if col not in df.columns:
            df[col] = ""

    return df

def br_money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_int(x: float) -> str:
    return f"{int(x):,}".replace(",", ".")

def to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    csv = dataframe.to_csv(index=False, sep=";", encoding="utf-8-sig")
    return csv.encode("utf-8-sig")

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

# =========================
# Sidebar: filtros
# =========================
st.sidebar.header("Filtros")
curva_filtro = st.sidebar.multiselect(
    "Curvas para incluir",
    options=["A","B","C","-"],
    default=["A","B","C","-"]
)

mask_any = (
    df["Curva 0-30"].isin(curva_filtro) |
    df["Curva 31-60"].isin(curva_filtro) |
    df["Curva 61-90"].isin(curva_filtro) |
    df["Curva 91-120"].isin(curva_filtro)
)
df_f = df[mask_any].copy()

# Métricas agregadas
df_f["Qtd total"] = df_f[["Qntd 0-30","Qntd 31-60","Qntd 61-90","Qntd 91-120"]].sum(axis=1)
df_f["Fat total"] = df_f[["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]].sum(axis=1)
df_f["TM total"] = np.where(df_f["Qtd total"] > 0, df_f["Fat total"] / df_f["Qtd total"], np.nan)

# Ranks por período
df_f["rank_0_30"] = df_f["Curva 0-30"].map(rank).fillna(0).astype(int)
df_f["rank_31_60"] = df_f["Curva 31-60"].map(rank).fillna(0).astype(int)
df_f["rank_61_90"] = df_f["Curva 61-90"].map(rank).fillna(0).astype(int)
df_f["rank_91_120"] = df_f["Curva 91-120"].map(rank).fillna(0).astype(int)

# Movimento de curva
df_f["delta_31_0"] = df_f["rank_0_30"] - df_f["rank_31_60"]
df_f["delta_61_31"] = df_f["rank_31_60"] - df_f["rank_61_90"]
df_f["delta_91_61"] = df_f["rank_61_90"] - df_f["rank_91_120"]

# =========================
# KPIs por período
# =========================
kpi_rows = []
for p, cc, qq, ff in periods:
    qty = df_f[qq].sum()
    fat = df_f[ff].sum()
    tm = fat / qty if qty > 0 else np.nan
    kpi_rows.append({"Período": p, "Qtd": qty, "Faturamento": fat, "Ticket médio": tm})
kpi_df = pd.DataFrame(kpi_rows)

total_ads = len(df_f)

# =========================
# Regras cirúrgicas: listas operacionais
# =========================

# Âncoras: A em todos os períodos
anchors = df_f[
    (df_f["Curva 0-30"]=="A") &
    (df_f["Curva 31-60"]=="A") &
    (df_f["Curva 61-90"]=="A") &
    (df_f["Curva 91-120"]=="A")
].copy()

# C recorrente (3 ou 4 períodos em C)
tmp = df_f.copy()
tmp["c_count"] = (tmp[["Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]]=="C").sum(axis=1)
c_rec = tmp[tmp["c_count"]>=3].copy()

# Sem vendas (proxy por janelas)
no_sales_90 = df_f[(df_f["Qntd 0-30"]==0) & (df_f["Qntd 31-60"]==0) & (df_f["Qntd 61-90"]==0)].copy()
no_sales_60 = df_f[(df_f["Qntd 0-30"]==0) & (df_f["Qntd 31-60"]==0)].copy()

# Queda de curva recente (31-60 -> 0-30) e queda forte
df_f["queda_recente"] = df_f["rank_0_30"] < df_f["rank_31_60"]
df_f["queda_forte"] = (df_f["rank_31_60"] - df_f["rank_0_30"]) >= 2  # caiu 2 níveis ou mais

# Oportunidade: vendeu 50 a 60 unidades em algum período recente
opp_50_60 = df_f[
    ((df_f["Qntd 0-30"] >= 50) & (df_f["Qntd 0-30"] <= 60)) |
    ((df_f["Qntd 31-60"] >= 50) & (df_f["Qntd 31-60"] <= 60))
].copy()

# Revitalizar cirúrgico:
# Regra 1: caiu de curva recente e vendeu entre 30 e 40 no 0-30 (tem sinal de tração agora)
# Regra 2: caiu de curva recente e tinha 30-40 no 31-60, mas 0-30 caiu para 0-10 (perdeu tração)
# Regra 3: queda forte e ainda tem volume (1-25) para tentar recuperar rápido
revitalize = df_f[
    (
        df_f["queda_recente"] &
        (
            ((df_f["Qntd 0-30"] >= 30) & (df_f["Qntd 0-30"] <= 40)) |
            (((df_f["Qntd 31-60"] >= 30) & (df_f["Qntd 31-60"] <= 40)) & (df_f["Qntd 0-30"] <= 10)) |
            (df_f["queda_forte"] & (df_f["Qntd 0-30"] >= 1) & (df_f["Qntd 0-30"] <= 25))
        )
    )
].copy()

# Inativar cirúrgico:
# Regra A: sem vendas 90 (0-30,31-60,61-90 = 0) -> inativar
# Regra B: proxy sem vendas 60 + curva atual fraca (C ou "-") + houve queda de curva -> inativar
# Regra C: C recorrente + sem vendas recentes (0-30 e 31-60 = 0) -> inativar
inactivate = df_f[
    (df_f.index.isin(no_sales_90.index)) |
    (
        (df_f.index.isin(no_sales_60.index)) &
        (df_f["Curva 0-30"].isin(["-","C"])) &
        (df_f["queda_recente"])
    ) |
    (
        (df_f.index.isin(c_rec.index)) &
        (df_f["Qntd 0-30"]==0) &
        (df_f["Qntd 31-60"]==0)
    )
].copy()

# Itens que eram A e caíram no 61-90 (recuperação)
a_drop_61_90 = df_f[(df_f["Curva 0-30"]=="A") & (df_f["Curva 61-90"]!="A")].copy()

# Itens que subiram para A depois
rise_to_A = df_f[
    df_f["Curva 0-30"].isin(["B","C","-"]) &
    ((df_f["Curva 31-60"]=="A") | (df_f["Curva 61-90"]=="A") | (df_f["Curva 91-120"]=="A"))
].copy()

# =========================
# Ação sugerida + plano tático 15 e 30 dias
# =========================

def action_bundle(row) -> tuple[str, str, str]:
    idx = row.name
    curva0 = row["Curva 0-30"]
    q0 = row["Qntd 0-30"]

    is_anchor = idx in anchors.index
    is_inactivate = idx in inactivate.index
    is_revitalize = idx in revitalize.index
    is_opp = idx in opp_50_60.index
    is_a_drop = idx in a_drop_61_90.index
    is_rise = idx in rise_to_A.index
    is_c_rec = idx in c_rec.index

    # 1) Inativar
    if is_inactivate:
        acao = "Inativar ou pausar"
        p15 = (
            "Dia 1 a 3: confirmar estoque, anúncio ativo e preço.\n"
            "Dia 4 a 7: se for item estratégico, fazer um último ajuste simples de página.\n"
            "Dia 8 a 15: sem reação, pausar e tirar do foco de mídia."
        )
        p30 = (
            "Semana 1: decidir manter no catálogo ou remover.\n"
            "Semana 2: se mantiver, reposicionar com kit ou variação.\n"
            "Semana 3 e 4: reativar só com meta mínima de venda, senão inativar definitivo."
        )
        return acao, p15, p30

    # 2) Âncoras
    if is_anchor:
        acao = "Escalar com controle e defender posição"
        p15 = (
            "Dia 1 a 3: zerar risco de ruptura e prazo alto.\n"
            "Dia 4 a 7: melhorar conversão do anúncio (título, fotos, variações).\n"
            "Dia 8 a 15: aumentar verba em passos pequenos e cortar termos ruins."
        )
        p30 = (
            "Semana 1: teste de preço pequeno e acompanhamento de conversão.\n"
            "Semana 2: separar campanhas por termos principais e termos long tail.\n"
            "Semana 3 e 4: escalar mantendo controle de custo e evitando canibalização."
        )
        return acao, p15, p30

    # 3) Oportunidade 50 a 60
    if is_opp:
        acao = "Oportunidade 50 a 60, alavancar ou escoar"
        p15 = (
            "Dia 1 a 3: validar margem e concorrência, não escalar no escuro.\n"
            "Dia 4 a 10: impulsionar termos exatos e melhorar exposição em posicionamentos úteis.\n"
            "Dia 11 a 15: se responder, aumentar lance só nos termos que vendem."
        )
        p30 = (
            "Semana 1: reforçar página do anúncio para segurar conversão com mais tráfego.\n"
            "Semana 2: testar kit ou variação para aumentar ticket.\n"
            "Semana 3 e 4: consolidar como projeto de crescimento ou escoar estoque com meta clara."
        )
        return acao, p15, p30

    # 4) A caiu no 61-90
    if is_a_drop:
        acao = "Recuperar, era A e perdeu tração"
        p15 = (
            "Dia 1 a 3: checar ruptura e mudanças de preço/frete.\n"
            "Dia 4 a 7: ajustar competitividade e revisar reputação e prazo.\n"
            "Dia 8 a 15: reativar mídia com termos exatos, revisar desperdício."
        )
        p30 = (
            "Semana 1: ajustar título e atributos para relevância.\n"
            "Semana 2: ajustar variações e qualidade do anúncio.\n"
            "Semana 3 e 4: estabilizar investimento mantendo só o que dá venda."
        )
        return acao, p15, p30

    # 5) Subiu para A depois
    if is_rise:
        acao = "Crescimento, consolidar curva A"
        p15 = (
            "Dia 1 a 5: entender o gatilho de crescimento e repetir em itens parecidos.\n"
            "Dia 6 a 10: ampliar exposição em termos rentáveis, travar termos ruins.\n"
            "Dia 11 a 15: melhorar página para aguentar escala sem cair conversão."
        )
        p30 = (
            "Semana 1: estruturar campanha por intenção de busca.\n"
            "Semana 2: proteger ticket médio e margem.\n"
            "Semana 3 e 4: escalar com limite de custo e sem travar estoque."
        )
        return acao, p15, p30

    # 6) Revitalizar cirúrgico
    if is_revitalize:
        acao = "Revitalizar, queda de curva com faixa 30 a 40 ou queda forte"
        p15 = (
            "Dia 1 a 4: auditoria rápida do anúncio (preço, frete, estoque, título, fotos).\n"
            "Dia 5 a 10: campanha leve com termos específicos e controle de desperdício.\n"
            "Dia 11 a 15: ajustar lances só nos termos que geram venda."
        )
        p30 = (
            "Semana 1: reorganizar variações e ajustar proposta do anúncio.\n"
            "Semana 2: testar kit ou condição comercial que não destrua margem.\n"
            "Semana 3 e 4: se não reagir, reclassificar como cauda longa e reduzir prioridade."
        )
        return acao, p15, p30

    # 7) C recorrente (sem inativar automaticamente)
    if is_c_rec:
        acao = "C recorrente, manter como cauda longa"
        p15 = (
            "Dia 1 a 7: sem mídia constante, só manter anúncio correto.\n"
            "Dia 8 a 15: encaixar em kits e vendas cruzadas com produtos A/B."
        )
        p30 = (
            "Semana 1 e 2: se estoque parado, bundle para escoar.\n"
            "Semana 3 e 4: decidir manter por mix ou descontinuar."
        )
        return acao, p15, p30

    # padrão por curva atual
    if curva0 == "A":
        return (
            "Manter e otimizar",
            "Dia 1 a 7: cortar desperdício e melhorar conversão.\nDia 8 a 15: ajustar lances e termos.",
            "Semana 1: melhorias na página.\nSemana 2 a 4: escalar apenas se mantiver ticket e giro."
        )

    if curva0 in ["B", "C"]:
        return (
            "Otimizar e definir foco",
            "Dia 1 a 5: checar termos e competitividade.\nDia 6 a 15: decidir se vira crescimento ou mix.",
            "Semana 1: estratégia por margem e giro.\nSemana 2 a 4: executar e medir."
        )

    return (
        "Sem venda recente, avaliar continuidade",
        "Dia 1 a 7: confirmar anúncio ativo e estoque.\nDia 8 a 15: se não houver sinal, pausar.",
        "Semana 1: testar ajustes mínimos.\nSemana 2 a 4: se não reagir, inativar."
    )

# Tabela do plano
plan = df_f.copy()
acoes = plan.apply(action_bundle, axis=1, result_type="expand")
plan["Ação sugerida"] = acoes[0]
plan["Plano 15 dias"] = acoes[1]
plan["Plano 30 dias"] = acoes[2]

def status_bucket(row):
    idx = row.name
    if idx in anchors.index:
        return "Âncora"
    if idx in inactivate.index:
        return "Inativar"
    if idx in revitalize.index:
        return "Revitalizar"
    if idx in opp_50_60.index:
        return "Oportunidade 50 a 60"
    if idx in a_drop_61_90.index:
        return "Recuperar (A caiu)"
    if idx in rise_to_A.index:
        return "Crescimento (virou A)"
    if idx in c_rec.index:
        return "C recorrente"
    return "Manter/Otimizar"

plan["Status"] = plan.apply(status_bucket, axis=1)

# =========================
# KPIs topo
# =========================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de anúncios", br_int(total_ads))
c2.metric("Faturamento total (4 janelas)", br_money(df_f[[p[3] for p in periods]].sum().sum()))
c3.metric("Qtd total (4 janelas)", br_int(df_f[[p[2] for p in periods]].sum().sum()))
tt_fat = df_f[[p[3] for p in periods]].sum().sum()
tt_qty = df_f[[p[2] for p in periods]].sum().sum()
c4.metric("Ticket médio total", br_money(tt_fat / tt_qty if tt_qty > 0 else 0.0))

st.divider()

tab1, tab2, tab3 = st.tabs(["Dashboard", "Listas e Exportação", "Plano tático por produto"])

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
        st.subheader("Distribuição de curvas por período")
        dist_rows = []
        for p, cc, qq, ff in periods:
            vc = df_f[cc].value_counts()
            for curva in ["A","B","C","-"]:
                dist_rows.append({"Período": p, "Curva": curva, "Anúncios": int(vc.get(curva, 0))})
        dist_df = pd.DataFrame(dist_rows)
        fig = px.bar(dist_df, x="Período", y="Anúncios", color="Curva", barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Faturamento por curva e período")
    rev_rows = []
    for p, cc, qq, ff in periods:
        grp = df_f.groupby(cc)[ff].sum()
        for curva in ["A","B","C","-"]:
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
    sample_cols = ["MLB","Título","Curva 0-30","Qntd 0-30","Fat. 0-30","Status","Ação sugerida"]
    sample = plan.sort_values("Fat total", ascending=False)[sample_cols].head(40).copy()
    sample["Fat. 0-30"] = sample["Fat. 0-30"].map(br_money)
    st.dataframe(sample, use_container_width=True, hide_index=True)

# =========================
# TAB 2: Listas e Exportação
# =========================
with tab2:
    st.subheader("Exportação rápida em CSV")

    anchors_export = anchors.copy().sort_values("Fat total", ascending=False)
    anchors_export = anchors_export[["MLB","Título","Fat total","Qtd total","TM total","Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]].copy()

    inactivate_export = inactivate.copy().sort_values("Fat total", ascending=False)
    inactivate_export = inactivate_export[["MLB","Título","Fat total","Qtd total","Curva 0-30","Qntd 0-30","Qntd 31-60","Qntd 61-90"]].copy()

    revitalize_export = revitalize.copy().sort_values("Fat total", ascending=False)
    revitalize_export = revitalize_export[["MLB","Título","Fat total","Qtd total","Curva 31-60","Curva 0-30","Qntd 31-60","Qntd 0-30"]].copy()

    opp_export = opp_50_60.copy().sort_values("Fat total", ascending=False)
    opp_export = opp_export[["MLB","Título","Fat total","Curva 0-30","Qntd 0-30","Curva 31-60","Qntd 31-60"]].copy()

    cA, cB, cC, cD = st.columns(4)

    with cA:
        st.markdown(f"**Âncoras:** {len(anchors_export)}")
        st.download_button("Baixar CSV Âncoras", data=to_csv_bytes(anchors_export),
                           file_name="ancoras_curva_ABC.csv", mime="text/csv")

    with cB:
        st.markdown(f"**Inativar:** {len(inactivate_export)}")
        st.download_button("Baixar CSV Inativar", data=to_csv_bytes(inactivate_export),
                           file_name="inativar_curva_ABC.csv", mime="text/csv")

    with cC:
        st.markdown(f"**Revitalizar:** {len(revitalize_export)}")
        st.download_button("Baixar CSV Revitalizar", data=to_csv_bytes(revitalize_export),
                           file_name="revitalizar_curva_ABC.csv", mime="text/csv")

    with cD:
        st.markdown(f"**Oportunidade 50 a 60:** {len(opp_export)}")
        st.download_button("Baixar CSV Oportunidade 50 a 60", data=to_csv_bytes(opp_export),
                           file_name="oportunidade_50_60.csv", mime="text/csv")

    st.divider()

    st.subheader("Visualizar listas")
    with st.expander("Ver Âncoras"):
        show = anchors_export.copy()
        show["Fat total"] = show["Fat total"].map(br_money)
        show["TM total"] = show["TM total"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        show["Qtd total"] = show["Qtd total"].map(br_int)
        st.dataframe(show, use_container_width=True, hide_index=True)

    with st.expander("Ver Inativar"):
        show = inactivate_export.copy()
        show["Fat total"] = show["Fat total"].map(br_money)
        show["Qtd total"] = show["Qtd total"].map(br_int)
        st.dataframe(show, use_container_width=True, hide_index=True)

    with st.expander("Ver Revitalizar"):
        show = revitalize_export.copy()
        show["Fat total"] = show["Fat total"].map(br_money)
        show["Qtd total"] = show["Qtd total"].map(br_int)
        st.dataframe(show, use_container_width=True, hide_index=True)

    with st.expander("Ver Oportunidade 50 a 60"):
        show = opp_export.copy()
        show["Fat total"] = show["Fat total"].map(br_money)
        st.dataframe(show, use_container_width=True, hide_index=True)

# =========================
# TAB 3: Plano tático por produto
# =========================
with tab3:
    st.subheader("Plano tático 15 e 30 dias por produto")

    status_opts = sorted(plan["Status"].unique().tolist())
    status_filter = st.multiselect("Filtrar por Status", options=status_opts, default=status_opts)

    min_fat = st.number_input("Faturamento total mínimo", min_value=0.0, value=0.0, step=100.0)
    text_search = st.text_input("Buscar por MLB ou Título", value="").strip().lower()

    view = plan[plan["Status"].isin(status_filter)].copy()
    view = view[view["Fat total"] >= float(min_fat)].copy()

    if text_search:
        view = view[
            view["MLB"].astype(str).str.lower().str.contains(text_search) |
            view["Título"].astype(str).str.lower().str.contains(text_search)
        ].copy()

    plan_cols = [
        "MLB","Título","Status",
        "Curva 31-60","Curva 0-30",
        "Qntd 31-60","Qntd 0-30",
        "Fat. 0-30","Fat total","Qtd total","TM total",
        "Ação sugerida","Plano 15 dias","Plano 30 dias"
    ]
    view_show = view[plan_cols].sort_values("Fat total", ascending=False).copy()

    st.download_button(
        "Baixar CSV do plano filtrado",
        data=to_csv_bytes(view_show),
        file_name="plano_tatico_por_produto.csv",
        mime="text/csv"
    )

    show = view_show.copy()
    for col in ["Fat. 0-30","Fat total"]:
        show[col] = show[col].map(br_money)
    show["Qtd total"] = show["Qtd total"].map(br_int)
    show["Qntd 0-30"] = show["Qntd 0-30"].map(br_int)
    show["Qntd 31-60"] = show["Qntd 31-60"].map(br_int)
    show["TM total"] = show["TM total"].apply(lambda x: br_money(x) if pd.notna(x) else "-")

    st.dataframe(show, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Regras que estamos usando agora")
    st.markdown(
        "- **Inativar:** sem vendas 90 dias, ou sem vendas recentes + curva fraca + queda de curva, ou C recorrente sem vendas recentes.\n"
        "- **Revitalizar:** queda recente com faixa 30 a 40, ou tinha 30 a 40 e caiu para até 10, ou queda forte com volume 1 a 25.\n"
        "- **Oportunidade 50 a 60:** vendeu 50 a 60 em 0-30 ou 31-60.\n"
        "- **Âncoras:** A em todos os períodos."
    )
