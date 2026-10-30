import json
import tempfile
import unittest
from pathlib import Path
import app
import sped
from test_app import xml, KEY

def c100(key=KEY, total='100,00', icms='18,00', status='00', operation='1', model='55', number='123'):
    values=['']*29
    for index,value in {0:'C100',1:operation,2:'0',3:'PARTICIPANTE',4:model,5:status,6:'1',7:number,8:key,9:'10102026',10:'10102026',11:total,12:'0',16:'9',20:'100,00',21:icms,24:'1,00',25:'1,65',26:'7,60'}.items():values[index]=value
    return '|'+ '|'.join(values)+'|'

def efd(documents=None, cnpj='11222333000181', start='01102026', end='31102026'):
    lines=[f'|0000|020|0|{start}|{end}|Empresa teste|{cnpj}||GO|123|5208707|||A|1|','|C001|0|']
    lines+= [c100()] if documents is None else documents
    lines+= [f'|C990|{len(lines)}|']
    lines+= [f'|9999|{len(lines)+1}|']
    return '\n'.join(lines)+'\n'

class SpedWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=Path(self.tmp.name)/'sped.sqlite3'
        with app.connect() as db:
            app.mutate(db,'company',{'cnpj':'11222333000181','name':'Empresa teste','regime':'Normal'})
            app.mutate(db,'period',{'company_id':1,'month':'2026-10'})
            app.mutate(db,'import',{'period_id':1,'xml':xml()})
    def tearDown(self):app.DB=self.old;self.tmp.cleanup()
    def call(self,action,data):
        with app.connect() as db:return app.mutate(db,action,data)
    def upload(self,content=None):return self.call('sped_import',{'period_id':1,'filename':'dominio.txt','content':efd() if content is None else content})
    def report(self):
        with app.connect() as db:return sped.state(db)['sped_audits'][0]['report']
    def rules(self):return [f['rule'] for f in self.report()['findings']]
    def test_matching_totals_and_persistence(self):
        self.upload();r=self.report()
        self.assertEqual((r['xml_count'],r['sped_count'],r['matched_keys']),(1,1,1))
        self.assertEqual(r['findings'],[])
        self.assertNotIn('warning',r)
    def test_presence_both_directions(self):
        self.upload(efd([c100(key='2'*44)]))
        self.assertCountEqual(self.rules(),['XML sem C100 correspondente','XML ausente na base'])
    def test_tax_and_operation_differences_are_review_items(self):
        self.upload(efd([c100(total='120,00',icms='0,00',operation='0')]))
        self.assertCountEqual(self.rules(),['Total da nota divergente','ICMS divergente','Operação divergente'])
    def test_duplicate_keys_and_empty_tax(self):
        self.upload(efd([c100(icms=''),c100()]))
        self.assertCountEqual(self.rules(),['Chave repetida no SPED','ICMS não informado no C100'])
    def test_cancelled_document_not_compared_as_regular(self):
        self.upload(efd([c100(status='02')]))
        self.assertEqual(self.rules(),['Situação fora do escopo'])
        self.assertEqual(self.report()['excluded'][0]['status'],'02')
        self.assertIn('warning',self.report())
    def test_other_models_and_cte_are_counted_outside_scope(self):
        self.upload(efd([c100(),c100(model='65'),'|D100|0|']))
        self.assertEqual(self.report()['other_documents'],2)
        self.assertEqual(self.report()['sped_count'],1)
    def test_wrong_company_month_and_bad_inputs_do_not_persist(self):
        for document in [efd(cnpj='99999999000199'),efd(start='01092026',end='30092026'),efd(start='02102026'),efd(end='30102026'),efd().replace('|9999|5|','|9999|999|'),efd([c100(total='NaN')]),efd([c100(key='123')]),'arquivo qualquer',efd().replace('|100,00|','|100.00|'),efd().replace('|C100|','C100|')]:
            with self.subTest(document=document[:30]):
                with self.assertRaises(ValueError):self.upload(document)
        with app.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM sped_files').fetchone()[0],0)
    def test_same_file_reimport_is_idempotent_but_new_audit_is_saved(self):
        self.upload();r=self.upload()
        self.assertTrue(r['duplicate'])
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sped_files').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sped_audits').fetchone()[0],2)
    def test_new_xml_marks_report_stale_and_recheck_refreshes(self):
        self.upload()
        self.call('import',{'period_id':1,'xml':xml(key='2'*44)})
        with app.connect() as db:self.assertTrue(sped.state(db)['sped_audits'][0]['stale'])
        self.call('sped_compare',{'sped_id':1})
        with app.connect() as db:self.assertFalse(sped.state(db)['sped_audits'][0]['stale'])
        self.assertIn('XML sem C100 correspondente',self.rules())
    def test_history_keeps_previous_sped_files(self):
        self.upload();self.upload(efd([c100(total='101,00')]))
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sped_files').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sped_audits').fetchone()[0],2)
    def test_closed_period_rejects_new_sped_and_recheck(self):
        self.upload();self.call('close',{'id':1})
        with self.assertRaises(ValueError):self.upload()
        with self.assertRaises(ValueError):self.call('sped_compare',{'sped_id':1})
    def test_csv_preserves_keys_uses_decimal_comma_and_escapes_formulas(self):
        self.upload(efd([c100(total='101,00',number='=2+2')]))
        report=self.report();report['company']='=HYPERLINK("example")'
        output=sped.report_csv(report,'2026-10-30T14:00:00+00:00').decode('utf-8-sig')
        self.assertIn("'"+KEY,output)
        self.assertIn("'=2+2",output)
        self.assertIn("'=HYPERLINK",output)
        self.assertIn('100,00;101,00',output)
        self.assertIn('Escopo;',output)
        self.assertIn('+00:00',output)

if __name__=='__main__':unittest.main()
