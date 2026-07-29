# ADR 0008 — Estratégia de templates da Meta

## Status

Aceita em 29/07/2026.

## Contexto

Na demonstração, o texto livre continua sendo o caminho principal e o template
recupera falhas fora da janela de atendimento. Depois da demonstração, os
templates devem poder se tornar o padrão sem duplicar policies ou jobs.

O template `dueflow_aviso_cobranca_v1` foi submetido à análise da Meta, mas
ainda não pode ser validado pela API real.

## Decisão

A decisão comercial produz uma mensagem lógica, independente do formato de
transporte. A configuração `META_TEMPLATE_MODE` escolhe a estratégia:

- `retry_only`: texto livre normalmente e template somente na recuperação;
- `always`: template em todos os lembretes elegíveis.

O template oficial é identificado por nome e idioma. Cliente e cobrança não
criam novos templates: fornecem, respectivamente, nome, descrição, valor e
vencimento como os quatro parâmetros aprovados.

O provider fake e o provider Meta implementam a mesma operação de template.
Cada tentativa preserva no trace o formato, o nome, o idioma, os parâmetros e a
prévia renderizada antes da chamada externa. Assim, uma rejeição síncrona
continua auditável.

## Consequências

- a mudança pós-demo exige configuração, não uma nova policy;
- o erro `131047` oferece reenvio seguro por template;
- o painel diferencia texto livre de template e apresenta sua configuração;
- o payload real é coberto por HTTP mock;
- a validação externa fica pendente até a aprovação pela Meta;
- um catálogo com templates distintos por tipo pode ser introduzido sem mudar
  o contrato da estratégia.
