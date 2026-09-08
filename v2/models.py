from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NarrationInstruction:
    tone: str = "neutral"
    intensity: str = "medium"
    pace: str = "medium"
    emphasis: List[str] = field(default_factory=list)
    pause_after_ms: int = 0


@dataclass
class SpeechSegment:
    id: int
    text: str
    chapter_index: int
    speaker: str = "narrator"
    context_before: str = ""
    context_after: str = ""
    continuity_group_id: str = ""
    instruction: NarrationInstruction = field(default_factory=NarrationInstruction)


@dataclass
class TTSResult:
    segment_id: int
    audio_path: str
    provider: str
    request_id: Optional[str] = None
    continuity_handle: Optional[str] = None
