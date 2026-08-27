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
- [ ] **D-12** Executar `/speckit-analyze`.
- [ ] **D-13** Corrigir inconsistências/gaps antes de implementação.

## Gate de implementação

- [ ] **D-14** Confirmar que não existe implementação antecipada servindo de requisito implícito.
- [ ] **D-15** Somente então executar `/speckit.implement`.
- [ ] **D-16** Após implementação, executar `/speckit.converge`.
