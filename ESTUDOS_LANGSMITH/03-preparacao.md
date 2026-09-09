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
