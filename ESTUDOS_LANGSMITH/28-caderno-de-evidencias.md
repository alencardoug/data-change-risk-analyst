# 28 · Meu caderno de evidências

[Índice](README.md) · [Anterior](27-fontes-e-validacao.md) · [Próximo: acompanhar produção](29-acompanhar-producao.md) · [Roteiro de três dias](00-roteiro-3-dias.md)

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

Juiz simulado (`--fixture-biased`): as duas discordâncias que eu encontrei **antes** de ler as notas do material; falsos positivos por critério; o que mudou com `--judge-error j04`:

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
| Suíte pytest `evals/` | 17 aprovados na baseline; casos e teste de conjunto que falham com `--variant bug`; exit de `-k c01` com e sem `--parcial`; `complete` do relatório | |
| Exportação (lab 17) | Identidade e diretório; `novos/ja_presentes/fora_da_janela` nas duas execuções, SHA-256 igual; recusa com `--conteudo` no mesmo diretório; modo `--send` executado ou não | |
| Retenção e custo | Parâmetros que troquei em `estimativa_mensal` e a fonte/data dos preços, ou “fictício” | |
| Painel nativo | Projeto, janela, filtro, unidade e agrupamento de cada gráfico; volume/erro iguais ao lab 16?; latência: método | |
| Produção (cap. 29) | Teto de gasto definido; visitas na janela (com e sem robôs); casos, risco, espera p50/p95 com `n` do lab 18; tracing ligado ou não; custo por caso e como o calculei | |
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

## Levar para outros projetos — e onde o seu julgamento decide

O caderno é o artefato mais simples do curso e o que mais depende de você: **hipótese, execução, observação, conclusão, o que ainda não sei**. Nenhuma linha dele pode ser preenchida por outra pessoa — ou por um assistente — sem deixar de ser evidência.

**Na plataforma de atendimento (Langfuse Cloud).** O `caderno_de_evolucao.md` daquele projeto tem a mesma estrutura, com fichas adaptadas ao domínio e — em setembro de 2026 — quase todos os campos como "Pendente": fotografia inicial (commit, modelos, hashes de prompts, snapshot do corpus, configuração N5, versão do SDK, referência de data das ofertas), ficha de caso observado (pedido, sequência de mensagens, resultado esperado com referência, resposta enviada, conversa/trace/observação/mensagem, caminho e mecanismo efetivos, falha percebida, critério e gravidade, etapa suspeita, estado do diagnóstico: *sem causa / hipótese / confirmado por experimento*), fila H01–H05, ficha de experimento (com "o que poderia refutar a hipótese" e "reserva de conferência final sem uso na elaboração" — dois campos que este caderno não tem e vale importar), e relatório por caminho com contagens e denominadores antes de porcentagens. "Pendente não é resultado negativo; indica trabalho ainda não executado" — a mesma disciplina de "não executei esta etapa com modelo real". A ficha de caso é o elo entre os dois cadernos: um trace ruim lido na sessão LF-6 vira uma ficha; a ficha vira um item de dataset com `source_trace_id`; o item vira uma linha no relatório por caminho. Sem a ficha, o dataset "cai do céu" — a observação do roteiro de três dias.

**Em projetos comuns do ecossistema.** Cinco linhas por experimento, sempre; campos vazios em vez de inventados; IDs e URLs só depois de vistos; "envio solicitado; ingestão não conferida" como estado legítimo; e a distinção entre resultado esperado, observado e conclusão permitida. Um caderno assim é o que torna uma decisão de seis meses atrás reconstruível — e é o que falta na maioria dos projetos com LLM, onde "testamos e melhorou" não tem rastro.

**O fator humano — onde a IA faz e onde você decide.** Aqui a fronteira é absoluta. Um assistente pode gerar um caderno inteiro, preenchido, coerente, com números plausíveis — e ele não vale nada, porque o valor do caderno é ser o registro do que **você** previu, rodou, viu e concluiu. Uma nota escrita pela IA sobre um experimento que ela não rodou é ficção com formatação de evidência; e uma nota escrita pela IA sobre um experimento que ela rodou ainda precisa da sua leitura, porque "o que posso concluir" e "o que ainda não sei" são julgamentos, não saídas. Foque em: (1) escrever a **hipótese** antes — é a linha que mais protege contra se convencer depois; (2) escrever "o que ainda não sei" com honestidade — é a linha que orienta o próximo experimento e a que a IA tende a omitir, porque tende a fechar; (3) usar a IA para o que ela faz bem no caderno: extrair IDs e números da saída de um comando, formatar a tabela, apontar uma ficha incompleta. Na plataforma, a sessão LF-6 é "humano + Claude Code" por desenho — a IA abre o trace, você julga a conversa; a ficha de caso registra o seu julgamento. Mantenha assim. O caderno é o lugar em que a sua crítica deixa de ser opinião e vira dado — e por isso é o lugar que não se delega.
