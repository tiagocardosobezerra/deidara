"""
Memory Card: a seção do Deidara no cartão de memória do time.

Como o memory card de um videogame: cada painel aprovado fica salvo (um
"save"), com versão e histórico, para ser carregado de novo quando precisar.
O cartão é UM repositório do time (`memory-card`, privado); cada solução tem a
sua seção, com a estrutura padrão. O Deidara só lê e grava a seção `deidara/`:
nunca toca nos arquivos da raiz nem nas outras seções.

    memory-card/
    ├── README.md                       o cartão (só é criado se ainda não existir)
    ├── ...                             outras soluções (não são tocadas)
    └── deidara/                        a seção do Deidara
        ├── README.md                   o que é a seção
        ├── CATALOGO.md                 gerado a cada envio
        └── saves/
            ├── <categoria>/<secao>/<artigo>/        um painel
            │   ├── README.md               o artigo (corpo entre <!-- corpo --> e <!-- /corpo -->)
            │   ├── ficha.json              versão, status, aprovação, fontes, indicadores, histórico, conferência
            │   ├── argila.json             a especificação aprovada
            │   ├── dicionario_indicadores.md
            │   └── prototipo.html
            └── indicadores/<pasta>/<indicador>/     um indicador
                ├── README.md
                └── ficha.json              definição, DAX, especificação, status, painéis, histórico

REF = <categoria>/<secao>/<artigo> (relativo a deidara/saves/). Status:
`rascunho` (padrão), `em-uso`; indicador também pode ser `oficial`.

Procure antes, ofereça depois: `buscar` antes de criar; depois do aceite,
`enviar` mostra a prévia e só grava com `--confirmar`; mudança pede
`--motivo`. Os catálogos (estrutura das fontes) NUNCA vão para o cartão.
"""

import datetime
import json
import os
import re
import shutil
import subprocess

from .util import chave, gravar_json, gravar_texto, ler_json, sem_acento

NOME_PADRAO = 'memory-card'
SECAO = 'deidara'
RAIZ_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RAIZ_SKILL, 'local', 'memory_card.json')
STATUS = ('rascunho', 'em-uso')
STATUS_INDICADOR = STATUS + ('oficial',)
CORPO_INI, CORPO_FIM = '<!-- corpo -->', '<!-- /corpo -->'


def slug(texto):
    return re.sub(r'[^a-z0-9]+', '-', sem_acento(texto or '').lower()).strip('-') or 'sem-nome'


def _agora():
    return datetime.datetime.now().strftime('%d/%m/%Y %H:%M')


# ============================================================ configuração
def configuracao():
    """{'repo','pasta'}; DEIDARA_MEMORY_CARD_REPO/DIR têm precedência; DEIDARA_MEMORY_CARD_DIR=- desliga."""
    cfg = ler_json(CONFIG) if os.path.exists(CONFIG) else {}
    if os.environ.get('DEIDARA_MEMORY_CARD_DIR') == '-':
        return {}
    for k, env in (('repo', 'DEIDARA_MEMORY_CARD_REPO'), ('pasta', 'DEIDARA_MEMORY_CARD_DIR')):
        if os.environ.get(env):
            cfg[k] = os.environ[env]
    return cfg if cfg.get('pasta') else {}


def secao(pasta):
    return os.path.join(pasta, SECAO)


