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

    # padroniza tipos
    for col in ["Qntd 0-30","Qntd 31-60","Qntd 61-90","Qntd 91-120"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in ["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]:
        df[col] = df[col].fillna("-").astype(str).str.strip()

    # garantias básicas
    for col in ["MLB", "Título"]:
        if col not in df.columns:
            df[col] = ""

    return df

def br_money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_int(x: float) -> str:
    return f"{int(x):,}".replace(",", ".")

def to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    # CSV com separador ; (bom para Excel BR)
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

# Métricas agregadas úteis
df_f["Qtd total"] = df_f[["Qntd 0-30","Qntd 31-60","Qntd 61-90","Qntd 91-120"]].sum(axis=1)
df_f["Fat total"] = df_f[["Fat. 0-30","Fat. 31-60","Fat. 61-90","Fat. 91-120"]].sum(axis=1)
df_f["TM total"] = np.where(df_f["Qtd total"] > 0, df_f["Fat total"] / df_f["Qtd total"], np.nan)

total_ads = len(df_f)

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

# =========================
# Definições de listas: âncoras, inativar, revitalizar e outros grupos
# =========================

# Âncoras: A em todos os períodos
anchors = df_f[
    (df_f["Curva 0-30"]=="A") &
    (df_f["Curva 31-60"]=="A") &
    (df_f["Curva 61-90"]=="A") &
    (df_f["Curva 91-120"]=="A")
].copy()

# A no 0-30 que caiu no 61-90 (virou B/C/-)
a_drop_61_90 = df_f[(df_f["Curva 0-30"]=="A") & (df_f["Curva 61-90"]!="A")].copy()

# Subiu para A depois
rise_to_A = df_f[
    df_f["Curva 0-30"].isin(["B","C","-"]) &
    ((df_f["Curva 31-60"]=="A") | (df_f["Curva 61-90"]=="A") | (df_f["Curva 91-120"]=="A"))
].copy()

# C recorrente: 3 ou 4 períodos em C
tmp = df_f.copy()
tmp["c_count"] = (tmp[["Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]]=="C").sum(axis=1)
c_rec = tmp[tmp["c_count"]>=3].copy()

# Sem vendas 90 dias (proxy): 0-30, 31-60, 61-90 = 0
no_sales_90 = df_f[
    (df_f["Qntd 0-30"]==0) &
    (df_f["Qntd 31-60"]==0) &
    (df_f["Qntd 61-90"]==0)
].copy()

# Sem vendas 60 dias (proxy): 0-30 e 31-60 = 0
no_sales_60 = df_f[
    (df_f["Qntd 0-30"]==0) &
    (df_f["Qntd 31-60"]==0)
].copy()

# Queda de curva recente (mais forte antes, pior agora)
df_f["rank_0_30"] = df_f["Curva 0-30"].map(rank).fillna(0).astype(int)
df_f["rank_31_60"] = df_f["Curva 31-60"].map(rank).fillna(0).astype(int)
df_f["rank_61_90"] = df_f["Curva 61-90"].map(rank).fillna(0).astype(int)
df_f["rank_91_120"] = df_f["Curva 91-120"].map(rank).fillna(0).astype(int)

df_f["queda_recente"] = df_f["rank_0_30"] < df_f["rank_31_60"]

# Revitalizar (heurística prática):
# - teve queda recente de curva e teve alguma tração no passado
# - e está com volume baixo agora (entre 1 e 40) OU está zerado agora, mas tinha 30-40 no 31-60
revitalize = df_f[
    (
        (df_f["queda_recente"]) &
        (
            ((df_f["Qntd 0-30"] >= 1) & (df_f["Qntd 0-30"] <= 40)) |
            ((df_f["Qntd 0-30"] == 0) & (df_f["Qntd 31-60"] >= 30) & (df_f["Qntd 31-60"] <= 40))
        )
    )
].copy()

# Inativar (regras objetivas):
# - sem vendas 90 dias, ou
# - sem vendas 60 dias e curva 0-30 é "-" ou "C"
inactivate = df_f[
    (df_f.index.isin(no_sales_90.index)) |
    ((df_f.index.isin(no_sales_60.index)) & (df_f["Curva 0-30"].isin(["-","C"])))
].copy()

# =========================
# Regras de ação sugerida + plano tático 15 e 30 dias
# =========================

def action_bundle(row) -> tuple[str, str, str]:
    """
    Retorna:
    - ação sugerida
    - plano 15 dias
    - plano 30 dias
    """

    curva0 = row["Curva 0-30"]
    q0 = row["Qntd 0-30"]
    f0 = row["Fat. 0-30"]
    queda = bool(row.get("queda_recente", False))

    is_anchor = (
        row["Curva 0-30"]=="A" and row["Curva 31-60"]=="A" and
        row["Curva 61-90"]=="A" and row["Curva 91-120"]=="A"
    )

    # flags (usando índices calculados)
    idx = row.name
    is_inactivate = idx in inactivate.index
    is_revitalize = idx in revitalize.index
    is_rise = idx in rise_to_A.index
    is_a_drop = idx in a_drop_61_90.index
    is_c_rec = idx in c_rec.index

    # 1) Inativar
    if is_inactivate:
        acao = "Inativar ou pausar"
        p15 = (
            "Dia 1 a 3: checar se existe estoque e se o anúncio está ativo.\n"
            "Dia 4 a 7: se for item estratégico, testar reposicionamento de preço e frete.\n"
            "Dia 8 a 15: se continuar sem venda, pausar e concentrar energia nos itens com giro."
        )
        p30 = (
            "Semana 1: decisão final de manter no catálogo ou remover.\n"
            "Semana 2: se mantiver, reformular página do anúncio e testar kit ou variação.\n"
            "Semana 3 e 4: reativar só com meta de venda mínima, senão inativar definitivo."
        )
        return acao, p15, p30

    # 2) Âncora
    if is_anchor:
        acao = "Escalar com controle e defender posição"
        p15 = (
            "Dia 1 a 3: validar estoque, ruptura e prazo de envio.\n"
            "Dia 4 a 7: revisar título, fotos e variações para aumentar conversão.\n"
            "Dia 8 a 15: aumentar verba em passos pequenos e cortar termos ruins."
        )
        p30 = (
            "Semana 1: teste de preço em faixa estreita e monitorar conversão.\n"
            "Semana 2: segmentar campanhas por termos principais e termos long tail.\n"
            "Semana 3 e 4: manter escala gradual, controlar custo por venda e evitar canibalização."
        )
        return acao, p15, p30

    # 3) Subiu para A depois
    if is_rise:
        acao = "Acelerar crescimento e consolidar curva A"
        p15 = (
            "Dia 1 a 5: identificar o que mudou (preço, estoque, frete, campanha) e replicar.\n"
            "Dia 6 a 10: ampliar exposição em termos rentáveis, manter negativo do que não vende.\n"
            "Dia 11 a 15: reforçar página do anúncio para segurar conversão com mais tráfego."
        )
        p30 = (
            "Semana 1: estruturar campanha separando termos fortes e termos de descoberta.\n"
            "Semana 2: otimizar para margem, evitar descontos que derrubam ticket.\n"
            "Semana 3 e 4: escalar orçamento se curva A se mantiver e o giro não travar por estoque."
        )
        return acao, p15, p30

    # 4) A que caiu no 61-90
    if is_a_drop:
        acao = "Plano de recuperação para voltar à A"
        p15 = (
            "Dia 1 a 3: checar ruptura e concorrência direta.\n"
            "Dia 4 a 7: ajustar preço e frete para faixa competitiva.\n"
            "Dia 8 a 15: reativar mídia com foco em termos exatos e revisar posicionamentos."
        )
        p30 = (
            "Semana 1: reescrever título e ajustar atributos para melhorar relevância.\n"
            "Semana 2: testar criativo e variações, revisar perguntas e reputação.\n"
            "Semana 3 e 4: estabilizar investimento, manter só termos que dão venda."
        )
        return acao, p15, p30

    # 5) Revitalizar por queda recente e volume baixo
    if is_revitalize or queda:
        acao = "Revitalizar e recuperar tração"
        p15 = (
            "Dia 1 a 4: auditoria rápida de anúncio (título, fotos, preço, frete, estoque).\n"
            "Dia 5 a 10: ativar campanha leve com termos específicos e controlar desperdício.\n"
            "Dia 11 a 15: se houver venda, aumentar lance apenas nos termos vencedores."
        )
        p30 = (
            "Semana 1: reorganizar variações e destacar benefício principal.\n"
            "Semana 2: testar kit, brinde ou condição comercial que não destrua margem.\n"
            "Semana 3 e 4: se não reagir, reclassificar para cauda longa e reduzir prioridade."
        )
        return acao, p15, p30

    # 6) C recorrente
    if is_c_rec:
        acao = "Cauda longa, manter com baixa prioridade"
        p15 = (
            "Dia 1 a 7: manter anúncio correto e sem investir em mídia constante.\n"
            "Dia 8 a 15: avaliar se cabe em kits e vendas cruzadas com produtos A/B."
        )
        p30 = (
            "Semana 1 e 2: se tiver estoque parado, criar ações para escoar com bundle.\n"
            "Semana 3 e 4: revisar portfólio, decidir manter por mix ou descontinuar."
        )
        return acao, p15, p30

    # 7) Padrão
    if curva0 == "A":
        acao = "Manter e otimizar"
        p15 = (
            "Dia 1 a 7: reduzir desperdício na mídia e melhorar conversão.\n"
            "Dia 8 a 15: ajustar lances e termos, manter consistência."
        )
        p30 = (
            "Semana 1: testar pequenas melhorias na página.\n"
            "Semana 2 a 4: escalar apenas se vender mais sem derrubar ticket."
        )
        return acao, p15, p30

    if curva0 in ["B", "C"]:
        acao = "Otimizar e escolher foco"
        p15 = (
            "Dia 1 a 5: checar competitividade e termos que realmente vendem.\n"
            "Dia 6 a 15: definir se vira projeto de crescimento ou só item de mix."
        )
        p30 = (
            "Semana 1: estratégia definida por margem e giro.\n"
            "Semana 2 a 4: se for crescimento, aumentar exposição, se não, reduzir esforço."
        )
        return acao, p15, p30

    # curva "-"
    acao = "Sem venda recente, avaliar continuidade"
    p15 = (
        "Dia 1 a 7: confirmar anúncio ativo, estoque e preço.\n"
        "Dia 8 a 15: se não houver sinal, pausar."
    )
    p30 = (
        "Semana 1: testar ajustes mínimos.\n"
        "Semana 2 a 4: se não reagir, inativar e realocar foco."
    )
    return acao, p15, p30


# Gera tabela de plano tático por produto (para dashboard e export)
plan = df_f.copy()
acoes = plan.apply(action_bundle, axis=1, result_type="expand")
plan["Ação sugerida"] = acoes[0]
plan["Plano 15 dias"] = acoes[1]
plan["Plano 30 dias"] = acoes[2]

# Um resumo de status (ajuda na filtragem)
def status_bucket(row):
    idx = row.name
    if idx in anchors.index:
        return "Âncora"
    if idx in inactivate.index:
        return "Inativar"
    if idx in revitalize.index:
        return "Revitalizar"
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

# =========================
# Abas principais
# =========================
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

    st.subheader("Perda acumulada: itens que eram A e deixaram de ser A")
    def cohort_loss(prev_curve_col, prev_fat_col, next_curve_col, next_fat_col, curve="A"):
        cohort = df_f[df_f[prev_curve_col] == curve]
        left = cohort[cohort[next_curve_col] != curve]
        stayed = cohort[cohort[next_curve_col] == curve]
        return {
            "cohort_n": len(cohort),
            "left_n": len(left),
            "stayed_n": len(stayed),
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

    st.subheader("Amostra com ação sugerida")
    sample_cols = ["MLB","Título","Curva 0-30","Qntd 0-30","Fat. 0-30","Status","Ação sugerida"]
    sample = plan.sort_values("Fat total", ascending=False)[sample_cols].head(30).copy()
    sample["Fat. 0-30"] = sample["Fat. 0-30"].map(br_money)
    st.dataframe(sample, use_container_width=True, hide_index=True)

# =========================
# TAB 2: Listas e Exportação
# =========================
with tab2:
    st.subheader("Exportação rápida de listas em CSV")

    # prepara dataframes de export
    anchors_export = anchors.copy().sort_values("Fat total", ascending=False)
    anchors_export = anchors_export[["MLB","Título","Fat total","Qtd total","TM total","Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"]].copy()

    inactivate_export = inactivate.copy().sort_values("Fat total", ascending=False)
    inactivate_export = inactivate_export[["MLB","Título","Fat total","Qtd total","Curva 0-30","Qntd 0-30","Qntd 31-60","Qntd 61-90"]].copy()

    revitalize_export = revitalize.copy().sort_values("Fat total", ascending=False)
    revitalize_export = revitalize_export[["MLB","Título","Fat total","Qtd total","Curva 0-30","Curva 31-60","Qntd 0-30","Qntd 31-60"]].copy()

    cA, cB, cC = st.columns(3)

    with cA:
        st.markdown(f"**Âncoras:** {len(anchors_export)} produtos")
        st.download_button(
            label="Baixar CSV Âncoras",
            data=to_csv_bytes(anchors_export),
            file_name="ancoras_curva_ABC.csv",
            mime="text/csv"
        )

    with cB:
        st.markdown(f"**Inativar:** {len(inactivate_export)} produtos")
        st.download_button(
            label="Baixar CSV Inativar",
            data=to_csv_bytes(inactivate_export),
            file_name="inativar_curva_ABC.csv",
            mime="text/csv"
        )

    with cC:
        st.markdown(f"**Revitalizar:** {len(revitalize_export)} produtos")
        st.download_button(
            label="Baixar CSV Revitalizar",
            data=to_csv_bytes(revitalize_export),
            file_name="revitalizar_curva_ABC.csv",
            mime="text/csv"
        )

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

    # colunas do plano
    plan_cols = [
        "MLB","Título","Status",
        "Curva 0-30","Qntd 0-30","Fat. 0-30",
        "Fat total","Qtd total","TM total",
        "Ação sugerida","Plano 15 dias","Plano 30 dias"
    ]
    view_show = view[plan_cols].sort_values("Fat total", ascending=False).copy()

    # botão export do plano filtrado
    st.download_button(
        label="Baixar CSV do plano filtrado",
        data=to_csv_bytes(view_show),
        file_name="plano_tatico_por_produto.csv",
        mime="text/csv"
    )

    # formatar para exibição
    show = view_show.copy()
    for col in ["Fat. 0-30","Fat total"]:
        show[col] = show[col].map(br_money)
    show["Qtd total"] = show["Qtd total"].map(br_int)
    show["Qntd 0-30"] = show["Qntd 0-30"].map(br_int)
    show["TM total"] = show["TM total"].apply(lambda x: br_money(x) if pd.notna(x) else "-")

    st.dataframe(show, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Guia rápido do que fazer primeiro")
    st.markdown(
        "- **Inativar:** cortar itens sem sinal de venda recente para liberar foco e caixa.\n"
        "- **Revitalizar:** itens com queda recente e volume baixo, bons para ajustes e teste rápido.\n"
        "- **Âncoras:** escalar com controle, sem estourar custo e sem ruptura.\n"
        "- **Recuperar (A caiu):** atacar causa raiz, normalmente ruptura, concorrência, preço ou exposição.\n"
        "- **Crescimento (virou A):** consolidar, separar campanhas e evitar derrubar ticket."
    )
