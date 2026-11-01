# Licenças de terceiros

## Power BI Design Files (Sajjad Ahmadi)

Os modelos de layout (`tecnicas/arte/modelos.py`, [referencias/modelos.md](referencias/modelos.md))
reproduzem a estrutura de páginas de dashboards do repositório
[Power BI Design Files](https://github.com/Dashboard-Design/Power-BI-Design-Files):
a divisão em regiões, as proporções e a técnica de fundo desenhado com
visuais transparentes. A formatação dos visuais de cada modelo (`terceiros/power-bi-design-files/estilos.json`) e as paletas
(`terceiros/power-bi-design-files/paletas.json`) foram tiradas dos `.pbix` dele, só as propriedades de formatação e as cores dos
temas que ele montou; os dois arquivos ficam em `terceiros/power-bi-design-files/`, como as outras fontes da
galeria, com a `LICENSE` original e o `ORIGEM.md` (commit, data da extração e a curadoria feita). As imagens de fundo, os dados e os visuais
personalizados daqueles dashboards não vêm no Deidara. As práticas de design
e de SVG em DAX ([referencias/design.md](referencias/design.md),
[referencias/svg.md](referencias/svg.md), `dicionario/visuais.json`) foram
escritas para o Deidara a partir do mesmo repositório. O tour guiado
(`tecnicas/c1/tour.py`) e o agrupador de textos (`ferramentas/agrupar_textos.py`)
seguem as ideias do Interactive Dashboard Tour e do Clustering & Similarity
Score dele, com código escrito para o Deidara.

Os temas JSON de terceiros que o repositório reúne (BIBB, Kerry Kolosko,
Zebra BI) não vêm no Deidara: são de outros autores. O Deidara aponta onde
baixá-los e os usa pelo `"tema": {"arquivo": ...}`; quem usa confere a
licença e dá o crédito. Os estudos de caso da pasta Practice (DataCamp) e as
bases de prática também ficam de fora; [referencias/design.md](referencias/design.md)
indica a pasta.

```
MIT License

Copyright (c) 2024 Sajjad Ahmadi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Microsoft Learn

Nomes, categorias, assinaturas e links do dicionário de funções DAX e Power
Query vêm da referência oficial da Microsoft; as descrições em pt-BR são do
Deidara e o texto da Microsoft não é copiado (ver [AVISO.md](AVISO.md)).

## JSON Schemas do Power BI (Microsoft)

Os schemas em `ferramentas/schemas/` são cópias dos publicados em
[microsoft/json-schemas](https://github.com/microsoft/json-schemas), guardadas
para o `validar_pbip.py` e os testes rodarem sem internet. Licença MIT,
Copyright (c) Microsoft Corporation. Ficam fora do pacote da skill.

## NIST/SEMATECH e-Handbook of Statistical Methods

As fórmulas e as regras do C4 Karura (`tecnicas/c4.py`, [referencias/estatistica.md](referencias/estatistica.md))
seguem o [e-Handbook of Statistical Methods](https://www.itl.nist.gov/div898/handbook/) do NIST: gráfico de
valores individuais (6.3.2.2), regras WECO (6.3.2), gráficos p e u (6.3.3.1 e 6.3.3.2), detecção de outliers
com o z-score modificado (1.3.5.17), sazonalidade (6.4.4.3) e box plot (1.3.3.7). Os testes usam os exemplos
resolvidos de lá como gabarito. Conteúdo público do governo dos Estados Unidos, que o NIST permite copiar e
distribuir pedindo o crédito ([política do NIST](https://www.nist.gov/oism/copyrights)).

## Galeria da comunidade (`terceiros/`)

Conteúdo aberto trazido para o Deidara por `ferramentas/atualizar_terceiros.py`. Todas as fontes têm licença
MIT, a mesma do Deidara. Cada pasta guarda a `LICENSE` original, sem alteração, e um `ORIGEM.md` com o
repositório, o commit e a data da cópia. Só entraram arquivos de texto (modelos, funções, documentação);
.pbix, imagens e vídeos ficaram nos repositórios de origem. O índice é o `terceiros/catalogo.json`
(`deidara.py galeria`).

| Pasta | Origem | Copyright |
|---|---|---|
| `terceiros/daxlib` | [daxlib/daxlib](https://github.com/daxlib/daxlib): funções DAX (SVG, IBCS, cascata, estatística, calendário) | (c) 2025 SQLBI e os autores de cada pacote (no `manifest.daxlib`) |
| `terceiros/deneb-vega-templates` | [avatorl/Deneb-Vega-Templates](https://github.com/avatorl/Deneb-Vega-Templates) | (c) 2024 Andrzej Leszkiewicz |
| `terceiros/dataviz-vega` | [avatorl/DataViz-Vega](https://github.com/avatorl/DataViz-Vega) | (c) 2024 Andrzej Leszkiewicz |
| `terceiros/deneb-showcase` | [PBI-David/Deneb-Showcase](https://github.com/PBI-David/Deneb-Showcase) | (c) 2023 Davide Bacci |
| `terceiros/deneb-vega-showcase` | [Flynnxx1/Deneb-Vega-Showcase](https://github.com/Flynnxx1/Deneb-Vega-Showcase) | (c) 2024 Ying Fu (Flynnxx1) |
| `terceiros/powerbi-deneb` | [CSalcedoDataBI/PowerBI-Deneb](https://github.com/CSalcedoDataBI/PowerBI-Deneb) | (c) 2026 Cristobal Salcedo |
| `terceiros/bravo-calendario` | [sql-bi/Bravo](https://github.com/sql-bi/Bravo), pasta `src/Assets/ManageDates/Templates` | (c) SQLBI Corporation |
| `terceiros/powerbi-svg` | [jurgenfolz/PowerBI-SVG](https://github.com/jurgenfolz/PowerBI-SVG) | (c) 2024 Klaus Jürgen Folz |
| `terceiros/deneb-metadados` | [deneb-viz/deneb](https://github.com/deneb-viz/deneb), pasta `packages/template-usermeta` | (c) Daniel Marsh-Patrick |

O que o Deidara gera a partir delas leva o crédito junto: o `functions.tmdl` do projeto traz o pacote, a
versão e os autores de cada bloco de funções; o visual Deneb mantém o `usermeta` do autor; o calendário cita o
modelo de feriados do Bravo. Nos feriados do Brasil, o Deidara traduziu os nomes e acrescentou a Consciência
Negra (Lei 14.759/2023), que o modelo do Bravo ainda não tinha.

Ficaram de fora, por licença: `avatorl/PowerBI-IBCS`, `avatorl/PowerBI-SVG` e `PowerBI-tips/Deneb-Templates`
(sem licença: todos os direitos com o autor) e `data-goblin/power-bi-agentic-development` (GPL-3.0, que
obrigaria o Deidara a mudar de licença). Servem só de referência.
