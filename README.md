# DueFlow

Aplicação web para cadastrar cobranças, decidir lembretes com o PolicyFlow e enviar mensagens pelo WhatsApp em modo fake ou pela API oficial da Meta.

O projeto está em construção. A documentação de escopo está em [`docs/plano-mvp.md`](docs/plano-mvp.md), e as decisões técnicas ficam em [`docs/decisoes`](docs/decisoes).

## Backend local

Requisitos:

- Python 3.12 ou 3.13;
- Git, necessário para instalar o PolicyFlow.

No PowerShell, a partir da raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "./backend[dev]"
Copy-Item .env.example .env
python -m alembic -c backend/alembic.ini upgrade head
python -m dueflow.cli create-admin --email admin@example.com --name "Administrador"
python -m uvicorn dueflow.main:app --reload
```

O comando `create-admin` solicita e confirma a senha sem exibi-la. A API fica disponível em `http://localhost:8000` e o health check em `http://localhost:8000/health`.

Para redefinir uma senha local:

```powershell
python -m dueflow.cli reset-password --email admin@example.com
```

A troca revoga todas as sessões abertas desse usuário.

## Autenticação

Somente `/health`, `/auth/login`, `/auth/refresh` e os webhooks da Meta são
públicos. A verificação do webhook usa um token próprio e o recebimento de
eventos exige uma assinatura HMAC válida. As demais rotas exigem
`Authorization: Bearer <access_token>`.

```text
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
POST /auth/change-password
```

O access token dura 15 minutos por padrão. O refresh token fica em cookie `HttpOnly`, é rotacionado a cada renovação e revogado no logout. Em produção, a aplicação recusa o segredo de desenvolvimento e exige `AUTH_COOKIE_SECURE=true`.

Em outro terminal, com o mesmo ambiente ativado, inicie o worker:

```powershell
python -m dueflow.worker
```

O worker consulta a fila no banco a cada dois segundos. Ele executa o PolicyFlow, renderiza a mensagem e usa o provider configurado. O padrão é `MESSAGE_PROVIDER=fake`, que não acessa a rede.

Para validar o produto integralmente pela interface, consulte o
[roteiro de demonstração](docs/roteiro-demonstracao.md).

## Frontend local

Requisitos:

- Node.js 22;
- API disponível em `http://localhost:8000`;
- usuário administrativo criado no backend.

Em outro terminal:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

O painel fica disponível em `http://localhost:5173`. A fundação inclui login, restauração da sessão por refresh token, renovação coordenada após `401`, rotas privadas, shell responsivo e componentes visuais reutilizáveis.

A tela inicial apresenta uma visão de negócio: clientes, cobranças pendentes, vencidas, vencendo hoje, próximos vencimentos, lembretes enviados e falhas que precisam de atenção. Ela consulta as métricas a cada 10 segundos, controla a automação e permite solicitar uma verificação manual sem expor jobs ou identificadores técnicos.

A área de clientes oferece busca, filtro por situação e paginação persistidos na URL, além de criação, detalhe, edição e consulta das cobranças relacionadas.

A área de cobranças oferece busca, filtros por situação e vencimento, criação, detalhe e edição. Cobranças pendentes podem ser marcadas como pagas, canceladas ou verificadas imediatamente pelas regras, sempre com confirmação e feedback na interface.

A área **Execuções da automação** concentra o diagnóstico técnico: listagem paginada por estado, origem e tipo, polling rápido enquanto houver trabalho ativo e detalhe com linha do tempo, tentativas, resultados, decisões, traces do PolicyFlow, erros e payload original. Quando a fila fica estável, a atualização desacelera; no detalhe, ela é encerrada ao atingir um estado terminal.

A área **Histórico de mensagens** oferece registros paginados por resultado, canal e tipo de mensagem. O detalhe mostra conteúdo, destino, provider, política, motivo, trace, chave de idempotência, resposta segura do provider e vínculos para cliente, cobrança e execução. Envios simulados, enviados e com falha recebem tratamentos visuais distintos.

Para validar o frontend:

```powershell
npm.cmd run lint
npm.cmd run test
npm.cmd run build
```

Para executar os testes:

```powershell
python -m pytest backend/tests
```

## API disponível

