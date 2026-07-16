"""数式手法。人が係数を決め、以後固定する（再生成に対して再調整しない縛り）。

設計の直観:
- 記事名との文字 n-gram TF-IDF 類似度が高い本文ほど正解らしい。
- ただし記事名の完全一致はダミー（正解記事にリンクして言及する側）にも強く出る。
  定義文を失った正解本文は自分の名前を名乗れないことが多いので、
  「名前をそのまま何度も呼ぶ文書」はむしろ疑う（完全一致ペナルティ）。
- 極端に短い/長い本文は情報量の偏りで類似度が歪むので長さで軽く補正する。
"""
from .. import features

W_SIM = 1.0
W_MENTION = 0.05     # 完全一致ペナルティ（3回で頭打ち）
W_LEN = 0.02         # 長さ補正の基準は log(2000)
LEN_PIVOT = 7.6


class Formula:
    def fit(self, train_queries, corpus, tfidf):
        pass  # 係数は固定。学習しない

    def score(self, title, candidate_ids, corpus, tfidf):
        out = {}
        for cid in candidate_ids:
            f = features.extract(title, corpus[cid], tfidf)
            out[cid] = (W_SIM * f["sim"]
                        - W_MENTION * min(f["mentions"], 3.0)
                        - W_LEN * abs(f["doc_len"] - LEN_PIVOT))
        return out
