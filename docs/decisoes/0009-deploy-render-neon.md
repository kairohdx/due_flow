# ADR 0009 — Deploy da demonstração no Render e Neon

## Status

Aceita em 29/07/2026.

## Contexto

A Oracle exige uma autorização temporária em cartão que não está disponível
para o projeto. A demonstração precisa de HTTPS, PostgreSQL persistente, API e
worker, sem ultrapassar duas horas de configuração.

## Decisão

O DueFlow será empacotado em uma única imagem para o Web Service gratuito do
Render. A imagem contém o frontend compilado, a API FastAPI e o worker como
processo separado. O PostgreSQL será fornecido pelo plano gratuito do Neon.

Essa composição é exclusiva do ambiente gratuito. API e worker continuam
componentes lógicos independentes e podem voltar a serviços separados sem
alterar fila ou domínio.

Na inicialização, o serviço aplica migrations, cria idempotentemente o
administrador e, quando habilitado, carrega o seed da demonstração.

## Consequências

- frontend e API usam a mesma origem, simplificando cookies e CORS;
- o Render fornece HTTPS e URL pública;
- o Neon preserva os dados quando o Web Service dorme;
- o worker para enquanto a instância gratuita está suspensa;
- o polling do painel mantém o serviço ativo durante a demonstração;
- a imagem e o `compose.yaml` continuam portáteis para uma VPS futura.
