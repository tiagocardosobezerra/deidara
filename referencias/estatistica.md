# C4 Karura: a estatística do painel

O C4 Karura é a obra-prima do Deidara: bombas tão pequenas que ninguém as vê, que
agem por dentro do alvo. Aqui ele acha, dentro do número, o que o olho não vê: se a
variação é sinal ou ruído, quem está fora da curva, se a meta cabe no processo e
para onde a série anda.

**Onde a conta acontece.** O Deidara nunca vê dado. Ele escreve a fórmula em DAX, e
o Power BI calcula sobre o dado real a cada atualização, respeitando os filtros. No
protótipo, a mesma conta roda em Python com os números fictícios: o gestor vê a
forma do gráfico e aprova se quer; os limites de verdade só existem no Power BI.

**De onde vem cada fórmula.** Do NIST/SEMATECH e-Handbook of Statistical Methods
(conteúdo público, ver LICENCAS-DE-TERCEIROS.md) e da Microsoft Learn. Os testes
conferem a conta contra os exemplos resolvidos do NIST.

## As técnicas

| Técnica | Pergunta do gestor | No argila.json | Fonte |
|---|---|---|---|
| Gráfico de controle | Essa variação é real ou ruído? | medida `controle` + visual `controle` | NIST 6.3.2.2, 6.3.3.1, 6.3.3.2 |
| Sinais de leitura | Quando eu me preocupo? | vem junto: `<nome> · sinal` | NIST 6.3.2 (regras WECO) |
| Meta x faixa normal | A meta é possível do jeito que estamos? | vem junto quando a medida tem meta: `<nome> · meta x faixa` | NIST 6.3.2 |
| Fora da curva | Quem está fora do padrão? | medida `fora_da_curva` | NIST 1.3.5.17 e 6.3.3.2 |
| Tendência | Está melhorando ou piorando de fato? | entra sozinha na frase do Tobi (`leitura`) quando há calendário | Microsoft Learn, LINESTX |
| Sazonalidade | Esse mês é sempre assim? | visual `linha` com o mês no eixo e o ano na legenda | NIST 6.4.4.3 |
| Faixa típica | Qual é o normal aqui? | agregações `mediana`, `quartil_1`, `quartil_3` | NIST 1.3.3.7 |
| Previsão ou anomalia | Como vai fechar? Teve mês estranho? | `"previsao": true` ou `"anomalias": true` no visual `linha` | Microsoft Learn |

```json
{"nome": "Controle do Turnover", "tipo": "controle", "medida": "Turnover"}
{"nome": "Fora da curva no salário", "tipo": "fora_da_curva", "medida": "Remuneração Média", "categoria": "dCargo[Cargo]"}
{"nome": "Remuneração mediana", "agregacao": "mediana", "coluna": "dColaborador[Remuneração]"}
```

```json
{"tipo": "controle", "medida": "Controle do Turnover"}
{"tipo": "cartao", "medida": "Controle do Turnover · meta x faixa"}
{"tipo": "barras", "categoria": "dCargo[Cargo]", "valores": ["Remuneração Média"], "cor": "Cor Fora da curva no salário"}
{"tipo": "linha", "categoria": "dCalendario[Nome do Mês]", "legenda": "dCalendario[Ano]", "valores": ["Turnover"]}
{"tipo": "linha", "categoria": "dCalendario[Mês/Ano]", "valores": ["Turnover"], "previsao": true}
```

O esboço já monta isso pela pergunta (o C2): "é sinal ou ruído?", "estamos na
meta?", "quem está fora da curva?", "é sazonal?", "como vai fechar?" e "qual é o
normal?" levam a técnica certa para a página "Sinal ou ruído".

## Gráfico de controle

Um ponto por mês (a coluna `Ano-Mês Num` do calendário), sobre os meses do filtro.
O tipo sai da medida, sem precisar escolher:

