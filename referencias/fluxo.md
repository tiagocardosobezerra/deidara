# Fluxo do Deidara (passo a passo)

Carregado sob demanda pelo `SKILL.md`. Comandos rodados da pasta da skill.

## Passo 1 — Entender o painel antes de abrir qualquer fonte

Um painel bom responde a decisões, não a tabelas. Antes de buscar qualquer
coisa, feche com o usuário (em poucas perguntas, não um formulário):

1. **Objetivo e público.** Quem abre o painel e que decisão toma com ele?
   ("o gestor de RH decide onde agir sobre turnover")
2. **Indicadores.** Para cada um: o que conta, o que divide, que filtro vale
   (ativos? só CLT?), o período (mês, acumulado no ano, últimos 12 meses), se
   maior é melhor ou pior (`polaridade`) e se há meta.
3. **Cortes.** Por quais dimensões o usuário quer abrir os números (cargo,
   empresa, motivo, mês). Cada corte vira um relacionamento que precisa de
   prova na fonte (ou ser declarado por quem conhece o dado).
4. **Origem de cada dado.** Banco (qual), modelo Power BI que já existe,
   planilha, lista do SharePoint? É isso que decide a receita.
5. **Páginas.** Normalmente uma visão geral (cartões + 2–3 gráficos) e uma
   página por tema. Mais de 12 visuais por página é sinal para dividir.

Se o indicador já existe em outro painel ou planilha, peça a definição de lá:
número igual com definição diferente é o pior defeito de um painel.

## Passo 2 — Receita e catálogo de cada fonte

```bash
python3 deidara.py receita sql --esquema dbo --tabelas F_DESLIGAMENTO,F_FUNCIONARIO -o receita_erp.sql
python3 deidara.py receita m --consultas Metas -o receita_metas.pq
```

Mande a receita para quem tem acesso à fonte (o cabeçalho explica como
rodar e copiar). Com o resultado colado num `.txt`:

```bash
python3 deidara.py catalogar --de erp.txt --fonte erp -o meu_painel/catalogos/erp.json
python3 deidara.py catalogar --de metas.txt --fonte metas --m pasta_dos_m -o meu_painel/catalogos/metas.json
```

Leia os avisos do `catalogar` com o usuário (coluna sem tipo, coluna
calculada que ficou de fora). Detalhes: [fontes.md](fontes.md).

O catálogo traz só estrutura. Pode ir para o repositório do painel? **Não**
se a estrutura for de um sistema de terceiros com licença restrita.

## Passo 3 — Moldar a argila

Escreva `meu_painel/argila.json` ([argila.md](argila.md)). Escolhas que o
usuário não precisa fazer, mas você precisa acertar:

- **Fato x dimensão.** Fato = evento ou movimento (desligamento, marcação,
  lançamento); dimensão = cadastro (cargo, empresa, motivo). Uma tabela de
  cadastro que também é medida (colaboradores → headcount) pode ser
  dimensão com medida de contagem.
- **Relacionamento.** `"de"` é sempre o lado muitos (a filha da FK) e
  `"para"` o lado um (a mãe). Se o `validar` disser que a FK está invertida,
  inverta. Entre fontes diferentes, só `"declarada"`, depois de confirmar os
  campos com o dono do dado ([fontes.md](fontes.md)).
- **Calendário.** Toda análise no tempo passa por `calendario`; uma data por
  tabela é a ativa, as outras ficam `"ativo": false`.
- **Medidas.** Comece por `deidara.py padroes "<assunto>"`. Prefira os tipos
  prontos (`agregacao`, `divisao`, tempo, estoque) ao DAX livre: eles geram a
  consulta de conferência e a validação é completa. DAX livre só com funções
  do dicionário (`deidara.py funcoes buscar`); ver [metricas.md](metricas.md).

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

Grava `argila.aprovacao.json` com o hash do argila e dos catálogos e os avisos
aceitos. Mudou qualquer vírgula depois? O `gerar` recusa: protótipo de novo
e novo aceite.

## Passo 6 — Katsu!

```bash
python3 deidara.py gerar meu_painel/argila.json [-o PASTA]
```

Entregue ao usuário, em linguagem simples: (a) o que foi gerado; (b) o
passo a passo do LEIA-ME (views das fontes SQL → abrir .pbip → parâmetros e
credenciais → atualizar → conferir → salvar como .pbix → publicar); (c) as
pendências aceitas, com destaque para as ligações declaradas. No
Windows, prefira uma pasta de saída curta (ex.: `C:\paineis\<nome>`): o
caminho completo dos arquivos do .pbip passa fácil do limite de 260
caracteres.
