"""Tests do hashing estavel."""
from src.utils.hashing import stable_hash


def test_mesma_entrada_mesmo_hash():
    obj = {"a": 1, "b": [1, 2, 3]}
    assert stable_hash(obj) == stable_hash(obj)


def test_ordem_de_chaves_nao_importa():
    a = {"x": 1, "y": 2}
    b = {"y": 2, "x": 1}
    assert stable_hash(a) == stable_hash(b)


def test_mudanca_pequena_muda_hash():
    a = {"x": 1}
    b = {"x": 2}
    assert stable_hash(a) != stable_hash(b)


def test_unicode_nao_quebra():
    obj = {"nome": "ações políticas — açaí"}
    h = stable_hash(obj)
    assert isinstance(h, str)
    assert len(h) == 64  # SHA-256 hex
