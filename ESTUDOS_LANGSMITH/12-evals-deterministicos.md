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

## Levar para outros projetos — e onde o seu julgamento decide

Avaliadores de código são baratos, previsíveis e explicáveis. A lição transferível é dupla: **use código onde código basta**, e **meça o recorte crítico separadamente da média**.

**Na plataforma de atendimento (Langfuse Cloud).** Os `critical_checks` do §6.2 são os avaliadores determinísticos daquele projeto: formato estruturado, escolha de oferta correta, consistência de data/preço com a referência, preservação de dado que o cliente já forneceu, ausência de envio proibido pelo cenário — cada um `PASS`/`FAIL`/`NOT_APPLICABLE`. Nenhum precisa de juiz. `Hit@8` na recuperação (o documento de referência apareceu entre os 8 recuperados?) é um `risk_correct` com outro nome: comparação exata de IDs, sem semântica. E o recall dos HIGH tem um paralelo que o contrato já enuncia: **"uma falha crítica não deve ser compensada por uma média alta de cordialidade"** — `ACCEPTABLE` exige todos os críticos aprovados e nenhuma nota 0; uma média de utilidade 1,8 com um preço errado é `UNACCEPTABLE`. A mutação "HIGH→LOW no adaptador" tem uma versão útil para plantar ali: um candidato que inverte o `expected_path` (entrega fallback livre onde havia `ANSWER` fundamentado) — os critérios qualitativos podem até subir, e o `critical_check` de caminho, quando listado, reprova. No Langfuse, avaliadores de código rodam no runner local e publicam scores por item do *dataset run*; o `INCONCLUSIVE` por referência ausente vira uma categoria própria, nunca zero — o mesmo cuidado do "denominador vazio" na precision dos HIGH.

**Em projetos comuns do ecossistema.** A distinção **avaliador por exemplo vs. avaliador de conjunto** é a mais esquecida. Acurácia, exact match, validade de schema e presença de campo são por exemplo; recall de uma classe, cobertura de um slice, "nenhum caso crítico falhou" são de conjunto e precisam da lista inteira. Em LangSmith, `summary_evaluators`; em Langfuse, calcule no runner e publique como score do run. E comparação por conjunto (`factors_exact`) só quando a ordem não faz parte do contrato — em `index_columns` ela faz; em uma lista de ofertas de agenda, provavelmente também.

**O fator humano — onde a IA faz e onde você decide.** Um assistente escreve `risk_correct`, `Hit@k` e `factors_exact` em segundos e sem erro de sintaxe. O que ele **não sabe** é qual classe é crítica e quanto custa cada tipo de erro. Que um HIGH virar LOW é intolerável e um LOW virar MEDIUM é só um incômodo — isso vem do negócio: revisão humana existe para os HIGH. Na plataforma, que um preço errado seja crítico e uma resposta prolixa não seja — vem de quem entende o que um paciente faz com um preço errado. Foque em escrever, antes do código, a **função de perda em português**: "errar X custa muito; errar Y custa pouco; não conseguir responder é aceitável se sinalizado". Depois peça o avaliador. E resista à tentação inversa: quando um avaliador determinístico reprova, a IA sugere com facilidade "relaxar o critério" ou "tratar como não aplicável". Decidir se o critério estava errado ou se o sistema está errado é julgamento seu — e o gate do capítulo 23 depende de você não ceder aqui.
