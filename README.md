# Painel Financeiro Mercado Livre

Aplicativo em Streamlit para leitura do relatório de vendas do Mercado Livre e consolidação dos principais indicadores financeiros.

## Indicadores do painel
- Faturamento total
- Frete pago pelo cliente
- Vendas canceladas
- Comissão total
- Frete cobrado total
- Faturamento líquido
- Repasse previsto
- Percentual de cancelamento
- Peso da comissão

## Lógica principal
- **Faturamento total**: soma de `Receita por produtos (BRL)`
- **Frete pago pelo cliente**: soma de `Receita por envio (BRL)`
- **Vendas canceladas**: soma absoluta de `Cancelamentos e reembolsos (BRL)` e apoio de leitura do status
- **Comissão total**: soma absoluta de `Tarifa de venda e impostos (BRL)`
- **Frete cobrado total**: soma absoluta de `Tarifas de envio (BRL)`
- **Faturamento líquido**: produtos + frete pago pelo cliente - cancelamentos - comissão - frete cobrado
- **Repasse previsto**: usa `Total (BRL)` dos pedidos não cancelados. Se essa coluna vier vazia ou zerada, o app reconstrói o valor usando a lógica financeira do relatório

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```
