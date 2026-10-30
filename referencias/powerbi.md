# O que o `gerar` entrega e como vira painel de verdade

## .pbix x .pbip

O **.pbix** é um arquivo binário fechado: o modelo de dados vai dentro dele
num formato interno do Analysis Services, que só o Power BI Desktop escreve.
Nenhuma ferramenta fora do Desktop gera um .pbix válido de forma suportada.

O **.pbip** (Projeto do Power BI) é o formato texto oficial da Microsoft para
o mesmo conteúdo, feito para git e para geração automática:

```
Painel.pbip                      aponta para o relatório
Painel.SemanticModel/            o modelo, em TMDL (um arquivo por tabela)
  definition.pbism
  definition/database.tmdl, model.tmdl, expressions.tmdl, relationships.tmdl
  definition/tables/*.tmdl       colunas, medidas, partição (Power Query)
Painel.Report/                   o relatório, em PBIR (um JSON por página e visual)
  definition.pbir
  definition/report.json, version.json, pages/...
  StaticResources/RegisteredResources/Deidara.json   o tema
```

O Desktop abre o .pbip e, em *Arquivo > Salvar como*, grava o .pbix. Essa é
a ponte. O .pbip continua sendo a fonte: versionável, revisável em pull
request e regenerável pelo Deidara.

## Como o Deidara garante que abre

- Todo JSON do relatório leva o `$schema` público da Microsoft e é
  conferido contra ele por `ferramentas/validar_pbip.py` (inclusive a
  configuração interna de cada visual).
- O TMDL é conferido estruturalmente (tabulação, referências de
  relacionamento a colunas que existem, `ref table`).
- Todo campo usado num visual existe no modelo.

Testado no Power BI Desktop 2.159 (outubro de 2026) com o projeto de
demonstração no modelo `faixa-de-kpis`: o projeto abre, atualiza, calcula as
medidas (inclusive estoque na data, meta e as medidas SVG), mostra o fundo
desenhado e reconhece os botões como navegação de página.

O que **não** dá para provar sem o Desktop: que a versão do Power BI da
máquina do usuário aceita o formato PBIR (versões anteriores a 2024 pedem a
opção em versão prévia) e que as views rodam no banco real. Por isso o
LEIA-ME começa pelo SQL e pela homologação.

## Projeto de demonstração (`--demo`)

`deidara.py gerar argila.json -o PASTA --demo` gera o mesmo projeto com a
origem de cada tabela trocada por linhas fictícias escritas no próprio
`.pbip` (`#table` do Power Query): 8 linhas por dimensão, algumas centenas na
tabela de pessoas e nos eventos, uma meta por empresa. Chaves batem entre as
tabelas, cada evento acontece uma vez por pessoa e depois da entrada dela, e
nada passa de hoje. Medidas, relacionamentos e páginas são os do projeto
real: abra no Power BI Desktop, clique em **Atualizar** e todos os números são
calculados de verdade, sem banco nenhum. O fundo das páginas leva o selo
"Demonstração · dados fictícios" e o LEIA-ME começa avisando. Para o painel
real, gere de novo sem `--demo`.

## Como cada fonte é lida

**SQL Server.** `sql/<fonte>/01_views.sql` cria uma view por tabela do modelo
no schema `bi`, já com os nomes amigáveis, as chaves compostas concatenadas e
as datas do calendário sem hora. O Power BI lê só as views, por dois
parâmetros (`<fonte>_Servidor`, `<fonte>_Banco`). Vantagens: o DBA revisa um
arquivo; mudar a origem não quebra o painel; permissão de leitura num schema
só. `02_conferencia.sql` traz o total de cada indicador direto no banco (geral
e por ano) e `03_qualidade.sql`, as checagens que derrubam ou distorcem a
atualização.

**Power BI existente / Power Query (Excel, SharePoint, CSV, API...).** A
partição reaproveita a consulta de origem que veio no catálogo e acrescenta
seleção, nomes, tipos e chave composta. Parâmetros e consultas auxiliares
dela vão para `expressions.tmdl`. A homologação é contra a própria fonte.

## Limitações conhecidas (versão atual)

- Modo de importação (Import) apenas; DirectQuery fica para depois.
- Sem parâmetros de campo: configure no Desktop depois de gerar, e não
  regenere por cima. Segurança por linha (`seguranca`), detalhamento
  (`"detalhe"`), páginas de dica (`"dica"`) e grupo de cálculo de tempo
  (`"grupo_calculo"`) saem prontos ([argila.md](argila.md)).
- Status de meta é por cor (verde/vermelho); ícones e faixas de tolerância ficam para depois.
- Visuais nativos, mais HTML Content e Deneb quando pedidos (`deidara.py
  visuais`); os outros visuais do AppSource o Deidara só descreve.
