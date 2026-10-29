# Medidas que desenham: SVG em DAX

Uma medida DAX pode devolver uma **imagem**: um texto SVG que o Power BI
desenha dentro da tabela, da matriz, do segmentador de botões, do cartão novo
ou como marcador do Azure Maps. É a forma nativa de pôr barra contra a meta,
status, seta de variação e pequenos gráficos dentro de uma linha, sem visual
personalizado. Escrito a partir do estudo do repositório
[Power BI Design Files](https://github.com/Dashboard-Design/Power-BI-Design-Files),
de Sajjad Ahmadi (licença MIT); as regras foram reescritas para o Deidara.

## O que o Deidara faz por você

- **Gera** a barra contra a meta (`"tipo": "svg_barra_meta"`, abaixo), já
  seguindo todas as regras desta página.
- **Marca a categoria de dados Image URL** em toda medida que devolve SVG
  (a gerada e a escrita à mão). É o erro mais comum: sem ela, o Power BI
  mostra o texto em vez da imagem.
- **Confere** a medida SVG escrita à mão no `validar` (erros e avisos
  marcados com `[SVG]`).
- **Desenha** no protótipo a mesma barra que vai sair no Power BI.
- **Recusa** a medida de imagem em visual que não seja tabela ou matriz.

## A barra contra a meta

```json
{"nome": "Turnover x Meta", "tipo": "svg_barra_meta", "medida": "Turnover",
 "categoria": "dEmpresa[Empresa]", "descricao": "Turnover de cada empresa contra a meta dela."}
```

e na página:

```json
{"tipo": "tabela", "campos": ["dEmpresa[Empresa]", "Turnover", "Turnover x Meta"]}
```

- `medida`: a medida que vira barra. Ela precisa ter `"meta"`; a cor segue a
  polaridade dela (verde bateu, vermelho não bateu).
- `categoria`: a coluna das linhas da tabela. O eixo é o mesmo para todas as
  linhas visíveis (o maior valor ou meta entre elas, com folga), então as
  barras são comparáveis entre si.
- Na linha de total a célula fica vazia, de propósito.
- No Power BI, se a barra ficar baixa, aumente o tamanho da imagem nas opções
  de formatação da tabela.

## Pílula, seta e selo

Também gerados prontos, no mesmo molde (`medida`, `categoria` e as regras abaixo):

```json
{"nome": "Status da meta", "tipo": "svg_pilula", "medida": "Turnover", "categoria": "dEmpresa[Empresa]"}
{"nome": "Variação", "tipo": "svg_seta", "medida": "Desligamentos", "comparar": "Desligamentos Ano Anterior", "categoria": "dCargo[Cargo]"}
{"nome": "Selo da posição", "tipo": "svg_posicao", "medida": "Desligamentos", "categoria": "dCargo[Cargo]"}
```

- **Pílula**: "Na meta" ou "Fora da meta" pela polaridade, com fundo claro e texto escuro da mesma cor (o texto
  diz a situação, a cor só reforça). A medida precisa de `meta`.
- **Seta**: ponto cinza no valor de `comparar` (o anterior) e a seta até o atual, no mesmo eixo para todas as
  linhas; verde se melhorou pela polaridade, vermelha se piorou.
- **Selo**: círculo com a posição (RANKX); os três primeiros na cor de destaque do tema, o resto em cinza.

## Radar, bolhas e variação IBCS

```json
{"nome": "Perfil do cargo", "tipo": "svg_radar", "medidas": ["Headcount", "Remuneração Média", "Turnover"], "categoria": "dCargo[Cargo]"}
{"nome": "Bolha do custo", "tipo": "svg_bolha", "medida": "Remuneração Total", "categoria": "dCargo[Cargo]", "colunas": "dEmpresa[Empresa]"}
{"nome": "Desvio", "tipo": "svg_variacao", "medida": "Headcount", "comparar": "Headcount Ano Anterior", "categoria": "dEmpresa[Empresa]"}
```

- **Radar**: um eixo por medida (3 a 8), cada um dividido pelo maior valor dela entre as linhas visíveis
  (`MAXX(ALLSELECTED(...))`). Os ângulos saem do Deidara já calculados (seno e cosseno fixos no texto), então a
  medida só multiplica. Mostra o perfil, não o tamanho: deixe os números ao lado.
- **Bolha**: o raio é a raiz do valor dividido pelo maior da matriz inteira (`CROSSJOIN` das linhas e colunas
  visíveis), para a área ficar proporcional. Só tem sentido na matriz.
- **Variação IBCS**: eixo no centro, barra para a direita quando o desvio é positivo e para a esquerda quando é
  negativo, no mesmo eixo para todas as linhas; a cor segue a polaridade, não o sinal.

## Iniciais e dispersão

```json
{"nome": "Iniciais da empresa", "tipo": "svg_iniciais", "categoria": "dEmpresa[Empresa]"}
{"nome": "Dispersão dos cargos", "tipo": "svg_dispersao", "categoria": "dCargo[Cargo]", "x": "Headcount", "y": "Remuneração Média"}
```

- **Iniciais**: círculo com a primeira letra da primeira e da última palavra; sai em dois tons (a medida e a
  `(ligado)`), para a imagem de cada botão do segmentador.
- **Dispersão**: o gráfico inteiro numa imagem só, no cartão novo (visual `imagem`). Não tem HASONEVALUE de
  propósito: é uma imagem por visual, não por linha. Com `imagem`, cada ponto vira a imagem do item, que precisa
  estar em `data:image/...` (base64); link externo não carrega dentro do SVG.

## As regras (para quem escreve a medida à mão)

Em ordem de gravidade. As marcadas com ✓ o `validar` confere.

### Quebram a imagem

1. ✓ **O texto começa com `data:image/svg+xml;charset=utf-8,`**, com a vírgula
   no fim. Sem o prefixo, não há imagem.
2. **Categoria de dados Image URL.** O Deidara marca sozinho no modelo gerado.
3. ✓ **`#` vira `%23`.** O texto é lido como endereço antes de virar SVG, e o
   `#` corta o endereço: `fill='%23107C10'`, nunca `fill='#107C10'`. Nome de
   cor (`red`, `gray`) não precisa de troca.
4. ✓ **`%` vira `%25`.** Pelo mesmo motivo: `width='100%25'`. Todo `%` dentro
   do SVG precisa ser seguido de dois dígitos hexadecimais.
5. **Aspas simples nos atributos.** O DAX usa aspas duplas para texto; com
   aspas simples no SVG, a emenda fica legível: `"<rect width='" & _w & "'/>"`.
   ✓ O `validar` avisa quando encontra aspas duplas escapadas.
6. **Número com ponto, não vírgula.** Num modelo em português, juntar um
   número ao texto pode sair `45,5`, que o SVG não entende. Use
   `FORMAT(_valor, "0.00", "en-US")` em toda coordenada.

### Falham em algum lugar

7. ✓ **`viewBox` sempre**, com folga e `overflow='visible'` juntos (ex.:
   `viewBox='-2 -2 104 24'` para um desenho de 100 x 20). Sem isso, borda e
   linha grossa saem cortadas.
8. **`width='100%25' height='100%25'`** para preencher a célula, e
   `display='block'` para tirar o espaço extra embaixo.
9. **`preserveAspectRatio='none'` só para barra e linha.** Em círculo, ícone
   ou texto, deforma.
10. ✓ **`HASONEVALUE` (ou `ISINSCOPE`) no `RETURN`**: no total e no subtotal
    não há uma linha só, e a imagem sai quebrada ou sem sentido.
11. ✓ **Sem `foreignObject`** (HTML dentro do SVG), filtro, imagem embutida ou
    endereço externo: não funcionam em todo lugar (celular, exportação).

### Deixam a medida fácil de manter

12. **Cores em variáveis, já com `%23`, com um comentário** dizendo qual é a
    cor: `VAR _corBarra = "%23107C10" -- verde`.
13. **Ordem fixa:** configuração, cálculos, cores, desenho, `RETURN`.
14. **Eixo comum quando a posição compara linhas** (barra, seta, progresso):
    calcule o máximo uma vez sobre todas as linhas visíveis
    (`MAXX(ALLSELECTED(<coluna>), <medida>)`), não linha a linha. Desenho com
    escala fixa (nota de 0 a 5, anel de 0 a 100%) não precisa.
15. **Ordenar pela imagem**: a tabela ordena a coluna de imagem pelo texto.
    Ponha um `<desc>` logo depois de `<svg>` com o valor em zeros à esquerda
    (`FORMAT(..., "000000000000")`), e a ordem passa a ser a do número.
16. **Enxuto:** sem `<?xml ...?>`, sem espaço sobrando, sem namespace que não
    é usado. O texto se repete em cada linha da tabela.

### Se aparecer uma dica de ferramenta que não devia

Mesmo com a dica desligada na tabela, às vezes aparece uma caixinha ao passar
o mouse na imagem. Mudar um pouco o tamanho da imagem nas opções de formatação
força o Power BI a redesenhar e ela some.

## Conferência final

- [ ] começa com `data:image/svg+xml;charset=utf-8,`
- [ ] nenhum `#` dentro do SVG; todo `%` seguido de dois dígitos hexadecimais
- [ ] `viewBox` com folga e `overflow='visible'`
- [ ] `HASONEVALUE`/`ISINSCOPE` no `RETURN`
- [ ] coordenadas com `FORMAT(..., "en-US")`
- [ ] `validar` sem `[SVG]`
