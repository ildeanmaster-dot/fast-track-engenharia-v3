# 0001 — Arquitetura medalhão

## Status
Aceita.

## Contexto
O desafio recomenda explicitamente arquitetura medalhão, Delta Lake e Time
Travel. Comparei brevemente outras opções antes de fechar.

## Opções consideradas

1. **Medalhão (Bronze/Silver/Gold)** — padrão Databricks.
2. **ELT direto** — ingere e transforma na mesma camada.
3. **Data Vault 2.0** — hub+link+sat com staging.

## Decisão
Adotar arquitetura medalhão.

## Justificativa

- **Idempotência natural**: Bronze preserva o payload bruto. Reprocessar
  Silver/Gold nunca exige voltar à API.
- **Auditoria por camada**: cada linha tem suas próprias colunas de
  auditoria. Rastrear linhagem é trivial.
- **Compatível com Delta**: SCD2, Time Travel e MERGE são operações de
  primeira classe.
- **Recomendado pelo desafio**: evita gastar pontos justificando uma
  alternativa.
- Data Vault seria overkill para o volume e cadência deste pipeline.

## Consequências

- 3 áreas de storage por ambiente (local Parquet + Databricks Volume).
- Caminhos abstraídos via configuração — sem hardcoding.
- "Replay" é re-rodar do Bronze para frente.
- Custo de storage maior do que ELT direto, mas dentro do esperado.
