# DueFlow — escopo e plano técnico do MVP

> Documento inicial para discussão. O nome `DueFlow` é provisório.

## 1. Visão geral

O DueFlow será uma aplicação web pequena para cadastrar clientes e cobranças, decidir quando uma cobrança deve gerar uma notificação e enviar — ou simular — lembretes pelo WhatsApp. O projeto também será um exemplo prático do pacote `policy_flow`: a decisão deve ser rastreável, mas o pacote não deve controlar persistência, HTTP, templates ou envio.

O repositório foi inspecionado em 29/07/2026 e contém apenas o diretório `.git`, sem commits ou código reutilizável. Não há conflitos com o escopo nem decisões legadas a preservar. A proposta parte de um monólito modular com backend e frontend no mesmo repositório.

## 2. Objetivo do MVP

Entregar uma aplicação demonstrável e implantável que permita:

1. cadastrar e editar clientes;
2. cadastrar e editar cobranças;
3. marcar cobranças como pagas ou canceladas;
4. processar cobranças manualmente e por agendamento;
5. selecionar uma única decisão com `policy_flow` e estratégia `FirstMatch`;
6. enviar pelo provider fake ou pela Meta WhatsApp Cloud API;
7. impedir notificações duplicadas;
8. consultar tentativas de envio e o trace da decisão;
9. executar localmente com poucos comandos;
10. migrar de SQLite para PostgreSQL sem alterar regras de negócio.

O primeiro marco demonstrável termina no provider fake. A API real do WhatsApp é uma extensão do mesmo fluxo, não um requisito para provar o núcleo do MVP.

## 3. Fora de escopo

- IA, geração de boletos, Pix, pagamentos, conciliação e emissão fiscal;
- cobrança recorrente sofisticada;
- multiempresa completa, RBAC, cadastro público, recuperação de senha ou autenticação social;
- editor de templates;
- CRM e outras integrações;
- websocket, filas externas, microserviços e Kubernetes;
- gráficos, design system ou frontend sofisticado;
- retentativas distribuídas e observabilidade corporativa;
- confirmação automática de pagamento;
- campanhas, respostas recebidas e webhooks da Meta, salvo se necessários depois para acompanhar status de entrega.

## 4. Principais casos de uso

- Criar, listar, consultar e editar cliente.
- Criar, listar, consultar e editar cobrança pendente.
- Marcar cobrança como paga ou cancelá-la.
- Processar uma cobrança específica para demonstração.
- Processar em lote as cobranças candidatas.
- Inspecionar decisão, política selecionada e trace.
- Consultar tentativas por cobrança e em uma lista geral.
- Reexecutar o processamento sem duplicar uma notificação já aceita como enviada.

Edição não deve permitir transições arbitrárias de status; `mark-paid` e `cancel` expressam essas ações separadamente.

## 5. Fluxo principal

```text
Scheduler automático ou endpoint manual
  → criar ProcessingJob no banco
  → responder imediatamente com job_id e status queued
  → worker reservar o job de forma atômica
  → buscar cobranças candidatas
  → montar contexto com data local de referência
  → executar PolicyFlow / FirstMatch
  → obter decisão estruturada e trace
  → encerrar sem tentativa quando não elegível
  → reservar chave de idempotência da notificação
  → renderizar template
  → selecionar provider fake ou Meta
  → enviar ou simular
  → persistir resultado da tentativa
  → concluir o job
```

Políticas somente decidem. O worker coordena os efeitos, e o provider somente envia. Execuções manuais e agendadas criam o mesmo tipo de job e chegam ao mesmo caso de uso.

## 6. Decisões técnicas

| Tema | Decisão para o MVP | Motivo/limite |
|---|---|---|
| Organização | Monólito modular, backend e frontend separados por diretório | Menor custo operacional sem misturar responsabilidades |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy 2 e Alembic | Stack direta, tipada e testável |
| Banco local | SQLite | Suficiente para demo e um único processo; habilitar foreign keys e `busy_timeout` |
| Banco de produção | PostgreSQL | Melhor concorrência, travas e operação contínua |
| Dinheiro | `Decimal` no domínio e `NUMERIC(12,2)` no banco | Nunca usar `float` |
| Datas | `due_date` como `date`; instantes persistidos em UTC | O vencimento é um dia civil; decisões usam `America/Sao_Paulo` |
| Scheduler/worker | Processo Python contínuo e separado da API | Permite automação e consumo rápido de jobs sem executar trabalho no HTTP |
| Fila | Tabela `processing_jobs` no banco | Demonstra processamento assíncrono e preserva uma porta para fila externa futura |
| Templates | Arquivos/configuração versionada no código | Só existem três e não há edição pelo usuário |
| HTTP externo | Cliente com timeout e interface injetável | Facilita testes sem rede |
| Autenticação | JWT de acesso curto + refresh token rotativo em cookie `HttpOnly` | Mantém a sessão sem expor o refresh token ao JavaScript |
| Frontend | React, TypeScript, Vite, React Router e TanStack Query | Rotas, cache de estado remoto, paginação e polling sem estado global de negócio |
| Provider padrão | `fake` | Demo confiável sem credenciais ou disponibilidade externa |
| Providers previstos | `fake` e `meta` | A interface existe para testes e troca de ambiente, não para suportar vários canais |
| Python | `>=3.12,<3.14` | O pacote exige 3.11+; 3.12 é a referência de deploy e 3.13 foi validado no spike |
| Dependências | `pip` + `pyproject.toml` | Ferramentas nativas são suficientes no MVP |
| Identificadores | UUID v4 gerado pela aplicação | Portável entre SQLite e PostgreSQL |

