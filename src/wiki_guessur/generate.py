"""コーパス生成。シードを固定すれば決定的に同じコーパスを再生成できる。

1. scan: ダンプ全体から (title, incoming_links) を1回だけ抽出してキャッシュする（シード非依存）。
2. generate: 母集団からシード付きでクエリをサンプリングし、ダンプをもう1周して
   正解本文と、そのクエリ記事名にリンクしている記事（ダミー候補）を集める。
   ダミーはクエリごとの reservoir sampling（シード決定的）で選ぶ。
"""
import hashlib
import json
import random
import sys
from pathlib import Path

from . import config
from .dump import iter_docs, normalize_title


def _scan_path(cfg: dict) -> Path:
    return config.CACHE_DIR / f"scan-{cfg['dump']['date']}.jsonl"


def scan(cfg: dict) -> Path:
    """全ページの (title, incoming_links) を抽出。キャッシュがあれば何もしない。"""
    path = _scan_path(cfg)
    if path.exists():
        return path
    tmp = path.with_suffix(".part")
    n = 0
    with open(tmp, "w", encoding="utf-8") as out:
        for doc in iter_docs(config.dump_dir(cfg)):
            out.write(json.dumps(
                {"t": doc["title"], "in": doc.get("incoming_links", 0)},
                ensure_ascii=False) + "\n")
            n += 1
    tmp.rename(path)
    print(f"scan: {n} pages -> {path}", file=sys.stderr)
    return path


def _query_rng(seed: int, title: str) -> random.Random:
    h = hashlib.sha256(f"{seed}:{title}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def strip_definition(text: str) -> str:
    """冒頭の定義文（最初の「。」まで）を除去する。"""
    head = text[:500]
    pos = head.find("。")
    if pos == -1:
        pos = head.find("\n")
    if pos == -1:
        return text
    return text[pos + 1:].lstrip()


def run(cfg: dict, seed: int) -> Path:
    g = cfg["generate"]
    out_dir = config.CORPORA_DIR / f"seed-{seed}"
    if (out_dir / "queries.jsonl").exists():
        print(f"corpus exists: {out_dir}", file=sys.stderr)
        return out_dir

    # 母集団の確定とクエリのサンプリング
    population = []
    with open(scan(cfg), encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["in"] >= g["min_incoming_links"]:
                population.append(rec["t"])
    population.sort()
    rng = random.Random(seed)
    queries = rng.sample(population, min(g["num_queries"], len(population)))
    qset = set(queries)
    print(f"population {len(population)}, sampled {len(queries)} queries", file=sys.stderr)

    # 本パス: 正解本文の収集と、ダミー候補の reservoir sampling
    answer: dict[str, dict] = {}          # query title -> doc
    reservoirs: dict[str, list[dict]] = {q: [] for q in queries}
    seen: dict[str, int] = {q: 0 for q in queries}
    target = {q: _query_rng(seed, q).randint(1, g["max_dummies"]) for q in queries}

    def clip(doc: dict) -> dict:
        return {"id": f"d{doc['page_id']}",
                "text": strip_definition(doc.get("text", ""))[:g["max_doc_chars"]]}

    for doc in iter_docs(config.dump_dir(cfg)):
        title = doc["title"]
        if title in qset:
            answer[title] = clip(doc)
        for link in doc.get("outgoing_link", []):
            t = normalize_title(link)
            if t not in qset or t == title:
                continue
            seen[t] += 1
            k = target[t]
            if len(reservoirs[t]) < k:
                reservoirs[t].append(clip(doc))
            else:
                j = _query_rng(seed, f"{t}:{seen[t]}").randrange(seen[t])
                if j < k:
                    reservoirs[t][j] = clip(doc)

    # 出力（本文が短すぎる・ダミーが取れなかったクエリは落とす）
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus: dict[str, str] = {}
    kept = dropped = 0
    with open(out_dir / "queries.jsonl", "w", encoding="utf-8") as qf:
        for q in queries:
            ans = answer.get(q)
            dummies = [d for d in reservoirs[q]
                       if ans and d["id"] != ans["id"] and len(d["text"]) >= g["min_doc_chars"]]
            if not ans or len(ans["text"]) < g["min_doc_chars"] or not dummies:
                dropped += 1
                continue
            cands = [ans] + dummies
            _query_rng(seed, f"{q}:shuffle").shuffle(cands)
            for d in cands:
                corpus[d["id"]] = d["text"]
            qf.write(json.dumps(
                {"title": q, "answer": ans["id"], "candidates": [d["id"] for d in cands]},
                ensure_ascii=False) + "\n")
            kept += 1
    with open(out_dir / "corpus.jsonl", "w", encoding="utf-8") as cf:
        for doc_id in sorted(corpus):
            cf.write(json.dumps({"id": doc_id, "text": corpus[doc_id]}, ensure_ascii=False) + "\n")
    with open(out_dir / "meta.json", "w", encoding="utf-8") as mf:
        json.dump({"seed": seed, "dump": cfg["dump"]["date"], "queries": kept,
                   "dropped": dropped, "corpus_docs": len(corpus)}, mf, ensure_ascii=False, indent=2)
    print(f"generated {out_dir}: {kept} queries ({dropped} dropped), {len(corpus)} docs", file=sys.stderr)
    return out_dir
