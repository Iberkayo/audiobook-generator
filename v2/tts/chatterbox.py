from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from ..models import SpeechSegment, TTSResult
from .base import TTSAdapter


class ChatterboxMultilingualAdapter(TTSAdapter):
    """Optional local/open-source Turkish TTS adapter.

    Requires the Chatterbox package and its PyTorch/torchaudio dependencies.
    The model is loaded lazily so the base application remains lightweight.
    """

    name = "chatterbox-multilingual"

    def __init__(
        self,
        device: str = "auto",
        language_id: str = "tr",
        t3_model: str = "v3",
        audio_prompt_path: str | None = None,
    ):
        self.device = self._resolve_device(device)
        self.language_id = language_id
        self.t3_model = t3_model
        self.audio_prompt_path = audio_prompt_path
        self._model = None

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

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        except ImportError as exc:
            raise RuntimeError(
                "Chatterbox is not installed. Install the optional local TTS dependencies first."
            ) from exc

        self._model = ChatterboxMultilingualTTS.from_pretrained(
            device=self.device,
            t3_model=self.t3_model,
        )
        return self._model

    def _generate_sync(self, text: str, output_path: Path) -> None:
        try:
            import torchaudio as ta
        except ImportError as exc:
            raise RuntimeError("torchaudio is required for Chatterbox output.") from exc

        model = self._load_model()
        kwargs = {"language_id": self.language_id}
        if self.audio_prompt_path:
            kwargs["audio_prompt_path"] = self.audio_prompt_path

        wav = model.generate(text, **kwargs)
        ta.save(str(output_path), wav, model.sr)

    async def synthesize(
        self,
        segment: SpeechSegment,
        output_dir: Path,
        continuity_handle: Optional[str] = None,
    ) -> TTSResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"segment_{segment.id:05d}.wav"

        # Chatterbox inference is synchronous/heavy. Offload it so callers keep
        # the same async adapter contract as hosted/streaming providers.
        await asyncio.to_thread(self._generate_sync, segment.text, audio_path)

        return TTSResult(
            segment_id=segment.id,
            audio_path=str(audio_path),
            provider=self.name,
            continuity_handle=None,
        )
