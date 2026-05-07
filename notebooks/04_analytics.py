# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Analytics (6 entregáveis obrigatórios)

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

# MAGIC %md ## Entregavel 1 — Atlas + HHI

# COMMAND ----------

atlas = (fm.alias("m")
           .join(dep.alias("d"), "id_deputado", "left")
           .join(fr.alias("f"), "id_frente", "left")
           .select("id_frente", F.col("f.nome_frente"), "id_deputado",
                   F.col("d.nome").alias("nome"),
                   F.col("d.sigla_partido"), F.col("d.sigla_uf")))
write_gold("gold_atlas_frentes", atlas)

participacao = atlas.groupBy("id_frente", "sigla_partido").count().withColumnRenamed("count", "n_partido")
total_frente = atlas.groupBy("id_frente").count().withColumnRenamed("count", "total")
hhi = (participacao.join(total_frente, "id_frente")
                   .withColumn("share", F.col("n_partido") / F.col("total"))
                   .groupBy("id_frente")
                   .agg(F.sum(F.pow("share", 2)).alias("hhi"),
                        F.first("total").alias("n_membros"),
                        F.countDistinct("sigla_partido").alias("n_partidos"))
                   .join(fr.select("id_frente", "nome_frente"), "id_frente", "left")
                   .orderBy("hhi"))
write_gold("gold_frente_diversidade", hhi)

# COMMAND ----------

# MAGIC %md ## Entregavel 2 — Calendario

# COMMAND ----------

total_eventos = ev.select("id_evento").distinct().count()
presencas = ed.groupBy("id_deputado").count().withColumnRenamed("count", "n_presencas")
taxa = (presencas.join(dep, "id_deputado")
                 .withColumn("total_eventos", F.lit(total_eventos))
                 .withColumn("taxa_presenca", F.col("n_presencas") / F.col("total_eventos"))
                 .select("id_deputado", "nome", "sigla_partido", "sigla_uf",
                         "n_presencas", "total_eventos", "taxa_presenca")
                 .orderBy(F.col("taxa_presenca").desc()))
write_gold("gold_taxa_presenca_deputado", taxa)

densidade = (ev.withColumn("ano", F.year("data_hora_inicio"))
               .withColumn("semana", F.weekofyear("data_hora_inicio"))
               .groupBy("ano", "semana").count()
               .withColumnRenamed("count", "qtd_eventos")
               .orderBy("ano", "semana"))
write_gold("gold_densidade_semanal", densidade)

futuros = ev.filter(F.col("data_hora_inicio") > F.current_timestamp())
write_gold("gold_eventos_futuros", futuros)

# COMMAND ----------

# MAGIC %md ## Entregavel 3 — Alinhamento

# COMMAND ----------

vv_validos = vv.filter(F.col("tipo_voto").isin("Sim", "Nao"))

def alinhamento_por(df, group_col):
    pivot = (df.groupBy("id_votacao", group_col, "tipo_voto").count()
               .groupBy("id_votacao", group_col)
               .pivot("tipo_voto", ["Sim", "Nao"]).sum("count").na.fill(0))
    return (pivot.withColumn("total", F.col("Sim") + F.col("Nao"))
                  .filter(F.col("total") >= 2)
                  .withColumn("alinhamento",
                              F.greatest(F.col("Sim"), F.col("Nao")) / F.col("total")))

ali_p = alinhamento_por(vv_validos, "sigla_partido")
resumo_p = (ali_p.groupBy("sigla_partido")
                  .agg(F.avg("alinhamento").alias("alinhamento_medio"),
                       F.countDistinct("id_votacao").alias("qtd_votacoes"))
                  .orderBy(F.col("alinhamento_medio").desc()))
write_gold("gold_resumo_alinhamento_partido", resumo_p)

vv_frente = vv_validos.join(fm.select("id_frente", "id_deputado"), "id_deputado")
ali_f = alinhamento_por(vv_frente, "id_frente")
resumo_f = (ali_f.groupBy("id_frente")
                  .agg(F.avg("alinhamento").alias("alinhamento_medio"),
                       F.countDistinct("id_votacao").alias("qtd_votacoes"))
                  .join(fr.select("id_frente", "nome_frente"), "id_frente", "left")
                  .orderBy(F.col("alinhamento_medio").desc()))
