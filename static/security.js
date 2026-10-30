let currentAccess=null,accessTimer=null,lastAccessPing=0;
function accessActivity(){
 if(!currentAccess?.authenticated||currentAccess.demo)return;
 clearTimeout(accessTimer);accessTimer=setTimeout(()=>lockOffice().catch(()=>{}),30*60*1000);
 if(Date.now()-lastAccessPing>5*60*1000){lastAccessPing=Date.now();fiscalRequest('/api/touch',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).catch(()=>{});}
}
function showAccess(status){
 clearTimeout(accessTimer);currentAccess=status;state={};document.body.classList.remove('demo-mode');$('#message').textContent='';$('header .badge').textContent='● Acesso bloqueado';$('#nav').replaceChildren();$('#title').textContent=status.setup_required?'Proteja seu escritório':'Que bom ter você por aqui';
 $('#session-actions').hidden=true;$('#content').innerHTML=`<div class="access-card panel"><span class="eyebrow">SEU ESPAÇO DE TRABALHO</span><h2>${status.setup_required?'Crie sua senha de acesso':'Entre com tranquilidade'}</h2><p class="muted">${status.setup_required?'No primeiro acesso, escolha uma senha para proteger a abertura dos seus dados neste programa. Use de 12 a 128 caracteres; uma frase longa pode ser mais fácil de lembrar.':'Digite sua senha para abrir o escritório. A sessão é bloqueada após 30 minutos sem atividade.'}</p><form id="access-form" method="post"><label>Senha<input name="password" type="password" autocomplete="${status.setup_required?'new-password':'current-password'}" minlength="${status.setup_required?'12':'1'}" maxlength="128" required></label>${status.setup_required?'<label>Confirme sua senha<input name="confirmation" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label>':''}<button>${status.setup_required?'Criar senha e entrar':'Entrar'}</button></form><p id="access-error" role="alert"></p><p class="muted">A senha protege o acesso pelo programa. O arquivo do banco e os backups não são criptografados: proteja também a conta do Windows e o disco. Guarde sua senha em local seguro; não a envie pelo chat.</p></div>`;
 $('#access-form [name=password]').focus();
}
async function ensureAccess(){
 const status=await fiscalRequest('/api/session');currentAccess=status;
 if(!status.authenticated){showAccess(status);return false}
 $('#session-actions').hidden=!!status.demo;accessActivity();return true;
}
async function lockOffice(){
 clearTimeout(accessTimer);
 try{await fiscalRequest('/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})}finally{showAccess({authenticated:false,setup_required:false,demo:false});$('#message').textContent='Acesso bloqueado. Entre novamente para continuar.';}
}
function renderSecurity(){
 const demo=currentAccess?.demo;
 return panel('Cuidado com os seus dados',`<p>Seu escritório merece um espaço organizado e protegido.</p><ul class="security-list"><li><b>Acesso local:</b> o servidor aceita conexões somente do próprio computador.</li><li><b>${demo?'Demonstração isolada':'Senha de acesso'}:</b> ${demo?'este modo usa apenas o banco de teste e não cadastra senhas.':'senha armazenada como hash com sal; sessões expiram e o botão Bloquear encerra o acesso.'}</li><li><b>Proteção no navegador:</b> pedidos vindos de outros sites e endereços inesperados são recusados.</li><li><b>Sem serviços externos de frases ou fontes:</b> o visual e as mensagens são carregados do próprio programa.</li></ul><p class="review">Nenhum sistema garante risco zero. A senha do programa não criptografa o banco. Quem tiver acesso aos arquivos do computador pode lê-los com outras ferramentas.</p>`)
 +panel('Backup completo do escritório',`<p>Baixe uma cópia consistente do banco, incluindo empresas, notas, XMLs, carteira e histórico. O backup da carteira continua disponível para exportar somente a agenda.</p><p class="muted">O ZIP contém dados fiscais e <b>não é criptografado</b>. Salve em um local protegido, preferencialmente com criptografia do Windows ou de uma unidade de backup. Não publique o arquivo em repositórios ou links abertos.</p><a class="button-link" href="/api/backup">Baixar backup completo</a><p class="muted">Para restaurar, feche o programa, guarde uma cópia do banco atual e siga o arquivo RESTAURAR.txt do ZIP. A senha não faz parte desse backup.</p>`)
 +(demo?'':panel('Trocar senha',`<form id="password-form" method="post"><label>Senha atual<input name="current" type="password" autocomplete="current-password" required></label><label>Nova senha<input name="password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><label>Confirme a nova senha<input name="confirmation" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><button>Atualizar senha</button></form><p class="muted">A troca encerra outras sessões abertas do programa.</p>`))
 +panel('Cuidados no computador e na futura versão online','<ul class="security-list"><li>Use uma conta individual do Windows, bloqueie a tela ao se afastar e mantenha o sistema atualizado.</li><li>Ative a Criptografia do dispositivo ou BitLocker, quando disponível, e proteja a chave de recuperação.</li><li>Guarde backups em um local separado e protegido; confira periodicamente se consegue restaurar uma cópia de teste.</li><li>Esta versão é local e usa uma senha por instalação. Antes de colocá-la online, precisaremos de HTTPS, usuários e permissões por escritório, proteção de infraestrutura e uma revisão de segurança específica.</li></ul>');
}
document.addEventListener('submit',async event=>{
 const form=event.target;if(!['access-form','password-form'].includes(form.id))return;
 event.preventDefault();const button=form.querySelector('button');button.disabled=true;
 try{
  const data=Object.fromEntries(new FormData(form));const action=form.id==='password-form'?'password':currentAccess.setup_required?'setup':'login';
  await fiscalRequest('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  form.reset();await load();$('#message').className='success';$('#message').textContent=action==='password'?'Senha atualizada. Outras sessões foram encerradas.':'Acesso liberado. Um bom dia de trabalho para você.';
 }catch(error){if(form.id==='access-form')$('#access-error').textContent=error.message;else failure(error)}finally{button.disabled=false}
});
document.addEventListener('click',event=>{if(event.target.closest('#lock-office'))lockOffice().catch(failure)});
for(const event of ['pointerdown','keydown'])document.addEventListener(event,accessActivity,{passive:true});
window.addEventListener('fiscal-session-expired',()=>{clearTimeout(accessTimer);showAccess({authenticated:false,setup_required:false,demo:false})});
window.addEventListener('message',event=>{if(event.origin!==location.origin)return;const frame=document.querySelector('.carteira-frame');if(event.source!==frame?.contentWindow)return;if(event.data?.type==='fiscal-activity')accessActivity();if(event.data?.type==='fiscal-session-expired')window.dispatchEvent(new Event('fiscal-session-expired'));});
