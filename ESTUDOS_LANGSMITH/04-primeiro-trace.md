# 04 · Seu primeiro trace custa duas porções de risoto fictício

[Índice](README.md) · [Anterior](03-preparacao.md) · [Próximo](05-dissecar-dcra.md)

**Objetivo:** enxergar raiz, filhos, inputs e outputs sem misturar isso com comportamento de modelo. Tempo: 20 minutos. Código: [01_trace_python.py](labs/01_trace_python.py).

O restaurante serve “risoto de dados” a R$18. O pedido tem duas unidades. A instrumentação registra uma consulta de cardápio e um cálculo. O total de R$36 é o valor do pedido fictício, **não custo de tokens ou cobrança de observabilidade**.

## Execute e abra

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py --send
```

O primeiro comando mostra a resposta sem enviar trace. O segundo envia os mesmos dados sintéticos. Abra a URL impressa ou [LangSmith](https://smith.langchain.com) → **Tracing → dcra-estudos → pedido-restaurante**.

Expanda a árvore. Se a interface abrir primeiro a vista de mensagens, procure **Details / Trace** para ver operações que não são chat. A estrutura conceitual deve ser:

```text
pedido-restaurante                 raiz, operação composta
├── consultar_cardapio              tipo tool
└── calcular_total                  tipo chain/padrão
```

Os tempos variam e spans internos de SDK podem mudar. Os nomes escolhidos por nós são a referência estável para o exercício.

## Cinco observações concretas

1. Abra o input da raiz. Encontre `item` e `quantidade`. O wrapper recebe um dicionário; a UI pode mostrá-lo dentro da chave `inputs`, correspondente ao nome do argumento da função.
2. Abra `consultar_cardapio`. Encontre `preco_reais=18`. A função é marcada com `run_type="tool"`; neste exemplo quem a chama é Python, não um agente que decidiu usá-la.
3. Abra `calcular_total`. Veja preço e quantidade, depois o retorno `36`. Você isolou uma transformação sem ler o fluxo inteiro.
4. Volte à raiz. Seu output é `{total_reais: 36, moeda: BRL}`. Esse contrato é o que a próxima etapa consumiria.
5. Abra metadata/tags. Procure `environment=lab`, `synthetic=true`, `scenario=pedido-valido` e o marcador do laboratório.

Agora ache os mesmos nomes no código. Os decoradores `@traceable` instrumentam funções; `_common.traced_call` instrumenta a operação superior e associa um UUID à execução. O SDK consegue representar uma hierarquia porque as chamadas filhas ocorrem no contexto da raiz. A API de instrumentação manual é documentada em [Custom instrumentation](https://docs.langchain.com/langsmith/annotate-code).

## Três conclusões que valem mais que o screenshot

**LangSmith funciona com Python sem LangChain.** Este laboratório não constrói chain nem grafo; a observabilidade é independente da escolha de orquestrador.

**Um span chamado tool não prova decisão agêntica.** Aqui existe uma chamada determinística. Para afirmar que o modelo escolheu uma ferramenta, você precisa observar a mensagem/chamada de ferramenta correspondente no loop do agente.

**Zero chamada LLM não é “qualidade zero” ou “modelo grátis”.** Não há modelo para medir. Tokens/custo de modelo podem estar ausentes. Ausência de campo é diferente de um valor numérico calculado igual a zero.

## Experimento rápido de leitura

Sem executar de novo, procure qual operação seria a primeira suspeita se o total fosse R$54:

- input com quantidade 3: o sistema talvez esteja correto para o input recebido;
- preço retornado 27: investigar a fonte do cardápio;
- input 18 × 2 e output 54 no cálculo: bug na transformação.

O mesmo raciocínio se aplica ao DCRA: primeiro descubra **onde a informação divergiu**; depois formule a correção.

**Para falar em entrevista:** “Instrumentei uma função Python com uma raiz e duas etapas. Inspecionei entradas, saídas e metadados. Isso mostra que tracing não depende de LangChain, embora a integração automática com LangChain/LangGraph reduza o trabalho.”

**Memorize:** *root run*, *child run*, *run type*, *metadata*, *tags*. Registre no [caderno](28-caderno-de-evidencias.md) a URL, o `run_id` e qual função você abriria para investigar um preço incorreto.

## Levar para outros projetos — e onde o seu julgamento decide

Um trace de duas porções de risoto ensina o mesmo que um trace de produção com quarenta spans: **raiz, filhos, entradas, saídas, metadados** — e a disciplina de achar no código cada nome que aparece na tela.

**Na plataforma de atendimento (Langfuse Cloud).** O "primeiro trace" daquele projeto é o probe LF-1, e o segundo é um turno N5 real: raiz `n5.process_turn`, filhos `rag.retrieve`, `ai.answer` (ou `ai.n5_free`), `autonomy.decision` e, numa **requisição posterior**, `message.sent`. Refaça as cinco observações concretas ali: (1) o input da raiz deve ter a mensagem disparadora e `session_id = conversation_id`; (2) em `rag.retrieve`, procure a **query exata que foi embedada** — não só IDs — e os hits com score e rank; (3) na geração, as `messages` reais enviadas ao provider, o modelo e o uso de tokens; (4) o output de `autonomy.decision` (`n5_path`, `fallback_reason`, `mechanism`); (5) `environment=local-n5` e `release=customer-care-013` nos metadados. E a mesma ressalva do "span chamado tool": no Langfuse, uma *generation* é uma chamada de modelo, mas uma `AIGeneration` da aplicação pode ter sido determinística — o nome parecido não prova que houve LLM. O adaptador daquele projeto exporta **só** os nomes da lista `_OBSERVATION_NAMES`; se um span não aparece, primeiro confira se ele está na lista, depois se o código passou por ali.

**Em projetos comuns do ecossistema.** A conclusão "LangSmith funciona com Python sem LangChain" vale igual para Langfuse (`@observe`, `start_as_current_observation`) e para OpenTelemetry puro. Em projetos que usam LangChain/LangGraph, o `CallbackHandler` do Langfuse ou a integração automática do LangSmith geram a árvore por você — o que é ótimo até você precisar de um span que a biblioteca não conhece (uma consulta SQL, uma regra de negócio, uma decisão de roteamento). Nesses casos o padrão deste lab — decorador na função, wrapper na operação composta, metadados de correlação — é o que você vai escrever à mão.

**O fator humano — onde a IA faz e onde você decide.** Um assistente resume um trace em três linhas: "a raiz chamou duas funções e retornou 36". Correto e inútil se o que você quer é **aprender a ler**. A leitura que vale é a sua: abrir cada nó, prever o que vai encontrar, conferir, e voltar ao código para achar o nome. O experimento do "total R$54" é o treino desse músculo: três hipóteses, três lugares para olhar, uma decisão sobre qual abrir primeiro. Foque nisso — é a habilidade que você vai usar às 2h da manhã com um incidente e sem assistente. A IA pode acelerar a navegação; não pode substituir a sua capacidade de olhar um span e perceber que o nome está certo e o conteúdo, errado. Na plataforma, isso é a sessão LF-6: quem conhece o atendimento olha o `rag.retrieve` e sabe que o documento no rank 1 não é o que o paciente precisava — o assistente só vê que o score era 0,71.
