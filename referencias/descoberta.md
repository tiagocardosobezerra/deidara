# Descoberta: achar as tabelas, sugerir e provar as ligações

Quando as informações chegam soltas (várias fontes, nenhuma FK entre elas),
o Deidara ajuda a montar o modelo em três passos. Nenhum deles liga nada
sozinho: quem confirma uma ligação é uma pessoa.

## 1. Buscar: quais tabelas atendem ao pedido

```bash
python3 deidara.py buscar "desligamentos por motivo com meta por empresa" --catalogos catalogos/erp.json catalogos/metas.json
```

Ranqueia as tabelas de **todos** os catálogos pelo nome e pela descrição das
tabelas e colunas, com plural, acento e sinônimos do negócio
(`dicionario/sinonimos.json`: "colaborador" = "funcionário" = "matrícula").
Confirme a escolha com o usuário antes de escrever o argila.json.

## 2. Relacionar: que ligações faltam

```bash
python3 deidara.py relacionar --argila argila.json                       # as tabelas do modelo
python3 deidara.py relacionar --catalogos erp.json metas.json --json     # antes de existir o argila
```

Para cada par de tabelas ainda não ligado (nem por caminho), pontua as colunas
candidatas e mostra **por quê**:

| Evidência | Efeito |
|---|---|
| mesmo núcleo de nome (`CODEMPRESA` ≈ `Cód. Empresa` ≈ `cod_empresa_fk`) | forte |
| nomes equivalentes pelos sinônimos (`COLIGADA` ≈ `EMPRESA`) | médio |
| a coluna aponta para a tabela mãe (`empresa` ⊂ `N_EMPRESA`) | médio |
| a ponta mãe é a PK da tabela (catálogo SQL) | forte |
| a ponta mãe NÃO é a PK (catálogo SQL) | contra: o lado "um" repete |
| unicidade desconhecida (planilha, SharePoint) | neutro: pede a prova |
| mesmo tipo / texto x inteiro | a favor / contra (texto sem marca de código "parece nome") |
| data, lógico ou número quebrado | descartada: não é chave |

Confiança: **alta** (70+), **média** (45+), **baixa** (30+). Ligações já
provadas no catálogo aparecem como tais. Sugestões que ficam **redundantes**
quando você aceita as de cima vêm marcadas. Com `--json`, cada sugestão traz
o trecho pronto do argila.json (`"declarada"` com `"por": "<quem confirmou>"`).

Regra: mostre as sugestões ao usuário, confirme os campos com o dono do dado e
só então escreva a ligação declarada, com o nome de quem confirmou.

## 3. Provar: medir a ligação na fonte

```bash
python3 deidara.py receita prova --argila argila.json --de "fMeta[Cód. Empresa]" --para "dEmpresa[CODEMPRESA]" -o prova.pq
```

- As duas pontas no mesmo SQL Server: receita **SQL** (SSMS).
- Fontes diferentes (planilha x ERP): receita **Power Query**, que lê o SQL
  Server direto (servidor e banco da fonte no argila.json) e a planilha pela
  consulta que já existe no arquivo.

É a única receita que lê conteúdo, só para **contar**. Devolve uma linha com
percentuais arredondados e sim/não, nunca um código ou um valor:

| Coluna | O que é |
|---|---|
| `pct_nulos_filha` | % das linhas da filha com o código em branco |
| `pct_linhas_com_par` | % das linhas da filha (com código) que acham par na mãe |
| `pct_codigos_com_par` | % dos códigos distintos da filha que existem na mãe |
| `mae_unica` | sim/não: o código é único na mãe |

```bash
python3 deidara.py provar --de resultado.txt --argila meu_painel/argila.json
```

| Veredito | Quando | No argila.json |
|---|---|---|
| provada | 99%+ das linhas com par e mãe única | sem aviso; a prova vai para o dicionário |
| provada com ressalva | 90–99% com par | aviso: as linhas sem par somem dos cortes |
| fraca | menos de 90% | aviso: provavelmente não é esta a ligação |
| reprovada | código repetido na mãe | **erro**: o Power BI recusa a relação 1:* |

Com `--argila`, o `provar` grava o bloco `"prova": {...}` dentro da `"declarada"` correspondente (confirme a ligação antes com `deidara.py confirmar`):

```json
{"de": "fMeta", "para": "dEmpresa",
 "declarada": {"campos": [["Cód. Empresa", "CODEMPRESA"]], "por": "Ana (RH)",
               "motivo": "mesmo código do ERP",
               "prova": {"pct_nulos_filha": 0.0, "pct_linhas_com_par": 100.0,
                         "pct_codigos_com_par": 100.0, "mae_unica": true, "em": "27/10/2026"}}}
```

Nunca escreva um bloco de prova à mão nem com números estimados: ele só vem
do resultado da receita rodada na fonte.
