# 0003 — PySpark nativo no Databricks, pandas como fallback local

## Status
Aceita.

## Contexto
O desafio enfatiza preferência absoluta a recursos nativos do PySpark. Mas
a iteração local (CI, dev) precisa rodar sem cluster Spark.

## Opções consideradas

1. **PySpark + pandas-fallback documentado** (escolhida).
2. **Só PySpark, com instalação local de Spark/JDK**.
3. **Só pandas**, deixar Databricks pra produção.

## Decisão

- **No Databricks**: notebooks usam PySpark nativo (DataFrames Spark).
- **Localmente**: `src/pipelines/run_local.py` usa pandas com a mesma
  lógica algorítmica.
- A separação é por arquivo: `src/transforms/silver.py` usa pandas;
  notebooks Databricks (`notebooks/02_silver.py`) reimplementam em PySpark
  inline.

## Justificativa

- **Performance em produção**: Spark é o que está pedido.
- **Iteração rápida**: pandas no CI roda em 6 segundos sem subir cluster.
- **Paridade lógica**: a mesma sequência de operações (rename, parse, dedup)
  fica visível em ambos.
- Custo: alguma duplicação de lógica entre Python local e notebooks
  Databricks. Mitigado por testes pandas que cobrem semântica.

## Consequências

- Quem editar a lógica precisa atualizar nos dois lugares.
- Tests pandas servem como contrato de comportamento.
- Em ambiente Databricks puro, o módulo `src/transforms/silver.py` não é
  importado nos notebooks — fica como fallback documentado.
