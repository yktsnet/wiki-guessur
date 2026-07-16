"""ダンプの取得。取得済みシャードはスキップする（冪等）。"""
import sys
import urllib.request
from pathlib import Path

from . import config


def run(cfg: dict) -> None:
    d = cfg["dump"]
    out_dir = config.dump_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{d['base_url']}/{d['date']}/index_name%3D{d['index']}"
    for i in range(d["shards"]):
        name = f"{d['index']}-{d['date']}-{i:05d}.json.bz2"
        dest = out_dir / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  skip {name} (exists)", file=sys.stderr)
            continue
        url = f"{base}/{name}"
        print(f"  get  {name}", file=sys.stderr)
        tmp = dest.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)
    print(f"done: {out_dir}", file=sys.stderr)
