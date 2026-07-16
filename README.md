# wiki-guessur

1行目（定義文）を消されたWikipedia記事は、自分がどの記事名の本文かを言い当てられるか。

LLMやRAGを「使えば解ける」で終わらせると、何が効いて解けたのかが残らない。このリポは、記事名と欠損本文の対応付けという1つのタスクを2種の基礎スコアラー（人が係数を決める数式手法、機械が係数を決める学習手法）と、その上に載せるLLM再判定層（僅差ケースだけLLMに聞く）の組み合わせ4通りで解き、手法の性格差を実測で見えるようにするための実験場である。コーパスを毎回ランダムに再生成し、一発の精度ではなく、分布が変わっても当て続けられるか（MRRの平均・分散）で比較する。

計画は [PLAN.md](PLAN.md)、設計判断の記録は [JUDGE.md](JUDGE.md) を参照。

## 使い方

配布はしない。clone して uv で動かす。

```console
$ uv sync
$ uv run wiki-guessur fetch              # jawiki cirrussearch ダンプ取得（約8.9GB・冪等）
$ uv run wiki-guessur generate --seed 0  # コーパス生成（シード決定的）
$ uv run wiki-guessur eval --method formula --seed 0
$ uv run wiki-guessur compare --seeds 0..2   # 生成+全手法評価+集計を一括
$ uv run wiki-guessur report             # 手法×シードの MRR 行列
```

LightGBM（gbdt 手法）は libomp を要求する。macOS で homebrew を使っていない環境では、
`DYLD_LIBRARY_PATH` に libomp の lib ディレクトリを渡す（Nix なら `nixpkgs#llvmPackages.openmp`）。
