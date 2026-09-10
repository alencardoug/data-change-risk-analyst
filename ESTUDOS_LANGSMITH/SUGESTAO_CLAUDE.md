# Parecer sobre o curso — leitura, execução e revisão

[Índice](README.md)

**Data: 10 de setembro de 2026.** Este documento avalia o material de `ESTUDOS_LANGSMITH/`, registra o que foi executado para chegar a essa avaliação e lista as mudanças que já apliquei. Ele segue a mesma regra que o curso impõe a si mesmo: separar o que foi medido do que foi lido.

## Veredito

**É um bom curso — e a distância entre ele e um tutorial comum não está no conteúdo de LangSmith, está na disciplina epistêmica.** A maioria do material sobre observabilidade de LLM ensina a clicar. Este ensina a perguntar “qual é o denominador?”, e faz isso repetidamente, em contextos diferentes, até virar hábito. Para o objetivo declarado — sustentar uma entrevista técnica sobre observabilidade e avaliação em até três dias — ele é adequado e, em vários pontos, melhor que o necessário.

Encontrei cinco problemas reais. Quatro eu corrigi; um está documentado abaixo com a razão de não ter mexido. Nenhum deles é de conteúdo errado: são lacunas de estrutura, de alcance e de manutenção.

## O que verifiquei antes de opinar

Não avaliei apenas lendo. Executei:

| Verificação | Resultado |
|---|---|
| `verificar_material.py` (antes das minhas mudanças) | 25 comandos, exit codes esperados, nenhuma tentativa de rede |
| `verificar_material.py` (depois) | 26 comandos, idem |
| `pytest tests ESTUDOS_LANGSMITH/tests` (sem o teste MCP) | 67 aprovados, 19 pulados |
| `ruff check src tests ESTUDOS_LANGSMITH` | Aprovado |
| Introspecção do `langsmith` 0.11.1 | Assinaturas conferidas; três depreciações encontradas |

As afirmações verificáveis do [capítulo 27](27-fontes-e-validacao.md) conferem. Isso é raro o bastante para ser dito com todas as letras: **o material declara o que executou, e o que ele declara é verdade.** A validação com bloqueio de `socket` nos subprocessos é um cuidado que quase nenhum curso tem — ela impede que um laboratório “local” dependa silenciosamente da rede.

## O que o curso faz melhor que a média

**Ensina denominadores, não botões.** A ideia central — “95% de qualidade” é uma frase incompleta sem unidade, população, janela e critério — reaparece no capítulo 02, na taxa por tentativa versus por pedido do 07, na dupla contagem de custo do 09, no recall de denominador vazio do 12, no viés de amostragem do 19 e na cobertura do juiz do 15. Um leitor que faça a rota inteira sai com um reflexo, não com uma lista.

**O bug plantado é bem escolhido.** A mutação HIGH→LOW vive no adaptador de estudo, depois de o grafo ter calculado o risco correto. Ela produz 81,25% de acerto geral e 0% de recall na classe que importa, com `factors_exact` intacto em 1,0. É um exemplo em que a média mente, o fator parece certo e a consequência de negócio é grave — três lições em um único experimento reproduzível que termina em exit code 1.

**A honestidade é estrutural, não decorativa.** O “inventário honesto” do capítulo 01 separa o que está no produto, o que foi acrescentado como estudo e o que não existe. Preços fictícios são rotulados como fictícios em todo lugar em que aparecem. O capítulo 27 lista o que **não** foi executado. O capítulo 24 instrui explicitamente: “se disse ‘validei em produção’ mostrando fixtures, corrija a afirmação”. Um candidato treinado assim não se queima numa pergunta de acompanhamento.

**As distinções conceituais são precisas onde normalmente são frouxas.** Checkpoint não é trace. `disposition` não é `risk category` nem `outcome`. Acionar investigação não é investigar com sucesso. Um span de tipo `tool` não prova decisão agêntica. Validade de schema não é fidelidade semântica. Cada uma dessas confusões é exatamente o que um entrevistador competente sonda.