SQLite continua adequado para a demo com uma API e um worker de baixo volume, usando WAL, `busy_timeout` e operações curtas. API e worker usam a mesma imagem e o mesmo código, porém comandos distintos. O worker consulta jobs frequentemente e cria o job automático no intervalo configurado. Uma implementação `JobQueue` pequena evita acoplar o caso de uso ao banco e permite migrar futuramente para uma fila externa.

## 7. Arquitetura proposta

As dependências apontam para dentro:

```text
Frontend → API → DatabaseJobQueue ← Worker/Scheduler
                                     ↓
                         Application (casos de uso)
                                     ↓
                      Domain (decisões e policies)
                                     ↑
                Infrastructure (SQLAlchemy e providers)
```

- **Domain:** conceitos puros de cobrança, contexto, decisão e políticas.
- **Application:** orquestra transações, idempotência, renderização e envio.
- **Infrastructure:** implementa repositórios, fila no banco, relógio, providers e bootstrap do worker.
- **API:** valida entrada, chama casos de uso e apresenta resultados.
- **Frontend:** consome a API; não replica regras de elegibilidade.

O PolicyFlow não será um microserviço. Ele permanece no pacote de domínio compartilhado, mas é executado pelo processo worker, não durante a requisição HTTP que cria o job.

Não é necessário adotar DDD completo, CQRS ou um framework de injeção de dependências. Funções/fábricas explícitas bastam.

## 8. Estrutura de diretórios

Estrutura proposta, ainda não criada:

