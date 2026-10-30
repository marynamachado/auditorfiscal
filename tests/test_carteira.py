import copy
import json
import tempfile
import unittest
from pathlib import Path
import app
import carteira
from test_agenda import sample

class FullCarteira(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=Path(self.tmp.name)/'full.sqlite3'
        with app.connect() as db:app.mutate(db,'agenda_import',{'content':json.dumps(sample())})
    def tearDown(self):
        app.DB=self.old;self.tmp.cleanup()
    def read(self):
        with app.connect() as db:return carteira.read(db)
    def save(self,snapshot):
        with app.connect() as db:return carteira.save(db,snapshot['state'],snapshot['revision'],app.log)
    def test_full_state_roundtrip_recurring_checklist_color(self):
        doc=self.read();s=doc['state'];c=s['companies'][0];c['color']='#123456'
        s['recurring']={'series':{'id':'series','company':c['id'],'title':'Mensal','active':True,'startIndex':24300,'nextIndex':24314,'dueOffset':1,'dueDay':31}}
        s['tasks'][0]['seriesId']='series'
        self.save(doc)
        restored=self.read()['state']
        self.assertEqual(restored['recurring'],s['recurring'])
        self.assertEqual(restored['tasks'][0]['checks'],s['tasks'][0]['checks'])
        self.assertEqual(restored['companies'][0]['color'],'#123456')
    def test_stale_tab_cannot_overwrite_newer_changes(self):
        a=self.read();b=copy.deepcopy(a)
        a['state']['companies'][0]['nome']='Nome atualizado';self.save(a)
        with self.assertRaises(carteira.Conflict):self.save(b)
        self.assertEqual(self.read()['state']['companies'][0]['nome'],'Nome atualizado')
    def test_deleting_from_carteira_preserves_fiscal_company(self):
        doc=self.read();s=doc['state'];s['companies']=s['companies'][1:];s['tasks']=[];s['notes']=[]
        self.save(doc)
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM companies').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM agenda_tasks').fetchone()[0],0)
        self.assertEqual(len(self.read()['state']['companies']),1)
    def test_invalid_state_rolls_back_projection_and_document(self):
        doc=self.read();self.save(doc);doc=self.read();doc['state']['tasks'][0]['due']='2026-02-31'
        with self.assertRaises(ValueError):self.save(doc)
        self.assertEqual(self.read()['state']['tasks'][0]['due'],'2026-10-31')
        with app.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM agenda_tasks').fetchone()[0],1)
    def test_rename_wallet_updates_fiscal_projection(self):
        doc=self.read();doc['state']['portfolios'][0]['name']='Escritório renomeado';self.save(doc)
        with app.connect() as db:
            names=[r['name'] for r in db.execute('SELECT name FROM wallets')]
        self.assertIn('Escritório renomeado',names);self.assertNotIn('Carteira Royal',names)
    def test_new_fiscal_company_appears_without_duplicate_on_save(self):
        self.save(self.read())
        with app.connect() as db:app.mutate(db,'company',{'cnpj':'11444777000161','name':'Nova empresa fiscal','regime':'Normal','wallet_id':1})
        doc=self.read()
        self.assertEqual(len(doc['state']['companies']),3)
        self.save(doc)
        self.assertEqual(len(self.read()['state']['companies']),3)

if __name__=='__main__':unittest.main()
