# 05 · Do resultado ao nó: três análises sob o microscópio

[Índice](README.md) · [Anterior](04-primeiro-trace.md) · [Próximo](06-threads-checkpoints-revisao.md)

**Objetivo:** usar o trace para explicar três caminhos do grafo real. Tempo: 30–40 minutos. Código: [02_dcra.py](labs/02_dcra.py) e [build.py](../src/dcra/graph/build.py).

Este lab instancia `GraphDeps` com interpretação e recomendação de fixture, catálogo em memória e o grafo do produto. **As regras e o workflow são reais; a geração é substituída.** O checkpointer em memória permite pausa/retomada dentro do mesmo processo. Não há consulta ao Postgres nem persistência de `AnalysisRecord` em banco neste laboratório.

## Experimento A — LOW

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case low --send
```

Abra a URL impressa. Entrada: `add index on orders(customer_id)`. Resultado esperado: **LOW**, `ADD_INDEX_LOW_RISK`, `AUTO_FINALIZED`, sem pausa.

1. Expanda `interpret`. Veja a operação `ADD_INDEX` e `index_columns=["customer_id"]` no estado resultante.
2. Encontre `collect_asset`, `collect_deps`, `collect_usage`.
3. Compare seus intervalos na timeline. Ser irmãos na árvore mostra a relação hierárquica; **sobreposição temporal** é a evidência visual de concorrência. Operações de fixture muito rápidas podem tornar isso difícil de enxergar.
4. Abra `assess_risk`, depois [assess](../src/dcra/rules/risk.py). O catálogo registra 90 leituras/dia para `customer_id`; a regra de contenção do índice usa limiar 100. Neste fixture o fator é LOW.
5. Siga a saída de `recommend` até `finalize`. Não procure uma aprovação humana que esse caminho não exige.

O fan-out ocorre nas arestas de `build_graph`; o reducer de `GraphState.evidence` consolida evidências. A implementação é uma prova estrutural da concorrência planejada; o trace permite observar o comportamento de uma execução.

## Experimento B — MEDIUM

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --send
```

Entrada: `drop column orders.customer_legacy_id`. Espere **MEDIUM**, fatores `REFERENCED_BY_VIEW` e `ACTIVELY_READ`, pausa no portão e `outcome=null`.

Abra as evidências: duas views e o consumidor `cs_lookup`. Vá ao `human_review`. O `__interrupt__` retornado pelo grafo contém o payload para revisão. Isso não é um crash do app; é uma saída prevista do protocolo de execução.

A recomendação fixture diz `DO_NOT_PROCEED`. Observe que o risco MEDIUM foi calculado antes, independentemente dessa frase. Esse detalhe evita confundir **disposition** da recomendação com **risk category** e **outcome** do caso.

## Experimento C — HIGH

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case high --send
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case unknown --send
```

| Caso | Evidência decisiva | Esperado |
|---|---|---|
| `orders.id` | chave primária e foreign key que a referencia | HIGH; revisão humana |
| `orders.legacy_region` | coluna ausente do catálogo fixture | HIGH; `ASSET_NOT_FOUND`; revisão humana |

No segundo caso, não espere investigação só porque o risco é HIGH. Abra `has_evidence_gap`: ativo inexistente não é a lacuna que aciona o investigador. O risco e a decisão de investigar respondem a perguntas distintas.

## A mesma leitura com o modelo do projeto

Após [preparar a conta](03-preparacao.md):

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --real --send
```

Agora procure os runs de modelo dentro de `interpret` e `recommend`, com prompt, retorno e uso de tokens quando reportado. O texto final pode variar. As evidências ainda são fixtures; este modo é um laboratório controlado, não réplica de todas as dependências da aplicação publicada.

Também pode abrir a [aplicação publicada](https://analisador-de-risco.web.app). Para rastrear suas execuções, você precisa de acesso ao workspace configurado **no servidor**. Informar uma chave no seu terminal não reconfigura o Cloud Run. O ambiente publicado pode ler metadados de Postgres e diferir do catálogo em memória.

**Conceito LangGraph:** fan-out/fan-in e roteamento por estado. **Utilidade:** leituras independentes e caminhos explicáveis. **Alternativa simples:** três chamadas sequenciais e `if/else`. **Defesa:** a combinação de paralelismo, revisão persistente e loop limitado motiva o grafo; o trace permite verificar a execução dessa estrutura. A integração de tracing é descrita em [observabilidade do LangChain](https://docs.langchain.com/oss/python/langchain/observability).

**Exercício oral:** explique por que HIGH não implica “agente vai investigar” e por que LOW não implica “LLM aprovou”.

## Levar para outros projetos — e onde o seu julgamento decide

O que este capítulo treina é **ir do resultado ao nó e do nó ao código** em três caminhos distintos do mesmo grafo. A plataforma de atendimento tem exatamente essa estrutura, com outros nomes.

**Na plataforma de atendimento (Langfuse Cloud).** Os "experimentos A, B e C" do N5 são os três caminhos de `maybe_open_autonomous_window()`: **reaproveitar `ANSWER`** (geração fundamentada entregue verbatim), **guided booking** (trigger elegível, ofertas e parser ordinal vs. embedding) e **fallback livre** (`status != "ANSWER"` ou atalho clínico abaixo de 0,40 → `generate_ungoverned_reply()`, que **não** recebe evidências). Para cada um, faça o que fez com LOW/MEDIUM/HIGH: abra o trace, ache `autonomy.decision`, leia `n5_path` e `fallback_reason`, e vá ao código confirmar por que aquele ramo disparou. As armadilhas são as mesmas: "HIGH não implica investigação" vira "saudação não é fallback até o trace confirmar o ramo"; "disposition ≠ risk category ≠ outcome" vira "status da geração ≠ caminho N5 ≠ mecanismo efetivo (`ungoverned_n5` vs. `governed_autonomy`)" — o ramo governado N3/N4 é avaliado **antes**, e classificar tudo como N5 porque o switch está ligado é o erro equivalente a "LLM aprovou". A sobreposição temporal dos coletores tem paralelo na recuperação: `retrieve()` mistura Q&A e clínico por distância, dedupa pais e corta em `top_k=8` — o trace mostra o resultado; o código explica a ordem.

**Em projetos comuns do ecossistema.** Todo grafo LangGraph com roteamento condicional merece este exercício: um caso por aresta condicional, executado com dependências falsas, com o trace guardado. É a forma mais barata de documentar "por que este caminho existe" e de detectar quando uma mudança de prompt muda o roteamento sem ninguém perceber. Em Langfuse, marque o caminho como score categórico (o projeto usa `n5.path`) — assim a distribuição de caminhos vira um gráfico, e uma mudança na distribuição vira um alerta.

**O fator humano — onde a IA faz e onde você decide.** Um assistente segue o trace e explica cada nó com precisão: "o roteador leu `risk == HIGH` e chamou `human_review`". É uma boa narração. O que só você faz é **julgar se o caminho estava certo para aquele caso** — e isso exige saber o que o pedido queria dizer. No DCRA, "remover `orders.id`" é HIGH porque você sabe o que é uma chave primária; na plataforma, "quanto custa a consulta com o oncologista?" caindo em fallback livre é um erro porque você sabe que existe uma tabela de preços que deveria ter sido recuperada. A IA vê ramos; você vê intenção. Foque nos casos em que o trace está "verde" e o caminho está errado — são os que nenhum filtro de erro vai mostrar, e os que um leitor automático descreve com naturalidade como se fossem corretos.
