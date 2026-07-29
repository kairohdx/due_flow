# Decisão 0002 — Contrato do provider fake de WhatsApp

- **Status:** aceita
- **Data:** 29/07/2026

## Contexto

Antes da Etapa 5, foi inspecionado o repositório local `mvp-loja-local` como referência de uma integração existente com a Meta WhatsApp Cloud API.

No estado analisado, a atualização de status de pedido não dispara diretamente uma mensagem. O contrato reutilizável está no sender de conversas e webhooks:

```text
send_text(to, body, phone_number_id opcional)
```

O payload textual usado pela integração é:

```json
{
  "messaging_product": "whatsapp",
  "to": "5511999990000",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Mensagem"
  }
}
```

## Decisão

O DueFlow mantém uma porta própria e pequena:

```text
send_text(to, body, correlation_id) → ProviderResult
```

O `FakeWhatsAppProvider`:

- recebe o telefone normalizado e remove apenas o `+` no payload Meta;
- monta o mesmo formato lógico de requisição textual;
- não acessa a rede;
- retorna status `simulated`;
- gera `wamid.fake.<uuid>`;
- retorna uma resposta simulada com `contacts` e `messages`;
- inclui o identificador de correlação;
- não recebe nem registra tokens.

A requisição e a resposta seguras são persistidas em `NotificationAttempt.provider_response`.

## Limites

- O fake não simula latência, webhook de entrega ou leitura.
- O fake não valida se o número existe no WhatsApp.
- Falhas podem ser exercitadas por um provider de teste injetado.
- `MESSAGE_PROVIDER=meta` continuará indisponível até a etapa da integração real.

## Consequências

- A demonstração mostra um resultado próximo ao contrato real sem depender da rede.
- O worker e o serviço de notificação não precisarão mudar ao introduzir a Meta.
- O provider real deverá traduzir HTTP e respostas da Graph API para o mesmo `ProviderResult`.
- O histórico permite comparar payload, status e identificador do provider.