```text
due_flow/
├── backend/
│   ├── alembic/
│   ├── src/dueflow/
│   │   ├── api/
│   │   ├── application/
│   │   ├── domain/
│   │   │   └── policies/
│   │   ├── infrastructure/
│   │   │   ├── db/
│   │   │   ├── messaging/
│   │   │   └── worker/
│   │   ├── templates/
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── compose.yaml
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

Para velocidade, um único Dockerfile multi-stage pode servir backend e frontend; isso deve ser decidido quando o deploy alvo for conhecido.

## 9. Modelagem das entidades

### Customer

| Campo | Tipo/observação |
|---|---|
| `id` | UUID ou inteiro; escolher um padrão único |
| `name` | string obrigatória |
| `phone` | string normalizada em E.164, única apenas se a regra comercial exigir |
| `active` | boolean, padrão `true` |
| `created_at`, `updated_at` | timestamp UTC |

Cliente inativo não deve receber novas notificações. A desativação preserva o histórico.

### Charge

| Campo | Tipo/observação |
|---|---|
| `id` | mesmo padrão de identificador |
| `customer_id` | FK obrigatória |
| `description` | string |
| `amount` | `NUMERIC(12,2)`, positivo |
| `due_date` | `date` |
| `status` | `pending`, `paid` ou `canceled` |
| `reminder_days_before` | inteiro não negativo; padrão configurável |
| `created_at`, `updated_at` | timestamp UTC |

`overdue` é derivado de `status == pending` e `due_date < hoje_local`; não é status persistido.

### NotificationAttempt

| Campo | Tipo/observação |
|---|---|
| `id` | identificador |
| `charge_id` | FK obrigatória |
| `notification_type` | `upcoming`, `due_today`, `overdue` |
| `provider` | `simulated` ou `meta` |
| `destination` | telefone usado no momento, preferencialmente protegido em logs |
| `message` | texto renderizado para auditoria da demo |
| `status` | `pending`, `sent`, `failed` ou `simulated` |
| `provider_message_id` | opcional |
| `error` | mensagem sanitizada e limitada |
| `idempotency_key` | string única |
| `policy_name` | política vencedora |
| `decision_reason` | motivo legível |
| `trace` | JSON opcional, enxuto |
| `processed_at` | timestamp UTC |

`skipped` não deve ser persistido como tentativa: não houve tentativa de envio. Ele aparece na resposta e no trace. Se auditoria de todos os processamentos se tornar necessária, criar futuramente uma entidade `ProcessingRun`, em vez de distorcer `NotificationAttempt`.

### MessageTemplate

Não persistir no MVP. Manter três templates versionados no backend, com placeholders permitidos explicitamente. Isso evita CRUD, cache e validação de templates. Migrar para tabela somente quando usuários precisarem editar conteúdo sem deploy.

### ProcessingJob

| Campo | Tipo/observação |
|---|---|
| `id` | UUID |
| `type` | inicialmente `process_charge` ou `process_due_charges` |
| `status` | `queued`, `processing`, `completed` ou `failed` |
| `payload` | JSON pequeno com parâmetros do trabalho |
| `scheduled_for` | instante UTC a partir do qual pode ser consumido |
| `attempts`, `max_attempts` | controle simples de execução |
| `locked_at`, `locked_by` | reserva e recuperação de trabalho abandonado |
| `started_at`, `finished_at` | instantes UTC opcionais |
| `error` | erro sanitizado e limitado |
| `created_at`, `updated_at` | timestamps UTC |

Status, agendamento, tentativas e locks são colunas, não ficam escondidos no JSON. O payload contém somente parâmetros do caso de uso, como `charge_id`, `reference_date` e `origin`.

### User

| Campo | Tipo/observação |
|---|---|
| `id` | UUID |
| `email` | string normalizada e única |
| `name` | string obrigatória |
| `password_hash` | hash Argon2id; senha nunca é persistida ou registrada |
| `active` | boolean, padrão `true` |
| `created_at`, `updated_at` | timestamps UTC |

O MVP terá usuários administrativos simples, sem cadastro público, organizações ou papéis. O primeiro usuário será criado por comando de bootstrap/seed, nunca por credencial fixa no código.

### RefreshSession

| Campo | Tipo/observação |
|---|---|
| `id` | UUID usado como identificador da sessão |
| `user_id` | FK obrigatória |
| `token_hash` | hash do segredo do refresh token; o valor bruto só existe no cookie |
| `expires_at` | instante UTC |
| `revoked_at` | instante UTC opcional |
| `replaced_by_id` | sessão sucessora opcional, usada na rotação |
| `created_at`, `last_used_at` | timestamps UTC |

Cada refresh invalida o token anterior e entrega outro cookie. Logout revoga a sessão atual. Isso preserva a experiência de “manter conectado” e permite encerrar uma sessão de verdade, diferentemente de um refresh JWT sem estado.

## 10. Estados e regras

- Somente cobrança `pending`, de cliente ativo e com telefone válido pode ser elegível.
- `paid` e `canceled` são estados terminais no MVP.
- `overdue`, `due_today` e `upcoming` são situações calculadas, não estados.
- A data de referência vem de um `Clock` injetável, convertida para `America/Sao_Paulo`.
- `upcoming` vale quando `0 < due_date - hoje <= reminder_days_before`.
- Não enviar duas vezes a mesma categoria para a mesma cobrança.
- Por padrão, uma cobrança pode receber no máximo um `upcoming`, um `due_today` e um `overdue`.
- Falha não altera a cobrança. Reenvio de falha exige regra explícita; para o MVP, permitir nova tentativa mantendo a mesma chave lógica apenas após liberar/finalizar a tentativa anterior de forma transacional.
- Alterar `due_date` depois de uma tentativa levanta uma questão de negócio: a recomendação inicial é incluir a data de vencimento na chave, permitindo novo ciclo após reagendamento.
- Telefone é normalizado para E.164 na entrada; país padrão não deve ser inferido silenciosamente.
- Valores são recebidos como string decimal na fronteira e serializados como string na API.

## 11. Políticas do `policy_flow`

Usar `FirstMatch` nesta ordem:

1. `SkipInactiveCustomerPolicy`
2. `SkipPaidPolicy`
3. `SkipCanceledPolicy`
4. `SkipInvalidPhonePolicy`
5. `OverduePolicy`
6. `DueTodayPolicy`
7. `UpcomingReminderPolicy`
8. `NoNotificationPolicy`

As seis políticas sugeridas originalmente cobrem datas e status, mas faltam duas condições práticas: cliente inativo e destino inválido. Elas podem ser validações anteriores ao fluxo; porém, incluí-las como políticas de skip torna a demonstração do trace mais clara sem criar uma explosão de classes. Se o pacote funcionar melhor com pré-condições, mover essas duas para validação é aceitável.

Contrato conceitual da decisão:

```text
NotificationDecision
- decision: skip | notify
- notification_type: upcoming | due_today | overdue | null
- template_key: string | null
- reason: string
- eligible: boolean
- recommended_action: none | send
- policy_name: string
- metadata: mapa pequeno e não sensível
```

O contexto contém apenas dados necessários e valores já normalizados. A policy não acessa banco, relógio global, FastAPI nem provider. O trace deve registrar estratégia, ordem avaliada, resultado resumido de cada policy e decisão final, sem telefone completo ou credenciais.

O spike da Etapa 0 confirmou a API pública do pacote na versão `0.1.0`. O DueFlow usará `PolicyEngine`, `@rule`, `RuleResult`, `FirstMatch`, `Execution.decision` e `Execution.trace`. O pacote será instalado diretamente do GitHub, fixado por hash de commit para builds reproduzíveis. O contrato e o commit validados estão registrados em `docs/decisoes/0001-integracao-policy-flow.md`.

## 12. Estratégia de idempotência

Definir a chave lógica:

```text
{charge_id}:{due_date}:{notification_type}
```

Criar índice/constraint único em `NotificationAttempt.idempotency_key`. No mesmo bloco transacional:

1. avaliar a decisão;
2. tentar inserir uma tentativa `pending`;
3. se a constraint conflitar com uma tentativa existente, não enviar;
4. efetuar o envio fora de uma transação longa;
5. atualizar a tentativa para `sent`, `simulated` ou `failed`.

No MVP, uma tentativa `failed` também preserva a chave e bloqueia reenvio automático. Isso evita duplicação quando não for possível provar se o provider aceitou a mensagem. Uma política explícita de retry ficará para evolução posterior.

Há uma janela entre o envio externo e a gravação do sucesso; nenhum banco local oferece entrega exatamente uma vez junto com uma API externa. Para reduzir risco:

- usar a reserva `pending` antes do envio;
- não reenviar automaticamente registros `pending` sem uma política de expiração/reconciliação;
- se a Meta aceitar idempotência no endpoint utilizado, repassar uma chave compatível;
- registrar `provider_message_id`;
- começar com execução serial.

Para falhas confirmadas antes de aceitação pelo provider, novas tentativas podem usar um contador físico (`attempt_no`) mantendo a mesma identidade lógica em uma entidade separada no futuro. Para simplificar o MVP, o reenvio de falha pode ser manual e criar nova linha com sufixo de tentativa, sob trava. Essa regra deve ser fechada antes do provider real.

## 13. Integração com WhatsApp

Definir uma porta semelhante a:

```text
MessageProvider.send(destination, message, correlation_id)
  → ProviderResult(status, provider_message_id, safe_response, error)
