import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import app
import fiscal
from test_app import xml,KEY
from test_sped import efd

def event(key=KEY,code='135',protocol='000000000000001'):
    return f'''<procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe"><evento><infEvento><chNFe>{key}</chNFe><tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento></infEvento></evento><retEvento><infEvento><chNFe>{key}</chNFe><tpEvento>110111</tpEvento><cStat>{code}</cStat><nProt>{protocol}</nProt></infEvento></retEvento></procEventoNFe>'''

class AssistedFiscal(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=Path(self.tmp.name)/'fiscal.sqlite3'
        with app.connect() as db:
            app.mutate(db,'company',{'cnpj':'11222333000181','name':'Caso fictício','regime':'Normal','uf':'GO','city':'Goiânia'})
            app.mutate(db,'period',{'company_id':1,'month':'2026-10'})
            app.mutate(db,'import',{'period_id':1,'xml':xml()})
    def tearDown(self):app.DB=self.old;self.tmp.cleanup()
    def call(self,action,data):
        data={'period_id':1,**data}
        with app.connect() as db:return app.mutate(db,action,data)
    def state(self):
        with app.connect() as db:return app.state(db)
    def rule(self,**extra):
        self.call('fiscal_rule',{'tax':'ICMS','name':'Regra FICTÍCIA de teste','rate':'18','valid_from':'2026-10','valid_to':'2026-10','legal_basis':'PARÂMETRO SINTÉTICO — não é legislação','prepared_by':'Conferente fictício',**extra})
        return self.state()['fiscal_rules'][-1]['id']
    def entry(self,**extra):return self.call('fiscal_entry',{'tax':'ICMS','kind':'debito','rule_id':1,'base':'100','invoice_id':1,'reason':'Hipótese fictícia para teste','evidence':'Documento sintético','prepared_by':'Conferente fictício',**extra})
    def case(self,**extra):self.call('fiscal_case',{'source':'Relatório FICTÍCIO de mês fechado, apenas para teste','ICMS':'18',**extra})
    def report(self):return self.state()['fiscal_reports'][0]
    def review(self):self.call('fiscal_review',{'snapshot':self.report()['snapshot'],'reviewer':'Conferente fictício','notes':'Teste de comparação, não aprovação profissional'})
    def test_mathematical_confrontation_and_close_gate(self):
        self.case();self.rule();self.entry()
        self.assertFalse(self.report()['review_current'])
        with self.assertRaises(ValueError):self.call('close',{'id':1})
        self.review();self.assertTrue(self.report()['review_current'])
        self.call('close',{'id':1});r=self.report()
        self.assertTrue(r['closed_snapshot']);self.assertEqual(r['differences'][0]['actual'],'18.00')
        with self.assertRaises(ValueError):self.entry()
    def test_missing_expected_and_empty_engine_never_validate(self):
        self.case(ICMS='');self.assertTrue(self.report()['blockers'])
        with self.assertRaises(ValueError):self.review()
        self.case(ICMS='0');self.assertTrue(any('Sem lançamentos' in b for b in self.report()['blockers']))
        self.assertEqual(self.report()['totals'][0]['credits'],'0.00')
    def test_rounding_is_explicit_per_entry(self):
        self.rule(tax='PIS',rate='0,65',rounding='HALF_UP');self.entry(tax='PIS',base='199,99')
        rid=self.rule(tax='PIS',rate='0.65',rounding='DOWN');self.entry(tax='PIS',base='199.99',rule_id=rid)
        self.assertEqual([r['amount'] for r in self.state()['fiscal_entries']],['1.30','1.29'])
    def test_credits_adjustments_opening_and_carry(self):
        self.rule(rate='10');self.entry(base='1000');self.entry(kind='credito',base='200')
        self.entry(kind='ajuste_debito',amount='10');self.entry(kind='ajuste_credito',amount='5');self.entry(kind='saldo_anterior',amount='30')
        with app.connect() as db:total=fiscal.totals(db,1)[0]
        self.assertEqual((total['debits'],total['credits'],total['opening_credit'],total['payable']),('110.00','25.00','30.00','55.00'))
        with self.assertRaises(ValueError):self.entry(kind='saldo_anterior',amount='1')
        self.entry(kind='ajuste_credito',amount='300')
        with app.connect() as db:total=fiscal.totals(db,1)[0]
        self.assertEqual((total['payable'],total['carry_credit']),('0.00','245.00'))
    def test_invalid_amounts_missing_justification_and_wrong_tax_rule(self):
        self.rule()
        for changes in ({'base':'NaN'},{'base':'-1'},{'base':'1.001'},{'reason':''},{'evidence':''},{'prepared_by':''},{'tax':'COFINS'},{'rule_id':999}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):self.entry(**changes)
        self.assertEqual(self.state()['fiscal_entries'],[])
    def test_rule_vigency_and_profile_compatibility(self):
        self.rule(valid_from='2026-11',valid_to='2026-12')
        with self.assertRaises(ValueError):self.entry()
        self.rule();self.entry(rule_id=2)
        self.call('fiscal_location',{'city':'Trindade','evidence':'Cadastro fictício revisto'})
        with self.assertRaises(ValueError):self.entry(rule_id=2)
        with self.assertRaises(ValueError):self.rule(rate='101')
    def test_reversal_preserves_original_and_requires_new_conference(self):
        self.case();self.rule();self.entry();self.review()
        self.entry(kind='ajuste_debito',amount='1');self.assertFalse(self.report()['review_current'])
        self.call('fiscal_reverse',{'entry_id':2,'reason':'Estorno fictício','evidence':'Documento de teste','prepared_by':'Conferente fictício'})
        self.assertEqual(self.report()['differences'][0]['actual'],'18.00');self.assertFalse(self.report()['review_current'])
        self.assertEqual(len(self.state()['fiscal_entries']),3)
        with self.assertRaises(ValueError):self.call('fiscal_reverse',{'entry_id':2,'reason':'x','evidence':'x','prepared_by':'x'})
        self.review();self.assertTrue(self.report()['review_current'])
    def test_cancel_is_pending_until_external_conference_and_preserves_xml(self):
        self.rule();self.entry();self.call('fiscal_event_import',{'xml':event()})
        self.assertEqual(self.state()['settlements'][0]['debit'],'18.00')
        with self.assertRaises(ValueError):self.call('close',{'id':1})
        self.call('fiscal_event_review',{'event_id':1,'status':'confirmado','reviewer':'Conferente fictício','evidence':'Fonte fictícia, somente para teste'})
        with app.connect() as db:
            self.assertEqual(fiscal.totals(db,1)[0]['payable'],'0.00')
            self.assertEqual(db.execute('SELECT xml FROM invoices WHERE id=1').fetchone()['xml'],xml())
        self.assertEqual(Decimal(self.state()['settlements'][0]['debit']),Decimal('0.00'))
        with self.assertRaises(ValueError):self.entry()
        self.call('fiscal_event_review',{'event_id':1,'status':'descartado','reviewer':'Conferente fictício','evidence':'Revisão fictícia do evento'})
        self.assertEqual(self.state()['settlements'][0]['debit'],'18.00')
    def test_unlinked_duplicate_and_unsuccessful_events_do_not_cancel(self):
        with self.assertRaises(ValueError):self.call('fiscal_event_import',{'xml':event(key='2'*44)})
        self.call('fiscal_event_import',{'xml':event(code='136')})
        with self.assertRaises(ValueError):self.call('fiscal_event_import',{'xml':event(code='136')})
        with self.assertRaises(ValueError):self.call('fiscal_event_review',{'event_id':1,'status':'confirmado','reviewer':'Teste','evidence':'Teste'})
        self.assertEqual(self.state()['settlements'][0]['debit'],'18.00')
    def test_only_blocked_duplicate_can_be_acknowledged(self):
        self.call('import',{'xml':xml()});finding=self.state()['findings'][0]
        self.call('fiscal_finding_review',{'finding_id':finding['id'],'reviewer':'Teste','evidence':'Cópia única fictícia conferida'})
        with app.connect() as db:self.assertEqual(fiscal.pending_findings(db,1),[])
        self.call('import',{'xml':xml(key='2'*44,ncm='')});structural=self.state()['findings'][-1]
        with self.assertRaises(ValueError):self.call('fiscal_finding_review',{'finding_id':structural['id'],'reviewer':'Teste','evidence':'Não pode ignorar campo ausente'})
        with self.assertRaises(ValueError):self.call('close',{'id':1})
    def test_sped_report_invalidates_on_event_and_flags_regular_cancelled_note(self):
        self.call('sped_import',{'filename':'ficticio.txt','content':efd()})
        self.call('fiscal_event_import',{'xml':event()})
        self.assertTrue(self.state()['sped_audits'][0]['stale'])
        self.call('fiscal_event_review',{'event_id':1,'status':'confirmado','reviewer':'Teste','evidence':'Fonte fictícia'})
        self.call('sped_compare',{'sped_id':1})
        result=self.state()['sped_audits'][0]
        self.assertFalse(result['stale'])
        self.assertEqual(result['report']['cancelled_xml_count'],1)
        self.assertIn('Cancelamento informado com C100 regular',[f['rule'] for f in result['report']['findings']])
    def test_regime_specific_unimplemented_engine_remains_blocked(self):
        with app.connect() as db:db.execute("UPDATE companies SET regime='Simples Nacional' WHERE id=1")
        self.case(ICMS='',DAS='100');self.assertTrue(any('DAS' in b for b in self.report()['blockers']))
        with self.assertRaises(ValueError):self.review()
    def test_close_snapshot_survives_later_cadastral_changes(self):
        self.case();self.rule();self.entry();self.review();self.call('close',{'id':1});before=self.report()
        with app.connect() as db:db.execute("UPDATE companies SET city='Trindade' WHERE id=1")
        self.assertEqual(self.report(),before)
    def test_unused_new_rule_does_not_invalidate_unchanged_case(self):
        self.case();self.rule();self.entry();self.review();self.rule(valid_from='2027-01',valid_to='2027-12')
        self.assertTrue(self.report()['review_current'])

if __name__=='__main__':unittest.main()
