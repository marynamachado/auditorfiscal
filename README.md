# Auditor Fiscal — V1 local em desenvolvimento

Aplicação web local com Python 3.12+ e SQLite, sem dependências externas. Os dados ficam em `data/fiscal.sqlite3`. Não é uma ferramenta fiscal homologada.

## Executar no Windows

1. Instale Python 3.12 ou mais recente pelo site oficial python.org.
2. Extraia a pasta completa do projeto no computador.
3. Dê dois cliques em `Iniciar-Windows.bat` e mantenha a janela aberta.
4. No navegador, abra `http://127.0.0.1:8000`.
5. No modo normal, crie sua senha no primeiro acesso. Depois, entre com essa senha. A demonstração continua sem senha e aceita somente documentos fictícios do kit.

No macOS/Linux: dentro da pasta, execute `python3 app.py` e abra o mesmo endereço. Para parar, pressione Ctrl+C no terminal. Não abra apenas o arquivo HTML.

## Testar com empresa fictícia, sem usar clientes reais

No Windows, abra **Iniciar-Demonstracao-Windows.bat**, mantenha a janela aberta e aguarde o navegador abrir. A página **Como testar** mostra a empresa já cadastrada e o selo **DEMONSTRAÇÃO**. No macOS/Linux, execute `python3 demo.py --open-browser`.

A demonstração usa **outro banco**, `data/demonstracao.sqlite3`, e a porta local 8001. Ela ignora `FISCAL_DB` e não substitui `data/fiscal.sqlite3`. Reabrir a demonstração preserva as alterações de teste. O banco inicial contém carteira, empresa, CNPJ exemplificativo, regime, CNAE, IE fictícia, município/UF, contato, honorário, tarefas, checklists, nota colorida e competências 10/2026 e 11/2026. Endereço e parâmetros estão também no JSON do kit.

Em **Como testar**, clique em **Baixar kit de teste** e use **Extrair tudo**. O ZIP inclui 16 arquivos: XMLs, SPEDs didáticos, cadastro fictício, resultados esperados e roteiro. Você pode importar os arquivos manualmente para exercitar o fluxo, ou clicar em **Carregar cenário automaticamente** para ver o resultado pronto. A carga automática exige uma competência sem notas; ela não apaga notas já importadas.

| Cenário | Resultado esperado |
| --- | --- |
| Correto — 10/2026 | 3 notas, nenhum alerta de XML, 3 C100 correspondentes, nenhuma diferença nos campos comparados; ICMS simulado: R$ 450 de débitos, R$ 180 de créditos potenciais, R$ 270 de saldo. O fechamento fiscal é permitido após conferir. |
| Alertas — 11/2026 | Lote de 7 XMLs: 3 importados, 1 duplicado, 3 rejeitados. Auditoria: NCM ausente e duplicidade. SPED: 4 C100 no escopo, 2 chaves correspondentes, 5 ocorrências para revisão e 1 nota cancelada fora do escopo. O fechamento fiscal é bloqueado pelos alertas de XML. |
| XML extra — após o cenário de alertas | Importar a nota 9999 torna o relatório desatualizado. Conferir novamente reduz de 5 para 4 ocorrências e altera o saldo simulado para R$ 288. |

O roteiro cobre os recursos implementados, incluindo carteira, notas, escrita, simulação de apuração, auditoria, relatórios, conclusões da carteira, fechamento fiscal, histórico, persistência e backup. **Não testa módulos futuros**: busca SEFAZ, integração direta ao Domínio, CT-e/NFS-e, SPED completo, correções, transmissão, reforma tributária ou folha.

Use **Reiniciar somente os dados de demonstração** para repetir do início. Essa ação apaga todas as alterações daquele banco de teste e recria o cadastro inicial; o banco normal permanece separado. O servidor recusa essa ação no modo normal e recusa substituir um banco sem a identificação de demonstração. Os documentos do kit são bloqueados no modo normal; o modo de demonstração aceita apenas documentos identificados como pertencentes ao kit.

