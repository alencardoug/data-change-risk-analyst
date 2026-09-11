# 18 · A produção encontra perguntas que seu dataset esqueceu

[Índice](README.md) · [Anterior](17-reprodutibilidade-prompts.md) · [Próximo](19-privacidade-amostragem.md)

**Objetivo:** desenhar um ciclo contínuo de qualidade e configurar uma regra de estudo na UI. Tempo: 25–35 minutos. Esta capacidade não está implantada no DCRA.

Uma avaliação offline pergunta: “como esta versão se sai nesta coleção de casos?”. Uma avaliação online observa execuções do tráfego e pergunta: “estão ocorrendo padrões de qualidade que precisam de atenção?”. Online pode ser assíncrona depois da resposta; não significa que um juiz precisa aumentar o tempo de cada requisição.

O tráfego geralmente não vem com gabarito pronto. Use critérios verificáveis no próprio contexto, como contrato, reconhecimento de lacuna e sustentação em evidências. Para saber se o objetivo real do usuário foi alcançado, talvez seja necessário feedback posterior ou um evento de negócio.

## Primeiro desenho: um loop de aprendizagem

```text
trace com falha ou baixa nota
  → triagem humana
  → caso sanitizado + critério/referência revisados
  → dataset versionado
  → experimento comparando correção e baseline
  → decisão de promoção
  → observação da versão seguinte
```

Na demo do DCRA, isso seria: detectar recomendação que afirma ausência de uso apesar de `UNAVAILABLE`; revisar o caso; criar um exemplo que exige explicitar a lacuna; avaliar uma correção de prompt; monitorar se esse erro diminuiu.

## Prática pequena pela UI

