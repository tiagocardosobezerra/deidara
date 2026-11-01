"""
================================================================================
 TÉCNICAS — o que o Deidara faz com a argila
================================================================================
Cada técnica tem o nome de uma habilidade (ou de um companheiro) do Deidara, como
os satélites do Vegapunk têm o nome de uma personalidade. Regra dos nomes: o
personagem dá nome à pasta ou ao módulo; dentro dela, os arquivos têm nome
descritivo (comandos.py, prototipo.py, pbir.py). A ordem é a do fluxo:

    te_no_kuchi/   as bocas das mãos: mastigam o pedido e moldam o esboço
    luneta/        o olho-luneta: vê a fonte de longe, sem tocar nela
                   (catálogo, receitas, descoberta, prova e o treino do olho)
    c2             o dragão que solta a bomba certa: os visuais pela pergunta
    c1/            as figuras pequenas: o protótipo para o gestor ver
    bunshin/       o clone de argila: números fictícios que parecem reais
    katsu/         a palavra que detona: o "sim" do gestor (o aceite) e o retrato
    c3/            a grande bomba depois do "Katsu!": o projeto Power BI e a
                   conferência no Desktop aberto
    arte/          "a arte é uma explosão": modelos de layout e página
    sasori/        o parceiro da arte eterna: funções e padrões conferidos
    tobi           o parceiro que não para de falar: a frase de leitura
    c4             C4 Karura, as bombas que ninguém vê: a estatística
    onoki/         o mestre que avalia: o acerto da busca e o retrato dela
    c0/            a autodestruição: desmonta o painel que já existe e o refaz
    akatsuki/      a organização de ninjas de outras vilas: o que a comunidade
                   abriu (terceiros/, a galeria)
    memory_card/   o cartão de memória do time (foge do tema de propósito,
                   como no Vegapunk: o nome é o da ideia)
    comum.py       o que os comandos têm em comum, mais validar e situacao

Camadas: o motor (`kibaku_nendo/`) não importa nenhuma técnica; quando precisa de
uma, pede pelo papel (`kibaku_nendo/registro.py`), e este arquivo diz qual módulo
faz cada papel. Cada técnica com comando tem `comandos.py` com `registrar(sub)`;
o `deidara.py` só percorre a lista.
"""

from kibaku_nendo.registro import registrar  # noqa: E402

# o que o motor pede pelo papel (kibaku_nendo/registro.py): o módulo só é importado quando o papel é pedido
registrar('dicionario', 'tecnicas.sasori')
registrar('galeria', 'tecnicas.akatsuki')
registrar('estatistica', 'tecnicas.c4')
registrar('leitura', 'tecnicas.tobi')
registrar('layout', 'tecnicas.arte.modelos')
registrar('tour', 'tecnicas.c1.tour')
registrar('prova', 'tecnicas.luneta.prova')
registrar('descoberta', 'tecnicas.luneta.descoberta')
