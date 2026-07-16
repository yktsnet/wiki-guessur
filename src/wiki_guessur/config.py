import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "cache"
CORPORA_DIR = ROOT / "corpora"
RESULTS_DIR = ROOT / "results"


def load() -> dict:
    with open(ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


def dump_dir(cfg: dict) -> Path:
    return CACHE_DIR / "dump" / cfg["dump"]["date"]
