"""LLM再判定層（未実装）。

基礎スコアラーの上位2候補のスコア差が閾値未満のケースだけを対象に、
サンプリングして LLM に判定させ、MRR の伸びを推定値として報告する層。
Phase 3 で実装する。API キーとモデルは config で指定する予定。
"""


class LlmRerank:
    def __init__(self, base):
        raise NotImplementedError("LLM再判定層は未実装（Phase 3）")
