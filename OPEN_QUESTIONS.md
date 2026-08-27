# Open Questions

Use estas perguntas como matéria-prima para `/speckit.clarify`. O agent deve priorizar apenas as que realmente mudam escopo, UX ou arquitetura. Não é necessário responder todas de uma vez.

## Produto

1. ✅ RESOLVIDO (2026-08-27, ADR-009): duas personas numa jornada — data engineer (propõe) + data owner/change approver (revisa).
2. A mudança analisada é apenas em schema/tabela ou também pode ser mudança de pipeline/regra de transformação?
3. O sistema produz somente recomendação ou também cria um registro formal da decisão? (tendência: registro formal — tabela `change_decision`, ADR-012; confirmar na spec)
4. O que caracteriza “evidência suficiente” para recomendar?
5. ✅ RESOLVIDO (2026-08-27, ADR-011): o reviewer pede revisão com nota em texto livre e o sistema regenera (loop), com limite de 2. Edição inline não entra no V0.

## Risco

6. ✅ RESOLVIDO (2026-08-27, ADR-010): `LOW/MEDIUM/HIGH + fatores`, categoria derivada de regras determinísticas.
7. Quais regras mínimas precisam ser determinísticas?
8. Um ativo desconhecido deve gerar HIGH, bloquear análise ou pedir informação?
9. Uma tool indisponível deve bloquear aprovação ou apenas reduzir confiança?

## LangGraph

10. Quais branches são genuinamente independentes e merecem parallelization?
11. Agent enrichment deve ocorrer por nível de risco ou por insuficiência de evidência?
12. Human-in-the-loop é obrigatório para todo risco ou apenas para alguns caminhos? (ADR-005 aceito; falta definir se todo risco pausa)
13. ✅ RESOLVIDO (2026-08-27, ADR-011): sim, o loop `revise → regenera → re-review` entra no V0, com limite de 2. Pendente: a nota realimenta só `recomendar` ou também `avaliar risco`/agente.
14. A demonstração precisa exibir nodes/estado em tempo real? (tendência: sim, UI mostra etapas + estado; confirmar)

## LangChain / Agent

15. O agent escolhe livremente entre tools read-only ou segue uma ordem parcial?
16. Structured output será usado apenas no parsing e recommendation ou também em outras decisões?
17. Qual comportamento deve ser mockado nos testes e qual deve ser testado com LLM real?

## MCP

18. MCP é requisito de V0, requisito de V1 ou apenas experimento opcional?
19. Se houver MCP, ele deve expor tools do domínio de dados, uma integração externa, ou ambos?
20. Qual aprendizado de MCP queremos demonstrar que uma tool Python local não demonstraria?

## Portfólio

21. Qual demo de 2–3 minutos melhor evidencia raciocínio arquitetural?
22. Quais 3 decisões técnicas devem aparecer claramente no README final?
23. Quais funcionalidades parecem “enterprise theater” e devem ser evitadas?
