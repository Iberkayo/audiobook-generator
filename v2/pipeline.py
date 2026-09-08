from pathlib import Path
from typing import List

from .audio import AudioAssembler
from .models import SpeechSegment, TTSResult
from .segmenter import SemanticSegmenter
from .tts.base import TTSAdapter


class AudiobookPipeline:
    def __init__(self, tts: TTSAdapter, segmenter: SemanticSegmenter | None = None):
        self.tts = tts
        self.segmenter = segmenter or SemanticSegmenter()
        self.assembler = AudioAssembler()

    async def generate_text(
        self,
        text: str,
        output_dir: str | Path,
        chapter_index: int = 1,
    ) -> tuple[List[SpeechSegment], List[TTSResult], str]:
        output_dir = Path(output_dir)
        segment_dir = output_dir / "segments"
        segment_dir.mkdir(parents=True, exist_ok=True)

        segments = self.segmenter.build_segments(text, chapter_index=chapter_index)
        results: List[TTSResult] = []
        continuity_handle = None

        for segment in segments:
            result = await self.tts.synthesize(
                segment,
                segment_dir,
                continuity_handle=continuity_handle,
            )
            results.append(result)
            continuity_handle = result.continuity_handle

        audio = self.assembler.assemble(r.audio_path for r in results)
        wav_path = self.assembler.export_wav(audio, output_dir / "audiobook_v2.wav")
        return segments, results, wav_path
