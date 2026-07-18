"""根幹保証: 同一シード・同一素材からは、何度生成しても同一のコーパスが出る。"""
import bz2
import hashlib
import json
import shutil

import pytest

from wiki_guessur import config, generate


def _write_synthetic_dump(dump_dir):
    """30ページの小さなダンプ。後半のページが前半のページへリンクする。"""
    dump_dir.mkdir(parents=True)
    lines = []
    for i in range(30):
        title = f"記事{i:02d}"
        body = f"{title}とは架空の項目である。" + f"本文の説明が続く{i}。" * 30
        links = [f"記事{j:02d}" for j in range(max(0, i - 5), i)]
        lines.append(json.dumps({"index": {"_id": i}}))
        lines.append(json.dumps({
            "page_id": i, "title": title, "namespace": 0, "text": body,
            "outgoing_link": links, "incoming_links": min(5, 29 - i),
        }, ensure_ascii=False))
    with bz2.open(dump_dir / "synthetic-00000.json.bz2", "wt", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


CFG = {
    "dump": {"date": "synthetic"},
    "generate": {"num_queries": 8, "min_incoming_links": 2, "max_dummies": 3,
                 "max_doc_chars": 4000, "min_doc_chars": 10},
}


def _generate_and_hash(tmp_path, monkeypatch, run_id):
    cache = tmp_path / f"cache-{run_id}"
    corpora = tmp_path / f"corpora-{run_id}"
    monkeypatch.setattr(config, "CACHE_DIR", cache)
    monkeypatch.setattr(config, "CORPORA_DIR", corpora)
    _write_synthetic_dump(cache / "dump" / "synthetic")
    out = generate.run(CFG, seed=42)
    h = hashlib.sha256()
    for name in ["queries.jsonl", "corpus.jsonl"]:
        h.update((out / name).read_bytes())
    shutil.rmtree(cache)
    return h.hexdigest()


def test_same_seed_same_corpus(tmp_path, monkeypatch):
    h1 = _generate_and_hash(tmp_path, monkeypatch, "a")
    h2 = _generate_and_hash(tmp_path, monkeypatch, "b")
    assert h1 == h2


def test_different_seed_different_corpus(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    corpora = tmp_path / "corpora"
    monkeypatch.setattr(config, "CACHE_DIR", cache)
    monkeypatch.setattr(config, "CORPORA_DIR", corpora)
    _write_synthetic_dump(cache / "dump" / "synthetic")
    out1 = generate.run(CFG, seed=1)
    out2 = generate.run(CFG, seed=2)
    assert (out1 / "queries.jsonl").read_text() != (out2 / "queries.jsonl").read_text()


def test_strip_definition():
    assert generate.strip_definition("Xとは何かである。続きの本文。") == "続きの本文。"
    assert generate.strip_definition("句点がない場合\n2行目") == "2行目"


def test_cap_candidates_preserves_order():
    from wiki_guessur.evaluate import cap_candidates
    q = {"title": "t", "answer": "c", "candidates": ["a", "b", "c", "d"]}
    capped = cap_candidates([q], k_cap=3)[0]
    assert capped["candidates"] == ["a", "b", "c"]  # 正解cの位置を動かさない


def test_query_rng_is_stable():
    a = generate._query_rng(0, "記事").random()
    b = generate._query_rng(0, "記事").random()
    c = generate._query_rng(1, "記事").random()
    assert a == b and a != c
