# 22 · O painel deve levar a uma decisão, não só ficar bonito

[Índice](README.md) · [Anterior](21-langfuse-otel.md) · [Próximo](23-ci-gates.md)

**Objetivo:** transformar traces em métricas defensáveis e investigar um incidente com ordem. Tempo: 30–40 minutos. Código: [16_consultar_runs.py](labs/16_consultar_runs.py). Os limites numéricos abaixo são exemplos de desenho, não SLOs implantados no DCRA.

Um painel com “tokens totais” é útil para volume, mas não responde se os usuários conseguem concluir uma análise correta. Comece pela jornada: pedido recebido, interpretação concluída, evidências obtidas, análise entregue, revisão finalizada quando exigida.

## Um pequeno painel hipotético

| Sinal | Pergunta | Recortes úteis |
|---|---|---|
| Erro técnico por pedido | a execução falhou? | versão, operação, provedor |
| Resposta degradada | faltou evidência apesar de resposta válida? | fonte, tipo de ativo |
| `structure_exact` em benchmark | interpretação corresponde ao pedido? | idioma, paráfrase, operação |
| Nota semântica + cobertura | recomendações parecem sustentadas? | juiz/rubrica, amostra, versão |
| p50/p95 de latência ativa | experiência típica e cauda | nó, modelo, caminho |
| Custo por caso concluído corretamente | eficiência com qualidade | revisões, agente acionado, versão |
| Tempo em revisão humana | onde os casos aguardam? | risco, equipe/processo |

Os sinais vêm de lugares diferentes: traces, resultados de eval e eventos de negócio. O projeto atual não implementa esse painel unificado; ele fornece elementos para discutir o desenho.

## Laboratório — quatro números sobre “erro”, todos corretos

Ler um trace de cada vez ensina a investigar. Operar exige agregar. Este laboratório faz a passagem: recebe uma árvore de runs e produz as medidas que um painel exibiria.

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/16_consultar_runs.py
```

A fonte local é [runs.jsonl](dados/runs.jsonl): três traces sintéticos, catorze runs. O trace `tA` conclui com coletores concorrentes; `tB` tem uma tentativa de `collect_deps` que falha e outra que funciona, com raiz sem erro; `tC` termina em erro.

Bloco `denominadores`:

| Medida | Valor | O que ela responde |
|---|---:|---|
| `erro_por_pedido` | 0,3333 | 1 das 3 raízes terminou com erro |
| `erro_por_run` | 0,2143 | 3 dos 14 runs registraram erro |
| `erro_por_tentativa_de_collect_deps` | 0,3333 | 1 das 3 tentativas dessa operação falhou |
| `pedidos_em_que_collect_deps_nunca_obteve_resposta` | 0 | o retry recuperou em todos os pedidos |

São quatro respostas corretas e incompatíveis para “qual é a taxa de erro?”. Um painel que mostra uma delas sem dizer qual convida a decisões erradas. Escolha a unidade que corresponde à pergunta: experiência do usuário costuma pedir a primeira; saúde de uma dependência pede a terceira; a quarta diz se a mitigação está funcionando.

Bloco `tempo_proprio`, no trace `tA`:

```text
raiz_ms                       1200,0
soma_ingenua_dos_filhos_ms    1200,0   ← soma das durações, ignorando concorrência
ocupacao_real_dos_filhos_ms   1000,0   ← união dos intervalos ocupados
tempo_proprio_ms               200,0   ← raiz menos essa ocupação
```

Somar as durações dos três coletores paralelos dá exatamente a duração da raiz e sugere que a orquestração não custa nada. Os coletores compartilham a mesma janela: ocupam 1000 ms, e sobram 200 ms de trabalho fora deles. É o mesmo cuidado do [capítulo 07](07-falhas-latencia-retries.md) e da agregação de custos do [capítulo 09](09-tokens-custos-orcamentos.md), agora em aritmética.

Bloco `latencia` traz `n` junto de cada percentil, pelo método *nearest-rank*. Repare em `collect_asset`: `n=1`, e p50 = p95 = a única observação. O número existe; a estimativa, não. Um painel que esconde o `n` transforma uma observação em cauda.

## Consultar os seus próprios traces

Depois de rodar labs com `--send`, agregue o que existe na sua conta:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/16_consultar_runs.py --send --dias 1
```

O script lê o projeto `dcra-estudos` na janela indicada e calcula as mesmas medidas sobre os seus runs. Os nomes de operação serão os dos laboratórios que você executou, não `collect_deps`; use `--operacao <nome>` para escolher o alvo do recorte por tentativa.

O laboratório imprime as consultas equivalentes:

```text
raízes do projeto      list_runs(project_name=..., is_root=True)
somente falhas         list_runs(project_name=..., error=True)
uma operação           list_runs(project_name=..., filter='eq(name, "collect_deps")')
chamadas de ferramenta list_runs(project_name=..., filter='eq(run_type, "tool")')
```

