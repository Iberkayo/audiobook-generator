from pathlib import Path
from typing import Optional

import edge_tts

from ..models import SpeechSegment, TTSResult
from .base import TTSAdapter


class EdgeTTSAdapter(TTSAdapter):
    """Free baseline adapter.

    Edge TTS does not expose a persistent cross-request continuity primitive,
    so the semantic segment itself is the main continuity improvement here.
    """

    name = "edge"

    def __init__(self, voice: str = "tr-TR-AhmetNeural"):
        self.voice = voice

    async def synthesize(
        self,
        segment: SpeechSegment,
        output_dir: Path,
        continuity_handle: Optional[str] = None,
    ) -> TTSResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"segment_{segment.id:05d}.mp3"
        communicator = edge_tts.Communicate(segment.text, self.voice)
        await communicator.save(str(audio_path))
        return TTSResult(
            segment_id=segment.id,
            audio_path=str(audio_path),
            provider=self.name,
            continuity_handle=None,
        )
