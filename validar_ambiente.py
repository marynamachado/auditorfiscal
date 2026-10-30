"""Validação técnica isolada. Não aprova uso fiscal ou revisão independente."""
import io
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.request import build_opener,ProxyHandler
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parent

def validate():
    import app,demo,recovery
    def local_db(path):return sqlite3.connect(path,factory=app.ManagedConnection)
    report={'created':datetime.now(timezone.utc).isoformat(),'platform':platform.system(),'python':platform.python_version(),'native_windows_execution':os.name=='nt','professional_approval':False,'independent_security_review':'pendente','checks':[],'manual_windows_checks':['Abrir o iniciador .bat no Windows e o navegador','Usar importação e carteira pela interface','Atualizar preservando data e configuração de senha','Restaurar cópia isolada e conferir com o contador','Conferir permissões da pasta, bloqueio do Windows e criptografia do dispositivo']}
    def check(name,operation):
        try:
            operation();report['checks'].append({'name':name,'passed':True});print('OK: '+name,flush=True)
        except Exception as error:
            report['checks'].append({'name':name,'passed':False,'error':type(error).__name__+': '+str(error)});print('FALHOU: '+name+' — '+str(error),flush=True)
    original_db,original_mode=app.DB,app.DEMO_MODE
    try:
        with tempfile.TemporaryDirectory(prefix='auditor-validacao-') as tmp:
            folder=Path(tmp);app.DB=folder/'demonstracao.sqlite3';app.DEMO_MODE=True
            def seed():
                with app.connect() as db:demo.seed(db);demo.load_scenario(db,'correto')
                with app.connect() as db:
                    state=app.state(db)
                    assert len(state['invoices'])==3 and state['settlements'][0]['balance']=='270.00'
            check('Fluxo sintético: XML, SPED e saldo simulado conhecido',seed)
            server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                opener=build_opener(ProxyHandler({}));base='http://127.0.0.1:'+str(server.server_port)
                def http():
                    with opener.open(base+'/api/health',timeout=5) as response:assert json.load(response)['demo']
                    with opener.open(base+'/api/state',timeout=5) as response:assert len(json.load(response)['invoices'])==3
                check('Servidor local e leitura das APIs',http)
                def backup():
                    with opener.open(base+'/api/backup',timeout=15) as response:raw=response.read()
                    with ZipFile(io.BytesIO(raw)) as archive:archive.extract('demonstracao.sqlite3',folder/'restaurado')
                    with local_db(folder/'restaurado'/'demonstracao.sqlite3') as db:
                        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                        assert db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]==3
                check('Backup completo HTTP e restauração em pasta isolada',backup)
            finally:server.shutdown();server.server_close()
            def corrupted_copy():
                saved=recovery.snapshot(app.DB,folder/'seguro.sqlite3')
                broken=folder/'corrompido.sqlite3';broken.write_bytes(b'COPIA FICTICIA CORROMPIDA')
                try:
                    with local_db(broken) as db:db.execute('PRAGMA integrity_check').fetchone()
                except sqlite3.DatabaseError:pass
                else:raise AssertionError('A cópia corrompida não foi detectada')
                shutil.copy2(saved,broken)
                with local_db(broken) as db:assert db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]==3
            check('Detectar cópia corrompida e recuperar cópia de teste',corrupted_copy)
            def migration():
                legacy=folder/'legado.sqlite3'
                with local_db(legacy) as db:
                    db.execute("CREATE TABLE companies(id INTEGER PRIMARY KEY,cnpj TEXT UNIQUE NOT NULL,name TEXT NOT NULL,regime TEXT NOT NULL,cnae TEXT,ie TEXT,city TEXT,uf TEXT,wallet_id INTEGER,icms_rate TEXT NOT NULL DEFAULT '18')")
                    db.execute("INSERT INTO companies(cnpj,name,regime,city,uf) VALUES ('11222333000181','LEGADO FICTICIO','Normal','Goiânia','GO')")
                saved=recovery.prepare_migration_backup(legacy);assert saved and saved.exists()
                app.DB=legacy;app.DEMO_MODE=False
                with app.connect() as db:assert db.execute('SELECT name FROM companies').fetchone()['name']=='LEGADO FICTICIO'
                with local_db(saved) as db:
                    assert db.execute('SELECT name FROM companies').fetchone()[0]=='LEGADO FICTICIO'
                    assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='fiscal_cases'").fetchone()
            check('Cópia anterior à atualização e preservação de cadastro legado',migration)
            def interruption():
                path=folder/'interrupcao.sqlite3'
                with local_db(path) as db:db.execute('CREATE TABLE probe(value INTEGER)');db.execute('INSERT INTO probe VALUES (1)')
                code="import sqlite3,os,sys; db=sqlite3.connect(sys.argv[1]); db.execute('BEGIN IMMEDIATE'); db.execute('INSERT INTO probe VALUES (2)'); os._exit(17)"
                child=subprocess.run([sys.executable,'-c',code,str(path)],timeout=10,capture_output=True)
                assert child.returncode==17
                with local_db(path) as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                    assert db.execute('SELECT COUNT(*) FROM probe').fetchone()[0]==1
            check('Rollback de transação SQLite após interrupção de processo sintético',interruption)
    finally:app.DB,app.DEMO_MODE=original_db,original_mode
    report['technical_checks_passed']=all(c['passed'] for c in report['checks'])
    return report

if __name__=='__main__':
    print('VALIDAÇÃO TÉCNICA ISOLADA — nenhum banco de clientes será aberto ou alterado.',flush=True)
    report=validate();target=ROOT/'data'/'validacao-tecnica.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Relatório: data/validacao-tecnica.json',flush=True)
    if not report['native_windows_execution']:print('Esta execução NÃO ocorreu no Windows. A validação nativa do Windows permanece pendente.',flush=True)
    print('Este relatório não é aprovação fiscal nem revisão independente de segurança.',flush=True)
    sys.exit(0 if report['technical_checks_passed'] else 1)
