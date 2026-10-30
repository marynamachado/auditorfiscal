# Plano de validação fiscal — Goiás

Status: piloto assistido; **não liberado para ser o sistema fiscal principal**. Ainda falta escolher a primeira empresa e competência reais. Nenhum caso foi conferido pelo contador durante esta implementação.

## Recorte e sequência

| Perfil | O que preparar | Pendência fiscal |
| --- | --- | --- |
| Comércio no regime normal em GO | XML, EFD ICMS/IPI, memória de apuração, ajustes e saldo anterior | Direito a crédito, ST, DIFAL, benefícios, devoluções, operações interestaduais e vigência legal |
| Lucro Presumido | Receitas e segregações, relatório de PIS/COFINS e memória de cálculo | Bases e exclusões, monofásicos, alíquota zero, regimes especiais e transição tributária |
| Lucro Real | Memória de débitos, créditos e controles por natureza | Elegibilidade, apropriação, estornos, créditos extemporâneos e transição tributária |
| Simples Nacional / MEI | Referências de PGDAS/DAS, RBT12, atividades, segregações e anexos | Motor DAS/segregações/faixas não implementado; conferência não pode ser concluída no piloto |
| Serviços em Goiânia | Cadastro municipal, NFS-e e memória de ISS | Regras municipais vigentes, local da incidência, retenções, deduções e leiaute |
| Serviços em Trindade | Mesmos documentos, com cadastro e legislação locais | Validação própria do município |
| Serviços em Aparecida de Goiânia | Mesmos documentos, com cadastro e legislação locais | Validação própria do município |

Os regimes não recebem uma alíquota genérica. ICMS tem recorte estadual; ISS depende do município; PIS/COFINS/IPI têm regras federais e específicas. O cadastro dos municípios no piloto é uma declaração do responsável; não houve validação cadastral online. A consulta à API do IBGE falhou neste ambiente. As referências iniciais de consulta são os portais oficiais [Economia de Goiás](https://goias.gov.br/economia/) e [Receita Federal](https://www.gov.br/receitafederal/pt-br), acessíveis durante a preparação. Isso **não comprova** análise do texto normativo, vigência, alíquotas ou benefícios. O contador deve apontar os dispositivos aplicáveis ao caso e à competência, inclusive a transição IBS/CBS/IS.

## Primeiro caso com o Danillo

1. Escolher uma empresa e um mês já fechado no Domínio. Trabalhar em cópia controlada e manter o Domínio como referência.
2. Registrar regime, município real, atividades, produtos e operações presentes no mês. Evitar começar com todos os casos especiais ao mesmo tempo.
3. Reunir XMLs, eventos, SPED aplicável, memória da apuração, saldo anterior, ajustes e resultados esperados. Não enviar certificados, senhas ou dados pessoais desnecessários no chat.
4. Em **Apuração assistida GO**, identificar a competência e a referência do relatório. Informar valores esperados somente para os tributos já conferidos; vazio significa pendente.
5. Cadastrar regras com nome, alíquota, arredondamento por lançamento, vigência, fundamentação e responsável informado. O programa calcula a base declarada, mas não confirma enquadramento ou vigência legal da regra.
6. Registrar débitos, créditos elegíveis, ajustes e saldo credor com documento e justificativa. Vincular à NF quando aplicável. Valores destacados no XML não viram créditos automaticamente.
7. Confrontar memória, bases, operações, apropriações e total com o Domínio. Uma diferença zero em um total não comprova cobertura de todas as operações.
8. Registrar a conferência somente depois da análise do contador. O nome informado é declaratório: não há verificação de identidade, CRC ou assinatura digital.
9. Guardar evidências fora do repositório público. Repetir com outros períodos, regimes, exceções e municípios antes de qualquer decisão de substituição do sistema principal.

## Controles implementados nesta etapa

- Regras e referências são versionadas; novas versões não apagam as anteriores.
- Débitos/créditos usam Decimal e arredondamento configurado. Ajustes e saldo anterior são informados com justificativa; valor a recolher e crédito a transportar são separados.
- Estorno preserva o lançamento original. Uma nova conferência é necessária depois de alterações relevantes, mesmo quando o total volta ao mesmo valor.
- Evento 110111 é recebido como pendente. Protocolo e código de retorno são filtros estruturais; assinatura, autenticidade e situação na SEFAZ não são verificadas. Confirmação exige consulta externa e declaração do responsável.
- Cancelamento confirmado por declaração exclui valores vinculados do cálculo assistido e da simulação, mantendo documentos e histórico. O confronto SPED fica desatualizado e aponta C100 regular incompatível com o cancelamento informado.
- Somente tentativas identificadas de duplicidade bloqueada podem ser reconhecidas como conferidas, comprovando uma cópia única. Campos estruturais ausentes e alertas legados não são resolvidos por esse reconhecimento.
- Se houver um caso cadastrado, o fechamento requer uma conferência atual sem bloqueios. A memória é preservada no fechamento. Fechamentos sem caso continuam sendo apenas controles locais do protótipo.

## O que ainda impede uma liberação profissional

Não há motor fiscal completo para todos os tributos, regimes e exceções. Bases e elegibilidade ainda são declaradas. DAS/Simples/MEI, IBS/CBS/IS, ST/DIFAL, benefícios, validação de assinaturas, consulta SEFAZ, NFS-e e reabertura/ajustes após fechamento permanecem pendentes. Casos sem movimento integral ou com todos os documentos cancelados precisam de fluxo específico. XML de emissão anterior à competência ainda não é aceito no importador inicial.

Resultados matemáticos de testes sintéticos não substituem validação fiscal. Critério de liberação: amostras reais representativas conferidas pelo contador, regras documentadas com vigência e fontes, exceções cobertas, recuperação comprovada no Windows e revisão independente de segurança com achados tratados.
