import io
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Painel de Repasse Mercado Livre",
    page_icon="💸",
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
    "Tarifa de venda e impostos (BRL)",
    "Cancelamentos e reembolsos (BRL)",
    "Total (BRL)",
    "Título do anúncio",
    "Canal de venda",
    "Forma de entrega",
    "Data de entrega",
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

    match = __import__("re").match(r"(\d{1,2}) de ([^ ]+) de (\d{4})(?: (\d{1,2}):(\d{2}))?$", text.lower())
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
        "Tarifa de venda e impostos (BRL)",
        "Tarifas de envio (BRL)",
        "Receita por envio (BRL)",
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

    if "Data de entrega" in df.columns:
        df["data_entrega_dt"] = df["Data de entrega"].apply(parse_brazilian_datetime)
    else:
        df["data_entrega_dt"] = pd.NaT

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
        na=False,
    )

    delivered_by_date = df["data_entrega_dt"].notna()
    delivered_by_text = status_mix.str.contains("entreg", regex=True, na=False)
    df["is_delivered"] = delivered_by_date | delivered_by_text

    df["repasse_ate_7d"] = (
        df["is_delivered"]
        & (~df["is_cancelled"])
        & (
            df["data_entrega_dt"].between(
                pd.Timestamp.today().normalize() - pd.Timedelta(days=7),
                pd.Timestamp.today().normalize() + pd.Timedelta(days=7),
                inclusive="both",
            )
            | df["data_entrega_dt"].isna()
        )
    )

    df["repasse_apos_7d"] = (
        (~df["is_cancelled"])
        & (~df["repasse_ate_7d"])
        & df["is_sent"]
    )

    return df

def compute_metrics(df: pd.DataFrame) -> dict:
    faturamento_total = df.get("Receita por produtos (BRL)", pd.Series(dtype=float)).sum()
    cancelamentos = df.get("Cancelamentos e reembolsos (BRL)", pd.Series(dtype=float)).abs().sum()
    comissao = df.get("Tarifa de venda e impostos (BRL)", pd.Series(dtype=float)).abs().sum()
    pedidos_enviados = int(df["is_sent"].sum()) if "is_sent" in df.columns else 0
    repasse_7 = df.loc[df["repasse_ate_7d"], "Total (BRL)"].sum() if "repasse_ate_7d" in df.columns else 0
    repasse_mais_7 = df.loc[df["repasse_apos_7d"], "Total (BRL)"].sum() if "repasse_apos_7d" in df.columns else 0

    return {
        "faturamento_total": float(faturamento_total),
        "cancelamentos": float(cancelamentos),
        "comissao": float(comissao),
        "pedidos_enviados": int(pedidos_enviados),
        "repasse_7": float(repasse_7),
        "repasse_7_pct": float(repasse_7 / faturamento_total) if faturamento_total else 0,
        "repasse_mais_7": float(repasse_mais_7),
        "repasse_mais_7_pct": float(repasse_mais_7 / faturamento_total) if faturamento_total else 0,
        "liquido_potencial": float(max(faturamento_total - cancelamentos - comissao, 0)),
        "cancel_pct": float(cancelamentos / faturamento_total) if faturamento_total else 0,
        "comissao_pct": float(comissao / faturamento_total) if faturamento_total else 0,
    }

def dataframe_for_download(df):
    export_cols = [c for c in [
        "N.º de venda", "Data da venda", "Estado", "Descrição do status", "Título do anúncio",
        "Canal de venda", "Forma de entrega", "Data de entrega", "Receita por produtos (BRL)",
        "Cancelamentos e reembolsos (BRL)", "Tarifa de venda e impostos (BRL)", "Total (BRL)",
        "is_cancelled", "is_sent", "is_delivered", "repasse_ate_7d", "repasse_apos_7d"
    ] if c in df.columns]
    return df[export_cols].copy()

def build_charts(metrics):
    donut_df = pd.DataFrame({
        "Categoria": ["Líquido potencial", "Cancelado", "Comissão"],
        "Valor": [metrics["liquido_potencial"], metrics["cancelamentos"], metrics["comissao"]],
    })
    fig_donut = px.pie(donut_df, names="Categoria", values="Valor", hole=0.55)

    repasse_df = pd.DataFrame({
        "Faixa": ["Até 7 dias", "Após 7 dias"],
        "Valor": [metrics["repasse_7"], metrics["repasse_mais_7"]],
    })
    fig_bar = px.bar(repasse_df, x="Faixa", y="Valor", text_auto=".2s")

    return fig_donut, fig_bar