### Clientes

- `POST /customers`
- `GET /customers`
- `GET /customers/{id}`
- `PUT /customers/{id}`

O telefone deve incluir o código do país e é normalizado para E.164. Exemplo:

```json
{
  "name": "Empresa Exemplo",
  "phone": "+55 (11) 99999-0000",
  "active": true
}
```

### Cobranças

- `POST /charges`
- `GET /charges`
- `GET /charges/{id}`
- `PUT /charges/{id}`
- `POST /charges/{id}/mark-paid`
- `POST /charges/{id}/cancel`

Todas as listagens aceitam `page` e `page_size`, com 25 itens por padrão e no máximo. A resposta contém `items`, `page`, `page_size`, `total` e `pages`. Cobranças também podem ser filtradas por `status`, `customer_id`, período de vencimento e busca por descrição:

```text
GET /charges?status=pending&customer_id=<uuid>&page=1&page_size=25
```

Valores monetários devem ser enviados como string decimal:

```json
{
  "customer_id": "00000000-0000-0000-0000-000000000000",
  "description": "Mensalidade",
  "amount": "1234.56",
  "due_date": "2026-07-31",
  "reminder_days_before": 3
}
```

`paid` e `canceled` são estados terminais. Repetir a mesma transição é idempotente; tentar trocar de um estado terminal para outro retorna `409`.

## Decisão de notificação

O núcleo de decisão usa o PolicyFlow com estratégia `FirstMatch`. Nesta ordem:

1. cliente inativo;
2. cobrança paga;
3. cobrança cancelada;
4. telefone inválido;
5. cobrança atrasada;
6. cobrança vencendo hoje;
7. cobrança dentro da janela de lembrete;
8. nenhuma notificação aplicável.

O caso de uso puro retorna uma `NotificationDecision` e um trace próprio do DueFlow. A API apenas enfileira o pedido; o worker chama esse caso de uso em segundo plano e executa o efeito somente quando a decisão é elegível.

## Processamento assíncrono

Para enfileirar todas as cobranças pendentes:

```http
POST /processing/run
Content-Type: application/json

{}
```

Para uma cobrança específica:

```http
POST /charges/{id}/process
Content-Type: application/json

{}
```

Os endpoints respondem imediatamente com HTTP `202`:

```json
{
  "job_id": "00000000-0000-0000-0000-000000000000",
  "status": "queued",
  "created": true
}
```

Consulte o andamento em:

```text
GET /processing/jobs
GET /processing/jobs/{job_id}
```

`GET /processing/jobs` aceita filtros `origin=manual|automatic` e `status`. O estado percorre `queued`, `processing` e `completed`. Falhas definitivas terminam em `failed`. Em desenvolvimento e teste, o corpo pode receber `reference_date` para demonstrações determinísticas; esse parâmetro é rejeitado em produção.

O detalhe do job também informa origem, cobrança individual associada, duração, estado terminal e um resultado tipado com decisões, tentativas e trace das policies.

## Automação

A automação começa pausada. Consulte e controle pelo painel ou API:

```text
GET  /automation
PUT  /automation
POST /automation/enable
POST /automation/disable
```

Para habilitar com o intervalo padrão de 120 segundos:

```http
POST /automation/enable
Content-Type: application/json

{}
```

Também é possível configurar o intervalo:

```json
{
  "interval_seconds": 120
}
```

Ao habilitar, o primeiro job é criado no próximo ciclo curto do worker; as execuções seguintes respeitam o intervalo. Jobs automáticos carregam `origin=automatic` e uma chave permanente por janela, evitando dois disparos lógicos do mesmo período.

## Provider fake e histórico

O `FakeWhatsAppProvider` usa o mesmo contrato textual planejado para a API da Meta. Ele monta um payload com `messaging_product`, destinatário, tipo e corpo, mas não realiza chamada externa. A resposta simulada contém um identificador `wamid.fake.*`.

O aceite simulado deixa a entrega como `pending`. Nos ciclos seguintes, o
worker produz eventos fictícios separados, usando os mesmos estados, métricas,
polling e timeline do fluxo real:

```dotenv
FAKE_DELIVERY_OUTCOME=delivered
FAKE_DELIVERY_DELAY_SECONDS=2
FAKE_DELIVERY_ERROR_CODE=131047
```

