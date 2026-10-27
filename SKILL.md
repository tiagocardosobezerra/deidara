---
name: deidara
description: "Arquiteto de painéis Power BI para o time de indicadores. Parte da estrutura real do banco (descoberta pelo Vegapunk, nunca adivinhada), monta a especificação do painel (modelo estrela, medidas DAX, páginas e visuais), gera um PROTÓTIPO navegável em HTML com números fictícios para validação e, só depois do aceite explícito do usuário, gera a estrutura completa: projeto Power BI (.pbip com modelo TMDL e relatório PBIR, que vira .pbix pelo Power BI Desktop), views SQL, consultas de conferência e dicionário de indicadores. Use sempre que o pedido envolver criar, prototipar ou especificar dashboard, painel, relatório Power BI, KPI, indicador, métrica, medida DAX, modelo estrela/dimensional ou .pbix/.pbip."
---

# Deidara

"Arte é uma explosão!" O Deidara molda a **argila** (a especificação do
painel), mostra a **escultura** (o protótipo) e, só com o "sim" do usuário,
**detona** (gera o projeto Power BI completo).

Todos os comandos rodam da pasta da skill pelo `deidara.py` (Python 3.8+,
sem dependência). Se `python3` não existir (no Windows costuma ser só o
atalho da Microsoft Store), use `python`, sem perguntar.

O Deidara **depende do Vegapunk** para a estrutura do banco: nome de tabela,
coluna, tipo e ligação vêm do `stella.py detalhar --json`. O Vegapunk fica
na pasta indicada por `VEGAPUNK_DIR` ou em `--vegapunk`.

## Regras que valem sempre

1. **Nunca adivinhe nome de tabela ou coluna.** Descubra pelo Vegapunk
   (`stella.py buscar` → escolha → `deidara.py coletar`). O `validar` recusa
   qualquer nome que não veio do `detalhar`; não "conserte" um erro trocando
   o nome por um parecido sem confirmar com o usuário.
2. **Relacionamento só com prova.** O Deidara usa a FK de agrupamento provado
   do Vegapunk. Ligação sem prova é erro; `"aceitar_sem_prova": true` só
   depois de o usuário confirmar os campos.
3. **Só estrutura, nunca dados.** Nenhuma linha do banco entra no protótipo
   nem na geração. Os números do protótipo são fictícios e isso é dito na
   tela. Se o usuário pedir "com os dados reais", explique que isso acontece
   no Power BI Desktop, depois de rodar as views.
4. **Indicador sem definição não entra.** Toda medida tem `descricao` em
   linguagem de negócio. Se o usuário não sabe dizer o que o número
   significa (numerador, denominador, filtro, período), pergunte antes.
5. **Protótipo antes de tudo.** Nunca rode `gerar` sem um protótipo
   mostrado e aprovado. Peça o aceite explicitamente ("Aprova este
   protótipo para eu gerar o projeto Power BI?"); só com o "sim" rode
   `aprovar --por "<nome>"`. Qualquer mudança depois disso pede novo
   protótipo e novo aceite (o `gerar` confere o hash e recusa).
6. **Indicador de estoque não é contagem de cadastro.** Headcount, contratos
   vigentes e afins são `estoque_na_data` (entradas até a data menos saídas
   até a data); taxa sobre estoque usa a média do período (`media_mensal`).
   Contar a tabela de cadastro inteira mistura ativos e desligados.
7. **Avisos são decisões do usuário.** Os `AVISO` do `validar` (data sem
   tipo, chave que não cobre a PK, coluna que não filtra a medida) vão para
   o usuário em linguagem simples antes do aceite; não os esconda.
8. **Saída em pt-BR**: datas `dd/MM/aaaa`, números `1.234.567,89`.
9. **O .pbix sai do Power BI Desktop.** O formato .pbix é binário e
   fechado; o Deidara entrega o .pbip (formato texto oficial do Power BI),
   que o Desktop abre e salva como .pbix. Diga isso com clareza; nunca
   prometa um .pbix gerado direto.
10. **Leia os `LEMBRETE:`** que os comandos imprimem em stderr e siga-os.

## Fluxo

| Passo | Faça | Detalhe |
|---|---|---|
| 1. Entender | objetivo do painel, público, decisões que ele apoia, indicadores (definição, polaridade, meta), cortes (por quê?), periodicidade | [referencias/fluxo.md](referencias/fluxo.md), Passo 1 |
| 2. Descobrir | Vegapunk: `stella.py buscar --dominio schema "<assunto>"` → escolha as tabelas → `python3 deidara.py coletar --vegapunk DIR TAB1 TAB2 ... -o projeto/schema.json` | Passo 2 |
| 3. Moldar | escreva `projeto/argila.json` (tabelas fato/dimensão, relacionamentos, calendário, medidas, páginas) → `python3 deidara.py validar projeto/argila.json` até zerar os erros | [referencias/argila.md](referencias/argila.md) |
| 4. Esculpir | `python3 deidara.py prototipar projeto/argila.json` → mostre o HTML ao usuário (abrir no navegador ou publicar), com os avisos | Passo 4 |
| 5. Iterar | ajuste o argila.json com o retorno do usuário → `prototipar` de novo; painel já aprovado antes? `deidara.py diff projeto/argila.json` e mostre as mudanças (fórmula que muda o número em destaque) | [referencias/argila.md](referencias/argila.md), "Versões e mudanças" |
| 6. Aceite | só com o "sim": `python3 deidara.py aprovar projeto/argila.json --por "<nome>"` | regra 5 |
| 7. Katsu! | `python3 deidara.py gerar projeto/argila.json` → entregue a pasta e o LEIA-ME | [referencias/powerbi.md](referencias/powerbi.md) |
| 8. Fechar | `stella.py confirmar --dominio schema "<pedido>" TABELA` no Vegapunk para cada tabela usada | regra 5 do Vegapunk |

Opcional, quando houver `jsonschema` instalado: `python3
ferramentas/validar_pbip.py <pasta gerada>` confere cada JSON do relatório
contra o schema oficial da Microsoft e as referências do TMDL.

## Referências

- [referencias/fluxo.md](referencias/fluxo.md): o passo a passo com as perguntas de descoberta
- [referencias/argila.md](referencias/argila.md): formato completo do argila.json
- [referencias/powerbi.md](referencias/powerbi.md): o que é gerado, .pbip x .pbix, como tornar real, limitações
- [exemplos/aurora/](exemplos/aurora/): exemplo completo sobre o schema fictício do Vegapunk
