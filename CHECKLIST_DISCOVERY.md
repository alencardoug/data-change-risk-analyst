# Discovery / Specification Quality Checklist

Não iniciar `/speckit.implement` enquanto os itens críticos estiverem abertos.

## Produto

- [ ] Persona primária definida.
- [ ] Problema e valor explicáveis em menos de 60 segundos.
- [ ] Escopo V0 cabe em uma demo curta.
- [ ] Pelo menos dois cenários exigem caminhos diferentes.
- [ ] Fora do escopo explícito.

## Requisitos

- [ ] Requisitos descrevem WHAT/WHY, não HOW.
- [ ] Requisitos funcionais são testáveis.
- [ ] Critérios de sucesso são observáveis/mensuráveis.
- [ ] Falta de evidência/tool failure tem comportamento especificado.
- [ ] Decisão humana é distinguível da recommendation da IA.
- [ ] Nenhuma ambiguidade de alto impacto permanece sem decisão.

## LangChain/LangGraph

- [ ] Cada uso de LangChain tem propósito claro.
- [ ] Cada uso de LangGraph tem propósito claro.
- [ ] Existe uma explicação defensável para workflow vs agent.
- [ ] O agent não possui efeito destrutivo.
- [ ] Routing crítico não depende desnecessariamente de LLM.
- [ ] Parallelization só existe se as subtarefas forem realmente independentes.
- [ ] Human-in-the-loop altera de fato o estado/fluxo.

## Portfólio

- [ ] Arquitetura é proporcional, sem “enterprise theater”.
- [ ] Há pelo menos 3 decisões técnicas interessantes para explicar em entrevista.
- [ ] A UI/demonstração mostra o workflow, não apenas texto final.
- [ ] Projeto pode ser executado localmente com instruções simples.

## Aprendizado

- [ ] Cada conceito principal tem um objetivo de aprendizado.
- [ ] Há uma alternativa mais simples registrada para cada escolha relevante.
- [ ] Testes distinguem lógica determinística de chamadas LLM.
- [ ] MCP tem um objetivo explícito ou é removido do V0.
