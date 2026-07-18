# Conventions

## 手法の実装

- 各手法は `src/wiki_guessur/methods/` に1ファイル1手法で置き、`methods/__init__.py` の `get(name)` で名前解決する。
- 手法は `fit(train_queries, corpus, tfidf)` と `score(title, candidate_ids, corpus, tfidf) -> {doc_id: score}` の2メソッドだけを公開する（スコアは高いほど正解らしい）。学習しない手法（formula・random・mention-*）は `fit` を何もせず通す。
- 数式手法の係数（`formula.py` の `W_*`）は初回生成でグリッドフィットした値に固定し、以後コードでは調整しない。調整する場合は係数を変えるのではなく、フィット根拠をdocstringに残した上で変える。

## 決定性

- 乱数はグローバルな RNG を共有しない。`generate.py` の `_query_rng(seed, key)` のように `hash(seed, キー)` から都度導出する。新しい乱択処理を足すときもこのパターンに従う。
- シードが同じなら出力が完全に決定的であることが頑健さ評価の前提。乱数の使い方を変える変更は決定性テスト（`tests/test_determinism.py`）で確認する。

## モジュール分割

- `config.py` — 設定読み込みとパス解決のみ。ロジックを持たない。
- `dump.py` — cirrussearchダンプのパースのみ。
- `generate.py` / `fetch.py` / `evaluate.py` / `diagnose.py` / `report.py` — CLIサブコマンド1つに対応する処理単位。`cli.py` はここへの薄いディスパッチに留める。
- `features.py` — 手法間で共有する特徴量抽出（TF-IDF類似度・出現回数など）。手法固有の重み付けは各 `methods/*.py` 側に置く。

## コード内コメント

- 「何をしているか」ではなく、判断の理由（なぜこの実装か・何を試して捨てたか）を書く。`formula.py` の係数固定の経緯や、`generate.py` の reservoir sampling の理由がその型。
