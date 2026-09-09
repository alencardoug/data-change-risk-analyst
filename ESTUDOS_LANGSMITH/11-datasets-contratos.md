# 11 · Monte a prova antes de escolher o vencedor

[Índice](README.md) · [Anterior](10-feedback-anotacao.md) · [Próximo](12-evals-deterministicos.md)

**Objetivo:** entender dataset, example, referência, slice e versão. Tempo: 25 minutos. Arquivo: [casos.jsonl](dados/casos.jsonl). Script: [05_dataset.py](labs/05_dataset.py).

Uma prova em que você inventa as perguntas depois de ver quem quer aprovar não mede muito. Uma avaliação também precisa de casos e critérios definidos com cuidado, antes de escolher a configuração vencedora.

## Abra uma linha do dataset

```json
{
  "id": "c03",
  "inputs": {"text": "drop column orders.id"},
  "outputs": {
    "risk": "HIGH",
    "awaiting_review": true,
    "factors": ["ACTIVELY_READ", "INBOUND_FOREIGN_KEY", "IN_PRIMARY_KEY"]
  },
  "metadata": {"slice": "critico", "difficulty": "easy"}
}
```

Aqui, `outputs` no arquivo são **referências esperadas**, escritas à mão para o catálogo fixture e a política do projeto. O target recebe apenas `inputs`. Os outputs efetivos só existem depois que ele executa. Essa separação é parte do modelo de avaliação de [datasets e exemplos](https://docs.langchain.com/langsmith/evaluation-concepts).

O campo `id` é uma identificação local legível; o script gera UUIDs estáveis para os exemplos remotos. `metadata.slice` permite analisar grupos como críticos, indisponibilidade, paráfrases e índices. Não é um fato passado ao grafo para escolher a resposta.

## Examine três tipos de caso

1. **c03 — falha com consequência grave:** classificar HIGH como LOW tiraria a revisão humana.
2. **c12 — fonte indisponível:** não confundir “não consegui verificar uso” com “nenhum uso”.
3. **c14 — pedido não reconhecido pela fixture:** espera erro definido, sem risco inventado e sem portão de revisão.

O c14 testa o contrato do parser didático. Ele não prova que o modelo real rejeitaria o mesmo texto: a implementação real e suas validações precisam de avaliação própria.

Os 16 casos foram escolhidos para cobrir caminhos e distinguir erros. Eles não são amostra aleatória do tráfego real. Por isso, 100% nesse conjunto é evidência de consistência com esse pequeno benchmark, não uma estimativa de precisão universal.

## Execute, depois publique

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/05_dataset.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/05_dataset.py --send
```

O primeiro comando mostra o formato. O segundo cria/reutiliza um dataset `dcra-estudo-contratos-<hash>`. Abra [LangSmith](https://smith.langchain.com) → **Datasets & Experiments** e procure o nome impresso. Na lista de exemplos, compare inputs, referência e metadata com o arquivo local.

O nome incorpora hash do conteúdo do arquivo; IDs por caso são estáveis para essa versão. Rerodar o comando não cria cópias duplicadas dos mesmos casos. O script confere exemplos existentes e recusa misturar conteúdo remoto alterado ou casos extras.

O snapshot remoto é registrado em `artefatos/05-dataset.json`, no campo `as_of`. Os experimentos usam a mesma referência temporal para comparar versões. A plataforma mantém versões de datasets; você também pode usar tags e consultas `list_examples(as_of=...)`. [Gerenciamento programático de datasets](https://docs.langchain.com/langsmith/manage-datasets-programmatically).

## Slice não é necessariamente conjunto de validação

“Crítico”, “português” e “entrada longa” são recortes de análise que podem se sobrepor. “Desenvolvimento”, “validação” e “teste final” são papéis no processo de ajuste. Manter o teste final separado reduz a chance de adaptar prompts ao gabarito e confundir memorização com generalização.

Neste curso os arquivos são pequenos e abertos para ensinar. Não alegue que o resultado dos 16 exemplos é uma avaliação cega. Depois de ajustar a solução, crie casos novos e revise as referências sem escolher apenas os fáceis.

## Exercício de projeto de benchmark

Proponha cinco casos adicionais, sem ainda tocar no produto:

- uma paráfrase em português;
- uma operação ambígua que exige esclarecimento;
- indisponibilidade de uma fonte crítica;
- duas evidências conflitantes;
- um caso raro de custo elevado com várias revisões.

Para cada um, escreva o que seria aceitável. Se não consegue estabelecer a referência, talvez esteja descobrindo uma decisão de produto pendente — o que é útil, mas não se resolve dando nota arbitrária.

**Memorize:** *dataset*, *example*, *reference output*, *slice*, *holdout*, *dataset version*, *data leakage*.
