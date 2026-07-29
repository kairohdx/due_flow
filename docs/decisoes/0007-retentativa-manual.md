# ADR 0007 — Retentativa manual de mensagens

## Status

Aceita em 29/07/2026.

## Contexto

Uma tentativa pode falhar antes do aceite da Meta ou depois, durante a entrega
no WhatsApp. Repetir qualquer mensagem indistintamente pode duplicar um envio
de resultado incerto, insistir em uma mensagem já entregue ou repetir texto
livre quando a Meta exige um template aprovado.

Também é necessário preservar a falha original e identificar quem pediu cada
nova tentativa.

## Decisão

Cada envio é uma tentativa física imutável e numerada. Uma retentativa cria
outro registro, relacionado à tentativa anterior e à raiz do histórico, com
usuário solicitante, job e resultado próprios.

A elegibilidade é decidida por um fluxo `FirstMatch` do `policy_flow`. As
policies bloqueiam primeiro estados incertos, em trânsito ou já concluídos,
cobranças resolvidas, clientes inválidos e tentativas que já possuem sucessora.
Depois classificam a recuperação como `retry`, `template`, `fix`, `review` ou
`block`. Somente `retry` permite o reenvio de texto livre.

O pedido cria um job `retry_notification` com chave de deduplicação por
tentativa de origem. O worker executa novamente a mesma avaliação imediatamente
antes do envio. Se um webhook ou uma alteração de negócio tornar a operação
inelegível, o job termina cancelado sem criar outra tentativa física.

Os endpoints autenticados são:

```text
GET  /notifications/{id}/recovery
POST /notifications/{id}/retry
GET  /notifications/{id}/attempts
```

## Consequências

- falhas anteriores nunca são sobrescritas;
- duas solicitações concorrentes compartilham o mesmo job pendente;
- resultados `unknown` e entregas em andamento não podem ser reenviados;
- erros que exigem template permanecem direcionados à Etapa 8.4;
- o painel consegue mostrar elegibilidade, motivo, execução e histórico
  completo das tentativas.