`FAKE_DELIVERY_OUTCOME` aceita `delivered`, `read` ou `failed`. O cenário
`delivered` percorre `pending → sent → delivered`; `read` acrescenta `read`; e
`failed` percorre `pending → sent → failed` usando o código configurado. Cada
transição ocorre em um ciclo diferente do worker e é marcada como simulada na
auditoria. Nenhuma chamada é feita à Meta nem ao endpoint público de webhook.

As tentativas ficam disponíveis em:

```text
GET /notifications
GET /notifications/{id}
GET /charges/{id}/notifications
```

Uma chave formada por cobrança, vencimento e tipo de notificação impede o envio repetido. Cobranças não elegíveis aparecem no trace do job, mas não geram `NotificationAttempt`.

Falhas confirmadas e classificadas como retentáveis podem ser avaliadas e
reenviadas manualmente:

```text
GET  /notifications/{id}/recovery
POST /notifications/{id}/retry
GET  /notifications/{id}/attempts
```

O reenvio é assíncrono e retorna um job `retry_notification`. O worker revalida
a cobrança, o cliente e os estados de envio e entrega antes de agir. Resultado
incerto, mensagem em trânsito, entrega concluída e erro que exige template,
correção ou análise não liberam o botão **Tentar novamente**. Cada reenvio cria
uma tentativa numerada, preserva a falha anterior e registra a tentativa de
origem e o usuário solicitante.

## Provider Meta

O worker também pode enviar mensagens de texto pela API oficial do WhatsApp
Cloud. O modo real é habilitado apenas por ambiente e exige todas as
configurações abaixo:

```dotenv
MESSAGE_PROVIDER=meta
META_WHATSAPP_TOKEN=
META_WHATSAPP_PHONE_NUMBER_ID=
META_GRAPH_API_VERSION=
META_GRAPH_API_BASE_URL=https://graph.facebook.com
META_REQUEST_TIMEOUT_SECONDS=10
META_WEBHOOK_VERIFY_TOKEN=
META_APP_SECRET=
META_TEMPLATE_MODE=retry_only
META_TEMPLATE_NAME=dueflow_aviso_cobranca_v1
META_TEMPLATE_LANGUAGE=pt_BR
```

`META_GRAPH_API_VERSION` deve ser preenchida explicitamente com a versão
habilitada na aplicação da Meta, no formato `vNN.N`. O projeto não fixa uma
versão silenciosamente para evitar que uma atualização da Graph API altere o
comportamento sem revisão.

Antes de iniciar o worker, é possível fazer um envio deliberado para um
destinatário autorizado:

```powershell
cd backend
python -m dueflow.cli test-meta --to +5511999999999
```

O comando não é executado pela suíte e mascara o telefone na saída. Tokens,
headers de autorização, telefones presentes na resposta e respostas brutas de
erro não são persistidos. Timeout, falha de rede, resposta inválida e erros
HTTP são convertidos em mensagens seguras e auditáveis.

O detalhe de cada cobrança apresenta seu **Histórico de envios** com provider e
resultado. Ao abrir uma tentativa, o painel informa claramente se o envio foi
simulado ou realizado pela Meta, mostra o status HTTP, o identificador devolvido
pela Meta e a correlação. O JSON completo permanece disponível em **Dados
técnicos sanitizados**.

Para voltar ao modo de demonstração sem rede:

```dotenv
MESSAGE_PROVIDER=fake
```

Mensagens de texto livres dependem de uma conversa aberta na janela permitida
pela Meta. Para iniciar conversas fora dessa janela, será necessário cadastrar
e usar um template aprovado compatível com as mensagens do DueFlow.

`META_TEMPLATE_MODE=retry_only` mantém texto livre como caminho normal e
oferece **Reenviar com template** quando uma falha, como a `131047`, exigir uma
nova conversa. Depois da demonstração, `META_TEMPLATE_MODE=always` transforma o
mesmo template no formato padrão dos lembretes, sem alterar as policies ou os
jobs.

O template esperado possui quatro parâmetros de corpo, nesta ordem:

1. nome do cliente;
2. descrição da cobrança;
3. valor em reais;
4. vencimento em `dd/mm/aaaa`.

