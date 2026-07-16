"""results.jsonl を集計して手法×シードの行列と分布（平均・分散）を出す。"""
import json
import statistics
from collections import defaultdict

from . import config


def run() -> None:
    path = config.RESULTS_DIR / "results.jsonl"
    if not path.exists():
        print("no results yet; run `wiki-guessur eval` first")
        return
    latest: dict[tuple, float] = {}  # 同じ (method, seed) は最後の実行を採用
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        latest[(r["method"], r["seed"])] = r["mrr"]

    by_method: dict[str, dict[int, float]] = defaultdict(dict)
    for (m, s), v in latest.items():
        by_method[m][s] = v
    seeds = sorted({s for _, s in latest})

    header = "| method | " + " | ".join(f"seed {s}" for s in seeds) + " | mean | stdev |"
    sep = "|" + "---|" * (len(seeds) + 3)
    lines = [header, sep]
    for m in sorted(by_method):
        vals = [by_method[m].get(s) for s in seeds]
        present = [v for v in vals if v is not None]
        mean = statistics.mean(present)
        stdev = statistics.stdev(present) if len(present) > 1 else 0.0
        cells = " | ".join(f"{v:.4f}" if v is not None else "-" for v in vals)
        lines.append(f"| {m} | {cells} | {mean:.4f} | {stdev:.4f} |")
    table = "\n".join(lines)
    out = config.RESULTS_DIR / "report.md"
    out.write_text(f"# MRR by method x seed\n\n{table}\n", encoding="utf-8")
    print(table)
    print(f"\nwritten: {out}")
