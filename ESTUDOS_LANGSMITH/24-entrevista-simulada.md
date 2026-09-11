# 24 · Explicar o que você consegue demonstrar

[Índice](README.md) · [Anterior](23-ci-gates.md) · [Próximo](25-desafios-gabarito.md)

**Objetivo:** apresentar uma decisão de engenharia apoiada em evidência. Tempo: 30–35 minutos. Grave uma demo de três minutos e seis respostas de até um minuto. Use o [caderno](28-caderno-de-evidencias.md) para registrar onde sua explicação ainda depende de consulta.

As respostas abaixo são modelos para adaptar ao que você executou. Se fez apenas o modo local, diga isso. Uma URL de trace só entra na apresentação depois que você a obtiver na própria conta.

## Demo de três minutos

Prepare os resultados antes de iniciar o cronômetro:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --review approve
.venv/bin/python ESTUDOS_LANGSMITH/labs/06_evaluate.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/12_regression_gate.py --candidate bug
```

O último comando deve terminar com exit code 1. Para apresentar também a UI do LangSmith, execute previamente o lab 02 com `--send`, conforme o capítulo [06](06-threads-checkpoints-revisao.md), e guarde as URLs impressas.

| Tempo | Mostre | Explique |
|---|---|---|
| 0:00–0:30 | Pedido de remoção de `orders.customer_legacy_id` | Uma mudança de schema pode afetar consumidores; o sistema reúne evidências e recomenda uma ação |
| 0:30–1:15 | Fatores de risco e `step_log`; ou os nós no trace, se enviado | O LLM do produto interpreta/redige; a categoria e o roteamento vêm de regras. Neste lab, essas chamadas de modelo são fixtures |
| 1:15–1:50 | As duas fases em `artefatos/02-medium-approve.json` | MEDIUM pausa; a aprovação sintética retoma o mesmo caso. `thread_id` permanece, `run_id` muda |
| 1:50–2:30 | Relatórios `06-baseline.json` e `06-bug.json` | A baseline acerta 16/16 categorias; a mutação acerta 13/16, mas perde todos os três HIGH |
| 2:30–3:00 | Saída do gate | A candidata viola o critério de risco/revisão. O benchmark apoia rejeitar essa mudança; não prova qualidade universal do modelo |

Um começo possível: “Construí um fluxo pequeno para analisar risco de mudanças em dados. Separei interpretação e recomendação por modelo da política determinística de risco. Vou mostrar a pausa de revisão e uma regressão que meu laboratório detecta.”

## Seis perguntas essenciais

### 1. Como LangChain, LangGraph e LangSmith entram no projeto?

“LangChain fornece a interface de modelo, saída estruturada e ferramentas. LangGraph coordena estado, ramificações, leituras paralelas e revisão com pausa/retomada. LangSmith registra a execução e oferece recursos para avaliá-la. No curso, consigo executar o grafo e avaliadores com dependências falsas.”

**Aponte:** [mapa do projeto](01-mapa-do-projeto.md). **Trade-off:** chamadas Python e `if/else` seriam suficientes para um fluxo linear; a continuidade da revisão e os caminhos com estado justificam LangGraph aqui. O primeiro lab mostra instrumentação de Python sem usar LangChain.

### 2. O que um trace prova sobre a qualidade da resposta?

“Ele mostra as operações registradas, suas entradas, saídas e relações. Uso isso para localizar onde um resultado surgiu. Para dizer se está correto, preciso de critérios: referência do dataset, avaliador de código ou rubrica humana. Uma execução sem exception pode produzir uma recomendação ruim.”

**Aponte:** `fallback` em [07](07-falhas-latencia-retries.md) e as métricas em [12](12-evals-deterministicos.md). Compare a disponibilidade da fonte com o status da raiz antes de concluir que houve sucesso.

### 3. Quem mantém a análise viva durante a revisão humana?

“O checkpointer do LangGraph armazena o estado, identificado por `thread_id`. No produto ele usa Postgres; no lab usa memória. LangSmith permite correlacionar as invocações registradas, mas o grafo retoma pelo checkpoint. O lab demonstra retomada no mesmo processo; não demonstra persistência após encerrar esse processo.”

**Aponte:** [06](06-threads-checkpoints-revisao.md) e `phases` do JSON. A duração de uma invocação e o tempo de espera do revisor são medidas diferentes. A revisão automatizada do lab deve ser apresentada como simulação.

### 4. Como você detectaria regressão ao mudar o sistema?

“Fixaria casos, referências e critérios antes de comparar versões. Neste exercício, o adaptador candidato troca HIGH por LOW e remove a pausa. O acerto de categoria cai para 81,25%, mas o dado decisivo é recall HIGH zero. O gate local reprova essa candidata.”

**Aponte:** [23](23-ci-gates.md). Os 16 casos verificam contratos do grafo com fixtures. Para avaliar o modelo de interpretação, o [lab 07](14-modelo-real-saida-estruturada.md) tem outro dataset e precisa executar chamadas reais.

### 5. Como mede custo e evita estourar o orçamento?

“Começo pelas chamadas que efetivamente consomem recursos. Evito somar uma raiz já agregada com seus filhos, e considero cache como parte da entrada. Também conto juízes, repetições e retries. Para limitar gasto, preciso de admissão antes da chamada e reconciliação depois; um dashboard sozinho só mede.”

**Aponte:** [09](09-tokens-custos-orcamentos.md): US$0,0033 por chamada com preços fictícios; três reservas aceitas e a quarta recusada. O limitador é didático e local. Não o apresente como orçamento implementado no produto.

### 6. Por que confiar em um juiz LLM?

“Não confiaria sem verificar. Definiria uma rubrica, compararia com anotações independentes e examinaria discordâncias. Separaria fundamentação de qualidade de escrita e mediria falhas do próprio juiz. Se a API falha, a nota fica ausente; isso não equivale a aprovação nem reprovação.”

**Aponte:** [15](15-juiz-llm-calibracao.md), `dados/juiz.json` e o juiz simulado de `08_judge.py --fixture-biased`: 4/6 de concordância que esconde dois falsos positivos em `grounded`, um deles por injeção. Sem executar `--real`, você examinou a rubrica e viu o formato de uma discordância, mas ainda não mediu concordância de um modelo. Igualdade de categoria e contrato de revisão já têm avaliadores de código.

## Perguntas para aprofundar

| Pergunta | Elementos de uma boa resposta | Onde praticar |
|---|---|---|
| “O p95 piorou; por onde começa?” | Janela e população comparáveis; caminho crítico; retries; chamada de modelo versus ferramenta; distinguir espera humana | [07](07-falhas-latencia-retries.md), [22](22-operacao-slos-incidentes.md) |
| “Como fecha o ciclo em produção?” | Detectar falha, revisar referência, criar caso de regressão, comparar versões, observar depois; medir também cobertura do avaliador | [18](18-evals-online-producao.md) |
| “Como reproduz um experimento?” | Código, alterações locais, prompt exato, modelo, evidências, dataset, avaliadores e configuração; hash identifica conteúdo, mas não o armazena | [17](17-reprodutibilidade-prompts.md) |
| “Como protege dados nos traces?” | Examinar o payload exportado, inclusive wrappers; redigir campos; definir amostragem consciente e registrar suas limitações | [19](19-privacidade-amostragem.md) |
| “Migraria para Langfuse/OTel?” | Comparar necessidades e o mesmo caso nas ferramentas; distinguir instrumentação, transporte e backend; declarar o que realmente experimentou | [21](21-langfuse-otel.md) |
| “É um sistema multiagente ou RAG?” | DCRA tem workflow e investigador limitado; não usa RAG nem orquestração multiagente. O RAG do lab 11 é um exercício separado | [16](16-avaliar-workflow-agentes.md), [20](20-rag-fora-do-projeto.md) |

## Critério para sua gravação

Para cada resposta, marque um ponto por: **conceito correto**, **evidência concreta**, **trade-off** e **limite da conclusão**. É uma rubrica de treino, sem promessa de prever o resultado da entrevista.

Se ficou só em nomes de ferramentas, regrave usando um caso. Se disse “validei em produção” mostrando fixtures, corrija a afirmação. Se apresentou um número, diga população, modo de execução e critério. A melhor resposta curta permite ao entrevistador perguntar “mostra?” e você saber o que abrir.
