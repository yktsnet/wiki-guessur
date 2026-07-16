import argparse

from . import config


def _seeds(spec: str) -> list[int]:
    """"0..9" または "0,3,5" 形式。"""
    if ".." in spec:
        a, b = spec.split("..")
        return list(range(int(a), int(b) + 1))
    return [int(s) for s in spec.split(",")]


def main() -> None:
    p = argparse.ArgumentParser(prog="wiki-guessur")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="Wikipediaダンプを取得（冪等）")

    g = sub.add_parser("generate", help="コーパスをシード決定的に生成")
    g.add_argument("--seed", type=int, required=True)

    e = sub.add_parser("eval", help="1構成×1シードのMRR計測")
    e.add_argument("--method", choices=["formula", "gbdt"], required=True)
    e.add_argument("--seed", type=int, required=True)

    c = sub.add_parser("compare", help="構成×シード群を一括実行")
    c.add_argument("--seeds", type=_seeds, required=True, help='例: "0..4" or "0,2,5"')
    c.add_argument("--methods", default="formula,gbdt")

    sub.add_parser("report", help="results.jsonl を集計して行列を出力")

    args = p.parse_args()
    cfg = config.load()

    if args.cmd == "fetch":
        from . import fetch
        fetch.run(cfg)
    elif args.cmd == "generate":
        from . import generate
        generate.run(cfg, args.seed)
    elif args.cmd == "eval":
        from . import evaluate
        evaluate.run(cfg, args.seed, args.method)
    elif args.cmd == "compare":
        from . import evaluate, generate
        for seed in args.seeds:
            generate.run(cfg, seed)
            for m in args.methods.split(","):
                evaluate.run(cfg, seed, m)
        from . import report
        report.run()
    elif args.cmd == "report":
        from . import report
        report.run()
