"""MRR 計測。クエリをシード決定的に train/test に割り、test 側で測る。

数式手法は train を使わないが、手法間の公平のため全手法を同じ test 集合で測る。
"""
import json
import random
import sys
from pathlib import Path

from . import config, features, methods


def load_corpus(seed: int) -> tuple[list[dict], dict[str, str]]:
    d = config.CORPORA_DIR / f"seed-{seed}"
    queries = [json.loads(l) for l in open(d / "queries.jsonl", encoding="utf-8")]
    corpus = {r["id"]: r["text"] for r in
              (json.loads(l) for l in open(d / "corpus.jsonl", encoding="utf-8"))}
    return queries, corpus


def split(queries: list[dict], seed: int, train_ratio: float):
    order = list(range(len(queries)))
    random.Random(f"split:{seed}").shuffle(order)
    n_train = int(len(queries) * train_ratio)
    train = [queries[i] for i in order[:n_train]]
    test = [queries[i] for i in order[n_train:]]
    return train, test


def mrr(method, queries: list[dict], corpus, tfidf) -> float:
    total = 0.0
    for q in queries:
        scores = method.score(q["title"], q["candidates"], corpus, tfidf)
        ranked = sorted(q["candidates"], key=lambda c: scores[c], reverse=True)
        total += 1.0 / (ranked.index(q["answer"]) + 1)
    return total / len(queries)


def cap_candidates(queries: list[dict], k_cap: int) -> list[dict]:
    """難易度ノブ: 候補数を k_cap に切り詰める（正解＋保存順の先頭ダミー）。決定的。

    保存順（生成時にシャッフル済み）を保って間引く。並べ替えると、スコア同点時に
    安定ソートが先頭要素を優遇するため、正解を先頭へ移す実装は MRR を水増しする。
    """
    capped = []
    for q in queries:
        dummies = [c for c in q["candidates"] if c != q["answer"]][:k_cap - 1]
        keep = set(dummies) | {q["answer"]}
        capped.append({**q, "candidates": [c for c in q["candidates"] if c in keep]})
    return capped


def load_context(seed: int) -> tuple[list[dict], dict[str, str], features.TitleTfidf]:
    """コーパスと TF-IDF をまとめて構築する。複数評価で使い回せる。"""
    queries, corpus = load_corpus(seed)
    print(f"seed {seed}: building tf-idf...", file=sys.stderr)
    tfidf = features.TitleTfidf([q["title"] for q in queries], corpus)
    return queries, corpus, tfidf


def run(cfg: dict, seed: int, method_name: str, k_cap: int | None = None,
        context: tuple | None = None, llm: bool = False) -> dict:
    queries, corpus, tfidf = context if context else load_context(seed)
    if k_cap is not None:
        queries = cap_candidates(queries, k_cap)
    train, test = split(queries, seed, cfg["eval"]["train_ratio"])
    m = methods.get(method_name)
    m.fit(train, corpus, tfidf)
    score = mrr(m, test, corpus, tfidf)
    result = {"seed": seed, "method": method_name, "mrr": round(score, 4),
              "n_test": len(test), "n_train": len(train)}
    if k_cap is not None:
        result["k_cap"] = k_cap
    if llm:
        from .methods.llm import rerank_sample
        result["method"] = f"{method_name}+llm"
        result["llm"] = rerank_sample(
            method_name, test,
            lambda q: m.score(q["title"], q["candidates"], corpus, tfidf),
            corpus, cfg["llm"], seed)
        result["mrr_est"] = round(score + result["llm"]["mrr_gain_est"], 4)
    config.RESULTS_DIR.mkdir(exist_ok=True)
    with open(config.RESULTS_DIR / "results.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return result
