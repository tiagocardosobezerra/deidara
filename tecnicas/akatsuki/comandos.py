"""
O comando da galeria (Akatsuki): o que a comunidade abriu.
"""



def cmd_galeria(a):
    """O que a comunidade abriu (terceiros/): modelos Deneb, funções DAX, calendários e SVG."""
    from tecnicas import akatsuki as galeria
    if a.ver:
        x = galeria.item(a.ver)
        if not x:
            print(f'"{a.ver}" não está na galeria (`deidara.py galeria <assunto>` lista os itens).')
            return 1
        print(f'{x["nome"]}  [{x["id"]}] · {x["tipo"]} · {x["autor"]} · licença MIT ({x["fonte"]})')
        if x.get('descricao'):
            print(f'  {x["descricao"]}')
        print(f'  Arquivo: {x["caminho"]}')
        if x['tipo'] == 'deneb':
            if x['campos']:
                print('  No argila.json (visual): {"tipo": "vegalite", "modelo": "' + x['id'] + '", "campos": {'
                      + ', '.join(f'"{c["name"]}": "<{"medida" if c.get("type") == "numeric" else "Tabela[Coluna]"}>"'
                                  for c in x['campos']) + '}}')
                for c in x['campos']:
                    print(f'    {c["name"]}: {c.get("description") or ""} ({c.get("type")}, {c.get("kind")})')
            else:
                print('  Exemplo sem campos marcados: use como referência (copie para "spec" e troque os campos).')
        if x['tipo'] == 'funcoes_dax':
            print(f'  No argila.json: "funcoes_dax": ["{x["id"]}"]; depois chame as funções no "dax" de uma medida.')
            for fn in x['funcoes']:
                print(f'    {fn["nome"]}: {fn["sobre"]}')
        if x['tipo'] == 'calendario' and x.get('paises'):
            print(f'  Feriados de {len(x["paises"])} países (Brasil incluído): "feriados": "BR" no "calendario".')
        return 0
    achados = galeria.buscar(a.termo or '', a.tipo)
    if not achados:
        print(f'Nada na galeria para "{a.termo}". Sem assunto, `deidara.py galeria` lista tudo.')
        return 1
    for x in achados[:a.limite]:
        selo = {'deneb': 'Deneb ' + x.get('provider', ''), 'funcoes_dax': f'{len(x.get("funcoes", []))} funções DAX',
                'calendario': 'calendário', 'svg': 'SVG'}[x['tipo']]
        pronto = '' if x.get('pronto_para_usar', True) else ' · exemplo'
        print(f'  {x["id"]:<58} {selo}{pronto} · {x["nome"][:50]}')
    if len(achados) > a.limite:
        print(f'  ... e mais {len(achados) - a.limite} (use --limite)')
    print('Detalhe e como usar: deidara.py galeria --ver <id>')
    return 0


def registrar(sub):
    gl = sub.add_parser('galeria', help='modelos Deneb, funções DAX, calendários e SVG da comunidade (MIT, em terceiros/)')
    gl.add_argument('termo', nargs='?', default='')
    gl.add_argument('--tipo', choices=['deneb', 'funcoes_dax', 'calendario', 'svg'])
    gl.add_argument('--ver', help='id do item: o que ele pede e como usar no argila.json')
    gl.add_argument('--limite', type=int, default=25)
    gl.set_defaults(func=cmd_galeria)
