# 0002 — Catálogo de endpoints declarativo em YAML

## Status
Aceita.

## Contexto
A API tem ~17 endpoints. Adicionar/remover endpoint sem mexer em código
Python deixa o pipeline mais previsível e auditável.

## Opções consideradas

1. **YAML em `conf/endpoints.yaml`** com loader tipado.
2. **Dict Python em `conf/config.py`**.
3. **Variáveis de ambiente**.
4. **Banco de dados de configuração**.

## Decisão
YAML carregado em dataclasses tipadas (`EndpointConfig`).

## Justificativa

- **Separa metadata de comportamento**: endpoints são dado, não código.
- **Permite comentários** explicando estratégia incremental por endpoint.
- **Type-safe downstream**: `EndpointConfig` é frozen dataclass com
  `__post_init__` validando estratégia incremental.
- **Adicionar endpoint** = adicionar bloco no YAML. Sem alterar cliente
  HTTP, ingestão ou silver.

## Consequências

- Dependência do `pyyaml` (já é padrão).
- Validação de schema do YAML é leve — confia em `dataclass` para campos
  obrigatórios.
- Tests do `config_loader` garantem que toda entrada tem PK e estratégia
  válida.
- Mudanças no schema do YAML implicam atualizar dataclass + tests.
