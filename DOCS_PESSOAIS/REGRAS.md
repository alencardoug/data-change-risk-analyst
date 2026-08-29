# REGRAS — a política de risco LOW / MEDIUM / HIGH

Tudo aqui vem de um único arquivo: `src/dcra/rules/risk.py`. É **código Python puro** — nenhuma
chamada de LLM, nenhuma aleatoriedade. Mesma entrada → sempre a mesma saída (é literalmente o que
o teste `tests/unit/test_risk_rules.py` verifica).

## Por que isso não é decidido pela IA

Esta é a decisão mais importante do projeto para defender em entrevista (README, seção "Three
decisions worth defending", ponto 2). A classificação de risco precisa ser **previsível,
auditável e testável** — se o LLM decidisse "MEDIUM" ou "HIGH", a mesma pergunta poderia dar
respostas diferentes em dias diferentes, e ninguém conseguiria explicar por que um caso foi
classificado de um jeito sem rodar o modelo de novo. Regras determinísticas são a diferença entre
"o sistema disse que é arriscado" e "o sistema disse que é arriscado **porque** a coluna está
numa foreign key — aqui está a prova". O LLM só entra depois, para redigir a recomendação em
linguagem natural — ele nunca escolhe a categoria nem decide o roteamento do grafo.

## O algoritmo, em uma frase

`assess(mudança, evidências) → categoria = a maior severidade entre os "fatores" que dispararam`.

Cada fator é um predicado nomeado (`RiskFactor`: `code`, `description`, `severity`) testado contra
a evidência coletada. Zero ou mais fatores disparam; a categoria final é o `max()` de suas
severidades (`LOW=0 < MEDIUM=1 < HIGH=2`, `RiskCategory.severity` em `src/dcra/domain/enums.py:19`).
Se nenhum fator disparar, um fator `NO_DEPENDENTS_OR_USAGE` (LOW) é adicionado — nunca existe uma
avaliação sem pelo menos um fator explicando o "porquê".

## Caminho especial: ativo não encontrado → sempre HIGH

Antes de qualquer outra regra, `asset_not_found()` verifica se a busca de metadados retornou
"não encontrado" (`EvidenceStatus.UNAVAILABLE` com `payload.reason == "not_found"`). Se sim, o
único fator é:

| Código | Severidade | Descrição |
|---|---|---|
| `ASSET_NOT_FOUND` | **HIGH** | "Affected asset was not found in the evidence source." |

Nenhuma outra regra roda. Racional: se o sistema não sabe nem que a tabela/coluna existe, ele não
tem base nenhuma para dizer "é seguro" — o padrão seguro é o mais alto risco possível, forçando
revisão humana. É o que a spec chama de "não inventar dados" (Constitution III) — o sistema
prefere admitir ignorância a assumir baixo risco.

## Regras para `ADD_INDEX`

Só uma pergunta importa: a coluna-alvo do índice é muito lida agora?

| Condição | Código | Severidade | Descrição |
|---|---|---|---|
| Existe consumidor com `reads_per_day ≥ 100` | `INDEX_BUILD_CONTENTION` | **MEDIUM** | "Index target is heavily read (N consumer(s) ≥ 100 reads/day); online build advised." |
| Caso contrário | `ADD_INDEX_LOW_RISK` | **LOW** | "Adding an index with no listed heavy-read contention." |

Racional: criar um índice não destrói dados nem quebra consumidores — o risco real é de
**contenção de banco** durante a construção (locks, I/O) se a tabela/coluna estiver sob carga
pesada de leitura. `ADD_INDEX` nunca dá HIGH — mesmo o pior caso aqui é "planeje uma janela de
manutenção", não "isso vai quebrar algo em produção". O limiar de 100 leituras/dia
(`_INDEX_CONTENTION_RPD` em `risk.py:15`) é um número arbitrário mas documentado — em um sistema
real, viria de dados históricos de contenção observada.

## Regras para `DROP_COLUMN` / `ALTER_COLUMN`

Aqui mora a maior parte da lógica, porque remover ou alterar uma coluna pode quebrar qualquer
coisa que dependa dela. Cada linha abaixo é avaliada independentemente — **vários fatores podem
disparar ao mesmo tempo**, e o resultado final é o pior deles:

| Condição | Código | Severidade | Descrição |
|---|---|---|---|
| Coluna participa da chave primária | `IN_PRIMARY_KEY` | **HIGH** | "Column participates in the primary key." |
| Coluna participa de uma constraint `UNIQUE` | `IN_UNIQUE_CONSTRAINT` | **HIGH** | "Column participates in a unique constraint." |
| Existe ≥1 foreign key apontando para a coluna | `INBOUND_FOREIGN_KEY` | **HIGH** | "N foreign key(s) reference this column." |
| Referenciada por ≥1 view/materialized view | `REFERENCED_BY_VIEW` | **MEDIUM** | "Referenced by N view/materialization(s)." |
| ≥1 consumidor downstream com `reads_per_day > 0` | `ACTIVELY_READ` | **MEDIUM** | "N downstream consumer(s) still read this column." |
| Evidência de dependências OU de uso ficou `UNAVAILABLE` | `EVIDENCE_UNAVAILABLE` | **MEDIUM** | "Some dependency/usage evidence could not be obtained; risk is uncertain." |
| Nenhum dos anteriores disparou | `NO_DEPENDENTS_OR_USAGE` | **LOW** | "No dependents and no recorded downstream usage." |

Intuição por trás de cada um:
- **HIGH** = quebrar isso quebra a integridade estrutural do próprio banco (chave primária, unique,
  FK apontando para você). Isso não é "opinião de risco" — é matemática relacional: remover a
  coluna causa um erro de banco em qualquer sistema que dependa dessa constraint.
- **MEDIUM** = quebrar isso quebra algo *fora* do banco (uma view de relatório, um serviço que lê
  os dados) — real, mas mais fácil de coordenar/migrar do que uma violação de integridade.
- **`EVIDENCE_UNAVAILABLE` também é MEDIUM, não LOW** — isso é uma escolha deliberada e importante:
  "eu não sei" nunca deve ser tratado como "está seguro". Incerteza sobe o risco, nunca abaixa.
- **LOW** só acontece quando a coluna genuinamente não tem nenhum dependente conhecido e nenhum
  uso registrado — o caso realmente seguro de excluir.

## O gatilho do agente investigador: `has_evidence_gap`

Uma segunda função, separada de `assess()`, decide se vale a pena chamar o agente de IA para
investigar mais fundo antes de recomendar. A regra (chamada de "regra A1" no `research.md`):

```
lacuna de evidência  ⟺  operação é DROP_COLUMN ou ALTER_COLUMN
                       E o ativo FOI encontrado (não é o caso ASSET_NOT_FOUND)
                       E (a fonte de dependências OU a de uso ficou UNAVAILABLE)
```

`ADD_INDEX` nunca gera lacuna (não precisa de investigação — a regra já é simples e completa). Um
ativo ausente também não gera lacuna — faz sentido, porque um agente **somente leitura** não pode
descobrir uma tabela que não existe; mandar ele investigar seria desperdício. A lacuna só existe
quando *algumas* fontes deram certo mas *outras* falharam — aí sim, vale tentar de novo (o agente
tenta as mesmas ferramentas; se a fonte realmente está fora do ar, ele volta de mãos vazias e a
recomendação segue com confiança `REDUCED`).

## Onde ver isso rodando

- Testes: `tests/unit/test_risk_rules.py` (cada regra isolada) e
  `tests/unit/test_routing.py` (a decisão de ir para `investigate` ou `recommend`).
- No banco: a coluna `risk_assessments` de `analysis_record` guarda o histórico completo de
  avaliações, com os `factors` exatos que dispararam — veja `INFO_BANCO.md`.
- Ao vivo: rode a demo (`DEMO.md`) e observe a seção "Risk" do Streamlit listar os códigos de
  fator com sua descrição, exatamente como nesta tabela.
