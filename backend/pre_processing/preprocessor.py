import re
import os
import json
from llama_cpp import Llama

from backend.config import MODEL_DIR

class Preprocessor:
    def __init__(self, mode="applicants", model_path=os.path.join(MODEL_DIR, "mistral-7b-instruct-v0.1-q4_k_m.gguf")):
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
        Processes a single text and safely extracts the first valid JSON object from the LLM output.
        Only prints the final cleaned JSON and ignores any extra duplicated output.
        """
        prompt = self._generate_prompt(text)
        response = self.llm.create_completion(prompt=prompt, max_tokens=400, temperature=0.5)

        raw_output = response['choices'][0]['text']

        try:
            json_start = raw_output.find('{')
            if json_start == -1:
                raise ValueError("No JSON block found in the output.")

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

            if json_end is None:
                raise ValueError("Unbalanced JSON braces found.")

            cleaned_output = raw_output[json_start:json_end]
            print(f"\n📨 Final Cleaned JSON:\n{cleaned_output}\n")
            parsed = json.loads(cleaned_output)
            return parsed

        except Exception as e:
            print(f"❌ Could not parse JSON: {e}")
            return None
