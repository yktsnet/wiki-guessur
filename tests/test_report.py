"""保証: report の手法×シード集計（平均・stdev）が個別の評価結果と整合する。"""
import json

from wiki_guessur import config, report


def test_report_aggregates_results(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    rows = [
        {"seed": 0, "method": "formula", "mrr": 0.8},
        {"seed": 1, "method": "formula", "mrr": 0.9},
        {"seed": 0, "method": "formula+llm", "mrr": 0.8, "mrr_est": 0.85},
        {"seed": 0, "method": "formula", "k_cap": 2, "mrr": 0.95},
    ]
    (tmp_path / "results.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    report.run()
    body = (tmp_path / "report.md").read_text(encoding="utf-8")

    # mean = (0.8+0.9)/2, stdev = stdev([0.8, 0.9])
    assert "| formula | 0.8000 | 0.9000 | 0.8500 | 0.0707 |" in body
    # LLM層つきは mrr でなく mrr_est を採用。1シードのみ → stdev 0
    assert "| formula+llm | 0.8500 | - | 0.8500 | 0.0000 |" in body
    # k_cap つきは掃引表へ分離集計される
    assert "k=2" in body and "| formula | 0.9500 |" in body
