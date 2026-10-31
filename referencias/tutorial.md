# Tutorial: do zero ao projeto Power BI em 15 minutos

Um painel de turnover com o exemplo do repositório (um ERP fictício em SQL
Server e uma planilha de metas no Excel). Rode os comandos da pasta da skill.
No dia a dia, quem roda é o Claude; aqui você vê cada passo por dentro. Todos
os nomes abaixo são os que o exemplo realmente produz.

## 1. A pasta do painel (1 min)

```
python deidara.py novo C:/paineis/turnover --projeto "Turnover RH"
```

Ela vem com `receitas/` (as três consultas, prontas para mandar a quem tem
acesso às fontes), `colado/`, `catalogos/` e um `ROTEIRO.md`.

## 2. A estrutura das fontes (3 min)

Num caso real, o DBA roda `receitas/receita_sql.sql` no SSMS e você cola a
grade em `colado/erp.txt`; a receita M faz o mesmo para a planilha. No
tutorial, use os resultados que já vêm no exemplo:

```
python deidara.py catalogar --de exemplos/aurora/colado/erp_receita_sql.txt --fonte erp -o C:/paineis/turnover/catalogos/erp.json
python deidara.py catalogar --de exemplos/aurora/colado/metas_receita_m.txt --fonte metas --m exemplos/aurora/colado/m -o C:/paineis/turnover/catalogos/metas.json
```

## 3. O primeiro esboço e a ligação sugerida (2 min)

```
python deidara.py esbocar C:/paineis/turnover --pedido "desligamentos por motivo e cargo com a meta de turnover por empresa"
python deidara.py validar C:/paineis/turnover/argila.json
```

O esboço reconhece o padrão de turnover e já traz a cadeia inteira, na ordem:
`Desligamentos`, `Headcount` (ativos no fim do período), `HC Médio`,
`Turnover` (desligamentos ÷ HC médio) e a `Meta de turnover`, pesada pelo HC
médio de cada empresa (a média simples daria à empresa pequena o peso da
grande). Vêm junto o calendário, as tabelas (`fDesligamento`,
`dMotivoDesligamento`, `dCargo`, `dColaborador`, `dEmpresa`, `fMetas`) e os
visuais que o C2 escolheu pela pergunta. Para ver a cadeia explicada:
`python deidara.py padroes turnover`.

O `validar` aponta **1 erro**: a ligação da planilha com a empresa foi
*sugerida*. Num caso real, confira os campos com o dono do dado; aqui,
confirme:

```
python deidara.py confirmar C:/paineis/turnover/argila.json --ligacao "fMetas->dEmpresa" --por "Ana (RH)"
```

`--por` é o nome de quem confirmou (fica no dicionário de indicadores). Se o
dono disser que não é essa a ligação, use `--remover`. Para provar com números,
o próprio `confirmar` imprime a `receita prova`; o resultado volta com
`provar --de resultado.txt --argila ...`, que grava a prova na ligação.

## 4. As definições (3 min)

Sobram só avisos: decisões para levar ao usuário, como o "valor ATUAL" do
cargo, o dono do indicador e o servidor de exemplo em `"fontes"`. Dois deles
travam o aceite: a `descricao` (para que serve o painel) e o `publico` (para
quem é). Troque os "A DEFINIR" no `argila.json`, por exemplo:

```json
"descricao": "Onde o turnover passou da meta e por quê.",
"publico": "Diretoria de RH",
```

Num caso real, o jeito mais rápido é o briefing no `painel.json` (as respostas
do gestor) e `esbocar ... --forcar`: as definições já entram no esboço. Errou
uma vírgula no JSON? O `validar` mostra a linha.

## 5. O protótipo (2 min)

```
python deidara.py prototipar C:/paineis/turnover/argila.json
```

Abra o `argila.prototipo.html`: clique no ⓘ de um cartão e veja a aba **Para
aprovar**. É isso que o gestor usa para dizer "sim" (ou pedir mudanças). O
botão "Copiar resumo do aceite" gera um texto com o código do protótipo e a
decisão; salve em um arquivo e passe em `aprovar --resumo resumo.txt`.

## 6. Aceite e projeto (2 min)

```
python deidara.py aprovar C:/paineis/turnover/argila.json --por "Gestor de RH"
python deidara.py gerar C:/paineis/turnover/argila.json -o C:/paineis/turnover/pbi
python deidara.py situacao C:/paineis/turnover/argila.json
```

Na pasta `pbi/`: o `.pbip`, o `LEIA-ME.md` (quem faz o quê e o que fazer se
algo der errado), o `HOMOLOGACAO.md` (o que conferir antes de publicar, com
onde ler cada número no painel) e o SQL, incluindo o headcount de cada fim de
mês para comparar com o painel.

## 7. (Opcional) O Memory Card do time (1 min)

```
python deidara.py memory-card iniciar --pasta C:/paineis/cartao-teste
python deidara.py memory-card enviar C:/paineis/turnover/argila.json --categoria "Recursos Humanos" --secao "Turnover"
```

O primeiro `enviar` mostra a prévia; com `--confirmar`, grava. Num caso real,
use `iniciar --repo DONO/memory-card` (o cartão do time no GitHub).
