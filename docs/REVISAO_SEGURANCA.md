# Pacote para revisão independente de segurança

**Revisão independente: NÃO realizada.** Este documento foi preparado durante a implementação, não por um terceiro. Os testes internos e correções abaixo não constituem certificação, pentest independente ou declaração de conformidade com a LGPD.

## Escopo atual

Aplicação Python/SQLite local, um responsável por instalação, senha local, sem servidor público ou segregação de usuários por escritório. O código pode ser público; bancos, configurações de senha, XMLs, backups e evidências reais devem permanecer fora do repositório.

Ativos: cadastros, contatos, notas, XMLs, escrituração, regras, registros de conferência, senha derivada e backups. Ameaças: sites maliciosos tentando acessar localhost, acesso indevido no navegador, cópia dos arquivos, malware/usuário com controle do Windows, arquivos fiscais manipulados, perda/corrupção e alterações não rastreáveis.

## Controles e evidências internas

- Escuta em 127.0.0.1; verificação de Host, Origin e Sec-Fetch-Site; JSON obrigatório nas mutações.
- APIs de dados e exportações exigem sessão no modo normal. Demonstração é separada e usa documentos fictícios.
- PBKDF2-SHA256 com sal aleatório, comparação constante, cookies HttpOnly/SameSite=Strict, expiração por inatividade/tempo absoluto e revogação de sessões ao trocar a senha.
- Limite de tentativas tanto no login quanto na verificação da senha atual para troca.
- CSP com scripts locais/nonce, políticas de enquadramento, referências e recursos; textos de usuários escapados ou inseridos com textContent.
- SQL parametrizado nos valores, limites de arquivos, bloqueio de DTD/entidades XML, snapshots e histórico de regras/lançamentos; backup anterior à mudança de estrutura.
- Testes automatizados e testes de navegador em dados temporários: não equivalem a ataque independente nem garantem ausência de vulnerabilidades.

## Riscos e limites que o revisor deve tratar

1. SQLite e backups **não são criptografados**. Senha do aplicativo não protege contra leitura, alteração ou remoção de arquivos por quem controla o computador. `chmod` não substitui ACLs e criptografia do Windows.
2. HTTP local sem TLS: apropriado somente ao recorte local definido; não utilizar como arquitetura de publicação online. Cookies não têm Secure nesse HTTP local.
3. Primeiro cadastro de senha depende da segurança da conta Windows e do acesso local. Não há identidade verificada, assinatura do contador, usuários individuais, permissões por escritório ou MFA.
4. Nome do preparador/conferente e fundamentos são declarados pelo operador. Histórico no mesmo banco não tem garantia de imutabilidade contra alterações por alguém com acesso aos arquivos.
5. XMLs e eventos não têm assinatura ou situação oficial verificadas; elegibilidade e regras ainda dependem de conferência externa. Arquivos de terceiros devem ser tratados como não confiáveis.
6. Avaliar sessões entre abas, dados em memória/BFCache, formulários não salvos, tratamento de erros, disponibilidade, concorrência e limites do servidor HTTP da biblioteca padrão.
7. Validar restauração, proteção de backups, pastas sincronizadas, malware, acesso compartilhado, descarte/retenção e medidas organizacionais para dados reais.

## Procedimento para a revisão externa

Fornecer ao profissional o código e este escopo, sem dados reais por padrão. Executar em cópia isolada com o kit fictício. Registrar versão/commit, plataforma, metodologia, testes de autorização/CSRF/DNS rebinding/XSS/arquivos/backup/sessões, severidade e reprodução dos achados, correções e retestes. Tratar achados críticos/altos antes de ampliar o uso. Guardar o relatório externo e o aceite dos responsáveis em local protegido.

Uma liberação para uso profissional exige também validação fiscal e operacional. Este pacote não autoriza exposição na internet nem substitui avaliação jurídica/organizacional de privacidade quando aplicável.
