import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Imports dos novos módulos multi-canal
from data_processing.factory import detect_and_process
from ui.components.shopee_components import (
    render_shopee_conversion_funnel,
    render_shopee_engagement_metrics,
    render_shopee_top_products,
    render_shopee_abc_distribution
)
from ui.components.helpers import to_xlsx_bytes, br_money, br_int, safe_div, pct, ensure_cols

st.set_page_config(page_title="Curva ABC, Diagnóstico e Ações", layout="wide")

# Forçar fundo preto absoluto via injeção direta
st.markdown(
    """
    <script>
        // Forçar fundo preto no carregamento e em mudanças
        const forceBlack = () => {
            document.body.style.backgroundColor = "#000000";
            const stApp = document.querySelector(".stApp");
            if (stApp) stApp.style.backgroundColor = "#000000";
        };
        forceBlack();
        setInterval(forceBlack, 1000);
    </script>
    <style>
        /* Forçar fundo preto absoluto */
        .stApp, .main, .block-container, body {
            background-color: #000000 !important;
        }
        /* Esconder elementos que podem ter cores residuais */
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# Estilo premium aprimorado v3.1
# =========================
st.markdown(
    """
<style>
/* ===== RESET E BASE ===== */
* { 
    font-variant-numeric: tabular-nums; 
    font-family: 'Inter', sans-serif;
}
.stApp, .main, .block-container, body {
    background-color: #000000 !important;
    color: #ffffff !important;
}
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1600px;}

/* Header transparente */
header[data-testid="stHeader"] {background: rgba(0,0,0,0);}

/* Esconde linhas separadoras */
hr {display: none !important;}

/* ===== SIDEBAR PREMIUM ===== */
section[data-testid="stSidebar"] {
  background: #000000 !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.15);
}
section[data-testid="stSidebar"] .block-container {padding-top: 1rem;}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
  letter-spacing: -0.3px;
  color: #e2e8f0;
}

/* ===== HEADER PRINCIPAL ===== */
.hero-header {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 24px 28px;
  margin: 0 0 1.5rem 0;
  position: relative;
  overflow: hidden;
}
.hero-title {
  font-size: 2rem;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #fff, #c4b5fd);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-subtitle {
  margin-top: 0.5rem;
  font-weight: 700;
  opacity: 1;
  font-size: 1rem;
  color: #ffffff;
}

