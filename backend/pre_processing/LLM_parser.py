"""
LLM_parser.py
─────────────
Natural language processing module for resume and job posting analysis in the 
Portfol.io MAS pipeline using a local LLM via `llama_cpp`.

Class
─────
• Preprocessor
    - Initializes a local LLM model.
    - Constructs prompts for either applicant resumes or job postings.
    - Extracts structured JSON from raw text using the LLM and robust parsing logic.

Methods
───────
• __init__(mode: str, model_path: str)
      Initializes the preprocessor in either "applicants" or "jobPostings" mode.
      Loads the foundation model with mmap/gpu settings.

• _generate_prompt(text: str) -> str
      Returns a task-specific prompt to instruct the LLM to extract structured data 
      from raw input (resume or job posting).

• process_text(text: str) -> dict | None
      Sends the generated prompt to the LLM, extracts the first JSON object from 
      its response, and safely parses it with `json` or `json5` fallback.

Usage
─────
Used by the `pre_processing_main.py` pipeline to transform raw PDF text into 
structured JSON that downstream agents (e.g. RecruiterAgent) can reason with.

Example
───────
from backend.pre_processing.LLM_parser import Preprocessor

parser = Preprocessor(mode="applicants")
parsed = parser.process_text("Jane Doe is a software engineer...")
"""

import re
import os
import json
import json5
from llama_cpp import Llama

from backend.config import MODEL_DIR, FOUNDATION_MODEL

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

class Preprocessor:
    def __init__(self, mode="applicants", model_path=os.path.join(MODEL_DIR, FOUNDATION_MODEL)):
        """
        Initializes the Preprocessor for either applicants or job postings.
        Loads the local LLM model.
        """
        assert mode in ["applicants", "jobPostings"]
        self.mode = mode

        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=8,
            n_gpu_layers=35,
            use_mlock=True,
            use_mmap=True,
            verbose=False
        )

    def _generate_prompt(self, text):
        """
        Generates the prompt depending on whether processing resumes or job postings.
        Also instructs the model to output ONLY valid JSON without extra decorations.
        """
        if self.mode == "applicants":
            return f"""
    Extract the following details from the resume below:

    1. Full candidate name (if available)
    2. GitHub link (if available)
    3. Personal portfolio or website link (if available)
    4. Skills (comma-separated list)
    5. Work experience summary
    6. Key projects mentioned
    7. Candidate summary (1-2 sentences)

    --- Resume ---
    {text}

    ⚠️ IMPORTANT: Only return a **valid JSON object**. 
    ⚠️ Do NOT include any extra text, explanations, "---", "[Result]", or anything outside of the JSON.
    ⚠️ Your response must start directly with '{{' and end with '}}'.

    Here is the required JSON format:

    {{
    "name": "...",
    "github": "...",
    "portfolio": "...",
    "skills": "...",
    "experience": "...",
    "projects": "...",
    "summary": "..."
    }}
    """
        else:
            return f"""
    Extract the following details from the job posting:

    1. Title of the role
    2. Job description
    3. Key requirements (comma-separated)

    --- Job Posting ---
    {text}

    ⚠️ IMPORTANT: Only return a **valid JSON object**. 
    ⚠️ Do NOT include any extra text, explanations, "---", "[Result]", or anything outside of the JSON.
    ⚠️ Your response must start directly with '{{' and end with '}}'.

    Here is the required JSON format:

    {{
    "title": "...",
    "description": "...",
    "requirements": "..."
    }}
    """

    def process_text(self, text):
        """
        Sends resume or job posting to LLM, extracts the first valid JSON object, and parses it robustly.
        Falls back to json5 if standard parsing fails. Recovers from unterminated strings, broken summary fields,
        stray braces inside strings, and missing closing characters.
        """

        import re

        RED = "\033[91m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"

        prompt = self._generate_prompt(text)
        response = self.llm.create_completion(prompt=prompt, max_tokens=400, temperature=0.5)
        raw_output = response['choices'][0]['text']

        try:
            json_start = raw_output.find('{')
            if json_start == -1:
                raise ValueError("No opening '{' found in LLM output.")

            brace_count = 0
            json_end = None
            for i, char in enumerate(raw_output[json_start:], start=json_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            # Extract the JSON chunk
            if json_end is None:
                cleaned_output = raw_output[json_start:].strip()
                if not cleaned_output.endswith("}"):
                    print(f"{YELLOW}(preprocessor.py)[W] Missing closing brace — appending one.{RESET}")
                    cleaned_output += "}"
            else:
                cleaned_output = raw_output[json_start:json_end].strip()

            # Special fix: if summary is cut off and there's no closing quote or brace
            if '"summary":' in cleaned_output and not cleaned_output.strip().endswith('"}'):
                print(f"{YELLOW}(preprocessor.py)[W] Fixing incomplete 'summary' field manually...{RESET}")
                match = re.search(r'"summary"\s*:\s*"(.*?)$', cleaned_output, re.DOTALL)
                if match:
                    partial_summary = match.group(1)
                    cutoff = max(partial_summary.rfind("."), partial_summary.rfind("!"), partial_summary.rfind("?"))
                    if cutoff != -1:
                        partial_summary = partial_summary[:cutoff+1]
                    else:
                        partial_summary = partial_summary[:1000]  # safe fallback
                    cleaned_output = re.sub(
                        r'"summary"\s*:\s*".*?$',
                        f'"summary": "{partial_summary}"',
                        cleaned_output,
                        flags=re.DOTALL
                    )
                    if not cleaned_output.strip().endswith("}"):
                        cleaned_output += "}"

            # Fix: remove a stray '}' inside final quoted field (e.g., "...projects.}")
            if cleaned_output.strip().endswith('}"}') or re.search(r'"summary"\s*:\s*".*}"}\s*$', cleaned_output):
                print(f"{YELLOW}(preprocessor.py)[W] Stray closing brace inside quoted field — trimming it.{RESET}")
                cleaned_output = re.sub(r'"}\s*$', '"', cleaned_output)

            # Final patches for quote and brace
            if cleaned_output.count('"') % 2 != 0:
                print(f"{YELLOW}(preprocessor.py)[W] Detected unclosed string — appending final quote{RESET}")
                cleaned_output += '"'
            if not cleaned_output.strip().endswith("}"):
                cleaned_output += "}"

            print(f"\n(preprocessor.py)[CHECK] Final Cleaned JSON:\n{cleaned_output}\n")

            # Parse with json first, then fallback to json5
            try:
                parsed = json.loads(cleaned_output)
                print(f"{GREEN}(preprocessor.py)[✓] Parsed with standard json.{RESET}")
            except json.JSONDecodeError as e1:
                print(f"{YELLOW}(preprocessor.py)[W] Standard JSON failed: {e1}{RESET}")
                print(f"{YELLOW}(preprocessor.py)[W] Trying json5 fallback...{RESET}")
                try:
                    parsed = json5.loads(cleaned_output)
                    print(f"{GREEN}(preprocessor.py)[✓] Parsed with json5 fallback.{RESET}")
                except Exception as e2:
                    raise ValueError(f"Both parsers failed: {e2}")

            return parsed

        except Exception as e:
            print("\n" + "="*50)
            print(f"{RED}ERROR{RESET}")
            print("="*50)
            print(f"{RED}(preprocessor.py)[E] Could not parse JSON: {e}{RESET}")
            print("\n(preprocessor.py)[E-PRINTING] Raw LLM Output:\n")
            print(raw_output.strip())
            print("\n" + "="*50 + "\n")
            return None
