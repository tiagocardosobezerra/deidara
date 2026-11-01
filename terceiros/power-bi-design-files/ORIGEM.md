# power-bi-design-files

A base dos onze modelos de layout do Deidara: a formatação de cada tipo de visual (`estilos.json`) e as cores
dos temas (`paletas.json`) dos dashboards de Sajjad Ahmadi.

- Repositório: https://github.com/Dashboard-Design/Power-BI-Design-Files
- Licença: MIT (texto em `LICENSE`, como o autor publicou)
- Commit: `a11da165e2642b3b2714dc8e0dbab4688e0b7025` (o mais recente na data da extração)
- Extraído em: 29/10/2026, dos `.pbix` listados em `estilos.json` (`origem`), um por modelo
- Só propriedades de formatação e cores: nada de dados, campos, imagens de fundo ou visuais personalizados.

## Curadoria

`estilos.json` não é a cópia bruta: de cada dashboard foi escolhido o visual de cada tipo que representa o
modelo, e saíram os objetos presos aos dados de origem (seletor de campo ou série, `data`, `items`, `image`,
`selection`). `ferramentas/extrair_design_files.py` tira um rascunho dos mesmos `.pbix` para comparar com uma
versão nova do repositório; o que mudar entra aqui à mão.

As correções de legibilidade do Deidara (eixo de meses na linha, nome inteiro no eixo das barras, seletor de
estado do segmentador de botões) não ficam neste arquivo: ficam no código, na guarda aplicada depois do estilo
(`tecnicas/c3/guarda.py`).

## O que é do Deidara, inspirado neste repositório

A geometria dos modelos (`tecnicas/arte/modelos.py`), as técnicas de visual (`dicionario/visuais.json`), o tour
guiado e o agrupador de textos são código e texto escritos para o Deidara a partir do estudo deste repositório,
sem cópia de arquivo (ver `LICENCAS-DE-TERCEIROS.md`).
