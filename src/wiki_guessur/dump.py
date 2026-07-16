"""cirrussearch ダンプ（ES bulk 形式）の読み出し。"""
import bz2
import json
import sys
from pathlib import Path
from typing import Iterator


def shard_paths(dump_dir: Path) -> list[Path]:
    return sorted(dump_dir.glob("*.json.bz2"))


def iter_docs(dump_dir: Path, progress: bool = True) -> Iterator[dict]:
    """本文ページ（namespace 0）だけを順に返す。順序はファイル名順×行順で決定的。"""
    paths = shard_paths(dump_dir)
    if not paths:
        raise FileNotFoundError(f"no dump shards in {dump_dir}; run `wiki-guessur fetch` first")
    for i, path in enumerate(paths):
        if progress:
            print(f"  shard {i + 1}/{len(paths)}: {path.name}", file=sys.stderr)
        with bz2.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                doc = json.loads(line)
                if "page_id" not in doc:  # {"index": ...} のアクション行
                    continue
                if doc.get("namespace") != 0:
                    continue
                yield doc


def normalize_title(t: str) -> str:
    """outgoing_link はアンダースコア区切りのことがあるので title 表記に揃える。"""
    return t.replace("_", " ")
