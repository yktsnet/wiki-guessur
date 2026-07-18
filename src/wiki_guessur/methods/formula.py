"""数式手法。人が係数を決め、以後固定する（再生成に対して再調整しない縛り）。

当初の設計では完全一致ペナルティと長さ補正を置いていたが、初回生成（seed 0 の
train 分割）でのグリッドフィットの結果、両補正とも MRR を下げることが分かり、
係数 0 で固定した。診断統計の示すとおりこのコーパスでは正解本文ほど自分の
記事名を呼び、その情報は記事名の文字 n-gram 類似度が既に内包しているため、
補正項は二重計上の雑音にしかならない。結果として本手法は
「記事名の文字 n-gram TF-IDF コサイン類似度」単体である。
"""
from .. import features

W_SIM = 1.0
W_MENTION = 0.0      # フィットの結果 0（ペナルティもボーナスも害）
W_LEN = 0.0          # 同上
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
