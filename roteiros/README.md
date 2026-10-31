# Roteiros das animações do README

**Português** | [English](README.en.md)

Esta pasta guarda o roteiro de cada animação SVG de `assets/`. O roteiro vem
antes do desenho: diz o que cada cena ensina, quanto tempo dura, o que aparece,
o texto exato na tela (em pt-BR e em inglês) e como cada elemento entra e sai.
Quem for desenhar ou corrigir um SVG começa por aqui; quem mudar o produto (um
comando, um número, um nome) confere aqui se alguma cena ficou desatualizada.

| Animação | Roteiro | Onde aparece | Duração | Pergunta que responde |
|---|---|---|---|---|
| `deidara-banner.svg` / `-en.svg` | [deidara-banner.md](deidara-banner.md) | topo do README, logo depois dos selos | 48 s, 6 cenas | por que o Deidara existe e o que ele entrega |
| `deidara-fluxo.svg` / `-en.svg` | [deidara-fluxo.md](deidara-fluxo.md) | seção "Como funciona por dentro", antes da tabela de peças | 36 s, 5 passos | como um pedido vira um projeto Power BI sem adivinhar nada |

As duas animações substituem os SVGs atuais, que hoje são quase estáticos
(só pulsam). O nome dos arquivos e o `alt` no README continuam os mesmos.

## O padrão que vem do Vegapunk

O Vegapunk (repositório irmão, `assets/vegapunk-banner.svg` e
`assets/vegapunk-sonar.svg`) não tem documento de roteiro separado: o roteiro
fica escondido no próprio SVG, num comentário de linha do tempo
(`/* Linha do tempo: 48 s. Cena 1 0–7 · Cena 2 7–13 ... */`) e num bloco
`/* Cena N */` para cada cena. Os roteiros desta pasta escrevem por extenso o
que esses SVGs fazem, e o SVG do Deidara deve repetir o mesmo comentário de
linha do tempo, para que o roteiro e o arquivo possam ser conferidos um contra
o outro.

Regras tiradas dos SVGs do Vegapunk, que valem para as duas animações:

1. **Um laço só, sem JavaScript.** Uma única duração para tudo (48 s no
   banner, 31 s no sonar do Vegapunk) e cada elemento com seus `@keyframes`
   em porcentagem desse laço. Nos roteiros, os tempos estão em segundos; para
   converter, `% = segundo ÷ duração × 100` (no banner de 48 s, 1 s = 2,0833%;
   no fluxo de 36 s, 1 s = 2,7778%).
2. **Narrativa em arco.** O banner vai da dor ao produto: (1) o que dá errado
   hoje, (2) o pedido do usuário, (3 e 4) o que o produto faz com cada parte
   do pedido, (5) os números medidos, (6) a assinatura. A animação de "como
   funciona" é um passo a passo numerado com uma faixa de progresso no topo.
3. **Um fio que atravessa as cenas.** No Vegapunk, o pedido se parte em dois
   "chips" (consulta e fórmula) que sobem para o canto, acendem quando a cena
   é deles e voltam juntos no fim. O Deidara usa o mesmo recurso com os chips
   **estrutura** e **painel**.
4. **Uma legenda por vez.** Uma frase curta embaixo, que entra depois da
   imagem e sai antes da próxima cena. Nunca duas legendas na tela.
5. **O errado aparece e é descartado, nunca escondido.** O Vegapunk mostra a
   função inventada (`CALCULA_BONUS`) virando lacuna e os achados irrelevantes
   como um eco cinza que fica para trás. O Deidara mostra o nome adivinhado
   sendo recusado pelo `validar` e a mudança depois do aceite sendo recusada
   pelo `gerar`.
6. **Exemplo fictício e plausível, com nomes de verdade do exemplo.** Os
   nomes vêm do tutorial (`fDesligamento`, `dCargo`, `fMetas->dEmpresa`,
   `Headcount`, `HC Médio`, `Turnover`). Nenhum dado real.
7. **Número só com a fonte da medição.** A cena de resultados do Vegapunk
   termina com "Medido com pedidos que o motor nunca tinha visto." No Deidara,
   os números vêm da tabela "Resultados" do README e levam a nota de onde
   foram medidos.
8. **Fim que emenda no começo.** Tudo some entre 98,958% e 100% do laço (os
   últimos 0,5 s), e a primeira cena começa do zero sem salto.
9. **Autossuficiente.** Fontes embutidas em base64 (o Vegapunk usa Inter,
   Poppins e JetBrains Mono), nenhuma imagem ou link externo: o GitHub serve o
   SVG como imagem e bloqueia o que vem de fora. O conteúdo animado mora num
   `<foreignObject>` de 1280 × 640 com HTML e CSS.
