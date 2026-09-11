# 23 · Quando a nota vira uma decisão de release

[Índice](README.md) · [Anterior](22-operacao-slos-incidentes.md) · [Próximo](24-entrevista-simulada.md)

**Objetivo:** ver uma regressão impedir a aprovação de uma candidata, primeiro por um gate que lê um relatório, depois pela mesma avaliação escrita como suíte pytest. Tempo: 25–30 minutos. Código: [12_regression_gate.py](labs/12_regression_gate.py) e [evals/](evals/test_contratos_dcra.py). Nenhum pipeline remoto será criado.

Uma eval calcula medidas. Um gate aplica uma política de aceitação a essas medidas. A política envolve o problema de negócio: qual regressão é intolerável e que trade-offs são aceitáveis?

## Execute

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/06_evaluate.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/12_regression_gate.py --candidate baseline
.venv/bin/python ESTUDOS_LANGSMITH/labs/12_regression_gate.py --candidate bug
```

A baseline deve passar. O último comando deve mostrar `FAIL` e terminar com **exit code 1**. Esse erro é o sucesso didático do detector, não um comando quebrado que precisa ser “arrumado” para ficar verde.

O gate exige:

- acerto de risco pelo menos 95%;
- recall dos HIGH igual a 100%;
- contrato de revisão correto em todos os casos;
- os 16 exemplos esperados;
- hashes atuais de código/dados iguais aos registrados no relatório.

Os limiares foram escolhidos para este exercício e seu erro deliberado. Eles não são um padrão universal recomendado para toda aplicação.

## A mesma avaliação como suíte pytest

O gate acima lê um JSON. Muitos times preferem que a avaliação **seja** um job de teste: cada caso é um teste, o exit code é o veredito e o relatório vai para a plataforma quando se quer. O SDK tem uma integração com pytest para isso; a pasta [evals/](evals/test_contratos_dcra.py) usa a integração sobre o mesmo target e os mesmos avaliadores do lab 06 — nenhuma regra de risco foi reimplementada.

```bash
uv run pytest ESTUDOS_LANGSMITH/evals
uv run pytest ESTUDOS_LANGSMITH/evals --variant bug; echo "exit=$?"
```

A primeira execução mostra 17 testes aprovados: 16 casos e um teste de conjunto. A segunda aplica a mutação HIGH→LOW e termina com **exit code 1**: falham c03, c04 e c07 — os três HIGH — e o teste de conjunto, porque o recall HIGH caiu a zero. O relatório fica em `artefatos/evals-<variante>.json`, com os mesmos números do lab 06; um teste do curso confere essa igualdade.

Três decisões de desenho merecem ser explicadas na entrevista:

- **Um caso por teste, e um teste para o conjunto.** `risk_correct` de cada caso é um assert. O recall HIGH não é: ele precisa de todas as referências HIGH no denominador. Por isso existe `test_conjunto_completo_com_recall_high`, que também exige que os 16 ids esperados tenham sido avaliados exatamente uma vez, e aplica a política registrada em `_suite.py` (`POLITICA`), copiada para o relatório.
- **Um subconjunto verde não aprova.** Rode `-k c01`: o caso passa, mas a sessão termina em **exit 1** com a mensagem `GATE: avaliação incompleta (1/16 casos)`, porque `-k` também deixa o teste de conjunto de fora — e um gate que dependesse de alguém lembrar de selecioná-lo não seria gate. Para investigar um caso sem essa reprovação, declare a intenção: `-k c01 --parcial`. O relatório sai com `complete: false` e `parcial: true` nos dois casos; antes de cada execução o relatório anterior da mesma variante é apagado, para que um resultado velho nunca passe pelo atual.
- **Registrar antes de afirmar.** Cada caso grava sua linha no coletor **antes** do assert. Se gravasse depois, um caso reprovado sumiria do conjunto e o recall seria calculado sobre menos casos — o mesmo erro do juiz que ignora falhas.
- **O agregado fica fora do dataset.** O teste de conjunto não leva `@pytest.mark.langsmith`: o plugin sincroniza cada teste marcado como um exemplo do dataset, e “recall do conjunto” não é um caso de negócio — iria aparecer como um 17º exemplo, diferente a cada variante. O conjunto vive no relatório local; para publicar um agregado, o caminho é o `summary_evaluators` do lab 06/13.
- **Local por padrão, remoto por decisão.** `@pytest.mark.langsmith` lê `LANGSMITH_TEST_TRACKING` no momento em que o módulo é importado. O `conftest.py` da pasta fixa `false` antes da coleta, além de desligar o tracing, e bloqueia `socket` — se a suíte tentar rede no modo local, o teste quebra. Tracking de testes e tracing são controles separados: um cria exemplos e feedback num dataset, o outro envia runs.

Com conta configurada, o modo remoto é explícito:

```bash
DCRA_EVALS_REMOTE=1 uv run pytest ESTUDOS_LANGSMITH/evals
```

Ele exige `LANGSMITH_API_KEY`, publica os 16 casos no dataset `dcra-evals-contratos` e cria um experimento `dcra-evals-<variante>:<sufixo>` com os inputs de cada caso, o gabarito como referência, as saídas e o feedback por avaliador; `LANGSMITH_EXPERIMENT_METADATA` leva variante e versão dos avaliadores. Na UI, 13/16 casos aprovados e 13/17 testes aprovados respondem a perguntas diferentes; o número que importa é o dos casos. **Esse modo não foi executado durante a validação do material** — a assinatura da integração foi inspecionada no SDK instalado e a semântica vem da [documentação do pytest no LangSmith](https://docs.langchain.com/langsmith/pytest). Ao executá-lo, registre dataset, experimento e a comparação com o lab 13 no [caderno](28-caderno-de-evidencias.md).

## Experimento de resultado velho

Depois de gerar o relatório, qualquer alteração em um dos arquivos incluídos no manifesto faz a checagem de correspondência falhar. Em vez de editar arquivos só para testar isso agora, abra o código e explique o risco que a condição evita: aprovar uma versão usando resultados produzidos antes da última alteração.

Para uma alteração real, reexecute o benchmark e gere novo relatório. A política deste laboratório inclui hashes de vários scripts, de forma conservadora; uma CI de produção pode delimitar com mais precisão quais artefatos determinam aquele target.

## Onde entraria numa CI real

Um desenho pequeno poderia executar:

```text
validar código e contratos determinísticos
  → executar benchmark de componentes afetados
  → verificar completude, versões e falhas de avaliação
  → comparar com baseline e gates por risco
  → produzir relatório revisável
  → promover segundo o processo do time
