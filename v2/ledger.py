from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .models import SpeechSegment, TTSResult


@dataclass
class LedgerRecord:
    segment_id: int
    chapter_index: int
    continuity_group_id: str
    source_text: str
    spoken_text: str
    source_sha256: str
    spoken_sha256: str
    normalization_events: List[dict] = field(default_factory=list)
    provider: Optional[str] = None
    audio_path: Optional[str] = None
    request_id: Optional[str] = None
    continuity_handle: Optional[str] = None
    synthesis_status: str = "pending"
    qa_status: str = "not_run"


class SegmentLedger:
    def __init__(self) -> None:
        self.records: Dict[int, LedgerRecord] = {}

    @staticmethod
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def register_segment(self, segment: SpeechSegment) -> None:
        source_text = segment.source_text or segment.text
        self.records[segment.id] = LedgerRecord(
            segment_id=segment.id,
            chapter_index=segment.chapter_index,
            continuity_group_id=segment.continuity_group_id,
            source_text=source_text,
            spoken_text=segment.text,
            source_sha256=self._sha(source_text),
            spoken_sha256=self._sha(segment.text),
            normalization_events=list(segment.normalization_events),
        )

    def mark_synthesized(self, result: TTSResult) -> None:
        record = self.records[result.segment_id]
        record.provider = result.provider
        record.audio_path = result.audio_path
        record.request_id = result.request_id
        record.continuity_handle = result.continuity_handle
        record.synthesis_status = "ok"

    def mark_failed(self, segment_id: int) -> None:
        self.records[segment_id].synthesis_status = "failed"

    def validate(self) -> None:
        if not self.records:
            raise ValueError("Segment ledger is empty")
        ids = sorted(self.records)
        expected = list(range(ids[0], ids[-1] + 1))
        if ids != expected:
            raise ValueError(f"Non-contiguous segment IDs: {ids}")
        missing_text = [r.segment_id for r in self.records.values() if not r.spoken_text.strip()]
        if missing_text:
            raise ValueError(f"Empty spoken text for segments: {missing_text}")

    def export_json(self, path: str | Path) -> str:
        self.validate()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "segments": [asdict(self.records[k]) for k in sorted(self.records)],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
