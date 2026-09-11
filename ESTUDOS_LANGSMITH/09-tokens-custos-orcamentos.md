# 09 · O agente não paga a conta; você precisa entendê-la

[Índice](README.md) · [Anterior](08-instrumentacao-contexto.md) · [Próximo](10-feedback-anotacao.md)

**Objetivo:** fazer contas corretas e distinguir medir de limitar gasto. Tempo: 25–30 minutos. Código: [09_costs.py](labs/09_costs.py).

## Primeiro, separe as contas

| Parcela | Exemplos |
|---|---|
| Modelo da aplicação | interpretação, recomendação, turnos do investigador |
| Avaliação | juiz LLM, repetições de targets, eventualmente modelos diferentes |
| Ferramentas | busca paga, consultas/serviços com preço por chamada |
| Infraestrutura | Cloud Run, banco, armazenamento, rede |
| Observabilidade | ingestão, retenção e recursos do plano |

O custo calculado em um span de modelo não é automaticamente o custo total do caso nem a fatura final. LangSmith pode calcular valores a partir de uso e tabela de preços ou receber custos explícitos. Integração, identificação do modelo e informação de uso precisam estar corretas. [Cost tracking](https://docs.langchain.com/langsmith/cost-tracking).

## Conta de guardanapo — números inventados

Rode:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/09_costs.py
```

Tabela **FICTÍCIA**: US$2 por milhão de tokens de entrada sem cache; US$0,50 por milhão de entrada lida do cache; US$8 por milhão de saída.

Uma chamada tem 1.000 tokens de entrada, dos quais 200 vieram do cache, e 200 de saída:

```text
entrada sem cache = (1.000 − 200) × 2 / 1.000.000 = US$0,0016
entrada com cache = 200 × 0,50 / 1.000.000         = US$0,0001
saída             = 200 × 8 / 1.000.000            = US$0,0016
total                                                  US$0,0033
```

Os 200 tokens de cache já estão dentro dos 1.000 de entrada. Somá-los como tokens adicionais contaria parte do uso duas vezes. O exemplo verifica também entradas inválidas, como cache maior que input.

O script monta um caso com três custos de folhas: **US$0,02195**. A soma errada de raiz agregada, wrapper do investigador e folhas dá **US$0,05470**. A diferença é dupla contagem, não uma taxa misteriosa.

## Veja os campos na UI, sem chamar modelo

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/09_costs.py --send
```

Abra o projeto **`dcra-estudos-custos-sinteticos`**. O exemplo envia uso e custo inventados identificados como tal. Procure `modelo-de-papel`, `usage_metadata` e os detalhes de entrada/cache/saída. Isso ensina o formato de medição; não representa execução ou preços de um provedor real.

Para medir de verdade, use o modo real do lab 02 e abra os spans de modelo. Campo ausente ou modelo sem correspondência de preço não autoriza concluir “custou zero”. Use os [metadados padronizados de modelo](https://docs.langchain.com/langsmith/ls-metadata-parameters) e confira a tabela correspondente ao período e à configuração da conta.

## Quanto custa uma avaliação?

Considere 16 exemplos × 2 versões × 3 repetições: **96 execuções de target**. Com um juiz por resultado: mais **96 execuções de juiz**. Se cada target tiver dois passos de modelo, já são 192 chamadas lógicas da aplicação antes dos juízes e retries.

Fórmula de planejamento:

```text
C_eval ≈ N × V × R × (C_target + J × C_juiz)
```

`N`: exemplos; `V`: variantes; `R`: repetições; `J`: juízes por resultado. Não multiplique também por concorrência: concorrência muda quantas execuções ocorrem ao mesmo tempo, não o número planejado de exemplos.

## Quanto custa guardar? — a parcela da observabilidade

A tabela da abertura tem uma linha que o resto do capítulo não somava: ingestão e retenção. O lab agora imprime `plataforma_mensal`, calculado por `estimativa_mensal` com uma tarifa **fictícia** (`TarifaPlataforma`) que copia só a **estrutura** da fatura documentada: a fatura tem **dois medidores**, um de ingestão, que conta todo trace do mês em qualquer faixa, e um de upgrades, que conta as promoções à retenção estendida feitas no mês — de traces ingeridos neste mês ou em outro. Na tarifa inventada: franquia de 5.000 traces ingeridos, US$0,0025 por trace ingerido, US$0,005 por upgrade e US$39 por assento.

Cenário: 20.000 traces ingeridos no mês e 2.000 upgrades (feedback pela API com retenção estendida, ou avaliador com a opção ligada).

```text
ingestão   20.000 − 5.000 de franquia = 15.000 × 0,0025        = US$37,50
upgrades   2.000 × 0,005                                       = US$10,00
assentos                                                         US$39,00
plataforma                                                       US$86,50
modelo da aplicação + juiz + armazenamento externo (inventados) + US$16,00
total                                                            US$102,50
```

Dois erros simétricos, ambos calculados pelo lab:

- **Erro A — tirar o promovido da ingestão: US$81,50.** Supõe que o trace promovido “sai” da faixa base. Não sai: a ingestão já aconteceu e foi contada.
- **Erro B — cobrar a ingestão de novo: US$91,50.** Soma ao upgrade o preço de ingestão outra vez, como se o upgrade fosse uma segunda ingestão.

O segundo cenário do lab, `plataforma_mes_sem_ingestao`, é um mês com **zero** traces novos e 500 upgrades de traces antigos: a fatura é US$41,50, não zero. É o caso que a conta “traces × preço” nunca representa. A regra exata de franquia, o preço de cada medidor e o que promove um trace vêm da sua conta e da [página de preços](https://www.langchain.com/pricing); a função existe para você trocar os parâmetros, não para citar estes números. O capítulo [22](22-operacao-slos-incidentes.md) trata das condições de promoção e da saída dos dados.

## Medidor, alarme e disjuntor

Um painel é o medidor. Um alerta de orçamento é o alarme. Um mecanismo que recusa uma próxima operação é o disjuntor. Não são garantias equivalentes.

O lab tem `Budget.reserve`: com US$0,010 fictício, aceita três reservas de US$0,0033 e recusa a quarta. É um exemplo local de admissão antes da execução. Em produção, precisa de estimativa conservadora, reconciliação com gasto observado e reserva atômica compartilhada entre workers. Também precisa considerar resposta em andamento, retries e cobrança de ferramentas.

`max_concurrency=1`, limite de recursão e `--limit 3` ajudam a controlar execução, mas nenhum deles, isoladamente, é teto financeiro. Os limites de gasto de **avaliadores gerenciados** do LangSmith têm seu próprio escopo, tratado em [18](18-evals-online-producao.md).

**Pergunta de entrevista:** “Como reduziria custo?” Meça a parcela dominante, compare qualidade antes/depois, reduza contexto redundante, evite investigação sem benefício, limite repetições e avalie roteamento de modelo/cache com critérios explícitos. O objetivo útil pode ser **custo por caso resolvido corretamente**, e não só custo por requisição.

**Memorize:** *token usage*, *cost attribution*, *cached input*, *budget enforcement*, *cost per successful task*, *retention tier*.

## Levar para outros projetos — e onde o seu julgamento decide

Separar as parcelas da conta, não contar tokens duas vezes, e distinguir **medidor, alarme e disjuntor** — três hábitos que valem para qualquer ferramenta e qualquer provedor.

**Na plataforma de atendimento (Langfuse Cloud).** As parcelas lá: modelo de atendimento (`gpt-5-mini` em `ai.answer`, `ai.n5_free`, `ai.clinical_rerank`, `ai.date_intent`), embeddings (`text-embedding-3-small` em `ai.embedding` — em cada `retrieve()` **e** na ingestão do catálogo), avaliação (juiz LLM da fase 2), infraestrutura (Postgres/pgvector local) e observabilidade (Langfuse Cloud free tier — confira o limite de observações/mês na conta). O plano já anota o ponto que este capítulo enfatiza: **registrar o preço de `gpt-5-mini` e `text-embedding-3-small` no Langfuse, com fonte datada, senão o custo vem vazio** — e vazio não é zero. A dupla contagem tem uma forma específica ali: um turno N5 com fallback livre tem **duas** gerações (a inicial, que não passou, e a livre); o custo do turno é a soma das duas, e um painel que agrega por trace e também por generation conta em dobro. A fórmula `C_eval ≈ N × V × R × (C_target + J × C_juiz)` se aplica ao runner da fase 2: 30 casos × 2 variantes × 1 repetição × (turno completo com embedding + 1 juiz) — e o `detalhamento_execucao.md` §6.3 já pede custos de atendimento, ingestão e avaliação **separados** no relatório. O disjuntor, lá, é o limite mensal na OpenAI e o `n5_kill_switch_enabled`; o alarme, o painel; e nenhum `top_k=8` ou debounce é teto financeiro.

**Em projetos comuns do ecossistema.** Três verificações antes de citar um custo: (1) o campo de uso está presente no span de modelo, e o modelo tem preço cadastrado (LangSmith: metadados padronizados; Langfuse: definição de modelo com preço por token de entrada/saída/cache)? (2) a agregação é por folha de modelo, não por raiz mais folhas? (3) o número inclui juízes, retries e repetições? Em LangChain, `usage_metadata` do `AIMessage` é a fonte; em `with_structured_output`, confira se o parser não engole o uso. E **custo por caso resolvido corretamente**, não por requisição — na plataforma, custo por conversa com resposta `ACCEPTABLE`, não por generation.

**O fator humano — onde a IA faz e onde você decide.** Um assistente faz a conta de guardanapo sem errar (e este lab foi escrito para você conferir se ele erra). O que ele não faz: **assinar a fatura** e decidir o teto. Definir "quanto este projeto pode gastar por mês" e "o que acontece quando bate no teto — pausa, degrada, avisa?" é uma decisão de negócio e de responsabilidade financeira que ninguém deve delegar. Foque nisso: antes de qualquer experimento, escreva o teto, configure o disjuntor no provedor (não só o alerta), e defina a métrica de eficiência que importa — custo por caso **útil**. Depois, use a IA para instrumentar e agregar. Há um segundo ponto seu: julgar se um gasto vale a pena. "A investigação com agente custou 3× e não trouxe evidência nova" é uma conclusão que exige olhar o benefício, e benefício é julgamento de quem conhece o domínio — a IA vê o custo, não o valor.
