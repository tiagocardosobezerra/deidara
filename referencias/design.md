# Design de painéis

Como o Deidara pensa o visual de um painel, e o que levar ao usuário quando a
conversa chega em "como vai ficar". Escrito a partir do estudo do repositório
[Power BI Design Files](https://github.com/Dashboard-Design/Power-BI-Design-Files),
de Sajjad Ahmadi (licença MIT): os princípios e as técnicas foram reescritos
para o Deidara, sem copiar arquivos. Técnicas prontas: `deidara.py visuais`.
Medidas que desenham imagem: [svg.md](svg.md).

## Os princípios

1. **Comece pela decisão.** Um painel existe para alguém decidir alguma coisa.
   Antes de qualquer gráfico, a `descricao` do painel diz que decisão ele
   apoia, e o `publico` diz quem decide. Se a pessoa não sabe dizer, o painel
   ainda não está pronto para ser desenhado.
2. **Mostre o porquê, não só o quê.** O cartão diz que o turnover subiu; a
   página precisa deixar o gestor descobrir onde (empresa, cargo, motivo).
   Cada indicador principal ganha pelo menos um corte que explica a variação.
3. **Interação com propósito.** Segmentador, detalhamento e navegação só
   entram quando encurtam o caminho até a resposta. Filtro que ninguém usa é
   ruído e mais um lugar para o número parecer errado.
4. **Design faz parte da análise.** Posição, tamanho, cor e texto decidem o
   que é lido primeiro. O mais importante fica em cima e à esquerda, maior; o
   detalhe fica embaixo.
5. **Reaproveite.** Tema, padrões de medida e técnicas de visual valem para o
   próximo painel. O Memory Card guarda o que deu certo.

## A página

O Deidara posiciona os visuais na mesma ordem no protótipo e no `.pbip`
(página 16:9, 1280 x 720, que cresce para baixo quando precisa):

| Faixa | O que vai | Por quê |
|---|---|---|
| topo | segmentadores | o contexto (período, empresa) antes dos números |
| logo abaixo | cartões e medidores | a resposta curta: o número e a meta |
| meio | gráficos, em duas colunas | a evolução e os cortes que explicam |
| fim | tabelas e matrizes | o detalhe para quem quer conferir |

Na conversa com o usuário:

- **Uma página, uma pergunta.** "Visão geral" responde "como estamos?";
  "Turnover" responde "onde está o problema?". Página com tudo não responde
  nada.
- **Poucos cartões.** Até cinco ou seis no topo. Mais que isso, ninguém lê.
- **Cada gráfico com um título que diz o que mostra** ("Desligamentos por
  motivo"), e não o nome técnico da medida.
- **Análise de causa numa página própria.** Árvore de decomposição, Pareto e
  melhores e piores pedem espaço e atenção.

## Cor

- **Cor significa alguma coisa.** Verde e vermelho são só para bateu ou não
  bateu a meta, e o Deidara já respeita a polaridade (no turnover, subir é
  ruim). Uma cor de destaque para chamar atenção; o resto em tons neutros.
- **Cor nunca é a única pista.** O protótipo mostra ✓/✗ ao lado do número;
  numa pílula de status, o texto diz a situação. Quem não distingue verde de
  vermelho precisa ler o painel do mesmo jeito.
- **Contraste.** O `validar` avisa quando o texto sobre o fundo do tema fica
  abaixo de 4,5:1 e quando uma cor de dados escolhida pelo time fica abaixo
  de 3:1 sobre o fundo.
- **Mesma cor, mesma coisa.** Se "Empresa A" é azul num gráfico, é azul em
  todos.

## Tema

O tema do relatório sai do bloco `"tema"` do `argila.json` (cores dos dados,
fundo e texto; ver [argila.md](argila.md)) e vai como tema personalizado no
`.pbip`. O que vale saber de temas do Power BI:

- o arquivo de tema é um JSON; além das cores (`dataColors`, fundo, texto,
  destaque de tabela), ele define classes de texto (título, rótulo, número de
  cartão) e o padrão de formatação de cada tipo de visual;
- um tema único para o time deixa todos os painéis com a mesma cara: defina
  uma vez e reaproveite no `"tema"` de cada `argila.json`;
- há geradores de tema e coleções da comunidade; use só tema cuja licença
  permita, e dê o crédito a quem fez.

O tema faz mais do que cor. Recursos que valem conhecer, todos editando o
JSON do tema no Power BI Desktop (o Deidara gera só cores e classes de texto):

- **Cores de sentimento** (`good`, `neutral`, `bad`) e de divergência
  (`maximum`, `center`, `minimum`): a formatação condicional usa essas cores
  por padrão, e o time inteiro fica com o mesmo verde e o mesmo vermelho.
- **Padrão de cada visual** (`visualStyles`): fonte, borda, rótulos e
  segmentador iguais em todo relatório, sem formatar visual por visual.
- **Predefinições de estilo** (style presets): variações nomeadas de um
  visual dentro do tema (cartão de destaque, cartão discreto) que quem monta
  o relatório escolhe numa lista.
- **Ícones próprios** (`icons`): ícones SVG no tema para os conjuntos de
  ícones da formatação condicional, no lugar dos ícones de fábrica.
- **Cores do tema por nome**: na formatação condicional por valor de campo, a
  medida pode devolver o nome de uma cor do tema em vez do código; trocar o
  tema troca a cor sem mexer na medida. Confira na versão do Power BI Desktop
  do time antes de depender disso.
- **Tema da organização**: o administrador do Power BI pode publicar temas
  para toda a organização, que aparecem na galeria de temas de todos. É o
  caminho para o tema único do time sem copiar arquivo.

## Visuais nativos primeiro

Os visuais nativos rendem muito mais do que o padrão sugere (veja `deidara.py
visuais`):

- o **segmentador de botões** vira controle segmentado (mês, trimestre, ano)
  ou cartões de KPI clicáveis;
- a **tabela** recebe barras contra a meta, pílulas de status e setas de
  variação desenhadas por medida SVG;
- a **árvore de decomposição** leva do número geral até a causa;
- o **Azure Maps** aceita marcador desenhado por medida SVG.

**Causa raiz.** Para explicar uma variação, o dashboard Root Cause Analysis
do Power BI Design Files junta quatro jeitos de olhar o mesmo número, e o
Deidara gera os quatro com visual nativo:

- a **espinha de peixe** (`svg_espinha`): numa imagem só, onde o indicador
  está pior que a média em cada corte;
- o **jitter plot** (`jitter`): todos os itens de um corte como pontos, para
  achar quem está fora da curva; uma dispersão por corte, lado a lado;
- o **ranking de impacto** (`impacto`): quem mais subiu e quem mais desceu o
  indicador entre os dois períodos, em verde e vermelho;
- a **árvore de decomposição**, para abrir o número corte a corte.

**Visual personalizado** só quando o nativo não resolve, e com três cuidados:
o administrador do Power BI precisa liberar o visual; prefira a versão
certificada; e alguém do time precisa saber manter. O Deidara gera dois
quando pedidos (HTML Content e Deneb). Os outros do catálogo (Chord, Word
Cloud, Violin Plot, Gantt e Play Axis; `deidara.py visuais personalizado`) ele
só descreve: monte no Power BI Desktop sobre o modelo gerado e registre no
LEIA-ME qual foi usado e por quê.

## Antes do Power BI

O protótipo do Deidara é o esboço do layout: o gestor aprova a disposição, os
indicadores e a navegação com números fictícios, antes de alguém abrir o
Power BI Desktop. Quem quiser ir além no visual pode desenhar em ferramenta de
design (Figma, por exemplo) a partir da página aprovada; a estrutura (o que
fica em cada faixa) continua a do `argila.json`.
