# 10 · Do “gostei” a um dado que ajuda a melhorar o sistema

[Índice](README.md) · [Anterior](09-tokens-custos-orcamentos.md) · [Próximo](11-datasets-contratos.md)

**Objetivo:** separar avaliação humana, pontuação automática e decisão de negócio. Tempo: 20–30 minutos. Código: [04_feedback.py](labs/04_feedback.py).

No DCRA, um revisor pode aprovar uma mudança apesar de discordar da redação da IA, ou rejeitar uma mudança porque o risco descrito está correto. Logo, **APPROVE não significa “resposta da IA correta”** e REJECT não significa o contrário. São rótulos de decisão de negócio, com outro propósito.

## Experimento A — feedback em código

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py --send
.venv/bin/python ESTUDOS_LANGSMITH/labs/04_feedback.py --send
```

O segundo comando lê o `run_id` salvo pelo primeiro e adiciona `lab_total_correto=1`, pois dois itens de R$18 somam R$36. Abra novamente o trace, atualize e encontre o feedback. A origem é API/código, com comentário explicando o critério. Não é uma pessoa revisando o caso.

O exemplo usa `Client.create_feedback(run_id, key=..., score=..., comment=...)`. A documentação de [avaliação](https://docs.langchain.com/langsmith/evaluation-concepts) descreve feedback como a saída pontuada/categorizada do avaliador. A operação também está na referência do SDK instalado, conferida no capítulo 27.

## Experimento B — uma anotação humana com rubrica

Abra no [LangSmith](https://smith.langchain.com) um trace do lab 02 com `--real --send`, ou uma recomendação existente à qual você tenha acesso. Vá à área de feedback/anotação do run escolhido. Registre separadamente:

| Critério | 1 | 0 | Sem nota |
|---|---|---|---|
| `grounded` | afirmações factuais sustentadas pelas evidências | contém fato inventado ou contraditório | evidências insuficientes para julgar |
| `non_binding` | apresenta conselho, sem alegar execução/aprovação | afirma ter decidido ou executado a mudança | saída ausente/falha técnica |
| `actionable` | explica uma próxima ação concreta ligada ao risco | recomendação vaga | caso fora da rubrica |

Para cada nota, copie no comentário um trecho curto **do resultado do seu próprio exemplo** e diga qual evidência o confirma ou contradiz. Rótulo sem motivo é difícil de revisar e de usar para calibrar juízes.

Escolha a unidade correta: se está avaliando a recomendação, anote o run com essa saída ou um root que a exponha claramente. Um score de qualidade de texto anexado à chamada de `collect_asset` perde significado.

## Experimento C — fila de anotação

Na área **Annotation Queues**, crie uma fila de estudo, por exemplo `dcra-recomendacoes-estudo`, com os critérios acima. Adicione dois runs que você acabou de inspecionar e revise-os. A documentação atual inclui filas de run individual e comparação em pares. [Uso de annotation queues](https://docs.langchain.com/langsmith/annotation-queues).

Se não tiver outro revisor disponível, faça uma segunda anotação em outro momento, sem ver a primeira, e registre a limitação. Isso mede sua consistência, não concordância entre pessoas independentes. Para medir concordância entre anotadores de fato, são necessárias anotações independentes e um processo para resolver divergências.

## Transformar a falha em exemplo

Ao encontrar “não existem consumidores” quando a evidência mostra `reads_per_day=4`, use **Add to Dataset** no run/fila, selecione um dataset de estudo e revise os campos.

O output observado é o objeto sob avaliação. **Não o aceite automaticamente como referência correta.** Corrija a referência ou escreva uma rubrica/assertion de aceitação; verifique quais inputs o target precisará receber. [Criação de datasets pela UI](https://docs.langchain.com/langsmith/manage-datasets-in-application).

Feedback, filas e datasets podem ter implicações de retenção/cobrança diferentes das de um trace apenas recebido. Consulte a [documentação de retenção](https://docs.langchain.com/langsmith/administration-overview) e a sua conta ao ampliar esse uso.

**Memorize:** *rubric*, *human annotation*, *feedback provenance*, *inter-annotator agreement*. Na entrevista, uma boa frase é: “Eu não usaria a aprovação de negócio como rótulo automático de qualidade; definiria critérios separados e guardaria a origem de cada anotação.”
