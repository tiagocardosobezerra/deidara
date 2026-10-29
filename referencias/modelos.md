# Modelos de layout

Um modelo decide onde cada visual fica, desenha o fundo da página (painéis,
título, navegação) e põe os visuais nativos transparentes por cima. É a
técnica dos dashboards do repositório
[Power BI Design Files](https://github.com/Dashboard-Design/Power-BI-Design-Files),
de Sajjad Ahmadi (licença MIT; ver [LICENCAS-DE-TERCEIROS.md](../LICENCAS-DE-TERCEIROS.md)):
a estrutura de onze páginas dele virou os onze modelos abaixo. O fundo é
desenhado pelo Deidara para cada painel, com o nome e a pergunta da página e
as cores do tema; as imagens originais não vêm junto.

```json
{"projeto": "Turnover contra a meta", "modelo": "faixa-de-kpis", ...}
```

Sem `"modelo"`, o painel usa o layout simples (`padrao`, 1280 x 720). O
`esbocar` já escreve `"modelo": "faixa-de-kpis"`. Lista: `deidara.py modelos`.

## Os onze

| Modelo | Como é | Bom para | Vem de |
|---|---|---|---|
| `faixa-de-kpis` | trilho de ícones das páginas, título com os filtros no canto, linha de cartões, gráficos em grade ao lado das tabelas | visão geral ("como estamos?") | Agents Performance |
| `coluna-de-kpis` | barra de filtros no topo, coluna de cartões à esquerda, grade de gráficos (o primeiro maior), abas das páginas no rodapé | painel de várias páginas percorridas em ordem | IT Support Performance |
| `secoes-com-rolagem` | barra lateral com título, cartões, filtros e a lista de páginas; o primeiro gráfico no topo e cada outro visual numa seção com cabeçalho; a página rola | detalhe para quem confere linha a linha | Ecommerce Conversion |
| `trilho-escuro` | trilho escuro com as páginas, faixa única de cartões, gráficos de dois em dois e tabelas largas | painel operacional | Inventory Analysis |
| `kpis-clicaveis` | menu de páginas à esquerda e faixa de cartões clicáveis: o cartão escolhido muda o gráfico principal e a tabela principal; o resto vai para um painel de detalhe à direita | vários indicadores no mesmo formato | Interactive Dashboard Tour |
| `historia-longa` | uma página alta e escura: título do painel, filtros, e cada página do `argila.json` vira uma seção numerada (cartões, depois gráficos e tabelas de dois em dois), com a conclusão (`descricao` do painel) no fim | apresentação para diretoria | The Movie Success Matrix |
| `executivo` | linha de até cinco KPIs, um gráfico principal (linha, área ou colunas) em largura total e o resto embaixo | diretoria acompanhando a tendência | Executive Sales Report |
| `mapa-central` | o mapa (ou o gráfico principal) no centro, KPIs à esquerda, até três minigráficos à direita, tabelas embaixo | leitura por território | GeoSales (Azure Maps) |
| `causa-raiz` | coluna de filtros, linha de KPIs e a árvore de decomposição (ou o gráfico principal) em destaque, com o detalhe embaixo | investigar a causa de uma variação | Root Cause Analysis |
| `tabela-lateral` | faixa de KPIs, gráficos à esquerda e uma tabela alta à direita | acompanhamento com conferência linha a linha | Performance for CEO e IT Support (página 3) |
| `equipes` | painel lateral colorido com KPIs, filtros e páginas; minigráficos no topo e o gráfico principal grande (a dispersão, se houver) | desempenho de equipes e pessoas | Sales Teams Quarterly Performance |

## Como cada visual é encaixado

O modelo separa os visuais da página em filtros (segmentadores), cartões
(cartão e medidor), gráficos e tabelas (tabela e matriz), e põe cada grupo na
sua região, na ordem em que aparecem no `argila.json`. A página cresce para
baixo quando os visuais não cabem; nada é cortado.

## A formatação vem junto

Cada modelo leva a formatação dos visuais do dashboard de onde veio (`dicionario/estilos.json`): fontes,
tamanhos, cores de texto, cantos, espaçamentos, rótulos, eixos e o estilo de cartões, segmentadores, tabelas
e gráficos. Do original sai só formatação: nada que dependa dos campos dele, imagem ou link. Cada propriedade
é conferida contra o schema da Microsoft que o Deidara usa, e a que não passa fica de fora. O layout
`padrao` continua com a formatação de fábrica do Power BI.

## O que muda no Power BI

- **Página de 1920 x 1080**, como nos modelos de origem, com letras maiores no
  tema (título 16, número de cartão 44).
- **Fundo da página**: um SVG por página (`StaticResources/RegisteredResources/
  fundo_*.svg`), registrado como imagem do relatório.
- **Visuais sem fundo próprio**: o painel é o desenho do fundo.
- **Navegação**: botões transparentes (Navegação de página) sobre o desenho
  do trilho, das abas, da lista ou do menu.
- **KPIs clicáveis**: cada cartão leva a uma página escondida com o gráfico e
  a tabela daquele KPI (uma página por cartão). É navegação nativa, sem
  parâmetro de campo: funciona em qualquer versão do Power BI. Mudou um
  visual da página? Todas as variações mudam junto, porque saem da mesma
  página do `argila.json`.
- **História longa**: sem `"tema"` próprio, o painel ganha o tema escuro
  (fundo `#0F1420`, texto `#E6EAF2` e cores claras para os dados).

## Cuidados

- Se mexer na posição de um visual no Power BI Desktop, o desenho do fundo não
  acompanha. Para mudar o layout, mude o `argila.json` e gere de novo.
- No celular, o protótipo empilha os visuais e esconde o fundo; no Power BI,
  monte a exibição para celular à parte se o painel for usado no telefone.
