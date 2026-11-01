"""
C0 · relato: o estudo em texto. No terminal, o resumo e o mais grave primeiro; em Markdown (c0_relatorio.md),
a ficha completa de cada medida para levar ao dono do indicador.
"""

import json

from tecnicas.c0.exame import ROTULO
from tecnicas.c0 import anatomia
from tecnicas.c0 import proposta as pr

ORDEM_NOTA = lambda x: (x[1]['nota'], x[0])   # noqa: E731  as piores primeiro


def mascarar(texto):
    """CPF e e-mail escritos na fórmula não saem no relatório (ele vai para o gestor e pode ir para o Memory Card)."""
    import re
    texto = re.sub(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '***.***.***-**', texto or '')
    return re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '***@***', texto)


PADRAO_PT = {'agregacao': 'soma ou contagem', 'divisao': 'taxa (divisão)', 'acumulado_ano': 'acumulado no ano',
             'ano_anterior': 'ano anterior', 'variacao_ano_anterior': 'variação contra o ano anterior',
             'mes_anterior': 'mês anterior', 'variacao_mes_anterior': 'variação contra o mês anterior',
             'movel_12m': 'últimos 12 meses', 'media_mensal': 'média dos meses', 'estoque_na_data': 'estoque na data',
             'filtrada': 'recorte de outra medida', 'meta_fixa': 'número fixo', 'svg': 'imagem', 'ranking': 'ranking',
             'cor': 'cor', 'texto': 'texto', 'tempo': 'conta de tempo', 'livre': 'conta própria'}


def no_painel(leg):
    """As medidas que aparecem em algum visual do relatório lido."""
    return {c['nome'] for pg in leg.get('paginas') or [] for v in pg['visuais'] for c in v['campos'] if c['tipo'] == 'medida'}


def para_gestor(leg, estudo, propostas=None):
    """O resumo de uma página, em linguagem de negócio: o que está errado no painel, o que muda e o que decidir."""
    vistas = no_painel(leg)
    alvo = [n for n in estudo['medidas'] if not leg['medidas'][n].get('oculta') and (not vistas or n in vistas)]
    errados = []
    for n in sorted(alvo, key=lambda n: estudo['medidas'][n]['nota']):
        x = estudo['medidas'][n]
        graves = [a for a in x['achados'] if a['gravidade'] in ('critico', 'alto')]
        if graves:
            errados.append(f'**{n}**: {graves[0]["efeito"]}.')
        elif x.get('nota_herdada') and x['herdados']:
            tit = x['herdados'][0][1]
            errados.append(f'**{n}**: usa [{x["herdados"][0][0]}], que tem problema ({tit[:1].lower() + tit[1:]}).')
    out = []
    if errados:
        out += [('No painel, ' if vistas else '') + f'{len(errados)} indicador(es) com número errado ou em risco:', '']
        out += [f'- {e}' for e in errados[:15]] + ([f'- ... e mais {len(errados) - 15} (na tabela abaixo)']
                                                     if len(errados) > 15 else []) + ['']
    else:
        out += ['Nenhum indicador com número errado ou em risco.', '']
    if propostas:
        muda = [(n, p['muda_o_numero']) for n, p in propostas.items() if p['muda_o_numero'] and n in alvo]
        if muda:
            out += ['Se refizermos no Deidara, estes números mudam (é a correção, não um erro novo):', '']
            out += [f'- **{n}**: ' + '; '.join(m) for n, m in muda] + ['']
    decidir = [n for n in alvo if not (leg['medidas'][n].get('descricao') or '').strip()]
    if decidir and leg['origem'] != 'dax':
        out += [f'Para o dono do indicador definir (hoje sem definição escrita): {", ".join(decidir)}.', '']
    return out


def _cortado(dax, linhas=40):
    partes = (dax or '').split('\n')
    return dax if len(partes) <= linhas else '\n'.join(partes[:linhas] + [f'-- ... mais {len(partes) - linhas} linha(s)'])


