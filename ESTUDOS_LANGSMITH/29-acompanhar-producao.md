# 29 · Alguém usa isto? — tráfego, uso e custo do app publicado

[Índice](README.md) · [Anterior](28-caderno-de-evidencias.md) · [Roteiro de três dias](00-roteiro-3-dias.md)

**Objetivo:** responder “alguém usa o app, o que faz nele e quanto custa” sem escrever código novo no produto. Tempo: 30–40 minutos, mais o que as contas pedirem. Código: [18_uso_producao.py](labs/18_uso_producao.py). Este é um **bloco extra**, fora da rota de três dias; acrescentado em 11 de setembro de 2026.

O curso inteiro mede coisas: contratos, regressões, custo por chamada, latência por nó. E a pergunta mais simples de operação ficou sem resposta: **alguém usa?** Ela tem três respostas diferentes, porque “usar” tem três significados, e cada um mora numa fonte que já existe.

| O que você quer saber | Onde já está | O que falta | Custo |
|---|---|---|---|
| Visitas ao app (tráfego) | Cloud Run registra requisições, latência e instâncias | Nada: abrir a aba **Métricas** | zero |
| Uso real: casos analisados, risco, decisões, espera | O app grava cada análise concluída no banco (Neon) | Sete consultas, prontas no lab 18 | zero |
| Dentro de cada caso: tokens, custo, erros, tempo por etapa | O código já envia ao LangSmith; está **desligado** no deploy | Um segredo, uma variável e republicar | zero até 5 mil traces/mês |

Os três números não batem entre si, e não deveriam: visitas ≠ pedidos ≠ casos concluídos. O capítulo [22](22-operacao-slos-incidentes.md) chamou isso de escolher o denominador. Aqui é a mesma lição com dados de verdade.

## Camada 0 — antes de olhar, limite o gasto

O app é público e sem login, e cada análise chama o modelo da OpenAI. Isso já é verdade hoje, com ou sem observabilidade: um robô ou uma pessoa entediada gera custo. Antes de divulgar o link ou ligar qualquer coisa nova:

