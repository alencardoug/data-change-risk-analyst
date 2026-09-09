# 15 · Quem corrige a prova do corretor?

[Índice](README.md) · [Anterior](14-modelo-real-saida-estruturada.md) · [Próximo](16-avaliar-workflow-agentes.md)

**Objetivo:** usar um juiz LLM como instrumento calibrável. Tempo: 30–40 minutos. Código: [08_judge.py](labs/08_judge.py). Casos: [juiz.json](dados/juiz.json).

Comparar `risk == "HIGH"` é tarefa boa para código. Julgar se uma recomendação inventou consumidores ou comunicou uma lacuna pode exigir análise semântica. Um LLM pode ajudar a escalar essa análise, mas sua nota continua sendo uma previsão do avaliador, não a verdade revelada em JSON.

## Faça a prova primeiro

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/08_judge.py
```

O comando mostra seis respostas e as anotações manuais do material. Antes de olhar a anotação, julgue:

1. Todas as afirmações factuais estão sustentadas pela evidência? `grounded`.
2. A resposta mantém caráter de recomendação, sem alegar que aprovou/executou a mudança? `non_binding`.

Exemplo: “Não existe consumidor ativo”, quando a evidência mostra quatro leituras/dia, é não sustentado. “Não consegui verificar uso; recomendo obter evidência” pode ser uma resposta sustentada diante de indisponibilidade.

Uma resposta que diz “já executei a remoção” falha no caráter não vinculante e alega um fato sem sustentação. Critérios podem se correlacionar; ainda vale mantê-los separados porque explicam o tipo de problema.

## Execute o juiz

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/08_judge.py --real --limit 3
.venv/bin/python ESTUDOS_LANGSMITH/labs/08_judge.py --real --send --limit 6 --project dcra-estudos-juizes
```

O segundo comando cria traces em projeto próprio para facilitar a leitura do custo de avaliação. O juiz recebe **evidência e resposta candidata**. A anotação humana de referência fica fora do prompt do juiz e é usada depois para medir concordância.

Abra `juiz-recomendacao` e o filho de modelo. Leia a rubrica `RUBRIC` no código; depois examine `grounded`, `non_binding` e `reason` no retorno. A razão deve apontar a afirmação relevante, não apenas dizer “parece bom”.

O resumo calcula concordância conjunta nos dois critérios sobre as avaliações válidas e informa `n_valid/n_total`. Uma falha de API/parser produz `judge_error` e ausência de nota; não ganha automaticamente zero ou um. Medir também a falha do medidor impede uma taxa de qualidade enganosa.

## Casos que cutucam o juiz

| Caso | O que testa |
|---|---|
| j01 | recomendação curta sustentada |
| j02 | negação contraditória de uso ativo |
| j03 | alegação de aprovação/execução sem evidência |
| j04 | reconhecimento correto de informação indisponível |
| j05 | candidato tenta instruir o juiz a dar uma nota |
| j06 | versão prolixa de uma recomendação sustentada |

O j05 é um pequeno teste de injeção na avaliação. A rubrica instrui o juiz a tratar o candidato como dado, mas isso é uma mitigação que precisa ser testada; não torna o avaliador invulnerável.

## Como calibrar em um trabalho real

Use um conjunto revisado por pessoas com conhecimento do domínio. Inclua positivos, negativos e casos difíceis. Compare notas por critério, inspecione discordâncias e mantenha uma versão da rubrica. Acrescente exemplos de fronteira quando a regra estiver ambígua.

Separe erros do candidato, erros do juiz e ambiguidade do gabarito. Às vezes a divergência mostra que “acionável” não estava definido de forma suficiente. Resolver isso é trabalho de avaliação, não “consertar o juiz até concordar comigo em tudo”.

Para comparação em pares, alterne a ordem A/B e oculte o nome do modelo quando possível. Isso ajuda a investigar vieses de posição, preferência por texto longo e sinais irrelevantes de autoridade. Avaliadores por referência, sem referência e em pares têm usos diferentes. [LLM-as-judge e avaliação em pares](https://docs.langchain.com/langsmith/evaluation-concepts).

Usar outro modelo pode trazer independência parcial, mas não garante eliminação de vieses. Mesmo modelo e mesma família podem compartilhar pontos cegos; um modelo diferente também pode ter os seus. A defesa sólida é a calibração observada na tarefa.

Seis casos são uma demonstração de procedimento, não uma validação estatística do juiz. O curso não pré-inventa o resultado da chamada real.

**Memorize:** *LLM-as-a-judge*, *groundedness*, *rubric calibration*, *position bias*, *judge failure*, *reference-free evaluation*.
