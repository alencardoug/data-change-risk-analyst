# 06 · Um caso, várias execuções: pausa não é latência do modelo

[Índice](README.md) · [Anterior](05-dissecar-dcra.md) · [Próximo](07-falhas-latencia-retries.md)

**Objetivo:** correlacionar execução inicial e retomadas sem confundir armazenamento de estado e telemetria. Tempo: 25–30 minutos.

Imagine que você deixa uma mala num guarda-volumes. O recibo permite recuperar a mala; uma câmera permite ver quem passou pelo balcão. Um vídeo não substitui o recibo nem armazena sua mala. No DCRA, checkpoint é o estado guardado; trace é a observação da execução.

## Experimento 1 — aprovar

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --review approve --send
```

Abra as duas URLs impressas. Procure as raízes `dcra-iniciar` e `dcra-retomar-approve`. Os `run_id` diferem, mas o `thread_id` é o mesmo. O primeiro resultado pausa; o segundo termina com `APPROVED`.

Este script simula a resposta de um revisor com dados declaradamente sintéticos. Na aplicação, a resposta vem da interação humana na UI. Não apresente a ação automatizada do laboratório como anotação humana independente.

Abra [build.py](../src/dcra/graph/build.py) e localize:

```python
config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
return compiled.invoke(Command(resume=value), config=config)
```

O checkpointer usa esse identificador para recuperar estado. A documentação atual do LangSmith orienta agrupar traces por metadados `thread_id` ou `session_id`; para agregações completas, confira a propagação aos filhos. O lab acrescenta `metadata.thread_id` explicitamente ao contexto e à configuração. [Threads no LangSmith](https://docs.langchain.com/langsmith/threads).

| Identificador | O que identifica |
|---|---|
| `ChangeRequest.id` | caso de negócio |
| `configurable.thread_id` | sequência de checkpoints do caso no LangGraph |
| `metadata.thread_id` | correlação de traces na observabilidade |
| `run_id` | uma operação instrumentada |
| `trace_id` | a árvore à qual o run pertence |

Os três primeiros usam o mesmo valor neste projeto/lab, por convenção. Essa escolha precisa ser implementada; não é uma lei de todas as aplicações.

## Experimento 2 — devolver apenas com nota

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --review return --send
```

Espere três raízes: inicial, devolução, aprovação. Na devolução, a recomendação passa de v1 para v2; o histórico de avaliação de risco continua com uma passagem. Confira no JSON gerado `recommendation_versions` e `risk_passes`, depois encontre o caminho no trace.

## Experimento 3 — devolver pedindo evidência

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --review return-evidence --send
```

Agora aparecem `reassess_gate`, os coletores outra vez, nova avaliação e `investigate`. Com o investigador fixture, ele acrescenta zero itens; o risco permanece MEDIUM. O histórico tem três avaliações: inicial, reavaliação após coleta e reavaliação dentro de `investigate`.

**Acionar investigação não garante sucesso da investigação.** Meça se houve evidência nova válida e se ela alterou a conclusão. Uma métrica “investigador executou” é atividade, não benefício.

## O relógio tem dois trabalhos

Se a análise leva 4 segundos, a pessoa demora 20 minutos e a retomada leva 0,2 segundo:

- latência técnica ativa aproximada: 4,2 segundos;
- espera humana: 20 minutos;
- tempo do processo de negócio: cerca de 20 minutos e 4,2 segundos.

Não some um período em que nenhum modelo estava executando ao “tempo de inferência”. Registre timestamps de domínio quando o objetivo for SLA do processo completo.

Na retomada, o nó que contém `interrupt()` é reexecutado desde o início; passos anteriores à chamada podem acontecer novamente. Efeitos externos nessa região exigem desenho idempotente. [Semântica de interrupt/resume](https://docs.langchain.com/oss/python/langgraph/interrupts).

**Limite deste lab:** memória não sobrevive ao fim do processo. Ele demonstra continuidade entre invocações usando o mesmo checkpointer vivo. A durabilidade em reinício usa Postgres no produto. A questão conhecida da lista de casos publicados e o caminho por ID estão em [KNOWN_ISSUES.md](../KNOWN_ISSUES.md).

**Conceito LangGraph:** execução persistente com intervenção externa. **Alternativa simples:** devolver recomendação e manter uma fila de revisão fora do grafo. **Defesa:** checkpoints modelam a continuidade; LangSmith ajuda a inspecioná-la, sem ser o armazenamento que retoma o workflow.

**Memorize:** *thread*, *checkpoint*, *resume*, *idempotency*, *business latency*.
