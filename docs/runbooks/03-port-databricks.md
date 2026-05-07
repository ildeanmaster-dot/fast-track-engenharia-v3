# Runbook 03 — Port para Databricks

## Pré-requisitos

- Conta Databricks (Free Edition ou Premium)
- Credencial Git para clonar repos GitHub no Workspace (OAuth ou PAT)
- Permissão para criar schema/volume no Unity Catalog

## Setup inicial (uma vez)

### 1. Importar o repo como Git folder

Workspace → Repos (ou Git folders) → Add Repo:

- URL: `https://github.com/ildeanmaster-dot/fast-track-engenharia-v3.git`
- Branch: `main`
- Path: `/Workspace/Users/<seu_email>/FAST-TRACK-ENGENHARIA-V3`

### 2. Criar schema e volume

Executar `notebooks/00_setup.py`. Cria:

- Schema `workspace.ftkeng_v3`
- Volume `workspace.ftkeng_v3.lakehouse`
- Subdirs: `samples/`, `bronze/`, `silver/`, `gold/`

E copia os JSONL do repo para `samples/`.

### 3. Executar pipeline

Em ordem:

1. `01_bronze.py` — JSONL → Delta com auditoria.
2. `02_silver.py` — schemas + dedup.
3. `03_gold.py` — dimensões + fatos.
4. `04_analytics.py` — 6 entregáveis.
5. `05_optionals.py` — Streaming + CDC.
6. `06_queries.py` — queries SQL representativas.

Rodar tudo via Job submit (recomendado):

```python
import requests, json

body = {
    "run_name": "ftk-v3-e2e",
    "tasks": [
        {"task_key": "setup", "notebook_task": {"notebook_path": ".../00_setup"}},
        {"task_key": "bronze", "notebook_task": {"notebook_path": ".../01_bronze"},
         "depends_on": [{"task_key": "setup"}]},
        # ... encadear demais tasks
    ],
}
```

## Auto-sync GitHub → Databricks

`.github/workflows/databricks-sync.yml` atualiza o Git folder do Databricks
a cada push em `main`.

Configurar 3 secrets no GitHub:

- `DATABRICKS_HOST` — `https://dbc-XXXXX.cloud.databricks.com`
- `DATABRICKS_TOKEN` — PAT pessoal (lifetime 90d)
- `DATABRICKS_REPO_ID` — id do Git folder (ver via `GET /api/2.0/repos`)

## Validação pós-execução

```sql
SELECT 'gold_atlas_frentes' AS tabela, COUNT(*) AS rows
FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_atlas_frentes`
UNION ALL SELECT 'gold_engajamento', COUNT(*)
FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_engajamento_deputado`;
```

## Limpeza

Após uso (free trial expirando ou para liberar storage):

```sql
DROP VOLUME IF EXISTS workspace.ftkeng_v3.lakehouse;
DROP SCHEMA IF EXISTS workspace.ftkeng_v3 CASCADE;
```

E revogar o PAT criado em Settings → Developer → Access tokens.
