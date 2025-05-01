# analyzer.py

import re
from collections import defaultdict
import torch
from .utils import get_device
from .config import TRUNCATE_LONG_FILES, MAX_FILE_LENGTH

from transformers import AutoTokenizer, AutoModelForCausalLM

def clean_readme_text(text):
    """
    Preprocess the README to remove badges, images, tables, and code blocks before feeding it to the LLM.
    """
    # Remove images and badges
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # Remove tables
    text = re.sub(r"\|.*?\|", "", text)

    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    return text

class CodeAnalyzer:
    def __init__(self, skills_to_verify):
        self.skills_to_verify = skills_to_verify
        self.device = get_device()

        print("🔄 Loading Deepseek-Coder model...")
        self.tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-instruct")
        self.model = AutoModelForCausalLM.from_pretrained(
            "deepseek-ai/deepseek-coder-1.3b-instruct",
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )

    def _summarize(self, prompt, max_output_tokens=256):
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512, padding=True).to(self.device)

        # 🛠 Attention mask is properly used
        input_length = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_output_tokens,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=False  # Deterministic output
            )

        # 🛠 Cut off the input part, keep only the generated continuation
        generated_tokens = outputs[0][input_length:]
        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

    def extract_skills_from_readme(self, readme_text):
        """
        Smarter extraction using cleaned README and improved prompt.
        """
        if not readme_text.strip():
            return []

        cleaned_text = clean_readme_text(readme_text)

        prompt = (
            "Given the following project description, list the technologies, frameworks, programming languages, "
            "and major libraries used or referenced. Only return the list, separated by commas. "
            "Ignore emojis, tables, diagrams, badges, and code snippets.\n\n"
            + cleaned_text
        )

        extracted_text = self._summarize(prompt)

        possible_skills = re.split(r'[,\n]', extracted_text)
        cleaned_skills = [s.strip() for s in possible_skills if len(s.strip()) > 0]

        return cleaned_skills

    def analyze_code_file(self, file_content, skill):
        """
        Analyze a code file for general coding skill.
        """
        if not file_content.strip():
            return None, None

        if TRUNCATE_LONG_FILES and len(file_content) > MAX_FILE_LENGTH:
            file_content = file_content[:MAX_FILE_LENGTH]

        prompt = (
            "You are an expert software engineer.\n"
            "Your task is to evaluate the quality of a given code snippet.\n\n"
            "Example Response:\n"
            "Script Score: 9\n"
            "The code is simple, clear, and functional with good use of a function.\n\n"
            "Now evaluate the following code snippet:\n\n"
            + file_content
        )

        result = self._summarize(prompt)

        print(f"🧠 Raw model output: {result}")  # Debug print

        lines = result.strip().splitlines()
        if len(lines) >= 2:
            try:
                score = int(lines[0].strip())
                explanation = lines[1].strip()
                return score, explanation
            except ValueError:
                return None, result.strip()
        else:
            return None, result.strip()

    def get_relevant_extensions_for_skill(self, skill):
        """
        Dynamically fetches file extensions or filenames related to the skill using the LLM.
        """
        return self.extension_detector.get_extensions_for_skill(skill)

    def is_file_relevant_to_skill(self, file_name, file_content, skill_extensions):
        """
        Decides if a given file is relevant to a skill based on its extensions or content.
        """
        file_name_lower = file_name.lower()
        content_lower = file_content.lower()

        for ext_or_keyword in skill_extensions:
            if not ext_or_keyword:
                continue
            ext_or_keyword = ext_or_keyword.strip().lower()

            # Match by filename
            if ext_or_keyword in file_name_lower:
                return True

            # Match by file extension
            if ext_or_keyword.startswith(".") and file_name_lower.endswith(ext_or_keyword):
                return True

            # Match by code content keyword
            if ext_or_keyword in content_lower:
                return True

        return False


class SkillExtensionDetector:
    """
    Given a skill (like 'Django' or 'Docker'), dynamically find what file types/extensions could match.
    """
    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.cache = {}

    def _summarize(self, prompt, max_output_tokens=64):
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(inputs["input_ids"], max_length=max_output_tokens)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def get_extensions_for_skill(self, skill):
        """
        Dynamically queries the LLM to get the relevant extensions for a skill.
        """
        if skill in self.cache:
            return self.cache[skill]

        prompt = f"For the skill '{skill}', list typical file extensions or filenames related to it. Return as a comma-separated list."
        result = self._summarize(prompt)

        extensions = [ext.strip() for ext in result.split(",") if ext.strip()]
        self.cache[skill] = extensions

        return extensions
