# 20 · O bibliotecário trouxe o livro errado; culpar o leitor ajuda?

[Índice](README.md) · [Anterior](19-privacidade-amostragem.md) · [Próximo](21-langfuse-otel.md)

**Objetivo:** transferir observabilidade e evals para um problema que não existe no DCRA. Tempo: 20–30 minutos. Código: [11_rag.py](labs/11_rag.py). Sem embeddings, banco vetorial ou modelo.

RAG combina recuperação de contexto e geração/resposta baseada nele. O DCRA não implementa RAG: suas evidências são estruturadas e suas regras explícitas. Este laboratório separado usa uma política de loja **inteiramente fictícia** para exercitar a separação de falhas.

O corpus tem dois documentos: prazo de devolução de sete dias e frete de três a cinco dias úteis. A pergunta é sobre devolução. Em vez de gastar com um modelo para produzir erros aleatórios, o código controla três cenários.

## Execute e compare

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/11_rag.py
.venv/bin/python ESTUDOS_LANGSMITH/labs/11_rag.py --send
```

Abra os três traces:

| Cenário | Documento recuperado | Resposta | Notas: recuperação / resposta / sustentada ou abstenção |
|---|---|---|---|
| `rag-good` | prazo | 7 dias | 1 / 1 / 1 |
| `rag-bad_retrieval` | frete | não há contexto suficiente | 0 / 0 / 1 |
| `rag-hallucination` | prazo | 90 dias | 1 / 0 / 0 |

Expanda `recuperar_politica`, um run de tipo retriever, e compare IDs/documentos. Depois abra `responder_fixture`. Esse filho é uma resposta programada, não uma chamada a modelo real.

## Faça o diagnóstico pela primeira divergência

No segundo cenário, a abstenção é coerente com o contexto recebido. Melhorar apenas o prompt de geração não fará o documento correto aparecer. Investigue consulta, filtros, indexação e ranking em um RAG real.

No terceiro cenário, o documento correto já chegou. O sistema até cita seu ID, mas a afirmação de 90 dias não está nele. **Ter uma citação não prova que ela sustenta a afirmação.** Agora o ponto a avaliar é o uso do contexto pela geração.

O primeiro cenário passa nesse corpus minúsculo. Isso não demonstra que a recuperação generaliza a outras perguntas ou que o sistema domina uma política completa.

## Métricas que pertencem a etapas diferentes

- **Recall@k da recuperação:** entre os documentos relevantes conhecidos, quantos apareceram nos k recuperados?
- **Precision@k:** que proporção dos k recuperados era relevante?
- **Correctness da resposta:** a resposta resolve corretamente a pergunta, segundo a referência?
- **Faithfulness/groundedness:** as afirmações são sustentadas pelo contexto fornecido?
- **Relevância da resposta:** ela atende à pergunta sem desviar?
- **Qualidade da abstenção:** quando faltava evidência, o sistema reconheceu a limitação adequadamente?

O lab mede um `recall_at_1` estreito, com um documento relevante conhecido, e usa um oráculo em código para os números. `supported_or_abstained` agrupa uma resposta sustentada e uma abstenção honesta, deixando correctness em outra métrica. Ele não é um avaliador semântico genérico para qualquer texto.

O [tutorial de avaliação de RAG](https://docs.langchain.com/langsmith/evaluate-rag-tutorial) apresenta a separação entre avaliar recuperação e resposta com LangSmith. O exercício aqui foi feito para você enxergar esse raciocínio antes de adicionar novas dependências.

## Leve a ideia de volta ao projeto

No DCRA, uma recomendação errada pode ter recebido um `StructuredChange` errado ou evidências incompletas. Avaliar somente o texto final mistura os problemas. Registre e avalie o que entrou em cada componente importante.

No sentido inverso, um RAG também pode precisar de autorização humana ou etapas determinísticas. Nesse caso LangGraph pode organizar o workflow, enquanto LangSmith observa e compara execuções. Não é necessário adicionar um grafo para implementar esta demonstração de duas funções.

**Conceito LangChain:** composição de recuperação e resposta, com contratos e tracing. **Alternativa simples:** busca local e função de resposta, como neste lab. **Defesa:** frameworks ajudam quando integrações e composição justificam seu custo; os critérios de qualidade são independentes deles.

**Exercício:** proponha um quarto cenário com documentos corretos e resposta correta, mas contexto dez vezes maior. Qualidade pode permanecer igual; compare custo e latência. “Mais contexto” não é uma vitória automática.

**Memorize:** *retrieval*, *groundedness*, *answer correctness*, *recall@k*, *abstention*.

## Levar para outros projetos — e onde o seu julgamento decide

Este é o capítulo que **mais** se aplica à plataforma de atendimento, porque ela é um RAG — e o DCRA não é. O bibliotecário e o leitor são dois componentes, com falhas e correções diferentes.

**Na plataforma de atendimento (Langfuse Cloud).** A taxonomia de falha do `playbook_diagnostico.md` é a versão de seis camadas dos três cenários deste lab: **conteúdo** (a informação não existe ou está inativa — antes de `bad_retrieval`: o livro não está na biblioteca); **recuperação** (`bad_retrieval`: existe, mas não chega às primeiras posições, ou Q&A e clínico disputam o lugar); **contexto** (informação de turno anterior não chega às `messages` — um caso que este lab não tem e que chat introduz); **geração** (`hallucination`: o documento certo chegou e o modelo afirmou o que não estava nele); **agenda** (resolvedor de ofertas); **envio**. A "primeira investigação sugerida" do playbook é literalmente o "diagnóstico pela primeira divergência": o dado consta no request do segundo turno? Não → camada 3, prompt não resolve. Consta → camada 4. As métricas por etapa já têm nomes lá: `Hit@8` na recuperação (só em casos com referência revisada, mesmo `k` entre variantes), consistência com referências e continuidade na resposta — e o contrato lembra que **no fallback livre `generate_ungoverned()` não recebe evidências**, então cobrar faithfulness dele é exigir citação inexistente no contrato daquele caminho: julgue pela informação que ele de fato teve. O exercício do "quarto cenário" (contexto dez vezes maior) tem versão prática: `retrieve()` embeda o **blob concatenado** de mensagens; a hipótese H01/candidata do plano é embedar só a última — e a comparação precisa mostrar `Hit@8` **e** custo/latência, não só um.

**Em projetos comuns do ecossistema.** Registre, em todo RAG: a query exata embedada (não a mensagem do usuário — são coisas diferentes depois de reescrita, concatenação ou corte), os documentos com ID/score/rank, e o contexto efetivamente colocado no prompt (depois de truncar). Avalie recuperação com referência de relevância; avalie geração com groundedness sobre o contexto **fornecido**; avalie abstenção como um resultado legítimo. "Ter citação não prova sustentação." Em LangChain, retrievers e o `CallbackHandler` do Langfuse ou a integração do LangSmith geram spans de tipo retriever automaticamente — mas a query reescrita e o corte de contexto costumam ficar fora, e são onde o problema mora.

**O fator humano — onde a IA faz e onde você decide.** Um assistente diagnostica o cenário `hallucination` corretamente se você der os três traces. Mas o julgamento de **relevância** — "este documento é o que o paciente precisava?" — é o gabarito de `Hit@k`, e só uma pessoa que conhece o conteúdo pode dá-lo. Um modelo julgando relevância é mais um juiz a calibrar (capítulo 15), não uma referência. Foque em duas coisas: (1) construir, você mesmo, o conjunto de pares (pergunta → documento certo) para os casos que viu falhar — é pequeno, e é o que torna a comparação de estratégias de recuperação possível; (2) resistir ao reflexo "melhora o prompt" — o playbook diz "diagnosticar antes de mexer em prompt; um prompt que diz 'lembre-se' não acrescenta uma informação que não chegou ao modelo". A IA, pedida para consertar uma resposta ruim, quase sempre propõe mudar o prompt, porque é o que ela consegue mudar; decidir que o problema é de recuperação, de corte de contexto ou de curadoria do conteúdo — e segurar a mudança de prompt até saber — é a disciplina que só você impõe. A decisão de **segurar RAGFlow/Elasticsearch até a Fase 0** é essa disciplina em forma de plano.
