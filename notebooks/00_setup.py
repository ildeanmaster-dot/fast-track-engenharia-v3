# Databricks notebook source
# MAGIC %md
# MAGIC # 00 — Setup do ambiente
# MAGIC
# MAGIC Cria schema, volume e copia os JSONL do repo para o Volume.

# COMMAND ----------

import os
import shutil

REPO_PATH = "/Workspace/Users/developer@yottaflow.com.br/FAST-TRACK-ENGENHARIA-V3"

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.ftkeng_v3")
spark.sql("CREATE VOLUME IF NOT EXISTS workspace.ftkeng_v3.lakehouse")

LAKEHOUSE = "/Volumes/workspace/ftkeng_v3/lakehouse"
SAMPLES = f"{LAKEHOUSE}/samples"
for sub in ("samples", "bronze", "silver", "gold", "ctl", "streaming"):
    dbutils.fs.mkdirs(f"{LAKEHOUSE}/{sub}")

print("LAKEHOUSE:", LAKEHOUSE)

# COMMAND ----------

# Copia samples do repo Workspace para o Volume UC.
src_dir = f"{REPO_PATH}/data/samples"
copied = 0
if os.path.exists(src_dir):
    for fname in os.listdir(src_dir):
        if fname.endswith(".jsonl"):
            src = f"{src_dir}/{fname}"
            if os.path.getsize(src) > 0:
                shutil.copy(src, f"{SAMPLES}/{fname}")
                copied += 1
print(f"copiados {copied} JSONL para {SAMPLES}")

# COMMAND ----------

print("Arquivos no Volume:")
for f in dbutils.fs.ls(SAMPLES):
    print(f"  {f.name}  ({f.size} bytes)")
