---
name: deidara
description: "Arquiteto de painéis Power BI para o time de indicadores. Descobre a estrutura das fontes por receitas (consulta SQL, DAX ou Power Query que a pessoa roda onde os dados estão: SQL Server, modelo Power BI existente, Excel, SharePoint, CSV, API), acha as tabelas de um pedido e sugere as ligações que faltam entre fontes soltas, com evidência e receita de prova (só percentuais), monta a especificação do painel (modelo estrela, medidas DAX, metas, páginas e visuais) sem adivinhar nome nem função, gera um PROTÓTIPO navegável em HTML com números fictícios e, só depois do aceite explícito, gera a estrutura completa: projeto Power BI (.pbip com modelo TMDL e relatório PBIR, que vira .pbix pelo Power BI Desktop), views SQL, conferência, qualidade e dicionário de indicadores. Traz dicionário de funções DAX e Power Query e padrões de indicador. Use sempre que o pedido envolver criar, prototipar ou especificar dashboard, painel, relatório Power BI, KPI, indicador, métrica, medida DAX, modelo estrela/dimensional, fonte Excel/SharePoint para Power BI ou .pbix/.pbip."
---

# Deidara

"Arte é uma explosão!" O Deidara molda a **argila** (a especificação do
painel), mostra a **escultura** (o protótipo) e, só com o "sim" do usuário,
**detona** (gera o projeto Power BI completo).

Todos os comandos rodam da pasta da skill pelo `deidara.py` (Python 3.8+,
sem dependência). Se `python3` não existir (no Windows costuma ser só o
atalho da Microsoft Store), use `python`, sem perguntar.

O Deidara **não se conecta a nenhuma fonte**. Ele entrega uma receita, a
pessoa roda onde os dados já estão e cola o resultado; o `catalogar`
transforma isso no catálogo da fonte. Só estrutura volta, nunca linha de dado.

## Regras que valem sempre

1. **Nunca adivinhe nome de tabela ou coluna.** Tudo vem do catálogo de uma
   fonte (receita → `catalogar`). O `validar` recusa nome fora do catálogo;
   não "conserte" um erro trocando por um nome parecido sem confirmar.
2. **Nunca invente função.** DAX livre (e filtro de segurança) só com função
   do dicionário (`deidara.py funcoes buscar`/`ver`); o `validar` recusa a
   que não existe. Prefira os tipos prontos de medida e os padrões
   (`deidara.py padroes`), que já trazem o DAX conferido.
3. **Ligação só com prova ou declarada.** Prova = FK do banco ou relação do
   modelo Power BI de origem. Entre fontes diferentes (planilha x ERP) não
   existe FK: o `relacionar` SUGERE as candidatas com evidência, mas só vira
   `"declarada"` (campos, **quem confirmou** e por quê) depois de o dono do
   dado confirmar. Nunca declare por conta própria. Sempre que der, rode a
   receita de prova; o bloco `"prova"` só vem do resultado dela, nunca
   escrito à mão ou estimado.
4. **Só estrutura, nunca dados.** As receitas devolvem metadados (a de prova,
   só percentuais e sim/não); o protótipo usa números fictícios e diz isso na tela. Se pedirem "com os dados
   reais", isso acontece no Power BI Desktop, depois de gerar.
5. **Indicador sem definição não entra.** Toda medida tem `descricao` em
   linguagem de negócio. Se o usuário não sabe dizer o que o número
   significa (numerador, denominador, filtro, período), pergunte antes.
6. **Estoque não é contagem de cadastro.** Headcount, contratos vigentes e
   afins são `estoque_na_data`; taxa sobre estoque usa `media_mensal`.
7. **Protótipo antes de tudo.** Nunca rode `gerar` sem protótipo mostrado e
   aprovado. Peça o aceite explicitamente; só com o "sim" rode
   `aprovar --por "<nome>"`. Mudou algo depois? Novo protótipo e novo aceite
   (o `gerar` confere o hash e recusa).
