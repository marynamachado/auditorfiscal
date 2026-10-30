"""Proteção de acesso local. Senha não criptografa o arquivo SQLite."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time
from http.cookies import SimpleCookie

ITERATIONS=600_000
IDLE_SECONDS=30*60

def valid_request(host,port,origin=None,fetch_site=None):
    allowed={'127.0.0.1:'+str(port),'localhost:'+str(port)}
    if port==80:allowed.update(('127.0.0.1','localhost'))
    return host in allowed and fetch_site!='cross-site' and (not origin or origin=='http://'+host)

class Access:
    def __init__(self,path,port,demo=False,clock=time.monotonic):
        self.path=Path(path);self.demo=demo;self.clock=clock;self.cookie_name='auditor_session_'+str(port)
        self.sessions={};self.failures=[];self.lock=threading.RLock()
    def config(self):
        if not self.path.exists():return None
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data['algorithm']!='pbkdf2-sha256' or data['iterations']!=ITERATIONS:raise ValueError()
            if len(base64.b64decode(data['salt'],validate=True))!=32 or len(base64.b64decode(data['digest'],validate=True))!=32:raise ValueError()
            return data
        except (OSError,ValueError,KeyError,TypeError):raise ValueError('A configuração de acesso está inválida. Seus dados foram preservados; solicite suporte local.') from None
    def token(self,cookie):
        try:
            parsed=SimpleCookie();parsed.load(cookie or '')
            return parsed[self.cookie_name].value if self.cookie_name in parsed else ''
        except Exception:return ''
    def authenticated(self,cookie,touch=True):
        if self.demo:return True
        now=self.clock();token=self.token(cookie)
        with self.lock:
            entry=self.sessions.get(token)
            if not entry:return False
            if now-entry['active']>=IDLE_SECONDS or now-entry['created']>=8*60*60:
                self.sessions.pop(token,None);return False
            if touch:entry['active']=now
            return True
    def status(self,cookie):
        return {'authenticated':self.authenticated(cookie,touch=False),'setup_required':not self.demo and self.config() is None,'demo':self.demo,'idle_minutes':30}
    def new_session(self):
        now=self.clock();token=secrets.token_urlsafe(32)
        with self.lock:
            self.sessions={k:v for k,v in self.sessions.items() if now-v['active']<IDLE_SECONDS}
            if len(self.sessions)>=32:self.sessions.pop(next(iter(self.sessions)))
            self.sessions[token]={'created':now,'active':now}
        return self.cookie_name+'='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'
    def logout(self,cookie):
        with self.lock:self.sessions.pop(self.token(cookie),None)
        return self.cookie_name+'=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
    def password_ok(self,password):
        return isinstance(password,str) and 12<=len(password)<=128
    def write_password(self,password):
        if not self.password_ok(password):raise ValueError('Escolha uma senha com 12 a 128 caracteres. Uma frase longa é uma boa opção.')
        salt=secrets.token_bytes(32)
        digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,ITERATIONS)
        data={'algorithm':'pbkdf2-sha256','iterations':ITERATIONS,'salt':base64.b64encode(salt).decode(),'digest':base64.b64encode(digest).decode()}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,prefix='.access-',suffix='.tmp',delete=False) as out:
                temporary=out.name;json.dump(data,out);out.flush();os.fsync(out.fileno())
            os.chmod(temporary,0o600);os.replace(temporary,self.path)
        finally:
            if temporary and os.path.exists(temporary):os.unlink(temporary)
        self.sessions.clear()
    def verify(self,password):
        if not isinstance(password,str) or len(password)>128:return False
        cfg=self.config()
        if not cfg:return False
        value=hashlib.pbkdf2_hmac('sha256',password.encode(),base64.b64decode(cfg['salt']),cfg['iterations'])
        return hmac.compare_digest(value,base64.b64decode(cfg['digest']))
    def setup(self,password,confirmation):
        with self.lock:
            if self.demo:raise ValueError('A demonstração usa somente dados fictícios e não cadastra senhas.')
            if self.config() is not None:raise ValueError('Já existe uma senha. Use Entrar.')
            if password!=confirmation:raise ValueError('As senhas não coincidem.')
            self.write_password(password)
            return self.new_session()
    def login(self,password):
        with self.lock:
            self.checked_password(password)
            return self.new_session()
    def checked_password(self,password):
        now=self.clock();self.failures=[t for t in self.failures if now-t<60]
        if len(self.failures)>=5:raise ValueError('Muitas tentativas. Aguarde um minuto antes de tentar novamente.')
        if not self.verify(password):
            self.failures.append(now);raise ValueError('Senha incorreta.')
        self.failures.clear()
    def change(self,current,password,confirmation):
        with self.lock:
            self.checked_password(current)
            if password!=confirmation:raise ValueError('As novas senhas não coincidem.')
            self.write_password(password)
            return self.new_session()
