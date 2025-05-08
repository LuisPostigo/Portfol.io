from llama_cpp import Llama
import os

# Use your config if available
from backend.config import MODEL_DIR, FOUNDATION_MODEL

# Full model path
MODEL_PATH = os.path.join(MODEL_DIR, FOUNDATION_MODEL)

# Load the model
print("[+] Loading Mistral model...")
try:
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_gpu_layers=0,  # Change to -1 if you know your GPU can handle it
        use_mmap=True,
        use_mlock=False,
        verbose=True
    )
    print("[CHECK] Model loaded successfully.")
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    exit(1)

# Prompt (no code blocks – Mistral doesn't need them and sometimes they confuse it)
instruction = """
You are a helpful AI assistant.

Evaluate the following Python script for the listed skills: object-oriented programming, python, error handling.

Return:
1. A raw JSON object with skill names as keys and values from 0–10 (no markdown).
2. One technically detailed sentence per skill explaining the justification for the rating (suitable for a senior developer review).
Each explanation must match the skill order in the JSON.

Python script:
class Logger:
    def __init__(self, filepath):
        self.filepath = filepath

    def log(self, message):
        with open(self.filepath, 'a') as f:
            f.write(message + '\\n')

logger = Logger("logfile.txt")
logger.log("Started process.")

Response:
"""

# Run inference
print("[*] Generating response...")
try:
    result = llm.create_completion(
        prompt=instruction,
        max_tokens=256,
        temperature=0.4,
    )
    print("[OUTPUT] Model output:\n", result["choices"][0]["text"].strip())
except Exception as e:
    print(f"[ERROR] Inference failed: {e}")
