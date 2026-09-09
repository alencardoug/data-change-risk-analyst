# 23 · Quando a nota vira uma decisão de release

[Índice](README.md) · [Anterior](22-operacao-slos-incidentes.md) · [Próximo](24-entrevista-simulada.md)

**Objetivo:** ver uma regressão impedir a aprovação de uma candidata. Tempo: 15–20 minutos. Código: [12_regression_gate.py](labs/12_regression_gate.py). Nenhum pipeline remoto será criado.

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

Você pode rodar evaluators via SDK e transformar resultados em asserts ou um status de job. A integração com testes é parte das práticas documentadas de [avaliação](https://docs.langchain.com/langsmith/evaluation-concepts). Não é necessário criar uma nova plataforma de CI para entender esse fluxo.

## Os erros que um gate ingênuo aceita

Uma média de 100% entre duas respostas recebidas não deve passar se o experimento deveria ter 80 casos. Uma nota anterior não deve representar um prompt novo. Um juiz indisponível não deve gerar uma aprovação por ausência de reprovações.

Por isso, verifique completude e integridade antes dos limiares. Em avaliações probabilísticas, planeje repetições e critérios de incerteza. Reexecutar até uma versão instável “dar verde” introduz viés e esconde a instabilidade que você deveria medir.

Além de qualidade, pode existir gate de latência, custo por sucesso e invariantes de processo. Cuidado para não criar metas incompatíveis: um ganho pequeno de tempo não compensa remover revisão dos HIGH se a revisão é requisito de negócio.

## Pergunta de entrevista

“Vocês garantem que uma mudança de prompt não causa regressão?” Uma resposta precisa é: “Não garantiria ausência universal de regressão. Usaria datasets versionados, critérios por capacidade e por risco, comparação com baseline e monitoramento depois da promoção. Neste estudo executei um gate que rejeita uma mutação HIGH→LOW e recusa relatórios incompatíveis com os arquivos atuais.”

**Memorize:** *quality gate*, *regression budget*, *artifact integrity*, *evaluation completeness*, *release criterion*.
