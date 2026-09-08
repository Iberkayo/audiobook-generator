$ErrorActionPreference = "Stop"

Write-Host "Installing F5-TTS into the active Python environment..."
python -m pip install --upgrade pip
python -m pip install f5-tts huggingface_hub hydra-core omegaconf soundfile

Write-Host "Checking F5-TTS imports..."
python -c "from f5_tts.infer.utils_infer import infer_process, load_model, load_vocoder, preprocess_ref_audio_text; print('F5-TTS import OK')"

Write-Host "F5-TTS setup complete."
