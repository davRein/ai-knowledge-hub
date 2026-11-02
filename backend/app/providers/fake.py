import hashlib
import math
import re

from app.providers.base import EMBEDDING_DIMENSIONS, Evidence, GroundedAnswer

STOPWORDS = set(
    "a an the is are was were be to of and or in on for with what how when where which "
    "does do did can you your my it this that from about tell me please "
    "der die das ein eine einer ist sind war wie was wo wann und oder im in zu mit "
    "von für den dem des ich du bitte mir mein meine document documents dokument dokumente".split()
)


def tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[^\W_]+", text.casefold())
        if len(word) > 1 and word not in STOPWORDS
    }


class FakeProvider:
    """Deterministic lexical test fixture, not a language model or semantic search."""

    name = "fake"
    profile = "fake:lexical-sha256-v1:1536"

    def embed(self, texts: list[str]) -> list[list[float]]:
        result: list[list[float]] = []
        for text in texts:
            vector = [0.0] * EMBEDDING_DIMENSIONS
            for token in tokens(text) or {"__empty__"}:
                digest = hashlib.sha256(token.encode()).digest()
                index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
                vector[index] += 1.0 if digest[4] % 2 else -1.0
            length = math.sqrt(sum(value * value for value in vector))
            if length == 0:
                vector[0] = 1.0
                length = 1.0
            result.append([value / length for value in vector])
        return result

    def answer(self, question: str, evidence: list[Evidence]) -> GroundedAnswer:
        question_tokens = tokens(question)
        candidates: list[tuple[int, str, str]] = []
        for source in evidence:
            for sentence in re.split(r"(?<=[.!?])\s+", source.text):
                overlap = len(question_tokens & tokens(sentence))
                if overlap:
                    candidates.append((overlap, sentence, source.source_id))
        candidates.sort(key=lambda item: -item[0])
        selected = candidates[:2]
        return GroundedAnswer(
            supported=bool(selected),
            answer="Fake provider (deterministic excerpts): "
            + " ".join(item[1] for item in selected),
            source_ids=list(dict.fromkeys(item[2] for item in selected)),
        )
