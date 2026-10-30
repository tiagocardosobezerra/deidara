"""
Números fictícios COERENTES para o protótipo.

Nenhuma linha do banco é lida. Cada medida ganha um total inventado
(semente = nome da medida) e cada rótulo de cada coluna ganha uma fatia
desse total. A coerência é a do Power BI:

- medida aditiva (soma, contagem): as fatias somam o total do cartão;
- divisão = numerador / denominador no mesmo filtro;
- acumulado no ano soma os meses até o mês do filtro; variação compara com
  o "ano anterior" fictício da mesma medida;
- coluna que NÃO filtra a medida (sem relacionamento até a tabela dela) não
  muda o valor: o protótipo repete o número em toda linha, exatamente como o
  Power BI faria. É o jeito mais rápido de o usuário ver um erro de modelo.
"""

import random

from kibaku_nendo.especificacao import (grafo_de_filtro as grafo_de_filtro,
                                        tabelas_da_medida as tabelas_da_medida, chega, medida)

MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
N_ROTULOS = 8
COLUNAS_DE_MES = ('Mês/Ano', 'Ano-Mês', 'Nome do Mês', 'Mês', 'Data')


def _rng(*partes):
    return random.Random('|'.join(str(p) for p in partes))


def _ano(m):
    if not m.get('calendario'):
        return 2025
    cal = next(t for t in m['tabelas'] if t['nome'] == m['calendario']['tabela'])
    return min(cal['fim'], 2025)


def categorias(m, campo):
    """Rótulos fictícios de uma coluna (o calendário ganha rótulos de data de verdade)."""
    for md in m['medidas']:                          # tabela auxiliar: as opções de verdade, ou a coluna copiada
        cfg = md.get('extra') or {}
        if cfg.get('tabela') == campo['tabela'] and cfg.get('coluna') == campo['nome']:
            if md['tipo'] == 'escolha':
                return list(cfg['rotulos'])
            if md['tipo'] == 'alternar':
                return [cfg['rotulo']]
            if md['tipo'] == 'cor_destaque':
                return categorias(m, {'tabela': cfg['origem'][0], 'nome': cfg['origem'][1], 'tipo': 'coluna'})
    for t in m['tabelas']:                           # grupo de cálculo: os itens, na ordem
        if t['nome'] == campo['tabela'] and t.get('grupo_calculo') and campo['nome'] == t['colunas'][0]['nome']:
            return [it['rotulo'] for it in t['grupo_calculo']['itens']]
    nome, ano = campo['nome'], _ano(m)
    if m.get('calendario') and campo['tabela'] == m['calendario']['tabela']:
        return {
            'Mês/Ano': [f'{MESES[i]}/{ano}' for i in range(12)],
            'Ano-Mês': [f'{ano}-{i + 1:02d}' for i in range(12)],
            'Data': [f'01/{i + 1:02d}/{ano}' for i in range(12)],
            'Ano': [str(ano - k) for k in range(4, -1, -1)],
            'Nome do Mês': MESES[:],
            'Trimestre': ['T1', 'T2', 'T3', 'T4'],
            'Mês': [str(i) for i in range(1, 13)],
            'Ano-Mês Num': [str(ano * 100 + i) for i in range(1, 13)],
            'Ano-Trimestre': [f'{a}-T{q}' for a in (ano - 1, ano) for q in range(1, 5)],
            'Ano-Trimestre Num': [str(a * 10 + q) for a in (ano - 1, ano) for q in range(1, 5)],
        }.get(nome, [str(ano)])
    if campo.get('familia') in ('data', 'datahora'):
        return [f'{(k * 5) % 28 + 1:02d}/{k % 12 + 1:02d}/{ano}' for k in range(N_ROTULOS)]
    if campo.get('familia') in ('inteiro', 'decimal', 'real'):
        return [str(1000 + 7 * k) for k in range(N_ROTULOS)]
    return [f'{nome} {chr(65 + k)}' for k in range(N_ROTULOS)]


