# 19 · Uma câmera útil não precisa filmar o número do cartão

[Índice](README.md) · [Anterior](18-evals-online-producao.md) · [Próximo](20-rag-fora-do-projeto.md)

**Objetivo:** observar o efeito de redação e entender vieses de sampling. Tempo: 25 minutos. Código: [10_privacy.py](labs/10_privacy.py). Todos os dados do exercício são sintéticos.

## Experimento A — o programa recebe um valor, o trace registra outro

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/10_privacy.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/10_privacy.py --send
```

Abra a URL impressa. A entrada usa `pessoa@example.com`, um endereço fictício. Encontre `[EMAIL_REMOVIDO]` nos inputs/outputs do wrapper e do filho `contato-redigido`.

Abra o código e procure:

```python
@traceable(process_inputs=redact, process_outputs=redact)
```

Os processadores transformam o que será registrado. A função de negócio continua recebendo o original e devolvendo seu resultado normal. O wrapper externo usa somente uma representação já redigida, para não registrar o dado bruto antes que o filho o processe. Essa separação é testada localmente.

A API aceita processamento em funções e em outros níveis de configuração. [Proteção de inputs/outputs](https://docs.langchain.com/langsmith/mask-inputs-outputs).

## O que esse regex não demonstra

Ele reconhece um padrão simples de e-mail em strings e percorre dicionários/listas. Não é um classificador completo de informação sensível. Não cobre automaticamente nomes de chave, tuples, anexos, SQL, parâmetros de URL, metadados, tags ou mensagens de exception. Um processor no pai tampouco garante que todo filho esteja redigido.

O exercício ensina a fronteira entre dado utilizado e telemetria exportada. Em uma aplicação real, defina uma política por campo e por etapa, verifique a árvore inteira e faça testes com amostras representativas. Manter IDs opacos de caso costuma ser mais útil à correlação que colocar e-mail no nome de um span.

Existe um trade-off: ocultar completamente o texto pode impedir diagnosticar uma extração errada. Considere contexto mínimo necessário, transformações antes do envio e acesso apropriado aos dados de investigação. A escolha deve atender à finalidade da observabilidade.

## Experimento B — sampling sem confundir ausência com falha

Depois de ter um trace funcionando, execute em processos separados:

```bash
LANGSMITH_TRACING_SAMPLING_RATE=0 .venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py --send
LANGSMITH_TRACING_SAMPLING_RATE=1 .venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py --send
```

No primeiro, a aplicação calcula o total, mas o trace novo é descartado pelo sampling; o script pode não conseguir recuperar sua URL. Ainda pode haver comunicação de controle com a API, porque você usou `--send`. No segundo, o trace é elegível a envio integral. Confira pelo `run_id`, não apenas por “a lista já tinha uma linha”. [Taxa de amostragem](https://docs.langchain.com/langsmith/sample-traces).

Os prefixos acima afetam só aquele comando. Para prática inicial, prefira taxa 1. Quando usar 0,1 em muitas execuções, espere uma proporção aproximada, não exatamente um trace a cada dez.

## O viés que parece melhoria

Imagine dois recortes:

- 100% das falhas são guardadas para investigação;
- 10% dos sucessos são guardados para economizar volume.

A fração de erros nessa coleção não é a taxa bruta de erros de todos os pedidos. O recorte foi desenhado para achar problemas, não para estimar a população sem ajuste. Registre políticas de seleção e use métricas de população completas ou estimadores adequados quando precisar de taxas.

Sampling decidido no início de uma execução (*head sampling*) não sabe quais runs vão falhar depois. Preservar todos os erros exige outra estratégia/arquitetura ou coleta adicional. Não afirme que um único percentual de sampling garante isso.

Em casos com várias retomadas, amostrar cada trace separadamente também pode deixar uma thread com histórico incompleto. Pense na unidade de seleção quando o critério depende da trajetória inteira.

**Memorize:** *redaction*, *data minimization*, *head sampling*, *tail sampling*, *selection bias*, *coverage*.