write_gold("gold_resumo_alinhamento_frente", resumo_f)

# COMMAND ----------

# MAGIC %md ## Entregavel 4 — CEAP com z-score

# COMMAND ----------

w_grupo = Window.partitionBy("tipo_despesa", "sigla_uf")
ceap = (desp.join(dep.select("id_deputado", "sigla_partido", "sigla_uf", "nome"),
                   "id_deputado", "left")
            .withColumn("media_grupo", F.avg("valor_liquido").over(w_grupo))
            .withColumn("std_grupo", F.stddev("valor_liquido").over(w_grupo))
            .withColumn("z_score",
                        F.expr("try_divide(valor_liquido - media_grupo, std_grupo)"))
            .withColumn("outlier", F.coalesce(F.abs("z_score") > 3, F.lit(False))))
write_gold("gold_ceap_anomalias", ceap)

ranking = (desp.groupBy("cnpj_fornecedor", "nome_fornecedor")
               .agg(F.sum("valor_liquido").alias("valor_total"),
                    F.count("cod_documento").alias("qtd_documentos"),
                    F.countDistinct("id_deputado").alias("qtd_deputados"))
               .orderBy(F.col("valor_total").desc()))
write_gold("gold_ceap_ranking_fornecedor", ranking.limit(200))

# COMMAND ----------

# MAGIC %md ## Entregavel 5 — CPIs

# COMMAND ----------

cpis = orgs.filter(F.col("nome_orgao").rlike("(?i)CPI|CPMI|Inqu[eé]rito"))
if "data_inicio" not in cpis.columns:
    cpis = cpis.withColumn("data_inicio", F.lit(None).cast("date"))
if "data_fim" not in cpis.columns:
    cpis = cpis.withColumn("data_fim", F.lit(None).cast("date"))
cpis = (cpis.withColumn("duracao_dias", F.datediff("data_fim", "data_inicio"))
            .withColumn("excedeu_prazo",
                        F.coalesce(F.col("duracao_dias") > 180, F.lit(False))))
write_gold("gold_cpi_catalogo", cpis)

# COMMAND ----------

# MAGIC %md ## Entregavel 6 — Engajamento

# COMMAND ----------

n_pres = ed.groupBy("id_deputado").count().withColumnRenamed("count", "n_presencas")
n_vot = vv.groupBy("id_deputado").count().withColumnRenamed("count", "n_votos")

eng = (dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf")
          .join(n_pres, "id_deputado", "left")
          .join(n_vot, "id_deputado", "left")
          .na.fill(0, ["n_presencas", "n_votos"]))

def norm_minmax(df, c):
    rng = df.agg((F.max(c) - F.min(c)).alias("rng"), F.min(c).alias("mn")).collect()[0]
    rng_v = rng["rng"] or 1
    mn = rng["mn"] or 0
    return df.withColumn(f"{c}_norm", (F.col(c) - F.lit(mn)) / F.lit(rng_v))

eng = norm_minmax(eng, "n_presencas")
eng = norm_minmax(eng, "n_votos")
eng = eng.withColumn("engajamento", (F.col("n_presencas_norm") + F.col("n_votos_norm")) / 2)
eng = eng.withColumn("percentil_nacional", F.percent_rank().over(Window.orderBy("engajamento")))
write_gold("gold_engajamento_deputado", eng.orderBy(F.col("engajamento").desc()))

total_v = vv.select("id_votacao").distinct().count()
votou = vv.groupBy("id_deputado").agg(F.countDistinct("id_votacao").alias("n_votou"))
absent = (dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf")
              .join(votou, "id_deputado", "left").na.fill(0, ["n_votou"])
              .withColumn("n_ausencias", F.lit(total_v) - F.col("n_votou"))
              .withColumn("taxa_ausencia", F.col("n_ausencias") / F.lit(total_v))
              .orderBy(F.col("taxa_ausencia").desc()))
write_gold("gold_absenteismo_votacao", absent)
