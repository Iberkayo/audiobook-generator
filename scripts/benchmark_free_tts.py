from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from v2.pipeline import AudiobookPipeline
from v2.tts.chatterbox import ChatterboxMultilingualAdapter
from v2.tts.edge import EdgeTTSAdapter


DEFAULT_SAMPLE = """Kapının arkasından hafif bir ses geldi. Ahmet olduğu yerde durdu. Koridorda kimse görünmüyordu.

— Orada kim var? diye seslendi.

Cevap gelmedi. Yalnızca saatin düzenli tıkırtısı duyuluyordu. Birkaç saniye sonra kapı yeniden gıcırdadı ve Ahmet, nefesini tutarak kapıya doğru bir adım attı.

Dr. Selim'in ona 12.03.2024 tarihinde söyledikleri birden aklına geldi. O gece riskin %25 olduğunu söylemişti; ama Ahmet o zaman buna inanmamıştı."""


def build_adapter(args):
    if args.provider == "edge":
        return EdgeTTSAdapter(voice=args.voice)
    if args.provider == "chatterbox":
        return ChatterboxMultilingualAdapter(
            device=args.device,
            language_id="tr",
            t3_model=args.chatterbox_model,
            audio_prompt_path=args.reference_audio,
        )
    raise ValueError(f"Unknown provider: {args.provider}")


async def main_async(args):
    text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else DEFAULT_SAMPLE
    output_dir = Path(args.output_dir) / args.provider
    adapter = build_adapter(args)
    pipeline = AudiobookPipeline(tts=adapter)

    segments, results, wav_path, ledger_path = await pipeline.generate_text(
        text=text,
        output_dir=output_dir,
        chapter_index=1,
    )

    print(f"Provider: {args.provider}")
    print(f"Segments: {len(segments)}")
    print(f"Generated: {len(results)}")
    print(f"WAV: {wav_path}")
    print(f"Ledger: {ledger_path}")
    print("\nSegments:")
    for segment in segments:
        print(f"[{segment.id}] {segment.text}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate comparable free-TTS audiobook samples.")
    parser.add_argument("--provider", choices=["edge", "chatterbox"], required=True)
    parser.add_argument("--text-file", help="Optional UTF-8 Turkish sample text.")
    parser.add_argument("--output-dir", default="benchmark_outputs")
    parser.add_argument("--voice", default="tr-TR-AhmetNeural", help="Edge TTS voice.")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    parser.add_argument("--chatterbox-model", default="v3")
    parser.add_argument("--reference-audio", help="Optional reference WAV for Chatterbox voice cloning.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