```

### Provider fake

- não realiza rede;
- retorna `simulated`;
- gera identificador local;
- registra de forma segura o conteúdo que seria enviado;
- é o padrão em desenvolvimento, testes e vídeo.

### Meta WhatsApp Cloud API

- configura token, phone number ID, Graph API version e URL base por ambiente;
- usa timeout explícito;
- envia apenas para destinatário autorizado no ambiente de teste;
- traduz respostas HTTP para um resultado interno;
- nunca registra token, Authorization header ou resposta bruta sem sanitização;
- limita e sanitiza erros persistidos;
- fica atrás da mesma porta do simulado.

Testar com um cliente HTTP falso/mock: validar URL, payload, headers esperados sem expor o token, timeout, erro 4xx/5xx e resposta válida. Manter um teste manual opcional, desabilitado por padrão, para o sandbox da Meta. A demo nunca deve depender da API real; primeiro mostrar o fluxo simulado e, se as credenciais estiverem válidas, repetir com o provider Meta.

## 14. Endpoints

### Necessários

- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /customers`
- `GET /customers`
- `GET /customers/{id}`
- `PUT /customers/{id}`
- `POST /charges`
- `GET /charges` com filtros simples
- `GET /charges/{id}`
- `PUT /charges/{id}` para campos editáveis enquanto pendente
- `POST /charges/{id}/mark-paid`
- `POST /charges/{id}/cancel`
- `POST /processing/run` — cria job em lote e retorna `202`
- `POST /charges/{id}/process` — cria job individual e retorna `202`
- `GET /processing/jobs` com filtros de status, origem e período
- `GET /processing/jobs/{id}`
- `GET /automation`
- `POST /automation/enable`
- `POST /automation/disable`
- `GET /notifications`
- `GET /notifications/{id}`
- `GET /charges/{id}/notifications`
- `GET /dashboard/summary`
- `GET /health`

Todos são justificáveis para a interface proposta. Apenas `/health`, login e refresh são públicos; os demais endpoints exigem access token. Logout usa a sessão do refresh token e `/auth/me` usa o access token.

