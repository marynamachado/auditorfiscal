"""Agenda persistida no SQLite; importação de dados sem executar HTML/JavaScript."""
import calendar
from datetime import date, datetime
import hashlib
import json
import re
import uuid

def migrate(db):
    columns = {r['name'] for r in db.execute('PRAGMA table_info(companies)')}
    for name in ('contact', 'phone', 'email', 'fee', 'source', 'review'):
        if name not in columns:
            db.execute(f"ALTER TABLE companies ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
    db.executescript('''
    CREATE TABLE IF NOT EXISTS agenda_tasks(id TEXT PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id), title TEXT NOT NULL, month TEXT NOT NULL DEFAULT '', due TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Pendente', priority TEXT NOT NULL DEFAULT 'Normal', notes TEXT NOT NULL DEFAULT '', checks TEXT NOT NULL DEFAULT '[]');
    CREATE TABLE IF NOT EXISTS agenda_notes(id TEXT PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id), text TEXT NOT NULL, color TEXT NOT NULL DEFAULT 'yellow');
    CREATE TABLE IF NOT EXISTS agenda_closures(company_id INTEGER NOT NULL REFERENCES companies(id), month TEXT NOT NULL, marked_at TEXT NOT NULL, PRIMARY KEY(company_id,month));
    CREATE TABLE IF NOT EXISTS agenda_checkins(day TEXT NOT NULL, item INTEGER NOT NULL, done INTEGER NOT NULL, PRIMARY KEY(day,item));
    CREATE TABLE IF NOT EXISTS agenda_sources(source_id TEXT PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id));
    ''')

def clean_cnpj(value):
    return re.sub(r'\D', '', str(value or ''))

def valid_cnpj(value):
    if len(value) != 14 or len(set(value)) == 1: return False
    for length in (12, 13):
        weights = list(range(length - 7, 1, -1)) + list(range(9, 1, -1))
        digit = sum(int(a) * b for a, b in zip(value[:length], weights)) * 10 % 11
        if int(value[length]) != (0 if digit == 10 else digit): return False
    return True

def text(value, limit=2000):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError('Texto inválido ou maior que o permitido')
    return value.strip()

def month(value, optional=False):
    if optional and value == '': return value
    value = text(value, 7)
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value) or int(value[:4]) < 1900:
        raise ValueError('Competência inválida')
    return value

def day(value, optional=False):
    if optional and value == '': return value
    if date.fromisoformat(value).isoformat() != value: raise ValueError('Data inválida')
    return value

def source_key(c):
    if c.get('source_key'): return text(c['source_key'],300)
    return 'legacy:' + str(c.get('id') or hashlib.sha256((clean_cnpj(c.get('cnpj'))+'|'+str(c.get('nome'))).encode()).hexdigest())

def parse_import(content):
    if not isinstance(content,str) or len(content.encode()) > 5_000_000: raise ValueError('Arquivo maior que 5 MB')
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Extrai somente o literal JSON do modelo conhecido, nunca executa scripts.
        marker = re.search(r'else\s*\{\s*let\s+c\s*=\s*',content)
        if not marker: raise ValueError('Envie o HTML da Carteira do Danillo ou seu backup JSON') from None
        try: companies, _ = json.JSONDecoder().raw_decode(content[marker.end():])
        except json.JSONDecodeError: raise ValueError('Lista de clientes do HTML inválida') from None
        data = {'version':1,'companies':companies,'tasks':[]}
    if not isinstance(data,dict) or data.get('version') != 1 or not isinstance(data.get('companies'),list) or not isinstance(data.get('tasks'),list):
        raise ValueError('Backup de agenda incompatível')
    if len(data['companies']) > 10000 or len(data['tasks']) > 100000: raise ValueError('Muitos registros')
    return data