Os filtros usam a linguagem de consulta do LangSmith, com operadores como `eq`, `neq`, `gt`, `and` e `or`. Ela também está na barra de busca da UI: a mesma expressão que filtra a lista de runs na tela pode ir para o SDK. `trace_filter` aplica a condição à raiz do trace e `tree_filter` a qualquer run da árvore — é assim que se pergunta “runs de `interpret` cujo pedido inteiro terminou em erro”. [Sintaxe de consulta de traces](https://docs.langchain.com/langsmith/trace-query-syntax).

**Aviso de versão.** No `langsmith` 0.11.1 deste repositório, `Client.list_runs` está marcado como *deprecated*, com remoção anunciada para depois de 31 de janeiro de 2027 e migração para `Client.runs.query`. O mesmo vale para `Client.read_run` e `Client.get_run_url`, usados por [_common.py](labs/_common.py) para imprimir a URL do trace. O curso continua no caminho antigo de propósito: ele é síncrono e funciona na conta gerenciada, enquanto `Client.runs` é assíncrono e exige backend `0.16` ou superior em instalação própria. Registre a data e verifique a sua versão antes de copiar este código para um projeto que vai durar.

## SLI, SLO e error budget

**SLI** é a medida. **SLO** é a meta operacional definida sobre ela em uma janela. Exemplo fictício: “99% das análises elegíveis entregam um resultado técnico válido em até 10 segundos, numa janela de sete dias”. É preciso especificar elegibilidade, o que conta como resultado válido e como revisões humanas entram no cálculo.

Se a meta exige 99%, o orçamento de erro dessa medida admite 1% de eventos não conformes na janela. Esse orçamento não é o orçamento financeiro e não mede sozinho qualidade semântica. Para uma introdução direta do próprio trabalho de SRE, consulte [Implementing SLOs — Google SRE Workbook](https://sre.google/workbook/implementing-slos/).

p95 é o ponto abaixo do qual ficam aproximadamente 95% das observações segundo o método de cálculo. Uma média baixa pode esconder uma cauda lenta. Com pouco tráfego, percentis oscilam; inclua a contagem de amostras e evite precisão teatral — foi o que o campo `n` do laboratório tornou visível.

## Simulação: “o custo dobrou, mas o tráfego não”

1. **Fixe janela e população.** Compare o mesmo ambiente e unidade: custo por caso, não total de um dia cheio contra meia manhã.
2. **Verifique medição.** Houve dupla instrumentação, mudança de tabela de preços ou inclusão de juízes no mesmo agregado?
3. **Segmente por caminho.** Aumentou a proporção de investigação, devoluções ou falhas com retry?
4. **Abra exemplares caros.** Use os traces para localizar as etapas responsáveis.
5. **Formule hipótese.** Por exemplo: a fonte de usage falhou mais e acionou investigação sem conseguir recuperá-la.
6. **Busque confirmação.** Compare indisponibilidade por fonte, calls de ferramentas e evidência nova encontrada.
7. **Planeje mitigação e validação.** Corrigir fonte, limitar trabalho improdutivo ou melhorar fallback; depois verificar custo e qualidade.

Reproduza a lógica com o [lab de falhas](07-falhas-latencia-retries.md) e o [lab de investigação](16-avaliar-workflow-agentes.md). Os dados didáticos tornam a causa conhecida, mas tente escrever a hipótese antes de olhar o código.

## Simulação: “qualidade caiu só em português”

Uma média geral estável pode esconder piora em um segmento pequeno. Compare exemplos de português da mesma versão de dataset e reveja referências. Confira se mudou prompt, modelo, normalização, população ou juiz. O slice precisa ter casos suficientes; dois exemplos são pistas, não uma taxa consolidada de produção.

**Onde esse recorte existe de verdade.** O slice `portugues` está em [interpretacao.jsonl](dados/interpretacao.jsonl), do [lab 07](14-modelo-real-saida-estruturada.md), com dois casos — i02 e i08. Ele **não** existe em [casos.jsonl](dados/casos.jsonl): os 16 casos de contrato passam pelo parser fixture de [_dcra.py](labs/_dcra.py), que só reconhece padrões em inglês, então um pedido em português cairia em `InterpretationError` em vez de medir interpretação. É uma limitação deliberada do fixture, não um esquecimento do benchmark — e um bom exemplo de por que “o slice X piorou” exige antes perguntar “esse slice existe neste conjunto, e com quantos casos?”.

## Operação da própria observabilidade

Também monitore atraso de ingestão, falhas de exportação, coverage de tracing/eval e erros do juiz. Não faça a execução de negócio depender desnecessariamente da UI de observabilidade estar disponível. No DCRA, checkpoints e registro persistido têm responsabilidades próprias, independentes da investigação no LangSmith.

Use IDs de alta cardinalidade, como caso/run, para busca e correlação. Para gráficos agregados, prefira dimensões controladas como operação, ambiente e versão. Transformar cada texto de usuário em série de métrica torna o painel difícil de operar.

**Exercício oral:** alguém apresenta “nossa taxa de erro é 21%”. Faça as três perguntas que decidem se esse número significa alguma coisa. Sugestão: qual é o denominador, qual é a janela, e uma falha recuperada por retry conta?

**Memorize:** *SLI*, *SLO*, *error budget*, *p95*, *nearest-rank*, *self time*, *cardinality*, *ingestion lag*, *root cause analysis*.
