# Decisão 0001 — Integração com o PolicyFlow

- **Status:** aceita
- **Data:** 29/07/2026

## Contexto

O DueFlow precisa escolher uma única ação para cada cobrança processada e mostrar por que essa ação foi escolhida. O pacote próprio `policy_flow` está disponível no repositório público [kairohdx/policy_flow](https://github.com/kairohdx/policy_flow).

Esta decisão registra o contrato verificado durante a Etapa 0. Toda documentação Markdown mantida neste repositório deve ser escrita em português do Brasil. Identificadores de código, payloads e termos impostos por bibliotecas podem permanecer em inglês.

## Decisão

Usar o pacote `policyflow-engine` na versão `0.1.0`, instalado diretamente do GitHub e fixado no commit:

```text
f86141837ae62a01d074e06fe1bd76b22fcc6153
```

Declaração prevista no `pyproject.toml` do backend:

```toml
dependencies = [
    "policyflow-engine @ git+https://github.com/kairohdx/policy_flow.git@f86141837ae62a01d074e06fe1bd76b22fcc6153",
]
```

Fixar o commit é necessário porque o pacote ainda está em fase inicial e não possui release ou tag publicada. Atualizações deverão trocar o hash de forma explícita e executar novamente os testes de contrato.

## Contrato verificado

O spike foi executado em Python 3.13.3, com instalação em ambiente virtual limpo diretamente pela URL Git. O pacote declara suporte a Python 3.11 ou superior e não possui dependências obrigatórias.

Foram verificadas as seguintes APIs públicas:

- `PolicyEngine[Contexto, Efeito]`;
- decorador `@rule(id="...")`;
- `RuleResult.pass_`, `RuleResult.consume` e seus campos `effect`, `reason` e `attributes`;
- `FirstMatch`;
- `engine.add_scope(...)`;
- `engine.run(...)`;
- `Execution.decision` e `Execution.decisions`;
- `Execution.trace` e seus eventos.

O teste usou duas regras na ordem:

1. `skip-paid`;
2. `due-today`.

Para uma cobrança pendente vencendo hoje, a primeira regra retornou `pass`, a segunda retornou `consume` e foi selecionada. Para uma cobrança paga, a primeira regra foi selecionada e a segunda não foi avaliada. Isso confirma a interrupção esperada do `FirstMatch`.

## Trace observado

O trace público fornece:

- identificadores de trace e execução;
- nome do pipeline;
- início, fim, duração e status;
- atributos informados pela aplicação;
- eventos ordenados;
- regra avaliada, resultado, motivo e duração;
- estratégia utilizada;
- quantidade de regras avaliadas;
- regra selecionada e efeito proposto.

Os principais eventos observados foram:

```text
execution.started
scope.entered
rule.evaluated
resolution.completed
effect.proposed
scope.exited
execution.completed
```

Esse contrato atende à explicabilidade do MVP. A API do DueFlow deverá converter o trace para um DTO próprio, evitando expor diretamente classes internas ou depender de uma sequência rígida de eventos.

## Limites de responsabilidade

O PolicyFlow:

- avalia regras na ordem configurada;
- resolve o primeiro resultado terminal;
- retorna a decisão e o trace.

O DueFlow:

- monta o contexto;
- interpreta o efeito;
- verifica idempotência;
- renderiza a mensagem;
- chama o provider fake ou a API oficial da Meta;
- persiste a tentativa;
- controla transações e estados.

As regras não devem acessar banco de dados, relógio global, FastAPI ou WhatsApp.

## Providers de WhatsApp

A abstração de provider não representa suporte planejado a vários sistemas de mensagens. Ela existe para manter dois modos intercambiáveis:

- `FakeWhatsAppProvider`: não acessa rede e registra resultado simulado;
- `MetaWhatsAppProvider`: usa a API oficial da Meta com credencial de teste e número real autorizado.

Nenhum provider de e-mail, SMS ou plataforma de terceiros faz parte do MVP.

## Decisões complementares

- Python suportado pelo DueFlow: `>=3.12,<3.14`.
- Versão de referência para container e produção: Python 3.12.
- Gerenciamento inicial: `pip` e `pyproject.toml`.
- Identificadores das entidades: UUID v4 gerado pela aplicação.
- Código pode usar nomes técnicos em inglês; documentação Markdown deve estar em PT-BR.

## Consequências

- Builds ficam reproduzíveis enquanto o commit continuar disponível.
- Atualizar o pacote exige uma ação consciente e novos testes.
- O DueFlow pode mostrar o trace sem implementar observabilidade própria.
- Um DTO interno protege a API do DueFlow contra mudanças no formato do pacote.
- A Etapa 1 pode começar sem criar um adaptador que replique o motor de políticas.

## Próximo passo

Criar a base do backend e declarar a dependência Git fixada. O primeiro teste permanente relacionado ao pacote deve reproduzir os dois comportamentos do spike: continuar após `pass` e interromper após o primeiro resultado terminal.
