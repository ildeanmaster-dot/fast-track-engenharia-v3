# Runbook 02 — Incidentes e replay

## Estratégias de recuperação

O pipeline é desenhado para ser idempotente — re-executar sempre converge
ao mesmo estado, dada a mesma resposta da API. Isso simplifica recuperação.

### Falha total no Bronze

Sintoma: `data/samples/*.jsonl` vazio ou inconsistente.

Recuperação:

```bash
python -m src.pipelines.run_local
```

Coleta tudo novamente. Custo: ~3-5 min de coleta, ~30 chamadas à API.

### Falha em endpoint específico

Sintoma: log mostra erro em um endpoint, outros OK.

Recuperação cirúrgica:

```python
from src.utils.config_loader import load
from src.ingestion.api_client import CamaraAPIClient
from src.ingestion.bronze import collect_simple
from src.utils.logging_setup import new_run_id

cfg = load()
client = CamaraAPIClient(cfg)
collect_simple(client, cfg.endpoints["votacoes"], new_run_id(), max_pages=5)
```

### Falha em fanout

Tipicamente o fanout falha em IDs específicos (HTTP 404 esperado).
O loop captura cada falha e segue. Verificar `logs/run-*.jsonl` para
ver quais IDs falharam:

```bash
grep -i "fanout falhou" logs/run-*.jsonl
```

### Reprocessar Silver/Gold sem reingerir

```bash
python -m src.pipelines.run_local --skip-bronze
```

Lê os JSONL existentes e reprocessa do Silver para frente.

### Replay no Databricks

Em Databricks com Delta:

```sql
-- Voltar Silver para uma versão anterior
RESTORE TABLE silver_proposicao_tramitacoes TO VERSION AS OF 5;

-- Inspecionar histórico
DESCRIBE HISTORY silver_proposicao_tramitacoes;
```

Depois reprocessar Gold a partir do estado restaurado (executar notebook
`03_gold.py`).

## Quando o reprocesso é seguro?

| Camada | Idempotente | Notas |
|---|---|---|
| Bronze | Sim | Sobrescreve completo. API pode retornar dados diferentes ao longo do tempo. |
| Silver | Sim | Função pura do Bronze. |
| Gold | Sim | Função pura do Silver. |
| State (watermarks) | Cuidado | Preservar valores de watermark se já consolidados. |

## Sinais de degradação

- Latência alta na API (> 5s por chamada): possível instabilidade da fonte.
  Deixar `tenacity` cuidar; se persistir, reduzir `max_pages`.
- 5xx em sequência (> 5 em 1 min): API instável. Pausar e tentar novamente
  em algumas horas.
- Mudança de schema (KeyError ou rename inesperado): atualizar
  `src/transforms/schemas.py` e re-rodar Silver para frente.
