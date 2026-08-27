# Open Questions

Use estas perguntas como matéria-prima para `/speckit.clarify`. O agent deve priorizar apenas as que realmente mudam escopo, UX ou arquitetura. Não é necessário responder todas de uma vez.

## Produto

1. ✅ RESOLVIDO (2026-08-27, ADR-009): duas personas numa jornada — data engineer (propõe) + data owner/change approver (revisa).
2. A mudança analisada é apenas em schema/tabela ou também pode ser mudança de pipeline/regra de transformação?
3. O sistema produz somente recomendação ou também cria um registro formal da decisão? (tendência: registro formal — tabela `change_decision`, ADR-012; confirmar na spec)
4. ✅ RESOLVIDO (2026-08-27, ADR-016 / FR-009+FR-010): recomendação é sempre produzida; "evidência insuficiente" (lacuna material) dispara a investigação adicional, não bloqueia a recomendação.
5. ✅ RESOLVIDO (2026-08-27, ADR-011): o reviewer pede revisão com nota em texto livre e o sistema regenera (loop), com limite de 2. Edição inline não entra no V0.

## Risco

6. ✅ RESOLVIDO (2026-08-27, ADR-010): `LOW/MEDIUM/HIGH + fatores`, categoria derivada de regras determinísticas.
7. Quais regras mínimas precisam ser determinísticas?
8. ✅ RESOLVIDO (2026-08-27, ADR-015 / FR-020): ativo desconhecido → HIGH com fator explícito "asset not found", segue para revisão. Não inventa dados.
9. ✅ RESOLVIDO (2026-08-27, ADR-016 / FR-024): não bloqueia; segue para revisão com lacuna sinalizada e confiança reduzida.

## LangGraph

10. ✅ RESOLVIDO (2026-08-27, ADR-017): `collect_asset` / `collect_deps` / `collect_usage` — 3 leituras independentes, fan-out/fan-in com reducer `merge_evidence`.
11. ✅ RESOLVIDO (2026-08-27, ADR-016 / FR-010): por lacuna de evidência material; nunca por nível de risco.
12. ✅ RESOLVIDO (2026-08-27, ADR-015 / FR-019): pausa humana só para MEDIUM/HIGH; LOW auto-finaliza.
13. ✅ RESOLVIDO (2026-08-27, ADR-011): sim, o loop `revise → regenera → re-review` entra no V0, com limite de 2. Pendente: a nota realimenta só `recomendar` ou também `avaliar risco`/agente.
14. ✅ RESOLVIDO (2026-08-27, ADR-017): sim — Streamlit com step view (etapas + evidências + risco + recomendação + gate) e README com diagrama/GIF.

## LangChain / Agent

15. ✅ RESOLVIDO (2026-08-27, ADR-017): `create_react_agent` escolhe livremente entre as 3 tools read-only, mas com lista de tools restrita + `recursion_limit` + prompt que o limita a preencher a lacuna.
16. ✅ RESOLVIDO (2026-08-27, ADR-017 / contracts/llm-schemas.md): structured output só em interpretação (`StructuredChange`) e recomendação (`Recommendation`); risco e roteamento nunca via LLM.
17. ✅ RESOLVIDO (2026-08-27, ADR-017): unit + e2e usam fake model (determinístico); llm_integration (poucos casos, opt-in `RUN_LLM_TESTS=1`) usa modelo real para schema de parsing/recomendação e tool-calling do agente.

## MCP

18. ✅ RESOLVIDO (2026-08-27, ADR-007 / ADR-017): V1. Fora do V0.
19. V1: expor UMA tool de evidência do domínio via servidor MCP local (não integração externa).
20. V1: demonstrar cliente/servidor/transporte MCP e o modo de falha "servidor MCP indisponível" — o que uma função Python local não exercita.

## Portfólio

21. ✅ RESOLVIDO (2026-08-27, README "The 2–3 minute demo"): o caso MEDIUM `drop column orders.customer_legacy_id` end-to-end — interpretação → fan-out paralelo → risco determinístico + fatores → recomendação IA → gate `interrupt()` → Approve → registro. Mais os contrastes LOW (auto-finaliza) e ativo ausente (HIGH).
22. ✅ RESOLVIDO (README "Three decisions worth defending"): (1) LangGraph vs chain — pausa/loop/branches em estado determinístico; (2) risco em código puro, nunca no LLM; (3) HITL via `interrupt()` + checkpoint, decisão humana como campo distinto da recomendação.
23. ✅ RESOLVIDO (README "What was deliberately not built"): fora — auth/RBAC, lifecycle completo de change-management, microserviços/filas, RAG/vector DB, multi-agent, tool de SQL genérico, dezenas de tabelas, métricas inventadas. Agente read-only + recursion-capped; sem DDL.
