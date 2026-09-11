# 03 · Preparar o laboratório e encontrar o projeto certo

[Índice](README.md) · [Anterior](02-fundamentos-observabilidade.md) · [Próximo](04-primeiro-trace.md)

**Objetivo:** rodar localmente e habilitar envio consciente ao seu workspace. Tempo: 20–30 minutos. O primeiro diagnóstico não chama serviços.

## 1. Ambiente Python

Abra um terminal na raiz:

```bash
cd /home/doug/Projetos/ia/ws_datachange
.venv/bin/python ESTUDOS_LANGSMITH/labs/00_doctor.py
```

O ambiente já estava presente durante a preparação do curso. O diagnóstico mostra versões, presença de chaves e o arquivo `ESTUDOS_LANGSMITH/artefatos/manifesto.json`. **Não imprime valores das chaves.** “Configurada” significa apenas que encontrou um valor não vazio e sem marcador de exemplo; a autenticação é verificada pelo serviço ao usar um laboratório remoto.

Se estiver em outra máquina sem `.venv`, use o fluxo de instalação do projeto:

```bash
uv sync --frozen
```

Preserve o `uv.lock` disponível. Um `pip install -U` generalizado muda o experimento antes de você começar. As versões verificadas estão no [registro de validação](27-fontes-e-validacao.md).

## 2. Conta LangSmith

