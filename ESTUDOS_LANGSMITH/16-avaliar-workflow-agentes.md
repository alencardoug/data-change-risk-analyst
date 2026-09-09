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
