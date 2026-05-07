# Modelo de dados

## Bronze

17 entidades, uma tabela por endpoint da API. Schema "raw" (JSON aninhado
preservado), com colunas de auditoria adicionadas.

## Silver

Após rename para `snake_case` e tipagem:

### Listas base

| Tabela | PK | Campos principais |
|---|---|---|
| `deputados` | `id_deputado` | nome, sigla_partido, sigla_uf, id_legislatura |
| `partidos` | `id_partido` | sigla_partido, nome_partido |
| `legislaturas` | `id_legislatura` | data_inicio, data_fim |
| `frentes` | `id_frente` | nome_frente, id_legislatura |
| `orgaos` | `id_orgao` | sigla_orgao, nome_orgao, tipo_orgao, data_inicio, data_fim |
| `eventos` | `id_evento` | data_hora_inicio, descricao_tipo, situacao |
| `votacoes` | `id_votacao` | data_hora_registro, descricao |
| `proposicoes` | `id_proposicao` | sigla_tipo, ementa, data_apresentacao |

### Fanouts (1:N)

| Tabela | PK |
|---|---|
| `frente_membros` | (id_frente, id_deputado) |
| `evento_deputados` | (id_evento, id_deputado) |
| `votacao_votos` | (id_votacao, id_deputado) |
| `deputado_despesas` | (id_deputado, cod_documento) |
| `deputado_discursos` | (id_deputado, data_hora_inicio) |
| `proposicao_tramitacoes` | (id_proposicao, sequencia) |
| `orgao_membros` | (id_orgao, id_deputado) |
| `orgao_eventos` | (id_evento) |
| `orgao_votacoes` | (id_votacao) |

## Gold — Star schema

### Dimensões (7)

| Tabela | Origem |
|---|---|
| `dim_deputado` | `silver.deputados` |
| `dim_partido` | `silver.partidos` |
| `dim_frente` | `silver.frentes` |
| `dim_orgao` | `silver.orgaos` |
| `dim_evento` | `silver.eventos` |
| `dim_fornecedor` | derivada de `silver.deputado_despesas` |
| `dim_data` | derivada das colunas temporais |

### Fatos (4)

| Tabela | Granularidade | Origem |
|---|---|---|
| `fato_voto` | (id_votacao, id_deputado) | `silver.votacao_votos` |
| `fato_presenca` | (id_evento, id_deputado) | `silver.evento_deputados` |
| `fato_despesa` | (id_deputado, cod_documento) | `silver.deputado_despesas` |
| `fato_tramitacao` | (id_proposicao, sequencia) | `silver.proposicao_tramitacoes` |

### Tabelas analíticas (gold_*)

Uma ou mais por entregável. Ver
[../src/analytics/](../src/analytics/) para detalhes.

## Relacionamentos

```
dim_data
 ▲
 │
fato_voto ─────► dim_deputado ─────► dim_partido
 │                  │
 ▼                  ▼
dim_frente       dim_orgao
                    │
                    ▼
                 dim_evento
                    │
                    ▼
                fato_presenca
                    │
                    ▼
                dim_data

fato_despesa ─────► dim_deputado
            │
            └─────► dim_fornecedor

fato_tramitacao ──► proposicoes (id_proposicao)
```
