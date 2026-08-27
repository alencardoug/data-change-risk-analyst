# Architecture Hypotheses

**Não é plano aprovado.** Este arquivo existe para dar alternativas concretas à fase `/speckit.plan` e evitar que o agent trate a primeira ideia como inevitável.

## Hipótese A — Workflow-first (preferida até prova em contrário)

- LangGraph controla etapas e decisões de processo.
- LangChain fornece model abstraction, structured output, tools e um agent investigador limitado.
- Regras críticas ficam determinísticas.
- Human review usa pausa/retomada do graph.

Vantagem: demonstra com clareza workflow vs agent.

Risco: podemos adicionar nodes apenas para mostrar recursos do framework.

## Hipótese B — Quase todo determinístico + uma única etapa LLM

- parsing e recommendation usam LLM;
- coleta/risco são totalmente determinísticos;
- sem investigator agent no V0.

Vantagem: V0 muito pequeno.

Risco: aprendizado de agent/tool calling fica pobre.

## Hipótese C — Agent-first com guardrails externos

- agent decide quais investigações executar;
- graph controla apenas gates/approval.

Vantagem: mais comportamento agentic.

Risco: maior variabilidade e talvez pior demonstração de um processo corporativo controlado.

## Hipótese de dados

Começar com poucos ativos simulados e poucas relações. PostgreSQL é candidato, mas a fase plan deve comparar:

- fixture/in-memory primeiro;
- SQLite;
- PostgreSQL desde o início.

Escolher o menor que não prejudique a demo e o aprendizado.

## Hipótese de MCP

Alternativas:

1. sem MCP no V0, adicionar depois;
2. uma tool do agent via MCP desde V0;
3. todas as tools externas via MCP.

Critério: MCP só entra cedo se o aprendizado incremental compensar a complexidade operacional.

## Hipótese de interface

Preferência inicial: uma UI simples que mostre:
- entrada;
- etapas concluídas;
- evidências;
- risco;
- recommendation;
- pausa para decisão humana.

Streamlit é candidato, não requisito.

## Hipótese de observabilidade

Tracing local/log estruturado pode bastar. LangSmith é opcional e deve entrar apenas se ajudar a demonstrar tool calls e execução do graph sem muito esforço.