Toda listagem usa `page` a partir de 1 e `page_size` entre 1 e 25, com padrão 25. A resposta segue um contrato único:

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 0,
  "pages": 0
}
```

Filtros e paginação permanecem na URL do frontend para permitir recarregar, compartilhar e voltar à mesma visão. Como ainda não existe consumidor público da API, a mudança das listas atuais para esse envelope deve ocorrer antes do frontend.

Os endpoints de processamento não executam policies nem enviam mensagens. Eles retornam imediatamente `job_id` e `queued`. `reference_date` só pode ser aceita em desenvolvimento/teste. O frontend consulta o job até `completed` ou `failed`; o detalhe final pode incluir contagens e traces enxutos.

Não criar `DELETE`, CRUD de templates nem endpoint separado para estados derivados.

## 15. Frontend e experiência operacional

O frontend de referência é o repositório local `mvp-painel-loja-local`, em `C:\Users\DX__D\Documents\Projetos\Agentes - Judite\mvp-painel-loja-local`. Reaproveitar como modelo os padrões de `authStore`, bootstrap da autenticação, cliente HTTP com apenas um refresh simultâneo, rotas protegidas, shell autenticado, tratamento de erros e hooks do TanStack Query. Não copiar as regras específicas de loja, papéis/RBAC, identidade provisória por headers nem a paginação local: o DueFlow é de usuário administrativo simples e sua paginação será feita pelo backend.

A aplicação terá login e um shell autenticado com menu lateral, cabeçalho, usuário atual e logout. O access token fica somente em memória; o refresh token fica em cookie `HttpOnly`, `Secure` em produção e `SameSite=Lax`. Ao recarregar a página, o frontend chama `/auth/refresh`, recupera a sessão e depois consulta `/auth/me`. Uma única tentativa de refresh atende requisições concorrentes que recebam `401`; se ela falhar, a sessão local é limpa e o usuário volta ao login.

Telas previstas:

- **Login:** e-mail, senha, feedback de credencial inválida e estado de carregamento.
- **Visão geral:** cartões para clientes cadastrados, cobranças pendentes, cobranças avaliadas, mensagens processadas, retries e falhas de notificação; estado da automação; botão **Processar agora**; atividade recente dos jobs.
- **Clientes:** listagem paginada, criação e detalhe com edição e cobranças relacionadas.
- **Cobranças:** listagem paginada com filtros, criação e detalhe com ações pagar, cancelar e processar.
- **Fila:** listagem paginada dos jobs, origem manual/automática, status, tentativas e horários.
- **Inspeção do job:** detalhe operacional do turno com linha do tempo, payload, contagens, decisões, policy vencedora, motivo, trace e erros sanitizados. O JSON bruto fica recolhido como apoio, não como visual principal.
- **Notificações:** listagem paginada e detalhe da tentativa, mensagem, provider, resultado e vínculo com cobrança/job.

O dashboard consulta `/dashboard/summary` a cada 10 segundos. A fila consulta a cada 2 segundos enquanto houver itens `queued` ou `processing` e reduz para 10 segundos quando estiver estável. O detalhe de um job para de consultar ao atingir `completed` ou `failed`. O polling pausa quando a aba está oculta e atualiza imediatamente quando ela volta ao foco. Durante cada nova consulta, a tela preserva o último resultado para evitar piscar ou voltar ao skeleton. TanStack Query controla esses intervalos, cancelamento, cache e invalidação; não criar `setInterval` disperso pelos componentes.

Os números devem ter definições visíveis e estáveis:

- `customers_total`: clientes cadastrados;
- `charges_pending`: cobranças de negócio ainda pendentes;
- `charges_evaluated_last_24h`: soma de cobranças avaliadas pelos jobs concluídos na janela;
- `notifications_processed_last_24h`: tentativas enviadas ou simuladas na janela;
- `job_retries_last_24h`: jobs executados novamente, identificados por `attempts > 1`, no mesmo período;
- `notification_failures_last_24h`: tentativas de notificação que falharam na janela.

As contagens `jobs_queued`, `jobs_processing`, `jobs_completed_last_24h` e `jobs_failed_last_24h` permanecem no contrato para diagnóstico operacional, mas não ocupam os cards principais. Um job em lote pode avaliar muitas cobranças; apresentar o número de jobs como “itens processados” distorceria o trabalho de negócio.

Como complementos úteis sem transformar o MVP em BI: exibir “atualizado há X segundos”, permitir atualização manual, manter filtros/página na URL, usar estados vazios acionáveis e mostrar horários na timezone configurada. Gráficos, websocket, design system completo e edição visual de policies continuam fora.

## 16. Scheduler e worker

- Um processo `python -m dueflow.worker` roda continuamente, separado da API.
- O worker consulta jobs disponíveis em intervalo curto, inicialmente a cada 2 segundos.
- A cada 120 segundos, se a automação estiver habilitada, cria um job `process_due_charges`.
- O botão **Processar agora** cria o mesmo job sem esperar o próximo intervalo.
- Um controle persistido permite habilitar ou pausar somente a criação automática; jobs já enfileirados continuam auditáveis.
- A reserva do job deve ser atômica. SQLite usa uma transação curta; PostgreSQL poderá usar `FOR UPDATE SKIP LOCKED`.
- Jobs `processing` com lock expirado podem voltar para `queued` respeitando `max_attempts`.
- Configurações iniciais: `WORKER_POLL_INTERVAL_SECONDS=2` e `AUTOMATION_INTERVAL_SECONDS=120`.
- O processo registra início, fim, duração e contagens sem PII completa.

Uma porta `JobQueue` será consumida pela aplicação e implementada inicialmente como `DatabaseJobQueue`. Migrar para Celery, RQ, SQS ou RabbitMQ deverá trocar principalmente esse adaptador e o bootstrap do worker, sem mover o PolicyFlow para outro serviço.

## 17. Testes

### Unitários

- paga seleciona skip e não chama provider;
- cancelada seleciona skip;
- cliente inativo e telefone inválido selecionam skip;
- atrasada seleciona `OverduePolicy`;
- vencendo hoje seleciona `DueTodayPolicy`;
- dentro da antecedência seleciona `UpcomingReminderPolicy`;
- fora da janela seleciona `NoNotificationPolicy`;
- ordem `FirstMatch` impede múltiplas decisões;
- dinheiro preserva precisão;
- decisão usa corretamente a data local;
- templates renderizam somente placeholders permitidos.

### Integração

- login inválido não cria sessão e usuário inativo não autentica;
- refresh rotaciona a sessão, token anterior deixa de funcionar e logout revoga o token atual;
- rotas privadas rejeitam access token ausente, expirado ou inválido;
- listagens respeitam o envelope, filtros, total, página padrão 25 e limite máximo 25;
- resumo do dashboard calcula corretamente janela móvel de 24 horas, fila, retries e falhas;
- mesma chave lógica não envia duas vezes;
- falha do provider é persistida e não muda a cobrança;
- provider fake não realiza chamada externa;
- provider Meta trata sucesso, timeout e erros usando HTTP mockado;
- execução manual e agendada chamam o mesmo caso de uso;
- concorrência sobre a mesma notificação resulta em uma reserva;
- endpoints validam telefone, decimal e transições;
- migrations sobem em banco vazio.

### Ponta a ponta mínimo

- login, recarga da página, renovação da sessão e logout;
- navegar pelas listagens paginadas e abrir o detalhe de cada item;
- observar dashboard e fila atualizando por polling sem recarregar a página;
- cadastrar cliente e cobrança, processar, visualizar tentativa e trace;
- repetir processamento e comprovar skip por idempotência.

Usar relógio injetável; testes não devem depender da data real.

## 18. Variáveis de ambiente

```dotenv
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./dueflow.db
CORS_ORIGINS=http://localhost:5173
APP_TIMEZONE=America/Sao_Paulo
DEFAULT_REMINDER_DAYS_BEFORE=3

