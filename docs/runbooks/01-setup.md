# Runbook 01 — Setup local

## Pré-requisitos

- Python 3.11 ou 3.12
- Git
- Acesso à internet (para bater na API da Câmara)

## Setup

```bash
git clone https://github.com/ildeanmaster-dot/fast-track-engenharia-v3.git
cd fast-track-engenharia-v3
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/Mac
pip install -r requirements-dev.txt
```

## Primeira execução

```bash
python -m src.pipelines.run_local
```

Saídas:

- `data/samples/*.jsonl` — Bronze raw
- `data/gold/*.parquet` — Gold materializada
- `logs/run-<id>.jsonl` — log estruturado da execução

## Iteração rápida

Após a primeira coleta, pode reaproveitar os JSONL:

```bash
python -m src.pipelines.run_local --skip-bronze
```

## Tests

```bash
pytest tests/ -v
ruff check src/ tests/
```

## Troubleshooting

| Sintoma | Causa | Solução |
|---|---|---|
| `HTTP 429 too many requests` | Rate limit estourado | Diminuir `RATE_LIMIT_RPM` no `.env` |
| `KeyError 'id'` em fanout | Pai não foi coletado | Rodar pipeline completo (sem `--skip-bronze`) |
| `pyspark` não instala | Versão Python > 3.12 | Use Python 3.11 ou 3.12 |
