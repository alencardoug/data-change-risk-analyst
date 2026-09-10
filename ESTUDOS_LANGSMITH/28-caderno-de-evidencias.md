# 28 · Meu caderno de evidências

[Índice](README.md) · [Anterior](27-fontes-e-validacao.md) · [Roteiro de três dias](00-roteiro-3-dias.md)

Este é um modelo para suas anotações. Copie as seções que precisar para um arquivo pessoal, por exemplo `ESTUDOS_LANGSMITH/artefatos/meu-caderno.md`. A pasta `artefatos/` é ignorada pelo Git. Use um nome próprio: os laboratórios sobrescrevem seus JSONs de nomes fixos quando são reexecutados.

Mantenha separados **resultado esperado**, **resultado que observei** e **conclusão que ele permite**. IDs e links abaixo começam vazios; preencha somente depois de executar. Registre ausência de envio/modelo como parte do método.

## Minha configuração

| Campo | Preencher |
|---|---|
| Data e horário, com fuso | |
| Objetivo da sessão | |
| Commit do código e alterações locais | |
| Arquivo de manifesto preservado | |
| Python / LangSmith / LangChain / LangGraph | |
| Modo | local com fixtures / envio ao LangSmith / modelo real / modelo real com envio |
| Workspace, projeto e região, se houve envio | |
| Modelo e parâmetros efetivos, se houve chamada real | |
| Dataset/snapshot e versão dos avaliadores | |
| Limite de exemplos, repetições e orçamento planejado | |

Execute `00_doctor.py` para produzir `artefatos/manifesto.json`. A presença de chave no diagnóstico não comprova autenticação. Registre nomes de configuração e versões; valores de chaves e conteúdo do `.env` não pertencem ao caderno.

## Uma ficha por experimento

```text
Título:
Data/hora/fuso:

Hipótese — o que pensei que aconteceria:
Critério de aceitação definido antes de executar:
Modo de execução e dependências reais/fixture:
Comando exato:
Código, dados, prompt/modelo e avaliador utilizados:

O que observei:
População, numerador/denominador e falhas de execução:
Arquivo de resultado preservado:
thread_id, se aplicável:
run_ids / URLs autenticadas, se enviados:
Dataset/experimento remoto, se criado:

O que a evidência permite concluir:
O que ainda não sei:
Decisão e próximo experimento que resolveria essa dúvida:
Minha explicação em até um minuto:
```

Se a API falhar, registre a falha e a ausência de resultado. Se não abriu o trace, escreva “envio solicitado; ingestão ainda não conferida”. Um UUID gerado pelo script local não comprova que exista um run na conta.

## Dia 1 — consigo explicar o caminho?

| Atividade | Evidência a registrar | Minha observação |
|---|---|---|
| Primeiro trace | R$36; funções filhas; URL somente se enviado | |
| LOW / MEDIUM / HIGH | Categoria, fatores e presença/ausência de pausa por caso | |
| Aprovação | Mesmo `thread_id` entre fases; `run_id` distinto; resultado `APPROVED` | |
| Devolução com e sem evidência | Versões da recomendação, passagens de risco e nós executados | |
| Falhas | Tentativas, disponibilidade da fonte, recuperação/degradação | |

Minha explicação de checkpoint versus trace:

Minha dúvida principal antes do dia 2:

## Dia 2 — consigo avaliar uma mudança?

| Medida | Baseline observada | Candidata observada | Casos que explicam a diferença |
|---|---|---|---|
| `risk_correct` | | | |
| `review_correct` | | | |
| `factors_exact` | | | |
| `error_contract` | | | |
| `high_risk_recall` | | | |
| Exemplos esperados / executados / falhos | | | |

Decisão segundo o gate e exit code observado:

Se executei o modelo real: quantidade de exemplos/repetições, `structure_exact`, erros e IDs dos resultados:

Se executei o juiz real: rubrica, concordância entre avaliações válidas, `n_valid/n_total`, discordância que examinei:

Se não executei essas etapas reais, o que pratiquei no ensaio:

Conta de custo que refiz à mão, com indicação de preços fictícios ou fonte/data de preços reais:

## Dia 3 — consigo defender a decisão?

| Atividade | Evidência a registrar | Minha conclusão |
|---|---|---|
| Prompts | Hashes locais; commits apenas se publicados | |
| Reprodução | Código/dados correspondem ao manifesto do resultado? | |
| RAG | Falha de recuperação versus resposta sem apoio no contexto | |
| Langfuse / OpenTelemetry | Leitura, ensaio ou execução remota efetivamente realizada | |
| Gate | Baseline aceita; mutação recusada; motivo e exit code | |
| Desafios | Número, hipótese original e correção depois do gabarito | |

Para cada resposta do [capítulo 24](24-entrevista-simulada.md), marque de 0 a 4: um ponto por conceito correto, evidência, trade-off e limite da conclusão.

| Pergunta | Pontos | Trecho a regravar ou evidência a localizar |
|---|---|---|
| Papel de cada ferramenta | | |
| Trace e qualidade | | |
| Pausa e retomada | | |
| Detecção de regressão | | |
| Custo e orçamento | | |
| Calibração do juiz | | |

## Exemplo preenchido — referência para comparar com sua execução

Este exemplo descreve o comportamento determinístico do lab 06. Ele não marca nenhuma atividade como realizada por você e não contém um experimento remoto.

**Hipótese:** uma média de acerto pode esconder a perda de detecção de casos críticos.

**Execução de referência:** `06_evaluate.py` e `12_regression_gate.py --candidate bug`, em modo local, com grafo real, dependências fixture e 16 casos de referência.

**Observação esperada:** baseline com 16/16 categorias corretas; candidata com 13/16. Os três HIGH viram LOW, portanto recall HIGH 0/3. O gate da candidata termina com exit code 1.

**Conclusão permitida:** a mutação viola os critérios de risco/revisão do exercício e deve ser recusada. Avaliar por recorte crítico revela o impacto que a média isolada esconde.

**Limite:** não houve modelo real nem medida de qualidade linguística, custo de provedor ou tráfego de produção. Os resultados locais ficam em `artefatos/06-baseline.json` e `artefatos/06-bug.json` depois da execução.

**Próxima pergunta:** o componente de interpretação real extrai corretamente operações e identificadores nos pedidos em português? O capítulo [14](14-modelo-real-saida-estruturada.md) prepara uma avaliação específica para isso.
