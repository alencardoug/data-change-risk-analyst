# Learning Objectives

Este projeto deve ensinar por implementação, não apenas usar bibliotecas.

## Obrigatório — LangChain

### Structured output
Aprender:
- por que schema é superior a parsing textual ad hoc;
- Pydantic/contratos;
- validação e tratamento de saída inválida.

Aplicação candidata:
- interpretar change request;
- produzir recommendation estruturada.

### Tools
Aprender:
- tool como capacidade externa com contrato estreito;
- diferença entre função Python, tool e integração MCP;
- limites de acesso e segurança.

### Agent
Aprender:
- agent como loop dinâmico de uso de tools;
- quando autonomia ajuda e quando um workflow determinístico é melhor;
- como limitar o agent a investigação read-only.

## Obrigatório — LangGraph

### State
Entender o estado como contrato do workflow, não como “memória mágica”.

### Nodes e edges
Saber explicar o que merece virar node e por quê.

### Conditional routing
Separar decisões determinísticas de decisões LLM-driven.

### Parallelization / reducers
Aprender apenas se houver subtarefas realmente independentes. Se for usado, saber explicar como múltiplos branches atualizam state sem conflito.

### Persistence / checkpointing
Entender `thread_id`, checkpoints e retomada de execução.

### Interrupt / human-in-the-loop
Entender que a execução é suspensa e depois retomada com nova entrada humana.

### Loops
Usar somente se o caso `edit/revise` permanecer no escopo.

## MCP — desejável, não obrigatório no primeiro incremento

Aprender:
- o problema de interoperabilidade que MCP resolve;
- diferença entre tool local e tool exposta por servidor MCP;
- lifecycle/transporte suficiente para uma demo local;
- por que MCP não substitui LangChain, LangGraph, banco ou API.

## Conceitos adjacentes que você deve aprender durante o projeto

### 1. Deterministic vs probabilistic boundaries — PRIORIDADE ALTA
Você deve saber defender por que algumas decisões ficam no LLM e outras no código.

### 2. Idempotência e retomada — PRIORIDADE MÉDIA
Human-in-the-loop e retries exigem pensar no que pode ou não ser executado mais de uma vez.

### 3. Testes de sistemas com LLM — PRIORIDADE ALTA
Distinguir:
- testes unitários determinísticos;
- mocks/fakes de modelo;
- poucos testes de integração com LLM real;
- avaliação qualitativa da recommendation.

### 4. Observabilidade de execução agentic — PRIORIDADE ALTA
Saber ler traces e entender chamadas de tools. LangSmith é **obrigatório** neste projeto (ADR-013): todo run do grafo, chamada de LLM e chamada de tool deve ser traçado, e o autor deve conseguir explicar um trace (onde o interrupt ocorreu, o loop de tool-calling do agente, tokens/latência).

### 5. Prompt/tool injection boundary — PRIORIDADE MÉDIA
Mesmo sem RAG, inputs do usuário podem tentar manipular o agent. A defesa principal neste projeto é limitar tools e efeitos, não criar um “super prompt de segurança”.

## Não é necessário aprender neste projeto

- RAG avançado;
- embeddings;
- GraphRAG;
- multi-agent orchestration;
- Kubernetes;
- filas/event streaming;
- fine-tuning.

Esses assuntos diluiriam o objetivo principal.

## Definition of Learned

Um conceito só é considerado aprendido quando o autor consegue responder:

1. O que é?
2. Que problema resolve aqui?
3. Onde está no código/graph?
4. Qual alternativa mais simples existia?
5. Qual trade-off aceitamos?
