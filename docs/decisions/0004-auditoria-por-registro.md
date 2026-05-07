# 0004 — Auditoria embutida por registro

## Status
Aceita.

## Contexto
O desafio pede mecanismos para rastrear origem e evolução dos dados.
Considerei se essa auditoria deveria ser:

1. Centralizada em uma tabela `ctl.ingestion_log` (Delta).
2. Embutida em cada registro como colunas `_audit.*`.
3. Híbrida.

## Decisão

Auditoria embutida (opção 2) com state externo de watermark (opção 1
parcial).

- **Cada registro Bronze** tem `_audit.ingest_ts`, `_audit.endpoint`,
  `_audit.source_url`, `_audit.page_number`, `_audit.run_id`,
  `_payload_hash`.
- **`data/ctl/ingestion_state.json`** mantém apenas watermarks por endpoint
  (último valor visto na coluna de watermark) — info de controle.
- Em Databricks, isso vira uma tabela `ctl.ingestion_state` Delta.

## Justificativa

- **Rastreabilidade self-contained**: dado um registro Bronze qualquer, eu
  sei imediatamente quando foi ingerido, de qual URL, em qual run. Sem
  precisar joinar com tabela CTL.
- **Idempotência por hash**: `_payload_hash` permite detectar mudança real
  vs. re-ingestão.
- **Linhagem por run**: filtrar por `run_id` mostra o impacto de uma
  execução específica.
- **State separado**: watermarks ficam em estrutura própria pois são
  contadores, não atributos do registro.

## Consequências

- Bronze fica ~5–10% maior em storage (campos de auditoria).
- Schema Bronze tem colunas que começam com `_` — convenção precisa estar
  clara para downstream.
- Silver descarta as `_audit.*` mas propaga `payload_hash` e `run_id` em
  colunas próprias.