- **Taxa em percentual** (turnover, absenteísmo): **gráfico p**. Centro p̄ = soma
  do numerador ÷ soma do denominador; limites p̄ ± 3·√(p̄(1−p̄)/n), com o n de cada
  mês. Mês com grupo menor tem limite mais largo, porque a taxa dele oscila mais.
- **Outra divisão** (acidentes por mil horas): **gráfico u**, ū ± 3·√(ū/n).
- **Valor** (contagem, soma, média): **XmR**, centro ± 3·MR̄/1,128, em que MR̄ é a
  média das diferenças entre um mês e o anterior (3 ÷ 1,128 = 2,66).

Force outro com `"grafico": "xmr" | "p" | "u"`. Precisa de `"calendario"`.

**Sinais.** Só três regras, para não gerar alarme falso: (1) ponto fora do limite;
(2) 8 meses seguidos do mesmo lado da média; (3) 6 meses seguidos subindo ou
descendo. Com todas as regras das WECO, o NIST mostra que o alarme falso sobe de 1
a cada 371 pontos para 1 a cada 92.

**Cuidados.** O NIST pede uns 20 pontos antes de confiar nos limites; o validar
avisa. Limite de controle não é meta: ele diz como o indicador costuma variar, e a
meta diz aonde o time quer chegar.

## Meta x faixa normal

Quando a medida tem meta, o controle ganha a frase `<nome> · meta x faixa`, usando
os limites com o tamanho médio do grupo:

- meta **dentro** da faixa: alguns meses batem e outros não, por acaso;
- meta **fora, do lado bom**: sem mudar o processo, ela não será atingida de forma
  estável;
- meta **fora, do lado ruim**: a meta é folgada, o processo já bate sempre.

"Lado bom" segue a polaridade (para turnover, menor é melhor).

## Fora da curva

- **Valor**: z-score **modificado**, 0,6745 × (valor − mediana) ÷ MAD, em que MAD é
  a mediana dos desvios absolutos. Acima de 3,5 é fora da curva. O NIST explica por
  que não o z-score comum: em grupo pequeno (8 cargos, 15 empresas), ele quase
  nunca passa de 3 e engana.
- **Taxa**: o **funil**, o gráfico p por unidade: (taxa − p̄) ÷ √(p̄(1−p̄)/n).
  Acima de 3 é fora. A empresa de 30 pessoas não é marcada só por ser pequena.

A medida vem com `Cor <nome>` (vermelho para quem está fora), para pintar as
barras do indicador.

## Tendência

Com calendário, a frase do Tobi ganha o trecho dos últimos 12 meses: a reta de
mínimos quadrados (`LINESTX`) dá a inclinação por mês e o r². Só com r² de 0,5 para
cima a frase afirma "tendência de alta" ou "de queda"; abaixo disso diz "sem
tendência clara". Com menos de 6 meses, fica quieta.

## Sazonalidade e faixa típica

- **Sazonalidade**: sem conta. Uma linha por ano, os meses no eixo (o gráfico por
  subsérie do NIST). Só faz sentido com 2 anos de dado ou mais.
- **Faixa típica**: `mediana`, `quartil_1` (25%) e `quartil_3` (75%) no lugar da
  média em salário, tempo de casa e afins, em que poucos valores altos puxam a
  média. Não têm conferência simples em SQL (são percentis por janela).

## Previsão e anomalia

São do próprio Power BI, no painel Análise do gráfico de linha. O Deidara monta o
gráfico e deixa o passo no LEIA-ME ("ligue Previsão no painel Análise"), porque
não grava essa opção no arquivo. As duas não funcionam juntas, e a anomalia pede
gráfico de linha sem legenda, uma medida só e pelo menos 4 pontos.

## O que ficou de fora

Correlação (lida como causa e efeito), regressão com vários fatores (precisa olhar
o dado), teste de hipótese com p-valor (o gráfico de controle responde a mesma
pergunta de um jeito que o gestor entende). O visual de principais influenciadores
só entra quando pedido: não funciona com DirectQuery nem com o grupo de cálculo.
Para depois: coorte de retenção e efeito de composição x efeito de taxa.