**A prosa respeita o leitor.** As metáforas — o guarda-volumes, a cozinha e o crítico, a câmera que não precisa filmar o cartão — carregam a distinção conceitual e depois saem do caminho. Não há entusiasmo vazio.

## Os problemas que encontrei

### 1. Quatro capítulos nunca apareciam na rota de três dias — corrigido

O roteiro citava 01–07, 09, 11–15, 17–21 e 23–25. Ficavam de fora **08** (instrumentação e contexto), **10** (feedback e anotação), **16** (avaliar workflow e agentes) e **22** (operação e SLOs).

Isso não é um detalhe de sumário. O README oferece a rota de três dias como “a camada essencial”, e um leitor com prazo faz exatamente o que a tabela manda. Ele terminaria sem tocar em filas de anotação, rubricas humanas e avaliação de trajetória de agente — três dos assuntos com maior probabilidade de cair numa entrevista sobre avaliação de sistemas com LLM. O capítulo 10 é pior de perder ainda por outro motivo: é ele que explica como uma falha observada vira uma referência revisada. Sem ele, o dia 2 começa com um dataset caído do céu.

**O que fiz:** redistribuí os três dias para incluir os quatro. O dia 1 ganhou o lab de contexto (15 min), o dia 2 ganhou a anotação com rubrica (20 min), o dia 3 ganhou avaliação de agente e operação (20 min cada). As sessões ficaram em 155, 160 e 160 minutos, dentro da faixa de 2–3 horas que o próprio material promete. Para não estourar, o capítulo 20 (RAG) passou a bloco opcional explícito, com o critério de decisão dito em voz alta: útil se a vaga mencionar recuperação, dispensável se não mencionar.

### 2. A métrica mais importante do curso não chegava ao LangSmith — corrigido

O capítulo 13 dizia, com franqueza: *“você pode inferir o recall pelas três linhas críticas, mas não espere uma coluna agregada adicional que o script não publicou”*.

Ou seja: o número que sustenta a decisão inteira — recall HIGH = 0 — existia no relatório local e **não** na tela que o aluno mostraria numa demo. O curso teria treinado alguém a dizer “a candidata perde todos os HIGH” e a abrir uma comparação onde isso não está escrito.

O `Client.evaluate` do SDK instalado aceita `summary_evaluators`, que é precisamente o mecanismo para métricas de conjunto. Verifiquei a assinatura e a forma da função contra o normalizador do SDK.

**O que fiz:** `high_risk_recall_summary` em [_evaluators.py](labs/_evaluators.py), passado pelo [lab 06](labs/06_evaluate.py). O experimento remoto agora publica `high_risk_recall` como métrica agregada — 1,0 na baseline, 0,0 na candidata. Os capítulos 12 e 13 explicam a diferença entre avaliador por exemplo e avaliador de resumo, que é conceitualmente importante: recall precisa de um denominador que nenhuma linha individual conhece. Há um teste novo cobrindo as duas formas, inclusive o caso de conjunto sem HIGH, em que a função devolve ausência de nota em vez de zero.

**Limite:** não publiquei um experimento remoto. A renderização na UI não está confirmada — ver capítulo 27.

### 3. Faltava o degrau entre ler um trace e operar um sistema — corrigido

Este era o maior buraco de conteúdo. O curso ensinava muito bem a investigar **uma** execução, e depois, no capítulo 22, projetava um painel inteiramente no papel. Entre “abra o span e veja 200 ms” e “escolha seus SLIs” não havia nenhum exercício de agregação. O capítulo 22 era o único capítulo sem laboratório, num curso cuja tese é “eu medi, encontrei, decidi”.

Isso também deixava sem prática uma habilidade concreta e muito perguntável: consultar runs. Nada no material tocava em `list_runs`, filtros, `is_root`, `trace_filter`/`tree_filter` — nem na linguagem de consulta que a barra de busca da UI usa.

