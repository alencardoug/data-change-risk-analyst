# 16 · A resposta final não conta tudo o que o agente fez

[Índice](README.md) · [Anterior](15-juiz-llm-calibracao.md) · [Próximo](17-reprodutibilidade-prompts.md)

**Objetivo:** avaliar processo, resultado e limites do workflow. Tempo: 25–35 minutos. Parte local; uma etapa opcional chama modelo.

Dois investigadores devolvem “evidência indisponível”. Um tentou as três fontes permitidas uma vez. O outro repetiu a mesma consulta até esgotar o limite. A resposta final pode ser parecida; custo, latência e qualidade do processo são diferentes.

Uma avaliação de agente pode observar o resultado final, componentes e trajetória de ferramentas. A documentação apresenta essas estratégias em [How to evaluate agents](https://docs.langchain.com/langsmith/evaluate-llm-application).

## Laboratório A — disparar a investigação de forma controlada

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case gap --send
```

O cenário desabilita a fonte `usage` no catálogo fixture. O grafo deve passar por `investigate`, mas a dependência de investigação falsa retorna `[]`. Abra o trace: você verá o nó, **sem um loop de modelo real**.

Agora, se quiser observar o agente com a configuração do projeto:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case gap --real --send
```

Abra `investigate`, expanda o agente e procure mensagens que solicitam ferramentas e seus resultados. Confira os nomes permitidos em [make_evidence_tools](../src/dcra/evidence/tools.py): `get_asset_metadata`, `get_dependencies` e `get_downstream_usage`.

O modelo decide o que chamar, então a sequência e o número de chamadas variam. Não prometa que todas as ferramentas serão usadas. A fonte foi desabilitada de propósito; consultar de novo não a conserta. Um `GraphRecursionError` ou outra falha neste modo é um resultado a inspecionar, não uma medição que deve ser omitida do relatório.

## Laboratório B — invariantes do processo

Rode os testes existentes com tracing desligado:

```bash
.venv/bin/python -m pytest tests/unit/test_routing.py tests/e2e/test_us2_approve_reject.py tests/e2e/test_us3_revision_limit.py -q
```

Abra esses arquivos e identifique o que é verificado. Em uma avaliação mais ampla, organize critérios assim:

| Tipo | Exemplo de critério | Método adequado |
|---|---|---|
| Contrato | operação tem coluna/índice válido | schema e código |
| Roteamento | HIGH/MEDIUM chega à revisão | execução do grafo com fixtures |
| Ferramentas | só ferramentas permitidas e argumentos coerentes | inspeção de chamadas estruturadas |
| Término | loop respeita mecanismo de limite | teste de trajetória e exceção prevista |
| Evidência | investigador acrescentou fato válido e útil | comparação de evidências antes/depois |
| Resultado | recomendação é sustentada e não vinculante | regras, humano ou juiz calibrado |
| Eficiência | custo/latência compatíveis com benefício | spans de uso + resultado por caso |

## Não imponha uma coreografia sem necessidade

Exigir a sequência exata `[asset, dependencies, usage]` pode reprovar uma execução válida que usou outra ordem de leituras independentes. Avalie a propriedade de que precisa: fontes exigidas foram consultadas, argumentos eram corretos, nenhuma ação proibida ocorreu, evidência foi adequadamente usada.

Uma sequência exata faz sentido quando a ordem é parte da correção, como revisar antes de finalizar ou obter autorização antes de um efeito externo. A rubrica de trajetória precisa distinguir dependência real de preferência estética.

No projeto, `recursion_limit=8` é uma guarda de passos do agente, e o grafo externo usa outro limite. A quantidade de passos não é igual ao número de ações de negócio nem define sozinha um teto de gasto.

## Experimento mental: qual nível de avaliação detecta cada problema?

- Interpretação erra a coluna: eval do componente de interpretação.
- Regras erram HIGH: teste da política com evidência conhecida.
- Recomendação inventa uma view: eval de sustentação em evidências.
- UI exibe LOW para um estado HIGH: eval do contrato de saída/integração, como a mutação do lab 06.
- Agente repete uma busca inútil: análise de trajetória e custo.
- Revisor humano foi ignorado: invariante de workflow e auditoria.

**Conceito LangGraph/LangChain:** orquestração explícita ao redor de um agente limitado. **Utilidade:** restringir onde existe autonomia e testar as fronteiras. **Alternativa simples:** uma coleta determinística adicional. **Defesa:** use agente apenas quando a flexibilidade de buscar evidência justificar custo e variabilidade; não declare benefício sem comparar com essa alternativa.

**Memorize:** *trajectory evaluation*, *tool selection*, *argument correctness*, *termination*, *end-to-end evaluation*.

## Levar para outros projetos — e onde o seu julgamento decide

A resposta final não conta o processo: **trajetória, ferramentas, término e custo** precisam de critérios próprios, e "avaliar a propriedade, não a coreografia" evita reprovar execuções válidas.

**Na plataforma de atendimento (Langfuse Cloud).** Não há um agente com loop de ferramentas, mas há um **workflow com decisões encadeadas** que merece a mesma tabela de critérios: *contrato* (a resposta tem o formato do caminho — oferta com ID, data válida); *roteamento* (`mechanism` e `n5_path` corretos para o caso — governado N3/N4 avaliado antes de N5; fallback livre só quando `status != ANSWER` ou atalho clínico fraco); *ferramentas* (o resolvedor de agenda foi consultado quando o pedido era de agendamento; `price_lookup` quando era preço); *término* (a pendência foi resolvida — `SENT`/`PAUSED`/`EDITED`/`TAKEN_OVER` — e não ficou sem desfecho por perda de telemetria); *evidência* (o `rag.retrieve` trouxe o documento certo, em que rank); *resultado* (rubrica); *eficiência* (duas gerações num turno de fallback; embedding por turno). "Atividade ≠ benefício" tem tradução direta: `n5.fallback_started = 1` mede que o fallback rodou, não que ajudou — a média dá frequência de fallback, e só a rubrica diz se o fallback foi útil. E a advertência sobre coreografia: exigir que o guided booking sempre passe por `extract_date_intent` antes de `interpret_slot_choice` reprovaria um caso legítimo em que o cliente já escolheu "a segunda". A ordem só é critério quando é parte da correção — e "autorização antes de efeito externo" é: em N5, nada é enviado antes de `resolves_at`.

**Em projetos comuns do ecossistema.** Para agentes com ferramentas (LangGraph `create_agent`, ReAct, tool calling direto): registre a lista de chamadas com argumentos, avalie *conjunto e argumentos* (fontes exigidas consultadas, argumentos coerentes, nenhuma ação proibida) em vez de sequência exata, teste o limite de passos como comportamento previsto, e meça evidência nova antes/depois. Um `GraphRecursionError` é resultado a reportar, não a omitir. Em Langfuse, cada chamada de ferramenta é um span filho da generation que a pediu; em LangSmith, um run de tipo `tool` — mas só a mensagem de tool call prova que o modelo *decidiu* chamar.

**O fator humano — onde a IA faz e onde você decide.** Um assistente propõe critérios de trajetória completos — e é aqui que ele mais frequentemente impõe coreografia: "a sequência esperada é [asset, dependencies, usage]", porque é a que viu no código. Decidir **qual propriedade importa** — ordem, conjunto, ausência de ação proibida — exige entender o que é dependência real e o que é preferência estética, e isso é conhecimento do domínio. Foque no experimento mental do capítulo: para cada tipo de problema, qual nível de avaliação o detecta? Fazer essa tabela para o seu sistema é o exercício de maior valor, porque ele revela onde não há avaliação nenhuma. Na plataforma, "revisor humano foi ignorado" tem a versão "mensagem enviada antes de `resolves_at`" — um invariante que nenhum juiz de texto detecta, e que você precisa saber que existe para pedir o teste. Por fim, a defesa do agente: "use agente só quando a flexibilidade justificar custo e variabilidade" é uma decisão de arquitetura sua. A IA, perguntada, tende a sugerir mais autonomia; a plataforma segurou RAGFlow, LangChain e LangGraph até o diagnóstico da Fase 0 justamente por uma decisão humana de não adicionar complexidade antes de saber onde dói.
