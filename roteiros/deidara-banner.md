# Roteiro: `deidara-banner.svg`

**Português** | [English](deidara-banner.en.md)

| | |
|---|---|
| Arquivos | `assets/deidara-banner.svg` (pt-BR) e `assets/deidara-banner-en.svg` |
| Onde | topo do `README.md` / `README.en.md`, logo depois dos selos |
| Tela | 1280 × 640, fundo `#0B1220`, grade de 32 px em `#1E2A44` |
| Duração | 48 s em laço, 6 cenas |
| `aria-label` / `alt` (pt) | Deidara: do pedido ao painel Power BI, com protótipo aprovado antes do projeto |
| `aria-label` / `alt` (en) | Deidara: from request to Power BI report, with an approved prototype before the project |
| Paralelo no Vegapunk | `vegapunk-banner.svg` (48 s, 6 cenas, mesmo arco) |

## A ideia em uma frase

Painel Power BI costuma dar errado de dois jeitos: alguém adivinha o nome da
coluna, e alguém constrói o painel inteiro antes de o gestor ver. O banner
mostra os dois erros, depois o Deidara resolvendo cada um (estrutura real das
fontes; protótipo aprovado antes do projeto), a explosão que gera o projeto e
os números que provam.

## Linha do tempo

Comentário que vai no topo do `<style>` dos dois SVGs:

```css
/* Linha do tempo: 48 s. Cena 1 0–7 · Cena 2 7–13 · Cena 3 13–23 · Cena 4 23–35 · Cena 5 35–43 · Cena 6 43–48 */
```

| Cena | Tempo | Nome | Ensina |
|---|---|---|---|
| 1 | 0–7 s | Os dois erros | adivinhar nome e construir antes de mostrar custam caro |
| 2 | 7–13 s | O pedido | um pedido tem duas perguntas: o que existe nas fontes e o que o gestor quer ver |
| 3 | 13–23 s | A estrutura volta | o Deidara não se conecta a nada: receita vai, só estrutura volta, e todo nome sai do catálogo |
| 4 | 23–35 s | A escultura | o gestor aprova um protótipo com números fictícios antes de qualquer projeto |
| 5 | 35–43 s | Katsu! | depois do "sim", sai o projeto completo, e os números são medidos |
| 6 | 43–48 s | Assinatura | o nome e as três promessas |

Fio entre as cenas: o pedido se parte em dois chips, **estrutura** (azul,
`#60A5FA`) e **painel** (laranja, `#FB923C`). Eles sobem para os cantos de
cima, cada um acende na cena dele (3 e 4) e voltam a se juntar na cena 6,
igual aos chips "consulta" e "fórmula" do Vegapunk.

---

## Cena 1 · Os dois erros (0–7 s)

**Ensina.** Os dois defeitos que o Deidara existe para evitar. O da esquerda é
técnico (nome inventado); o da direita é de processo (construir antes de
aprovar). Os dois juntos fazem o espectador pensar "já passei por isso".

**O que aparece.** Tela dividida ao meio, como no Vegapunk.

- Esquerda (fundo `rgba(96,165,250,.04)`, borda direita `#1E2A44`): um
  cartão de editor 548 × 220, cabeçalho "Power BI · medida" com ponto azul.
  Nele, uma linha de DAX sendo digitada em JetBrains Mono 22 px:
  `Turnover = DIVIDE([Desligamentos], COUNTROWS(Funcionarios))`.
- Direita (fundo `rgba(251,146,60,.05)`): um cartão do mesmo tamanho,
  cabeçalho "Reunião · painel pronto" com ponto laranja, mostrando a miniatura
  de um painel terminado (três cartões e um gráfico de barras, sem números
  legíveis). Embaixo da miniatura, um balão de fala do gestor.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| cabeçalho esquerdo | Power BI · medida | Power BI · measure |