**O que fiz:** [16_consultar_runs.py](labs/16_consultar_runs.py) e [runs.jsonl](dados/runs.jsonl), com três traces sintéticos e catorze runs. Sem flags, agrega a árvore local; com `--send`, aplica as mesmas medidas aos runs que o aluno já criou no próprio projeto, e imprime as consultas equivalentes.

O laboratório produz quatro respostas corretas e diferentes para “qual é a taxa de erro?”:

| Medida | Valor | Pergunta que responde |
|---|---:|---|
| `erro_por_pedido` | 0,3333 | 1 das 3 raízes falhou — o que o usuário sentiu |
| `erro_por_run` | 0,2143 | 3 dos 14 runs — o número que mais aparece em painéis e menos responde algo |
| `erro_por_tentativa_de_collect_deps` | 0,3333 | a dependência falha com frequência |
| `pedidos_em_que_collect_deps_nunca_obteve_resposta` | 0 | …e o retry está escondendo isso |

E, no trace com coletores concorrentes, a soma ingênua das durações dos filhos dá **exatamente** a duração da raiz — sugerindo que a orquestração é gratuita. A ocupação real é 1000 ms e sobram 200 ms de tempo próprio. A lição de paralelismo do capítulo 07 e a de dupla contagem do 09 deixam de ser advertências e viram aritmética que o aluno executa. Os percentis saem com `n` ao lado: `collect_asset` tem `n=1`, e ali p50 e p95 são a mesma observação.

Acrescentei também o desafio 11 no capítulo 25 e dois termos ao glossário.

### 4. Três métodos do SDK usados pelo curso estão obsoletos — documentado

A introspecção do `langsmith` 0.11.1 mostra avisos de depreciação em `Client.read_run`, `Client.get_run_url` e `Client.list_runs`, com remoção anunciada para depois de **31 de janeiro de 2027**.

Os dois primeiros são usados por [_common.py](labs/_common.py) na função que imprime a URL do trace — ou seja, no caminho que **todo** laboratório com `--send` percorre. O capítulo 27 dizia ter verificado “a presença dos métodos e parâmetros utilizados”, o que é verdade e insuficiente: presença não é suporte futuro.

**O que fiz:** documentei nos capítulos 22 e 27, com o substituto que o próprio SDK indica. **Não migrei**, e a razão está registrada: o namespace `Client.runs` é assíncrono e sua primeira leitura chama `_check_backend_version`, exigindo backend `0.16` ou superior em instalação própria. Trocar acrescentaria plumbing assíncrono e uma dependência de versão sem nenhum ganho didático. É uma decisão, não um descuido — e o aluno agora sabe dela, o que aliás é um bom assunto de entrevista.

### 5. Uma simulação apontava para um dataset onde o recorte não existe — corrigido

O capítulo 22 propunha a simulação “a qualidade caiu só em português” logo depois de o aluno ter passado dois dias com o benchmark de 16 casos. Só que `casos.jsonl` **não tem nenhum caso em português**. O slice `parafrase` são c15 e c16, ambos em inglês.

E não é um esquecimento que se conserte acrescentando casos: o parser fixture de [_dcra.py](labs/_dcra.py) só reconhece padrões em inglês, então um pedido em português cairia em `InterpretationError` em vez de medir interpretação. O slice `portugues` existe, com dois casos, em `interpretacao.jsonl` — o dataset do lab 07, que usa modelo real.

**O que fiz:** o capítulo 22 agora diz onde o recorte existe, onde não existe e por quê. A observação virou conteúdo: antes de investigar “o slice X piorou”, pergunte se o slice X existe naquele conjunto e com quantos casos.

## O que eu considerei e decidi não fazer

**Não acrescentei casos ao `casos.jsonl`.** Seria tentador cobrir português e ambiguidade. Mas 16 é um número memorizado em seis lugares — a tabela do capítulo 12, o gate, os gabaritos do 25, a demo do 24, o registro do 27 — e 13/16 = 81,25% é uma frase que o aluno vai dizer em voz alta. Trocar o denominador para ganhar dois casos custaria mais do que rende, e o exercício de propor casos novos já está no capítulo 11, onde faz mais sentido.