1. Na OpenAI, defina um **limite mensal** para o projeto ou a organização (Configurações → *Limits*/*Budgets*; o nome muda). É um disjuntor, não um medidor — a distinção do [capítulo 09](09-tokens-custos-orcamentos.md).
2. No Google Cloud, crie um **alerta de orçamento** para o projeto, como o `DEPLOYMENT.md` já recomenda. Cloud Run e Neon ficam nas faixas gratuitas em tráfego de demonstração; o alerta existe para o dia em que não ficarem.
3. O LangSmith, no plano Developer, é gratuito até a franquia de traces do mês. O que acontece acima dela — cobrança por uso ou pausa da ingestão — depende de haver pagamento cadastrado na conta; confira lá antes de contar com um ou outro.

## Camada 1 — visitas: o Cloud Run já conta

Console do Google Cloud → **Cloud Run** → serviço `dcra` (região `us-east1`, os valores padrão de [deploy.sh](../deploy/deploy.sh)) → aba **Métricas**. Você vê contagem de requisições, latência, instâncias ativas e tempo faturável, por período. Nada a instalar.

Duas coisas que esses gráficos **não** dizem:

- **Requisição não é pessoa.** O Streamlit abre um websocket por sessão e faz chamadas de saúde (`/_stcore/health`) e de arquivos estáticos. Uma visita são dezenas de requisições; uma aba esquecida aberta também conta.
- **URL pública recebe robôs.** Rastreadores batem em `/` sem nunca submeter um pedido. Só o banco diz quem analisou alguma coisa.

Para contar carregamentos da página inicial e ver quem chegou, os logs de requisição servem melhor que o gráfico. Um ponto de partida — **não executado nesta validação**; a sintaxe vem da linguagem de consulta do Cloud Logging, confira na sua conta:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="dcra"
   AND httpRequest.requestMethod="GET" AND httpRequest.requestUrl=~"^https://[^/]+/?$"' \
  --freshness=7d --format="table(timestamp, httpRequest.status, httpRequest.userAgent)"
```

Anote no caderno: janela, quantas linhas, quantas com *user agent* de navegador, quantas de robô. Esse é o numerador honesto de “visitas”. A URL divulgada, `analisador-de-risco.web.app`, é um redirecionamento do Firebase Hosting para o Cloud Run; o Hosting tem contadores próprios, mas a requisição que importa é a que chega ao serviço.

## Camada 2 — uso real: o banco do app

Cada caso **finalizado** vira um registro em `analysis_record` (o nó `finalize`, em [nodes.py](../src/dcra/graph/nodes.py)). O lab 18 lê essa tabela com sete consultas, cada uma com a pergunta e o denominador escritos ao lado:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/18_uso_producao.py            # imprime o SQL, pronto para colar
.venv/bin/python ESTUDOS_LANGSMITH/labs/18_uso_producao.py --db --dias 30   # roda em DATABASE_URL, só leitura
```

| Consulta | Pergunta | Denominador |
|---|---|---|
| `casos_por_dia` | quantos casos concluídos, por dia **do pedido** | registros finalizados na janela |
| `risco_final` | qual categoria a última avaliação deu | idem; sem avaliação aparece como `SEM_AVALIACAO`, não como LOW |
| `desfechos` | automático, aprovado ou rejeitado; com ou sem revisão | idem |
| `devolucoes` | quantos revisores devolveram (RETURN) e quantas versões foram precisas | só casos revisados |
| `espera_humana_s` | do pedido à última decisão humana: p50, p95, máximo, `n` | só casos revisados **e concluídos** |
| `tempo_ate_concluir_s` | do pedido à finalização, separado por revisado/não | não se somam: um é tempo de máquina, o outro inclui gente |
| `iniciados_vs_concluidos` | threads com checkpoint contra registros | quem parou na revisão, abandonou ou falhou está só no primeiro número |

O modo `--db` abre uma transação **somente leitura**; o script não tem nenhuma instrução de escrita. Para produção, `DATABASE_URL` é a mesma string do Neon que está no Secret Manager, com `sslmode=require`; alternativa sem Python é colar o SQL impresso no editor do Neon.

**Duas armadilhas que só apareceram com dados reais.** As consultas foram validadas contra o banco de desenvolvimento desta máquina (28 registros, 11 de setembro de 2026), e as duas primeiras versões estavam erradas:

1. `created_at` do registro é a hora da **finalização**, não do pedido — o objeto é criado dentro de `finalize`. Medir a espera humana como `decided_at − created_at` deu **−0,01 s**. A hora do pedido está em `change_request.submitted_at`; corrigido, a espera ficou em p50 = 158 s e p95 ≈ 2 h, com `n = 7`.
2. Dezenove registros vinham sem avaliação de risco: eram fixtures dos testes do produto gravadas no banco de desenvolvimento. `risk_assessments->-1->>'category'` devolve `NULL` para eles, e um agregado que ignorasse o `NULL` teria mostrado 9 casos “com risco” num total de 28 sem avisar. O SQL agora nomeia o buraco: `SEM_AVALIACAO`.

Nenhum desses dois números é de produção. Eles estão aqui porque mostram o método: rodar a consulta, desconfiar do resultado, achar o campo certo.

## Camada 3 — dentro de cada caso: ligar o que já existe

O produto já tem integração com LangSmith (ligada por padrão no [.env.example](../.env.example), pela ADR-013); até 11 de setembro de 2026 o deploy a desligava com `LANGSMITH_TRACING=false`. Nessa data a configuração foi alterada **no repositório** — [deploy.sh](../deploy/deploy.sh) e [create-secrets.sh](../deploy/create-secrets.sh) — como correção pontual registrada no [plano](PLANO_DE_DESENVOLVIMENTO.md): é configuração, não código do grafo, e o [DEPLOYMENT.md](../DEPLOYMENT.md) descreve o novo estado. O que mudou e o que ainda falta para valer em produção:

1. **Segredo.** `create-secrets.sh` cria ou rotaciona `dcra-langsmith-api-key` a partir de `LANGSMITH_API_KEY` e dá o mesmo acesso da conta de serviço do Cloud Run. Ele grava **só as variáveis exportadas** e mantém os segredos cujas variáveis não estão no ambiente — proteção contra um `source .env` distraído, em que `DATABASE_URL` aponta para o `localhost` do docker e sobrescreveria o Neon. Reusar a chave do `.env` local é aceitável.

2. **Deploy.** `deploy.sh` liga `LANGSMITH_TRACING=true` e `LANGSMITH_PROJECT=dcra-prod` — um projeto **próprio** para produção, para não misturar com `dcra-estudos` nem com o `dcra` local — e recusa publicar se algum dos três segredos faltar. Para desligar sem editar nada: `LANGSMITH_TRACING=false deploy/deploy.sh`. O diff aplicado:

   ```diff
   +LANGSMITH_TRACING="${LANGSMITH_TRACING:-true}"
   +LANGSMITH_PROJECT="${LANGSMITH_PROJECT:-dcra-prod}"
   +for secret in dcra-database-url dcra-openai-api-key dcra-langsmith-api-key; do
   +  gcloud secrets describe "$secret" >/dev/null 2>&1 \
   +    || { echo "Missing secret $secret — run deploy/create-secrets.sh first." >&2; exit 1; }
   +done
    ...
   -  --set-secrets="DATABASE_URL=dcra-database-url:latest,OPENAI_API_KEY=dcra-openai-api-key:latest" \
   -  --set-env-vars="...,LANGSMITH_TRACING=false"
   +  --set-secrets="DATABASE_URL=dcra-database-url:latest,OPENAI_API_KEY=dcra-openai-api-key:latest,LANGSMITH_API_KEY=dcra-langsmith-api-key:latest" \
   +  --set-env-vars="...,LANGSMITH_TRACING=${LANGSMITH_TRACING},LANGSMITH_PROJECT=${LANGSMITH_PROJECT}"
   ```

   O app não depende do LangSmith para funcionar (capítulo [06](06-threads-checkpoints-revisao.md): o checkpoint é do banco, não do trace).

3. **Publicar.** `deploy/deploy.sh`, com `gcloud` autenticado. **Executado em 11 de setembro de 2026:** revisão `dcra-00002-kcv` no ar com 100% do tráfego, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=dcra-prod` e os três segredos montados; `/_stcore/health` respondeu 200 e o redirecionamento de `analisador-de-risco.web.app` continua apontando para a mesma URL. Nenhuma análise foi submetida nessa validação, então o projeto `dcra-prod` só nasce no LangSmith com o primeiro caso real.

4. **Ler.** Abra o projeto `dcra-prod` no [LangSmith](https://smith.langchain.com). O painel do projeto mostra volume por dia, erros, latência e tokens/custo — o modelo é `gpt-4o`, que a tabela de preços da plataforma reconhece, então o custo aparece sem configuração. Cada `run` e cada `resume` é uma **raiz**; um caso com revisão tem duas ou mais raízes com o mesmo `thread_id`. Para “custo por caso”, some por thread e divida pelos casos do banco — não pelas raízes.

5. **Privacidade e retenção.** O trace guarda o texto que qualquer visitante digitou. É um app de demonstração, mas registre isso; se um dia entrar dado real, o [capítulo 19](19-privacidade-amostragem.md) tem os processadores de redação. Sem feedback pela API e sem avaliador com retenção ligada, nada é promovido à faixa estendida ([22](22-operacao-slos-incidentes.md)): os traces expiram na faixa base e a fatura é zero.

**E o E4 do plano?** Avaliador online, metas de qualidade e triagem semanal só fazem sentido quando a camada 2 mostrar casos suficientes para haver o que triar. Até lá, “acompanhar” é abrir as três fontes uma vez por semana e anotar quatro números: visitas, casos, custo, espera. Foi o que este capítulo entregou.

## O que este capítulo não afirma

Não foram executados nesta validação: o comando `gcloud logging read`, uma análise real no app publicado e, portanto, a leitura de um trace em `dcra-prod`. Foram executados, em 11 de setembro de 2026: `create-secrets.sh` (mantendo os dois segredos existentes e criando o terceiro) e `deploy.sh` (revisão `dcra-00002-kcv`, saúde 200, redirecionamento intacto). Foram executados: o lab 18 nos dois modos contra um Postgres local (`docker compose up -d postgres`), e o teste que o cobre — que insere três registros, confere as sete consultas e apaga o que inseriu; sem banco alcançável ele é **pulado**, não aprovado. O teste se recusa a rodar contra um host que não seja local.

**Pergunta de entrevista:** “Como você sabe se o sistema é usado e quanto custa por caso?” Uma resposta precisa: “Três fontes, três denominadores. Requisições no Cloud Run dizem se alguém chega, inclusive robôs. O banco diz quantos casos foram concluídos, com que risco e quanto o revisor esperou — só dos concluídos; os parados estão nos checkpoints. O LangSmith diz o custo por execução, e custo por caso é a soma por thread dividida pelos casos do banco. Antes de ligar qualquer um deles, coloquei um teto de gasto na OpenAI, porque o app é público.”

**Memorize:** *traffic vs usage*, *survivorship* (só os concluídos aparecem), *read-only transaction*, *cost per case*, *budget cap*, *request time vs finalization time*.
