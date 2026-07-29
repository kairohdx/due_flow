# ADR 0006 — Webhooks e estados de entrega da Meta

## Status

Aceita em 29/07/2026.

## Contexto

Uma resposta HTTP de sucesso ao envio pela Cloud API confirma apenas que a Meta
aceitou a requisição. A entrega ao destinatário ocorre de forma assíncrona e
pode terminar em `failed`, inclusive com uma resposta posterior enviada por
webhook.

O painel precisa diferenciar esses dois resultados sem armazenar o payload
integral da Meta ou expor dados internos e pessoais desnecessários.

## Decisão

O DueFlow expõe `GET /webhooks/meta` para a verificação da URL e
`POST /webhooks/meta` para eventos. A requisição de evento só é processada
quando `X-Hub-Signature-256` corresponde ao HMAC SHA-256 do corpo bruto usando
o App Secret configurado.

Cada evento de status é correlacionado pelo `provider_message_id` (`wamid`). A
tentativa preserva dois eixos: resultado síncrono do envio
(`pending`, `succeeded`, `failed`, `unknown` ou `simulated`) e estado assíncrono
da entrega (`not_started`, `pending`, `sent`, `delivered`, `read` ou `failed`).
Timeout e falha de rede são `unknown`, pois não provam aceite nem rejeição.

As transições bem-sucedidas são monotônicas: `pending`, `sent`, `delivered` e
`read`. Eventos repetidos, regressivos, desconhecidos ou posteriores a um
estado terminal não alteram o registro. `failed` também é terminal. O endpoint
continua respondendo com sucesso nesses casos para evitar reentregas inúteis.

Somente o subconjunto necessário para auditoria é persistido. O payload bruto,
telefones completos, `internal_1p_only_data` e outros campos internos são
descartados.

Um catálogo local traduz erros relevantes para título, explicação, orientação
e categoria de ação, preservando separadamente os detalhes técnicos
sanitizados. Códigos desconhecidos recebem uma mensagem genérica em português.
O catálogo não executa retentativas e pode evoluir sem alterar o protocolo do
webhook.

No modo fake, o worker gera eventos assíncronos determinísticos depois do
aceite simulado. Eles percorrem os mesmos estados de entrega e usam o mesmo
modelo de auditoria, mas são identificados como simulados e não passam pelo
endpoint público nem exigem uma assinatura Meta fictícia.

Validação, parsing, idempotência e transições permanecem explícitos. O
`policy_flow` será usado somente na decisão de recuperação posterior, com
`FirstMatch`, quando houver ganho em prioridade, motivo e trace.

## Consequências

- aceite da requisição e entrega deixam de ser tratados como sinônimos;
- falhas assíncronas passam a aparecer no histórico e nas métricas;
- a interface pode acompanhar estados pendentes por polling;
- o endpoint público depende de HTTPS na exposição externa, token de
  verificação próprio e App Secret;
- a retentativa manual pode ser construída sobre falhas confirmadas sem perder
  a trilha da tentativa original.
