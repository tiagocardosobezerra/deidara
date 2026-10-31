# Exemplo legado (para o C0)

Projeto Power BI "de mercado", escrito à mão, com os erros clássicos de indicador: turnover dividido pela
contagem do cadastro, média de taxas, meta pela média simples, meta escrita na fórmula, ano anterior contra o
ano inteiro, IFERROR e divisão com "/", soma da folha com desligados, FILTER na tabela inteira, TODAY() como fim
do período, CPF na fórmula, coluna que não existe, coluna calculada fazendo papel de medida, relação nos dois
sentidos, calendário não marcado e data/hora automática. Nenhum dado: só a estrutura.

    python deidara.py c0 estudar exemplos/legado
    python deidara.py c0 propor exemplos/legado --medida "Turnover %"
    python deidara.py c0 importar exemplos/legado -o C:/paineis/rh-refeito
