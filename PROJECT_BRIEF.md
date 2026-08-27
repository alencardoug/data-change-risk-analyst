# Project Brief

## Intenção

Construir um projeto pequeno de AI Engineering com aparência e raciocínio corporativos, apropriado para portfólio profissional e para demonstrar domínio prático de LangChain e LangGraph.

## Critério de sucesso profissional

Ao abrir o repositório ou assistir a uma demonstração curta, um recrutador técnico ou gestor deve conseguir perceber que o autor sabe:

- transformar um problema empresarial em workflow;
- separar decisões determinísticas de decisões probabilísticas;
- controlar autonomia de agentes;
- modelar estado, transições e aprovação humana;
- integrar LLMs a dados e tools com contratos explícitos;
- testar comportamento crítico;
- limitar escopo e justificar trade-offs.

O projeto **não precisa** provar escala, alta disponibilidade, compliance real, segurança enterprise ou integração com sistemas de produção.

## Critério de sucesso educacional

Ao terminar, o autor deve conseguir explicar sem decorar código:

- quando usar LangChain;
- quando usar LangGraph;
- diferença entre workflow e agent;
- por que determinado passo é node e outro é tool;
- quando routing deve ser determinístico ou dirigido por modelo;
- como state atravessa o graph;
- por que reducers podem ser necessários em branches paralelos;
- como checkpointing e `thread_id` se relacionam com pausa/retomada;
- como human-in-the-loop funciona conceitualmente;
- o que MCP acrescenta e o que ele não substitui.

## Restrições

- Preferir um V0 que caiba aproximadamente em alguns dias de trabalho focado.
- Evitar datasets grandes e muitas regras simuladas.
- Evitar RAG, embeddings e VectorDB neste projeto.
- Evitar multi-agent sem necessidade demonstrável.
- Evitar frontend separado se Streamlit ou equivalente simples for suficiente.
- Evitar microserviços, Kubernetes, Kafka e infraestrutura irrelevante ao aprendizado.
- Preferir dados estruturados pequenos e totalmente simuláveis.

## Hipótese de domínio

**Data Change Risk Analyst**.

Uma pessoa propõe uma alteração em um ativo de dados. O sistema busca fatos sobre o ativo e seu uso, avalia risco, complementa a investigação quando necessário, gera recomendação e pausa para decisão humana.

Essa hipótese será testada contra alternativas e pode ser reduzida ou ajustada.

## Não objetivo

O objetivo não é construir um sistema real de Change Data Management nem uma plataforma universal de governança de dados. O domínio é um veículo para demonstrar arquitetura agentic controlada.
