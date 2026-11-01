"""
Esculpir: o protótipo navegável do painel, num único .html sem dependência
externa (abre offline, em qualquer navegador, e pode ser enviado por e-mail
para validação).

Os números são FICTÍCIOS, determinísticos e coerentes entre si (ver
simulacao.py): o protótipo valida layout, indicadores e navegação, nunca
valor. Nenhuma linha do banco é lida — regra "só estrutura, nunca dados" do
Deidara.
"""

import json

from kibaku_nendo.especificacao import medida
from tecnicas.arte.modelos import montar, paginas_do_relatorio
from tecnicas.bunshin.simulacao import Simulador
# o desenho de cada visual (e os nomes que outros módulos importam daqui)
from tecnicas.c1.visuais import (_corta, _e, _mapa, formatar, svg_visual, titulo_do_cartao)  # noqa: F401
from tecnicas.katsu import retrato
from kibaku_nendo.especificacao import grafo_de_filtro as grafo_de_filtro, tabelas_da_medida as tabelas_da_medida, chega
from kibaku_nendo.relato import para_gestor
from kibaku_nendo.relato import nota_de_ajuda


def _niveis(m):
    """Fato no nível 0; cada dimensão no menor número de saltos até um fato."""
    viz = {}
    for r in m['relacionamentos']:
        viz.setdefault(r['de'], set()).add(r['para'])
        viz.setdefault(r['para'], set()).add(r['de'])
    nivel = {t['nome']: 0 for t in m['tabelas'] if t['tipo'] == 'fato'}
    if not nivel and m['tabelas']:
        nivel[m['tabelas'][0]['nome']] = 0
    fila = list(nivel)
    while fila:
        x = fila.pop(0)
        for y in sorted(viz.get(x, ())):
            if y not in nivel:
                nivel[y] = nivel[x] + 1
                fila.append(y)
    fim = max(nivel.values(), default=0)
    for t in m['tabelas']:
        nivel.setdefault(t['nome'], fim + 1)     # sem relacionamento: coluna à parte
    return nivel


