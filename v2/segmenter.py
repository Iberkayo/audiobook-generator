import re
from typing import List

from .models import SpeechSegment


class SemanticSegmenter:
    """Groups literary text into context-preserving speech blocks.

    The goal is to reduce TTS context resets while still respecting
    paragraph/dialogue boundaries and provider request-size limits.
    """

    SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÇĞİÖŞÜ0-9\"'—–-])")
    DIALOGUE_RE = re.compile(r"^\s*(?:[\"“”]|[—–-]\s)")

    def __init__(self, target_chars: int = 500, max_chars: int = 900):
        if target_chars <= 0 or max_chars <= 0 or target_chars > max_chars:
            raise ValueError("target_chars must be > 0 and <= max_chars")
        self.target_chars = target_chars
        self.max_chars = max_chars

    def split_sentences(self, paragraph: str) -> List[str]:
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if not paragraph:
            return []
        return [s.strip() for s in self.SENTENCE_RE.split(paragraph) if s.strip()]

    def _is_dialogue(self, text: str) -> bool:
        return bool(self.DIALOGUE_RE.match(text))

    def _flush(self, blocks: List[str], current: List[str]) -> None:
        if current:
            blocks.append(" ".join(current).strip())
            current.clear()

    def make_blocks(self, text: str) -> List[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        blocks: List[str] = []
        current: List[str] = []
        current_len = 0
        current_dialogue = None

        for paragraph in paragraphs:
            sentences = self.split_sentences(paragraph)
            if not sentences:
                continue

            paragraph_is_dialogue = self._is_dialogue(sentences[0])

            if current and current_dialogue is not None and paragraph_is_dialogue != current_dialogue:
                self._flush(blocks, current)
                current_len = 0

            for sentence in sentences:
                sentence_len = len(sentence) + (1 if current else 0)
                sentence_is_dialogue = self._is_dialogue(sentence)

                boundary_change = (
                    current
                    and current_dialogue is not None
                    and sentence_is_dialogue != current_dialogue
                )
                would_overflow = current and current_len + sentence_len > self.max_chars
                target_reached = current and current_len >= self.target_chars

                if boundary_change or would_overflow or target_reached:
                    self._flush(blocks, current)
                    current_len = 0

                if not current:
                    current_dialogue = sentence_is_dialogue

                current.append(sentence)
                current_len += len(sentence) + (1 if len(current) > 1 else 0)

            # paragraph boundaries are meaningful, but do not always force a TTS reset.
            if current and current_len >= self.target_chars:
                self._flush(blocks, current)
                current_len = 0

        self._flush(blocks, current)
        return blocks

    def build_segments(self, text: str, chapter_index: int = 1) -> List[SpeechSegment]:
        blocks = self.make_blocks(text)
        segments: List[SpeechSegment] = []
        continuity_group_id = f"chapter-{chapter_index}"

        for i, block in enumerate(blocks, start=1):
            previous_text = blocks[i - 2] if i > 1 else ""
            next_text = blocks[i] if i < len(blocks) else ""
            segments.append(
                SpeechSegment(
                    id=i,
                    text=block,
                    chapter_index=chapter_index,
                    speaker="dialogue" if self._is_dialogue(block) else "narrator",
                    context_before=previous_text[-600:],
                    context_after=next_text[:600],
                    continuity_group_id=continuity_group_id,
                )
            )
        return segments
