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

from .especificacao import _grafo_de_filtro, _tabelas_da_medida, chega, medida

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
        self.filtra = _grafo_de_filtro(m)
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
        alvo = _tabelas_da_medida(self.m, md['nome'])
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
        if tipo in ('svg_barra_meta', 'svg_pilula', 'svg_seta', 'svg_posicao', 'svg_radar', 'svg_bolha', 'svg_variacao'):
            return self.valor(md['svg'].get('base') or '', filtros)
        if tipo == 'lista_top':
            return self.lista(md, filtros)
        if tipo == 'escolha':                        # mostra a primeira opção, a que vem selecionada
            return self.valor(md['depende'][0], filtros) if md.get('depende') else 0
        if tipo == 'alternar':
            return self.valor(md['extra']['desligado'], filtros) if md['extra'].get('desligado') else 0
        if tipo in ('cor_destaque', 'svg_iniciais', 'svg_dispersao', 'html_kpis', 'svg_espinha'):
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
