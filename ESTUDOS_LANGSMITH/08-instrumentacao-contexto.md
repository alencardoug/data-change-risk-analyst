# 08 · O fio que liga as etapas não se propaga por telepatia

[Índice](README.md) · [Anterior](07-falhas-latencia-retries.md) · [Próximo](09-tokens-custos-orcamentos.md)

**Objetivo:** entender o alcance da instrumentação automática e a propagação de contexto. Tempo: 25 minutos. Código: [14_context.py](labs/14_context.py), [_common.py](labs/_common.py).

Em LangChain/LangGraph, os callbacks das bibliotecas cobrem muitas operações. Uma função Python arbitrária, um subprocesso ou um serviço remoto não se torna automaticamente parte da mesma árvore só por estar no mesmo repositório. A instrumentação precisa marcar a operação e transportar a relação com o chamador.

## O que instrumentar

Uma fronteira útil normalmente responde a uma pergunta: “a leitura do catálogo demorou?”, “a normalização alterou o identificador?”, “o juiz falhou?”. Não precisa decorar cada soma ou cada acesso a um dicionário.

O lab 01 usa `@traceable` em funções e um wrapper na operação composta. O projeto usa `.invoke()` do grafo e dos componentes integrados. Em ambos os casos, você quer entradas, saídas, duração, erro e contexto suficiente para correlacionar.

Uma divisão razoável para este sistema é: raiz por invocação do workflow; nós como etapas; chamadas de modelo/ferramenta como filhos; identificador de caso compartilhado nos metadados. Evite nomes de span contendo o texto inteiro do usuário: isso prejudica agrupamento e pode exportar dados desnecessários.

## Experimento de contexto

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/14_context.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/14_context.py --send
```

O output deve conter:

```json
{
  "lost": {"case_id": "sem-contexto", "result": 20},
  "propagated": {"case_id": "caso-sintetico-42", "result": 20}
}
```

O cálculo é idêntico; a capacidade de relacioná-lo ao caso muda. O primeiro worker executa em `Context()` vazio, deliberadamente. O segundo usa `copy_context().run`, que transporta os `ContextVar` presentes, incluindo o contexto de tracing.

No LangSmith, procure `contexto-threads`. O worker propagado deve ser descendente dessa raiz. O worker sem contexto pode aparecer como outra raiz, com metadados ausentes; procure também runs `worker` no mesmo projeto e horário. Se sampling estiver ativo, ele pode nem ser enviado.

Este exemplo simula a perda explicitamente para ser estável entre versões de Python. Não significa que toda tarefa assíncrona perca contexto, nem que o LangGraph deixe de cuidar dos executores que gerencia.

## E quando muda o processo ou o serviço?

`copy_context` não cruza uma conexão HTTP. O SDK documenta propagação distribuída por cabeçalhos, com `run_tree.to_headers()` no chamador e contexto pai no receptor. [Tracing distribuído](https://docs.langchain.com/langsmith/distributed-tracing).

Esboço conceitual, **não um servidor criado neste curso**:

```python
# Chamador, dentro de um run:
headers = get_current_run_tree().to_headers()
# transporte HTTP leva headers + payload

# Receptor, após receber headers:
with tracing_context(parent=headers):
    executar_funcao_instrumentada(payload)
```

O `trace_id` relaciona operações de uma execução; `thread_id` pode agrupar várias execuções do mesmo caso. Copiar apenas o `thread_id` permite correlação, mas não estabelece por si só a relação pai-filho de um trace distribuído.

## Como verificar se a instrumentação está certa

Abra um trace e escolha um filho:

1. O pai corresponde à operação que o chamou?
2. O ID de caso chegou ao filho?
3. O projeto/ambiente identifica a execução corretamente?
4. Há duas instrumentações produzindo spans duplicados para a mesma chamada?
5. Entradas e saídas ajudam o diagnóstico sem incluir dados desnecessários?

Os testes do curso capturam árvores em memória com `tracing_context(enabled="local")`, sem ingestão remota, para verificar hierarquia e metadados. O modo local do SDK é diferente dos scripts sem `--send`, que normalmente desativam tracing e só executam a lógica.

**Conceito LangChain:** callbacks/contexto de execução. **Utilidade:** acompanhar a chamada composta sem decoradores em todos os componentes. **Alternativa:** spans manuais em funções próprias. **Defesa:** integrar instrumentação é trabalho de engenharia; uma árvore incompleta pode induzir diagnóstico incorreto. [Instrumentação manual](https://docs.langchain.com/langsmith/annotate-code).

**Memorize:** *context propagation*, *parent-child relationship*, *orphan span*, *correlation ID*.
