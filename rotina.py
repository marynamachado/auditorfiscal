"""Cadastros e organização da rotina fiscal; não emite nem transmite documentos."""
import json
from datetime import date, datetime
import agenda

REGIMES=('Normal','Lucro Real','Lucro Presumido','Simples Nacional','MEI')
OBLIGATIONS=('EFD ICMS/IPI','EFD Contribuições','DCTFWeb/MIT','EFD-Reinf','DEFIS','DAS','DARF','ICMS/GO','ISS municipal','Outra obrigação')
TABLES=('routine_profiles','routine_catalog','routine_classifications','routine_obligations')

def migrate(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS routine_profiles(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL REFERENCES companies(id),valid_from TEXT NOT NULL,regime TEXT NOT NULL,accountant TEXT NOT NULL,crc TEXT NOT NULL,crc_uf TEXT NOT NULL,address TEXT NOT NULL,partners TEXT NOT NULL,notes TEXT NOT NULL,source TEXT NOT NULL,prepared_by TEXT NOT NULL,created TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS routine_profiles_company ON routine_profiles(company_id,valid_from,id);
    CREATE TABLE IF NOT EXISTS routine_catalog(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL REFERENCES companies(id),kind TEXT NOT NULL,code TEXT NOT NULL,name TEXT NOT NULL,payload TEXT NOT NULL,source TEXT NOT NULL,prepared_by TEXT NOT NULL,created TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS routine_catalog_code ON routine_catalog(company_id,kind,code,id);
    CREATE TABLE IF NOT EXISTS routine_classifications(id INTEGER PRIMARY KEY,invoice_id INTEGER NOT NULL REFERENCES invoices(id),accumulator_id INTEGER NOT NULL REFERENCES routine_catalog(id),reason TEXT NOT NULL,prepared_by TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS routine_obligations(id INTEGER PRIMARY KEY,period_id INTEGER NOT NULL REFERENCES periods(id),obligation TEXT NOT NULL,status TEXT NOT NULL,due TEXT NOT NULL,evidence TEXT NOT NULL,prepared_by TEXT NOT NULL,created TEXT NOT NULL);
    ''')

def text(value,label,required=True,limit=2000):
    value=agenda.text(value or '',limit)
    if required and not value:raise ValueError('Informe '+label)
    return value

def choice(value,allowed,label):
    if value not in allowed:raise ValueError(label+' inválido')
    return value

def company(db,ident):
    row=db.execute('SELECT * FROM companies WHERE id=?',(int(ident),)).fetchone()
    if not row:raise ValueError('Empresa inexistente')
    return row

def current_catalog(db,cid,kind=None):
    rows=[dict(r) for r in db.execute('SELECT * FROM routine_catalog WHERE company_id=? ORDER BY id',(cid,))]
    latest={}
    for row in rows:
        if kind is None or row['kind']==kind:latest[(row['kind'],row['code'])]=row
    return list(latest.values())

def tax_snapshot(db,cid,month,pid):
    profile=db.execute('SELECT * FROM routine_profiles WHERE company_id=? AND valid_from<=? ORDER BY valid_from DESC,id DESC LIMIT 1',(cid,month)).fetchone()
    assignments=[dict(r) for r in db.execute('''SELECT c.* FROM routine_classifications c JOIN invoices n ON n.id=c.invoice_id WHERE n.period_id=? AND c.id=(SELECT MAX(x.id) FROM routine_classifications x WHERE x.invoice_id=c.invoice_id) ORDER BY c.invoice_id''',(pid,))]
    ids={r['accumulator_id'] for r in assignments}
    accumulators=[dict(r) for r in db.execute("SELECT * FROM routine_catalog WHERE company_id=? AND kind='accumulator' ORDER BY id",(cid,)) if r['id'] in ids]
    return {'profile':dict(profile) if profile else None,'classifications':assignments,'accumulators':accumulators}

def mutate(db,action,data,log):
    # Lock before checking period or creating a version, serializing against closure.
    db.execute('UPDATE periods SET closed=closed WHERE id=?',(data.get('period_id',-1),))
    now=datetime.now().isoformat(timespec='seconds')
    preparer=text(data.get('prepared_by'),'o responsável informado',limit=160)
    if action in ('routine_profile','routine_catalog'):
        c=company(db,data['company_id']);cid=c['id']
        source=text(data.get('source'),'a referência conferida')
        if action=='routine_profile':
            start=agenda.month(data.get('valid_from',''))
            if db.execute('SELECT 1 FROM periods WHERE company_id=? AND closed=1 AND month>=?',(cid,start)).fetchone():raise ValueError('Esta vigência alcança competência fechada; registre uma vigência posterior ao último fechamento')
            regime=choice(data.get('regime'),REGIMES,'Regime')
            if regime!=c['regime']:raise ValueError('O regime da vigência deve coincidir com o cadastro atual da empresa; mudanças de regime exigem revisão específica ainda não implementada')
            partners=text(data.get('partners'),'os sócios',False,4000)
            db.execute('INSERT INTO routine_profiles(company_id,valid_from,regime,accountant,crc,crc_uf,address,partners,notes,source,prepared_by,created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(cid,start,regime,text(data.get('accountant'),'o contador',limit=160),text(data.get('crc'),'o CRC',limit=40),choice(data.get('crc_uf'),('GO','AC','AL','AP','AM','BA','CE','DF','ES','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'),'UF do CRC'),text(data.get('address'),'o endereço conferido',limit=500),partners,text(data.get('notes'),'as observações',False,4000),source,preparer,now))
        else:
            kind=choice(data.get('kind'),('accumulator','product','third_party'),'Tipo de cadastro')
            code=text(data.get('code'),'o código',limit=50);name=text(data.get('name'),'a descrição',limit=200)
            if kind=='accumulator':
                taxes=data.get('taxes','')
                if not isinstance(taxes,str):raise ValueError('Lista de tributos inválida')
                taxes=[v.strip().upper() for v in taxes.split(',') if v.strip()]
                if any(t not in ('ICMS','IPI','PIS','COFINS','ISS','RETENCOES') for t in taxes):raise ValueError('Use ICMS, IPI, PIS, COFINS, ISS ou RETENCOES separados por vírgula')
                cfop=text(data.get('cfop'),'o CFOP',False,4)
                if cfop and (not cfop.isascii() or not cfop.isdigit() or len(cfop)!=4):raise ValueError('CFOP deve ter quatro dígitos')
                payload={'direction':choice(data.get('direction'),('Entrada','Saída'),'Operação'),'treatment':choice(data.get('treatment'),('A conferir','Tributada','Isenta','Não tributada','Substituição tributária','Mista'),'Tratamento'),'stock':choice(data.get('stock'),('A conferir','Sim','Não'),'Estoque'),'accounting':choice(data.get('accounting'),('A conferir','Sim','Não'),'Reflexo contábil'),'taxes':taxes,'cfop':cfop}
            elif kind=='product':
                ncm=text(data.get('ncm'),'o NCM',False,8)
                if ncm and (not ncm.isascii() or not ncm.isdigit() or len(ncm)!=8):raise ValueError('NCM deve ter oito dígitos; para serviços deixe em branco')
                payload={'item_type':choice(data.get('item_type'),('Produto','Serviço'),'Tipo de item'),'ncm':ncm,'unit':text(data.get('unit'),'a unidade',False,20),'notes':text(data.get('notes'),'as observações',False)}
            else:
                cnpj=agenda.clean_cnpj(data.get('cnpj',''))
                if not agenda.valid_cnpj(cnpj):raise ValueError('Informe um CNPJ válido para o terceiro; cadastro por CPF ainda não disponível')
                payload={'role':choice(data.get('role'),('Cliente','Fornecedor','Cliente e fornecedor'),'Papel'),'cnpj':cnpj,'city':text(data.get('city'),'o município',False,120),'uf':text(data.get('uf'),'a UF',False,2)}
            db.execute('INSERT INTO routine_catalog(company_id,kind,code,name,payload,source,prepared_by,created) VALUES (?,?,?,?,?,?,?,?)',(cid,kind,code,name,json.dumps(payload,ensure_ascii=False),source,preparer,now))
    elif action=='routine_classify':
        invoice=db.execute('SELECT n.*,p.company_id,p.closed FROM invoices n JOIN periods p ON p.id=n.period_id WHERE n.id=?',(int(data['invoice_id']),)).fetchone()
        if not invoice or invoice['closed']:raise ValueError('Escolha uma nota de competência aberta')
        # Acquire a write lock before rechecking above, even if no period_id supplied.
        accumulator=db.execute("SELECT * FROM routine_catalog WHERE id=? AND kind='accumulator' AND company_id=?",(int(data['accumulator_id']),invoice['company_id'])).fetchone()
        if not accumulator:raise ValueError('Acumulador não pertence à empresa da nota')
        if json.loads(accumulator['payload'])['direction']!=invoice['direction']:raise ValueError('Operação do acumulador incompatível com a nota')
        if not any(r['id']==accumulator['id'] for r in current_catalog(db,invoice['company_id'],'accumulator')):raise ValueError('Escolha a versão atual do acumulador')
        db.execute('INSERT INTO routine_classifications(invoice_id,accumulator_id,reason,prepared_by,created) VALUES (?,?,?,?,?)',(invoice['id'],accumulator['id'],text(data.get('reason'),'a justificativa da classificação'),preparer,now))
    elif action=='routine_obligation':
        pid=int(data['period_id'])
        if not db.execute('SELECT 1 FROM periods WHERE id=?',(pid,)).fetchone():raise ValueError('Competência inexistente')
        obligation=choice(data.get('obligation'),OBLIGATIONS,'Obrigação')
        status=choice(data.get('status'),('Pendente','Preparado externamente','Validado externamente','Transmitido externamente','Não se aplica'),'Situação')
        due=agenda.day(data.get('due',''),optional=True)
        if due and not 1900<=date.fromisoformat(due).year<=9999:raise ValueError('Data inválida')
        evidence=text(data.get('evidence'),'a referência ou justificativa',status!='Pendente')
        db.execute('INSERT INTO routine_obligations(period_id,obligation,status,due,evidence,prepared_by,created) VALUES (?,?,?,?,?,?,?)',(pid,obligation,status,due,evidence,preparer,now))
    else:raise ValueError('Operação da rotina desconhecida')
    # IDs/reference metadata only: avoid duplicating partners and addresses in freeform history.
    log(db,action+' · responsável informado: '+preparer)
    return {'ok':True}

def state(db):
    return {table:[dict(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY id')] for table in TABLES}
