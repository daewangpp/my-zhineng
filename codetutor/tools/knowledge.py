# -*- coding: utf-8 -*-
"""报错知识库检索(RAG)。

纯 Python 实现 TF-IDF 检索,零外部依赖,离线可跑 ——
满足教学场景的"可解释、可演示"要求:每次诊断引用了哪条知识,完全透明。
知识库格式:JSONL,每行一条 {"id","title","error_key","error_types",
"keywords","root_cause","teaching_point","example_bad","example_good"}
"""
import json
import math
import os
import re

import config


def tokenize(text):
    """中英文混合分词:英文按单词,中文按单字+二元组。"""
    text = (text or "").lower()
    tokens = re.findall(r"[a-z_][a-z0-9_]*", text)
    zh_chars = re.findall(r"[一-鿿]", text)
    tokens.extend(zh_chars)
    tokens.extend(zh_chars[i] + zh_chars[i + 1] for i in range(len(zh_chars) - 1))
    return tokens


class KnowledgeBase:
    def __init__(self, path=None):
        self.path = path or config.KB_PATH
        self.entries = []
        self.df = {}
        self.n_docs = 0
        self.vectors = []
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.entries.append(json.loads(line))
        self.n_docs = len(self.entries)
        doc_tokens = []
        for e in self.entries:
            text = " ".join(str(e.get(k, "")) for k in
                            ("title", "error_key", "keywords", "root_cause",
                             "teaching_point", "example_bad"))
            toks = tokenize(" ".join(e.get("error_types", [])) + " " + text)
            doc_tokens.append(toks)
            for t in set(toks):
                self.df[t] = self.df.get(t, 0) + 1
        self.vectors = [self._tfidf(toks) for toks in doc_tokens]

    def _tfidf(self, tokens):
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        vec = {}
        n = max(len(tokens), 1)
        for t, c in tf.items():
            idf = math.log((self.n_docs + 1) / (self.df.get(t, 0) + 1)) + 1
            vec[t] = (c / n) * idf
        return vec

    @staticmethod
    def _cosine(v1, v2):
        common = set(v1) & set(v2)
        dot = sum(v1[t] * v2[t] for t in common)
        n1 = math.sqrt(sum(x * x for x in v1.values()))
        n2 = math.sqrt(sum(x * x for x in v2.values()))
        return dot / (n1 * n2) if n1 and n2 else 0.0

    def search(self, query, top_k=2):
        """检索最相关的知识条目,返回 [(score, entry), ...] 的前 top_k。"""
        if not self.entries:
            return []
        qv = self._tfidf(tokenize(query))
        scored = [(self._cosine(qv, dv), e) for dv, e in zip(self.vectors, self.entries)]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(s, e) for s, e in scored[:top_k] if s > 0.01]


_kb = None


def get_kb():
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def search(query, top_k=2):
    return [e for _, e in get_kb().search(query, top_k=top_k)]
