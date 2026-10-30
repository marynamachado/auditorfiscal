# Auditor Fiscal — V1 local em desenvolvimento

Aplicação web local com Python 3.12+ e SQLite, sem dependências externas. Os dados ficam em `data/fiscal.sqlite3`. Não é uma ferramenta fiscal homologada.

## Executar no Windows

1. Instale Python 3.12 ou mais recente pelo site oficial python.org.
2. Extraia a pasta completa do projeto no computador.
3. Dê dois cliques em `Iniciar-Windows.bat` e mantenha a janela aberta.
4. No navegador, abra `http://127.0.0.1:8000`.

No macOS/Linux: dentro da pasta, execute `python3 app.py` e abra o mesmo endereço. Para parar, pressione Ctrl+C no terminal. Não abra apenas o arquivo HTML.

## Primeiro uso

Cadastre uma carteira e seu responsável, depois uma empresa com CNPJ válido. Abra a competência do mês e importe uma NF-e modelo 55 da empresa e do mesmo mês. Confira notas, itens e alertas antes de fechar. Duplicidades são bloqueadas e registradas. Competências com alertas ou sem notas não podem ser fechadas. A resolução de alertas ainda não está disponível.

## Limites desta entrega

Implementados cadastro de empresas, criação/edição/exclusão de carteiras, competências, importação de NF-e, escrita fiscal, verificações iniciais, simulação de ICMS e histórico. A agenda permite revisar razão social, CNPJ e regime, contatos e honorários. Regras fiscais completas por UF/CFOP/CST, revisão de créditos, resolução de alertas fiscais, reabertura fiscal, autenticação e migração online permanecem pendentes. O percentual do dashboard mede competências fechadas. A alíquota cadastrada é apenas referência nesta etapa.

A simulação soma ICMS destacado de saídas e subtrai ICMS potencial de entradas. Não considera direito ao crédito, ST, DIFAL, ajustes, benefícios, saldos anteriores nem validação de assinatura/autorização da NF-e. Não use os resultados para recolher impostos ou transmitir obrigações. O fechamento registra uma trava local, não representa entrega ao Fisco.

Use dados fictícios no primeiro teste. O servidor aceita conexões somente do próprio computador. Não exponha na internet: faltam autenticação, controle de acesso, HTTPS e implantação adequada. Histórico é operacional, sem garantia de imutabilidade.

## Backup

Feche o programa e copie toda a pasta `data` para um local seguro. Para restaurar, com o programa fechado, recoloque essa pasta. XMLs e informações fiscais estão no banco; proteja o arquivo. A futura versão online precisará de usuários, permissões, banco de servidor e backups automáticos.

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
