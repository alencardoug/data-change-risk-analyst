# 21 · As quatro ferramentas da vaga, sem confundir seus papéis

[Índice](README.md) · [Anterior](20-rag-fora-do-projeto.md) · [Próximo](22-operacao-slos-incidentes.md)

**Objetivo:** transferir conceitos para Langfuse e OpenTelemetry, mantendo foco na entrevista. Tempo: 20–30 minutos; extensão executável opcional.

| Ferramenta | Papel principal nesta conversa | Exemplo |
|---|---|---|
| LangChain | componentes/integrações para aplicações com modelos e agentes | modelo, saída estruturada, ferramentas |
| LangGraph | execução de workflows/agentes com estado | ramificação, paralelismo, checkpoint, interrupt/resume |
| LangSmith | observar, avaliar e trabalhar com artefatos de aplicações de IA | traces, datasets, experimentos, prompts, feedback |
| Langfuse | observabilidade e avaliação de aplicações de IA, com recursos de prompts/datasets | traces/observations, scores, experimentos, prompts |

A tabela seleciona responsabilidades relevantes; não é inventário de toda a oferta de cada produto. Você não precisa hospedar o DCRA no LangSmith para enviar traces da aplicação que já roda no Cloud Run. Tampouco precisa de LangGraph para usar Langfuse.

## O vocabulário muda, o raciocínio continua

| Conceito | LangSmith | Langfuse |
|---|---|---|
| Execução observada | trace com runs | trace com observations |
| Chamada de modelo | run de tipo `llm` | observation de tipo `generation` |
| Correlação entre interações | thread metadata | session/correlação configurada |
| Nota | feedback | score |
| Casos de avaliação | dataset/examples | dataset/items |
| Rodada de comparação | experiment | experiment/dataset run, conforme UI/API |
| Artefato de prompt | prompt e commits/tags | prompt e versões/labels |

Essas são correspondências de finalidade, **não conversões garantidas campo a campo**. Confira schema, semântica de custo e unidade de agregação antes de migrar dados. As capacidades e o modelo de instrumentação do Langfuse estão em [Observability overview](https://langfuse.com/docs/observability/overview) e na [referência Python atual](https://python.reference.langfuse.com/langfuse).

## Mesmo risoto, outra câmera — lab opcional

O [15_langfuse.py](labs/15_langfuse.py) recria o pedido de R$36 do lab 01. Primeiro rode o ensaio:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/15_langfuse.py
```

Para executar de fato, crie/selecione um projeto de estudo no Langfuse e configure, em seu `.env`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL` conforme a região indicada pela conta. Um exemplo de interface regional é [Langfuse Cloud EU](https://cloud.langfuse.com); use a região que corresponde às suas credenciais.

Rode em um ambiente separado do produto:

```bash
uv run --no-project --with 'langfuse>=4,<5' --with 'python-dotenv>=1,<2' python ESTUDOS_LANGSMITH/labs/15_langfuse.py --send
```

Esse comando pode baixar dependências e envia observações à sua conta. Não modifica `pyproject.toml` nem faz instalação no ambiente do produto. A faixa da dependência permite alterações dentro da versão principal; registre a versão efetivamente resolvida se repetir o experimento.

Abra **Traces** no projeto de estudo. Procure `pedido-restaurante`, com filhos `consultar_cardapio` e `calcular_total`. Compare com o trace do LangSmith: mesmas perguntas sobre entrada, saída, relações e duração.

O código usa `start_as_current_observation` para criar spans no contexto ativo e `flush` ao finalizar. O exemplo remoto de Langfuse **não foi executado na preparação do material**; sua API foi conferida na documentação e o modo de ensaio foi verificado. [Instrumentação e ciclo de vida do cliente](https://langfuse.com/docs/observability/sdk/instrumentation).

## Onde entra OpenTelemetry

OpenTelemetry fornece APIs, SDKs e convenções de telemetria; não é, sozinho, a UI onde você gerencia datasets e compara recomendações. Um pipeline pode instrumentar operações, exportar spans via OTLP e usar um collector para processar/encaminhar dados.

Langfuse usa uma base OpenTelemetry em seu SDK atual. LangSmith também oferece integração com OpenTelemetry e mapeamento de atributos. Logo, “LangSmith não aceita OTel” seria uma afirmação incorreta. [Tracing com OpenTelemetry no LangSmith](https://docs.langchain.com/langsmith/trace-with-opentelemetry).

Ao combinar integrações, observe spans duplicados, contexto quebrado, atribuição de custo, formatos de mensagens e atributos que um destino não interpreta. Emitir a mesma chamada duas vezes pode produzir gráficos convincentes e contas erradas.

## Como escolher em vez de torcer

Avalie adequação ao stack, experiência de investigação/eval, opções de hospedagem, integração com telemetria existente, governança, custo total e esforço de operação. Langfuse oferece [self-hosting](https://langfuse.com/self-hosting), mas isso traz responsabilidade de manutenção; não significa custo operacional zero. Requisitos e ofertas empresariais devem ser conferidos no momento da decisão.

**Resposta defensável:** “Eu começaria pelos mesmos casos e critérios nas ferramentas candidatas. Compararia qualidade dos traces, facilidade de avaliação, integração, acesso aos dados e custo operacional. Minha experiência prática mais aprofundada aqui está em LangSmith.”

**Memorize:** *observation*, *generation*, *score*, *OTLP*, *collector*, *instrumentation*, *backend*.
