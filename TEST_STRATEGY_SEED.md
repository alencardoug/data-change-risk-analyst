# Test Strategy Seed

Este arquivo não define testes finais; ele registra princípios para a fase plan.

## Separar três tipos

### 1. Deterministic tests
Para:
- regras de risco;
- routing;
- state transitions;
- validação de schemas;
- persistência;
- tool contracts.

Devem ser rápidos e sem LLM real.

### 2. LLM integration tests
Poucos casos representativos para:
- structured parsing;
- tool calling esperado;
- recommendation no schema.

Não comparar prosa exata.

### 3. End-to-end demo tests
Casos pequenos que percorrem caminhos diferentes e chegam a human review.

## Falhas que precisam ser consideradas no plan

- asset inexistente;
- tool indisponível;
- saída estruturada inválida;
- agent não encontra evidência adicional;
- usuário rejeita;
- usuário pede revisão;
- retomada com thread/checkpoint incorreto.
