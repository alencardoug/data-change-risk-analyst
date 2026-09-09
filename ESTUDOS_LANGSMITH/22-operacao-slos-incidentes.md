# 22 · O painel deve levar a uma decisão, não só ficar bonito

[Índice](README.md) · [Anterior](21-langfuse-otel.md) · [Próximo](23-ci-gates.md)

**Objetivo:** escolher sinais e investigar um incidente com ordem. Tempo: 20–30 minutos. Os limites numéricos abaixo são exemplos de desenho, não SLOs implantados no DCRA.

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

## SLI, SLO e error budget

**SLI** é a medida. **SLO** é a meta operacional definida sobre ela em uma janela. Exemplo fictício: “99% das análises elegíveis entregam um resultado técnico válido em até 10 segundos, numa janela de sete dias”. É preciso especificar elegibilidade, o que conta como resultado válido e como revisões humanas entram no cálculo.

Se a meta exige 99%, o orçamento de erro dessa medida admite 1% de eventos não conformes na janela. Esse orçamento não é o orçamento financeiro e não mede sozinho qualidade semântica. Para uma introdução direta do próprio trabalho de SRE, consulte [Implementing SLOs — Google SRE Workbook](https://sre.google/workbook/implementing-slos/).

p95 é o ponto abaixo do qual ficam aproximadamente 95% das observações segundo o método de cálculo. Uma média baixa pode esconder uma cauda lenta. Com pouco tráfego, percentis oscilam; inclua a contagem de amostras e evite precisão teatral.

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

## Operação da própria observabilidade

Também monitore atraso de ingestão, falhas de exportação, coverage de tracing/eval e erros do juiz. Não faça a execução de negócio depender desnecessariamente da UI de observabilidade estar disponível. No DCRA, checkpoints e registro persistido têm responsabilidades próprias, independentes da investigação no LangSmith.

Use IDs de alta cardinalidade, como caso/run, para busca e correlação. Para gráficos agregados, prefira dimensões controladas como operação, ambiente e versão. Transformar cada texto de usuário em série de métrica torna o painel difícil de operar.

**Memorize:** *SLI*, *SLO*, *error budget*, *p95*, *cardinality*, *ingestion lag*, *root cause analysis*.
