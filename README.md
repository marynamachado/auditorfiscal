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

Implementados cadastro de empresas, criação/edição/exclusão de carteiras, competências, importação de NF-e, escrita fiscal, verificações iniciais, simulação de ICMS e histórico. A edição de empresas, regras fiscais completas por UF/CFOP/CST, revisão de créditos, resolução de alertas, reabertura, autenticação e migração online permanecem pendentes. O percentual do dashboard mede competências fechadas. A alíquota cadastrada é apenas referência nesta etapa.

A simulação soma ICMS destacado de saídas e subtrai ICMS potencial de entradas. Não considera direito ao crédito, ST, DIFAL, ajustes, benefícios, saldos anteriores nem validação de assinatura/autorização da NF-e. Não use os resultados para recolher impostos ou transmitir obrigações. O fechamento registra uma trava local, não representa entrega ao Fisco.

Use dados fictícios no primeiro teste. O servidor aceita conexões somente do próprio computador. Não exponha na internet: faltam autenticação, controle de acesso, HTTPS e implantação adequada. Histórico é operacional, sem garantia de imutabilidade.

## Backup

Feche o programa e copie toda a pasta `data` para um local seguro. Para restaurar, com o programa fechado, recoloque essa pasta. XMLs e informações fiscais estão no banco; proteja o arquivo. A futura versão online precisará de usuários, permissões, banco de servidor e backups automáticos.

## Validação

Execute `python3 -m unittest discover -s tests -v`. Os testes usam banco temporário e não alteram seus dados.
