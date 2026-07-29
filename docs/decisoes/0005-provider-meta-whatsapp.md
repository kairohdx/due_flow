# Decisão 0005 — Provider da Meta WhatsApp Cloud API

## Contexto

O fluxo assíncrono e a idempotência já funcionavam com o provider fake. A
integração real precisava reutilizar a mesma porta sem permitir que token,
header de autorização ou resposta bruta sensível chegassem ao banco ou aos logs.

## Decisão

O `MetaWhatsAppProvider` envia mensagens de texto para:

```text
/{graph_api_version}/{phone_number_id}/messages
```

O provider:

- recebe credenciais somente pela configuração do processo;
- usa `Authorization: Bearer` apenas na requisição HTTP;
- aplica timeout explícito;
- converte sucesso em `ProviderResult(status=sent)`;
- mascara telefones e remove tokens antes de devolver dados persistíveis;
- traduz timeout, rede, HTTP e contrato inválido para erros seguros;
- exige versão da Graph API explícita, sem default oculto;
- pode receber um cliente HTTP injetado para testes sem rede.

O worker seleciona `fake` ou `meta` por `MESSAGE_PROVIDER`. O modo fake continua
sendo o padrão e não exige nenhuma credencial da Meta.

## Consequências

- A fila, as policies e o serviço de notificação não conhecem HTTP ou credenciais.
- Falhas continuam auditáveis em `NotificationAttempt`.
- A suíte valida a integração com transporte HTTP mockado.
- Um comando manual separado permite testar um número autorizado sem criar dados
  no banco.
- Mensagens livres só funcionam dentro da janela permitida pela Meta. Iniciar
  conversas fora dela exigirá um template aprovado e uma decisão de produto
  específica para seus parâmetros.
