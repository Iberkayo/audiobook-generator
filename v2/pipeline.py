from dataclasses import asdict
from pathlib import Path
from typing import List

from .audio import AudioAssembler
from .ledger import SegmentLedger
from .models import SpeechSegment, TTSResult
from .normalizer import TurkishTextNormalizer
from .segmenter import SemanticSegmenter
from .tts.base import TTSAdapter


class AudiobookPipeline:
    def __init__(
        self,
        tts: TTSAdapter,
        segmenter: SemanticSegmenter | None = None,
        normalizer: TurkishTextNormalizer | None = None,
    ):
        self.tts = tts
        self.segmenter = segmenter or SemanticSegmenter()
        self.normalizer = normalizer or TurkishTextNormalizer()
        self.assembler = AudioAssembler()

    def _normalize_segments(self, segments: List[SpeechSegment]) -> None:
        for segment in segments:
            segment.source_text = segment.text
            normalized = self.normalizer.normalize(segment.text)
            segment.text = normalized.spoken_text
            segment.normalization_events = [asdict(event) for event in normalized.events]

            if segment.context_before:
                segment.context_before = self.normalizer.normalize(segment.context_before).spoken_text
            if segment.context_after:
                segment.context_after = self.normalizer.normalize(segment.context_after).spoken_text

    async def generate_text(
        self,
        text: str,
        output_dir: str | Path,
        chapter_index: int = 1,
    ) -> tuple[List[SpeechSegment], List[TTSResult], str, str]:
        output_dir = Path(output_dir)
        segment_dir = output_dir / "segments"
        segment_dir.mkdir(parents=True, exist_ok=True)

        segments = self.segmenter.build_segments(text, chapter_index=chapter_index)
        self._normalize_segments(segments)

        ledger = SegmentLedger()
        for segment in segments:
            ledger.register_segment(segment)

        results: List[TTSResult] = []
        continuity_handle = None

        for segment in segments:
            try:
                result = await self.tts.synthesize(
                    segment,
                    segment_dir,
                    continuity_handle=continuity_handle,
                )
            except Exception:
                ledger.mark_failed(segment.id)
                ledger.export_json(output_dir / "segment_ledger.json")
                raise

            results.append(result)
            ledger.mark_synthesized(result)
            continuity_handle = result.continuity_handle

        audio = self.assembler.assemble(r.audio_path for r in results)
        wav_path = self.assembler.export_wav(audio, output_dir / "audiobook_v2.wav")
        ledger_path = ledger.export_json(output_dir / "segment_ledger.json")
        return segments, results, wav_path, ledger_path
