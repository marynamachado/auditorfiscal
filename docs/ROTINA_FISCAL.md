# Rotina fiscal do escritório

Este é o escopo de evolução solicitado a partir da rotina usada no Domínio. A versão atual continua em validação e não substitui o Domínio. Ter todas as etapas no menu não significa ter um motor fiscal completo.

| Etapa | Disponível e persistido no SQLite | Pendente para a rotina completa |
| --- | --- | --- |
| Cadastro | Empresa, carteira, regime cadastral, contador/CRC declarados, endereço, sócios e observações opcionais | Consulta oficial por CNPJ, validação externa do CRC, cadastro societário estruturado completo e mudanças históricas de regime |
| Parâmetros | Versões por vigência mensal e regras assistidas explícitas de tributos | Incidência automática, vigências diárias, retenções, regras legais completas por regime, produto, operação e município |
| Auxiliares | Acumuladores versionados; produtos/serviços com NCM informado; clientes/fornecedores por CNPJ | Importação dos catálogos, tabela NCM oficial, regras de impostos por NCM, cadastro de terceiros por CPF e vínculo automático com os itens |
| Notas | NF-e modelo 55 por XML, entrada/saída, notas e itens, classificação manual da nota por acumulador | Busca automática, NFS-e, CT-e, lançamento manual fiscal completo, mapeamento de itens e classificação automática |
| Apuração | Simulação de ICMS; lançamentos e regras assistidos de ICMS, PIS, COFINS, IPI e ISS; comparação declarada com mês do Domínio | Cobertura e validação legal de todos os regimes, DAS, IRPJ/CSLL, retenções, benefícios, ST/DIFAL e guias oficiais |
| Obrigações | Acompanhamento manual de prazo, situação e evidências externas, com histórico | Geração, validação oficial e transmissão de EFD ICMS/IPI, EFD Contribuições, DCTFWeb/MIT, EFD-Reinf, DEFIS e demais arquivos aplicáveis |

Não há integração direta com o Domínio. A conferência SPED existente compara parte dos registros C100 de uma EFD ICMS/IPI importada; não gera SPED, não valida o arquivo inteiro e não cobre EFD Contribuições.

## Como testar sem clientes reais

1. Abra `Iniciar-Demonstracao-Windows.bat` e confirme o selo DEMONSTRAÇÃO.
2. Em **Como testar**, carregue o cenário correto de 10/2026. Não feche a competência ainda.
3. Abra **Rotina Fiscal**, selecione a empresa fictícia e o mês 2026-10.
4. Em **Parâmetros**, registre vigência 2026-10, contador/CRC fictícios, endereço fictício e fonte “TESTE SEM VALIDADE FISCAL”. Pode acrescentar um sócio fictício e sua participação. Nenhum dado é consultado ou aprovado no CRC/Receita.
5. Em **Acumuladores**, crie um de Entrada e outro de Saída. Use “A conferir” quando não souber o tratamento. Tributos podem ser listados como `ICMS, PIS, COFINS`; isso não cria créditos, bases ou alíquotas.
6. Cadastre um produto e um fornecedor fictícios nas respectivas abas. Repetir o mesmo código interno cria uma nova versão; os códigos são separados por empresa e tipo de cadastro.
7. Em **Classificar notas**, vincule a entrada ao acumulador de Entrada e as saídas ao de Saída. Confira a justificativa e o responsável. Os valores dos XMLs devem permanecer iguais.
8. Crie uma nova versão de acumulador com o mesmo código. A nota já classificada deve conservar a versão usada anteriormente; reclassificar exige uma nova gravação explícita. O histórico de classificação fica no banco e na memória do caso fiscal fechado.
9. Em **Obrigações**, registre uma obrigação fictícia como pendente. Avançar a situação exige referência/justificativa externa. Não transmita documentos fictícios a qualquer órgão. O sistema somente armazena a declaração do responsável; não verifica o protocolo.
10. Feche e reabra a demonstração e confira a persistência. **Reiniciar somente os dados de demonstração** apaga também estes novos cadastros de teste, preservando o banco normal.

## Regras de preservação e conferência

As versões não são apagadas por novas gravações. Uma nota só pode usar um acumulador da própria empresa, da operação correspondente e na versão atual no momento da classificação. Não é permitido classificar notas de competências fechadas. Classificação é para a nota inteira: operações mistas e exceções exigem análise dos itens pelo contador e ainda não têm rateio automático.

A vigência de um novo perfil não pode alcançar uma competência fechada. A memória da apuração assistida inclui o perfil vigente, as classificações atuais e as versões de acumuladores efetivamente usadas. Uma alteração relevante invalida a conferência anterior do caso aberto; um perfil de vigência futura ou um acumulador novo ainda não usado não altera a memória do mês. O fechamento mantém uma cópia da memória. Acompanhamento de obrigações externas pode continuar após o fechamento e não muda os cálculos.

Parâmetros textuais, NCM, CFOP, estoque e reflexo contábil registrados nos auxiliares ainda não alimentam um motor automático. Os cálculos existentes continuam dependendo das regras e lançamentos explícitos da **Apuração assistida GO**. Cadastro de regime na vigência deve coincidir com o cadastro atual; transição de regime ainda exige um desenvolvimento específico. Versões não representam auditoria imutável: quem controla o arquivo SQLite pode alterá-lo.

## Goiás e obrigações vigentes

ICMS exige confirmação na Secretaria da Economia de Goiás. ISS depende da legislação e dos portais de Goiânia, Trindade ou Aparecida de Goiânia. Não se adota GARE ou outro modelo de guia estadual por analogia com outro estado; GNRE e outros recolhimentos dependem da operação. Não há geração de guia nesta versão.

O roteiro fornecido pelo usuário é uma referência de fluxo, não uma especificação legal atualizada de obrigações. DCTF, DCTFWeb/MIT, DEFIS e EFD-Reinf têm escopos e periodicidades próprios, que devem ser confirmados para cada contribuinte e período. Os nomes no acompanhamento não determinam aplicabilidade, prazo ou obrigação de entrega. Identifique na referência quando o período da obrigação difere da competência usada para organização.

Para liberar cada novo motor, usar empresa e período conhecidos, regras com fontes e vigências, confronto com o Domínio e documentos originais, validação do contador, testes nativos no Windows e revisão independente de segurança. Nenhuma dessas aprovações foi presumida.
