"""自明な基準線。

- Random: 一様ランダム順（シード決定的）。数字の下限の錨。
- MentionMin: 記事名の完全一致が最も少ない候補を選ぶ。ねじれ仮説
  「言及する文書ほど正解ではない」の直接テストで、これがランダムに勝つなら
  ねじれは実在し、formula の完全一致ペナルティに根拠があることになる。
"""
import hashlib


class Random:
    def fit(self, train_queries, corpus, tfidf):
        pass

    def score(self, title, candidate_ids, corpus, tfidf):
        return {cid: int.from_bytes(
            hashlib.sha256(f"{title}:{cid}".encode()).digest()[:8], "big")
            for cid in candidate_ids}


class MentionMin:
    def fit(self, train_queries, corpus, tfidf):
        pass

    def score(self, title, candidate_ids, corpus, tfidf):
        return {cid: -corpus[cid].count(title) for cid in candidate_ids}


class MentionMax:
    """MentionMin の逆。診断統計が示した「正解ほど自分の名前を呼ぶ」の直接テスト。"""

    def fit(self, train_queries, corpus, tfidf):
        pass

    def score(self, title, candidate_ids, corpus, tfidf):
        return {cid: corpus[cid].count(title) for cid in candidate_ids}
