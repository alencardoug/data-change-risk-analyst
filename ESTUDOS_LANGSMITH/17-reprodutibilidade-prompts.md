# 17 · Guardar a receita é diferente de reproduzir cada bolha do bolo

[Índice](README.md) · [Anterior](16-avaliar-workflow-agentes.md) · [Próximo](18-evals-online-producao.md)

**Objetivo:** registrar o suficiente para reconstruir condições e comparar resultados. Tempo: 25–35 minutos. Código: [00_doctor.py](labs/00_doctor.py), [13_prompts.py](labs/13_prompts.py).

Reprodutibilidade em sistemas com LLM tem níveis. Você pode reconstruir o que foi enviado, reexecutar o mesmo procedimento e observar resultados comparáveis sem garantir texto idêntico em todas as chamadas. Modelo hospedado, paralelismo, fontes externas e configuração influenciam o resultado.

`temperature=0` reduz uma fonte de variação; não transforma um serviço de modelo em função matemática imutável. Checkpoint recupera estado do workflow; não congela todos os serviços externos que uma próxima etapa consultará.

## Abra o manifesto

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/00_doctor.py
```

Abra `artefatos/manifesto.json`. Ele registra SHA do Git, indicador de árvore modificada, versão de Python/pacotes e hashes dos arquivos relevantes de código, dados e dependências. Não exporta `.env` nem valores das chaves.

O indicador de árvore modificada importa: “rodei o commit abc” pode ser enganoso se havia alterações locais. Hashes ajudam a identificar conteúdos, mas **não armazenam o conteúdo por si só**. Para reconstruir, guarde o código/dataset correspondente em controle de versão ou artefato apropriado.

## Laboratório: duas receitas e uma referência fixa

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/13_prompts.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/13_prompts.py --send
```

O primeiro compara prompts locais e hashes. O segundo cria um prompt privado de estudo com nome novo, publica v1 e v2 e recupera **v1 pelo hash do commit**, depois de v2 já existir.

Abra as URLs impressas na área **Prompts** do LangSmith. Compare as versões. Na v2, a instrução exige sinalizar lacunas e manter caráter de recomendação. O script não chama modelo: publicar uma receita não é provar que ela produz um bolo melhor.

Abra [13_prompts.py](labs/13_prompts.py): `push_prompt` publica, `pull_prompt_commit` obtém a identificação da revisão e `pull_prompt("nome:hash")` fixa uma revisão específica. O uso atual é pelo SDK `langsmith`, sem depender do antigo pacote `langchainhub`. [Gerenciamento programático de prompts](https://docs.langchain.com/langsmith/manage-prompts-programmatically).

Uma tag como `prod` ou `staging` pode mudar para outro commit. É útil para promoção, mas registre também o commit resolvido em cada execução. Pull de `latest` significa acompanhar o mais recente, não reproduzir uma versão fixa. [Versões, tags e ambientes de prompt](https://docs.langchain.com/langsmith/manage-prompts).

## Sua ficha de experimento

| Item | Por que registrar |
|---|---|
| Código + alterações locais | regras e adapters podem ter mudado |
| Versões de Python e SDKs | serialização/instrumentação/comportamento podem diferir |
| Prompt exato + commit/hash | nome amigável não identifica o conteúdo |
| Modelo e parâmetros efetivos | alias e defaults podem mudar |
| Dataset + snapshot | adicionar/remover caso muda a prova |
| Evidências/ferramentas + instante | catálogo e uso externos mudam |
| Avaliadores + rubricas | trocar a régua muda a nota |
| Repetições, concorrência, retries e cache | alteram variabilidade, tempo e custo |
| Outputs e IDs de runs/experimentos | permitem inspecionar o que realmente aconteceu |

O manifesto do curso cobre parte dessa ficha. Os traces e metadados do lab real cobrem outros itens. Um modelo identificado só por alias continua sujeito às limitações do provedor; não invente um snapshot que ele não oferece.

## Dois detalhes especialmente bons deste repositório

Em [risk.py](../src/dcra/rules/risk.py), os fatores e a categoria vêm de funções puras sobre a entrada, mas `RiskAssessment.assessed_at` recebe um timestamp novo. Compare a parte semântica se quiser verificar determinismo, não o objeto inteiro byte a byte.

Em [state.py](../src/dcra/graph/state.py), o reducer ordena e elimina duplicações por chave, com **first-write-wins**. Para itens diferentes, a ordenação estabiliza a lista. Para duas escritas conflitantes na mesma chave, o primeiro conteúdo prevalece: não declare que essa operação resolve conflitos de forma independente da ordem. Isso merece teste e política próprios se tal situação entrar no escopo.

**Conceito LangGraph:** estado recuperável e reducers. **Alternativa simples:** snapshots explícitos e composição sequencial. **Defesa:** persistência e ordenação ajudam, mas a afirmação de reprodutibilidade precisa especificar quais campos e dependências estão controlados.

**Memorize:** *provenance*, *immutable revision*, *snapshot*, *replay*, *repeatability*, *working tree dirty*.