class Simulador:
    def __init__(self, m):
        self.m = m
        self.filtra = grafo_de_filtro(m)
        self._fatias = {}

    # ------------------------------------------------------------- básicos
    def total(self, md):
        r = _rng('total', md['nome'])
        if isinstance(md.get('meta'), (int, float)) and md['meta'] > 0 and not self.aditiva(md):
            return md['meta'] * r.uniform(0.85, 1.12)     # média ou taxa com meta fixa: fica perto dela, como na vida real
        return {'percentual': r.uniform(0.04, 0.30), 'moeda': r.uniform(2e5, 6e6), 'inteiro': r.uniform(300, 6000),
                'decimal': r.uniform(50, 900)}.get(md['formato'], r.uniform(50, 900))

    def fatia(self, campo, rotulo):
        """Participação do rótulo no total (as fatias de uma coluna somam 1)."""
        k = (campo['tabela'], campo['nome'])
        if k not in self._fatias:
            rot = categorias(self.m, campo)
            pesos = [_rng('peso', *k, x).uniform(0.4, 1.6) for x in rot]
            s = sum(pesos)
            self._fatias[k] = {x: p / s for x, p in zip(rot, pesos)}
        return self._fatias[k].get(rotulo, 1 / max(1, len(self._fatias[k])))

    def _filtros_validos(self, md, filtros):
        alvo = tabelas_da_medida(self.m, md['nome'])
        return [(c, r) for c, r in filtros if any(chega(self.m, self.filtra, c['tabela'], a, md['nome']) for a in alvo)]

    # --------------------------------------------------------------- valor
    def valor(self, nome, filtros=()):
        """Valor da medida sob filtros [(campo, rótulo)]."""
        md = medida(self.m, nome)
        if not md:
            return 0
        filtros = self._filtros_validos(md, list(filtros))
        tipo = md['tipo']
        if tipo == 'meta':
            return float(md['dax'])
        if tipo == 'cor':
            return 0
        if tipo in ('svg_barra_meta', 'svg_pilula', 'svg_seta', 'svg_posicao', 'svg_radar', 'svg_bolha', 'svg_variacao',
                    'svg_estrelas', 'svg_progresso'):
            return self.valor(md['svg'].get('base') or '', filtros)
        if tipo == 'lista_top':
            return self.lista(md, filtros)
        if tipo == 'leitura':
            return self.leitura(md, filtros)
        if tipo in ('controle', 'c4'):
            return self.controle(md, filtros)
        if tipo == 'fora_da_curva':
            return self.fora_da_curva(md, filtros)
        if tipo == 'escolha':                        # mostra a primeira opção, a que vem selecionada
            return self.valor(md['depende'][0], filtros) if md.get('depende') else 0
        if tipo == 'alternar':
            return self.valor(md['extra']['desligado'], filtros) if md['extra'].get('desligado') else 0
        if tipo in ('cor_destaque', 'svg_iniciais', 'svg_dispersao', 'html_kpis', 'svg_espinha', 'html_tour'):
            return 0
        if tipo == 'impacto':
            if not self.classificacao(md['ranking'], filtros)[0]:
                return None
            return self.valor(md['ranking']['base'], filtros) - self.valor(md['ranking']['comparar'], filtros)
        if tipo == 'aviso':
            return self.aviso(md, filtros)
        if tipo in ('posicao', 'pareto', 'melhores_piores', 'jitter'):
            return self._ranking(md, filtros)
        if tipo == 'divisao':
            num, den = md['depende']
            d = self.valor(den, filtros)
            r = self.valor(num, filtros) / d if d else 0
            if md['formato'] == 'percentual' or isinstance(md.get('meta'), (int, float)):
                # numerador e denominador fictícios vivem em escalas independentes: mantém a
                # variação entre as linhas, mas traz o nível para uma taxa plausível
                d0 = self.valor(den)
                r0 = self.valor(num) / d0 if d0 else 0
                r = r * self.total(md) / r0 if r0 else r
            return r
        if tipo in ('acumulado_ano', 'ano_anterior', 'variacao_ano_anterior', 'variacao_mes_anterior',
                    'media_mensal', 'movel_12m'):
            return self._tempo(md, filtros)
        aditiva = tipo == 'estoque_na_data' or tipo == 'agregacao' and md['dax'].split('(')[0] in ('SUM', 'COUNT', 'COUNTROWS', 'DISTINCTCOUNTNOBLANK') \
            and md['formato'] != 'percentual'
        v = self.total(md)
        for campo, rotulo in filtros:
            if aditiva:
                v *= self.fatia(campo, rotulo)
            else:
                v *= _rng('var', md['nome'], campo['nome'], rotulo).uniform(0.75, 1.25)
        return round(v) if md['formato'] == 'inteiro' and aditiva else v

    def classificacao(self, cfg, filtros):
        """(rótulo da linha, [(rótulo, valor)] na ordem do ranking) ou (None, []) fora de uma linha."""
        linha = next(((c, r) for c, r in filtros if (c['tabela'], c['nome']) == (cfg.get('tabela'), cfg.get('coluna'))), None)
        if not linha:
            return None, []
        outros = [(c, r) for c, r in filtros if (c, r) != linha]
        vals = [(r, self.valor(cfg['base'], outros + [(linha[0], r)])) for r in categorias(self.m, linha[0])]
        vals.sort(key=lambda x: -x[1] if cfg.get('ordem', 'maior_primeiro') == 'maior_primeiro' else x[1])
        return linha[1], vals

    def aviso(self, md, filtros=()):
        """O texto do aviso: quantos e quais estão fora da meta (vazio quando ninguém está)."""
        cfg = md['extra']
        if not cfg.get('base'):
            return ''
        col = {'tabela': cfg['tabela'], 'nome': cfg['coluna'], 'tipo': 'coluna'}
        rot = categorias(self.m, col)
        fora = [r for r in rot if self.status(cfg['base'], list(filtros) + [(col, r)]) is False]
        if not fora:
            return ''
        return (f'⚠ {len(fora)} de {len(rot)} fora da meta de {cfg["base"]}: ' + ', '.join(fora[:3])
                + ('…' if len(fora) > 3 else ''))

    def lista(self, md, filtros=()):
        """Os N primeiros da coluna, em texto: [(rótulo, valor)]."""
        cfg = md['ranking']
        col = {'tabela': cfg['tabela'], 'nome': cfg['coluna'], 'tipo': 'coluna'}
        outros = [(c, r) for c, r in filtros if (c['tabela'], c['nome']) != (cfg['tabela'], cfg['coluna'])]
        vals = [(r, self.valor(cfg['base'], outros + [(col, r)])) for r in categorias(self.m, col)]
        vals.sort(key=lambda x: -x[1] if cfg.get('ordem', 'maior_primeiro') == 'maior_primeiro' else x[1])
        return vals[:cfg.get('n') or 5]

    def leitura(self, md, filtros=()):
        """A frase do Tobi com os números fictícios (a mesma conta da medida DAX)."""
        from tecnicas import tobi
        cfg = md['ranking']
        base = medida(self.m, cfg['base'])
        col = {'tabela': cfg['tabela'], 'nome': cfg['coluna'], 'tipo': 'coluna'}
        outros = [(c, r) for c, r in filtros if (c['tabela'], c['nome']) != (cfg['tabela'], cfg['coluna'])]
        itens = [(r, self.valor(cfg['base'], outros + [(col, r)]), self.valor(cfg['comparar'], outros + [(col, r)]))
                 for r in categorias(self.m, col)]
        from tecnicas.c1.prototipo import formatar
        serie = None
        if self.m.get('calendario'):                 # a tendência dos últimos 12 meses (C4 Karura)
            mes = self._mes()
            serie = [self.valor(cfg['base'], outros + [(mes, r)]) for r in categorias(self.m, mes)]
        return tobi.frase(base['nome'], self.valor(cfg['base'], outros), self.valor(cfg['comparar'], outros), itens,
                          base['formato'], base['polaridade'] != 'menor_melhor', cfg.get('aditiva'),
                          lambda v, f: formatar(v, f, True), serie)

    def _mes(self):
        return {'tabela': self.m['calendario']['tabela'], 'nome': 'Mês/Ano', 'tipo': 'coluna'}

    def grafico_de_controle(self, nome_controle, filtros=()):
        """A série do gráfico de controle com os números fictícios: rótulos, valores, centro, limites e sinais."""
        from tecnicas import c4
        cfg = medida(self.m, nome_controle)['extra']
        mes = self._mes()
        outros = [(c, r) for c, r in filtros if (c['tabela'], c['nome']) != (mes['tabela'], mes['nome'])]
        rot = categorias(self.m, mes)
        valores = [self.valor(cfg['base'], outros + [(mes, r)]) for r in rot]
        if cfg['grafico'] == 'xmr':
            g = c4.xmr(valores)
            sup, inf = [g['superior']] * len(rot), [g['inferior']] * len(rot)
        else:
            # numerador e denominador fictícios vivem em escalas próprias: o numerador sai da taxa que o protótipo
            # mostra, para a conta do gráfico p (ou u) bater com a linha desenhada
            dens = [self.valor(cfg['denominador'], outros + [(mes, r)]) for r in rot]
            if cfg['grafico'] == 'p' and sum(dens):     # o grupo de cada mês (headcount) é do tamanho do todo, não uma fatia
                escala = self.valor(cfg['denominador'], outros) / (sum(dens) / len(dens))
                dens = [d * escala for d in dens]
            nums = [v * d for v, d in zip(valores, dens)]
            g = (c4.grafico_p if cfg['grafico'] == 'p' else c4.grafico_u)(nums, dens)
            sup, inf = g['superior'], g['inferior']
        return {'rotulos': rot, 'valores': valores, 'centro': g['centro'], 'superior': sup, 'inferior': inf,
                'sinais': c4.sinais(valores, g['centro'], sup, inf), 'mes': mes}

    def controle(self, md, filtros=()):
        """Centro, limites, sinal e a frase da meta x faixa (as medidas do C4 Karura)."""
        from tecnicas import c4
        from tecnicas.c1.prototipo import formatar
        dono = md['nome'] if md['tipo'] == 'controle' else md['extra']['de']
        cfg = medida(self.m, dono)['extra']
        g = self.grafico_de_controle(dono, filtros)
        k = next((g['rotulos'].index(r) for c, r in filtros
                  if (c['tabela'], c['nome']) == (g['mes']['tabela'], 'Mês/Ano') and r in g['rotulos']), None)
        parte = next((p for p, n in cfg['partes'].items() if n == md['nome']), 'centro')
        if parte == 'centro':
            return g['centro']
        if parte in ('superior', 'inferior'):
            lista = g[parte]
            return lista[k] if k is not None else sum(lista) / len(lista)
        if parte == 'sinal':
            return g['sinais'][k] if k is not None else None
        base = medida(self.m, cfg['base'])
        meta = self.valor(base['meta_medida'], filtros)
        sup, inf = sum(g['superior']) / len(g['superior']), sum(g['inferior']) / len(g['inferior'])
        fmt = lambda v: formatar(v, base['formato'], True)
        faixa = f'{fmt(inf)} a {fmt(sup)}'
        caso = c4.meta_x_faixa(meta, sup, inf, base['polaridade'] == 'maior_melhor')
        return {'dentro': f'A meta ({fmt(meta)}) está dentro da faixa normal ({faixa}): alguns meses vão bater e '
                          'outros não, por acaso.',
                'inalcancavel': f'A meta ({fmt(meta)}) está fora da faixa normal ({faixa}): sem mudar o processo, '
                                'ela não será atingida de forma estável.',
                'folgada': f'A meta ({fmt(meta)}) é folgada: a faixa normal ({faixa}) já fica toda do lado bom.'}[caso]

    def fora_da_curva(self, md, filtros=()):
        """O z (modificado ou do funil) do item da linha, com os números fictícios."""
        from tecnicas import c4
        cfg = md['extra']
        col = {'tabela': cfg['tabela'], 'nome': cfg['coluna'], 'tipo': 'coluna'}
        linha = next((r for c, r in filtros if (c['tabela'], c['nome']) == (cfg['tabela'], cfg['coluna'])), None)
        if linha is None:
            return None
        outros = [(c, r) for c, r in filtros if (c['tabela'], c['nome']) != (cfg['tabela'], cfg['coluna'])]
        rot = categorias(self.m, col)
        if cfg['funil']:
            dens = [self.valor(cfg['denominador'], outros + [(col, r)]) for r in rot]
            taxas = [self.valor(cfg['base'], outros + [(col, r)]) for r in rot]
            zs = c4.z_funil([t * d for t, d in zip(taxas, dens)], dens)   # o numerador sai da taxa mostrada
        else:
            zs = c4.z_modificado([self.valor(cfg['base'], outros + [(col, r)]) for r in rot])
        return dict(zip(rot, zs)).get(linha)

    def _ranking(self, md, filtros):
        cfg = md['ranking']
        rotulo, vals = self.classificacao(cfg, filtros)
        if rotulo is None:
            return None
        nomes = [r for r, _ in vals]
        pos = nomes.index(rotulo) + 1 if rotulo in nomes else None
        if md['tipo'] == 'posicao':
            return pos
        if md['tipo'] == 'jitter':                   # o mesmo espalhamento da medida DAX
            return (pos * 37 % 101) / 100 if pos else None
        if md['tipo'] == 'melhores_piores':
            n = cfg.get('n') or 5
            return dict(vals)[rotulo] if pos and (pos <= n or pos > len(nomes) - n) else None
        desc = sorted(vals, key=lambda x: -x[1])
        total = sum(v for _, v in desc) or 1
        acum = 0
        for r, v in desc:
            acum += v
            if r == rotulo:
                return acum / total
        return None

    def _tempo(self, md, filtros):
        base = md['depende'][0]
        if md['tipo'] in ('media_mensal', 'movel_12m'):
            return self.valor(base, filtros) * _rng('suave', md['nome'], *[r for _, r in filtros]).uniform(0.97, 1.03)
        mes = next(((c, r) for c, r in filtros if c['nome'] in COLUNAS_DE_MES), None)
        outros = [(c, r) for c, r in filtros if (c, r) != mes]
        if md['tipo'] == 'acumulado_ano':
            if not mes:
                return self.valor(base, filtros)
            rot = categorias(self.m, mes[0])
            ate = rot.index(mes[1]) + 1 if mes[1] in rot else len(rot)
            return sum(self.valor(base, outros + [(mes[0], x)]) for x in rot[:ate])
        atual = self.valor(base, filtros)
        fator = _rng('anterior', md['nome'], *[r for _, r in filtros]).uniform(0.8, 1.2)
        anterior = atual * fator
        if md['tipo'] == 'ano_anterior':
            return anterior
        return (atual - anterior) / anterior if anterior else 0

    def aditiva(self, md):
        """A medida soma por linha (o total é a soma das linhas)?"""
        if not md:
            return False
        if md['tipo'] == 'estoque_na_data':
            return True
        return md['tipo'] == 'agregacao' and md['dax'].split('(')[0] in ('SUM', 'COUNT', 'COUNTROWS') \
            and md['formato'] != 'percentual'

    def status(self, nome, filtros=()):
        """True = bateu a meta, False = não bateu, None = sem meta."""
        md = medida(self.m, nome)
        if not md or not md.get('meta_medida'):
            return None
        v, meta = self.valor(nome, filtros), self.valor(md['meta_medida'], filtros)
        return v >= meta if md['polaridade'] == 'maior_melhor' else v <= meta

    def serie(self, nome, campo, rotulos, extra=()):
        return [self.valor(nome, list(extra) + [(campo, r)]) for r in rotulos]
