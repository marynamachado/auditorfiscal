import json
import tempfile
import unittest
from pathlib import Path
import app
import demo
import demo_data

class Demonstration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old_db,self.old_mode=app.DB,app.DEMO_MODE
        app.DB=Path(self.tmp.name)/'demo.sqlite3';app.DEMO_MODE=True
        with app.connect() as db:demo.seed(db)
    def tearDown(self):
        app.DB,app.DEMO_MODE=self.old_db,self.old_mode;self.tmp.cleanup()
    def read(self):
        with app.connect() as db:return app.state(db)
    def call(self,action,data):
        with app.connect() as db:return app.mutate(db,action,data)
    def test_seed_has_full_company_wallet_months_and_agenda(self):
        s=self.read();c=s['companies'][0]
        self.assertTrue(s['demo']['enabled'])
        self.assertEqual((len(s['wallets']),len(s['companies']),len(s['periods']),len(s['agenda_tasks'])),(1,1,2,6))
        for field in ('cnpj','name','regime','cnae','ie','city','uf','wallet_id','icms_rate','contact','phone','email','fee'):self.assertTrue(c[field],field)
        self.assertEqual(len(json.loads(s['agenda_tasks'][0]['checks'])),2)
        self.assertEqual(s['invoices'],[])
        with app.connect() as db:demo.seed(db)
        self.assertEqual(len(self.read()['agenda_tasks']),6)
    def test_correct_scenario_matches_expected_tax_and_closes(self):
        self.call('demo_load',{'scenario':'correto'});s=self.read();expected=demo_data.scenarios()['correto']['expected']
        self.assertEqual(len(s['invoices']),expected['imported'])
        self.assertEqual(s['findings'],[])
        self.assertEqual(len(s['sped_audits'][0]['report']['findings']),0)
        self.assertEqual(s['settlements'][0]['debit'],expected['icms_debit'])
        self.assertEqual(s['settlements'][0]['potential_credit'],expected['potential_credit'])
        self.assertEqual(s['settlements'][0]['balance'],expected['balance'])
        self.assertEqual(sorted(n['total'] for n in s['invoices']),['1050.00','2100.00','525.00'])
        self.call('close',{'id':1})
        with self.assertRaises(ValueError):self.call('import',{'period_id':1,'xml':next(iter(demo_data.scenarios()['correto']['xmls'].values()))})
    def test_alert_scenario_has_exact_document_and_sped_outcomes(self):
        result=self.call('demo_load',{'scenario':'alertas'});s=self.read()
        statuses=[r['status'] for r in result['results']]
        self.assertEqual((statuses.count('Importada'),statuses.count('Duplicada'),statuses.count('Rejeitada')),(3,1,3))
        self.assertEqual(len(s['findings']),2)
        r=s['sped_audits'][0]['report']
        self.assertEqual((r['sped_count'],r['matched_keys'],len(r['findings']),len(r['excluded'])),(4,2,5,1))
        with self.assertRaises(ValueError):self.call('close',{'id':2})
        with self.assertRaises(ValueError):self.call('demo_load',{'scenario':'alertas'})
    def test_extra_note_invalidates_report_and_recheck_reduces_findings(self):
        self.call('demo_load',{'scenario':'alertas'})
        self.call('import',{'period_id':2,'xml':demo_data.scenarios()['alertas']['extra']})
        self.assertTrue(self.read()['sped_audits'][0]['stale'])
        self.call('sped_compare',{'sped_id':1});s=self.read()
        self.assertEqual(len(s['sped_audits'][0]['report']['findings']),4)
        self.assertEqual(s['settlements'][1]['balance'],'288.00')
    def test_demo_reset_is_repeatable_and_does_not_touch_another_database(self):
        real=Path(self.tmp.name)/'real.sqlite3'
        other=app.sqlite3.connect(real);other.execute('CREATE TABLE untouched(value TEXT)');other.execute("INSERT INTO untouched VALUES ('Preservar')");other.commit();other.close()
        before=real.read_bytes()
        self.call('demo_load',{'scenario':'correto'});self.call('demo_reset',{})
        s=self.read()
        self.assertEqual((len(s['invoices']),len(s['sped_audits']),len(s['agenda_tasks'])),(0,0,6))
        self.assertEqual(real.read_bytes(),before)
        self.call('demo_reset',{});self.call('demo_load',{'scenario':'correto'})
        self.assertEqual(len(self.read()['invoices']),3)
    def test_normal_mode_rejects_reset_seed_and_fictitious_documents(self):
        app.DEMO_MODE=False
        with self.assertRaises(ValueError):self.call('demo_reset',{})
        with app.connect() as db:
            with self.assertRaises(ValueError):demo.seed(db)
        with self.assertRaisesRegex(ValueError,'fictício'):self.call('import',{'period_id':1,'xml':next(iter(demo_data.scenarios()['correto']['xmls'].values()))})
        with self.assertRaisesRegex(ValueError,'didático'):self.call('sped_import',{'period_id':1,'content':demo_data.scenarios()['correto']['sped']})
        self.assertEqual(len(self.read()['companies']),1)
    def test_seed_refuses_existing_unmarked_business_database(self):
        app.DB=Path(self.tmp.name)/'unmarked.sqlite3'
        with app.connect() as db:db.execute("INSERT INTO wallets(name,responsible) VALUES ('Preservar','Pessoa')")
        with self.assertRaisesRegex(ValueError,'já contém dados'):
            with app.connect() as db:demo.seed(db)
        with app.connect() as db:self.assertEqual(db.execute('SELECT name FROM wallets').fetchone()['name'],'Preservar')
    def test_kit_is_deterministic_and_has_expected_manifest_and_homologation(self):
        files=demo_data.files();self.assertEqual(files,demo_data.files())
        for name,content in files.items():
            if name.endswith('.xml') and 'invalido' not in name:
                root=app.ET.fromstring(content)
                for element in root.iter():element.tag=element.tag.split('}')[-1]
                self.assertEqual(root.findtext('infNFe/ide/tpAmb'),'2')
                self.assertIn(demo_data.MARKER,content.decode())
        self.assertEqual(json.loads(files['RESULTADOS_ESPERADOS.json'])['alertas']['sped_findings'],5)

if __name__=='__main__':unittest.main()
