# Portfolio Criteria

## O projeto deve parecer profissional por estes sinais

- problema empresarial compreensível em menos de um minuto;
- arquitetura proporcional ao problema;
- README com diagrama e demo;
- decisões críticas registradas;
- separação entre lógica determinística e LLM;
- tools com contratos estreitos;
- human-in-the-loop real;
- testes das regras e do routing;
- tratamento explícito de falhas;
- dados de demonstração coerentes;
- execução local reproduzível;
- código legível e módulos com responsabilidades claras.

## Não usar como sinal falso de profissionalismo

- microserviços sem necessidade;
- Kubernetes;
- Kafka;
- dezenas de tabelas;
- autenticação simulada só para dizer que existe;
- “enterprise architecture” excessiva;
- 20 ADRs triviais;
- abstrações genéricas para uma única implementação;
- multi-agent apenas para impressionar;
- métricas inventadas sem uso.

## Demo ideal

A demonstração final deve conseguir mostrar, em poucos minutos:

1. entrada de uma mudança;
2. interpretação estruturada;
3. coleta de evidências;
4. routing do graph;
5. uso de tools/agent quando aplicável;
6. avaliação de risco explicável;
7. interrupção aguardando humano;
8. decisão/feedback;
9. retomada e estado final.

## Perguntas que o repositório deve ajudar a responder em entrevista

- “Por que LangGraph e não apenas uma chain?”
- “Por que nem tudo é um agent?”
- “Como você controla o que o LLM pode fazer?”
- “O que acontece se uma tool falhar?”
- “Como você testa routing e regras sem pagar chamadas de LLM?”
- “Por que MCP foi ou não foi usado?”
- “Como retomaria um workflow interrompido?”
- “O que você mudaria para produção real?”
