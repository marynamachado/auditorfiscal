# Instalação, atualização e recuperação no Windows

Status: o script técnico foi executado neste ambiente Linux. A execução nativa e a experiência no Windows do escritório **permanecem pendentes**.

## Teste técnico isolado

1. Baixar o ZIP atualizado e extrair em uma pasta nova.
2. Executar `Validar-Windows.bat`. Ele usa somente bancos temporários e dados fictícios, sem abrir os cadastros dos clientes.
3. Guardar `data/validacao-tecnica.json`. O relatório informa sistema operacional, versão do Python, resultados e tarefas manuais pendentes, sem aprovar uso profissional.

O teste verifica XML/SPED sintéticos, APIs locais, exportação e restauração de backup, detecção de uma cópia corrompida, recuperação da cópia, preservação de cadastro legado após atualização e rollback de uma transação SQLite em processo interrompido. Esse último teste não simula todos os pontos de falha da aplicação nem perda física do disco.

## Aceite manual no computador de destino

- Abrir o iniciador de demonstração e conferir que o navegador e o selo DEMONSTRAÇÃO aparecem.
- Executar os dois cenários do kit, navegar pela carteira, gravar tarefas, conferir o resultado, fechar e abrir o programa novamente.
- Em uma instalação de teste do modo normal, cadastrar senha, entrar, bloquear, reentrar, trocar senha e conferir encerramento de outra sessão. Não usar uma senha real em relatório de testes.
- Baixar backup completo e restaurar em **outra pasta de teste**, com o programa fechado; conferir dados e histórico. O ZIP não é criptografado.
- Registrar Python/Windows utilizados, data, responsável, resultado e evidências. Não incluir senhas, tokens, nomes de clientes ou dados fiscais desnecessários no relatório compartilhado.

## Atualização controlada

1. Fechar todas as janelas do Auditor Fiscal.
2. Guardar uma cópia protegida de toda a pasta `data`, incluindo configuração de senha. Não misturar banco normal e demonstração.
3. Extrair o código novo em outra pasta e copiar os dados preservados para ela. Manter a pasta anterior para possível retorno.
4. Abrir a instalação nova. Antes da mudança estrutural deste piloto, o iniciador normal faz uma cópia consistente em `data/backups/antes-piloto-go-*.sqlite3` quando necessária. Essas cópias também precisam de proteção de acesso/disco.
5. Conferir cadastros, período, totais conhecidos e senha antes de continuar o trabalho.

As conexões da aplicação agora são encerradas ao sair do contexto de transação, inclusive em erros, para liberar arquivos e travas. Não há migração com restauração automática: se a atualização falhar, interrompa o uso e preserve todos os arquivos para analisar antes de restaurar.

## Recuperação

Com o programa fechado, preservar o banco com falha e a configuração de acesso. Restaurar uma cópia consistente em pasta separada, com versão compatível, e comparar cadastros, documentos, histórico e resultados com uma referência conhecida. Só substituir a instalação de trabalho depois da conferência. Nunca sobrescrever o único banco disponível nem restaurar com outro processo escrevendo nele.

Concluir o teste automático não comprova suporte a todas as versões do Windows, antivírus, pastas sincronizadas ou cenários de queda. A validação manual no computador real e a política de backups continuam necessárias.
