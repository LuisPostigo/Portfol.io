import os
import requests
from llama_cpp import Llama
import json
from urllib.parse import urlparse

class SingleScriptAnalyzer:
    def __init__(self, file_url, skills, model, verbose=False):
        self.file_url = file_url
        self.skills = skills
        self.model = model
        self.verbose = verbose
        self.name = os.path.basename(urlparse(file_url).path) 

    def get_default_branch(self, user, repo):
        api_url = f"https://api.github.com/repos/{user}/{repo}"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        return response.json().get("default_branch", "main")

    def fetch_code(self):
        parsed = urlparse(self.file_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 5:
            raise ValueError("Invalid GitHub blob URL format")

        user, repo, blob_keyword, branch_guess, *file_path = path_parts
        filepath_str = "/".join(file_path)

        default_branch = self.get_default_branch(user, repo)
        raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{default_branch}/{filepath_str}"

        response = requests.get(raw_url, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch code from: {raw_url}")
        return response.text

    def generate_prompt(self, code):
      skill_str = ", ".join(self.skills)
      return f"""
You are a Tech Recruiter Lead evaluating code samples.

Your task is to evaluate **only** the following skills: {skill_str}.

---

### INSTRUCTION FORMAT

For each skill, return:
1. A single **JSON object** like:
{{
  "Python": {{"depth": 8, "coverage": true}},
  "Unit Testing": {{"depth": 6, "coverage": true}}
}}

2. Then, one **technical sentence per skill**, in the same order as the JSON.

Use these delimiters:

### JSON EVAL:
<JSON_BLOCK>

### EXPLANATION:
<EXPLANATIONS>

---

### EXAMPLE 1 (Evaluating: Python, Pandas)
### Code:
import pandas as pd

df = pd.read_csv("data.csv")
df["price"] = df["price"].fillna(0)
print(df.describe())

### JSON EVAL:
{{
  "Python": {{"depth": 8, "coverage": true}},
  "Pandas": {{"depth": 9, "coverage": true}}
}}

### EXPLANATION:
The script uses clean Python syntax and standard I/O functions.
Pandas is used efficiently for data loading, filling nulls, and summarizing statistics.

---

### EXAMPLE 2 (Evaluating: SQL, Regex)
### Code:
import re

query = "SELECT * FROM users WHERE email LIKE '%@example.com'"
match = re.search(r"@example\\.com", "test@example.com")

### JSON EVAL:
{{
  "SQL": {{"depth": 5, "coverage": true}},
  "Regex": {{"depth": 6, "coverage": true}}
}}

### EXPLANATION:
SQL is visible in string form, though not dynamically executed.
A regular expression is correctly used for basic domain matching.

---

### EXAMPLE 3 (Evaluating: Object-Oriented Programming, Error Handling)
### Code:
class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        try:
            print(f"Hello, {self.name}!")
        except:
            print("Error greeting.")

Greeter("Luis").greet()

### JSON EVAL:
{{
  "Object-Oriented Programming": {{"depth": 8, "coverage": true}},
  "Error Handling": {{"depth": 5, "coverage": true}}
}}

### EXPLANATION:
OOP is well-demonstrated via class and method encapsulation.
Error handling exists but lacks specificity in the exception clause.

---

### TARGET EVALUATION

Now evaluate the following code **only for**: {skill_str}.

### Code:
{code}

RESPONSE:
"""
    
    def run(self):
        try:
            code = self.fetch_code()
            prompt = self.generate_prompt(code)
            response = self.model(prompt, max_tokens=256)

            print(f"\n(LLM) Model Response for {self.name}:\n{response['choices'][0]['text'].strip()}\n")

            if not response or "choices" not in response or not response["choices"]:
                print(f"(!) Empty or malformed response for file: {self.file_url}")
                return {"error": "Model returned no response"}

            output = response["choices"][0]["text"].strip()
            return {"result": output}

        except Exception as e:
            print(f"(X) Exception while analyzing {self.file_url}: {e}")
            return {"error": str(e)}