# Audiobook Generator V2

## Goal

Validate long-form narration quality with free/local TTS first. Paid providers are added only after semantic segmentation, context planning and QA prove useful.

## Current V2 core

- Provider-independent `TTSAdapter`
- Free Edge TTS baseline adapter
- Semantic speech-block segmentation instead of sentence-by-sentence synthesis
- Previous/next text context stored on every `SpeechSegment`
- `continuity_group_id` for future provider continuity APIs
- Clean PCM/WAV assembly
- No synthetic Gaussian room tone

## Flow

```text
Text
  -> SemanticSegmenter
  -> SpeechSegment[]
  -> TTSAdapter
  -> generated audio segments
  -> PCM assembly
  -> audiobook_v2.wav
```

## Important design rule

The core application must not depend on a specific TTS provider. Future adapters can map the same planning model to ElevenLabs, Gemini, Cartesia, OpenAI or local models.

## Next free-model experiments

1. Keep Edge TTS as the regression baseline.
2. Add one truly local/open Turkish-capable adapter.
3. Build a fixed Turkish audiobook evaluation passage.
4. Compare V1 sentence-by-sentence vs V2 semantic blocks by listening.
5. Only then add Narrative Director / paid providers.

## Planned next modules

- Turkish text normalization
- Segment ledger and coverage validation
- Local/open TTS adapter
- ASR QA
- Dialogue/speaker resolver
- Scene-level Narrative Director
