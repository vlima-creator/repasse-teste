# Painel de Repasse Mercado Livre

Aplicativo em Streamlit para leitura do relatório de vendas do Mercado Livre e geração de indicadores operacionais de repasse.

## O que o app mostra
- Faturamento total gerado das vendas
- Vendas canceladas ou reembolsadas
- Comissão total descontada
- Pedidos enviados
- Previsão estimada de repasse até 7 dias
- Previsão estimada de repasse após 7 dias
- Percentuais sobre o faturamento total
- Tabela de pedidos com filtros

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
A previsão de repasse é estimada, não financeira oficial. Para conciliação exata, cruze com extrato do Mercado Pago ou relatório financeiro do Mercado Livre.
