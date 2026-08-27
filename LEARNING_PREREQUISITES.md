# Learning Prerequisites

Você não precisa estudar tudo antes de começar. Aprenda os conceitos no momento em que o SDD chegar à decisão correspondente.

## Antes de `/speckit.plan`

### Precisa saber conceitualmente
- workflow vs agent;
- structured output;
- tool calling;
- state/nodes/edges;
- deterministic vs probabilistic decision.

Objetivo: conseguir participar das decisões de arquitetura sem apenas aceitar o que o coding agent sugerir.

## Antes de implementar human-in-the-loop

Aprender:
- checkpoint;
- `thread_id`;
- interrupt/resume;
- idempotência básica.

## Antes de implementar MCP

Aprender:
- tool local vs servidor MCP;
- cliente/servidor;
- transporte local suficiente para a demo;
- por que MCP é interoperabilidade e não orquestração.

## Durante testes

Aprender:
- mocks/fakes de LLM;
- testes de routing/state;
- testes de tool contracts;
- poucos testes end-to-end reais.

## Não bloquear o início por falta de conhecimento

O próprio projeto deve ser a trilha de aprendizado. Quando uma task introduzir conceito novo, o agent deve explicar:

1. conceito;
2. uso neste projeto;
3. alternativa;
4. trade-off;
5. como testar.
