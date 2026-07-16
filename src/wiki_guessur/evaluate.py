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


def run(cfg: dict, seed: int, method_name: str) -> dict:
    queries, corpus = load_corpus(seed)
    train, test = split(queries, seed, cfg["eval"]["train_ratio"])
    print(f"seed {seed}: {len(train)} train / {len(test)} test, building tf-idf...",
          file=sys.stderr)
    tfidf = features.TitleTfidf([q["title"] for q in queries], corpus)
    m = methods.get(method_name)
    m.fit(train, corpus, tfidf)
    score = mrr(m, test, corpus, tfidf)
    result = {"seed": seed, "method": method_name, "mrr": round(score, 4),
              "n_test": len(test), "n_train": len(train)}
    config.RESULTS_DIR.mkdir(exist_ok=True)
    with open(config.RESULTS_DIR / "results.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return result
