"""コーパスの診断統計。ベンチマークの前提（言及と同一性のねじれ）を実測で確かめる。

- 記事名の出現率: 正解本文とダミー本文で、記事名をそのまま含む割合と平均回数を比べる。
  ダミー側が高ければ「名前に言及する文書ほど正解ではない」ねじれが実在する。
- 候補数kの分布: MRR の解釈に必要（kが小さいほど当てやすい）。
- ランダム基準MRR: 一様ランダムに順位付けした場合の期待値 E[1/rank] = H(k)/k をクエリ平均。
"""
import json
import statistics
import sys
from collections import Counter

from . import config
from .evaluate import load_corpus


def _harmonic(k: int) -> float:
    return sum(1.0 / i for i in range(1, k + 1))


def run(seed: int) -> dict:
    queries, corpus = load_corpus(seed)
    ans_has = ans_cnt = dum_has = dum_cnt = n_dum = 0
    ks = Counter()
    rand_mrr = []
    for q in queries:
        t = q["title"]
        k = len(q["candidates"])
        ks[k] += 1
        rand_mrr.append(_harmonic(k) / k)
        for cid in q["candidates"]:
            m = corpus[cid].count(t)
            if cid == q["answer"]:
                ans_has += bool(m)
                ans_cnt += m
            else:
                dum_has += bool(m)
                dum_cnt += m
                n_dum += 1
    n = len(queries)
    result = {
        "seed": seed,
        "queries": n,
        "k_mean": round(sum(k * c for k, c in ks.items()) / n, 2),
        "k_dist": {str(k): ks[k] for k in sorted(ks)},
        "random_mrr": round(statistics.mean(rand_mrr), 4),
        "answer_mention_rate": round(ans_has / n, 4),
        "answer_mentions_avg": round(ans_cnt / n, 2),
        "dummy_mention_rate": round(dum_has / n_dum, 4),
        "dummy_mentions_avg": round(dum_cnt / n_dum, 2),
    }
    config.RESULTS_DIR.mkdir(exist_ok=True)
    with open(config.RESULTS_DIR / f"diagnostics-seed-{seed}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
    return result
