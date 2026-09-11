# 07 · O trace verde que esconde um pequeno incêndio

[Índice](README.md) · [Anterior](06-threads-checkpoints-revisao.md) · [Próximo](08-instrumentacao-contexto.md)

**Objetivo:** diferenciar tentativa falha, falha final e resposta degradada. Tempo: 20–25 minutos. Código: [03_failures.py](labs/03_failures.py). Sem modelo.

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/03_failures.py --send
```

São quatro traces. Os timeouts e atrasos são **injetados em funções locais**; nenhum serviço real é derrubado. Abra cada URL impressa e expanda `ler_catalogo`.

| Trace | O que ocorre | Onde procurar |
|---|---|---|
| `falha-slow` | uma leitura bem-sucedida, com espera sintética maior | duração do filho |
| `falha-retry` | primeira tentativa falha; segunda funciona | filho com erro seguido de filho com sucesso |
| `falha-fallback` | duas tentativas falham; a função devolve indisponibilidade | raiz pode completar sem exception; output `degraded=true` |
| `falha-crash` | duas tentativas falham e a exception sobe | erro na raiz |

No último caso, o CLI captura a exception esperada para continuar o exercício. O span instrumentado da raiz já registrou a falha antes dessa captura externa.

## O diagnóstico que você deve fazer

No `retry`, conte chamadas a `ler_catalogo`: duas. Conte respostas finais ao chamador: uma. Portanto, taxa de falha **por tentativa** e taxa de falha **por pedido** têm denominadores diferentes.

No `fallback`, examine `dependency_count=null`. Não troque por zero: “não consegui consultar” não significa “não existem dependentes”. O projeto preserva essa distinção por `EvidenceStatus.UNAVAILABLE`, e as regras podem acrescentar `EVIDENCE_UNAVAILABLE`.

No `slow`, o tempo foi gasto dentro da leitura. Em um incidente real, abrir o filho ajuda a escolher a investigação: fonte lenta, fila, conexão, processamento local ou modelo. O trace não explica automaticamente a causa abaixo do ponto mais profundo instrumentado; talvez você precise de métricas de banco ou rede.

## Duas camadas de retry no seu projeto

Abra [factory.py](../src/dcra/llm/factory.py):

- `build_chat_model` configura `max_retries=2` na integração do provedor;
- `interpret` pode fazer uma segunda tentativa quando há `ValidationError`/`ValueError`;
- `draft_recommendation` também tem nova tentativa de validação e fallback definido.

Um pedido pode atravessar retries do transporte e retries de aplicação. **Duas tentativas de parsing não significam duas requisições físicas no máximo.** A granularidade exposta pelo trace depende da integração: retries internos do SDK podem aparecer como duração adicional dentro do mesmo span, sem um filho por requisição HTTP.

Não invente “seis chamadas observadas” apenas por multiplicar configurações. A multiplicação descreve um cenário possível sob determinadas falhas; a contagem efetiva depende de quais condições ocorreram e do comportamento do SDK.

## Latência: não some o que aconteceu ao mesmo tempo

Suponha coletores com 120 ms, 200 ms e 80 ms, executados em paralelo. A contribuição ideal dessa etapa ao caminho crítico é próxima do maior tempo, 200 ms, mais overhead; não 400 ms. Já uma sequência de retries consome tempos sucessivos e possivelmente backoff.

Além disso, um pai normalmente inclui o tempo de seus filhos. Somar pai e filho contabiliza o mesmo intervalo duas vezes. O mesmo cuidado reaparece nos custos agregados.

## Transforme observação em critério

Para este exercício, escreva:

```text
Erro técnico de pedido = raiz terminou com exception não recuperada.
Resposta degradada = raiz retornou sem evidência suficiente e sinalizou a lacuna.
Sucesso útil = informação necessária foi obtida e a resposta atende ao contrato.
```

São definições didáticas; uma aplicação real precisa de critérios próprios. Um fallback pode ser a resposta correta diante da indisponibilidade, mas ainda representar degradação da capacidade do serviço.

**Exercício oral:** “A taxa de erro caiu depois que criamos um fallback. Melhorou?” Responda que precisa verificar qualidade, cobertura de evidências, uso do fallback e experiência final. Capturar exceptions pode melhorar disponibilidade aparente enquanto esconde perda de utilidade.

**Memorize:** *retry*, *fallback*, *degraded response*, *critical path*, *denominator*. Para localizar as operações e seus erros na interface, consulte [conceitos de observabilidade](https://docs.langchain.com/langsmith/observability-concepts).

## Levar para outros projetos — e onde o seu julgamento decide

"Trace verde com incêndio dentro" é o padrão de falha mais comum em sistemas com LLM, e o mais fácil de esconder atrás de um fallback bem-intencionado.

**Na plataforma de atendimento (Langfuse Cloud).** O projeto é **fail-open por desenho** — em duas camadas. A observabilidade não pode afetar o atendimento (Langfuse fora do ar, flag desligada ou erro do SDK: nada muda para o cliente). E o próprio atendimento tem fallbacks: `status != "ANSWER"` cai em `generate_ungoverned_reply()`; provider `unavailable` aparece como status em `ai_generations`; em N2, falha de IA/RAG não impede o envio manual. Cada um desses é uma **resposta degradada** que uma taxa de erro técnico não vê. Refaça as três definições deste capítulo para lá: *erro técnico* = o turno não produziu decisão (nem `autonomy.decision`); *degradado* = fallback livre por falta de evidência, ou `INCONCLUSIVE` por referência ausente; *sucesso útil* = resposta enviada **e** critérios da rubrica atendidos. O contrato de scores já separa: `n5.fallback_started = 1` mesmo quando a chamada livre falha, e turnos que falham antes da decisão entram na contagem de falhas sem receber um falso 0. As "duas camadas de retry" têm uma lição invertida ali: o cliente OpenAI é criado com `max_retries=0` em `ai/providers.py` — a camada de transporte está **desligada de propósito**, e uma nova tentativa é sempre uma ação visível (a regeneração pelo operador, `ai.draft_regenerated`, ou um novo turno). Confira essa configuração antes de assumir que "houve retry"; e, se alguém religar `max_retries`, a contagem de requisições físicas por span deixa de ser 1 sem que o trace mostre um filho por tentativa. E a latência: `retrieve()` (embedding + consulta pgvector), geração e envio ocorrem em requisições diferentes; somar durações de spans que nem estão na mesma requisição é o erro do "pai + filho" em outra roupa.

**Em projetos comuns do ecossistema.** Todo `try/except` que devolve um valor padrão é um candidato a esconder perda de utilidade. Em LangChain, `.with_fallbacks()` e `with_retry()` são convenientes e invisíveis: a cadeia "funciona", e o modelo caro foi substituído pelo barato sem ninguém marcar isso no trace. A regra prática: **toda degradação vira um campo explícito** (`degraded=true`, `fallback_reason=...`, `EvidenceStatus.UNAVAILABLE`) e um score categórico — nunca só uma linha de log. E `null` continua diferente de zero: "não consegui consultar" não é "não existe".

**O fator humano — onde a IA faz e onde você decide.** Um assistente escreve retries, fallbacks e circuit breakers com prazer — e cada um deles melhora a disponibilidade aparente. O que ele não faz é a pergunta do exercício oral: *"a taxa de erro caiu depois do fallback; melhorou?"* Responder exige saber o que o usuário perdeu. Na plataforma, um paciente que recebe uma resposta cordial de fallback livre em vez do preço correto não apareceu em nenhuma métrica de erro — e só uma pessoa que leu a conversa sabe que ele saiu sem a informação. Foque em definir, por escrito, as três categorias (erro, degradado, sucesso útil) **para o seu domínio**, antes de pedir a qualquer IA que instrumente. Sem isso, ela vai instrumentar "exception ou não", que é a única definição que ela consegue inferir do código. Depois, faça o exercício inverso: pegue cinco traces verdes e pergunte, um a um, "o que este usuário realmente recebeu?". É a auditoria que nenhum filtro faz.
