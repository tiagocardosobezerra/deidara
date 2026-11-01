"""
Conferência no Power BI Desktop aberto: o que o schema e os testes não veem.

O `validar_pbip` confere o JSON e o TMDL; o Desktop confere o DAX de verdade. Medida que o motor recusa (filtro
True/False com medida dentro, função de outra versão) passa em tudo e só aparece com o painel aberto, como um
aviso no painel de campos. Aqui o Deidara pergunta ao próprio motor do Desktop, pela porta local do msmdsrv e a
biblioteca ADOMD que vem com o Power BI:

- o erro de cada medida, item de grupo de cálculo e partição (INFO.MEASURES, INFO.CALCULATIONITEMS, INFO.PARTITIONS);
- cada medida calculada no total e mês a mês (com calendário), para o erro que só aparece na conta.

Só Windows, com o Power BI Desktop aberto no projeto. Nada é gravado no modelo; `--atualizar` pede a atualização
dos dados antes (o projeto de demonstração não pede credencial).
"""

import json
import os
import subprocess
import time

SCRIPT = r'''
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'
$saida = [ordered]@{ instancias = @(); erro = $null }
try {
  $ms = @(Get-Process msmdsrv -ErrorAction SilentlyContinue)
  foreach ($p in $ms) {
    $porta = (Get-NetTCPConnection -State Listen -OwningProcess $p.Id -ErrorAction SilentlyContinue |
              Select-Object -First 1).LocalPort
    $pai = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").ParentProcessId
    $titulo = (Get-Process -Id $pai -ErrorAction SilentlyContinue).MainWindowTitle
    $linha = (Get-CimInstance Win32_Process -Filter "ProcessId=$pai").CommandLine
    $arquivo = if ($linha -match '"([^"]+\.pbi[px])"') { $Matches[1] } else { $null }
    $saida.instancias += [ordered]@{ porta = $porta; titulo = $titulo; arquivo = $arquivo; pid = $pai; dll = (Join-Path (Split-Path $p.Path) 'Microsoft.PowerBI.AdomdClient.dll') }
  }
  $alvo = $saida.instancias | Where-Object { -not $env:DEIDARA_PORTA -or "$($_.porta)" -eq $env:DEIDARA_PORTA } | Select-Object -First 1
  if ($alvo -and $env:DEIDARA_CONSULTAS) {
    Add-Type -Path $alvo.dll
    $c = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$($alvo.porta)")
    $c.Open()
    $cmd = $c.CreateCommand()
    if ($env:DEIDARA_ATUALIZAR) {
      $cmd.CommandText = "SELECT [CATALOG_NAME] FROM `$SYSTEM.DBSCHEMA_CATALOGS"
      $r = $cmd.ExecuteReader(); $null = $r.Read(); $banco = $r.GetValue(0); $r.Close()
      $cmd.CommandText = '{"refresh": {"type": "full", "objects": [{"database": "' + $banco + '"}]}}'
      $null = $cmd.ExecuteNonQuery()
    }
    $resultados = @()
    foreach ($q in (Get-Content -Raw -Encoding UTF8 $env:DEIDARA_CONSULTAS | ConvertFrom-Json)) {
      $item = [ordered]@{ id = $q.id; linhas = @(); erro = $null }
      try {
        $cmd.CommandText = $q.dax
        $r = $cmd.ExecuteReader()
        while ($r.Read()) {
          $linha = @(); for ($i = 0; $i -lt $r.FieldCount; $i++) { $linha += "$($r.GetValue($i))" }
          $item.linhas += ,$linha
        }
        $r.Close()
      } catch { $item.erro = $_.Exception.InnerException.Message; if (-not $item.erro) { $item.erro = $_.Exception.Message } }
      $resultados += $item
    }
    $c.Close()
    $saida.resultados = $resultados
  }
} catch { $saida.erro = $_.Exception.Message }
$saida | ConvertTo-Json -Depth 6 -Compress
'''


def _rodar(consultas=None, porta=None, atualizar=False, pasta_tmp=None):
    env = dict(os.environ)
    if porta:
        env['DEIDARA_PORTA'] = str(porta)
    if atualizar:
        env['DEIDARA_ATUALIZAR'] = '1'
    if consultas is not None:
        arq = os.path.join(pasta_tmp or os.getcwd(), '.deidara_consultas.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(consultas, f, ensure_ascii=False)
        env['DEIDARA_CONSULTAS'] = arq
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', SCRIPT],
                           capture_output=True, env=env, timeout=600)
    finally:
        if consultas is not None:
            os.remove(arq)
    texto = r.stdout.decode('utf-8', 'replace').strip()
    try:
        return json.loads(texto[texto.index('{'):], strict=False)
    except ValueError:
        return {'instancias': [], 'erro': (r.stderr.decode('utf-8', 'replace') or texto or 'sem resposta')[:500]}


