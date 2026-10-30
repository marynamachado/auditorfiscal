import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
import app
import recovery

class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'legado.sqlite3'
        with sqlite3.connect(self.source,factory=app.ManagedConnection) as db:
            db.execute('CREATE TABLE retained(value TEXT)');db.execute("INSERT INTO retained VALUES ('preservar')")
    def tearDown(self):self.tmp.cleanup()
    def test_snapshot_preserves_original_and_restores_integrity(self):
        original=hashlib.sha256(self.source.read_bytes()).digest()
        target=recovery.snapshot(self.source,self.root/'copy.sqlite3')
        with sqlite3.connect(target,factory=app.ManagedConnection) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT value FROM retained').fetchone()[0],'preservar')
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(),original)
        with self.assertRaises(ValueError):recovery.snapshot(self.source,target)
        with self.assertRaises(ValueError):recovery.snapshot(self.source,self.source)
    def test_before_migration_snapshot_and_corrupt_source(self):
        backup=recovery.prepare_migration_backup(self.source)
        self.assertTrue(backup.is_file())
        broken=self.root/'broken.sqlite3';broken.write_bytes(b'NAO E UM BANCO')
        with self.assertRaises(sqlite3.DatabaseError):recovery.prepare_migration_backup(broken)
        self.assertEqual(broken.read_bytes(),b'NAO E UM BANCO')
    def test_connection_context_releases_handle_even_after_failure(self):
        old=app.DB;app.DB=self.root/'managed.sqlite3'
        try:
            with app.connect() as db:db.execute("INSERT INTO wallets(name,responsible) VALUES ('Teste','Teste')")
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            with self.assertRaises(ValueError):
                with app.connect() as failed:
                    failed.execute("INSERT INTO wallets(name,responsible) VALUES ('Nao persistir','Teste')")
                    raise ValueError('Falha sintética')
            with self.assertRaises(sqlite3.ProgrammingError):failed.execute('SELECT 1')
            with app.connect() as checked:self.assertEqual(checked.execute('SELECT COUNT(*) FROM wallets').fetchone()[0],1)
            self.assertIsNone(recovery.prepare_migration_backup(app.DB))
        finally:app.DB=old

if __name__=='__main__':unittest.main()
