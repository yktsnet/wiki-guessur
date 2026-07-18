"""保証: eval は同一コーパス・同一手法に対して、何度実行しても同じ MRR を返す。

Reproduce の「同じ手順・同じシードで同じ数字」の評価側。生成側の決定性は
test_determinism.py が保証する。
"""
from wiki_guessur import config, evaluate, generate

from test_determinism import CFG, _write_synthetic_dump


def test_eval_same_corpus_same_mrr(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "CORPORA_DIR", tmp_path / "corpora")
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path / "results")
    _write_synthetic_dump(tmp_path / "cache" / "dump" / "synthetic")
    generate.run(CFG, seed=42)

    cfg = {**CFG, "eval": {"train_ratio": 0.5}}
    r1 = evaluate.run(cfg, seed=42, method_name="formula")
    r2 = evaluate.run(cfg, seed=42, method_name="formula")
    assert r1["mrr"] == r2["mrr"]
    assert r1["n_test"] == r2["n_test"] and r1["n_train"] == r2["n_train"]
