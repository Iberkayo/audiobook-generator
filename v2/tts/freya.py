from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

from ..models import SpeechSegment, TTSResult
from .base import TTSAdapter


class FreyaTTSAdapter(TTSAdapter):
    """Turkish-first local TTS adapter for FreyaTTS-small.

    FreyaTTS is currently installed from its GitHub repository rather than
    from PyPI. By default this adapter looks for a checkout at
    third_party/FreyaTTS inside the audiobook-generator repository.
    """

    name = "freya"

    def __init__(
        self,
        device: str = "auto",
        model_id: str = "freyavoice/freya-tts",
        steps: int = 32,
        seed: int = 9,
        source_dir: str | Path | None = None,
    ):
        self.device = self._resolve_device(device)
        self.model_id = model_id
        self.steps = steps
        self.seed = seed
        self.source_dir = Path(source_dir) if source_dir else self._default_source_dir()
        self._model = None

    @staticmethod
    def _default_source_dir() -> Path:
        return Path(__file__).resolve().parents[2] / "third_party" / "FreyaTTS"

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def _import_freya(self):
        try:
            from freyatts import FreyaTTS
            return FreyaTTS
        except ImportError:
            pass

        if self.source_dir.exists():
            source = str(self.source_dir.resolve())
            if source not in sys.path:
                sys.path.insert(0, source)
            try:
                from freyatts import FreyaTTS
                return FreyaTTS
            except ImportError as exc:
                raise RuntimeError(
                    "FreyaTTS source exists but its Python dependencies are missing. "
                    "Run scripts\\setup_freya.ps1 from the repository root."
                ) from exc

        raise RuntimeError(
            "FreyaTTS is not installed. Run scripts\\setup_freya.ps1 from the "
            "repository root, then retry the benchmark."
        )

    def _load_model(self):
        if self._model is not None:
            return self._model

        FreyaTTS = self._import_freya()
        print(f"[Freya] Loading {self.model_id} on {self.device} ...")
        self._model = FreyaTTS.from_pretrained(self.model_id, device=self.device)
        return self._model

    def _generate_sync(self, text: str, output_path: Path) -> None:
        model = self._load_model()
        wav = model.synthesize(text, steps=self.steps, seed=self.seed)
        model.save_wav(wav, str(output_path))

    async def synthesize(
        self,
        segment: SpeechSegment,
        output_dir: Path,
        continuity_handle: Optional[str] = None,
    ) -> TTSResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"segment_{segment.id:05d}.wav"
        await asyncio.to_thread(self._generate_sync, segment.text, audio_path)

        return TTSResult(
            segment_id=segment.id,
            audio_path=str(audio_path),
            provider=self.name,
            continuity_handle=None,
        )
