# Data Change Risk Analyst — SDD Discovery Starter

Este repositório **ainda não é uma implementação**. Ele é um ponto de partida para definir, questionar e validar o projeto com Spec-Driven Development antes de escrever o produto.

## Por que este pacote existe

O projeto tem dois objetivos igualmente importantes:

1. **Portfólio profissional** — produzir um projeto corporativo pequeno, coerente e tecnicamente defensável, bom o suficiente para demonstrar capacidade de AI Engineering em processos seletivos sem fingir ser uma plataforma enterprise completa.
2. **Aprendizado deliberado** — usar o projeto para aprender e conseguir explicar LangChain e LangGraph por meio de usos reais: structured output, tools, agent, state, routing, parallelization, persistence e human-in-the-loop.

A complexidade só é aceita quando melhora um desses dois objetivos.

## Hipótese de produto

O ponto de partida é um **Data Change Risk Analyst**: uma aplicação que recebe uma solicitação de mudança em um ativo de dados, investiga evidências estruturadas, avalia risco, produz uma recomendação e exige revisão humana antes da decisão final.

Exemplo inicial:

> Remover a coluna `customer_legacy_id` da tabela `orders`.

Esta hipótese **pode mudar durante clarify/analyze**. Nome, escopo, regras, dados, arquitetura e ferramentas ainda não são fatos consumados.

## O que foi removido do starter anterior

Foram removidos deliberadamente:

- `app.py`;
- `src/` com implementação LangChain/LangGraph;
- `tests/` de implementação;
- `pyproject.toml`;
- `docker-compose.yml`;
- schema e seed PostgreSQL;
- servidor MCP implementado.

Motivo: código antecipado cria **anchoring**. Um coding agent tende a tratar o que já existe como requisito implícito e apenas completar a solução. Neste pacote, a especificação deve dirigir a implementação — e não o contrário.

## O que permanece como premissa aceita

- O resultado precisa parecer corporativo e profissional na medida certa para portfólio.
- O produto deve ser pequeno e demonstrável.
- LangChain e LangGraph precisam ter papéis reais, não ornamentais.
- LangGraph deve aparecer claramente na demonstração.
- Human-in-the-loop é desejado e deve ser investigado como requisito central.
- O domínio deve privilegiar dados estruturados.
- RAG não é objetivo deste projeto.
- MCP é desejado, mas só deve entrar se agregar aprendizado/portfólio sem inflar o V0.
- Interface é desejável para portfólio, porém deve ser a opção mais simples que apresente bem o workflow.

## Como começar

Leia nesta ordem:

1. `PROJECT_BRIEF.md`
2. `CONSTITUTION_SEED.md`
3. `DISCOVERY_NOTES.md`
4. `OPEN_QUESTIONS.md`
5. `LEARNING_OBJECTIVES.md`
6. `PORTFOLIO_CRITERIA.md`
7. `SDD_WORKFLOW.md`
8. `AGENTS.md`

Depois abra Codex ou Claude Code e use `START_PROMPT.md`.

**Não peça para implementar o produto ainda.** O primeiro objetivo é transformar as hipóteses em uma especificação que sobreviva a uma rodada séria de `clarify` e `analyze`.
