"""Diagnóstico local e somente leitura, sem imprimir dados dos clientes."""
import json
import socket
import sqlite3
import sys
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT=Path(__file__).resolve().parent

def collect(port=8001, emit=None):
    lines=['DIAGNÓSTICO DA DEMONSTRAÇÃO — AUDITOR FISCAL','Nenhum cadastro será alterado. Este relatório não lista clientes.','Python: '+sys.version.split()[0]]
    if emit:
        for line in lines:emit(line)
    def log(message):
        lines.append(message)
        if emit:emit(message)
    if sys.version_info<(3,9):log('ATENÇÃO: Python antigo. Instale Python 3.12 ou mais recente.')
    required=('app.py','demo.py','demo_data.py','agenda.py','carteira.py','sped.py','static/index.html','static/app.js','static/demo.js','static/request.js','static/style.css')
    log('Conferindo os arquivos...')
    missing=[name for name in required if not (ROOT/name).is_file()]
    log('Arquivos do programa: '+('OK' if not missing else 'FALTANDO: '+', '.join(missing)))
    # Apenas loopback; não consulta serviços externos nem altera o proxy do usuário.
    opener=build_opener(ProxyHandler({}))
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=2):pass
        log('Porta local '+str(port)+': aberta')
    except OSError:
        log('Porta local '+str(port)+': sem resposta. O iniciador pode estar fechado ou ter falhado.')
    for endpoint in ('/api/health','/api/state'):
        log('Consultando '+endpoint+'...')
        try:
            with opener.open('http://127.0.0.1:'+str(port)+endpoint,timeout=5) as response:
                raw=response.read(2_000_001)
                if len(raw)>2_000_000:
                    log(endpoint+': resposta recebida, maior que 2 MB; conteúdo não incluído.')
                    continue
                data=json.loads(raw)
                if endpoint=='/api/health':
                    ok=isinstance(data,dict) and data.get('service')=='auditor-fiscal'
                    log(endpoint+(': programa identificado; modo demonstração '+('SIM' if data.get('demo') else 'NÃO') if ok else ': outro programa ou versão incompatível'))
                else:
                    ok=isinstance(data,dict) and isinstance(data.get('companies'),list)
                    log(endpoint+(': dados respondendo; conteúdo dos cadastros omitido.' if ok else ': formato incompatível.'))
        except Exception as error:
            status=' '+str(error.code) if getattr(error,'code',None) else ''
            log(endpoint+': não respondeu corretamente ('+type(error).__name__+status+').')
    database=ROOT/'data'/'demonstracao.sqlite3'
    if not database.is_file():log('Banco de demonstração: ainda não foi criado. Abra o iniciador.')
    else:
        try:
            with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=3) as db:
                row=db.execute('SELECT version FROM demo_meta WHERE id=1').fetchone()
                log('Banco de demonstração: '+('identificado e legível.' if row and row[0]=='auditor-fiscal-demo-v1' else 'identificação ausente ou incompatível.'))
        except sqlite3.Error as error:
            log('Banco de demonstração: falha de leitura ('+type(error).__name__+': '+str(error)+'). Feche outras janelas do programa e tente novamente.')
    return lines

if __name__=='__main__':
    print('Verificando... isso pode levar até 15 segundos.',flush=True)
    lines=collect(emit=lambda line:print(line,flush=True))
    try:
        folder=ROOT/'data';folder.mkdir(exist_ok=True)
        (folder/'diagnostico-demonstracao.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print('\nRelatório salvo em data/diagnostico-demonstracao.txt',flush=True)
    except OSError:
        print('\nNão foi possível salvar o relatório. Envie uma foto desta janela.',flush=True)