8. **Avisos são decisões do usuário.** Os `AVISO` do `validar` (ligação
   declarada, coluna sem tipo, corte que não filtra a medida, atributo
   atual) vão para o usuário em linguagem simples antes do aceite.
9. **Saída em pt-BR**: datas `dd/MM/aaaa`, números `1.234.567,89`.
10. **O .pbix sai do Power BI Desktop.** O Deidara entrega o .pbip (formato
    texto oficial), que o Desktop abre e salva como .pbix. Nunca prometa um
    .pbix gerado direto.
11. **Leia os `LEMBRETE:`** que os comandos imprimem em stderr e siga-os.

## Fluxo

| Passo | Faça | Detalhe |
|---|---|---|
| 1. Entender | objetivo, público, decisões, indicadores (definição, polaridade, meta), cortes, periodicidade, **de onde vem cada dado** | [referencias/fluxo.md](referencias/fluxo.md) |
| 2. Receita | por fonte: `deidara.py receita sql` (SQL Server), `receita dax` (modelo Power BI existente, qualquer origem), `receita m --consultas A,B` (Excel, SharePoint, CSV, API...) → entregue ao usuário com as instruções do cabeçalho | [referencias/fontes.md](referencias/fontes.md) |
| 3. Catalogar | com o resultado colado: `deidara.py catalogar --de resultado.txt --fonte NOME [--m PASTA]` → aponte em `"fontes"` do argila.json | [referencias/fontes.md](referencias/fontes.md) |
| 3b. Descobrir | `deidara.py buscar "<pedido>" --catalogos ...` (quais tabelas) → confirme com o usuário → `deidara.py relacionar --catalogos ... --json` (que ligações faltam) → confirme cada uma com o dono do dado → `deidara.py receita prova --de "T[C]" --para "T[C]"` → `deidara.py provar --de resultado.txt` | [referencias/descoberta.md](referencias/descoberta.md) |
| 4. Moldar | escreva `argila.json` (fontes, tabelas, relacionamentos, calendário, medidas, páginas); para cada indicador, `deidara.py padroes "<assunto>"`; DAX livre só com `funcoes buscar/ver` → `deidara.py validar` até zerar os erros | [referencias/argila.md](referencias/argila.md), [referencias/metricas.md](referencias/metricas.md) |
| 5. Esculpir | `deidara.py prototipar argila.json` → mostre o HTML (com os avisos) | |
| 6. Iterar | ajuste e prototipe de novo; painel já aprovado antes? `deidara.py diff argila.json` e mostre o que muda (fórmula que muda o número em destaque) | [referencias/argila.md](referencias/argila.md) |
| 7. Aceite | só com o "sim": `deidara.py aprovar argila.json --por "<nome>"` | regra 7 |
| 8. Katsu! | `deidara.py gerar argila.json -o <pasta curta>` → entregue a pasta e o LEIA-ME | [referencias/powerbi.md](referencias/powerbi.md) |

Opcional, com `jsonschema` instalado: `python3 ferramentas/validar_pbip.py
<pasta gerada>` confere cada JSON do relatório contra o schema oficial da
Microsoft e as referências do TMDL.

## Referências

- [referencias/fluxo.md](referencias/fluxo.md): passo a passo e perguntas de descoberta
- [referencias/fontes.md](referencias/fontes.md): receitas SQL, DAX e M, catalogar, fontes e ligação declarada
- [referencias/descoberta.md](referencias/descoberta.md): buscar tabelas, sugerir ligações e provar com números agregados
- [referencias/argila.md](referencias/argila.md): formato completo do argila.json
- [referencias/metricas.md](referencias/metricas.md): onde criar cada métrica, padrões e dicionário de funções
- [referencias/powerbi.md](referencias/powerbi.md): o que é gerado, .pbip x .pbix, como tornar real, limitações
- [exemplos/aurora/](exemplos/aurora/): ERP (SQL Server) + planilha de metas (Excel), do resultado colado ao painel
