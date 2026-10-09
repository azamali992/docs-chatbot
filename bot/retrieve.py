"""Keyword retrieval with BM25.

BM25 needs no API calls, no vector database and no embedding bill, and for a
help centre of a few hundred to a few thousand pages it finds the right section
reliably. Headings are counted twice because a question usually names the topic
("return", "warranty", "battery").
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from .ingest import Chunk

STOPWORDS = set("""a an the and or but if of to in on at for from by with about as is are was were be been
being do does did have has had can could would should will shall may might must i you we they he she it my
your our their me us them this that these those what which who whom how when where why there here not no
yes so than then too very just also into over under up down out off again any all each few more most other
some such only own same s t don doesn didn isn aren wasn weren hasn haven hadn won wouldn couldn shouldn""".split())

SYNONYMS = {
    "refund": ["return", "refund"], "send": ["return", "ship"], "back": ["return"],
    "deliver": ["delivery", "shipping"], "delivered": ["delivery", "shipping"], "arrive": ["delivery"],
    "ship": ["shipping"], "shipped": ["shipping"], "cost": ["price", "cost"], "much": ["price", "cost"],
    "fast": ["speed", "time"], "far": ["range", "miles"], "charge": ["charging", "charge"],
    "guarantee": ["warranty"], "broken": ["warranty", "defects"], "pay": ["payment", "financing"],
    "installments": ["financing", "affirm"], "tall": ["height", "sizing"], "height": ["height", "sizing"],
    "plane": ["flights"], "fly": ["flights"], "flight": ["flights"], "build": ["assembly"],
    "assemble": ["assembly"], "together": ["assembly"], "setup": ["assembly"], "set": ["assembly"],
    "long": ["time", "days"], "take": ["time", "days"], "days": ["delivery", "time"], "heavy": ["weight"], "weigh": ["weight"], "repair": ["service", "repairs"],
}


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str, expand: bool = False) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    if expand:
        words = words + [s for w in words for s in SYNONYMS.get(w, [])]
    return [_stem(w) for w in words]


class Index:
    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("no documents to index")
        self.chunks = chunks
        corpus = [tokenize(c.title) * 2 + tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(corpus)
        self.by_id = {c.id: c for c in chunks}

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        tokens = tokenize(query, expand=True)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)
        return [(c, float(s)) for c, s in ranked[:k] if s > 0]
