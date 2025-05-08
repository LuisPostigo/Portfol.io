import os
import json
import re
from collections import defaultdict
from statistics import mean

ANALYSIS_ROOT = os.path.join("backend", "services", "github_analyzer", "analized_files")


def normalize_skill(skill: str) -> str:
    return re.sub(r"[-_\s]+", " ", skill.lower().strip())


class AnalyzeRepoForGivenUser:
    def __init__(self, github_url: str, llm_model):
        self.github_url = github_url
        self.username = github_url.rstrip("/").split("/")[-1].lower()
        self.user_dir = os.path.join(ANALYSIS_ROOT, self.username)

        if llm_model is None:
            raise ValueError("llm_model must be provided to AnalyzeRepoForGivenUser.")
        self.model = llm_model

    class ScoresAndCoverages:
        def __init__(self, user_dir):
            self.user_dir = user_dir
            self.skill_data = defaultdict(lambda: {"depths": [], "coverage_count": 0, "total": 0})

        @staticmethod
        def extract_json_object(text: str):
            brace_count = 0
            json_start = -1
            for i, c in enumerate(text):
                if c == '{':
                    if brace_count == 0:
                        json_start = i
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0 and json_start != -1:
                        json_str = text[json_start:i + 1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue
            return None

        def compute(self):
            for root, _, files in os.walk(self.user_dir):
                for file in files:
                    if file.endswith(".json"):
                        path = os.path.join(root, file)
                        try:
                            with open(path, encoding="utf-8") as f:
                                data = json.load(f)
                                result_text = data.get("result", "")
                                skill_dict = self.extract_json_object(result_text)
                                if not skill_dict:
                                    print(f"(!) No valid JSON object found in {file}")
                                    continue

                                for raw_skill, details in skill_dict.items():
                                    if not isinstance(details, dict):
                                        print(f"(!) Skipping malformed skill entry: {raw_skill} -> {details}")
                                        continue

                                    skill = normalize_skill(raw_skill)
                                    depth = details.get("depth", 0)
                                    coverage = details.get("coverage", False)

                                    self.skill_data[skill]["total"] += 1
                                    if coverage:
                                        self.skill_data[skill]["depths"].append(depth)
                                        self.skill_data[skill]["coverage_count"] += 1
                        except Exception as e:
                            print(f"(X) Error processing {file}: {e}")
                            continue

            result = {}
            for skill, stats in self.skill_data.items():
                avg_depth = mean(stats["depths"]) if stats["depths"] else 0
                result[skill] = {
                    "avg_depth": round(avg_depth, 2),
                    "coverage": f"{stats['coverage_count']}/{stats['total']}"
                }

            return result

    class FinalLLMAssessment:
        def __init__(self, user_dir, model):
            self.user_dir = user_dir
            self.model = model

        def gather_batches(self, max_tokens_per_chunk=3000):
            chunks = []
            current_chunk = ""
            for root, _, files in os.walk(self.user_dir):
                for file in files:
                    if file.endswith(".json"):
                        try:
                            with open(os.path.join(root, file), encoding="utf-8") as f:
                                result = json.load(f).get("result", "").strip()
                                if len(current_chunk) + len(result) > max_tokens_per_chunk:
                                    chunks.append(current_chunk)
                                    current_chunk = result
                                else:
                                    current_chunk += "\n\n" + result
                        except:
                            continue
            if current_chunk:
                chunks.append(current_chunk)
            return chunks

        def summarize_chunk(self, chunk):
            prompt = f"""
You are a senior developer evaluating the portfolio of a candidate.
Below is a batch of project assessments evaluating their code across various skills.
Summarize this batch by describing the strengths and weaknesses demonstrated:

Assessments:
{chunk}

Partial Summary:
"""
            result = self.model.create_completion(
                prompt=prompt,
                max_tokens=512,
                temperature=0.4
            )
            return result["choices"][0]["text"].strip()

        def generate_summary(self):
            chunks = self.gather_batches()
            summaries = [self.summarize_chunk(chunk) for chunk in chunks]

            final_prompt = f"""
You are a senior developer evaluating a programming candidate based on several partial summaries.
Based on the following batch evaluations, write a full final report on the candidate:

{chr(10).join(summaries)}

Final Evaluation:
"""
            response = self.model.create_completion(prompt=final_prompt, max_tokens=512, temperature=0.4)
            return response["choices"][0]["text"].strip()

    def analyze(self):
        if not os.path.exists(self.user_dir):
            return {
                "success": False,
                "username": self.username,
                "error": f"No analysis directory found for GitHub user '{self.username}'."
            }

        try:
            score_analyzer = self.ScoresAndCoverages(self.user_dir)
            skill_scores = score_analyzer.compute()

            final_llm = self.FinalLLMAssessment(self.user_dir, self.model)
            final_summary = final_llm.generate_summary()

            return {
                "success": True,
                "username": self.username,
                "skill_scores": skill_scores,
                "final_summary": final_summary
            }

        except Exception as e:
            return {
                "success": False,
                "username": self.username,
                "error": f"Unexpected error during analysis: {str(e)}"
            }

    def get_summary_text(self):
        return self.analyze()

if __name__ == "__main__":
    analyzer = AnalyzeRepoForGivenUser("https://github.com/KhizarFareed")
    result = analyzer.get_summary_text()
    print ("========================================================================")
    print (result)
