(()=>{
 const messages=[
  {kind:'motivational',text:'Um passo de cada vez também é progresso.',source:'Para o seu dia'},
  {kind:'biblical',text:'O Senhor é o meu pastor; nada me faltará.',source:'Salmos 23:1'},
  {kind:'motivational',text:'Trabalhe com atenção, respeite seu ritmo e celebre as pequenas conquistas.',source:'Para o seu dia'},
  {kind:'biblical',text:'Tudo tem o seu tempo determinado.',source:'Eclesiastes 3:1 · trecho'},
  {kind:'motivational',text:'Organizar o próximo passo pode trazer mais leveza ao caminho.',source:'Para o seu dia'},
  {kind:'biblical',text:'Entrega o teu caminho ao Senhor; confia nele.',source:'Salmos 37:5 · trecho'},
  {kind:'motivational',text:'Uma pausa para respirar também faz parte de um bom trabalho.',source:'Para o seu dia'},
  {kind:'biblical',text:'O coração alegre aformoseia o rosto.',source:'Provérbios 15:13 · trecho'}
 ];
 let mode='all',offset=0;try{mode=localStorage.getItem('auditor.inspiration')||'all'}catch{}
 if(!['all','motivational','biblical','off'].includes(mode))mode='all';
 function paint(){
  const box=document.getElementById('inspiration');box.hidden=mode==='off';document.getElementById('messages-toggle').setAttribute('aria-expanded',String(mode!=='off'));
  if(mode==='off')return;
  const list=messages.filter(m=>mode==='all'||m.kind===mode),date=new Date(),index=(date.getFullYear()+date.getMonth()*31+date.getDate()+offset)%list.length,m=list[index];
  document.getElementById('quote-text').textContent=m.text;document.getElementById('quote-source').textContent=m.source;document.getElementById('quote-mode').value=mode;
 }
 function save(){try{localStorage.setItem('auditor.inspiration',mode)}catch{}paint()}
 document.getElementById('messages-toggle').addEventListener('click',()=>{mode=mode==='off'?'all':'off';save()});
 document.getElementById('quote-next').addEventListener('click',()=>{offset++;paint()});
 document.getElementById('quote-mode').addEventListener('change',event=>{mode=event.target.value;offset=0;save()});paint();
})();