Os documentos são sintéticos: XMLs com ambiente de homologação, sem assinatura ou protocolo; SPED simplificado que não foi validado no PVA. As alíquotas e valores são escolhidos para facilitar o teste, sem aplicação das regras legais do estado. IE, CEP e contatos são exemplificativos. Não houve consulta cadastral e nenhuma associação a empresas reais é afirmada. **Não enviar os documentos ao Domínio, ao PVA ou ao Fisco.**

### Se a demonstração ficar vazia ou carregando

O carregamento normal leva alguns segundos. As consultas da tela e os botões de cenário têm limite de espera de 15 segundos e mostram uma orientação caso a resposta não chegue. Uma operação pode ter sido salva mesmo se a resposta se perder; recarregue antes de repetir. Abrir o HTML diretamente também mostra a orientação para usar o iniciador.

Feche apenas as janelas pretas e abas do Auditor Fiscal, extraia a versão atualizada completa para uma pasta nova e abra **Iniciar-Demonstracao-Windows.bat**. Mantenha a janela aberta. Se a página continuar vazia, dê dois cliques em **Diagnosticar-Demonstracao-Windows.bat**, na mesma pasta da instalação com problema. O diagnóstico verifica os arquivos, a porta local, as respostas do programa e a leitura do banco, sem alterar cadastros. Ele salva `data/diagnostico-demonstracao.txt`; envie esse arquivo ou uma foto da janela. Não lista clientes nem credenciais.

## Primeiro uso

Cadastre uma carteira e seu responsável, depois uma empresa com CNPJ válido. Abra a competência do mês e importe os XMLs de NF-e modelo 55 da empresa e do mesmo mês. Confira notas, itens e alertas antes de fechar. Duplicidades são bloqueadas e registradas. Competências com alertas de XML ou sem notas não podem ser fechadas. A resolução desses alertas ainda não está disponível.

## Limites desta entrega

Implementados cadastro de empresas, criação/edição/exclusão de carteiras, competências, importação de NF-e, escrita fiscal, verificações iniciais, simulação de ICMS, histórico, senha de acesso local e backup completo. A agenda permite revisar razão social, CNPJ e regime, contatos e honorários. Regras fiscais completas por UF/CFOP/CST, revisão de créditos, resolução de alertas fiscais, reabertura fiscal e migração online permanecem pendentes. O percentual do dashboard mede competências fechadas. A alíquota cadastrada é apenas referência nesta etapa.

A simulação soma ICMS destacado de saídas e subtrai ICMS potencial de entradas. Não considera direito ao crédito, ST, DIFAL, ajustes, benefícios, saldos anteriores nem validação de assinatura/autorização da NF-e. Não use os resultados para recolher impostos ou transmitir obrigações. O fechamento registra uma trava local, não representa entrega ao Fisco.

Use dados fictícios no primeiro teste. O servidor aceita conexões somente do próprio computador. A senha protege o acesso pelo programa, mas esta versão não deve ser exposta na internet: ainda faltam HTTPS, usuários e permissões por escritório, infraestrutura e revisão específicas para implantação online. Histórico é operacional, sem garantia de imutabilidade.

## Backup

Feche o programa e copie toda a pasta `data` para um local seguro. Para restaurar, com o programa fechado, recoloque essa pasta. XMLs e informações fiscais estão no banco; proteja o arquivo. A futura versão online precisará de usuários, permissões, banco de servidor e backups automáticos.

Em **Segurança e Backup → Baixar backup completo**, é possível baixar um ZIP consistente do SQLite, incluindo carteira, notas, XMLs e relatórios, mesmo com o programa aberto. A configuração de senha não é incluída nesse ZIP. Siga `RESTAURAR.txt` para uma restauração local com o programa fechado. O ZIP não é criptografado; guarde-o em local protegido. O backup JSON da carteira cobre somente a agenda.

## Visual acolhedor e mensagens

A interface e a carteira usam tons de creme, verde suave e terracota. O cartão de mensagens permite escolher frases motivacionais, versículos bíblicos curtos com referência, ambos ou ocultar as mensagens. **Outra mensagem** alterna o texto; **Mensagens** mostra/oculta o cartão. Não há rotação automática nem serviço externo de frases, fontes ou imagens. Somente essa preferência visual é guardada no localStorage; dados fiscais e senhas não são armazenados ali.

