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
        if tipo == 'divisao':
            num, den = md['depende']
            d = self.valor(den, filtros)
            r = self.valor(num, filtros) / d if d else 0
            if md['formato'] == 'percentual':
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
