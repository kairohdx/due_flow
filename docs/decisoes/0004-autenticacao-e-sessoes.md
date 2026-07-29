# 0004 — Autenticação e sessões revogáveis

## Status

Aceita em 29/07/2026.

## Contexto

O frontend precisa manter o usuário conectado sem persistir credenciais sensíveis no armazenamento acessível ao JavaScript. Também precisamos proteger as rotas de negócio e encerrar uma sessão de forma efetiva no logout.

## Decisão

- usar senha com hash Argon2id;
- emitir access token JWT curto, com 15 minutos por padrão, mantido somente em memória pelo frontend;
- emitir refresh token opaco no formato `session_id.segredo`;
- persistir apenas o SHA-256 do segredo do refresh token;
- enviar o refresh em cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção;
- rotacionar o refresh token em toda renovação e rejeitar o token anterior;
- revogar a sessão no logout e rejeitar access tokens vinculados a ela;
- manter `/health`, login e refresh públicos e proteger as demais rotas;
- criar o usuário inicial por comando interativo, sem senha fixa ou cadastro público.

## Consequências

Cada requisição autenticada consulta usuário e sessão no banco. Esse custo é aceitável no MVP e permite revogação imediata. Uma futura implantação distribuída poderá adicionar cache curto sem mudar o contrato HTTP.

O DueFlow não adota neste momento multiempresa, RBAC, cadastro público, recuperação de senha ou autenticação social.
