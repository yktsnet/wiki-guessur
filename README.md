# wiki-guessur

冒頭の定義文を消されたWikipedia記事がどの記事名に対応するかを、係数固定の数式・再学習するGBDT・LLM再判定の組み合わせで解き、コーパスを引き直しても当て続けられるかを実測するベンチマーク。

LLMやRAGを「使えば解ける」で終わらせると、何が効いて解けたのかが残らない。このリポは記事名と欠損本文の対応付けという1つのタスクを、2種の基礎スコアラー（人が係数を決める数式手法、機械が係数を決める学習手法）と、その上に載せるLLM再判定層（僅差ケースだけLLMに聞く）の組み合わせ4通りで解き、手法の性格差を実測で見えるようにする実験場である。

## Results

5シード（0〜4）でのMRR平均・標準偏差。

| method | mean | stdev |
|---|---|---|
| formula（数式のみ） | 0.8383 | 0.0060 |
| formula+llm | 0.8528 | 0.0050 |
| gbdt（学習のみ） | 0.8580 | 0.0065 |
| gbdt+llm | 0.8735 | 0.0058 |
| mention-max（自明基準） | 0.7277 | 0.0053 |
| mention-min | 0.3573 | 0.0096 |
| random | 0.4716 | 0.0084 |

工夫した2手法（数式・学習）は自明基準（記事名の言及回数だけで選ぶ）やランダムを明確に上回り、分布も安定している（stdev 0.006前後）。formulaとgbdtの差は0.02弱で、自動適応する学習手法がやや優位だが差は大きくない。

