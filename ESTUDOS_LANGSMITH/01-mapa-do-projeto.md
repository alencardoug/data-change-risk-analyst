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

**Acrescentado como estudo:** tracing manual de Python, dataset de avaliação, comparação baseline/candidata, rubrica de juiz e um juiz simulado que erra, a mesma avaliação como suíte pytest, exemplos de custo com estimativa de retenção, exportação de runs por SDK com manifesto, leitura do uso real a partir do banco do app, versionamento de prompts, RAG didático e uma demonstração opcional de Langfuse.

**Ainda não implantado no produto:** programa contínuo de eval online, dashboards/SLOs de qualidade, gates de release orientados por evals, implantação de Langfuse e coleta distribuída com OpenTelemetry. Os capítulos ensinam a projetar ou experimentar essas capacidades; não atribuem esse histórico à aplicação publicada. O [plano de desenvolvimento](PLANO_DE_DESENVOLVIMENTO.md) registra por que essas cinco continuam adiadas e o que as destravaria.

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

## Levar para outros projetos — e onde o seu julgamento decide

O exercício deste capítulo — separar **o que está no produto, o que foi feito como estudo e o que ainda é proposta** — é o primeiro que vale a pena repetir em qualquer projeto, antes de instrumentar qualquer coisa.

**Na plataforma de atendimento (Langfuse Cloud).** O inventário honesto já existe em `LANGFUSE/README.md` e `revisao_claude_code.md`: instrumentação N5 nos três pontos em andamento na branch `refino-rag`; contratos de avaliação e de prompts **escritos, não implementados**; RAGFlow/Elasticsearch instalados na máquina, **segurados** até a Fase 0. Faça a tabela de responsabilidades equivalente à deste capítulo: interpretar → `ai/providers.py` (`generate`, `generate_ungoverned`, `rerank_clinical`, `extract_date_intent`); recuperar → `rag/service.py::retrieve()`; decidir caminho → `ai/router.py::maybe_open_autonomous_window()`; enviar → `autonomy/service.py::resolve_elapsed_autonomous_sends()`; registrar → `customer_service.ai_generations` e o catálogo de eventos de auditoria. Os "quatro cuidados de leitura" também têm equivalentes: `status = ANSWER` prova que houve resposta, não que ela resolveu; `_AUTONOMOUS_CLINICAL_MIN_SCORE = 0.40` é um gate específico, não nota universal; uma `AIGeneration` pode ser determinística e nunca ter chamado modelo; e a mensagem é criada numa requisição **posterior** à geração — o trace de um turno não termina onde a chamada ao modelo termina.

**Em projetos comuns do ecossistema.** Todo projeto com LangChain/LangGraph tem esse mapa implícito: onde o modelo entra, onde a política é código, onde o estado é guardado, onde a decisão humana acontece. Escreva-o antes de olhar um trace. Sem ele, cada span parece igualmente importante, e o diagnóstico vira leitura aleatória. Em um agente com ferramentas, acrescente uma linha "onde está o limite de passos e o que acontece quando ele estoura"; em um RAG, "onde a query é montada e onde o contexto é cortado".

**O fator humano — onde a IA faz e onde você decide.** Um assistente lê o código e produz a tabela de responsabilidades em segundos — e é provável que a produza bem. O que ele faz pior, e onde você é o diferencial, é o **inventário honesto**: dizer o que *não* foi feito, o que foi feito com fixtures e o que só existe em documento. A IA tende a descrever a arquitetura como se tudo já funcionasse, porque os documentos de plano e o código parecem iguais para ela. Foque em duas frases que só você pode assinar: "isto está implantado e eu executei", e "isto é proposta e ninguém executou". Na plataforma, o `plano_curso_pratico.md` "substituído" e o Compose `langfuse` que virou apêndice são exemplos disso: um leitor automático os apresentaria como capacidades; você sabe que são história. Seu julgamento aqui é o que separa uma entrevista (ou uma decisão de projeto) defensável de uma que desmonta na primeira pergunta "mostra?".