Abra [LangSmith](https://smith.langchain.com), entre e selecione o workspace desejado. Vá a **Settings → API Keys → Create API Key**, ou procure a área equivalente de chaves se a navegação tiver mudado. Copie a chave para seu `.env` existente em um editor. Não substitua o restante desse arquivo.

```dotenv
# Trecho a preencher no .env existente
LANGSMITH_API_KEY=<sua-chave-real>
```

Os laboratórios definem `LANGSMITH_PROJECT=dcra-estudos` e controlam tracing por `--send`. O app original continua usando sua configuração própria quando iniciado em outro processo. Uma chave pode exigir `LANGSMITH_WORKSPACE_ID` quando o contexto da conta abrange múltiplos workspaces; região e endpoint também precisam combinar com sua conta. [Quickstart de tracing](https://docs.langchain.com/langsmith/observability-quickstart) e [configuração de workspace](https://docs.langchain.com/langsmith/trace-with-opentelemetry).

Use o endpoint indicado pela configuração da sua região. Por exemplo, a documentação registra `https://eu.api.smith.langchain.com` para EU. **URL do site e URL da API são coisas diferentes.** Não copie o endpoint de outro workspace só porque uma captura de tela o usa.

Você não precisa criar manualmente um tracing project: a ingestão pode criá-lo ao receber traces com um nome novo. Depois procure `dcra-estudos` em **Tracing / Tracing Projects**. A navegação documentada é uma referência; nomes de menus podem variar por versão, permissões e plano.

## 3. Primeiro envio

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/01_trace_python.py --send
```

Resultado local esperado: `total_reais: 36`. O script faz flush, tenta obter uma URL autenticada pelo SDK e também imprime o `run_id`. Abra essa URL. Se a ingestão ainda estiver sendo processada, abra LangSmith, escolha `dcra-estudos` e procure `pedido-restaurante` no intervalo de tempo atual.

Não há uma URL privada universal que este curso possa fornecer de antemão: ela depende de organização, projeto e run criados na sua conta. O link impresso resolve isso sem publicar seu trace.

## 4. Quando chegarmos ao modelo real

Os labs 02, 07 e 08 reutilizam [build_chat_model](../src/dcra/llm/factory.py). Para os modos `--real`, configure `LLM_PROVIDER`, `LLM_MODEL` e a chave do provedor no mesmo `.env`. Use um modelo acessível na sua conta e compatível com a integração já instalada; o diagnóstico não garante essa disponibilidade.

Comece com `--limit 3 --repetitions 1`. A quantidade de exemplos não é teto financeiro: podem existir novas tentativas e a quantidade de tokens varia.

## Se nada aparecer

| Sintoma | Verificação concreta |
|---|---|
| O cálculo roda, trace ausente | Você acrescentou `--send`? Sem ele o modo é local |
| Falha de autenticação | Chave correta, workspace correto, endpoint da região correta |
| Projeto parece vazio | Nome, workspace, intervalo temporal, filtros e possível sampling |
| Trace aparece segundos depois | Exportação em lote e processamento da ingestão |
| Script antigo perde os últimos spans | Finalização do processo antes do flush |
| pytest passa e nada é enviado | `tests/conftest.py` desativa tracing intencionalmente |
| O app tem traces, laboratório não | São processos/configurações diferentes; rode o doctor e confira o comando |

**Memorize:** *workspace*, *tracing project*, *endpoint*, *flush*. A chave da API autoriza envio; o nome do projeto organiza os dados; nenhum deles é o `thread_id` de um caso.

## Levar para outros projetos — e onde o seu julgamento decide

Preparar o laboratório parece burocracia, mas é onde se decidem três coisas que um assistente de IA não pode decidir por você: **onde os dados vão parar, quem paga, e quem está autorizado**.

**Na plataforma de atendimento (Langfuse Cloud).** A preparação equivalente está feita e registrada: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` no `.env` local (com `LANGFUSE_HOST` aceito como alias, e os dois obrigados a concordar); a flag `LANGFUSE_TRACING_ENABLED=false` na configuração versionada e `true` só no `.env` de quem usa; `langfuse==4.15.1` fixado em `app/requirements.txt`; `environment=local-n5` para desenvolvimento e `local-test` para a suíte; e um **comando de prova isolado** (`langfuse_probe.py`: um trace, uma chamada com custo, um score) antes de tocar o atendimento — o mesmo papel do `01_trace_python.py --send` aqui. As lições transferem uma a uma: URL do site ≠ URL da API (região Cloud EU/US); "chave configurada" ≠ "autenticação verificada"; o provedor `deterministic-test` fica fora da instrumentação para que `pytest` não envie nada, exatamente como o `conftest.py` deste repositório desliga o tracing. Uma diferença a registrar: no Langfuse, o que sai do processo inclui **texto de mensagem, prompt renderizado e evidências** — o `spec.md` da 013 lista isso e o que **nunca** sai (`OPENAI_API_KEY`, `*_PEPPER`, token anônimo, `Session` SQLAlchemy). Reler essa lista antes de ligar a flag é a preparação que importa.

**Em projetos comuns do ecossistema.** Todo projeto precisa do mesmo trio: projeto/ambiente de observabilidade separado por finalidade (produção ≠ estudo ≠ testes), controle explícito de envio (flag, não presença de chave), e um "doctor" que diga o que está configurado sem imprimir valores. Em LangChain/LangGraph, a integração automática é conveniente e por isso perigosa: uma chave esquecida num ambiente de CI manda traces de teste para o projeto de produção. Trate o envio como uma decisão, não como um efeito colateral da instalação.

**O fator humano — onde a IA faz e onde você decide.** Um assistente escreve o `.env.example`, o script de diagnóstico e até o probe. O que ele **não deve** fazer — e onde você é o único responsável — é criar contas, gerar e guardar chaves, escolher a região e aceitar os termos de uso de um serviço que vai receber os dados da sua aplicação. Foque nisso: antes de ligar qualquer flag, responda em uma linha "que dados saem, para qual região, sob qual plano, e quem mais tem acesso ao workspace". Na plataforma de atendimento, o cenário é um Cancer Center com dados sintéticos hoje; a pergunta "e quando não forem sintéticos?" é sua, não da ferramenta. E há um limite ético claro: chaves e segredos nunca entram numa conversa com IA, nem "só para testar". A IA pode dizer *como* configurar; a autorização para configurar é sua.
