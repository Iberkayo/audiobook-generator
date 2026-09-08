from pathlib import Path
from typing import Iterable

from pydub import AudioSegment


class AudioAssembler:
    """Assembles generated segments without synthetic Gaussian room tone.

    Audio is kept as PCM in memory and encoded only at final export.
    """

    def __init__(self, inter_segment_ms: int = 180):
        self.inter_segment_ms = inter_segment_ms

    def assemble(self, audio_paths: Iterable[str]) -> AudioSegment:
        combined = AudioSegment.empty()
        first = True
        for path in audio_paths:
            audio = AudioSegment.from_file(path)
            if not first and self.inter_segment_ms > 0:
                combined += AudioSegment.silent(duration=self.inter_segment_ms)
            combined += audio
            first = False
        return combined

    def export_wav(self, audio: AudioSegment, output_path: str | Path) -> str:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(output_path, format="wav")
        return str(output_path)
