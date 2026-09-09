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

Executar um avaliador online pode elevar o trace à retenção estendida e mudar sua cobrança. A regra pode continuar ativa depois de uma aplicação retroativa a runs anteriores. Faça a demonstração pequena e entenda o efeito persistente antes de ampliar.

## Um limite conceitual

Se o score de groundedness cair, você observou um sinal. Ainda precisa saber se mudou o tráfego, o modelo, as evidências ou o próprio juiz. Monitore cobertura e falhas do avaliador junto com as notas. “Não há notas ruins” pode significar “o avaliador parou de executar”.

**Memorize:** *online evaluation*, *reference-free criterion*, *feedback loop*, *evaluation coverage*, *evaluator spend limit*.
