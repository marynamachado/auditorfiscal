
'use strict';const KEY='carteira.danillo.v1';let lastSavedJSON=null;let state={version:1,companies:[],tasks:[],checkins:{},notes:[]},group='all',page='cards';let activeTasks={},currentChecks=[],calendarDate=new Date(new Date().getFullYear(),new Date().getMonth(),1),selectedDay='',detailId='',returnDetail='',closureFilter='all';const $=id=>document.getElementById(id);function el(tag,text){const e=document.createElement(tag);e.textContent=text??'';return e}const uid=()=>globalThis.crypto?.randomUUID?.()||Date.now()+'-'+Math.random().toString(16).slice(2);function today(){let d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}function diff(d){if(!/^\d{4}-\d{2}-\d{2}$/.test(d||''))return null;let a=today().split('-').map(Number),b=d.split('-').map(Number);return Math.round((Date.UTC(b[0],b[1]-1,b[2])-Date.UTC(a[0],a[1]-1,a[2]))/86400000)}function dateBR(d){if(!d)return 'Sem data';let a=d.split('-');return a.length===3?`${a[2]}/${a[1]}/${a[0]}`:d}function done(t){return ['Concluída','Finalizada'].includes(t.status)}function info(t){if(done(t))return ['Finalizada','green'];let n=diff(t.due);if(n!==null&&n<0)return ['Atrasada','red'];if(n===0)return ['Vence hoje','yellow'];if(n!==null&&n<=3)return ['Vence em '+n+' dia(s)','yellow'];return [t.status==='Aguardando'?'Aguardando':'Pendente','']}let serverRevision=0;
function save(){try{
  ensurePortfolios(state);validateState(state);
  const request=new XMLHttpRequest();request.open('POST','/api/carteira',false);request.setRequestHeader('Content-Type','application/json');
  request.send(JSON.stringify({revision:serverRevision,state}));
  const result=JSON.parse(request.responseText);if(request.status!==200)throw Error(result.error||'Falha ao salvar');
  serverRevision=result.revision;lastSavedJSON=JSON.stringify(state);$('saveStatus').textContent='● Salvo no banco de dados';$('saveStatus').classList.remove('error');return true;
}catch(e){if(lastSavedJSON)state=JSON.parse(lastSavedJSON);$('saveStatus').textContent='⚠ Alteração não salva';$('saveStatus').classList.add('error');alert('Não foi possível salvar. '+e.message);return false}}
function company(id){return state.companies.find(c=>c.id===id)}function groupOf(c){return c.portfolioId||''}
function renderCustomTabs(){
  document.querySelectorAll('.custom-tab').forEach(x=>x.remove());
  let nav=$('mainTabs'),before=nav.querySelector('[data-page=agenda]');
  if(group!=='all'&&!state.portfolios.some(p=>p.id===group))group='all';
  state.portfolios.forEach(p=>{let b=button(p.name,'tab custom-tab'+(page==='cards'&&group===p.id?' active':''),()=>switchPage('cards',p.id));b.dataset.page='cards';b.dataset.group=p.id;nav.insertBefore(b,before)});
  nav.querySelector('[data-group="all"]').classList.toggle('active',page==='cards'&&group==='all');
}
function badge(text,kind=''){let n=el('span',text);n.className='tag '+kind;return n}function button(label,css,action){let b=el('button',label);b.className=css;b.type='button';b.onclick=action;return b}function switchPage(p,g){page=p;if(g)group=g;document.querySelectorAll('.section').forEach(x=>x.classList.toggle('active',x.id==='page-'+p));document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.page===p&&(p!=='cards'||x.dataset.group===group)));render()}document.querySelectorAll('.tab').forEach(x=>x.onclick=()=>switchPage(x.dataset.page,x.dataset.group));function reference(){return $('referenceMonth').value}function closureMonth(){return reference()||today().slice(0,7)}function closureKey(cid,period){return cid+'|'+period}function closureMarked(cid,period=closureMonth()){return !!(state.completions||{})[closureKey(cid,period)]}function monthPending(cid,period=closureMonth()){return state.tasks.filter(t=>t.company===cid&&t.period===period&&!done(t))}function closureDone(cid,period=closureMonth()){return closureMarked(cid,period)&&monthPending(cid,period).length===0}function invalidateClosure(t){if(!done(t)&&t.period&&state.completions)delete state.completions[closureKey(t.company,t.period)]}function tasksFor(c){let p=reference();return state.tasks.filter(t=>t.company===c.id&&(!p||t.period===p))}function colorFor(c){if(/^#[0-9a-f]{6}$/i.test(c.color||''))return c.color;let key=c.cnpj||c.nome||c.id,h=0;for(let x of key)h=(h*31+x.charCodeAt(0))>>>0;return 'hsl('+(h%360)+' 42% 53%)'}function filteredTasks(){let p=reference();return state.tasks.filter(t=>!p||t.period===p)}function monthIndex(ym){let m=/^(\d{4})-(0[1-9]|1[0-2])$/.exec(ym||'');return m?Number(m[1])*12+Number(m[2])-1:null}function monthString(n){let year=Math.floor(n/12),month=n%12+1;return String(year).padStart(4,'0')+'-'+String(month).padStart(2,'0')}function dueFor(idx,series){let m=idx+series.dueOffset,year=Math.floor(m/12),month=m%12+1,last=new Date(Date.UTC(year,month,0)).getUTCDate();return monthString(m)+'-'+String(Math.min(series.dueDay,last)).padStart(2,'0')}function makeFuture(){let changed=false;state.recurring=state.recurring||{};let current=monthIndex(today().slice(0,7));for(let series of Object.values(state.recurring)){if(!series.active)continue;let end=Math.max(current,series.startIndex)+12;let steps=0;while(series.nextIndex<=end&&steps++<1200){let idx=series.nextIndex,period=monthString(idx);if(!state.tasks.some(t=>t.seriesId===series.id&&t.period===period)){state.tasks.push({id:uid(),title:series.title,company:series.company,office:series.office||'',period,due:dueFor(idx,series),status:'Pendente',priority:series.priority,notes:series.notes,checks:(series.checks||[]).map(x=>({text:x.text,done:false})),seriesId:series.id,recurrenceOccurrence:period});invalidateClosure(state.tasks[state.tasks.length-1]);changed=true}series.nextIndex++;changed=true}}return changed}function render(){ensurePortfolios(state);if($('portfolioModal').open)renderPortfolioManager();state.notes=state.notes||[];state.checkins=state.checkins||{};state.completions=state.completions||{};renderCustomTabs();$('closurePeriod').textContent='Fechamento: '+closureMonth().split('-').reverse().join('/')+(reference()?'':' (mês atual)');$('totalClients').textContent=state.companies.length;$('lateCount').textContent=state.tasks.filter(t=>!done(t)&&diff(t.due)!==null&&diff(t.due)<0).length;$('soonCount').textContent=state.tasks.filter(t=>!done(t)&&diff(t.due)!==null&&diff(t.due)>=0&&diff(t.due)<=3).length;$('doneCount').textContent=state.tasks.filter(done).length;renderCards();renderAgenda();renderDaily();renderCalendar();renderCompletionSummary();if($('companyModal').open&&detailId)renderDetail()}
function showTask(t,card){let wrap=el('div');wrap.className='task';let check=el('input');check.type='checkbox';check.checked=done(t);check.setAttribute('aria-label','Finalizar '+t.title);check.onchange=()=>{t.status=check.checked?'Finalizada':'Pendente';invalidateClosure(t);save();render()};let content=el('div');content.className='task-main';let title=el('div',t.title);title.className='task-title'+(done(t)?' done':'');let ti=el('div');ti.className='task-info';let [text,kind]=info(t);ti.append(badge(text,kind),el('span',dateBR(t.due)));if(t.period)ti.append(el('span','· '+t.period));if(t.priority==='Alta')ti.append(badge('Alta prioridade','yellow'));if(t.seriesId)ti.append(badge('↻ Mensal',''));content.append(title,ti);let edit=button('Editar','task-edit',()=>openTask(t.company,t.id));wrap.append(check,content,edit);card.append(wrap)}function renderCards(){let out=$('cards');out.replaceChildren();let q=$('search').value.trim().toLowerCase(),filter=$('statusFilter').value;let list=state.companies.filter(c=>{let g=groupOf(c);let ingroup=group==='all'||group===g;return ingroup&&(closureFilter==='all'||(closureFilter==='done'&&closureDone(c.id))||(closureFilter==='open'&&!closureDone(c.id)))&&(!q||searchMatches(c,q))}).sort((a,b)=>{const score=c=>{let ds=tasksFor(c).filter(t=>!done(t)&&diff(t.due)!==null).map(t=>diff(t.due));return ds.length?Math.min(...ds):99999};return score(a)-score(b)||a.nome.localeCompare(b.nome,'pt-BR')});$('noCards').textContent=list.length?'':'Nenhum cliente nesta carteira. Use “Cadastrar cliente” para adicionar.';list.forEach(c=>{let allTasks=tasksFor(c);let tasks=allTasks.filter(t=>!filter||(filter==='done'&&done(t))||(filter==='pending'&&!done(t))||(filter==='late'&&!done(t)&&diff(t.due)!==null&&diff(t.due)<0));if(filter&&!tasks.length)return;let card=el('article');card.className='card';let companyFinished=closureDone(c.id);if(companyFinished){card.classList.add('company-done');let complete=el('div','✓ Fechamento marcado como finalizado · '+closureMonth().split('-').reverse().join('/'));complete.className='completion-banner';card.append(complete)}card.addEventListener('click',e=>{if(!e.target.closest('button,input,select,textarea,a,label'))openDetail(c.id)});card.style.setProperty('--company-color',colorFor(c));card.style.setProperty('--company-bg','color-mix(in srgb, '+colorFor(c)+' 13%, white)');let overdue=allTasks.filter(t=>!done(t)&&diff(t.due)!==null&&diff(t.due)<0).length;if(overdue){card.classList.add('overdue');let warning=el('div','⚠ '+overdue+' demanda(s) atrasada(s)');warning.className='overdue-banner';card.append(warning)}let top=el('div');top.className='cardtop';let row=el('div');row.className='cardtitle';let icon=el('div',(c.nome||'?').slice(0,1).toUpperCase());icon.className='badge-icon';let names=el('div');names.style='flex:1;min-width:0';let name=button(c.nome,'company-name company-open',()=>openDetail(c.id));let meta=el('div',(c.cnpj||'CNPJ não informado')+' · '+(c.regime||'Regime não informado'));meta.className='company-meta';names.append(name,meta);let more=el('div','Abrir detalhes e finalizar demandas ↗');more.className='company-more';names.append(more);let edit=button('Editar','textbtn',()=>openClient(c.id));row.append(icon,names,edit);top.append(row);let m=el('div');m.style='margin-top:10px';let displayGroup=groupLabel(c);m.append(badge(displayGroup));top.append(m);if(c.fee!==''&&c.fee!==undefined&&c.fee!==null){let fee=el('div','Honorário combinado: '+Number(c.fee).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})+' / mês');fee.className='money';top.append(fee)}card.append(top);let body=el('div');body.className='tasklist';if(!tasks.length){let x=el('div','Nenhuma tarefa nesta empresa.');x.className='empty';body.append(x)}let ordered=[...tasks].sort((a,b)=>Number(done(a))-Number(done(b))||(a.due||'9999').localeCompare(b.due||'9999'));let visible=activeTasks[c.id]?ordered:ordered.slice(0,3);visible.forEach(t=>showTask(t,body));if(ordered.length>3)body.append(button(activeTasks[c.id]?'Mostrar menos':'Ver todas as '+ordered.length+' tarefas','textbtn',()=>{activeTasks[c.id]=!activeTasks[c.id];renderCards()}));card.append(body);let notes=state.notes.filter(n=>n.company===c.id);if(notes.length){let n=el('div');n.className='notes';notes.forEach(note=>{let box=el('div',note.text);box.className='note '+(['yellow','pink','blue','green'].includes(note.color)?note.color:'yellow');box.append(button('×','',()=>{if(confirm('Excluir esta anotação?')){state.notes=state.notes.filter(x=>x.id!==note.id);save();render()}}));n.append(box)});card.append(n)}let foot=el('div');foot.className='cardfoot';foot.append(button('Abrir empresa','btn ghost sm',()=>openDetail(c.id)),button('＋ Tarefa','btn light sm',()=>openTask(c.id)),button('✎ Nota','btn light sm',()=>openNote(c.id)));card.append(foot);out.append(card)});if(!out.children.length)$('noCards').textContent=closureFilter==='done'?'Nenhuma empresa marcada como finalizada nesta competência.':filter?'Nenhuma empresa com tarefa nesta situação.':'Nenhuma empresa nesta visualização.'}
function row(body,values){let tr=el('tr');for(let v of values){let td=el('td');v instanceof Node?td.append(v):td.textContent=v??'';tr.append(td)}body.append(tr)}function renderAgenda(){let out=$('agenda');out.replaceChildren();let ts=[...state.tasks].sort((a,b)=>(a.due||'9999').localeCompare(b.due||'9999'));$('agendaEmpty').textContent=ts.length?'':'Nenhuma tarefa cadastrada ainda.';ts.forEach(t=>{let [text,kind]=info(t);row(out,[dateBR(t.due),t.title,company(t.company)?.nome||'Empresa não encontrada',badge(text,kind),button('Editar','textbtn',()=>openTask(t.company,t.id))])})}const checks=['Revisar demandas atrasadas','Conferir documentos recebidos','Definir as prioridades do dia','Atualizar o andamento das tarefas'];function renderDaily(){let list=state.checkins[today()]||[];[$('checkins'),$('homeChecks')].forEach(box=>{box.replaceChildren();checks.forEach((s,i)=>{let l=el('label'),c=el('input');c.type='checkbox';c.checked=!!list[i];c.onchange=()=>{let v=state.checkins[today()]||[];v[i]=c.checked;state.checkins[today()]=v;if(save())renderDaily()};l.append(c,el('span',s));box.append(l)})});let home=$('homeTasks');home.replaceChildren();let current=state.tasks.filter(t=>!done(t)&&diff(t.due)!==null&&diff(t.due)<=0).sort((a,b)=>a.due.localeCompare(b.due));if(!current.length){let p=el('p','Nenhuma tarefa cadastrada para hoje ou em atraso.');p.className='home-empty';home.append(p)}current.slice(0,5).forEach(t=>{let item=el('div');item.className='home-task';let link=button(t.title+' · '+(company(t.company)?.nome||'Empresa não encontrada'),'textbtn',()=>openTask(t.company,t.id));let [text,kind]=info(t);item.append(link,badge(text,kind));home.append(item)});let urg=$('urgent');urg.replaceChildren();let listUrg=state.tasks.filter(t=>!done(t)&&diff(t.due)!==null&&diff(t.due)<=3).sort((a,b)=>a.due.localeCompare(b.due));if(!listUrg.length){let p=el('p','Nenhuma tarefa cadastrada com prazo próximo ou vencido.');p.className='muted';urg.append(p)}listUrg.slice(0,20).forEach(t=>{let p=el('p');p.style='padding:10px 0;border-bottom:1px solid #eef2f3';let [txt,k]=info(t);p.append(button(t.title+' · '+(company(t.company)?.nome||''),'textbtn',()=>openTask(t.company,t.id)),badge(txt,k));urg.append(p)})}
function openTask(cid='',id='',due=''){if($('companyModal').open){returnDetail=detailId;$('companyModal').close()} let f=$('taskForm');f.reset();let s=$('taskCompany');s.replaceChildren(new Option('Escolha uma empresa',''));[...state.companies].sort((a,b)=>a.nome.localeCompare(b.nome,'pt-BR')).forEach(c=>s.add(new Option(c.nome+' · '+groupLabel(c),c.id)));let t=state.tasks.find(x=>x.id===id);let recurring=t?.seriesId&&state.recurring?.[t.seriesId];$('repeatMonthly').checked=false;$('repeatBox').hidden=!!t?.seriesId;$('repeatActive').hidden=!recurring?.active;$('stopRepeat').dataset.series=recurring?.id||'';currentChecks=(t?.checks||[]).map(x=>({...x}));f.elements.checklist.value=currentChecks.map(x=>x.text).join('\n');let checkBox=$('taskChecks');checkBox.replaceChildren();if(currentChecks.length){checkBox.append(el('p','Marque as etapas concluídas:'));currentChecks.forEach((item,i)=>{let l=el('label');l.className='inline';let c=el('input');c.type='checkbox';c.checked=!!item.done;c.onchange=()=>currentChecks[i].done=c.checked;l.append(c,el('span',item.text));checkBox.append(l)})}f.elements.id.value=id;$('deleteTask').hidden=!t;f.elements.company.value=cid;if(!t){f.elements.due.value=due||'';f.elements.period.value=reference()||(due||today()).slice(0,7);}$('taskHeading').textContent=t?'Editar tarefa':'Nova tarefa';if(t){f.elements.title.value=t.title;f.elements.company.value=t.company;f.elements.due.value=t.due||'';f.elements.period.value=t.period||'';f.elements.status.value=done(t)?'Finalizada':t.status==='Aguardando'?'Aguardando':'Pendente';f.elements.priority.value=t.priority==='Alta'?'Alta':'Normal';f.elements.notes.value=t.notes||''}$('taskModal').showModal()}$('newTaskGlobal').onclick=()=>openTask();$('deleteTask').onclick=()=>{if(confirm('Excluir esta tarefa?')){state.tasks=state.tasks.filter(t=>t.id!==$('taskForm').elements.id.value);if(save()){$('taskModal').close();render();if(returnDetail){let x=returnDetail;returnDetail='';openDetail(x)}}}};$('taskForm').onsubmit=e=>{e.preventDefault();let f=e.target,v=Object.fromEntries(new FormData(f));if(!v.title.trim()||!company(v.company)){alert('Informe a tarefa e escolha uma empresa.');return}let i=state.tasks.findIndex(t=>t.id===v.id);let existing=i>=0?state.tasks[i]:{};let checks=v.checklist.split('\n').map(x=>x.trim()).filter(Boolean).map((text,i)=>({text,done:currentChecks[i]?.text===text?!!currentChecks[i].done:false}));let repeat=f.elements.repeatMonthly.checked&&!existing.seriesId;let refIndex=monthIndex(v.period),dueIndex=monthIndex((v.due||'').slice(0,7));if(repeat&&(refIndex===null||dueIndex===null||!/^\d{4}-\d{2}-\d{2}$/.test(v.due))){alert('Para repetir todo mês, informe a competência e a data de entrega.');return}let t={...existing,id:v.id||uid(),title:v.title.trim(),company:v.company,due:v.due,period:v.period,status:v.status,priority:v.priority,notes:v.notes.trim(),checks};if(repeat){state.recurring=state.recurring||{};let seriesId=uid();t.seriesId=seriesId;t.recurrenceOccurrence=v.period;state.recurring[seriesId]={id:seriesId,active:true,company:v.company,title:t.title,office:t.office||'',priority:t.priority,notes:t.notes,checks:t.checks,startIndex:refIndex,nextIndex:refIndex+1,dueOffset:dueIndex-refIndex,dueDay:Number(v.due.slice(8,10))}}if(existing.seriesId&&(t.company!==existing.company||t.period!==existing.period)){alert('Em uma tarefa mensal, mantenha a empresa e a competência. Para outro mês ou cliente, crie uma nova tarefa.');return}if(i>=0)state.tasks[i]=t;else state.tasks.push(t);invalidateClosure(t);if(repeat)makeFuture();if(save()){$('taskModal').close();render();if(returnDetail){let x=returnDetail;returnDetail='';openDetail(x)}}};
$('stopRepeat').onclick=()=>{let id=$('stopRepeat').dataset.series,series=state.recurring?.[id];if(!series)return;if(confirm('Interromper a criação de novos meses? As tarefas já criadas continuarão na agenda.')){series.active=false;if(save()){alert('Repetição interrompida. Os meses já criados continuam na agenda.');$('repeatActive').hidden=true}}};function openClient(id=''){
  if($('companyModal').open){returnDetail=detailId;$('companyModal').close()}
  let f=$('clientForm');f.reset();let c=company(id);f.elements.id.value=id;
  $('clientHeading').textContent=c?'Editar cliente':'Cadastrar cliente';$('deleteClient').hidden=!c;
  if(c){for(let name of ['nome','cnpj','regime','contact','phone','email'])f.elements[name].value=c[name]||'';f.elements.fee.value=c.fee??'';f.elements.color.value=/^#[0-9a-f]{6}$/i.test(c.color||'')?c.color:'#5d9c92'}
  populateClientPortfolios(c?.portfolioId||(group!=='all'?group:state.portfolios.find(p=>p.id==='portfolio-own')?.id)||state.portfolios[0]?.id||'__new__');
  $('clientModal').showModal();
}
$('addClientTop').onclick=()=>openClient();
$('clientGroup').onchange=clientPortfolioChanged;
$('clientForm').onsubmit=e=>{
  e.preventDefault();let f=e.target,v=Object.fromEntries(new FormData(f));
  if(!v.nome.trim()){alert('Preencha o nome do cliente.');return}
  if(v.cnpj.trim()&&state.companies.some(x=>x.id!==v.id&&normalizeDoc(x.cnpj)===normalizeDoc(v.cnpj))){alert('Já existe um cliente com este CNPJ. Edite o cadastro existente.');return}
  let selected;
  try{selected=v.grupo==='__new__'?createPortfolio(v.otherGroup):state.portfolios.find(p=>p.id===v.grupo);if(!selected)throw Error('Escolha uma carteira para o cliente.')}catch(err){alert(err.message);return}
  let c=company(v.id);if(!c){c={id:uid(),origem:'Cadastro manual'};state.companies.push(c)}
  Object.assign(c,{nome:v.nome.trim(),cnpj:v.cnpj.trim(),regime:v.regime.trim(),contact:v.contact.trim(),phone:v.phone.trim(),email:v.email.trim(),portfolioId:selected.id,grupo:selected.name,fee:v.fee===''?'':Number(v.fee),color:v.color});
  if(save()){
    if(page==='cards'&&group!=='all')group=selected.id;
    $('clientModal').close();render();showToast('Cliente salvo em '+selected.name+'.');
    if(returnDetail){let x=returnDetail;returnDetail='';openDetail(x)}
  }
};
function openNote(cid){if($('companyModal').open){returnDetail=detailId;$('companyModal').close()}let f=$('noteForm');f.reset();f.elements.company.value=cid;$('noteCompany').textContent=company(cid)?.nome||'';$('noteModal').showModal()}$('noteForm').onsubmit=e=>{e.preventDefault();let v=Object.fromEntries(new FormData(e.target));if(!v.text.trim())return;state.notes.push({id:uid(),company:v.company,text:v.text.trim(),color:v.color});if(save()){$('noteModal').close();render();if(returnDetail){let x=returnDetail;returnDetail='';openDetail(x)}}};document.querySelectorAll('[data-close]').forEach(x=>x.onclick=()=>{let target=x.dataset.close;$(target).close();if(returnDetail&&target!=='companyModal'){let id=returnDetail;returnDetail='';openDetail(id)}});$('search').oninput=renderCards;$('statusFilter').onchange=renderCards;
function backup(){let blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='backup_carteira_danillo_'+today()+'.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}$('backupBtn').onclick=backup;$('export').onclick=backup;$('restore').onclick=async()=>{
  let f=$('backupFile').files[0];if(!f){alert('Escolha um arquivo de backup.');return}
  try {
    if(f.size>5000000)throw Error('O arquivo excede 5 MB.');
    let v=validateState(JSON.parse(await f.text()));
    if(!confirm('O backup substituirá os dados atuais. Uma cópia de segurança dos dados atuais será baixada antes. Continuar?'))return;
    backup();state=v;makeFuture();
    if(save()){returnDetail='';detailId='';$('search').value='';$('statusFilter').value='';closureFilter='all';['clientsAll','clientsOpen','clientsDone'].forEach((name,i)=>$(name).classList.toggle('active',i===0));switchPage('cards','all');showToast('Backup restaurado com sucesso.');}
  }catch(e){alert('Não foi possível restaurar: '+e.message)}
};

function openDetail(id){if(!company(id))return;detailId=id;renderDetail();if(!$('companyModal').open)$('companyModal').showModal()}
function renderDetail(){let c=company(detailId);if(!c)return;let all=tasksFor(c),pending=all.filter(t=>!done(t)),ref=reference();$('detailName').textContent=c.nome;$('detailGroup').textContent=groupLabel(c);$('detailContact').textContent=[c.cnpj&&('CNPJ: '+c.cnpj),c.contact&&('Contato: '+c.contact),c.phone&&('Telefone: '+c.phone),c.email].filter(Boolean).join(' · ');$('detailReference').textContent=ref?'Competência selecionada: '+ref:'Todas as competências, inclusive tarefas sem mês';$('detailSummary').textContent=all.length+' tarefa(s) nesta visualização · '+pending.length+' pendente(s) · '+(all.length-pending.length)+' finalizada(s)';let list=$('detailTasks');list.replaceChildren();if(!all.length){let p=el('p','Nenhuma tarefa para esta empresa nesta competência.');p.className='empty';list.append(p)}all.sort((a,b)=>Number(done(a))-Number(done(b))||(a.due||'9999').localeCompare(b.due||'9999')).forEach(t=>showTask(t,list));let notes=$('detailNotes');notes.replaceChildren();state.notes.filter(n=>n.company===c.id).forEach(n=>{let box=el('div',n.text);box.className='note '+(['yellow','pink','blue','green'].includes(n.color)?n.color:'yellow');notes.append(box)});let period=closureMonth(),monthTasks=monthPending(c.id,period),marked=closureDone(c.id,period);$('detailDone').disabled=false;$('detailDone').textContent='✓ Finalizar tarefas de '+period.split('-').reverse().join('/');$('detailDone').title='Finaliza somente tarefas pendentes desta competência';$('markCompany').textContent=marked?'↶ Reabrir fechamento '+period.split('-').reverse().join('/'):'✓ Marcar empresa finalizada em '+period.split('-').reverse().join('/');let explain=el('p',marked?'Fechamento marcado como finalizado para '+period+'.':'Fechamento de '+period+': '+monthTasks.length+' tarefa(s) pendente(s).');explain.className='focus-card';list.prepend(explain)}
$('detailAddTask').onclick=()=>openTask(detailId);$('detailAddNote').onclick=()=>openNote(detailId);$('detailEdit').onclick=()=>openClient(detailId);$('detailDone').onclick=()=>{
  let ref=closureMonth(),tasks=monthPending(detailId,ref);
  if(!tasks.length){showToast('Nenhuma tarefa pendente para '+ref.split('-').reverse().join('/')+'.');return}
  tasks.forEach(t=>t.status='Finalizada');
  if(save()){render();showToast(tasks.length+' tarefa(s) finalizada(s). Você pode desmarcá-las para reabrir.');}
};
$('markCompany').onclick=()=>{
  let ref=closureMonth(),key=closureKey(detailId,ref);state.completions=state.completions||{};
  if(closureDone(detailId,ref)){delete state.completions[key];if(save()){render();showToast('Fechamento reaberto.');}return}
  let pending=monthPending(detailId,ref);
  if(pending.length){showToast('Finalize as '+pending.length+' tarefa(s) deste mês antes de fechar a empresa.');return}
  state.completions[key]={markedAt:new Date().toISOString()};
  if(save()){$('companyModal').close();closureFilter='open';['clientsAll','clientsOpen','clientsDone'].forEach((name,j)=>$(name).classList.toggle('active',j===1));render();showToast('Empresa finalizada. Consulte a aba Finalizadas.');}
};

function renderCalendar(){let title=$('calTitle'),grid=$('calendarGrid'),year=calendarDate.getFullYear(),month=calendarDate.getMonth();title.textContent=calendarDate.toLocaleDateString('pt-BR',{month:'long',year:'numeric'});grid.replaceChildren();['D','S','T','Q','Q','S','S'].forEach(x=>{let d=el('div',x);d.className='cal-week';grid.append(d)});let start=new Date(year,month,1).getDay(),days=new Date(year,month+1,0).getDate();for(let i=0;i<start;i++)grid.append(el('span'));for(let i=1;i<=days;i++){let d=year+'-'+String(month+1).padStart(2,'0')+'-'+String(i).padStart(2,'0');let b=button(String(i),'cal-day',()=>{selectedDay=d;renderCalendar()});if(d===selectedDay)b.classList.add('selected');if(d===today())b.classList.add('is-today');let count=filteredTasks().filter(t=>t.due===d).length;if(count)b.classList.add('has');b.setAttribute('aria-label',dateBR(d)+' — '+count+' tarefa(s)');grid.append(b)}$('calendarSelected').textContent='Demandas em '+dateBR(selectedDay);let list=$('calendarTasks');list.replaceChildren();let day=filteredTasks().filter(t=>t.due===selectedDay);if(!day.length){let p=el('p','Nenhuma demanda cadastrada para este dia.');p.className='muted';list.append(p)}day.forEach(t=>{let p=el('div');p.className='calendar-task';let b=button(t.title,'textbtn',()=>openTask(t.company,t.id));let [label,kind]=info(t);p.append(b,el('span',(company(t.company)?.nome||'Empresa não encontrada')+' · '),badge(label,kind));list.append(p)})}
['clientsAll','clientsOpen','clientsDone'].forEach((id,i)=>$(id).onclick=()=>{closureFilter=['all','open','done'][i];['clientsAll','clientsOpen','clientsDone'].forEach((name,j)=>$(name).classList.toggle('active',j===i));renderCards()});
$('calPrev').onclick=()=>{calendarDate=new Date(calendarDate.getFullYear(),calendarDate.getMonth()-1,1);selectedDay=calendarDate.getFullYear()+'-'+String(calendarDate.getMonth()+1).padStart(2,'0')+'-01';renderCalendar()};$('calNext').onclick=()=>{calendarDate=new Date(calendarDate.getFullYear(),calendarDate.getMonth()+1,1);selectedDay=calendarDate.getFullYear()+'-'+String(calendarDate.getMonth()+1).padStart(2,'0')+'-01';renderCalendar()};$('calendarAdd').onclick=()=>openTask('','',selectedDay);$('referenceMonth').onchange=()=>{let p=reference();$('referenceHint').textContent=p?'Exibindo apenas a competência '+p+'. Tarefas sem competência ficam ocultas neste filtro.':'Exibindo todas as competências, inclusive tarefas sem mês informado.';render()};$('clearReference').onclick=()=>{$('referenceMonth').value='';$('referenceMonth').dispatchEvent(new Event('change'))};
function calculate(expression){let src=expression.replace(/\s/g,'').replace(/,/g,'.').replace(/×/g,'*').replace(/÷/g,'/');if(!src||src.length>100||/[^0-9.+*/()\-]/.test(src))throw Error('Conta inválida');let pos=0;function factor(){if(src[pos]==='+'){pos++;return factor()}if(src[pos]==='-'){pos++;return -factor()}if(src[pos]==='('){pos++;let n=add();if(src[pos++]!==')')throw Error('Parênteses incompletos');return n}let m=src.slice(pos).match(/^(?:\d+(?:\.\d*)?|\.\d+)/);if(!m)throw Error('Conta incompleta');pos+=m[0].length;return Number(m[0])}function mul(){let n=factor();while(src[pos]==='*'||src[pos]==='/'){let op=src[pos++],v=factor();if(op==='/'&&v===0)throw Error('Não é possível dividir por zero');n=op==='*'?n*v:n/v}return n}function add(){let n=mul();while(src[pos]==='+'||src[pos]==='-'){let op=src[pos++],v=mul();n=op==='+'?n+v:n-v}return n}let result=add();if(pos!==src.length||!Number.isFinite(result))throw Error('Conta inválida');return Number(result.toPrecision(12)).toString().replace('.',',')}
const calcButtons=['7','8','9','÷','4','5','6','×','1','2','3','−','C','0',',','+','(',')','⌫','='];calcButtons.forEach(value=>{let b=button(value,'',()=>{let input=$('calcDisplay');$('calcError').textContent='';if(value==='C')input.value='';else if(value==='⌫')input.value=input.value.slice(0,-1);else if(value==='='){try{input.value=calculate(input.value)}catch(e){$('calcError').textContent=e.message}}else input.value+=(value==='−'?'-':value);input.focus()});if(['÷','×','−','+'].includes(value))b.className='op';if(value==='=')b.className='equals';$('calcKeys').append(b)});$('calcDisplay').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();try{$('calcDisplay').value=calculate($('calcDisplay').value);$('calcError').textContent=''}catch(err){$('calcError').textContent=err.message}}});

