"""学習手法。再生成のたびに train 分割で LightGBM (lambdarank) を再学習する。"""
import numpy as np

from .. import features

FEATURE_ORDER = ["sim", "mentions", "mention_density", "first_pos", "doc_len", "title_len"]


def _row(title, text, tfidf):
    f = features.extract(title, text, tfidf)
    return [f[k] for k in FEATURE_ORDER]


class Gbdt:
    def __init__(self):
        self.model = None

    def fit(self, train_queries, corpus, tfidf):
        import lightgbm as lgb
        rows, labels, groups = [], [], []
        for q in train_queries:
            for cid in q["candidates"]:
                rows.append(_row(q["title"], corpus[cid], tfidf))
                labels.append(1 if cid == q["answer"] else 0)
            groups.append(len(q["candidates"]))
        train_set = lgb.Dataset(np.array(rows), label=np.array(labels), group=groups)
        self.model = lgb.train(
            {"objective": "lambdarank", "metric": "ndcg", "verbosity": -1,
             "num_leaves": 31, "learning_rate": 0.1, "min_data_in_leaf": 20},
            train_set, num_boost_round=100)

    def score(self, title, candidate_ids, corpus, tfidf):
        x = np.array([_row(title, corpus[cid], tfidf) for cid in candidate_ids])
        preds = self.model.predict(x)
        return dict(zip(candidate_ids, preds))
