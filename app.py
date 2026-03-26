
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime
import re

st.set_page_config(
    page_title="Painel Financeiro Mercado Livre",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== TEMA E ESTILOS PROFISSIONAIS ==========
st.markdown("""
    <style>
    /* Variáveis de cor */
    :root {
        --primary: #2c3e50;
        --secondary: #3498db;
        --success: #27ae60;
        --warning: #f39c12;
        --danger: #e74c3c;
        --light-bg: #ecf0f1;
        --card-bg: #ffffff;
        --text-dark: #2c3e50;
        --text-light: #7f8c8d;
        --border-color: #bdc3c7;
    }

    /* Tema geral */
    * {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    body {
        background-color: #f5f7fa;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #ecf0f1;
    }

    /* Títulos */
    h1 {
        color: #2c3e50;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 5px;
    }

    h2 {
        color: #2c3e50;
        font-weight: 600;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        margin-top: 30px;
        margin-bottom: 20px;
    }

    h3 {
        color: #34495e;
        font-weight: 600;
    }

    /* Captions e textos auxiliares */
    .stCaption {
        color: #7f8c8d;
        font-size: 14px;
    }

    /* Cards customizados - Liquid Glass Style */
    .metric-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #95a5a6;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.95);
    }

    .metric-card.primary {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-left: 4px solid #3498db;
        color: #2c3e50;
    }

    .metric-card.success {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-left: 4px solid #27ae60;
        color: #2c3e50;
    }

    .metric-card.warning {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-left: 4px solid #f39c12;
        color: #2c3e50;
    }

    .metric-card.danger {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-left: 4px solid #e74c3c;
        color: #2c3e50;
    }

    .metric-card.light {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-left: 4px solid #95a5a6;
        color: #2c3e50;
    }

    /* Upload area */
    .upload-container {
        background: linear-gradient(135deg, #ecf0f1 0%, #f5f7fa 100%);
        border: 2px dashed #3498db;
        border-radius: 12px;
        padding: 30px;
        text-align: center;
        margin: 20px 0;
    }

    .upload-header {
        color: #2c3e50;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .upload-subtitle {
        color: #7f8c8d;
        font-size: 14px;
    }

    /* Botões */
    .stButton > button {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #2980b9;
        box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
    }

    /* Filtros */
    .stMultiSelect, .stSelectbox, .stDateInput {
        border-radius: 8px;
    }

    /* Tabela */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Info/Warning/Error boxes */
    .stInfo {
        background-color: #d1ecf1;
        border-left: 4px solid #0c5460;
        border-radius: 8px;
    }

    .stWarning {
        background-color: #fff3cd;
        border-left: 4px solid #856404;
        border-radius: 8px;
    }

    .stSuccess {
        background-color: #d4edda;
        border-left: 4px solid #155724;
        border-radius: 8px;
    }

    .stError {
        background-color: #f8d7da;
        border-left: 4px solid #721c24;
        border-radius: 8px;
    }

    /* Dividers */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #bdc3c7, transparent);
        margin: 30px 0;
    }

    /* Sidebar header */
    [data-testid="stSidebar"] h2 {
        color: #ecf0f1;
        border-bottom-color: #3498db;
    }

    [data-testid="stSidebar"] h3 {
        color: #bdc3c7;
    }

    </style>
    """, unsafe_allow_html=True)

PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

EXPECTED_COLUMNS = [
    "N.º de venda", "Data da venda", "Estado", "Descrição do status",
    "Receita por produtos (BRL)", "Receita por envio (BRL)",
    "Tarifa de venda e impostos (BRL)", "Tarifas de envio (BRL)",
    "Cancelamentos e reembolsos (BRL)", "Total (BRL)",
]


def brl(value: float) -> str:
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def pct(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def normalize_text(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


def parse_brazilian_datetime(value):
    if pd.isna(value) or isinstance(value, pd.Timestamp):
        return value if isinstance(value, pd.Timestamp) else pd.NaT
    text = str(value).strip().replace(" hs.", "").replace(" hs", "")
    for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return pd.to_datetime(datetime.strptime(text, fmt))
        except:
            pass
    match = re.match(r"(\d{1,2}) de ([^ ]+) de (\d{4})(?: (\d{1,2}):(\d{2}))?$", text.lower())
    if match:
        month = PT_MONTHS.get(match.group(2))
        if month:
            return pd.Timestamp(year=int(match.group(3)), month=month, day=int(match.group(1)),
                              hour=int(match.group(4) or 0), minute=int(match.group(5) or 0))
    return pd.NaT


@st.cache_data(show_spinner=False)
def load_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    df = pd.read_excel(uploaded_file, sheet_name=xls.sheet_names[0], header=5)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(normalize_text)
    
    numeric_cols = [
        "Receita por produtos (BRL)", "Receita por acréscimo no preço (pago pelo comprador)",
        "Taxa de parcelamento equivalente ao acréscimo", "Tarifa de venda e impostos (BRL)",
        "Receita por envio (BRL)", "Tarifas de envio (BRL)", "Cancelamentos e reembolsos (BRL)",
        "Total (BRL)", "Unidades", "Preço unitário de venda do anúncio (BRL)",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["data_venda_dt"] = df["Data da venda"].apply(parse_brazilian_datetime) if "Data da venda" in df.columns else pd.NaT
    df["Estado"] = df.get("Estado", "")
    df["Descrição do status"] = df.get("Descrição do status", "")

    status_mix = (df["Estado"].fillna("") + " " + df["Descrição do status"].fillna("")).str.lower()
    df["is_cancelled"] = status_mix.str.contains("cancel|reembolso|devolu|estornado|devolvido|devolvida|reembolsado|reembolsada", regex=True, na=False) | (df.get("Cancelamentos e reembolsos (BRL)", 0).abs() > 0)
    df["is_sent"] = status_mix.str.contains("entreg|a caminho|coleta|pronta para emitir|imprimir a etiqueta|envio|em trânsito|transito", regex=True)
    df["repasse_base"] = df.get("Total (BRL)", pd.Series(0, index=df.index)).fillna(0)

    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    faturamento_total = df.get("Receita por produtos (BRL)", pd.Series(dtype=float)).sum()
    frete_pago_cliente = df.get("Receita por envio (BRL)", pd.Series(dtype=float)).sum()
    cancelamentos = df.get("Cancelamentos e reembolsos (BRL)", pd.Series(dtype=float)).abs().sum()
    comissao = df.get("Tarifa de venda e impostos (BRL)", pd.Series(dtype=float)).abs().sum()
    frete_cobrado = df.get("Tarifas de envio (BRL)", pd.Series(dtype=float)).abs().sum()
    
    faturamento_liquido = faturamento_total + frete_pago_cliente - cancelamentos - comissao - frete_cobrado
    nao_cancelados = ~df.get("is_cancelled", pd.Series(False, index=df.index))
    repasse_previsto = df.loc[nao_cancelados, "repasse_base"].sum() if "repasse_base" in df.columns else 0
    repaid_total = max(0, repasse_previsto - faturamento_liquido)
    base_bruta_com_frete = faturamento_total + frete_pago_cliente

    return {
        "faturamento_total": float(faturamento_total),
        "frete_pago_cliente": float(frete_pago_cliente),
        "cancelamentos": float(cancelamentos),
        "comissao": float(comissao),
        "frete_cobrado": float(frete_cobrado),
        "repaid_total": float(repaid_total),
        "faturamento_liquido": float(faturamento_liquido),
        "pedidos_enviados": int(df["is_sent"].sum()) if "is_sent" in df.columns else 0,
        "repasse_previsto": float(repasse_previsto),
        "cancel_pct": float(cancelamentos / faturamento_total) if faturamento_total else 0,
        "comissao_pct": float(comissao / faturamento_total) if faturamento_total else 0,
        "base_bruta_com_frete": float(base_bruta_com_frete),
    }


def dataframe_for_download(df):
    export_cols = [c for c in [
        "N.º de venda", "Data da venda", "Estado", "Descrição do status", "Título do anúncio",
        "Canal de venda", "Forma de entrega", "Receita por produtos (BRL)",
        "Receita por envio (BRL)", "Cancelamentos e reembolsos (BRL)",
        "Tarifa de venda e impostos (BRL)", "Tarifas de envio (BRL)",
        "Total (BRL)", "repasse_base", "is_cancelled", "is_sent"
    ] if c in df.columns]
    return df[export_cols].copy()


def analyze_product_profitability(df):
    """Analisa lucratividade por produto"""
    if "Título do anúncio" not in df.columns:
        return pd.DataFrame()
    
    product_analysis = df.groupby("Título do anúncio").agg({
        "Receita por produtos (BRL)": "sum",
        "Receita por envio (BRL)": "sum",
        "Cancelamentos e reembolsos (BRL)": lambda x: x.abs().sum(),
        "Tarifa de venda e impostos (BRL)": lambda x: x.abs().sum(),
        "Tarifas de envio (BRL)": lambda x: x.abs().sum(),
        "N.º de venda": "count",
    }).reset_index()
    
    product_analysis.columns = ["Produto", "Faturamento", "Frete Cliente", "Cancelamentos", "Comissão", "Frete Cobrado", "Vendas"]
    product_analysis["Líquido"] = (product_analysis["Faturamento"] + product_analysis["Frete Cliente"] - 
                                     product_analysis["Cancelamentos"] - product_analysis["Comissão"] - 
                                     product_analysis["Frete Cobrado"])
    product_analysis["Margem %"] = (product_analysis["Líquido"] / (product_analysis["Faturamento"] + product_analysis["Frete Cliente"])) * 100
    
    return product_analysis.sort_values("Líquido", ascending=False)


def build_temporal_chart(df):
    """Constrói gráfico de tendência temporal"""
    if "data_venda_dt" not in df.columns or df["data_venda_dt"].isna().all():
        return None
    
    daily_data = df.groupby(df["data_venda_dt"].dt.date).agg({
        "Receita por produtos (BRL)": "sum",
        "Receita por envio (BRL)": "sum",
        "Cancelamentos e reembolsos (BRL)": lambda x: x.abs().sum(),
        "Tarifa de venda e impostos (BRL)": lambda x: x.abs().sum(),
        "Tarifas de envio (BRL)": lambda x: x.abs().sum(),
    }).reset_index()
    
    daily_data.columns = ["Data", "Faturamento", "Frete Cliente", "Cancelamentos", "Comissão", "Frete Cobrado"]
    daily_data["Líquido"] = (daily_data["Faturamento"] + daily_data["Frete Cliente"] - 
                              daily_data["Cancelamentos"] - daily_data["Comissão"] - daily_data["Frete Cobrado"])
    daily_data["Repasse"] = daily_data["Líquido"]  # Simplificado para visualização
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_data["Data"], y=daily_data["Faturamento"], mode="lines+markers", name="Faturamento", line=dict(color="#3498db", width=2)))
    fig.add_trace(go.Scatter(x=daily_data["Data"], y=daily_data["Líquido"], mode="lines+markers", name="Faturamento Líquido", line=dict(color="#27ae60", width=2)))
    fig.add_trace(go.Scatter(x=daily_data["Data"], y=daily_data["Comissão"], mode="lines+markers", name="Comissão", line=dict(color="#e74c3c", width=2)))
    
    fig.update_layout(
        title="Tendência de Faturamento e Custos",
        xaxis_title="Data",
        yaxis_title="Valor (R$)",
        font=dict(family="Segoe UI, sans-serif", size=12, color="#2c3e50"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#ecf0f1", zeroline=False),
        hovermode="x unified",
        height=400,
    )
    
    return fig


def build_charts(metrics):
    # Gráfico de Pizza - Composição
    composicao_df = pd.DataFrame({
        "Categoria": ["Faturamento Líquido", "Frete Cliente", "Cancelamentos", "Comissão", "Frete Cobrado", "Repaid"],
        "Valor": [
            max(metrics["faturamento_liquido"], 0),
            metrics["frete_pago_cliente"],
            metrics["cancelamentos"],
            metrics["comissao"],
            metrics["frete_cobrado"],
            metrics["repaid_total"]
        ],
    })
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=composicao_df["Categoria"],
        values=composicao_df["Valor"],
        hole=0.4,
        marker=dict(colors=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']),
        textposition='inside',
        textinfo='label+percent'
    )])
    fig_donut.update_layout(
        font=dict(family="Segoe UI, sans-serif", size=12, color="#2c3e50"),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=400
    )

    # Gráfico de Barras - Comparativo
    comparativo_df = pd.DataFrame({
        "Indicador": ["Faturamento Total", "Base com Frete", "Repasse Previsto", "Faturamento Líquido"],
        "Valor": [
            metrics["faturamento_total"],
            metrics["base_bruta_com_frete"],
            metrics["repasse_previsto"],
            metrics["faturamento_liquido"],
        ],
    })
    
    fig_bar = go.Figure(data=[go.Bar(
        x=comparativo_df["Indicador"],
        y=comparativo_df["Valor"],
        marker=dict(color=['#3498db', '#2980b9', '#27ae60', '#2ecc71']),
        text=[f'R$ {v/1000:.1f}k' for v in comparativo_df["Valor"]],
        textposition='outside',
    )])
    fig_bar.update_layout(
        font=dict(family="Segoe UI, sans-serif", size=12, color="#2c3e50"),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#ecf0f1', zeroline=False),
        margin=dict(l=0, r=0, t=0, b=0),
        height=400,
        showlegend=False
    )

    return fig_donut, fig_bar


def render_metric_card(col, icon, title, value, description, card_type="light", percentage=None, percentage_color=None):
    """Renderiza um card de métrica profissional com porcentagem opcional"""
    with col:
        percentage_html = ""
        if percentage is not None:
            color = percentage_color if percentage_color else "#7f8c8d"
            percentage_html = f'<div style="font-size: 14px; color: {color}; margin-top: 6px; font-weight: 700;">{percentage}</div>'
        
        st.markdown(
            f"""
            <div class="metric-card {card_type}">
                <div style="display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 15px;">
                    <div style="font-size: 28px;">{icon}</div>
                </div>
                <div style="font-size: 13px; opacity: 0.8; margin-bottom: 8px; font-weight: 500;">{title}</div>
                <div style="font-size: 28px; font-weight: 700; margin-bottom: 8px;">{value}</div>
                {percentage_html}
                <div style="font-size: 12px; opacity: 0.7; margin-top: 8px;">{description}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ========== HEADER ==========
st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="margin: 0; font-size: 32px;">Painel Financeiro Mercado Livre</h1>
        <p style="color: #7f8c8d; margin-top: 5px; font-size: 16px;">Análise detalhada de vendas, custos e rentabilidade</p>
    </div>
    """, unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### Lógica de Cálculo")
    st.markdown(
        """
        **1. Faturamento Total**  
        Soma da coluna `Receita por produtos (BRL)`.

        **2. Frete Pago pelo Cliente**  
        Soma de `Receita por envio (BRL)`.

        **3. Vendas Canceladas**  
        Soma de `Cancelamentos e reembolsos (BRL)`.

        **4. Comissão Total**  
        Soma de `Tarifa de venda e impostos (BRL)`.

        **5. Frete Cobrado Total**  
        Soma de `Tarifas de envio (BRL)`.

        **6. Faturamento Líquido**  
        `Faturamento` + `Frete Cliente` - `Cancelamentos` - `Comissão` - `Frete Cobrado`.

        **7. Repasse Previsto**  
        Soma de `Total (BRL)` para pedidos não cancelados.

        **8. Repaid / Benefícios**  
        `Repasse Previsto` - `Faturamento Líquido`.
        """
    )
    st.divider()
    st.info("O Repaid captura automaticamente bônus de campanhas (CPC) ou ajustes do Mercado Livre.")

# ========== UPLOAD ==========
st.markdown('<div class="upload-container"><div class="upload-header">Importar Relatório</div><div class="upload-subtitle">Arraste ou selecione o arquivo .xlsx exportado do Mercado Livre</div></div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")

if uploaded_file is None:
    st.info("Aguardando upload da planilha para gerar o painel de análise...")
    st.stop()

try:
    raw_df = load_excel(uploaded_file)
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in raw_df.columns]
    df = clean_dataframe(raw_df)
    metrics = compute_metrics(df)
except Exception as exc:
    st.error("Não foi possível ler o arquivo. Verifique se ele está no padrão exportado pelo Mercado Livre.")
    st.exception(exc)
    st.stop()

if missing_cols:
    st.warning(f"Colunas não encontradas: {', '.join(missing_cols)}")

# ========== SEÇÃO 1: RECEITAS ==========
st.markdown("### Receitas")
col1, col2, col3, col4 = st.columns(4, gap="small")
fat_total_pct = (metrics["faturamento_total"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0
frete_pct = (metrics["frete_pago_cliente"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0
liquido_pct = (metrics["faturamento_liquido"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0

render_metric_card(col1, "₹", "Faturamento Total", brl(metrics["faturamento_total"]), "Receita de produtos", "primary", f"{fat_total_pct:.1f}% da base bruta", "#27ae60")
render_metric_card(col2, "→", "Frete Pago pelo Cliente", brl(metrics["frete_pago_cliente"]), "Receita de envio", "success", f"{frete_pct:.1f}% da base bruta", "#27ae60")
render_metric_card(col3, "◆", "Base Bruta", brl(metrics["base_bruta_com_frete"]), "Total com frete", "light", "100% base", "#3498db")
render_metric_card(col4, "✓", "Faturamento Líquido", brl(metrics["faturamento_liquido"]), "Resultado operacional", "primary", f"{liquido_pct:.1f}% da base bruta", "#27ae60")

# ========== SEÇÃO 2: CUSTOS ==========
st.markdown("### Custos e Deduções")
col5, col6, col7, col8 = st.columns(4, gap="small")
cancel_pct = (metrics["cancelamentos"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0
comissao_pct = (metrics["comissao"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0
frete_cobrado_pct = (metrics["frete_cobrado"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0
repaid_pct = (metrics["repaid_total"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0

render_metric_card(col5, "✕", "Vendas Canceladas", brl(metrics["cancelamentos"]), "Cancelamentos e reembolsos", "danger", f"{cancel_pct:.1f}% da base bruta", "#e74c3c")
render_metric_card(col6, "◆", "Comissão Total", brl(metrics["comissao"]), "Tarifa de venda e impostos", "warning", f"{comissao_pct:.1f}% da base bruta", "#e74c3c")
render_metric_card(col7, "→", "Frete Cobrado", brl(metrics["frete_cobrado"]), "Tarifas de envio", "warning", f"{frete_cobrado_pct:.1f}% da base bruta", "#e74c3c")
render_metric_card(col8, "⬆", "Repaid / Benefícios", brl(metrics["repaid_total"]), "Bônus de campanhas", "success", f"{repaid_pct:.1f}% da base bruta", "#27ae60")

# ========== SEÇÃO 3: RESULTADO FINAL ==========
st.markdown("### Resultado Final")
col_result1, col_result2 = st.columns(2, gap="large")
repasse_pct = (metrics["repasse_previsto"] / metrics["base_bruta_com_frete"] * 100) if metrics["base_bruta_com_frete"] > 0 else 0

with col_result1:
    render_metric_card(st.columns(1)[0], "◆", "Repasse Previsto", brl(metrics["repasse_previsto"]), "Valor final a receber", "primary", f"{repasse_pct:.1f}% da base bruta", "#27ae60")
with col_result2:
    render_metric_card(st.columns(1)[0], "↑", "Pedidos Enviados", str(metrics["pedidos_enviados"]), "Total de pedidos", "light")

# ========== SEÇÃO 4: INDICADORES ==========
st.markdown("### Indicadores de Performance")
ind_col1, ind_col2 = st.columns(2, gap="large")
with ind_col1:
    render_metric_card(st.columns(1)[0], "↓", "% Cancelamento", pct(metrics["cancel_pct"]), "Sobre faturamento total", "light")
with ind_col2:
    render_metric_card(st.columns(1)[0], "◆", "Peso da Comissão", pct(metrics["comissao_pct"]), "Sobre faturamento total", "light")

# ========== GRÁFICOS ==========
st.markdown("### Análise Visual")
fig_donut, fig_bar = build_charts(metrics)
chart_col1, chart_col2 = st.columns(2, gap="large")
with chart_col1:
    st.markdown("#### Composição Financeira")
    st.plotly_chart(fig_donut, use_container_width=True)
with chart_col2:
    st.markdown("#### Comparativo de Valores")
    st.plotly_chart(fig_bar, use_container_width=True)

# ========== INSIGHTS ==========
st.markdown("### Insights Automáticos")
insight_col1, insight_col2, insight_col3 = st.columns(3, gap="medium")
with insight_col1:
    st.success(f"Cancelamentos: {pct(metrics['cancel_pct'])} do faturamento")
with insight_col2:
    st.info(f"Comissão: {pct(metrics['comissao_pct'])} do faturamento")
with insight_col3:
    if metrics["repaid_total"] > 0:
        st.success(f"Benefícios extras: {brl(metrics['repaid_total'])}")
    else:
        st.warning("Nenhum benefício extra detectado")

# ========== FILTROS ==========
st.markdown("### Filtros e Análise Detalhada")
f1, f2, f3 = st.columns(3, gap="medium")

with f1:
    status_options = sorted([s for s in df["Estado"].dropna().unique().tolist() if str(s).strip()])
    selected_status = st.multiselect("Status", status_options, help="Filtrar por status de venda")

with f2:
    canal_options = sorted([s for s in df.get("Canal de venda", pd.Series(dtype=str)).dropna().unique().tolist() if str(s).strip()])
    selected_canais = st.multiselect("Canal de Venda", canal_options, help="Filtrar por canal")

with f3:
    if df["data_venda_dt"].notna().any():
        min_date = df["data_venda_dt"].min().date()
        max_date = df["data_venda_dt"].max().date()
        selected_period = st.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        selected_period = None

filtered_df = df.copy()

if selected_period and isinstance(selected_period, tuple) and len(selected_period) == 2:
    start_date, end_date = selected_period
    filtered_df = filtered_df[filtered_df["data_venda_dt"].dt.date.between(start_date, end_date, inclusive="both")]

if selected_status:
    filtered_df = filtered_df[filtered_df["Estado"].isin(selected_status)]

if selected_canais and "Canal de venda" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Canal de venda"].isin(selected_canais)]

# ========== ANÁLISE DE LUCRATIVIDADE POR PRODUTO ==========
st.markdown("### Análise de Lucratividade por Produto")
product_profitability = analyze_product_profitability(filtered_df)

if not product_profitability.empty:
    # Gráfico de barras
    fig_products = go.Figure(data=[
        go.Bar(
            x=product_profitability["Produto"][:10],  # Top 10
            y=product_profitability["Líquido"][:10],
            marker=dict(color=product_profitability["Margem %"][:10], colorscale="RdYlGn", showscale=True, colorbar=dict(title="Margem %")),
            text=[f"R$ {v:.2f}" for v in product_profitability["Líquido"][:10]],
            textposition="outside",
        )
    ])
    fig_products.update_layout(
        title="Top 10 Produtos por Faturamento Líquido",
        xaxis_title="Produto",
        yaxis_title="Faturamento Líquido (R$)",
        font=dict(family="Segoe UI, sans-serif", size=11, color="#2c3e50"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor="#ecf0f1", zeroline=False),
        height=400,
        margin=dict(b=100),
    )
    st.plotly_chart(fig_products, use_container_width=True)
    
    # Tabela de detalhes
    st.markdown("#### Detalhes de Lucratividade")
    product_display = product_profitability[["Produto", "Faturamento", "Frete Cliente", "Comissão", "Frete Cobrado", "Líquido", "Margem %", "Vendas"]].copy()
    product_display["Faturamento"] = product_display["Faturamento"].apply(brl)
    product_display["Frete Cliente"] = product_display["Frete Cliente"].apply(brl)
    product_display["Comissão"] = product_display["Comissão"].apply(brl)
    product_display["Frete Cobrado"] = product_display["Frete Cobrado"].apply(brl)
    product_display["Líquido"] = product_display["Líquido"].apply(brl)
    product_display["Margem %"] = product_display["Margem %"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(product_display, use_container_width=True, height=300)
else:
    st.info("Sem dados de produtos para análise.")

# ========== GRÁFICO DE TENDÊNCIA TEMPORAL ==========
st.markdown("### Tendência Temporal")
temporal_chart = build_temporal_chart(filtered_df)
if temporal_chart:
    st.plotly_chart(temporal_chart, use_container_width=True)
else:
    st.info("Sem dados temporais para análise. Verifique se as datas estão corretas no relatório.")

# ========== TABELA ==========
st.markdown("### Detalhamento de Pedidos")
download_df = dataframe_for_download(filtered_df)
st.dataframe(download_df, use_container_width=True, height=420)

# ========== DOWNLOADS ==========
st.markdown("### Exportar Dados")
col_csv, col_txt = st.columns(2, gap="medium")

with col_csv:
    csv_data = download_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar CSV",
        data=csv_data,
        file_name="pedidos_filtrados_mercado_livre.csv",
        mime="text/csv",
    )

with col_txt:
    summary_text = f"""
PAINEL FINANCEIRO MERCADO LIVRE
{'='*50}

RECEITAS:
  Faturamento Total: {brl(metrics['faturamento_total'])}
  Frete Pago pelo Cliente: {brl(metrics['frete_pago_cliente'])}
  Base Bruta: {brl(metrics['base_bruta_com_frete'])}

CUSTOS:
  Cancelamentos: {brl(metrics['cancelamentos'])}
  Comissão: {brl(metrics['comissao'])}
  Frete Cobrado: {brl(metrics['frete_cobrado'])}

RESULTADO:
  Faturamento Líquido: {brl(metrics['faturamento_liquido'])}
  Repaid/Benefícios: {brl(metrics['repaid_total'])}
  Repasse Previsto: {brl(metrics['repasse_previsto'])}

INDICADORES:
  % Cancelamento: {pct(metrics['cancel_pct'])}
  Peso da Comissão: {pct(metrics['comissao_pct'])}
  Pedidos Enviados: {metrics['pedidos_enviados']}
    """.strip()
    
    st.download_button(
        "Baixar Resumo TXT",
        data=summary_text.encode("utf-8"),
        file_name="resumo_financeiro_mercado_livre.txt",
        mime="text/plain",
    )
