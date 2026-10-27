# Aviso sobre dados de terceiros

O Deidara não se conecta a nenhuma fonte de dados. Ele entrega receitas
(consultas SQL, DAX e Power Query); quem já tem acesso às fontes roda a
receita e cola o resultado. Este aviso diz o que entra, o que nunca entra e de
quem é a responsabilidade.

## O que vem neste repositório

| Vem junto | Não vem |
|---|---|
| o motor (`deidara.py`, `argila/`), o dicionário de funções e os padrões de indicador, as referências, as ferramentas e os testes | nenhum metadado de sistema real |
| um exemplo **fictício** (`exemplos/aurora`): um ERP inventado e uma planilha de metas inventada, do resultado colado ao projeto gerado | nenhum catálogo, painel, aprovação ou cartão de quem usa |

O motor **não contém, nunca conteve e nunca vai conter** estrutura de nenhum
sistema real de terceiros.

## O que nunca entra

**Só estrutura, nunca dado.** As receitas devolvem nomes de tabela e de
coluna, descrições, tipos, chaves e ligações. Nenhuma linha de cadastro,
nenhum valor. A única receita que olha para o conteúdo é a de **prova** de uma
ligação, e ela devolve só percentuais e sim/não (quantos por cento das linhas
acham par, se a chave é única), nunca um código ou um nome.

O **protótipo** usa números fictícios, gerados a partir do nome de cada
medida. Os números reais só existem no Power BI, depois que o projeto gerado é
aberto e atualizado no ambiente do time.

## Privacidade dos dados pessoais

O Deidara trata colunas que identificam pessoas (CPF, e-mail, telefone, data
de nascimento, nome numa tabela de pessoas) com cuidado:

- o esboço nunca usa uma delas como rótulo de um gráfico;
- o `validar` avisa quando uma delas entra no modelo sem ser usada em nenhum
  visual (LGPD: só o necessário);
- o Memory Card mostra uma prévia antes de gravar, só versiona a seção
  `deidara/`, não envia para um cartão que não esteja privado, e os catálogos
  das fontes nunca vão para ele.

Mesmo assim, quem decide o que o painel mostra e para quem é o time, com a
segurança por linha (RLS) quando for preciso.

## Responsabilidade pelo uso

Ao catalogar uma fonte real:

1. Você confirma que tem acesso legítimo a ela e que pode compartilhar a sua
   estrutura com quem vai montar o painel.
2. Os catálogos, as especificações (`argila.json`), as aprovações e o Memory
   Card são de sua responsabilidade e do seu time; este projeto não os
   distribui.
3. Mantenha esses arquivos fora de repositórios públicos. O cartão do time é
   criado **privado** por padrão.

## Documentação da Microsoft

Os nomes, as categorias, as assinaturas e os links do dicionário de funções
vêm da referência oficial da Microsoft (Microsoft Learn). As descrições e os
usos em pt-BR foram escritos para o Deidara; o texto da Microsoft não é
copiado. A documentação completa de cada função é a da Microsoft, no link.
Power BI, Power Query e SQL Server são marcas da Microsoft; o Deidara não tem
vínculo com a Microsoft.
