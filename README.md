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

## Agenda e clientes dos escritórios

Abra **Agenda e Clientes** no menu. As carteiras representam escritórios ou grupos atendidos; cada cliente é também uma empresa do módulo fiscal. O responsável da carteira pode ser alterado em **Carteiras**.

Na seção **Trazer dados da agenda antiga**, selecione `Carteira_Danillo_Offline.html` e clique em **Importar clientes e agenda**. O HTML fornecido contém os 72 cadastros iniciais: 52 da Carteira Royal e 20 de Terceirizados. Nenhum prazo ou honorário será inventado. O importador extrai apenas dados JSON e não executa scripts do arquivo. CNPJ incompleto e regime não informado são sinalizados para revisão, sem completar dígitos por suposição.

As tarefas e alterações que você fez na agenda antiga ficam no navegador, não dentro do HTML. Para trazê-las, abra a agenda antiga no mesmo navegador e perfil, clique em **Backup**, salve o JSON e importe esse JSON na nova tela. Faça essa importação também no Windows: os dados do ambiente na nuvem não são sincronizados com seu computador.

A importação acrescenta dados sem substituir registros existentes. Reimportar os mesmos dados não duplica clientes nem tarefas. Cadastros existentes são associados por CNPJ/identificador e preservados, inclusive dados revisados. Para corrigir razão social, CNPJ ou regime, abra o cartão do cliente e use **Revisar cadastro da empresa**. Para atualizar contato, honorário ou escritório, use o formulário de contato. Honorários não representam pagamentos recebidos.

Use os filtros por escritório, nome/CNPJ/contato, competência e situação. O calendário mostra os prazos do mês, inclusive de tarefas de outra competência; clicar no dia filtra a lista pelos vencimentos. Cada cliente tem tarefas, anotações coloridas e uma conclusão de trabalho por mês. Concluir trabalho na agenda exige finalizar suas tarefas do mês e **não fecha a competência fiscal**. Reabrir uma tarefa reabre a conclusão do trabalho. Clientes sem tarefas podem ser marcados manualmente como concluídos; o percentual considera todos os clientes da carteira selecionada.

Novas tarefas podem gerar 3, 6 ou 12 ocorrências mensais independentes, ajustadas ao último dia do mês, sem ajustes de feriados. No backup antigo, as ocorrências já geradas e seus checklists são importados; modelos de recorrência futura não são ativados automaticamente. Checklists importados ficam disponíveis para consulta. Não há avisos quando o sistema está fechado.

**Baixar backup da agenda** exporta clientes, carteiras, tarefas, anotações, conclusões e check-ins em JSON. Esse backup não inclui XMLs, escrita fiscal nem apurações: para uma cópia completa, use a pasta `data` com o sistema fechado. Os dados reais ficam no SQLite local e não são incluídos no código distribuído pelo GitHub.

## Atualizar uma instalação Windows existente

Feche a janela do programa, faça uma cópia segura da pasta `data` e baixe o ZIP atualizado do GitHub. Extraia em uma pasta nova e copie sua pasta `data` para dentro dela, ao lado de `app.py`. Abra `Iniciar-Windows.bat` dessa nova pasta. A estrutura do banco é atualizada ao iniciar, preservando os dados existentes. Depois importe seu HTML ou backup na agenda, se ainda não tiver feito isso. Não envie o banco nem o backup para um repositório público.