## Proteção dos dados locais

No primeiro uso do **modo normal**, o responsável cria uma senha de 12 a 128 caracteres diretamente no computador. Não há senha padrão, envio de senha pelo chat ou recuperação por e-mail. Guarde a senha em um gerenciador seguro. A configuração fica junto ao banco, em arquivo `.access.json`, com sal aleatório e derivação PBKDF2-SHA256 de 600 mil iterações, sem a senha em texto. Preserve toda a pasta `data` ao atualizar. Recuperação de uma senha esquecida exige um procedimento local autorizado e backup; não existe atalho de recuperação pela interface.

As sessões ficam na memória do servidor, usam cookies HttpOnly/SameSite=Strict específicos da porta, expiram após 30 minutos sem atividade ou no máximo 8 horas e são encerradas quando o programa fecha. **Bloquear acesso** limpa a tela e encerra a sessão; salve o que estiver editando antes de bloquear. O bloqueio por inatividade também remove os dados da tela, podendo descartar alterações ainda não salvas. A troca de senha encerra as outras sessões. Cinco tentativas incorretas de login geram uma espera de um minuto.

Pedidos com Host inesperado ou origem de outro site são recusados, e as APIs de dados e de exportação exigem sessão no modo normal. O navegador recebe políticas para impedir scripts e conexões externos, incorporação por outros sites e acesso à câmera, microfone e localização. A demonstração permanece sem senha para permitir o teste; não use dados reais nesse modo.

**Limite importante:** senha de aplicativo não é criptografia do SQLite. Quem controla os arquivos do computador pode ler ou modificar o banco e a configuração de acesso. Os backups também não são criptografados. Use contas individuais do Windows, bloqueio de tela, permissões da pasta, atualizações e Criptografia do dispositivo/BitLocker quando disponíveis; proteja também a chave de recuperação e as cópias externas. Não compartilhe o banco ou backups por links abertos. Nenhuma dessas medidas garante risco zero nem substitui uma revisão de segurança antes de colocar o sistema online.

## Validação

Execute `python3 -m unittest discover -s tests -v`. Os testes usam banco temporário e não alteram seus dados.

## Carteira original integrada

Abra **Agenda e Clientes** no menu. A própria interface da Carteira do Danillo agora aparece dentro do sistema: cartões coloridos por cliente, carteiras, pesquisa, competência, calendário, calculadora, tarefas e checklists, notas coloridas, honorários e contatos, repetições mensais, conclusão/reabertura de trabalho por empresa, resumo de conclusões, check-in diário, backup e restauração.

Os dados são salvos no SQLite do sistema a cada alteração. Não há dependência de localStorage. A carteira mantém todos os detalhes do formato original, inclusive modelos de repetição, cores, etapas e conclusões. Os cadastros e atividades também são refletidos nas tabelas do sistema. Se outra janela salvar uma revisão mais recente, a gravação é bloqueada até recarregar, para evitar perder alterações.

Os clientes já importados na versão anterior aparecem automaticamente. Se estiver começando no Windows, use **Importar clientes do HTML** no topo da carteira e selecione `Carteira_Danillo_Offline.html`: o arquivo contém 72 cadastros iniciais (52 Royal e 20 Terceirizados). O código distribuído pelo GitHub não contém os dados reais dos clientes. O importador lê dados JSON sem executar o HTML enviado.

Para trazer tarefas e alterações feitas na agenda antiga, abra-a no mesmo navegador e perfil em que a utilizava, baixe seu backup JSON e use **Backup e ajuda → Restaurar** na carteira integrada. A restauração substitui o conteúdo da carteira e baixa uma cópia de segurança antes. Repetições mensais são preservadas e voltam a gerar ocorrências futuras como na agenda original. A carteira precisa estar aberta para gerar novas ocorrências; não há avisos com o sistema fechado. Datas não são ajustadas por feriados.

