# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Gold (dimensões + fatos)

# COMMAND ----------

from pyspark.sql import functions as F

LAKEHOUSE = "/Volumes/workspace/ftkeng_v3/lakehouse"

def read_silver(name):
    return spark.read.format("delta").load(f"{LAKEHOUSE}/silver/{name}")

def write_gold(name, df):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true") \
          .save(f"{LAKEHOUSE}/gold/{name}")
    n = df.count()
    print(f"  gold.{name:<30s} {n:>5d} rows")
    return n

# COMMAND ----------

dep = read_silver("deputados")
part = read_silver("partidos")
fr = read_silver("frentes")
fm = read_silver("frente_membros")
orgs = read_silver("orgaos")
ev = read_silver("eventos")
ed = read_silver("evento_deputados")
vt = read_silver("votacoes")
vv = read_silver("votacao_votos")
desp = read_silver("deputado_despesas")

# COMMAND ----------

# MAGIC %md ## Dimensões

# COMMAND ----------

write_gold("dim_deputado",
           dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf", "id_legislatura"))
write_gold("dim_partido", part)
write_gold("dim_frente", fr)
write_gold("dim_orgao", orgs)
write_gold("dim_evento",
           ev.select("id_evento", "data_hora_inicio", "data_hora_fim",
                     "descricao_tipo", "situacao"))

forn = (desp.select("cnpj_fornecedor", "nome_fornecedor")
            .filter(F.col("cnpj_fornecedor").isNotNull())
            .dropDuplicates(["cnpj_fornecedor"]))
write_gold("dim_fornecedor", forn)

# COMMAND ----------

# MAGIC %md ## Fatos

# COMMAND ----------

write_gold("fato_voto",
           vv.select("id_votacao", "id_deputado", "tipo_voto", "sigla_partido", "sigla_uf"))
write_gold("fato_presenca",
           ed.select("id_evento", "id_deputado", "sigla_partido", "sigla_uf"))
write_gold("fato_despesa", desp)

try:
    tram = read_silver("proposicao_tramitacoes")
    write_gold("fato_tramitacao", tram)
except Exception as e:
    print(f"fato_tramitacao pulado: {str(e)[:100]}")
