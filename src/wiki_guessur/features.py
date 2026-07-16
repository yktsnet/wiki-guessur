"""記事名×候補本文の特徴量。数式手法と学習手法で共用する（標準ライブラリのみ）。

TF-IDF は「クエリ記事名に現れる文字 n-gram」だけを次元に取る。
類似度計算に効くのはその次元だけなので、コーパス全体の n-gram 辞書は持たない。
"""
import math
from collections import Counter

NGRAM_SIZES = (2, 3)


def char_ngrams(s: str) -> Counter:
    c: Counter = Counter()
    for n in NGRAM_SIZES:
        for i in range(len(s) - n + 1):
            c[s[i:i + n]] += 1
    return c


class TitleTfidf:
    """クエリ記事名群の n-gram に限定した DF を、コーパス全文書から数える。"""

    def __init__(self, titles: list[str], corpus: dict[str, str]):
        self.vocab: set[str] = set()
        for t in titles:
            self.vocab |= set(char_ngrams(t))
        df: Counter = Counter()
        for text in corpus.values():
            seen = {g for g in char_ngrams(text) if g in self.vocab}
            df.update(seen)
        n_docs = max(len(corpus), 1)
        self.idf = {g: math.log((n_docs + 1) / (df[g] + 1)) + 1 for g in self.vocab}

    def similarity(self, title: str, text: str) -> float:
        """title の n-gram 次元に限定したコサイン類似度。"""
        tv = char_ngrams(title)
        dv = char_ngrams(text)
        num = t_norm = d_norm = 0.0
        for g, tf in tv.items():
            idf = self.idf.get(g, 1.0)
            tw = tf * idf
            dw = dv.get(g, 0) * idf
            num += tw * dw
            t_norm += tw * tw
        for g in set(dv) & self.vocab:
            w = dv[g] * self.idf.get(g, 1.0)
            d_norm += w * w
        if num == 0 or t_norm == 0 or d_norm == 0:
            return 0.0
        return num / (math.sqrt(t_norm) * math.sqrt(d_norm))


def extract(title: str, text: str, tfidf: TitleTfidf) -> dict[str, float]:
    length = max(len(text), 1)
    mentions = text.count(title)
    first = text.find(title)
    return {
        "sim": tfidf.similarity(title, text),
        "mentions": float(mentions),
        "mention_density": mentions / length * 1000,
        "first_pos": first / length if first >= 0 else 1.0,
        "doc_len": math.log(length),
        "title_len": float(len(title)),
    }
