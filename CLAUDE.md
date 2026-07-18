# CLAUDE.md

@context/conventions.md
@context/structure.md

## フェーズ

Issueドリブン期。相談者（開放チャット）は Issue 設計のみ、実装は `issue()` で起動する実行者が行う。

## コマンド

```console
$ uv sync                                          # 依存インストール
$ uv run wiki-guessur fetch                        # jawiki cirrussearch ダンプ取得（約8.2GB・冪等）
$ uv run wiki-guessur generate --seed 0            # コーパス生成（シード決定的）
$ uv run wiki-guessur eval --method formula --seed 0
$ uv run wiki-guessur eval --method gbdt --seed 0 --llm   # 要 GEMINI_API_KEY
$ uv run wiki-guessur compare --seeds 0..4         # 生成+全手法評価+集計を一括
$ uv run wiki-guessur diagnose --seeds 0..4
$ uv run wiki-guessur sweep --seeds 0..4
$ uv run wiki-guessur report
```

LightGBM は libomp を要求する。macOS で homebrew を使っていない環境では、`DYLD_LIBRARY_PATH` に libomp の lib ディレクトリを渡す（Nix なら `nix-shell -p llvmPackages.openmp` して `nix-build '<nixpkgs>' -A llvmPackages.openmp --no-out-link` の `/lib`）。`uv` 自体も Nix 経由なら `nix-shell -p uv --run "uv run ..."`。

## アーキテクチャの要点

- 唯一の設定ソースは `config.toml`（ダンプ版・生成パラメータ・LLM設定）。ダンプの版は変えない。頑健さ評価の変動要因はシードだけに絞る。
- 手法は `src/wiki_guessur/methods/` に1手法1ファイルで実装し、`fit` / `score` の2メソッドだけを公開する（詳細は `context/conventions.md`）。
- データフローとサブコマンドの対応は `context/structure.md` を参照。

## 検証手段

- `nix-shell -p uv --run "uv run pytest -q"` — シード決定性・係数フィットの回帰テスト
- MRR数値に影響する変更（`methods/*.py`・`generate.py`・`evaluate.py`）は、変更後に `uv run wiki-guessur eval --method {対象} --seed 0` を実行し、`results/report.md` の該当値と比較する
- LLM層（`methods/llm.py`）に触れた変更は `GEMINI_API_KEY` を設定し `--llm` 付きで1回実行し、レート制限・応答パースが壊れていないか確認する
