# 14 · JSON bonito ainda pode apontar para a coluna errada

[Índice](README.md) · [Anterior](13-experimentos-comparacao.md) · [Próximo](15-juiz-llm-calibracao.md)

**Objetivo:** avaliar interpretação real sem exigir que toda a aplicação esteja no ar. Tempo: 25–35 minutos. Código: [07_real_model.py](labs/07_real_model.py). Dados: [interpretacao.jsonl](dados/interpretacao.jsonl).

No DCRA, `StructuredChange` define quais campos a interpretação deve produzir. Validação de schema pode exigir `target_column` para DROP_COLUMN e `index_columns` para ADD_INDEX. Ela não sabe sozinha se o modelo copiou o identificador certo do pedido.

Um resultado com `target_column="customer_id"` pode passar no Pydantic e estar errado para “remova customer_legacy_id”. **Validade estrutural é necessária, mas não substitui fidelidade semântica.**

## Ensaio, depois uma execução pequena

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/07_real_model.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/07_real_model.py --real --limit 3
```

O primeiro não chama modelo. O segundo chama o provedor configurado e salva resultados localmente, com tracing desativado. Observe os casos selecionados: um DROP em inglês, um em português e um índice.

Para comparar dois prompts no LangSmith:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/07_real_model.py --real --send --limit 3 --variant both
```

São seis execuções planejadas de target, antes de retries. Abra o dataset `dcra-estudo-interpretacao-<hash>` e compare experimentos `interpretacao-baseline` e `interpretacao-candidate`.

## O que cada variante faz

**Baseline:** usa `interpret(model, text)` e o prompt do produto em [factory.py](../src/dcra/llm/factory.py), incluindo sua tentativa adicional de validação.

**Candidate:** usa um prompt próprio do estudo, com instruções explícitas sobre português, fidelidade de identificadores e ordem de colunas. Usa `with_structured_output(StructuredChange)` diretamente, sem a mesma camada adicional de retry de parsing.

Portanto esta primeira comparação tem uma diferença de prompt **e de política de retry na aplicação**. Ela serve para inspecionar as duas configurações, mas não permite atribuir uma diferença de custo/qualidade apenas ao texto do prompt. Para um experimento causal focado no prompt, iguale a política de retries no adaptador de estudo antes de ampliar o benchmark.

## Leia a nota

`exact_structure` compara:

- `operation`;
- `target_table`;
- `target_column`;
- `index_columns`, preservando a ordem.

Ela não compara literalmente `alter_detail`, que é texto livre, nem usa a confiança declarada pelo modelo como prova de acerto. O dataset também não valida se o schema físico existe: esse trabalho pertence à coleta de evidência e às regras.

Abra [models.py](../src/dcra/domain/models.py) e veja `_check_shape`. Depois compare com o avaliador. O primeiro valida forma e combinações permitidas; o segundo compara a extração ao gabarito do pedido.

No trace, abra o filho de modelo. Veja a mensagem enviada, a resposta estruturada e dados de uso quando disponíveis. Em algumas integrações, o caminho passa por tool calling/parser, em outras por schema nativo; observe o formato efetivamente emitido, sem inferir a implementação só do nome `with_structured_output`. [Structured output no LangChain](https://docs.langchain.com/oss/python/langchain/structured-output).

## Amplie com uma pergunta clara

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/07_real_model.py --real --send --limit 8 --repetitions 2 --variant both
```

Execute somente quando a rodada pequena estiver funcionando e você tiver decidido ampliar o gasto: são 32 execuções de target. Procure especialmente o índice composto: inverter `customer_id, status` muda o contrato, mesmo que ambas as colunas apareçam.

O resultado do modelo **não tem gabarito de taxa de sucesso prometida neste curso**. Registre falhas reais e formule uma hipótese. Se todos passarem, isso não prova que a candidata melhorou; talvez o benchmark ainda seja fácil demais para distingui-las.

**Conceito LangChain:** interface de modelo e saída estruturada. **Utilidade:** receber objetos validados e trocar a geração por um adaptador de teste. **Alternativa:** cliente do provedor + parsing/validação próprios. **Defesa:** schema reduz falhas de formato; evals medem se a estrutura corresponde ao pedido.

**Memorize:** *schema validity*, *semantic correctness*, *component evaluation*, *retry policy*, *controlled comparison*.
