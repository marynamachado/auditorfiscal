const fiscalDate=value=>new Date(value).toLocaleString('pt-BR');
const fiscalValue=value=>/^\d+(?:\.\d+)?$/.test(String(value))?money(value):esc(value||'—');
let xmlBatchResults=[],xmlBatchRunning=false,spedPeriodFilter='';
function renderXmlImport(){
 return panel('Importar NF-e em lote',`<p class="muted">Selecione os XMLs exportados ou obtidos pelo Domínio. Use uma empresa e competência por lote. Até 200 arquivos, com 5 MB por XML. Cada arquivo é conferido e salvo separadamente; erros em um não impedem os demais.</p><form id="upload">${select('period_id','Competência aberta',state.periods.filter(p=>!p.closed).map(p=>[p.id,period(p.id)]))}<label>Arquivos XML<input type="file" name="file" accept=".xml" multiple required></label><button ${xmlBatchRunning?'disabled':''}>${xmlBatchRunning?'Importando…':'Importar e auditar lote'}</button></form><p class="muted">Nesta etapa, só NF-e modelo 55 com data de emissão dentro da competência selecionada. Documentos de emissão anterior, CT-e, NFS-e e eventos ainda não são tratados. Não há busca automática no Domínio ou na SEFAZ.</p>`)
 + (xmlBatchResults.length?panel('Resultado do último lote nesta sessão',table(['Arquivo','Resultado','Detalhe'],xmlBatchResults.map(r=>[esc(r.filename),esc(r.status),esc(r.detail)]))):'');
}
async function importXmlBatch(form){
 if(xmlBatchRunning)throw Error('Já existe um lote em andamento');
 const files=Array.from(form.elements.file.files),period_id=form.elements.period_id.value;
 if(!files.length||files.length>200)throw Error('Selecione entre 1 e 200 arquivos XML por lote');
 xmlBatchRunning=true;xmlBatchResults=[];
 try{
  for(let index=0;index<files.length;index++){
   const file=files[index];const button=form.querySelector('button');button.textContent=`Importando ${index+1} de ${files.length}…`;
   try{
    if(file.size>5000000)throw Error('Arquivo maior que 5 MB');
    const response=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({period_id,xml:await file.text()})});
    const result=await response.json();if(!response.ok)throw Error(result.error);
    xmlBatchResults.push({filename:file.name,status:result.duplicate?'Duplicada':'Importada',detail:result.duplicate?'Não foi criada outra cópia. Ocorrência registrada na auditoria.':'Salva no banco e disponível na Escrita Fiscal.'});
   }catch(error){xmlBatchResults.push({filename:file.name,status:'Não importada',detail:error.message})}
  }
 }finally{xmlBatchRunning=false;await load()}
 const count=status=>xmlBatchResults.filter(r=>r.status===status).length;
 $('#message').className=count('Não importada')?'error':'success';$('#message').textContent=`Lote processado: ${count('Importada')} importada(s), ${count('Duplicada')} duplicada(s), ${count('Não importada')} não importada(s). Confira o resultado por arquivo.`;
}
function renderSped(){
 const periods=state.periods.filter(p=>!p.closed);
 let html=panel('Conferir arquivos do Domínio',`<p>Compare os XMLs com o SPED Fiscal da mesma empresa e mês.</p><ol class="muted"><li>Abra a competência mensal em <b>Competências</b>.</li><li>Importe os XMLs em <b>Importação XML</b>.</li><li>Peça ao Danillo a <b>EFD ICMS/IPI (SPED Fiscal)</b> exportada pelo Domínio e selecione o TXT abaixo.</li></ol><p class="muted">A comparação usa os arquivos enviados. Não acessa o Domínio, não altera a escrituração e não transmite obrigações.</p>`)
 +panel('Importar SPED Fiscal e conferir',`<form id="sped-upload">${select('period_id','Competência aberta',periods.map(p=>[p.id,period(p.id)]))}<label>Arquivo EFD ICMS/IPI (.txt)<input name="file" type="file" accept=".txt" required></label><button>Importar e conferir</button></form><p class="muted">Até 20 MB. Aceita UTF-8 e Windows-1252. O arquivo original permanece guardado no banco; importar um novo arquivo não apaga os relatórios anteriores. Esta conferência não substitui o validador oficial (PVA).</p>`);
 html+=panel('Última conferência de cada competência',`<div class="agenda-filters">${agendaOptions('spedPeriodFilter','Filtrar competência',state.periods.map(p=>[p.id,period(p.id)]),spedPeriodFilter)}</div>`);
 const audits=state.sped_audits.filter(a=>!spedPeriodFilter||a.period_id==spedPeriodFilter);
 if(!audits.length)return html+panel('Relatórios','<p class="muted">Nenhuma conferência salva neste filtro. Importe os XMLs e um arquivo SPED para começar.</p>');
 for(const audit of audits){
  const r=audit.report;
  html+=panel(esc(period(audit.period_id)),`<p class="muted">Arquivo: ${esc(r.filename)} · Layout informado: ${esc(r.layout)} · Conferido em ${esc(fiscalDate(audit.created))}</p>${audit.stale?'<p class="review">A base de XMLs ou o SPED mudou desde esta conferência. Execute novamente.</p>':''}${r.warning?`<p class="review">${esc(r.warning)}</p>`:''}<div class="grid">${[['XMLs na base',r.xml_count],['C100 no escopo',r.sped_count],['Chaves correspondentes',r.matched_keys],['Ocorrências para revisar',r.findings.length]].map(([label,value])=>`<div class="card"><span class="muted">${label}</span><strong>${value}</strong></div>`).join('')}</div><p class="muted">${esc(r.scope)}</p><div class="agenda-actions"><button data-sped-compare="${state.sped_files.find(f=>f.period_id===audit.period_id)?.id||audit.sped_id}">Conferir novamente com o SPED mais recente</button><a class="download-link" href="/api/sped-report?id=${audit.id}">Baixar relatório para Excel (CSV)</a></div><p class="muted">Diferenças de impostos podem decorrer de créditos permitidos e ajustes. Cada ocorrência exige revisão do contador. Ausência de divergências nestes campos não significa validação fiscal completa.</p>`);
  html+=panel('Ocorrências desta conferência',r.findings.length?table(['Ocorrência','Nota / chave','XML','SPED','Linha','Orientação'],r.findings.map(f=>[esc(f.rule),`${esc(f.number||'—')}<br><small>${esc(f.key)}</small>`,fiscalValue(f.xml),fiscalValue(f.sped),f.line||'—',esc(f.note)])):'<p class="muted">Nenhuma diferença encontrada nos documentos e campos comparados. Confira o escopo e os documentos excluídos abaixo.</p>');
  if(r.excluded.length||r.other_documents)html+=panel('Documentos fora desta comparação',`<p class="muted">${r.other_documents} documento(s) de outros modelos ou do registro D100 não foram comparados. Abaixo estão as NF-e com situações diferentes de 00/01, incluindo canceladas, denegadas e complementares.</p>`+table(['Número','Chave','Situação no SPED','Linha'],r.excluded.map(d=>[esc(d.number),esc(d.key),esc(d.status),d.line])));
 }
 html+=panel('Histórico de conferências · últimas 100',table(['Data/hora local','Competência','Arquivo','Relatório'],state.sped_audit_history.filter(a=>!spedPeriodFilter||a.period_id==spedPeriodFilter).map(a=>[esc(fiscalDate(a.created)),esc(period(a.period_id)),esc(a.filename),`<a class="download-link" href="/api/sped-report?id=${a.id}">Baixar CSV</a>`])));
 return html;
}
document.addEventListener('change',e=>{if(e.target.name==='spedPeriodFilter'){spedPeriodFilter=e.target.value;render()}});
document.addEventListener('click',async e=>{const button=e.target.closest('[data-sped-compare]');if(!button)return;button.disabled=true;try{await send('sped_compare',{sped_id:button.dataset.spedCompare})}catch(error){failure(error)}finally{button.disabled=false}});
async function importSped(form){
 const file=form.elements.file.files[0];if(!file||file.size>20000000)throw Error('Selecione um TXT de até 20 MB');
 const bytes=await file.arrayBuffer();let content;
 try{content=new TextDecoder('utf-8',{fatal:true}).decode(bytes)}catch{content=new TextDecoder('windows-1252').decode(bytes)}
 await send('sped_import',{period_id:form.elements.period_id.value,filename:file.name,content});
}
