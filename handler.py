import runpod
import torch
import torchaudio as ta
import base64
import io
import tempfile
import os

# Load model at module level (before serverless starts)
# This runs once when container starts, not per-request
print("Loading Chatterbox Multilingual model...")
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = ChatterboxMultilingualTTS.from_pretrained(device=DEVICE)
print(f"Model loaded on {DEVICE}")


def decode_audio_to_tempfile(audio_base64: str) -> str:
    """Decode base64 audio and save to temp file for Chatterbox."""
    audio_bytes = base64.b64decode(audio_base64)
    
    # Create temp file with proper extension
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_file.write(audio_bytes)
    temp_file.close()
    
    return temp_file.name


def encode_audio_to_base64(waveform: torch.Tensor, sample_rate: int) -> str:
    """Encode generated audio to base64."""
    buffer = io.BytesIO()
    ta.save(buffer, waveform, sample_rate, format="wav")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def handler(job):
    """
    RunPod serverless handler for Chatterbox Multilingual TTS.
    
    Input schema:
    {
        "text": str,                      # Text to synthesize
        "language_id": str,               # Language code: es, en, fr, de, etc.
        "reference_audio": str | None,    # Base64 encoded reference audio for voice cloning
        "exaggeration": float | None,     # Emotion intensity (0.0 - 1.0, default 0.5)
        "cfg_weight": float | None        # Pace/style adherence (default 0.5)
    }
    
    Output schema:
    {
        "audio_base64": str,              # Base64 encoded WAV
        "sample_rate": int,
        "duration_seconds": float
    }
    """
    job_input = job["input"]
    
    # Extract inputs
    text = job_input.get("text")
    language_id = job_input.get("language_id", "es")
    reference_audio_b64 = job_input.get("reference_audio")
    exaggeration = job_input.get("exaggeration", 0.5)
    cfg_weight = job_input.get("cfg_weight", 0.5)
    
    # Validate
    if not text:
        return {"error": "Missing 'text' field"}
    
    if language_id not in ["ar", "da", "de", "el", "en", "es", "fi", "fr", 
                            "he", "hi", "it", "ja", "ko", "ms", "nl", "no", 
                            "pl", "pt", "ru", "sv", "sw", "tr", "zh"]:
        return {"error": f"Unsupported language_id: {language_id}"}
    
    temp_audio_path = None
    
    try:
        # Handle reference audio for voice cloning
        audio_prompt_path = None
        if reference_audio_b64:
            temp_audio_path = decode_audio_to_tempfile(reference_audio_b64)
            audio_prompt_path = temp_audio_path
        
        # Generate speech
        with torch.inference_mode():
            wav = MODEL.generate(
                text,
                language_id=language_id,
                audio_prompt_path=audio_prompt_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight
            )
        
        # Calculate duration
        duration = wav.shape[1] / MODEL.sr
        
        # Encode output
        audio_b64 = encode_audio_to_base64(wav, MODEL.sr)
        
        return {
            "audio_base64": audio_b64,
            "sample_rate": MODEL.sr,
            "duration_seconds": round(duration, 2)
        }
    
    except Exception as e:
        return {"error": str(e)}
    
    finally:
        # Cleanup temp file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


# Start serverless worker
runpod.serverless.start({"handler": handler})