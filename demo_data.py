"""Kit determinístico e inteiramente sintético; não contém dados de clientes."""
from decimal import Decimal
import json
import xml.etree.ElementTree as ET

MARKER='AUDITOR FISCAL DEMONSTRACAO SEM VALIDADE FISCAL'
COMPANY='11222333000181'
SUPPLIER='11444777000161'
CUSTOMER='12345678000195'
WALLET='DEMONSTRAÇÃO — escritório fictício'

def money(value):return f'{Decimal(str(value)):.2f}'

def access_key(cnpj, month, number):
    base='52'+month[2:4]+month[5:7]+cnpj+'55'+'999'+str(number).zfill(9)+'1'+str(number+70000000).zfill(8)
    total=sum(int(c)*(2+i%8) for i,c in enumerate(reversed(base)))
    digit=11-total%11
    return base+str(0 if digit>=10 else digit)

def document(number,month,base,entry=False,missing_ncm=False,unrelated=False):
    issuer=SUPPLIER if entry or unrelated else COMPANY
    recipient=CUSTOMER if unrelated or not entry else COMPANY
    base=Decimal(str(base));icms=base*Decimal('.18');ipi=base*Decimal('.05')
    return {'number':str(number),'month':month,'issuer':issuer,'recipient':recipient,'entry':entry,
        'key':access_key(issuer,month,number),'base':money(base),'icms':money(icms),'ipi':money(ipi),
        'pis':money(base*Decimal('.0165')),'cofins':money(base*Decimal('.076')),'total':money(base+ipi),'missing_ncm':missing_ncm}

def xml(doc):
    root=ET.Element('NFe',xmlns='http://www.portalfiscal.inf.br/nfe')
    info=ET.SubElement(root,'infNFe',Id='NFe'+doc['key'],versao='4.00')
    def group(parent,tag,fields):
        node=ET.SubElement(parent,tag)
        for name,value in fields.items():ET.SubElement(node,name).text=str(value)
        return node
    group(info,'ide',{'cUF':'52','cNF':str(int(doc['number'])+70000000),'natOp':'OPERACAO FICTICIA PARA TESTE','mod':'55','serie':'999','nNF':doc['number'],'dhEmi':doc['month']+'-10T10:00:00-03:00','tpNF':'1','idDest':'1','cMunFG':'5208707','tpImp':'1','tpEmis':'1','cDV':doc['key'][-1],'tpAmb':'2','finNFe':'1','indFinal':'1','indPres':'0','procEmi':'0','verProc':'AF-DEMO-1.0'})
    emit=group(info,'emit',{'CNPJ':doc['issuer'],'xNome':MARKER+' - EMITENTE'})
    group(emit,'enderEmit',{'xLgr':'RUA EXEMPLO FICTICIO','nro':'100','xBairro':'BAIRRO DE TESTE','cMun':'5208707','xMun':'GOIANIA','UF':'GO','CEP':'00000000','cPais':'1058','xPais':'BRASIL'})
    ET.SubElement(emit,'IE').text='000000000';ET.SubElement(emit,'CRT').text='3'
    dest=group(info,'dest',{'CNPJ':doc['recipient'],'xNome':'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL'})
    group(dest,'enderDest',{'xLgr':'RUA CENARIO DE TESTE','nro':'200','xBairro':'BAIRRO FICTICIO','cMun':'5208707','xMun':'GOIANIA','UF':'GO','CEP':'00000000','cPais':'1058','xPais':'BRASIL'})
    ET.SubElement(dest,'indIEDest').text='9'
    det=ET.SubElement(info,'det',nItem='1')
    group(det,'prod',{'cProd':'DEMO001','cEAN':'SEM GTIN','xProd':'PRODUTO FICTICIO - SEM VALIDADE FISCAL','NCM':'' if doc['missing_ncm'] else '73181500','CFOP':'5102','uCom':'UN','qCom':'1.0000','vUnCom':doc['base'],'vProd':doc['base'],'cEANTrib':'SEM GTIN','uTrib':'UN','qTrib':'1.0000','vUnTrib':doc['base'],'indTot':'1'})
    tax=ET.SubElement(det,'imposto')
    icms=ET.SubElement(tax,'ICMS')
    group(icms,'ICMS00',{'orig':'0','CST':'00','modBC':'3','vBC':doc['base'],'pICMS':'18.00','vICMS':doc['icms']})
    ipi=group(tax,'IPI',{'cEnq':'999'})
    group(ipi,'IPITrib',{'CST':'50','vBC':doc['base'],'pIPI':'5.00','vIPI':doc['ipi']})
    pis=ET.SubElement(tax,'PIS');group(pis,'PISAliq',{'CST':'01','vBC':doc['base'],'pPIS':'1.65','vPIS':doc['pis']})
    cofins=ET.SubElement(tax,'COFINS');group(cofins,'COFINSAliq',{'CST':'01','vBC':doc['base'],'pCOFINS':'7.60','vCOFINS':doc['cofins']})
    total=ET.SubElement(info,'total')
    group(total,'ICMSTot',{'vBC':doc['base'],'vICMS':doc['icms'],'vICMSDeson':'0.00','vFCP':'0.00','vBCST':'0.00','vST':'0.00','vFCPST':'0.00','vFCPSTRet':'0.00','vProd':doc['base'],'vFrete':'0.00','vSeg':'0.00','vDesc':'0.00','vII':'0.00','vIPI':doc['ipi'],'vIPIDevol':'0.00','vPIS':doc['pis'],'vCOFINS':doc['cofins'],'vOutro':'0.00','vNF':doc['total']})
    group(info,'transp',{'modFrete':'9'})
    pay=ET.SubElement(info,'pag');group(pay,'detPag',{'tPag':'90','vPag':'0.00'})
    group(info,'infAdic',{'infCpl':MARKER+'. Documento sintetico, sem assinatura ou autorizacao. Nao transmitir nem importar em sistemas oficiais.'})
    return ET.tostring(root,encoding='utf-8',xml_declaration=True).decode()

