# 22 · O painel deve levar a uma decisão, não só ficar bonito

[Índice](README.md) · [Anterior](21-langfuse-otel.md) · [Próximo](23-ci-gates.md)

**Objetivo:** transformar traces em métricas defensáveis, investigar um incidente com ordem e saber quanto custa guardar os dados e como tirá-los da plataforma. Tempo: 40–50 minutos. Código: [16_consultar_runs.py](labs/16_consultar_runs.py) e [17_exportar_runs.py](labs/17_exportar_runs.py). Os limites numéricos abaixo são exemplos de desenho, não SLOs implantados no DCRA.

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

## Laboratório — o painel nativo, na sua conta

O lab 16 calcula as medidas em código. A plataforma desenha as mesmas medidas em gráficos, e a pergunta útil é se os dois concordam quando olham **a mesma população na mesma janela**. Este exercício precisa de conta; sem ela, leia o procedimento e registre a lacuna.

1. Gere um conjunto pequeno e identificado de traces num projeto só para isto:

   ```bash
   .venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py --send --project dcra-estudos-painel
   .venv/bin/python ESTUDOS_LANGSMITH/labs/04_feedback.py --send --project dcra-estudos-painel
   .venv/bin/python ESTUDOS_LANGSMITH/labs/03_failures.py --send --project dcra-estudos-painel
   ```

   Isso dá um trace de sucesso com feedback e quatro cenários de falha/retry, com metadados `environment=lab` e `synthetic=true`. Anote a hora de início e de fim, com fuso.

