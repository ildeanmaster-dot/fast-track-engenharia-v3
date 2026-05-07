# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Bronze (JSONL → Delta com auditoria)

# COMMAND ----------

from datetime import datetime, timezone

from pyspark.sql.functions import lit, sha2, to_json, struct

LAKEHOUSE = "/Volumes/workspace/ftkeng_v3/lakehouse"
SAMPLES = f"{LAKEHOUSE}/samples"

run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
ingest_ts = datetime.now(timezone.utc).isoformat()

# COMMAND ----------

bronze_counts = {}
for entry in dbutils.fs.ls(SAMPLES):
    fname = entry.name
    if not fname.endswith(".jsonl"):
        continue
    name = fname[:-6]
    try:
        df = spark.read.json(f"{SAMPLES}/{fname}")
        df = (df.withColumn("ingest_ts", lit(ingest_ts))
                .withColumn("run_id", lit(run_id))
                .withColumn("endpoint", lit(name)))
        df.write.format("delta").mode("overwrite").option("overwriteSchema", "true") \
              .save(f"{LAKEHOUSE}/bronze/{name}")
        bronze_counts[name] = df.count()
        print(f"  bronze.{name:<25s} {bronze_counts[name]:>5d} rows")
    except Exception as e:
        print(f"  bronze.{name}: FAIL {str(e)[:120]}")

print(f"\nBronze: {sum(bronze_counts.values())} rows em {len(bronze_counts)} tabelas")
