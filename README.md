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

Somente `/health`, `/auth/login` e `/auth/refresh` são públicos. As demais rotas exigem `Authorization: Bearer <access_token>`.

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

As tentativas ficam disponíveis em:

```text
GET /notifications
GET /notifications/{id}
GET /charges/{id}/notifications
```

Uma chave formada por cobrança, vencimento e tipo de notificação impede o envio repetido. Cobranças não elegíveis aparecem no trace do job, mas não geram `NotificationAttempt`.

## Visão geral e diagnóstico operacional

O resumo destinado ao polling da tela inicial está disponível em:

```text
GET /dashboard/summary
```

A resposta informa clientes cadastrados, cobranças pendentes, vencidas, vencendo hoje, vencendo nos próximos sete dias e lembretes processados nas últimas 24 horas. O contrato mantém contagens técnicas de execuções, avaliações, retries e falhas para a área avançada **Execuções da automação**, mas a Visão geral não apresenta esses dados como indicadores de negócio. `generated_at` e `window_started_at` deixam a janela móvel explícita.

## Idioma da documentação

Os documentos Markdown do repositório são escritos em português do Brasil. Nomes de código e termos definidos por bibliotecas permanecem em inglês quando isso torna a implementação mais clara.
