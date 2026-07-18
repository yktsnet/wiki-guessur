"""保証: LLM再判定層は candidates を含まない応答（セーフティブロック等）でも
クラッシュせず、判定をスキップして基礎スコアラーの順位を維持する。"""
import io
import json

from wiki_guessur.methods import llm


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_call_returns_none_without_candidates(monkeypatch):
    blocked = json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode()
    monkeypatch.setattr(llm.urllib.request, "urlopen",
                        lambda req, timeout: _FakeResp(blocked))
    assert llm._call("m", "key", "prompt") is None


def test_rerank_sample_skips_when_call_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(llm, "_call", lambda *a, **k: None)

    queries = [{"title": f"q{i}", "answer": "a", "candidates": ["a", "b", "c"]}
               for i in range(3)]
    corpus = {"a": "本文a", "b": "本文b", "c": "本文c"}
    scores_fn = lambda q: {"a": 1.0, "b": 0.99, "c": 0.0}  # top2僅差 → 全件close
    cfg_llm = {"model": "m", "gap_threshold": 0.5, "text_chars": 100,
               "sample_rate": 1.0, "rpm": 60000}

    result = llm.rerank_sample("formula", queries, scores_fn, corpus, cfg_llm, seed=0)

    assert result["n_skipped"] == result["n_sampled"] == 3
    assert result["llm_picked_answer_rate"] is None
    assert result["mrr_delta_sampled"] is None
    assert result["mrr_gain_est"] is None