def c100(doc,status='00',wrong=False):
    fields=['']*29
    for i,value in {0:'C100',1:'0' if doc['entry'] else '1',2:'1' if doc['entry'] else '0',3:'FORN_DEMO' if doc['entry'] else 'CLI_DEMO',4:'55',5:status,6:'999',7:doc['number'],8:doc['key']}.items():fields[i]=value
    if status=='00':
        total=money(Decimal(doc['total'])+10) if wrong else doc['total']
        icms=money(Decimal(doc['icms'])-1) if wrong else doc['icms']
        for i,value in {9:'10'+doc['month'][5:7]+doc['month'][:4],10:'10'+doc['month'][5:7]+doc['month'][:4],11:total,12:'0',13:'0.00',14:'0.00',15:doc['base'],16:'9',17:'0.00',18:'0.00',19:'0.00',20:doc['base'],21:icms,22:'0.00',23:'0.00',24:doc['ipi'],25:doc['pis'],26:doc['cofins'],27:'0.00',28:'0.00'}.items():fields[i]=value.replace('.',',')
    return '|'+ '|'.join(fields)+'|'

def sped(month,rows):
    import calendar
    year,mo=map(int,month.split('-'))
    lines=[f'|0000|020|0|01{mo:02}{year}|{calendar.monthrange(year,mo)[1]}{mo:02}{year}|{MARKER}|{COMPANY}||GO|000000000|5208707|||A|1|','|0001|0|',f'|0005|EMPRESA FICTICIA|00000000|RUA EXEMPLO FICTICIO|100||BAIRRO DE TESTE|||fiscal@example.invalid|','|0990|4|','|C001|0|',*rows,f'|C990|{len(rows)+2}|']
    lines.append(f'|9999|{len(lines)+1}|')
    return '\n'.join(lines)+'\n'

