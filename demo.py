"""Inicia uma demonstração isolada; nunca usa o banco fiscal normal."""
import json
from datetime import datetime, timezone
from pathlib import Path
import app
import demo_data

VERSION='auditor-fiscal-demo-v1'
DEMO_DB=Path(__file__).parent/'data'/'demonstracao.sqlite3'

def require_demo(db):
    if not app.DEMO_MODE:raise ValueError('Esta operação só está disponível no modo demonstração')
    row=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='demo_meta'").fetchone()
    marker=db.execute('SELECT version FROM demo_meta WHERE id=1').fetchone() if row else None
    if not marker or marker['version']!=VERSION:raise ValueError('Banco sem identificação de demonstração; nenhuma informação foi apagada')

def populate(db):
    app.mutate(db,'wallet',{'name':demo_data.WALLET,'responsible':'Contador de teste'})
    app.mutate(db,'company',{'cnpj':demo_data.COMPANY,'name':demo_data.MARKER+' LTDA','regime':'Normal','cnae':'4744099','ie':'000000000','city':'Goiânia','uf':'GO','wallet_id':1,'icms_rate':'18'})
    app.mutate(db,'agenda_contact',{'company_id':1,'wallet_id':1,'contact':'Responsável de demonstração','phone':'(00) 00000-0000','email':'fiscal@example.invalid','fee':'350.00'})
    db.execute('UPDATE companies SET source=? WHERE id=1',('Kit de demonstração sintético',))
    for month in ('2026-10','2026-11'):
        app.mutate(db,'period',{'company_id':1,'month':month})
        for title in ('Importar XMLs de demonstração','Conferir o relatório SPED de teste','Revisar e concluir o trabalho do mês'):
            app.mutate(db,'agenda_task',{'company_id':1,'title':title,'month':month,'due':month+'-28','priority':'Normal','notes':'Tarefa fictícia. Veja o roteiro em Como testar.'})
        db.execute('UPDATE agenda_tasks SET checks=? WHERE month=? AND title=?',(json.dumps([{'text':'Selecionar a competência '+month,'done':False},{'text':'Conferir o resultado de cada arquivo','done':False}],ensure_ascii=False),month,'Importar XMLs de demonstração'))
    app.mutate(db,'agenda_note',{'company_id':1,'text':'DEMONSTRAÇÃO: Rua Exemplo Fictício, 100 — Bairro de Teste — Goiânia/GO. CEP e IE fictícios. Honorário de R$ 350,00 apenas para testar. Alíquotas didáticas, sem validade fiscal.','color':'yellow'})
    app.log(db,'Empresa e competências de demonstração preparadas, sem importar notas automaticamente')

def seed(db):
    if not app.DEMO_MODE:raise ValueError('Demonstração não habilitada')
    db.execute('CREATE TABLE IF NOT EXISTS demo_meta(id INTEGER PRIMARY KEY CHECK(id=1),version TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS demo_runs(id INTEGER PRIMARY KEY,scenario TEXT NOT NULL,created TEXT NOT NULL,results TEXT NOT NULL,audit_id INTEGER)')
    row=db.execute('SELECT version FROM demo_meta WHERE id=1').fetchone()
    if row:
        require_demo(db)
        return
    tables=[r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('demo_meta','demo_runs')")]
    if any(db.execute('SELECT 1 FROM "'+name.replace('"','""')+'" LIMIT 1').fetchone() for name in tables):
        raise ValueError('O banco selecionado já contém dados sem identificação de demonstração. Nenhum cadastro foi substituído.')
    db.execute('INSERT INTO demo_meta(id,version) VALUES (1,?)',(VERSION,))
    populate(db)

def reset(db):
    require_demo(db)
    for table in ('demo_runs','fiscal_closures','fiscal_reviews','fiscal_finding_reviews','fiscal_cases','fiscal_entries','fiscal_rules','fiscal_events','sped_audits','sped_files','items','invoices','findings','agenda_tasks','agenda_notes','agenda_closures','agenda_checkins','agenda_sources','carteira_document','periods','companies','wallets','history'):
        db.execute('DELETE FROM '+table)
    populate(db)
    return {'ok':True}

def load_scenario(db, name):
    require_demo(db)
    scenario=demo_data.scenarios().get(name)
    if not scenario:raise ValueError('Cenário não encontrado')
    p=db.execute('SELECT p.* FROM periods p JOIN companies c ON c.id=p.company_id WHERE c.cnpj=? AND p.month=?',(demo_data.COMPANY,scenario['month'])).fetchone()
    if not p or p['closed']:raise ValueError('A competência de demonstração está fechada ou foi alterada; reinicie a demonstração para repetir')
    if db.execute('SELECT 1 FROM invoices WHERE period_id=?',(p['id'],)).fetchone():raise ValueError('Já existem notas nessa competência. Continue o roteiro manual ou reinicie a demonstração antes de carregar o cenário automático.')
    db.execute('UPDATE demo_meta SET version=version WHERE id=1')
    results=[]
    for filename,content in scenario['xmls'].items():
        db.execute('SAVEPOINT demo_xml')
        try:
            result=app.mutate(db,'import',{'period_id':p['id'],'xml':content})
            results.append({'filename':filename,'status':'Duplicada' if result.get('duplicate') else 'Importada','detail':'Duplicidade registrada, sem criar outra nota' if result.get('duplicate') else 'Salva no banco'})
            db.execute('RELEASE demo_xml')
        except (ValueError,app.ET.ParseError,app.sqlite3.IntegrityError) as error:
            db.execute('ROLLBACK TO demo_xml');db.execute('RELEASE demo_xml')
            results.append({'filename':filename,'status':'Rejeitada','detail':str(error)})
    report=app.mutate(db,'sped_import',{'period_id':p['id'],'filename':'SPED_DIDATICO_'+scenario['month']+'.txt','content':scenario['sped']})
    db.execute('INSERT INTO demo_runs(scenario,created,results,audit_id) VALUES (?,?,?,?)',(name,datetime.now(timezone.utc).isoformat(timespec='seconds'),json.dumps(results,ensure_ascii=False),report['audit_id']))
    return {'ok':True,'results':results,'audit_id':report['audit_id']}

def info(db):
    result={'enabled':app.DEMO_MODE,'runs':[]}
    if app.DEMO_MODE:
        require_demo(db)
        result['runs']=[dict(r) for r in db.execute('SELECT * FROM demo_runs ORDER BY id DESC')]
        for r in result['runs']:r['results']=json.loads(r['results'])
    return result

if __name__=='__main__':
    import sys
    app.DB=DEMO_DB
    app.DEMO_MODE=True
    print('Preparando o banco separado de demonstração...',flush=True)
    app.recovery.prepare_migration_backup(app.DB)
    with app.connect() as db:seed(db)
    print('MODO DEMONSTRAÇÃO: banco separado dos clientes reais. Sem validade fiscal.',flush=True)
    app.run(port=8001,open_browser='--open-browser' in sys.argv)
