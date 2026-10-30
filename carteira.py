"""Estado completo da interface original, com controle de versão e projeção fiscal."""
import json
import uuid
from datetime import datetime
import agenda

class Conflict(ValueError):
    pass

def migrate(db):
    db.execute('CREATE TABLE IF NOT EXISTS carteira_document(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)')
    if 'agenda_hidden' not in {r['name'] for r in db.execute('PRAGMA table_info(companies)')}:
        db.execute('ALTER TABLE companies ADD COLUMN agenda_hidden INTEGER NOT NULL DEFAULT 0')

def read(db):
    row=db.execute('SELECT revision,payload FROM carteira_document WHERE id=1').fetchone()
    if row:
        data=json.loads(row['payload'])
        linked=set()
        for c in data['companies']:
            record=db.execute('SELECT company_id FROM agenda_sources WHERE source_id=?',(agenda.source_key(c),)).fetchone()
            if record:linked.add(record['company_id'])
        base=agenda.backup(db)
        portfolios={p['name']:p for p in data.get('portfolios',[])}
        for p in base['portfolios']:
            if p['name'] not in portfolios:
                p['id']='fiscal-wallet:'+p['id'];data.setdefault('portfolios',[]).append(p);portfolios[p['name']]=p
        base_wallets={str(r['id']):r['name'] for r in db.execute('SELECT id,name FROM wallets')}
        for c in base['companies']:
            hidden=db.execute('SELECT agenda_hidden FROM companies WHERE id=?',(int(c['id']),)).fetchone()['agenda_hidden']
            if int(c['id']) not in linked and not hidden:
                wallet=portfolios.get(base_wallets.get(c['portfolioId']))
                c['portfolioId']=wallet['id'] if wallet else ''
                c['id']='fiscal-client:'+c['id']
                data['companies'].append(c)
        return {'revision':row['revision'],'state':data}
    data=agenda.backup(db)
    data['companies']=[c for c in data['companies'] if not db.execute('SELECT agenda_hidden FROM companies WHERE id=?',(int(c['id']),)).fetchone()['agenda_hidden']]
    data['recurring']={}
    return {'revision':0,'state':data}

def validate(data):
    if not isinstance(data,dict) or data.get('version')!=1:raise ValueError('Agenda incompatível')
    for name in ('companies','tasks','notes','portfolios'):
        if not isinstance(data.get(name,[]),list):raise ValueError('Lista inválida: '+name)
        ids=[x.get('id') for x in data.get(name,[]) if isinstance(x,dict)]
        if len(ids)!=len(data.get(name,[])) or any(not isinstance(i,str) or not i or len(i)>300 for i in ids) or len(set(ids))!=len(ids):raise ValueError('Identificadores inválidos: '+name)
    if len(data['companies'])>10000 or len(data['tasks'])>100000:raise ValueError('Limite de registros excedido')
    cids={c['id'] for c in data['companies']}
    pids={p['id'] for p in data.get('portfolios',[])}
    for c in data['companies']:
        if c.get('portfolioId') and c['portfolioId'] not in pids:raise ValueError('Carteira não encontrada')
    for kind in ('tasks','notes'):
        if any(x.get('company') not in cids for x in data.get(kind,[])):raise ValueError('Cliente não encontrado')
    for name in ('recurring','checkins','completions'):
        if not isinstance(data.get(name,{}),dict):raise ValueError('Dados inválidos: '+name)
    for key,s in data.get('recurring',{}).items():
        if not isinstance(s,dict) or s.get('id')!=key or s.get('company') not in cids or not isinstance(s.get('active'),bool):raise ValueError('Repetição mensal inválida')
        for field in ('startIndex','nextIndex','dueOffset','dueDay'):
            if type(s.get(field)) is not int:raise ValueError('Parâmetro de repetição inválido')
        if not 12000<=s['startIndex']<s['nextIndex']<=120000 or not 1<=s['dueDay']<=31 or abs(s['dueOffset'])>120:raise ValueError('Limites de repetição inválidos')
    return data

