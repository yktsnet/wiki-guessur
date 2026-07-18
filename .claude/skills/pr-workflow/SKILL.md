---
name: pr-workflow
description: ブランチ作成 → 実装 → 検証 → PR 作成の一連フロー
---

以下の手順で issue を実行する。$ARGUMENTS に issue ファイルのパスを渡す。

**前提: Claude Code はコードを書いて PR を出すまでが担当。実行・確認・マージは user が行う。**

0. `context/conventions.md` を読む
1. issue ファイルを読む
2. `git status` で未コミットがあれば報告して止まる
3. `git checkout -b claude/{id}-{branch-slug}`（id と branch-slug は issue から取得）
4. 対象ファイルを読んで実装。Issue ファイルの `status:` は変更しない（issue-finish が処理する）。
5. issue の「確認」項目に従い静的チェックを実施する
   - `nix-shell -p uv --run "uv run pytest -q"`
   - gbdt/LLM層に触れた場合は `nix-shell -p uv llvmPackages.openmp --run "DYLD_LIBRARY_PATH=$(nix-build '<nixpkgs>' -A llvmPackages.openmp --no-out-link)/lib uv run wiki-guessur eval --method gbdt --seed 0"` で最小構成の実行確認
   - issue 固有の確認があればそれも実施
6. `git add {変更したファイル}`
   `git diff --name-only --cached` を実行する。
   出力が issue の「対象」フィールドと完全一致することを確認する。
   不一致があれば実装に戻り修正する。一致してから次に進む。
7. `git commit -m "{type}: {タイトル}"`
8. PR ボディを `issues/.pr_body_draft.md` に書き出し、同内容を `issues/done/{id}_{branch-slug}_pr.md` にもコピーする。
   `git add issues/done/{id}_{branch-slug}_pr.md` して `git commit -m "chore: add PR record {id}"` でコミットしてから PR を作成する。
   `issues/.pr_body_draft.md` の内容:
   ```
   ## 変更内容
   {issue の内容フィールドを展開}

   ## 静的確認結果
   {検証コマンドの結果、issue の確認項目に対する結果}

   ## 検証手順
   - MRR数値に影響する変更: `uv run wiki-guessur eval --method {method} --seed 0` の出力が変わっていないか、あるいは意図通り変わっているかを確認する
   - LLM層に触れた変更: `GEMINI_API_KEY` を設定して `--llm` 付きで1回実行し、レート制限・応答パースが壊れていないか確認する
   ```
   `gh pr create --base main --title "{type}: {タイトル}" --body-file issues/.pr_body_draft.md`
9. PR の URL を出力して終了
   ```
   ✅ PR created: {URL}
   Next: 検証手順を実施 → gh pr merge {番号} --merge
   ```
