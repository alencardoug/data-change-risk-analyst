# 13 · Coloque baseline e candidata na mesma bancada

[Índice](README.md) · [Anterior](12-evals-deterministicos.md) · [Próximo](14-modelo-real-saida-estruturada.md)

**Objetivo:** criar experimentos no LangSmith, comparar casos pareados e justificar uma decisão. Tempo: 25–35 minutos. Usa LangSmith, sem modelo pago.

## Execute

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/05_dataset.py --send
.venv/bin/python ESTUDOS_LANGSMITH/labs/06_evaluate.py --send
```

Abra [LangSmith](https://smith.langchain.com) → **Datasets & Experiments** → o dataset cujo nome foi impresso no lab 05. Procure os experimentos com prefixos `dcra-baseline` e `dcra-bug`. O SDK acrescenta identificadores aos nomes para distinguir execuções.

Selecione os dois e abra a comparação. O nome preciso do botão pode variar; a operação desejada é comparar resultados dos mesmos exemplos, lado a lado. O modelo conceitual e a navegação estão no [guia de análise de experimentos](https://docs.langchain.com/langsmith/analyze-an-experiment).

## O que abrir na tela

1. Veja a média de `risk_correct`: 1 contra 0,8125, salvo falhas de execução/ingestão.
2. Localize a linha cujo input remove `orders.id`.
3. Compare os outputs: HIGH na baseline, LOW na candidata.
4. Compare `factors_exact`: os fatores podem continuar corretos enquanto a categoria foi corrompida pelo adaptador.
5. Abra o trace desse exemplo. Vá até `assess_risk`: o nó ainda calculou HIGH. Volte ao output do target e encontre a divergência.
6. Inspecione os outros dois casos críticos antes de concluir que é um caso isolado.

Agora você tem localização do defeito, extensão observada e critério de rejeição. Isso é mais útil que apenas olhar uma barra vermelha.

## Abra o código da execução

Em [06_evaluate.py](labs/06_evaluate.py), encontre:

```python
results = client.evaluate(
    target,
    data=examples,
    evaluators=EVALUATORS,
    summary_evaluators=SUMMARY_EVALUATORS,
    experiment_prefix="...",
    max_concurrency=1,
    num_repetitions=1,
)
```

O código real usa `partial(target, variant=variant)`. `data` vem de `list_examples(..., as_of=...)`, fixando o snapshot. A baseline e a candidata recebem os mesmos exemplos, e as métricas usam o mesmo código de avaliação. A configuração de concorrência e repetições é descrita em [Experiment configuration](https://docs.langchain.com/langsmith/experiment-configuration).

Um **tracing project** agrupa execuções observadas. Um **dataset** contém exemplos. Um **experiment** registra a execução de uma configuração sobre exemplos, com outputs, notas e traces. Os experimentos não precisam aparecer como simples novas linhas do projeto `dcra-estudos`: a área natural de comparação é o dataset.

## Comparar sem trapacear acidentalmente

Altere uma variável relevante por vez quando quiser atribuir causa. Se troca prompt, modelo, catálogo, dataset e juiz simultaneamente, uma diferença de nota não identifica qual mudança a produziu.

Também compare falhas novas e correções por exemplo. Dois sistemas podem ter média igual e errar casos completamente diferentes. Para o DCRA, perder um caso de chave primária pode ser mais importante que ganhar várias paráfrases fáceis.

Em modelos reais, repetições ajudam a observar variabilidade. Mas três repetições do mesmo caso não criam três problemas independentes. Guarde o ID do exemplo e analise a dependência entre repetições ao estimar incerteza.

Se a baseline tiver 90/100 e a candidata 92/100 em um conjunto pequeno, não chame automaticamente de melhora sólida. Veja onde mudou, repita de forma planejada, examine incerteza e relevância prática. Um ganho estatístico pequeno pode não compensar o dobro do custo ou uma regressão crítica.

## Relatório de cinco linhas

Preencha no caderno:

```text
Comparação: baseline × bug; dataset e snapshot: ...
Critério: preservar classificação e revisão de todos os HIGH.
Observação: 3/3 casos HIGH falharam na candidata; média geral 13/16.
Localização: saída do adaptador, após o grafo calcular o risco correto.
Decisão: rejeitar candidata neste gate; não promover com base na média geral.
```

Os quatro avaliadores por exemplo produzem uma nota por linha; o recall HIGH só existe sobre o conjunto. Por isso o lab também passa `summary_evaluators=[high_risk_recall_summary]`, e o experimento recebe `high_risk_recall` como métrica agregada — 1,0 na baseline, 0,0 na candidata. É a diferença entre um avaliador que julga um exemplo e um que julga a rodada. A média de um avaliador por exemplo não substitui isso: nenhuma média de `risk_correct` tem os três casos HIGH como denominador.

**Memorize:** *experiment*, *baseline*, *candidate*, *paired comparison*, *regression*, *slice analysis*.
