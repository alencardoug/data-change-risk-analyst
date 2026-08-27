# SDD Workflow

## Objetivo

Usar GitHub Spec Kit para que os artefatos gerados sejam a fonte de verdade da implementação.

Os arquivos na raiz deste starter são **seeds/contexto**, não substitutos dos artefatos oficiais do Spec Kit.

## Fluxo recomendado para este projeto

```text
constitution
    ↓
specify
    ↓
clarify
    ↓
requirements quality gate
    ↓
plan
    ↓
tasks
    ↓
analyze
    ↓
implement
    ↓
converge
```

`/speckit.checklist` pode ser usado quando quisermos um checklist específico adicional; o importante é não iniciar implementação com requisitos materialmente ambíguos.

## Gate 0 — Constitution

Entrada:
- `PROJECT_BRIEF.md`;
- `CONSTITUTION_SEED.md`.

Saída esperada:
- constituição curta e normativa.

Não decidir stack detalhada aqui.

## Gate 1 — Specify

Entrada:
- `PROJECT_BRIEF.md`;
- `DISCOVERY_NOTES.md` como contexto, não solução.

A especificação deve responder WHAT/WHY:
- persona;
- problema;
- histórias de usuário;
- cenários;
- requisitos;
- critérios de sucesso.

**Não colocar LangGraph nodes, banco, bibliotecas ou estrutura de arquivos na especificação funcional.**

## Gate 2 — Clarify

Usar `OPEN_QUESTIONS.md` como backlog de incertezas.

Regra:
- perguntar apenas o que muda escopo, UX, risco ou arquitetura;
- preferir poucas perguntas de alto impacto;
- atualizar a spec com cada resposta aceita.

## Gate 3 — Requirements quality

Antes de planejar, validar:
- requisitos testáveis;
- sem contradições;
- critérios de sucesso mensuráveis;
- sem decisões técnicas disfarçadas de requisito;
- cenários principais e de falha.

Ver `CHECKLIST_DISCOVERY.md`.

## Gate 4 — Plan

Agora sim decidir HOW:
- stack;
- modelo de estado;
- nodes;
- tools;
- boundaries determinístico/probabilístico;
- persistência;
- MCP sim/não e fase;
- interface;
- testes;
- estrutura do repositório.

As ideias de `ARCHITECTURE_HYPOTHESES.md` devem ser comparadas, não copiadas automaticamente.

## Gate 5 — Tasks

Gerar tarefas pequenas, ordenadas e verificáveis.

Cada uso importante de LangChain/LangGraph deve ter:
- tarefa de implementação;
- tarefa/critério de teste;
- objetivo de aprendizado relacionado.

## Gate 6 — Analyze

Executar análise cruzada entre constituição, spec, plan e tasks.

Bloquear implementação se houver:
- requisito sem task;
- task sem requisito/justificativa;
- conflito com constituição;
- componente arquitetural não necessário;
- decisão crítica ainda ambígua;
- requisito de segurança sem mecanismo correspondente.

## Gate 7 — Implement

Somente após análise aceitável.

Implementar incrementalmente. Ao final de cada incremento, registrar:
- conceito LangChain/LangGraph usado;
- motivo;
- teste;
- trade-off.

## Gate 8 — Converge

Após implementação, comparar estado atual do código com spec/plan/tasks e adicionar gaps restantes. Não considerar “funcionou na demo” como equivalente a “convergiu com a spec”.
