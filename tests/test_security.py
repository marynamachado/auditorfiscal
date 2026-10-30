import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
import app
from security import Access, IDLE_SECONDS, valid_request

PASSWORD='Senha ficticia apenas para testes 2026'
NEW_PASSWORD='Outra frase ficticia para testar 2026'

class LocalAccess(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=0
        self.access=Access(Path(self.tmp.name)/'test.access.json',8000,clock=lambda:self.now)
    def tearDown(self):self.tmp.cleanup()
    def setup(self):return self.access.setup(PASSWORD,PASSWORD)
    def test_hash_and_unique_salt_no_plain_password(self):
        cookie=self.setup();raw=self.access.path.read_text()
        self.assertNotIn(PASSWORD,raw)
        self.assertEqual(json.loads(raw)['algorithm'],'pbkdf2-sha256')
        self.assertTrue(self.access.verify(PASSWORD));self.assertFalse(self.access.verify('incorreta'))
        other=Access(Path(self.tmp.name)/'other.json',8000);other.setup(PASSWORD,PASSWORD)
        self.assertNotEqual(self.access.config()['salt'],other.config()['salt'])
        self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
    def test_requires_setup_and_rejects_short_or_mismatched_password(self):
        self.assertTrue(self.access.status(None)['setup_required'])
        for a,b in [('curta','curta'),(PASSWORD,'diferente')]:
            with self.assertRaises(ValueError):self.access.setup(a,b)
        self.setup();before=self.access.path.read_bytes()
        with self.assertRaises(ValueError):self.setup()
        self.assertEqual(self.access.path.read_bytes(),before)
    def test_expiration_and_activity_refresh(self):
        cookie=self.setup();self.assertTrue(self.access.authenticated(cookie))
        self.now=IDLE_SECONDS-1;self.assertTrue(self.access.authenticated(cookie))
        self.now+=IDLE_SECONDS-1;self.assertTrue(self.access.authenticated(cookie,touch=False))
        self.now+=2;self.assertFalse(self.access.authenticated(cookie))
    def test_logout_and_password_change_revoke_sessions(self):
        first=self.setup();second=self.access.login(PASSWORD)
        self.access.logout(first);self.assertFalse(self.access.authenticated(first));self.assertTrue(self.access.authenticated(second))
        third=self.access.change(PASSWORD,NEW_PASSWORD,NEW_PASSWORD)
        self.assertFalse(self.access.authenticated(second));self.assertTrue(self.access.authenticated(third))
        self.assertFalse(self.access.verify(PASSWORD));self.assertTrue(self.access.verify(NEW_PASSWORD))
    def test_restart_preserves_password_but_does_not_restore_sessions(self):
        cookie=self.setup();restarted=Access(self.access.path,8000,clock=lambda:self.now)
        self.assertFalse(restarted.status(None)['setup_required'])
        self.assertFalse(restarted.authenticated(cookie))
        self.assertTrue(restarted.authenticated(restarted.login(PASSWORD)))
    def test_absolute_expiration_even_with_regular_activity(self):
        cookie=self.setup()
        for i in range(16):
            self.now+=29*60;self.assertTrue(self.access.authenticated(cookie))
        self.now=8*60*60+1
        self.assertFalse(self.access.authenticated(cookie))
    def test_rate_limit_and_recovery_after_one_minute(self):
        self.setup()
        for i in range(5):
            with self.assertRaises(ValueError):self.access.login('errada')
        with self.assertRaisesRegex(ValueError,'Muitas tentativas'):self.access.login(PASSWORD)
        self.now=61;self.assertTrue(self.access.authenticated(self.access.login(PASSWORD)))
    def test_corrupt_settings_fail_closed_and_demo_does_not_store_password(self):
        self.access.path.write_text('{quebrado')
        with self.assertRaises(ValueError):self.access.status(None)
        demo=Access(Path(self.tmp.name)/'demo.json',8001,demo=True)
        self.assertTrue(demo.authenticated(None))
        with self.assertRaises(ValueError):demo.setup(PASSWORD,PASSWORD)
        self.assertFalse(demo.path.exists())
    def test_host_origin_and_fetch_site_policy(self):
        self.assertTrue(valid_request('127.0.0.1:8000',8000))
        self.assertTrue(valid_request('localhost:8000',8000,'http://localhost:8000','same-origin'))
        for host,origin,site in [('attacker.example:8000',None,None),('127.0.0.1:8000','https://attacker.example',None),('127.0.0.1:8000','null',None),('127.0.0.1:8000',None,'cross-site'),('127.0.0.1:8001',None,None)]:
            self.assertFalse(valid_request(host,8000,origin,site))
    def test_sensitive_routes_require_session_and_cross_site_is_rejected(self):
        handler=object.__new__(app.Handler);handler.server=SimpleNamespace(server_port=8000,access_control=self.access)
        handler.headers=Message();handler.headers['Host']='127.0.0.1:8000'
        responses=[];handler.respond=lambda code,body:responses.append(code)
        for route in ('/api/state','/api/carteira','/api/backup','/api/agenda-backup','/api/sped-report?id=1'):
            handler.path=route;self.assertFalse(handler.guard());self.assertEqual(responses[-1],401)
        cookie=self.setup();handler.headers['Cookie']=cookie;handler.path='/api/state';self.assertTrue(handler.guard())
        handler.headers['Origin']='https://attacker.example';self.assertFalse(handler.guard());self.assertEqual(responses[-1],403)

if __name__=='__main__':unittest.main()