def _faixa(n):
    return 'reprovado' if n < 5 else 'com ressalvas' if n < 8 else 'bom' if n < 9.5 else 'ótimo'


def resumo(leg, estudo):
    meds = estudo['medidas']
    cont = {}
    for x in meds.values():
        for a in x['achados']:
            cont[a['gravidade']] = cont.get(a['gravidade'], 0) + 1
    for a in estudo['modelo']:
        cont[a['gravidade']] = cont.get(a['gravidade'], 0) + 1
    origem = {'pbip': 'projeto Power BI (.pbip)', 'receita': 'resultado da receita DAX', 'dax': 'DAX colado'}[leg['origem']]
    partes = [f'{n} {ROTULO[g].lower()}' for g, n in sorted(cont.items(), key=lambda x: list(ROTULO).index(x[0]))]
    return (f'C0 · {origem}: {len(leg["tabelas"])} tabela(s), {len(meds)} medida(s), '
            f'{len(leg.get("paginas") or [])} página(s). Nota {estudo["nota"]:.1f} ({_faixa(estudo["nota"])})'
            + (f' · {", ".join(partes)}' if partes else ' · nada a corrigir'))


def terminal(leg, estudo, detalhe=False, propostas=None):
    out = [resumo(leg, estudo), ''] + [x.replace('**', '') for x in para_gestor(leg, estudo, propostas)]
    if estudo['modelo']:
        out.append('Modelo:')
        for a in estudo['modelo']:
            out.append(f'  [{ROTULO[a["gravidade"]]}] {a["titulo"]}: {a["efeito"]}. → {a["correcao"]}')
        out.append('')
    for nome, x in sorted(estudo['medidas'].items(), key=ORDEM_NOTA):
        if not detalhe and not x['achados'] and not x.get('nota_herdada'):
            continue
        md = leg['medidas'][nome]
        out.append(f'[{nome}]  nota {x["nota"]:.1f} · {PADRAO_PT.get(x["padrao"]["tipo"], x["padrao"]["tipo"])}'
                   + (' · no painel' if nome in no_painel(leg) else ''))
        out.append(f'  O que é: {md.get("descricao") or "(sem descrição)"}')
        out.append(f'  O que a fórmula faz: {x["leitura"]}')
        for a in x['achados']:
            out.append(f'  [{ROTULO[a["gravidade"]]}] {a["titulo"]}: {a["efeito"]}.')
            out.append(f'      → {a["correcao"]}' + (f' ({a["evidencia"]})' if a.get('evidencia') else ''))
        for dep, tit in x.get('herdados') or []:
            out.append(f'  herda de [{dep}]: {tit}')
        if detalhe:
            out.append('  Árvore:')
            out += ['    ' + l for l in anatomia.desenhar(anatomia.arvore(nome, leg))]
        if propostas and nome in propostas:
            _proposta_texto(out, propostas[nome])
        out.append('')
    ok = [n for n, x in estudo['medidas'].items() if not x['achados'] and not x.get('nota_herdada')]
    if ok and not detalhe:
        out.append(f'Sem nada a corrigir: {", ".join(ok[:12])}' + (' ...' if len(ok) > 12 else ''))
    return '\n'.join(out).rstrip() + '\n'


def _proposta_texto(out, p):
    if p['muda_o_numero']:
        out.append('  ⚠ Muda o número: ' + '; '.join(p['muda_o_numero']))
    if p['dax_sugerido']:
        out.append('  DAX corrigido (mesmo número): ' + mascarar(p['dax_sugerido']).replace('\n', ' '))
    out.append('  No Deidara (argila.json):')
    out += ['    ' + mascarar(json.dumps(m, ensure_ascii=False)) for m in p['argila']]
    for m in p['melhorias']:
        out.append(f'  + {m}')