Use somente o projeto de estudo. Se quiser um exemplo puramente de código, a [documentação de online code evaluators](https://docs.langchain.com/langsmith/online-evaluations-code) descreve a configuração disponível. Para praticar um juiz gerenciado:

1. Gere um ou dois traces com `02_dcra.py --case medium --real --send`.
2. Abra [LangSmith](https://smith.langchain.com) → **Tracing** → `dcra-estudos` → **Evaluators**.
3. Escolha adicionar um avaliador, criar do zero e usar LLM-as-a-judge, ou o fluxo equivalente disponível na conta.
4. Dê um nome como `recomendacao-nao-vinculante-estudo`.
5. Filtre pelo tipo/nome de run que contenha a recomendação. Pré-visualize os runs selecionados. Não avalie todo nó do grafo indiscriminadamente.
6. Mapeie as variáveis do avaliador aos campos reais de entrada/saída vistos no trace. Se o root contém um estado com `recommendations`, escolha a última recomendação; se avaliar o filho correspondente, use seu formato específico.
7. Defina a rubrica: “a saída apresenta conselho ou afirma que aprovou/executou a mudança?”. Use os exemplos do capítulo 15 como referência de interpretação.
8. Configure modelo/credenciais pelo mecanismo de secrets oferecido pela UI. A chave no `.env` local não é automaticamente transferida para uma execução gerenciada no servidor.
9. Restrinja o escopo e confira os controles de gasto disponíveis. Ative para a pequena demonstração; gere um novo caso; veja o feedback e os logs do avaliador.
10. Depois de observar o resultado, desative a regra de estudo se não quiser novas avaliações nos próximos labs.

A navegação, filtros, sampling e limites estão descritos no [guia atual de juízes online](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge). Disponibilidade e administração podem variar por conta. Se a UI não oferecer a opção, desenhe a configuração no caderno e use o juiz via SDK do lab 08 para praticar a rubrica.

## Quatro controles que não são intercambiáveis

| Controle | O que limita |
|---|---|
| Sampling de tracing | quais traces são enviados/registrados |
| Filtro de avaliador | quais runs são elegíveis à avaliação |
| Sampling de avaliador | fração dos elegíveis que será avaliada |
| Spend limit de avaliador | gasto do avaliador gerenciado no escopo configurado |

A documentação atual oferece limites semanais de gasto para avaliadores anexados a projetos/datasets, com comportamento de pausa ao alcançar o limite. Isso **não é um teto de gasto do LLM da sua aplicação**, nem controla automaticamente o loop Python do lab 08. Confira o escopo efetivo mostrado na sua conta.

Um avaliador online eleva o trace à retenção estendida **se a opção de retenção do avaliador estiver ligada** — é uma configuração, e o upgrade é cobrado como evento à parte. Confira essa opção ao criar a regra e registre-a no caderno. A regra pode continuar ativa depois de uma aplicação retroativa a runs anteriores. Faça a demonstração pequena e entenda o efeito persistente antes de ampliar; o [capítulo 22](22-operacao-slos-incidentes.md) separa os ciclos de retenção por tipo de dado e estima o efeito no custo.

## Um limite conceitual

Se o score de groundedness cair, você observou um sinal. Ainda precisa saber se mudou o tráfego, o modelo, as evidências ou o próprio juiz. Monitore cobertura e falhas do avaliador junto com as notas. “Não há notas ruins” pode significar “o avaliador parou de executar”.

**Memorize:** *online evaluation*, *reference-free criterion*, *feedback loop*, *evaluation coverage*, *evaluator spend limit*.

## Levar para outros projetos — e onde o seu julgamento decide

O ciclo **tráfego → triagem → caso → dataset → experimento → promoção → observação** é a única forma de o sistema aprender com o que o dataset esqueceu — e cada seta dele tem um passo humano.

**Na plataforma de atendimento (Langfuse Cloud).** O ciclo já está desenhado no `playbook_diagnostico.md` (conversa observada → problema e evidência → caso de avaliação → uma mudança candidata → comparação → decisão e verificação) e a "rotina depois da Fase 0" é a triagem: cinco conversas novas por período, registrar o problema recorrente mais relevante, adicionar aos casos, decidir o próximo experimento — **triagem só; implementar e avaliar exige tempo à parte**. Os critérios *reference-free* daquele domínio, verificáveis no próprio contexto: a resposta cita um preço/data — ele bate com a referência recuperada no `rag.retrieve` do mesmo trace? O cliente forneceu um dado no turno anterior — ele consta nas `messages` enviadas ao provider? O caminho foi fallback livre — havia documento com score alto que foi ignorado? Nenhum precisa de gabarito humano por conversa. No Langfuse, isso vira um *evaluator* gerenciado (LLM-as-a-judge sobre traces, com filtro por nome de observação e sampling) ou um job seu lendo traces pela API e publicando scores — o plano prefere começar pelo segundo, sob controle. Os quatro controles não intercambiáveis existem lá com outros nomes: `sample_rate` do SDK (quais traces são enviados — o adaptador usa 1,0); filtro do evaluator (quais observações); sampling do evaluator; e o limite de gasto, que no Langfuse é o do **seu** provedor de LLM configurado para o juiz — não há teto separado por avaliador como no LangSmith; confira na conta. A advertência "não avalie todo nó indiscriminadamente" é literal ali: avalie `n5.process_turn` ou a generation final, não `ai.embedding`.

**Em projetos comuns do ecossistema.** Online ≠ síncrono: o juiz roda depois, sobre a amostra, sem entrar na latência do usuário. Monitore **cobertura e falhas do avaliador junto com as notas** — "não há notas ruins" pode ser "o avaliador parou". E antes de ligar uma regra, saiba o efeito persistente: retenção estendida (LangSmith), custo do juiz por trace, e que a regra pode continuar ativa depois de uma aplicação retroativa. Ligue pequeno, desligue depois de ver, religue com escopo.

**O fator humano — onde a IA faz e onde você decide.** A IA pode fazer quase todo o ciclo sozinha — detectar nota baixa, propor caso, gerar correção, rodar experimento, e "recomendar promoção". É exatamente por isso que as duas setas humanas importam mais aqui do que em qualquer outro capítulo: a **triagem** (este trace é um problema real ou um falso positivo do juiz? é frequente? é grave?) e a **promoção** (esta versão vai para os pacientes?). Se você automatizar as duas, construiu um sistema que se ajusta às opiniões do próprio juiz — e o capítulo 15 mostrou o que um juiz aceita. Foque em: (1) fazer a triagem você mesmo, em lote curto e regular (as cinco conversas do playbook), com a ficha de caso preenchida; (2) exigir que toda promoção passe pela comparação do capítulo 13, com a sua leitura das linhas que pioraram; (3) quando um score cair, perguntar primeiro "mudou o tráfego, o modelo, as evidências ou o juiz?" — a IA vai propor uma correção de prompt antes de responder isso. Na plataforma, o plano diz "E4 só faz sentido quando a camada 2 mostrar casos suficientes para haver o que triar" — a decisão de **quando** ligar avaliação online é sua, e é uma decisão sobre volume e responsabilidade, não sobre ferramenta.
