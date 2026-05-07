# Databricks notebook source
# MAGIC %md
# MAGIC # 06 — Queries de validação dos entregáveis

# COMMAND ----------

# MAGIC %md ## 1. Top 10 frentes mais diversas (HHI)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_frente, nome_frente, n_membros, n_partidos, hhi
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_frente_diversidade`
# MAGIC ORDER BY hhi ASC LIMIT 10

# COMMAND ----------

# MAGIC %md ## 2. Top 10 deputados por taxa de presença

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_deputado, nome, sigla_partido, sigla_uf, taxa_presenca
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_taxa_presenca_deputado`
# MAGIC ORDER BY taxa_presenca DESC LIMIT 10

# COMMAND ----------

# MAGIC %md ## 3. Frentes mais alinhadas vs partidos mais alinhados

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'frente' AS tipo, alinhamento_medio, qtd_votacoes
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_resumo_alinhamento_frente`
# MAGIC ORDER BY alinhamento_medio DESC LIMIT 5

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'partido' AS tipo, sigla_partido, alinhamento_medio, qtd_votacoes
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_resumo_alinhamento_partido`
# MAGIC ORDER BY alinhamento_medio DESC LIMIT 5

# COMMAND ----------

# MAGIC %md ## 4. CEAP outliers (z-score > 3)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_deputado, nome, sigla_uf, tipo_despesa, valor_liquido,
# MAGIC        ROUND(media_grupo, 2) AS media_grupo,
# MAGIC        ROUND(z_score, 2) AS z_score
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_ceap_anomalias`
# MAGIC WHERE outlier = true
# MAGIC ORDER BY z_score DESC LIMIT 20

# COMMAND ----------

# MAGIC %md ## 4b. Top fornecedores CEAP

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT cnpj_fornecedor, nome_fornecedor, valor_total, qtd_documentos, qtd_deputados
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_ceap_ranking_fornecedor`
# MAGIC ORDER BY valor_total DESC LIMIT 15

# COMMAND ----------

# MAGIC %md ## 5. CPIs identificadas

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_orgao, sigla_orgao, nome_orgao,
# MAGIC        data_inicio, data_fim, duracao_dias, excedeu_prazo
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_cpi_catalogo`
# MAGIC ORDER BY data_inicio DESC

# COMMAND ----------

# MAGIC %md ## 6. Top 10 mais engajados

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_deputado, nome, sigla_partido,
# MAGIC        n_presencas, n_votos,
# MAGIC        ROUND(engajamento, 4) AS engajamento,
# MAGIC        ROUND(percentil_nacional, 4) AS percentil
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_engajamento_deputado`
# MAGIC ORDER BY engajamento DESC LIMIT 10

# COMMAND ----------

# MAGIC %md ## Opcional CDC — estado atual de cada PL

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_proposicao, sequencia, sigla_orgao, descricao_situacao, valid_from
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_pl_estado_atual`
# MAGIC ORDER BY valid_from DESC LIMIT 20

# COMMAND ----------

# MAGIC %md ## Opcional Streaming — votações urgentes

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_votacao, data_hora_registro, descricao, urgencia
# MAGIC FROM delta.`/Volumes/workspace/ftkeng_v3/lakehouse/gold/gold_alertas_votacao`
# MAGIC WHERE urgencia = 'urgente'
# MAGIC ORDER BY data_hora_registro DESC LIMIT 20
