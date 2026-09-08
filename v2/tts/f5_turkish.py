from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from ..models import SpeechSegment, TTSResult
from .base import TTSAdapter


class F5TurkishAdapter(TTSAdapter):
    """F5-TTS adapter using a Turkish fine-tuned checkpoint.

    Default model: multilingual-tts/F5-TTS-OpenBible-Turkish.
    This model is zero-shot and requires a clean 5-10 second Turkish
    reference clip plus its exact transcript.
    """

    name = "f5-turkish"

    def __init__(
        self,
        device: str = "auto",
        model_repo: str = "multilingual-tts/F5-TTS-OpenBible-Turkish",
        reference_audio: str | None = None,
        reference_text: str | None = None,
        nfe_steps: int = 32,
        speed: float = 1.0,
    ):
        self.device = self._resolve_device(device)
        self.model_repo = model_repo
        self.reference_audio = reference_audio
        self.reference_text = reference_text
        self.nfe_steps = nfe_steps
        self.speed = speed

        self._model = None
        self._vocoder = None
        self._infer_process = None
        self._preprocess_ref_audio_text = None

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
            return

        try:
            from huggingface_hub import hf_hub_download
            from hydra.utils import get_class
            from omegaconf import OmegaConf
            from f5_tts.infer.utils_infer import (
                infer_process,
                load_model,
                load_vocoder,
                preprocess_ref_audio_text,
            )
        except ImportError as exc:
            raise RuntimeError(
                "F5-TTS dependencies are not installed. Run scripts/setup_f5.ps1 first."
            ) from exc

        ckpt = hf_hub_download(self.model_repo, "model_last.pt")
        vocab = hf_hub_download(self.model_repo, "vocab.txt")
        config = hf_hub_download(self.model_repo, "F5-TTS_OpenBible_Turkish.yaml")

        model_cfg = OmegaConf.load(config)
        model_cls = get_class(f"f5_tts.model.{model_cfg.model.backbone}")

        self._vocoder = load_vocoder(
            vocoder_name="vocos",
            is_local=False,
            device=self.device,
        )
        self._model = load_model(
            model_cls,
            model_cfg.model.arch,
            ckpt,
            mel_spec_type="vocos",
            vocab_file=vocab,
            use_ema=True,
            device=self.device,
        )
        self._infer_process = infer_process
        self._preprocess_ref_audio_text = preprocess_ref_audio_text

    def _generate_sync(self, text: str, output_path: Path) -> None:
        if not self.reference_audio:
            raise ValueError(
                "F5 Turkish requires --reference-audio with a clean 5-10 second Turkish WAV."
            )
        if not self.reference_text:
            raise ValueError(
                "F5 Turkish requires --reference-text containing the exact transcript of the reference audio."
            )

        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("soundfile is required for F5-TTS output.") from exc

        self._load_model()

        ref_audio, ref_text = self._preprocess_ref_audio_text(
            self.reference_audio,
            self.reference_text,
        )

        wav, sr, _ = self._infer_process(
            ref_audio,
            ref_text,
            text,
            self._model,
            self._vocoder,
            mel_spec_type="vocos",
            nfe_step=self.nfe_steps,
            speed=self.speed,
            device=self.device,
        )
        sf.write(str(output_path), wav, sr)

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
