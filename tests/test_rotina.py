import tempfile
import unittest
from pathlib import Path
import app
import rotina
from test_app import xml
import test_fiscal

class Routine(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=app.DB;self.old_demo=app.DEMO_MODE
        app.DB=Path(self.tmp.name)/'test.sqlite3';app.DEMO_MODE=False
        with app.connect() as db:
            for name,cnpj in [('Fictícia GO','11222333000181'),('Outra fictícia','11444777000161')]:
                app.mutate(db,'company',{'name':name,'cnpj':cnpj,'regime':'Normal','uf':'GO','city':'Goiânia'})
            app.mutate(db,'period',{'company_id':1,'month':'2026-10'})
            app.mutate(db,'import',{'period_id':1,'xml':xml()})
    def tearDown(self):app.DB=self.old;app.DEMO_MODE=self.old_demo;self.tmp.cleanup()
    def call(self,action,**data):
        with app.connect() as db:return app.mutate(db,action,{'company_id':1,'prepared_by':'Pessoa fictícia','source':'Fonte fictícia',**data})
    def state(self):
        with app.connect() as db:return app.state(db)
    def accumulator(self,**data):
        self.call('routine_catalog',kind='accumulator',code='001',name='Entrada sintética',direction='Saída',treatment='Tributada',stock='Não',accounting='A conferir',taxes='ICMS, PIS',**data)
        return self.state()['routine_catalog'][-1]['id']
    def profile(self,**data):
        self.call('routine_profile',valid_from='2026-10',regime='Normal',accountant='Contador fictício',crc='FICTICIO',crc_uf='GO',address='Endereço fictício',partners='Sócio fictício 100%',**data)
    def classify(self,accumulator):self.call('routine_classify',invoice_id=1,accumulator_id=accumulator,reason='Conferência sintética')
    def test_versioned_profile_effective_month_and_closed_period_guard(self):
        self.profile();self.profile(notes='Nova versão de conferência')
        self.assertEqual(len(self.state()['routine_profiles']),2)
        with app.connect() as db:
            self.assertIsNone(rotina.tax_snapshot(db,1,'2026-09',1)['profile'])
            self.assertEqual(rotina.tax_snapshot(db,1,'2026-10',1)['profile']['notes'],'Nova versão de conferência')
            db.execute('UPDATE periods SET closed=1 WHERE id=1')
        with self.assertRaisesRegex(ValueError,'fechada'):self.profile()
        self.call('routine_profile',valid_from='2026-11',regime='Normal',accountant='Contador fictício',crc='TESTE',crc_uf='GO',address='Teste')
    def test_accumulator_versions_preserve_classification_and_xml_amounts(self):
        original=self.state()['invoices'];first=self.accumulator();self.classify(first)
        self.call('routine_catalog',kind='accumulator',code='001',name='Nova versão',direction='Saída',treatment='Isenta',stock='Não',accounting='Não')
        with app.connect() as db:
            snap=rotina.tax_snapshot(db,1,'2026-10',1)
            self.assertEqual(snap['classifications'][0]['accumulator_id'],first)
            self.assertEqual(snap['accumulators'][0]['name'],'Entrada sintética')
        self.assertEqual(self.state()['invoices'],original)
        with self.assertRaisesRegex(ValueError,'versão atual'):self.classify(first)
        self.classify(self.state()['routine_catalog'][-1]['id'])
        self.assertEqual(len(self.state()['routine_classifications']),2)
    def test_wrong_company_direction_and_closed_note_rejected(self):
        wrong_company=self.accumulator(company_id=2)
        with self.assertRaisesRegex(ValueError,'não pertence'):self.classify(wrong_company)
        self.call('routine_catalog',kind='accumulator',code='S01',name='Entrada',direction='Entrada',treatment='A conferir',stock='Não',accounting='Não')
        with self.assertRaisesRegex(ValueError,'incompatível'):self.classify(self.state()['routine_catalog'][-1]['id'])
        valid=self.accumulator()
        with app.connect() as db:db.execute('UPDATE periods SET closed=1 WHERE id=1')
        with self.assertRaisesRegex(ValueError,'aberta'):self.classify(valid)
    def test_catalog_validation_and_tenant_isolation(self):
        with self.assertRaisesRegex(ValueError,'CFOP'):self.accumulator(cfop='123')
        with self.assertRaisesRegex(ValueError,'NCM'):self.call('routine_catalog',kind='product',code='P1',name='Fictício',item_type='Produto',ncm='123')
        with self.assertRaisesRegex(ValueError,'CNPJ'):self.call('routine_catalog',kind='third_party',code='T1',name='Fictício',role='Fornecedor',cnpj='00000000000000')
        self.call('routine_catalog',kind='product',code='P1',name='<script>texto</script>',item_type='Produto',ncm='12345678')
        self.call('routine_catalog',kind='product',code='P1',name='Serviço novo',item_type='Serviço')
        self.call('routine_catalog',kind='third_party',code='T1',name='Terceiro fictício',role='Fornecedor',cnpj='11444777000161')
        with app.connect() as db:
            self.assertEqual(len(rotina.current_catalog(db,1)),2)
            self.assertEqual(len(rotina.current_catalog(db,2)),0)
    def test_obligation_is_declaratory_versioned_and_requires_external_evidence(self):
        self.call('routine_obligation',period_id=1,obligation='EFD ICMS/IPI',status='Pendente')
        with self.assertRaisesRegex(ValueError,'referência'):self.call('routine_obligation',period_id=1,obligation='EFD ICMS/IPI',status='Transmitido externamente')
        with self.assertRaises(ValueError):self.call('routine_obligation',period_id=1,obligation='EFD ICMS/IPI',status='Pendente',due='2026-02-30')
        with app.connect() as db:db.execute('UPDATE periods SET closed=1 WHERE id=1')
        self.call('routine_obligation',period_id=1,obligation='EFD ICMS/IPI',status='Transmitido externamente',evidence='PROTOCOLO FICTICIO — declaração não verificada')
        self.assertEqual(len(self.state()['routine_obligations']),2)
    def test_profile_requires_known_company_regime_and_responsible(self):
        with self.assertRaises(ValueError):self.profile(company_id=999)
        self.call('routine_profile',valid_from='2026-10',regime='Normal',accountant='Contador fictício',crc='FICTICIO',crc_uf='GO',address='Endereço fictício')
        with self.assertRaisesRegex(ValueError,'regime'):self.call('routine_profile',valid_from='2026-10',regime='Simples Nacional',accountant='Teste',crc='TESTE',crc_uf='GO',address='Teste')
        with self.assertRaises(ValueError):self.accumulator(prepared_by='')

class RoutineReview(unittest.TestCase):
    # Reuse only the fiscal fixture/helpers, not its test methods.
    setUp=test_fiscal.AssistedFiscal.setUp
    tearDown=test_fiscal.AssistedFiscal.tearDown
    call=test_fiscal.AssistedFiscal.call
    state=test_fiscal.AssistedFiscal.state
    case=test_fiscal.AssistedFiscal.case
    rule=test_fiscal.AssistedFiscal.rule
    entry=test_fiscal.AssistedFiscal.entry
    report=test_fiscal.AssistedFiscal.report
    review=test_fiscal.AssistedFiscal.review
    def test_routine_changes_invalidate_fiscal_review_and_preserve_frozen_memory(self):
        self.case();self.rule();self.entry();self.review()
        self.assertTrue(self.report()['review_current'])
        data={'company_id':1,'valid_from':'2026-10','regime':'Normal','accountant':'Fictício','crc':'TESTE','crc_uf':'GO','address':'Fictício','source':'Fictício','prepared_by':'Fictício'}
        self.call('routine_profile',data)
        self.assertFalse(self.report()['review_current']);self.review()
        # A future profile does not invalidate the current month.
        self.call('routine_profile',{**data,'valid_from':'2026-11'})
        self.assertTrue(self.report()['review_current'])
        self.call('routine_catalog',{'company_id':1,'kind':'accumulator','code':'1','name':'Fictício','direction':'Saída','treatment':'A conferir','stock':'Não','accounting':'Não','source':'Fictício','prepared_by':'Fictício'})
        self.assertTrue(self.report()['review_current'])
        self.call('routine_classify',{'invoice_id':1,'accumulator_id':1,'reason':'Fictício','prepared_by':'Fictício'})
        self.assertFalse(self.report()['review_current']);self.review()
        self.call('close',{'id':1});frozen=self.report()['routine_snapshot']
        self.assertEqual(frozen['profile']['valid_from'],'2026-10')
        self.call('routine_profile',{**data,'valid_from':'2026-12'})
        self.assertEqual(self.report()['routine_snapshot'],frozen)