O modo fake gera o mesmo payload de template, marca a tentativa como simulada e
percorre o fluxo assíncrono de entrega. Nome, idioma, parâmetros e conteúdo
renderizado ficam disponíveis no detalhe da mensagem mesmo quando a submissão
falha. O envio real de texto livre foi validado localmente e no Render em
29/07/2026, incluindo o recebimento no celular e os eventos do webhook. Permanece
pendente somente a validação externa do template configurado.

### Webhook de entrega

Configure na Meta uma URL HTTPS pública apontando para:

```text
GET  /webhooks/meta
POST /webhooks/meta
```

Use em `META_WEBHOOK_VERIFY_TOKEN` um valor aleatório exclusivo para a
verificação da URL. `META_APP_SECRET` deve conter o App Secret da aplicação e é
usado para validar `X-Hub-Signature-256` sobre o corpo bruto de cada evento.
Esses valores não devem ser iguais ao token de acesso do WhatsApp.

Depois de validar a URL, assine o campo `messages` da conta do WhatsApp
Business. O DueFlow correlaciona `statuses` pelo `wamid` e mantém dois
resultados independentes:

- envio para a Meta: `pending`, `succeeded`, `failed`, `unknown` ou
  `simulated`;
- entrega no WhatsApp: `not_started`, `pending`, `sent`, `delivered`, `read`
  ou `failed`.

Timeout e falha de rede ficam como `unknown`, pois não comprovam se a Meta
aceitou a solicitação. Um HTTP de sucesso registra apenas o aceite e nunca é
apresentado como entrega confirmada.

Eventos duplicados, desconhecidos ou regressivos são aceitos sem alterar o
histórico. Em falhas, somente código, título, detalhes e metadados sanitizados
necessários à auditoria são persistidos; o payload bruto e campos internos da
Meta são descartados. O painel apresenta uma timeline com envio e entrega,
traduz códigos conhecidos — incluindo o `131047` — e usa uma orientação
genérica em português para códigos ainda não catalogados. Os detalhes técnicos
sanitizados continuam disponíveis para diagnóstico.

O endpoint retorna `503` enquanto os segredos do webhook não estiverem
configurados. Para o teste externo, a API precisa estar acessível pela Meta por
HTTPS; o painel atualiza automaticamente o estado enquanto a entrega ainda está
pendente.

Referências oficiais: [envio de mensagens pela Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages),
[códigos de erro do WhatsApp](https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/)
e [versionamento da Graph API](https://developers.facebook.com/docs/graph-api/changelog/versions).

## Visão geral e diagnóstico operacional

O resumo destinado ao polling da tela inicial está disponível em:

```text
GET /dashboard/summary
```

A resposta informa clientes cadastrados, cobranças pendentes, vencidas, vencendo hoje, vencendo nos próximos sete dias e lembretes processados nas últimas 24 horas. O contrato mantém contagens técnicas de execuções, avaliações, retries e falhas para a área avançada **Execuções da automação**, mas a Visão geral não apresenta esses dados como indicadores de negócio. `generated_at` e `window_started_at` deixam a janela móvel explícita.

## Idioma da documentação

Os documentos Markdown do repositório são escritos em português do Brasil. Nomes de código e termos definidos por bibliotecas permanecem em inglês quando isso torna a implementação mais clara.

## Deploy da demonstração

O repositório inclui uma imagem única com frontend, API e worker, um
`compose.yaml` para execução local e um Blueprint do Render. O banco recomendado
para a demonstração é o PostgreSQL gratuito do Neon.

O passo a passo completo está em
[Deploy gratuito no Render com Neon](docs/deploy-render-neon.md).

Resumo:

1. crie o projeto `dueflow-demo` no Neon;
2. copie a connection string;
3. envie o repositório ao GitHub;
4. escolha **New > Blueprint** no Render;
5. preencha `DATABASE_URL`, `INITIAL_ADMIN_EMAIL` e
   `INITIAL_ADMIN_PASSWORD`;
6. acesse a URL gerada e ative a automação.

O serviço aplica a baseline do Alembic, cria o administrador e carrega três
cobranças idempotentes para a demonstração. Nenhum segredo deve ser enviado ao
Git.
