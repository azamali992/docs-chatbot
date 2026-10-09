"""Question -> retrieved sections -> grounded answer with citations.

Guards against the two things that make support bots dangerous:
1. Answering from nothing. If retrieval finds no relevant section, the LLM is never called.
2. Citing sources it didn't use. Citations are checked against the sections actually sent;
   an answer that claims to be found but cites nothing valid is replaced with a handoff.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLM
from .retrieve import Index

FALLBACK = ("I couldn't find that in our help docs. You can reach the team at {contact} "
            "and they'll sort it out.")


@dataclass
class Source:
    id: str
    title: str
    snippet: str


@dataclass
class Reply:
    answer: str
    found: bool
    sources: list[Source] = field(default_factory=list)


class Bot:
    def __init__(self, index: Index, llm: LLM, company: str, contact: str, k: int = 5, min_score: float = 1.0):
        self.index, self.llm, self.company, self.contact = index, llm, company, contact
        self.k, self.min_score = k, min_score

    def _fallback(self) -> Reply:
        return Reply(FALLBACK.format(contact=self.contact), found=False)

    def ask(self, question: str, history: list[dict] | None = None) -> Reply:
        question = question.strip()[:1000]
        if not question:
            return Reply("Ask me anything about our bikes, shipping, returns or warranty.", found=False)

        # The question on its own must match something in the docs. Otherwise an off-topic
        # question would ride on the previous question's keywords and get an answer.
        own = self.index.search(question, self.k)
        if not own or own[0][1] < self.min_score:
            return self._fallback()

        # For follow-ups ("and to Canada?"), re-rank with the previous question added.
        history = (history or [])[-6:]
        last_user = next((h["content"] for h in reversed(history) if h.get("role") == "user"), "")
        hits = self.index.search(f"{question} {last_user}", self.k) if last_user else own

        numbered = "\n\n".join(f"[{i}] {c.title}\n{c.text}" for i, (c, _) in enumerate(hits, start=1))
        convo = "\n".join(f"{h['role']}: {h['content'][:500]}" for h in history)
        draft = self.llm.draft(self.company, question, numbered, convo)

        valid = [n for n in dict.fromkeys(draft.citations) if 1 <= n <= len(hits)]
        if not draft.found or not draft.answer.strip() or not valid:
            return self._fallback()
        sources = [Source(hits[n - 1][0].id, hits[n - 1][0].title, hits[n - 1][0].text[:280]) for n in valid]
        return Reply(draft.answer.strip(), found=True, sources=sources)