def svg_modelo(m):
    nivel = _niveis(m)
    colunas = {}
    for t in m['tabelas']:
        colunas.setdefault(nivel[t['nome']], []).append(t)
    bw, W = 220, 1180
    ncol = max(colunas) + 1 if colunas else 1
    gap = (W - ncol * bw) / (ncol + 1)

    def caixa_h(t):
        return 52 + 18 * min(10, len([c for c in t['colunas'] if not c['oculta']]))

    pos, H = {}, 0
    for k in range(ncol):
        y = 30
        for t in colunas.get(k, []):
            pos[t['nome']] = (gap + k * (bw + gap), y, caixa_h(t))
            y += caixa_h(t) + 28
        H = max(H, y)
    out = [f'<svg viewBox="0 0 {W} {H}" class="modelo" role="img" aria-label="Diagrama do modelo de dados">']
    for r in m['relacionamentos']:
        if r['de'] not in pos or r['para'] not in pos:
            continue
        (x1, y1, h1), (x2, y2, h2) = pos[r['de']], pos[r['para']]
        if x1 == x2:
            a, b = (x1 + bw, y1 + 30), (x2 + bw, y2 + 30)
            meio = x1 + bw + 40
        else:
            a = (x1 + bw if x2 > x1 else x1, y1 + min(h1 / 2, 40))
            b = (x2 if x2 > x1 else x2 + bw, y2 + min(h2 / 2, 40))
            meio = (a[0] + b[0]) / 2
        d = f'M{a[0]},{a[1]} C{meio},{a[1]} {meio},{b[1]} {b[0]},{b[1]}'
        para_dir = b[0] > a[0] or x1 == x2
        decl = ' declarada' if str(r['prova']).startswith('declarada') else ''
        out.append(f'<path d="{d}" class="rel{"" if r["ativo"] else " inativa"}{decl}">'
                   f'<title>{_e(r["de"])}[{_e(r["de_coluna"])}] muitos → um {_e(r["para"])}[{_e(r["para_coluna"])}] · prova: {_e(r["prova"])}</title></path>'
                   f'<text x="{a[0] + (6 if para_dir else -6)}" y="{a[1] - 5}" class="card" text-anchor="{"start" if para_dir else "end"}">*</text>'
                   f'<text x="{b[0] + (6 if x1 == x2 else (-6 if para_dir else 6))}" y="{b[1] - 5}" class="card" '
                   f'text-anchor="{"start" if x1 == x2 else ("end" if para_dir else "start")}">1</text>')
    for t in m['tabelas']:
        x, y, h = pos[t['nome']]
        cls = 'fato' if t['tipo'] == 'fato' else 'dim'
        out.append(f'<g><rect x="{x}" y="{y}" width="{bw}" height="{h}" rx="6" class="cx {cls}"/>'
                   f'<text x="{x + 10}" y="{y + 20}" class="t">{_e(_corta(t["nome"], 26))}</text>'
                   f'<text x="{x + 10}" y="{y + 36}" class="sub">{_e(_corta((t.get("fonte") + " · " + t["origem"]) if t["origem"] else "gerada no Power Query", 32))}</text>'
                   f'<line x1="{x}" x2="{x + bw}" y1="{y + 44}" y2="{y + 44}" class="grade"/>')
        visiveis = [c for c in t['colunas'] if not c['oculta']]
        for k, c in enumerate(visiveis[:10]):
            out.append(f'<text x="{x + 12}" y="{y + 62 + k * 18}" class="cel">{_e(_corta(c["nome"], 30))}</text>')
        if len(visiveis) > 10:
            out.append(f'<text x="{x + bw - 10}" y="{y + h - 6}" class="sub" text-anchor="end">+{len(visiveis) - 10}</text>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)


# --------------------------------------------------------------------- HTML
CSS = """
:root{--fundo:#F3F2F1;--pagina:#FFFFFF;--texto:#252423;--suave:#605E5C;--borda:#E1DFDD;--destaque:#118DFF;
--aviso:#8A6100;--avisofundo:#FFF4CE;--erro:#A4262C}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--fundo:#1B1A19;--texto:#F3F2F1;--suave:#C8C6C4;--borda:#3B3A39}}
*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",system-ui,sans-serif;background:var(--fundo);color:var(--texto)}
header{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;padding:16px 20px 8px}
header h1{font-size:20px;margin:0}header .meta{color:var(--suave);font-size:13px}
.faixa{margin:0 20px 10px;padding:8px 12px;border-radius:6px;background:var(--avisofundo);color:var(--aviso);font-size:13px}
nav{display:flex;gap:4px;padding:0 20px;flex-wrap:wrap;border-bottom:1px solid var(--borda)}
nav button{font:inherit;font-size:14px;border:0;background:none;color:var(--suave);padding:10px 14px;cursor:pointer;border-bottom:3px solid transparent}
nav button[aria-selected=true]{color:var(--texto);border-bottom-color:var(--destaque);font-weight:600}
main{padding:16px 20px 40px}section{display:none}section.ativa{display:block}
.palco{width:100%;overflow:hidden}.pagina{position:relative;transform-origin:0 0;background:var(--pagina);box-shadow:0 1px 4px rgba(0,0,0,.15)}
.pagina h2{position:absolute;left:16px;top:8px;margin:0;font-size:20px;color:#252423}
.vis{position:absolute;background:#fff;border:1px solid #EDEBE9;border-radius:4px}
.vis.segmentador,.vis.botoes{border-color:transparent;background:transparent}
.fundo{position:absolute;left:0;top:0;line-height:0}.fundo svg{display:block}
.desenhada .vis{background:transparent;border:0}
.desenhada .t{font-size:19px}.desenhada .sub{font-size:14px}.desenhada .kpi{font-size:54px}.desenhada .kpi2{font-size:30px}
.desenhada .eixo{font-size:13px}.desenhada .cab,.desenhada .cel{font-size:15px}.desenhada .info{width:26px;height:26px;font-size:14px;line-height:24px}.desenhada .vis.segmentador .caixa{fill:#fff}
.ir{position:absolute;background:transparent;border:0;padding:0;cursor:pointer;border-radius:12px;z-index:3}
.ir:hover{background:rgba(127,127,127,.12)}.ir:focus-visible{outline:3px solid var(--destaque)}
.ajuda{position:absolute;width:44px;height:44px;border-radius:50%;border:2px solid var(--destaque);background:#fff;
color:var(--destaque);font:700 20px Segoe UI,sans-serif;cursor:pointer;z-index:6}
.notas{position:absolute;inset:0;z-index:5;background:rgba(255,255,255,.35)}
.abre-tour,.fecha-tour{position:absolute;width:164px;height:44px;border-radius:22px;border:2px solid var(--destaque);
background:#fff;color:var(--destaque);font:700 14px Segoe UI,sans-serif;cursor:pointer;z-index:6}
.tour-proto{position:absolute;left:0;top:0;z-index:7}.fecha-tour{top:16px;z-index:1000}
.nota-ajuda{position:absolute;box-sizing:border-box;padding:10px 12px;background:rgba(255,255,255,.96);
border:2px solid var(--destaque);border-radius:8px;font:13px Segoe UI,sans-serif;color:#252423;overflow:auto}
.nota-ajuda b{display:block;margin-bottom:4px}.nota-ajuda p{margin:0 0 4px}
.escura .vis text{fill:#E6EAF2}.escura .vis .sub,.escura .vis .eixo{fill:#9AA4B8}.escura .grade,.escura .trilho{stroke:#2A3346}
.escura .zebra{fill:#1F2738}.escura .vis .caixa,.escura.desenhada .vis.segmentador .caixa{fill:#1A2130;stroke:#3A4560}
.escura .info{background:#1A2130;color:#C8D0E0;border-color:#3A4560}
.vis svg{display:block;font-family:"Segoe UI",system-ui,sans-serif}
.t{font-size:14px;font-weight:600;fill:#252423}.sub{font-size:12px;fill:#605E5C}.kpi{font-size:34px;font-weight:600;fill:#252423}
.kpi2{font-size:22px;font-weight:600;fill:#252423}.eixo{font-size:11px;fill:#605E5C}.cab{font-size:12px;font-weight:600;fill:#252423}
.cel{font-size:12px;fill:#252423}.grade{stroke:#E1DFDD}.zebra{fill:#F8F8F8}.trilho{fill:none;stroke:#E1DFDD}
.caixa{fill:#fff;stroke:#8A8886}.nota{color:var(--suave);font-size:13px;margin:8px 0 0}
.modelo{width:100%;height:auto;background:var(--pagina);border-radius:6px}.cx{stroke-width:1.5}
.cx.fato{fill:#EAF3FF;stroke:#118DFF}.cx.dim{fill:#fff;stroke:#8A8886}.rel{stroke:#605E5C;stroke-width:1.5}
.rel{fill:none}.rel.inativa{stroke-dasharray:6 4}.rel.declarada{stroke:#C55A11;stroke-dasharray:3 3;stroke-width:2}.card{font-size:13px;font-weight:600;fill:#605E5C}
table .sub{color:#605E5C}
table{border-collapse:collapse;width:100%;font-size:13px;background:var(--pagina);color:#252423}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--borda);vertical-align:top}
th{position:sticky;top:0;background:#F3F2F1}code,pre{font-family:Consolas,monospace;font-size:12px}pre{margin:0;white-space:pre-wrap}
.tabela-rolagem{overflow-x:auto}ul.lista{padding-left:20px;line-height:1.6}.ok{color:#107C10}.erro{color:var(--erro)}
@media (max-width:700px){header,main{padding-left:16px;padding-right:16px}nav{padding:0 8px}
.palco{height:auto!important;overflow:visible}.pagina{transform:none!important;width:auto!important;height:auto!important;
background:transparent;box-shadow:none}.pagina h2{position:static;margin:0 0 10px;color:var(--texto)}
.vis{position:relative!important;left:auto!important;top:auto!important;width:auto!important;height:auto!important;margin:0 0 10px}
.vis svg{width:100%;height:auto}.fundo,.ir{display:none}
.desenhada .vis:not(.segmentador):not(.botoes){background:#fff;border:1px solid #EDEBE9;border-radius:6px}
.escura.desenhada .vis:not(.segmentador):not(.botoes){background:#141A26;border-color:#2A3346}}
.decisao{display:flex;flex-direction:column;gap:6px;margin:6px 0 12px}.decisao label{display:flex;gap:8px;align-items:center}
#aprovador{font:inherit;padding:6px 8px;border:1px solid var(--borda);border-radius:6px;margin-left:6px}
.info{position:absolute;top:4px;right:4px;width:22px;height:22px;border-radius:50%;border:1px solid #C8C6C4;background:#fff;
color:#605E5C;font:600 12px/20px "Segoe UI",sans-serif;cursor:pointer;padding:0;z-index:2}
.info:hover,.info:focus{border-color:var(--destaque);color:var(--destaque);outline:none}
#painel{position:fixed;right:16px;bottom:16px;max-width:420px;width:calc(100% - 32px);max-height:60vh;overflow:auto;background:var(--pagina);
color:#252423;border:1px solid var(--borda);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:14px 16px;display:none;z-index:10}
#painel.aberto{display:block}#painel h3{margin:0 24px 8px 0;font-size:15px}#painel dl{margin:0}#painel dt{font-weight:600;margin-top:10px}
#painel dd{margin:2px 0 0}#painel .fechar{position:absolute;top:8px;right:10px;border:0;background:none;font-size:18px;cursor:pointer;color:#605E5C}
.aprovar{max-width:980px}.aprovar .ind{background:var(--pagina);color:#252423;border:1px solid var(--borda);border-radius:8px;padding:12px 14px;margin:10px 0}
.aprovar label{display:flex;gap:10px;align-items:flex-start;cursor:pointer}.aprovar input[type=checkbox]{width:18px;height:18px;margin-top:2px}
.aprovar .det{color:#605E5C;font-size:13px;margin:4px 0 0 28px}.aprovar textarea{width:100%;min-height:64px;font:inherit;padding:8px;
border:1px solid var(--borda);border-radius:6px}.aprovar h3{margin:22px 0 6px}.botao{font:inherit;font-weight:600;border:0;border-radius:6px;
background:var(--destaque);color:#fff;padding:10px 16px;cursor:pointer}.botao:focus{outline:2px solid #252423}
.progresso{font-size:14px;margin:6px 0 12px}.copiado{color:#107C10;margin-left:10px}
@media print{nav,.faixa .so-tela,.info,#painel,.botao{display:none!important}section{display:block!important;break-after:page}
.palco{height:auto!important;overflow:visible}.pagina{transform:none!important;box-shadow:none;zoom:.62}body{background:#fff}}
"""

JS = """
const botoes=[...document.querySelectorAll('nav button')];
function abrir(id){const sec=document.getElementById(id);const aba=(sec&&sec.dataset.aba)||id;
botoes.forEach(b=>b.setAttribute('aria-selected',b.dataset.alvo===aba));
document.querySelectorAll('section').forEach(s=>s.classList.toggle('ativa',s.id===id));escalar();
try{history.replaceState(null,'','#'+id)}catch(e){}}
botoes.forEach(b=>b.addEventListener('click',()=>abrir(b.dataset.alvo)));
document.querySelectorAll('.ir').forEach(b=>b.addEventListener('click',()=>{abrir(b.dataset.ir);scrollTo(0,0);}));
document.querySelectorAll('.ajuda').forEach(b=>b.addEventListener('click',()=>{const n=b.nextElementSibling;n.hidden=!n.hidden;}));
document.querySelectorAll('.abre-tour').forEach(b=>b.addEventListener('click',()=>{const t=b.nextElementSibling;t.hidden=false;
t.querySelectorAll('details').forEach(d=>d.open=d.classList.contains('tg-raiz'));}));
document.querySelectorAll('.fecha-tour').forEach(b=>b.addEventListener('click',()=>{b.parentElement.hidden=true;}));
function escalar(){if(innerWidth<=700){document.querySelectorAll('.pagina').forEach(pg=>pg.style.transform='');return;}
document.querySelectorAll('section.ativa .palco').forEach(p=>{const pg=p.firstElementChild;
const k=Math.min(1,p.clientWidth/pg.offsetWidth);pg.style.transform='scale('+k+')';p.style.height=(pg.offsetHeight*k)+'px';});}
addEventListener('resize',escalar);
const h=location.hash.slice(1);abrir(h&&document.getElementById(h)&&document.getElementById(h).dataset.aba?h:botoes[0].dataset.alvo);
const painel=document.getElementById('painel');
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
document.querySelectorAll('.info').forEach(b=>b.addEventListener('click',ev=>{ev.stopPropagation();
const d=JSON.parse(b.dataset.info);let x='<button class="fechar" aria-label="Fechar">×</button><h3>'+esc(d.titulo)+'</h3><dl>';
d.itens.forEach(i=>{x+='<dt>'+esc(i.nome)+'</dt><dd>'+esc(i.definicao||'Sem definição ainda.')+(i.meta?'<br><small>'+esc(i.meta)+'</small>':'')+'</dd>';});
if(!d.itens.length)x+='<dd>Filtro da página (ilustrativo no protótipo): escolha um valor e os números da página respondem a ele.'+(d.excecoes&&d.excecoes.length?' <b>Não mudam com este filtro:</b> '+esc(d.excecoes.join(', '))+'.':'')+'</dd>';
painel.innerHTML=x+'</dl>';painel.classList.add('aberto');painel.querySelector('.fechar').focus();
painel.querySelector('.fechar').addEventListener('click',()=>{painel.classList.remove('aberto');b.focus();});}));
document.addEventListener('keydown',e=>{if(e.key==='Escape')painel.classList.remove('aberto');});
const CHAVE='deidara:'+document.body.dataset.chave;
function ler(){try{return JSON.parse(localStorage.getItem(CHAVE)||'{}')}catch(e){return {}}}
function gravar(v){try{localStorage.setItem(CHAVE,JSON.stringify(v))}catch(e){}}
const estado=ler();
document.querySelectorAll('[data-guardar]').forEach(el=>{const k=el.dataset.guardar;
if(k in estado){if(el.type==='checkbox')el.checked=estado[k];else el.value=estado[k];}
el.addEventListener('input',()=>{estado[k]=el.type==='checkbox'?el.checked:el.value;gravar(estado);progresso();});});
function progresso(){const cs=[...document.querySelectorAll('.aprovar input[type=checkbox]')];const ok=cs.filter(c=>c.checked).length;
const p=document.getElementById('progresso');if(p)p.textContent=ok+' de '+cs.length+' indicador(es) confirmado(s)';}
progresso();
const copiar=document.getElementById('copiar');
if(copiar)copiar.addEventListener('click',()=>{const NL=String.fromCharCode(10);const b=document.body.dataset;
const dec=document.querySelector('input[name=decisao]:checked');const nome=(document.getElementById('aprovador').value||'').trim();
let t='Aceite do protótipo: '+b.projeto+' (versão '+b.versao+')'+NL+'Código: '+b.codigo+NL;
t+='Decisão: '+(dec?dec.value:'(não marcada)')+NL+'Aprovador: '+(nome||'(não informado)')+NL;
t+='Data: '+new Date().toLocaleDateString('pt-BR')+NL+NL+'Indicadores:'+NL;
document.querySelectorAll('.aprovar .ind').forEach(d=>{const c=d.querySelector('input');t+=(c.checked?'  [x] ':'  [ ] ')+d.dataset.nome+NL;});
document.querySelectorAll('.aprovar textarea').forEach(a=>{if(a.value.trim())t+=NL+a.dataset.rotulo+':'+NL+'  '+a.value.trim().split(NL).join(NL+'  ')+NL;});
const fim=()=>{document.getElementById('copiado').textContent='Resumo copiado: cole no e-mail ou no chat para o analista.';};
if(!dec||!nome){document.getElementById('copiado').textContent='Marque a decisão e escreva seu nome antes de copiar.';return;}
if(navigator.clipboard)navigator.clipboard.writeText(t).then(fim,()=>{prompt('Copie o resumo:',t)});else prompt('Copie o resumo:',t);});
document.querySelector('nav').addEventListener('keydown',e=>{const i=botoes.indexOf(document.activeElement);if(i<0)return;
let j=null;if(e.key==='ArrowRight')j=(i+1)%botoes.length;if(e.key==='ArrowLeft')j=(i-1+botoes.length)%botoes.length;
if(j!==null){e.preventDefault();botoes[j].focus();abrir(botoes[j].dataset.alvo);}});
"""


def _texto_meta(m, md):
    if not md.get('meta_medida'):
        return ''
    alvo = medida(m, md['meta_medida'])
    valor = formatar(float(alvo['dax']), alvo['formato'], True) if alvo and alvo['tipo'] == 'meta' else md['meta_medida']
    sentido = 'quanto maior, melhor' if md['polaridade'] == 'maior_melhor' else 'quanto menor, melhor'
    return f'Meta: {valor} ({sentido})'


def codigo_do_prototipo(m):
    """Identifica o que o gestor viu: muda quando muda qualquer coisa que aparece no painel."""
    import hashlib
    return hashlib.sha1(json.dumps(retrato(m), sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:8]


def _excecoes_do_filtro(m, v, pagina):
    if v['tipo'] not in ('segmentador', 'botoes', 'abas', 'alternar') or not v.get('categoria'):
        return []
    g = grafo_de_filtro(m)
    nomes = {x['nome'] for o in pagina['visuais'] for x in o['valores'] + o['campos'] if x and x['tipo'] == 'medida'}
    return sorted(n for n in nomes
                  if not all(chega(m, g, v['categoria']['tabela'], a, n) for a in tabelas_da_medida(m, n)))


def _botao_info(m, v, pagina=None):
    nomes = [x['nome'] for x in v['valores'] + v['campos'] + ([v['meta']] if v.get('meta') else []) if x and x['tipo'] == 'medida']
    itens = []
    for n in dict.fromkeys(nomes):
        md = medida(m, n)
        if md and md['tipo'] not in ('cor', 'corte'):
            itens.append({'nome': md['nome'], 'definicao': md['descricao'], 'meta': _texto_meta(m, md)})
    excecoes = _excecoes_do_filtro(m, v, pagina) if pagina else []
    dados = json.dumps({'titulo': v['titulo'], 'itens': itens, 'excecoes': excecoes}, ensure_ascii=False)
    return f'<button type="button" class="info" aria-label="O que é: {_e(v["titulo"])}" data-info="{_e(dados)}">i</button>'


def _secao_aprovar(m, problemas):
    onde = {}
    for pg in m['paginas']:
        for v in pg['visuais']:
            for x in v['valores'] + v['campos'] + ([v['meta']] if v.get('meta') else []):
                if x and x['tipo'] == 'medida':
                    onde.setdefault(x['nome'], []).append(pg['nome'])
    inds = []
    for md in m['medidas']:
        if md['tipo'] in ('cor', 'meta', 'corte') or md['nome'] not in onde:
            continue
        paginas = ', '.join(dict.fromkeys(onde[md['nome']]))
        meta = _texto_meta(m, md)
        inds.append(f'<div class="ind" data-nome="{_e(md["nome"])}"><label><input type="checkbox" data-guardar="ok:{_e(md["nome"])}">'
                    f'<span><b>{_e(md["nome"])}</b> — {_e(md["descricao"] or "sem definição")}</span></label>'
                    f'<div class="det">Aparece em: {_e(paginas)}{" · " + _e(meta) if meta else ""}</div></div>')
    traduzidos = [t for t in dict.fromkeys(para_gestor(a) for a in problemas.avisos) if t]
    pontos = ''.join(f'<li>{_e(t)}</li>' for t in traduzidos) or '<li class="ok">Nenhum.</li>'
    comentarios = ''.join(f'<h3>Comentários sobre a página {_e(pg["nome"])}</h3><textarea data-guardar="c:{_e(pg["nome"])}" '
                          f'data-rotulo="Página {_e(pg["nome"])}" placeholder="O que mudar, tirar ou acrescentar?"></textarea>'
                          for pg in m['paginas'])
    return (f'<section id="aprovar" class="aprovar"><p>Antes de dizer "sim", confirme se cada número significa o que você '
            f'espera. Os valores do protótipo são fictícios: aqui se aprova <b>o que</b> é medido e <b>como</b> aparece.</p>'
            f'<div class="progresso" id="progresso"></div>{"".join(inds)}'
            f'<h3>Pontos de atenção (converse com o analista)</h3><ul class="lista">{pontos}</ul>{comentarios}'
            f'<h3>A sua decisão</h3><div class="decisao"><label><input type="radio" name="decisao" value="Aprovo" '
            f'data-guardar="d:aprovo"> Aprovo este protótipo</label><label><input type="radio" name="decisao" '
            f'value="Peço ajustes" data-guardar="d:ajustes"> Peço ajustes (veja os comentários)</label></div>'
            f'<p><label>Seu nome <input type="text" id="aprovador" data-guardar="nome" autocomplete="name"></label></p>'
            f'<p><button type="button" class="botao" id="copiar">Copiar resumo do aceite</button><span class="copiado" '
            f'id="copiado" role="status"></span></p><p class="nota">As marcações ficam só neste navegador: mande o resumo '
            f'copiado ao analista (e-mail ou chat). O aceite vale quando ele registra o seu "sim" no Deidara.</p></section>')


def _rotular_secao(s):
    """<section role=tabpanel ... aria-labelledby="aba-XYZ"> com id="XYZ" de volta."""
    import re as _re
    return _re.sub(r'<section role="tabpanel" tabindex="0" aria-labelledby="aba-([^"]+)"',
                   r'<section role="tabpanel" tabindex="0" id="\1" aria-labelledby="aba-\1"', s, count=1)


def gerar_html(m, problemas, versao):
    cores = m['tema']['cores']
    sim = Simulador(m)
    abas, secoes = [], []
    rel = paginas_do_relatorio(m)
    ids = [f'p{k + 1}' for k in range(len(rel))]
    aba_do_grupo = {}
    for i, pg in enumerate(rel):
        sid = ids[i]
        if not pg['oculta'] or pg.get('dica') or pg.get('detalhe'):   # dica e detalhe também se aprovam
            abas.append((sid, f'Dica · {pg["nome"]}' if pg.get('dica') else
                         f'Detalhe · {pg["nome"]}' if pg.get('detalhe') else pg['nome']))
            aba_do_grupo[pg['grupo']] = sid
        lay = montar(m, rel, i)
        vis = []
        for v, p in lay['posicoes']:
            vv = dict(v, titulo='') if id(v) in lay['sem_titulo'] else v
            vis.append(f'<div class="vis {v["tipo"]}" style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px">'
                       f'{_botao_info(m, v, pg)}{svg_visual(sim, vv, p, cores)}</div>')
        ir = ''.join(f'<button type="button" class="ir" data-ir="{ids[n["alvo"]]}" title="{_e(n["rotulo"])}" '
                     f'aria-label="{_e(n["rotulo"])}" style="left:{n["x"]}px;top:{n["y"]}px;width:{n["w"]}px;height:{n["h"]}px">'
                     f'</button>' for n in lay['nav'])
        if pg.get('ajuda'):
            notas = ''.join(f'<div class="nota-ajuda" style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px">'
                            + ''.join(f'<{"b" if k == 0 else "p"}>{_e(t)}</{"b" if k == 0 else "p"}>'
                                      for k, t in enumerate(nota_de_ajuda(m, v))) + '</div>' for v, p in lay['posicoes'])
            ir += (f'<button type="button" class="ajuda" aria-label="Como ler esta página" title="Como ler esta página" '
                   f'style="left:{lay["w"] - 64}px;top:{lay["h"] - 104}px">?</button><div class="notas" hidden>{notas}</div>')
        tour = next((medida(m, x['tour']) for x in m['paginas'] if x['nome'] == pg['nome'] and isinstance(x.get('tour'), str)),
                    None) if not pg['oculta'] else None
        if tour:                                     # o mesmo HTML do Power BI, por cima da página
            x_tour = lay['w'] - (248 if pg.get('ajuda') else 184)
            ir += (f'<button type="button" class="abre-tour" style="left:{x_tour}px;top:{lay["h"] - 104}px">▶ Tour guiado</button>'
                   f'<div class="tour-proto" hidden>{tour["extra"]["html"]}'
                   f'<button type="button" class="fecha-tour" style="left:{lay["w"] - 184}px">Voltar</button></div>')
        classes = 'pagina' + (' desenhada' if lay['fundo'] else '') + (' escura' if lay['escuro'] else '')
        fundo = f'<div class="fundo" aria-hidden="true">{lay["fundo"]}</div>' if lay['fundo'] else f'<h2>{_e(pg["nome"])}</h2>'
        desc = f'<p class="nota">{_e(pg["descricao"])}</p>' if pg['descricao'] and not lay['fundo'] else ''
        if pg.get('detalhe'):
            c = pg['detalhe']
            desc += (f'<p class="nota">Página de detalhamento: no Power BI, clique com o botão direito num ponto de '
                     f'{_e(c["tabela"])}[{_e(c["nome"])}] em outra página e escolha Detalhar; ela abre filtrada pelo item.</p>')
        if pg.get('dica'):
            de = [v.get('titulo') or v['tipo'] for x in m['paginas'] for v in x['visuais'] if v.get('dica') == pg['nome']]
            desc += (f'<p class="nota">Página de dica (320 x 240): aparece ao passar o mouse em '
                     f'{_e(", ".join(de) or "nenhum visual ainda")}.</p>')
        secoes.append(f'<section id="{sid}" data-aba="{aba_do_grupo.get(pg["grupo"], sid)}"><div class="palco">'
                      f'<div class="{classes}" style="width:{lay["w"]}px;height:{lay["h"]}px">'
                      f'{fundo}{"".join(vis)}{ir}</div></div>{desc}</section>')
    abas.append(('aprovar', 'Para aprovar'))
    secoes.append(_secao_aprovar(m, problemas))
    abas.append(('modelo', 'Modelo de dados'))
    rels = ''.join(f'<tr><td>{_e(r["de"])}[{_e(r["de_coluna"])}]</td><td>{_e(r["para"])}[{_e(r["para_coluna"])}]</td>'
                   f'<td>{"ativa" if r["ativo"] else "inativa"}</td><td>{_e(r["prova"])}'
                   + (f'<br><span class="sub">campos: {_e(", ".join(f"{a}={b}" for a, b in r["campos"]))}</span>' if r['composta'] else '')
                   + '</td></tr>' for r in m['relacionamentos'])
    secoes.append(f'<section id="modelo">{svg_modelo(m)}<h3>Relacionamentos (muitos → um)</h3><div class="tabela-rolagem"><table>'
                  f'<tr><th>De (muitos)</th><th>Para (um)</th><th>Estado</th><th>Prova da ligação</th></tr>{rels}</table></div></section>')
    abas.append(('indicadores', 'Indicadores'))
    linhas = ''.join(f'<tr><td><b>{_e(x["nome"])}</b><br><span class="sub">{_e(x["pasta"])}</span></td><td>{_e(x["descricao"])}</td>'
                     f'<td>{_e(x["formato"] or "")}</td><td><pre>{_e(x["dax"] or "")}</pre></td></tr>' for x in m['medidas']
                     if x['tipo'] not in ('cor', 'corte'))
    secoes.append(f'<section id="indicadores"><div class="tabela-rolagem"><table><tr><th>Indicador</th><th>Definição</th>'
                  f'<th>Formato</th><th>DAX</th></tr>{linhas}</table></div></section>')
    abas.append(('pendencias', f'Pendências do analista ({len(problemas.avisos)})'))
    av = ''.join(f'<li>{_e(a)}</li>' for a in problemas.avisos) or '<li class="ok">Nenhuma pendência.</li>'
    secoes.append(f'<section id="pendencias"><p>Detalhe técnico dos pontos de atenção (para o analista):</p>'
                  f'<ul class="lista">{av}</ul></section>')
    secoes = [s.replace('<section id="', '<section role="tabpanel" tabindex="0" aria-labelledby="aba-', 1)
              .replace('aria-labelledby="aba-', 'aria-labelledby="aba-', 1) for s in secoes]
    secoes = [_rotular_secao(s) for s in secoes]
    nav = ''.join(f'<button type="button" role="tab" id="aba-{sid}" aria-controls="{sid}" data-alvo="{sid}">{_e(n)}</button>'
                  for sid, n in abas)
    meta = ' · '.join(x for x in [m['publico'] and f'Público: {m["publico"]}',
                                  m['responsavel'] and f'Responsável: {m["responsavel"]}',
                                  m.get('versao') and f'painel v{m["versao"]}', f'Deidara {versao}'] if x)
    chave_local = f'{m["projeto"]}|{m.get("versao") or versao}'
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(m['projeto'])} · protótipo</title><style>{CSS}</style></head>
<body data-chave="{_e(chave_local)}" data-projeto="{_e(m['projeto'])}" data-versao="{_e(m.get('versao') or '—')}" data-codigo="{codigo_do_prototipo(m)}">
<header><h1>{_e(m['projeto'])}</h1><span class="meta">{_e(meta)}</span></header>
<div class="faixa">Protótipo gerado pelo Deidara. Os números são fictícios: valide layout, indicadores e navegação, não valores.
<span class="so-tela">Clique em ⓘ para ver o que cada número significa; a aba <b>Para aprovar</b> reúne o que confirmar.</span></div>
<nav role="tablist">{nav}</nav><main>{''.join(secoes)}</main>
<aside id="painel" role="dialog" aria-live="polite"></aside>
<script>{JS}</script></body></html>
"""
