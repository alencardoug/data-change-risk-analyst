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

O exemplo usa `Client.create_feedback(run_id, key=..., score=..., comment=..., session_id=..., start_time=...)`. O `session_id` é o UUID do projeto que contém o run — obtido com `client.read_project(project_name=...)` — e passou a ser obrigatório na [migração para o SmithDB](https://docs.langchain.com/langsmith/smithdb-sdk-migration): o servidor localiza o run pela partição (projeto, hora de início), não por uma busca pelo id. É por isso que o lab 01 grava o projeto e o `start_time` ao lado do `run_id`. A documentação de [avaliação](https://docs.langchain.com/langsmith/evaluation-concepts) descreve feedback como a saída pontuada/categorizada do avaliador. A operação também está na referência do SDK instalado, conferida no capítulo 27.

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

Feedback, filas e datasets têm implicações de retenção/cobrança próprias — e diferentes entre si: pela documentação lida em 11 de setembro de 2026, feedback e notas pela UI não mudam a faixa de retenção do trace; feedback pela API só promove com `extend_trace_retention=true`; e entrar numa fila de anotação não promove por padrão. Consulte a [documentação de retenção](https://docs.langchain.com/langsmith/administration-overview) e a sua conta ao ampliar esse uso; a tabela por tipo de dado está no [capítulo 22](22-operacao-slos-incidentes.md).

**Memorize:** *rubric*, *human annotation*, *feedback provenance*, *inter-annotator agreement*. Na entrevista, uma boa frase é: “Eu não usaria a aprovação de negócio como rótulo automático de qualidade; definiria critérios separados e guardaria a origem de cada anotação.”

## Levar para outros projetos — e onde o seu julgamento decide

Este é o capítulo em que o fator humano deixa de ser um comentário lateral e vira o **próprio dado**. Tudo que vem depois — dataset, juiz, gate — herda a qualidade da anotação que uma pessoa fez aqui.

**Na plataforma de atendimento (Langfuse Cloud).** A confusão "APPROVE ≠ resposta correta" tem uma versão exata lá: em N2, o operador **aceita, edita ou regenera** o rascunho (`ai.draft_accepted`, `ai.draft_edited`, `ai.draft_regenerated`); em N5, deixa a janela de veto expirar, pausa, edita ou assume controle (`n5.pending_outcome`: `SENT`, `PAUSED`, `EDITED`, `TAKEN_OVER`). Nenhum desses é uma nota de qualidade: um operador pode editar um rascunho correto por preferência de tom, ou deixar passar um rascunho errado porque estava com quatro conversas abertas. São **rótulos de decisão operacional**, valiosos como sinal fraco — o `OBSERVABILITY.md` reserva o *Human Correction Rate* como KPI futuro justamente por isso — mas não substituem uma anotação com rubrica. A rubrica já está escrita (`detalhamento_execucao.md` §6.2): utilidade, continuidade, consistência com referências, clareza — cada uma 0/1/2 — mais `critical_checks` objetivos e `INCONCLUSIVE` quando falta referência, sem converter em zero. No Langfuse, isso vira *scores* com nome por critério (numérico ou categórico), comentário citando o trecho, e origem registrada (`source`: anotação humana vs. eval automática vs. API). A **fila de anotação** existe lá também (*annotation queues*), e o plano prevê exatamente o que o Experimento C faz aqui: dois revisores, critérios explícitos, concordância medida antes de calibrar o juiz. "Add to Dataset" tem o paralelo: um trace ruim vira item de `n5-baseline-v1` com `source_trace_id`, `expected_facts` **revisados** — o output observado é o objeto sob julgamento, nunca a referência.

**Em projetos comuns do ecossistema.** Três regras portáveis: (1) uma nota por critério, nunca uma nota global; (2) todo feedback carrega origem (humano, código, juiz, evento de negócio) — em LangSmith `feedback_source_type`, em Langfuse `source`/`author`; (3) a unidade certa: anote o run que produziu a saída avaliada, não a raiz de um grafo com dez nós nem a chamada de embedding. E a retenção: em LangSmith, feedback pela API pode promover o trace à faixa estendida; em Langfuse, scores ficam com o trace e seguem a retenção do projeto — confira antes de anotar em massa.

**O fator humano — onde a IA faz e onde você decide.** Aqui a fronteira é nítida: a IA pode preencher uma fila de anotação em minutos, e o resultado será plausível, consistente e **inútil como referência**, porque a pergunta que a anotação responde é "uma pessoa que conhece o atendimento considera isto aceitável?". Se a IA responde, você mediu concordância da IA consigo mesma. Foque em três coisas que só você produz: (1) a rubrica — os critérios vêm do que o serviço deve ser, e "clareza para um paciente ansioso" é uma definição sua; (2) a anotação com trecho citado — "rótulo sem motivo é difícil de revisar"; (3) a segunda anotação independente, sua ou de outra pessoa, para saber se o critério é estável. Depois disso, sim, a IA entra: como juiz **calibrado contra as suas notas** (capítulo 15), como agregador, como quem sugere casos para a fila. A ordem importa: humano primeiro, máquina depois — e nunca o contrário, nem "para ganhar tempo".
