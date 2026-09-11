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

## Levar para outros projetos — e onde o seu julgamento decide

A lição central — **checkpoint é o estado guardado; trace é a observação; a espera humana não é latência do modelo** — é a que mais se perde quando um projeto troca de ferramenta ou de framework.

**Na plataforma de atendimento (Langfuse Cloud).** Ali não há LangGraph nem `interrupt()`, mas há o mesmo fenômeno com outro mecanismo: a **janela de veto**. `maybe_open_autonomous_window()` abre uma pendência (`opens_at`), e a mensagem só é criada depois, por `resolve_elapsed_autonomous_sends()`, numa requisição posterior — poll do cliente, do operador ou `_drive_unclaimed_autonomy()`. O estado da pendência vive no Postgres; o Langfuse observa `autonomy.pending_opened` e `autonomy.pending_resolved` como eventos separados, e o contrato §3.4 proíbe **atualizar** um score de `PENDING` para `SENT`, porque uma abertura atrasada poderia sobrescrever um desfecho. É a mesma disciplina de "nunca segurar um span aberto durante a espera": o trace do turno não engloba a janela; a correlação é por `session_id = conversation_id` e `trace_id = triggering_message_id`. A tabela de identificadores deste capítulo tem a sua versão lá: `conversation_id` (caso de negócio), `triggering_message_id` (turno), `pending_id` (pendência), `message_id` (envio confirmado) — e a regra "isso precisa ser implementado, não é uma lei" vale dobrado, porque a convenção foi escolhida por quem leu `autonomy/service.py`. O relógio com dois trabalhos também: `n5.response_latency_ms` mede da mensagem disparadora ao envio e **inclui** debounce e janela de veto; o tempo de LLM está dentro das generations. Não some um ao outro nem apresente o primeiro como "latência do modelo".

**Em projetos comuns do ecossistema.** Todo sistema com humano no loop — aprovação, revisão de rascunho, escalonamento — tem essa fronteira. Em LangGraph, é `interrupt()`/`Command(resume)` com checkpointer; em FastAPI puro, é uma linha numa tabela e um poll; em filas, é uma mensagem esperando. Em todos, a idempotência do trecho reexecutado na retomada é uma responsabilidade do desenho, e a observabilidade só a revela se você marcar a retomada como raiz própria com o mesmo identificador de correlação. Em Langfuse, `session_id` cumpre o papel do `thread_id` de metadados; em LangSmith, `metadata.thread_id`. Nenhum dos dois retoma nada.

**O fator humano — onde a IA faz e onde você decide.** Este é o capítulo em que você **é** o componente. No DCRA, a revisão de MEDIUM/HIGH; na plataforma, o operador que reivindica, edita o rascunho, assume controle ou deixa a janela de veto expirar. Um assistente de IA pode simular a aprovação (o lab faz isso e avisa que é sintético), mas a decisão real, com sua nota e sua responsabilidade, é o dado mais valioso que o sistema produz — e o mais fácil de contaminar se for automatizado "só para gerar volume". Foque em duas coisas: (1) definir o que conta como latência de negócio e o que conta como latência técnica, porque essa fronteira é uma decisão de produto que o trace não toma; (2) revisar, você mesmo, cada trecho de código que roda **antes** de um `interrupt()` ou antes de abrir uma pendência, perguntando "se isto rodar duas vezes, o que acontece?". A IA escreve o código; a pergunta "duas vezes" é sua, e é ela que evita uma mensagem duplicada para um paciente.