10. **Pausável.** Toda classe animada lê `animation-delay: var(--d, 0s)` e
    `animation-play-state: var(--ps, running)`, como no Vegapunk, para pausar
    ou congelar um quadro ao revisar.
11. **Duas línguas, mesma linha do tempo.** O arquivo `-en.svg` tem
    exatamente os mesmos tempos e posições; só o texto muda. Todo texto de
    interface é traduzido; nomes de tabela, coluna, comando e arquivo ficam
    como são. (O banner em inglês do Vegapunk deixou passar "JOIN provado" em
    português: os roteiros daqui listam todo texto nas duas línguas para isso
    não se repetir.)
12. **Rótulo acessível próprio.** Cada SVG tem `role="img"` e um `aria-label`
    igual ao `alt` do README. (O sonar do Vegapunk reaproveitou o rótulo do
    banner; aqui cada um tem o seu.)

## O que o Deidara acrescenta

- **Movimento reduzido.** Os SVGs atuais do Deidara já respeitam
  `@media (prefers-reduced-motion: reduce)`, e isso fica. Com movimento
  reduzido, cada animação mostra um quadro final parado que se explica sozinho
  (descrito no fim de cada roteiro).
- **A paleta do Deidara, não a do Vegapunk.** Fundo `#0B1220` com grade
  `#1E2A44` e o brilho âmbar do banner atual, como nos dois projetos. Cores com
  significado fixo:

| Cor | Hex | Significa |
|---|---|---|
| azul | `#60A5FA` | a fonte e a estrutura (receita, catálogo) |
| âmbar | `#F59E0B` | a argila (especificação, esboço, validação) |
| laranja | `#FB923C` | a escultura (protótipo) e a explosão (Katsu!) |
| verde | `#34D399` | aceite, prova, entrega pronta |
| vermelho | `#F87171` | erro: nome adivinhado, mudança sem aceite |
| cinza | `#475569` / `#94A3B8` | o que foi descartado, texto de apoio |
| texto | `#E2E8F0` | texto principal |

  Cor nunca é a única pista: todo estado também tem palavra ou ícone (✓, ✕,
  "A CONFIRMAR", "APROVADO"), como pede `referencias/design.md`.
- **Tipografia.** Inter para texto, Poppins 800 para o nome "DEIDARA" e
  "Katsu!", JetBrains Mono para código, nomes de arquivo e comandos. Embutidas,
  como no Vegapunk (os SVGs atuais do Deidara usam fontes do sistema, o que
  muda a medida do texto de máquina para máquina).
- **Sem o personagem.** O Vegapunk tem uma ilustração própria. O Deidara usa
  um símbolo original em vez de desenhar o personagem de Naruto: a explosão
  de oito pontas do banner atual ("Katsu!") e um pássaro de argila geométrico
  e simples, feito de polígonos, que serve de mascote.

## Como conferir um SVG contra o roteiro

1. O comentário de linha do tempo do SVG tem as mesmas cenas e os mesmos
   segundos do roteiro.
2. Cada texto da coluna "Texto na tela" aparece no SVG pt-BR, e a tradução da
   mesma linha aparece no `-en.svg`.
3. Pausando em cada marca (`--ps: paused` e `--d` negativo com o segundo
   desejado), o quadro bate com a coluna "O que aparece".
4. Nenhum elemento fica na tela depois do tempo de saída escrito no roteiro.
5. Os números da cena de resultados são os mesmos da tabela "Resultados" do
   README no dia em que o SVG é gerado.

## Outras animações possíveis

O Vegapunk tem duas animações, e as duas daqui cobrem os mesmos lugares do
README. Se valer a pena uma terceira, as candidatas mais fortes são:

- **`deidara-modelos.svg`**, na seção "Modelos de layout": a mesma página do
  exemplo (um cartão de Turnover, barras por motivo, uma tabela) se
  reencaixando nos onze modelos, um a cada 2,5 s, com o nome do modelo
  (`faixa-de-kpis`, `executivo`, `causa-raiz`...) e a linha "Bom para" da
  tabela de `referencias/modelos.md`. Mostra num relance o que a tabela leva
  onze linhas para dizer.
- **`deidara-escultura.svg`**, perto do tutorial: só o protótipo, em tamanho
  grande, com o ⓘ abrindo, a aba "Para aprovar", os comentários e o botão
  "Copiar resumo do aceite". Hoje isso aparece de forma resumida na cena 4 do
  banner; vale um SVG próprio se o protótipo virar o argumento principal do
  README.

Nenhuma das duas tem roteiro ainda: só entram se o dono do repositório
quiser.
