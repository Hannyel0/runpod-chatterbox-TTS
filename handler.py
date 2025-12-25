import runpod
import torch
import torchaudio as ta
import base64
import io
import tempfile
import os
import re

# Load model at module level (before serverless starts)
# This runs once when container starts, not per-request
print("Loading Chatterbox Multilingual model...")
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = ChatterboxMultilingualTTS.from_pretrained(device=DEVICE)
print(f"Model loaded on {DEVICE}")
DEFAULT_VOICE_PATH = "/app/voices/voice-sport-spanish-2.mp3"

# Max characters per chunk (Chatterbox works best with shorter segments)
MAX_CHUNK_LENGTH = 250


def split_text_into_chunks(text: str, max_length: int = MAX_CHUNK_LENGTH) -> list[str]:
    """
    Split text into chunks by sentences, keeping under max_length.
    Tries to split on sentence boundaries first, then falls back to other punctuation.
    """
    # If text is short enough, return as-is
    if len(text) <= max_length:
        return [text.strip()]
    
    # Split by sentence-ending punctuation (. ! ? and Spanish ¿ ¡)
    sentence_pattern = r'(?<=[.!?¿¡])\s+'
    sentences = re.split(sentence_pattern, text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If adding this sentence exceeds max length
        if len(current_chunk) + len(sentence) + 1 > max_length:
            # Save current chunk if it has content
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # If single sentence is too long, split by commas or force split
            if len(sentence) > max_length:
                # Try splitting by commas
                sub_parts = re.split(r',\s*', sentence)
                sub_chunk = ""
                for part in sub_parts:
                    if len(sub_chunk) + len(part) + 2 > max_length:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip())
                        # Force split if still too long
                        while len(part) > max_length:
                            chunks.append(part[:max_length].strip())
                            part = part[max_length:]
                        sub_chunk = part
                    else:
                        sub_chunk = f"{sub_chunk}, {part}" if sub_chunk else part
                current_chunk = sub_chunk
            else:
                current_chunk = sentence
        else:
            current_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


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
        "text": str,                      # Text to synthesize (supports long text)
        "language_id": str,               # Language code: es, en, fr, de, etc.
        "reference_audio": str | None,    # Base64 encoded reference audio for voice cloning
        "exaggeration": float | None,     # Emotion intensity (0.0 - 1.0, default 0.5)
        "cfg_weight": float | None        # Pace/style adherence (default 0.5)
    }
    
    Output schema:
    {
        "audio_base64": str,              # Base64 encoded WAV
        "sample_rate": int,
        "duration_seconds": float,
        "chunks_processed": int           # Number of text chunks processed
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
            # User provided custom reference audio
            temp_audio_path = decode_audio_to_tempfile(reference_audio_b64)
            audio_prompt_path = temp_audio_path
        elif os.path.exists(DEFAULT_VOICE_PATH):
            # Use baked-in default voice
            audio_prompt_path = DEFAULT_VOICE_PATH
            print(f"Using default voice: {DEFAULT_VOICE_PATH}")
        
        # Split text into chunks
        chunks = split_text_into_chunks(text)
        print(f"Processing {len(chunks)} chunk(s)")
        
        # Generate audio for each chunk
        audio_segments = []
        
        with torch.inference_mode():
            for i, chunk in enumerate(chunks):
                print(f"Generating chunk {i+1}/{len(chunks)}: {chunk[:50]}...")
                
                wav = MODEL.generate(
                    chunk,
                    language_id=language_id,
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
                audio_segments.append(wav)
        
        # Concatenate all audio segments
        if len(audio_segments) == 1:
            final_audio = audio_segments[0]
        else:
            # Add small silence between chunks for natural pauses
            silence_duration = int(0.3 * MODEL.sr)  # 300ms silence
            silence = torch.zeros(1, silence_duration)
            
            concatenated = []
            for i, segment in enumerate(audio_segments):
                concatenated.append(segment)
                if i < len(audio_segments) - 1:  # Don't add silence after last segment
                    concatenated.append(silence)
            
            final_audio = torch.cat(concatenated, dim=1)
        
        # Calculate duration
        duration = final_audio.shape[1] / MODEL.sr
        
        # Encode output
        audio_b64 = encode_audio_to_base64(final_audio, MODEL.sr)
        
        return {
            "audio_base64": audio_b64,
            "sample_rate": MODEL.sr,
            "duration_seconds": round(duration, 2),
            "chunks_processed": len(chunks)
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
    finally:
        # Cleanup temp file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


# Start serverless worker
runpod.serverless.start({"handler": handler})