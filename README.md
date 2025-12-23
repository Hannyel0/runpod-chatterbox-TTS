# 🎙️ RunPod Chatterbox TTS

A serverless text-to-speech endpoint powered by [Chatterbox Multilingual](https://github.com/resemble-ai/chatterbox) on RunPod. Generate natural speech in 23 languages with zero-shot voice cloning.

## ✨ Features

- **23 Languages** — Spanish, English, French, German, Japanese, Chinese, and more
- **Voice Cloning** — Clone any voice with just 5-10 seconds of reference audio
- **Emotion Control** — Adjust expressiveness from monotone to dramatic
- **Serverless** — Pay only for what you use, auto-scales to zero
- **Fast Cold Starts** — Model pre-baked into Docker image + FlashBoot ready

## 🚀 Quick Start

### Deploy to RunPod

1. Pull the image or build your own:

   ```bash
   docker build -t yourusername/chatterbox-tts:latest .
   docker push yourusername/chatterbox-tts:latest
   ```

2. Create a serverless endpoint in [RunPod Console](https://console.runpod.io/serverless):
   - Template → New Template → Enter your Docker image
   - GPU: RTX 4000 Ada / L4 / A4000 (8-16GB VRAM)
   - Enable FlashBoot ✅

### API Usage

```python
import runpod
import base64

runpod.api_key = "your_api_key"
endpoint = runpod.Endpoint("your_endpoint_id")

# Basic TTS
result = endpoint.run_sync({
    "input": {
        "text": "Hola, esto es una prueba.",
        "language_id": "es"
    }
})

# With voice cloning
with open("reference.wav", "rb") as f:
    ref_audio = base64.b64encode(f.read()).decode()

result = endpoint.run_sync({
    "input": {
        "text": "Your text here",
        "language_id": "en",
        "reference_audio": ref_audio,
        "exaggeration": 0.6
    }
})

# Save output
audio = base64.b64decode(result["audio_base64"])
with open("output.wav", "wb") as f:
    f.write(audio)
```

## 📥 Input Schema

| Field             | Type   | Required | Description                              |
| ----------------- | ------ | -------- | ---------------------------------------- |
| `text`            | string | ✅       | Text to synthesize                       |
| `language_id`     | string | ✅       | Language code (see below)                |
| `reference_audio` | string | ❌       | Base64 WAV for voice cloning             |
| `exaggeration`    | float  | ❌       | Emotion intensity (0.0-1.0, default 0.5) |
| `cfg_weight`      | float  | ❌       | Style adherence (0.0-1.0, default 0.5)   |

## 📤 Output Schema

```json
{
  "audio_base64": "UklGRi...",
  "sample_rate": 24000,
  "duration_seconds": 2.45
}
```

## 🌍 Supported Languages

| Code | Language | Code | Language  | Code | Language   |
| ---- | -------- | ---- | --------- | ---- | ---------- |
| `ar` | Arabic   | `he` | Hebrew    | `pl` | Polish     |
| `da` | Danish   | `hi` | Hindi     | `pt` | Portuguese |
| `de` | German   | `it` | Italian   | `ru` | Russian    |
| `el` | Greek    | `ja` | Japanese  | `sv` | Swedish    |
| `en` | English  | `ko` | Korean    | `sw` | Swahili    |
| `es` | Spanish  | `ms` | Malay     | `tr` | Turkish    |
| `fi` | Finnish  | `nl` | Dutch     | `zh` | Chinese    |
| `fr` | French   | `no` | Norwegian |      |            |

## 🎯 Voice Cloning Tips

For best results:

- Use 5-15 seconds of clean audio
- WAV format, 24kHz+ sample rate
- Single speaker, no background noise
- Match the reference style to desired output emotion

## 💰 Cost Estimation

| Traffic         | GPU          | Active Workers | ~Monthly Cost |
| --------------- | ------------ | -------------- | ------------- |
| 100 req/day     | RTX 4000 Ada | 0 (flex)       | $5-15         |
| 1,000 req/day   | L4           | 1              | $50-80        |
| 10,000+ req/day | L4           | 2+             | $200+         |

## 🛠️ Local Development

```bash
# Test locally
python handler.py --test_input '{"input": {"text": "Hello world", "language_id": "en"}}'
```

## 📄 License

MIT — Model weights subject to [Chatterbox license](https://github.com/resemble-ai/chatterbox).

## 🙏 Credits

- [Resemble AI](https://github.com/resemble-ai/chatterbox) — Chatterbox TTS model
- [RunPod](https://runpod.io) — Serverless GPU infrastructure
