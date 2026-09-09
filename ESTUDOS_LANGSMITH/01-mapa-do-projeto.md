# 01 · O que você realmente construiu

[Índice](README.md) · [Anterior](00-roteiro-3-dias.md) · [Próximo](02-fundamentos-observabilidade.md)

**Objetivo:** conseguir distinguir experiência implementada, experiência feita neste curso e proposta futura. Tempo: 20 minutos. Sem rede ou modelo.

O DCRA interpreta um pedido de mudança de schema, coleta evidências, aplica regras de risco e redige uma recomendação. Casos LOW finalizam automaticamente; MEDIUM/HIGH passam por revisão humana. A aplicação não executa o DDL da mudança proposta.

Pense em um aeroporto. O LLM traduz a solicitação do passageiro e ajuda a explicar a situação. As regras de segurança definem a classificação. LangGraph organiza as etapas e a espera por autorização. LangSmith permite examinar a viagem de uma execução pelo sistema.

| Responsabilidade | Onde abrir | O que procurar |
|---|---|---|
| Interpretar linguagem | [factory.py](../src/dcra/llm/factory.py) | `interpret`, `with_structured_output`, `_INTERPRET_SYS` |
| Contratos de entrada/saída | [models.py](../src/dcra/domain/models.py) | `StructuredChange`, `Recommendation`, validadores |
| Orquestrar | [build.py](../src/dcra/graph/build.py) | `build_graph`, arestas, `run`, `resume` |
| Aplicar política | [risk.py](../src/dcra/rules/risk.py) | `assess`, `has_evidence_gap` |
| Pausar/revisar | [nodes.py](../src/dcra/graph/nodes.py) | `human_review`, `interrupt`, roteadores |
| Investigar lacuna | [investigator.py](../src/dcra/agent/investigator.py) | `create_agent`, ferramentas permitidas, limite 8 |
| Recuperar estado | [checkpointer.py](../src/dcra/persistence/checkpointer.py) | `PostgresSaver` |
| Registrar decisão | [repository.py](../src/dcra/persistence/repository.py) | persistência de `AnalysisRecord` |
| Ligar tracing | [.env.example](../.env.example) | `LANGSMITH_TRACING`, chave e projeto |

Para chegar ao trecho sem depender de números de linha:

```bash
rg -n 'def interpret|with_structured_output|def assess|def human_review|interrupt\(' src/dcra
rg -n 'create_agent|RECURSION_LIMIT' src/dcra/agent/investigator.py
```

## O inventário honesto

**No produto:** integração automática de LangChain/LangGraph com LangSmith, configuração por ambiente, testes determinísticos com dependências falsas, testes opcionais com modelo real, checkpoints e registro de negócio. A documentação anterior de [observabilidade](../docs/observability.md) é o ponto de partida.

**Acrescentado como estudo:** tracing manual de Python, dataset de avaliação, comparação baseline/candidata, rubrica de juiz, exemplos de custo, versionamento de prompts, RAG didático e uma demonstração opcional de Langfuse.

**Ainda não implantado no produto:** programa contínuo de eval online, dashboards/SLOs de qualidade, gates de release orientados por evals, implantação de Langfuse e coleta distribuída com OpenTelemetry. Os capítulos ensinam a projetar ou experimentar essas capacidades; não atribuem esse histórico à aplicação publicada.

## Quatro correções úteis à leitura dos documentos antigos

1. O investigador atual chama `langchain.agents.create_agent`. A menção antiga a `create_react_agent` descreve uma fase anterior. Conceito de loop com ferramentas permanece; o símbolo atual deve vir do código.
2. [tests/conftest.py](../tests/conftest.py) contém uma fixture automática que define `LANGSMITH_TRACING=false`. Rodar os testes de integração com chave de LangSmith, por si só, não garante traces.
3. `recursion_limit=8` limita passos do runtime do agente. Não promete oito chamadas HTTP, oito ferramentas ou uma conta de oito centavos.
4. `step_log` e trace têm granularidades diferentes. O primeiro descreve etapas de domínio; o segundo pode mostrar chamadas internas, erros e tempos que o log de negócio não registra.

Há outras boas oportunidades de raciocínio: o código de risco usa `reads_per_day > 0` para `ACTIVELY_READ`; não calcule uma janela temporal a partir do nome `_RECENT_DAYS`, que está declarado mas não participa dessa regra. A palavra “determinístico” precisa corresponder a predicados executados, não a comentários.

## Exercício: siga uma decisão até sua origem

Abra `risk.py` e encontre `IN_PRIMARY_KEY`. Depois abra `route_after_recommend` em `nodes.py`. Responda: o texto da recomendação escolhe a revisão humana? **Não: o roteador olha a categoria de risco.** A categoria vem da política em Python sobre evidências.

**Conceito LangChain/LangGraph:** separar integração com o modelo de orquestração e política. **Utilidade:** testar regras sem pagar por geração e observar a fronteira entre código e modelo. **Alternativa simples:** funções Python e uma tabela de estados. **Defesa:** o grafo se justifica pela pausa persistente, ramificações e revisão limitada; usar framework não é requisito para ter tracing.

**Memorize:** *separation of concerns*, *structured output*, *deterministic policy*. Explique em suas palavras por que uma resposta bem escrita ainda pode corresponder a uma análise ruim.
