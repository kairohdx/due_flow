# Decisão 0003 — Scheduler dentro do processo worker

- **Status:** aceita
- **Data:** 29/07/2026

## Contexto

O MVP precisa demonstrar que cobranças são processadas automaticamente e fora da requisição HTTP. Também precisa permitir que o usuário habilite ou pause a automação por um botão.

## Decisão

O scheduler roda no mesmo processo contínuo do worker, separado da API:

```text
FastAPI → banco ← worker + scheduler
```

O worker:

1. verifica se a janela automática está vencida;
2. reserva essa janela de forma atômica;
3. cria um job `process_due_charges` com origem `automatic`;
4. consome jobs disponíveis;
5. executa o mesmo caso de uso usado pelo botão manual.

O estado da automação é persistido em uma linha singleton da tabela `automation_settings`.

## Regras

- A automação começa desabilitada.
- Habilitar agenda a primeira execução imediatamente.
- O intervalo padrão é 120 segundos.
- Pausar impede novas criações automáticas, sem apagar o histórico.
- Cada janela possui uma chave de deduplicação permanente.
- Jobs manuais liberam a chave ao terminar; jobs automáticos preservam a chave da janela.
- A data de referência automática usa `America/Sao_Paulo`.

## Consequências

- API e worker continuam processos independentes.
- Não é necessário adicionar cron Linux ou APScheduler.
- O frontend pode mostrar jobs filtrados por `origin=automatic`.
- Duas instâncias do worker não devem criar a mesma janela.
- Uma futura fila externa pode manter o scheduler e trocar apenas o adaptador `JobQueue`.

