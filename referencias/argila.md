# argila.json — a especificação do painel

Um arquivo JSON (UTF-8) por painel. Exemplo completo:
[../exemplos/aurora/argila.json](../exemplos/aurora/argila.json).

## Raiz

| Campo | Obrigatório | O que é |
|---|---|---|
| `projeto` | sim | nome do painel (vira o nome do .pbip) |
| `fontes` | sim | `{"nome": {"catalogo": "caminho do catálogo", ...}}`; fonte SQL Server aceita também `servidor`, `banco` (valores iniciais dos parâmetros), `esquema_origem` (padrão `dbo`) e `esquema_views` (padrão `bi`). Ver [fontes.md](fontes.md) |
| `versao` | recomendado | versão do painel (ex.: `1.0`), vai para o histórico de mudanças |
| `descricao`, `publico`, `responsavel` | não | aparecem no protótipo e na documentação |
| `tema` | não | `cores` (lista hex, a 1ª é a principal), `fundo`, `texto` |
| `tabelas` | sim | tabelas do modelo |
| `relacionamentos` | não | ligações entre tabelas do modelo |
| `calendario` | não | tabela de datas gerada |
| `medidas` | sim | os indicadores |
| `paginas` | sim | as páginas e os visuais |
| `seguranca` | não | papéis de segurança por linha (RLS) |

## tabelas

```json
{"nome": "dCargo", "tipo": "dimensao", "fonte": "erp", "origem": "F_CARGO",
 "colunas": [{"coluna": "CODCARGO", "nome": "Cód. Cargo"}, "DESCRICAOCARGO"],
 "filtro": "t.ATIVO = 1"}
```

- `nome`: nome no Power BI. Convenção: `f` + nome para fato, `d` para dimensão.
- `tipo`: `fato` ou `dimensao`.
- `fonte`: nome da fonte em `fontes` (pode omitir quando há uma só).
- `origem`: tabela ou consulta, **exatamente** como está no catálogo da fonte.
- `colunas`: texto (nome igual à origem) ou objeto com `coluna` (origem),
  `nome` (amigável), `formato` (`inteiro`, `decimal`, `moeda`, `percentual`,
  `data`), `oculta`, `descricao` (padrão: a do catálogo) e `tipo` (só quando
  a fonte não trouxe o tipo: `inteiro`, `decimal`, `real`, `data`,
  `datahora`, `hora`, `logico`, `texto`).
- `filtro`: só fonte SQL Server; entra no `WHERE` da view como está (o alias
  da origem é `t`). Não é conferido: revise o SQL. Nas outras fontes, filtre na
  própria consulta Power Query.

Colunas de ligação que você não listou entram sozinhas, ocultas.

## relacionamentos

```json
{"de": "fDesligamento", "para": "dMotivo"}
{"de": "fMovimento", "para": "dData", "via": ["DATAPAGAMENTO"], "ativo": false}
{"de": "fMeta", "para": "dEmpresa",
 "declarada": {"campos": [["Cód. Empresa", "CODEMPRESA"]], "por": "Ana (RH)", "motivo": "mesmo código do ERP"}}
```

- `de` = lado muitos (a filha), `para` = lado um (a mãe).
- A ligação vem do catálogo da fonte (FK do banco ou relação do modelo Power
  BI de origem). Chave composta vira a coluna oculta `Chave <para>` nas duas
  pontas (na view ou no Power Query): o Power BI só relaciona por uma coluna.
- `via`: os campos da filha, quando há mais de uma ligação entre as tabelas.
- `ativo`: só uma relação ativa por par de tabelas.
- `declarada`: entre fontes diferentes ou sem prova, depois de confirmar os
  campos com o dono do dado; `por` é obrigatório ([fontes.md](fontes.md)).

## calendario

```json
{"nome": "dCalendario", "inicio": 2020, "fim": 2026,
 "datas": [{"tabela": "fDesligamento", "coluna": "Data do Desligamento"},
           {"tabela": "fDesligamento", "coluna": "Data de Aviso", "ativo": false}]}
```

Gera a tabela (Power Query) com `Data`, `Ano`, `Mês`, `Nome do Mês`,
`Trimestre`, `Ano-Mês`, `Mês/Ano` (ordenada certo) e marca como tabela de
datas. As colunas de `datas` viram `date` na view (sem hora).

## medidas

Tipos prontos (preferidos: validação completa e consulta de conferência):

```json
{"nome": "Headcount", "agregacao": "contagem_linhas", "tabela": "dColaborador", "formato": "inteiro"}
{"nome": "Remuneração Total", "agregacao": "soma", "coluna": "dColaborador[Remuneração]", "formato": "moeda"}
{"nome": "Turnover", "tipo": "divisao", "numerador": "Desligamentos", "denominador": "Headcount", "formato": "percentual"}
{"nome": "Desligamentos Acum. Ano", "tipo": "acumulado_ano", "base": "Desligamentos"}
```

- `agregacao`: `soma`, `media`, `minimo`, `maximo`, `contagem`,
  `contagem_distinta` (ignora em branco), `contagem_linhas` (esta pede `tabela`).
