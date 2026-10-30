#!/usr/bin/env python3
"""
Agrupa textos livres (chamados, comentários de pesquisa, motivos digitados)
em temas, e mede o quanto uma resposta conversa com a pergunta. Roda onde
os dados estão, como as receitas: o Deidara nunca lê as linhas, só usa as
colunas novas que este script devolve.

Saída: o mesmo CSV com três colunas a mais, que viram dimensão e medida no
painel ("Tema" e "Palavras do tema" na dimensão, "Similaridade" na fato):

- Tema: número do grupo (1 a K), de textos com palavras parecidas;
- Palavras do tema: as palavras que mais marcam o grupo, para nomear o tema;
- Similaridade (com --resposta): de 0 a 1, quanto a resposta usa as
  palavras da pergunta (cosseno entre os dois textos). Perto de zero pede
  revisão: a resposta pode não ter tratado o que foi pedido.

Sem dependência: TF-IDF e k-médias em Python puro, para alguns milhares de
linhas. Inspirado no Clustering & Similarity Score do dashboard IT Support
do Power BI Design Files (Sajjad Ahmadi, MIT); o código é do Deidara.

Uso:
    python3 ferramentas/agrupar_textos.py chamados.csv --texto Descricao [--resposta Resposta] [-k 8] [-o saida.csv]
"""

import argparse
import csv
import math
import random
import re
import sys
import unicodedata
from collections import Counter

VAZIAS = set('''a ao aos as até com como da das de do dos e é em entre era essa esse esta este eu foi há isso já
lhe mais mas me mesmo meu minha muito na nas não nem no nos o os ou para pela pelo por qual quando que se sem ser
seu sua são também te tem ter um uma umas uns vai você vocês está estão foram favor bom dia boa tarde noite obrigado
obrigada olá oi the and for with this that from your have has are was were please thanks hello'''.split())


def palavras(texto):
    t = unicodedata.normalize('NFKD', (texto or '').lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return [w for w in re.findall(r'[a-z0-9]{3,}', t) if w not in VAZIAS and not w.isdigit()]


def tfidf(documentos):
    """Um vetor esparso {palavra: peso} por documento, já normalizado (norma 1)."""
    n = len(documentos)
    df = Counter(w for d in documentos for w in set(d))
    idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}
    vetores = []
    for d in documentos:
        tf = Counter(d)
        v = {w: c * idf[w] for w, c in tf.items()}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1
        vetores.append({w: x / norma for w, x in v.items()})
    return vetores


def cosseno(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0) for w, x in a.items())


def kmedias(vetores, k, voltas=25, semente=42):
    """k-médias esférico (cosseno): devolve o grupo de cada vetor e os centros."""
    sorteio = random.Random(semente)
    cheios = [i for i, v in enumerate(vetores) if v]
    k = max(1, min(k, len(cheios)))
    centros = [dict(vetores[i]) for i in sorteio.sample(cheios, k)]
    grupos = [0] * len(vetores)
    for _ in range(voltas):
        novos = [max(range(k), key=lambda j: cosseno(v, centros[j])) if v else 0 for v in vetores]
        if novos == grupos and _:
            break
        grupos = novos
        for j in range(k):
            soma = Counter()
            for v, g in zip(vetores, grupos):
                if g == j:
                    soma.update(v)
            norma = math.sqrt(sum(x * x for x in soma.values())) or 1
            centros[j] = {w: x / norma for w, x in soma.items()} if soma else centros[j]
    return grupos, centros


def main(argv=None):
    ap = argparse.ArgumentParser(description='Agrupa textos livres em temas e mede a similaridade da resposta.')
    ap.add_argument('csv')
    ap.add_argument('--texto', required=True, help='coluna com o texto a agrupar (ex.: Descricao)')
    ap.add_argument('--resposta', help='coluna com a resposta, para a similaridade')
    ap.add_argument('-k', type=int, default=8, help='quantos temas (padrão 8)')
    ap.add_argument('--separador', default=None, help='separador do CSV (padrão: descobre sozinho)')
    ap.add_argument('-o', '--saida', help='CSV de saída (padrão: <entrada>_temas.csv)')
    a = ap.parse_args(argv)
    with open(a.csv, encoding='utf-8-sig', newline='') as f:
        amostra = f.read(4096)
        f.seek(0)
        sep = a.separador or csv.Sniffer().sniff(amostra, delimiters=';,\t|').delimiter
        linhas = list(csv.DictReader(f, delimiter=sep))
    if not linhas:
        print('CSV vazio.', file=sys.stderr)
        return 1
    for col in [a.texto] + ([a.resposta] if a.resposta else []):
        if col not in linhas[0]:
            print(f'coluna "{col}" não está no CSV (colunas: {", ".join(linhas[0])})', file=sys.stderr)
            return 1
    docs = [palavras(x[a.texto]) for x in linhas]
    vetores = tfidf(docs)
    grupos, centros = kmedias(vetores, a.k)
    marcas = {j: ', '.join(w for w, _ in sorted(c.items(), key=lambda x: -x[1])[:4]) for j, c in enumerate(centros)}
    if a.resposta:
        pares = tfidf(docs + [palavras(x[a.resposta]) for x in linhas])
        n = len(linhas)
    for i, x in enumerate(linhas):
        x['Tema'] = grupos[i] + 1 if vetores[i] else ''
        x['Palavras do tema'] = marcas[grupos[i]] if vetores[i] else ''
        if a.resposta:
            x['Similaridade'] = f'{cosseno(pares[i], pares[i + n]):.3f}'
    saida = a.saida or re.sub(r'\.csv$', '', a.csv, flags=re.I) + '_temas.csv'
    with open(saida, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=sep)
        w.writeheader()
        w.writerows(linhas)
    contagem = Counter(x['Tema'] for x in linhas)
    print(f'{len(linhas)} linhas em {len(centros)} temas -> {saida}')
    for j in range(len(centros)):
        print(f'  Tema {j + 1} ({contagem.get(j + 1, 0)} linhas): {marcas[j]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