function normalizeDoc(v){return String(v||'').replace(/[^a-z0-9]/gi,'').toUpperCase()}
function normalized(v){return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()}
function searchMatches(c,q){return normalized([c.nome,c.cnpj,c.contact,c.phone,c.email].join(' ')).includes(normalized(q))||(/^[\d.\/-]+$/.test(q)&&normalizeDoc(c.cnpj).includes(normalizeDoc(q)))}
function groupLabel(c){return state.portfolios?.find(p=>p.id===c.portfolioId)?.name||c.grupo||legacyPortfolioName(c.origem||'Clientes próprios')}
let toastTimer;
function showToast(message){let box=$('toast');box.textContent=message;box.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>box.hidden=true,5000)}
function validateState(v){
  const fail=message=>{throw Error(message)};
  const object=x=>!!x&&typeof x==='object'&&!Array.isArray(x);
  const str=(x,max=2000)=>typeof x==='string'&&x.length<=max;
  const optionalString=x=>x===undefined||x===null||str(x,1000000);
  const dateOK=x=>!x||(/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T12:00:00Z'))&&new Date(x+'T12:00:00Z').toISOString().slice(0,10)===x);
  if(!object(v)||v.version!==1||!Array.isArray(v.companies)||!Array.isArray(v.tasks))fail('Este arquivo não é um backup compatível da agenda.');
  if(v.companies.length>10000||v.tasks.length>100000)fail('O backup excede o limite de registros.');
  const ids=new Set(),taskIds=new Set(),noteIds=new Set();
  for(const c of v.companies){
    if(!object(c)||!str(c.id,200)||!c.id||ids.has(c.id)||!str(c.nome,500)||!c.nome.trim())fail('Há um cadastro de cliente inválido ou duplicado.');
    for(const k of ['cnpj','regime','grupo','origem','color','contact','phone','email','portfolioId'])if(!optionalString(c[k]))fail('Dados inválidos no cadastro de cliente.');
    if(c.fee!==undefined&&c.fee!==null&&c.fee!==''&&(!Number.isFinite(Number(c.fee))||Number(c.fee)<0))fail('Honorário inválido.');
    ids.add(c.id);
  }
  const checkList=arr=>Array.isArray(arr)&&arr.every(x=>object(x)&&str(x.text,1000000)&&typeof x.done==='boolean');
  for(const t of v.tasks){
    if(!object(t)||!str(t.id,200)||!t.id||taskIds.has(t.id)||!ids.has(t.company)||!str(t.title,500)||!t.title.trim())fail('Há uma tarefa inválida ou sem cliente correspondente.');
    if(!['Pendente','Aguardando','Finalizada','Concluída'].includes(t.status)||!optionalString(t.due)||!dateOK(t.due)||!optionalString(t.period)||(t.period&&monthIndex(t.period)===null))fail('Situação, data ou competência inválida.');
    if(t.checks!==undefined&&!checkList(t.checks))fail('Checklist inválido.');
    if(!optionalString(t.notes)||!optionalString(t.seriesId)||!optionalString(t.priority))fail('Dados inválidos na tarefa.');
    taskIds.add(t.id);
  }
  if(v.notes!==undefined&&!Array.isArray(v.notes))fail('Anotações inválidas.');
  for(const n of v.notes||[]){if(!object(n)||!str(n.id,200)||!n.id||noteIds.has(n.id)||!ids.has(n.company)||!str(n.text)||!optionalString(n.color))fail('Anotação inválida.');noteIds.add(n.id)}
  for(const k of ['recurring','completions','checkins'])if(v[k]!==undefined&&!object(v[k]))fail('Dados de '+k+' inválidos.');
  for(const [key,series] of Object.entries(v.recurring||{})){
    if(!object(series)||series.id!==key||!ids.has(series.company)||!str(series.title,500)||typeof series.active!=='boolean'||!Number.isInteger(series.startIndex)||!Number.isInteger(series.nextIndex)||series.startIndex<12000||series.nextIndex<=series.startIndex||series.nextIndex>120000||!Number.isInteger(series.dueOffset)||Math.abs(series.dueOffset)>120||!Number.isInteger(series.dueDay)||series.dueDay<1||series.dueDay>31||(series.checks!==undefined&&!checkList(series.checks)))fail('Repetição mensal inválida.');
  }
  for(const [day,values] of Object.entries(v.checkins||{}))if(!dateOK(day)||!day||!Array.isArray(values)||!values.every(x=>x===null||typeof x==='boolean'))fail('Check-in diário inválido.');
  for(const [key,value] of Object.entries(v.completions||{})){let split=key.lastIndexOf('|');if(split<1||!ids.has(key.slice(0,split))||monthIndex(key.slice(split+1))===null||!object(value)||!str(value.markedAt,100))fail('Fechamento inválido.');}
  if(v.portfolios!==undefined){
    if(!Array.isArray(v.portfolios)||v.portfolios.length>10000)fail('Lista de carteiras inválida.');
    const portfolioIds=new Set(),portfolioNames=new Set();
    for(const p of v.portfolios){if(!object(p)||!str(p.id,200)||!p.id||['all','__new__'].includes(p.id)||portfolioIds.has(p.id)||!str(p.name,1000)||!p.name.trim()||portfolioNames.has(portfolioNameKey(p.name)))fail('Carteira inválida ou duplicada.');portfolioIds.add(p.id);portfolioNames.add(portfolioNameKey(p.name))}
    for(const c of v.companies)if(c.portfolioId&&!portfolioIds.has(c.portfolioId))fail('Cliente vinculado a uma carteira inexistente.');
  }
  return {...v,notes:v.notes||[],checkins:v.checkins||{},recurring:v.recurring||{},completions:v.completions||{}};
}
function removeClient(id){
  let c=company(id);if(!c)return;
  let count=state.tasks.filter(t=>t.company===id).length,noteCount=state.notes.filter(n=>n.company===id).length;
  if(!confirm('Excluir '+c.nome+' e seus '+count+' tarefa(s), '+noteCount+' anotação(ões) e fechamentos? Esta ação só pode ser desfeita restaurando um backup.'))return;
  backup();state.companies=state.companies.filter(x=>x.id!==id);state.tasks=state.tasks.filter(x=>x.company!==id);state.notes=state.notes.filter(x=>x.company!==id);
  state.recurring=Object.fromEntries(Object.entries(state.recurring||{}).filter(([,x])=>x.company!==id));
  state.completions=Object.fromEntries(Object.entries(state.completions||{}).filter(([key])=>!key.startsWith(id+'|')));
  if(save()){returnDetail='';detailId='';$('clientModal').close();$('companyModal').close();render();showToast('Cliente excluído. Guarde o backup gerado em Downloads.');}
};
$('deleteClient').onclick=()=>removeClient($('clientForm').elements.id.value);
$('detailDelete').onclick=()=>removeClient(detailId);
for(const dialogId of ['taskModal','clientModal','noteModal'])$(dialogId).addEventListener('cancel',e=>{e.preventDefault();$(dialogId).close();if(returnDetail){let id=returnDetail;returnDetail='';openDetail(id)}});
// Associate all form labels with their controls without changing the supplied layout.
document.querySelectorAll('label.field').forEach((label,index)=>{let control=label.nextElementSibling;if(control&&['INPUT','SELECT','TEXTAREA'].includes(control.tagName)){if(!control.id)control.id='field-'+index;label.htmlFor=control.id}});
let renderedDay=today();setInterval(()=>{if(today()!==renderedDay){renderedDay=today();if(makeFuture())save();$('today').textContent=new Date().toLocaleDateString('pt-BR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});render()}},60000);

function cleanPortfolioName(value){return String(value||'').trim().replace(/\s+/g,' ')}
function portfolioNameKey(value){return normalized(cleanPortfolioName(value))}
function legacyPortfolioName(name){return name==='Planilha Royal'?'Carteira Royal':name==='PDF fechamento setembro'?'Terceirizados':name==='Cadastro manual'?'Clientes próprios':name}
function ensurePortfolios(target){
  let changed=false;
  if(!Array.isArray(target.portfolios)){
    target.portfolios=[{id:'portfolio-royal',name:'Carteira Royal'},{id:'portfolio-outsourced',name:'Terceirizados'},{id:'portfolio-own',name:'Clientes próprios'}];changed=true;
  }
  for(const c of target.companies){
    let p=target.portfolios.find(x=>x.id===c.portfolioId);
    if(!p){let name=cleanPortfolioName(legacyPortfolioName(c.grupo||c.origem||'Clientes próprios'));p=target.portfolios.find(x=>portfolioNameKey(x.name)===portfolioNameKey(name));if(!p){p={id:'portfolio-'+uid(),name:name||'Clientes próprios'};target.portfolios.push(p)}c.portfolioId=p.id;changed=true}
    if(c.grupo!==p.name){c.grupo=p.name;changed=true}
  }
  return changed;
}
function validPortfolioName(value,id=''){
  let name=cleanPortfolioName(value);
  if(!name)throw Error('Digite um nome para a carteira.');
  if(name.length>80)throw Error('Use até 80 caracteres no nome da carteira.');
  if(state.portfolios.some(p=>p.id!==id&&portfolioNameKey(p.name)===portfolioNameKey(name)))throw Error('Já existe uma carteira com esse nome. Escolha a existente ou use outro nome.');
  return name;
}
function createPortfolio(value){let p={id:'portfolio-'+uid(),name:validPortfolioName(value)};state.portfolios.push(p);return p}
function renamePortfolio(id,value){
  let p=state.portfolios.find(x=>x.id===id);if(!p)throw Error('Carteira não encontrada.');
  p.name=validPortfolioName(value,id);
  state.companies.filter(c=>c.portfolioId===id).forEach(c=>c.grupo=p.name);
  return p;
}
function clientPortfolioChanged(){let isNew=$('clientGroup').value==='__new__';$('otherGroupBox').hidden=!isNew;$('newClientPortfolio').required=isNew;$('clientRenameGroup').hidden=isNew||!$('clientGroup').value}
function populateClientPortfolios(selected){
  const select=$('clientGroup');select.replaceChildren();
  state.portfolios.forEach(p=>select.add(new Option(p.name,p.id)));
  select.add(new Option('＋ Criar nova carteira','__new__'));
  select.value=selected==='__new__'||state.portfolios.some(p=>p.id===selected)?selected:state.portfolios[0]?.id||'__new__';clientPortfolioChanged();
}
function renderPortfolioManager(){
  let list=$('portfolioList');list.replaceChildren();
  state.portfolios.forEach(p=>{
    let row=el('div');row.className='portfolio-row';let info=el('div');
    let count=state.companies.filter(c=>c.portfolioId===p.id).length;
    info.append(el('strong',p.name),el('small',count===1?'1 cliente':count+' clientes'));
    let rename=button('Renomear','btn light sm',()=>openRenamePortfolio(p.id));rename.setAttribute('aria-label','Renomear '+p.name);
    row.append(info,rename);list.append(row);
  });
  if(!state.portfolios.length){let empty=el('p','Crie sua primeira carteira acima.');empty.className='muted';list.append(empty)}
}
function openRenamePortfolio(id){
  let p=state.portfolios.find(x=>x.id===id);if(!p)return;
  let f=$('renamePortfolioForm');f.elements.id.value=id;f.elements.name.value=p.name;
  let count=state.companies.filter(c=>c.portfolioId===id).length;
  $('renamePortfolioImpact').textContent='O novo nome será usado para '+count+' cliente(s) desta carteira. As tarefas e os fechamentos serão mantidos.';
  $('renamePortfolioError').textContent='';$('renamePortfolioModal').showModal();
}
$('managePortfolios').onclick=()=>{$('portfolioMessage').textContent='';$('portfolioForm').reset();renderPortfolioManager();$('portfolioModal').showModal()};
$('closePortfolioManager').onclick=()=>$('portfolioModal').close();
$('closeRenamePortfolio').onclick=()=>$('renamePortfolioModal').close();
$('cancelRenamePortfolio').onclick=()=>$('renamePortfolioModal').close();
$('clientRenameGroup').onclick=()=>openRenamePortfolio($('clientGroup').value);
$('portfolioForm').onsubmit=e=>{
  e.preventDefault();let selected=$('clientGroup').value;
  try{let p=createPortfolio(e.target.elements.name.value);if(save()){$('portfolioMessage').classList.remove('error');$('portfolioMessage').textContent='Carteira “'+p.name+'” criada. Ela já está disponível nas abas e nos cadastros.';e.target.reset();populateClientPortfolios(selected);render()}}
  catch(err){$('portfolioMessage').classList.add('error');$('portfolioMessage').textContent=err.message}
};
$('renamePortfolioForm').onsubmit=e=>{
  e.preventDefault();let selected=$('clientGroup').value;
  try{let p=renamePortfolio(e.target.elements.id.value,e.target.elements.name.value);if(save()){$('renamePortfolioModal').close();populateClientPortfolios(selected);$('portfolioMessage').classList.remove('error');$('portfolioMessage').textContent='Nome atualizado para “'+p.name+'”.';render();showToast('Carteira renomeada para '+p.name+'.')}}
  catch(err){$('renamePortfolioError').textContent=err.message}
};

// Read-only projections: a completed task is distinct from a marked monthly closing.
function completionSummary(data, month, portfolioId='all', clientId='all'){
  const clients=data.companies.filter(c=>(portfolioId==='all'||c.portfolioId===portfolioId)&&(clientId==='all'||c.id===clientId));
  const ids=new Set(clients.map(c=>c.id)), byClient=new Map(clients.map(c=>[c.id,[]]));
  let unassigned=0;
  for(const t of data.tasks){if(!ids.has(t.company))continue;if(!t.period)unassigned++;if(t.period===month)byClient.get(t.company).push(t)}
  const rows=clients.map(c=>{
    const tasks=byClient.get(c.id), completed=tasks.filter(done).length, pending=tasks.length-completed;
    return {client:c,tasks,completed,pending,closed:!!data.completions?.[c.id+'|'+month]&&pending===0};
  });
  const total=rows.reduce((n,r)=>n+r.tasks.length,0), completed=rows.reduce((n,r)=>n+r.completed,0), closed=rows.filter(r=>r.closed).length;
  return {rows,total,completed,pending:total-completed,closed,open:rows.length-closed,unassigned,percent:rows.length?Math.round(closed/rows.length*100):0};
}
function summaryMonthLabel(month){return month.split('-').reverse().join('/')}
function summaryTable(target,headers,rows){
  target.replaceChildren();
  if(!rows.length){const p=el('p','Nenhum registro para os filtros selecionados.');p.className='muted';target.append(p);return}
  const table=el('table'), head=el('thead'), tr=el('tr'), body=el('tbody');
  headers.forEach(h=>{const th=el('th',h);th.scope='col';tr.append(th)});head.append(tr);
  rows.forEach(cells=>{const row=el('tr');cells.forEach(value=>{const td=el('td');if(value instanceof Node)td.append(value);else td.textContent=String(value);row.append(td)});body.append(row)});
  table.append(head,body);target.append(table);
}
function summarySelect(select,entries,allLabel){
  const previous=select.value;select.replaceChildren(new Option(allLabel,'all'));
  entries.forEach(x=>select.add(new Option(x.label,x.id)));select.value=entries.some(x=>x.id===previous)?previous:'all';
}
function renderCompletionSummary(){
  if(page!=='summary')return;
  const monthInput=$('summaryMonth');if(!monthInput.value)monthInput.value=today().slice(0,7);
  summarySelect($('summaryPortfolio'),state.portfolios.map(p=>({id:p.id,label:p.name})),'Todas as carteiras');
  const portfolio=$('summaryPortfolio').value;
  summarySelect($('summaryClient'),state.companies.filter(c=>portfolio==='all'||c.portfolioId===portfolio).sort((a,b)=>a.nome.localeCompare(b.nome,'pt-BR')).map(c=>({id:c.id,label:c.nome})),'Todos os clientes');
  const client=$('summaryClient').value,month=monthInput.value,s=completionSummary(state,month,portfolio,client);
  $('summaryScope').textContent='Competência '+summaryMonthLabel(month)+' · '+s.rows.length+' cliente(s) nos filtros selecionados';
  const metrics=$('completionMetrics');metrics.replaceChildren();
  for(const [label,value,detail,kind] of [['Tarefas concluídas',s.completed,'de '+s.total+' tarefa(s) no mês','green'],['Tarefas pendentes',s.pending,'Inclui tarefas aguardando retorno','amber'],['Fechamentos finalizados',s.closed,s.open+' cliente(s) com fechamento aberto','green'],['Progresso dos fechamentos',s.percent+'%',s.closed+' de '+s.rows.length+' cliente(s)','']]){
    const box=el('div');box.className='metric '+kind;box.append(el('small',label),el('b',value),el('span',detail));metrics.append(box);
  }
  $('summaryUnassigned').hidden=!s.unassigned;$('summaryUnassigned').textContent=s.unassigned+' tarefa(s) sem competência não entram nos totais mensais. Para incluí-las, informe a competência ao editar a tarefa.';
  const portfolioRows=state.portfolios.filter(p=>portfolio==='all'||p.id===portfolio).map(p=>{
    const x=completionSummary(state,month,p.id,client);
    if(client!=='all'&&!x.rows.length)return null;
    return [button(p.name,'textbtn summary-link',()=>{$('summaryPortfolio').value=p.id;$('summaryClient').value='all';renderCompletionSummary()}),x.rows.length,x.completed+' / '+x.total,x.closed,x.open,x.percent+'%'];
  }).filter(Boolean);
  summaryTable($('summaryPortfolioTable'),['Carteira','Clientes','Tarefas concluídas','Fechamentos finalizados','Abertos','Progresso'],portfolioRows);
  summaryTable($('summaryClientTable'),['Cliente','Carteira','Concluídas','Pendentes','Fechamento'],s.rows.slice().sort((a,b)=>a.client.nome.localeCompare(b.client.nome,'pt-BR')).map(r=>[
    button(r.client.nome,'textbtn summary-link',()=>{$('summaryClient').value=r.client.id;renderCompletionSummary();$('summaryDetails').scrollIntoView({block:'nearest',behavior:'smooth'})}),
    state.portfolios.find(p=>p.id===r.client.portfolioId)?.name||'',r.completed,r.pending,badge(r.closed?'Finalizado':r.pending?'Aberto · com pendências':r.tasks.length?'Aberto · falta marcar':'Aberto · sem tarefas',r.closed?'green':'yellow')
  ]));
  const details=$('summaryDetails');details.hidden=client==='all';
  if(client!=='all'&&s.rows.length){
    const r=s.rows[0];$('summaryDetailTitle').textContent=r.client.nome+' · '+summaryMonthLabel(month);
    $('summaryDetailState').textContent=r.closed?'Fechamento marcado como finalizado.':r.pending?'Há tarefas pendentes. O fechamento permanece aberto.':'O fechamento ainda não foi marcado como finalizado.';
    summaryTable($('summaryTaskTable'),['Tarefa','Prazo','Situação'],r.tasks.slice().sort((a,b)=>Number(done(a))-Number(done(b))||(a.due||'9999').localeCompare(b.due||'9999')).map(t=>[t.title,dateBR(t.due),badge(done(t)?'Concluída':t.status==='Aguardando'?'Aguardando':'Pendente',done(t)?'green':'yellow')]));
  }
  const ids=new Set(s.rows.map(r=>r.client.id)),months=new Set([month]);
  state.tasks.forEach(t=>{if(ids.has(t.company)&&t.period)months.add(t.period)});
  Object.keys(state.completions||{}).forEach(key=>{const split=key.lastIndexOf('|');if(ids.has(key.slice(0,split)))months.add(key.slice(split+1))});
  summaryTable($('summaryHistoryTable'),['Competência','Tarefas concluídas','Pendentes','Fechamentos finalizados','Progresso'],[...months].sort().reverse().map(m=>{
    const x=completionSummary(state,m,portfolio,client);
    return [button(summaryMonthLabel(m)+(m===month?' · selecionada':''),'textbtn summary-link',()=>{monthInput.value=m;renderCompletionSummary()}),x.completed+' / '+x.total,x.pending,x.closed+' / '+x.rows.length,x.percent+'%'];
  }));
}
$('summaryMonth').onchange=renderCompletionSummary;
$('summaryPortfolio').onchange=()=>{$('summaryClient').value='all';renderCompletionSummary()};
$('summaryClient').onchange=renderCompletionSummary;
$('summaryReset').onclick=()=>{$('summaryMonth').value=today().slice(0,7);$('summaryPortfolio').value='all';$('summaryClient').value='all';renderCompletionSummary()};
$('summaryOpenClient').onclick=()=>{const id=$('summaryClient').value;if(!company(id))return;$('referenceMonth').value=$('summaryMonth').value;$('referenceMonth').dispatchEvent(new Event('change'));openDetail(id)};

async function init(){try{
  const response=await fetch('/api/carteira',{cache:'no-store'});if(!response.ok)throw Error('Não foi possível acessar o banco');
  const result=await response.json();serverRevision=result.revision;state=validateState(result.state);lastSavedJSON=JSON.stringify(state);
  if(ensurePortfolios(state)|makeFuture()){if(!save())return;}
  $('saveStatus').textContent='● Salvo no banco de dados';selectedDay=today();
  $('today').textContent=new Date().toLocaleDateString('pt-BR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});render();
}catch(e){$('saveStatus').textContent='⚠ Falha ao carregar';alert('Não foi possível carregar a carteira: '+e.message)}}
$('importHtml').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{
 if(file.size>5000000)throw Error('Arquivo maior que 5 MB');
 const response=await fetch('/api/carteira_import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:await file.text(),revision:serverRevision})});
 const result=await response.json();if(!response.ok)throw Error(result.error);await init();showToast(result.clients_added+' clientes adicionados.');
}catch(err){alert(err.message)}finally{e.target.value=''}};
init();