LLM再判定層はseed 0〜4の全シードで一貫して底上げする（formula側+0.0145、gbdt側+0.0155）。ただしLLMの正解選択率は土台が強いほど下がる（formula僅差で80〜91%、gbdt僅差で63〜75%）。土台のスコアラーが多くの手がかりを使い切るほど、残る僅差ケースは本質的に紛らわしい問題として残るためと考えられる。詳細は[Design Decisions](#design-decisions)を参照。

難易度ノブ（候補数上限k）を動かした場合、formula・gbdtとも候補が増えるほど単調に劣化し、この掃引だけでは2手法の頑健さの差はあまり見えていない。

| method | k=2 | k=4 | k=6 | k=8 | k=10 |
|---|---|---|---|---|---|
| formula | 0.9335 | 0.8768 | 0.8514 | 0.8414 | 0.8383 |
| gbdt | 0.9395 | 0.8921 | 0.8696 | 0.8618 | 0.8580 |

再実行するには [Reproduce](#reproduce) の `report` を参照。

## Method

Wikipediaの記事本文から、冒頭の定義文（「〇〇とは、〜である」の一文）だけを消す。残った本文と記事名の候補群を渡し、どの候補がその本文の記事名かを当てさせる。候補には正解の記事名1つに加えて、その記事名にリンクしている別記事（言及はしているが本人ではない記事）を数件混ぜる。Wikipediaの記事は本文中で自分の名前を繰り返す一方、他記事へのリンクはアンカー表記が記事名と一致しないことが多い。定義文を消すと自己同定の手がかりは減るが、本文中の名前の出現頻度という手がかりはまだ残っている。この手がかりをどこまで使い切れるかが、4通りの手法の性格差として現れる。

評価はMRR（Mean Reciprocal Rank）。記事名ごとに「正解の候補が候補一覧の何位に来たか」の逆数を点数にし（1位なら1/1点、2位なら1/2点）、全記事名で平均する。検索エンジンの結果順位や推薦システムのランキング評価で使われる標準的な指標で、「1位を当てたか」だけを見るPrecision@k・Recall@k・Hit Rate@kと違い、正解が2位に沈んだケースと10位に沈んだケースを区別できる。正解に複数段階の良さがある課題ではNDCGのような重み付けが使われるが、このタスクの正解は候補群の中に1つしかなく段階を持たないため、素のMRRで足りると判断した。

本体の評価軸は1回のMRRではなく、コーパスをシードごとに再生成したときのMRRの分布（平均・分散）である。「一回当てられるか」ではなく「分布が変わっても当て続けられるか」を測る。

比較する4手法は「基礎スコアラー2種（数式 / GBDT）× LLM再判定層の有無」。タスク定義・コーパス生成規模・実装形態の全文は[docs/method.md](docs/method.md)を参照。

## Reproduce

配布はしない。clone して uv で動かす。同じ手順・同じシード・同じダンプ版（config.tomlに固定）で同じ数字が出ることは設計しているが、それ以外の環境・用途は保証しない。

```console
$ uv sync
$ uv run wiki-guessur fetch              # jawiki cirrussearch ダンプ取得（約8.2GB・冪等）
$ uv run wiki-guessur generate --seed 0  # コーパス生成（シード決定的）
$ uv run wiki-guessur eval --method formula --seed 0        # 1構成のMRR計測
$ uv run wiki-guessur eval --method gbdt --seed 0 --llm     # LLM再判定層つき（要 GEMINI_API_KEY）
$ uv run wiki-guessur compare --seeds 0..4   # 生成+全手法評価+集計を一括
$ uv run wiki-guessur diagnose --seeds 0..4  # 診断統計（言及率・候補数分布・ランダム基準）
$ uv run wiki-guessur sweep --seeds 0..4     # 難易度ノブ（候補数上限）の掃引
$ uv run wiki-guessur report                 # 手法×シードの MRR 行列と掃引表
```

`fetch` は約8.2GBのダンプ取得を伴う。結果だけを読みたい場合や、既存コーパスに自分の手法を足して評価したいだけの場合はダンプは不要で、[Releases](https://github.com/yktsnet/wiki-guessur/releases/tag/corpora-20260712) に添付した生成済みコーパス（seed 0〜4）を展開すれば `eval` 以降だけで足りる。

```console
$ curl -LO https://github.com/yktsnet/wiki-guessur/releases/download/corpora-20260712/corpora-seed-0.tar.gz
$ tar xzf corpora-seed-0.tar.gz -C corpora/
```

LightGBM（gbdt 手法）は libomp を要求する。macOS で homebrew を使っていない環境では、`DYLD_LIBRARY_PATH` に libomp の lib ディレクトリを渡す（Nix なら `nixpkgs#llvmPackages.openmp`）。

コードのライセンスはMIT（[LICENSE](LICENSE)）。Releasesのコーパスに含まれるWikipedia本文はCC BY-SAに基づく。出典: Wikipedia（[jawiki cirrussearch dump](https://dumps.wikimedia.org/other/cirrus_search_index/), 20260712時点）。再利用時は同ライセンスの継承と帰属表示が必要。

## Design Decisions

- **素材は cirrussearch ダンプの直接パース**。本文とリンクグラフを同時に持ち、wikitextパーサ不要な唯一の候補だった。ダンプ版は `config.toml` に日付で固定し、頑健さ評価の変動要因をシードだけにする。
- **完全一致ペナルティは反証を受けて棄却**。「ダミーは記事名を含みやすい」という当初の想定と実測は逆で、正解本文の65%が自分の記事名を含む（ダミーは35%）。数式手法は素のTF-IDF類似度単体に確定した。
- **学習手法はLightGBMのlambdarank**。タスクは順位付けなので二値分類でなくランキング学習を使う。
- **LLMは4つ目の手法ではなく再判定層**。基礎スコアラーの上位2候補が僅差のときだけ差し替える。効果は土台の性能に依存する構造そのものを比較対象にする。
- **コーパスはReleasesに添付、9GBのダンプは各自取得**。利用者の大半は結果を読むか既存コーパスで評価したいだけで、それに必要なのはコーパスまでで足りる。

判断の過程（反証した仮説・検討して落とした代替案を含む全文）は[docs/design-decisions.md](docs/design-decisions.md)を参照。

## Scope

**Focus**: Wikipediaダンプ由来で自己完結する、記事名と欠損本文の対応付けタスク。数式・GBDT・LLM再判定層の性格差を、精度だけでなく複数シードでの頑健さ（MRRの分布）で比較する。

**Out-of-Scope**: 埋め込み/BERT系手法の追加。難易度ノブの全パラメータ化（候補数上限のみ実装、除去文量ノブは再生成コストのため保留）。並列化。パッケージング・レジストリ公開。外部の問題設定・データの持ち込み（素材と生成過程はすべてWikipediaダンプ由来）。
