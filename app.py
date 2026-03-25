
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime
import re

st.set_page_config(
    page_title="Painel Financeiro Mercado Livre",
    page_icon="💰",
    layout="wide",
)

PT_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

EXPECTED_COLUMNS = [
    "N.º de venda",
    "Data da venda",
    "Estado",
    "Descrição do status",
    "Receita por produtos (BRL)",
    "Receita por envio (BRL)",
    "Tarifa de venda e impostos (BRL)",
    "Tarifas de envio (BRL)",
    "Cancelamentos e reembolsos (BRL)",
    "Total (BRL)",
]


def brl(value: float) -> str:
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def pct(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_brazilian_datetime(value):
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value

    text = str(value).strip().replace(" hs.", "").replace(" hs", "")
    for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return pd.to_datetime(datetime.strptime(text, fmt))
        except Exception:
            pass

    match = re.match(r"(\d{1,2}) de ([^ ]+) de (\d{4})(?: (\d{1,2}):(\d{2}))?$", text.lower())
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        hour = int(match.group(4) or 0)
        minute = int(match.group(5) or 0)
        month = PT_MONTHS.get(month_name)
        if month:
            return pd.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute)
    return pd.NaT


@st.cache_data(show_spinner=False)
def load_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    target_sheet = xls.sheet_names[0]
    df = pd.read_excel(uploaded_file, sheet_name=target_sheet, header=5)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(normalize_text)

    numeric_cols = [
        "Receita por produtos (BRL)",
        "Receita por acréscimo no preço (pago pelo comprador)",
        "Taxa de parcelamento equivalente ao acréscimo",
        "Tarifa de venda e impostos (BRL)",
        "Receita por envio (BRL)",
        "Tarifas de envio (BRL)",
        "Cancelamentos e reembolsos (BRL)",
        "Total (BRL)",
        "Unidades",
        "Preço unitário de venda do anúncio (BRL)",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Data da venda" in df.columns:
        df["data_venda_dt"] = df["Data da venda"].apply(parse_brazilian_datetime)
    else:
        df["data_venda_dt"] = pd.NaT

    if "Estado" not in df.columns:
        df["Estado"] = ""
    if "Descrição do status" not in df.columns:
        df["Descrição do status"] = ""

    status_mix = (df["Estado"].fillna("") + " " + df["Descrição do status"].fillna("")).str.lower()

    df["is_cancelled"] = status_mix.str.contains(
        "cancel|reembolso|devolu|estornado|devolvido|devolvida|reembolsado|reembolsada",
        regex=True,
        na=False,
    ) | (df.get("Cancelamentos e reembolsos (BRL)", 0).abs() > 0)

    df["is_sent"] = status_mix.str.contains(
        "entreg|a caminho|coleta|pronta para emitir|imprimir a etiqueta|envio|em trânsito|transito",
        regex=True,
    )

    # Lógica de cálculo conforme o usuário explicou
    receita_produtos = df.get("Receita por produtos (BRL)", pd.Series(0, index=df.index)).fillna(0)
    receita_acrescimo = df.get("Receita por acréscimo no preço (pago pelo comprador)", pd.Series(0, index=df.index)).fillna(0)
    taxa_parcelamento = df.get("Taxa de parcelamento equivalente ao acréscimo", pd.Series(0, index=df.index)).fillna(0)
    comissao = df.get("Tarifa de venda e impostos (BRL)", pd.Series(0, index=df.index)).fillna(0)
    tarifas_envio = df.get("Tarifas de envio (BRL)", pd.Series(0, index=df.index)).fillna(0)
    cancelamentos = df.get("Cancelamentos e reembolsos (BRL)", pd.Series(0, index=df.index)).fillna(0)
    total_reportado = df.get("Total (BRL)", pd.Series(0, index=df.index)).fillna(0)

    # Cálculo base (sem benefícios/repaid)
    # Nota: comissao, tarifas_envio e cancelamentos costumam vir negativos no relatório, por isso somamos
    df["calculo_base"] = receita_produtos + receita_acrescimo - taxa_parcelamento + comissao + tarifas_envio + cancelamentos
    
    # O Repaid é a diferença positiva entre o que o ML reportou e o nosso cálculo base
    # Ajuste: arredondar para evitar erros de precisão de ponto flutuante
    df["repaid_beneficio"] = (total_reportado - df["calculo_base"]).round(2).clip(lower=0)
    
    # Repasse base é o total reportado
    df["repasse_base"] = total_reportado

    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    faturamento_total = df.get("Receita por produtos (BRL)", pd.Series(dtype=float)).sum()
    frete_pago_cliente = df.get("Receita por envio (BRL)", pd.Series(dtype=float)).sum()
    cancelamentos = df.get("Cancelamentos e reembolsos (BRL)", pd.Series(dtype=float)).abs().sum()
    comissao = df.get("Tarifa de venda e impostos (BRL)", pd.Series(dtype=float)).abs().sum()
    frete_cobrado = df.get("Tarifas de envio (BRL)", pd.Series(dtype=float)).abs().sum()
    repaid_total = df.get("repaid_beneficio", pd.Series(0, index=df.index)).sum()
    
    pedidos_enviados = int(df["is_sent"].sum()) if "is_sent" in df.columns else 0

    # Faturamento líquido agora inclui o benefício/repaid
    # Lógica: Faturamento Total - Taxas + Repaid
    faturamento_liquido = faturamento_total - cancelamentos - comissao - frete_cobrado + repaid_total

    nao_cancelados = ~df.get("is_cancelled", pd.Series(False, index=df.index))
    repasse_previsto = df.loc[nao_cancelados, "repasse_base"].sum() if "repasse_base" in df.columns else 0

    base_bruta_com_frete = faturamento_total + frete_pago_cliente

    return {
        "faturamento_total": float(faturamento_total),
        "frete_pago_cliente": float(frete_pago_cliente),
        "cancelamentos": float(cancelamentos),
        "comissao": float(comissao),
        "frete_cobrado": float(frete_cobrado),
        "repaid_total": float(repaid_total),
        "faturamento_liquido": float(faturamento_liquido),
        "pedidos_enviados": int(pedidos_enviados),
        "repasse_previsto": float(repasse_previsto),
        "repasse_previsto_pct": float(repasse_previsto / base_bruta_com_frete) if base_bruta_com_frete else 0,
        "cancel_pct": float(cancelamentos / faturamento_total) if faturamento_total else 0,
        "comissao_pct": float(comissao / faturamento_total) if faturamento_total else 0,
        "repaid_pct": float(repaid_total / faturamento_total) if faturamento_total else 0,
        "base_bruta_com_frete": float(base_bruta_com_frete),
    }


def dataframe_for_download(df):
    export_cols = [c for c in [
        "N.º de venda", "Data da venda", "Estado", "Descrição do status", "Título do anúncio",
        "Canal de venda", "Forma de entrega", "Receita por produtos (BRL)",
        "Receita por envio (BRL)", "Cancelamentos e reembolsos (BRL)",
        "Tarifa de venda e impostos (BRL)", "Tarifas de envio (BRL)",
        "Total (BRL)", "repaid_beneficio", "repasse_base", "is_cancelled", "is_sent"
    ] if c in df.columns]
    return df[export_cols].copy()


def build_charts(metrics):
    composicao_df = pd.DataFrame({
        "Categoria": [
            "Faturamento líquido",
            "Frete pago pelo cliente",
            "Cancelado",
            "Comissão",
            "Frete cobrado",
            "Repaid/Benefícios"
        ],
        "Valor": [
            max(metrics["faturamento_liquido"], 0),
            metrics["frete_pago_cliente"],
            metrics["cancelamentos"],
            metrics["comissao"],
            metrics["frete_cobrado"],
            metrics["repaid_total"]
        ],
    })
    fig_donut = px.pie(composicao_df, names="Categoria", values="Valor", hole=0.55)

    comparativo_df = pd.DataFrame({
        "Indicador": ["Faturamento total", "Base com frete do cliente", "Repasse previsto", "Faturamento líquido"],
        "Valor": [
            metrics["faturamento_total"],
            metrics["base_bruta_com_frete"],
            metrics["repasse_previsto"],
            metrics["faturamento_liquido"],
        ],
    })
    fig_bar = px.bar(comparativo_df, x="Indicador", y="Valor", text_auto=".2s")
    return fig_donut, fig_bar


def render_metric_card(col, icon, title, value, description, bg_color="white"):
    """Renderiza um card de métrica com estilo customizado"""
    with col:
        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #e0e0e0;
                margin-bottom: 10px;
                height: 160px;
            ">
                <div style="display: flex; align-items: center; margin-bottom: 12px;">
                    <div style="
                        font-size: 24px;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background-color: rgba(255, 193, 7, 0.2);
                        border-radius: 8px;
                    ">
                        {icon}
                    </div>
                </div>
                <div style="color: #666; font-size: 12px; margin-bottom: 8px;">
                    {title}
                </div>
                <div style="color: #000; font-size: 22px; font-weight: bold; margin-bottom: 8px;">
                    {value}
                </div>
                <div style="color: #999; font-size: 11px;">
                    {description}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_indicator_card(col, icon, title, value, description):
    """Renderiza um card de indicador"""
    with col:
        st.markdown(
            f"""
            <div style="
                background-color: white;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #e0e0e0;
                margin-bottom: 10px;
            ">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="
                        font-size: 24px;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background-color: rgba(255, 193, 7, 0.2);
                        border-radius: 8px;
                    ">
                        {icon}
                    </div>
                    <div>
                        <div style="color: #666; font-size: 12px;">
                            {title}
                        </div>
                        <div style="color: #000; font-size: 20px; font-weight: bold;">
                            {value}
                        </div>
                        <div style="color: #999; font-size: 11px;">
                            {description}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


st.title("Painel Financeiro Mercado Livre")
st.caption(
    "Faça upload do relatório de vendas do Mercado Livre em Excel e acompanhe faturamento, cancelamentos, comissões, fretes e repasse previsto."
)

with st.sidebar:
    st.header("Como o cálculo funciona")
    st.markdown(
        """
        **Faturamento total**  
        Soma da coluna `Receita por produtos (BRL)`.

        **Vendas canceladas**  
        Soma absoluta da coluna `Cancelamentos e reembolsos (BRL)`.

        **Comissão total**  
        Soma absoluta da coluna `Tarifa de venda e impostos (BRL)`.

        **Frete cobrado total**  
        Soma absoluta da coluna `Tarifas de envio (BRL)`.

        **Repaid / Benefícios**  
        Diferença positiva entre o `Total (BRL)` reportado e o cálculo base (Produtos + Acréscimo - Taxas - Frete). Representa bônus de campanhas como CPC.

        **Faturamento líquido**  
        `Faturamento` - cancelamentos - comissão - frete cobrado + Repaid.

        **Repasse previsto**  
        Soma do `Total (BRL)` para pedidos sem sinal de cancelamento.
        """
    )
    st.warning(
        "O repasse previsto é uma estimativa com base nas informações do relatório de vendas. O valor financeiro real pode variar conforme liberações e ajustes do Mercado Livre."
    )

uploaded_file = st.file_uploader("Envie o arquivo .xlsx do relatório de vendas", type=["xlsx"])

if uploaded_file is None:
    st.info("Suba uma planilha para começar.")
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
    st.warning("Algumas colunas esperadas não foram encontradas. O app tentou continuar com o que estava disponível.")

# ========== SEÇÃO DE CARDS PRINCIPAIS ==========
st.markdown("---")

# Primeira linha de cards (4 colunas para acomodar o Repaid)
col1, col2, col3, col4 = st.columns(4, gap="small")
render_metric_card(
    col1, 
    "💵", 
    "Faturamento Total",
    brl(metrics["faturamento_total"]),
    "Receita total por produtos",
    bg_color="#fffbf0"
)
render_metric_card(
    col2,
    "❌",
    "Vendas Canceladas",
    brl(metrics["cancelamentos"]),
    "Cancelamentos e reembolsos",
    bg_color="white"
)
render_metric_card(
    col3,
    "%",
    "Comissão Total",
    brl(metrics["comissao"]),
    "Tarifa de venda e impostos",
    bg_color="#fffbf0"
)
render_metric_card(
    col4,
    "🎁",
    "Repaid / Benefícios",
    brl(metrics["repaid_total"]),
    "Bônus de campanhas (CPC, etc)",
    bg_color="#f0fff4" # Verde clarinho para destacar benefício
)

# Segunda linha de cards
col5, col6, col7, col8 = st.columns(4, gap="small")
render_metric_card(
    col5,
    "🚚",
    "Frete Cobrado Total",
    brl(metrics["frete_cobrado"]),
    "Tarifas de envio descontadas",
    bg_color="white"
)
render_metric_card(
    col6,
    "✅",
    "Faturamento Líquido",
    brl(metrics["faturamento_liquido"]),
    "Faturamento - taxas + benefícios",
    bg_color="#fffbf0"
)
render_metric_card(
    col7,
    "📦",
    "Repasse Previsto",
    brl(metrics["repasse_previsto"]),
    "Valor previsto conforme relatório",
    bg_color="#fffbf0"
)
render_metric_card(
    col8,
    "📈",
    "Pedidos Enviados",
    str(metrics["pedidos_enviados"]),
    "Total de pedidos com status de envio",
    bg_color="white"
)

# ========== SEÇÃO DE INDICADORES ==========
st.markdown("---")
st.subheader("Indicadores")

ind_col1, ind_col2, ind_col3 = st.columns(3, gap="medium")
render_indicator_card(
    ind_col1,
    "📊",
    "% Cancelamento",
    pct(metrics["cancel_pct"]),
    "sobre o faturamento total"
)
render_indicator_card(
    ind_col2,
    "%",
    "Peso da Comissão",
    pct(metrics["comissao_pct"]),
    "sobre o faturamento total"
)
render_indicator_card(
    ind_col3,
    "✨",
    "Impacto Benefícios",
    pct(metrics["repaid_pct"]),
    "ganho extra sobre faturamento"
)

st.markdown("---")

st.caption(f"Base bruta considerada para conciliação: {brl(metrics['base_bruta_com_frete'])} = produtos + frete pago pelo cliente")

fig_donut, fig_bar = build_charts(metrics)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.subheader("Composição financeira")
    st.plotly_chart(fig_donut, use_container_width=True)
with chart_col2:
    st.subheader("Comparativo geral")
    st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Insights automáticos")
insight_col1, insight_col2, insight_col3 = st.columns(3)
insight_col1.success(f"Cancelamentos representam {pct(metrics['cancel_pct'])} do faturamento de produtos.")
insight_col2.info(f"A comissão consome {pct(metrics['comissao_pct'])} do faturamento de produtos.")
if metrics["repaid_total"] > 0:
    insight_col3.success(f"Você recebeu {brl(metrics['repaid_total'])} em benefícios extras (Repaid).")
else:
    insight_col3.warning("Nenhum benefício extra (Repaid) detectado neste relatório.")

st.subheader("Filtros")
f1, f2, f3 = st.columns(3)

status_options = sorted([s for s in df["Estado"].dropna().unique().tolist() if str(s).strip()])
selected_status = f1.multiselect("Filtrar por status", status_options)

canal_options = sorted([s for s in df.get("Canal de venda", pd.Series(dtype=str)).dropna().unique().tolist() if str(s).strip()])
selected_canais = f2.multiselect("Filtrar por canal", canal_options)

filtered_df = df.copy()

if df["data_venda_dt"].notna().any():
    min_date = df["data_venda_dt"].min().date()
    max_date = df["data_venda_dt"].max().date()
    selected_period = f3.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(selected_period, tuple) and len(selected_period) == 2:
        start_date, end_date = selected_period
        filtered_df = filtered_df[
            filtered_df["data_venda_dt"].dt.date.between(start_date, end_date, inclusive="both")
        ]

if selected_status:
    filtered_df = filtered_df[filtered_df["Estado"].isin(selected_status)]

if selected_canais and "Canal de venda" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Canal de venda"].isin(selected_canais)]

st.subheader("Tabela de pedidos")
download_df = dataframe_for_download(filtered_df)
st.dataframe(download_df, use_container_width=True, height=420)

csv_data = download_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Baixar tabela filtrada em CSV",
    data=csv_data,
    file_name="pedidos_filtrados_mercado_livre.csv",
    mime="text/csv",
)

summary_text = f"""
Painel Financeiro Mercado Livre

Faturamento total: {brl(metrics['faturamento_total'])}
Vendas canceladas: {brl(metrics['cancelamentos'])}
Comissão total: {brl(metrics['comissao'])}
Frete cobrado total: {brl(metrics['frete_cobrado'])}
Repaid / Benefícios: {brl(metrics['repaid_total'])}
Faturamento líquido: {brl(metrics['faturamento_liquido'])}
Repasse previsto: {brl(metrics['repasse_previsto'])}
Percentual de cancelamento: {pct(metrics['cancel_pct'])}
Peso da comissão: {pct(metrics['comissao_pct'])}
""".strip()

st.download_button(
    "Baixar resumo em TXT",
    data=summary_text.encode("utf-8"),
    file_name="resumo_financeiro_mercado_livre.txt",
    mime="text/plain",
)
