"""Demo end-to-end ao vivo para apresentacao.

Faz tudo num comando:
1. apaga samples antigos (zera estado)
2. coleta da API da Camara (bate na API real, ao vivo)
3. sobe os JSONL recem coletados pro Volume Databricks
4. dispara os notebooks completos (setup -> queries) como Job
5. valida a Gold materializada via SQL e imprime contagens

Uso:
    python scripts/live_demo.py

Requer DATABRICKS_HOST e DATABRICKS_TOKEN no .env.

Por que ingestao fica fora do cluster Databricks?
    Clusters Databricks (especialmente serverless / Free Edition) tem egress
    de internet restrito por seguranca. Em arquiteturas reais, a ingestao
    da API fica em worker dedicado (Lambda, Cron, Airflow) que entrega
    JSONL no object storage. O cluster consome dali. Esse script reproduz
    esse padrao.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "ftkeng_v3"
WORKSPACE_REPO = "/Workspace/Users/developer@yottaflow.com.br/FAST-TRACK-ENGENHARIA-V3"
# 00_setup nao entra no Job: o live_demo cria schema/volume e sobe samples direto.
NOTEBOOKS = [
    f"{WORKSPACE_REPO}/notebooks/01_bronze",
    f"{WORKSPACE_REPO}/notebooks/02_silver",
    f"{WORKSPACE_REPO}/notebooks/03_gold",
    f"{WORKSPACE_REPO}/notebooks/04_analytics",
    f"{WORKSPACE_REPO}/notebooks/05_optionals",
    f"{WORKSPACE_REPO}/notebooks/06_queries",
]


def _ensure_schema_volume(host: str, token: str) -> None:
    """Cria schema e volume via SQL antes de subir samples."""
    H = _h(token)
    r = requests.get(f"{host}/api/2.0/sql/warehouses", headers=H, timeout=30).json()
    if not r.get("warehouses"):
        return
    wid = r["warehouses"][0]["id"]
    for sql in (f"CREATE SCHEMA IF NOT EXISTS workspace.{SCHEMA}",
                f"CREATE VOLUME IF NOT EXISTS workspace.{SCHEMA}.lakehouse"):
        body = {"statement": sql, "warehouse_id": wid,
                "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"}
        rsp = requests.post(f"{host}/api/2.0/sql/statements", headers=H,
                            data=json.dumps(body), timeout=60).json()
        sid = rsp.get("statement_id")
        state = rsp.get("status", {}).get("state")
        while state in ("PENDING", "RUNNING"):
            time.sleep(1)
            rsp = requests.get(f"{host}/api/2.0/sql/statements/{sid}",
                               headers=H, timeout=30).json()
            state = rsp.get("status", {}).get("state")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        sys.exit("ERRO: .env nao encontrado.")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def step1_limpa_samples() -> None:
    print("\n[1/5] Limpando samples antigos...")
    samples_dir = ROOT / "data" / "samples"
    if samples_dir.exists():
        shutil.rmtree(samples_dir)
    samples_dir.mkdir(parents=True, exist_ok=True)
    print(f"  apagados.")


def step2_coleta_api() -> None:
    print("\n[2/5] Coletando da API ao vivo...")
    sys.path.insert(0, str(ROOT))
    from src.ingestion.bronze import collect_all
    from src.utils.config_loader import load
    from src.utils.logging_setup import new_run_id

    cfg = load()
    run_id = new_run_id()
    results = collect_all(cfg, run_id, max_pages_simple=2)
    total = sum(results.values())
    print(f"\n  Total: {total} registros em {len(results)} entidades (run_id={run_id})")


def step3_upload_volume(host: str, token: str) -> None:
    """Sobe samples direto pro Volume UC (Files API suporta arquivos grandes)."""
    print(f"\n[3/5] Subindo JSONL para o Volume UC ftkeng_v3...")
    volume_base = f"/Volumes/workspace/{SCHEMA}/lakehouse/samples"
    samples = sorted((ROOT / "data" / "samples").glob("*.jsonl"))

    # garante diretorio existe
    requests.put(
        f"{host}/api/2.0/fs/directories{volume_base}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    for f in samples:
        content = f.read_bytes()
        if not content:
            continue
        target = f"{volume_base}/{f.name}"
        # Files API: PUT direto, sem base64. Aceita ate ~5GB.
        r = requests.put(
            f"{host}/api/2.0/fs/files{target}",
            headers={"Authorization": f"Bearer {token}"},
            params={"overwrite": "true"},
            data=content,
            timeout=300,
        )
        status = "ok" if r.status_code in (200, 204) else f"FAIL {r.status_code}"
        print(f"  {status:<10s} {f.name:<32s} {len(content):>9d} B")


def step4_run_pipeline(host: str, token: str) -> bool:
    print(f"\n[4/5] Disparando pipeline no Databricks (schema {SCHEMA})...")
    H = _h(token)
    tasks: list[dict] = []
    prev = None
    for nb_path in NOTEBOOKS:
        key = nb_path.rsplit("/", 1)[-1]
        task: dict = {"task_key": key, "notebook_task": {"notebook_path": nb_path}}
        if prev:
            task["depends_on"] = [{"task_key": prev}]
        tasks.append(task)
        prev = key

    body = {"run_name": f"ftk-v3-live-{int(time.time())}", "tasks": tasks}
    r = requests.post(f"{host}/api/2.2/jobs/runs/submit", headers=H,
                      data=json.dumps(body), timeout=60)
    run_id = r.json().get("run_id")
    print(f"  run_id={run_id}")

    deadline = time.time() + 60 * 30
    while True:
        if time.time() > deadline:
            print("  timeout 30 min")
            return False
        time.sleep(20)
        st = requests.get(f"{host}/api/2.2/jobs/runs/get?run_id={run_id}",
                          headers=H, timeout=60).json()
        life = st.get("state", {}).get("life_cycle_state")
        result = st.get("state", {}).get("result_state")
        print(f"  life={life} result={result}")
        if life in ("TERMINATED", "INTERNAL_ERROR", "SKIPPED"):
            for t in st.get("tasks", []):
                tk = t["task_key"]
                tr = t.get("state", {}).get("result_state")
                print(f"    task={tk:<22s} state={tr}")
            return result == "SUCCESS"


def step5_validar_gold(host: str, token: str) -> None:
    print(f"\n[5/5] Validando Gold...")
    H = _h(token)
    r = requests.get(f"{host}/api/2.0/sql/warehouses", headers=H, timeout=30).json()
    if not r.get("warehouses"):
        return
    wid = r["warehouses"][0]["id"]

    tabelas = [
        "gold_atlas_frentes",
        "gold_frente_diversidade",
        "gold_taxa_presenca_deputado",
        "gold_resumo_alinhamento_frente",
        "gold_ceap_anomalias",
        "gold_ceap_ranking_fornecedor",
        "gold_cpi_catalogo",
        "gold_engajamento_deputado",
        "gold_pl_estado_atual",
        "gold_alertas_votacao",
    ]
    for tabela in tabelas:
        sql = f"SELECT COUNT(*) AS n FROM delta.`/Volumes/workspace/{SCHEMA}/lakehouse/gold/{tabela}`"
        body = {"statement": sql, "warehouse_id": wid,
                "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"}
        rsp = requests.post(f"{host}/api/2.0/sql/statements", headers=H,
                            data=json.dumps(body), timeout=60).json()
        sid = rsp.get("statement_id")
        state = rsp.get("status", {}).get("state")
        while state in ("PENDING", "RUNNING"):
            time.sleep(2)
            rsp = requests.get(f"{host}/api/2.0/sql/statements/{sid}",
                               headers=H, timeout=30).json()
            state = rsp.get("status", {}).get("state")
        if state == "SUCCEEDED":
            n = int(rsp["result"]["data_array"][0][0])
            print(f"  {tabela:<40s} {n:>6d} rows")
        else:
            print(f"  {tabela:<40s} skip/erro")


def main() -> None:
    _load_env()
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        sys.exit("DATABRICKS_HOST/TOKEN ausentes em .env")

    print("=" * 60)
    print("LIVE DEMO — V3")
    print("API: https://dadosabertos.camara.leg.br/api/v2")
    print(f"Databricks schema: workspace.{SCHEMA}")
    print("=" * 60)

    step1_limpa_samples()
    step2_coleta_api()
    _ensure_schema_volume(host, token)
    step3_upload_volume(host, token)
    if step4_run_pipeline(host, token):
        step5_validar_gold(host, token)
    print("\n=== Demo concluida ===")


if __name__ == "__main__":
    main()
