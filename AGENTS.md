# AGENTS.md

## Fase atual

**PROJETO CONCLUÍDO E CONGELADO.** Construído, testado e publicado
(https://analisador-de-risco.web.app). Ver `README.md` → "Status",
`CLAUDE.md` e `KNOWN_ISSUES.md`.

O restante deste arquivo é o **registro histórico** da fase de
discovery/specification (SDD) que originou o produto — mantido para
rastreabilidade, não como instrução ativa. Na época, o repositório foi
propositalmente esvaziado de implementação para reduzir anchoring e permitir
SDD investigativo.

## Missão

Ajudar a definir a menor versão profissional do Data Change Risk Analyst que:

1. seja convincente como portfólio de AI Engineering;
2. ensine LangChain e LangGraph por usos reais;
3. permaneça pequena;
4. não introduza complexidade sem justificativa.

## Ordem de leitura

1. `PROJECT_BRIEF.md`
2. `CONSTITUTION_SEED.md`
3. `DISCOVERY_NOTES.md`
4. `OPEN_QUESTIONS.md`
5. `LEARNING_OBJECTIVES.md`
6. `PORTFOLIO_CRITERIA.md`
7. `SDD_WORKFLOW.md`
8. `REQUIREMENTS_SEED.md`
9. `ARCHITECTURE_HYPOTHESES.md`
10. `DECISIONS.md`

## Regras de investigação

- Tratar arquitetura existente como hipótese.
- Desafiar requisitos que parecem existir apenas para mostrar framework.
- Fazer perguntas quando uma resposta muda substancialmente escopo, UX, risco ou arquitetura.
- Preferir poucas perguntas de alto impacto a questionários extensos.
- Não fazer o usuário decidir detalhes que têm um default técnico seguro e reversível.
- Quando houver duas opções plausíveis, explicar trade-off e recomendar uma.
- Procurar a menor solução que cumpra objetivos de portfólio + aprendizado.
- Não criar código do produto até o gate de implementação em `TASKS.md`.

## Regra de aprendizado

Quando uma decisão envolver LangChain/LangGraph, explicar de forma curta:

- qual conceito está em jogo;
- por que pode ser útil aqui;
- alternativa mais simples;
- o que o usuário precisa saber para defender a decisão em entrevista.

## Hierarquia de autoridade

1. Constituição gerada pelo Spec Kit.
2. Feature spec gerada e clarificada.
3. Plan/ADRs aprovados.
4. Tasks geradas e analisadas.
5. Código.
6. Arquivos seed deste starter.

Se um seed conflitar com uma decisão posterior aprovada, o seed perde.
