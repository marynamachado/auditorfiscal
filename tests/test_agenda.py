import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import app
import agenda

def sample():
    return {'version':1,'companies':[{'id':'client-a','nome':'Cliente de teste','cnpj':'11222333000181','regime':'REAL','origem':'Planilha Royal'},{'id':'client-b','nome':'Cadastro incompleto','cnpj':'1234567890123','regime':'','origem':'PDF fechamento setembro'}],'tasks':[{'id':'task-a','company':'client-a','title':'Conferir documentos','period':'2026-10','due':'2026-10-31','status':'Pendente','checks':[{'text':'Conferir XML','done':False}]}],'notes':[{'id':'note-a','company':'client-a','text':'Aguardar documentos','color':'blue'}],'checkins':{'2026-10-30':[True,False,False,True]},'completions':{}}

class AgendaWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.old=app.DB
        app.DB=Path(self.tmp.name)/'agenda.sqlite3'
    def tearDown(self):
        app.DB=self.old; self.tmp.cleanup()
    def call(self,action,data):
        with app.connect() as db:return app.mutate(db,action,data)
    def state(self):
        with app.connect() as db:return app.state(db)
    def import_sample(self):return self.call('agenda_import',{'content':json.dumps(sample())})
    def test_import_persists_links_and_reviews_without_guessing(self):
        r=self.import_sample();s=self.state()
        self.assertEqual(r['clients_added'],2)
        self.assertEqual([c['regime'] for c in s['companies']],['Lucro Real','Não informado'])
        self.assertEqual(s['companies'][1]['cnpj'],'1234567890123')
        self.assertIn('Conferir CNPJ',s['companies'][1]['review'])
        self.assertEqual(s['wallets'][0]['responsible'],'Danillo')
        self.assertEqual(s['companies'][0]['wallet_id'],s['wallets'][0]['id'])
        self.assertEqual(s['agenda_tasks'][0]['company_id'],s['companies'][0]['id'])
        self.assertEqual(len(s['agenda_notes']),1)
        self.assertEqual(s['agenda_checkins'][0]['done'],1)
    def test_repeat_import_preserves_edits_and_no_duplicates(self):
        self.import_sample()
        self.call('agenda_status',{'id':'legacy:task-a','status':'Finalizada'})
        r=self.import_sample()
        self.assertEqual((r['clients_added'],r['tasks_added'],r['notes_added']),(0,0,0))
        self.assertEqual(self.state()['agenda_tasks'][0]['status'],'Finalizada')
    def test_completion_is_separate_from_fiscal_close_and_reopening(self):
        self.import_sample()
        with self.assertRaises(ValueError):self.call('agenda_close',{'company_id':1,'month':'2026-10'})
        self.call('agenda_status',{'id':'legacy:task-a','status':'Finalizada'})
        self.call('agenda_close',{'company_id':1,'month':'2026-10'})
        self.assertEqual(len(self.state()['agenda_closures']),1)
        self.assertEqual(self.state()['periods'],[])
        self.call('agenda_status',{'id':'legacy:task-a','status':'Pendente'})
        self.assertEqual(self.state()['agenda_closures'],[])
    def test_monthly_repetition_handles_end_of_month(self):
        self.import_sample()
        self.call('agenda_task',{'company_id':1,'title':'Entrega mensal','month':'2027-01','due':'2027-01-31','repeat':3})
        ts=[t for t in self.state()['agenda_tasks'] if t['title']=='Entrega mensal']
        self.assertEqual([t['due'] for t in ts],['2027-01-31','2027-02-28','2027-03-31'])
        self.assertEqual([t['month'] for t in ts],['2027-01','2027-02','2027-03'])
    def test_backup_roundtrip_and_merge(self):
        self.import_sample()
        self.call('agenda_task',{'company_id':1,'title':'Nova tarefa'})
        self.call('agenda_note',{'company_id':1,'text':'Nova anotação','color':'green'})
        with app.connect() as db: backup=agenda.backup(db)
        r=self.call('agenda_import',{'content':json.dumps(backup)})
        self.assertEqual((r['clients_added'],r['tasks_added'],r['notes_added']),(0,0,0))
        other=Path(self.tmp.name)/'restored.sqlite3'; app.DB=other
        self.call('agenda_import',{'content':json.dumps(backup)})
        s=self.state()
        self.assertEqual((len(s['companies']),len(s['agenda_tasks']),len(s['agenda_notes'])),(2,2,2))
        self.assertEqual(json.loads(s['agenda_tasks'][0]['checks'])[0]['text'],'Conferir XML')
    def test_bad_backup_rolls_back_everything(self):
        bad=sample();bad['tasks'][0]['company']='missing'
        with self.assertRaises(ValueError):self.call('agenda_import',{'content':json.dumps(bad)})
        self.assertEqual(self.state()['companies'],[])
        self.assertEqual(self.state()['wallets'],[])
    def test_html_data_only_no_execution(self):
        content='<script>throw new Error("never execute"); else{let c='+json.dumps(sample()['companies'])+';danger()}</script>'
        r=self.call('agenda_import',{'content':content})
        self.assertEqual(r['clients_added'],2)
        self.assertEqual(self.state()['agenda_tasks'],[])
    def test_contacts_fee_wallet_and_invalid_values(self):
        self.import_sample()
        self.call('agenda_contact',{'company_id':1,'wallet_id':2,'contact':'Responsável','phone':'1234','email':'teste@example.com','fee':'250.50'})
        c=self.state()['companies'][0]
        self.assertEqual((c['wallet_id'],c['fee']),(2,'250.50'))
        with self.assertRaises(ValueError):self.call('agenda_contact',{'company_id':1,'wallet_id':2,'fee':'NaN'})
        with self.assertRaises(ValueError):self.call('agenda_task',{'company_id':999,'title':'Inválida'})
    def test_review_company_clears_pending_fields(self):
        self.import_sample()
        self.call('agenda_company',{'company_id':2,'name':'Cadastro revisado','cnpj':'11444777000161','regime':'Simples Nacional'})
        c=self.state()['companies'][1]
        self.assertEqual((c['name'],c['regime'],c['review']),('Cadastro revisado','Simples Nacional',''))
        with self.assertRaises(ValueError):self.call('agenda_company',{'company_id':2,'name':'Inválido','cnpj':'123','regime':'Normal'})
    def test_schema_migration_preserves_existing_company(self):
        raw=sqlite3.connect(app.DB)
        raw.execute("CREATE TABLE companies(id INTEGER PRIMARY KEY,cnpj TEXT UNIQUE NOT NULL,name TEXT NOT NULL,regime TEXT NOT NULL,cnae TEXT,ie TEXT,city TEXT,uf TEXT,wallet_id INTEGER,icms_rate TEXT NOT NULL DEFAULT '18')")
        raw.execute("INSERT INTO companies(cnpj,name,regime) VALUES ('11222333000181','Nome já revisado','Normal')")
        raw.commit();raw.close()
        self.import_sample()
        s=self.state()
        self.assertEqual(s['companies'][0]['name'],'Nome já revisado')
        self.assertEqual(s['agenda_tasks'][0]['company_id'],1)
    def test_backup_preserves_empty_wallet_responsible(self):
        self.call('wallet',{'name':'Carteira vazia','responsible':'Responsável teste'})
        with app.connect() as db: backup=agenda.backup(db)
        app.DB=Path(self.tmp.name)/'empty-restored.sqlite3'
        self.call('agenda_import',{'content':json.dumps(backup)})
        self.assertEqual(self.state()['wallets'][0]['responsible'],'Responsável teste')

if __name__=='__main__':unittest.main()