def import_agenda(db, data, log):
    wallets = {}
    for p in data.get('portfolios',[]):
        name = text(p['name'],1000)
        if not name: raise ValueError('Carteira sem nome')
        wallets[text(p['id'])] = name
        if not db.execute('SELECT 1 FROM wallets WHERE name=?',(name,)).fetchone():
            db.execute('INSERT INTO wallets(name,responsible) VALUES (?,?)',(name,text(p.get('responsible') or 'Danillo')))
    aliases = {'Planilha Royal':'Carteira Royal','PDF fechamento setembro':'Terceirizados','Cadastro manual':'Clientes próprios'}
    regimes = {'SIMPLES':'Simples Nacional','PRESUMIDO':'Lucro Presumido','REAL':'Lucro Real','MEI':'MEI','':'Não informado'}
    mapping = {}
    added = 0
    reviews = 0
    for c in data['companies']:
        name = text(c.get('nome',''),500)
        if not name: raise ValueError('Cliente sem nome')
        key = source_key(c)
        cnpj = clean_cnpj(c.get('cnpj'))
        # Não inventa dígitos nem atribui regime a cadastros incompletos.
        review = []
        if not valid_cnpj(cnpj): review.append('Conferir CNPJ original: '+str(c.get('cnpj','')))
        regime = text(c.get('regime') or '',100)
        if not regime or regime == 'Não informado': review.append('Informar regime tributário')
        office = wallets.get(c.get('portfolioId')) or c.get('grupo') or aliases.get(c.get('origem'), c.get('origem')) or 'Clientes próprios'
        office = text(office,1000)
        w = db.execute('SELECT id FROM wallets WHERE name=?',(office,)).fetchone()
        wid = w['id'] if w else db.execute('INSERT INTO wallets(name,responsible) VALUES (?,?)',(office,'Danillo')).lastrowid
        existing = db.execute('SELECT company_id FROM agenda_sources WHERE source_id=?',(key,)).fetchone()
        if not existing and cnpj: existing = db.execute('SELECT id AS company_id FROM companies WHERE cnpj=?',(cnpj,)).fetchone()
        if existing:
            cid = existing['company_id']
        else:
            cid = db.execute('''INSERT INTO companies(cnpj,name,regime,wallet_id,contact,phone,email,fee,source,review)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',(cnpj or 'SEM-CNPJ:'+key,name,regimes.get(regime,regime),wid,text(c.get('contact') or ''),text(c.get('phone') or ''),text(c.get('email') or ''),str(c.get('fee') or ''),text(c.get('origem') or 'Backup da agenda'),'; '.join(review))).lastrowid
            added += 1
            reviews += bool(review)
        db.execute('INSERT OR IGNORE INTO agenda_sources(source_id,company_id) VALUES (?,?)',(key,cid))
        if c.get('id'):
            if c['id'] in mapping: raise ValueError('Identificador de cliente duplicado')
            mapping[c['id']] = cid
    def cid_for(record):
        cid = mapping.get(record.get('company'))
        if cid is None: raise ValueError('Tarefa ou anotação sem cliente correspondente')
        return cid
    tasks = notes = 0
    for t in data['tasks']:
        cid = cid_for(t)
        tid = ('' if data.get('format') == 'auditorfiscal-agenda-v1' else 'legacy:')+text(t['id'],200)
        title = text(t['title'],500)
        status = t.get('status','Pendente')
        if not title or status not in ('Pendente','Aguardando','Finalizada','Concluída'): raise ValueError('Tarefa inválida')
        checks = t.get('checks',[])
        if not isinstance(checks,list) or any(not isinstance(x,dict) or not isinstance(x.get('done'),bool) or not isinstance(x.get('text'),str) for x in checks): raise ValueError('Checklist inválido')
        tasks += db.execute('INSERT OR IGNORE INTO agenda_tasks(id,company_id,title,month,due,status,priority,notes,checks) VALUES (?,?,?,?,?,?,?,?,?)',(tid,cid,title,month(t.get('period') or '',True),day(t.get('due') or '',True),status,text(t.get('priority') or 'Normal'),text(t.get('notes') or '',100000),json.dumps(checks,ensure_ascii=False))).rowcount
    for n in data.get('notes',[]):
        nid = ('' if data.get('format') == 'auditorfiscal-agenda-v1' else 'legacy:')+text(n['id'],200)
        notes += db.execute('INSERT OR IGNORE INTO agenda_notes(id,company_id,text,color) VALUES (?,?,?,?)',(nid,cid_for(n),text(n['text']),text(n.get('color') or 'yellow',20))).rowcount
    for key, v in data.get('completions',{}).items():
        ident, m = key.rsplit('|',1)
        if ident not in mapping: raise ValueError('Conclusão sem cliente correspondente')
        db.execute('INSERT OR IGNORE INTO agenda_closures(company_id,month,marked_at) VALUES (?,?,?)',(mapping[ident],month(m),text(v['markedAt'],100)))
    for d, values in data.get('checkins',{}).items():
        day(d)
        if not isinstance(values,list) or any(x is not None and not isinstance(x,bool) for x in values): raise ValueError('Check-in inválido')
        for i, done in enumerate(values[:4]): db.execute('INSERT OR IGNORE INTO agenda_checkins(day,item,done) VALUES (?,?,?)',(d,i,int(bool(done))))
    log(db,f'Importação da agenda: {added} clientes, {tasks} tarefas e {notes} anotações adicionados; {reviews} cadastros para revisão')
    return {'ok':True,'clients_added':added,'tasks_added':tasks,'notes_added':notes,'review':reviews,'recurring_templates':len(data.get('recurring',{}))}

def company_exists(db, cid):
    if not db.execute('SELECT 1 FROM companies WHERE id=?',(cid,)).fetchone(): raise ValueError('Empresa não encontrada')

def mutate(db, action, data, log):
    if action == 'agenda_import':
        try: return import_agenda(db,parse_import(data['content']),log)
        except (KeyError,TypeError,AttributeError,IndexError): raise ValueError('Estrutura do arquivo da agenda inválida') from None
    if action == 'agenda_company':
        cid = int(data['company_id']); company_exists(db,cid)
        cnpj = clean_cnpj(data['cnpj'])
        if not valid_cnpj(cnpj): raise ValueError('CNPJ inválido; confira o documento original')
        name = text(data['name'],500)
        regime = data['regime']
        if not name or regime not in ('Normal','Simples Nacional','Lucro Real','Lucro Presumido','MEI'): raise ValueError('Informe nome e regime tributário válido')
        db.execute('UPDATE companies SET name=?,cnpj=?,regime=?,review=? WHERE id=?',(name,cnpj,regime,'',cid))
    elif action == 'agenda_task':
        cid = int(data['company_id'])
        company_exists(db,cid)
        title = text(data['title'],500)
        if not title: raise ValueError('Informe a tarefa')
        m, due = month(data.get('month',''),True),day(data.get('due',''),True)
        status = data.get('status','Pendente')
        if status not in ('Pendente','Aguardando','Finalizada','Concluída'): raise ValueError('Situação inválida')
        priority = data.get('priority','Normal')
        if priority not in ('Normal','Alta','Baixa'): raise ValueError('Prioridade inválida')
        repeat = int(data.get('repeat') or 1)
        if not 1 <= repeat <= 12: raise ValueError('Repetição deve ser entre 1 e 12 meses')
        if repeat > 1 and (not m or not due or data.get('id')): raise ValueError('Repetição exige nova tarefa, competência e prazo')
        notes = text(data.get('notes',''),100000)
        old = None
        if data.get('id'):
            old = db.execute('SELECT * FROM agenda_tasks WHERE id=?',(data['id'],)).fetchone()
            if not old: raise ValueError('Tarefa não encontrada')
        for i in range(repeat):
            def advance(value):
                base = date.fromisoformat(value+'-01' if len(value)==7 else value)
                n = base.year*12+base.month-1+i
                y, mo = divmod(n,12)
                return date(y,mo+1,min(base.day,calendar.monthrange(y,mo+1)[1])).isoformat()
            mm = advance(m)[:7] if i else m
            dd = advance(due) if i else due
            if old:
                db.execute('UPDATE agenda_tasks SET company_id=?,title=?,month=?,due=?,status=?,priority=?,notes=? WHERE id=?',(cid,title,mm,dd,status,priority,notes,old['id']))
                db.execute('DELETE FROM agenda_closures WHERE company_id=? AND month=?',(old['company_id'],old['month']))
            else: db.execute('INSERT INTO agenda_tasks(id,company_id,title,month,due,status,priority,notes) VALUES (?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),cid,title,mm,dd,status,priority,notes))
            db.execute('DELETE FROM agenda_closures WHERE company_id=? AND month=?',(cid,mm))
    elif action == 'agenda_status':
        t = db.execute('SELECT * FROM agenda_tasks WHERE id=?',(data['id'],)).fetchone()
        if not t: raise ValueError('Tarefa não encontrada')
        status = data['status']
        if status not in ('Pendente','Aguardando','Finalizada'): raise ValueError('Situação inválida')
        db.execute('UPDATE agenda_tasks SET status=? WHERE id=?',(status,t['id']))
        if status != 'Finalizada': db.execute('DELETE FROM agenda_closures WHERE company_id=? AND month=?',(t['company_id'],t['month']))
    elif action == 'agenda_note':
        cid = int(data['company_id']); company_exists(db,cid)
        content = text(data['text'])
        if not content: raise ValueError('Informe a anotação')
        color = data.get('color','yellow')
        if color not in ('yellow','pink','blue','green'): raise ValueError('Cor inválida')
        db.execute('INSERT INTO agenda_notes(id,company_id,text,color) VALUES (?,?,?,?)',(str(uuid.uuid4()),cid,content,color))
    elif action == 'agenda_delete_note':
        db.execute('DELETE FROM agenda_notes WHERE id=?',(data['id'],))
    elif action == 'agenda_close':
        cid = int(data['company_id']); company_exists(db,cid)
        m = month(data['month'])
        if db.execute("SELECT 1 FROM agenda_tasks WHERE company_id=? AND month=? AND status NOT IN ('Finalizada','Concluída')",(cid,m)).fetchone(): raise ValueError('Finalize as tarefas do mês antes de concluir o trabalho')
        db.execute('INSERT OR REPLACE INTO agenda_closures(company_id,month,marked_at) VALUES (?,?,?)',(cid,m,datetime.now().isoformat(timespec='seconds')))
    elif action == 'agenda_reopen':
        db.execute('DELETE FROM agenda_closures WHERE company_id=? AND month=?',(int(data['company_id']),month(data['month'])))
    elif action == 'agenda_checkin':
        d, item = day(data['day']),int(data['item'])
        if not 0 <= item < 4 or not isinstance(data['done'],bool): raise ValueError('Check-in inválido')
        db.execute('INSERT OR REPLACE INTO agenda_checkins(day,item,done) VALUES (?,?,?)',(d,item,int(data['done'])))
    elif action == 'agenda_contact':
        cid = int(data['company_id']); company_exists(db,cid)
        wallet_id = int(data['wallet_id'])
        if not db.execute('SELECT 1 FROM wallets WHERE id=?',(wallet_id,)).fetchone(): raise ValueError('Carteira inválida')
        fee = data.get('fee','')
        if fee != '':
            from decimal import Decimal, InvalidOperation
            try: value = Decimal(str(fee))
            except InvalidOperation: raise ValueError('Honorário inválido') from None
            if not value.is_finite() or value<0: raise ValueError('Honorário inválido')
            fee = str(value)
        db.execute('UPDATE companies SET contact=?,phone=?,email=?,fee=?,wallet_id=? WHERE id=?',(text(data.get('contact','')),text(data.get('phone','')),text(data.get('email','')),fee,wallet_id,cid))
    else: raise ValueError('Operação desconhecida')
    log(db,action+': '+json.dumps(data,ensure_ascii=False))
    return {'ok':True}

def state(db):
    return {name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in ('agenda_tasks','agenda_notes','agenda_closures','agenda_checkins')}

def backup(db):
    data = {'version':1,'format':'auditorfiscal-agenda-v1','companies':[],'tasks':[],'notes':[],'portfolios':[],'completions':{},'checkins':{}}
    for w in db.execute('SELECT * FROM wallets'):
        data['portfolios'].append({'id':str(w['id']),'name':w['name'],'responsible':w['responsible']})
    for c in db.execute('SELECT * FROM companies'):
        source = db.execute('SELECT source_id FROM agenda_sources WHERE company_id=? ORDER BY source_id LIMIT 1',(c['id'],)).fetchone()
        data['companies'].append({'id':str(c['id']),'nome':c['name'],'cnpj':c['cnpj'],'regime':c['regime'],'portfolioId':str(c['wallet_id']) if c['wallet_id'] else '', 'contact':c['contact'],'phone':c['phone'],'email':c['email'],'fee':c['fee'],'origem':c['source'],'source_key':source['source_id'] if source else 'fiscal:'+str(c['id'])})
    for t in db.execute('SELECT * FROM agenda_tasks'):
        task = dict(t)
        task['company'] = str(task.pop('company_id'))
        task['period'] = task.pop('month')
        task['checks'] = json.loads(task['checks'])
        data['tasks'].append(task)
    for n in db.execute('SELECT * FROM agenda_notes'):
        note = dict(n); note['company']=str(note.pop('company_id'))
        data['notes'].append(note)
    for c in db.execute('SELECT * FROM agenda_closures'):
        data['completions'][str(c['company_id'])+'|'+c['month']]={'markedAt':c['marked_at']}
    for c in db.execute('SELECT * FROM agenda_checkins'):
        values=data['checkins'].setdefault(c['day'],[False]*4)
        values[c['item']]=bool(c['done'])
    return data