Excluir cliente remove seu cartão, tarefas, notas, repetições e conclusões da carteira. O cadastro fiscal e os documentos fiscais são preservados. As conclusões e reaberturas da carteira acompanham o trabalho do escritório e não fecham/reabrem competências fiscais nem transmitem obrigações. Honorários informados não comprovam pagamento. CNPJs e regimes incompletos permanecem sinalizados no cadastro fiscal para revisão.

O backup JSON da carteira inclui clientes, tarefas, etapas, notas, carteiras, repetições, check-ins e conclusões. Para incluir XMLs, escrita fiscal e todos os dados do sistema, feche o programa e copie a pasta `data`. Os dados da nuvem não são sincronizados com o Windows.

## Atualizar uma instalação Windows existente

Feche a janela do programa, faça uma cópia segura da pasta `data` e baixe o ZIP atualizado do GitHub. Extraia em uma pasta nova e copie sua pasta `data` para dentro dela, ao lado de `app.py`. Abra `Iniciar-Windows.bat` dessa nova pasta. A estrutura do banco é atualizada ao iniciar, preservando os dados existentes. Depois importe seu HTML ou backup na agenda, se ainda não tiver feito isso. Não envie o banco nem o backup para um repositório público.

## Primeiro fluxo com o Domínio: XML em lote e conferência SPED

O sistema recebe arquivos que o contador já possui ou exporta do Domínio. Não se conecta diretamente ao Domínio, à SEFAZ, a e-mails ou ERPs. Não usa certificado nesta etapa e não altera ou transmite arquivos fiscais.

1. Abra a competência de uma empresa em **Competências**.
2. Em **Importação XML**, selecione até 200 XMLs por lote, cada um de até 5 MB. O seletor de arquivos do Windows permite selecionar vários arquivos. Cada nota é salva em uma transação própria. Notas válidas permanecem importadas mesmo se outro arquivo falhar; a tela mostra sucesso, duplicidade ou erro por arquivo. O resultado detalhado do lote fica na sessão da página; as notas e os registros de importação bem-sucedida permanecem no banco.
3. Em **Conferência SPED**, selecione a mesma competência e o TXT da **EFD ICMS/IPI (SPED Fiscal)** exportado pelo Domínio. Não é a EFD Contribuições. O arquivo deve conter o CNPJ correto e cobrir o mês completo; são aceitos UTF-8 e Windows-1252, até 20 MB.
4. Confira o relatório com o contador. Ele aponta XML sem C100 regular correspondente, C100 sem XML na base, chave repetida, operação divergente e diferenças de total, ICMS, IPI, PIS e COFINS. Campos vazios no SPED não são tratados como zero. Diferenças não representam automaticamente erro fiscal: valores escriturados podem refletir ajustes ou restrições ao crédito.
5. Use **Baixar relatório para Excel (CSV)** para compartilhar a conferência. O relatório inclui empresa, período, arquivo, data da conferência, tamanho das bases e escopo. Chaves longas são prefixadas como texto para preservar os dígitos no Excel. Os arquivos e relatórios são preservados no banco; a tela oferece os últimos 100 relatórios para download.

A conferência inicial compara somente NF-e modelo 55 nos registros C100 com situações 00 e 01. Documentos cancelados, denegados, complementares, de regime especial e outros modelos são informados como fora do escopo. Não valida o arquivo no PVA nem compara itens, CFOP/CST, ST, DIFAL, direito ao crédito, eventos, CT-e, NFS-e, regras estaduais, IBS/CBS/IS ou obrigações contábeis. A ausência de diferenças não certifica regularidade fiscal. O SPED inteiro é preservado, mas somente os campos descritos são interpretados.

A importação atual de XML exige emissão dentro da competência. Entradas de emissão anterior ainda precisam de um fluxo próprio; por isso, um XML ausente na base não prova erro ou ausência no Domínio. Se importar novos XMLs depois de conferir, o relatório é marcado como desatualizado. Clique em **Conferir novamente com o SPED mais recente** para gerar outro relatório, preservando o anterior.

Os relatórios de SPED são informativos: não corrigem a escrituração, não removem alertas e não determinam sozinhos o fechamento fiscal. A validação da aplicabilidade das regras e o primeiro teste com arquivos reais do Domínio devem ser feitos pelo contador antes de uso operacional.
