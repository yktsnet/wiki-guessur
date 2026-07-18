# Guarantee Ledger

## Guarantees

### 1. `tests/test_determinism.py` — generate / evaluate (corpus generation, candidate capping)

- `generate.run` は同一シード・同一素材からは、何度実行しても同一のコーパス（queries.jsonl・corpus.jsonl）を生成する
- `generate.run` は異なるシードからは異なるコーパスを生成する（シードが分布の変動要因として機能する）
- `evaluate.cap_candidates` は候補数を上限に切り詰める際、残る候補の順序を変えない（正解の順位を動かさない）

| 保証（要約） | 対応テスト |
|---|---|
| 同一シード・同一素材 → 同一コーパス | `test_same_seed_same_corpus` |
| 異なるシード → 異なるコーパス | `test_different_seed_different_corpus` |
| 候補切り詰めで順序不変 | `test_cap_candidates_preserves_order` |

### 2. `tests/test_eval_determinism.py` — evaluate (MRR measurement)

同一コーパス・同一手法に対して、何度実行しても同じ MRR・同じ train/test 分割数を返す（Reproduce の「同じ手順・同じシードで同じ数字」の評価側。生成側は 1. が保証する）。

| 保証（要約） | 対応テスト |
|---|---|
| 同一コーパス・同一手法 → 同一 MRR | `test_eval_same_corpus_same_mrr` |

### 3. `tests/test_llm_fallback.py` — methods/llm (rerank fallback)

- `_call` は API 応答に `candidates` が含まれない場合（セーフティブロック等）、例外を投げず None を返す
- `rerank_sample` は判定が None のケースをスキップとして数え、基礎スコアラーの順位を維持したまま完走する（スキップのみの場合、各推定値は None になる）

| 保証（要約） | 対応テスト |
|---|---|
| candidates 欠落応答 → None（例外なし） | `test_call_returns_none_without_candidates` |
| 判定不能ケースはスキップし順位維持 | `test_rerank_sample_skips_when_call_returns_none` |

### 4. `tests/test_report.py` — report (aggregation)

手法×シードの集計（平均・stdev）が個別の評価結果と整合する。LLM 層つきの行は実測 `mrr` でなく推定 `mrr_est` を採用し、`k_cap` つきの結果は掃引表へ分離集計される。

| 保証（要約） | 対応テスト |
|---|---|
| 平均・stdev が個別結果と整合（mrr_est 優先・掃引分離） | `test_report_aggregates_results` |

## About

対象は契約面（CLI から観測可能な生成・評価・集計の振る舞い、README の Reproduce が約束する再現性）のみで、内部実装（`strip_definition`・`_query_rng` 等）のテストは載せない。ここに載っていない振る舞いは約束ではなく、予告なく変わりうる。本台帳は docs/design-decisions.md と同格であり、実装が食い違う場合は指摘対象である。
