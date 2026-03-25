# Painel de Repasse Mercado Livre

Aplicativo em Streamlit para leitura do relatório de vendas do Mercado Livre e geração de indicadores financeiros e operacionais.

## O que o app mostra
- Faturamento total gerado das vendas
- Vendas canceladas ou reembolsadas
- Comissão total descontada
- Frete cobrado total
- Faturamento líquido
- Repasse previsto
- Percentual de cancelamento
- Peso da comissão
- Tabela de pedidos com filtros

## Regras principais
- Faturamento total: soma de `Receita por produtos (BRL)`
- Faturamento líquido: `Receita por produtos + Receita por envio - cancelamentos - comissão - tarifas de envio`
- Repasse previsto: usa `Total (BRL)` para pedidos não cancelados
- Quando `Total (BRL)` vier vazio ou zerado, o app reconstrói o repasse com base nas colunas financeiras do relatório
- Quando existir `Receita por envio (BRL)`, esse valor entra no cálculo, pois impacta o valor final recebido

## Como rodar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Como subir no GitHub e Streamlit Community Cloud
1. Crie um repositório no GitHub.
2. Envie os arquivos deste projeto.
3. No Streamlit Community Cloud, conecte o repositório.
4. Defina `app.py` como arquivo principal.
5. Publique.

## Estrutura
- `app.py`: app principal
- `requirements.txt`: dependências
- `README.md`: instruções

## Observação
O repasse previsto é estimado com base no relatório de vendas. Para conciliação financeira oficial, cruze com extrato do Mercado Pago ou relatório financeiro do Mercado Livre.
