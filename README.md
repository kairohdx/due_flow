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

## Autenticação

Somente `/health`, `/auth/login` e `/auth/refresh` são públicos. As demais rotas exigem `Authorization: Bearer <access_token>`.

```text
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

O access token dura 15 minutos por padrão. O refresh token fica em cookie `HttpOnly`, é rotacionado a cada renovação e revogado no logout. Em produção, a aplicação recusa o segredo de desenvolvimento e exige `AUTH_COOKIE_SECURE=true`.

Em outro terminal, com o mesmo ambiente ativado, inicie o worker:

```powershell
python -m dueflow.worker
```

O worker consulta a fila no banco a cada dois segundos. Ele executa o PolicyFlow, renderiza a mensagem e usa o provider configurado. O padrão é `MESSAGE_PROVIDER=fake`, que não acessa a rede.

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

As listagens aceitam `limit` e `offset`. Cobranças também podem ser filtradas por `status` e `customer_id`:

```text
GET /charges?status=pending&customer_id=<uuid>
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

## Automação

A automação começa pausada. Consulte e controle pelo painel ou API:

```text
GET  /automation
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
GET /charges/{id}/notifications
```

Uma chave formada por cobrança, vencimento e tipo de notificação impede o envio repetido. Cobranças não elegíveis aparecem no trace do job, mas não geram `NotificationAttempt`.

## Idioma da documentação

Os documentos Markdown do repositório são escritos em português do Brasil. Nomes de código e termos definidos por bibliotecas permanecem em inglês quando isso torna a implementação mais clara.
