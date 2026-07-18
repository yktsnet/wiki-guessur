# Structure

## ディレクトリ構成

```
src/wiki_guessur/
├── cli.py            # サブコマンドのディスパッチのみ
├── config.py          # config.toml 読み込み・パス解決
├── dump.py            # cirrussearch ダンプのパース（title・text・outgoing_link）
├── fetch.py            # ダンプ取得（冪等）
├── generate.py         # コーパス生成（scan → クエリサンプリング → 本パス）
├── features.py         # 手法間で共有する特徴量抽出
├── evaluate.py          # eval サブコマンドの実体（MRR計測・LLM層呼び出し）
├── diagnose.py          # diagnose サブコマンドの実体（言及率などの診断統計）
├── report.py            # report サブコマンドの実体（結果の集計・Markdown出力）
└── methods/
    ├── __init__.py       # get(name) によるレジストリ
    ├── formula.py         # 数式手法（係数固定）
    ├── gbdt.py            # 学習手法（LightGBM lambdarank）
    ├── llm.py             # LLM再判定層（Gemini API）
    └── trivial.py         # 自明基準線（random / mention-min / mention-max）

tests/
└── test_determinism.py  # シード決定性・係数フィットの回帰テスト

config.toml       # ダンプ版・生成パラメータ・LLM設定（唯一の設定ソース）
cache/            # ダンプ本体・scanキャッシュ（gitignore・再生成可能）
corpora/          # 生成済みコーパス（gitignore・Releasesに添付分を展開する先）
results/          # eval/report の出力（追跡対象。README Resultsの元データ）
docs/             # README から分離した全文（method.md・design-decisions.md）
```

## データフロー

```
cirrussearch dump (cache/dump/{date}/)
        │  dump.iter_docs
        ▼
scan (cache/scan-{date}.jsonl)         ← generate.py: (title, incoming_links) のみ、シード非依存
        │  母集団の確定
        ▼
generate --seed N                      ← ダンプをもう1周し、正解本文とダミー候補(reservoir sampling)を収集
        ▼
corpora/seed-N/{queries,corpus}.jsonl
        │
        ▼
eval --method {formula,gbdt,...} [--llm] --seed N
        │  methods.get(method) で rank 関数を解決 → train/test 分割 → MRR計測 → (--llm時) 僅差ケースを再判定
        ▼
results/results.jsonl (1行1構成×シード)
        │
        ▼
report                                  → results/report.md（README Resultsの元データ）
```

`compare` は generate → eval（全構成×全シード）→ report を一括で回す。`diagnose` と `sweep` は corpora/ を読むだけで、ダンプへは戻らない。
