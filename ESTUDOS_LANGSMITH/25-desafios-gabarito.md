# 25 · Investigar antes de abrir o gabarito

[Índice](README.md) · [Anterior](24-entrevista-simulada.md) · [Próximo](26-glossario.md)

**Objetivo:** ligar hipótese, execução e decisão sem repetir frases decoradas. Escolha três desafios para uma sessão de 20–30 minutos. Todos podem ser resolvidos localmente; os exercícios conceituais indicam seus dados no enunciado.

Antes de expandir cada resposta, escreva no [caderno](28-caderno-de-evidencias.md): previsão, evidência procurada e critério de conclusão. Números de custo são fictícios, conforme o lab 09. Os desafios não exigem alterar o produto.

## 1. O detector que falha nos casos mais importantes

Execute `06_evaluate.py`. A candidata acertou 13 de 16 categorias. Isso basta para aceitá-la? Identifique os casos errados e uma métrica que mostre o impacto de negócio. Depois rode o gate com `--candidate bug`.

<details>
<summary>Gabarito e evidência</summary>

Nos relatórios `artefatos/06-baseline.json` e `artefatos/06-bug.json`, filtre as linhas cuja referência é HIGH. São três casos; na candidata, todos viram LOW e deixam de aguardar revisão. O recall dos HIGH é **0/3 = 0**, apesar de **13/16 = 81,25%** de acerto geral. `factors_exact` permanece 1: fatores corretos não garantem categoria nem roteamento corretos.

O gate recusa a candidata, com exit code 1. A mutação vive em [labs/_dcra.py](labs/_dcra.py); ela não altera as regras do produto. A evidência demonstra detecção desta regressão nos casos de referência, sem medir a qualidade de um LLM real.

</details>

## 2. Uma raiz sem exception e uma fonte indisponível

Execute `03_failures.py`. Compare `retry`, `fallback` e `crash`. Em qual deles houve recuperação da consulta? Em qual existe uma resposta degradada? É correto transformar `dependency_count=null` em zero?

<details>
<summary>Gabarito e evidência</summary>

Em `retry`, a primeira tentativa falha e a segunda retorna `OBTAINED`, `dependency_count=2`, `degraded=false`. Em `fallback`, as duas falham; a função retorna `UNAVAILABLE`, contagem ausente e `degraded=true`. A ausência de exception na raiz é compatível com essa degradação.

Em `crash`, a segunda falha se propaga pela função instrumentada; o CLI captura a exception esperada para completar o exercício. Consulte `artefatos/03-falhas.json` e [labs/03_failures.py](labs/03_failures.py). Com envio habilitado, inspecione também as tentativas filhas. Zero afirmaria que a consulta verificou ausência de dependentes; `null` indica que esse dado não foi obtido.

</details>

## 3. Uma devolução que muda o caminho