st.title("Painel de Repasse Mercado Livre")
st.caption("Faça upload do relatório de vendas do Mercado Livre em Excel e veja os indicadores de faturamento, cancelamento, comissão e previsão estimada de repasse.")

with st.sidebar:
    st.header("Como o cálculo funciona")
    st.markdown(
        """
        **Faturamento total**  
        Soma da coluna `Receita por produtos (BRL)`.

        **Vendas canceladas**  
        Soma absoluta da coluna `Cancelamentos e reembolsos (BRL)` e leitura do status.

        **Comissão total descontada**  
        Soma absoluta da coluna `Tarifa de venda e impostos (BRL)`.

        **Pedidos enviados**  
        Contagem de pedidos com indícios logísticos de envio, coleta, entrega, etiqueta ou trânsito.

        **Repasse até 7 dias**  
        Estimativa baseada em pedidos entregues recentemente e sem sinais de cancelamento.

        **Repasse após 7 dias**  
        Estimativa baseada em pedidos ainda enviados, em rota ou preparação logística sem cancelamento.
        """
    )
    st.warning("A previsão de repasse é uma estimativa operacional. Para valor financeiro exato, cruze com o extrato do Mercado Pago ou relatório financeiro do Mercado Livre.")

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

col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento total", brl(metrics["faturamento_total"]))
col2.metric("Vendas canceladas", brl(metrics["cancelamentos"]))
col3.metric("Comissão total", brl(metrics["comissao"]))
col4.metric("Pedidos enviados", f'{metrics["pedidos_enviados"]:,}'.replace(",", "."))

col5, col6, col7, col8 = st.columns(4)
col5.metric("Repasse até 7 dias", brl(metrics["repasse_7"]), pct(metrics["repasse_7_pct"]))
col6.metric("Repasse após 7 dias", brl(metrics["repasse_mais_7"]), pct(metrics["repasse_mais_7_pct"]))
col7.metric("Percentual de cancelamento", pct(metrics["cancel_pct"]))
col8.metric("Peso da comissão", pct(metrics["comissao_pct"]))

fig_donut, fig_bar = build_charts(metrics)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.subheader("Composição do faturamento")
    st.plotly_chart(fig_donut, use_container_width=True)
with chart_col2:
    st.subheader("Previsão de repasses")
    st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Insights automáticos")
insight_col1, insight_col2, insight_col3 = st.columns(3)
insight_col1.success(f"Cancelamentos representam {pct(metrics['cancel_pct'])} do faturamento bruto.")
insight_col2.info(f"A comissão consome {pct(metrics['comissao_pct'])} do faturamento bruto.")
insight_col3.warning(f"O repasse estimado de curto prazo representa {pct(metrics['repasse_7_pct'])} do faturamento bruto.")

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
    "Canal de venda", "Forma de entrega", "Data de entrega",
    "Receita por produtos (BRL)", "Cancelamentos e reembolsos (BRL)", "Tarifa de venda e impostos (BRL)", "Total (BRL)"
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
Painel de Repasse Mercado Livre

Faturamento total: {brl(metrics["faturamento_total"])}
Vendas canceladas: {brl(metrics["cancelamentos"])}
Comissão total: {brl(metrics["comissao"])}
Pedidos enviados: {metrics["pedidos_enviados"]}
Repasse até 7 dias: {brl(metrics["repasse_7"])} ({pct(metrics["repasse_7_pct"])})
Repasse após 7 dias: {brl(metrics["repasse_mais_7"])} ({pct(metrics["repasse_mais_7_pct"])})
Percentual de cancelamento: {pct(metrics["cancel_pct"])}
Peso da comissão: {pct(metrics["comissao_pct"])}

Aviso:
A previsão de repasse é estimada com base no comportamento logístico e nos status presentes no relatório de vendas.
"""
st.download_button(
    label="Baixar resumo em TXT",
    data=summary_text.encode("utf-8"),
    file_name="resumo_painel_repasse.txt",
    mime="text/plain",
)
