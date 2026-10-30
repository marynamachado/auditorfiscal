import json
import os
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent
DB = Path(os.environ.get('FISCAL_DB', str(ROOT / 'data' / 'fiscal.sqlite3')))

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS wallets(id INTEGER PRIMARY KEY, name TEXT NOT NULL, responsible TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY, cnpj TEXT UNIQUE NOT NULL, name TEXT NOT NULL, regime TEXT NOT NULL, cnae TEXT, ie TEXT, city TEXT, uf TEXT, wallet_id INTEGER REFERENCES wallets(id), icms_rate TEXT NOT NULL DEFAULT '18');
    CREATE TABLE IF NOT EXISTS periods(id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id), month TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0, UNIQUE(company_id,month));
    CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY, period_id INTEGER NOT NULL REFERENCES periods(id), access_key TEXT NOT NULL, number TEXT, issued TEXT, direction TEXT NOT NULL, total TEXT NOT NULL, icms TEXT NOT NULL, ipi TEXT NOT NULL, pis TEXT NOT NULL, cofins TEXT NOT NULL, xml TEXT NOT NULL, UNIQUE(period_id,access_key));
    CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices(id), product TEXT, ncm TEXT, cfop TEXT, cst TEXT, base TEXT, icms TEXT, ipi TEXT, pis TEXT, cofins TEXT);
    CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY, period_id INTEGER REFERENCES periods(id), message TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, created TEXT NOT NULL, action TEXT NOT NULL);
    ''')
    return db

def log(db, action):
    db.execute('INSERT INTO history(created,action) VALUES (?,?)', (datetime.now().isoformat(timespec='seconds'), action))

def digits(value):
    return ''.join(c for c in str(value) if c.isdigit())

def amount(value):
    try:
        n = Decimal(value or '0')
    except InvalidOperation:
        raise ValueError('Valor fiscal inválido') from None
    if not n.is_finite() or n < 0:
        raise ValueError('Valor fiscal inválido')
    return str(n)

def import_xml(db, period_id, xml):
    p = db.execute('SELECT p.*,c.cnpj FROM periods p JOIN companies c ON c.id=p.company_id WHERE p.id=?', (period_id,)).fetchone()
    if not p or p['closed']:
        raise ValueError('Selecione uma competência aberta')
    if len(xml.encode()) > 5_000_000 or '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
        raise ValueError('XML não permitido ou maior que 5 MB')
    root = ET.fromstring(xml)
    for node in root.iter():
        node.tag = node.tag.split('}')[-1]
    inf = root if root.tag == 'infNFe' else root.find('.//infNFe')
    if inf is None or inf.findtext('ide/mod') != '55':
        raise ValueError('Envie um XML de NF-e modelo 55')
    key = inf.get('Id', '').removeprefix('NFe')
    if len(key) != 44 or not key.isdigit():
        raise ValueError('Chave de acesso inválida')
    issuer, recipient = inf.findtext('emit/CNPJ'), inf.findtext('dest/CNPJ')
    if p['cnpj'] not in (issuer, recipient):
        raise ValueError('A NF-e não pertence à empresa selecionada')
    issued = inf.findtext('ide/dhEmi') or inf.findtext('ide/dEmi') or ''
    if issued[:7] != p['month']:
        raise ValueError('Data da NF-e fora da competência selecionada')
    direction = 'Saída' if issuer == p['cnpj'] else 'Entrada'
    if db.execute('SELECT 1 FROM invoices WHERE period_id=? AND access_key=?', (period_id,key)).fetchone():
        db.execute('INSERT INTO findings(period_id,message) VALUES (?,?)', (period_id, 'Importação duplicada bloqueada: '+key))
        log(db, 'Duplicidade bloqueada: '+key)
        return {'duplicate': True}
    totals = inf.find('total/ICMSTot')
    if totals is None:
        raise ValueError('Totais fiscais ausentes')
    values = [amount(totals.findtext(t)) for t in ('vNF','vICMS','vIPI','vPIS','vCOFINS')]
    cur = db.execute('INSERT INTO invoices(period_id,access_key,number,issued,direction,total,icms,ipi,pis,cofins,xml) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (period_id,key,inf.findtext('ide/nNF'),issued,direction,*values,xml))
    details = inf.findall('det')
    if not details:
        raise ValueError('NF-e sem itens')
    for det in details:
        def t(path): return det.findtext(path) or ''
        def tax(group,field): return det.findtext('imposto/'+group+'/*/'+field) or '0'
        cfop, ncm = t('prod/CFOP'), t('prod/NCM')
        cst = det.findtext('imposto/ICMS/*/CST') or det.findtext('imposto/ICMS/*/CSOSN') or ''
        vals = [amount(tax(g,f)) for g,f in [('ICMS','vBC'),('ICMS','vICMS'),('IPI','vIPI'),('PIS','vPIS'),('COFINS','vCOFINS')]]
        db.execute('INSERT INTO items(invoice_id,product,ncm,cfop,cst,base,icms,ipi,pis,cofins) VALUES (?,?,?,?,?,?,?,?,?,?)', (cur.lastrowid,t('prod/xProd'),ncm,cfop,cst,*vals))
        issues = []
        if len(ncm)!=8: issues.append('NCM ausente ou inválido')
        if len(cfop)!=4: issues.append('CFOP ausente ou inválido')
        if not cst: issues.append('CST/CSOSN ausente')
        if issuer == p['cnpj'] and cfop[:1] not in ('5','6','7'): issues.append('CFOP incompatível com saída do emitente')
        for issue in issues:
            db.execute('INSERT INTO findings(period_id,message) VALUES (?,?)', (period_id, f'NF {inf.findtext("ide/nNF")}: {issue}'))
    log(db, f'NF-e {key} importada: {direction}')
    return {'imported': True}

def mutate(db, action, data):
    if action == 'wallet':
        if not data.get('name','').strip() or not data.get('responsible','').strip(): raise ValueError('Informe nome e responsável')
        if data.get('id'):
            db.execute('UPDATE wallets SET name=?,responsible=? WHERE id=?',(data['name'],data['responsible'],data['id']))
        else: db.execute('INSERT INTO wallets(name,responsible) VALUES (?,?)',(data['name'],data['responsible']))
    elif action == 'delete_wallet':
        db.execute('DELETE FROM wallets WHERE id=?',(data['id'],))
    elif action == 'company':
        cnpj = digits(data.get('cnpj',''))
        if len(cnpj)!=14 or len(set(cnpj))==1: raise ValueError('Informe um CNPJ com 14 dígitos')
        for length in (12,13):
            weights = list(range(length-7,1,-1))+list(range(9,1,-1))
            digit = (sum(int(a)*b for a,b in zip(cnpj[:length],weights))*10)%11
            if int(cnpj[length]) != (0 if digit==10 else digit): raise ValueError('Dígitos verificadores do CNPJ inválidos')
        if not data.get('name','').strip() or data.get('regime') not in ('Normal','Simples Nacional'): raise ValueError('Nome ou regime inválido')
        rate = Decimal(amount(data.get('icms_rate','18')))
        if rate>100: raise ValueError('Alíquota deve estar entre 0 e 100')
        db.execute('INSERT INTO companies(cnpj,name,regime,cnae,ie,city,uf,wallet_id,icms_rate) VALUES (?,?,?,?,?,?,?,?,?)',(cnpj,data['name'],data['regime'],data.get('cnae'),data.get('ie'),data.get('city'),data.get('uf'),data.get('wallet_id') or None,str(rate)))
    elif action == 'period':
        month = data['month']
        if datetime.strptime(month,'%Y-%m').strftime('%Y-%m') != month: raise ValueError('Competência inválida')
        db.execute('INSERT INTO periods(company_id,month) VALUES (?,?)',(data['company_id'],month))
    elif action == 'close':
        p = db.execute('SELECT * FROM periods WHERE id=?',(data['id'],)).fetchone()
        if not p or p['closed']: raise ValueError('Competência já fechada ou inexistente')
        if db.execute('SELECT 1 FROM findings WHERE period_id=?',(data['id'],)).fetchone(): raise ValueError('Existem alertas de auditoria; fechamento bloqueado')
        if not db.execute('SELECT 1 FROM invoices WHERE period_id=?',(data['id'],)).fetchone(): raise ValueError('Importe e confira as notas antes de fechar')
        db.execute('UPDATE periods SET closed=1 WHERE id=?',(data['id'],))
    elif action == 'import': return import_xml(db,int(data['period_id']),data['xml'])
    else: raise ValueError('Operação desconhecida')
    log(db, action+': '+json.dumps(data,ensure_ascii=False))
    return {'ok':True}

def state(db):
    result = {name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in ('wallets','companies','periods','items','findings','history')}
    result['invoices'] = [dict(r) for r in db.execute('SELECT id,period_id,access_key,number,issued,direction,total,icms,ipi,pis,cofins FROM invoices')]
    settlements = []
    for p in result['periods']:
        notes = [n for n in result['invoices'] if n['period_id']==p['id']]
        debit = sum((Decimal(n['icms']) for n in notes if n['direction']=='Saída'),Decimal(0))
        credit = sum((Decimal(n['icms']) for n in notes if n['direction']=='Entrada'),Decimal(0))
        settlements.append({'period_id':p['id'],'debit':str(debit),'potential_credit':str(credit),'balance':str(max(debit-credit,Decimal(0)))})
    result['settlements']=settlements
    return result

class Handler(BaseHTTPRequestHandler):
    def respond(self, code, body, kind='application/json; charset=utf-8'):
        raw = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/api/state':
            with connect() as db: self.respond(200,state(db))
        elif self.path in ('/','/style.css','/app.js'):
            name = 'index.html' if self.path=='/' else self.path[1:]
            kind = {'html':'text/html','css':'text/css','js':'text/javascript'}[name.split('.')[-1]]
            self.respond(200,(ROOT/'static'/name).read_bytes(),kind+'; charset=utf-8')
        else: self.respond(404,{'error':'Não encontrado'})

    def do_POST(self):
        if self.headers.get('Origin') and self.headers['Origin'] != 'http://'+self.headers.get('Host',''):
            return self.respond(403,{'error':'Origem não permitida'})
        try:
            size = int(self.headers.get('Content-Length','0'))
            if size>6_000_000: raise ValueError('Arquivo muito grande')
            data = json.loads(self.rfile.read(size))
            with connect() as db: result = mutate(db,self.path.removeprefix('/api/'),data)
            self.respond(200,result)
        except (ValueError,KeyError,ET.ParseError,sqlite3.IntegrityError) as e:
            self.respond(400,{'error':str(e)})

if __name__=='__main__':
    with connect(): pass
    print('Auditor Fiscal iniciado. Abra http://127.0.0.1:8000',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
