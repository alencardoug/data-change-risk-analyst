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

## Levar para outros projetos — e onde o seu julgamento decide

Comparar baseline e candidata **nos mesmos exemplos, com a mesma régua, mudando uma variável** — é o método científico reduzido ao essencial, e é o que separa "melhorou" de "parece que melhorou".

**Na plataforma de atendimento (Langfuse Cloud).** O runner da fase 2 (§6.3) tem três operações — sincronizar dataset, avaliar snapshots, comparar variantes — e o critério de seleção do §6.4 é uma versão do "relatório de cinco linhas": nenhuma nova falha crítica nos casos comparados; nenhuma queda **não explicada** nos casos de conferência final; melhoria demonstrada no critério-alvo; custo e latência apresentados; se ambíguo, continua candidato. E a frase que fecha o parágrafo é a deste capítulo: *"Não promover apenas porque a média geral subiu. A seleção é uma decisão explícita do usuário, não um comando do avaliador."* Dois cuidados são específicos de lá. **Isolamento entre variantes**: cada variante em processo próprio, sem reaproveitar settings ou conexões — porque a "candidata" pode ser um prompt com label `candidato` **ou** um modelo global diferente, e misturar os dois é a "trapaça acidental" de mudar cinco coisas ao mesmo tempo. **Transição de caminho**: uma melhoria de recuperação pode mudar o `expected_path` efetivo (um caso que caía em fallback livre passa a ter `ANSWER`); o contrato manda registrar a transição e comparar pelos mesmos casos, sem classificá-la automaticamente como erro nem escondê-la. No Langfuse, cada variante é um *dataset run* sobre os mesmos itens; a comparação lado a lado por item existe na UI, e o manifesto da execução (commit, modelos, versões de prompt, fixture, juiz, repetições) é o que permite dizer o que mudou.

**Em projetos comuns do ecossistema.** Quatro regras portáveis: uma variável por vez; comparação **pareada** por exemplo (não duas médias); repetições quando há modelo real, sem tratá-las como casos independentes; e um conjunto de conferência final que ninguém olhou durante a elaboração. Em LangChain, "troquei o modelo" costuma trocar também tokenização, limites de contexto e comportamento de structured output — três variáveis disfarçadas de uma.

**O fator humano — onde a IA faz e onde você decide.** Um assistente executa os dois experimentos, tabula as médias e escreve "a candidata melhorou 3 pontos". Está tecnicamente certo e é exatamente o relatório que este capítulo ensina a desconfiar. O trabalho que é seu: **abrir a linha em que a candidata regrediu** e decidir se aquele caso importa mais que os que melhoraram. No DCRA, perder `orders.id` vale mais que ganhar cinco paráfrases; na plataforma, errar uma data de consulta vale mais que ficar mais conciso em dez saudações. Essa ponderação não está nos números — está no que você sabe sobre as consequências. Foque também na frase "se ambíguo, continua candidato": a IA tende a fechar a decisão (é o que se pede dela); você pode, e às vezes deve, **não decidir** e pedir outro experimento. E note o padrão ético embutido no contrato do projeto: a seleção é do usuário. Quando um assistente diz "recomendo promover", trate como uma hipótese a verificar nas linhas, não como veredito.
