"""基礎スコアラーのレジストリ。各手法は fit / score を持つ。

- fit(train_queries, corpus, tfidf): 学習手法だけが使う。数式手法は無視する。
- score(title, candidate_ids, corpus, tfidf) -> {doc_id: score}: 高いほど正解らしい。
"""


def get(name: str):
    if name == "formula":
        from .formula import Formula
        return Formula()
    if name == "gbdt":
        from .gbdt import Gbdt
        return Gbdt()
    raise ValueError(f"unknown method: {name}")
