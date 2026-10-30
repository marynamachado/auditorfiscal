import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

KEY='1'*44
def xml(issuer='11222333000181',recipient='99999999000199',key=KEY,ncm='12345678',month='2026-10'):
    return f'''<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{key}"><ide><mod>55</mod><nNF>123</nNF><dhEmi>{month}-10T12:00:00-03:00</dhEmi></ide><emit><CNPJ>{issuer}</CNPJ></emit><dest><CNPJ>{recipient}</CNPJ></dest><det nItem="1"><prod><xProd>Produto de teste</xProd><NCM>{ncm}</NCM><CFOP>5102</CFOP></prod><imposto><ICMS><ICMS00><CST>00</CST><vBC>100.00</vBC><vICMS>18.00</vICMS></ICMS00></ICMS><IPI><IPITrib><vIPI>1.00</vIPI></IPITrib></IPI><PIS><PISAliq><vPIS>1.65</vPIS></PISAliq></PIS><COFINS><COFINSAliq><vCOFINS>7.60</vCOFINS></COFINSAliq></COFINS></imposto></det><total><ICMSTot><vNF>100.00</vNF><vICMS>18.00</vICMS><vIPI>1.00</vIPI><vPIS>1.65</vPIS><vCOFINS>7.60</vCOFINS></ICMSTot></total></infNFe></NFe></nfeProc>'''

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=app.DB
        app.DB=Path(self.tmp.name)/'test.sqlite3'
        with app.connect() as db:
            app.mutate(db,'wallet',{'name':'Fiscal','responsible':'Ana'})
            app.mutate(db,'company',{'cnpj':'11222333000181','name':'Empresa teste','regime':'Normal','wallet_id':1})
            app.mutate(db,'period',{'company_id':1,'month':'2026-10'})
    def tearDown(self):
        app.DB=self.old
        self.tmp.cleanup()
    def call(self,action,data):
        with app.connect() as db:return app.mutate(db,action,data)
    def read(self):
        with app.connect() as db:return app.state(db)
    def test_import_persist_settlement_close(self):
        self.call('import',{'period_id':1,'xml':xml()})
        s=self.read()
        self.assertEqual(s['invoices'][0]['direction'],'Saída')
        self.assertEqual(s['items'][0]['pis'],'1.65')
        self.assertEqual(s['settlements'][0]['balance'],'18.00')
        self.call('close',{'id':1})
        self.assertEqual(self.read()['periods'][0]['closed'],1)
        with self.assertRaises(ValueError):self.call('import',{'period_id':1,'xml':xml(key='2'*44)})
    def test_entry_and_duplicate(self):
        self.call('import',{'period_id':1,'xml':xml(issuer='99999999000199',recipient='11222333000181')})
        result=self.call('import',{'period_id':1,'xml':xml(issuer='99999999000199',recipient='11222333000181')})
        self.assertTrue(result['duplicate'])
        s=self.read()
        self.assertEqual(len(s['invoices']),1)
        self.assertEqual(s['invoices'][0]['direction'],'Entrada')
        self.assertEqual(s['settlements'][0]['potential_credit'],'18.00')
        with self.assertRaises(ValueError):self.call('close',{'id':1})
    def test_wrong_month_company_and_malformed_rollback(self):
        for document in (xml(month='2026-09'),xml(issuer='99999999000199'),'<broken>',xml().replace('<vNF>100.00</vNF>','<vNF>NaN</vNF>'),xml().replace('<vPIS>1.65</vPIS>','<vPIS>bad</vPIS>')):
            with self.assertRaises((ValueError,app.ET.ParseError)):
                self.call('import',{'period_id':1,'xml':document})
        self.assertEqual(self.read()['invoices'],[])
    def test_missing_fields_block_close(self):
        self.call('import',{'period_id':1,'xml':xml(ncm='')})
        self.assertEqual(len(self.read()['findings']),1)
        with self.assertRaises(ValueError):self.call('close',{'id':1})
    def test_wallet_edit_delete_protection(self):
        self.call('wallet',{'id':1,'name':'Nova','responsible':'Maria'})
        self.assertEqual(self.read()['wallets'][0]['name'],'Nova')
        with self.assertRaises(app.sqlite3.IntegrityError):self.call('delete_wallet',{'id':1})
    def test_invalid_cnpj(self):
        with self.assertRaises(ValueError):self.call('company',{'cnpj':'11222333000180','name':'Inválida','regime':'Normal'})

if __name__=='__main__':unittest.main()
