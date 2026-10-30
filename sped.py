"""Conferência inicial de NF-e modelo 55: XML x C100 da EFD ICMS/IPI.

Compara documentos e valores declarados; não valida direito a créditos nem substitui o PVA.
"""
import calendar
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

def migrate(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS sped_files(id INTEGER PRIMARY KEY, period_id INTEGER NOT NULL REFERENCES periods(id), filename TEXT NOT NULL, digest TEXT NOT NULL, created TEXT NOT NULL, raw TEXT NOT NULL, parsed TEXT NOT NULL, UNIQUE(period_id,digest));
    CREATE TABLE IF NOT EXISTS sped_audits(id INTEGER PRIMARY KEY, sped_id INTEGER NOT NULL REFERENCES sped_files(id), period_id INTEGER NOT NULL REFERENCES periods(id), created TEXT NOT NULL, invoice_count INTEGER NOT NULL, report TEXT NOT NULL);
    ''')

def number(value, label, line, required=False):
    if value == '' and not required: return None
    if not re.fullmatch(r'\d+(?:,\d{1,2})?',value): raise ValueError(f'Linha {line}: {label} inválido; esperado valor sem milhar e com vírgula decimal')
    return str(Decimal(value.replace(',','.')))

def parse(content, cnpj, month):
    if not isinstance(content,str) or len(content.encode())>20_000_000:raise ValueError('SPED maior que 20 MB')
    lines=[line.strip() for line in content.lstrip('\ufeff').splitlines() if line.strip()]
    if not lines or not lines[0].startswith('|0000|') or not lines[-1].startswith('|9999|'):raise ValueError('Envie uma EFD ICMS/IPI completa, com registros 0000 e 9999')
    records=[]
    for index,line in enumerate(lines,1):
        if not line.startswith('|') or not line.endswith('|'):raise ValueError(f'Linha {index}: delimitadores do SPED inválidos')
        records.append((index,line[1:-1].split('|')))
    header=records[0][1]
    if len(header)<11 or header[6]!=cnpj:raise ValueError('O CNPJ do SPED não corresponde à empresa selecionada')
    try:
        first=datetime.strptime(header[3],'%d%m%Y').date()
        last=datetime.strptime(header[4],'%d%m%Y').date()
    except ValueError:raise ValueError('Datas de abertura do SPED inválidas') from None
    expected_first=month+'-01'
    expected_last=month+'-'+str(calendar.monthrange(first.year,first.month)[1]).zfill(2)
    if first.isoformat()!=expected_first or last.isoformat()!=expected_last:raise ValueError('O SPED deve cobrir integralmente a competência selecionada')
    end=records[-1][1]
    if len(end)!=2 or not end[1].isdigit() or int(end[1])!=len(lines):raise ValueError('Quantidade de linhas do registro 9999 divergente')
    if sum(r[0]=='0000' for _,r in records)!=1:raise ValueError('SPED contém mais de uma abertura 0000')
    docs=[];excluded=[];other=0
    for line,fields in records:
        if fields[0]=='D100':other+=1
        if fields[0]!='C100':continue
        if len(fields)<9:raise ValueError(f'Linha {line}: C100 incompleto')
        if fields[4]!='55':other+=1;continue
        situation=fields[5]
        if situation not in ('00','01'):
            excluded.append({'line':line,'key':fields[8],'status':situation,'number':fields[7]})
            continue
        if len(fields)<29:raise ValueError(f'Linha {line}: C100 regular incompleto')
        if fields[1] not in ('0','1'):raise ValueError(f'Linha {line}: operação do C100 inválida')
        key=fields[8]
        if not re.fullmatch(r'\d{44}',key):raise ValueError(f'Linha {line}: chave de NF-e ausente ou inválida')
        docs.append({'line':line,'key':key,'number':fields[7],'direction':'Entrada' if fields[1]=='0' else 'Saída','status':situation,
            **{name:number(fields[col],name,line,name=='total') for name,col in [('total',11),('icms',21),('ipi',24),('pis',25),('cofins',26)]}})
    return {'documents':docs,'excluded':excluded,'other_documents':other,'month':month,'cnpj':cnpj,'lines':len(lines),'layout':header[1]}

def open_period(db, ident):
    period=db.execute('SELECT p.*,c.cnpj,c.name FROM periods p JOIN companies c ON c.id=p.company_id WHERE p.id=?',(ident,)).fetchone()
    if not period or period['closed']:raise ValueError('Selecione uma competência aberta')
    return period

def compare(db, sped_id, log):
    source=db.execute('SELECT * FROM sped_files WHERE id=?',(sped_id,)).fetchone()
    if not source:raise ValueError('SPED não encontrado')
    p=open_period(db,source['period_id'])
    parsed=json.loads(source['parsed'])
    xmls={r['access_key']:dict(r) for r in db.execute('SELECT * FROM invoices WHERE period_id=?',(p['id'],))}
    groups=defaultdict(list)
    for doc in parsed['documents']:groups[doc['key']].append(doc)
    findings=[]
    def finding(rule,key,note,xml='',sped='',line=None,number=''):
        findings.append({'rule':rule,'key':key,'number':number,'xml':xml,'sped':sped,'line':line,'note':note})
    excluded_keys={x['key'] for x in parsed['excluded'] if x['key']}
    for key,invoice in xmls.items():
        if key not in groups:
            if key in excluded_keys:
                finding('Situação fora do escopo',key,'Há XML na base, mas a nota consta no SPED com situação cancelada, denegada ou especial. Conferir eventos e situação do documento.',number=invoice['number'])
            else:
                finding('XML sem C100 correspondente',key,'NF-e importada não localizada entre os C100 regulares modelo 55 deste arquivo. Conferir período e escrituração.',number=invoice['number'])
    for key,docs in groups.items():
        if len(docs)>1:finding('Chave repetida no SPED',key,'Linhas: '+', '.join(str(d['line']) for d in docs),line=docs[0]['line'],number=docs[0]['number'])
        invoice=xmls.get(key)
        if not invoice:
            finding('XML ausente na base',key,'A nota consta no SPED, mas seu XML não foi importado para esta competência. Isso não prova ausência no Domínio.',line=docs[0]['line'],number=docs[0]['number'])
            continue
        for doc in docs:
            if doc['direction']!=invoice['direction']:
                finding('Operação divergente',key,'Conferir entrada/saída e o vínculo da empresa com a nota.',invoice['direction'],doc['direction'],doc['line'],doc['number'])
            for field,label in [('total','Total da nota'),('icms','ICMS'),('ipi','IPI'),('pis','PIS'),('cofins','COFINS')]:
                if doc[field] is None:
                    if Decimal(invoice[field])!=0:finding(label+' não informado no C100',key,'Campo vazio no SPED; não foi tratado como zero.',invoice[field],'Não informado',doc['line'],doc['number'])
                elif Decimal(invoice[field])!=Decimal(doc[field]):
                    finding(label+' divergente',key,'Diferença entre valor destacado no XML e valor escriturado. Pode decorrer de crédito permitido, ajustes ou tratamento fiscal; requer revisão.',invoice[field],doc[field],doc['line'],doc['number'])
    report={'company':p['name'],'cnpj':p['cnpj'],'month':p['month'],'filename':source['filename'],'digest':source['digest'],'layout':parsed['layout'],
        'xml_count':len(xmls),'sped_count':len(parsed['documents']),'matched_keys':sum(k in xmls for k in groups),'excluded':parsed['excluded'],'other_documents':parsed['other_documents'],'findings':findings,
        'scope':'Conferência inicial: presença, chaves repetidas, operação, total, ICMS, IPI, PIS e COFINS de NF-e modelo 55, situações 00 e 01 do C100. Não valida PVA, itens, CFOP/CST, créditos, eventos, CT-e, serviços, reforma tributária ou transmissão.'}
    if not xmls or not parsed['documents']:report['warning']='Uma das bases não contém NF-e no escopo; a comparação está incompleta.'
    created=datetime.now(timezone.utc).isoformat(timespec='seconds')
    audit_id=db.execute('INSERT INTO sped_audits(sped_id,period_id,created,invoice_count,report) VALUES (?,?,?,?,?)',(sped_id,p['id'],created,len(xmls),json.dumps(report,ensure_ascii=False))).lastrowid
    log(db,f'Conferência SPED {source["filename"]}: {len(findings)} ocorrências, relatório {audit_id}')
    return {'ok':True,'audit_id':audit_id,'findings':len(findings)}

def import_file(db, data, log):
    p=open_period(db,int(data['period_id']))
    content=data['content'];filename=data.get('filename','SPED.txt')
    if not isinstance(filename,str) or len(filename)>255:raise ValueError('Nome de arquivo inválido')
    parsed=parse(content,p['cnpj'],p['month'])
    digest=hashlib.sha256(content.encode()).hexdigest()
    existing=db.execute('SELECT id FROM sped_files WHERE period_id=? AND digest=?',(p['id'],digest)).fetchone()
    if existing:
        ident=existing['id']
    else:
        ident=db.execute('INSERT INTO sped_files(period_id,filename,digest,created,raw,parsed) VALUES (?,?,?,?,?,?)',(p['id'],filename,digest,datetime.now(timezone.utc).isoformat(timespec='seconds'),content,json.dumps(parsed,ensure_ascii=False))).lastrowid
        log(db,f'SPED importado para conferência: {filename}')
    result=compare(db,ident,log);result['duplicate']=bool(existing)
    return result

def state(db):
    files=[dict(r) for r in db.execute('SELECT id,period_id,filename,digest,created FROM sped_files ORDER BY id DESC')]
    audits=[]
    for r in db.execute('SELECT * FROM sped_audits WHERE id IN (SELECT MAX(id) FROM sped_audits GROUP BY period_id) ORDER BY id DESC'):
        entry=dict(r);entry['report']=json.loads(entry['report'])
        count=db.execute('SELECT COUNT(*) FROM invoices WHERE period_id=?',(r['period_id'],)).fetchone()[0]
        latest=db.execute('SELECT MAX(id) FROM sped_files WHERE period_id=?',(r['period_id'],)).fetchone()[0]
        entry['stale']=count!=r['invoice_count'] or latest!=r['sped_id']
        audits.append(entry)
    history=[dict(r) for r in db.execute('SELECT a.id,a.period_id,a.created,f.filename FROM sped_audits a JOIN sped_files f ON f.id=a.sped_id ORDER BY a.id DESC LIMIT 100')]
    return {'sped_files':files,'sped_audits':audits,'sped_audit_history':history}

def report_csv(report, created):
    import csv
    import io
    output=io.StringIO();writer=csv.writer(output,delimiter=';')
    def safe(value):
        value=str(value if value is not None else '')
        return "'"+value if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')) or (value.isdigit() and len(value)>=14) else value
    for record in [['Empresa',report['company']],['CNPJ',report['cnpj']],['Competência',report['month']],['Arquivo',report['filename']],['Conferido em (com fuso)',created],['XMLs na base',report['xml_count']],['C100 no escopo',report['sped_count']],['Documentos de outros modelos fora do escopo',report['other_documents']],['Aviso',report.get('warning','')],['Escopo',report['scope']],[],['Ocorrência','Chave','Nota','XML','SPED','Linha','Observação']]:writer.writerow([safe(x) for x in record])
    for f in report['findings']:
        values=[]
        for key in ('rule','key','number','xml','sped','line','note'):
            value=f[key]
            if key in ('xml','sped') and re.fullmatch(r'\d+(?:\.\d+)?',str(value)):value=str(value).replace('.',',')
            values.append(safe(value))
        writer.writerow(values)
    for item in report['excluded']:writer.writerow(['Fora do escopo',safe(item['key']),safe(item['number']),'','',item['line'],'Situação '+safe(item['status'])])
    return output.getvalue().encode('utf-8-sig')
