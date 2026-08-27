# Discovery Notes

## Origem da ideia

Foram comparados cinco tipos de projetos corporativos: análise de incidentes, auditoria de processos, solicitações internas, análise de mudanças em dados e assistente de decisão. A hipótese de **análise de mudanças em dados** foi escolhida porque oferece uma combinação favorável de:

- domínio estruturado;
- poucos dados simulados;
- poucas regras determinísticas;
- routing natural;
- investigação com tools;
- human-in-the-loop justificável;
- boa visualização de LangGraph;
- MCP possível sem precisar de RAG.

## Workflow candidato — NÃO AUTORITATIVO

```text
change request
     ↓
interpret request
     ↓
collect evidence
 ┌──────┼──────┐
asset   deps   usage
 └──────┼──────┘
        ↓
   assess risk
        ↓
  need enrichment?
    ↙        ↘
  no        yes
  │          ↓
  │      investigator agent
  │          │
  └──────┬───┘
         ↓
 recommendation
         ↓
 human review
 approve / edit / reject
         ↓
 final record
```

## Tecnologias candidatas — NÃO DECIDIDAS

- Python;
- LangChain;
- LangGraph;
- PostgreSQL;
- Streamlit;
- Pydantic;
- MCP em fase posterior;
- provider LLM intercambiável.

A fase `plan` deve decidir versões, bibliotecas e estrutura de arquivos com base na especificação aprovada.

## Hipóteses que precisam ser desafiadas

1. Se o risco LOW deve pular o agent.
2. Se o agent deve existir por risco ou por **falta de evidência**.
3. Se coleta de evidência realmente precisa ser paralela ou se isso é apenas oportunidade didática.
4. Se três tipos de mudanças (`DROP_COLUMN`, `ALTER_COLUMN`, `ADD_INDEX`) são a melhor amostra.
5. Se score numérico 0–100 agrega valor ou se categorias/fatores são mais profissionais.
6. Se MCP deve entrar no V0 ou ficar em V1.
7. Se PostgreSQL é necessário no primeiro incremento ou um repositório em memória seria melhor para aprender o graph primeiro.
8. Se a interface deve mostrar o graph/progresso ou apenas o resultado.
9. O que exatamente torna o caso convincente para um entrevistador sem virar uma simulação exagerada.

## Regra de descoberta

Qualquer item acima pode ser removido. O objetivo do SDD não é confirmar esta arquitetura; é encontrar a menor arquitetura que cumpra o `PROJECT_BRIEF.md`.
