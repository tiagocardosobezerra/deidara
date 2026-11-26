# Experiência do painel

Este guia mostra como o painel conduz quem lê, da primeira pergunta até a ação. Ele vem depois de
[design.md](design.md), que trata da página, da cor e do tema. Aqui o assunto é o caminho do leitor.
O texto é do Deidara. As ideias seguem as fontes citadas em cada parte e no fim, e nada delas foi
copiado (ver [LICENCAS-DE-TERCEIROS.md](../LICENCAS-DE-TERCEIROS.md)).

## 1. Jornada por persona

Antes de desenhar, pergunte à pessoa quem abre o painel, com que frequência e o que faz depois.
A resposta fica em `publico` e na `descricao` do argila.json.

| Persona | Abre o painel para | Precisa ver primeiro | Termina em |
|---|---|---|---|
| diretoria | saber se está tudo bem | 3 a 5 números com a meta | uma pergunta ao gestor |
| gestor da área | achar onde está o problema | o corte que explica a variação | uma ação com responsável |
| analista | conferir e explicar | a tabela de detalhe e a definição | a resposta ao gestor |

Cada persona tem uma página de entrada própria, ou a mesma página com um caminho claro para o
detalhe. Painel que serve "para todo mundo" costuma não servir para ninguém. A Microsoft pede o
mesmo ao desenhar para um público definido
([Microsoft Learn, dicas de design de dashboards](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips)).

## 2. Uma página por pergunta, com título que é a pergunta

- Cada página responde a **uma** pergunta do gestor. O título da página é essa pergunta
  ("O turnover está na meta?", "Onde o custo da folha cresceu?"). Um rótulo genérico como
  "Visão geral" não serve.
- O título de cada visual também é uma pergunta ou uma afirmação que se confere
  ("Quais cargos puxam os desligamentos?").
- Logo abaixo do título vem uma **frase de leitura**: o que o leitor deve notar, em uma linha
  ("Três cargos somam 60% dos desligamentos do ano"). No protótipo a frase vem da conta fictícia.
  No Power BI, ela vira uma medida de texto ou um subtítulo, e nunca um número escrito à mão.

## 3. Os atos: diagnóstico, causa, ação, resultado

Um painel bom conta a história em quatro atos, nesta ordem de páginas ou de faixas:

1. **Diagnóstico**: como estamos contra a meta (cartões, medidor, linha no tempo).
2. **Causa**: onde e por quê (barras ordenadas, árvore de decomposição, `visuais causa`).
3. **Ação**: o que fazer e com quem (tabela de exceções com responsável, lista de casos).
4. **Resultado**: a ação funcionou? (antes e depois, sinal ou ruído no C4 Karura).