Execute os dois comandos e compare as fases:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --review return
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --review return-evidence
```

Quantas recomendações existem depois da devolução? Por que a quantidade de passagens pelo risco difere? Os dois comandos deveriam compartilhar o mesmo `thread_id`?

<details>
<summary>Gabarito e evidência</summary>

Cada comando cria seu próprio caso e três fases: início, devolução, aprovação. Dentro de cada caso, o `thread_id` é estável e cada fase recebe um `run_id` distinto. Entre comandos, os IDs dos casos são diferentes.

Depois de `return`, `recommendation_versions=[1,2]` e `risk_passes=1`. Depois de `return-evidence`, as versões também são `[1,2]`, mas `risk_passes=3`: avaliação inicial, reavaliação após re-coleta e reavaliação dentro de `investigate`. Confira [06](06-threads-checkpoints-revisao.md) e [nodes.py](../src/dcra/graph/nodes.py), sem inferir o número de chamadas de modelo apenas pelo tamanho do histórico.

As evidências fixture permanecem iguais, então solicitar reavaliação não implica mudar a categoria. A aprovação final simulada produz `APPROVED`.

</details>

## 4. Três maneiras de contar a mesma conta

Uma chamada recebe 1.000 tokens, incluindo 200 de cache, e gera 200. Use a tabela fictícia do lab 09: US$2, US$0,50 e US$8 por milhão para entrada sem cache, cache e saída. Qual é o custo? Quantas dessas chamadas cabem em US$0,010? Qual o erro de somar raiz agregada e filhos?

<details>
<summary>Gabarito e evidência</summary>

`800 × 2 / 1.000.000 + 200 × 0,50 / 1.000.000 + 200 × 8 / 1.000.000` resulta em **US$0,0033**. Três reservas somam **US$0,0099**; a quarta ultrapassa o limite.

Em `09_costs.py`, as três folhas do caso completo somam **US$0,02195**. A conta deliberadamente errada retorna **US$0,05470**, porque inclui a raiz agregada, as folhas e o wrapper do agente. Compare `artefatos/09-custos.json`. Isso demonstra contabilidade local; os valores não são preços atuais nem cobrança medida de um provedor.

</details>

## 5. O juiz concordou em todas as respostas recebidas

Situação hipotética: deveriam existir seis avaliações, mas quatro terminaram com erro de API. As duas válidas concordaram com a anotação manual. Como apresentar o resultado? Execute o ensaio de `08_judge.py` para examinar os critérios.

<details>
<summary>Gabarito e evidência</summary>

Reporte concordância **2/2 nas avaliações válidas**, cobertura **2/6** e **4/6 erros do juiz**. Não anuncie “100% de qualidade em seis casos”. A concordância mede relação com a referência manual; a disponibilidade do medidor é outra medida.

O [lab 08](labs/08_judge.py) mantém `agreement=None` em caso de erro e separa `n_valid` de `n_total`. Sem `--real`, ele só apresenta os casos e as anotações: os números deste desafio são hipotéticos, não resultado desse comando. Para ver a mecânica com um erro de verdade, rode `--fixture-biased --judge-error j04`: cobertura 5/6, concordância 3/5 e exit code 1. Se nenhuma avaliação for válida, concordância fica ausente, não 0 ou 100%.

</details>

## 6. Uma resposta com citação ainda pode estar errada

Execute `11_rag.py`. Explique como `bad_retrieval` e `hallucination` podem falhar por motivos diferentes. Qual deles obtém a evidência correta? Qual se abstém sem inventar uma resposta?

<details>
<summary>Gabarito e evidência</summary>

| Modo | Recall de recuperação @1 | Resposta correta | Fundamentada ou abstenção |
|---|---|---|---|
| `good` | 1 | 1 | 1 |
| `bad_retrieval` | 0 | 0 | 1 |
| `hallucination` | 1 | 0 | 0 |

`bad_retrieval` recebe a política de frete e se abstém. `hallucination` recebe o documento do prazo de sete dias, mas afirma noventa; a citação presente não sustenta o número. Compare `artefatos/11-rag.json`. Os avaliadores são oráculos estreitos sobre dois documentos sintéticos, sem embeddings nem LLM. O prazo pertence ao corpus inventado do exercício.

</details>

## 7. O mesmo cálculo ficou sem identidade

Execute `14_context.py`. Os dois workers devolvem 20. Por que apenas um conhece `case_id`? `copy_context()` resolveria automaticamente a propagação para outro serviço?

<details>
<summary>Gabarito e evidência</summary>

O primeiro worker roda deliberadamente em `Context()` vazio e recebe `sem-contexto`. O segundo roda com `copy_context()` e recebe `caso-sintetico-42`. O resultado de negócio coincide, mas falta correlação no primeiro caminho.

Consulte `artefatos/14-contexto.json`. O experimento demonstra contexto Python no mesmo processo. Outro serviço precisa de propagação no transporte e extração no destino, como explicado em [08](08-instrumentacao-contexto.md). Ele também não prova que todo Python perde contexto por padrão: a perda foi injetada explicitamente.

</details>

## 8. A referência vazou para a aplicação

Um colega propõe passar `case` inteiro ao target de avaliação, incluindo `outputs` esperados, para “ajudar o modelo”. Qual problema isso cria? Localize a separação atual entre target e avaliadores.

<details>
<summary>Gabarito e evidência</summary>

O modelo passa a receber parte da resposta usada para corrigi-lo. O resultado deixa de representar a situação em que só o pedido está disponível. Em [06_evaluate.py](labs/06_evaluate.py), o target recebe `case['inputs']`; os avaliadores recebem o resultado e `case['outputs']` separadamente.

Referências também precisam de revisão própria: copiar automaticamente a saída da baseline como verdade pode eternizar seus erros. O dataset do curso contém referências explícitas em [casos.jsonl](dados/casos.jsonl), que você pode conferir contra os requisitos e evidências.

</details>

## 9. O benchmark é antigo, mas ainda está verde

Você alterou um prompt depois de gerar o relatório da candidata. O acerto salvo continua em 100%. O relatório pode aprovar o código atual? Leia `12_regression_gate.py` e execute `13_prompts.py`.

<details>
<summary>Gabarito e evidência</summary>

O relatório precisa corresponder aos artefatos avaliados. O gate compara os hashes atuais de código/dados com o manifesto salvo e recusa divergência, mesmo que as métricas antigas passem. Uma mudança exige nova avaliação da versão correspondente.

O lab 13 demonstra dois conteúdos de prompt com hashes diferentes. Seu modo local não publica commits nem mede melhoria de resposta. Em uso remoto, fixar um commit de prompt ajuda a reconstruir a entrada; uma tag mutável ou `latest` não identifica uma revisão imutável. Um hash sozinho também não guarda o conteúdo.

</details>

## 10. A amostra contém só casos ruins

Situação hipotética: você conserva todos os erros e apenas 10% dos sucessos. O dashboard dos traces conservados mostra 20% de erro. É a taxa de erro de todo o tráfego? Como investigaria sem perder casos raros?

<details>
<summary>Gabarito e evidência</summary>

A seleção tem probabilidades diferentes por resultado. A média dos traces conservados não estima diretamente a taxa geral. Mantenha contadores do tráfego total ou use uma amostra representativa para estimar taxas; a amostra enriquecida de erros continua útil para investigação.

Se as probabilidades de inclusão forem conhecidas, ponderação pode corrigir certas estimativas, desde que o desenho e os pressupostos sejam adequados. Não tente corrigir a conta com um percentual único sem saber como os dados foram selecionados. Veja [19](19-privacidade-amostragem.md) e [22](22-operacao-slos-incidentes.md).

</details>

## 11. Quatro taxas de erro para o mesmo dia

Execute `16_consultar_runs.py`. O time pergunta: “qual foi nossa taxa de erro?”. O bloco `denominadores` oferece quatro números. Qual deles você levaria a uma conversa sobre experiência do usuário? Qual levaria a uma conversa sobre a saúde do catálogo? E por que a soma das durações dos filhos do trace `tA` é exatamente igual à duração da raiz?

<details>
<summary>Gabarito e evidência</summary>

Para experiência do usuário, `erro_por_pedido` = **1/3 ≈ 0,3333**: uma das três raízes terminou em erro, e é isso que alguém sentiu. Para a saúde do catálogo, `erro_por_tentativa_de_collect_deps` = **1/3**, acompanhado de `pedidos_em_que_collect_deps_nunca_obteve_resposta` = **0** — a dependência falha com frequência, e o retry vem escondendo isso. `erro_por_run` = **3/14 ≈ 0,2143** é o número que mais aparece em painéis e o que menos responde a alguma pergunta: seu denominador mistura raízes e filhos de traces de tamanhos diferentes.

No `tA`, os três coletores rodam na mesma janela. A soma ingênua dá 1200 ms, igual à raiz, sugerindo que a orquestração não custa nada; a ocupação real é 1000 ms e sobram **200 ms** de tempo próprio. Compare `artefatos/16-consultas.json` com [runs.jsonl](dados/runs.jsonl), onde os horários de início e fim estão explícitos. O mesmo cuidado aparece no [07](07-falhas-latencia-retries.md) para latência e no [09](09-tokens-custos-orcamentos.md) para custo.

</details>

## Como corrigir seu raciocínio

Marque um ponto por hipótese verificável, evidência adequada e conclusão com limite explícito. Revise os desafios em que você acertou o número, mas não soube indicar de onde veio. Para o próximo ensaio oral, escolha justamente uma dessas lacunas.

## Levar para outros projetos — e onde o seu julgamento decide

Onze desafios com gabarito escondido: **hipótese, evidência, conclusão com limite**. O formato é reutilizável; os desafios da plataforma de atendimento ainda não têm gabarito — e é isso que os torna melhores.

**Na plataforma de atendimento (Langfuse Cloud).** As hipóteses H01–H05 do `caderno_de_evolucao.md` são desafios sem `<details>`: *H01* — o recorte de mensagens prejudica a continuidade (verificação: comparar histórico necessário com o request do turno que repetiu a pergunta); *H02* — a posição do primeiro resultado direciona para o caminho errado (referência correta × ranking × caminho × saída); *H03* — o fallback é pouco útil porque faltam dados na entrada (inspecionar o request de `ai.n5_free` e julgar pela informação recebida); *H04* — resposta ruim vem do template/documento ou do rerank, sem composição livre; *H05* — lentidão fora da geração (debounce, janela, polls). Reescreva cada uma no formato deste capítulo antes de abrir um trace: **previsão** ("acho que em mais da metade dos casos ruins o dado do turno anterior não está no request"), **evidência procurada** (o span de geração de 10 conversas de dois turnos), **critério de conclusão** ("se ≥ 5/10 não têm o dado, H01 confirmada como modo de falha frequente; se ≤ 2/10, descartada como dominante"). Vários desafios daqui têm tradução direta: o **5** (juiz concordou nas respostas recebidas) é a regra "inconclusivos separados, não contados como concordância"; o **8** (referência vazou) é "o target recebe `messages`, os avaliadores recebem `expected_facts`"; o **9** (benchmark antigo verde) é o manifesto com versão de prompt e hash de corpus; o **10** (amostra só de ruins) é a leitura de 20–30 conversas *ruins* da Fase 0 — ela acha modos de falha, não estima taxa de acerto; o **11** (quatro taxas de erro) é `n5.fallback_started` versus turnos sem decisão.

**Em projetos comuns do ecossistema.** Transforme cada incidente resolvido em um desafio com gabarito: enunciado com os dados disponíveis, pergunta, e a resposta com a evidência que a sustentou. É a documentação de operação mais útil que existe, porque treina a próxima pessoa em vez de só informá-la — e a IA é boa em dar forma ao enunciado depois que você escreveu a resposta.

**O fator humano — onde a IA faz e onde você decide.** A IA resolve os onze desafios instantaneamente — e, se você a deixar, você não aprende nada. Este capítulo existe para produzir em você a experiência de **prever, verificar e errar**, e é a única parte do curso em que o assistente é contraproducente por definição. Foque em: (1) escrever a previsão antes de qualquer consulta, mesmo que esteja errada — uma previsão errada corrigida ensina mais do que uma resposta certa lida; (2) nos desafios da plataforma, que não têm gabarito, ser rigoroso com o critério de conclusão **antes** de abrir os traces — porque sem ele qualquer resultado confirma a hipótese que você já gostava; (3) usar a IA **depois**: para checar o seu raciocínio, para sugerir uma evidência que você não considerou, para fazer a pergunta seguinte. A frase "marque um ponto por hipótese verificável, evidência adequada e conclusão com limite explícito" é a rubrica do seu próprio julgamento; ninguém pontua isso por você. E há um limite ético embutido aqui: na Fase 0 da plataforma, as conversas lidas são o único dado sobre o que o serviço faz com as pessoas; o julgamento sobre "isto foi ruim para quem perguntou" é uma responsabilidade que faz sentido manter humana, mesmo quando a IA pudesse classificar mais rápido.