def markdown(leg, estudo, propostas=False):
    props = {n: pr.propor(n, leg, x, estudo['medidas']) for n, x in estudo['medidas'].items()} if propostas else None
    out = ['# C0 · estudo do indicador', '', resumo(leg, estudo), '', '## Em uma página', '']
    out += para_gestor(leg, estudo, props)
    out += ['',
           'Notas: crítico = o número sai errado (a medida não passa de 4); alto = errado em parte dos cortes ou '
           'períodos (não passa de 7); médio = risco ou governança; baixo = estilo. Só a estrutura foi lida: '
           'nenhum dado.', '']
    if estudo['modelo']:
        out += ['## O modelo', '']
        out += [f'- **{ROTULO[a["gravidade"]]}** — {a["titulo"]}: {a["efeito"]}. *Correção:* {a["correcao"]}.'
                for a in estudo['modelo']]
        extra = pr.propor_modelo(leg, estudo) if propostas else []
        out += [f'- *Proposta:* {x}' for x in extra] + ['']
    vistas = no_painel(leg)
    out += ['## As medidas', '', '| Medida | No painel | Nota | O que é | Problemas |', '|---|---|---|---|---|']
    for nome, x in sorted(estudo['medidas'].items(), key=ORDEM_NOTA):
        probs = [f'{ROTULO[a["gravidade"]]}: {a["titulo"]}' for a in x['achados']]
        if x.get('nota_herdada') and x['herdados']:
            probs.append(f'herda de [{x["herdados"][0][0]}]')
        out.append(f'| {nome} | {"sim" if nome in vistas else ""} | {x["nota"]:.1f} | '
                   f'{PADRAO_PT.get(x["padrao"]["tipo"], x["padrao"]["tipo"])} | {", ".join(probs).replace("|", "/") or "—"} |')
    out.append('')
    grande = len(estudo['medidas']) > 150
    if grande:
        out += [f'Modelo grande ({len(estudo["medidas"])} medidas): a ficha abaixo detalha só as medidas com problema '
                'ou que aparecem no painel; o DAX longo vem cortado (o inteiro está no modelo).', '']
    for nome, x in sorted(estudo['medidas'].items(), key=ORDEM_NOTA):
        md = leg['medidas'][nome]
        graves = any(a['gravidade'] in ('critico', 'alto') for a in x['achados'])
        if grande and not graves and nome not in vistas:
            continue
        out += [f'### {nome}', '', f'- **Nota:** {x["nota"]:.1f} ({_faixa(x["nota"])})',
                f'- **Definição registrada:** {md.get("descricao") or "nenhuma"}',
                f'- **O que a fórmula faz:** {x["leitura"]}',
                f'- **Formato:** {md.get("formato") or "nenhum"} · **Pasta:** {md.get("pasta") or "—"}', '',
                '```dax', f'{nome} =', mascarar(_cortado(md['dax'])), '```', '', 'Árvore:', '', '```']
        out += anatomia.desenhar(anatomia.arvore(nome, leg, 3)) + ['```', '']
        for a in x['achados']:
            out.append(f'- **{ROTULO[a["gravidade"]]}** — {a["titulo"]}: {a["efeito"]}. *Correção:* {a["correcao"]}.'
                       + (f' (`{a["evidencia"]}`)' if a.get('evidencia') else ''))
        for dep, tit in x.get('herdados') or []:
            out.append(f'- herda de [{dep}]: {tit}')
        if propostas:
            p = props[nome]
            if p['muda_o_numero']:
                out.append('- **Muda o número:** ' + '; '.join(p['muda_o_numero']))
            if p['dax_sugerido']:
                out += ['', 'DAX corrigido (mesmo número):', '', '```dax', mascarar(p['dax_sugerido']), '```']
            out += ['', 'No Deidara:', '', '```json'] + [mascarar(json.dumps(m, ensure_ascii=False)) for m in p['argila']] + ['```']
            out += [f'- {m}' for m in p['melhorias']]
        out.append('')
    return '\n'.join(out).rstrip() + '\n'
