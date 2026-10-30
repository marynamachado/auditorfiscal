// Requisições locais com prazo de resposta e confirmação explícita de gravação.
window.fiscalRequest=async function(url,options={}){
 const {timeoutMs=15000,...settings}=options;
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),timeoutMs);
 const writing=!!settings.method&&settings.method.toUpperCase()!=='GET';
 try{
  const response=await fetch(url,{...settings,cache:'no-store',signal:controller.signal});
  let data;
  try{data=await response.json()}catch(error){if(error.name==='AbortError')throw error;throw Error((writing?'A operação pode ter sido salva, mas não foi possível confirmá-la. Recarregue a página antes de repetir. ':'')+'O programa respondeu com uma página incompatível. Feche as janelas antigas do Auditor Fiscal e abra novamente o iniciador da pasta atualizada.')}
  if(!response.ok)throw Error(data.error||'O programa não conseguiu concluir esta operação.');
  return data;
 }catch(error){
  if(error.name==='AbortError')throw Error(writing?'Não foi possível confirmar a operação em 15 segundos. Ela pode ter sido salva: recarregue a página antes de repetir. Confira se a janela do programa continua aberta.':'O programa não respondeu em 15 segundos. Confira se a janela Iniciar-Demonstracao-Windows.bat continua aberta e clique em Recarregar.');
  if(error instanceof TypeError)throw Error((writing?'Não foi possível confirmar a gravação; ela pode ter sido salva. Recarregue antes de repetir. ':'')+'Não foi possível conectar ao programa. Mantenha a janela do iniciador aberta e recarregue a página.');
  throw error;
 }finally{clearTimeout(timer)}
};