JWT_SECRET=
JWT_ISSUER=dueflow
JWT_AUDIENCE=dueflow-web
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRES_DAYS=30
AUTH_REFRESH_COOKIE_NAME=dueflow_refresh
AUTH_COOKIE_SECURE=false

MESSAGE_PROVIDER=fake
META_WHATSAPP_TOKEN=
META_WHATSAPP_PHONE_NUMBER_ID=
META_GRAPH_API_VERSION=
META_GRAPH_API_BASE_URL=https://graph.facebook.com
META_REQUEST_TIMEOUT_SECONDS=10

AUTOMATION_INTERVAL_SECONDS=120
WORKER_POLL_INTERVAL_SECONDS=2
WORKER_LOCK_TTL_SECONDS=300
WORKER_MAX_ATTEMPTS=3

LOG_LEVEL=INFO
```

Validar na inicialização apenas as credenciais exigidas pelo provider escolhido. `.env` deve entrar no `.gitignore`; `.env.example` contém nomes e valores seguros, nunca segredos.

## 19. Execução local

Experiência alvo após implementação:

```text
1. copiar .env.example para .env
2. subir banco/API (ou usar SQLite)
3. executar migrations
4. iniciar API
5. iniciar frontend
6. opcionalmente iniciar o worker em processo separado
```

O README deverá fornecer comandos exatos definidos pelo gerenciador escolhido. `docker compose up --build` deve oferecer o caminho mais simples para a demo, com provider fake e dados de seed opcionais. A execução sem Docker também deve ser documentada para desenvolvimento rápido.

## 20. Plano de implementação por etapas

Cada etapa termina com uma verificação executável.

### Etapa 0 — Contratos e spike do pacote — concluída

- [x] definir instalação direta pelo Git e fixar versão/commit;
- [x] executar um spike mínimo de `FirstMatch`, contexto, resultado e trace;
- [x] definir UUID v4, suporte a Python e gerenciador de dependências;
- [x] registrar as decisões em PT-BR.

**Pronto quando:** o pacote instala em ambiente limpo e um teste mínimo documenta sua API real.

### Etapa 1 — Base do backend — concluída

- [x] criar pacote Python, configuração tipada e aplicação FastAPI;
- [x] configurar SQLAlchemy, Alembic e SQLite;
- [x] criar primeira migration das três entidades;
- [x] implementar `/health`;
- [x] preparar `.gitignore`, `.env.example` e testes de inicialização.

**Pronto quando:** banco vazio migra e `/health` responde em teste e localmente. Validado em 29/07/2026 com 7 testes, ciclo de upgrade/downgrade da migration e health check em processo Uvicorn local.

### Etapa 2 — Domínio e API básica — concluída

- [x] implementar modelos/validações de cliente e cobrança;
- [x] normalizar telefone e preservar decimal;
- [x] implementar casos de uso e endpoints necessários;
- [x] testar transições paga/cancelada e filtros.

**Pronto quando:** cliente e cobrança podem ser criados e consultados via API. Validado em 29/07/2026 com 20 testes e `alembic check` sem divergências.

### Etapa 3 — PolicyFlow e trace — concluída

- [x] definir contexto e `NotificationDecision`;
- [x] implementar somente as policies listadas;
- [x] configurar `FirstMatch` na ordem acordada;
- [x] devolver decisão e trace pelo caso de uso puro, ainda sem HTTP assíncrono;
- [x] cobrir matriz de datas/status com relógio fixo.

**Pronto quando:** uma cobrança processada retorna decisão e trace corretos sem enviar. Validado em 29/07/2026 com 32 testes; o trace diferencia policies avaliadas e não avaliadas sem expor o telefone.

### Etapa 4 — Fila no banco e worker assíncrono — concluída

- [x] criar `ProcessingJob` e migration;
- [x] definir a porta `JobQueue` e o adaptador `DatabaseJobQueue`;
- [x] implementar reserva atômica, estados, tentativas e recuperação de lock;
- [x] criar o processo worker e os endpoints que retornam `202`;
- [x] permitir consulta do status do job;
- [x] testar concorrência e execução fora do processo HTTP.

**Pronto quando:** um botão cria um job, a API responde imediatamente e o worker executa o PolicyFlow em segundo plano. Validado em 29/07/2026 com 43 testes, disputa entre consumidores, recuperação de lock e migration alinhada.

### Etapa 5 — Notificações fake e idempotência — concluída

- [x] criar porta do provider e provider fake;
- [x] criar templates em código;
- [x] orquestrar reserva, renderização, envio e persistência;
- [x] implementar chave única e comportamento de duplicata;
- [x] implementar processamento individual e em lote.

**Pronto quando:** o fluxo completo da demo funciona e a segunda execução não duplica. Validado em 29/07/2026 com 51 testes, payload fake compatível com a Meta e smoke test em processos separados.

### Etapa 6 — Scheduler e controle da automação — concluída

- [x] criar jobs automáticos no intervalo configurado;
- [x] persistir estado habilitado/pausado;
- [x] implementar endpoints de controle;
- [x] garantir um único disparo lógico por janela;
- [x] registrar logs e reutilizar o mesmo fluxo do botão.

**Pronto quando:** uma cobrança é processada sem ação manual e o histórico prova a origem automática. Validado em 29/07/2026 com 58 testes e smoke test usando API e worker em processos separados.

### Etapa 7 — Aplicação web autenticada e observabilidade da automação

#### Etapa 7.1 — Autenticação e sessões — concluída

- [x] criar `User` e `RefreshSession`, migration e comando para criar o usuário inicial;
- [x] implementar Argon2id, access token JWT curto e refresh token opaco rotativo;
- [x] implementar login, refresh, logout, `/auth/me` e proteção das rotas;
- [x] configurar cookie por ambiente e cobrir expiração, rotação, revogação e usuário inativo.

**Pronto quando:** o usuário entra, recarrega a página sem perder a sessão, renova o acesso e o logout invalida o refresh token. Validado em 29/07/2026 com 65 testes, rotação com bloqueio de replay, revogação e migration alinhada.

#### Etapa 7.2 — Contratos para consumo do frontend — concluída

- [x] padronizar todas as listagens no envelope paginado, com 25 itens por padrão e máximo;
- [x] adicionar filtros necessários à UI e detalhe de notificação;
- [x] criar `/dashboard/summary` com métricas e janela móvel de 24 horas;
- [x] garantir que o detalhe do job contenha dados suficientes para sua inspeção.

**Pronto quando:** OpenAPI descreve paginação, filtros, métricas e detalhes sem o frontend precisar agregar tabelas ou interpretar JSON interno. Validado em 29/07/2026 com 68 testes, envelope uniforme nas quatro listagens, métricas determinísticas e resultado do job tipado no OpenAPI.

#### Etapa 7.3 — Fundação do frontend e sessão — concluída

- [x] criar React, TypeScript e Vite;
- [x] configurar rotas públicas/privadas, layout, cliente HTTP e TanStack Query;
- [x] implementar login, restauração da sessão, refresh coordenado e logout;
- [x] adaptar os padrões do `mvp-painel-loja-local` sem importar RBAC ou contexto de loja;
- [x] criar componentes base de tabela, paginação, formulário, feedback, estado vazio e erro.

**Pronto quando:** a aplicação abre no login, mantém o usuário conectado com segurança e navega pelo shell autenticado. Validado em 29/07/2026 com lint, 5 testes de frontend e build de produção; o shell responsivo e a identidade visual própria do DueFlow estão preparados para as telas funcionais.

#### Etapa 7.4 — Visão geral do negócio — concluída

- [x] criar cartões para clientes, cobranças pendentes, vencidas, vencendo hoje, próximos vencimentos, lembretes enviados e falhas de envio;
- [x] exibir estado da automação e ações habilitar, pausar e verificar agora;
- [x] separar métricas de negócio dos dados técnicos de execução;
- [x] mostrar instante da última atualização e polling de 10 segundos;
- [x] pausar polling com aba oculta e atualizar ao recuperar foco.

**Pronto quando:** a tela inicial apresenta a situação das cobranças em linguagem de negócio e permite perceber a automação funcionando sem expor jobs, retries ou traces. Refinado em 29/07/2026 com métricas de vencimento calculadas no fuso do negócio e acompanhamento assíncrono em linguagem simplificada.

#### Etapa 7.5 — Clientes

- [x] implementar listagem paginada, criação e filtros;
- [x] implementar detalhe e edição;
- [x] mostrar cobranças relacionadas no detalhe.

**Pronto quando:** o ciclo de clientes funciona integralmente pela interface. Validado em 29/07/2026 com 11 testes de frontend, filtros e paginação persistidos na URL, formulário reutilizável de criação e edição, cobranças relacionadas no detalhe, lint e build de produção.

#### Etapa 7.6 — Cobranças

- [x] implementar listagem paginada e filtros de situação;
- [x] implementar criação, detalhe e edição;
- [x] adicionar ações pagar, cancelar e verificar agora com confirmação e feedback.

**Pronto quando:** o ciclo principal de cobrança funciona integralmente pela interface. Validado em 29/07/2026 com 14 testes de frontend, filtros e paginação persistidos na URL, ações confirmadas em diálogo e feedback assíncrono sem expor identificadores técnicos.

#### Etapa 7.7 — Execuções da automação

- [x] implementar listagem paginada das execuções por status e origem;
- [x] fazer polling a cada 2 segundos enquanto houver itens pendentes e desacelerar quando estável;
- [x] implementar detalhe técnico com linha do tempo, tentativas, decisões, trace, resultados e erros;
- [x] interromper polling do detalhe em estados terminais.

**Pronto quando:** a área avançada permite acompanhar `queued → processing → completed/failed` e explicar visualmente cada execução sem misturar esses dados com a Visão geral. Validado em 29/07/2026 com 17 testes de frontend, filtros e paginação na URL, polling adaptativo de 2/15 segundos, interrupção do polling em estado terminal, detalhe completo do PolicyFlow, lint e build de produção.

#### Etapa 7.8 — Histórico de notificações

- implementar listagem paginada com filtros;
- implementar detalhe da mensagem/tentativa e vínculos para cliente, cobrança e job;
- diferenciar visualmente envio simulado, sucesso e falha.

**Pronto quando:** toda tentativa pode ser encontrada e auditada sem Swagger.

#### Etapa 7.9 — Qualidade da experiência e roteiro

- tratar loading, estados vazios, erros, confirmações e responsividade;
- manter paginação e filtros na URL;
- cobrir login, sessão, polling e roteiro principal com testes de frontend e ponta a ponta;
- validar acessibilidade básica por teclado e contraste.

**Pronto quando:** o roteiro principal funciona de modo previsível sem Swagger ou comandos manuais.

### Etapa 8 — WhatsApp real

- implementar cliente Meta e sanitização;
- testar via HTTP mock;
- validar manualmente com destinatário autorizado;
- documentar configuração e fallback simulado.

**Pronto quando:** a integração real pode ser habilitada somente por ambiente e uma falha fica auditável.

### Etapa 9 — Empacotamento, demo e deploy

- criar Docker/Compose;
- criar seed determinístico com cobranças nos três cenários;
- finalizar README e checklist;
- testar instalação limpa e PostgreSQL;
- realizar ensaio do vídeo e deploy em VPS simples.

**Pronto quando:** outra pessoa sobe o projeto seguindo apenas o README.

A ordem prioriza primeiro a decisão pura, depois a execução assíncrona e só então os efeitos de notificação. Assim, a automação pode ser demonstrada com jobs observáveis antes de depender da API real da Meta.

## 21. Checklist da demonstração

- [ ] Ambiente usa provider `simulated` e relógio/data previsível.
- [ ] Banco está migrado e seed opcional carregado.
- [ ] Cliente de teste tem telefone válido.
- [ ] Há cobrança vencendo hoje ou dentro da janela.
- [ ] Cadastrar cliente pela interface.
- [ ] Cadastrar cobrança pela interface.
- [ ] Clicar em **Processar agora**.
- [ ] Mostrar `FirstMatch`, policies avaliadas, policy vencedora e motivo.
- [ ] Mostrar mensagem e tentativa `simulated` no histórico.
- [ ] Processar novamente e mostrar que não duplicou.
- [ ] Opcional: trocar para provider Meta e mostrar recebimento no número autorizado.
- [ ] Ter gravação/plano alternativo caso a API Meta esteja indisponível.
- [ ] Confirmar que tokens e telefone completo não aparecem em logs ou vídeo.

## 22. Riscos e pontos em aberto

| Item | Risco/decisão pendente | Recomendação |
|---|---|---|
| Evolução do `policy_flow` | Projeto está em `0.1.0` e ainda não possui releases/tags | Fixar hash do commit e atualizar conscientemente |
| Semântica de retry | `failed` pode ou não significar mensagem aceita | Tratar por categoria de erro; no início, retry manual |
| Concorrência | Jobs manuais e automáticos podem atingir a mesma cobrança | Deduplicação do job, reserva transacional e idempotência da notificação |
| SQLite | Contenção com vários processos | Limitar à demo; PostgreSQL em produção |
| Worker | Dois consumidores podem reservar o mesmo job | Reserva atômica, lock com expiração e constraint de deduplicação |
| Scheduler | Duplicação da varredura automática | Chave lógica por janela de execução e processo único no MVP |
| Meta templates | Conversas iniciadas pela empresa podem exigir template aprovado | Confirmar formato e conta de teste antes da etapa real |
| Trace | API real do pacote pode não expor todos os passos desejados | Adaptar o nível de detalhe sem acoplar domínio a internals |
| Reagendamento | Alteração de `due_date` redefine notificações? | Incluir `due_date` na chave, sujeito a validação comercial |
| Atraso | Enviar uma vez ou diariamente enquanto atrasada? | Uma vez no MVP; cadência fica fora do escopo |
| PII | Mensagem e destino são persistidos | Restringir acesso, mascarar logs e definir retenção depois |
| Sessão | Refresh token roubado pode prolongar acesso | Cookie `HttpOnly`/`Secure`, rotação, hash no banco e revogação no logout |
| Polling | Muitas abas podem aumentar consultas ao banco | Pausar em aba oculta, desacelerar quando estável e manter respostas agregadas pequenas |
| Métricas | Contagens ambíguas enfraquecem a demonstração | Definir nomes e janela móvel de 24 horas no contrato da API |
| Deploy | VPS, domínio e TLS ainda não escolhidos | Manter imagem portátil e decidir na etapa 8 |

Funcionalidades tentadoras que devem continuar fora: editor de templates, retry sofisticado, recorrência, webhooks de entrega, cadastro/recuperação de senha, RBAC, dashboards gráficos e múltiplos canais. Nenhuma é necessária para validar decisão, envio e idempotência.

## 23. Possíveis evoluções depois do MVP

- isolamento por organização, RBAC, cadastro e recuperação de senha;
- templates editáveis, versionados e aprovados;
- webhooks da Meta e estados de entrega/leitura;
- políticas de retry com backoff e fila;
- lembretes recorrentes e cadência configurável;
- importação CSV;
- novos canais, como e-mail;
- trilha completa de `ProcessingRun`;
- métricas operacionais e retenção de PII;
- integração com pagamentos para baixa automática;
- scheduler gerenciado ou workers quando o volume justificar.

## Próxima ação recomendada

Iniciar a **Etapa 7.8 — Histórico de notificações**: implementar listagem paginada, filtros, detalhe de cada tentativa e vínculos com cliente, cobrança e execução.
