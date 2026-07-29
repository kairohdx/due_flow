# Deploy gratuito no Render com Neon

Este roteiro publica o DueFlow como uma demonstração sem cartão:

- um Web Service gratuito no Render;
- frontend, API e worker na mesma imagem;
- PostgreSQL gratuito e persistente no Neon.

O serviço gratuito do Render dorme depois de 15 minutos sem tráfego. Enquanto o
painel estiver aberto, o polling mantém o serviço ativo e o worker processa a
fila normalmente. Ao acordar, o worker recupera locks expirados e o scheduler
retoma a automação.

## 1. Criar o banco no Neon

1. Crie o projeto `dueflow-demo`.
2. Mantenha o Neon Auth desativado.
3. Copie a connection string com `sslmode=require`.
4. Guarde a URL completa; ela será cadastrada como segredo no Render.

O DueFlow aceita tanto `postgresql://` quanto `postgresql+psycopg://` e
seleciona o driver Psycopg automaticamente.

## 2. Publicar o repositório

Envie a branch com a Etapa 9 para o GitHub. Não envie `.env`, connection string,
senha administrativa, token da Meta ou App Secret.

## 3. Criar o Blueprint no Render

1. No Render, escolha **New > Blueprint**.
2. Conecte o repositório do DueFlow.
3. Confirme o arquivo `render.yaml`.
4. Preencha os valores solicitados:
   - `DATABASE_URL`: connection string do Neon;
   - `INITIAL_ADMIN_EMAIL`: e-mail usado no primeiro login;
   - `INITIAL_ADMIN_PASSWORD`: senha forte exclusiva para a demo.
5. Confirme a criação do serviço gratuito.

O Blueprint gera `JWT_SECRET`, ativa cookies seguros, aplica as migrations,
cria o administrador, carrega o seed idempotente e inicia API e worker.

## 4. Validar

Quando o deploy terminar:

1. abra `https://dueflow-demo.onrender.com/health`;
2. confirme `{"status":"ok","database":"ok"}`;
3. abra `https://dueflow-demo.onrender.com`;
4. entre com o administrador configurado;
5. ative a automação em **Configurações**;
6. mantenha o painel aberto durante a demonstração;
7. execute o roteiro em `docs/roteiro-demonstracao.md`.

O primeiro acesso após o serviço dormir pode levar cerca de um minuto.

## 5. Integração com a Meta

O deploy começa com:

```dotenv
MESSAGE_PROVIDER=fake
META_TEMPLATE_MODE=retry_only
META_TEMPLATE_NAME=dueflow_aviso_cobranca_v1
META_TEMPLATE_LANGUAGE=pt_BR
```

O provider real pode ser habilitado antes da aprovação do template para testar
texto livre dentro de uma janela de atendimento válida. Altere
`MESSAGE_PROVIDER` para `meta` e cadastre token, Phone Number ID, versão da Graph
API, Verify Token e App Secret como segredos do Render.

O envio de texto livre foi validado localmente e no Render em 29/07/2026, com
recebimento no celular e acompanhamento dos estados pelo webhook. Mantenha
`META_TEMPLATE_MODE=retry_only` durante a demonstração. O envio externo com
template continua pendente até a aprovação de `dueflow_aviso_cobranca_v1` pela
Meta.

## Execução local equivalente

Crie um `.env` local com:

```dotenv
JWT_SECRET=troque-por-um-segredo-com-mais-de-32-caracteres
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=troque-esta-senha
DEMO_SEED_ENABLED=true
```

Depois execute:

```powershell
docker compose up --build
```

O painel ficará em `http://localhost:8000`.
