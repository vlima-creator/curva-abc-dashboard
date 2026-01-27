"""
Componentes de UI específicos para a Shopee.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def render_shopee_conversion_funnel(df_export: pd.DataFrame):
    """
    Renderiza as métricas de conversão da Shopee: funil + origem do tráfego.
    
    Etapas: Visitantes → Add ao Carrinho → Pedidos → Pagos
    """
    st.markdown("### 📊 Métricas de Conversão")
    
    # Layout de 2 colunas
    col_funil, col_origem = st.columns(2)
    
    with col_funil:
        st.markdown("**Funil de Conversão**")
        # Agrega métricas
        total_visitantes = df_export['_shopee_visitantes'].sum()
        total_add_carrinho = df_export['_shopee_add_carrinho'].sum()
        total_pedidos = df_export['Qtd total'].sum()  # Pedidos realizados
        total_compradores = df_export['_shopee_compradores'].sum()  # Pedidos pagos
        
        # Prepara dados para o gráfico de pizza
        labels = ["Visitantes", "Add Carrinho", "Pedidos", "Pagos"]
        values = [total_visitantes, total_add_carrinho, total_pedidos, total_compradores]
        colors = ["#60a5fa", "#34d399", "#fbbf24", "#4ade80"]
        
        # Cria o gráfico de pizza
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker=dict(
                colors=colors,
                line=dict(color='rgba(255,255,255,0.3)', width=2)
            ),
            textfont=dict(size=14, color='white', family='Inter'),
            textposition='inside',
            textinfo='label+value+percent',
            hole=0.4  # Donut chart
        )])
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=20, b=20),
            font=dict(color='#9ca3af'),
            height=400,
            showlegend=True,
            legend=dict(
                font=dict(color='#ffffff'),
                bgcolor='rgba(0,0,0,0)'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_origem:
        st.markdown("**Origem do Tráfego**")
        # Verifica se há dados de PC/App
        if '_shopee_visitantes_pc' in df_export.columns and '_shopee_visitantes_app' in df_export.columns:
            visitantes_pc = df_export['_shopee_visitantes_pc'].iloc[0]
            visitantes_app = df_export['_shopee_visitantes_app'].iloc[0]
            
            # Cria gráfico de pizza para PC vs Aplicativo
            fig_origem = go.Figure(data=[go.Pie(
                labels=['Aplicativo', 'PC'],
                values=[visitantes_app, visitantes_pc],
                marker=dict(
                    colors=['#FF6B6B', '#4ECDC4'],
                    line=dict(color='rgba(255,255,255,0.3)', width=2)
                ),
                textfont=dict(size=14, color='white', family='Inter'),
                textposition='inside',
                textinfo='label+value+percent',
                hole=0.4  # Donut chart
            )])
            
            fig_origem.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=20, b=20),
                font=dict(color='#9ca3af'),
                height=400,
                showlegend=True,
                legend=dict(
                    font=dict(color='#ffffff'),
                    bgcolor='rgba(0,0,0,0)'
                )
            )
            
            st.plotly_chart(fig_origem, use_container_width=True)
        else:
            st.info("📊 Dados de origem do tráfego não disponíveis. Faça upload do arquivo traffic_overview para visualizar.")
    
    # Calcula taxas de conversão
    taxa_carrinho = (total_add_carrinho / total_visitantes * 100) if total_visitantes > 0 else 0
    taxa_pedido = (total_pedidos / total_visitantes * 100) if total_visitantes > 0 else 0
    taxa_pagamento = (total_compradores / total_pedidos * 100) if total_pedidos > 0 else 0
    
    # Exibe métricas de conversão
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Taxa Add Carrinho</div>
            <div class="metric-value">{taxa_carrinho:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Taxa Pedido</div>
            <div class="metric-value">{taxa_pedido:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Taxa Pagamento</div>
            <div class="metric-value">{taxa_pagamento:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)


def render_shopee_engagement_metrics(df_export: pd.DataFrame):
    """
    Renderiza métricas de engajamento da Shopee.
    """
    # Calcula médias ponderadas
    total_visitantes = df_export['_shopee_visitantes'].sum()
    total_visualizacoes = df_export['_shopee_visualizacoes'].sum()
    
    # Taxa de rejeição média ponderada
    if total_visitantes > 0:
        taxa_rejeicao_media = (df_export['_shopee_taxa_rejeicao'] * df_export['_shopee_visitantes']).sum() / total_visitantes
        taxa_conversao_media = (df_export['_shopee_taxa_conversao'] * df_export['_shopee_visitantes']).sum() / total_visitantes
        viz_por_visitante = total_visualizacoes / total_visitantes
    else:
        taxa_rejeicao_media = 0
        taxa_conversao_media = 0
        viz_por_visitante = 0
    
    st.markdown("""
    <div class="section-box">
        <div class="section-header">
            <div class="section-icon">📊</div>
            <div>
                <div class="section-title">Métricas de Engajamento</div>
                <div class="section-desc">Indicadores de comportamento dos visitantes</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Taxa de Rejeição</div>
            <div class="metric-value">{taxa_rejeicao_media*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Visualizações/Visitante</div>
            <div class="metric-value">{viz_por_visitante:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Taxa de Conversão</div>
            <div class="metric-value">{taxa_conversao_media*100:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total de Visitantes</div>
            <div class="metric-value">{int(total_visitantes):,}</div>
        </div>
        """, unsafe_allow_html=True)


def render_shopee_top_rejection_rate(df_export: pd.DataFrame):
    """
    Renderiza os Top 5 produtos com maior taxa de rejeição
    """
    st.markdown("""
    <div class="section-box">
        <div class="section-header">
            <div class="section-icon">⚠️</div>
            <div>
                <div class="section-title">Top 5 Produtos com Maior Taxa de Rejeição</div>
                <div class="section-desc">Produtos que precisam de atenção imediata para melhorar conversão</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Filtrar produtos com dados válidos
    df_valid = df_export[
        (df_export['_shopee_taxa_rejeicao'].notna()) & 
        (df_export['_shopee_taxa_rejeicao'] > 0) &
        (df_export['_shopee_visitantes'] > 0)
    ].copy()
    
    if df_valid.empty:
        st.info("⚠️ Não há dados de taxa de rejeição disponíveis.")
        return
    
    # Ordenar por taxa de rejeição (maior para menor) e pegar top 5
    top_rejection = df_valid.nlargest(5, '_shopee_taxa_rejeicao')[[
        'Título', '_shopee_taxa_rejeicao', '_shopee_visitantes', 
        '_shopee_taxa_conversao', 'Fat total'
    ]].copy()
    
    # Renomear colunas para exibição
    top_rejection.columns = ['Produto', 'Taxa Rejeição', 'Visitantes', 'Taxa Conversão', 'Faturamento']
    
    # Formatar valores
    top_rejection['Taxa Rejeição'] = top_rejection['Taxa Rejeição'].apply(lambda x: f"{x*100:.1f}%")
    top_rejection['Taxa Conversão'] = top_rejection['Taxa Conversão'].apply(lambda x: f"{x*100:.2f}%")
    top_rejection['Faturamento'] = top_rejection['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
    top_rejection['Visitantes'] = top_rejection['Visitantes'].apply(lambda x: f"{int(x):,}")
    
    # Resetar índice e adicionar ranking
    top_rejection = top_rejection.reset_index(drop=True)
    top_rejection.index = top_rejection.index + 1
    top_rejection.index.name = '#'
    
    # Exibir tabela estilizada
    st.dataframe(
        top_rejection,
        use_container_width=True,
        height=250
    )
    
    # Adicionar dica de ação
    st.markdown("""
    <div style="
        background: #fff8e1;
        border: 1px solid #ffd54f;
        border-radius: 8px;
        padding: 16px;
        margin-top: 16px;
        display: flex;
        gap: 12px;
        align-items: flex-start;
    ">
        <div style="
            background: #ffd54f;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 20px;
        ">
            💡
        </div>
        <div style="flex: 1;">
            <div style="
                font-weight: 600;
                font-size: 16px;
                color: #1a1a1a;
                margin-bottom: 8px;
            ">
                Ação Recomendada
            </div>
            <div style="
                font-size: 14px;
                color: #333333;
                line-height: 1.6;
            ">
                Produtos com alta taxa de rejeição precisam de otimização urgente:
                <ul style="margin: 8px 0 0 20px; padding-left: 0;">
                    <li style="margin-bottom: 4px;">Melhorar qualidade das fotos (zoom, fundo limpo, uso real)</li>
                    <li style="margin-bottom: 4px;">Revisar título e descrição (clareza, benefícios, FAQ)</li>
                    <li style="margin-bottom: 4px;">Ajustar preço ou destacar diferenciais</li>
                    <li style="margin-bottom: 4px;">Verificar avaliações negativas e responder</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_shopee_top_products(df_export: pd.DataFrame, top_n: int = 10):
    """
    Renderiza tabela de top produtos da Shopee.
    """
    st.markdown("""
    <div class="section-box">
        <div class="section-header">
            <div class="section-icon">🏆</div>
            <div>
                <div class="section-title">Top Produtos por Faturamento</div>
                <div class="section-desc">Produtos com melhor performance no período</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Ordena por faturamento
    df_top = df_export.nlargest(top_n, 'Fat total').copy()
    
    # Formata valores
    df_display = pd.DataFrame({
        'SKU': df_top['MLB'],
        'Produto': df_top['Título'].str[:50] + '...',
        'Faturamento': df_top['Fat total'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
        'Unidades': df_top['Qtd total'].apply(lambda x: f"{int(x):,}".replace(",", ".")),
        'Ticket Médio': df_top['TM total'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
        'Curva': df_top['Curva 0-30'],
        'Taxa Conversão': df_top['_shopee_taxa_conversao'].apply(lambda x: f"{x*100:.2f}%"),
        'Visitantes': df_top['_shopee_visitantes'].apply(lambda x: f"{int(x):,}".replace(",", "."))
    })
    
    st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)


def render_shopee_abc_distribution(df_export: pd.DataFrame):
    """
    Renderiza distribuição da curva ABC para Shopee.
    """
    st.markdown("""
    <div class="section-box">
        <div class="section-header">
            <div class="section-icon">📈</div>
            <div>
                <div class="section-title">Distribuição por Curva ABC</div>
                <div class="section-desc">Classificação dos produtos por faturamento</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Conta produtos por curva
    curva_counts = df_export['Curva 0-30'].value_counts()
    curva_revenue = df_export.groupby('Curva 0-30')['Fat total'].sum()
    
    # Cria DataFrame para visualização
    curva_data = pd.DataFrame({
        'Curva': curva_counts.index,
        'Produtos': curva_counts.values,
        'Faturamento': [curva_revenue.get(c, 0) for c in curva_counts.index]
    })
    
    # Ordena: A, B, C, -
    order = {'A': 0, 'B': 1, 'C': 2, '-': 3}
    curva_data['_order'] = curva_data['Curva'].map(order)
    curva_data = curva_data.sort_values('_order').drop(columns=['_order'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de produtos por curva
        fig1 = px.bar(
            curva_data,
            x='Curva',
            y='Produtos',
            color='Curva',
            color_discrete_map={'A': '#4ade80', 'B': '#fbbf24', 'C': '#f87171', '-': '#6b7280'},
            text='Produtos'
        )
        fig1.update_traces(textposition='outside')
        fig1.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(color='#9ca3af'),
            showlegend=False,
            title=dict(text="Quantidade de Produtos", font=dict(size=14, color='#ffffff'))
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Gráfico de faturamento por curva
        fig2 = px.bar(
            curva_data,
            x='Curva',
            y='Faturamento',
            color='Curva',
            color_discrete_map={'A': '#4ade80', 'B': '#fbbf24', 'C': '#f87171', '-': '#6b7280'}
        )
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(color='#9ca3af'),
            showlegend=False,
            title=dict(text="Faturamento por Curva", font=dict(size=14, color='#ffffff'))
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Exibe métricas resumidas
    col1, col2, col3, col4 = st.columns(4)
    
    for col, curva in zip([col1, col2, col3, col4], ['A', 'B', 'C', '-']):
        with col:
            qtd = curva_counts.get(curva, 0)
            fat = curva_revenue.get(curva, 0)
            pct_fat = (fat / df_export['Fat total'].sum() * 100) if df_export['Fat total'].sum() > 0 else 0
            
            st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-label">Curva {curva}</div>
                <div class="kpi-value">{int(qtd)} produtos</div>
                <div class="kpi-label">{pct_fat:.1f}% do faturamento</div>
            </div>
            """, unsafe_allow_html=True)