**Não adicionei laboratório de comparação em pares nem de juiz online executável.** Ambos exigem chamada de modelo e conta configurada. Escrever um caminho que não pude executar contra a promessa do capítulo 27 valeria menos que a honestidade que ele protege.

**Não migrei o SDK para `Client.runs.*`.** Explicado no item 4.

## O que ainda falta, se você quiser continuar

Nada disso é bloqueante para a entrevista. Em ordem de retorno:

1. **Dashboards nativos do LangSmith.** O capítulo 22 projeta um painel e agora agrega métricas por código, mas o produto tem gráficos próprios que o material nunca abre. É a lacuna mais visível que resta, e ela precisa de conta real para ser escrita honestamente.
2. **Integração de eval com pytest.** O capítulo 23 monta o gate lendo um relatório em JSON, o que é didático e transparente. O SDK tem uma integração com pytest que encaixaria no mesmo capítulo e é o que muitos times realmente usam em CI.
3. **Retenção, cobrança e exportação em massa.** Aparecem de passagem nos capítulos 10 e 18. Numa entrevista sobre operação, “quanto custa guardar isso e como tiro os dados daqui” é pergunta frequente.
4. **Um caso em que o juiz LLM erra e você percebe.** O capítulo 15 ensina calibração muito bem no procedimento, mas o aluno nunca vê uma discordância concreta sem chamar modelo. Seis anotações fixture com um juiz fixture deliberadamente enviesado dariam esse momento sem gastar nada.

## Como eu usaria este material

Se o prazo for de três dias, siga o roteiro como está agora — ele cobre os 25 capítulos práticos e cabe em 2h40 por sessão. Se for menos, a rota de 90 minutos preserva os argumentos mais demonstráveis, e eu acrescentaria só o lab 16: quatro taxas de erro corretas e incompatíveis é a coisa mais rápida de contar que demonstra maturidade real.

O que torna este curso incomum não é ensinar LangSmith. É treinar alguém a dizer “esse número não significa o que você acha que significa, e aqui está o porquê” — com um experimento aberto na tela para provar. Isso vale numa entrevista, e vale depois dela.

---

**Mudanças aplicadas nesta revisão**

| Arquivo | Mudança |
|---|---|
| [00-roteiro-3-dias.md](00-roteiro-3-dias.md) | Rota redistribuída; capítulos 08, 10, 16 e 22 incluídos; capítulo 20 marcado como opcional |
| [labs/_evaluators.py](labs/_evaluators.py) | `high_risk_recall_summary` e `SUMMARY_EVALUATORS` |
| [labs/06_evaluate.py](labs/06_evaluate.py) | Publica a métrica de conjunto no experimento remoto |
| [labs/16_consultar_runs.py](labs/16_consultar_runs.py) | Novo: agrega traces em métricas; `--send` consulta o projeto real |
| [dados/runs.jsonl](dados/runs.jsonl) | Novo: três traces sintéticos, catorze runs |
| [12](12-evals-deterministicos.md), [13](13-experimentos-comparacao.md) | Avaliador por exemplo versus avaliador de resumo |
| [22-operacao-slos-incidentes.md](22-operacao-slos-incidentes.md) | Laboratório novo, consultas e filtros, aviso de depreciação, correção do slice de português |
| [25-desafios-gabarito.md](25-desafios-gabarito.md) | Desafio 11, sobre denominadores e tempo próprio |
| [26-glossario.md](26-glossario.md) | *Self time* e *nearest-rank* |
| [27-fontes-e-validacao.md](27-fontes-e-validacao.md) | Números da validação, tabela de depreciações, o que ficou sem execução remota |
| [README.md](README.md) | Contagem de scripts e pergunta do bloco 22 |
| [tests/test_labs.py](tests/test_labs.py) | Dois testes novos (12 no total) |
| [verificar_material.py](verificar_material.py) | 26 comandos |

O código do produto em `src/` não foi tocado.