/* ===== CARDS DE MÉTRICAS ===== */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 1.5rem;
}
@media (max-width: 1200px) {
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
}
.metric-card {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.metric-card:hover {
  background: rgba(82, 121, 111, 0.15);
  border-color: rgba(82, 121, 111, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(82, 121, 111, 0.2);
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  margin-bottom: 12px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: #ffffff !important;
}
.metric-icon svg {
  color: #ffffff !important;
  stroke: #ffffff !important;
  width: 28px;
  height: 28px;
}

.metric-label {
  font-size: 0.85rem;
  font-weight: 700;
  opacity: 1;
  margin: 0 0 4px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #ffffff;
}
.metric-value {
  font-size: 1.75rem;
  font-weight: 900;
  margin: 0;
  letter-spacing: -0.5px;
  color: #ffffff !important;
}
.metric-value { color: #ffffff !important; }

/* ===== PERIOD SELECTOR ===== */
.period-selector {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 16px;
}
.period-label {
  font-size: 0.9rem;
  font-weight: 800;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== LOGISTICA CARD ===== */
.logistics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 1rem 0;
}
@media (max-width: 900px) {
  .logistics-grid { grid-template-columns: 1fr; }
}
.logistics-card {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.logistics-card:hover {
  background: rgba(82, 121, 111, 0.15);
  border-color: rgba(82, 121, 111, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(82, 121, 111, 0.2);
}

.logistics-icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
  color: #ffffff !important;
}
.logistics-icon svg {
  color: #ffffff !important;
  stroke: #ffffff !important;
  width: 24px;
  height: 24px;
}
.logistics-title {
  font-size: 0.85rem;
  font-weight: 700;
  opacity: 1;
  margin-bottom: 4px;
  text-transform: uppercase;
  color: #ffffff;
}
.logistics-value {
  font-size: 1.5rem;
  font-weight: 800;
}
.logistics-value.full { color: #4ade80; }
.logistics-value.correios { color: #60a5fa; }
.logistics-value.flex { color: #fbbf24; }
.logistics-value.outros { color: #9ca3af; }

.logistics-bar {
  height: 8px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  margin-top: 12px;
  overflow: hidden;
}
.logistics-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}
.logistics-bar-fill.full { background: linear-gradient(90deg, #22c55e, #4ade80); }
.logistics-bar-fill.correios { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.logistics-bar-fill.flex { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.logistics-bar-fill.outros { background: linear-gradient(90deg, #6b7280, #9ca3af); }

/* ===== ADS CARD ===== */
.ads-container {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  margin: 1rem 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.ads-container:hover {
  border-color: rgba(82, 121, 111, 0.6);
  box-shadow: 0 4px 16px rgba(82, 121, 111, 0.15);
}
.ads-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.ads-icon {
  font-size: 1.2rem;
  color: #ffffff !important;
}
.ads-icon svg {
  color: #ffffff !important;
  stroke: #ffffff !important;
  width: 24px;
  height: 24px;
}
.ads-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}
.ads-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}
.ads-metric {
  text-align: center;
  padding: 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 12px;
}
.ads-metric.ads { border-left: 4px solid #f97316; }
.ads-metric.organic { border-left: 4px solid #22c55e; }
.ads-metric-value {
  font-size: 2rem;
  font-weight: 800;
}
.ads-metric-value.ads { color: #fb923c; }
.ads-metric-value.organic { color: #4ade80; }
.ads-metric-label {
  font-size: 0.85rem;
  opacity: 0.7;
  margin-top: 4px;
}
.ads-bar-container {
  margin-top: 16px;
}
.ads-bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  opacity: 0.7;
  margin-bottom: 6px;
}
.ads-bar {
  height: 12px;
  background: rgba(255,255,255,0.1);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
}
.ads-bar-ads {
  height: 100%;
  background: linear-gradient(90deg, #f97316, #fb923c);
  transition: width 0.5s ease;
}
.ads-bar-organic {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #4ade80);
  transition: width 0.5s ease;
}

/* ===== EXPORT CARDS ===== */
.export-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin: 1rem 0;
}
@media (max-width: 1000px) {
  .export-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
  .export-grid { grid-template-columns: 1fr; }
}
.export-card {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.export-card:hover {
  background: rgba(82, 121, 111, 0.15);
  border-color: rgba(82, 121, 111, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(82, 121, 111, 0.2);
}

.export-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.export-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  background: rgba(255, 255, 255, 0.05);
  color: #a0a0a0;
}
.export-icon.defense { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.export-icon.correction { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.export-icon.attack { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.export-icon.cleanup { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.export-icon.opportunity { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.export-icon.combo { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }

.export-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}
.export-desc {
  font-size: 0.85rem;
  opacity: 0.6;
}
.export-stats {
  display: flex;
  gap: 20px;
}
.export-stat {
  flex: 1;
}
.export-stat-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: #ffffff;
}
.export-stat-label {
  font-size: 0.75rem;
  opacity: 0.6;
  text-transform: uppercase;
}

/* ===== TACTICAL CARD ===== */
.tactical-card {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.tactical-card:hover {
  background: rgba(82, 121, 111, 0.15);
  border-color: rgba(82, 121, 111, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(82, 121, 111, 0.2);
}

.tactical-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.tactical-title {
  font-size: 1rem;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
}
.tactical-mlb {
  font-size: 0.8rem;
  opacity: 0.6;
  font-family: monospace;
}
.tactical-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}
.tactical-badge.defense { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
.tactical-badge.correction { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
.tactical-badge.attack { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.tactical-badge.cleanup { background: rgba(244, 63, 94, 0.2); color: #fb7185; }
.tactical-badge.optimization { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }

.tactical-metrics {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tactical-metric {
  min-width: 80px;
}
.tactical-metric-value {
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}
.tactical-metric-label {
  font-size: 0.7rem;
  opacity: 0.6;
  text-transform: uppercase;
}
.tactical-action {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.9rem;
  color: #ffffff;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tactical-action svg {
  width: 18px;
  height: 18px;
  color: #ffffff !important;
  stroke: #ffffff !important;
}

/* ===== FRONT CARDS ===== */
.front-card {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.front-card:hover {
  background: rgba(82, 121, 111, 0.15);
  border-color: rgba(82, 121, 111, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(82, 121, 111, 0.2);
}

.front-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.front-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff !important;
}
.front-icon svg {
  width: 24px;
  height: 24px;
  color: #ffffff !important;
  stroke: #ffffff !important;
}

.front-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}
.front-desc {
  font-size: 0.85rem;
  opacity: 0.6;
}
.front-stats {
  display: flex;
  gap: 20px;
}
.front-stat {
  flex: 1;
  text-align: center;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 10px;
}
.front-stat-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: #ffffff;
}
.front-stat-label {
  font-size: 0.7rem;
  opacity: 0.6;
  text-transform: uppercase;
}

/* ===== REPORT SECTIONS ===== */
.report-section {
  background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  padding: 24px;
  margin-bottom: 24px;
}
.report-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.report-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  background: rgba(255, 255, 255, 0.05);
  color: #a0a0a0;
}
.report-icon.purple { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.report-icon.blue { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.report-icon.green { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.report-icon.amber { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.report-icon.rose { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }
.report-icon.cyan { background: rgba(255, 255, 255, 0.05); color: #a0a0a0; }

.report-title {
  font-size: 1.4rem;
  font-weight: 900;
  color: #ffffff;
  margin: 0;
  text-transform: uppercase;
}
.report-desc {
  font-size: 0.9rem;
  opacity: 0.6;
  margin-top: 2px;
}

/* ===== KPI HIGHLIGHT ===== */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 16px 0;
}
@media (max-width: 800px) {
  .kpi-grid { grid-template-columns: 1fr; }
}
.kpi-box {
  background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 20px;
  text-align: center;
}
.kpi-box.purple { border-top: 3px solid #8b5cf6; }
.kpi-box.blue { border-top: 3px solid #3b82f6; }
.kpi-box.green { border-top: 3px solid #22c55e; }
.kpi-box.amber { border-top: 3px solid #f59e0b; }
.kpi-box.rose { border-top: 3px solid #f43f5e; }

.kpi-value {
  font-size: 2rem;
  font-weight: 800;
  margin-bottom: 4px;
}
.kpi-value.purple { color: #ffffff; }
.kpi-value.blue { color: #ffffff; }
.kpi-value.green { color: #ffffff; }
.kpi-value.amber { color: #ffffff; }
.kpi-value.rose { color: #ffffff; }

.kpi-label {
  font-size: 0.85rem;
  font-weight: 800;
  opacity: 1;
  color: #ffffff;
  text-transform: uppercase;
}

/* ===== INSIGHT CARD ===== */
.insight-card {
  background: linear-gradient(145deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05));
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 14px;
  padding: 18px 20px;
  margin: 16px 0;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.insight-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
  color: #a0a0a0;
}
.insight-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #c4b5fd;
  margin-bottom: 4px;
}
.insight-text {
  font-size: 0.9rem;
  opacity: 0.85;
  line-height: 1.5;
}

/* ===== FRONT SUMMARY ===== */
.front-summary {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin: 16px 0;
}
.front-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 30px;
  font-size: 0.9rem;
}
.front-pill-icon {
  font-size: 1rem;
  color: #a0a0a0;
}
.front-pill-count {
  font-weight: 900;
  color: #ffffff;
}
.front-pill-label {
  font-weight: 800;
  opacity: 1;
  color: #ffffff;
  text-transform: uppercase;
}

/* ===== SECTION HEADER ===== */
.section-box {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.section-box:hover {
  border-color: rgba(82, 121, 111, 0.6);
  box-shadow: 0 4px 16px rgba(82, 121, 111, 0.15);
}
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.section-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff !important;
}
.section-icon svg {
  color: #ffffff !important;
  stroke: #ffffff !important;
  width: 24px;
  height: 24px;
}
/* Cores residuais removidas */

.section-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}
.section-desc {
  font-size: 0.85rem;
  opacity: 0.6;
}

/* ===== INPUTS ===== */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div {
  border-radius: 12px !important;
  border-color: rgba(255,255,255,0.08) !important;
  background: rgba(255, 255, 255, 0.03) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-baseweb="input"] > div:hover,
div[data-baseweb="select"] > div:hover {
  border-color: rgba(82, 121, 111, 0.4) !important;
}
div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {
  border-color: rgba(82, 121, 111, 0.6) !important;
  box-shadow: 0 0 0 2px rgba(82, 121, 111, 0.1) !important;
}

/* ===== BOTÕES ===== */
div.stDownloadButton button, div.stButton button {
  border-radius: 12px !important;
  padding: 0.6rem 1rem !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  background: rgba(255, 255, 255, 0.05) !important;
  backdrop-filter: blur(5px) !important;
  font-weight: 800 !important;
  color: #ffffff !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div.stDownloadButton button:hover, div.stButton button:hover {
  background: rgba(82, 121, 111, 0.25) !important;
  border-color: rgba(82, 121, 111, 0.6) !important;
  box-shadow: 0 4px 16px rgba(82, 121, 111, 0.3) !important;
  transform: translateY(-1px) !important;
}

/* ===== TABS ===== */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
  background: rgba(255,255,255,0.03);
  padding: 8px;
  border-radius: 14px;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px !important;
  padding: 10px 20px !important;
  font-weight: 800 !important;
}
.stTabs [aria-selected="true"] {
  background: rgba(82, 121, 111, 0.25) !important;
  border: 1px solid rgba(82, 121, 111, 0.6) !important;
  color: #ffffff !important;
}

/* ===== EXPANDERS ===== */
.streamlit-expanderHeader {
  background: rgba(255,255,255,0.03) !important;
  border-radius: 12px !important;
}


/* ===== SIDEBAR PREMIUM v2 ===== */
.sidebar-section {
  background: linear-gradient(145deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.06));
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 16px;
}
.sidebar-section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.15);
}
.sidebar-section-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff !important;
}
.sidebar-section-icon svg {
  color: #ffffff !important;
  stroke: #ffffff !important;
  width: 20px;
  height: 20px;
}
.sidebar-section-title {
  font-size: 0.95rem;
  font-weight: 800;
  color: #ffffff;
}
.sidebar-section-desc {
  font-size: 0.75rem;
  font-weight: 600;
  opacity: 1;
  margin-top: 2px;
  color: #ffffff;
}
.sidebar-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 14px;
}
.sidebar-stat {
  background: rgba(255,255,255,0.04);
  border-radius: 10px;
  padding: 10px;
  text-align: center;
}
.sidebar-stat-value {
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}
.sidebar-stat-label {
  font-size: 0.65rem;
  font-weight: 700;
  opacity: 1;
  text-transform: uppercase;
  margin-top: 2px;
  color: #ffffff;
}
.sidebar-tip {
  background: linear-gradient(145deg, rgba(34, 197, 94, 0.12), rgba(34, 197, 94, 0.04));
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 10px;
  padding: 12px;
  margin-top: 12px;
  font-size: 0.8rem;
  color: #86efac;
  line-height: 1.4;
}
.sidebar-version {
  text-align: center;
  font-size: 0.75rem;
  opacity: 0.4;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

/* ===== FILTER BAR v2 ===== */
.filter-container {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 24px;
  margin-bottom: 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.filter-container:hover {
  border-color: rgba(82, 121, 111, 0.6);
  box-shadow: 0 4px 16px rgba(82, 121, 111, 0.15);
}
.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.filter-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}.insight-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff !important;
}
.insight-icon svg {
  width: 22px;
  height: 22px;
  color: #ffffff !important;
  stroke: #ffffff !important;
}
.filter-main-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #e2e8f0;
}
.filter-subtitle {
  font-size: 0.8rem;
  opacity: 0.6;
}
.filter-count {
  background: rgba(139, 92, 246, 0.2);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #a78bfa;
}
.filter-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr 1fr;
  gap: 16px;
  align-items: end;
}
@media (max-width: 1000px) {
  .filter-grid { grid-template-columns: 1fr 1fr; }
}
.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-label {
  font-size: 0.8rem;
  font-weight: 800;
  color: #ffffff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ===== FRONT BUTTONS ===== */
.front-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.front-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}
.front-btn.defense {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.3);
}
.front-btn.correction {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.3);
}
.front-btn.attack {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border-color: rgba(59, 130, 246, 0.3);
}
.front-btn.cleanup {
  background: rgba(244, 63, 94, 0.15);
  color: #fb7185;
  border-color: rgba(244, 63, 94, 0.3);
}
.front-btn.optimization {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  border-color: rgba(139, 92, 246, 0.3);
}
.front-btn-count {
  background: rgba(255,255,255,0.15);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.8rem;
}


/* ===== SIDEBAR CARD ===== */
.sidebar-card {
  background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 16px;
  margin: 0.5rem 0 1rem 0;
}
.sidebar-title {
  font-size: 0.9rem;
  font-weight: 700;
  margin-bottom: 12px;
  color: #a5b4fc;
}

/* ===== FILTER BAR ===== */
.filter-bar {
  background: linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
}
.filter-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #a5b4fc;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== PROGRESS BAR ===== */
.progress-container {
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  height: 8px;
  overflow: hidden;
  margin: 8px 0;
}
.progress-bar {
  height: 100%;
  border-radius: 10px;
  transition: width 0.5s ease;
}
.progress-bar.green { background: linear-gradient(90deg, #22c55e, #4ade80); }
.progress-bar.amber { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.progress-bar.rose { background: linear-gradient(90deg, #f43f5e, #fb7185); }

/* ===== GRÁFICOS PLOTLY COM LIQUID GLASS ===== */
.js-plotly-plot {
  background: rgba(255, 255, 255, 0.03) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 16px !important;
  padding: 16px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.js-plotly-plot:hover {
  border-color: rgba(82, 121, 111, 0.4) !important;
  box-shadow: 0 4px 16px rgba(82, 121, 111, 0.15) !important;
}

/* ===== DATAFRAMES COM LIQUID GLASS ===== */
.stDataFrame {
  background: rgba(255, 255, 255, 0.03) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 16px !important;
  overflow: hidden !important;
}

/* ===== TABS COM HOVER VERDE MILITAR ===== */
.stTabs [data-baseweb="tab"]:hover {
  background: rgba(82, 121, 111, 0.15) !important;
}
.stTabs [aria-selected="true"] {
  background: rgba(82, 121, 111, 0.25) !important;
  border: 1px solid rgba(82, 121, 111, 0.6) !important;
  color: #ffffff !important;
}
.stTabs [data-baseweb="tab"] {
  color: #888888 !important;
}

</style>
    """,
    unsafe_allow_html=True,
)

# Header principal
st.markdown(
    """
<div class="hero-header">
  <div class="hero-title">
    <span style="margin-right:10px; vertical-align:middle; display:inline-flex; align-items:center;">
      <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
    </span>
    CURVA ABC, DIAGNÓSTICO E AÇÕES
  </div>
  <div class="hero-subtitle">Análise inteligente para decisões rápidas por frente e prioridade</div>
</div>
    """,
    unsafe_allow_html=True,
)


# =========================
# Helpers visuais
# =========================
def get_svg_icon(name: str):
    icons = {
        "package": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>',
        "dollar-sign": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
        "bar-chart-3": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>',
        "target": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        "trending-up": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
        "star": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
        "banknote": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>',
        "award": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>',
        "calendar": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>',
        "truck": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 17h4V5H2v12h3m15 0h2v-3.34a2 2 0 0 0-.73-1.5l-2.47-1.96a2 2 0 0 0-1.27-.45H14v7.25"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/></svg>',
        "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
        "megaphone": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/></svg>',
        "lightbulb": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1.3.5 2.6 1.5 3.5.8.8 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>',
        "search": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>',
        "layout": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><line x1="3" x2="21" y1="9" y2="9"/><line x1="9" x2="9" y1="21" y2="9"/></svg>'
    }
    return icons.get(name, icons["activity"])

def render_metric_card(label: str, value: str, icon: str = "activity", color: str = "purple"):
    svg = get_svg_icon(icon)
    st.markdown(
        f"""
<div class='metric-card'>
  <div class='metric-icon'>{svg}</div>
  <p class='metric-label'>{label}</p>
  <p class='metric-value'>{value}</p>
</div>
        """,
        unsafe_allow_html=True,
    )

def render_metric_grid(metrics: list):
    """Renderiza grid de métricas. metrics = [(label, value, icon, color), ...]"""
    html = '<div class="metric-grid">'
    for label, value, icon, color in metrics:
        icon_map = {
            "📦": "package",
            "💰": "dollar-sign",
            "📊": "bar-chart-3",
            "🎯": "target",
            "📈": "trending-up",
            "⭐": "star",
            "💵": "banknote",
            "🏆": "award"
        }
        icon_name = icon_map.get(icon, "activity")
        svg = get_svg_icon(icon_name)
        html += f"""
<div class='metric-card'>
  <div class='metric-icon'>{svg}</div>
  <p class='metric-label'>{label}</p>
  <p class='metric-value'>{value}</p>
</div>
        """
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def render_logistics_section(full_pct: float, correios_pct: float, flex_pct: float, outros_pct: float, period: str):
    """Renderiza seção de logística com todas as formas de entrega"""
    truck_svg = get_svg_icon("truck")
    package_svg = get_svg_icon("package")
    html = f"""
<div class="section-box">
  <div class="section-header">
    <div class="section-icon">{truck_svg}</div>
    <div>
      <div class="section-title">Logística - Período {period}</div>
      <div class="section-desc">Distribuição por forma de entrega</div>
    </div>
  </div>
  <div class="logistics-grid">
    <div class="logistics-card full">
      <div class="logistics-icon">{package_svg}</div>
      <div class="logistics-title">Full</div>
      <div class="logistics-value full">{full_pct:.1f}%</div>
      <div class="logistics-bar">
        <div class="logistics-bar-fill full" style="width: {full_pct}%"></div>
      </div>
    </div>
    <div class="logistics-card correios">
      <div class="logistics-icon">{package_svg}</div>
      <div class="logistics-title">Correios / Pontos</div>
      <div class="logistics-value correios">{correios_pct:.1f}%</div>
      <div class="logistics-bar">
        <div class="logistics-bar-fill correios" style="width: {correios_pct}%"></div>
      </div>
    </div>
    <div class="logistics-card flex">
      <div class="logistics-icon">{package_svg}</div>
      <div class="logistics-title">Flex</div>
      <div class="logistics-value flex">{flex_pct:.1f}%</div>
      <div class="logistics-bar">
        <div class="logistics-bar-fill flex" style="width: {flex_pct}%"></div>
      </div>
    </div>
  </div>
</div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_ads_section(ads_pct: float, organic_pct: float, ads_qty: int, organic_qty: int, period: str):
    """Renderiza seção de vendas por publicidade"""
    megaphone_svg = get_svg_icon("megaphone")
    html = f"""
<div class="ads-container">
  <div class="ads-header">
    <div class="ads-icon">{megaphone_svg}</div>
    <div class="ads-title">Vendas por Publicidade - Período {period}</div>
  </div>
  <div class="ads-grid">
    <div class="ads-metric ads">
      <div class="ads-metric-value ads">{ads_pct:.1f}%</div>
      <div class="ads-metric-label">Via Publicidade ({ads_qty:,} vendas)</div>
    </div>
    <div class="ads-metric organic">
      <div class="ads-metric-value organic">{organic_pct:.1f}%</div>
      <div class="ads-metric-label">Orgânicas ({organic_qty:,} vendas)</div>
    </div>
  </div>
  <div class="ads-bar-container">
    <div class="ads-bar-labels">
      <span>Ads</span>
      <span>Orgânico</span>
    </div>
    <div class="ads-bar">
      <div class="ads-bar-ads" style="width: {ads_pct}%"></div>
      <div class="ads-bar-organic" style="width: {organic_pct}%"></div>
    </div>
  </div>
</div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_export_card(icon: str, title: str, desc: str, itens: int, fat: float, card_type: str):
    """Renderiza card de exportação com estatísticas"""
    icon_map = {
        "🛡️": "target",
        "⚠️": "activity",
        "🚀": "trending-up",
        "🧹": "package",
        "⚙️": "star",
        "📦": "package"
    }
    icon_name = icon_map.get(icon, "package")
    svg = get_svg_icon(icon_name)
    return f"""
<div class='export-card'>
  <div class='export-header'>
    <div class='export-icon'>{svg}</div>
    <div>
      <div class='export-title'>{title}</div>
      <div class='export-desc'>{desc}</div>
    </div>
  </div>
  <div class='export-stats'>
    <div class='export-stat'>
      <div class='export-stat-value'>{br_int(itens)}</div>
      <div class='export-stat-label'>Itens</div>
    </div>
    <div class='export-stat'>
      <div class='export-stat-value'>{br_money(fat)}</div>
      <div class='export-stat-label'>Faturamento</div>
    </div>
  </div>
</div>
    """

def render_tactical_card(row: dict, frente: str):
    """Renderiza card tático para um produto"""
    frente_map = {
        "DEFESA": "defense",
        "CORREÇÃO": "correction",
        "ATAQUE": "attack",
        "LIMPEZA": "cleanup",
        "OTIMIZAÇÃO": "optimization"
    }
    card_class = frente_map.get(frente, "optimization")
    
    return f"""
<div class='tactical-card {card_class}'>
  <div class='tactical-header'>
    <div>
      <p class='tactical-title'>{row.get('Título', '-')[:60]}...</p>
      <p class='tactical-mlb'>{row.get('MLB', '-')}</p>
    </div>
    <span class='tactical-badge {card_class}'>{frente}</span>
  </div>
  <div class='tactical-metrics'>
    <div class='tactical-metric'>
      <div class='tactical-metric-value'>{row.get('Curva 0-30', '-')}</div>
      <div class='tactical-metric-label'>Curva Atual</div>
    </div>
    <div class='tactical-metric'>
      <div class='tactical-metric-value'>{row.get('Curva 31-60', '-')}</div>
      <div class='tactical-metric-label'>Curva Anterior</div>
    </div>
    <div class='tactical-metric'>
      <div class='tactical-metric-value'>{br_money(float(row.get('Fat. 0-30', 0))) if row.get('Fat. 0-30') else '-'}</div>
      <div class='tactical-metric-label'>Fat. Atual</div>
    </div>
    <div class='tactical-metric'>
      <div class='tactical-metric-value'>{br_int(row.get('Qntd 0-30', 0))}</div>
      <div class='tactical-metric-label'>Qtd. Atual</div>
    </div>
  </div>
  <div class='tactical-action'>{get_svg_icon("lightbulb")} {row.get('Ação sugerida', 'Sem ação definida')}</div>
</div>
    """

def render_front_summary(fronts: list):
    """Renderiza resumo das frentes. fronts = [(icon, count, label), ...]"""
    html = '<div class="front-summary">'
    icon_map = {
        "🛡️": "target",
        "⚠️": "activity",
        "🚀": "trending-up",
        "🧹": "package",
        "⚙️": "star"
    }
    for icon, count, label in fronts:
        icon_name = icon_map.get(icon, "package")
        svg = get_svg_icon(icon_name)
        html += f"""
<div class='front-pill'>
  <span class='front-pill-icon'>{svg}</span>
  <span class='front-pill-count'>{count}</span>
  <span class='front-pill-label'>{label}</span>
</div>
        """
    html += '</div>'
    return html

def render_report_section(icon: str, title: str, desc: str, color: str):
    """Renderiza header de seção do relatório"""
    icon_map = {
        "🔍": "search",
        "📦": "package",
        "📊": "bar-chart-3"
    }
    icon_name = icon_map.get(icon, "layout")
    svg = get_svg_icon(icon_name)
    return f"""
<div class='report-section'>
  <div class='report-header'>
    <div class='report-icon'>{svg}</div>
    <div>
      <div class='report-title'>{title}</div>
      <div class='report-desc'>{desc}</div>
    </div>
  </div>
    """

def render_kpi_highlight(kpis: list):
    """Renderiza KPIs destacados. kpis = [(value, label, color), ...]"""
    html = '<div class="kpi-grid">'
    for value, label, color in kpis:
        html += f"""
<div class='kpi-box {color}'>
  <div class='kpi-value {color}'>{value}</div>
  <div class='kpi-label'>{label}</div>
</div>
        """
    html += '</div>'
    return html

def render_insight_card(icon: str, title: str, text: str):
    """Renderiza card de insight"""
    icon_map = {
        "💡": "lightbulb",
        "📈": "trending-up",
        "🎯": "target",
        "📦": "package"
    }
    icon_name = icon_map.get(icon, "lightbulb")
    svg = get_svg_icon(icon_name)
    return f"""
<div class='insight-card'>
  <div class='insight-icon'>{svg}</div>
  <div>
    <div class='insight-title'>{title}</div>
    <div class='insight-text'>{text}</div>
  </div>
</div>
    """

def section_header(title: str, desc: str, icon: str = "📊", color: str = "purple"):
    """Renderiza header de seção"""
    icon_map = {
        "📊": "bar-chart-3",
        "🎯": "target",
        "📈": "trending-up",
        "🚚": "truck"
    }
    icon_name = icon_map.get(icon, "layout")
    svg = get_svg_icon(icon_name)
    st.markdown(
        f"""
<div class='section-box'>
  <div class='section-header'>
    <div class='section-icon'>{svg}</div>
    <div>
      <div class='section-title'>{title}</div>
      <div class='section-desc'>{desc}</div>
    </div>
  </div>
        """,
        unsafe_allow_html=True,
    )

def section_footer():
    st.markdown("</div>", unsafe_allow_html=True)

def render_front_card(icon: str, title: str, desc: str, itens: int, fat: float, card_type: str, filename: str, df_seg: pd.DataFrame):
    """Renderiza card de frente com download"""
    icon_map = {
        "🛡️": "target",
        "⚠️": "activity",
        "🚀": "trending-up",
        "🧹": "package",
        "⚙️": "star"
    }
    icon_name = icon_map.get(icon, "package")
    svg = get_svg_icon(icon_name)
    st.markdown(
        f"""
<div class='front-card'>
  <div class='front-header'>
    <div class='front-icon'>{svg}</div>
    <div>
      <div class='front-title'>{title}</div>
      <div class='front-desc'>{desc}</div>
    </div>
  </div>
  <div class='front-stats'>
    <div class='front-stat'>
      <div class='front-stat-value'>{br_int(itens)}</div>
      <div class='front-stat-label'>Itens</div>
    </div>
    <div class='front-stat'>
      <div class='front-stat-value'>{br_money(fat)}</div>
      <div class='front-stat-label'>Faturamento</div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        f"📥 Baixar {title}",
        data=to_xlsx_bytes(df_seg),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{title}_{filename}",
    )

# =========================
# Helpers de formatação
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

def pct(x, decimals=1) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{round(float(x) * 100, decimals)}%"
    except Exception:
        return "-"



def ensure_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Garante que todas as colunas existam antes do recorte (evita KeyError)."""
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols].copy()

rank = {"-": 0, "C": 1, "B": 2, "A": 3}

# Períodos em ordem decrescente (mais antigo primeiro)
periods = [
    ("91-120", "Curva 91-120", "Qntd 91-120", "Fat. 91-120"),
    ("61-90", "Curva 61-90", "Qntd 61-90", "Fat. 61-90"),
    ("31-60", "Curva 31-60", "Qntd 31-60", "Fat. 31-60"),
    ("0-30", "Curva 0-30", "Qntd 0-30", "Fat. 0-30"),
]

QTY_COLS = ["Qntd 0-30", "Qntd 31-60", "Qntd 61-90", "Qntd 91-120"]
FAT_COLS = ["Fat. 0-30", "Fat. 31-60", "Fat. 61-90", "Fat. 91-120"]
CURVE_COLS = ["Curva 0-30", "Curva 31-60", "Curva 61-90", "Curva 91-120"]

# =========================
# Loaders
# =========================
@st.cache_data
def _transform_ml_raw(file) -> tuple:
    """Converte o relatorio bruto de vendas do Mercado Livre (120 dias) na estrutura 'Export'.
    Retorna: (df_export, df_logistics, df_ads)
    """

    def _seek0(f):
        try:
            f.seek(0)
        except Exception:
            pass

    def _pick_col(cols, target: str) -> str:
        if target in cols:
            return target
        for c in cols:
            sc = str(c).strip()
            if sc.startswith(target + "."):
                return c
        t = target.lower()
        for c in cols:
            if t in str(c).lower():
                return c
        raise KeyError(f"Coluna '{target}' não encontrada")

    def _try_pick_col(cols, target: str):
        try:
            return _pick_col(cols, target)
        except KeyError:
            return None

    _seek0(file)
    preview = pd.read_excel(file, sheet_name=0, header=None, nrows=80)

    header_row = None
    for i in range(min(60, len(preview))):
        row = preview.iloc[i].astype(str).str.lower()
        if row.str.contains('data da venda', na=False).any() or row.str.contains('# de anúncio', na=False).any() or row.str.contains('de anúncio', na=False).any():
            header_row = i
            break
    if header_row is None:
        header_row = 0

    _seek0(file)
    df = pd.read_excel(file, sheet_name=0, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]

    col_data = _pick_col(df.columns, 'Data da venda')
    col_unid = _pick_col(df.columns, 'Unidades')

    try:
        col_rec = _pick_col(df.columns, 'Receita por produtos (BRL)')
    except Exception:
        col_rec = _pick_col(df.columns, 'Receita por produtos')

    col_mlb = _pick_col(df.columns, '# de anúncio')
    col_sku = _try_pick_col(df.columns, 'SKU')
    col_tit = _pick_col(df.columns, 'Título do anúncio')
    col_log = _pick_col(df.columns, 'Forma de entrega')
    
    # Nova coluna: Venda por publicidade (nome correto do ML)
    col_ads = None
    ads_variations = [
        'Venda por publicidade',  # Nome correto do ML
        'Venda por Publicidade',
        'Vendas por Publicidade',
        'Vendas por publicidade', 
        'vendas por publicidade',
        'venda por publicidade',
        'Publicidade',
        'publicidade',
    ]
    for var in ads_variations:
        col_ads = _try_pick_col(df.columns, var)
        if col_ads is not None:
            break
    
    # Se ainda não encontrou, busca parcial por "publicidade"
    if col_ads is None:
        for c in df.columns:
            c_lower = str(c).lower().strip()
            if 'publicidade' in c_lower:
                col_ads = c
                break

    use_cols = [col_data, col_unid, col_rec, col_mlb, col_tit, col_log]
    if col_sku is not None:
        use_cols.insert(4, col_sku)
    if col_ads is not None:
        use_cols.append(col_ads)

    base = df[use_cols].copy()

    # Renomear colunas
    if col_sku is None and col_ads is None:
        base.columns = ['data', 'unidades', 'receita', 'mlb', 'titulo', 'logistica']
        base['sku'] = ''
        base['ads'] = ''
    elif col_sku is None and col_ads is not None:
        base.columns = ['data', 'unidades', 'receita', 'mlb', 'titulo', 'logistica', 'ads']
        base['sku'] = ''
    elif col_sku is not None and col_ads is None:
        base.columns = ['data', 'unidades', 'receita', 'mlb', 'sku', 'titulo', 'logistica']
        base['ads'] = ''
    else:
        base.columns = ['data', 'unidades', 'receita', 'mlb', 'sku', 'titulo', 'logistica', 'ads']

    base['mlb'] = base['mlb'].astype(str).str.strip()
    base['sku'] = base['sku'].astype(str).str.strip()
    base['titulo'] = base['titulo'].astype(str).str.strip()
    base['logistica'] = base['logistica'].astype(str).str.strip()
    base['ads'] = base['ads'].astype(str).str.strip().str.lower()

    empty_mlb = base['mlb'].isin(['', 'nan', 'none', 'None', 'NaN'])
    if empty_mlb.any():
        base.loc[empty_mlb, 'mlb'] = base.loc[empty_mlb, 'sku']

    base['_data_raw'] = base['data'].astype(str)
    base['data'] = pd.to_datetime(base['_data_raw'], errors='coerce', dayfirst=True)

    if base['data'].notna().sum() == 0:
        s = base['_data_raw'].astype(str)
        for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y'):
            tmp = pd.to_datetime(s, errors='coerce', format=fmt)
            if tmp.notna().sum() > 0:
                base['data'] = tmp
                break

    if base['data'].notna().sum() == 0:
        month_map = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
            'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
            'agosto': '08', 'setembro': '09', 'outubro': '10',
            'novembro': '11', 'dezembro': '12',
        }
        s = base['_data_raw'].astype(str).str.lower()
        s = s.str.replace('hs.', '', regex=False).str.replace('hs', '', regex=False)
        for name, num in month_map.items():
            s = s.str.replace(rf'\b{name}\b', num, regex=True)
        s = s.str.replace(r'\s*de\s*', '/', regex=True)
        s = s.str.replace(r'\s+', ' ', regex=True).str.strip()
        tmp = pd.to_datetime(s, errors='coerce', dayfirst=True)
        if tmp.notna().sum() > 0:
            base['data'] = tmp

    base = base.drop(columns=['_data_raw'], errors='ignore')
    base = base.dropna(subset=['data'])
    base = base[~base['mlb'].isin(['', 'nan', 'none', 'None', 'NaN'])].copy()

    base['unidades'] = pd.to_numeric(base['unidades'], errors='coerce').fillna(0).astype(int)

    rec = base['receita']
    if rec.dtype == object:
        rec = (rec.astype(str)
                 .str.replace('\u00a0', '', regex=False)
                 .str.replace('.', '', regex=False)
                 .str.replace(',', '.', regex=False))
    base['receita'] = pd.to_numeric(rec, errors='coerce').fillna(0.0)

    if base.empty:
        cols = ['MLB','Título'] + [f'Qntd {p}' for p in ['0-30','31-60','61-90','91-120']] + [f'Fat. {p}' for p in ['0-30','31-60','61-90','91-120']] + [f'Curva {p}' for p in ['0-30','31-60','61-90','91-120']]
        empty_df = pd.DataFrame(columns=cols)
        empty_log = pd.DataFrame(columns=['periodo', 'full_pct', 'correios_pct', 'flex_pct', 'outros_pct', 'full_qty', 'correios_qty', 'flex_qty', 'outros_qty'])
        empty_ads = pd.DataFrame(columns=['periodo', 'ads_pct', 'organic_pct', 'ads_qty', 'organic_qty'])
        return empty_df, empty_log, empty_ads

    ref = base['data'].max()
    base['dias'] = (ref - base['data']).dt.days

    def bucket(d):
        if d <= 30:
            return '0-30'
        if d <= 60:
            return '31-60'
        if d <= 90:
            return '61-90'
        if d <= 120:
            return '91-120'
        return None

    base['periodo'] = base['dias'].apply(bucket)
    base = base.dropna(subset=['periodo'])

    # Classificar logística
    log_lower = base['logistica'].str.lower()
    base['is_full'] = log_lower.str.contains('full', na=False)
    base['is_correios'] = log_lower.str.contains('correios', na=False) | log_lower.str.contains('pontos', na=False) | log_lower.str.contains('ponto de envio', na=False)
    base['is_flex'] = log_lower.str.contains('flex', na=False)
    base['is_outros'] = ~(base['is_full'] | base['is_correios'] | base['is_flex'])
    
    # Classificar vendas por publicidade: "Sim" = venda via Ads, Vazio/outros = Orgânica
    # Normaliza valores e verifica se é "sim" ou variações
    ads_lower = base['ads'].astype(str).str.strip().str.lower()
    base['is_ads'] = ads_lower.isin(['sim', 's', 'yes', 'y', '1', 'true', 'si'])
    
    # Debug: contar quantos Ads foram encontrados
    ads_count = base['is_ads'].sum()
    total_count = len(base)
    # st.write(f"DEBUG: {ads_count} vendas via Ads de {total_count} total")

    # Agregar por período para logística
    logistics_data = []
    ads_data = []
    
    for periodo in ['0-30', '31-60', '61-90', '91-120']:
        periodo_df = base[base['periodo'] == periodo]
        total_qty = int(periodo_df['unidades'].sum())
        
        if total_qty > 0:
            full_qty = int(periodo_df[periodo_df['is_full']]['unidades'].sum())
            correios_qty = int(periodo_df[periodo_df['is_correios']]['unidades'].sum())
            flex_qty = int(periodo_df[periodo_df['is_flex']]['unidades'].sum())
            outros_qty = int(periodo_df[periodo_df['is_outros']]['unidades'].sum())
            
            logistics_data.append({
                'periodo': periodo,
                'full_pct': (full_qty / total_qty) * 100,
                'correios_pct': (correios_qty / total_qty) * 100,
                'flex_pct': (flex_qty / total_qty) * 100,
                'outros_pct': (outros_qty / total_qty) * 100,
                'full_qty': full_qty,
                'correios_qty': correios_qty,
                'flex_qty': flex_qty,
                'outros_qty': outros_qty,
                'total_qty': total_qty
            })
            
            # Vendas por publicidade
            ads_qty = int(periodo_df[periodo_df['is_ads']]['unidades'].sum())
            organic_qty = total_qty - ads_qty
            
            ads_data.append({
                'periodo': periodo,
                'ads_pct': (ads_qty / total_qty) * 100,
                'organic_pct': (organic_qty / total_qty) * 100,
                'ads_qty': ads_qty,
                'organic_qty': organic_qty,
                'total_qty': total_qty
            })
        else:
            logistics_data.append({
                'periodo': periodo,
                'full_pct': 0, 'correios_pct': 0, 'flex_pct': 0, 'outros_pct': 0,
                'full_qty': 0, 'correios_qty': 0, 'flex_qty': 0, 'outros_qty': 0, 'total_qty': 0
            })
            ads_data.append({
                'periodo': periodo,
                'ads_pct': 0, 'organic_pct': 0, 'ads_qty': 0, 'organic_qty': 0, 'total_qty': 0
            })

    df_logistics = pd.DataFrame(logistics_data)
    df_ads = pd.DataFrame(ads_data)

    # Agregação para export
    agg_total = base.groupby(['mlb','titulo','periodo'], as_index=False).agg(
        unidades=('unidades','sum'),
        receita=('receita','sum'),
    )

    agg_full = base[base['is_full']].groupby(['mlb','titulo','periodo'], as_index=False).agg(
        unidades_full=('unidades','sum'),
        receita_full=('receita','sum'),
    )

    agg = agg_total.merge(agg_full, on=['mlb','titulo','periodo'], how='left')
    agg['unidades_full'] = agg['unidades_full'].fillna(0).astype(int)
    agg['receita_full'] = agg['receita_full'].fillna(0.0)

    out_q = agg.pivot_table(index=['mlb','titulo'], columns='periodo', values='unidades', aggfunc='sum', fill_value=0)
    out_f = agg.pivot_table(index=['mlb','titulo'], columns='periodo', values='receita', aggfunc='sum', fill_value=0.0)
    out_qf = agg.pivot_table(index=['mlb','titulo'], columns='periodo', values='unidades_full', aggfunc='sum', fill_value=0)
    out_ff = agg.pivot_table(index=['mlb','titulo'], columns='periodo', values='receita_full', aggfunc='sum', fill_value=0.0)

    out = out_q.reset_index().rename(columns={'mlb':'MLB','titulo':'Título'})

    for p in ['0-30','31-60','61-90','91-120']:
        out[f'Qntd {p}'] = out_q[p].values if p in out_q.columns else 0
        out[f'Fat. {p}'] = out_f[p].values if p in out_f.columns else 0.0

        q_full = out_qf[p].values if p in out_qf.columns else 0
        f_full = out_ff[p].values if p in out_ff.columns else 0.0

        q_tot = out[f'Qntd {p}'].replace(0, np.nan)
        f_tot = out[f'Fat. {p}'].replace(0, np.nan)

        out[f'Share Full Qtd {p}'] = (q_full / q_tot).fillna(0.0)
        out[f'Share Full Fat {p}'] = (f_full / f_tot).fillna(0.0)
        out[f'Logística dom {p}'] = np.where(out[f'Share Full Qtd {p}'] >= 0.5, 'FULL', 'NÃO FULL')

    def curva_abc(fat_series: pd.Series) -> pd.Series:
        fat = fat_series.fillna(0.0)
        total = float(fat.sum())
        if total <= 0:
            return pd.Series(['-'] * len(fat), index=fat.index)
        order = fat.sort_values(ascending=False)
        cum = order.cumsum() / total
        curve = pd.Series(index=order.index, dtype=object)
        curve.loc[cum <= 0.80] = 'A'
        curve.loc[(cum > 0.80) & (cum <= 0.95)] = 'B'
        curve.loc[cum > 0.95] = 'C'
        curve.loc[order == 0] = '-'
        return curve.reindex(fat.index).fillna('-')

    for p in ['0-30','31-60','61-90','91-120']:
        out[f'Curva {p}'] = curva_abc(out[f'Fat. {p}'])

    return out, df_logistics, df_ads


@st.cache_data
def load_main(file) -> tuple:
    """Aceita planilha pronta (aba Export) OU relatorio bruto do ML.
    Retorna: (df_main, df_logistics, df_ads)
    """
    if hasattr(file, 'seek'):
        file.seek(0)

    df_logistics = pd.DataFrame()
    df_ads = pd.DataFrame()

    try:
        xls = pd.ExcelFile(file)
        sheet_names = [str(s) for s in getattr(xls, 'sheet_names', [])]
    except Exception:
        if hasattr(file, 'seek'):
            file.seek(0)
        df, df_logistics, df_ads = _transform_ml_raw(file)
    else:
        if 'Export' in sheet_names:
            if hasattr(file, 'seek'):
                file.seek(0)
            df = pd.read_excel(file, sheet_name='Export')
        else:
            if hasattr(file, 'seek'):
                file.seek(0)
            df, df_logistics, df_ads = _transform_ml_raw(file)

    for col in QTY_COLS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    for col in FAT_COLS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    for col in CURVE_COLS:
        if col not in df.columns:
            df[col] = '-'
        df[col] = df[col].fillna('-').astype(str).str.strip()

    if 'MLB' not in df.columns:
        df['MLB'] = ''
    if 'Título' not in df.columns:
        if 'Titulo' in df.columns:
            df['Título'] = df['Titulo']
        else:
            df['Título'] = ''

    df['MLB'] = df['MLB'].astype(str).str.strip()
    df['Título'] = df['Título'].astype(str).str.strip()

    return df, df_logistics, df_ads


# =========================
# Sidebar Premium v2
# =========================
with st.sidebar:
    # Logo e título
    chart_svg = get_svg_icon("bar-chart-3")
    st.markdown(
        f"""
<div style="text-align: center; padding: 10px 0 20px 0;">
  <div style="font-size: 2rem; margin-bottom: 4px; display: flex; justify-content: center; color: #ffffff;">{chart_svg}</div>
  <div style="font-size: 1.1rem; font-weight: 800; background: linear-gradient(135deg, #fff, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Curva ABC</div>
  <div style="font-size: 0.75rem; opacity: 0.5;">Diagnóstico & Ações</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # Seção de Upload
    package_svg = get_svg_icon("package")
    st.markdown(
        f"""
<div class='sidebar-section'>
  <div class='sidebar-section-header'>
    <div class='sidebar-section-icon'>{package_svg}</div>
    <div>
      <div class='sidebar-section-title'>Upload de Dados</div>
      <div class='sidebar-section-desc'>Mercado Livre ou Shopee</div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    
    uploaded_files = st.file_uploader(
        "📂 Carregar relatório(s) de vendas",
        type=["xlsx", "xls"],
        help="Suporta Mercado Livre e Shopee. Para Shopee, você pode enviar múltiplos arquivos.",
        accept_multiple_files=True,
        key="main_files"
    )

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # Seção de Filtros
    target_svg = get_svg_icon("target")
    st.markdown(
        f"""
<div class='sidebar-section'>
  <div class='sidebar-section-header'>
    <div class='sidebar-section-icon'>{target_svg}</div>
    <div>
      <div class='sidebar-section-title'>Filtros Globais</div>
      <div class='sidebar-section-desc'>Selecione as curvas para análise</div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    curve_filter = st.multiselect(
        "Curvas 0-30",
        options=["A", "B", "C", "-"],
        default=["A", "B", "C", "-"],
        help="A = Top 80% faturamento | B = Próximos 15% | C = Últimos 5% | - = Sem vendas"
    )
    
    # Dica
    st.markdown(
        """
<div class='sidebar-tip'>
  <strong>DICA:</strong> Use as curvas para focar sua análise. Curva A são seus produtos estrela!
</div>
        """,
        unsafe_allow_html=True,
    )
    
    # Versão
    st.markdown(
        """
<div class='sidebar-version'>
  Dashboard v4.3 • Manus AI
</div>
        """,
        unsafe_allow_html=True,
    )

if not uploaded_files:
    st.info("Faça upload do(s) relatório(s) de vendas (Mercado Livre ou Shopee) para começar.")
    st.stop()

# =========================
# Carregar dados
# =========================
# Detecta o canal baseado no primeiro arquivo
try:
    from data_processing.factory import detect_channel
    canal_detectado = detect_channel(uploaded_files)
    
    # Armazena o canal no session_state
    st.session_state['canal'] = canal_detectado
    
    # Exibe o canal detectado na sidebar
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-section">
            <div class="sidebar-section-header">
                <div class="sidebar-section-icon">🏪</div>
                <div>
                    <div class="sidebar-section-title">Canal Detectado</div>
                    <div class="sidebar-section-desc">{canal_detectado}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Processa conforme o canal
    if canal_detectado == 'Shopee':
        from data_processing.factory import detect_and_process
        _, df, df_logistics, df_ads = detect_and_process(uploaded_files)
    else:  # Mercado Livre - usa lógica original
        df, df_logistics, df_ads = load_main(uploaded_files[0])
    
except Exception as e:
    st.error(f"Erro ao processar arquivo(s): {str(e)}")
    import traceback
    st.error(traceback.format_exc())
    st.stop()

if df.empty:
    st.warning("Nenhum dado válido encontrado no arquivo.")
    st.stop()

# Filtrar por curva
df_f = df[df["Curva 0-30"].isin(curve_filter)].copy()

if df_f.empty:
    st.warning("Nenhum produto corresponde aos filtros selecionados.")
    st.stop()

# =========================
# Cálculos auxiliares
# =========================
df_f["Fat total"] = df_f[FAT_COLS].sum(axis=1)
df_f["Qtd total"] = df_f[QTY_COLS].sum(axis=1)
df_f["TM total"] = df_f.apply(lambda r: safe_div(r["Fat total"], r["Qtd total"]), axis=1)

kpi_rows = []
for p, cc, qq, ff in periods:
    fat = float(df_f[ff].sum())
    qty = int(df_f[qq].sum())
    tm = safe_div(fat, qty)
    kpi_rows.append({"Período": p, "Qtd": qty, "Faturamento": fat, "Ticket médio": tm})
kpi_df = pd.DataFrame(kpi_rows)

# =========================
# Segmentações
# =========================
# Adapta segmentações conforme o canal
if st.session_state.get('canal') == 'Shopee':
    # Para Shopee (período único), usa apenas curva atual
    anchors = df_f[
        (df_f["Curva 0-30"] == "A")
    ].sort_values("Fat total", ascending=False).copy()
    
    inactivate = df_f[
        (df_f["Qntd 0-30"] == 0)
    ].sort_values("Fat total", ascending=False).copy()
    
    revitalize = df_f[
        (df_f["Curva 0-30"].isin(["C", "-"])) &
        (df_f["Qntd 0-30"] > 0)  # Teve vendas mas está em C ou -
    ].sort_values("Fat total", ascending=False).copy()
else:
    # Para Mercado Livre (múltiplos períodos), usa histórico
    anchors = df_f[
        (df_f["Curva 0-30"] == "A") &
        (df_f["Curva 31-60"].isin(["A", "B"])) &
        (df_f["Curva 61-90"].isin(["A", "B"]))
    ].sort_values("Fat total", ascending=False).copy()
    
    inactivate = df_f[
        (df_f["Qntd 0-30"] == 0) &
        (df_f["Qntd 31-60"] == 0) &
        (df_f["Qntd 61-90"] == 0)
    ].sort_values("Fat total", ascending=False).copy()
    
    revitalize = df_f[
        (df_f["Curva 31-60"].isin(["A", "B"])) &
        (df_f["Curva 0-30"].isin(["C", "-"]))
    ].sort_values("Fat total", ascending=False).copy()

if st.session_state.get('canal') == 'Shopee':
    # Para Shopee, adapta segmentações para período único
    rise_to_A = df_f[
        (df_f["Curva 0-30"] == "A") &
        (df_f["Qntd 0-30"] > 0)
    ].sort_values("Fat total", ascending=False).copy()
    
    opp_50_60 = df_f[
        (df_f["Curva 0-30"] == "B")
    ].sort_values("Fat total", ascending=False).copy()
    
    dead_stock_combo = df_f[
        (df_f["Curva 0-30"] == "-") &
        (df_f["Fat total"] > 0)
    ].sort_values("TM total", ascending=False).copy()
    
    # Fuga de receita: produtos C ou - com bom ticket médio (potencial)
    drop_alert = df_f[
        (df_f["Curva 0-30"].isin(["C", "-"])) &
        (df_f["TM total"] > df_f["TM total"].median())
    ].copy()
    
    if len(drop_alert) > 0:
        drop_alert["Perda estimada"] = drop_alert["TM total"] * 10  # Estima perda baseada no TM
        drop_alert = drop_alert.sort_values("Perda estimada", ascending=False)
else:
    # Para Mercado Livre, usa lógica original com histórico
    rise_to_A = df_f[
        (df_f["Curva 31-60"].isin(["B", "C"])) &
        (df_f["Curva 0-30"] == "A")
    ].sort_values("Fat total", ascending=False).copy()
    
    opp_50_60 = df_f[
        (df_f["Curva 0-30"] == "B") &
        (df_f["Qntd 0-30"] >= df_f["Qntd 31-60"] * 1.1)
    ].sort_values("Fat total", ascending=False).copy()
    
    dead_stock_combo = df_f[
        (df_f["Curva 0-30"] == "-") &
        (df_f["Fat total"] > 0)
    ].sort_values("TM total", ascending=False).copy()
    
    drop_alert = df_f[
        (df_f["Curva 31-60"].isin(["A", "B"])) &
        (df_f["Curva 0-30"].isin(["C", "-"]))
    ].copy()
    
    if len(drop_alert) > 0:
        drop_alert["Fat anterior ref"] = drop_alert[["Fat. 31-60", "Fat. 61-90"]].max(axis=1)
        drop_alert["Perda estimada"] = drop_alert["Fat anterior ref"] - drop_alert["Fat. 0-30"]
        drop_alert = drop_alert.sort_values("Perda estimada", ascending=False)

# =========================
# Plano tático
# =========================
plan = df_f.copy()

def suggest_action(row):
    c0, c1 = row["Curva 0-30"], row["Curva 31-60"]
    
    # Para Shopee (sem histórico), usa apenas curva atual
    if st.session_state.get('canal') == 'Shopee':
        if c0 == "A":
            return "Garantir estoque 30d + otimizar fotos/título + avaliar Shopee Ads"
        elif c0 == "B":
            return "Testar Shopee Ads com palavras-chave específicas (cauda longa)"
        elif c0 == "C":
            # Verifica se tem bom ticket médio (potencial)
            tm_total = row.get("TM total", 0)
            if tm_total > 0:
                return "Diagnosticar gargalo (CTR/conversão) + melhorar imagens/descrição"
            else:
                return "Testar preço promocional + bundle ou liquidar"
        elif c0 == "-":
            # Verifica se teve faturamento (dead stock) ou é inativo
            fat_total = row.get("Fat total", 0)
            if fat_total > 0:
                return "Criar bundle com produto âncora ou participar Shopee Liquida"
            else:
                return "Testar preço promocional última chance ou desativar"
        return "-"
    
    # Para Mercado Livre (com histórico), usa comparação de períodos
    if c0 == "A" and c1 in ["A", "B"]:
        return "Garantir estoque 30-60d + completar ficha técnica 100% + avaliar ML Ads"
    if c0 == "A" and c1 in ["C", "-"]:
        return "Subiu rápido – validar se é sazonal ou tendência antes de escalar"
    if c0 == "B" and c1 == "A":
        return "Caiu de A→B: diagnosticar (CTR/conversão/Buy Box) + corrigir gargalo"
    if c0 == "B" and c1 in ["B", "C"]:
        return "Potencial de crescimento: otimizar anúncio (conversão >2%) + testar ML Ads"
    if c0 == "C":
        return "Diagnosticar gargalo (foto/preço/descrição) + testar promoção ou kit"
    if c0 == "-":
        return "Sem giro: otimizar última chance (preço/foto) ou liquidar e liberar capital"
    return "-"

plan["Ação sugerida"] = plan.apply(suggest_action, axis=1)

actions = pd.DataFrame(index=plan.index)
actions["7d"] = "-"
actions["15d"] = "-"
actions["30d"] = "-"

# DEFESA - Âncoras (produtos A estáveis)
if st.session_state.get('canal') == 'Shopee':
    actions.loc[anchors.index, "7d"] = "Garantir estoque 30-60d + monitorar taxa resposta (100%) + checar prazo entrega"
    actions.loc[anchors.index, "15d"] = "Adicionar foto uso real + tabela medidas + responder FAQ na descrição"
    actions.loc[anchors.index, "30d"] = "Testar Shopee Ads (cauda longa) se ACOS < margem + criar bundle upsell"
else:
    actions.loc[anchors.index, "7d"] = "Estoque 30-60d + monitorar Buy Box + validar reputação (resposta <24h, reclamações <1%)"
    actions.loc[anchors.index, "15d"] = "Completar ficha técnica 100% + adicionar vídeo 15-30s + organizar variações"
    actions.loc[anchors.index, "30d"] = "Se conversão >2%: testar ML Ads (cauda longa, ACOS <25-30%) + Full/Flex"

# CORREÇÃO - Queda de faturamento / Fuga de receita
if st.session_state.get('canal') == 'Shopee':
    actions.loc[drop_alert.index, "7d"] = "Diagnosticar: CTR baixo (imagem/título) ou conversão baixa (descrição/preço/frete)"
    actions.loc[drop_alert.index, "15d"] = "Testar nova capa (zoom produto + selo benefício) + expandir descrição com FAQ"
    actions.loc[drop_alert.index, "30d"] = "Participar Flash Sale (margem mín aceitável) + cupom prazo limitado"
else:
    actions.loc[drop_alert.index, "7d"] = "Diagnosticar: CTR <1% (foto/título) ou conversão <2% (preço/descrição/frete) + comparar concorrentes"
    actions.loc[drop_alert.index, "15d"] = "Corrigir gargalo: foto fundo branco + título otimizado + FAQ na descrição + ajustar preço"
    actions.loc[drop_alert.index, "30d"] = "Se ajustes não funcionaram: oferta relâmpago ou cupom + responder avaliações negativas"

# CORREÇÃO - Reativar produtos
if st.session_state.get('canal') == 'Shopee':
    actions.loc[revitalize.index, "7d"] = "Ler avaliações negativas concorrentes + responder todas avaliações negativas"
    actions.loc[revitalize.index, "15d"] = "Ajustar preço (usar âncora: cheio+desconto) + melhorar capa (fundo limpo)"
    actions.loc[revitalize.index, "30d"] = "Cupom seguidor (criar base clientes) + monitorar se conversão voltou"
else:
    actions.loc[revitalize.index, "7d"] = "Diagnosticar problema: sem impressões (SEO) ou CTR baixo (foto) + verificar categoria correta"
    actions.loc[revitalize.index, "15d"] = "Otimizar: título com palavra-chave + ficha técnica 100% + foto fundo branco + vídeo"
    actions.loc[revitalize.index, "30d"] = "Testar preço promocional (abaixo média) + cupom + monitorar se conversão voltou"

# ATAQUE - Subindo para A
if st.session_state.get('canal') == 'Shopee':
    actions.loc[rise_to_A.index, "7d"] = "Estoque 30-60d + otimizar anúncio (conversão >2%) antes de investir Ads"
    actions.loc[rise_to_A.index, "15d"] = "Ativar Shopee Ads: orçamento baixo + palavras cauda longa + monitorar ACOS"
    actions.loc[rise_to_A.index, "30d"] = "Se ROAS >3: aumentar budget + participar campanhas (11.11, Black Friday)"
else:
    actions.loc[rise_to_A.index, "7d"] = "Estoque 60-90d + validar conversão >2% + completar ficha técnica 100% + Full/Flex"
    actions.loc[rise_to_A.index, "15d"] = "Ativar ML Ads: orçamento baixo + palavras cauda longa + monitorar ACOS diariamente"
    actions.loc[rise_to_A.index, "30d"] = "Se ACOS <25-30%: aumentar budget + participar ofertas relâmpago + monitorar posição orgânica"

# ATAQUE - Oportunidades B/C
if st.session_state.get('canal') == 'Shopee':
    actions.loc[opp_50_60.index, "7d"] = "Calcular margem líquida + ACOS máx aceitável + volume busca categoria"
    actions.loc[opp_50_60.index, "15d"] = "Testar Ads: termos específicos (ex: 'sapato social preto 40' > 'sapato')"
    actions.loc[opp_50_60.index, "30d"] = "Ajustar lances (alto rendimento: +lance | baixo: pausar) + criar bundles"
else:
    actions.loc[opp_50_60.index, "7d"] = "Calcular margem líquida + ACOS máx aceitável + otimizar anúncio (conversão >2%)"
    actions.loc[opp_50_60.index, "15d"] = "Testar ML Ads: termos específicos (ex: 'tênis corrida nike 42' > 'tênis') + monitorar CTR"
    actions.loc[opp_50_60.index, "30d"] = "Ajustar lances (alto ROAS: +lance | baixo: pausar) + testar kit com produto âncora"

# LIMPEZA - Combo/Kit
if st.session_state.get('canal') == 'Shopee':
    actions.loc[dead_stock_combo.index, "7d"] = "Analisar: quem comprou também comprou? Pesquisar combos concorrentes"
    actions.loc[dead_stock_combo.index, "15d"] = "Criar bundle (dead stock + âncora) desconto 10-20% + anúncio novo"
    actions.loc[dead_stock_combo.index, "30d"] = "Se bundle não funcionou: Shopee Liquida com preço agressivo"
else:
    actions.loc[dead_stock_combo.index, "7d"] = "Analisar: quem comprou também comprou? Pesquisar kits concorrentes + avaliar margem kit"
    actions.loc[dead_stock_combo.index, "15d"] = "Criar kit (dead stock + âncora) desconto 10-20% + anúncio novo otimizado + variações"
    actions.loc[dead_stock_combo.index, "30d"] = "Se kit não vendeu: liquidação agressiva (preço abaixo custo) + oferta relâmpago"

# LIMPEZA - Inativar
if st.session_state.get('canal') == 'Shopee':
    actions.loc[inactivate.index, "7d"] = "Calcular custo oportunidade (capital imobilizado) + verificar se obsoleto"
    actions.loc[inactivate.index, "15d"] = "Liquidação: preço agressivo + frete grátis + comunicar 'Última Chance'"
    actions.loc[inactivate.index, "30d"] = "Se não vendeu: desativar + liquidar lote ou doar (crédito fiscal)"
else:
    actions.loc[inactivate.index, "7d"] = "Calcular custo oportunidade (capital imobilizado) + diagnosticar: obsoleto ou anúncio ruim?"
    actions.loc[inactivate.index, "15d"] = "Liquidação: preço agressivo + frete grátis + comunicar 'Última Chance' + ML Ads baixo orçamento"
    actions.loc[inactivate.index, "30d"] = "Se não vendeu: desativar + liquidar lote (revendedores) ou doar (crédito fiscal)"

# OTIMIZAÇÃO - Produtos que não se encaixam em outras frentes
# Identificar índices de otimização (todos que não estão nas outras frentes)
all_classified = set(anchors.index) | set(drop_alert.index) | set(revitalize.index) | set(rise_to_A.index) | set(opp_50_60.index) | set(dead_stock_combo.index) | set(inactivate.index)
optimization_idx = [idx for idx in plan.index if idx not in all_classified]

for idx in optimization_idx:
    row = plan.loc[idx]
    c0 = row.get("Curva 0-30", "-")
    c1 = row.get("Curva 31-60", "-")
    
    if c0 == "A":
        # Produto A que não é âncora - subiu rápido
        actions.loc[idx, "7d"] = "Validar se é sazonal"
        actions.loc[idx, "15d"] = "Monitorar tendência"
        actions.loc[idx, "30d"] = "Decidir estratégia"
    elif c0 == "B":
        # Produto B estável ou em transição
        actions.loc[idx, "7d"] = "Analisar histórico"
        actions.loc[idx, "15d"] = "Testar otimização"
        actions.loc[idx, "30d"] = "Avaliar promoção"
    elif c0 == "C":
        # Produto C - baixo volume
        actions.loc[idx, "7d"] = "Revisar preço"
        actions.loc[idx, "15d"] = "Testar destaque"
        actions.loc[idx, "30d"] = "Avaliar combo"
    else:
        # Sem vendas recentes
        actions.loc[idx, "7d"] = "Verificar anúncio"
        actions.loc[idx, "15d"] = "Ajustar estratégia"
        actions.loc[idx, "30d"] = "Decidir manter/remover"

plan["Plano 7 dias"] = actions["7d"]
plan["Plano 15 dias"] = actions["15d"]
plan["Plano 30 dias"] = actions["30d"]

def frente_bucket(idx):
    if idx in anchors.index:
        return "DEFESA"
    if idx in drop_alert.index:
        return "CORREÇÃO"
    if idx in revitalize.index:
        return "CORREÇÃO"
    if idx in rise_to_A.index or idx in opp_50_60.index:
        return "ATAQUE"
    if idx in dead_stock_combo.index or idx in inactivate.index:
        return "LIMPEZA"
    return "OTIMIZAÇÃO"

plan["Frente"] = [frente_bucket(i) for i in plan.index]

# =========================
# Diagnóstico macro
# =========================
dist_0_30 = df_f["Curva 0-30"].value_counts().reindex(["A", "B", "C", "-"]).fillna(0).astype(int)
dist_0_30_df = pd.DataFrame({"Curva": dist_0_30.index, "Anúncios": dist_0_30.values})

fat_0_30_total = float(df_f["Fat. 0-30"].sum())
fat_0_30_A = float(df_f.loc[df_f["Curva 0-30"] == "A", "Fat. 0-30"].sum())
conc_A_0_30 = safe_div(fat_0_30_A, fat_0_30_total)

# Busca ticket médio usando os nomes de período
tm_0_30_row = kpi_df.loc[kpi_df["Período"] == "0-30", "Ticket médio"]
tm_31_60_row = kpi_df.loc[kpi_df["Período"] == "31-60", "Ticket médio"]
tm_61_90_row = kpi_df.loc[kpi_df["Período"] == "61-90", "Ticket médio"]

tm_0_30 = float(tm_0_30_row.iloc[0]) if len(tm_0_30_row) > 0 else 0.0
tm_31_60 = float(tm_31_60_row.iloc[0]) if len(tm_31_60_row) > 0 else 0.0
tm_61_90 = float(tm_61_90_row.iloc[0]) if len(tm_61_90_row) > 0 else 0.0

def tm_direction(a, b, c):
    if np.isnan(a) or np.isnan(b) or np.isnan(c):
        return "Sem dados suficientes para leitura do ticket médio."
    if a < b < c:
        return "📈 Ticket médio subindo. Ajuda margem, mas pode cair volume se preço esticar."
    if a > b > c:
        return "📉 Ticket médio caindo. Pode ser mix mais barato ou promoções."
    if b < a and c > b:
        return "🔄 Ticket caiu e depois recuperou."
    if b > a and c < b:
        return "⚡ Ticket subiu e depois caiu."
    return "📊 Ticket oscilando. Vale cruzar com mix e concorrência."

tm_reading = tm_direction(tm_0_30, tm_31_60, tm_61_90)

# =========================
# KPIs topo
# =========================
total_ads = len(df_f)
tt_fat = float(df_f[FAT_COLS].sum().sum())
tt_qty = int(df_f[QTY_COLS].sum().sum())

# Renderiza métricas principais
render_metric_grid([
    ("Total de Anúncios", br_int(total_ads), "📦", "purple"),
    ("Faturamento Total", br_money(tt_fat), "💰", "green"),
    ("Quantidade Total", br_int(tt_qty), "📊", "blue"),
    ("Ticket Médio", br_money(safe_div(tt_fat, tt_qty) if tt_qty else 0.0), "🎯", "amber"),
])

st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["DASHBOARD", "LISTAS E EXPORTAÇÃO", "PLANO TÁTICO", "RELATÓRIO ESTRATÉGICO"])

# =========================
# TAB 1: Dashboard
# =========================
with tab1:
    # Seletor de período
    st.markdown(
        """
<div class='period-selector'>
  <div class='period-label'><i data-lucide="calendar" style="margin-right:8px;"></i> Selecione o Período para Análise</div>
</div>
<script>lucide.createIcons();</script>
        """,
        unsafe_allow_html=True,
    )
    
    selected_period = st.selectbox(
        "Período",
        options=["0-30", "31-60", "61-90", "91-120"],
        index=0,
        label_visibility="collapsed"
    )
    
    # Mapear colunas baseado no período selecionado
    period_map = {
        "0-30": ("Curva 0-30", "Qntd 0-30", "Fat. 0-30"),
        "31-60": ("Curva 31-60", "Qntd 31-60", "Fat. 31-60"),
        "61-90": ("Curva 61-90", "Qntd 61-90", "Fat. 61-90"),
        "91-120": ("Curva 91-120", "Qntd 91-120", "Fat. 91-120"),
    }
    
    curve_col, qty_col, fat_col = period_map[selected_period]
    
    # Métricas do período selecionado
    period_fat = float(df_f[fat_col].sum())
    period_qty = int(df_f[qty_col].sum())
    period_tm = safe_div(period_fat, period_qty)
    
    # Distribuição de curvas do período
    dist_period = df_f[curve_col].value_counts().reindex(["A", "B", "C", "-"]).fillna(0).astype(int)
    dist_period_df = pd.DataFrame({"Curva": dist_period.index, "Anúncios": dist_period.values})
    
    # Métricas do período
    render_metric_grid([
        (f"Faturamento {selected_period}", br_money(period_fat), "💰", "green"),
        (f"Quantidade {selected_period}", br_int(period_qty), "📦", "blue"),
        (f"Ticket Médio {selected_period}", br_money(period_tm), "🎯", "amber"),
        (f"Curva A ({selected_period})", br_int(dist_period.get("A", 0)), "⭐", "purple"),
    ])

    left, right = st.columns([1.2, 1])

    with left:
        section_header("Resumo por Período", "Visão consolidada das 4 janelas de tempo", "📅", "purple")
        show = kpi_df.copy()
        show["Qtd"] = show["Qtd"].map(br_int)
        show["Faturamento"] = show["Faturamento"].map(br_money)
        show["Ticket médio"] = show["Ticket médio"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        
        # Destacar período selecionado
        st.dataframe(show, use_container_width=True, hide_index=True, height=220)
        section_footer()

    with right:
        section_header(f"Distribuição de Curvas ({selected_period})", f"Período selecionado: {selected_period} dias", "🎯", "blue")
        colors_map = {"A": "#22c55e", "B": "#3b82f6", "C": "#f59e0b", "-": "#6b7280"}
        fig = px.bar(
            dist_period_df, 
            x="Curva", 
            y="Anúncios",
            color="Curva",
            color_discrete_map=colors_map
        )
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=20, b=20),
            font=dict(color='#9ca3af')
        )
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
        section_footer()

    # Seções específicas por canal
    if st.session_state.get('canal') == 'Mercado Livre':
        # Seção de Logística (apenas Mercado Livre)
        if not df_logistics.empty:
            log_row = df_logistics[df_logistics['periodo'] == selected_period]
            if not log_row.empty:
                log_row = log_row.iloc[0]
                render_logistics_section(
                    full_pct=log_row['full_pct'],
                    correios_pct=log_row['correios_pct'],
                    flex_pct=log_row['flex_pct'],
                    outros_pct=log_row['outros_pct'],
                    period=selected_period
                )
        else:
            # Fallback para cálculo antigo se não tiver dados de logística
            if all(c in df_f.columns for c in [f"Share Full Qtd {selected_period}", f"Share Full Fat {selected_period}"]):
                section_header(f"Logística no Período {selected_period}", "Distribuição FULL vs NÃO FULL", "🚚", "cyan")
                qtd_total = float(df_f[qty_col].sum())
                fat_total = float(df_f[fat_col].sum())
                share_full_qtd = (
                    (df_f[qty_col] * df_f[f"Share Full Qtd {selected_period}"]).sum() / qtd_total
                    if qtd_total > 0 else 0.0
                )
                share_full_fat = (
                    (df_f[fat_col] * df_f[f"Share Full Fat {selected_period}"]).sum() / fat_total
                    if fat_total > 0 else 0.0
                )
                dom = "FULL" if share_full_qtd >= 0.5 else "NÃO FULL"
                
                render_metric_grid([
                    ("FULL por Quantidade", pct(share_full_qtd, 1), "📦", "cyan"),
                    ("FULL por Faturamento", pct(share_full_fat, 1), "💵", "green"),
                    ("Logística Dominante", dom, "🏆", "purple" if dom == "FULL" else "amber"),
                ])
                section_footer()

        # Seção de Vendas por Publicidade (apenas Mercado Livre)
        if not df_ads.empty:
            ads_row = df_ads[df_ads['periodo'] == selected_period]
            if not ads_row.empty:
                ads_row = ads_row.iloc[0]
                render_ads_section(
                    ads_pct=ads_row['ads_pct'],
                    organic_pct=ads_row['organic_pct'],
                    ads_qty=int(ads_row['ads_qty']),
                    organic_qty=int(ads_row['organic_qty']),
                    period=selected_period
                )
    
    elif st.session_state.get('canal') == 'Shopee':
        # Seções específicas da Shopee
        st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)
        
        # Funil de Conversão
        render_shopee_conversion_funnel(df_f)
        
        st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)
        
        # Métricas de Engajamento
        render_shopee_engagement_metrics(df_f)
        
        st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)
        
        # Distribuição ABC
        render_shopee_abc_distribution(df_f)
        
        st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)
        
        # Top Produtos
        render_shopee_top_products(df_f, top_n=10)

    section_header("Faturamento por Curva e Período", "Comparativo entre as janelas de tempo", "📊", "green")
    rev_rows = []
    for p, cc, qq, ff in periods:
        grp = df_f.groupby(cc)[ff].sum()
        for curva in ["A", "B", "C", "-"]:
            rev_rows.append({"Período": p, "Curva": curva, "Faturamento": float(grp.get(curva, 0.0))})
    rev_df = pd.DataFrame(rev_rows)
    fig2 = px.bar(
        rev_df, 
        x="Período", 
        y="Faturamento", 
        color="Curva", 
        barmode="group",
        color_discrete_map=colors_map,
        category_orders={"Período": ["91-120", "61-90", "31-60", "0-30"]}  # Ordem decrescente
    )
    fig2.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color='#9ca3af'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig2, use_container_width=True)
    section_footer()

    section_header("Evolução do Ticket Médio", "Tendência ao longo dos períodos", "📈", "amber")
    tm_df = kpi_df.copy()
    tm_df["Ticket médio"] = tm_df["Ticket médio"].fillna(0.0)
    fig3 = px.line(
        tm_df, 
        x="Período", 
        y="Ticket médio", 
        markers=True,
        category_orders={"Período": ["91-120", "61-90", "31-60", "0-30"]}  # Ordem decrescente
    )
    fig3.update_traces(line_color='#f59e0b', marker_color='#fbbf24', line_width=3, marker_size=10)
    fig3.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color='#9ca3af')
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.info(tm_reading)
    section_footer()

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    
    section_header("Ações por Frente", "Visão estratégica das prioridades", "🎯", "rose")
    
    def _front_agg(df_seg: pd.DataFrame):
        if df_seg is None or len(df_seg) == 0:
            return 0, 0.0
        fat_col_agg = "Fat. 0-30" if "Fat. 0-30" in df_seg.columns else ("Fat total" if "Fat total" in df_seg.columns else None)
        fat = float(df_seg[fat_col_agg].sum()) if fat_col_agg else 0.0
        return int(len(df_seg)), fat

    crescimento = pd.concat([ensure_cols(rise_to_A, plan.columns), ensure_cols(opp_50_60, plan.columns)], ignore_index=True)
    crescimento = crescimento.drop_duplicates(subset=[c for c in ["MLB", "SKU", "# de anúncio", "Título"] if c in crescimento.columns])

    col1, col2 = st.columns(2)
    
    with col1:
        itens, fat = _front_agg(anchors)
        render_front_card("🛡️", "Defesa - Âncoras", "Proteja estoque e conversão", itens, fat, "defense", "ancoras.csv", anchors)
        
        itens, fat = _front_agg(drop_alert)
        render_front_card("⚠️", "Correção - Fuga de Receita", "Produtos que caíram", itens, fat, "correction", "fuga_de_receita.csv", drop_alert)

    with col2:
        itens, fat = _front_agg(crescimento)
        render_front_card("🚀", "Ataque - Crescimento", "Produtos em ascensão", itens, fat, "attack", "crescimento.csv", crescimento)
        
        itens, fat = _front_agg(inactivate)
        render_front_card("🧹", "Limpeza - Parados", "Produtos para cortar ou liquidar", itens, fat, "cleanup", "parados_inativar.csv", inactivate)

    section_footer()

# =========================
# TAB 2: Listas e Exportação (MELHORADA)
# =========================
with tab2:
    st.markdown(render_report_section("package", "Central de Exportação", "Baixe listas segmentadas para ação imediata", "blue"), unsafe_allow_html=True)
    


    # Função para adicionar planos de ação aos exports
    def enrich_df(base_df: pd.DataFrame) -> pd.DataFrame:
        result = base_df.copy()
        # Adicionar colunas de plano do dataframe plan
        plan_data = plan[["MLB", "Ação sugerida", "Plano 7 dias", "Plano 15 dias", "Plano 30 dias"]].drop_duplicates("MLB")
        result = result.merge(plan_data, on="MLB", how="left", suffixes=("", "_plan"))
        return result

    anchors_export = enrich_df(anchors.copy())
    inactivate_export = enrich_df(inactivate.copy())
    revitalize_export = enrich_df(revitalize.copy())
    opp_export = enrich_df(opp_50_60.copy())
    drop_export = enrich_df(drop_alert.copy())
    combo_export = enrich_df(dead_stock_combo.copy())

    # Colunas base + planos de ação
    plan_cols = ["Ação sugerida", "Plano 7 dias", "Plano 15 dias", "Plano 30 dias"]
    
    anchors_cols = ["MLB","Título","Fat total","Qtd total","TM total","Curva 0-30","Curva 31-60","Curva 61-90","Curva 91-120"] + plan_cols
    inactivate_cols = ["MLB","Título","Fat total","Qtd total","Curva 0-30","Qntd 0-30","Qntd 31-60","Qntd 61-90"] + plan_cols
    revitalize_cols = ["MLB","Título","Fat total","Qtd total","Curva 31-60","Curva 0-30","Qntd 31-60","Qntd 0-30"] + plan_cols
    opp_cols = ["MLB","Título","Fat total","Curva 0-30","Qntd 0-30","Curva 31-60","Qntd 31-60"] + plan_cols
    drop_cols = ["MLB","Título","Curva 31-60","Curva 61-90","Curva 0-30","Fat anterior ref","Fat. 0-30","Perda estimada"] + plan_cols
    combo_cols = ["MLB","Título","TM histórico","Fat. 31-60","Fat. 61-90","Fat. 91-120","Fat. 0-30"] + plan_cols

    anchors_export = ensure_cols(anchors_export, anchors_cols)
    inactivate_export = ensure_cols(inactivate_export, inactivate_cols)
    revitalize_export = ensure_cols(revitalize_export, revitalize_cols)
    opp_export = ensure_cols(opp_export, opp_cols)
    drop_export = ensure_cols(drop_export, drop_cols)
    combo_export = ensure_cols(combo_export, combo_cols)

    # Calcular faturamentos
    def get_fat(df_exp):
        if "Fat total" in df_exp.columns:
            return float(df_exp["Fat total"].sum())
        elif "Fat. 0-30" in df_exp.columns:
            return float(df_exp["Fat. 0-30"].sum())
        return 0.0

    # Grid de cards de exportação
    st.markdown('<div class="export-grid">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(render_export_card("🛡️", "Âncoras", "Produtos estáveis em curva A", len(anchors_export), get_fat(anchors_export), "defense"), unsafe_allow_html=True)
        st.download_button("📥 Baixar Excel", data=to_xlsx_bytes(anchors_export), file_name="ancoras.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_anc", use_container_width=True)
    
    with col2:
        st.markdown(render_export_card("⚠️", "Fuga de Receita", "Produtos que caíram de curva", len(drop_export), get_fat(drop_export), "correction"), unsafe_allow_html=True)
        st.download_button("📥 Baixar Excel", data=to_xlsx_bytes(drop_export), file_name="fuga_receita.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_drop", use_container_width=True)
    
    with col3:
        st.markdown(render_export_card("🚀", "Crescimento", "Produtos em ascensão", len(opp_export), get_fat(opp_export), "attack"), unsafe_allow_html=True)
        st.download_button("📥 Baixar Excel", data=to_xlsx_bytes(opp_export), file_name="crescimento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_opp", use_container_width=True)

    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.markdown(render_export_card("🧹", "Inativar", "Produtos sem giro", len(inactivate_export), get_fat(inactivate_export), "cleanup"), unsafe_allow_html=True)
        st.download_button("📥 Baixar Excel", data=to_xlsx_bytes(inactivate_export), file_name="inativar.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_ina", use_container_width=True)
    
    with col5:
        st.markdown(render_export_card("🔄", "Revitalizar", "Produtos para recuperar", len(revitalize_export), get_fat(revitalize_export), "opportunity"), unsafe_allow_html=True)
        st.download_button("📥 Baixar Excel", data=to_xlsx_bytes(revitalize_export), file_name="revitalizar.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_rev", use_container_width=True)
    
    with col6:
        st.markdown(render_export_card("🎁", "Combos/Liquidação", "Produtos para kits", len(combo_export), get_fat(combo_export), "combo"), unsafe_allow_html=True)
        st.download_button("📥 Baixar Excel", data=to_xlsx_bytes(combo_export), file_name="combos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_combo", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Preview expandido
    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
    
    with st.expander("PRÉVIA: FUGA DE RECEITA (TOP 20 POR PERDA ESTIMADA)", expanded=False):
        show = drop_export.head(20).copy()
        show["Fat anterior ref"] = show["Fat anterior ref"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        show["Fat. 0-30"] = show["Fat. 0-30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        show["Perda estimada"] = show["Perda estimada"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")

        st.dataframe(show, use_container_width=True, hide_index=True, height=450)

    with st.expander("PRÉVIA: ÂNCORAS (TOP 20 POR FATURAMENTO)", expanded=False):
        show = anchors_export.head(20).copy()
        show["Fat total"] = show["Fat total"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        show["TM total"] = show["TM total"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        st.dataframe(show, use_container_width=True, hide_index=True, height=450)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TAB 3: Plano Tático (MELHORADA v2)
# =========================
with tab3:
    st.markdown(render_report_section("layout", "Plano Tático por Produto", "Ações detalhadas para 15 e 30 dias", "purple"), unsafe_allow_html=True)

    # Contagem de frentes para exibir nos botões
    fronts = sorted(plan["Frente"].unique().tolist())
    all_front_counts = plan["Frente"].value_counts()
    
    # Container de filtros premium
    st.markdown(f"""
<div class="filter-container">
  <div class="filter-header">
    <div class="filter-header-left">
      <div class="filter-icon">🎯</div>
      <div>
        <div class="filter-main-title">🎯CENTRAL DE FILTROS</div>
        <div class="filter-subtitle">Refine sua análise por frente, faturamento e busca</div>
      </div>
    </div>
    <div class="filter-count">{len(plan)} produtos</div>
  </div>
</div>
    """, unsafe_allow_html=True)
    
    # Seleção de frentes com botões visuais
    st.markdown("**SELECIONE AS FRENTES:**")
    
    # Criar botões de frente com contagem
    front_cols = st.columns(5)
    front_icons = {"DEFESA": "🛡️", "CORREÇÃO": "⚠️", "ATAQUE": "🚀", "LIMPEZA": "🧹", "OTIMIZAÇÃO": "⚙️"}
    front_colors = {"DEFESA": "defense", "CORREÇÃO": "correction", "ATAQUE": "attack", "LIMPEZA": "cleanup", "OTIMIZAÇÃO": "optimization"}
    
    front_filter = []
    for i, frente in enumerate(["DEFESA", "CORREÇÃO", "ATAQUE", "LIMPEZA", "OTIMIZAÇÃO"]):
        with front_cols[i]:
            count = int(all_front_counts.get(frente, 0))
            icon = front_icons.get(frente, "")
            if st.checkbox(f"{icon} {frente} ({count})", value=True, key=f"front_{frente}"):
                front_filter.append(frente)
    
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    
    # Linha de filtros adicionais
    col1, col2, col3 = st.columns([1.5, 2, 1])
    
    with col1:
        st.markdown("**FATURAMENTO MÍNIMO:**")
        min_fat = st.number_input(
            "Fat. mínimo",
            min_value=0.0,
            value=0.0,
            step=100.0,
            label_visibility="collapsed",
            format="%.2f"
        )
    
    with col2:
        st.markdown("**BUSCAR PRODUTO:**")
        text_search = st.text_input(
            "Buscar",
            value="",
            label_visibility="collapsed",
            placeholder="Digite MLB ou nome do produto..."
        )
    
    with col3:
        st.markdown("**VISUALIZAÇÃO:**")
        view_mode = st.selectbox(
            "Modo",
            ["Cards", "Tabela"],
            label_visibility="collapsed"
        )

    # Aplicar filtros
    view = plan[plan["Frente"].isin(front_filter)].copy() if front_filter else plan.copy()
    view = view[view["Fat total"] >= float(min_fat)].copy()

    if text_search:
        text_search = text_search.strip().lower()
        view = view[
            view["MLB"].astype(str).str.lower().str.contains(text_search) |
            view["Título"].astype(str).str.lower().str.contains(text_search)
        ].copy()

    # Resumo das frentes filtradas
    front_counts = view["Frente"].value_counts()
    
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    
    # Métricas resumidas
    res_cols = st.columns(4)
    with res_cols[0]:
        st.metric("PRODUTOS FILTRADOS", f"{len(view):,}")
    with res_cols[1]:
        st.metric("FAT. TOTAL", br_money(view["Fat total"].sum()))
    with res_cols[2]:
        st.metric("QTD. TOTAL", f"{int(view['Qtd total'].sum()):,}")
    with res_cols[3]:
        avg_tm = view["TM total"].mean() if len(view) > 0 else 0
        st.metric("TM MÉDIO", br_money(avg_tm))
    
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    cols = [
        "MLB", "Título", "Frente",
        "Curva 31-60", "Curva 0-30",
        "Qntd 31-60", "Qntd 0-30",
        "Fat. 0-30", "Fat total", "TM total",
        "Ação sugerida", "Plano 7 dias", "Plano 15 dias", "Plano 30 dias"
    ]

    view_show = ensure_cols(view.sort_values("Fat total", ascending=False), cols)

    # Botão de download
    st.download_button(
        "📥 Baixar Excel do Plano Filtrado",
        data=to_xlsx_bytes(view_show),
        file_name="plano_tatico.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    if view_mode == "Cards":
        # Visualização em cards
        for idx, row in view_show.head(20).iterrows():
            st.markdown(render_tactical_card(row.to_dict(), row.get("Frente", "OTIMIZAÇÃO")), unsafe_allow_html=True)
        
        if len(view_show) > 20:
            st.info(f"Mostrando 20 de {len(view_show)} produtos. Use os filtros para refinar ou baixe o CSV completo.")
    else:
        # Visualização em tabela
        show = view_show.copy()
        show["Fat. 0-30"] = show["Fat. 0-30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        show["Fat total"] = show["Fat total"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
        show["TM total"] = show["TM total"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")

        st.dataframe(show, use_container_width=True, hide_index=True, height=600)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TAB 4: Relatório Estratégico (MELHORADA)
# =========================
with tab4:
    # Seção 1: Diagnóstico Macro
    st.markdown(render_report_section("search", "Diagnóstico Macro", "Visão geral da saúde do catálogo", "purple"), unsafe_allow_html=True)
    
    # KPIs destacados
    st.markdown(
        render_kpi_highlight([
            (br_int(total_ads), "Total de Anúncios", "purple"),
            (f"{round(float(conc_A_0_30 or 0.0) * 100, 1)}%", "Concentração Curva A", "green"),
            (br_money(tm_0_30), "Ticket Médio Atual", "amber"),
        ]),
        unsafe_allow_html=True
    )
    
    # Insight do ticket médio
    st.markdown(render_insight_card("📊", "Análise do Ticket Médio", tm_reading), unsafe_allow_html=True)
    
    # Distribuição de curvas
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Distribuição de Curvas (0-30)")
        st.dataframe(dist_0_30_df, use_container_width=True, hide_index=True, height=180)
    
    with col2:
        st.markdown("#### Evolução por Período")
        show_kpi = kpi_df.copy()
        show_kpi["Qtd"] = show_kpi["Qtd"].map(br_int)
        show_kpi["Faturamento"] = show_kpi["Faturamento"].map(br_money)
        show_kpi["Ticket médio"] = show_kpi["Ticket médio"].apply(lambda x: br_money(x) if pd.notna(x) else "-")
        st.dataframe(show_kpi, use_container_width=True, hide_index=True, height=180)

    st.markdown("</div>", unsafe_allow_html=True)

    # Seção 2: Segmentação
    st.markdown(render_report_section("package", "Segmentação de Produtos", "Análise por categoria estratégica", "blue"), unsafe_allow_html=True)
    
    # Resumo das frentes
    front_counts_all = plan["Frente"].value_counts()
    st.markdown(
        render_front_summary([
            ("🛡️", int(front_counts_all.get("DEFESA", 0)), "DEFESA"),
            ("⚠️", int(front_counts_all.get("CORREÇÃO", 0)), "CORREÇÃO"),
            ("🚀", int(front_counts_all.get("ATAQUE", 0)), "ATAQUE"),
            ("🧹", int(front_counts_all.get("LIMPEZA", 0)), "LIMPEZA"),
            ("⚙️", int(front_counts_all.get("OTIMIZAÇÃO", 0)), "OTIMIZAÇÃO"),
        ]),
        unsafe_allow_html=True
    )

    # Âncoras
    st.markdown("#### 🛡️ Produtos Âncora (Top 5)")
    top5_anchors = anchors.head(5).copy()
    fat_sum_top5 = float(top5_anchors["Fat total"].sum()) if len(top5_anchors) else 0.0
    
    st.markdown(
        render_kpi_highlight([
            (br_int(len(anchors)), "Total de Âncoras", "green"),
            (br_money(fat_sum_top5), "Fat. Top 5", "blue"),
            (f"{round(len(anchors)/max(total_ads,1)*100, 1)}%", "% do Catálogo", "purple"),
        ]),
        unsafe_allow_html=True
    )

    anchor_cols = ["MLB","Título","Fat total","Qtd total","TM total"]
    show = ensure_cols(top5_anchors, anchor_cols)
    show["Fat total"] = show["Fat total"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
    show["Qtd total"] = show["Qtd total"].map(br_int)
    show["TM total"] = show["TM total"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
    st.dataframe(show, use_container_width=True, hide_index=True, height=220)

    # Fuga de receita
    st.markdown("#### ⚠️ Alerta de Fuga de Receita (Top 10)")
    loss_total = float(drop_alert["Perda estimada"].sum()) if len(drop_alert) else 0.0
    
    st.markdown(
        render_kpi_highlight([
            (br_int(len(drop_alert)), "Produtos em Fuga", "rose"),
            (br_money(loss_total), "Perda Estimada", "amber"),
            (f"{round(len(drop_alert)/max(total_ads,1)*100, 1)}%", "% do Catálogo", "purple"),
        ]),
        unsafe_allow_html=True
    )

    if len(drop_alert) > 0:
        st.markdown(
            render_insight_card("⚠️", "Atenção Imediata", 
                f"Você tem {len(drop_alert)} produtos que caíram de curva, representando uma perda estimada de {br_money(loss_total)}. Priorize a correção destes itens."),
            unsafe_allow_html=True
        )

    drop_cols_show = ["MLB","Título","Curva 31-60","Curva 0-30","Perda estimada"]
    show = ensure_cols(drop_alert.head(10), drop_cols_show)
    show["Perda estimada"] = show["Perda estimada"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
    st.dataframe(show, use_container_width=True, hide_index=True, height=350)

    st.markdown("</div>", unsafe_allow_html=True)

    # Seção 3: Plano Operacional
    st.markdown(render_report_section("layout", "Plano Operacional", "Distribuição de ações por frente", "green"), unsafe_allow_html=True)

    front_order = ["LIMPEZA", "CORREÇÃO", "ATAQUE", "DEFESA", "OTIMIZAÇÃO"]
    
    # Download do plano completo
    op_cols = ["Frente","MLB","Título","Curva 0-30","Fat. 0-30","Ação sugerida","Plano 7 dias","Plano 15 dias","Plano 30 dias"]
    op = ensure_cols(plan, op_cols).copy()
    op = op.sort_values(["Frente", "Fat. 0-30"], ascending=[True, False])

    st.download_button(
        "📥 Baixar Plano Operacional Completo",
        data=to_xlsx_bytes(op),
        file_name="plano_operacional_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # Tabelas por frente
    for fr in front_order:
        subset = op[op["Frente"] == fr].head(10).copy()
        if len(subset) == 0:
            continue
        
        icon = {"LIMPEZA": "🧹", "CORREÇÃO": "⚠️", "ATAQUE": "🚀", "DEFESA": "🛡️", "OTIMIZAÇÃO": "⚙️"}.get(fr, "📦")
        
        with st.expander(f"{icon} {fr} ({len(op[op['Frente'] == fr])} itens)", expanded=False):
            subset["Fat. 0-30"] = subset["Fat. 0-30"].apply(lambda x: br_money(float(x)) if pd.notna(x) else "-")
            st.dataframe(subset, use_container_width=True, hide_index=True, height=350)

    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; opacity: 0.5; font-size: 0.85rem; padding: 20px 0;">
        📊 Curva ABC Dashboard v4.3 | Análise inteligente para decisões rápidas
    </div>
    """,
    unsafe_allow_html=True
)
