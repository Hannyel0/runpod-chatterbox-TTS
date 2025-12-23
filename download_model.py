"""Pre-download model during Docker build to avoid cold start delays."""
import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

print("Downloading Chatterbox Multilingual model...")
# This caches to ~/.cache/huggingface
model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
print("Model downloaded successfully!")