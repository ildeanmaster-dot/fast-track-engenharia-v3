"""Schemas canonicos da camada Silver.

Define renames bronze -> silver, chaves primarias e tipagem temporal por
entidade. Tambem expoe colunas de auditoria comuns a todas as tabelas Silver.

Audit cols (silver):
    silver_ingest_ts    - quando o silver foi escrito
    run_id              - correlaciona com bronze
    payload_hash        - hash do payload bronze (deteccao de mudanca)
"""
from __future__ import annotations

from typing import Any

# campo bronze -> snake_case silver (campos nao listados sao mantidos com mesmo nome)
RENAMES: dict[str, dict[str, str]] = {
    "deputados": {
        "id": "id_deputado",
        "siglaPartido": "sigla_partido",
        "siglaUf": "sigla_uf",
        "idLegislatura": "id_legislatura",
        "urlFoto": "url_foto",
    },
    "partidos": {
        "id": "id_partido",
        "sigla": "sigla_partido",
        "nome": "nome_partido",
    },
    "legislaturas": {
        "id": "id_legislatura",
        "dataInicio": "data_inicio",
        "dataFim": "data_fim",
    },
    "frentes": {
        "id": "id_frente",
        "titulo": "nome_frente",
        "idLegislatura": "id_legislatura",
    },
    "frente_membros": {
        "id": "id_deputado",
        "_parent_id": "id_frente",
        "nome": "nome_deputado",
        "siglaPartido": "sigla_partido",
        "siglaUf": "sigla_uf",
    },
    "orgaos": {
        "id": "id_orgao",
        "sigla": "sigla_orgao",
        "nome": "nome_orgao",
        "codTipoOrgao": "cod_tipo_orgao",
        "tipoOrgao": "tipo_orgao",
        "dataInicio": "data_inicio",
        "dataFim": "data_fim",
    },
    "orgao_membros": {
        "id": "id_deputado",
        "_parent_id": "id_orgao",
        "siglaPartido": "sigla_partido",
        "siglaUf": "sigla_uf",
    },
    "orgao_eventos": {
        "id": "id_evento",
        "_parent_id": "id_orgao_pai",
        "dataHoraInicio": "data_hora_inicio",
        "dataHoraFim": "data_hora_fim",
    },
    "orgao_votacoes": {
        "id": "id_votacao",
        "_parent_id": "id_orgao_pai",
        "dataHoraRegistro": "data_hora_registro",
    },
    "eventos": {
        "id": "id_evento",
        "dataHoraInicio": "data_hora_inicio",
        "dataHoraFim": "data_hora_fim",
        "descricaoTipo": "descricao_tipo",
    },
    "evento_deputados": {
        "id": "id_deputado",
        "_parent_id": "id_evento",
        "siglaPartido": "sigla_partido",
        "siglaUf": "sigla_uf",
    },
    "votacoes": {
        "id": "id_votacao",
        "dataHoraRegistro": "data_hora_registro",
    },
    "votacao_votos": {
        "_parent_id": "id_votacao",
        "tipoVoto": "tipo_voto",
        "dataRegistroVoto": "data_registro_voto",
    },
    "deputado_despesas": {
        "_parent_id": "id_deputado",
        "tipoDespesa": "tipo_despesa",
        "codDocumento": "cod_documento",
        "valorDocumento": "valor_documento",
        "valorLiquido": "valor_liquido",
        "valorGlosa": "valor_glosa",
        "dataDocumento": "data_documento",
        "nomeFornecedor": "nome_fornecedor",
        "cnpjCpfFornecedor": "cnpj_fornecedor",
    },
    "deputado_discursos": {
        "_parent_id": "id_deputado",
        "dataHoraInicio": "data_hora_inicio",
        "dataHoraFim": "data_hora_fim",
        "siglaTipoDiscurso": "tipo_discurso",
        "transcricao": "transcricao",
    },
    "proposicoes": {
        "id": "id_proposicao",
        "siglaTipo": "sigla_tipo",
        "ementa": "ementa",
        "dataApresentacao": "data_apresentacao",
    },
    "proposicao_tramitacoes": {
        "_parent_id": "id_proposicao",
        "dataHora": "data_hora",
        "siglaOrgao": "sigla_orgao",
        "descricaoSituacao": "descricao_situacao",
        "descricaoTramitacao": "descricao_tramitacao",
    },
}

PKS: dict[str, list[str]] = {
    "deputados": ["id_deputado"],
    "partidos": ["id_partido"],
    "legislaturas": ["id_legislatura"],
    "frentes": ["id_frente"],
    "frente_membros": ["id_frente", "id_deputado"],
    "orgaos": ["id_orgao"],
    "orgao_membros": ["id_orgao", "id_deputado"],
    "orgao_eventos": ["id_evento"],
    "orgao_votacoes": ["id_votacao"],
    "eventos": ["id_evento"],
    "evento_deputados": ["id_evento", "id_deputado"],
    "votacoes": ["id_votacao"],
    "votacao_votos": ["id_votacao", "id_deputado"],
    "deputado_despesas": ["id_deputado", "cod_documento"],
    "deputado_discursos": ["id_deputado", "data_hora_inicio"],
    "proposicoes": ["id_proposicao"],
    "proposicao_tramitacoes": ["id_proposicao", "sequencia"],
}

# coluna -> tipo (date | ts) para parse temporal
TEMPORAL_COLS: dict[str, list[tuple[str, str]]] = {
    "legislaturas": [("data_inicio", "date"), ("data_fim", "date")],
    "orgaos": [("data_inicio", "date"), ("data_fim", "date")],
    "orgao_eventos": [("data_hora_inicio", "ts"), ("data_hora_fim", "ts")],
    "orgao_votacoes": [("data_hora_registro", "ts")],
    "eventos": [("data_hora_inicio", "ts"), ("data_hora_fim", "ts")],
    "votacoes": [("data_hora_registro", "ts")],
    "votacao_votos": [("data_registro_voto", "ts")],
    "deputado_despesas": [("data_documento", "ts")],
    "deputado_discursos": [("data_hora_inicio", "ts"), ("data_hora_fim", "ts")],
    "proposicoes": [("data_apresentacao", "date")],
    "proposicao_tramitacoes": [("data_hora", "ts")],
}


def schema_summary() -> dict[str, Any]:
    """Resumo das entidades Silver para validacao."""
    return {
        "n_entidades": len(RENAMES),
        "entidades": sorted(RENAMES.keys()),
        "pks": PKS,
    }
