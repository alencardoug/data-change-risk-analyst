# Requirements Seed — WHAT/WHY only

Este arquivo serve de matéria-prima para `/speckit.specify`. Ele deliberadamente evita stack e arquitetura.

## Problema

Mudanças aparentemente pequenas em ativos de dados podem afetar consumidores desconhecidos. Em ambientes corporativos, uma decisão de mudança precisa considerar evidências e ser revisável.

## Usuário candidato

Profissional responsável por revisar uma mudança em dados antes de aprová-la.

A persona exata deve ser confirmada em `clarify`.

## Jornada candidata

1. Usuário descreve uma mudança proposta.
2. Sistema identifica o objeto da mudança.
3. Sistema obtém fatos relevantes disponíveis.
4. Sistema apresenta risco e justificativas.
5. Sistema apresenta recomendação.
6. Humano decide ou pede revisão.
7. Sistema mantém um resultado final rastreável.

## Requisitos funcionais candidatos

- Aceitar uma solicitação textual curta.
- Representar a solicitação de forma estruturada.
- Obter evidências estruturadas sobre o ativo afetado.
- Explicitar quando uma evidência não estiver disponível.
- Avaliar risco com fatores compreensíveis.
- Investigar fatos adicionais quando isso puder alterar a recomendação.
- Produzir recomendação não vinculante.
- Exigir revisão humana antes do resultado final.
- Permitir ao humano aprovar, rejeitar ou solicitar revisão da recomendação, caso este terceiro caminho sobreviva ao `clarify`.
- Registrar o resultado final da análise.

## Critérios de sucesso candidatos

- A demo deve tornar claro por que uma mudança é considerada mais ou menos arriscada.
- O sistema não pode inventar dependências ou uso inexistentes na fonte simulada.
- O usuário deve conseguir distinguir recomendação da IA de decisão humana.
- Pelo menos dois cenários devem percorrer caminhos diferentes do workflow.
- Uma falha de evidência/tool deve produzir comportamento explícito, não alucinação silenciosa.

## Fora do escopo candidato

- execução de DDL real;
- autenticação corporativa;
- gestão completa de change management;
- RAG/documentos;
- multi-agent;
- dados reais de empresa.