2. Abra o projeto `dcra-estudos-painel` no [LangSmith](https://smith.langchain.com) e procure a área de dashboards. A [documentação atual](https://docs.langchain.com/langsmith/dashboards) descreve painéis pré-construídos por projeto e gráficos personalizados; confirme na sua conta o que está disponível, porque isso varia por plano e muda com o tempo.

3. Monte, ou localize no painel pronto, cinco gráficos: **volume de raízes**, **raízes com erro**, **latência p50/p95**, **tokens/custo** (vai aparecer vazio ou fictício aqui — não há modelo real) e **feedback**. Para cada um, escreva no caderno: projeto, janela, filtro, unidade e agrupamento. Um gráfico sem essas cinco informações é decoração.

4. Compare com o código, sobre a mesma população:

   ```bash
   .venv/bin/python ESTUDOS_LANGSMITH/labs/16_consultar_runs.py --send --dias 1 --project dcra-estudos-painel --operacao ler_catalogo
   ```

   Volume e erro devem bater exatamente se a janela for a mesma. Latência pode divergir: o lab usa *nearest-rank*; a UI usa o método dela, que a documentação nem sempre nomeia. Registre a diferença como diferença de método, não como “um dos dois está errado”, e registre o `n`.

5. Guarde a configuração de cada gráfico como texto, sem capturas com chave ou conteúdo sensível. Se um gráfico não existir na sua conta, escreva isso; não descreva uma tela que você não viu.

**O que este material não afirma:** nenhum painel foi criado durante a validação do curso, e nenhum valor da UI foi comparado com o lab 16. O procedimento acima é o exercício; a evidência é sua. Para o app **publicado** — e não os traces de estudo — o [capítulo 29](29-acompanhar-producao.md) liga o tracing em produção e junta o painel ao banco e ao Cloud Run.

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

## Retenção, cobrança e saída dos dados

Numa entrevista sobre operação, “quanto custa guardar isso e como tiro os dados daqui” aparece cedo. Quatro tipos de dado têm ciclos diferentes, e misturá-los é o erro mais comum:

| Dado | Onde vive | Retenção e cobrança | Como sai |
|---|---|---|---|
| Trace de rotina | projeto de tracing | fica na faixa **base** (14 dias na consulta de 11 de setembro de 2026) e conta no medidor de ingestão; é a maior parte do volume | consulta por SDK, exportação em massa |
| Trace promovido à faixa **estendida** | mesmo projeto | a promoção é um **evento cobrado à parte**, quando ocorre — pode cair no mês seguinte ao da ingestão | idem |
| Feedback e anotações | ligados ao run | feedback e notas **pela UI não mudam a faixa**; feedback **pela API/SDK só promove com `extend_trace_retention=true`**; entrar numa fila de anotação não promove por padrão | `list_feedback`, exportação |
| Avaliadores online e regras de automação | configuração do projeto | promovem o trace **se a opção de retenção do avaliador/regra estiver ligada**; é uma escolha de configuração, não um efeito automático | — |
| Datasets e experimentos | fora dos projetos de tracing | datasets têm retenção indefinida; runs de experimentos nascem na faixa estendida | SDK de datasets |
| Cópias exportadas | seu disco, bucket ou repositório | passam a ser **sua** responsabilidade: prazo, acesso, sanitização | você decide |

Condições e mecanismos acima vêm da [documentação de administração](https://docs.langchain.com/langsmith/administration-overview), lida em 11 de setembro de 2026 — inclusive o prazo da faixa estendida, que aparece com valores diferentes em páginas diferentes e por isso não está na tabela. Preços vêm da [página de preços](https://www.langchain.com/pricing). Tudo isso muda; registre a data da consulta e confira no workspace qual configuração de retenção os seus avaliadores têm.

**Quanto custa guardar.** O lab 09 ganhou uma estimativa parametrizada, `estimativa_mensal`, com preços **fictícios** e a **estrutura** da fatura documentada: um medidor de ingestão, que conta todo trace do mês, e um medidor de upgrades, que conta as promoções do mês — inclusive de traces ingeridos em meses anteriores. Ela mostra os dois erros simétricos: tirar o trace promovido da ingestão (subestima) e cobrar a ingestão de novo no mês do upgrade (superestima). Troque os parâmetros pelos da sua conta antes de citar um número.

**Tirar os dados.** O lab 17 faz uma exportação pequena por SDK:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/17_exportar_runs.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/17_exportar_runs.py   # de novo: nada é duplicado
```

Sem `--send`, a fonte é a árvore sintética de [runs.jsonl](dados/runs.jsonl) mais [feedback.jsonl](dados/feedback.jsonl). A janela padrão vai de 10:00 a 10:08 e é **fechada à esquerda e aberta à direita**: `tA` e `tB` entram (11 runs), `tC` começa às 10:09 e fica de fora (`fora_da_janela: 3`). A segunda execução relata `novos: 0, ja_presentes: 11` e o SHA-256 do arquivo não muda — a mesma propriedade que torna uma retomada segura depois de uma interrupção. Saem três arquivos em `artefatos/17-export/<origem>-<janela>/`: `runs.jsonl`, `feedback.jsonl` e `manifesto.json`, com a **identidade** da exportação (origem, janela, opções), a lista de execuções, a reconciliação (ids únicos, raízes, erros, filhos sem pai no arquivo, feedback sem run) e o manifesto de versões.

Três regras protegem o manifesto de mentir:

- **Um diretório, uma identidade.** O nome do diretório vem de origem, janela e opções, e o script recusa gravar num diretório cujo manifesto tenha outra identidade — local → remoto, projeto A → B, outra janela ou `--conteudo` depois de uma exportação sem conteúdo. Experimente: `17_exportar_runs.py --conteudo --destino <o diretório da execução anterior>` termina em exit 1.
- **Acima do teto, nada.** `--max` é o teto de runs **dentro da janela**; o script pede `max + 1` ao servidor para saber se há excesso e, havendo, não grava nada: `17_exportar_runs.py --max 3` termina em exit 1 com a orientação de reduzir a janela. Um arquivo parcial nunca é apresentado como completo.
- **Sem `--conteudo`, sem texto livre.** Por padrão saem metadados; `inputs`/`outputs` ficam de fora, a mensagem de erro é reduzida à classe (`TimeoutError`, não `TimeoutError: catalogo nao respondeu`) e `comment`/`value` do feedback saem como nulos — uma mensagem de exceção ou um comentário humano pode carregar entrada do usuário. `--conteudo` libera tudo, e o manifesto registra a escolha.

Com conta, o mesmo script lê o seu projeto:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/17_exportar_runs.py --send --project dcra-estudos --dias 1
.venv/bin/python ESTUDOS_LANGSMITH/labs/17_exportar_runs.py --send --project dcra-estudos --desde 2026-09-10T00:00:00Z --ate 2026-09-11T00:00:00Z --conteudo
```

Uma cópia local é uma cópia a mais para proteger ([19](19-privacidade-amostragem.md)); por isso o padrão é sem texto livre. Os dois limites da janela vão ao servidor pela [linguagem de consulta](https://docs.langchain.com/langsmith/trace-query-syntax) — `and(gte(start_time, "…Z"), lt(start_time, "…Z"))` — e a checagem local continua como verificação; o manifesto guarda o filtro enviado. Como no lab 16, o caminho usa `list_runs`, deprecado no SDK instalado — a decisão está registrada acima. **O modo `--send` não foi executado na validação do material**; o filtro, o teto e a normalização foram testados com um cliente falso.

Isso **não** é o bulk export nativo. Esse recurso, segundo a [documentação consultada](https://docs.langchain.com/langsmith/data-export) em 11 de setembro de 2026, grava Parquet num bucket compatível com S3 e é pago: contas criadas depois de 3 de agosto de 2026 só o têm no plano Enterprise; contas anteriores, em Plus ou Enterprise até 1º de fevereiro de 2027. O plano gratuito (Developer) cobre todo o resto do curso. Se a sua conta permitir, registre destino, job, campos, contagem e a leitura posterior do arquivo; se não permitir, deixe o item como pendente em vez de descrever um job que não rodou.

**Exercício oral:** alguém apresenta “nossa taxa de erro é 21%”. Faça as três perguntas que decidem se esse número significa alguma coisa. Sugestão: qual é o denominador, qual é a janela, e uma falha recuperada por retry conta?

**Memorize:** *SLI*, *SLO*, *error budget*, *p95*, *nearest-rank*, *self time*, *cardinality*, *ingestion lag*, *root cause analysis*, *retention tier*, *idempotent export*.

## Levar para outros projetos — e onde o seu julgamento decide

Painel que leva a uma decisão, quatro taxas de erro corretas e incompatíveis, `n` junto do p95, retenção e saída dos dados — operação é o lugar onde a medição encontra a responsabilidade.

**Na plataforma de atendimento (Langfuse Cloud).** O "pequeno painel hipotético" tem uma versão já desenhada em `detalhamento_execucao.md` §4.1 (widgets mínimos) e uma fonte de verdade declarada: **o Postgres continua a origem das métricas de negócio** (`docs/metrics/v3_queries.sql`); o Langfuse é a interface de diagnóstico, e a duplicação é aceita. É a decisão certa segundo este capítulo: "não faça a execução de negócio depender da UI de observabilidade". Os quatro denominadores têm tradução imediata: *erro por pedido* = turnos sem decisão / turnos disparados; *erro por run* = observações com erro / observações (o número que menos responde); *erro por tentativa de uma operação* = falhas de `ai.n5_free` / chamadas de `ai.n5_free`; *pedidos em que a operação nunca respondeu* = turnos em que **nenhuma** geração completou. O contrato de scores já protege um deles: "turnos que falham antes de chegar à decisão entram na contagem de falhas, sem receber um falso 0". O "tempo próprio" é especialmente importante ali porque o turno atravessa requisições: `n5.response_latency_ms` (da mensagem ao envio) inclui debounce e janela de veto; a soma das generations é o tempo de modelo; a diferença é o tempo do processo — e um painel que mostra só o primeiro atribui ao LLM uma espera que é de desenho. A simulação "o custo dobrou" tem uma hipótese pronta no domínio: a proporção de fallback livre subiu (duas gerações por turno), porque a recuperação piorou — e `n5.fallback_started` é o score que confirma ou refuta. Sobre retenção e saída: no Langfuse Cloud, retenção é configuração por projeto e a exportação é por API ou *batch export* — confira o que o free tier permite antes de contar com uma cópia; o lab 17 daqui (janela fechada-aberta, identidade por diretório, sem texto livre por padrão) é o modelo do script que você escreveria lá.

**Em projetos comuns do ecossistema.** SLI com unidade, população e janela; SLO com elegibilidade e definição de "resultado válido"; `n` ao lado de todo percentil; dimensões controladas nos gráficos (operação, ambiente, versão) e IDs de alta cardinalidade só para busca; monitorar a própria observabilidade (atraso de ingestão, cobertura do juiz, erros de exportação); e uma tabela de retenção/cobrança por tipo de dado, com data de consulta. `list_runs` deprecado no SDK 0.11.1 é um lembrete geral: registre a versão antes de copiar código para algo que vai durar.

**O fator humano — onde a IA faz e onde você decide.** Um assistente monta o painel, calcula os quatro denominadores e até escreve o runbook de incidente. O que ele não faz: **definir o SLO** ("99% dos turnos elegíveis entregam resposta válida em 10 s" exige decidir o que é elegível e o que é válido — decisões de produto) e **escolher qual denominador vai para qual conversa** (experiência do usuário → por pedido; saúde do catálogo → por tentativa). Foque nisso, e em mais dois pontos. Primeiro, a investigação sob pressão: os sete passos da simulação são um método, e a IA segue métodos bem — mas o passo 5, "formule hipótese", é onde o conhecimento do sistema entra ("a fonte de usage falhou e acionou investigação sem recuperá-la" não é dedutível do painel; é intuição de quem conhece o caminho). Escreva a hipótese **antes** de pedir ajuda; depois use a IA para buscar confirmação. Segundo, retenção e exportação são decisões de custódia: quanto tempo os traces ficam, quem pode exportar, para onde vai a cópia e quem a protege. A IA escreve o script idempotente; a decisão de que a cópia sai **sem texto livre por padrão** é uma escolha de quem responde pelos dados. E o exercício oral — "nossa taxa de erro é 21%": as três perguntas (denominador, janela, retry conta?) são o hábito que você leva para qualquer reunião, com ou sem assistente.