Essa estrutura de contexto, conflito e resolução vem de
[*Storytelling with Data*, de Cole Nussbaumer Knaflic](https://www.storytellingwithdata.com/books).
O livro é só uma referência citada e nada dele foi copiado. As regras de notação do
[IBCS](https://www.ibcs.com/) (International Business Communication Standards) levam ao mesmo
lugar: a mensagem vem antes do gráfico, e a mesma coisa tem sempre a mesma forma (real, plano,
ano anterior).

## 4. Navegação e detalhamento

- O caminho natural vai do resumo ao detalhe. Use detalhamento (*drillthrough*) do cartão ou da
  barra para a página de detalhe já filtrada
  ([Microsoft Learn, drillthrough](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-drillthrough)).
- Botões de navegação e indicadores mostram onde o leitor está e como voltar
  ([Microsoft Learn, indicadores](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-bookmarks)).
  Esta é a heurística "visibilidade do estado do sistema" e "controle e liberdade do usuário" de
  [Jakob Nielsen (Nielsen Norman Group, 10 heurísticas de usabilidade)](https://www.nngroup.com/articles/ten-usability-heuristics/).
- Use os mesmos filtros no mesmo lugar em todas as páginas. A heurística "consistência e padrões"
  vale aqui: o leitor não deveria ter que aprender cada página de novo.

## 5. Dica de ajuda: o ⓘ do protótipo vira o ⓘ do Power BI

O leitor não deve precisar perguntar ao analista o que um número significa. A heurística "ajuda e
documentação" de Nielsen pede a explicação no lugar onde a dúvida aparece.

- No protótipo, cada visual com medida tem um ⓘ com o nome, a definição (`descricao`) e a meta
  de cada medida.
- No `.pbip`, o mesmo texto vai para a **dica de ajuda do cabeçalho do visual**:
  `visualContainerObjects.visualHeader` com `showTooltipButton` e `visualHeaderTooltip.text`.
  As duas saem da mesma função (`texto_de_ajuda` em `tecnicas/c1/prototipo.py`), por isso
  protótipo e Power BI não divergem. Quando o estilo do modelo esconde o cabeçalho, o Deidara liga
  só o cabeçalho e o botão da dica. Os outros botões ficam como o autor do estilo deixou. A dica
  que vinha do dashboard de origem sai. Segmentadores e visuais sem medida não ganham dica.
- A `descricao` de cada medida é, portanto, texto para o gestor: uma frase curta, sem DAX, que diz
  o que entra e o que fica de fora. Uma descrição vazia vira "Sem definição ainda." nos dois lados.
- A dica de página (`"dica"` no visual) e a página de ajuda (`"ajuda": true`) complementam o ⓘ.
  Elas servem para o contexto que não cabe numa frase
  ([Microsoft Learn, dicas de ferramenta de relatório](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-tooltips)).

## 6. Acessibilidade

Siga a lista de conferência da Microsoft
([Microsoft Learn, relatórios acessíveis](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports))
e as regras do WCAG 2.2:

- **Cor nunca é a única pista**
  ([WCAG 1.4.1, uso de cor](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)):
  status vem com ícone, seta ou texto ("▲ 3,2 p.p. acima da meta"), e não só verde ou vermelho.
  A linha da meta é tracejada e tem rótulo.
- **Contraste**
  ([WCAG 1.4.3, contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)):
  texto com pelo menos 4,5:1 contra o fundo, e 3:1 para texto grande. O Deidara confere o contraste
  do tema no protótipo ([design.md](design.md), "Cor").
  O `validar` avisa (`[Acessibilidade]`) em dois casos. O primeiro é a coluna de tabela ou matriz que
  mostra o status só pela cor da letra, sem a meta nem uma medida de status ao lado (`svg_pilula`,
  `svg_seta`, `svg_barra_meta`, `svg_variacao`, `svg_progresso`). O segundo é a barra colorida pelo
  status sem a linha da meta.
- **Eixo das barras no zero**: o comprimento da barra é o número. Uma barra que não nasce no zero
  exagera a diferença, e o FT Visual Vocabulary, o guia do Urban Institute e o guia do GOV.UK Analysis
  Function dizem o mesmo (links nas fontes). A `guarda` (`tecnicas/c3/guarda.py`) tira das barras e
  colunas o início fixo fora do zero e a escala logarítmica que venham do estilo de origem. Sem início
  fixo, o Power BI põe o zero no eixo das barras sozinho. Um tema de arquivo (`"tema": {"arquivo": ...}`)
  que fixe o eixo não passa pela `guarda`.
- **Texto alternativo**
  ([WCAG 1.1.1, conteúdo não textual](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)):
  cada visual do `.pbip` sai com `altText`, o que o leitor de tela diz dele. O texto traz o tipo, o
  título, as medidas e o corte, e a meta quando houver, em até 250 caracteres (`texto_alternativo` em
  `tecnicas/c1/prototipo.py`). O texto alternativo do dashboard de origem do estilo (em inglês, de outro
  assunto) é descartado.
- **Ordem de leitura**: a ordem de tabulação segue a ordem visual (o PBIR grava `tabOrder` na mesma
  ordem do protótipo).
- **Paleta para daltonismo**: no máximo 5 ou 6 cores de categoria. Para "bom" e "ruim", use o par
  azul e laranja em vez de verde e vermelho quando o público for amplo.

## 7. Antes de levar ao gestor

- [ ] Cada página tem uma pergunta no título e uma frase de leitura.
- [ ] Os atos aparecem na ordem: diagnóstico, causa, ação, resultado.
- [ ] Do resumo ao detalhe há no máximo dois cliques, e há como voltar.
- [ ] Toda medida em visual tem `descricao` para o ⓘ e para a dica do Power BI.
- [ ] Nenhuma informação depende só da cor, e o contraste passa.
- [ ] O `validar` não traz nenhum aviso `[Acessibilidade]`.

## Fontes

- Microsoft Learn: [dicas de design de dashboards](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips),
  [relatórios acessíveis](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports),
  [drillthrough](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-drillthrough),
  [dicas de ferramenta de relatório](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-tooltips),
  [indicadores](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-bookmarks).
- Jakob Nielsen, [10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics/)
  (Nielsen Norman Group). O uso é citado com o crédito e o link que a página pede.
- [IBCS, International Business Communication Standards](https://www.ibcs.com/).
- Cole Nussbaumer Knaflic, [*Storytelling with Data*](https://www.storytellingwithdata.com/books) (Wiley, 2015).
- W3C, WCAG 2.2: [1.1.1 Non-text Content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html),
  [1.4.1 Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html),
  [1.4.3 Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- Eixo das barras no zero: [FT Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary)
  (Financial Times, texto com todos os direitos reservados: só o link),
  [Urban Institute Data Visualization Style Guide](https://urbaninstitute.github.io/graphics-styleguide/),
  [GOV.UK Analysis Function, gráficos](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-charts/).
  As três são só citadas, e as regras foram escritas pelo Deidara.
