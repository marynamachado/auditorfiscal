import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import diagnostico

class Response(io.BytesIO):
    def __init__(self,data):super().__init__(json.dumps(data).encode())

class Diagnostic(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_read_only_report_omits_customer_data(self):
        folder=self.root/'data';folder.mkdir();database=folder/'demonstracao.sqlite3'
        db=sqlite3.connect(database);db.execute('CREATE TABLE demo_meta(id INTEGER,version TEXT)');db.execute("INSERT INTO demo_meta VALUES (1,'auditor-fiscal-demo-v1')");db.commit();db.close()
        before=hashlib.sha256(database.read_bytes()).digest()
        opener=MagicMock();opener.open.side_effect=[Response({'service':'auditor-fiscal','demo':True}),Response({'companies':[{'name':'NOME PRIVADO NAO IMPRIMIR'}]})]
        with patch.object(diagnostico,'ROOT',self.root),patch.object(diagnostico,'build_opener',return_value=opener),patch.object(diagnostico.socket,'create_connection',return_value=MagicMock()):
            report='\n'.join(diagnostico.collect())
        self.assertIn('modo demonstração SIM',report)
        self.assertIn('dados respondendo',report)
        self.assertIn('identificado e legível',report)
        self.assertNotIn('NOME PRIVADO',report)
        self.assertEqual(hashlib.sha256(database.read_bytes()).digest(),before)
    def test_unavailable_program_and_missing_files_are_reported(self):
        opener=MagicMock();opener.open.side_effect=TimeoutError
        with patch.object(diagnostico,'ROOT',self.root),patch.object(diagnostico,'build_opener',return_value=opener),patch.object(diagnostico.socket,'create_connection',side_effect=TimeoutError):
            report='\n'.join(diagnostico.collect())
        self.assertIn('FALTANDO:',report)
        self.assertIn('Porta local 8001: sem resposta',report)
        self.assertIn('/api/state: não respondeu',report)
        self.assertIn('ainda não foi criado',report)

if __name__=='__main__':unittest.main()