def scenarios():
    good=[document(1001,'2026-10',1000,entry=True),document(2001,'2026-10',2000),document(2002,'2026-10',500)]
    bad=[document(1002,'2026-11',1000,entry=True),document(3001,'2026-11',2000),document(3002,'2026-11',500,missing_ncm=True)]
    extra=document(9999,'2026-11',100)
    good_files={f'{i:02}_{"entrada" if d["entry"] else "saida"}_{d["number"]}.xml':xml(d) for i,d in enumerate(good,1)}
    bad_files={f'{i:02}_{"entrada" if d["entry"] else "saida"}_{d["number"]}{"_sem_ncm" if d["missing_ncm"] else ""}.xml':xml(d) for i,d in enumerate(bad,1)}
    bad_files.update({'04_duplicada_3001.xml':xml(bad[1]),'05_outra_empresa.xml':xml(document(4001,'2026-11',100,unrelated=True)),'06_mes_incorreto.xml':xml(document(4002,'2026-10',100)),'07_xml_invalido.xml':'<NFe><infNFe>ARQUIVO FICTICIO QUEBRADO</NFe>'})
    return {
        'correto':{'month':'2026-10','folder':'01_fluxo_correto_10_2026','xmls':good_files,'sped':sped('2026-10',[c100(d) for d in good]),'expected':{'imported':3,'duplicate':0,'rejected':0,'xml_alerts':0,'sped_findings':0,'icms_debit':'450.00','potential_credit':'180.00','balance':'270.00','sped_count':3,'matched_keys':3}},
        'alertas':{'month':'2026-11','folder':'02_alertas_11_2026','xmls':bad_files,'sped':sped('2026-11',[c100(bad[0]),c100(bad[1],wrong=True),c100(bad[1]),c100(extra),c100(document(8888,'2026-11',100),status='02')]),'extra':xml(extra),'expected':{'imported':3,'duplicate':1,'rejected':3,'xml_alerts':2,'sped_findings':5,'icms_debit':'450.00','potential_credit':'180.00','balance':'270.00','sped_count':4,'matched_keys':2}}
    }

def files():
    result={}
    for scenario in scenarios().values():
        folder=scenario['folder']
        for name,content in scenario['xmls'].items():result[folder+'/XML/'+name]=content.encode()
        result[folder+'/SPED_DIDATICO_'+scenario['month']+'.txt']=scenario['sped'].encode()
        if 'extra' in scenario:result[folder+'/EXTRA_IMPORTAR_DEPOIS/08_nota_9999.xml']=scenario['extra'].encode()
    company={'aviso':MARKER,'cnpj_exemplificativo':COMPANY,'razao_social':MARKER+' LTDA','nome_fantasia':'Loja de testes — demonstração','regime':'Normal','cnae':'4744099','ie_ficticia':'000000000','municipio':'Goiânia','uf':'GO','codigo_municipio':'5208707','endereco':'Rua Exemplo Fictício, 100 — Bairro de Teste','cep_ficticio':'00000000','contato':'Responsável de demonstração','email':'fiscal@example.invalid','telefone_ficticio':'(00) 00000-0000','carteira':WALLET,'responsavel':'Contador de teste','aliquota_referencia':'18','observacao':'Números exemplificativos, sem consulta cadastral. Alíquotas e tributos didáticos, sem aplicação das regras legais de Goiás. XMLs sem assinatura/protocolo; SPED simplificado sem validação no PVA.'}
    result['EMPRESA_FICTICIA.json']=json.dumps(company,ensure_ascii=False,indent=2).encode()
    result['RESULTADOS_ESPERADOS.json']=json.dumps({k:v['expected'] for k,v in scenarios().items()},ensure_ascii=False,indent=2).encode()
    result['LEIA_PRIMEIRO.txt']=GUIDE.encode()
    return result

