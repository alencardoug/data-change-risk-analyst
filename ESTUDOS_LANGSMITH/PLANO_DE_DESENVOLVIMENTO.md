# Plano de desenvolvimento das lacunas de observabilidade e avaliação

[Índice](README.md)

**Data:** 11 de setembro de 2026. **Status:** E1 implementada e validada localmente (a publicação remota da suíte pytest ainda não foi executada) e a parte local de E2 idem; itens que dependem de conta ou plano pendentes; E3–E7 adiadas por decisão registrada na seção 0. As seções 1–4 são a proposta original, mantida como referência.

Este plano cobre as quatro sugestões de [SUGESTAO_CLAUDE.md](SUGESTAO_CLAUDE.md#o-que-ainda-falta-se-você-quiser-continuar) e as cinco capacidades do [inventário do projeto](01-mapa-do-projeto.md#o-inventário-honesto). No segundo documento, a redação encontrada é **“Ainda não implantado no produto”**.

A sequência recomendada é completar a bancada de estudo, estabelecer uma base de telemetria no DCRA e implantar as capacidades operacionais em incrementos pequenos. O pedido atual autoriza elaborar este plano. O produto publicado continua no estado congelado registrado em [CLAUDE.md](../CLAUDE.md); a execução futura das etapas de produto deverá registrar o novo escopo e atualizar esse status.

## 0. Decisão de escopo e estado — 11 de setembro de 2026

A proposta abaixo foi adaptada antes de executar. O critério: fazer tudo o que cabe como **extensão de estudo**, sem tocar em `src/dcra/`, sem infraestrutura nova e sem depender de conta autenticada; deixar explícito o que fica pendente e por quê.

| Lacuna | Estado | Onde está | O que ainda falta |
|---|---|---|---|
| Caso concreto em que o juiz erra (E1.1) | **Implementado e validado localmente** | `labs/08_judge.py --fixture-biased`, `dados/juiz_enviesado.json`, capítulo 15 | Nada; é simulação de procedimento, identificada como tal |
| Integração de eval com pytest (E1.2) | **Implementado e validado localmente** | `evals/` (`conftest.py`, `test_contratos_dcra.py`, `_suite.py`), capítulo 23 | Executar `DCRA_EVALS_REMOTE=1` numa conta e registrar dataset/experimento |
| Retenção, cobrança e exportação (E2.2) | **Procedimento, script e estimativa prontos; evidência remota pendente** | `labs/17_exportar_runs.py`, `dados/feedback.jsonl`, `estimativa_mensal` no lab 09, capítulos 09 e 22 | `--send` numa conta; bulk export depende de plano |
| Dashboards nativos (E2.1) | **Procedimento escrito; nenhuma evidência** | Capítulo 22, seção do painel nativo | Executar na conta, comparar com o lab 16, registrar no caderno |
| Acompanhar tráfego e uso (pedido de 11 de setembro) | **Implementado como estudo; tracing de produção ligado e publicado (revisão `dcra-00002-kcv`, 11 de setembro)** | Capítulo 29, `labs/18_uso_producao.py`, `deploy/deploy.sh`, `deploy/create-secrets.sh`, `DEPLOYMENT.md` | Submeter um caso e abrir `dcra-prod`; rodar o lab 18 contra o Neon; definir teto de gasto na OpenAI |
| Eval online contínuo (E4.1) | Adiado; a parte que interessava (ver tráfego e uso) foi resolvida sem ele | Capítulo 18 continua como desenho | Casos reais em volume que justifique triagem |
| Dashboards/SLOs de qualidade (E4.2) | Adiado | Capítulo 22 continua como desenho | Idem; além disso, tráfego real para haver o que medir |
| Gates de release por evals (E5) | Adiado; a parte de avaliação existe | `evals/` e `12_regression_gate.py` são o gate; falta ligá-lo à promoção | Workflow de CI e mudança em `deploy/deploy.sh` |
| Langfuse no produto (E6) | Adiado | Lab 15 continua como demonstração | Decisão de descongelar; dependência nova |
| OpenTelemetry distribuído (E7) | Adiado | Capítulo 21 continua como leitura | Decisão de descongelar; MCP está desligado no deploy |

**Por que E3–E7 ficaram adiadas.** As cinco alteram o runtime publicado (`graph/build.py`, `config.py`, `nodes.py`, cliente e servidor MCP, `deploy.sh`), o que contraria o estado congelado registrado em [CLAUDE.md](../CLAUDE.md) e não é correção pontual. Exigem um ambiente de homologação com Cloud Run, Neon e segredos próprios — custo recorrente para um produto sem usuários. E os SLOs de E4 seriam medidos sobre tráfego sintético, porque o produto não tem tráfego orgânico; o resultado seria uma demonstração, não operação. O inventário do [capítulo 01](01-mapa-do-projeto.md) que diz “ainda não implantado” é informação correta, não dívida.

**O que destravaria essas etapas.** Uma razão concreta para o produto evoluir (usuários reais, requisito de mostrar um pipeline vivo), a aceitação do custo de homologação e a decisão explícita de atualizar o status em `CLAUDE.md`. Se isso acontecer, E5 é a primeira: o gate já existe como código e só precisa de um workflow e da ligação com a promoção da imagem.

**E0 foi reduzida.** Sem mudança de produto não há `specs/002-…`; este documento é o registro de escopo. Versões e hashes continuam nos manifestos que os labs gravam.

**Uma correção pontual no produto, decidida em 11 de setembro de 2026.** A pedido, o deploy passou a ligar o tracing do LangSmith em produção (`LANGSMITH_TRACING=true`, projeto `dcra-prod`, terceiro segredo). É configuração — nenhum arquivo em `src/` mudou — e é reversível por variável de ambiente. O status congelado em `CLAUDE.md` permanece. A mudança foi publicada no mesmo dia (revisão `dcra-00002-kcv`); o capítulo 29 registra a verificação.

**Migração para a API v2 do SDK — 12 de setembro de 2026.** A UI acusou *Legacy API usage detected*; os labs usavam `read_run`, `get_run_url` e `list_runs` (deprecados, remoção após 31 de janeiro de 2027) e `create_feedback` sem `session_id`. Todos os labs e arquivos ligados foram revistos: `trace(...)`/`run.end` no lugar do wrapper `traced_call`; `client.runs.get_url` e `client.runs.query` (assíncronos, via `asyncio.run`) no lugar dos métodos legados; feedback com `session_id`/`start_time`; `read_dataset_version(tag="latest")`. Foi preciso atualizar o `langsmith` para 0.12.4 (só o `uv.lock`, não versionado): na 0.11.1 o cliente v2 falhava ao conectar por misturar `httpx` e `httpx2`. Nenhum arquivo em `src/` mudou. Detalhes e evidência no [capítulo 27](27-fontes-e-validacao.md).

**Validação da execução.** `uv run pytest` (57 aprovados, 19 pulados), `uv run pytest ESTUDOS_LANGSMITH/tests` (26 aprovados, catorze novos; um deles só com Postgres local), `uv run ruff check src tests ESTUDOS_LANGSMITH`, e `verificar_material.py` com 38 comandos sem tentativa de rede. Uma revisão do Codex no mesmo dia apontou seis correções (proveniência e teto da exportação, gate sobre subconjunto, manifesto da suíte, modelo de cobrança e condições de retenção), todas aplicadas. Detalhes e o que ficou sem execução remota estão no [capítulo 27](27-fontes-e-validacao.md).

## 1. Escopo e ponto de partida

| Lacuna solicitada | Entrega planejada | Etapa |
|---|---|---|
| Dashboards nativos do LangSmith | Exercício executado na conta real, configuração reproduzível e comparação com agregação local | E2 |
| Integração de eval com pytest | Suíte com integração oficial, execução local e publicação opcional | E1 |
| Retenção, cobrança e exportação em massa | Política, estimativa parametrizada e exportação verificável | E2 |
| Caso concreto em que o juiz erra | Juiz fixture enviesado, discordâncias explicadas e relatório de calibração | E1 |
| Programa contínuo de eval online | Avaliadores sobre execuções do DCRA, cobertura, triagem e retorno ao dataset | E4 |
| Dashboards/SLOs de qualidade | Painel operacional com população, janela, metas e resposta a desvios | E4 |
| Gates de release orientados por evals | CI que avalia o artefato candidato e impede sua promoção quando reprova | E5 |
| Implantação de Langfuse | Integração selecionável na aplicação, validada em ambiente publicado | E6 |
| Coleta distribuída com OpenTelemetry | Propagação entre processos e exportação por um Collector | E7 |

Constatações do repositório que mudam a ordem do trabalho:

- O [script de deploy](../deploy/deploy.sh) configura `LANGSMITH_TRACING=false`. A integração existe no código, mas o plano não presume ingestão ativa em produção. A configuração efetiva do Cloud Run ainda precisa ser conferida.
- [06_evaluate.py](labs/06_evaluate.py), [_evaluators.py](labs/_evaluators.py) e [12_regression_gate.py](labs/12_regression_gate.py) já oferecem benchmark, métricas e gate local. O trabalho é integrá-los e fortalecer a promoção, aproveitando essa base.
- Os 16 casos de [casos.jsonl](dados/casos.jsonl) executam o grafo real com dependências fixture. Eles avaliam contratos e política, sem comprovar a qualidade do modelo real. [interpretacao.jsonl](dados/interpretacao.jsonl) cobre essa outra frente, incluindo português.
- [08_judge.py](labs/08_judge.py) já tem seis referências humanas e juiz real opcional; sem `--real`, apenas mostra os casos. Falta executar e explicar um juiz simulado que discorde.
- Não foi encontrado workflow versionado em `.github/workflows/`. O deploy atual é um script executado manualmente.
- [tests/conftest.py](../tests/conftest.py) desliga tracing automaticamente. A integração pytest precisará de configuração própria, incluindo o controle separado de envio de resultados.
- O MCP atual usa um subprocesso por `stdio` e está desligado no deploy. Spans locais ou um exemplo de restaurante não demonstram coleta distribuída do DCRA.

O ambiente local inspecionado continha `langsmith 0.11.1`, `langchain 1.3.18`, `langgraph 1.2.11` e `pytest 9.1.1`. Em 12 de setembro de 2026 o `langsmith` foi atualizado para 0.12.4 e os labs migraram para a API v2 (SmithDB); o [capítulo 27](27-fontes-e-validacao.md) registra o que mudou, o defeito da 0.11.1 que forçou a atualização e o que foi executado remotamente.

## 2. Sequência, esforço e dependências

Estimativa para uma pessoa familiarizada com o repositório. As horas incluem implementação, testes e documentação; excluem espera por acessos, provisionamento e observação de tráfego. São estimativas de planejamento, não medições.

| Etapa | Resultado | Depende de | Esforço |
|---|---|---|---|
| E0 | Escopo, contratos de medição e compatibilidade definidos | — | 2–4 h |
| E1 | Juiz enviesado e integração pytest funcionando localmente | E0 | 8–12 h |
| E2 | Dashboards de estudo, retenção e exportação validados | E0; pytest remoto usa E1 | 8–12 h |
| E3 | Telemetria do produto validada em homologação | E0, E2 | 8–12 h |
| E4 | Eval online, painel de qualidade e rotina de operação | E1, E3 | 12–20 h |
| E5 | Gates integrados à promoção de releases | E1, E3; calibração semântica usa E4 | 8–12 h |
| E6 | Langfuse integrado ao DCRA | E3, E5 | 6–10 h |
| E7 | Coleta distribuída via OpenTelemetry | E6 | 10–16 h |
| E8 | Evidências finais e documentação reconciliadas | E1–E7 | 4–6 h |

**Total estimado: 66–104 horas**, aproximadamente 11–18 dias com seis horas produtivas por dia, mais as janelas de observação. E1 e E2 podem avançar independentemente; o gate determinístico de E5 pode começar antes de E4 terminar.

O primeiro marco útil é **E0–E2, em 18–28 horas**: cobre as quatro sugestões do parecer sem alterar o runtime do produto. E3–E5 acrescentam operação e controle de release. E6–E7 completam as lacunas de integração; ficam por último por exigirem mais infraestrutura.

## 3. Etapas executáveis

### E0 — Fixar o escopo e o contrato de medição

**Tarefas**

- Registrar o incremento futuro em `specs/002-observabilidade-e-avaliacao/`, com spec, decisões e tarefas proporcionais ao escopo. Preservar os registros históricos da V0/V1.
- Definir ambientes distintos: estudo, homologação e produção; identificar workspace, região, acesso aos recursos e orçamento de execução remota.
- Registrar versões resolvidas, commit, hashes de datasets/prompts/avaliadores e política de baseline. Conferir as APIs instaladas, especialmente consultas de runs, pytest e integração OTel; concentrar compatibilidade em um adaptador pequeno quando necessário.
- Definir o contrato mínimo: `case_id/thread_id`, identificador da invocação, ambiente, versão do código/prompt/modelo, operação, risco, resultado e versão da recomendação. IDs servem à correlação; gráficos usam dimensões de cardinalidade controlada.
- Distinguir uma invocação do grafo de um caso de negócio: `run` e cada `resume` podem gerar traces diferentes para o mesmo caso. Definir também a unidade de avaliação: uma versão de recomendação.

**Aceite:** as nove lacunas têm uma entrega e um critério de conclusão; contratos e versões estão registrados; cada etapa remota identifica acesso e recurso de que depende. A política de risco continua determinística, o DDL continua fora do escopo e a avaliação não decide a aprovação humana.

### E1 — Completar os dois exercícios locais

**E1.1 · Juiz fixture com erro observável**

- Estender `labs/08_judge.py` com um modo explícito, por exemplo `--fixture-biased`, preservando o ensaio atual e o caminho `--real`.
- Reutilizar as seis referências de `dados/juiz.json`. Acrescentar saídas fixas em `dados/juiz_enviesado.json`, com dois erros deliberados: aceitar a contradição de j02 e obedecer à instrução indevida de j05.
- Produzir concordância conjunta e por critério, contagens de falsos positivos/negativos, cobertura e a lista das discordâncias. Explicar, em cada uma, qual evidência permite detectar o erro.
- Manter a referência fora da entrada do juiz. Separar nota ausente, erro do avaliador e discordância válida.

**Aceite:** seis avaliações fixture válidas, duas discordâncias conhecidas e concordância conjunta de 4/6, reproduzíveis sem rede. Um cenário de falha do juiz demonstra que ausência de nota não vira aprovação. O capítulo 15 identifica esses resultados como simulação; seis casos não certificam um juiz para produção.

**E1.2 · Avaliações pelo pytest**

- Criar uma suíte de avaliação separada, inicialmente em `ESTUDOS_LANGSMITH/evals/`, reutilizando o target e os avaliadores existentes. Evitar outra implementação das regras de risco.
- Usar a integração oficial com `@pytest.mark.langsmith`, entradas, referências, saídas e feedback. Desabilitar envio por padrão com `LANGSMITH_TEST_TRACKING=false`, além de tracing; habilitar publicação somente no modo remoto explícito. Esse controle de tracking é documentado separadamente do tracing. [Integração oficial com pytest](https://docs.langchain.com/langsmith/pytest).
- Manter métricas por caso e métricas de conjunto distintas. O recall HIGH continua calculado sobre todas as referências HIGH; uma sequência de asserts individuais não substitui o relatório agregado.
- Demonstrar baseline aprovada e candidata HIGH→LOW reprovada. A execução deliberadamente reprovada deve ser verificada por seu exit code, sem deixar a suíte normal permanentemente vermelha.
- Registrar um experimento remoto quando houver acesso, com dataset, versão e métricas identificáveis. Isolar as fixtures que desligam tracing e testar que os modos locais não tentam acessar rede.

**Aceite:** os 16 IDs esperados são avaliados exatamente uma vez; baseline e mutação produzem os mesmos resultados do lab 06; o modo local funciona sem credenciais; a publicação é confirmada por um experimento real antes de ser declarada validada.

**Arquivos principais:** `labs/08_judge.py`, `dados/juiz_enviesado.json` (novo), `evals/` (novo), `tests/test_labs.py`, `15-juiz-llm-calibracao.md`, `23-ci-gates.md` e `verificar_material.py`.

### E2 — Dashboards nativos, retenção e exportação

**E2.1 · Painel de estudo no LangSmith**

- Gerar um conjunto pequeno e identificado de traces sintéticos com os labs existentes: sucesso, erro, retry recuperado e notas de feedback.
- Abrir o dashboard do projeto e criar um painel com volume, erros de raízes, latência, tokens/custo quando disponíveis e feedback. Separar dados de estudo, aplicação e avaliadores.
- Registrar projeto, janela, filtros, unidade e agrupamento de cada gráfico. Comparar contagens e métricas compatíveis com `16_consultar_runs.py` usando exatamente a mesma população e janela.
- Documentar o método de percentil quando houver diferença entre UI e cálculo local. Não comparar custo fictício de um lab com cobrança real.
- Guardar configurações e evidências da UI sem credenciais ou conteúdo sensível. A plataforma possui dashboards predefinidos e personalizados; a disponibilidade efetiva deverá ser confirmada na conta. [Dashboards do LangSmith](https://docs.langchain.com/langsmith/dashboards).

**Aceite:** painel acessível, configuração reproduzível e comparação documentada de pelo menos volume, erro e latência. Gráficos indisponíveis ou discrepâncias de agregação ficam registrados como limites, sem uma captura simulada apresentada como UI real.

**E2.2 · Retenção, cobrança e saída dos dados**

- Criar um guia operacional com política por tipo de dado: traces de rotina, falhas, feedback, datasets e arquivos exportados. Registrar responsável, prazo de retenção e procedimento de expiração de cada cópia.
- Explicar que feedback e automações podem promover traces à retenção estendida, com efeito na cobrança, e que datasets têm ciclo de retenção próprio. Conferir as condições no workspace e datar a consulta. [Retenção e cobrança](https://docs.langchain.com/langsmith/administration-overview).
- Criar uma estimativa parametrizada que separe ingestão/retenção, upgrade de retenção, modelo da aplicação, juiz e armazenamento externo. Considerar franquias e evitar contabilizar o trace estendido duas vezes. Valores didáticos continuam rotulados; preços efetivos vêm da conta e da [página de preços](https://www.langchain.com/pricing).
- Implementar exportação pequena por SDK para JSONL, com janela fechada, paginação, IDs únicos, feedback solicitado e manifesto. Reexecutar sem duplicar registros; não chamar esse caminho de exportação em massa.
- Validar o bulk export nativo para bucket compatível com S3, em Parquet, quando o plano permitir. A documentação consultada restringe esse recurso aos planos Plus/Enterprise. Registrar destino, job, campos, contagem e leitura posterior do arquivo. [Bulk export](https://docs.langchain.com/langsmith/data-export).

**Aceite:** a exportação pode ser lida localmente, reconciliada por IDs/contagens e retomada ou repetida sem duplicação; relações entre runs e campos ausentes ficam explícitos. Bulk export só é marcado concluído depois de um job real e arquivo verificado. Falta de plano elegível deixa esse subitem pendente e permite avançar nas demais entregas.

**Arquivos principais:** `22-operacao-slos-incidentes.md`, capítulos 09/10/18/19, `labs/17_exportar_runs.py` (novo) e `ops/langsmith/` (novo, apenas configurações e roteiros sem segredos).

### E3 — Preparar a telemetria do produto

**Tarefas**

- Conferir a configuração efetiva do Cloud Run e criar uma homologação com estado persistido e segredos próprios. Tornar o deploy parametrizável por ambiente.
- Habilitar tracing em homologação e acrescentar os metadados de E0 nas invocações e retomadas. Verificar sua presença nos filhos relevantes; não presumir propagação em toda integração.
- Expor um registro observável mínimo da recomendação com as evidências necessárias à avaliação. Aplicar minimização e sanitização antes do envio, incluindo notas humanas e entradas livres. Testar que o processamento para telemetria não altera o estado do grafo.
- Registrar sucesso técnico, interpretação recusada, pausa para revisão e degradação por evidência indisponível como situações distintas. Uma pausa esperada não é erro; resposta tecnicamente válida não prova qualidade semântica.
- Manter contagens de início/fim em logs de negócio independentes do exportador e reconciliá-las com traces recebidos. Assim, ausência de tráfego e falha de ingestão podem ser distinguidas; uma amostra de traces não fornece sozinha o total de pedidos.
- Registrar tempos de eventos de revisão para medir espera humana. Não estimar essa espera pela duração de um span nem apenas pelos casos finalizados.
- Verificar comportamento quando o exportador está indisponível, com envio assíncrono, limite de espera e finalização adequada. O caso de negócio precisa continuar e a perda de telemetria precisa ser observável.

**Aceite:** LOW finalizado, MEDIUM/HIGH pausado, retomada após reinício, interpretação recusada e evidência indisponível geram evidência rastreável. `case_id` liga os traces de execução/retomada ao registro de negócio. Desligar tracing preserva resultados, checkpoints e revisão humana. A integração pode ser revertida por configuração.

**Arquivos principais:** `src/dcra/graph/build.py`, `src/dcra/config.py`, um módulo pequeno em `src/dcra/observability/` (novo), pontos necessários em `nodes.py`, `.env.example`, `deploy/deploy.sh`, `DEPLOYMENT.md` e `docs/observability.md`.

**Conceito LangChain/LangGraph:** callbacks e contexto de execução transportam telemetria ao longo do grafo. São úteis para observar paralelismo e retomadas; logs estruturados seriam a alternativa mais simples. A decisão é defensável porque acrescenta visibilidade às fronteiras já existentes, sem criar novos nós de negócio para monitoramento.

### E4 — Eval online e SLOs de qualidade

**E4.1 · Ciclo de avaliação**

- Começar com avaliadores nativos de código para contratos verificáveis e um juiz amostrado para sustentação da recomendação. Configurações, filtros, rubricas e versões devem ficar registrados no repositório.
- Avaliar cada versão de recomendação concluída uma vez, identificada por run/recomendação/versão do avaliador. Filtrar por ambiente e finalidade para não avaliar traces dos próprios juízes nem contar todos os nós como novos pedidos.
- Adaptar a validação de código ao ambiente gerenciado: ele tem bibliotecas restritas e não acessa a rede. Não pressupor que possa importar `dcra` ou consultar o Postgres. [Avaliadores online de código](https://docs.langchain.com/langsmith/online-evaluations-code).
- Antes de ativar o juiz em produção, calibrá-lo com referências humanas revisadas, incluindo contradição, evidência ausente, aprovação indevida e injeção. Reservar casos que não foram usados para ajustar a rubrica. O juiz enviesado de E1 ensina a detectar falhas, mas não serve como certificação dessa calibração.
- Começar com amostra pequena, concorrência controlada e limite financeiro explícito; registrar elegíveis, selecionados, avaliados, inválidos, custo e atraso. Avaliação ocorre depois da resposta, sem entrar no caminho de aprovação do caso.
- Instituir triagem semanal pelo mantenedor e após violação de contrato crítico. Um caso selecionado é revisado, sanitizado, adicionado a um dataset versionado e usado para verificar uma correção.

**E4.2 · Painel e metas**

| Indicador | Denominador/unidade | Política inicial proposta |
|---|---|---|
| Contrato de revisão MEDIUM/HIGH | Transições elegíveis observadas, contando cada versão uma vez | Zero desvios; qualquer ocorrência exige triagem |
| Erro técnico | Invocações elegíveis de `run`/`resume` | Medir taxa e volume por ambiente e versão |
| Cobertura de avaliação | Avaliações válidas / recomendações selecionadas | Exibir junto de selecionadas/elegíveis, falhas e atraso |
| Groundedness / caráter não vinculante | Recomendações com avaliação válida | Exibir amostra e versão da rubrica; aprovação humana do caso não é rótulo de qualidade |
| Latência ativa | Invocações concluídas, excluindo espera humana | p50/p95 com `n` e recorte por caminho |
| Tempo de revisão | Casos que entraram em revisão | Espera dos concluídos e idade dos ainda abertos |
| Custo | Caso e versão de recomendação | Separar aplicação, avaliador e fonte da tarifa |

Para produção, usar uma janela inicial de observação de sete dias. Em baixo volume, ampliar a observação e declarar insuficiência de dados. Depois registrar alvos numéricos de disponibilidade, latência e qualidade, com população mínima e ação de resposta, com base nessa baseline. Percentis de um punhado de demos não viram compromisso operacional.

Manter recall HIGH como métrica offline sobre referências conhecidas. Uma distribuição de categorias em produção não fornece o denominador para medir recall. Para limites que o dashboard nativo não calcule, usar um relatório periódico pequeno sobre os mesmos dados, com sinal de violação e responsável definido.

**Aceite:** uma falha controlada em homologação recebe avaliação, aparece no painel, é triada e gera caso de regressão. Avaliador desligado ou com erro reduz cobertura e produz sinal próprio. A etapa de produção só termina após configuração ativa, janela observada e SLOs registrados; ensaio sintético continua identificado como homologação.

**Arquivos principais:** `ops/langsmith/`, `evals/` para avaliações do produto (novo, separado das demonstrações), capítulos 15/18/22, `docs/observability.md` e um roteiro operacional de triagem.

### E5 — Tornar a avaliação parte efetiva do release

**Tarefas**

- Criar workflow de CI, preferencialmente GitHub Actions se o repositório estiver nesse serviço, com lint, testes determinísticos, benchmark e relatório anexado. O gate local continua utilizável sem a plataforma.
- Reutilizar o benchmark de 16 casos como primeira proteção. Preservar o dataset didático; casos operacionais novos ficam em dataset de produto versionado.
- Exigir, inicialmente: `risk_correct >= 0.95`, `high_risk_recall == 1.0`, `review_correct == 1.0`, fatores e contrato de erro corretos, os IDs esperados sem duplicatas, ausência de falhas de avaliação e manifesto correspondente ao artefato candidato. Dataset vazio, HIGH ausente ou resultado incompleto não aprovam release.
- Acrescentar avaliação com modelo real para mudanças em prompts, modelo ou integração LLM. Reutilizar as referências de interpretação e a rubrica calibrada; comparar baseline e candidata no mesmo dataset, com versões fixadas e repetições predefinidas. Os testes fixture não substituem essa etapa.
- Exigir zero violações críticas nos casos revisados de interpretação/aprovação indevida. Fixar os demais limiares de qualidade, custo e latência após a baseline, antes de avaliar a candidata. Resultado inconclusivo impede promoção automática e pede análise, sem repetir até obter uma execução favorável.
- Ligar a promoção de imagem à aprovação dos jobs e ao commit/digest avaliado. Adaptar o caminho manual de deploy para consumir a mesma verificação e impedir o desvio acidental do gate.
- Manter envio ao LangSmith opcional no gate determinístico; indisponibilidade do SaaS não invalida um relatório local completo. Já a falta de uma avaliação real exigida deve deixar a promoção pendente.

**Aceite:** baseline passa; mutação HIGH→LOW, caso ausente/duplicado, erro do avaliador e relatório de outra versão bloqueiam promoção. Um release aprovado referencia a imagem efetivamente avaliada. O caminho com modelo real executa o código/prompt candidato e distingue cache/replay de nova medição.

**Arquivos principais:** `.github/workflows/evals.yml` (novo, se aplicável), `evals/`, `labs/12_regression_gate.py` ou um núcleo compartilhado pequeno, `Makefile`, `pyproject.toml`, `deploy/deploy.sh` e capítulo 23.

### E6 — Integrar Langfuse à aplicação

**Tarefas**

- Usar Langfuse Cloud como implantação inicial recomendada, evitando operar uma plataforma adicional apenas para a demonstração. Hospedagem própria fica como alternativa se houver requisito concreto de controle dos dados; a integração ao produto faz parte desta etapa em ambos os casos.
- Criar um perfil selecionável de observabilidade, inicialmente desligado por padrão, e conectar o `CallbackHandler` às invocações do DCRA, incluindo `resume`. A integração oficial usa callbacks de LangChain e suporta o mesmo padrão no LangGraph. [Integração Langfuse/LangChain](https://langfuse.com/integrations/frameworks/langchain).
- Preservar correlação de caso/sessão, metadados, sanitização e tratamento de falhas de E3. Fixar versões compatíveis em vez de depender de atualização irrestrita.
- Executar a mesma matriz de casos no DCRA com LangSmith e com Langfuse, em execuções identificadas. Comparar árvore, chamadas de modelo, ferramentas, tokens, erros e correlação da retomada.
- Habilitar o perfil em homologação publicada e depois em uma revisão controlada do produto. Manter o perfil operacional padrão enviando ao LangSmith para sustentar os evals de E4. Exercitar Langfuse na revisão identificada; dupla coleta permanente ou migração do ciclo de avaliação exige decisão registrada de custo e utilidade.

**Aceite:** traces do DCRA publicado aparecem no Langfuse, incluindo pausa/retomada e chamada real de modelo. O exemplo de restaurante não conta para esse aceite. Configurar um backend não duplica chamadas de negócio nem contabiliza a mesma geração duas vezes no mesmo destino; desabilitá-lo preserva o comportamento do produto.

**Arquivos principais:** `src/dcra/observability/`, `src/dcra/graph/build.py`, configuração/deploy, dependências opcionais, `docs/observability.md` e capítulo 21.

**Conceito LangChain/LangGraph:** callbacks desacoplam observação e execução. A alternativa mais simples é manter apenas LangSmith; Langfuse se justifica aqui pelo objetivo explícito de experimentar outro backend com os mesmos casos, sem reconstruir o workflow.

### E7 — Demonstrar coleta distribuída com OpenTelemetry

**Tarefas**

- Usar a fronteira de processos que já existe: aplicação → cliente MCP → servidor MCP por `stdio`. Propagar contexto por invocação em um portador de metadados definido e testado; verificar o suporte das versões instaladas antes de escolher o ponto de extensão. Não depender de variável de ambiente global para correlacionar chamadas concorrentes.
- Instrumentar cliente e servidor, associando spans ao contexto recebido. Se os adaptadores não expuserem metadados, fazer uma extensão estreita nessa fronteira e registrar a decisão; um serviço HTTP de demonstração separado não encerra a lacuna de integração do produto.
- Acrescentar um OpenTelemetry Collector em configuração de desenvolvimento/homologação, recebendo OTLP, aplicando limites de fila/lote e encaminhando ao destino selecionado. Usar a integração suportada pelo SDK instalado; conferir o modo de tracing e as convenções de atributos. [OpenTelemetry no LangSmith](https://docs.langchain.com/langsmith/trace-with-opentelemetry) e [modos de exportação](https://docs.langchain.com/langsmith/log-traces-to-project).
- Testar propagação explícita entre os processos e concorrência. OpenTelemetry fornece mecanismos de injeção/extração de contexto; a aplicação precisa transportar esse contexto na fronteira adotada. [Propagação em Python](https://opentelemetry.io/docs/languages/python/propagation/).
- Validar ingestão OTLP e versões do backend Langfuse, evitando APIs legadas de ingestão. Registrar mapeamentos e campos sem correspondência. [Compatibilidade do Langfuse](https://langfuse.com/docs/compatibility).
- Habilitar o caminho MCP instrumentado em homologação e no perfil publicado que será demonstrado. Testar indisponibilidade do MCP separadamente de indisponibilidade do Collector: a primeira afeta a evidência; a segunda afeta a telemetria.

**Aceite:** um pedido do DCRA gera spans em dois processos, com mesmo `trace_id`, relação pai/filho correta e `service.name` distinto. Pedidos concorrentes não misturam contexto. Remover a propagação em teste produz a quebra detectável da árvore. O Collector indisponível não impede a análise; o caminho MCP indisponível mantém a evidência `UNAVAILABLE` prevista pelo produto.

**Arquivos principais:** `src/dcra/mcp/client.py`, `src/dcra/mcp/server.py`, `src/dcra/observability/`, configuração do Collector e Compose/deploy, testes MCP, `docs/mcp.md` e capítulo 21.

**Conceito LangChain/LangGraph:** callbacks observam componentes do workflow, mas não garantem contexto entre processos. OTel acrescenta essa correlação; a alternativa simples é buscar logs pelo `case_id`. A decisão se sustenta pela fronteira MCP existente e pela demonstração de causalidade entre serviços, sem multiplicar a arquitetura de negócio.

### E8 — Consolidar evidências e encerrar o incremento

- Atualizar o mapa do projeto com estados precisos: proposto, implementado localmente, validado remotamente e implantado. Atualizar `README.md`, `CLAUDE.md` e `AGENTS.md` quanto ao status da evolução quando ela ocorrer.
- Manter o parecer de Claude como registro histórico, acrescentando referência às entregas posteriores quando concluídas.
- Atualizar capítulos afetados, desafios, caderno de evidências e capítulo 27 com comandos, versões, resultados e limitações realmente observados. Acrescentar as extensões ao roteiro como blocos extras, revendo tempos antes de alterar a promessa de três dias.
- Publicar uma demonstração curta: regressão rejeitada pela CI, erro detectado pelo juiz/triagem, painel com denominadores e trace do DCRA atravessando a fronteira MCP.
- Registrar configuração de retorno, recursos que devem permanecer ativos e rotina mínima do mantenedor. Qualquer pendência de conta, janela ou plano comercial permanece visível.

**Aceite final:** cada uma das nove linhas da matriz tem evidência verificável no nível prometido. Código local, configuração preparada e recurso implantado não recebem o mesmo status.

## 4. Validação e limites da execução

Em cada incremento de código, executar os checks exigidos por [CLAUDE.md](../CLAUDE.md), acrescentando a suíte de estudo quando afetada:

```bash
uv run pytest
uv run ruff check src tests
uv run pytest ESTUDOS_LANGSMITH/tests
uv run ruff check ESTUDOS_LANGSMITH
.venv/bin/python ESTUDOS_LANGSMITH/verificar_material.py
```

À medida que `evals/` e módulos operacionais forem criados, incluí-los nos comandos e no CI. Manter testes de modelo, Postgres, MCP, SaaS e Collector identificados por dependência. Registrar skips e o ambiente da execução; um teste pulado não valida a integração correspondente.

Os testes novos devem proteger falhas concretas: exportação involuntária no modo local, vazamento de contexto, perda de correlação após retomada, gate incompleto, juiz inválido e interferência da telemetria no fluxo de negócio. As execuções remotas usam conjuntos pequenos e orçamento definido para a etapa.

As principais dependências externas são acesso aos workspaces, recurso comercial de bulk export, segredos de homologação/produção e autorização operacional para publicar a evolução. Elas são necessárias no momento de executar essas etapas; nenhuma delas impede elaborar ou revisar este plano.

**Limite desta preparação:** foram lidos os arquivos citados, inspecionadas versões locais e consultadas fontes oficiais. Não foram acessados workspaces autenticados, alterado o Cloud Run, enviados traces nem executados modelos para produzir este plano.
