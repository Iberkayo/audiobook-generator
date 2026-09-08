import json

from v2.ledger import SegmentLedger
from v2.models import SpeechSegment, TTSResult


def test_ledger_preserves_source_and_spoken_text(tmp_path):
    ledger = SegmentLedger()
    segment = SpeechSegment(
        id=1,
        text="yüzde yirmi beş indirim",
        source_text="%25 indirim",
        chapter_index=1,
        continuity_group_id="chapter-1",
        normalization_events=[
            {
                "source": "%25",
                "spoken": "yüzde yirmi beş",
                "kind": "percentage",
                "start": 0,
                "end": 3,
            }
        ],
    )
    ledger.register_segment(segment)
    ledger.mark_synthesized(
        TTSResult(
            segment_id=1,
            audio_path="segments/segment_00001.mp3",
            provider="edge",
        )
    )

    output = tmp_path / "ledger.json"
    ledger.export_json(output)
    payload = json.loads(output.read_text(encoding="utf-8"))

    record = payload["segments"][0]
    assert record["source_text"] == "%25 indirim"
    assert record["spoken_text"] == "yüzde yirmi beş indirim"
    assert record["provider"] == "edge"
    assert record["synthesis_status"] == "ok"
    assert record["normalization_events"][0]["kind"] == "percentage"
