"""Piloto de apuração assistida. Não contém alíquotas legais pré-aprovadas.

Calcula lançamentos declarados com regras versionadas e exige confronto com um
caso externo. Isso não equivale a homologação fiscal ou auditoria independente.
"""
import hashlib
import json
import rotina
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_DOWN
import xml.etree.ElementTree as ET
from agenda import valid_cnpj

CITIES=('Goiânia','Trindade','Aparecida de Goiânia')
TAXES=('ICMS','PIS','COFINS','IPI','ISS')
REFERENCE_TAXES=TAXES+('DAS',)
KINDS=('debito','credito','ajuste_debito','ajuste_credito','saldo_anterior')

def migrate(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS fiscal_cases(id INTEGER PRIMARY KEY,period_id INTEGER NOT NULL REFERENCES periods(id),regime TEXT NOT NULL,municipality TEXT NOT NULL,source TEXT NOT NULL,expected TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS fiscal_rules(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL REFERENCES companies(id),tax TEXT NOT NULL,name TEXT NOT NULL,rate TEXT NOT NULL,rounding TEXT NOT NULL,valid_from TEXT NOT NULL,valid_to TEXT NOT NULL,regime TEXT NOT NULL,municipality TEXT NOT NULL,legal_basis TEXT NOT NULL,prepared_by TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS fiscal_entries(id INTEGER PRIMARY KEY,period_id INTEGER NOT NULL REFERENCES periods(id),tax TEXT NOT NULL,kind TEXT NOT NULL,rule_id INTEGER REFERENCES fiscal_rules(id),invoice_id INTEGER REFERENCES invoices(id),base TEXT NOT NULL,amount TEXT NOT NULL,reason TEXT NOT NULL,evidence TEXT NOT NULL,prepared_by TEXT NOT NULL,reversal_of INTEGER UNIQUE REFERENCES fiscal_entries(id),created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS fiscal_events(id INTEGER PRIMARY KEY,period_id INTEGER NOT NULL REFERENCES periods(id),invoice_id INTEGER NOT NULL REFERENCES invoices(id),digest TEXT NOT NULL UNIQUE,protocol TEXT NOT NULL,response_code TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pendente',raw TEXT NOT NULL,reviewer TEXT NOT NULL DEFAULT '',evidence TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,reviewed_at TEXT NOT NULL DEFAULT '',revision INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS fiscal_reviews(id INTEGER PRIMARY KEY,case_id INTEGER NOT NULL REFERENCES fiscal_cases(id),snapshot TEXT NOT NULL,reviewer TEXT NOT NULL,notes TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS fiscal_finding_reviews(id INTEGER PRIMARY KEY,finding_id INTEGER NOT NULL UNIQUE REFERENCES findings(id),reviewer TEXT NOT NULL,evidence TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS fiscal_closures(id INTEGER PRIMARY KEY,period_id INTEGER NOT NULL UNIQUE REFERENCES periods(id),case_id INTEGER NOT NULL REFERENCES fiscal_cases(id),report TEXT NOT NULL,created TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS fiscal_entries_period ON fiscal_entries(period_id);
    CREATE INDEX IF NOT EXISTS fiscal_cases_period ON fiscal_cases(period_id);
    CREATE INDEX IF NOT EXISTS fiscal_events_invoice ON fiscal_events(invoice_id);
    CREATE INDEX IF NOT EXISTS fiscal_events_period ON fiscal_events(period_id);
    ''')
    fields={r['name'] for r in db.execute('PRAGMA table_info(findings)')}
    if 'code' not in fields:db.execute("ALTER TABLE findings ADD COLUMN code TEXT NOT NULL DEFAULT 'legacy'")
    if 'invoice_id' not in fields:db.execute('ALTER TABLE findings ADD COLUMN invoice_id INTEGER REFERENCES invoices(id)')
    if 'reviewed_at' not in {r['name'] for r in db.execute('PRAGMA table_info(fiscal_events)')}:db.execute("ALTER TABLE fiscal_events ADD COLUMN reviewed_at TEXT NOT NULL DEFAULT ''")
    if 'revision' not in {r['name'] for r in db.execute('PRAGMA table_info(fiscal_events)')}:db.execute('ALTER TABLE fiscal_events ADD COLUMN revision INTEGER NOT NULL DEFAULT 0')

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def text(value,label,limit=2000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Informe '+label+' (até '+str(limit)+' caracteres)')
    return value.strip()

def value(raw,rate=False):
    try:
        raw=str(raw).strip()
        if ',' in raw:raw=raw.replace('.','').replace(',','.')
        result=Decimal(raw)
    except (InvalidOperation,ValueError):raise ValueError('Valor numérico inválido') from None
    if not result.is_finite() or result<0 or result>Decimal('999999999999.99'):raise ValueError('Valor fora do limite permitido')
    if rate:
        if result>100 or result.as_tuple().exponent < -6:raise ValueError('Alíquota deve estar entre 0 e 100, com até 6 casas decimais')
    elif result!=result.quantize(Decimal('.01')):raise ValueError('Informe um valor monetário com até 2 casas decimais')
    return result

def money(number):return format(number.quantize(Decimal('.01')),'.2f')

def month(raw):
    try:
        if datetime.strptime(raw,'%Y-%m').strftime('%Y-%m')!=raw:raise ValueError()
    except (ValueError,TypeError):raise ValueError('Vigência inválida; use ano-mês') from None
    return raw

def period(db,ident):
    # Serializa alterações financeiras e o fechamento do mesmo banco.
    db.execute('UPDATE periods SET closed=closed WHERE id=?',(ident,))
    row=db.execute('SELECT p.*,c.name,c.regime,c.city,c.uf FROM periods p JOIN companies c ON c.id=p.company_id WHERE p.id=?',(ident,)).fetchone()
    if not row or row['closed']:raise ValueError('Selecione uma competência aberta')
    return row

def cancelled(db,period_id):
    return {r['invoice_id'] for r in db.execute("SELECT invoice_id FROM fiscal_events WHERE period_id=? AND status='confirmado'",(period_id,))}

def event_snapshot(db,pid):
    events=[dict(r) for r in db.execute('SELECT id,digest,status,reviewed_at,revision FROM fiscal_events WHERE period_id=? ORDER BY id',(pid,))]
    return hashlib.sha256(json.dumps(events,sort_keys=True).encode()).hexdigest() if events else None

def pending_findings(db,pid):
    return [dict(r) for r in db.execute('SELECT f.* FROM findings f LEFT JOIN fiscal_finding_reviews r ON r.finding_id=f.id WHERE f.period_id=? AND r.id IS NULL',(pid,))]

def totals(db,period_id):
    rows=[dict(r) for r in db.execute('SELECT * FROM fiscal_entries WHERE period_id=? ORDER BY id',(period_id,))]
    excluded=cancelled(db,period_id)
    result=[]
    for tax in TAXES:
        included=[r for r in rows if r['tax']==tax and r['invoice_id'] not in excluded]
        def sum_kind(kind):return sum((Decimal(r['amount']) for r in included if r['kind']==kind),Decimal(0))
        debits=sum_kind('debito')+sum_kind('ajuste_debito')
        credits=sum_kind('credito')+sum_kind('ajuste_credito')
        opening=sum_kind('saldo_anterior')
        net=debits-credits-opening
        result.append({'tax':tax,'debits':money(debits),'credits':money(credits),'opening_credit':money(opening),'payable':money(max(net,Decimal(0))),'carry_credit':money(max(-net,Decimal(0))),'entries':len(included),'excluded':sum(r['tax']==tax and r['invoice_id'] in excluded for r in rows)})
    return result

def case_report(db,case):
    case=dict(case);pid=case['period_id']
    company=dict(db.execute('SELECT c.* FROM companies c JOIN periods p ON p.company_id=c.id WHERE p.id=?',(pid,)).fetchone())
    entries=[dict(r) for r in db.execute('SELECT * FROM fiscal_entries WHERE period_id=? ORDER BY id',(pid,))]
    rule_ids={entry['rule_id'] for entry in entries if entry['rule_id']}
    rules=[dict(r) for r in db.execute('SELECT * FROM fiscal_rules WHERE company_id=? ORDER BY id',(company['id'],)) if r['id'] in rule_ids]
    invoices=[dict(r) for r in db.execute('SELECT id,access_key,total,icms,ipi,pis,cofins FROM invoices WHERE period_id=? ORDER BY id',(pid,))]
    events=[dict(r) for r in db.execute('SELECT id,invoice_id,status,digest,reviewer,evidence,revision FROM fiscal_events WHERE period_id=? ORDER BY id',(pid,))]
    findings=[dict(r) for r in db.execute('SELECT * FROM findings WHERE period_id=? ORDER BY id',(pid,))]
    items=[dict(r) for r in db.execute('SELECT i.* FROM items i JOIN invoices n ON n.id=i.invoice_id WHERE n.period_id=? ORDER BY i.id',(pid,))]
    sped=db.execute('SELECT digest FROM sped_files WHERE period_id=? ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
    finding_reviews=[dict(r) for r in db.execute('SELECT r.* FROM fiscal_finding_reviews r JOIN findings f ON f.id=r.finding_id WHERE f.period_id=? ORDER BY r.id',(pid,))]
    report=totals(db,pid);actual={r['tax']:r for r in report}
    expected=json.loads(case['expected']);differences=[];blockers=[]
    if company['uf']!='GO' or company['city'] not in CITIES:blockers.append('Complete o cadastro da empresa com UF GO e um município do piloto')
    if not valid_cnpj(company['cnpj']):blockers.append('CNPJ cadastral inválido; revise o cadastro da empresa')
    if company['regime'] not in ('Normal','Lucro Real','Lucro Presumido','Simples Nacional','MEI'):blockers.append('Regime tributário não definido no cadastro')
    if company['regime']!=case['regime'] or company['city']!=case['municipality']:blockers.append('Cadastro de regime ou município mudou desde a criação do caso; registre um novo caso')
    if company['regime'] in ('Simples Nacional','MEI'):blockers.append('O motor de DAS, segregações e faixas do Simples/MEI ainda está fora deste piloto')
    if not expected:blockers.append('Ainda não foram informados os resultados esperados do mês fechado no Domínio')
    for tax,expected_amount in expected.items():
        if tax not in TAXES:
            blockers.append('O motor de '+tax+' ainda não foi implementado; a referência permanece registrada')
            continue
        if not actual[tax]['entries']:blockers.append('Sem lançamentos assistidos de '+tax+'; um resultado vazio não valida a apuração')
        delta=Decimal(actual[tax]['payable'])-Decimal(expected_amount)
        differences.append({'tax':tax,'expected':expected_amount,'actual':actual[tax]['payable'],'difference':money(delta)})
        if delta:blockers.append('Diferença em '+tax+' em relação ao resultado informado')
    if not invoices:blockers.append('Sem XMLs para o confronto do caso')
    if pending_findings(db,pid):blockers.append('Há alertas de XML pendentes; esta etapa não resolve inconsistências estruturais')
    if any(e['status']=='pendente' for e in events):blockers.append('Há eventos de cancelamento aguardando conferência')
    fiscal_company={k:company[k] for k in ('id','cnpj','name','regime','city','uf','cnae','ie')}
    month=db.execute('SELECT month FROM periods WHERE id=?',(pid,)).fetchone()['month']
    routine=rotina.tax_snapshot(db,company['id'],month,pid)
    snapshot=hashlib.sha256(json.dumps({'case':case,'company':fiscal_company,'routine':routine,'entries':entries,'rules':rules,'invoices':invoices,'items':items,'events':events,'findings':findings,'finding_reviews':finding_reviews,'sped_digest':sped['digest'] if sped else None},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    last=db.execute('SELECT * FROM fiscal_reviews WHERE case_id=? ORDER BY id DESC LIMIT 1',(case['id'],)).fetchone()
    return {'case':case,'company_fiscal_snapshot':fiscal_company,'routine_snapshot':routine,'totals':report,'differences':differences,'blockers':blockers,'snapshot':snapshot,'review_current':bool(last and last['snapshot']==snapshot and not blockers),'last_review':dict(last) if last else None}

def close_check(db,pid):
    if db.execute("SELECT 1 FROM fiscal_events WHERE period_id=? AND status='pendente'",(pid,)).fetchone():raise ValueError('Confira os eventos de cancelamento antes de fechar')
    latest=db.execute('SELECT * FROM fiscal_cases WHERE period_id=? ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
    if latest:
        report=case_report(db,latest)
        if not report['review_current']:raise ValueError('O caso de validação ainda não tem conferência atual registrada; confira os bloqueios na apuração assistida')
        return report
    return None

def freeze(db,pid,report):
    if report:
        report=dict(report,closed_snapshot=True)
        db.execute('INSERT INTO fiscal_closures(period_id,case_id,report,created) VALUES (?,?,?,?)',(pid,report['case']['id'],json.dumps(report,ensure_ascii=False),now()))

def mutate(db,action,data,log):
    p=period(db,int(data['period_id']))
    pid=p['id']
    if action=='fiscal_location':
        city=data.get('city')
        if city not in CITIES:raise ValueError('Selecione Goiânia, Trindade ou Aparecida de Goiânia')
        evidence=text(data.get('evidence'),'a referência cadastral conferida')
        db.execute('UPDATE companies SET city=?,uf=? WHERE id=?',(city,'GO',p['company_id']))
        log(db,'Município GO informado para empresa '+str(p['company_id'])+': '+city+'; referência: '+evidence)
    elif action=='fiscal_case':
        if p['uf']!='GO' or p['city'] not in CITIES:raise ValueError('Complete o município da empresa na seção do piloto GO')
        expected={}
        for tax in REFERENCE_TAXES:
            raw=data.get(tax,'')
            if raw!='':expected[tax]=money(value(raw))
        source=text(data.get('source'),'a identificação do mês e relatório de referência do Domínio')
        db.execute('INSERT INTO fiscal_cases(period_id,regime,municipality,source,expected,created) VALUES (?,?,?,?,?,?)',(pid,p['regime'],p['city'],source,json.dumps(expected),now()))
    elif action=='fiscal_rule':
        tax=data.get('tax')
        if tax not in TAXES:raise ValueError('Tributo sem motor implementado neste piloto')
        start,end=month(data.get('valid_from')),month(data.get('valid_to'))
        if start>end:raise ValueError('Fim de vigência anterior ao início')
        rounding=data.get('rounding','HALF_UP')
        if rounding not in ('HALF_UP','DOWN'):raise ValueError('Arredondamento inválido')
        if p['uf']!='GO' or p['city'] not in CITIES:raise ValueError('Complete o município GO da empresa')
        db.execute('INSERT INTO fiscal_rules(company_id,tax,name,rate,rounding,valid_from,valid_to,regime,municipality,legal_basis,prepared_by,created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(p['company_id'],tax,text(data.get('name'),'o nome da regra',160),str(value(data.get('rate'),True)),rounding,start,end,p['regime'],p['city'],text(data.get('legal_basis'),'a fundamentação e referência a conferir'),text(data.get('prepared_by'),'quem preparou os parâmetros',160),now()))
    elif action=='fiscal_entry':
        tax,kind=data.get('tax'),data.get('kind')
        if tax not in TAXES or kind not in KINDS:raise ValueError('Tributo ou tipo de lançamento inválido')
        rule_id=None;base=Decimal(0)
        if kind in ('debito','credito'):
            rule_id=int(data.get('rule_id') or 0)
            rule=db.execute('SELECT * FROM fiscal_rules WHERE id=?',(rule_id,)).fetchone()
            if not rule or rule['company_id']!=p['company_id'] or rule['tax']!=tax:raise ValueError('Regra incompatível com a empresa ou tributo')
            if rule['regime']!=p['regime'] or rule['municipality']!=p['city'] or not rule['valid_from']<=p['month']<=rule['valid_to']:raise ValueError('Regra fora da vigência, regime ou município')
            base=value(data.get('base'))
            amount=(base*Decimal(rule['rate'])/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP if rule['rounding']=='HALF_UP' else ROUND_DOWN)
        else:amount=value(data.get('amount'))
        if kind=='saldo_anterior' and db.execute("SELECT 1 FROM fiscal_entries WHERE period_id=? AND tax=? AND kind='saldo_anterior'",(pid,tax)).fetchone():raise ValueError('Saldo anterior já registrado; use ajuste documentado para uma correção')
        invoice_id=int(data.get('invoice_id') or 0) or None
        if invoice_id:
            if not db.execute('SELECT 1 FROM invoices WHERE id=? AND period_id=?',(invoice_id,pid)).fetchone():raise ValueError('Nota de outra competência')
            if invoice_id in cancelled(db,pid):raise ValueError('Nota com cancelamento conferido; não crie novos débitos ou créditos vinculados a ela')
        reason=text(data.get('reason'),'a justificativa do tratamento fiscal')
        evidence=text(data.get('evidence'),'o documento ou referência de suporte')
        prepared=text(data.get('prepared_by'),'quem informou o lançamento',160)
        db.execute('INSERT INTO fiscal_entries(period_id,tax,kind,rule_id,invoice_id,base,amount,reason,evidence,prepared_by,created) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(pid,tax,kind,rule_id,invoice_id,money(base),money(amount),reason,evidence,prepared,now()))
    elif action=='fiscal_reverse':
        original=db.execute('SELECT * FROM fiscal_entries WHERE id=? AND period_id=?',(int(data['entry_id']),pid)).fetchone()
        if not original or original['reversal_of']:raise ValueError('Lançamento original não encontrado ou já é um estorno')
        if db.execute('SELECT 1 FROM fiscal_entries WHERE reversal_of=?',(original['id'],)).fetchone():raise ValueError('Lançamento já estornado')
        reverse='ajuste_credito' if original['kind'] in ('debito','ajuste_debito') else 'ajuste_debito'
        db.execute('INSERT INTO fiscal_entries(period_id,tax,kind,invoice_id,base,amount,reason,evidence,prepared_by,reversal_of,created) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(pid,original['tax'],reverse,original['invoice_id'],'0.00',original['amount'],text(data.get('reason'),'a justificativa de estorno'),text(data.get('evidence'),'a evidência do estorno'),text(data.get('prepared_by'),'quem informou o estorno',160),original['id'],now()))
    elif action=='fiscal_event_import':
        raw=data.get('xml','')
        if not isinstance(raw,str) or len(raw.encode())>3_000_000 or '<!DOCTYPE' in raw.upper() or '<!ENTITY' in raw.upper():raise ValueError('XML de evento não permitido')
        root=ET.fromstring(raw)
        for el in root.iter():el.tag=el.tag.split('}')[-1]
        infos=[el for el in root.iter('infEvento') if el.findtext('tpEvento')=='110111']
        keys={el.findtext('chNFe') for el in infos}
        if len(keys)!=1:raise ValueError('Envie um único evento de cancelamento NF-e (110111) com chave identificada')
        key=next(iter(keys));invoice=db.execute('SELECT id FROM invoices WHERE access_key=? AND period_id=?',(key,pid)).fetchone()
        if not invoice:raise ValueError('A nota do evento não foi importada nesta competência')
        returned=next((el for el in infos if el.findtext('nProt')),None)
        protocol=returned.findtext('nProt') if returned is not None else ''
        code=returned.findtext('cStat') if returned is not None else ''
        if len(protocol or '')>64 or len(code or '')>4:raise ValueError('Metadados do evento fora do limite permitido')
        digest=hashlib.sha256(raw.encode()).hexdigest()
        if db.execute('SELECT 1 FROM fiscal_events WHERE digest=?',(digest,)).fetchone():raise ValueError('Este arquivo de evento já foi recebido')
        db.execute('INSERT INTO fiscal_events(period_id,invoice_id,digest,protocol,response_code,raw,created) VALUES (?,?,?,?,?,?,?)',(pid,invoice['id'],digest,protocol or '',code or '',raw,now()))
    elif action=='fiscal_event_review':
        event=db.execute('SELECT * FROM fiscal_events WHERE id=? AND period_id=?',(int(data['event_id']),pid)).fetchone()
        if not event:raise ValueError('Evento inexistente')
        status=data.get('status')
        if status not in ('confirmado','descartado'):raise ValueError('Decisão de conferência inválida')
        if status==event['status']:raise ValueError('Essa decisão já está registrada')
        if status=='confirmado' and (not event['protocol'] or event['response_code'] not in ('135','155')):raise ValueError('O arquivo não contém retorno/protocolo compatível com cancelamento registrado; confira na fonte oficial')
        db.execute('UPDATE fiscal_events SET status=?,reviewer=?,evidence=?,reviewed_at=?,revision=revision+1 WHERE id=?',(status,text(data.get('reviewer'),'o responsável pela conferência',160),text(data.get('evidence'),'a fonte oficial e justificativa conferidas'),now(),event['id']))
    elif action=='fiscal_finding_review':
        finding=db.execute('SELECT * FROM findings WHERE id=? AND period_id=?',(int(data['finding_id']),pid)).fetchone()
        if not finding or finding['code']!='duplicate_attempt' or not finding['invoice_id']:raise ValueError('Somente uma tentativa de duplicidade bloqueada e identificada pode ser reconhecida neste piloto')
        if not db.execute('SELECT 1 FROM invoices WHERE id=? AND period_id=?',(finding['invoice_id'],pid)).fetchone():raise ValueError('A cópia única da nota não está identificada')
        if db.execute('SELECT 1 FROM fiscal_finding_reviews WHERE finding_id=?',(finding['id'],)).fetchone():raise ValueError('Ocorrência já conferida')
        db.execute('INSERT INTO fiscal_finding_reviews(finding_id,reviewer,evidence,created) VALUES (?,?,?,?)',(finding['id'],text(data.get('reviewer'),'quem conferiu a cópia única',160),text(data.get('evidence'),'a referência que comprova a cópia única preservada'),now()))
    elif action=='fiscal_review':
        case=db.execute('SELECT * FROM fiscal_cases WHERE period_id=? ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
        if not case:raise ValueError('Registre o caso de referência primeiro')
        report=case_report(db,case)
        if report['snapshot']!=data.get('snapshot'):raise ValueError('Os dados mudaram; recarregue e confira novamente')
        if report['blockers']:raise ValueError('A conferência ainda tem bloqueios: '+'; '.join(report['blockers']))
        db.execute('INSERT INTO fiscal_reviews(case_id,snapshot,reviewer,notes,created) VALUES (?,?,?,?,?)',(case['id'],report['snapshot'],text(data.get('reviewer'),'quem realizou a conferência',160),text(data.get('notes'),'a evidência da conferência com o contador'),now()))
    else:raise ValueError('Operação fiscal desconhecida')
    log(db,action+': '+json.dumps({k:v for k,v in data.items() if k!='xml'},ensure_ascii=False))
    return {'ok':True}

def state(db):
    result={name:[dict(r) for r in db.execute('SELECT * FROM '+name+' ORDER BY id')] for name in ('fiscal_cases','fiscal_rules','fiscal_entries','fiscal_reviews','fiscal_finding_reviews')}
    result['fiscal_events']=[dict(r) for r in db.execute('SELECT id,period_id,invoice_id,protocol,response_code,status,reviewer,evidence,created,reviewed_at,revision FROM fiscal_events ORDER BY id')]
    result['fiscal_reports']=[]
    for row in db.execute('SELECT * FROM fiscal_cases WHERE id IN (SELECT MAX(id) FROM fiscal_cases GROUP BY period_id) ORDER BY id DESC'):
        frozen=db.execute('SELECT report FROM fiscal_closures WHERE period_id=?',(row['period_id'],)).fetchone()
        result['fiscal_reports'].append(json.loads(frozen['report']) if frozen else case_report(db,row))
    return result
