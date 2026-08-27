# Constitution Seed

Este arquivo é **entrada para `/speckit.constitution`**, não substitui a constituição gerada pelo Spec Kit.

## Princípios propostos

### 1. Purpose before framework
Toda funcionalidade deve existir primeiro por valor de produto ou aprendizado. Não adicionar LangChain, LangGraph, MCP ou qualquer biblioteca apenas para aumentar a lista de tecnologias.

### 2. Controlled autonomy
Processos críticos pertencem ao workflow. O LLM pode interpretar, investigar e recomendar dentro de limites explícitos; ações finais relevantes permanecem sob controle determinístico e/ou humano.

### 3. Evidence over invention
O sistema nunca deve apresentar dependência, uso, criticidade ou histórico corporativo simulado como fato sem ter obtido isso da fonte de dados ou de uma tool.

### 4. Deterministic rules for deterministic policy
Regras de risco que precisem ser previsíveis, auditáveis e testáveis devem ficar em código/configuração, não escondidas em prompt.

### 5. Human review is a first-class workflow state
Aprovação humana deve ser modelada como parte do processo, não como um botão cosmético depois da resposta do LLM.

### 6. Portfolio proportionality
Profissionalismo significa clareza, contratos, testes, rastreabilidade e boas decisões — não quantidade de serviços ou arquivos.

### 7. Learning visibility
Cada uso importante de LangChain/LangGraph deve ter justificativa arquitetural registrada e ser demonstrável na interface ou documentação.

### 8. Smallest sufficient system
Preferir a menor solução que preserve o caso de uso e os objetivos educacionais.

### 9. No destructive real-world execution
A aplicação de portfólio não executará DDL em sistemas reais nem terá tool genérica de SQL arbitrário.

### 10. Specification outranks scaffold
Quando implementação existir, especificação aceita e ADRs aprovados têm precedência sobre código antigo ou protótipos.

## Questões para constitution

Durante `/speckit.constitution`, validar se estes princípios são suficientes e remover os redundantes. A constituição final deve ser curta o bastante para realmente governar decisões futuras.
