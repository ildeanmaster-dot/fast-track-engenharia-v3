# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — Opcionais (Streaming + CDC tramitacao)

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

LAKEHOUSE = "/Volumes/workspace/ftkeng_v3/lakehouse"

def read_silver(name):
    return spark.read.format("delta").load(f"{LAKEHOUSE}/silver/{name}")

def write_gold(name, df):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true") \
          .save(f"{LAKEHOUSE}/gold/{name}")
    n = df.count()
    print(f"  gold.{name:<35s} {n:>5d} rows")
    return n

# COMMAND ----------

# MAGIC %md ## Opcional 1 — CDC tramitação SCD2

# COMMAND ----------

try:
    tram = read_silver("proposicao_tramitacoes")
    w = Window.partitionBy("id_proposicao").orderBy("data_hora")
    scd2 = (tram.withColumn("valid_from", F.col("data_hora"))
                 .withColumn("valid_to", F.lead("data_hora").over(w))
                 .withColumn("is_current", F.col("valid_to").isNull()))
    write_gold("gold_pl_tramitacao_scd2", scd2)

    estado_atual = scd2.filter(F.col("is_current"))
    write_gold("gold_pl_estado_atual", estado_atual)

    alertas = scd2.withColumn("tipo_alerta",
        F.when(F.col("descricao_situacao").rlike("(?i)plen[aá]rio|pronta para pauta"), "avanco_plenario")
         .when(F.col("descricao_situacao").rlike("(?i)arquiv|encerr"), "arquivamento")
         .when(F.col("descricao_situacao").rlike("(?i)vota[çc][aã]o"), "votacao")
         .when(F.col("descricao_situacao").rlike("(?i)promulga|sancion"), "promulgacao")
    ).filter(F.col("tipo_alerta").isNotNull())
    write_gold("gold_pl_alertas_transicao", alertas)
except Exception as e:
    print(f"CDC pulado: {str(e)[:120]}")

# COMMAND ----------

# MAGIC %md ## Opcional 2 — Streaming votações (alertas + classificação urgência)

# COMMAND ----------

vt = read_silver("votacoes")
alertas_vot = (vt.withColumn("urgencia",
    F.when(F.col("descricao").rlike("(?i)urg[eê]ncia|emergen|plen[aá]rio|destaque|acordo de l[ií]deres|prioridade"),
           "urgente").otherwise("normal"))
    .select("id_votacao", "data_hora_registro", "descricao", "urgencia")
    .orderBy(F.col("data_hora_registro").desc()))
write_gold("gold_alertas_votacao", alertas_vot)
