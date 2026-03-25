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

    receita_produtos = df.get("Receita por produtos (BRL)", pd.Series(0, index=df.index)).fillna(0)
    receita_envio = df.get("Receita por envio (BRL)", pd.Series(0, index=df.index)).fillna(0)
    comissao = df.get("Tarifa de venda e impostos (BRL)", pd.Series(0, index=df.index)).fillna(0)
    tarifas_envio = df.get("Tarifas de envio (BRL)", pd.Series(0, index=df.index)).fillna(0)
    cancelamentos = df.get("Cancelamentos e reembolsos (BRL)", pd.Series(0, index=df.index)).fillna(0)

    total_reportado = df.get("Total (BRL)", pd.Series(0, index=df.index)).fillna(0)
    total_reconstruido = receita_produtos + receita_envio + comissao + tarifas_envio + cancelamentos
    usar_total_reconstruido = total_reportado.eq(0) & (
        receita_produtos.ne(0) | receita_envio.ne(0) | comissao.ne(0) | tarifas_envio.ne(0) | cancelamentos.ne(0)
    )
    df["repasse_base"] = total_reportado.where(~usar_total_reconstruido, total_reconstruido)

    return df



def compute_metrics(df: pd.DataFrame) -> dict:
    faturamento_total = df.get("Receita por produtos (BRL)", pd.Series(dtype=float)).sum()
    receita_envio = df.get("Receita por envio (BRL)", pd.Series(dtype=float)).sum()
    cancelamentos = df.get("Cancelamentos e reembolsos (BRL)", pd.Series(dtype=float)).abs().sum()
    comissao = df.get("Tarifa de venda e impostos (BRL)", pd.Series(dtype=float)).abs().sum()
    frete_cobrado = df.get("Tarifas de envio (BRL)", pd.Series(dtype=float)).abs().sum()
    pedidos_enviados = int(df["is_sent"].sum()) if "is_sent" in df.columns else 0

    faturamento_liquido = faturamento_total + receita_envio - cancelamentos - comissao - frete_cobrado
    faturamento_liquido = float(faturamento_liquido)

    nao_cancelados = ~df.get("is_cancelled", pd.Series(False, index=df.index))
    repasse_previsto = df.loc[nao_cancelados, "repasse_base"].clip(lower=0).sum() if "repasse_base" in df.columns else 0

    return {
        "faturamento_total": float(faturamento_total),
        "receita_envio": float(receita_envio),
        "cancelamentos": float(cancelamentos),
        "comissao": float(comissao),
        "frete_cobrado": float(frete_cobrado),
        "faturamento_liquido": float(faturamento_liquido),
        "pedidos_enviados": int(pedidos_enviados),
        "repasse_previsto": float(repasse_previsto),
        "repasse_previsto_pct": float(repasse_previsto / faturamento_total) if faturamento_total else 0,
        "cancel_pct": float(cancelamentos / faturamento_total) if faturamento_total else 0,
        "comissao_pct": float(comissao / faturamento_total) if faturamento_total else 0,
        "frete_pct": float(frete_cobrado / faturamento_total) if faturamento_total else 0,
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



def build_charts(metrics):
    composicao_df = pd.DataFrame({
        "Categoria": ["Faturamento líquido", "Cancelado", "Comissão", "Frete cobrado"],
        "Valor": [
            max(metrics["faturamento_liquido"], 0),
            metrics["cancelamentos"],
            metrics["comissao"],
            metrics["frete_cobrado"],
        ],
    })
    fig_donut = px.pie(composicao_df, names="Categoria", values="Valor", hole=0.55)

    comparativo_df = pd.DataFrame({
        "Indicador": ["Faturamento total", "Repasse previsto", "Faturamento líquido"],
        "Valor": [
            metrics["faturamento_total"],
            metrics["repasse_previsto"],
            metrics["faturamento_liquido"],
        ],
    })
    fig_bar = px.bar(comparativo_df, x="Indicador", y="Valor", text_auto=".2s")
    return fig_donut, fig_bar


st.title("Painel Financeiro Mercado Livre")
st.caption(
    "Faça upload do relatório de vendas do Mercado Livre em Excel e veja os indicadores principais de faturamento, cancelamento, comissão, frete e repasse previsto."
)

with st.sidebar:
    st.header("Como o cálculo funciona")
    st.markdown(
        """
        **Faturamento total**  
        Soma da coluna `Receita por produtos (BRL)`.

        **Vendas canceladas**  
        Soma absoluta da coluna `Cancelamentos e reembolsos (BRL)` e leitura do status.

        **Comissão total**  
        Soma absoluta da coluna `Tarifa de venda e impostos (BRL)`.

        **Frete cobrado total**  
        Soma absoluta da coluna `Tarifas de envio (BRL)`.

        **Faturamento líquido**  
        Faturamento total + `Receita por envio (BRL)` - cancelamentos - comissão - frete cobrado.

        **Repasse previsto**  
        Soma do `Total (BRL)` para pedidos sem sinal de cancelamento ou reembolso. Quando o `Total (BRL)` vier vazio ou zerado, o app reconstrói o valor usando produto + receita por envio - comissão - frete - cancelamentos.
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

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Faturamento total", brl(metrics["faturamento_total"]))
col2.metric("Vendas canceladas", brl(metrics["cancelamentos"]))
col3.metric("Comissão total", brl(metrics["comissao"]))
col4.metric("Frete cobrado total", brl(metrics["frete_cobrado"]))
col5.metric("Faturamento líquido", brl(metrics["faturamento_liquido"]))

col6, col7, col8 = st.columns(3)
col6.metric("Repasse previsto", brl(metrics["repasse_previsto"]), pct(metrics["repasse_previsto_pct"]))
col7.metric("Percentual de cancelamento", pct(metrics["cancel_pct"]))
col8.metric("Peso da comissão", pct(metrics["comissao_pct"]))

st.caption(f"Receita por envio considerada nos cálculos: {brl(metrics['receita_envio'])}")

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
insight_col1.success(f"Cancelamentos representam {pct(metrics['cancel_pct'])} do faturamento bruto.")
insight_col2.info(f"A comissão consome {pct(metrics['comissao_pct'])} do faturamento bruto.")
insight_col3.warning(
    f"O repasse previsto considera {brl(metrics['receita_envio'])} de receita por envio quando houver cobrança de frete ao comprador."
)

st.subheader("Filtros")
f1, f2, f3 = st.columns(3)

status_options = sorted([s for s in df["Estado"].dropna().unique().tolist() if str(s).strip()])
selected_status = f1.multiselect("Filtrar por status", status_options)

canal_options = sorted([s for s in df.get("Canal de venda", pd.Series(dtype=str)).dropna().unique().tolist() if str(s).strip()])
selected_canais = f2.multiselect("Filtrar por canal", canal_options)

if df["data_venda_dt"].notna().any():
    min_date = df["data_venda_dt"].min().date()
    max_date = df["data_venda_dt"].max().date()
    selected_period = f3.date_input("Período da venda", value=(min_date, max_date))
else:
    selected_period = None
    f3.info("Sem datas válidas para filtrar.")

filtered_df = df.copy()
if selected_status:
    filtered_df = filtered_df[filtered_df["Estado"].isin(selected_status)]
if selected_canais:
    filtered_df = filtered_df[filtered_df["Canal de venda"].isin(selected_canais)]
if isinstance(selected_period, tuple) and len(selected_period) == 2 and df["data_venda_dt"].notna().any():
    start_dt = pd.Timestamp(selected_period[0])
    end_dt = pd.Timestamp(selected_period[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    filtered_df = filtered_df[filtered_df["data_venda_dt"].between(start_dt, end_dt, inclusive="both")]

st.subheader("Tabela de pedidos")
display_cols = [c for c in [
    "N.º de venda", "Data da venda", "Estado", "Descrição do status", "Título do anúncio",
    "Canal de venda", "Forma de entrega", "Receita por produtos (BRL)",
    "Receita por envio (BRL)", "Cancelamentos e reembolsos (BRL)",
    "Tarifa de venda e impostos (BRL)", "Tarifas de envio (BRL)",
    "Total (BRL)", "repasse_base"
] if c in filtered_df.columns]
st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)

csv_bytes = dataframe_for_download(filtered_df).to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="Baixar tabela filtrada em CSV",
    data=csv_bytes,
    file_name="pedidos_filtrados_mercado_livre.csv",
    mime="text/csv",
)

summary_text = f"""
Painel Financeiro Mercado Livre

Faturamento total: {brl(metrics["faturamento_total"])}
Receita por envio considerada: {brl(metrics["receita_envio"])}
Vendas canceladas: {brl(metrics["cancelamentos"])}
Comissão total: {brl(metrics["comissao"])}
Frete cobrado total: {brl(metrics["frete_cobrado"])}
Faturamento líquido: {brl(metrics["faturamento_liquido"])}
Repasse previsto: {brl(metrics["repasse_previsto"])} ({pct(metrics["repasse_previsto_pct"])})
Percentual de cancelamento: {pct(metrics["cancel_pct"])}
Peso da comissão: {pct(metrics["comissao_pct"])}

Aviso:
O repasse previsto é uma estimativa feita com base nas informações disponíveis no relatório de vendas.
Quando existir `Receita por envio (BRL)`, esse valor também é considerado nos cálculos.
"""
st.download_button(
    label="Baixar resumo em TXT",
    data=summary_text.encode("utf-8"),
    file_name="resumo_painel_financeiro.txt",
    mime="text/plain",
)