def save(db, data, revision, log):
    # Reserva a transação antes de comparar revisões de abas concorrentes.
    db.execute('UPDATE carteira_document SET revision=revision WHERE id=1')
    current=read(db)
    if revision!=current['revision']:raise Conflict('A agenda foi alterada em outra janela. Recarregue a página antes de continuar.')
    validate(data)
    data['format']='auditorfiscal-agenda-v1'
    old_portfolios={p['id']:p['name'] for p in current['state'].get('portfolios',[])}
    for p in data.get('portfolios',[]):
        old_name=old_portfolios.get(p['id'])
        if old_name and old_name!=p['name'] and not db.execute('SELECT 1 FROM wallets WHERE name=?',(p['name'],)).fetchone():
            db.execute('UPDATE wallets SET name=? WHERE name=?',(p['name'],old_name))
    # Guarda as projeções antigas até que a transação inteira seja validada.
    for table in ('agenda_tasks','agenda_notes','agenda_closures','agenda_checkins'):
        db.execute('DELETE FROM '+table)
    agenda.import_agenda(db,data,lambda *_:None)
    db.execute('UPDATE companies SET agenda_hidden=1')
    for c in data['companies']:
        key=agenda.source_key(c)
        linked=db.execute('SELECT company_id FROM agenda_sources WHERE source_id=?',(key,)).fetchone()
        cid=linked['company_id']
        p=next((p for p in data.get('portfolios',[]) if p['id']==c.get('portfolioId')),None)
        wid=db.execute('SELECT id FROM wallets WHERE name=?', (p['name'],)).fetchone()['id'] if p else None
        raw=agenda.clean_cnpj(c.get('cnpj'))
        regime={'SIMPLES':'Simples Nacional','REAL':'Lucro Real','PRESUMIDO':'Lucro Presumido','':'Não informado'}.get(c.get('regime') or '',c.get('regime'))
        review=[]
        if not agenda.valid_cnpj(raw):review.append('Conferir CNPJ original: '+str(c.get('cnpj') or ''))
        if regime=='Não informado':review.append('Informar regime tributário')
        db.execute('UPDATE companies SET name=?,cnpj=?,regime=?,wallet_id=?,contact=?,phone=?,email=?,fee=?,review=?,agenda_hidden=0 WHERE id=?',(c['nome'],raw or 'SEM-CNPJ:'+key,regime,wid,c.get('contact') or '',c.get('phone') or '',c.get('email') or '',str(c.get('fee') or ''),'; '.join(review),cid))
    new_revision=current['revision']+1
    db.execute('INSERT OR REPLACE INTO carteira_document(id,revision,payload) VALUES (1,?,?)',(new_revision,json.dumps(data,ensure_ascii=False)))
    log(db,f'Carteira salva, revisão {new_revision}: {len(data["companies"])} clientes, {len(data["tasks"])} tarefas')
    return {'revision':new_revision,'ok':True}

def import_html(db, content, revision, log):
    imported=agenda.parse_import(content)
    if imported['tasks'] or not content.lstrip().startswith('<'):raise ValueError('Para restaurar JSON, use Restaurar backup na própria carteira')
    current=read(db)
    if revision!=current['revision']:raise Conflict('Recarregue a carteira antes de importar')
    data=current['state'];added=0
    data.setdefault('portfolios',[])
    aliases={'Planilha Royal':'Carteira Royal','PDF fechamento setembro':'Terceirizados'}
    for c in imported['companies']:
        cnpj=agenda.clean_cnpj(c.get('cnpj'))
        if any(agenda.clean_cnpj(x.get('cnpj'))==cnpj for x in data['companies']):continue
        name=aliases.get(c.get('origem'),c.get('origem')) or 'Clientes próprios'
        portfolio=next((p for p in data['portfolios'] if p['name']==name),None)
        if not portfolio:
            portfolio={'id':str(uuid.uuid4()),'name':name};data['portfolios'].append(portfolio)
        c=dict(c,id=str(uuid.uuid4()),portfolioId=portfolio['id'])
        data['companies'].append(c);added+=1
    result=save(db,data,revision,log)
    result['clients_added']=added
    return result