| código | `Turnover = DIVIDE([Desligamentos], COUNTROWS(Funcionarios))` | igual (é código) |
| erro esquerdo | Funcionarios não existe no modelo | Funcionarios is not in the model |
| cabeçalho direito | Reunião · painel pronto | Meeting · finished report |
| balão do gestor | Não era isso que eu pedi. | That's not what I asked for. |
| carimbo | REFAZER | REDO |
| legenda (5,5–6,9 s) | Adivinhar o nome da **tabela**. Construir antes de **mostrar**. | Guess the **table** name. Build before you **show**. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 0,3 s | começa a digitação da esquerda, `steps()` com um passo por caractere, cursor piscando (`blink` de 1 s) |
| 1,6 s | a digitação chega a `Funcionarios`; a palavra fica vermelha (`#F87171`) e treme 4 px para os lados por 0,5 s |
| 1,8 s | o selo de erro sobe 8 px e aparece embaixo da palavra (fundo `#3A1420`, borda `#F87171`, ícone de alerta) |
| 2,4 s | à direita, a miniatura do painel aparece de baixo; as barras crescem da esquerda (`scaleX`) |
| 3,4 s | o balão do gestor aparece com leve escala (0,92 → 1) |
| 3,9 s | a miniatura recebe um carimbo vermelho girado −10° que cai de escala 1,6 para 1 |
| 5,5 s | a legenda entra de baixo (10 px) |
| 6,6–7,0 s | as duas metades saem para o centro com escala 0,9 e somem, como no Vegapunk; a legenda some junto |

---

## Cena 2 · O pedido (7–13 s)

**Ensina.** O usuário descreve o painel em português, do jeito que falaria
com um colega. O Deidara lê e separa duas perguntas diferentes.

**O que aparece.**

- O mascote (pássaro de argila geométrico, em âmbar e laranja) entra pela
  direita e fica no canto inferior direito até a cena 6.
- Balão de fala grande no centro, rótulo "você" em cima, com o pedido.
- As palavras-chave do pedido ganham fundo claro uma depois da outra.
- O balão se desfaz e as palavras viram dois chips lado a lado no meio da tela.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| rótulo do balão | você | you |
| pedido | Quero os desligamentos por motivo e cargo, com a meta de turnover por empresa. | I want terminations by reason and role, with the turnover target by company. |
| palavras destacadas | desligamentos · motivo · cargo · meta de turnover · empresa | terminations · reason · role · turnover target · company |
| chip azul | estrutura · o que existe nas fontes | structure · what the sources have |
| chip laranja | painel · o que o gestor quer ver | report · what the manager wants to see |
| legenda (10,5–12,9 s) | Um pedido, duas perguntas. O Deidara responde cada uma. | One request, two questions. Deidara answers each one. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 7,0 s | a grade de fundo aparece (opacidade 0 → 1 em 0,8 s) e fica até 47,5 s |
| 7,3 s | o balão aparece com escala 0,92 → 1 |
| 7,4 s | o mascote entra da direita (`translateX(120%)` → 0, curva `cubic-bezier(.2,.8,.2,1)`) |
| 7,9–9,1 s | as cinco palavras acendem em sequência, 0,3 s entre uma e outra |
| 10,0 s | o balão some; os dois chips nascem colados no centro (um com a borda esquerda redonda, o outro com a direita, formando uma pílula só) e se afastam 90 px para cada lado |
| 10,5 s | a legenda entra |
| 13,0–13,3 s | a legenda sai; os chips sobem para os cantos de cima (azul em x 56, laranja em x 874, y 48) |

---

## Cena 3 · A estrutura volta (13–23 s)

**Ensina.** O Deidara não se conecta a nenhuma fonte. Ele entrega uma receita,
quem tem acesso roda e cola o resultado, e só a estrutura volta: nenhuma linha
de dado. Todo nome do painel sai desse catálogo, e o nome amigável é escrito
em cima do nome real.

**O que aparece.** O chip **estrutura** acende no canto (opacidade 1); o chip
**painel** fica a 30%.

- À esquerda, uma faixa vertical azul com o título "SUA FONTE" e dois ícones:
  banco (ERP · SQL Server) e planilha (Metas · Excel). Uma linha tracejada
  separa a faixa do resto da tela, como uma parede.
- Um cartão de arquivo `receita_sql.sql` atravessa a parede da direita para a
  esquerda. A primeira linha do arquivo é um comentário com a instrução.
- Volta pela parede, da esquerda para a direita, uma fila de "fichas" pequenas
  em JetBrains Mono: nomes de tabela, coluna e tipo.
- Uma ficha diferente, cinza, com o ícone de uma linha de tabela e o texto de
  um registro ("linha de dado"), tenta passar e bate na parede: para, fica
  cinza e desce para o chão da faixa.
- À direita, as fichas se encaixam numa tabela de catálogo com duas colunas:
  "na fonte" (nome real) e "no painel" (nome amigável).
