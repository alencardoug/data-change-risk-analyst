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
