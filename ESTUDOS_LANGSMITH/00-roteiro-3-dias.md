# 00 · Um roteiro que cabe antes da entrevista

[Índice](README.md) · [Próximo: mapa do projeto](01-mapa-do-projeto.md)

**Seu prazo: até três dias.** Reserve idealmente três sessões de 2–3 horas. Em cada uma, alterne vinte minutos de leitura/prática e cinco de explicação em voz alta. Uma explicação que só funciona quando o arquivo está aberto ainda precisa de treino.

## Dia 1 — enxergar a execução

| Tempo | Faça | Evidência que deve guardar |
|---|---|---|
| 20 min | Leia [01](01-mapa-do-projeto.md) e [02](02-fundamentos-observabilidade.md) | Um desenho separando aplicação, checkpoint e observabilidade |
| 25 min | Prepare o ambiente em [03](03-preparacao.md); execute o lab 01 em [04](04-primeiro-trace.md) | Primeiro trace e os dois filhos |
| 35 min | Execute os casos LOW, MEDIUM e HIGH em [05](05-dissecar-dcra.md) | Caminhos diferentes, com explicação de uma regra |
| 25 min | Faça pausa/retomada de [06](06-threads-checkpoints-revisao.md) | Mesmo `thread_id`, execuções distintas |
| 20 min | Injete as falhas de [07](07-falhas-latencia-retries.md) | Um root sem erro contendo uma tentativa falha |
| 15 min | Explique o sistema em dois minutos e anote dúvidas | Resposta sem ler nomes de funções |

Ao terminar, consiga apontar: “a interpretação aconteceu aqui; a política de risco aqui; o custo do modelo aqui; a espera humana pertence ao processo de negócio”. Se ainda disser que LangSmith retoma o grafo, volte ao capítulo 06.

## Dia 2 — medir se a mudança melhorou

| Tempo | Faça | Evidência |
|---|---|---|
| 20 min | Leia [11](11-datasets-contratos.md); examine três referências | Inputs separados de gabaritos |
| 30 min | Rode [12](12-evals-deterministicos.md) | 16/16 na baseline, 13/16 com bug, recall HIGH 0 |
| 30 min | Publique dataset e compare experimentos em [13](13-experimentos-comparacao.md) | Uma linha em que a candidata regrediu |
| 20 min | Faça o lab 07 de [14](14-modelo-real-saida-estruturada.md), se a conta de modelo estiver pronta | Input, JSON retornado e critério de comparação |
| 25 min | Leia a rubrica e execute/analise [15](15-juiz-llm-calibracao.md) | Discordância possível entre juiz e anotação manual |
| 15 min | Faça [09](09-tokens-custos-orcamentos.md) | Conta de custo e efeito de repetir avaliações |

Se não puder chamar um modelo, faça o ensaio dos labs 07 e 08 e deixe anotado **“não executei esta etapa com modelo real”**. Você ainda terá executado o grafo, a instrumentação e os avaliadores de código.

## Dia 3 — defender decisões

| Tempo | Faça | Evidência |
|---|---|---|
| 25 min | Leia [17](17-reprodutibilidade-prompts.md) e rode o lab 13 | Hash/commit de prompt e manifesto |
| 20 min | Leia [18](18-evals-online-producao.md) e [19](19-privacidade-amostragem.md) | Desenho do ciclo online → dataset → experimento |
| 20 min | Rode o pequeno RAG de [20](20-rag-fora-do-projeto.md) | Recuperação ruim versus resposta inventada |
| 20 min | Leia a comparação de [21](21-langfuse-otel.md) | Diferenças de responsabilidade entre quatro ferramentas |
| 15 min | Faça o gate de [23](23-ci-gates.md) | Exit code 1 para uma regressão deliberada |
| 35 min | Grave as respostas de [24](24-entrevista-simulada.md) | Demo de três minutos e seis respostas curtas |
| 15 min | Resolva três [desafios](25-desafios-gabarito.md) | Hipótese, evidência e conclusão |

Não gaste a última noite tentando dominar uma implantação completa do Langfuse ou OpenTelemetry. São aprofundamentos úteis depois de você conseguir explicar o ciclo de avaliação com precisão.

## Se restarem só 90 minutos

1. Prepare e rode `01_trace_python.py --send` — 15 min.
2. Rode `02_dcra.py --case medium --review approve --send` — 20 min.
3. Rode `06_evaluate.py` e interprete o bug — 20 min.
4. Leia os exemplos de custos e reprodutibilidade — 15 min.
5. Ensaie a demo e as perguntas 1–6 do capítulo 24 — 20 min.

Essa rota curta não substitui as outras; ela preserva os argumentos mais demonstráveis.

## Pequeno contrato consigo mesmo

Abra o [caderno](28-caderno-de-evidencias.md). Para cada experimento, escreva quatro linhas: **o que pensei que aconteceria; o que executei; o que observei; o que posso concluir**. Acrescente uma quinta quando necessário: o que ainda não sei.

Exemplo: “A média cairia pouco. Executei a candidata com bug em 16 casos. Ela acertou 13, mas errou os três HIGH. A mudança é inaceitável segundo nosso gate, embora 81,25% pareça razoável isoladamente.” Essa frase já tem substância para uma entrevista.