```

A suíte `evals/` é a forma executável desse desenho até a linha do relatório: `uv run pytest ESTUDOS_LANGSMITH/evals` seria o job, o exit code seria o status e `evals-<variante>.json` o artefato anexado. A integração com testes é parte das práticas documentadas de [avaliação](https://docs.langchain.com/langsmith/evaluation-concepts). Este repositório não tem um workflow de CI versionado; o deploy é um script manual, e ligar a promoção da imagem a essa suíte é uma evolução do produto, registrada como pendente no [plano](PLANO_DE_DESENVOLVIMENTO.md).

## Os erros que um gate ingênuo aceita

Uma média de 100% entre duas respostas recebidas não deve passar se o experimento deveria ter 80 casos. Uma nota anterior não deve representar um prompt novo. Um juiz indisponível não deve gerar uma aprovação por ausência de reprovações.

Por isso, verifique completude e integridade antes dos limiares — é o que a suíte faz ao terminar a sessão, e o manifesto do relatório inclui os hashes dos próprios arquivos de `evals/`, porque mudar a política de aprovação também muda a identidade da avaliação. Em avaliações probabilísticas, planeje repetições e critérios de incerteza. Reexecutar até uma versão instável “dar verde” introduz viés e esconde a instabilidade que você deveria medir.

Além de qualidade, pode existir gate de latência, custo por sucesso e invariantes de processo. Cuidado para não criar metas incompatíveis: um ganho pequeno de tempo não compensa remover revisão dos HIGH se a revisão é requisito de negócio.

## Pergunta de entrevista

“Vocês garantem que uma mudança de prompt não causa regressão?” Uma resposta precisa é: “Não garantiria ausência universal de regressão. Usaria datasets versionados, critérios por capacidade e por risco, comparação com baseline e monitoramento depois da promoção. Neste estudo executei um gate que rejeita uma mutação HIGH→LOW e recusa relatórios incompatíveis com os arquivos atuais, e a mesma avaliação como suíte pytest, que reprova a mutação pelo exit code.”

**Memorize:** *quality gate*, *regression budget*, *artifact integrity*, *evaluation completeness*, *release criterion*, *test tracking*.

## Levar para outros projetos — e onde o seu julgamento decide

Uma eval calcula; um gate **decide**. A política dentro do gate — o que é intolerável, o que é aceitável, o que invalida o relatório — é a parte que não se automatiza sem alguém assiná-la.

**Na plataforma de atendimento (Langfuse Cloud).** O gate está escrito, ainda sem CI: o critério de seleção de prompt do §6.4 (nenhuma nova falha crítica; nenhuma queda não explicada na conferência final; melhoria no critério-alvo; custo/latência apresentados; ambíguo = continua candidato) e a aceitação da Fase 0 (§4.5: três caminhos demonstrados, um trace cada; Langfuse parado / flag `false` → atendimento e `pytest` intactos; `smoke_*` e gates de backend/frontend passam). Os "erros que um gate ingênuo aceita" têm equivalentes concretos ali: uma média 2/2 em utilidade quando deveriam ser 30 casos (completude); um relatório gerado com prompts `ativo` de ontem para aprovar a versão de hoje (correspondência de artefatos — o manifesto do §6.3 inclui versões/hash dos prompts e do corpus por isso); um juiz que devolveu `INCONCLUSIVE` em 20 casos e "não reprovou nenhum" (falha do medidor). A regra "registrar antes de afirmar" da suíte pytest tem uma versão de dados: `smoke_ingestion_changed.py` reverte embeddings; um gate que rode sobre um catálogo com embeddings de teste está avaliando outra coisa — o manifesto precisa de `embedding_model` e contagem do corpus, e o gate precisa conferi-los. A integração LF-5 usa projeto Compose separado e banco `oncology_langfuse_test` — é a "CI" mínima daquele projeto: um ambiente que não é o cotidiano, com estado inicial restaurado. No Langfuse, o relatório de um *dataset run* com scores por item é o artefato; o exit code continua sendo do seu runner.

**Em projetos comuns do ecossistema.** O desenho pequeno serve para qualquer stack: validar contratos determinísticos → benchmark dos componentes afetados → completude, versões e falhas de avaliação → comparação com baseline e gates por risco → relatório revisável → promoção segundo o processo do time. Um subconjunto verde não aprova (`-k c01` termina em 1 sem `--parcial`). Reexecutar até "dar verde" esconde a instabilidade que você deveria medir. E gates conflitantes: latência versus revisão obrigatória dos casos críticos.

**O fator humano — onde a IA faz e onde você decide.** Um assistente escreve a suíte, o coletor, o gate de completude e o job de CI — e o faz bem, porque é engenharia. O que é irredutivelmente seu são os **limiares e a política**: "recall dos HIGH = 100%" e "acerto ≥ 95%" foram escolhidos para este exercício; na plataforma, "nenhuma nova falha crítica" e "nenhuma queda não explicada na conferência final" são escolhas sobre o que o serviço pode arriscar com um paciente. Ninguém deve delegar isso, e vale registrar quem decidiu e quando. Foque em três pontos. Primeiro, **resistir a relaxar o gate** quando ele reprova: a IA, pedida para "fazer o pipeline passar", propõe ajustar o limiar, marcar o caso como não aplicável ou pular o teste de conjunto — todas mudanças válidas em código e erradas em política, e a decisão entre "o critério estava errado" e "o sistema está errado" é sua (capítulo 12). Segundo, ler o relatório reprovado antes de qualquer correção: a linha que falhou é informação; o verde é só ausência dela. Terceiro, a promoção: o contrato da plataforma diz "a seleção é uma decisão explícita do usuário, não um comando do avaliador" — o gate reprova sozinho, mas **aprovar** é um ato humano, e é assim que deve continuar enquanto o que se promove afeta pessoas.
