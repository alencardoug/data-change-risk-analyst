# Tasks — Discovery only

**Não há tasks de implementação neste starter.** Elas devem ser produzidas por `/speckit.tasks` depois de specification + clarify + plan.

## SDD setup

- [x] **D-01** Ler `PROJECT_BRIEF.md` e `CONSTITUTION_SEED.md`.
- [x] **D-02** Criar/atualizar constituição via `/speckit-constitution`. → v1.0.0 em `.specify/memory/constitution.md` (ADR-014).
- [x] **D-03** Criar feature specification via `/speckit-specify`. → `specs/001-data-change-risk-review/spec.md`.

## Clarification

- [x] **D-04** Executar `/speckit-clarify`. → 4 perguntas, ADR-016; seção `## Clarifications` na spec.
- [x] **D-05** Revisar `OPEN_QUESTIONS.md`. → Q1,Q4,Q5,Q6,Q8–Q20 marcadas resolvidas.
- [x] **D-06** Validar spec com `CHECKLIST_DISCOVERY.md` / checklist de requisitos. → `checklists/requirements.md` 16/16.

## Planning

- [x] **D-07** Executar `/speckit-plan`; comparar `ARCHITECTURE_HYPOTHESES.md`. → Hipótese A escolhida; `plan.md` + `research.md` + `data-model.md` + `contracts/` + `quickstart.md`.
- [x] **D-08** Registrar decisões aprovadas em `DECISIONS.md`. → ADR-006/007 accepted, ADR-017.
- [x] **D-09** Verificar se o plan preserva `LEARNING_OBJECTIVES.md` e `PORTFOLIO_CRITERIA.md`. → Constitution Check §VI + tabela de conceitos no plan.

## Tasks/analyze

- [x] **D-10** Executar `/speckit-tasks`. → `specs/001-data-change-risk-review/tasks.md` (64 tarefas, 6 fases).
- [x] **D-11** Mapear cada task a requisito e objetivo de aprendizado. → refs FR + "Learning objectives covered" por fase (revisão formal no D-12).
- [x] **D-12** Executar `/speckit-analyze`. → 0 CRITICAL / 0 HIGH; 3 MEDIUM + 5 LOW. Relatório na conversa.
- [x] **D-13** Corrigir inconsistências/gaps antes de implementação. → G1 (T065), G2 (T066), A1 (T030 + research §5) aplicados. C1/A2/I1/U1/G3 aceitos como não-bloqueantes.

## Gate de implementação

- [x] **D-14** Confirmar que não existe implementação antecipada servindo de requisito implícito. → scaffold estava vazio; código nasceu do `tasks.md`.
- [x] **D-15** Executar `/speckit-implement`. → **V0 completo**: 65/66 tarefas (Fases 1–6). 50 testes determinísticos verdes (fake model + `MemorySaver`, sem API key/DB) + 2 DB-gated + `llm_integration` opt-in; ruff limpo. Única tarefa aberta: **T061** = rodar S1–S8 contra modelo real uma vez (precisa da chave Anthropic + Postgres do usuário).
- [x] **D-16** Executar `/speckit-converge`. → `tasks_appended`: **Phase 7: Convergence** (T067–T071), depois **implementada e verde** com Postgres real via Docker: resume restart-safe com `PostgresSaver` (T067), round-trip do `PostgresRepository` (T068), caminho "reopen" (T069), agente investigador movido para `src/dcra/agent/investigator.py` (T070), asserção das descrições dos fatores (T071). **56 testes passando com DB, 53 sem DB.** Nenhuma violação de constituição.

## Estado final

Todas as tarefas de `specs/001-data-change-risk-review/tasks.md` concluídas **exceto T061** (rodar S1–S8 contra modelo Anthropic real uma vez — precisa da `ANTHROPIC_API_KEY` do usuário; os 8 cenários já rodam automatizados com fake model). Postgres de dev fica de pé via `docker compose up -d` (parar com `docker compose down`).
