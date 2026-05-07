# Arquitetura

## Visão geral

```
                                                     ┌──────────────┐
                                                     │  6 entregaveis│
                                                     │  + 2 opcionais│
                                                     └──────────────┘
                                                            ▲
        ┌──────────┐    ┌────────────┐    ┌───────────────┐ │
  API   │ Bronze   │    │ Silver     │    │ Gold          │─┤
  ───►  │ Delta +  │───►│ Schema +   │───►│ Star Schema + │ │
        │ Auditoria│    │ SCD2 +     │    │ Marts         │─┘
        │          │    │ Dedup PK   │    │               │
        └──────────┘    └────────────┘    └───────────────┘
            ▲                                   │
            │                                   ▼
        ┌─────────────────────────────────────────────┐
        │ Quality (CNPJ DV, expectations) + Auditoria │
        └─────────────────────────────────────────────┘
```

## Camadas

### Bronze

- **Local:** JSONL em `data/samples/` (versionado para o Databricks importar
  via Repo).
- **Databricks:** Delta em `/Volumes/workspace/ftkeng_v3/lakehouse/bronze/`.
- **Auditoria por registro:** cada linha tem `_audit.ingest_ts`,
  `_audit.endpoint`, `_audit.source_url`, `_audit.page_number`,
  `_audit.run_id` e `_payload_hash` (SHA-256 do payload).
- **Estratégias incrementais:** declaradas no catálogo YAML
  ([conf/endpoints.yaml](../conf/endpoints.yaml)).

### Silver

- Rename para `snake_case` declarativo em
  [src/transforms/schemas.py](../src/transforms/schemas.py).
- Tipagem explícita: timestamps em UTC, datas como `date`, numéricos como
  `int64`/`float64`.
- Deduplicação por chave primária (`drop_duplicates(subset=pk, keep="last")`).
- Achatamento especial: `votacao_votos.deputado_` (objeto aninhado vira
  colunas planas `id_deputado`, `nome_deputado`, etc.).
- Auditoria silver: `silver_ingest_ts`, `run_id`, `payload_hash` propagado
  do bronze.

### Gold

Star schema:

| Tipo | Tabelas |
|---|---|
| Dimensões | `dim_deputado`, `dim_partido`, `dim_frente`, `dim_orgao`, `dim_evento`, `dim_fornecedor`, `dim_data` |
| Fatos | `fato_voto`, `fato_presenca`, `fato_despesa`, `fato_tramitacao` |

Tabelas analíticas (`gold_*`) materializam um aspecto de cada entregável.

## Estratégias incrementais

| Estratégia | Quando usar |
|---|---|
| `snapshot` | Listas pequenas e estáveis (partidos, deputados ativos) |
| `append` | Eventos novos e imutáveis (votações, votos) |
| `append_watermark` | Fluxos temporais (despesas por ano/mês) |
| `merge_by_hash` | Atualizações em registros existentes (proposições) |
| `scd2_by_hash` | Histórico relevante de mudanças (tramitações de PL) |

## Resiliência

- **Cliente HTTP** com `tenacity` faz retry exponencial em 429 e 5xx.
- **Rate limit** cliente-side (180 RPM por padrão) evita 429 preventivamente.
- **State control** em `data/ctl/ingestion_state.json` guarda watermarks por
  endpoint.
- **Bronze idempotente**: re-rodar sobrescreve. Silver/Gold são funções
  determinísticas a partir do Bronze.
- **Replay**: re-rodar do Bronze para frente reprocessa qualquer ponto.
- Detalhes em [runbooks/02-incidentes.md](runbooks/02-incidentes.md).

## Auditoria e linhagem

```
API
 │ ingest_ts, source_url, page_number, run_id, payload_hash
 ▼
Bronze (JSONL/Delta)
 │ silver_ingest_ts, run_id (mesmo run), payload_hash (propagado)
 ▼
Silver (DataFrame/Delta)
 │ run_id propagado nas analíticas
 ▼
Gold (Parquet/Delta)
```

Qualquer linha em Gold pode ser rastreada até a `source_url` original via
`run_id` + `payload_hash`.

## Dependências entre tabelas

```
   deputados ──┬── frente_membros ── frentes
               ├── evento_deputados ── eventos
               ├── votacao_votos ── votacoes
               ├── deputado_despesas
               └── deputado_discursos

   proposicoes ──── proposicao_tramitacoes (SCD2)

   orgaos ──┬── orgao_membros (deputados)
            ├── orgao_eventos (eventos)
            └── orgao_votacoes (votacoes)
```
