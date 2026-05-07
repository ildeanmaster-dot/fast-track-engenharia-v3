# Câmara dos Deputados — Pipeline Lakehouse

[![tests](https://github.com/ildeanmaster-dot/fast-track-engenharia-v3/actions/workflows/tests.yml/badge.svg)](https://github.com/ildeanmaster-dot/fast-track-engenharia-v3/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![databricks](https://img.shields.io/badge/databricks-Premium-orange)](https://www.databricks.com/)

Pipeline ponta-a-ponta sobre os Dados Abertos da Câmara dos Deputados. Projeto
final do programa **Upskill Tiller — Engenharia de Dados, T2**.

---

## Sumário

- [Visão geral](#visão-geral)
- [Entregáveis](#entregáveis)
- [Arquitetura](#arquitetura)
- [Quickstart local](#quickstart-local)
- [Quickstart Databricks](#quickstart-databricks)
- [Estrutura](#estrutura)
- [Operação](#operação)
- [Decisões e documentação](#decisões-e-documentação)

## Visão geral

Solução end-to-end sobre 17 endpoints da [API Câmara](https://dadosabertos.camara.leg.br/),
arquitetura medalhão (Bronze → Silver → Gold) com Delta Lake + Time Travel.
Roda em três modos:

- **Pandas local** — iteração rápida, CI sem cluster.
- **PySpark local** — paridade com Databricks usando Delta open-source.
- **Databricks Premium** — Unity Catalog + Volumes + Workflows.

## Entregáveis

### Obrigatórios (6)

1. **Atlas das frentes** — HHI por frente, sobreposição entre frentes
   ideologicamente opostas, deputados em N frentes, evolução por legislatura.
2. **Calendário de eventos** — taxa de presença por deputado/tipo, densidade
   semanal, semanas vazias, view de eventos futuros.
3. **Correlação frente × votação** — alinhamento médio dentro de frentes vs.
   dentro de partidos, por votação.
4. **Raio-X CEAP** — z-score por categoria × UF, ranking de fornecedores com
   flag de CNPJ suspeito (validação DV + heurística multi-UF).
5. **Auditoria de CPIs** — catálogo, duração vs. prazo regimental,
   produtividade (com relatório vs. sem).
6. **Engajamento parlamentar** — score composto (presenças × votos × discursos)
   com percentil partidário e nacional.

### Opcionais (2)

7. **Streaming de votações** — micro-batch a cada 10 min com classificação de
   urgência e SLA dashboard.
8. **CDC de tramitação** — SCD2 com `valid_from`/`valid_to`/`is_current` por
   proposição, alertas de transição (chegada ao Plenário, arquivamento).

## Arquitetura

```
        ┌──────────┐      ┌──────────┐      ┌────────────────┐
  API   │ Bronze   │      │ Silver   │      │ Gold           │
  ───►  │ Delta    │ ───► │ Schema + │ ───► │ Star + Marts   │
        │ Raw+Audit│      │ SCD2     │      │ + Entregáveis  │
        └──────────┘      └──────────┘      └────────────────┘
```

Detalhe completo em [docs/architecture.md](docs/architecture.md). Modelo
relacional em [docs/data_model.md](docs/data_model.md).

## Quickstart local

Requer Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.pipelines.run_local
```

Para iterar sem reingerir tudo:

```bash
python -m src.pipelines.run_local --skip-bronze
```

Tests:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
ruff check src/ tests/
```

## Quickstart Databricks

Schema: `workspace.ftkeng_v3`. Volume: `workspace.ftkeng_v3.lakehouse`.

1. **Importar como Git folder** apontando para este repo.
2. **Executar notebooks** em ordem:
   - `00_setup.py` — schema + volume + cópia de samples
   - `01_bronze.py` — JSONL → Delta com auditoria
   - `02_silver.py` — schemas explícitos + SCD2
   - `03_gold.py` — dimensões + fatos
   - `04_analytics.py` — 6 entregáveis materializados
   - `05_optionals.py` — Streaming + CDC
   - `06_queries.py` — queries SQL de validação

Auto-sync GitHub → Databricks Repo configurado em
`.github/workflows/databricks-sync.yml`. Configurar 3 secrets:
`DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_REPO_ID`.

## Estrutura

```
.
├── conf/
│   ├── endpoints.yaml             # catálogo declarativo dos 17 endpoints
│   └── ideologia_partidos.yaml    # mapa eixo esquerda-direita
├── src/
│   ├── ingestion/                 # cliente HTTP + bronze + state
│   ├── transforms/                # schemas + silver + gold
│   ├── analytics/                 # 6 obrigatórios + 2 opcionais
│   ├── quality/                   # cnpj + expectations + audit
│   ├── pipelines/                 # orquestradores
│   └── utils/                     # config + logging + hashing
├── notebooks/                     # versão Databricks
├── tests/unit/                    # pytest com mocks
└── docs/
    ├── architecture.md
    ├── data_model.md
    ├── decisions/                 # ADRs
    └── runbooks/                  # operação e incidentes
```

## Operação

- [docs/runbooks/01-setup.md](docs/runbooks/01-setup.md) — setup local
- [docs/runbooks/02-incidentes.md](docs/runbooks/02-incidentes.md) — replay e
  reprocessamento
- [docs/runbooks/03-port-databricks.md](docs/runbooks/03-port-databricks.md)
  — port para Databricks

## Decisões e documentação

| Documento | Conteúdo |
|---|---|
| [architecture.md](docs/architecture.md) | Arquitetura medalhão + fluxo |
| [data_model.md](docs/data_model.md) | Modelo Silver + Gold + relacionamentos |
| [decisions/0001-medalhao.md](docs/decisions/0001-medalhao.md) | Por que medalhão |
| [decisions/0002-catalogo-yaml.md](docs/decisions/0002-catalogo-yaml.md) | YAML como catálogo |
| [decisions/0003-pyspark-nativo.md](docs/decisions/0003-pyspark-nativo.md) | PySpark como backend |
| [decisions/0004-auditoria-por-registro.md](docs/decisions/0004-auditoria-por-registro.md) | Auditoria embutida |

## Sobre

Desenvolvido com auxílio de IA (Claude). Decisões e revisões são minhas.