ROTULOS = {'medidas': 'medida', 'grupo': 'item do grupo de cálculo', 'particoes': 'partição'}


def consultas_do_modelo(medidas, calendario=None):
    """As consultas DAX: os erros que o motor guarda e cada medida no total e (com calendário) mês a mês."""
    out = [{'id': 'erros:medidas', 'dax': 'EVALUATE FILTER(SELECTCOLUMNS(INFO.MEASURES(), "n", [Name], "e", '
                                          '[ErrorMessage]), NOT ISBLANK([e]))'},
           {'id': 'erros:grupo', 'dax': 'EVALUATE FILTER(SELECTCOLUMNS(INFO.CALCULATIONITEMS(), "n", [Name], "e", '
                                        '[ErrorMessage]), NOT ISBLANK([e]))'},
           {'id': 'erros:particoes', 'dax': 'EVALUATE FILTER(SELECTCOLUMNS(INFO.PARTITIONS(), "n", [Name], "e", '
                                            '[ErrorMessage]), NOT ISBLANK([e]))'}]
    for nome in medidas:
        ref = '[' + nome.replace(']', ']]') + ']'
        out.append({'id': f'total:{nome}', 'dax': f'EVALUATE ROW("v", {ref})'})
        if calendario:
            out.append({'id': f'mes:{nome}', 'dax': f"EVALUATE SUMMARIZECOLUMNS('{calendario}'[Ano-Mês], \"v\", {ref})"})
    return out


def conferir(medidas, calendario=None, porta=None, atualizar=False, pasta_tmp=None):
    """{'instancia': {...}, 'problemas': [(onde, erro)], 'calculadas': n, 'vazias': [medidas sem valor no total]}"""
    base = _rodar(porta=porta)
    if base.get('erro'):
        return {'erro': base['erro']}
    inst = [i for i in base['instancias'] if not porta or str(i['porta']) == str(porta)]
    if len(inst) > 1 and pasta_tmp:                  # o Desktop aberto num projeto dentro da pasta do argila.json
        dentro = [i for i in inst if i.get('arquivo') and
                  os.path.normcase(os.path.abspath(i['arquivo'])).startswith(os.path.normcase(pasta_tmp) + os.sep)]
        inst = dentro if len(dentro) == 1 else inst
    if not inst:
        return {'erro': 'nenhum Power BI Desktop aberto' if not base['instancias'] else
                f'nenhum Power BI Desktop na porta {porta}', 'instancias': base['instancias']}
    if len(inst) > 1:
        return {'erro': 'mais de um Power BI Desktop aberto: escolha com --porta', 'instancias': inst}
    r = _rodar(consultas_do_modelo(medidas, calendario), porta=inst[0]['porta'], atualizar=atualizar,
               pasta_tmp=pasta_tmp)
    if r.get('erro'):
        return {'erro': r['erro']}
    problemas, vazias = [], []
    for x in r.get('resultados') or []:
        tipo, _, nome = x['id'].partition(':')
        if x['erro'] and tipo == 'mes' and (f'medida {nome}', x['erro'].strip()) in problemas:
            continue                                 # o mesmo erro do total: uma linha só
        if x['erro']:
            onde = f'consulta {ROTULOS[nome]}' if tipo == 'erros' else f'medida {nome}' + (' (mês a mês)' if tipo == 'mes' else '')
            problemas.append((onde, x['erro'].strip()))
        elif tipo == 'erros':
            problemas += [(f'{ROTULOS[nome]} {ln[0]}', ln[1]) for ln in x['linhas']]
        elif tipo == 'total' and (not x['linhas'] or not x['linhas'][0][0]):
            vazias.append(nome)
    return {'instancia': inst[0], 'problemas': problemas, 'calculadas': len(medidas), 'vazias': vazias}


def _mesmo_arquivo(a, b):
    return bool(a and b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def abrir(pbip, espera=300):
    """Abre o .pbip no Power BI Desktop e espera o motor dele responder. Devolve a porta, ou None no tempo esgotado."""
    if os.name != 'nt':
        return None
    os.startfile(os.path.abspath(pbip))              # noqa: S606 (o Desktop é o programa associado ao .pbip)
    limite = time.time() + espera
    while time.time() < limite:
        time.sleep(5)
        inst = [i for i in _rodar().get('instancias') or [] if _mesmo_arquivo(i.get('arquivo'), pbip) and i.get('porta')]
        if inst:
            time.sleep(10)                           # o motor responde antes de o relatório terminar de carregar
            return inst[0]['porta']
    return None


def fechar(porta):
    """Fecha o Power BI Desktop daquela porta, sem salvar (é o projeto gerado, que se gera de novo)."""
    inst = [i for i in _rodar().get('instancias') or [] if str(i.get('porta')) == str(porta)]
    for i in inst:
        subprocess.run(['taskkill', '/PID', str(i['pid']), '/F', '/T'], capture_output=True)
    return bool(inst)

