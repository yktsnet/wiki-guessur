"""LLM再判定層。基礎スコアラーの上位2候補が僅差のケースだけを LLM に聞く。

無料枠（15 RPM / 500 RPD）の制約から、僅差ケース全件ではなく 1/10 を
シード決定的にサンプリングして判定し、全対象へ適用した場合の MRR の伸びを
推定値として報告する（実測と推定を区別する。PLAN「比較の構造」参照）。

API キーは環境変数 GEMINI_API_KEY から読む。リポには書かない。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """以下はWikipedia記事の記事名と、冒頭の定義文を除去した2つの本文A・Bです。
記事名「{title}」の本文はどちらですか。AかBの1文字だけで答えてください。

## A
{a}

## B
{b}"""


def _call(model: str, api_key: str, prompt: str, retries: int = 3) -> str:
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 1000},
    }).encode()
    req = urllib.request.Request(
        API_URL.format(model=model), data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            candidates = data.get("candidates") or []
            if not candidates or "content" not in candidates[0]:
                print(f"  skip: no usable candidate ({data})", file=sys.stderr)
                return None
            return candidates[0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print("  429: waiting 30s", file=sys.stderr)
                time.sleep(30)
                continue
            raise
    raise RuntimeError("unreachable")


def rerank_sample(base_name: str, test, scores_fn, corpus, cfg_llm, seed: int):
    """僅差ケースを抽出し、サンプリングして LLM 判定。実測デルタと全体推定を返す。

    scores_fn(query) -> {cid: score}
    """
    from ..generate import _query_rng

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY が未設定")
    model = cfg_llm["model"]
    th = cfg_llm["gap_threshold"]
    chars = cfg_llm["text_chars"]

    close = []
    for q in test:
        s = scores_fn(q)
        ranked = sorted(q["candidates"], key=lambda c: s[c], reverse=True)
        vals = sorted(s.values(), reverse=True)
        span = max(vals[0] - vals[-1], 1e-9)
        if (vals[0] - vals[1]) / span < th:
            close.append((q, ranked))

    sampled = [c for c in close
               if _query_rng(seed, f"llm:{base_name}:{c[0]['title']}").random()
               < cfg_llm["sample_rate"]]
    print(f"close {len(close)}/{len(test)}, sampled {len(sampled)}", file=sys.stderr)

    delta = 0.0
    picked_answer = 0
    skipped = 0
    for i, (q, ranked) in enumerate(sampled):
        top1, top2 = ranked[0], ranked[1]
        # A/B の割当もシード決定的に反転し、位置バイアスを均す
        flip = _query_rng(seed, f"ab:{q['title']}").random() < 0.5
        a, b = (top2, top1) if flip else (top1, top2)
        ans = _call(model, api_key, PROMPT.format(
            title=q["title"], a=corpus[a][:chars], b=corpus[b][:chars]))
        if ans is None:
            skipped += 1
            print(f"  [{i+1}/{len(sampled)}] {q['title']}: skipped (no response)",
                  file=sys.stderr)
            time.sleep(60 / cfg_llm["rpm"])
            continue
        choice = a if ans.upper().startswith("A") else b
        new_ranked = ranked if choice == top1 else \
            [top2, top1] + ranked[2:]
        old_rank = ranked.index(q["answer"]) + 1
        new_rank = new_ranked.index(q["answer"]) + 1
        delta += 1.0 / new_rank - 1.0 / old_rank
        picked_answer += (choice == q["answer"])
        print(f"  [{i+1}/{len(sampled)}] {q['title']}: "
              f"{'kept' if choice == top1 else 'swapped'} "
              f"rank {old_rank}->{new_rank}", file=sys.stderr)
        time.sleep(60 / cfg_llm["rpm"])

    n = len(sampled) - skipped
    return {
        "n_close": len(close),
        "n_sampled": len(sampled),
        "n_skipped": skipped,
        "llm_picked_answer_rate": round(picked_answer / n, 4) if n else None,
        "mrr_delta_sampled": round(delta / n, 4) if n else None,
        # サンプル平均デルタを僅差ケース全体に外挿し、test 全体の MRR 換算にする
        "mrr_gain_est": round((delta / n) * len(close) / len(test), 4) if n else None,
    }
