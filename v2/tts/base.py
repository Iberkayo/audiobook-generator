from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..models import SpeechSegment, TTSResult


class TTSAdapter(ABC):
    name = "base"

    @abstractmethod
    async def synthesize(
        self,
        segment: SpeechSegment,
        output_dir: Path,
        continuity_handle: Optional[str] = None,
    ) -> TTSResult:
        """Synthesize one planned speech segment.

        continuity_handle is provider-specific state returned from the
        previous segment. Adapters that cannot use it may safely ignore it.
        """
        raise NotImplementedError
