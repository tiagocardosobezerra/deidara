# Métricas: onde criar, padrões e dicionário de funções

## Onde criar cada coisa

| Meio | Quando | No Deidara |
|---|---|---|
| **Medida DAX** | todo número que responde a filtro: somas, contagens, taxas, comparações no tempo | medidas do argila.json (tipos prontos ou `dax`) |
| **Cálculo visual** | cálculo que só vale num visual: acumulado no eixo, média móvel do gráfico, % do total do próprio visual | não gerado; crie no Desktop. Se o número aparece em mais de um lugar, é medida |
| **Grupo de cálculo** | a mesma transformação para muitas medidas (YTD, ano anterior, variação para 10 indicadores) | não gerado; com poucas medidas, os tipos de tempo resolvem |
| **Coluna no Power Query** | regra por linha: faixa, classificação, chave, limpeza, tipos; dados de planilha/SharePoint | seleção, nomes, tipos e chaves já gerados; regras próprias entram na consulta de origem |
| **View SQL** | regra por linha e filtro de origem em banco, que outros sistemas também usam | `filtro` da tabela e colunas da view |
| **Coluna calculada DAX** | último recurso: atributo que depende de outra tabela do modelo | não gerada de propósito |

Regra curta: **por linha → origem (Power Query/SQL); responde a filtro →
medida; só num visual → cálculo visual.**

## Padrões de indicador

```bash
python3 deidara.py padroes                 # onde criar + todos os padrões
python3 deidara.py padroes "acumulado"     # filtra por assunto
```

Cada padrão traz o trecho pronto do argila.json, o DAX equivalente, a
alternativa (cálculo visual, grupo de cálculo, coluna na origem) e as
armadilhas. Os padrões cobrem: total aditivo, distintos, taxa, participação
no total, medida com recorte, estoque na data, média do período, acumulado no
ano, ano anterior e variação, móvel 12 meses, último valor (semiaditivo),
ranking, prazo médio, faixa, segunda data (relação inativa) e meta com status.
Fonte: `dicionario/padroes.json` (o time pode acrescentar os seus).

## Dicionário de funções

```bash
python3 deidara.py funcoes buscar "ano anterior"          # DAX (padrão)
python3 deidara.py funcoes buscar "excel" --linguagem m   # Power Query
python3 deidara.py funcoes ver DATESINPERIOD
```

`dicionario/dax.json` (462 funções) e `dicionario/m.json` (667): nome,
categoria, assinatura e o link da página oficial da Microsoft (em pt-BR); as
mais usadas em indicadores têm também uma descrição e um "uso em
indicadores" escritos para o Deidara. A documentação completa é a da
Microsoft, no link de cada função: o Deidara não copia o texto dela.

**Validação.** Todo DAX livre (medida `dax`, filtro de segurança) é lido
função por função: a que não está no dicionário é **erro**, com sugestão de
nome parecido. Nada de função "que deve existir".

**Sua versão.** Funções novas aparecem a cada versão do Power BI. Para
validar contra exatamente o que você tem instalado, rode a receita de
funções (`receita funcoes-dax` / `funcoes-m`) e `catalogar --funcoes`; o
resultado fica em `dicionario/local/` e passa a valer junto.