GUIDE='''DEMONSTRAÇÃO DO AUDITOR FISCAL — SEM VALIDADE FISCAL

1. Execute Iniciar-Demonstracao-Windows.bat. Mantenha a janela aberta.
2. No menu Como testar, confira o selo de DEMONSTRAÇÃO. A empresa e as competências 10/2026 e 11/2026 já estarão cadastradas, em banco separado dos clientes reais.
3. Baixe este kit pelo botão do sistema e use Extrair tudo no Windows.

CENÁRIO CORRETO — 10/2026
4. Em Importação XML, selecione a competência 2026-10 da empresa de demonstração. Importe os três arquivos da pasta 01_fluxo_correto_10_2026/XML.
5. Esperado: 3 importadas, nenhuma duplicada ou rejeitada. Em Escrita Fiscal, confira uma entrada de R$ 1.050,00 e duas saídas de R$ 2.100,00 e R$ 525,00, com itens e tributos.
6. Em Apuração ICMS: débitos R$ 450,00, créditos potenciais R$ 180,00, saldo simulado R$ 270,00. Valores meramente didáticos.
7. Em Conferência SPED, selecione a mesma competência e envie o TXT da pasta 01. Esperado: 3 C100, 3 chaves correspondentes, nenhuma ocorrência nos campos comparados. Baixe o CSV para conferir no Excel.
8. Na carteira, abra o cliente, selecione 10/2026, teste pesquisa, contatos, honorários, tarefa, checklist, nota colorida, calendário e check-in. Conclua as tarefas do mês e marque o trabalho finalizado. Isso não fecha a competência fiscal.
9. Em Competências, feche 2026-10. Tentar importar outro XML nessa competência deverá ser bloqueado.

CENÁRIO COM ALERTAS — 11/2026
10. Importe apenas os sete XMLs da pasta 02_alertas_11_2026/XML para 2026-11.
11. Esperado: 3 importadas, 1 duplicada e 3 rejeitadas (outra empresa, mês incorreto e XML quebrado). Auditoria: NCM ausente e tentativa de duplicidade. O fechamento fiscal deve ser bloqueado por esses alertas de XML.
12. Importe o TXT da pasta 02 em Conferência SPED. Esperado: 4 C100 no escopo, 2 chaves correspondentes, 5 ocorrências: uma nota sem C100, uma chave repetida, uma diferença de total, uma de ICMS e uma nota cujo XML falta na base. Uma nota cancelada fica fora do escopo.
13. Opcional: importe a nota 9999 da subpasta EXTRA_IMPORTAR_DEPOIS para 2026-11. O relatório ficará desatualizado. Refaça a conferência: restarão 4 ocorrências; o novo saldo de ICMS simulado será R$ 288,00.

ALTERNATIVA AUTOMÁTICA
Em Como testar, os botões de carregar cenário importam os mesmos arquivos e geram a conferência. Use-os em competências ainda sem notas, em vez das etapas manuais, para ver o resultado pronto.

REPETIR E CONFERIR PERSISTÊNCIA
Feche o programa e abra a demonstração novamente: os dados devem permanecer. Teste o backup e a restauração da carteira em Backup e ajuda. Para repetir tudo do início, use Reiniciar somente os dados de demonstração, na tela Como testar. Essa ação apaga as alterações do banco de demonstração, não o banco dos clientes reais. A V1 ainda não resolve alertas fiscais nem corrige notas automaticamente.

LIMITES
Estes documentos são sintéticos, não são notas autorizadas e não devem ser enviados ao Domínio, ao PVA ou ao Fisco. O SPED didático é simplificado e atende somente ao leitor inicial do sistema. Este kit testa os recursos implementados: não testa busca SEFAZ, integração direta ao Domínio, CT-e, NFS-e, SPED completo, correções, transmissão, folha ou reforma tributária. Esses módulos ainda não estão implementados. Contatos, IE, CEP e valores são exemplificativos. Não houve consulta cadastral e nenhuma associação a empresas reais é afirmada.
'''