- No canto de baixo da tabela, um contador fixo.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| título da faixa | SUA FONTE | YOUR SOURCE |
| subtítulo da faixa | o Deidara não se conecta a nada | Deidara connects to nothing |
| ícones | ERP · SQL Server / Metas · Excel | ERP · SQL Server / Targets · Excel |
| 1ª linha da receita | `-- rode no SSMS e cole a grade` | `-- run in SSMS and paste the grid` |
| fichas que passam | `F_DESLIGAMENTO` · `DATADESLIGAMENTO date` · `F_CARGO` · `CODCARGO int` · `Metas` | iguais (são nomes da fonte) |
| ficha barrada | 1043 · Ana S. · 12/03/2024 | igual |
| rótulo da ficha barrada | fica na fonte | stays at the source |
| cabeçalhos do catálogo | na fonte · no painel | at the source · in the report |
| linhas do catálogo | `F_DESLIGAMENTO` → fDesligamento · `DATADESLIGAMENTO` → Data de desligamento · `CODCARGO` → Cód. Cargo · `Metas` → fMetas | iguais (veja a nota abaixo) |
| contador | linhas de dado: 0 | data rows: 0 |
| selo da tabela | nomes reais do catálogo | real names from the catalog |
| legenda (19,5–22,8 s) | A receita vai. Só a estrutura volta. | The recipe goes out. Only the structure comes back. |

Os nomes amigáveis ficam em português também no SVG em inglês: são os nomes
que o Deidara realmente gera, e o README em inglês avisa que o painel sai em
pt-BR.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 13,3 s | a faixa "SUA FONTE" entra da esquerda (−40 px → 0); a parede tracejada desenha de cima para baixo (`stroke-dashoffset`) |
| 14,2 s | o cartão `receita_sql.sql` entra pela direita e desliza até a parede em 1,2 s |
| 15,4 s | o cartão atravessa a parede e encolhe até o ícone do ERP; o ícone pulsa uma vez (escala 1 → 1,08 → 1) |
| 16,0–17,6 s | cinco fichas atravessam a parede para a direita, 0,3 s entre elas, cada uma com rastro azul curto |
| 16,9 s | a ficha cinza parte junto, bate na parede, recua 6 px, perde a cor e desce 30 px; o rótulo "fica na fonte" aparece ao lado e some em 18,5 s |
| 17,6–18,8 s | as linhas do catálogo aparecem da esquerda (−12 px → 0), 0,3 s entre elas; na coluna "no painel", o nome amigável é digitado |
| 18,9 s | o selo "nomes reais do catálogo" estala (escala 0,6 → 1,1 → 1) |
| 18,9 s | o contador "linhas de dado: 0" ganha fundo verde por 1 s e volta |
| 19,5 s | a legenda entra |
| 22,4–23,0 s | tudo da cena sobe 16 px e some; o chip **estrutura** volta a 30% |

---

## Cena 4 · A escultura (23–35 s)

**Ensina.** Antes de qualquer projeto, o gestor vê o painel como ele vai
ficar, com números fictícios, entende cada número (ⓘ) e aprova numa aba
própria. O aceite fica registrado e trava a especificação: mudou depois, o
Deidara recusa gerar.

**O que aparece.** O chip **painel** acende no canto; o chip **estrutura**
fica a 30%.

- Uma janela de navegador estilizada (barra com três pontos e o nome do
  arquivo `argila.prototipo.html`), 900 × 420, centrada.
- Dentro, uma página no modelo `faixa-de-kpis`: trilho de ícones à esquerda,
  título "Visão geral" com a pergunta da página embaixo, linha de três
  cartões, um gráfico de barras por motivo e uma tabela por cargo com a barra
  contra a meta dentro da célula.
- Uma faixa no topo da janela, sempre visível nesta cena: "números fictícios".
- Um ⓘ no canto do cartão Turnover abre uma dica.
- A janela troca para a aba "Para aprovar": checklist de três itens e um
  campo de decisão.
