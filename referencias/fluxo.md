# Fluxo do Deidara (passo a passo)

Carregado sob demanda pelo `SKILL.md`. Comandos rodados da pasta da skill.

## Passo 1 — Entender o painel antes de abrir o banco

Um painel bom responde a decisões, não a tabelas. Antes de buscar qualquer
coisa, feche com o usuário (em poucas perguntas, não um formulário):

1. **Objetivo e público.** Quem abre o painel e que decisão toma com ele?
   ("o gestor de RH decide onde agir sobre turnover")
2. **Indicadores.** Para cada um: o que conta, o que divide, que filtro vale
   (ativos? só CLT?), o período (mês, acumulado no ano, últimos 12 meses), se
   maior é melhor ou pior (`polaridade`) e se há meta.
3. **Cortes.** Por quais dimensões o usuário quer abrir os números (cargo,
   empresa, motivo, mês). Cada corte vira um relacionamento que precisa de
   prova no Vegapunk.
4. **Páginas.** Normalmente uma visão geral (cartões + 2–3 gráficos) e uma
   página por tema. Mais de 12 visuais por página é sinal para dividir.

Se o indicador já existe em outro painel ou planilha, peça a definição de lá:
número igual com definição diferente é o pior defeito de um painel.

## Passo 2 — Descobrir as tabelas (Vegapunk)

```bash
python3 <vegapunk>/stella.py buscar --dominio schema "desligamentos por motivo e cargo"
python3 deidara.py coletar --vegapunk <vegapunk> F_DESLIGAMENTO F_FUNCIONARIO F_CARGO -o meu_painel/schema.json
```

Siga o fluxo de schema do Vegapunk (Passo 1.5: desconfie de tabela
staging/temporária no topo; ambiguidade se confirma com o usuário). O
`coletar` recusa tabela que o Vegapunk não conhece.

O `schema.json` traz só estrutura: colunas, descrições, tipos, PK e FKs com
a prova do agrupamento. Pode ir para o repositório do painel? **Não** se o
schema for de um sistema de terceiros com licença restrita: trate como o
`egghead/` do Vegapunk (ver AVISO.md dele).

## Passo 3 — Moldar a argila

Escreva `meu_painel/argila.json` ([argila.md](argila.md)). Escolhas que o
usuário não precisa fazer, mas você precisa acertar:

- **Fato x dimensão.** Fato = evento ou movimento (desligamento, marcação,
  lançamento); dimensão = cadastro (cargo, empresa, motivo). Uma tabela de
  cadastro que também é medida (colaboradores → headcount) pode ser
  dimensão com medida de contagem.
- **Relacionamento.** `"de"` é sempre o lado muitos (a filha da FK) e
  `"para"` o lado um (a mãe). Se o `validar` disser que a FK está invertida,
  inverta.
- **Calendário.** Toda análise no tempo passa por `calendario`; uma data por
  tabela é a ativa, as outras ficam `"ativo": false`.
- **Medidas.** Prefira os tipos prontos (`agregacao`, `divisao`, tempo) ao
  DAX livre: eles geram a consulta de conferência e a validação é completa.

```bash
python3 deidara.py validar meu_painel/argila.json
```

Zere os erros. Os avisos ficam para o usuário decidir no Passo 4.

## Passo 4 — Esculpir o protótipo

```bash
python3 deidara.py prototipar meu_painel/argila.json
```

Gera `argila.prototipo.html`: páginas na mesma posição que vão para o Power
BI, modelo de dados com a prova de cada ligação, dicionário de indicadores e
a aba Pendências (os avisos). Mostre ao usuário (abrir o arquivo no
navegador; em Claude Code, publicar como artifact ajuda a compartilhar com o
time) e pergunte o que mudar. Lembre: números fictícios.

## Passo 5 — Aceite

Só com o "sim" explícito:

```bash
python3 deidara.py aprovar meu_painel/argila.json --por "Nome de quem aprovou"
```

Grava `argila.aprovacao.json` com o hash do argila e do schema e os avisos
aceitos. Mudou qualquer vírgula depois? O `gerar` recusa: protótipo de novo
e novo aceite.

## Passo 6 — Katsu!

```bash
python3 deidara.py gerar meu_painel/argila.json [-o PASTA]
```

Entregue ao usuário, em linguagem simples: (a) o que foi gerado; (b) o
passo a passo do LEIA-ME (views → abrir .pbip → parâmetros → atualizar →
conferir → salvar como .pbix → publicar); (c) as pendências aceitas. No
Windows, prefira uma pasta de saída curta (ex.: `C:\paineis\<nome>`): o
caminho completo dos arquivos do .pbip passa fácil do limite de 260
caracteres.

## Passo 7 — Fechar o laço no Vegapunk

Para cada tabela usada: `stella.py confirmar --dominio schema "<pedido>"
TABELA`. É o que recalibra a busca dele.
