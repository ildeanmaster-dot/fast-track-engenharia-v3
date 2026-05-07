"""Pipeline local end-to-end em pandas (sem Spark).

Orquestra: bronze (API -> JSONL) -> silver -> gold dim/fato -> 6 entregaveis
+ 2 opcionais. Salva todos os DataFrames como parquet em data/gold/.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.analytics import (
    atlas_frentes,
    calendario,
    cdc_tramitacao,
    ceap,
    correlacao,
    cpis,
    engajamento,
    streaming_votacoes,
)
from src.ingestion.bronze import collect_all
from src.transforms import gold as gold_mod
from src.transforms.silver import to_silver_all
from src.utils.config_loader import load, load_ideologia
from src.utils.logging_setup import setup_logging

GOLD_DIR = Path("data/gold")


def _save(df: pd.DataFrame | None, name: str) -> None:
    if df is None or df.empty:
        print(f"  [skip] {name} (vazio)")
        return
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    out = GOLD_DIR / f"{name}.parquet"
    df.to_parquet(out, index=False)
    print(f"  [ok]   {name:<40s} {len(df):>5d}")


def main(skip_bronze: bool = False) -> None:
    logger, run_id, _ = setup_logging(level=logging.INFO)
    logger.info("pipeline iniciado", extra={"run_id": run_id, "skip_bronze": skip_bronze})

    cfg = load()
    ideologia = load_ideologia()

    if not skip_bronze:
        print("\n=== Bronze (API -> JSONL) ===")
        results = collect_all(cfg, run_id, max_pages_simple=2)
        total = sum(results.values())
        print(f"\nTotal bronze: {total} registros em {len(results)} entidades")

    print("\n=== Silver ===")
    silver = to_silver_all(run_id=run_id)
    for name, df in silver.items():
        print(f"  {name:<25s} {len(df):>5d}")

    print("\n=== Gold - dimensoes e fatos ===")
    _save(gold_mod.dim_deputado(silver), "dim_deputado")
    _save(gold_mod.dim_partido(silver), "dim_partido")
    _save(gold_mod.dim_frente(silver), "dim_frente")
    _save(gold_mod.dim_orgao(silver), "dim_orgao")
    _save(gold_mod.dim_evento(silver), "dim_evento")
    _save(gold_mod.dim_fornecedor(silver), "dim_fornecedor")
    _save(gold_mod.dim_data(silver), "dim_data")
    _save(gold_mod.fato_voto(silver), "fato_voto")
    _save(gold_mod.fato_presenca(silver), "fato_presenca")
    _save(gold_mod.fato_despesa(silver), "fato_despesa")
    _save(gold_mod.fato_tramitacao(silver), "fato_tramitacao")

    blocks = [
        ("Atlas frentes",  lambda: atlas_frentes.build_all(silver, ideologia)),
        ("Calendario",     lambda: calendario.build_all(silver)),
        ("Correlacao",     lambda: correlacao.build_all(silver)),
        ("CEAP",           lambda: ceap.build_all(silver)),
        ("CPIs",           lambda: cpis.build_all(silver)),
        ("Engajamento",    lambda: engajamento.build_all(silver)),
        ("CDC tramitacao", lambda: cdc_tramitacao.build_all(silver)),
        ("Streaming",      lambda: streaming_votacoes.build_all(silver)),
    ]

    for label, builder in blocks:
        print(f"\n=== Gold - {label} ===")
        try:
            for name, df in builder().items():
                _save(df, name)
        except Exception as exc:
            logger.exception("erro em %s", label)
            print(f"  [erro] {label}: {exc}")

    print(f"\nFinalizado. run_id={run_id} | gold em {GOLD_DIR.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-bronze", action="store_true",
                        help="reutiliza JSONL ja em data/samples/")
    args = parser.parse_args()
    main(skip_bronze=args.skip_bronze)