- O carimbo APROVADO cai sobre a janela, com o código do aceite embaixo.
- Por último, um "fantasma": uma mudança feita depois do aceite, recusada.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| barra da janela | `argila.prototipo.html` | igual |
| faixa de aviso | números fictícios | fictional numbers |
| abas | Visão geral · Turnover · Modelo de dados · Pendências · Para aprovar | Visão geral · Turnover · Modelo de dados · Pendências · Para aprovar (as abas reais são em pt-BR) |
| título da página | Visão geral | Visão geral |
| pergunta da página | Onde o turnover passou da meta? | Onde o turnover passou da meta? |
| cartões | Turnover 2,1% (meta 1,8%) · Desligamentos 148 · HC Médio 7.040 | iguais (o protótipo é em pt-BR) |
| barras | Motivo A … Motivo E | iguais |
| dica do ⓘ | Turnover = desligamentos do período ÷ headcount médio. Menor é melhor. | Turnover = terminations in the period ÷ average headcount. Lower is better. |
| checklist | ✓ os indicadores dizem o que eu preciso · ✓ os cortes estão certos · ✓ as pendências foram decididas | ✓ the KPIs say what I need · ✓ the breakdowns are right · ✓ the open items are decided |
| fala do gestor | Aprovo. | Approved. |
| carimbo | APROVADO | APPROVED |
| código do aceite | aceite 7F3A·C21E · argila + catálogos | approval 7F3A·C21E · spec + catalogs |
| fantasma | `"cor": "#FF0000"` em fMetas, depois do aceite | `"cor": "#FF0000"` on fMetas, after approval |
| recusa do fantasma | gerar recusa: mudou depois do aceite. Novo protótipo, novo "sim". | generate refuses: changed after approval. New prototype, new "yes". |
| legenda (31,0–34,8 s) | Primeiro a escultura. O gestor decide. | Sculpture first. The manager decides. |

A dica do ⓘ e o checklist são traduzidos no SVG em inglês porque explicam a
cena para quem lê; os textos que são do protótipo (abas, títulos, números)
ficam em pt-BR, como o protótipo real.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 23,0 s | a janela sobe 16 px e aparece; a faixa "números fictícios" pisca uma vez |
| 23,4–24,6 s | o fundo da página se desenha: trilho, título, painéis (opacidade em sequência, 0,2 s entre eles) |
| 24,6–25,6 s | os cartões caem 30 px no lugar, um a cada 0,3 s; os números contam de 0 até o valor (contador CSS com `@property`, igual ao Vegapunk) |
| 25,2 s | as barras crescem da esquerda; as barras contra a meta da tabela crescem e a linha da meta aparece por cima |
| 26,4 s | o cursor vai até o ⓘ; a dica abre com escala 0,92 → 1 e fica 2 s |
| 28,4 s | a dica fecha; a aba "Para aprovar" fica sublinhada e o conteúdo da janela desliza para a esquerda |
| 28,8–29,7 s | os três itens do checklist ganham ✓ verde, 0,3 s entre eles |
| 30,0 s | o balão "Aprovo." aparece ao lado da janela |
| 30,4 s | o carimbo APROVADO cai girado −10°, da escala 1,6 para 1 (o `stamp` que o banner atual já tem) |
| 30,8 s | o código do aceite aparece embaixo do carimbo com um cadeado fechando |
| 31,0 s | a legenda entra |
| 32,0 s | o fantasma entra pela direita, em vermelho claro, e encosta no cadeado |
| 32,4 s | o cadeado treme 4 px; o fantasma fica cinza e a recusa aparece embaixo dele |
| 33,8 s | o fantasma some para a direita |
| 34,4–35,0 s | a janela e a legenda sobem 16 px e somem; o chip **painel** volta a 30% |

---

## Cena 5 · Katsu! (35–43 s)

**Ensina.** Só depois do aceite o Deidara gera o projeto Power BI de verdade,
mais tudo o que o time precisa para homologar. E o que está escrito no README
foi medido.

**O que aparece.** Dois momentos.

1. **A explosão (35,0–38,6 s).** A estrela de oito pontas do banner atual, com
   "Katsu!" no meio, nasce no centro, cresce e explode em partículas âmbar e
   laranja. Das partículas sai uma árvore de arquivos em JetBrains Mono, à
   esquerda, e um ícone do Power BI Desktop à direita com uma seta
   `.pbip → .pbix`.
2. **Os números (38,6–43,0 s).** Quatro painéis, como na cena 5 do Vegapunk,
   cada um com o número grande que conta de 0 até o valor, o nome e uma barra
   fina embaixo.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| explosão | Katsu! | Katsu! |
| árvore | `Painel.pbip` · `Painel.SemanticModel/` (TMDL) · `Painel.Report/` (PBIR) · `sql/erp/01_views.sql` · `sql/erp/02_conferencia.sql` · `sql/erp/03_qualidade.sql` · `HOMOLOGACAO.md` · `LEIA-ME.md` · `docs/dicionario_indicadores.md` | igual (são nomes de arquivo) |
| seta | abre no Desktop, salva como .pbix | opens in Desktop, saves as .pbix |
| painel 1 | **24 de 24** · arquivos JSON do projeto conferidos contra os schemas da Microsoft | **24 of 24** · project JSON files checked against Microsoft's schemas |
| painel 2 | **11** · modelos de layout, do protótipo ao .pbip | **11** · layout templates, from prototype to .pbip |
| painel 3 | **31** · técnicas de visual geradas prontas | **31** · visual techniques generated ready to use |
| painel 4 | **0** · linhas de dado que as receitas devolvem | **0** · data rows the recipes return |
| nota (40,6–42,8 s) | Medido no exemplo do repositório: um ERP fictício em SQL Server e uma planilha de metas. | Measured on the repository example: a fictional SQL Server ERP and a targets spreadsheet. |