- `tipo`: `divisao` (DIVIDE, sem erro de divisão por zero), `acumulado_ano`,
  `ano_anterior`, `variacao_ano_anterior`, `variacao_mes_anterior`,
  `media_mensal` (média dos valores de fim de mês no período) e `movel_12m`
  (estas pedem `calendario` e `base`; nenhuma mostra valor em mês futuro).
- `estoque_na_data`: quantos estão "dentro" no último dia do período
  (headcount ativo, contratos vigentes). `entradas` = coluna de data de
  entrada; a saída é `fim` (coluna de data na mesma tabela, em branco =
  ainda dentro) **ou** `saidas` (coluna de data de outra tabela, ex.: a fato
  de desligamentos). Não precisa de relacionamento com o calendário.
- `dax`: DAX livre, para o que os tipos não cobrem. O Deidara confere toda
  referência `Tabela[Coluna]` e `[Medida]` e toda função contra o dicionário
  (função inexistente é erro), mas não a lógica. Ver [metricas.md](metricas.md).

```json
{"nome": "Headcount", "tipo": "estoque_na_data", "entradas": "dColaborador[Data de Admissão]",
 "saidas": "fDesligamento[Data do Desligamento]"}
{"nome": "HC Médio", "tipo": "media_mensal", "base": "Headcount"}
{"nome": "Turnover", "tipo": "divisao", "numerador": "Desligamentos", "denominador": "HC Médio",
 "formato": "percentual", "polaridade": "menor_melhor", "meta": 0.05}
```

Comuns a todas: `formato` (padrão: `inteiro` para contagem e estoque,
`percentual` para variação, o da base para tempo, `decimal` no resto),
`descricao` (obrigatória na prática: regra 4), `pasta` (display folder),
`tabela` (onde a medida mora; padrão: a tabela da coluna ou a primeira
fato), `oculta`, `polaridade` (`maior_melhor` ou `menor_melhor`) e `meta`.

**Meta.** Um número gera a medida `Meta <nome>`; o nome de outra medida usa
essa medida como meta. Toda meta gera também `Cor <nome>` (oculta), verde
quando bate a meta pela polaridade e vermelha quando não bate. O cartão
mostra "Meta: …" no título e pinta o valor; tabela e matriz pintam a
coluna; o medidor usa a meta como alvo.

## paginas

```json
{"nome": "Turnover", "descricao": "…", "visuais": [
  {"tipo": "segmentador", "campo": "dCalendario[Ano]"},
  {"tipo": "cartao", "medida": "Turnover"},
  {"tipo": "medidor", "medida": "Turnover", "meta": "Meta Turnover"},
  {"tipo": "colunas", "categoria": "dCalendario[Mês/Ano]", "valores": ["Desligamentos"], "legenda": "dMotivo[Motivo]"},
  {"tipo": "barras",  "categoria": "dCargo[Cargo]", "valores": ["Headcount"]},
  {"tipo": "linha",   "categoria": "dCalendario[Mês/Ano]", "valores": ["A", "B"]},
  {"tipo": "rosca",   "categoria": "dMotivo[Motivo]", "valores": ["Desligamentos"]},
  {"tipo": "tabela",  "campos": ["dCargo[Cargo]", "Headcount"]},
  {"tipo": "matriz",  "linhas": ["dCargo[Cargo]"], "colunas": ["dCalendario[Trimestre]"], "valores": ["Desligamentos"]}
]}
```

Coluna é sempre `Tabela[Coluna]` (nomes do modelo); medida é o nome solto.
`titulo` é opcional em qualquer visual. A posição é automática e igual no
protótipo e no Power BI: segmentadores no topo, cartões e medidores, gráficos
em duas colunas e tabelas/matrizes em largura inteira.

`id` (opcional, em qualquer visual): nome fixo do visual no PBIR. Sem ele, o
nome sai de página + tipo + título, e reordenar os visuais não muda nada.

## seguranca (RLS)

```json
"seguranca": [
  {"papel": "Gestor da empresa", "descricao": "Cada gestor vê só a própria empresa.",
   "regras": [{"tabela": "dEmpresa", "filtro": "dEmpresa[E-mail do Gestor] = USERPRINCIPALNAME()"}]}
]
```

Cada regra é um filtro DAX booleano sobre uma tabela do modelo (as colunas são
conferidas). Vira `roles/<papel>.tmdl`; os membros de cada papel se configuram
no serviço (LEIA-ME). A coluna com o e-mail precisa estar no catálogo de uma
fonte, como qualquer outra. Funções do filtro são conferidas no dicionário.

## Versões e mudanças

Cada `aprovar` grava o retrato do painel aprovado e, a partir do segundo, a
lista do que mudou (indicador novo, fórmula alterada, visual que saiu…), que
vira o "Histórico de mudanças" do dicionário de indicadores.

```bash
python3 deidara.py diff argila.json                 # contra a última aprovação
python3 deidara.py diff argila.json --contra v1.json  # contra outro argila
```

Uma fórmula que muda é destacada ("FÓRMULA mudou (o número muda)"): avise
quem consome o painel antes de publicar. O `gerar` também recusa uma
aprovação feita com outra versão do Deidara.