def _rodar(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8')
    except FileNotFoundError:
        return None


def _git(pasta, *args):
    return _rodar(['git', '-C', pasta, *args])


README_RAIZ = """# Memory Card

O cartão de memória do time: cada solução guarda aqui, na sua seção, o que foi
aprovado e salvo, com versão e histórico.

- [deidara/](deidara/): painéis e indicadores (Power BI).
"""

README_SECAO = """# Memory Card — seção Deidara

Os painéis e indicadores do time: cada painel aprovado no Deidara fica salvo aqui
(um "save"), com versão, histórico e o que foi aprovado; cada indicador também,
com a sua definição (e a OFICIAL, quando houver).

- [CATALOGO.md](CATALOGO.md): os painéis por categoria e seção, e os indicadores (oficiais primeiro).
- `saves/<categoria>/<secao>/<artigo>/`: um painel (artigo, ficha, especificação, dicionário, protótipo).
- `saves/indicadores/<pasta>/<indicador>/`: um indicador (definição, fórmula, painéis que usam, histórico).

Não edite à mão: use `deidara.py memory-card` (enviar, marcar, conferir). O texto do
artigo, entre `<!-- corpo -->` e `<!-- /corpo -->`, pode ser editado.

A estrutura das fontes (catálogos) nunca vem para o cartão.
"""


def iniciar(repo=None, pasta=None, publico=False):
    """Cria (privado) ou liga o cartão, clona e grava a configuração."""
    repo = repo or None
    pasta = os.path.abspath(pasta or os.path.join(os.path.expanduser('~'), (repo or NOME_PADRAO).split('/')[-1]))
    msgs = []
    if repo:
        if repo.split('/')[-1] != NOME_PADRAO:
            msgs.append(f'aviso: o cartão do time costuma ser {NOME_PADRAO}; usando {repo}')
        vis = _rodar(['gh', 'repo', 'view', repo, '--json', 'visibility', '--jq', '.visibility'])
        if vis is None:
            raise ValueError('o `gh` (GitHub CLI) não está instalado: instale e rode `gh auth login`')
        if vis.returncode != 0:
            r = _rodar(['gh', 'repo', 'create', repo, '--public' if publico else '--private',
                        '--description', 'Memory Card do time'])
            if r.returncode != 0:
                raise ValueError(f'não consegui criar {repo}: {r.stderr.strip()[:300]}')
            msgs.append(f'repositório {repo} criado ({"público" if publico else "privado"})')
        elif vis.stdout.strip().upper() == 'PUBLIC' and not publico:
            raise ValueError(f'{repo} é PÚBLICO: um painel leva nomes de tabela e coluna das fontes. Use um '
                             'repositório privado ou, se for de propósito, --publico')
        if os.path.isdir(os.path.join(pasta, '.git')):
            url = _git(pasta, 'remote', 'get-url', 'origin')
            if url and url.returncode == 0 and repo.lower() not in url.stdout.strip().lower():
                raise ValueError(f'{pasta} é um clone de outro repositório ({url.stdout.strip()}): use --pasta')
            msgs.append(f'usando o clone que já existe em {pasta}')
        else:
            if os.path.isdir(pasta) and os.listdir(pasta):
                raise ValueError(f'{pasta} já existe e não é o cartão: use --pasta')
            r = _rodar(['gh', 'repo', 'clone', repo, pasta])
            if r.returncode != 0:
                raise ValueError(f'não consegui clonar {repo}: {r.stderr.strip()[:300]}')
            msgs.append(f'cartão clonado em {pasta}')
    else:
        os.makedirs(pasta, exist_ok=True)
        if not os.path.isdir(os.path.join(pasta, '.git')) and shutil.which('git'):
            _git(pasta, 'init', '-q')
        msgs.append(f'cartão local em {pasta} (sem repositório remoto: nada é enviado)')
    _atualizar(pasta)
    os.makedirs(os.path.join(pasta, SECAO, 'saves'), exist_ok=True)
    novos = []
    if not os.path.exists(os.path.join(pasta, 'README.md')):
        gravar_texto(os.path.join(pasta, 'README.md'), README_RAIZ)     # cartão novo: a raiz ainda não existe
        novos.append('README.md')
    if not os.path.exists(os.path.join(pasta, SECAO, 'README.md')):
        gravar_texto(os.path.join(pasta, SECAO, 'README.md'), README_SECAO)
        _catalogo_md(pasta)
        msgs.append(_commit(pasta, 'Memory Card: seção deidara', novos, repo, publico))
    else:
        msgs.append(f'a seção {SECAO}/ já existe no cartão')
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    gravar_json(CONFIG, {'repo': repo, 'pasta': pasta, 'publico': publico})
    msgs.append(f'configuração em {CONFIG}')
    return msgs


# ================================================================== leitura
def saves(pasta):
    """[(ref, ficha)] de todos os saves."""
    base = os.path.join(pasta, SECAO, 'saves')
    out = []
    for raiz, _, arqs in os.walk(base):
        if 'ficha.json' in arqs:
            ref = os.path.relpath(raiz, base).replace(os.sep, '/')
            out.append((ref, ler_json(os.path.join(raiz, 'ficha.json'))))
    return sorted(out)


def indicadores(pasta):
    return {chave(f['nome']): (ref, f) for ref, f in saves(pasta) if f.get('tipo') == 'indicador'}


def _texto_do_save(pasta, ref):
    arq = os.path.join(pasta, SECAO, 'saves', ref, 'README.md')
    return open(arq, encoding='utf-8').read() if os.path.exists(arq) else ''


def buscar(pasta, termos, limite=10):
    """Título e descrição pesam mais; depois categoria, seção, indicadores e fontes; depois o artigo."""
    ts = [chave(t) for t in ' '.join(termos).split() if t.strip()]
    out = []
    for ref, f in saves(pasta):
        alto = chave(' '.join([f.get('titulo', ''), f.get('descricao', '')]))
        medio = chave(' '.join([f.get('categoria', ''), f.get('secao', ''), ' '.join(f.get('indicadores', [])),
                                ' '.join(f.get('fontes', {})), f.get('dax', '')]))
        baixo = chave(_texto_do_save(pasta, ref))
        pontos = 0
        for t in ts:
            pontos += 3 if t in alto else 2 if t in medio else 1 if t in baixo else -100
        if pontos > 0:
            out.append((pontos + (2 if f.get('status') == 'oficial' else 0), ref, f))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [(ref, f) for _, ref, f in out[:limite]]


# ============================================================ comparação
def _ind_do_modelo(md, argila):
    bruta = next((x for x in argila.get('medidas', []) if chave(x.get('nome', '')) == chave(md['nome'])), {})
    return {'nome': md['nome'], 'descricao': md['descricao'], 'dax': md['dax'], 'formato': md['formato'],
            'polaridade': md['polaridade'], 'pasta': md['pasta'] or 'Geral', 'meta': md.get('meta_medida'),
            'especificacao': bruta}


def diferencas_indicador(antes, depois):
    out = []
    if (antes.get('dax') or '').strip() != (depois.get('dax') or '').strip():
        out.append('FÓRMULA mudou (o número muda)')
    if (antes.get('descricao') or '').strip() != (depois.get('descricao') or '').strip():
        out.append('definição mudou')
    for k in ('formato', 'polaridade', 'meta'):
        if antes.get(k) != depois.get(k):
            out.append(f'{k}: {antes.get(k) or "—"} → {depois.get(k) or "—"}')
    return out


def _medidas_reais(modelo):
    return [md for md in modelo['medidas'] if md['tipo'] not in ('cor', 'meta')]


def avisos_do_modelo(pasta, modelo):
    """Para o `validar`: medida com o nome de um indicador do cartão, mas com outra definição."""
    if not pasta or not os.path.isdir(os.path.join(pasta, SECAO, 'saves')):
        return []
    lib = indicadores(pasta)
    out = []
    for md in _medidas_reais(modelo):
        if chave(md['nome']) not in lib:
            continue
        ref, f = lib[chave(md['nome'])]
        dif = diferencas_indicador(f, _ind_do_modelo(md, {}))
        if not dif:
            continue
        oficial = f.get('status') == 'oficial'
        out.append(f'medida {md["nome"]}: difere do indicador {"OFICIAL" if oficial else "do Memory Card"} '
                   f'{ref} (v{f["versao"]}): {"; ".join(dif)}. '
                   + ('Use a definição oficial ou dê outro nome ao indicador.' if oficial else
                      'Reaproveite a definição ou explique a diferença ao enviar (--motivo).'))
    return out


# ================================================================== enviar
def planejar(pasta, argila, modelo, aprovacao, categoria, secao, artigo, motivo, texto, relacionados, status):
    """A prévia do `enviar`: o que vai mudar, versões, bloqueios e o artigo como vai ficar."""
    from . import governanca
    ref = f'{slug(categoria)}/{slug(secao)}/{slug(artigo or modelo["projeto"])}'
    atual = dict(saves(pasta)).get(ref)
    retrato = governanca.retrato(modelo)
    mud = governanca.diferencas((atual or {}).get('retrato') or {}, retrato) if atual else []
    lib = indicadores(pasta)
    inds, bloqueios, erros = [], [], []
    for md in _medidas_reais(modelo):
        novo = _ind_do_modelo(md, argila)
        iref = f'indicadores/{slug(novo["pasta"])}/{slug(md["nome"])}'
        existente = lib.get(chave(md['nome']))
        if existente:
            iref = existente[0]
        dif = diferencas_indicador(existente[1], novo) if existente else []
        estado = 'novo' if not existente else 'alterado' if dif else 'igual'
        if estado == 'alterado' and existente[1].get('status') == 'oficial':
            bloqueios.append(f'{md["nome"]} é OFICIAL ({iref}) e este painel muda: {"; ".join(dif)}. Use a definição '
                             'oficial, renomeie o indicador, ou tire o oficial antes (`memory-card marcar ... '
                             '--status em-uso --motivo`)')
        inds.append({'nome': md['nome'], 'ref': iref, 'estado': estado, 'mudancas': dif, 'registro': novo,
                     'versao': (existente[1]['versao'] + (1 if dif else 0)) if existente else 1})
    if not atual and not texto:
        texto = _corpo_padrao(modelo, aprovacao)
    if atual and mud and not motivo:
        erros.append('o painel já está no cartão e mudou: informe --motivo "<por que mudou>"')
    if any(i['estado'] == 'alterado' for i in inds) and not motivo:
        erros.append('há indicador já salvo com definição diferente: informe --motivo')
    if status and status not in STATUS:
        erros.append(f'status de painel: {", ".join(STATUS)}')
    for r in relacionados or []:
        if r not in dict(saves(pasta)):
            erros.append(f'relacionado {r} não existe no cartão')
    versao = (atual['versao'] + (1 if mud else 0)) if atual else 1
    return {'ref': ref, 'atual': atual, 'novo': atual is None, 'mudancas': mud, 'versao': versao,
            'indicadores': inds, 'bloqueios': bloqueios, 'erros': erros, 'texto': texto, 'motivo': motivo,
            'status': status or (atual or {}).get('status') or 'rascunho', 'categoria': categoria, 'secao': secao,
            'titulo': artigo or modelo['projeto'], 'relacionados': list(relacionados or []),
            'aprovacao': aprovacao, 'retrato': retrato, 'descricao': modelo['descricao'],
            'fontes': {n: f['tipo'] for n, f in modelo['fontes'].items()}}


def _corpo_padrao(modelo, aprovacao):
    inds = '\n'.join(f'- **{md["nome"]}**: {md["descricao"] or "—"}' for md in _medidas_reais(modelo))
    fontes = '\n'.join(f'- `{n}` ({f["tipo"]})' for n, f in modelo['fontes'].items())
    ligs = '\n'.join(f'- {r["de"]}[{r["de_coluna"]}] → {r["para"]}[{r["para_coluna"]}] — {r["prova"]}'
                     for r in modelo['relacionamentos'])
    avisos = '\n'.join(f'- {a}' for a in aprovacao.get('avisos_aceitos') or []) or '- Nenhuma registrada.'
    return f"""## O que faz

{modelo['descricao'] or '—'}

## Quando usar

Público: {modelo['publico'] or '—'}.

## Como funciona

Fontes:
{fontes}

Ligações (com a prova de cada uma):
{ligs or '- —'}

## Indicadores

{inds or '- —'}

## Regras de negócio

As definições acima, aprovadas por {aprovacao.get('aprovado_por') or '—'} em {aprovacao.get('em') or '—'}.

## Limitações

{avisos}
"""


def _readme(f, corpo, rel_links, artefatos):
    hist = '\n'.join(f'| v{h["versao"]} | {h["em"]} | {h.get("por") or "—"} | {h.get("motivo") or "—"} |'
                     for h in reversed(f.get('historico', [])))
    rel = '\n'.join(f'- [{t}](../../../{r}/)' for r, t in rel_links) or '- —'
    art = '\n'.join(f'- [{n}]({n})' for n in artefatos)
    conf = f.get('conferencia') or {}
    conf_txt = f'{conf.get("situacao")} em {conf.get("em")}' if conf else 'ainda não conferido'
    return f"""# {f['titulo']}

**{f['categoria']} › {f['secao']}** · versão {f['versao']} · status **{f['status']}**

{f.get('descricao') or ''}

{CORPO_INI}
{corpo.strip()}
{CORPO_FIM}

## {'O painel' if f['tipo'] == 'painel' else 'O indicador'}

{art}

Última conferência: {conf_txt}.

## Relacionados

{rel}

## Histórico

| Versão | Data | Por | Motivo |
|---|---|---|---|
{hist}
"""


def _corpo_existente(pasta, ref):
    texto = _texto_do_save(pasta, ref)
    if CORPO_INI in texto and CORPO_FIM in texto:
        return texto.split(CORPO_INI, 1)[1].split(CORPO_FIM, 1)[0]
    return None


def _corpo_indicador(reg):
    esp = json.dumps(reg['especificacao'], ensure_ascii=False, indent=1) if reg.get('especificacao') else '—'
    return f"""## Definição

{reg['descricao'] or '—'}

## Fórmula (DAX)

```dax
{reg['dax']}
```

Formato: {reg['formato'] or '—'} · polaridade: {(reg.get('polaridade') or '').replace('_', ' ')} · meta: {reg.get('meta') or '—'}

## Especificação no Deidara (argila.json)

```json
{esp}
```
"""


def gravar(pasta, plano, por, caminho_argila, artefatos):
    """Grava o plano (já confirmado), atualiza relacionados e catálogo, faz commit e push."""
    if plano['bloqueios'] or plano['erros']:
        raise ValueError('\n'.join(plano['bloqueios'] + plano['erros']))
    hoje = _agora()
    ref, atual = plano['ref'], plano['atual'] or {}
    dsave = os.path.join(pasta, SECAO, 'saves', *ref.split('/'))
    os.makedirs(dsave, exist_ok=True)
    corpo = plano['texto'] or _corpo_existente(pasta, ref) or ''
    hist = list(atual.get('historico', []))
    if plano['novo'] or plano['mudancas']:
        hist.append({'versao': plano['versao'], 'em': hoje, 'por': por,
                     'motivo': plano['motivo'] or 'primeira versão no cartão',
                     'mudancas': plano['mudancas'] or ['primeira versão no cartão']})
    rel_inds = [i['ref'] for i in plano['indicadores']]
    rels = list(dict.fromkeys(list(atual.get('relacionados', [])) + plano['relacionados'] + rel_inds))
    aprov = plano['aprovacao']
    ficha = {'tipo': 'painel', 'titulo': plano['titulo'], 'categoria': plano['categoria'], 'secao': plano['secao'],
             'descricao': plano['descricao'], 'versao': plano['versao'], 'status': plano['status'],
             'versao_painel': plano['retrato'].get('versao') or '', 'aprovado_por': aprov.get('aprovado_por'),
             'aprovado_em': aprov.get('em'), 'salvo_por': por, 'salvo_em': hoje,
             'fontes': plano['fontes'],
             'indicadores': [i['nome'] for i in plano['indicadores']], 'relacionados': rels,
             'retrato': plano['retrato'], 'historico': hist, 'conferencia': atual.get('conferencia')}
    shutil.copyfile(caminho_argila, os.path.join(dsave, 'argila.json'))
    nomes_art = ['argila.json']
    for nome, origem in artefatos.items():
        if origem and os.path.exists(origem):
            shutil.copyfile(origem, os.path.join(dsave, nome))
            nomes_art.append(nome)
    titulos = {r: f.get('titulo', r) for r, f in saves(pasta)}
    for i in plano['indicadores']:
        titulos[i['ref']] = i['nome']
    gravar_json(os.path.join(dsave, 'ficha.json'), ficha)
    gravar_texto(os.path.join(dsave, 'README.md'), _readme(ficha, corpo, [(r, titulos.get(r, r)) for r in rels], nomes_art))
    for i in plano['indicadores']:
        _gravar_indicador(pasta, i, ref, plano['titulo'], por, plano['motivo'], hoje)
    for r in plano['relacionados']:
        _ligar_de_volta(pasta, r, ref, plano['titulo'])
    _catalogo_md(pasta)
    return _commit(pasta, f'{plano["titulo"]} v{plano["versao"]}: {plano["motivo"] or "novo no cartão"}')


def _gravar_indicador(pasta, i, ref_painel, titulo_painel, por, motivo, hoje):
    dind = os.path.join(pasta, SECAO, 'saves', *i['ref'].split('/'))
    os.makedirs(dind, exist_ok=True)
    arq = os.path.join(dind, 'ficha.json')
    atual = ler_json(arq) if os.path.exists(arq) else None
    reg = i['registro']
    if atual is None:
        ficha = {'tipo': 'indicador', 'titulo': reg['nome'], 'nome': reg['nome'], 'categoria': 'Indicadores',
                 'secao': reg['pasta'], 'descricao': reg['descricao'], 'versao': 1, 'status': 'rascunho',
                 **{k: reg[k] for k in ('dax', 'formato', 'polaridade', 'meta', 'especificacao')},
                 'relacionados': [ref_painel],
                 'historico': [{'versao': 1, 'em': hoje, 'por': por, 'motivo': f'criado em {titulo_painel}',
                                'mudancas': ['criado']}]}
    else:
        ficha = dict(atual)
        ficha['relacionados'] = list(dict.fromkeys(atual.get('relacionados', []) + [ref_painel]))
        if i['mudancas']:
            ficha.update({'descricao': reg['descricao'],
                          **{k: reg[k] for k in ('dax', 'formato', 'polaridade', 'meta', 'especificacao')},
                          'versao': atual['versao'] + 1})
            ficha['historico'] = atual.get('historico', []) + [{
                'versao': ficha['versao'], 'em': hoje, 'por': por, 'motivo': motivo, 'mudancas': i['mudancas'],
                'painel': titulo_painel, 'dax_anterior': atual.get('dax')}]
    gravar_json(arq, ficha)
    _reescrever_readme(pasta, i['ref'], ficha, _corpo_indicador(ficha))


def _reescrever_readme(pasta, ref, ficha, corpo=None):
    titulos = {r: f.get('titulo', r) for r, f in saves(pasta)}
    corpo = corpo if corpo is not None else (_corpo_existente(pasta, ref) or '')
    artefatos = [] if ficha['tipo'] == 'indicador' else [n for n in ('argila.json', 'dicionario_indicadores.md',
                                                                      'prototipo.html')
                                                         if os.path.exists(os.path.join(pasta, SECAO, 'saves', ref, n))]
    gravar_texto(os.path.join(pasta, SECAO, 'saves', *ref.split('/'), 'README.md'),
                 _readme(ficha, corpo, [(r, titulos.get(r, r)) for r in ficha.get('relacionados', [])], artefatos))


def _ligar_de_volta(pasta, ref, outro, titulo):
    arq = os.path.join(pasta, SECAO, 'saves', *ref.split('/'), 'ficha.json')
    f = ler_json(arq)
    if outro not in f.get('relacionados', []):
        f['relacionados'] = f.get('relacionados', []) + [outro]
        gravar_json(arq, f)
        _reescrever_readme(pasta, ref, f)


def marcar(pasta, ref, status, por, motivo=None):
    arq = os.path.join(pasta, SECAO, 'saves', *ref.split('/'), 'ficha.json')
    if not os.path.exists(arq):
        raise ValueError(f'{ref} não existe no cartão (veja `memory-card catalogo`)')
    f = ler_json(arq)
    validos = STATUS_INDICADOR if f['tipo'] == 'indicador' else STATUS
    if status not in validos:
        raise ValueError(f'status válidos para {f["tipo"]}: {", ".join(validos)}')
    if (status == 'oficial' or f.get('status') == 'oficial') and not motivo:
        raise ValueError('tornar ou deixar de ser OFICIAL pede --motivo')
    if f.get('status') == status:
        return f'{ref} já está como {status}'
    f['historico'] = f.get('historico', []) + [{'versao': f['versao'], 'em': _agora(), 'por': por,
                                                 'motivo': motivo or f'status: {status}',
                                                 'mudancas': [f'status {f.get("status")} → {status}']}]
    f['status'] = status
    gravar_json(arq, f)
    _reescrever_readme(pasta, ref, f, _corpo_indicador(f) if f['tipo'] == 'indicador' else None)
    _catalogo_md(pasta)
    return _commit(pasta, f'{f["titulo"]}: {status}' + (f' ({motivo})' if motivo else ''))


def _catalogo_md(pasta):
    todos = saves(pasta)
    pns = [(r, f) for r, f in todos if f.get('tipo') == 'painel']
    inds = [(r, f) for r, f in todos if f.get('tipo') == 'indicador']
    linhas = ['# Catálogo do Memory Card', '', 'Gerado pelo Deidara a cada envio. Não edite à mão.', '',
              '## Painéis', '']
    cat_atual = None
    for r, f in sorted(pns, key=lambda x: (x[1]['categoria'], x[1]['secao'], x[1]['titulo'])):
        if f['categoria'] != cat_atual:
            cat_atual = f['categoria']
            linhas += [f'### {cat_atual}', '', '| Seção | Painel | Versão | Status | Aprovado por |', '|---|---|---|---|---|']
        linhas.append(f'| {f["secao"]} | [{f["titulo"]}](saves/{r}/) | v{f["versao"]} | {f["status"]} | '
                      f'{f.get("aprovado_por") or "—"} |')
    linhas += ['', '## Indicadores', '', '| Indicador | Pasta | Versão | Status | Definição |', '|---|---|---|---|---|']
    for r, f in sorted(inds, key=lambda x: (x[1]['status'] != 'oficial', chave(x[1]['titulo']))):
        linhas.append(f'| [{f["titulo"]}](saves/{r}/) | {f["secao"]} | v{f["versao"]} | '
                      f'{"**oficial**" if f["status"] == "oficial" else f["status"]} | '
                      f'{(f.get("descricao") or "—").replace("|", "/")} |')
    gravar_texto(os.path.join(pasta, SECAO, 'CATALOGO.md'), '\n'.join(linhas) + '\n')


def _atualizar(pasta):
    """Traz o que as outras pessoas (e soluções) enviaram, antes de ler ou gravar."""
    if os.path.isdir(os.path.join(pasta, '.git')):
        remoto = _git(pasta, 'remote')
        if remoto and remoto.stdout.strip():
            _git(pasta, 'pull', '--ff-only', '--quiet')


def _privado_ok(repo, publico):
    if not repo or publico:
        return True
    vis = _rodar(['gh', 'repo', 'view', repo, '--json', 'visibility', '--jq', '.visibility'])
    return bool(vis and vis.returncode == 0 and vis.stdout.strip().upper() == 'PRIVATE')


def _commit(pasta, mensagem, extras=(), repo=None, publico=None):
    """Commit SÓ da seção deidara/ (e de arquivos de raiz criados agora) e push, se houver remoto."""
    if not os.path.isdir(os.path.join(pasta, '.git')):
        return 'gravado na pasta (sem git: não versionado)'
    cfg = configuracao() if repo is None else {'repo': repo, 'publico': publico}
    _git(pasta, 'add', '-A', '--', SECAO, *extras)
    r = _git(pasta, 'commit', '-q', '-m', mensagem, '--', SECAO, *extras)
    if r is None:
        return 'gravado na pasta (git não encontrado)'
    if r.returncode != 0 and not any(x in (r.stdout + r.stderr) for x in ('nothing to commit', 'no changes added')):
        return f'gravado, mas o commit falhou: {(r.stderr or r.stdout).strip()[:200]}'
    remoto = _git(pasta, 'remote')
    if not remoto or not remoto.stdout.strip():
        return 'versionado no git local (sem repositório remoto)'
    if not _privado_ok(cfg.get('repo'), cfg.get('publico')):
        return 'versionado no git local, mas NÃO enviado: o cartão não está privado (confira no GitHub)'
    p = _git(pasta, 'push', '-q')
    if p.returncode != 0:
        return f'versionado no git local, mas o envio falhou: {p.stderr.strip()[:200]}'
    return 'versionado e enviado ao cartão'


# ================================================================= conferir
def conferir(pasta, catalogos_por_fonte, resolver, refs=(), registrar=False, por=''):
    """Revalida painéis salvos contra os catálogos atuais de quem roda. {ref: (situação, [detalhes])}."""
    lib = indicadores(pasta)
    out = {}
    for ref, f in saves(pasta):
        if f.get('tipo') != 'painel' or (refs and ref not in refs):
            continue
        argila = ler_json(os.path.join(pasta, SECAO, 'saves', *ref.split('/'), 'argila.json'))
        faltam = [n for n in (argila.get('fontes') or {}) if n not in catalogos_por_fonte]
        if faltam:
            out[ref] = ('sem catálogo', [f'falta o catálogo da fonte {n} (gere com a receita e o catalogar)'
                                         for n in faltam])
            continue
        modelo, prob = resolver(argila, {n: catalogos_por_fonte[n] for n in argila['fontes']})
        detalhes = list(prob.erros)
        for md in _medidas_reais(modelo) if not prob.erros else []:
            ind = lib.get(chave(md['nome']))
            if ind and ind[1].get('status') == 'oficial' and diferencas_indicador(ind[1], _ind_do_modelo(md, {})):
                detalhes.append(f'medida {md["nome"]} difere do indicador OFICIAL {ind[0]}')
        situacao = 'quebrado' if prob.erros else 'divergente' if detalhes else 'ok'
        out[ref] = (situacao, detalhes)
        if registrar:
            f['conferencia'] = {'situacao': situacao, 'em': _agora(), 'por': por, 'detalhes': detalhes[:20]}
            gravar_json(os.path.join(pasta, SECAO, 'saves', *ref.split('/'), 'ficha.json'), f)
            _reescrever_readme(pasta, ref, f)
    if registrar and out:
        _catalogo_md(pasta)
        out['__commit__'] = ('', [_commit(pasta, 'conferência dos painéis')])
    return out