**Fonte dos números.** A tabela "Resultados" do README. Antes de gerar o SVG,
confira se algum mudou (a contagem de testes muda a cada versão e por isso
ficou de fora; os quatro acima mudam pouco). O painel 4 conta para baixo, de
um número qualquer até 0, para que o zero seja notado.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 35,0 s | a estrela nasce no centro (escala 0,2 → 1) com "Katsu!" em Poppins 800 |
| 35,6 s | a estrela incha (1 → 1,25) e explode: 16 partículas voam para fora com `cubic-bezier(.2,.8,.2,1)` e somem em 0,8 s; o brilho âmbar do fundo dobra por 0,4 s |
| 36,2–37,8 s | as linhas da árvore aparecem de cima para baixo, 0,15 s entre elas, com recuo de pasta |
| 37,0 s | o ícone do Desktop e a seta entram da direita |
| 38,4–38,6 s | a árvore e o ícone desfocam (`blur(8px)`) e somem, como a passagem de cena do Vegapunk |
| 38,6–40,4 s | os quatro painéis sobem 40 px, 0,3 s entre eles; os números contam com `cubic-bezier(.15,.7,.3,1)`; as barras finas crescem quando o número para |
| 40,6 s | a nota aparece embaixo |
| 42,4–43,0 s | painéis e nota desfocam e somem |

---

## Cena 6 · Assinatura (43–48 s)

**Ensina.** Nome, promessa e onde o Deidara roda. É o quadro que fica na
memória e o que aparece para quem tem movimento reduzido.

**O que aparece.** O desenho final do banner atual, refeito com as fontes
embutidas: "Deidara" grande no centro, o subtítulo, as três pílulas âmbar e
uma linha de rodapé. Os chips **estrutura** e **painel** descem dos cantos e
se juntam numa pílula só em cima do nome. O mascote continua no canto.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| chips juntos | estrutura · painel | structure · report |
| nome | DEIDARA | DEIDARA |
| subtítulo | primeiro a escultura. depois, a explosão. | sculpture first. then, the explosion. |
| pílulas | Só estrutura, nunca dado · Nenhum nome adivinhado · .pbip pronto para o Desktop | Structure only, never data · No guessed names · .pbip ready for Desktop |
| rodapé | Claude Code · Power BI .pbip (TMDL + PBIR) · SQL Server · Excel · MIT | Claude Code · Power BI .pbip (TMDL + PBIR) · SQL Server · Excel · MIT |

O subtítulo é a frase do fim do README ("primeiro a escultura. depois, a
explosão."), para o banner e o rodapé do README fecharem com a mesma ideia.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 43,0 s | os chips descem dos cantos com mola (`cubic-bezier(.3,1.4,.5,1)`) e se colam em x 320 / 610, y 140 |
| 43,6 s | "DEIDARA" aparece com escala 0,92 → 1 e espaçamento entre letras .18em → .06em |
| 44,0 s | o subtítulo sobe 10 px |
| 44,3 s | as três pílulas sobem 10 px, 0,15 s entre elas |
| 44,6 s | o rodapé aparece |
| 47,5–48,0 s | tudo some junto (opacidade 1 → 0), inclusive o mascote e a grade, e o laço volta à cena 1 |

---

## Movimento reduzido

Com `prefers-reduced-motion: reduce`, nenhuma animação roda e a tela mostra a
cena 6 parada, com os chips já juntos. É o mesmo conteúdo do banner atual,
então nada se perde para quem não vê o movimento.

## Erros a evitar

- Prometer um `.pbix` gerado direto: o Deidara entrega o `.pbip`; o `.pbix`
  sai do Desktop (regra 7 do `SKILL.md`). A seta da cena 5 diz isso.
- Mostrar um número real ou um nome de pessoa real: tudo vem do exemplo
  fictício.
- Pôr a explosão antes do aceite: a ordem (escultura → "sim" → Katsu!) é a
  mensagem.
- Deixar texto de explicação em português no SVG em inglês. Só ficam em pt-BR
  os nomes que o Deidara gera (nomes amigáveis, abas e títulos do protótipo).
