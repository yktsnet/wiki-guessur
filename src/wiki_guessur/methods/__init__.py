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
    if name == "random":
        from .trivial import Random
        return Random()
    if name == "mention-min":
        from .trivial import MentionMin
        return MentionMin()
    if name == "mention-max":
        from .trivial import MentionMax
        return MentionMax()
    raise ValueError(f"unknown method: {name}")
