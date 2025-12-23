import runpod
import base64
import os
from dotenv import load_dotenv

load_dotenv()

runpod.api_key = os.getenv("RUNPOD_API_KEY")
endpoint = runpod.Endpoint(os.getenv("RUNPOD_ENDPOINT_ID"))

result = endpoint.run_sync({
    "input": {
        "text": "Hola, esto es una prueba de síntesis de voz.",
        "language_id": "es"
    }
}, timeout=120)

print(result)

if "audio_base64" in result:
    audio = base64.b64decode(result["audio_base64"])
    with open("test_output.wav", "wb") as f:
        f.write(audio)
    print("Saved to test_output.wav")