# 12 · Uma avaliação de verdade pega um erro que você plantou

[Índice](README.md) · [Anterior](11-datasets-contratos.md) · [Próximo](13-experimentos-comparacao.md)

**Objetivo:** executar avaliadores de código e entender exatamente o que suas notas significam. Tempo: 25–30 minutos. Sem rede/modelo.

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/06_evaluate.py
```

O script executa o grafo para os 16 casos, primeiro com a baseline e depois com uma mutação **só no adaptador de laboratório**. Nenhuma regra do produto foi editada.

Abra [_dcra.py](labs/_dcra.py), função `target`. A variante `bug` transforma o risco HIGH da resposta do adaptador em LOW e informa que não aguarda revisão. É o equivalente didático a uma camada de apresentação/integracão que perde a criticidade do resultado.

O grafo ainda percorreu o caminho original e calculou fatores corretos. Essa diferença é proposital: a falha pode estar depois do componente de regras. Por isso avaliamos o contrato consumido pelo chamador, além de inspecionar etapas internas.

## Resultado esperado

| Métrica | Baseline | Variante com bug |
|---|---:|---:|
| `risk_correct` | 1,0000 | 0,8125 |
| `review_correct` | 1,0000 | 0,8125 |
| `factors_exact` | 1,0000 | 1,0000 |
| `error_contract` | 1,0000 | 1,0000 |
| Recall dos casos HIGH | 1,0000 | 0,0000 |

Os três casos HIGH são c03, c04 e c07. A média de classificação é 13/16 na candidata, mas ela falha em todos os exemplos dessa classe crítica.

Abra `artefatos/06-bug.json` e localize c03. Compare `outputs`, `reference` e `scores`. A nota não veio de uma impressão de leitura: veio de um predicado explícito aplicado a duas estruturas.

## Leia o avaliador

Em [_evaluators.py](labs/_evaluators.py):

```python
def risk_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "risk_correct",
            "score": int(outputs.get("risk") == reference_outputs["risk"])}
```

`key` identifica a métrica. `score` é o valor numérico; aqui 0 ou 1. Os mesmos avaliadores podem ser adaptados pelo SDK quando `Client.evaluate` fornece outputs e referências. Consulte as [entradas/saídas de avaliadores](https://docs.langchain.com/langsmith/evaluation-concepts).

Logo abaixo está `high_risk_recall_summary`, que recebe **as listas inteiras** de outputs e referências em vez de um par. Existem duas famílias: o avaliador por exemplo responde “esta linha está certa?”; o avaliador de resumo responde “o que a rodada mostrou?”. Recall precisa da segunda, porque seu denominador são os três HIGH de referência — uma quantidade que nenhuma linha individual conhece. Média de notas por exemplo e métrica de conjunto não são a mesma operação.

`factors_exact` compara conjuntos porque a ordem dos códigos não importa para esse contrato. Se a multiplicidade de um fator fosse relevante, transformar em conjunto esconderia duplicações: o método de comparação precisa respeitar a semântica.

`error_contract` confere a presença esperada de erro. Não mede qualidade da mensagem, tipo específico da exception nem ausência de gravação indevida. São propriedades adicionais possíveis; uma nota existente não cobre automaticamente critérios que não implementou.

## Precision e recall, com um caso importante

Para detectar HIGH:

```text
recall HIGH = HIGH corretamente identificados / todos os HIGH de referência
precision HIGH = HIGH corretamente identificados / todos os que o sistema chamou de HIGH
```

Na candidata, recall é 0/3 = 0. Ela não prevê HIGH algum, então a precision dessa classe tem denominador zero; precisa de uma convenção explícita ou valor ausente. O curso evita transformar ausência de casos em sucesso.

O custo do falso LOW é diferente do custo de mandar um LOW para revisão desnecessária. Uma função de perda ponderada ou gates por risco podem refletir isso. Defina essas prioridades com o problema de negócio, não apenas com conveniência estatística.

## O que este resultado prova e o que não prova

Prova que os contratos da baseline e a política atual se alinham às 16 referências e que os avaliadores detectam a mutação deliberada. Não prova compreensão de linguagem do LLM, robustez a todo schema ou qualidade da recomendação natural: esses componentes usam fixtures.

Uma avaliação **offline** é feita sobre um conjunto de exemplos fora do tráfego vivo. Ela pode usar internet e chamar modelos. O que fizemos aqui é uma avaliação offline **executada localmente sem rede**; no próximo capítulo publicaremos experimentos offline no SaaS.

**Pergunta de entrevista:** “Por que não usar juiz LLM para tudo?” Porque igualdade de categoria, presença de revisão e validade de contrato podem ser verificadas com código previsível, barato e explicável. Reserve julgamento semântico para onde ele acrescenta informação.

**Memorize:** *target*, *evaluator*, *exact match*, *false negative*, *recall*, *offline evaluation*.
